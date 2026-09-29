"""HC-CACHE-ISO-001/002 — the agent answer cache must never serve one
profile's answer to another profile (S-CACHE).

Defect (measured at branch B, `src/backend/modules/agent/cache.py:31-35`):
``CacheKey`` is ``(normalized_question, profile_version)`` — no profile id.
``profile_version`` is a fingerprint of the profile's verified evidence
(``api/assistant.py::_profile_version``); two profiles with the same
fingerprint (for example two empty profiles, both ``"o:0:|d:0:"``) collide on
the same key and share cache entries for the same question text.

HC-CACHE-ISO-001 goes through HTTP via ``tests/support/routes.py::route_client``,
per recurring-failures.md #1: a test that calls the route function directly
cannot see a broken ``Depends(...)``.

HC-CACHE-ISO-002 is a unit test of the key itself: before the fix, pydantic's
default ``extra="ignore"`` silently drops the unknown ``profile_id`` kwarg
(``CacheKey`` sets only ``frozen=True``), so two keys built with different
``profile_id`` values compare equal.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as A
from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import chat_session, document, model_settings, observation  # noqa: F401  register tables
from modules.agent.cache import CacheKey, clear_cache, get_cached, put_cached
from modules.agent.schemas import AgentTerminal
from tests.support.routes import route_client


async def _make_profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    return session, engine


def _client(profile_id, profile_db):
    ctx = route_client(assistant_router, "/assistant", profile_id=profile_id)
    client = ctx.__enter__()

    async def _override_profile_db():
        return profile_db

    client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
    return ctx, client


@pytest.mark.asyncio
async def test_hc_cache_iso_001_two_profiles_never_share_cached_answer():
    """Two profiles, same question, same (empty) evidence fingerprint
    ("o:0:|d:0:") must each get their own answer over HTTP, never a cached
    copy of the other profile's answer."""
    profile_a = str(uuid.uuid4())
    profile_b = str(uuid.uuid4())
    question = "what is my latest ldl?"

    session_a, engine_a = await _make_profile_db()
    session_b, engine_b = await _make_profile_db()

    calls: list[str] = []

    async def _stub_run_agent(question, ctx):
        calls.append(ctx.profile_id)
        return AgentTerminal(
            terminal="answer",
            text=f"answer-for-{ctx.profile_id}",
            citations=[],
            run_id=f"run-{ctx.profile_id}",
        )

    clear_cache()
    try:
        with patch.object(A, "run_agent", _stub_run_agent):
            ctx_a, client_a = _client(profile_a, session_a)
            try:
                resp_a = client_a.post("/assistant/chat", json={"question": question})
            finally:
                ctx_a.__exit__(None, None, None)

            ctx_b, client_b = _client(profile_b, session_b)
            try:
                resp_b = client_b.post("/assistant/chat", json={"question": question})
            finally:
                ctx_b.__exit__(None, None, None)
    finally:
        clear_cache()
        await session_a.close()
        await engine_a.dispose()
        await session_b.close()
        await engine_b.dispose()

    assert resp_a.status_code == 200, resp_a.text
    assert resp_b.status_code == 200, resp_b.text

    text_b = resp_b.json()["full_response"]
    assert f"answer-for-{profile_b}" in text_b, text_b
    assert f"answer-for-{profile_a}" not in text_b, text_b
    assert calls == [profile_a, profile_b], (
        f"expected the stub to run once per profile (a miss each time), got {calls}"
    )


def test_hc_cache_iso_002_cache_key_is_profile_scoped():
    """The key itself must distinguish profiles: same question, same
    version, different profile_id -> different key, and a value stored under
    one profile is never visible to a get_cached() for another."""
    key_a = CacheKey(normalized_question="q", profile_version="v", profile_id="a")
    key_b = CacheKey(normalized_question="q", profile_version="v", profile_id="b")
    assert key_a != key_b

    clear_cache()
    try:
        terminal = AgentTerminal(
            terminal="answer", text="answer-for-a", citations=[], run_id="run-a"
        )
        put_cached(key_a, terminal)
        assert get_cached(key_b) is None
    finally:
        clear_cache()
