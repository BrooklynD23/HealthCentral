"""LEGACY-CITE-PROMPT: constrained-decoding cite path for the legacy RAG answer.

HC-LCP-004  _cite_schema(n): enum 1..n, minItems 1, additionalProperties false at both levels
HC-LCP-005  a valid structured answer renders to text the unchanged parser/validator accept
HC-LCP-006  invalid / forged structured answers render to None
HC-LCP-007  prose (external runner, every existing mock) renders to None and passes through
"""
from __future__ import annotations

import asyncio
import json

from modules.rag import RAGModule, _cite_schema
from tests.legacy_eval.harness import FakeRunner, build_chunks


def _answer(**over) -> dict:
    base = {
        "report_facts": [{"text": "Glucose: 95 mg/dL (reference range 70-100 mg/dL)", "cites": [1]}],
        "general_info": [{"text": "Glucose is the primary source of energy for cells", "cites": [2]}],
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
    assert "GENERAL INFO:\n- Glucose is the primary source of energy for cells [cite:2]" in text
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
    out = asyncio.run(rag._generate_with_runner("prompt", FakeRunner(prose)))
    assert out == prose
