"""B-3 PARA-1-R3 option C: the local advice judge ORed into the prohibited floor.

Plan: docs/plans/2026-10-15-build-program/lane-B-interpretation-eval.md §B-3.
Owner decisions: PARA-R3-Q1..Q8, PR3-TIER (A), PR3-S5N (owner-decisions-2026-09-27.md).

Every test uses a fake provider through ModelRunner(_provider=...), so no model
is needed. The two route tests (HC-PARA-103/104/106) go through HTTP with
tests/support/routes.py::route_client, because a test that calls a handler as a
plain function cannot see a broken Depends(...).

`allow_judge_runner()` is the shared ALLOW fake that other test files import
when they reach a real rag.query (contracts R-2: no blanket bypass flag, so
each such test passes an explicit judge that answers ALLOW).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.model_runner import InferenceResult, ModelRunner

_NO_PATH = object()

# A clean answer the regex floor does not touch.
CLEAN_ANSWER = (
    "REPORT FACTS:\nYour LDL result is listed as 120 mg/dL [cite:1]. ANSWER-SENTINEL-4d1c"
)
# Judge-only: paraphrased advice with none of the floor's phrases in it.
PARAPHRASED_ADVICE = (
    "REPORT FACTS:\nYour LDL is 190 mg/dL [cite:1].\n\n"
    "IMPLICATIONS:\nPeople with a number like this usually end up on a statin, "
    "so ask to be put on one. PARA-JUDGE-ONLY-77e2"
)
# Floor hit: "you have <word>" and "should take" are both prohibited patterns.
FLOOR_ANSWER = (
    "REPORT FACTS:\nYour LDL is 190 mg/dL [cite:1].\n\n"
    "IMPLICATIONS:\nThis means you have hyperlipidemia and you should take "
    "20 mg atorvastatin daily. PARA-FLOOR-55a0"
)


class _Provider:
    """Fake LLM provider: records every prompt, answers with a scripted reply."""

    def __init__(self, reply="ALLOW", finish="stop", raises=None, available=True,
                 model_path=_NO_PATH):
        self.reply = reply
        self.finish = finish
        self.raises = raises
        self.available = available
        self.prompts: list[str] = []
        self.configs: list = []
        if model_path is not _NO_PATH:
            # Instance attribute, so hasattr(provider, "_find_model_path") is True
            # only for the tests that ask for a model path.
            if isinstance(model_path, BaseException):
                def _boom():
                    raise model_path
                self._find_model_path = _boom
            else:
                self._find_model_path = lambda: model_path

    def is_available(self) -> bool:
        return self.available

    async def generate_async(self, messages, config):
        self.prompts.append(messages[0].content)
        self.configs.append(config)
        if self.raises is not None:
            raise self.raises
        return InferenceResult(
            text=self.reply, tokens_generated=1, finish_reason=self.finish, model_name="fake"
        )


def judge_runner(reply="ALLOW", **kw) -> tuple[ModelRunner, _Provider]:
    provider = _Provider(reply=reply, **kw)
    return ModelRunner(_provider=provider), provider


def allow_judge_runner() -> ModelRunner:
    """ModelRunner whose judge answers ALLOW. For tests that reach a real rag.query."""
    return judge_runner("ALLOW")[0]


def _rag_module():
    from modules.rag import RAGModule

    return RAGModule(enable_verification=False)


def _chunk(text="LDL cholesterol reference text. CONTEXT-SENTINEL-9b3e"):
    from modules.rag import RetrievedChunk

    return RetrievedChunk(
        chunk_id="c1", source_type="reference", doc_id=None, doc_title="LDL reference",
        page=None, text=text, relevance_score=0.9,
    )


async def _query(answer: str, **kw):
    rag = _rag_module()
    rag.retrieve_context = AsyncMock(return_value=[_chunk()])
    rag._generate_with_runner = AsyncMock(return_value=answer)
    return await rag.query(question="what is my ldl?", profile_id="profile-a", **kw)


# ---------------------------------------------------------------- HC-PARA-101


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reply,finish,raises,available,expected",
    [
        ("ALLOW", "stop", None, True, "ALLOW"),
        (" ALLOW\n", "stop", None, True, "ALLOW"),
        ("BLOCK", "stop", None, True, "BLOCK"),
        ("", "stop", None, True, "UNAVAILABLE"),
        ("allow", "stop", None, True, "UNAVAILABLE"),
        ("ALLOW please", "stop", None, True, "UNAVAILABLE"),
        ("ALLOW\nBLOCK", "stop", None, True, "UNAVAILABLE"),
        ("ALLOW", "timeout", None, True, "UNAVAILABLE"),
        ("ALLOW", "stop", RuntimeError("boom"), True, "UNAVAILABLE"),
        ("ALLOW", "stop", None, False, "UNAVAILABLE"),
    ],
)
async def test_hc_para_101_parser_is_exact_and_fails_closed(
    reply, finish, raises, available, expected
):
    from modules.agent.guardrails.advice_judge import advice_judge

    runner, _ = judge_runner(reply, finish=finish, raises=raises, available=available)
    assert await advice_judge("some answer", runner) == expected


# ---------------------------------------------------------------- HC-PARA-102


@pytest.mark.asyncio
async def test_hc_para_102_judge_prompt_goes_only_to_the_local_runner():
    from modules.agent.guardrails.advice_judge import FROZEN_PROMPT

    external, ext_provider = judge_runner(CLEAN_ANSWER)  # the request (external) runner
    local, local_provider = judge_runner("ALLOW")
    rag = _rag_module()
    rag.retrieve_context = AsyncMock(return_value=[_chunk()])
    judge_marker = FROZEN_PROMPT.split("{answer}")[0]
    with patch("modules.rag.get_model_runner", return_value=local):
        result = await rag.query(
            question="what is my ldl?", profile_id="profile-a", model_runner=external
        )
    assert ext_provider.prompts, "the request runner generated nothing"
    assert all(judge_marker not in p for p in ext_provider.prompts), \
        "the answer judge prompt reached the external runner"
    assert len(local_provider.prompts) == 1
    assert local_provider.prompts[0].startswith(judge_marker)
    assert result.prohibited_advice is False


# ------------------------------------------------------- HC-PARA-103 / 104 / 106


def _judge_patch(runner):
    return patch("modules.rag.get_model_runner", return_value=runner)


@pytest.mark.asyncio
async def test_hc_para_103_chat_route_blocks_on_judge_block():
    from tests.test_safe_chat_prohibited import (
        ESCALATE_TEMPLATE, _audit_rows, _post_chat, _RecordingMasterDb,
    )

    floor = __import__("modules.interpret_safety", fromlist=["x"]).InterpretationSafetyGuard
    assert not any(re.search(p, PARAPHRASED_ADVICE, re.I) for p, _ in floor.PROHIBITED_PATTERNS), \
        "fixture must be judge-only, not a floor hit"
    master = _RecordingMasterDb()
    with _judge_patch(judge_runner("BLOCK")[0]):
        resp, turns = await _post_chat(PARAPHRASED_ADVICE, master)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "PARA-JUDGE-ONLY-77e2" not in json.dumps(body)
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert [t.content for t in turns if t.role == "assistant"] == [ESCALATE_TEMPLATE]
    rows = _audit_rows(master)
    assert len(rows) == 1 and rows[0].event_type == "assistant.prohibited_blocked"
    assert json.loads(rows[0].details_json) == {
        "reason": "advice_judge", "decision": "escalate",
    }
    assert "PARA-JUDGE-ONLY-77e2" not in str(rows[0].details_json)


from tests.test_safe_interp_grounded import dbs  # noqa: E402,F401  (fixture)


async def _grounded(dbs, answer, runner):
    from unittest.mock import patch as _p

    import api.interpretations as I
    from tests.test_safe_interp_grounded import _call, _rag

    profile_db, master_db, obs_id = dbs
    with _p.object(I, "get_rag_module", return_value=_rag(answer)), _judge_patch(runner):
        resp = _call(profile_db, master_db, "POST",
                     f"/interpretations/observations/{obs_id}/interpret-grounded")
    return resp, master_db


async def _blocked_row(master_db):
    from tests.test_safe_interp_grounded import _audit_rows

    rows = await _audit_rows(master_db)
    blocked = [r for r in rows if r.event_type == "interpretation.prohibited_blocked"]
    assert len(blocked) == 1, [r.event_type for r in rows]
    return json.loads(blocked[0].details_json)


@pytest.mark.asyncio
async def test_hc_para_104_grounded_route_blocks_on_judge_block(dbs):
    from tests.test_safe_interp_grounded import ESCALATE_TEMPLATE

    resp, master_db = await _grounded(dbs, PARAPHRASED_ADVICE, judge_runner("BLOCK")[0])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "PARA-JUDGE-ONLY-77e2" not in json.dumps(body)
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert await _blocked_row(master_db) == {"reason": "advice_judge", "decision": "escalate"}


@pytest.mark.asyncio
async def test_hc_para_106_judge_raises_blocks_chat_route():
    from tests.test_safe_chat_prohibited import (
        ESCALATE_TEMPLATE, _audit_rows, _post_chat, _RecordingMasterDb,
    )

    master = _RecordingMasterDb()
    runner, _ = judge_runner(raises=RuntimeError("judge down"))
    with _judge_patch(runner):
        resp, turns = await _post_chat(CLEAN_ANSWER, master)
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_response"] == ESCALATE_TEMPLATE
    assert [t.content for t in turns if t.role == "assistant"] == [ESCALATE_TEMPLATE]
    assert json.loads(_audit_rows(master)[0].details_json) == {
        "reason": "advice_judge_unavailable", "decision": "escalate",
    }


@pytest.mark.asyncio
async def test_hc_para_106b_judge_raises_blocks_grounded_route(dbs):
    from tests.test_safe_interp_grounded import ESCALATE_TEMPLATE

    runner, _ = judge_runner(raises=RuntimeError("judge down"))
    resp, master_db = await _grounded(dbs, CLEAN_ANSWER, runner)
    assert resp.status_code == 201, resp.text
    assert resp.json()["full_response"] == ESCALATE_TEMPLATE
    assert await _blocked_row(master_db) == {
        "reason": "advice_judge_unavailable", "decision": "escalate",
    }


# ---------------------------------------------------------------- HC-PARA-105


@pytest.mark.asyncio
async def test_hc_para_105_floor_hit_escalates_and_judge_is_not_called():
    runner, provider = judge_runner("ALLOW")
    result = await _query(FLOOR_ANSWER, judge_runner=runner)
    assert result.prohibited_advice is True
    assert result.prohibited_reason == "prohibited_pattern"
    assert provider.prompts == [], "the judge ran although the floor already fired"


# ---------------------------------------------------------------- HC-PARA-107


@pytest.mark.asyncio
async def test_hc_para_107_judge_prompt_has_answer_only():
    from modules.agent.guardrails.advice_judge import FROZEN_PROMPT

    for category in ("diagnostic", "certainty", "dosing", "medication", "emergency"):
        assert category in FROZEN_PROMPT.lower(), category
    runner, provider = judge_runner("ALLOW")
    rag = _rag_module()
    rag.retrieve_context = AsyncMock(return_value=[_chunk()])
    rag._generate_with_runner = AsyncMock(return_value=CLEAN_ANSWER)
    await rag.query(
        question="QUESTION-SENTINEL-2f8a", profile_id="profile-a",
        history=[{"role": "user", "content": "HISTORY-SENTINEL-6c4d"}],
        judge_runner=runner,
    )
    (prompt,) = provider.prompts
    assert "ANSWER-SENTINEL-4d1c" in prompt
    for leaked in ("QUESTION-SENTINEL-2f8a", "CONTEXT-SENTINEL-9b3e", "HISTORY-SENTINEL-6c4d"):
        assert leaked not in prompt, leaked
    cfg = provider.configs[0]
    assert (cfg.max_tokens, cfg.temperature, cfg.timeout_seconds) == (3, 0.0, 2)


# ------------------------------------------------------- HC-PARA-108 / 109


def _low_tier_path() -> Path:
    from modules.model_selector import TIER_MODEL_CONFIG

    return Path("/models") / TIER_MODEL_CONFIG["low"]["filename"].upper()  # casefold match


@pytest.mark.asyncio
async def test_hc_para_108_low_tier_file_is_unavailable_without_a_call():
    from modules.agent.guardrails.advice_judge import advice_judge

    runner, provider = judge_runner("ALLOW", model_path=_low_tier_path())
    assert await advice_judge("some answer", runner) == "UNAVAILABLE"
    assert provider.prompts == [], "generate_async was called on the low tier"

    runner, provider = judge_runner("ALLOW", model_path=OSError("cannot resolve model path"))
    assert await advice_judge("some answer", runner) == "UNAVAILABLE"
    assert provider.prompts == [], "a detection failure must fail closed without a call"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_path", [_NO_PATH, None, Path("/models/gemma-4-e4b-it-Q4_K_M.gguf")],
    ids=["no-method", "none", "mid-tier-file"],
)
async def test_hc_para_109_no_file_or_non_low_file_runs_the_judge(model_path):
    from modules.agent.guardrails.advice_judge import advice_judge

    runner, provider = judge_runner("ALLOW", model_path=model_path)
    assert await advice_judge("some answer", runner) == "ALLOW"
    assert len(provider.prompts) == 1
