"""Tests for pathology entity extractor."""

import pytest

from modules.extract_pathology import extract_pathology_entities


class TestExtractPathologyEntities:
    def test_extracts_specimen_type(self):
        text = "SURGICAL PATHOLOGY\nSPECIMEN: Left breast biopsy\nDIAGNOSIS: Benign"
        entities = extract_pathology_entities(text)
        types = [e for e in entities if e["entity_type"] == "specimen_type"]
        assert len(types) == 1
        assert types[0]["entity_value"] == "biopsy"

    def test_extracts_diagnosis(self):
        text = "DIAGNOSIS: Invasive ductal carcinoma, grade 2\nMARGINS: Clear"
        entities = extract_pathology_entities(text)
        dx = [e for e in entities if e["entity_type"] == "diagnosis"]
        assert len(dx) == 1
        assert "ductal carcinoma" in dx[0]["entity_value"]

    def test_extracts_margins(self):
        text = "DIAGNOSIS: Carcinoma\nMARGINS: Negative for tumor, closest margin 2mm"
        entities = extract_pathology_entities(text)
        margins = [e for e in entities if e["entity_type"] == "margins"]
        assert len(margins) == 1
        assert "Negative" in margins[0]["entity_value"]

    def test_extracts_stage(self):
        text = "DIAGNOSIS: Adenocarcinoma\nStage: pT2N0M0"
        entities = extract_pathology_entities(text)
        stage = [e for e in entities if e["entity_type"] == "stage"]
        assert len(stage) == 1
        assert "pT2N0M0" in stage[0]["entity_value"]

    def test_empty_text_returns_empty(self):
        entities = extract_pathology_entities("")
        assert entities == []
