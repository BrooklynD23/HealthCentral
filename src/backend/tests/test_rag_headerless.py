"""LCP-HEADERLESS (owner LCP-HL-SCOPE (a), LCP-HL-LABELS (a)): the legacy parser
counts section headers only at the start of a line, text outside a section is
REPORT FACTS (so it must carry [cite:N]), and context labels are not served.

HC-LCPH-001  headerless uncited text -> "Report facts section missing citations"
HC-LCPH-002  prose mentioning "uncertainties" mid-line is not cut
HC-LCPH-003  repr dict / curly keys / JSON string / JSON array stay whole (x4)
HC-LCPH-004  line-start headers still split; **UNCERTAINTY** is a header
"""

from __future__ import annotations

import pytest

from modules.rag import RAGModule
from tests.legacy_eval.harness import build_chunks

REPR_DICT = (
    "{'report_facts': [{'text': 'Glucose: 95 mg/dL [cite:1]', 'cites': [1]}], "
    "'uncertainties': ['Reference ranges can vary between laboratories.']}"
)
CURLY_KEYS = (
    "{“report_facts”: [{“text”: “Glucose: 95 mg/dL [cite:1]”}], "
    '“uncertainties”: ["Reference ranges can vary between laboratories."]}'
)
JSON_STRING = '"REPORT FACTS:\\n- Glucose: 95 mg/dL [cite:1]"'  # literal backslash-n
JSON_ARRAY = (
    '[{"text": "Glucose: 95 mg/dL [cite:1]", "cites": [1]}, '
    '{"text": "Reference ranges can vary.", "cites": []}]'
)


def _validate(text: str):
    return RAGModule(enable_verification=False).validate_response(text, build_chunks("glucose"))


def test_hc_lcph_001_headerless_uncited_text_is_report_facts_without_citation():
    result = _validate("Your LDL is 128 mg/dL, above the range.")
    assert "Report facts section missing citations" in result.validation_errors
    assert result.is_valid is False


def test_hc_lcph_002_mid_line_uncertainties_does_not_cut_the_text():
    text = "LDL Cholesterol is 128 mg/dL [cite:1]. There are uncertainties about lab ranges."
    result = _validate(text)
    assert "\n".join(s.content for s in result.segments) == text
    assert [s.segment_type for s in result.segments] == ["report_facts"]


@pytest.mark.parametrize(
    "text", [REPR_DICT, CURLY_KEYS, JSON_STRING, JSON_ARRAY], ids=["repr", "curly", "json-string", "array"]
)
def test_hc_lcph_003_structured_shapes_are_never_fragments(text):
    result = _validate(text)
    assert [(s.segment_type, s.content) for s in result.segments] == [("report_facts", text)]


def test_hc_lcph_004_line_start_headers_split_and_singular_uncertainty_counts():
    rag = RAGModule(enable_verification=False)
    parsed = rag._parse_response_segments(
        "REPORT FACTS:\n- X [cite:1]\n\nGENERAL INFO:\n- Y\n\nUNCERTAINTIES:\n- Z"
    )
    assert [(s.segment_type, s.content) for s in parsed] == [
        ("report_facts", "- X [cite:1]"),
        ("general_info", "- Y"),
        ("uncertainty", "- Z"),
    ]
    singular = rag._parse_response_segments("**UNCERTAINTY**\n- Z")
    assert [(s.segment_type, s.content) for s in singular] == [("uncertainty", "- Z")]
    # Conservative pin: a prose line that merely starts with the word is not a header.
    prose = "Uncertainty about lab ranges [cite:1]"
    parsed_prose = rag._parse_response_segments(prose)
    assert [(s.segment_type, s.content) for s in parsed_prose] == [("report_facts", prose)]

