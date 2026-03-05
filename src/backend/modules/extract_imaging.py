"""Imaging entity extractor.

Extracts structured entities from imaging/radiology report text using regex patterns.
"""

from __future__ import annotations

import re


MODALITY_PATTERN = re.compile(
    r"\b(MRI|CT\s*scan|CT|X[\-\s]?ray|ultrasound|radiograph|fluoroscopy|mammograph|PET\s*scan|PET/CT)\b",
    re.IGNORECASE,
)

BODY_REGION_PATTERN = re.compile(
    r"\b(brain|head|chest|abdomen|pelvis|spine|lumbar|cervical|thoracic|knee|shoulder|hip|ankle|wrist|hand|foot|neck|extremit(?:y|ies))\b",
    re.IGNORECASE,
)

FINDINGS_PATTERN = re.compile(r"FINDINGS?:?\s*(.+?)(?=\n\s*[A-Z]{2,}|\Z)", re.DOTALL | re.IGNORECASE)
IMPRESSION_PATTERN = re.compile(r"IMPRESSION:?\s*(.+?)(?=\n\s*[A-Z]{2,}|\Z)", re.DOTALL | re.IGNORECASE)

LATERALITY_PATTERN = re.compile(r"\b(left|right|bilateral)\b", re.IGNORECASE)
CONTRAST_PATTERN = re.compile(r"\b(with(?:out)?\s+contrast|contrast[\-\s]enhanced|non[\-\s]?contrast)\b", re.IGNORECASE)
ORDERING_PROVIDER_PATTERN = re.compile(r"(?:ordering|referring)\s+(?:physician|provider|doctor|MD):?\s*(.+)", re.IGNORECASE)
REPORT_DATE_PATTERN = re.compile(r"(?:date|exam\s+date|study\s+date):?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", re.IGNORECASE)


def extract_imaging_entities(text: str) -> list[dict]:
    """Extract structured entities from imaging report text.

    Returns list of dicts with keys: entity_type, entity_value, confidence, source_page.
    """
    entities: list[dict] = []

    modalities = MODALITY_PATTERN.findall(text)
    if modalities:
        entities.append({
            "entity_type": "modality",
            "entity_value": modalities[0].strip(),
            "confidence": 0.95,
            "source_page": None,
        })

    regions = BODY_REGION_PATTERN.findall(text)
    if regions:
        entities.append({
            "entity_type": "body_region",
            "entity_value": regions[0].strip().lower(),
            "confidence": 0.9,
            "source_page": None,
        })

    findings = FINDINGS_PATTERN.search(text)
    if findings:
        entities.append({
            "entity_type": "finding",
            "entity_value": findings.group(1).strip()[:500],
            "confidence": 0.85,
            "source_page": None,
        })

    impression = IMPRESSION_PATTERN.search(text)
    if impression:
        entities.append({
            "entity_type": "impression",
            "entity_value": impression.group(1).strip()[:500],
            "confidence": 0.85,
            "source_page": None,
        })

    laterality = LATERALITY_PATTERN.search(text)
    if laterality:
        entities.append({
            "entity_type": "laterality",
            "entity_value": laterality.group(1).lower(),
            "confidence": 0.9,
            "source_page": None,
        })

    contrast = CONTRAST_PATTERN.search(text)
    if contrast:
        entities.append({
            "entity_type": "contrast_used",
            "entity_value": contrast.group(1).strip().lower(),
            "confidence": 0.9,
            "source_page": None,
        })

    provider = ORDERING_PROVIDER_PATTERN.search(text)
    if provider:
        entities.append({
            "entity_type": "ordering_provider",
            "entity_value": provider.group(1).strip(),
            "confidence": 0.8,
            "source_page": None,
        })

    report_date = REPORT_DATE_PATTERN.search(text)
    if report_date:
        entities.append({
            "entity_type": "report_date",
            "entity_value": report_date.group(1).strip(),
            "confidence": 0.9,
            "source_page": None,
        })

    return entities
