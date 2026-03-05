"""Tests for document import classification integration.

Tests that classify_document is correctly invoked during import.
"""

import pytest
from modules.document_classifier import classify_document, ClassificationResult


class TestClassificationIntegration:
    def test_imaging_report_classifies_correctly(self):
        """Full imaging report text should classify as imaging."""
        text = """RADIOLOGY REPORT

Patient: John Doe
Date: 03/04/2026
Ordering Provider: Dr. Smith

MRI of lumbar spine without contrast

TECHNIQUE: Multiplanar multisequence MRI of the lumbar spine.

FINDINGS:
Normal alignment. No fracture or subluxation.
Disc heights are maintained. No significant disc herniation.
The spinal canal is patent. No spinal stenosis.

IMPRESSION:
Normal MRI of the lumbar spine. No acute abnormality.
"""
        result = classify_document(text)
        assert result.category == "imaging"
        assert result.confidence >= 0.9

    def test_pathology_report_classifies_correctly(self):
        text = """SURGICAL PATHOLOGY REPORT

Specimen: Left breast, needle core biopsy
Site: Left breast, 2 o'clock

DIAGNOSIS: Invasive ductal carcinoma, grade 2
Nottingham grade: 2/3 (tubules 2, nuclei 2, mitoses 1)
MARGINS: N/A (core biopsy)

Signed by: Dr. Jane Pathologist
"""
        result = classify_document(text)
        assert result.category == "pathology"
        assert result.confidence >= 0.9
