"""Tests for rule-based document category classifier."""

import pytest

from modules.document_classifier import classify_document, ClassificationResult


class TestClassifyDocument:
    def test_imaging_strong_keywords(self):
        text = "RADIOLOGY REPORT\nMRI of lumbar spine\nFINDINGS: No acute abnormality\nIMPRESSION: Normal"
        result = classify_document(text)
        assert result.category == "imaging"
        assert result.confidence >= 0.9

    def test_pathology_strong_keywords(self):
        text = "PATHOLOGY REPORT\nSPECIMEN: Left breast biopsy\nDIAGNOSIS: Invasive ductal carcinoma"
        result = classify_document(text)
        assert result.category == "pathology"
        assert result.confidence >= 0.9

    def test_visit_notes_strong_keywords(self):
        text = "PROGRESS NOTE\nChief Complaint: Follow-up hypertension\nAssessment: BP well controlled\nPlan: Continue lisinopril"
        result = classify_document(text)
        assert result.category == "visit_notes"
        assert result.confidence >= 0.9

    def test_unknown_when_no_keywords(self):
        text = "This is a random document with no medical keywords specific to any category."
        result = classify_document(text)
        assert result.category == "unknown"

    def test_lab_report_returns_lab(self):
        text = "LABORATORY RESULTS\nGlucose: 95 mg/dL\nHemoglobin A1c: 5.7%\nReference Range: 4.0-5.6%"
        result = classify_document(text)
        assert result.category == "lab"

    def test_only_first_two_pages_used(self):
        """Classification should only use first 2 pages of text."""
        page1 = "Some unrelated text"
        page2 = "More unrelated text"
        page3 = "RADIOLOGY REPORT MRI FINDINGS IMPRESSION"
        text = f"{page1}\f{page2}\f{page3}"
        result = classify_document(text)
        assert result.category == "unknown"
