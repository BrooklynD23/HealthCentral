"""Tests for category-aware RAG retrieval.

Currently validates that the classifier returns valid categories.
Category-based RAG filtering is deferred to Phase 3 (see TODO in rag.py).
"""

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.document_classifier import classify_document


class TestRagCategoryFilter:
    def test_classifier_returns_valid_categories(self) -> None:
        """Classifier only returns known categories."""
        valid_categories = {"imaging", "pathology", "visit_notes", "lab", "unknown"}

        texts = [
            "RADIOLOGY REPORT\nMRI brain\nFINDINGS: Normal\nIMPRESSION: Normal",
            "PATHOLOGY REPORT\nSPECIMEN: Biopsy\nDIAGNOSIS: Benign",
            "PROGRESS NOTE\nChief Complaint: Headache\nASSESSMENT: Migraine",
            "LABORATORY RESULTS\nGlucose: 95 mg/dL",
            "Random unrelated text with no keywords",
        ]

        for text in texts:
            result = classify_document(text)
            assert result.category in valid_categories
            assert 0.0 <= result.confidence <= 1.0
            assert result.classified_by == "rule"

    def test_unknown_category_has_zero_confidence(self) -> None:
        result = classify_document("This text has no medical keywords whatsoever.")
        assert result.category == "unknown"
        assert result.confidence == 0.0
