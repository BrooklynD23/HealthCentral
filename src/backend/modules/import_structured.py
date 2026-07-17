"""Structured import parsers for lab CSV and FHIR R4 Bundle files (HC-M23).

Pure, DB-free parsers, mirroring the purity contract of
``modules/fhir_export.py``: no I/O, no network, no LLM. Callers (currently
only ``api/documents.py``) read the decrypted file text and hand it to
``parse_lab_csv``/``parse_fhir_bundle``, then persist the result themselves.

Every parsed fact carries ``quote=None`` — a CSV cell or a FHIR JSON field
has no verbatim document-text span the way an OCR'd PDF does — and a flat
``confidence`` of 0.6. Persistence always marks these unverified
(``user_verified=False`` / ``verified_by_user=None``) so imported data enters
the same review queue as everything else; that policy lives in the caller,
not here.

Untrusted input: file content reaching this module is attacker-controllable
(a user-supplied upload). Parsing is stdlib-only (``csv``/``json``, no
``eval``/deserialization of code), and every free-text field is length-capped
via ``_cap`` before being returned so a hostile huge value can't balloon
storage. Values that fail to parse are recorded as inert text (``value_text``)
or skipped with a reason — never guessed at.

No invented dates: an unparseable or absent date leaves the observation
undated (``collected_at=None``) rather than defaulting to "now".
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

IMPORT_CONFIDENCE = 0.6
IMPORT_EXTRACTION_VERSION = "import-v1"

# Untrusted-input guard: caps every free-text field pulled from an import
# file so a hostile huge value can't balloon into unbounded storage.
_MAX_FIELD_LEN = 2000


@dataclass
class StructuredImportResult:
    """Result of parsing one structured import file."""

    observations: list[dict] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    # Each item: {"reason": str, "detail": str}
    skipped: list[dict] = field(default_factory=list)
    source_kind: str = ""  # "lab_csv" | "fhir_bundle"


def _cap(text: Optional[str]) -> Optional[str]:
    """Length-cap a free-text field. Untrusted input never grows unbounded."""
    if text is None:
        return None
    return str(text)[:_MAX_FIELD_LEN]


def _parse_float(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y")


def _parse_date(raw: Optional[str]) -> Optional[str]:
    """Best-effort ISO-8601 / MM-DD-YYYY date parse -> ISO date string.

    Never invents a date: any unparseable or missing value returns None so
    the observation stays undated rather than being guessed at.
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    # FHIR effectiveDateTime is often a full ISO datetime (with time/offset).
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

# Canonical headers match ExportModule.export_csv (modules/export.py):
# Date, Analyte, Value, Unit, Reference Low, Reference High, Flag.
# Aliases are matched case-insensitively with underscores/spaces folded
# together (see _normalize_header).
_HEADER_ALIASES: dict[str, set[str]] = {
    "date": {"date", "collected", "collection date"},
    "analyte": {"analyte", "test", "name"},
    "value": {"value", "result"},
    "unit": {"unit", "units"},
    "ref_low": {"ref low", "low", "reference low"},
    "ref_high": {"ref high", "high", "reference high"},
    "flag": {"flag", "abnormal"},
}
_ALIAS_TO_FIELD: dict[str, str] = {
    alias: canonical for canonical, aliases in _HEADER_ALIASES.items() for alias in aliases
}


def _normalize_header(raw: str) -> str:
    return re.sub(r"[\s_]+", " ", raw.strip().lower())


def _build_header_map(fieldnames: Optional[list[str]]) -> dict[str, str]:
    """Map canonical field name -> the actual CSV header string present."""
    mapping: dict[str, str] = {}
    for header in fieldnames or []:
        canonical = _ALIAS_TO_FIELD.get(_normalize_header(header))
        if canonical and canonical not in mapping:
            mapping[canonical] = header
    return mapping


def parse_lab_csv(text: str) -> StructuredImportResult:
    """Parse a CSV of lab results into observation dicts.

    Design decision (documented per the milestone spec): an empty CSV (no
    content, or a header with zero data rows) is NOT an error here — it
    returns a zero-observation result with a `skipped` explanation. The
    caller still creates the Document row for record-keeping (the user did
    attempt an import); this mirrors the app's existing tolerant behavior
    for zero-observation OCR results rather than hard-failing the request.
    """
    result = StructuredImportResult(source_kind="lab_csv")

    if not text or not text.strip():
        result.skipped.append({"reason": "empty_file", "detail": "CSV file was empty"})
        return result

    reader = csv.DictReader(io.StringIO(text))
    header_map = _build_header_map(reader.fieldnames)

    if "analyte" not in header_map:
        result.skipped.append({
            "reason": "no_analyte_column",
            "detail": "CSV has no recognizable analyte/test/name column",
        })
        return result

    row_count = 0
    for i, row in enumerate(reader, start=2):  # header is row 1
        row_count += 1
        analyte_raw = (row.get(header_map["analyte"]) or "").strip()
        if not analyte_raw:
            result.skipped.append({
                "reason": "missing_analyte",
                "detail": f"row {i}: no analyte/test name",
            })
            continue

        raw_value = row.get(header_map["value"]) if "value" in header_map else None
        value = _parse_float(raw_value)
        value_text = None
        if value is None and raw_value and raw_value.strip():
            value_text = _cap(raw_value.strip())

        raw_date = row.get(header_map["date"]) if "date" in header_map else None
        raw_unit = (row.get(header_map["unit"]) or "").strip() if "unit" in header_map else ""
        raw_flag = (row.get(header_map["flag"]) or "").strip() if "flag" in header_map else ""

        result.observations.append({
            "analyte_raw": _cap(analyte_raw),
            "value": value,
            "value_text": value_text,
            "unit": _cap(raw_unit) or None,
            "ref_low": _parse_float(row.get(header_map["ref_low"])) if "ref_low" in header_map else None,
            "ref_high": _parse_float(row.get(header_map["ref_high"])) if "ref_high" in header_map else None,
            "ref_range_text": None,
            "flag": _cap(raw_flag) or None,
            "collected_at": _parse_date(raw_date),
            "confidence": IMPORT_CONFIDENCE,
        })

    if row_count == 0:
        result.skipped.append({"reason": "no_data_rows", "detail": "CSV had a header but no data rows"})

    return result


# ---------------------------------------------------------------------------
# FHIR R4 Bundle
# ---------------------------------------------------------------------------

# MedicationStatement.status -> verb-first prefix (HC-M13 verb-first
# contract: entity_value starts with start/stop/increase/decrease/change/
# continue). FHIR statuses without a clear HealthCentral analog fall back to
# "continue" (the safest / least assertive verb) rather than guessing.
_MED_STATUS_VERB: dict[str, str] = {
    "active": "start",
    "intended": "start",
    "completed": "stop",
    "stopped": "stop",
    "on-hold": "stop",
    "entered-in-error": "stop",
}


def _clean_phrase(text: str) -> str:
    return " ".join(text.split()).strip(" .,;:").strip()


def _map_fhir_observation(resource: dict) -> Optional[dict]:
    code = resource.get("code") if isinstance(resource.get("code"), dict) else {}
    analyte_raw = code.get("text")
    if not analyte_raw or not str(analyte_raw).strip():
        return None
    analyte_raw = str(analyte_raw).strip()

    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    vq = resource.get("valueQuantity")
    if isinstance(vq, dict) and vq.get("value") is not None:
        try:
            value = float(vq["value"])
        except (TypeError, ValueError):
            value = None
        if vq.get("unit"):
            unit = str(vq["unit"])
    if value is None:
        vs = resource.get("valueString")
        if vs:
            value_text = str(vs)

    ref_low = ref_high = None
    ref_range_text = None
    ranges = resource.get("referenceRange")
    if isinstance(ranges, list) and ranges and isinstance(ranges[0], dict):
        r0 = ranges[0]
        low = r0.get("low")
        if isinstance(low, dict) and low.get("value") is not None:
            try:
                ref_low = float(low["value"])
            except (TypeError, ValueError):
                ref_low = None
        high = r0.get("high")
        if isinstance(high, dict) and high.get("value") is not None:
            try:
                ref_high = float(high["value"])
            except (TypeError, ValueError):
                ref_high = None
        if r0.get("text"):
            ref_range_text = str(r0["text"])

    flag = None
    interp = resource.get("interpretation")
    if isinstance(interp, list) and interp and isinstance(interp[0], dict):
        if interp[0].get("text"):
            flag = str(interp[0]["text"])

    effective = resource.get("effectiveDateTime")
    collected_at = _parse_date(effective) if isinstance(effective, str) else None

    return {
        "analyte_raw": _cap(analyte_raw),
        "value": value,
        "value_text": _cap(value_text),
        "unit": _cap(unit),
        "ref_low": ref_low,
        "ref_high": ref_high,
        "ref_range_text": _cap(ref_range_text),
        "flag": _cap(flag),
        "collected_at": collected_at,
        "confidence": IMPORT_CONFIDENCE,
    }


def _map_medication_statement(resource: dict) -> Optional[dict]:
    med_concept = resource.get("medicationCodeableConcept")
    med_concept = med_concept if isinstance(med_concept, dict) else {}
    med_name = med_concept.get("text")
    if not med_name:
        codings = med_concept.get("coding")
        if isinstance(codings, list) and codings and isinstance(codings[0], dict):
            med_name = codings[0].get("display")
    if not med_name or not str(med_name).strip():
        return None
    med_name = str(med_name).strip()

    status = str(resource.get("status") or "").strip().lower()
    verb = _MED_STATUS_VERB.get(status, "continue")

    dosage_text = None
    dosages = resource.get("dosage")
    if isinstance(dosages, list) and dosages and isinstance(dosages[0], dict):
        dosage_text = dosages[0].get("text")

    parts = [verb, med_name]
    if dosage_text and str(dosage_text).strip():
        parts.append(str(dosage_text).strip())
    entity_value = _cap(_clean_phrase(" ".join(parts)).lower())

    return {
        "entity_type": "medication_change",
        "category": "visit_notes",
        "entity_value": entity_value,
        "quote": None,
        "confidence": IMPORT_CONFIDENCE,
    }


def _map_condition(resource: dict) -> Optional[dict]:
    code = resource.get("code") if isinstance(resource.get("code"), dict) else {}
    value = code.get("text")
    if not value or not str(value).strip():
        return None
    return {
        "entity_type": "diagnosis",
        "category": "visit_notes",
        "entity_value": _cap(str(value).strip()),
        "quote": None,
        "confidence": IMPORT_CONFIDENCE,
    }


def parse_fhir_bundle(text: str) -> StructuredImportResult:
    """Parse a FHIR R4 ``Bundle`` JSON string into observation/entity dicts.

    Raises ``ValueError`` for malformed JSON or JSON that isn't a Bundle —
    callers (the import route) turn that into a 400 with a clear message.
    Once past that gate, unknown/unsupported resource types and individual
    resources missing required fields are counted in ``skipped`` rather than
    raising, so one bad entry never fails the whole import.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict) or data.get("resourceType") != "Bundle":
        raise ValueError("JSON is not a FHIR R4 Bundle (resourceType != \"Bundle\")")

    result = StructuredImportResult(source_kind="fhir_bundle")

    for entry in data.get("entry") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("resource"), dict):
            result.skipped.append({
                "reason": "invalid_entry",
                "detail": "bundle entry has no resource object",
            })
            continue
        resource = entry["resource"]
        resource_type = resource.get("resourceType")

        if resource_type == "Observation":
            obs = _map_fhir_observation(resource)
            if obs is None:
                result.skipped.append({
                    "reason": "unparseable_observation",
                    "detail": f"Observation {resource.get('id', '?')} had no usable code.text",
                })
            else:
                result.observations.append(obs)
        elif resource_type == "MedicationStatement":
            ent = _map_medication_statement(resource)
            if ent is None:
                result.skipped.append({
                    "reason": "unparseable_medication",
                    "detail": f"MedicationStatement {resource.get('id', '?')} had no medication text",
                })
            else:
                result.entities.append(ent)
        elif resource_type == "Condition":
            ent = _map_condition(resource)
            if ent is None:
                result.skipped.append({
                    "reason": "unparseable_condition",
                    "detail": f"Condition {resource.get('id', '?')} had no code.text",
                })
            else:
                result.entities.append(ent)
        else:
            result.skipped.append({
                "reason": "unknown_resource_type",
                "detail": str(resource_type),
            })

    return result
