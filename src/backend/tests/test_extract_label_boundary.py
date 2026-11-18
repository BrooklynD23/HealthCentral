"""EXTRACT-LABEL-BOUNDARY: imaging and visit-note labels must be whole words.

Merge-only owner gate EXTRACT-LB-DIFF: extracted values change (see the plan).
"""

import pytest

from modules import extract_visit_notes
from modules.extract_imaging import extract_imaging_entities
from modules.extract_visit_notes import extract_visit_note_entities


def _vis(text, entity_type):
    return [e["entity_value"] for e in extract_visit_note_entities(text) if e["entity_type"] == entity_type]


def _img(text, entity_type):
    return [e["entity_value"] for e in extract_imaging_entities(text) if e["entity_type"] == entity_type]


def test_hc_elb_001_plan_inside_explanation_is_not_a_plan_prefix():
    """The mid-word match 'ation of plan: rest' is gone.

    The whole word 'plan:' after 'of' is a boundary-clean label, like HC-ELB-005's
    'DISCHARGE PLAN: home', so its body 'rest' is still read as the plan.
    """
    text = "Explanation of plan: rest\nVITALS: ok"
    assert _vis(text, "plan") == ["rest"]
    assert _vis(text, "vitals") == ["ok"]


@pytest.mark.parametrize(
    "text,entity_type,kind",
    [
        ("reassessment: x", "assessment", "vis"),
        ("misdiagnosis: none", "diagnoses", "vis"),
        ("account: settled", "chief_complaint", "vis"),
        ("reordering physician: smith", "ordering_provider", "img"),
        ("forewarning signs: chest pain", "warning_sign", "vis"),
        ("update: 12/05/2024", "report_date", "img"),
        ("candidate: 12/05/2024", "report_date", "img"),
    ],
    ids=["reassessment", "misdiagnosis", "account", "reordering-ordering-provider",
         "forewarning", "update-date", "candidate-date"],
)
def test_hc_elb_002_label_inside_a_word_gives_no_entity(text, entity_type, kind):
    got = _vis(text, entity_type) if kind == "vis" else _img(text, entity_type)
    assert got == []


def test_hc_elb_002_protests_ordered_is_not_a_tests_ordered_label():
    """Label pattern directly: the verb pattern may still read 'ordered: none'."""
    assert extract_visit_notes.TESTS_ORDERED_LABEL_PATTERN.search("protests ordered: none") is None
    assert extract_visit_notes.TESTS_ORDERED_LABEL_PATTERN.search("tests ordered: CBC") is not None


@pytest.mark.parametrize(
    "text,entity_type,kind",
    [
        ("new findings list", "finding", "img"),
        ("the care plan discussed", "plan", "vis"),
    ],
    ids=["findings-noun", "plan-noun"],
)
def test_hc_elb_003_colonless_noun_use_gives_no_entity(text, entity_type, kind):
    got = _vis(text, entity_type) if kind == "vis" else _img(text, entity_type)
    assert got == []


def test_hc_elb_004_labelled_sections_still_extract():
    img = "FINDINGS: No acute fracture.\nIMPRESSION: Normal study."
    assert _img(img, "finding") == ["No acute fracture."]
    assert _img(img, "impression") == ["Normal study."]
    vis = "ASSESSMENT: Type 2 diabetes, stable.\nPLAN: Continue metformin.\nVITAL SIGNS: BP 120/80, HR 72"
    assert _vis(vis, "assessment") == ["Type 2 diabetes, stable."]
    assert _vis(vis, "plan") == ["Continue metformin."]
    assert _vis(vis, "vitals") == ["BP 120/80, HR 72"]


def test_hc_elb_004_single_line_labels_still_extract():
    assert _vis("Chief complaint: cough", "chief_complaint") == ["cough"]
    assert _vis("Provider: Dr Smith", "provider") == ["Dr Smith"]
    assert _vis("Visit date 12/05/2024", "visit_date") == ["12/05/2024"]
    assert _img("Ordering physician: Dr Lee", "ordering_provider") == ["Dr Lee"]
    assert _img("Exam date: 12/05/2024", "report_date") == ["12/05/2024"]


def test_hc_elb_005_label_after_a_word_still_extracts():
    """\\b, not a line-start anchor: a boundary-clean label mid-sentence works."""
    assert _vis("DISCHARGE PLAN: home", "plan") == ["home"]


def test_hc_elb_006_assessment_and_plan_header_gives_the_body():
    assert _vis("ASSESSMENT AND PLAN: stable", "assessment") == ["stable"]


def test_hc_elb_007_colonless_header_gives_no_plan():
    """Named cost reviewed at EXTRACT-LB-DIFF: a colonless section header stops matching."""
    assert _vis("PLAN\nIncrease lisinopril", "plan") == []


@pytest.mark.parametrize(
    "text,entity_type,kind",
    [
        ("providers: smith", "provider", "vis"),
        ("attendings: dr x", "provider", "vis"),
        ("ordering MDs: x", "ordering_provider", "img"),
    ],
    ids=["providers", "attendings", "MDs"],
)
def test_hc_elb_008_label_followed_by_a_letter_gives_no_entity(text, entity_type, kind):
    got = _vis(text, entity_type) if kind == "vis" else _img(text, entity_type)
    assert got == []
