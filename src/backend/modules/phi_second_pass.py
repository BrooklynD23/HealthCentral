"""Independent second PHI detector (RSI1-DONATE PR-2, DON-DETECTOR a).

Detect-only: returns the Safe Harbor category of each hit, never the matched
value and never rewritten text (45 CFR 164.514(b)(2)). Written independently
of modules/redaction.py (no import of it; HC-DON-012). Any hit drops the
record in modules/data_donation.collect.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

CATEGORIES = (
    "name", "geographic", "date", "phone", "email", "ssn", "mrn",
    "account_number", "url", "ip_address", "age_over_89", "device_vehicle_id",
)

# On-device model pass (DON-NER-MODEL "Adopt obi, agent sets", configuration C1).
# The pin is code, not config/model_manifest.json. Only scripts/download_models.py
# phi-ner fetches it; the runtime loads the directory offline and fails closed.
PHI_NER_REPO_ID = "obi/deid_roberta_i2b2"
PHI_NER_REVISION = "78f2152eb93ddd817290ce8dbe46f1a6685e09fc"
PHI_NER_WEIGHTS_SHA256 = "557152273204b0a28593da47b423dd0206e87c3b94839bd28ff8d6d90f0cf261"
PHI_NER_FETCH_FILES = (
    "README.md", "config.json", "merges.txt", "model.safetensors",
    "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.json",
)
PHI_NER_THRESHOLD = 0.5
PHI_NER_WINDOW = 512
PHI_NER_STRIDE = 64
# Model label -> hit category. AGE is handled by value (age_over_89 only for >= 90);
# ID is an identifier number of any kind (SSN, MRN, account, device): category "id".
PHI_NER_LABEL_CATEGORY = {
    "PATIENT": "name", "STAFF": "name", "HCW": "name", "PER": "name",
    "LOC": "geographic",
    "DATE": "date", "PHONE": "phone", "EMAIL": "email",
    "ID": "id",
}
_BACKEND_DIR = Path(__file__).resolve().parents[1]


def resolve_phi_ner_model_dir() -> Path:
    """Directory the model is loaded from (PHI_NER_MODEL_PATH); relative to src/backend."""
    from core.config import settings

    path = Path(settings.phi_ner_model_path)
    return path if path.is_absolute() else _BACKEND_DIR / path

_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|"
    r"Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
)
_CAP = r"(?:[A-Z]'[A-Z]|[A-Z])[a-z]+(?:[-'][A-Z][a-z]+)?"
# "my X is 123", "X: 123", "X = 123"
_IS = r"(?:\s*(?:[:#=]|\bis\b|\bwas\b))?\s*"
# Clinical/analyte/heading words that are capitalised in assistant prose but are not names.
_STOP = (
    "results|result|total|white|red|blood|cells|cell|count|reference|range|vitamin|hemoglobin|cholesterol|"
    "glucose|creatinine|potassium|sodium|calcium|magnesium|platelets|ferritin|thyroid|kidney|liver|heart|"
    "rate|pressure|oxygen|body|mass|index|fasting|urine|serum|panel|test|tests|normal|high|low|lab|labs|"
    "report|summary|note|notes|status|level|levels|value|values|your|my|the|this|that|what|why|how"
)
_NOT_STOP = rf"(?!(?i:{_STOP})\b)"
_NAME = rf"{_NOT_STOP}{_CAP}"
_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ "
    "NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).replace(" ", "|")

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,10}\b")),
    ("url", re.compile(r"\b(?:https?://|www\.)\S+", re.I)),
    ("ip_address", re.compile(r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b")),
    ("ssn", re.compile(
        rf"\b\d{{3}}-\d{{2}}-\d{{4}}\b|\b\d{{3}} \d{{2}} \d{{4}}\b"
        rf"|\b(?:SSN|social security(?: number| no\.?| #)?){_IS}\d{{3}}[-. ]?\d{{2}}[-. ]?\d{{4}}\b", re.I)),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[-. ])?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)")),
    ("date", re.compile(
        rf"\b\d{{1,2}}([-/.])\d{{1,2}}\1\d{{2,4}}\b|\b\d{{4}}([-/.])\d{{1,2}}\2\d{{1,2}}(?!\d)"
        rf"|(?<![\d/.])(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])(?![\d/])|\b{_MONTH}\s+\d{{4}}\b"
        rf"|\b{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,\s*\d{{4}})?\b|\b\d{{1,2}}(?:st|nd|rd|th)?(?:\s+of)?\s+{_MONTH}\b"
    )),
    ("mrn", re.compile(
        rf"\b(?:MRN|medical record(?: number| no\.?| #)?|chart(?: number| no\.?| #)){_IS}[A-Z]*[- ]?\d{{4,}}\b", re.I)),
    ("account_number", re.compile(
        rf"\b(?:account|acct|member|policy|insurance|beneficiary|subscriber|license|licence|certificate|"
        rf"patient id|health plan)(?: id| number| no\.?| #)?{_IS}[A-Z]{{0,4}}-?\d[\w-]{{3,}}\b", re.I)),
    # underscore-joined labels ("patient_id_-_98765"): broad on purpose, a hit only drops the record
    ("account_number", re.compile(r"\b(?:patient|member|account|policy|mrn|ssn|insurance)_[\w#.=-]{0,40}\d{3,}", re.I)),
    ("device_vehicle_id", re.compile(
        r"\b(?:VIN|serial(?: number| no\.?| #)?|UDI|device id|plate)(?:\s*[:#])?\s*[A-Z0-9-]{5,}\b", re.I)),
    ("age_over_89", re.compile(r"\b(?:age[d]?(?:\s*:)?\s*(?:9\d|1[0-2]\d)|(?:9\d|1[0-2]\d)[- ]y(?:ea)?rs?[- ]old|(?:9\d|1[0-2]\d)\s*y/?o)\b", re.I)),
    ("geographic", re.compile(
        rf"\b\d{{1,6}}\s+(?:[A-Z][a-z]+\s+){{1,3}}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way)\b\.?"
        rf"|\b(?:{_STATES})\s+\d{{5}}(?:-\d{{4}})?\b|\b[Zz][Ii][Pp](?: code)?{_IS}\d{{5}}\b|\b{_CAP},\s*(?:{_STATES})\b")),
    ("name", re.compile(
        rf"\b(?i:patient name|name|patient|pt)\.?(?:\s*(?i:is|:))?\s*{_NAME}(?:\s+[A-Z]\.)?(?:\s+{_NAME})?"
        # honorifics: no stop-list ("Dr. White" is a name)
        rf"|\b(?:[Mm]r|[Mm]rs|[Mm]s|[Mm]iss|[Dd]r)\.?\s*{_CAP}(?:\s+[A-Z]\.)?(?:\s+{_CAP})?"
        r"|\b(?:patient_)?name_*[=:]_*[A-Za-z]"
        rf"|\b(?i:seen by|referred by|signed by|spoke with|guardian|spouse|wife|husband|mother|father|son|daughter)\s+(?:Dr\.?\s+|Mr\.?\s+|Mrs\.?\s+|Ms\.?\s+)?{_NAME}(?:\s+{_NAME})?"
        rf"|\b{_NAME}\s+{_NAME}\b"
    )),
)


@dataclass(frozen=True)
class Hit:
    """One detection. Carries the Safe Harbor category only, never the value."""

    category: str


class PhiNerUnavailableError(RuntimeError):
    """The on-device PHI model is missing, fails its sha256 pin, or cannot load offline.

    Messages are path-free (they reach logs). Nothing degrades to rules only.
    """


_SPELLED_AGE = {"ninety": 90, "one hundred": 100, "a hundred": 100, "hundred": 100}
_AGE_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
# Test seam: a duck-typed model with labelled_spans(text). None means use the bundle.
_MODEL_OVERRIDE = None
# The verified, loaded bundle for this process (a failure is never cached).
_MODEL_CACHE = None


def _age_value(span: str) -> int | None:
    m = re.search(r"\d{1,3}", span)
    if m:
        return int(m.group())
    m = re.search(
        r"\b(one hundred|a hundred|hundred|ninety)(?:[\s-]+(one|two|three|four|five|six|seven|eight|nine))?\b",
        span.lower(),
    )
    if not m:
        return None
    return _SPELLED_AGE[m.group(1)] + (_AGE_UNITS[m.group(2)] if m.group(2) and m.group(1) == "ninety" else 0)


class PhiNerModel:
    """obi/deid_roberta_i2b2 loaded offline. Returns (label, span text) pairs only inside the module."""

    def __init__(self, tokenizer, model):
        self._tok = tokenizer
        self._model = model
        self._id2label = model.config.id2label

    def labelled_spans(self, text: str) -> list[tuple[str, str]]:
        """(base label, span text) per run of same-label tokens with probability >= threshold."""
        import torch

        enc = self._tok(
            text, return_offsets_mapping=True, truncation=True, max_length=PHI_NER_WINDOW,
            stride=PHI_NER_STRIDE, return_overflowing_tokens=True, padding=True, return_tensors="pt",
        )
        offsets = enc.pop("offset_mapping")
        enc.pop("overflow_to_sample_mapping", None)
        with torch.no_grad():
            logits = self._model(**{k: v for k, v in enc.items() if k in ("input_ids", "attention_mask", "token_type_ids")}).logits
        probs = logits.softmax(-1)
        spans: list[tuple[str, str]] = []
        for w in range(probs.shape[0]):
            p, idx = probs[w].max(-1)
            cur, start, end = None, 0, 0
            for t in range(probs.shape[1]):
                a, b = offsets[w][t].tolist()
                label = self._id2label[int(idx[t])]
                base = label.split("-", 1)[-1] if "-" in label else label
                ok = a != b and base != "O" and float(p[t]) >= PHI_NER_THRESHOLD
                if ok and base == cur and a <= end + 1:
                    end = b
                    continue
                if cur is not None:
                    spans.append((cur, text[start:end]))
                cur, start, end = (base, a, b) if ok else (None, 0, 0)
            if cur is not None:
                spans.append((cur, text[start:end]))
        return spans


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_bundle(directory: Path) -> None:
    missing = [name for name in PHI_NER_FETCH_FILES if not (directory / name).is_file()]
    if missing:
        raise PhiNerUnavailableError(
            f"on-device PHI model not installed ({len(missing)} files missing). "
            "Fetch it once with: cd src/backend && python scripts/download_models.py phi-ner"
        )
    if _sha256(directory / "model.safetensors") != PHI_NER_WEIGHTS_SHA256:
        raise PhiNerUnavailableError("on-device PHI model weights do not match the pinned sha256")


def _load_model() -> PhiNerModel:
    """Load the verified bundle from the local directory only (local_files_only=True)."""
    import logging

    directory = resolve_phi_ner_model_dir()
    _verify_bundle(directory)
    try:
        from transformers import AutoModelForTokenClassification, AutoTokenizer
    except ImportError:
        raise PhiNerUnavailableError("transformers is not installed") from None
    # transformers logs the model path at INFO while loading; keep it out of log sinks.
    quiet = [logging.getLogger(n) for n in ("transformers",)]
    prev_levels = [lg.level for lg in quiet]
    for lg in quiet:
        lg.setLevel(max(lg.getEffectiveLevel(), logging.WARNING))
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(directory), local_files_only=True)
        model = AutoModelForTokenClassification.from_pretrained(str(directory), local_files_only=True).eval()
    except Exception as exc:  # corrupt or incompatible files: fail closed, never download
        raise PhiNerUnavailableError(f"on-device PHI model failed to load: {type(exc).__name__}") from None
    finally:
        for lg, level in zip(quiet, prev_levels):
            lg.setLevel(level)
    return PhiNerModel(tokenizer, model)


def _get_model():
    global _MODEL_CACHE
    if _MODEL_OVERRIDE is not None:
        return _MODEL_OVERRIDE
    if _MODEL_CACHE is None:
        _MODEL_CACHE = _load_model()
    return _MODEL_CACHE


def ensure_model() -> None:
    """Raise PhiNerUnavailableError unless the verified model is available."""
    _get_model()


def rule_hits(text: str | None) -> list[Hit]:
    """Rules only (configuration C0): one Hit per matching category occurrence."""
    if not text:
        return []
    hits: list[Hit] = []
    for category, pattern in _PATTERNS:
        hits.extend(Hit(category) for _ in pattern.finditer(text))
    return hits


def model_hits(text: str | None) -> list[Hit]:
    """The on-device model's hits, mapped to categories. Raises PhiNerUnavailableError if absent."""
    if not text:
        return []
    hits: list[Hit] = []
    for label, span in _get_model().labelled_spans(text):
        if label == "AGE":
            value = _age_value(span)
            if value is not None and value >= 90:
                hits.append(Hit("age_over_89"))
        elif label in PHI_NER_LABEL_CATEGORY:
            hits.append(Hit(PHI_NER_LABEL_CATEGORY[label]))
    return hits


def detect(text: str | None) -> list[Hit]:
    """Return one Hit per matching occurrence: the rules (C0) plus the on-device model (C1).

    Category only, never the matched value. Raises PhiNerUnavailableError when
    the model is not available: a missing model is never a rules-only answer.
    """
    if not text:
        return []
    return rule_hits(text) + model_hits(text)
