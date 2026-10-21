"""RUNSTEP-CONTRACT — a RunLog never leaves memory.

Owner answer RRSI-OQ-14 (2026-09-27): ``RunStep.payload`` holds the full tool
output, values included, not handles. That is acceptable only because the
RunLog lives and dies inside ``run_agent``. HC-RUNLOG-001 pins that: one
POST /assistant/chat through HTTP (tests/support/routes.py::route_client) on
the agent path, with a tool output carrying a canary in a field the draft node
never renders, then asserts the canary is in the RunLog (positive control) and
absent from audit calls, the answer cache, stored chat turns and logs.
"""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as A
import modules.agent.cache as agent_cache
import modules.agent.graph as agent_graph
from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import chat_session, model_settings  # noqa: F401  register tables
from models.chat_session import ChatSession, ChatTurn
from models.document import Document
from models.observation import Observation
from modules.agent.state import RunLog
from modules.agent.tools.query_observations import QueryObservationsOutput, QueryObservationsTool
from tests.support.routes import route_client

PROFILE = "profile-a"  # route_client's default session
WHEN = datetime(2026, 1, 15, 12, 0, 0)
# draft renders only value/unit/date/analyte from a row; this extra output
# field is never read by it, so it can only travel inside the RunLog.
CANARY = "RUNLOG-CANARY-7f3c9a21"


class _CanaryOutput(QueryObservationsOutput):
    unrendered_note: str = CANARY


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    db = AsyncSession(engine, expire_on_commit=False)
    db.add(Document(
        id="doc-1", profile_id=PROFILE, path_hash="p", content_hash="c",
        doc_type="pdf", status="verified", collection_date=WHEN, imported_at=WHEN,
    ))
    db.add(Observation(
        id="obs-1", profile_id=PROFILE, doc_id="doc-1", analyte_canonical="glucose",
        analyte_raw="glucose", value=90.0, unit="mg/dL", collected_at=WHEN,
        user_verified=True, verified_at=WHEN,
    ))
    await db.commit()
    agent_cache.clear_cache()
    try:
        yield db
    finally:
        agent_cache.clear_cache()
        await db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_runlog_001_runlog_never_reaches_audit_cache_turns_or_logs(profile_db, caplog):
    caplog.set_level(logging.DEBUG)
    real_run = QueryObservationsTool.run

    async def _run_with_canary(self, args, ctx):
        out = await real_run(self, args, ctx)
        return _CanaryOutput(rows=out.rows)

    run_logs: list[RunLog] = []

    def _recording_run_log(**kwargs):
        run_log = RunLog(**kwargs)
        run_logs.append(run_log)
        return run_log

    audit_spy = AsyncMock()
    put_spy = []
    real_put = A.put_cached

    def _put(key, terminal):
        put_spy.append((key, terminal))
        return real_put(key, terminal)

    with patch.object(A, "is_agent_enabled", return_value=True), \
         patch.object(QueryObservationsTool, "run", _run_with_canary), \
         patch.object(agent_graph, "RunLog", _recording_run_log), \
         patch("core.audit.create_audit_log", audit_spy), \
         patch.object(A, "create_audit_log", audit_spy), \
         patch.object(A, "put_cached", _put):
        with route_client(assistant_router, "/assistant", profile_id=PROFILE) as client:

            async def _override_profile_db():
                return profile_db

            client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
            resp = client.post("/assistant/chat", json={"question": "what is my glucose?"})

    # Agent answered (not the legacy RAG fallback).
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verification"]["summary"].startswith("agent:groundedness:answer"), body["verification"]
    assert "90" in body["full_response"]

    # Positive control: the canary really is in the run's steps.
    assert len(run_logs) == 1
    act_steps = [s for s in run_logs[0].steps if s.node == "act"]
    assert act_steps, "no act step recorded"
    assert any(CANARY in str(s.payload) for s in act_steps), "canary missing from RunLog"

    # Not in the response the client sees.
    assert CANARY not in resp.text

    # Not in any audit call (positional and keyword args, both import sites).
    assert audit_spy.await_count > 0, "audit spy saw no calls, so it proves nothing"
    assert CANARY not in repr(audit_spy.await_args_list)

    # Not in the cache: what was stored, and what the cache now holds.
    assert len(put_spy) == 1
    assert CANARY not in repr(put_spy)
    assert all(CANARY not in v.model_dump_json() for v in agent_cache._cache.values())
    assert all(CANARY not in k.model_dump_json() for k in agent_cache._cache)

    # Not in persistence: the chat rows written for this turn.
    turns = (await profile_db.execute(select(ChatTurn))).scalars().all()
    sessions = (await profile_db.execute(select(ChatSession))).scalars().all()
    assert len(turns) == 2
    assert CANARY not in repr([(t.role, t.content) for t in turns])
    assert CANARY not in repr([(s.id, getattr(s, "title", None)) for s in sessions])

    # Not in logs, even at DEBUG.
    assert CANARY not in caplog.text
