"""EMPTY-ANSWER-SERVED (owner gate EMPTY-ANS-SCOPE = (a), 2026-10-21): an empty or
whitespace-only model answer is a failed answer, not a valid one.

HC-EAS-001  chat: "" / whitespace -> the G-B5 abstain template is served and persisted
HC-EAS-002  RAGModule.validate_response("") -> is_valid False, "Empty model response"
HC-EAS-003  interpret-grounded: empty answer -> 201 with is_valid False
HC-EAS-004  interpret-grounded: a clean answer keeps its main-branch verdict
            (pin; green before and after the fix)

All routes are driven over HTTP. Unlike test_safe_interp_grounded._rag, the
interpret-grounded tests here leave verification real.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import api.interpretations as I
from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE
from modules.rag import RAGModule, RetrievedChunk
from tests.legacy_eval.harness import CHAT_PATH, AllowJudge, build_chunks, legacy_chat_client
from tests.test_safe_interp_grounded import CLEAN_ANSWER, _call, dbs  # noqa: F401

# Measured on main b9d285e: the real verifier fails both claims of CLEAN_ANSWER
# (validation_errors: '2 claim(s) could not be verified', 'Low faithfulness score').
MEASURED_CLEAN_IS_VALID = False


@pytest.mark.parametrize("answer", ["", "   \n"])
def test_hc_eas_001_empty_chat_answer_abstains_over_http(answer):
    with legacy_chat_client(build_chunks("glucose"), answer) as (client, append_turns):
        resp = client.post(CHAT_PATH, json={"question": "What was my glucose?"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    uncertainty = [s for s in body["segments"] if s["segment_type"] == "uncertainty"]
    assert len(uncertainty) == 1
    assert uncertainty[0]["content"] == ABSTAIN_TEMPLATE
    saved = append_turns.await_args.kwargs["assistant_content"]
    assert saved == body["full_response"]
    assert saved != ""


def test_hc_eas_002_validate_response_rejects_empty_answer():
    result = RAGModule(enable_verification=True).validate_response("", build_chunks("glucose"))
    assert result.is_valid is False
    assert "Empty model response" in result.validation_errors


def _real_verification_rag(answer: str) -> RAGModule:
    with patch("modules.rag.get_model_runner") as runner, patch("modules.rag.EmbeddingsModule"):
        runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        rag = RAGModule(enable_verification=True)
    rag.retrieve_context = AsyncMock(return_value=[
        RetrievedChunk(
            chunk_id="c1", source_type="reference", doc_id=None, doc_title="LDL reference",
            page=None, text="LDL cholesterol reference text.", relevance_score=0.9,
        )
    ])
    rag._generate_with_runner = AsyncMock(return_value=answer)
    return rag


async def _grounded(dbs, answer: str):  # noqa: F811
    profile_db, master_db, obs_id = dbs
    with patch.object(I, "get_rag_module", return_value=_real_verification_rag(answer)), \
            patch("modules.rag.get_model_runner", return_value=AllowJudge()):
        return _call(profile_db, master_db, "POST",
                     f"/interpretations/observations/{obs_id}/interpret-grounded")


@pytest.mark.asyncio
async def test_hc_eas_003_empty_grounded_answer_is_not_valid(dbs):  # noqa: F811
    resp = await _grounded(dbs, "")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    assert "Empty model response" in body["validation_errors"]
    assert body["full_response"] == ""
    assert body["grounded_segments"] == []


@pytest.mark.asyncio
async def test_hc_eas_004_clean_grounded_answer_verdict_unchanged(dbs):  # noqa: F811
    resp = await _grounded(dbs, CLEAN_ANSWER)
    assert resp.status_code == 201, resp.text
    # Measured on main (b9d285e) before the fix; the empty check must not move it.
    body = resp.json()
    assert body["is_valid"] is MEASURED_CLEAN_IS_VALID
    # Guards against a check that fires on every answer (the is_valid pin alone
    # cannot see that). Not the full error list: it carries a faithfulness score.
    assert "Empty model response" not in body["validation_errors"]
