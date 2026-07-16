"""Pathology entity extractor.

Extracts structured entities from pathology report text using regex patterns.
"""

from __future__ import annotations

import re

from modules.extract_spans import with_span


SPECIMEN_TYPE_PATTERN = re.compile(
    r"\b(biopsy|excision|resection|aspiration|cytology|smear|swab)\b",
    re.IGNORECASE,
)

SPECIMEN_SITE_PATTERN = re.compile(
    r"(?:specimen|site|source):?\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

DIAGNOSIS_PATTERN = re.compile(
    r"(?:DIAGNOSIS|FINAL DIAGNOSIS|PATHOLOGIC DIAGNOSIS):?\s*(.+?)(?=\n\s*[A-Z]{2,}|\Z)",
    re.DOTALL | re.IGNORECASE,
)

GRADE_PATTERN = re.compile(
    r"\b(?:grade|Gleason|Nottingham)\s*:?\s*([\w\s/\+]+?)(?:\n|[,;.])",
    re.IGNORECASE,
)

STAGE_PATTERN = re.compile(
    r"\b(pT\d[a-d]?(?:N\d)?(?:M\d)?|Stage\s+[IVX]+[A-C]?)\b",
    re.IGNORECASE,
)

MARGINS_PATTERN = re.compile(
    r"(?:MARGINS?):?\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

SPECIAL_STAINS_PATTERN = re.compile(
    r"(?:SPECIAL\s+STAINS?|IMMUNOHISTOCHEMISTRY|IHC):?\s*(.+?)(?=\n\s*[A-Z]{2,}|\Z)",
    re.DOTALL | re.IGNORECASE,
)

PATHOLOGIST_PATTERN = re.compile(
    r"(?:pathologist|signed\s+by|reported\s+by):?\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

PATH_REPORT_DATE_PATTERN = re.compile(
    r"(?:date|report\s+date|collection\s+date):?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
    re.IGNORECASE,
)


def extract_pathology_entities(text: str) -> list[dict]:
    """Extract structured entities from pathology report text."""
    entities: list[dict] = []

    specimen_type = SPECIMEN_TYPE_PATTERN.search(text)
    if specimen_type:
        entities.append(with_span({
            "entity_type": "specimen_type",
            "entity_value": specimen_type.group(1).strip().lower(),
            "confidence": 0.9,
            "source_page": None,
        }, text, specimen_type))

    site = SPECIMEN_SITE_PATTERN.search(text)
    if site:
        entities.append(with_span({
            "entity_type": "specimen_site",
            "entity_value": site.group(1).strip(),
            "confidence": 0.85,
            "source_page": None,
        }, text, site))

    diagnosis = DIAGNOSIS_PATTERN.search(text)
    if diagnosis:
        entities.append(with_span({
            "entity_type": "diagnosis",
            "entity_value": diagnosis.group(1).strip()[:500],
            "confidence": 0.85,
            "source_page": None,
        }, text, diagnosis))

    grade = GRADE_PATTERN.search(text)
    if grade:
        entities.append(with_span({
            "entity_type": "grade",
            "entity_value": grade.group(1).strip(),
            "confidence": 0.8,
            "source_page": None,
        }, text, grade))

    stage = STAGE_PATTERN.search(text)
    if stage:
        entities.append(with_span({
            "entity_type": "stage",
            "entity_value": stage.group(1).strip(),
            "confidence": 0.85,
            "source_page": None,
        }, text, stage))

    margins = MARGINS_PATTERN.search(text)
    if margins:
        entities.append(with_span({
            "entity_type": "margins",
            "entity_value": margins.group(1).strip(),
            "confidence": 0.85,
            "source_page": None,
        }, text, margins))

    stains = SPECIAL_STAINS_PATTERN.search(text)
    if stains:
        entities.append(with_span({
            "entity_type": "special_stains",
            "entity_value": stains.group(1).strip()[:500],
            "confidence": 0.8,
            "source_page": None,
        }, text, stains))

    pathologist = PATHOLOGIST_PATTERN.search(text)
    if pathologist:
        entities.append(with_span({
            "entity_type": "pathologist",
            "entity_value": pathologist.group(1).strip(),
            "confidence": 0.8,
            "source_page": None,
        }, text, pathologist))

    report_date = PATH_REPORT_DATE_PATTERN.search(text)
    if report_date:
        entities.append(with_span({
            "entity_type": "report_date",
            "entity_value": report_date.group(1).strip(),
            "confidence": 0.9,
            "source_page": None,
        }, text, report_date))

    return entities
