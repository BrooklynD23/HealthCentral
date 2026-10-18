"""RSI-T2-EVAL: legacy citation eval harness (scripts/legacy_cite_eval.py).

HC-T2E-001  classify: one body per kind, order rule pinned (timeout beats citations)
HC-T2E-002  questions_v1.json: 20 questions, 6 chunks, pinned sha256
HC-T2E-003  run_questions drives the REAL route + validate_response: a cited fake
            answer counts answered_cited, the same answer uncited counts abstained
HC-T2E-004  summarise: schema, every kind counted, rates = count / n
HC-T2E-005  render_markdown: one row per model, baseline deltas, missing -> "—"
HC-T2E-006  main refuses under pytest (exit 3) and never touches get_model_runner
HC-T2E-007  sealed output holds no question, response or chunk text
HC-T2E-008  cite-value diagnostic: a number absent from the cited chunk mismatches

Every model here is a fake (tests/legacy_eval/harness.py::FakeRunner). Fixture
text is synthetic; it holds no patient data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE
from scripts import legacy_cite_eval as t2e
from tests.legacy_eval.harness import FakeRunner

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "legacy_cite_eval" / "questions_v1.json"
# A fixture edit must change this line in the same diff (never a silent drift from MM-1).
FIXTURE_SHA256 = "ecb906035db228f1af9fc2d5698fe9bf9cf0e34bbd88296b5719a8a41c0d990e"

CITED = (
    "REPORT FACTS:\nGlucose: 95 mg/dL (reference range 70-100 mg/dL) [cite:1].\n\n"
    "UNCERTAINTIES:\nReference ranges can vary between laboratories."
)
UNCITED = CITED.replace(" [cite:1]", "")
TIMEOUT_TEXT = "UNCERTAINTIES:\nI was unable to fully process your question within the time limit."


def _seg(segment_type: str, content: str, cited: bool, doc_id: str = "doc-1") -> dict:
    citations = [{"source_type": "user_observation", "doc_id": doc_id, "text_snippet": "x"}] if cited else []
    return {"segment_type": segment_type, "content": content, "citations": citations}


def _body(full_response: str, segments: list[dict] | None = None) -> dict:
    return {"full_response": full_response, "segments": segments or [], "validation_errors": []}


def test_hc_t2e_001_classify_each_kind_and_order():
    no_model = _body("Note: This response is based on the knowledge base only. Glucose is a sugar.")
    timeout = _body(TIMEOUT_TEXT, [_seg("report_facts", "Glucose: 95 [cite:1]", cited=True)])
    escalated = _body(ESCALATE_TEMPLATE)
    abstained = _body("**UNCERTAINTY**\n" + ABSTAIN_TEMPLATE)
    cited = _body("**REPORT FACTS**\nGlucose: 95 mg/dL", [_seg("report_facts", "Glucose: 95 mg/dL", cited=True)])
    uncited = _body("**GENERAL INFO**\nGlucose is a sugar.", [_seg("general_info", "Glucose is a sugar.", cited=False)])

    assert t2e.classify(no_model) == "no_model"
    assert t2e.classify(timeout) == "timeout"  # order rule: timeout text wins over citations
    assert t2e.classify(escalated) == "escalated"
    assert t2e.classify(abstained) == "abstained"
    assert t2e.classify(cited) == "answered_cited"
    assert t2e.classify(uncited) == "answered_uncited"
    # On this branch G-B5 maps the runner's timeout text to the abstain template, so the
    # text rule alone cannot see a timeout; the recorded finish_reason must.
    assert t2e.classify(abstained, finish_reason="timeout") == "timeout"
    # A non-200 response is a run failure, never an "uncited answer".
    assert t2e.classify({"detail": "Error processing chat request"}, status_code=500) == "error"


def test_hc_t2e_002_fixture_shape_and_pinned_sha():
    doc = t2e.load_questions(FIXTURE)
    assert doc["version"] == 1
    assert len(doc["questions"]) == 20
    assert len(doc["chunks"]) == 6
    assert doc["questions"][0] == "What was my latest glucose?"
    assert doc["chunks"][0]["text"].startswith("Glucose: 95 mg/dL")
    assert t2e.fixture_sha256(FIXTURE) == FIXTURE_SHA256


def test_hc_t2e_003_metric_driven_by_real_validation():
    doc = t2e.load_questions(FIXTURE)
    chunks = t2e.build_chunks(doc)

    cited = t2e.summarise(t2e.run_questions(doc["questions"], chunks, runner_patch=FakeRunner(CITED)), "fake")
    assert cited["answered_cited"] == 20
    assert cited["abstained"] == 0

    uncited = t2e.summarise(t2e.run_questions(doc["questions"], chunks, runner_patch=FakeRunner(UNCITED)), "fake")
    assert uncited["abstained"] == 20
    assert uncited["answered_cited"] == 0
    assert uncited["validation_errors"]["Report facts section missing citations"] == 20

    timed_out = t2e.summarise(
        t2e.run_questions(doc["questions"][:2], chunks, runner_patch=FakeRunner("", "timeout")), "fake"
    )
    assert timed_out["timeout"] == 2
    assert timed_out["abstained"] == 0


def test_hc_t2e_003b_real_runner_path_refused_under_pytest():
    with pytest.raises(RuntimeError, match="inside pytest"):
        t2e.run_questions(["What was my latest glucose?"], [], runner_patch=None)


def test_hc_t2e_004_summarise_schema_and_rates():
    per_question = [
        {"kind": "abstained", "validation_errors": ["Report facts section missing citations"], "latency_ms": 10.0},
        {"kind": "abstained", "validation_errors": ["Report facts section missing citations"], "latency_ms": 20.0},
        {"kind": "answered_cited", "validation_errors": [], "latency_ms": 30.0, "cite_value_mismatch": 0},
        {"kind": "escalated", "validation_errors": [], "latency_ms": 40.0},
    ]
    s = t2e.summarise(per_question, "m1")
    for key in ("schema_version", "model", "n", "abstain_rate", "cited_answer_rate", "validation_errors",
                "latency_ms_p50", "latency_ms_p95", "cite_value_mismatch", *t2e.KINDS):
        assert key in s, key
    assert s["model"] == "m1"
    assert s["n"] == 4
    assert s["abstained"] == 2 and s["answered_cited"] == 1 and s["escalated"] == 1
    assert s["timeout"] == 0 and s["no_model"] == 0 and s["answered_uncited"] == 0 and s["error"] == 0
    assert s["abstain_rate"] == pytest.approx(2 / 4)
    assert s["cited_answer_rate"] == pytest.approx(1 / 4)
    assert s["validation_errors"] == {"Report facts section missing citations": 2}
    assert s["latency_ms_p50"] == pytest.approx(25.0)
    assert 30.0 < s["latency_ms_p95"] <= 40.0


def _summary(model: str, abstained: int, cited: int, n: int = 20) -> dict:
    s = t2e.summarise(
        [{"kind": "abstained", "validation_errors": [], "latency_ms": 1.0}] * abstained
        + [{"kind": "answered_cited", "validation_errors": [], "latency_ms": 1.0, "cite_value_mismatch": 0}] * cited
        + [{"kind": "answered_uncited", "validation_errors": [], "latency_ms": 1.0}] * (n - abstained - cited),
        model,
    )
    return s


def test_hc_t2e_005_render_markdown_with_baseline():
    report = {"models": [_summary("gemma4:e4b", 18, 2), _summary("qwen3:8b", 10, 8)]}
    md = t2e.render_markdown(report)
    header = md.splitlines()[0]
    for col in ("model", "abstained", "cited", "uncited", "escalated", "timeout", "no-model",
                "abstain rate", "cited-answer rate", "cite-value mismatches"):
        assert col in header, col
    assert "Δ abstain" not in header
    rows = [line for line in md.splitlines() if line.startswith("| gemma4") or line.startswith("| qwen3")]
    assert len(rows) == 2

    baseline = {"models": [_summary("gemma4:e4b", 20, 0)]}
    md2 = t2e.render_markdown(report, baseline=baseline)
    assert "Δ abstain" in md2.splitlines()[0] and "Δ cited" in md2.splitlines()[0]
    gemma = next(line for line in md2.splitlines() if line.startswith("| gemma4"))
    qwen = next(line for line in md2.splitlines() if line.startswith("| qwen3"))
    assert gemma.rstrip().endswith("| -2 | +2 |")
    assert qwen.rstrip().endswith("| — | — |")  # missing from baseline: never 0


def test_hc_t2e_006_main_refuses_under_pytest(monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_hc_t2e_006")
    monkeypatch.setattr("core.model_runner.get_model_runner", lambda: calls.append(1))
    monkeypatch.setattr(t2e.subprocess, "run", lambda *a, **k: calls.append(2))

    for argv in (["--models", "x", "--out-dir", str(tmp_path)],
                 ["--one-model", "x", "--json-out", str(tmp_path / "x.json")]):
        assert t2e.main(argv) == 3
    assert calls == []
    assert "refusing to run a real-model eval inside pytest" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_hc_t2e_007_sealed_output_has_no_text(tmp_path):
    doc = t2e.load_questions(FIXTURE)
    sealed_q = tmp_path / "sealed.json"
    sealed_q.write_text(json.dumps(doc), encoding="utf-8")

    for name, runner in (("cited", FakeRunner(CITED)), ("uncited", FakeRunner(UNCITED))):
        model = t2e.evaluate(sealed_q, name, sealed=True, runner_patch=runner)
        report = t2e.build_report([model], sealed_q, sealed=True)
        out = tmp_path / name
        t2e.write_outputs(out, report)
        written = (out / "legacy_cite_eval.json").read_text(encoding="utf-8")
        written += (out / "legacy_cite_eval.md").read_text(encoding="utf-8")

        assert report["questions_sha256"] == t2e.fixture_sha256(sealed_q)
        assert report["questions_sha256"] in written
        assert "per_question" not in written
        for q in doc["questions"]:
            assert q not in written, q
        for c in doc["chunks"]:
            assert c["text"] not in written
        for text in (CITED, UNCITED, "Glucose: 95", "Reference ranges can vary", ABSTAIN_TEMPLATE):
            assert text not in written, text
        assert json.loads((out / "legacy_cite_eval.json").read_text(encoding="utf-8"))["models"][0]["n"] == 20

    # Non-sealed output does keep the per-question detail (so the test above can fail).
    open_report = t2e.build_report([t2e.evaluate(sealed_q, "open", runner_patch=FakeRunner(CITED))], sealed_q)
    assert doc["questions"][0] in json.dumps(open_report)


def test_hc_t2e_008_cite_value_mismatch():
    chunks = {"doc-1": "Glucose: 95 mg/dL (reference range 70-100 mg/dL), collected 2026-01-10."}
    match = _body("x", [_seg("report_facts", "Glucose: 95 mg/dL (reference range 70-100 mg/dL) [cite:1].", True)])
    wrong = _body("x", [_seg("report_facts", "Glucose: 96 mg/dL [cite:1].", True)])
    other_doc = _body("x", [_seg("report_facts", "Glucose: 95 mg/dL [cite:2].", True, doc_id="doc-2")])
    general = _body("x", [_seg("general_info", "Normal is 60-200 [cite:1].", True)])

    assert t2e.cite_value_mismatches(match, chunks) == 0
    assert t2e.cite_value_mismatches(wrong, chunks) == 1
    assert t2e.cite_value_mismatches(other_doc, {**chunks, "doc-2": "LDL Cholesterol: 128 mg/dL"}) == 1
    assert t2e.cite_value_mismatches(general, chunks) == 0  # only report_facts segments are checked
