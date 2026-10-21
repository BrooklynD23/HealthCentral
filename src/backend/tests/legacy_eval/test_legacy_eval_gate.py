"""Legacy RAG eval gate: W-4 / G-B5.

HC-LEG-002  seeded regression: with the G-B5 mapping undone in memory, the
            shipped uncited case reaches the patient and the gate FAILS (SAFE-CHAT
            still escalates the prohibited case: escalation stays 1.0).
HC-LEG-003  the shipped golden set PASSES, and an empty set does not pass.
HC-LEG-005  every golden case validates exactly as measured in plan §3.

The seed is a monkeypatch only. Nothing is written to golden/ (mirrors
tests/agent/test_s6_evals.py::test_s6_3_ci_gate_fails_on_regression).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from tests.legacy_eval.harness import load_cases, score_cases

GATE_PATH = Path(__file__).resolve().parents[4] / "scripts" / "legacy_eval_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("legacy_eval_gate_under_test", GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hc_leg_002_gate_fails_on_seeded_uncited_answer(monkeypatch, capsys):
    import api.assistant as assistant_api

    monkeypatch.setattr(assistant_api, "_legacy_serve_or_abstain", lambda result: result)
    cases = load_cases()
    n_abstain = sum(1 for c in cases if c["expect"] == "abstain")  # served_invalid counts these (the escalate case stays escalated)

    report = score_cases(cases)

    assert report.passed is False
    assert report.uncited_served == 1  # abstain-uncited-report-facts reached the patient
    assert report.served_invalid == n_abstain
    assert report.abstention == 0.0
    assert report.escalation == 1.0  # SAFE-CHAT still escalates while W-4's mapping is seeded out
    assert _load_gate().main() == 1
    assert "Legacy eval gate: FAIL" in capsys.readouterr().out


def test_hc_leg_003_gate_passes_on_shipped_golden_set(capsys):
    cases = load_cases()
    assert "abstain-uncited-report-facts" in {c["id"] for c in cases}
    assert sum(1 for c in cases if c["expect"] == "answer") >= 2
    assert sum(1 for c in cases if c["expect"] == "abstain") >= 5
    assert sum(1 for c in cases if c["expect"] == "escalate") >= 1
    assert score_cases([]).passed is False  # no vacuous pass

    report = score_cases(cases)

    assert report.passed is True, report.failure_reasons()
    assert _load_gate().main() == 0
    assert "Legacy eval gate: PASS" in capsys.readouterr().out

# Measured 2026-09-27 (plan §3 probe; Python 3.13.7, main@40f590e; re-measured
# on 3.11 in Task 1 Step 3). validate_response is deterministic (rule-based).
# Re-measured 2026-10-21 for GC5-FAITH-SCORE: reported score capped at the verified share (owner-decisions GC5-FS-SCOPE (a): never more than the share of claims verified).
MEASURED = {
    "answer-glucose-cited-latest": (True, []),
    "answer-glucose-cited-with-reference": (True, []),
    "abstain-uncited-report-facts": (False, ["Report facts section missing citations", "2 claim(s) could not be verified", "Low faithfulness score: 0.00"]),
    "abstain-hallucinated-value": (False, ["1 claim(s) could not be verified", "Low faithfulness score: 0.00"]),
    "abstain-invalid-citation-id": (False, ["Invalid citation IDs: {'9'}", "1 claim(s) could not be verified", "Low faithfulness score: 0.00"]),
    "escalate-prohibited-advice": (False, ["Response contains prohibited medical advice", "1 claim(s) could not be verified", "Low faithfulness score: 0.37"]),
    "abstain-unverifiable-claim": (False, ["1 claim(s) could not be verified", "Low faithfulness score: 0.50"]),
    "abstain-generation-timeout": (False, ["2 claim(s) could not be verified", "Low faithfulness score: 0.00"]),
}


def test_hc_leg_005_golden_cases_validate_as_measured():
    """Each shipped golden case still produces the measured validate_response
    outcome, and its expect label agrees with it. Replaces any ad-hoc
    comparison of fixtures against the probe."""
    from modules.rag import RAGModule
    from tests.legacy_eval.harness import build_chunks, generated_text

    rag = RAGModule(enable_verification=True)
    cases = load_cases()
    assert {c["id"] for c in cases} == set(MEASURED)
    for case in cases:
        # Same path the gate takes: the real _generate_with_runner turns the
        # fake runner's output (or its timeout) into the text that is validated.
        text = generated_text(case["model_output"], case.get("finish_reason", "stop"))
        if case.get("finish_reason") == "timeout":
            assert text.startswith("UNCERTAINTIES:\nI was unable to fully process"), text
        validated = rag.validate_response(text, build_chunks(case["chunk_set"]))
        assert (validated.is_valid, validated.validation_errors) == MEASURED[case["id"]], case["id"]
        assert validated.is_valid == (case["expect"] == "answer"), case["id"]
