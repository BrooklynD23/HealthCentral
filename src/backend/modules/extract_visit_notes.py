"""Visit notes entity extractor.

Extracts structured entities from progress notes, discharge summaries, etc.
"""

from __future__ import annotations

import re


VISIT_TYPE_PATTERN = re.compile(
    r"\b(progress\s+note|discharge\s+summary|consult\s+note|follow[\-\s]?up|initial\s+visit|annual\s+exam|physical\s+exam)\b",
    re.IGNORECASE,
)

CHIEF_COMPLAINT_PATTERN = re.compile(
    r"(?:chief\s+complaint|CC|reason\s+for\s+visit):?\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

ASSESSMENT_PATTERN = re.compile(
    r"(?:ASSESSMENT|A/P|ASSESSMENT\s+AND\s+PLAN):?\s*(.+?)(?=\n\s*(?:PLAN|[A-Z]{2,})|\Z)",
    re.DOTALL | re.IGNORECASE,
)

PLAN_PATTERN = re.compile(
    r"(?:PLAN):?\s*(.+?)(?=\n\s*[A-Z]{2,}|\Z)",
    re.DOTALL | re.IGNORECASE,
)

DIAGNOSES_PATTERN = re.compile(
    r"(?:DIAGNOS[IE]S?|ICD[\-\s]?\d+):?\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

PROVIDER_PATTERN = re.compile(
    r"(?:provider|physician|attending|seen\s+by|signed\s+by):?\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)

VISIT_DATE_PATTERN = re.compile(
    r"(?:date\s+of\s+(?:visit|service)|visit\s+date|encounter\s+date):?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
    re.IGNORECASE,
)

VITALS_PATTERN = re.compile(
    r"(?:VITAL\s+SIGNS?|VITALS?):?\s*(.+?)(?=\n\s*[A-Z]{2,}|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def extract_visit_note_entities(text: str) -> list[dict]:
    """Extract structured entities from visit note text."""
    entities: list[dict] = []

    visit_types = VISIT_TYPE_PATTERN.findall(text)
    if visit_types:
        entities.append({
            "entity_type": "visit_type",
            "entity_value": visit_types[0].strip().lower(),
            "confidence": 0.9,
            "source_page": None,
        })

    cc = CHIEF_COMPLAINT_PATTERN.search(text)
    if cc:
        entities.append({
            "entity_type": "chief_complaint",
            "entity_value": cc.group(1).strip(),
            "confidence": 0.9,
            "source_page": None,
        })

    assessment = ASSESSMENT_PATTERN.search(text)
    if assessment:
        entities.append({
            "entity_type": "assessment",
            "entity_value": assessment.group(1).strip()[:500],
            "confidence": 0.85,
            "source_page": None,
        })

    plan = PLAN_PATTERN.search(text)
    if plan:
        entities.append({
            "entity_type": "plan",
            "entity_value": plan.group(1).strip()[:500],
            "confidence": 0.85,
            "source_page": None,
        })

    diagnoses = DIAGNOSES_PATTERN.search(text)
    if diagnoses:
        entities.append({
            "entity_type": "diagnoses",
            "entity_value": diagnoses.group(1).strip(),
            "confidence": 0.8,
            "source_page": None,
        })

    provider = PROVIDER_PATTERN.search(text)
    if provider:
        entities.append({
            "entity_type": "provider",
            "entity_value": provider.group(1).strip(),
            "confidence": 0.8,
            "source_page": None,
        })

    visit_date = VISIT_DATE_PATTERN.search(text)
    if visit_date:
        entities.append({
            "entity_type": "visit_date",
            "entity_value": visit_date.group(1).strip(),
            "confidence": 0.9,
            "source_page": None,
        })

    vitals = VITALS_PATTERN.search(text)
    if vitals:
        entities.append({
            "entity_type": "vitals",
            "entity_value": vitals.group(1).strip()[:300],
            "confidence": 0.85,
            "source_page": None,
        })

    return entities
