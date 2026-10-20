"""LCP-HEADERLESS (owner LCP-HL-SCOPE (a), LCP-HL-LABELS (a)): the legacy parser
counts section headers only at the start of a line, text outside a section is
REPORT FACTS (so it must carry [cite:N]), and context labels are not served.

HC-LCPH-001  headerless uncited text -> "Report facts section missing citations"
HC-LCPH-002  prose mentioning "uncertainties" mid-line is not cut
HC-LCPH-003  repr dict / curly keys / JSON string / JSON array stay whole (x4)
HC-LCPH-004  line-start headers still split; **UNCERTAINTY** is a header
HC-LCPH-005  over HTTP: [USER_OBSERVATION:N] is not served, [cite:N] is
HC-LCPH-006  verifier receives raw labelled text
HC-LCPH-007  over HTTP: a prefixed unverified value is not served
HC-LCPH-008  ClaimExtractor splits sections like the parser
HC-LCPH-009  a stripped context label keeps the preceding newline
HC-LCPH-010  GENERAL INFORMATION stays a section header
"""

from __future__ import annotations

import pytest

from modules.claim_extractor import ClaimExtractor
from modules.rag import RAGModule, VerificationMetadata
from tests.legacy_eval.harness import CHAT_PATH, build_chunks, legacy_chat_client

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
    # A colon after a mid-line keyword must not cut either (fails if the ^ anchor goes).
    text2 = "LDL is 128 mg/dL [cite:1]. Some uncertainties: lab ranges vary."
    result2 = _validate(text2)
    assert [(s.segment_type, s.content) for s in result2.segments] == [("report_facts", text2)]


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
    bold = rag._parse_response_segments("**REPORT FACTS:**\n- X [cite:1]")
    assert [(s.segment_type, s.content) for s in bold] == [("report_facts", "- X [cite:1]")]
    # Conservative pin: a prose line that merely starts with the word is not a header.
    prose = "Uncertainty about lab ranges [cite:1]"
    parsed_prose = rag._parse_response_segments(prose)
    assert [(s.segment_type, s.content) for s in parsed_prose] == [("report_facts", prose)]


def test_hc_lcph_005_context_labels_are_not_served_over_http():
    answer = (
        "REPORT FACTS:\n- Glucose: 95 mg/dL (reference range 70-100 mg/dL) "
        "[USER_OBSERVATION:1] [cite:1]"
    )
    with legacy_chat_client(build_chunks("glucose"), answer) as (client, _append):
        resp = client.post(CHAT_PATH, json={"question": "What was my glucose?"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is True
    assert "[cite:1]" in body["full_response"]
    assert "[USER_OBSERVATION:" not in body["full_response"]


def test_hc_lcph_006_verifier_receives_raw_text_with_labels():
    """Labels are stripped after verification: the verifier must still see them."""
    rag = RAGModule(enable_verification=True)
    seen = {}

    def spy(response, chunks, segments):
        seen["response"] = response
        seen["segments"] = [s.content for s in segments]
        return VerificationMetadata(verification_enabled=True, faithfulness_score=1.0)

    answer = "REPORT FACTS:\n- Glucose: 95 mg/dL [USER_OBSERVATION:1] [cite:1]"
    rag._run_verification_pipeline = spy
    result = rag.validate_response(answer, build_chunks("glucose"))
    assert "[USER_OBSERVATION:1]" in seen["response"]
    assert any("[USER_OBSERVATION:1]" in c for c in seen["segments"])
    assert all("[USER_OBSERVATION:" not in s.content for s in result.segments)


PREFIXED_ANSWER = (
    "Your glucose is 300 mg/dL, far above the range [cite:1].\n\n"
    "REPORT FACTS:\n- Glucose: 95 mg/dL (reference range 70-100 mg/dL) [cite:1]"
)


def test_hc_lcph_007_prefixed_unverified_value_is_not_served_over_http():
    with legacy_chat_client(build_chunks("glucose"), PREFIXED_ANSWER) as (client, _append):
        resp = client.post(CHAT_PATH, json={"question": "What was my glucose?"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    assert "300 mg/dL" not in body["full_response"]
    assert all("300 mg/dL" not in s["content"] for s in body["segments"])


def test_hc_lcph_008_claim_extractor_splits_like_the_parser():
    ex = ClaimExtractor()
    claims = ex.extract_claims(PREFIXED_ANSWER).claims
    assert any(c.segment_type == "report_facts" and "300 mg/dL" in c.text for c in claims)

    headerless = ex.extract_claims("Your LDL is 128 mg/dL [cite:1].").claims
    assert headerless and all(c.segment_type == "report_facts" for c in headerless)

    text2 = "LDL is 128 mg/dL [cite:1]. Some uncertainties: lab ranges vary."
    assert ex._parse_sections(text2) == [("report_facts", text2)]

    # Same (type, content) as the parser on the HC-LCPH-004 inputs.
    rag = RAGModule(enable_verification=False)
    for text in (
        "REPORT FACTS:\n- X [cite:1]\n\nGENERAL INFO:\n- Y\n\nUNCERTAINTIES:\n- Z",
        "**UNCERTAINTY**\n- Z",
        "**REPORT FACTS:**\n- X [cite:1]",
        "Uncertainty about lab ranges [cite:1]",
        "REPORT FACTS:\n- A\nUNCERTAINTIES:\n- B\nREPORT FACTS:\n- C",
        PREFIXED_ANSWER,
        "   ",
    ):
        assert ex._parse_sections(text) == [
            (s.segment_type, s.content) for s in rag._parse_response_segments(text)
        ]


def test_hc_lcph_009_stripped_context_label_keeps_the_preceding_newline():
    # Fails if _CONTEXT_LABEL_RE goes back to \s?, which would eat the newline.
    kept = _validate("REPORT FACTS:\n- X [cite:1]\n[YOUR_RESULTS:1] Glucose 95 [cite:1]")
    content = kept.segments[0].content
    assert "- X [cite:1]\n" in content
    assert "[YOUR_RESULTS:" not in content
    assert content.endswith("Glucose 95 [cite:1]")


GENERAL_INFORMATION_ANSWER = (
    "REPORT FACTS:\n- Glucose: 95 mg/dL (reference range 70-100 mg/dL) [cite:1]\n\n"
    "GENERAL INFORMATION:\nGlucose is a sugar used for energy."
)


def test_hc_lcph_010_general_information_header_still_splits_over_http():
    with legacy_chat_client(build_chunks("glucose"), GENERAL_INFORMATION_ANSWER) as (client, _append):
        resp = client.post(CHAT_PATH, json={"question": "What was my glucose?"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    assert "GENERAL INFORMATION" not in body["full_response"]
    assert ClaimExtractor()._parse_sections(GENERAL_INFORMATION_ANSWER)[1][0] == "general_info"
