"""HC-A1-VERIFY-001..003 — the agent path must not report fabricated
verification numbers.

Roadmap item A1 (docs/plans/2026-09-10-implementation-roadmap.md): before
this fix, `api/assistant.py::_agent_terminal_to_response_parts` built
`VerificationInfo` from hardcoded constants (`faithfulness_score=1.0`,
`failed_claims=0`) for EVERY answer terminal, regardless of whether any
sentence was actually dropped by the guard's groundedness mapping. A health
app was showing patients a perfect trust score that nothing computed.

These go through HTTP via `tests/support/routes.py::route_client`, per
recurring-failures.md #1: a test calling the route function directly cannot
see a broken `Depends(...)`. The POST /assistant/chat route pulls its
profile-scoped dependencies (`ProfileDbSession`) through FastAPI's real
dependency graph here, not by calling `chat(...)` as a plain function.

Each test seeds the agent's semantic cache (`modules/agent/cache.py`) with a
synthetic `AgentTerminal` under the exact `(normalized_question,
profile_version)` key the route will compute for an empty profile, so the
cache-hit branch of `_serve_via_agent` — and therefore the real
`_agent_terminal_to_response_parts` — is exercised end-to-end over HTTP,
without needing to drive the full plan/act/reflect/draft graph.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import chat_session, document, model_settings, observation  # noqa: F401  register tables
from modules.agent.cache import CacheKey, clear_cache, normalize_question, put_cached
from modules.agent.schemas import AgentTerminal, Citation
from tests.support.routes import route_client


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _client(profile_id, profile_db):
    ctx = route_client(assistant_router, "/assistant", profile_id=profile_id)
    client = ctx.__enter__()

    async def _override_profile_db():
        return profile_db

    client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
    return ctx, client


EMPTY_PROFILE_VERSION = "o:0:|d:0:"  # _profile_version's fingerprint for a profile with no rows


def _seed_cache(question: str, terminal: AgentTerminal) -> None:
    key = CacheKey(
        normalized_question=normalize_question(question),
        profile_version=EMPTY_PROFILE_VERSION,
    )
    put_cached(key, terminal)


@pytest.mark.asyncio
async def test_hc_a1_verify_001_partial_grounding_never_reports_perfect_score(profile_db):
    """An answer terminal where the guard's groundedness mapping dropped one
    sentence must NOT come back as a 1.0 faithfulness score with zero failed
    claims — that combination is only honest when a real mapping produced it.
    """
    profile_id = str(uuid.uuid4())
    question = "How has my LDL and kidney function changed?"
    terminal = AgentTerminal(
        terminal="answer",
        text="Your LDL was 138 mg/dL.",
        citations=[Citation(source_type="document", source_id="obs-ldl-1", locator="obs-ldl-1")],
        run_id="run-partial",
        surviving_count=3,
        dropped_count=1,
    )
    clear_cache()
    try:
        _seed_cache(question, terminal)
        ctx, client = _client(profile_id, profile_db)
        try:
            resp = client.post("/assistant/chat", json={"question": question})
        finally:
            ctx.__exit__(None, None, None)
    finally:
        clear_cache()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    v = body["verification"]

    assert v["enabled"] is True
    assert not (v["faithfulness_score"] == 1.0 and v["failed_claims"] == 0), (
        "a partial-grounding answer (1 sentence dropped) must not report a "
        "perfect, zero-failure score"
    )
    assert v["total_claims"] == 4
    assert v["verified_claims"] == 3
    assert v["failed_claims"] == 1
    assert v["faithfulness_score"] == pytest.approx(0.75)
    assert "faithfulness" not in v["summary"]
    assert v["summary"] == "agent:groundedness:answer"


@pytest.mark.asyncio
async def test_hc_a1_verify_002_fully_grounded_answer_reports_real_perfect_score(profile_db):
    """A real mapping with zero drops legitimately reports 1.0/0 — the
    invariant is "fabricated", not "perfect is forbidden".
    """
    profile_id = str(uuid.uuid4())
    question = "What was my most recent HDL result?"
    terminal = AgentTerminal(
        terminal="answer",
        text="Your HDL was 55 mg/dL.",
        citations=[Citation(source_type="document", source_id="obs-hdl-1", locator="obs-hdl-1")],
        run_id="run-full",
        surviving_count=2,
        dropped_count=0,
    )
    clear_cache()
    try:
        _seed_cache(question, terminal)
        ctx, client = _client(profile_id, profile_db)
        try:
            resp = client.post("/assistant/chat", json={"question": question})
        finally:
            ctx.__exit__(None, None, None)
    finally:
        clear_cache()

    assert resp.status_code == 200, resp.text
    v = resp.json()["verification"]

    assert v["enabled"] is True
    assert v["total_claims"] == 2
    assert v["verified_claims"] == 2
    assert v["failed_claims"] == 0
    assert v["faithfulness_score"] == 1.0


@pytest.mark.asyncio
async def test_hc_a1_verify_003_terminal_with_no_counts_disables_verification(profile_db):
    """A terminal that never went through groundedness mapping (e.g. the
    pre-model advice-gate escalate) carries no surviving/dropped counts.
    `enabled=False` is the honest value — never an invented score — and the
    frontend already branches on `enabled` to show nothing in that case.
    """
    profile_id = str(uuid.uuid4())
    question = "Should I stop taking my statin?"
    terminal = AgentTerminal(
        terminal="escalate",
        text="Please discuss medication changes with your doctor.",
        citations=[],
        run_id="run-escalate",
        # surviving_count / dropped_count intentionally omitted (None)
    )
    assert terminal.surviving_count is None
    assert terminal.dropped_count is None

    clear_cache()
    try:
        _seed_cache(question, terminal)
        ctx, client = _client(profile_id, profile_db)
        try:
            resp = client.post("/assistant/chat", json={"question": question})
        finally:
            ctx.__exit__(None, None, None)
    finally:
        clear_cache()

    assert resp.status_code == 200, resp.text
    v = resp.json()["verification"]

    assert v["enabled"] is False
    assert v["faithfulness_score"] == 0.0
    assert v["total_claims"] == 0
    assert v["failed_claims"] == 0
