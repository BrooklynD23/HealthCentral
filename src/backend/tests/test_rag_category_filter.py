"""Tests for category-aware RAG retrieval.

Validates that category filtering works in document retrieval.
"""

import pytest
from modules.document_classifier import classify_document


class TestRagCategoryFilter:
    def test_classifier_returns_valid_categories(self):
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
