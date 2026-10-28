"""RAG-TIMEOUT-ANSWER, option 1 "Keep the sentence, label it" (plan delta
2026-10-27, RAG-TIMEOUT-GROUNDED; owner ruling 2026-10-28).

A generation timeout is labelled as a failed answer: validation_errors ==
["Generation timed out"], and the canned timeout sentence is not sent through
the claim verifier, which can only fail it. The grounded route keeps serving
the sentence (no 503, no new branch). The chat abstain (G-B5) is unchanged.

HC-RTA-001  RAGModule.query with a timeout runner: labelled, no claim checks (RED)
HC-RTA-002  interpret-grounded, safety mode off, timeout runner: labelled, sentence served (RED)
HC-RTA-003  /assistant/chat with the timeout runner still serves and persists ABSTAIN_TEMPLATE (pin)
HC-RTA-004  interpret-grounded, clean answer keeps its main verdict, is not labelled (pin)
HC-RTA-005  interpret-grounded, safety mode on, timeout runner: ABSTAIN_TEMPLATE and
            one interpretation.strict_abstained row (pin)

The runner is tests/legacy_eval/harness.py::FakeRunner, so the real
_generate_with_runner timeout branch runs. Routes go through HTTP.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import api.assistant as A
import api.interpretations as I
from modules import rag as rag_module
from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE
from modules.rag import RAGModule, RetrievedChunk
from tests.legacy_eval.harness import CHAT_PATH, FakeRunner, build_chunks, legacy_chat_client
from tests.test_empty_answer import MEASURED_CLEAN_IS_VALID
from tests.test_safe_interp_grounded import CLEAN_ANSWER, _call, dbs  # noqa: F401
from tests.test_safety_mode_strict import _audit_rows, _dbs, _interp, _set_strict

PROFILE_ID = "profile-a"  # route_client's default session profile_id
GENERATION_TIMEOUT_ERROR = "Generation timed out"
# Main's literal, byte for byte (modules/rag.py _generate_with_runner, before the fix).
TIMEOUT_TEXT = (
    "UNCERTAINTIES:\n"
    "I was unable to fully process your question within the time limit. "
    "Please try asking a more specific question about your results."
)
# interpret-grounded's full_response for the timeout text, measured on main
# (safety mode off, real verifier): the header is parsed, the sentence is kept.
MEASURED_TIMEOUT_FULL_RESPONSE = (
    "**UNCERTAINTY**\n"
    "I was unable to fully process your question within the time limit. "
    "Please try asking a more specific question about your results."
)
GROUNDED_URL = "/interpretations/observations/{obs_id}/interpret-grounded"


@pytest.fixture(autouse=True)
def _fresh_rag_singletons(monkeypatch):
    """The factories cache one module each. Every test builds its own."""
    monkeypatch.setattr(A, "_rag_module", None, raising=False)
    monkeypatch.setattr(A, "_strict_rag_module", None, raising=False)


def _ldl_chunks() -> list[RetrievedChunk]:
    return [RetrievedChunk(
        chunk_id="c1", source_type="reference", doc_id=None, doc_title="LDL reference",
        page=None, text="LDL cholesterol reference text.", relevance_score=0.9,
    )]


def _real_rag(factory) -> RAGModule:
    """A module from `factory`, with retrieval stubbed. Generation and the
    verification pipeline stay real."""
    with patch("modules.rag.get_model_runner") as runner, patch("modules.rag.EmbeddingsModule"):
        runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        rag = factory()
    rag.retrieve_context = AsyncMock(return_value=_ldl_chunks())
    return rag


def _runner(text: str = "", finish_reason: str = "timeout"):
    """Patch the runner that the grounded route and chat look up per request."""
    return patch(
        "core.external_runner.get_runner_for_request",
        AsyncMock(return_value=FakeRunner(text, finish_reason)),
    )


# ---------------------------------------------------------------------------
# HC-RTA-001: the shared core, at the RAG module (RED)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_rta_001_query_labels_generation_timeout():
    rag = _real_rag(lambda: RAGModule(enable_verification=True))
    result = await rag.query(
        question="Explain my lab result for LDL Cholesterol.",
        profile_id=PROFILE_ID,
        model_runner=FakeRunner(text="", finish_reason="timeout"),
    )
    assert result.is_valid is False
    assert result.validation_errors == [GENERATION_TIMEOUT_ERROR]
    assert result.insufficient_context is False
    assert result.verification.verification_enabled is False
    assert rag_module.GENERATION_TIMEOUT_TEXT == TIMEOUT_TEXT


# ---------------------------------------------------------------------------
# HC-RTA-002: interpret-grounded, safety mode off, over HTTP (RED)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_rta_002_grounded_timeout_is_labelled_and_sentence_served(dbs):  # noqa: F811
    profile_db, master_db, obs_id = dbs
    rag = _real_rag(lambda: RAGModule(enable_verification=True))
    with patch.object(I, "get_rag_module", return_value=rag), _runner():
        resp = _call(profile_db, master_db, "POST", GROUNDED_URL.format(obs_id=obs_id))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["validation_errors"] == [GENERATION_TIMEOUT_ERROR]
    assert body["is_valid"] is False
    assert body["verification"]["enabled"] is False
    assert body["verification"]["total_claims"] == 0
    assert body["verification"]["issues"] == []
    assert body["full_response"] == MEASURED_TIMEOUT_FULL_RESPONSE


# ---------------------------------------------------------------------------
# HC-RTA-003: chat keeps its G-B5 abstain and persists it (pin)
# ---------------------------------------------------------------------------

def test_hc_rta_003_chat_timeout_still_abstains_and_persists():
    with legacy_chat_client(build_chunks("glucose"), "", finish_reason="timeout") as (
        client, append_turns,
    ):
        resp = client.post(CHAT_PATH, json={"question": "What was my glucose?"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    uncertainty = [s for s in body["segments"] if s["segment_type"] == "uncertainty"]
    assert [s["content"] for s in uncertainty] == [ABSTAIN_TEMPLATE]
    saved = append_turns.await_args.kwargs["assistant_content"]
    assert saved == body["full_response"]
    assert ABSTAIN_TEMPLATE in saved
    assert "time limit" not in saved


# ---------------------------------------------------------------------------
# HC-RTA-004: a clean grounded answer keeps its verdict and is not labelled (pin)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_rta_004_clean_grounded_answer_verdict_unchanged(dbs):  # noqa: F811
    profile_db, master_db, obs_id = dbs
    rag = _real_rag(lambda: RAGModule(enable_verification=True))
    with patch.object(I, "get_rag_module", return_value=rag), _runner(CLEAN_ANSWER, "stop"):
        resp = _call(profile_db, master_db, "POST", GROUNDED_URL.format(obs_id=obs_id))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_valid"] is MEASURED_CLEAN_IS_VALID
    # Guards against a short-circuit that fires on every answer: the verifier must still run.
    assert body["verification"]["enabled"] is True
    assert GENERATION_TIMEOUT_ERROR not in body["validation_errors"]


# ---------------------------------------------------------------------------
# HC-RTA-005: safety mode on, timeout runner: one strict abstain row (pin)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_rta_005_strict_timeout_still_abstains_with_one_audit_row():
    # _dbs() makes a user-verified observation, so _refuse_unverified does not fire first.
    async with _dbs() as (profile_db, master, obs_id):
        _set_strict(profile_db, True)
        assert await A.is_strict_safety_mode(profile_db) is True
        strict_rag = _real_rag(A.get_strict_rag_module)
        off_rag = _real_rag(lambda: RAGModule(enable_verification=True))
        with patch.object(I, "get_strict_rag_module", return_value=strict_rag), \
             patch.object(I, "get_rag_module", return_value=off_rag), _runner():
            resp = _interp(profile_db, master, obs_id)

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["full_response"] == ABSTAIN_TEMPLATE
        assert [s["content"] for s in body["grounded_segments"]] == [ABSTAIN_TEMPLATE]
        assert body["is_valid"] is False
        rows = await _audit_rows(master)
        assert sorted(r.event_type for r in rows) == [
            "interpretation.grounded", "interpretation.strict_abstained",
        ]
