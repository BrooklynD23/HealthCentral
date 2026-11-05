"""LEGACY-ADVICE-GATE: with the agent off or failed, an advice question must not
reach the model.

Plan: docs/plans/2026-10-22-mvp-rows-plan.md, section "LEGACY-ADVICE-GATE".

The pre-model `classify_advice` gate used to run only inside the agent graph.
On the legacy path (agent flag off, or the agent raised) the question went to
`rag.query` and only the post-hoc prohibited-pattern check ran. These tests
drive POST /assistant/chat over HTTP (tests/support/routes.py::route_client)
with a real in-memory profile DB. Spies on both RAG module factories and on
the external runner prove the model is never reached for an advice question.

HC-LAG-001  agent off, advice question -> ESCALATE_TEMPLATE, no model call
HC-LAG-002  agent raises, advice question -> same, and the fallback ran
HC-LAG-003  agent off, factual question -> still reaches rag.query (pin)
HC-LAG-004  the audit row names the reason and carries no question text
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as A
from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import chat_session, document, model_settings, observation  # noqa: F401
from models.chat_session import ChatTurn
from modules.agent.guardrails.templates import ESCALATE_TEMPLATE
from modules.rag import ResponseSegment as RagSegment
from modules.rag import ValidatedResponse, VerificationMetadata
from tests.support.routes import route_client

ADVICE_QUESTION = "Should I stop taking metformin?"
FACTUAL_QUESTION = "What was my LDL result?"
FACTUAL_ANSWER = "FACTUAL-ANSWER-4c1e"


class _RecordingMasterDb:
    """Master-DB double: records added rows and commit calls."""

    def __init__(self) -> None:
        self.added: list = []
        self.commits = 0

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def execute(self, *_a, **_k):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result


async def _profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


def _valid_result() -> ValidatedResponse:
    return ValidatedResponse(
        segments=[RagSegment(segment_type="report_facts", content=FACTUAL_ANSWER, citations=[])],
        is_valid=True,
        verification=VerificationMetadata(),
    )


class _Spies:
    """What the route touched. One query mock is shared by both RAG factories so a
    call through either the normal or the strict module is counted."""

    def __init__(self) -> None:
        self.query = AsyncMock(return_value=_valid_result())
        self.rag = MagicMock()
        self.rag.query = self.query
        self.runner = MagicMock()
        self.runner.generate_async = AsyncMock()
        self.serve_via_agent = AsyncMock(side_effect=RuntimeError("agent down"))


async def _post_chat(question: str, *, agent_enabled: bool):
    master = _RecordingMasterDb()
    spies = _Spies()
    profile_db, engine = await _profile_db()
    try:
        with patch.object(A, "get_rag_module", return_value=spies.rag), \
             patch.object(A, "get_strict_rag_module", return_value=spies.rag), \
             patch.object(A, "is_agent_enabled", return_value=agent_enabled), \
             patch.object(A, "_serve_via_agent", spies.serve_via_agent), \
             patch(
                 "core.external_runner.get_runner_for_request",
                 AsyncMock(return_value=spies.runner),
             ):
            with route_client(
                assistant_router, "/assistant", profile_id="profile-a", master_db=master
            ) as client:

                async def _override_profile_db():
                    return profile_db

                client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
                resp = client.post("/assistant/chat", json={"question": question})
        profile_db.expire_all()
        turns = list((await profile_db.execute(select(ChatTurn))).scalars().all())
        return resp, turns, master, spies
    finally:
        await profile_db.close()
        await engine.dispose()


def _audit_rows(master) -> list:
    return [o for o in master.added if type(o).__name__ == "AuditLog"]


def _assert_escalated_without_model(resp, turns, spies) -> None:
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert body["segments"] == [
        {"segment_type": "uncertainty", "content": ESCALATE_TEMPLATE, "citations": []}
    ]
    spies.query.assert_not_awaited()
    spies.query.assert_not_called()
    spies.runner.generate_async.assert_not_awaited()
    assert spies.runner.mock_calls == [], "the runner was touched"
    assistant_turns = [t for t in turns if t.role == "assistant"]
    assert [t.content for t in assistant_turns] == [ESCALATE_TEMPLATE]


@pytest.mark.asyncio
async def test_hc_lag_001_agent_off_advice_question_escalates_without_model_call():
    resp, turns, _master, spies = await _post_chat(ADVICE_QUESTION, agent_enabled=False)
    _assert_escalated_without_model(resp, turns, spies)
    spies.serve_via_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_hc_lag_002_agent_failed_advice_question_escalates_without_model_call():
    resp, turns, _master, spies = await _post_chat(ADVICE_QUESTION, agent_enabled=True)
    # The agent was tried and raised, so this is the fallback path, not the flag-off path.
    spies.serve_via_agent.assert_awaited_once()
    _assert_escalated_without_model(resp, turns, spies)


@pytest.mark.asyncio
async def test_hc_lag_003_agent_off_factual_question_still_reaches_the_model():
    resp, turns, master, spies = await _post_chat(FACTUAL_QUESTION, agent_enabled=False)
    assert resp.status_code == 200, resp.text
    spies.query.assert_awaited_once()
    assert spies.query.await_args.kwargs["question"] == FACTUAL_QUESTION
    body = resp.json()
    assert FACTUAL_ANSWER in body["full_response"]
    assert body["full_response"] != ESCALATE_TEMPLATE
    assert [t.content for t in turns if t.role == "assistant"] == [body["full_response"]]
    blocked = [r for r in _audit_rows(master) if r.event_type == "assistant.prohibited_blocked"]
    assert blocked == []


@pytest.mark.asyncio
async def test_hc_lag_004_pre_model_audit_row_names_reason_and_holds_no_question_text():
    resp, _turns, master, spies = await _post_chat(ADVICE_QUESTION, agent_enabled=False)
    assert resp.status_code == 200, resp.text
    spies.query.assert_not_awaited()
    rows = _audit_rows(master)
    assert len(rows) == 1
    row = rows[0]
    assert row.event_type == "assistant.prohibited_blocked"
    assert row.profile_id == "profile-a"
    assert json.loads(row.details_json) == {"reason": "pre_model_advice", "decision": "escalate"}
    blob = " ".join(str(getattr(row, c.name)) for c in row.__table__.columns).lower()
    assert ADVICE_QUESTION.lower() not in blob
    assert "metformin" not in blob
    assert master.commits >= 1
