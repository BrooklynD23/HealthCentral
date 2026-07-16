"""Rule-based document category classifier.

Classifies documents into: imaging, pathology, visit_notes, lab, unknown.
Uses keyword matching on first 2 pages of OCR text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

IMAGING_STRONG = re.compile(
    r"\b(MRI|CT\s*scan|X[\-\s]?ray|ultrasound|radiograph|radiology\s+report|fluoroscopy|mammograph|PET\s*scan)\b",
    re.IGNORECASE,
)
IMAGING_SECTION = re.compile(r"\b(FINDINGS|IMPRESSION|TECHNIQUE|COMPARISON)\b")

PATHOLOGY_STRONG = re.compile(
    r"\b(biopsy|specimen|histologic|cytology|surgical\s+pathology|pathology\s+report|gross\s+description|microscopic)\b",
    re.IGNORECASE,
)
PATHOLOGY_SECTION = re.compile(r"\b(DIAGNOSIS|MARGINS|SPECIAL\s+STAINS|IMMUNOHISTOCHEMISTRY)\b")

VISIT_STRONG = re.compile(
    r"\b(chief\s+complaint|progress\s+note|discharge\s+summary|discharge\s+instructions|consult\s+note|history\s+of\s+present\s+illness|after[\-\s]visit\s+summary|(?-i:AVS)|patient\s+instructions)\b",
    re.IGNORECASE,
)
VISIT_SECTION = re.compile(r"\b(ASSESSMENT|PLAN|VITAL\s+SIGNS|REVIEW\s+OF\s+SYSTEMS)\b")

LAB_STRONG = re.compile(
    r"\b(laboratory\s+results?|reference\s+range|CBC|BMP|CMP|lipid\s+panel|hemoglobin\s+A1c|mg/dL|mmol/L|mEq/L)\b",
    re.IGNORECASE,
)


@dataclass
class ClassificationResult:
    """Result of document classification."""
    category: str       # 'imaging', 'pathology', 'visit_notes', 'lab', 'unknown'
    confidence: float   # 0.0 to 1.0
    classified_by: str  # 'rule'


def _extract_first_two_pages(text: str) -> str:
    """Extract text from first 2 pages (split on form feed)."""
    pages = text.split("\f")
    return "\f".join(pages[:2])


def _score_category(text: str, strong_pattern: re.Pattern, section_pattern: re.Pattern | None = None) -> float:
    """Score a category based on keyword matches."""
    strong_matches = len(strong_pattern.findall(text))
    section_matches = len(section_pattern.findall(text)) if section_pattern else 0

    if strong_matches >= 2:
        return 1.0
    if strong_matches == 1 and section_matches >= 1:
        return 0.9
    if strong_matches == 1:
        return 0.8
    if section_matches >= 2:
        return 0.7
    return 0.0


def classify_document(text: str) -> ClassificationResult:
    """Classify document text into a category.

    Uses first 2 pages only. Returns highest-scoring category above 0.7 threshold.
    """
    first_pages = _extract_first_two_pages(text)

    scores = {
        "imaging": _score_category(first_pages, IMAGING_STRONG, IMAGING_SECTION),
        "pathology": _score_category(first_pages, PATHOLOGY_STRONG, PATHOLOGY_SECTION),
        "visit_notes": _score_category(first_pages, VISIT_STRONG, VISIT_SECTION),
        "lab": _score_category(first_pages, LAB_STRONG),
    }

    best_category = max(scores, key=scores.get)  # type: ignore
    best_score = scores[best_category]

    if best_score < 0.7:
        return ClassificationResult(category="unknown", confidence=0.0, classified_by="rule")

    return ClassificationResult(
        category=best_category,
        confidence=best_score,
        classified_by="rule",
    )
