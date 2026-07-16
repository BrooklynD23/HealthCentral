"""Tests for visit notes entity extractor."""

import pytest

from modules.extract_visit_notes import extract_visit_note_entities


class TestExtractVisitNoteEntities:
    def test_extracts_visit_type(self):
        text = "PROGRESS NOTE\nChief Complaint: Headache"
        entities = extract_visit_note_entities(text)
        types = [e for e in entities if e["entity_type"] == "visit_type"]
        assert len(types) == 1
        # HC-M13: visit_type values are canonical subtypes.
        assert types[0]["entity_value"] == "progress"

    def test_extracts_chief_complaint(self):
        text = "Chief Complaint: Follow-up hypertension\nASSESSMENT: BP controlled"
        entities = extract_visit_note_entities(text)
        cc = [e for e in entities if e["entity_type"] == "chief_complaint"]
        assert len(cc) == 1
        assert "hypertension" in cc[0]["entity_value"]

    def test_extracts_assessment(self):
        text = "ASSESSMENT: Type 2 diabetes well controlled. A1c 6.5%\nPLAN: Continue metformin"
        entities = extract_visit_note_entities(text)
        assess = [e for e in entities if e["entity_type"] == "assessment"]
        assert len(assess) == 1
        assert "diabetes" in assess[0]["entity_value"]

    def test_extracts_plan(self):
        text = "ASSESSMENT: HTN\nPLAN: Increase lisinopril to 20mg daily. Follow up in 4 weeks."
        entities = extract_visit_note_entities(text)
        plan = [e for e in entities if e["entity_type"] == "plan"]
        assert len(plan) == 1
        assert "lisinopril" in plan[0]["entity_value"]

    def test_empty_text_returns_empty(self):
        entities = extract_visit_note_entities("")
        assert entities == []
