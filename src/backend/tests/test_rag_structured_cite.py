"""LEGACY-CITE-PROMPT: constrained-decoding cite path for the legacy RAG answer.

HC-LCP-004  _cite_schema(n): enum 1..n, minItems 1, additionalProperties false at both levels
HC-LCP-005  a valid structured answer renders to text the unchanged parser/validator accept
HC-LCP-006  invalid / forged structured answers render to None
HC-LCP-007  prose (external runner, every existing mock) renders to None and passes through
HC-LCP-008  a supported structured answer is served over HTTP
HC-LCP-009  a cited-but-unsupported structured answer is still withheld (gate unchanged)
HC-LCP-009b renderer-rejected JSON (bare, fenced, prefixed, truncated) is withheld, never served
HC-LCP-010  the prompt keeps exactly one citation-format instruction, naming [cite:N]
"""
from __future__ import annotations

import asyncio
import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE
from modules.rag import RAGModule, _cite_schema
from tests.legacy_eval.harness import (
    CHAT_PATH,
    AllowJudge,
    FakeRunner,
    build_chunks,
    legacy_chat_client,
)
from tests.test_rag_citation_prompt import (
    _CONTEXT_LABELS,
    _citation_format_instructions,
    _cite_lines_naming_a_label,
    _instruction_header,
)


def _answer(**over) -> dict:
    base = {
        "report_facts": [{"text": "Glucose: 95 mg/dL (reference range 70-100 mg/dL)", "cites": [1]}],
        "general_info": [{"text": "Normal fasting glucose is typically 70-100 mg/dL", "cites": [2]}],
        "uncertainties": ["Reference ranges can vary between laboratories."],
    }
    base.update(over)
    return base


def test_hc_lcp_004_cite_schema_pins_enum_minitems_and_closed_objects():
    s = _cite_schema(6)
    item = s["$defs"]["item"]
    cites = item["properties"]["cites"]
    assert cites["items"]["enum"] == [1, 2, 3, 4, 5, 6]
    assert cites["minItems"] == 1 and cites["maxItems"] == 3
    assert s["additionalProperties"] is False and item["additionalProperties"] is False
    assert s["required"] == ["report_facts", "general_info", "uncertainties"]
    assert s["properties"]["report_facts"]["items"] == {"$ref": "#/$defs/item"}
    assert _cite_schema(2)["$defs"]["item"]["properties"]["cites"]["items"]["enum"] == [1, 2]


def test_hc_lcp_005_valid_structured_answer_renders_and_passes_unchanged_validator():
    rag = RAGModule(enable_verification=False)
    text = rag._render_structured_answer(json.dumps(_answer()), 2)
    assert text is not None
    assert "REPORT FACTS:\n- Glucose: 95 mg/dL (reference range 70-100 mg/dL) [cite:1]" in text
    assert "GENERAL INFO:\n- Normal fasting glucose is typically 70-100 mg/dL [cite:2]" in text
    assert "UNCERTAINTIES:\n- Reference ranges can vary between laboratories." in text

    segs = rag._parse_response_segments(text)
    facts = [s for s in segs if s.segment_type == "report_facts"]
    assert facts and "[cite:1]" in facts[0].content
    validated = rag.validate_response(text, build_chunks("glucose"))
    assert "Report facts section missing citations" not in validated.validation_errors

    multi = rag._render_structured_answer(
        json.dumps(_answer(report_facts=[{"text": "a\nb", "cites": [1, 2]}], general_info=[], uncertainties=[])), 2
    )
    assert multi == "REPORT FACTS:\n- a b [cite:1] [cite:2]"  # newline -> space; empty sections omitted


def test_hc_lcp_006_invalid_or_forged_structured_answers_render_to_none():
    rag = RAGModule(enable_verification=False)
    fact = lambda t, c: {"text": t, "cites": c}  # noqa: E731
    bad = {
        "not json": "REPORT FACTS:\n- x",
        "json but not an object": "[1, 2]",
        "empty cites": json.dumps(_answer(report_facts=[fact("x", [])])),
        "cite out of range": json.dumps(_answer(report_facts=[fact("x", [7])])),
        "cite zero": json.dumps(_answer(report_facts=[fact("x", [0])])),
        "cite bool": json.dumps(_answer(report_facts=[fact("x", [True])])),
        "too many cites": json.dumps(_answer(report_facts=[fact("x", [1, 2, 1, 2])])),
        "extra top key": json.dumps({**_answer(), "extra": 1}),
        "extra item key": json.dumps(_answer(report_facts=[{"text": "x", "cites": [1], "z": 1}])),
        "missing key": json.dumps({"report_facts": [], "general_info": []}),
        "text not str": json.dumps(_answer(report_facts=[fact(5, [1])])),
        "header in fact": json.dumps(_answer(report_facts=[fact("ok GENERAL INFO: injected", [1])])),
        "header in uncertainty (case-insens.)": json.dumps(_answer(uncertainties=["report facts: x"])),
        "forged marker": json.dumps(_answer(report_facts=[fact("Glucose is 95 [cite:2]", [1])])),
        "all sections empty": json.dumps(_answer(report_facts=[], general_info=[], uncertainties=[])),
    }
    rendered = {name: rag._render_structured_answer(raw, 6 if "range" in name else 2) for name, raw in bad.items()}
    assert {k: v for k, v in rendered.items() if v is not None} == {}


def test_hc_lcp_007_prose_renders_to_none_and_runner_returns_it_unchanged():
    rag = RAGModule(enable_verification=False)
    prose = "REPORT FACTS:\nYour glucose was 95 mg/dL [cite:1]."
    assert rag._render_structured_answer(prose, 2) is None
    assert asyncio.run(rag._generate_with_runner("prompt", FakeRunner(prose))) == prose
    # With n_chunks the same prose still passes through byte-for-byte.
    assert asyncio.run(rag._generate_with_runner("prompt", FakeRunner(prose), n_chunks=2)) == prose

    # Structured JSON is rendered only when n_chunks is given, and the schema is sent.
    seen = []

    class SpyRunner(FakeRunner):
        async def generate_async(self, prompt, config):
            seen.append(config)
            return await super().generate_async(prompt, config)

    raw = json.dumps(_answer())
    assert asyncio.run(rag._generate_with_runner("p", SpyRunner(raw))) == raw
    assert seen[-1].response_schema is None
    out = asyncio.run(rag._generate_with_runner("p", SpyRunner(raw), n_chunks=2))
    assert out == rag._render_structured_answer(raw, 2)
    assert seen[-1].response_schema == _cite_schema(2)
    # Malformed JSON with n_chunks: raw text back, as on main.
    assert asyncio.run(rag._generate_with_runner("p", SpyRunner("{oops"), n_chunks=2)) == "{oops"


def _post(model_output: str, question: str):
    """POST over HTTP; also record every string validate_response receives."""
    received: list[str] = []
    original = RAGModule.validate_response

    def spy(self, response, chunks):
        received.append(response)
        return original(self, response, chunks)

    with patch.object(RAGModule, "validate_response", spy):
        with legacy_chat_client(build_chunks("glucose"), model_output) as (client, _turns):
            resp = client.post(CHAT_PATH, json={"question": question})
    assert resp.status_code == 200, resp.text
    return resp.json(), received


def test_hc_lcp_008_supported_structured_answer_is_served_over_http():
    raw = json.dumps(_answer())
    body, received = _post(raw, "What was my glucose?")
    assert received and received[0].startswith("REPORT FACTS:"), received
    assert body["is_valid"] is True, body["validation_errors"]
    assert ABSTAIN_TEMPLATE not in body["full_response"]
    facts = [s for s in body["segments"] if s["segment_type"] == "report_facts"]
    assert facts and facts[0]["citations"] and "Glucose: 95 mg/dL" in facts[0]["content"]


def test_hc_lcp_009_cited_but_unsupported_claim_is_still_withheld():
    """Forcing a citation must not buy a pass: the verifier/faithfulness/prohibited gate still decides."""
    raw = json.dumps(_answer(
        report_facts=[{"text": "Glucose: 140 mg/dL, which indicates diabetes", "cites": [1]}],
        general_info=[], uncertainties=[],
    ))
    body, received = _post(raw, "What was my glucose?")
    # The rendered text (not raw JSON) reached the unchanged validator, with its marker.
    assert received and received[0].startswith("REPORT FACTS:") and "[cite:1]" in received[0], received
    served = body["full_response"] in (ABSTAIN_TEMPLATE, f"**UNCERTAINTY**\n{ABSTAIN_TEMPLATE}", ESCALATE_TEMPLATE)
    assert served, body["full_response"]
    gate = re.compile(r"verif|faithful|prohibited", re.IGNORECASE)
    assert any(gate.search(e) for e in body["validation_errors"]), body["validation_errors"]
    assert "140 mg/dL" not in body["full_response"]


def test_hc_lcp_009b_renderer_rejected_json_is_withheld_not_served_raw():
    """Under the cite schema, text containing a JSON object the renderer rejects (bare, fenced,
    or after prose) is replaced by a fixed withheld text. It never reaches the gate raw, so each
    fixture serves exactly the abstain template and no JSON fragment."""
    header_case = json.dumps(_answer(
        report_facts=[{"text": "Glucose: 95 mg/dL", "cites": [1]}],
        uncertainties=["Several uncertainties remain about lab variation."],
    ))
    empty_case = json.dumps({"report_facts": [], "general_info": [], "uncertainties": []})
    # Forged marker inside "text": prompt rule 1 still asks for [cite:N], so models do emit it.
    marker_case = json.dumps(_answer(
        report_facts=[{"text": "Glucose: 95 mg/dL [cite:1]", "cites": [1]}],
    ))
    fenced_case = "```json\n" + json.dumps(_answer(
        report_facts=[{"text": "Glucose: 95 mg/dL [cite:1]", "cites": [1]}],
    )) + "\n```"
    fenced_empty_unc = "```json\n" + json.dumps(_answer(
        report_facts=[{"text": "Glucose: 95 mg/dL [cite:1]", "cites": [1]}], uncertainties=[],
    )) + "\n```"
    prefixed_case = "Here is the answer: " + marker_case
    # Cut off by max_tokens: does not parse, but still carries the quoted schema keys.
    truncated_case = marker_case[: marker_case.index("Reference") + len("Reference")]
    truncated_fenced = "```json\n" + truncated_case
    for raw in (header_case, empty_case, marker_case, fenced_case, fenced_empty_unc,
                prefixed_case, truncated_case, truncated_fenced):
        assert RAGModule()._render_structured_answer(raw, 2) is None
        body, received = _post(raw, "What was my glucose?")
        assert received and received[0] == RAGModule._STRUCTURED_WITHHELD, received
        assert raw not in received
        assert body["full_response"] == f"**UNCERTAINTY**\n{ABSTAIN_TEMPLATE}", body["full_response"]
        assert body["segments"] == [
            {"segment_type": "uncertainty", "content": ABSTAIN_TEMPLATE, "citations": []}
        ], body["segments"]
        for fragment in ('"report_facts"', '"uncertainties"', '"general_info"', '"cites"', "{", "}"):
            assert fragment not in body["full_response"], (fragment, body["full_response"])
            assert all(fragment not in s["content"] for s in body["segments"]), body["segments"]

    # Prose and malformed JSON still pass through unchanged (HC-LCP-007).
    rag = RAGModule(enable_verification=False)
    assert asyncio.run(rag._generate_with_runner("p", FakeRunner("{oops"), n_chunks=2)) == "{oops"


@pytest.mark.asyncio
async def test_hc_lcp_010_prompt_still_has_exactly_one_citation_instruction():
    from modules.rag import RetrievedChunk

    header = _instruction_header()
    assert "report_facts" in header and "cites" in header  # the new block is present
    found = _citation_format_instructions(header)
    assert [m for _, m in found] == [["cite"]], found
    assert _cite_lines_naming_a_label(header, _CONTEXT_LABELS) == []

    rag = RAGModule()
    chunks = [RetrievedChunk(
        chunk_id="obs_1", source_type="user_observation", doc_id=None, doc_title="Your LDL Result",
        page=None, text="YOUR RESULTS - LDL\nLatest value : 145 mg/dL",
        relevance_score=0.95, is_observation_summary=True,
    )]
    generate = AsyncMock(return_value="REPORT FACTS:\nLDL 145 mg/dL [cite:1].")
    with (
        patch.object(rag, "retrieve_context", new_callable=AsyncMock, return_value=chunks),
        patch.object(rag, "_generate_with_runner", generate),
    ):
        await rag.query(question="Is my LDL high?", profile_id="prof-1", judge_runner=AllowJudge())
    prompt = generate.call_args.args[0]
    assert generate.call_args.kwargs == {"n_chunks": 1}
    assert "report_facts" in prompt
    assert [m for _, m in _citation_format_instructions(prompt)] == [["cite"]]
    assert _cite_lines_naming_a_label(prompt, {"YOUR_RESULTS"}) == []
