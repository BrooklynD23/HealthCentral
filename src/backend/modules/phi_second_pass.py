"""Independent second PHI detector (RSI1-DONATE PR-2, DON-DETECTOR a).

Detect-only: returns the Safe Harbor category of each hit, never the matched
value and never rewritten text (45 CFR 164.514(b)(2)). Written independently
of modules/redaction.py (no import of it; HC-DON-012). Any hit drops the
record in modules/data_donation.collect.
"""

from __future__ import annotations

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


def detect(text: str | None) -> list[Hit]:
    """Return one Hit per matching category occurrence in ``text``."""
    if not text:
        return []
    hits: list[Hit] = []
    for category, pattern in _PATTERNS:
        hits.extend(Hit(category) for _ in pattern.finditer(text))
    return hits
