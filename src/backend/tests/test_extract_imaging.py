"""Tests for imaging entity extractor."""

import pytest

from modules.extract_imaging import extract_imaging_entities


class TestExtractImagingEntities:
    def test_extracts_modality(self):
        text = "RADIOLOGY REPORT\nMRI of lumbar spine with contrast"
        entities = extract_imaging_entities(text)
        modalities = [e for e in entities if e["entity_type"] == "modality"]
        assert len(modalities) == 1
        assert modalities[0]["entity_value"] == "MRI"

    def test_extracts_body_region(self):
        text = "CT scan of the chest\nFINDINGS: Normal"
        entities = extract_imaging_entities(text)
        regions = [e for e in entities if e["entity_type"] == "body_region"]
        assert len(regions) == 1
        assert regions[0]["entity_value"] == "chest"

    def test_extracts_findings(self):
        text = "FINDINGS: No acute cardiopulmonary abnormality\nIMPRESSION: Normal"
        entities = extract_imaging_entities(text)
        findings = [e for e in entities if e["entity_type"] == "finding"]
        assert len(findings) == 1
        assert "cardiopulmonary" in findings[0]["entity_value"]

    def test_extracts_impression(self):
        text = "FINDINGS: Normal\nIMPRESSION: No acute abnormality identified"
        entities = extract_imaging_entities(text)
        impressions = [e for e in entities if e["entity_type"] == "impression"]
        assert len(impressions) == 1
        assert "acute abnormality" in impressions[0]["entity_value"]

    def test_extracts_laterality(self):
        text = "MRI of left knee\nFINDINGS: Meniscal tear"
        entities = extract_imaging_entities(text)
        lat = [e for e in entities if e["entity_type"] == "laterality"]
        assert len(lat) == 1
        assert lat[0]["entity_value"] == "left"

    def test_extracts_contrast(self):
        text = "CT scan with contrast\nFINDINGS: Normal"
        entities = extract_imaging_entities(text)
        contrast = [e for e in entities if e["entity_type"] == "contrast_used"]
        assert len(contrast) == 1

    def test_empty_text_returns_empty(self):
        entities = extract_imaging_entities("")
        assert entities == []
