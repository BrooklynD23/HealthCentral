"""W-4 / owner decision G-B5 (2026-09-27): on the legacy (non-agent) RAG path an
answer with is_valid=False is never served; the fixed ABSTAIN_TEMPLATE is.

HC-LEG-001  forced faithfulness 0.5 -> abstention template, over HTTP
HC-LEG-004  forced faithfulness 0.6 (the unchanged threshold) -> answer served
            (baseline-green characterization test; not red-first)
HC-LEG-006  invalid but not prohibited -> the SAFE-CHAT branch does not overwrite
            the abstention (red-first)
HC-LEG-007  prohibited -> SAFE-CHAT still serves ESCALATE_TEMPLATE
            (baseline-green characterization test; not red-first)

All go through POST /assistant/chat (route_client). The scorer is
monkeypatched on the class; modules/faithfulness.py is not edited (C-SAFE-1).
"""

from __future__ import annotations

import pytest

from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE
from modules.faithfulness import FaithfulnessScorer, FaithfulnessScores
from tests.legacy_eval.harness import CHAT_PATH, build_chunks, legacy_chat_client

# Passes every other validate_response check on the "glucose" chunks
# (measured 2026-09-27: is_valid=True, errors=[], faithfulness 0.932), so
# forcing the scorer isolates the faithfulness trigger.
CITED_ANSWER = (
    "REPORT FACTS:\n"
    "Glucose: 95 mg/dL (reference range 70-100 mg/dL) [cite:1].\n\n"
    "UNCERTAINTIES:\n"
    "Reference ranges can vary between laboratories."
)

# Byte-identical to golden abstain-uncited-report-facts / escalate-prohibited-advice.
UNCITED_ANSWER = (
    "REPORT FACTS:\nYour glucose result was 95 mg/dL, within the reference range of 70-100 mg/dL.\n\n"
    "GENERAL INFO:\nGlucose is the primary source of energy for the body's cells."
)
PROHIBITED_ANSWER = (
    "REPORT FACTS:\nYour glucose was 95 mg/dL [cite:1].\n\n"
    "GENERAL INFO:\nYou should take metformin to control your blood sugar."
)


def _force_faithfulness(monkeypatch: pytest.MonkeyPatch, score: float) -> None:
    def _score_response(self, claims, source_texts, per_claim_entailment=None):
        return FaithfulnessScores(
            overall_score=score,
            entailment_score=score,
            lexical_score=score,
            semantic_score=0.0,
            consistency_score=1.0,
            n_supporting_facts=0,
            n_contradicting_facts=0,
            n_unsupported_facts=0,
            scoring_confidence=1.0,
            issues=[],
        )

    monkeypatch.setattr(FaithfulnessScorer, "score_response", _score_response)


def test_hc_leg_001_low_faithfulness_legacy_answer_returns_abstention_over_http(monkeypatch):
    _force_faithfulness(monkeypatch, 0.5)
    with legacy_chat_client(build_chunks("glucose"), CITED_ANSWER) as (client, append_turns):
        resp = client.post(CHAT_PATH, json={"question": "What was my glucose?"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Faithfulness is the only failed check: 0.5 alone forces the abstention.
    assert body["is_valid"] is False
    assert body["validation_errors"] == ["Low faithfulness score: 0.50"]
    # OQ-5 = A (owner W4-OQ-5): the verification footer is cleared under an abstention.
    assert body["verification"]["enabled"] is False
    assert body["verification"]["issues"] == []
    # The patient sees the fixed template and nothing else.
    assert body["segments"] == [
        {"segment_type": "uncertainty", "content": ABSTAIN_TEMPLATE, "citations": []}
    ]
    assert body["full_response"] == f"**UNCERTAINTY**\n{ABSTAIN_TEMPLATE}"
    # The invalid answer appears nowhere in the payload.
    assert "95 mg/dL" not in resp.text
    assert "Reference ranges can vary" not in resp.text
    # What is persisted (history, feedback, RL export) is what was served.
    assert append_turns.await_args.kwargs["assistant_content"] == body["full_response"]


def test_hc_leg_004_faithfulness_at_threshold_0_6_is_served_unchanged(monkeypatch):
    _force_faithfulness(monkeypatch, 0.6)
    with legacy_chat_client(build_chunks("glucose"), CITED_ANSWER) as (client, append_turns):
        resp = client.post(CHAT_PATH, json={"question": "What was my glucose?"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is True
    assert body["validation_errors"] == []
    assert ABSTAIN_TEMPLATE not in resp.text
    assert [s["segment_type"] for s in body["segments"]] == ["report_facts", "uncertainty"]
    assert "[cite:1]" in body["segments"][0]["content"]
    assert append_turns.await_args.kwargs["assistant_content"] == body["full_response"]


def test_hc_leg_006_safe_chat_does_not_overwrite_the_abstention_over_http():
    """Invalid but not prohibited: W-4's abstention must survive the SAFE-CHAT branch."""
    with legacy_chat_client(build_chunks("glucose"), UNCITED_ANSWER) as (client, append_turns):
        resp = client.post(CHAT_PATH, json={"question": "What was my glucose?"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    assert "Response contains prohibited medical advice" not in body["validation_errors"]
    assert body["segments"] == [
        {"segment_type": "uncertainty", "content": ABSTAIN_TEMPLATE, "citations": []}
    ]
    assert body["full_response"] == f"**UNCERTAINTY**\n{ABSTAIN_TEMPLATE}"
    assert body["verification"]["enabled"] is False  # OQ-5 = A: footer cleared
    assert ESCALATE_TEMPLATE not in resp.text
    assert "95 mg/dL" not in resp.text  # the withheld answer is nowhere in the payload
    assert append_turns.await_args.kwargs["assistant_content"] == body["full_response"]


def test_hc_leg_007_prohibited_advice_still_escalates_over_http():
    """Prohibited: SAFE-CHAT's escalation wins over W-4's abstention (owner SAFE-CHAT-TPL)."""
    with legacy_chat_client(build_chunks("glucose"), PROHIBITED_ANSWER) as (client, append_turns):
        resp = client.post(CHAT_PATH, json={"question": "What should I do about my glucose?"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["segments"] == [
        {"segment_type": "uncertainty", "content": ESCALATE_TEMPLATE, "citations": []}
    ]
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert ABSTAIN_TEMPLATE not in resp.text
    assert "metformin" not in resp.text
    assert append_turns.await_args.kwargs["assistant_content"] == ESCALATE_TEMPLATE
