"""HC-FBK-001..004 - FEEDBACK-MODEL-FIELDS-SET: an upsert keeps what it leaves out.

Defect: `upsert_feedback` ran `existing.correction_text = body.correction_text`
unconditionally, so a thumb click after a reload (no correction in the body)
erased the patient's stored correction and tags. Fix: overwrite a field only when
the request names it (`model_fields_set`); an explicit `null` still clears it.

All tests go through HTTP via `tests/support/routes.py::route_client`.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.feedback as feedback_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import chat_session, response_feedback  # noqa: F401  register tables
from models.chat_session import ChatSession, ChatTurn
from models.response_feedback import ResponseFeedback
from tests.support.routes import route_client

PROFILE = "11111111-1111-1111-1111-111111111111"


async def _profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    db = AsyncSession(engine, expire_on_commit=False)
    session_id, turn_id = str(uuid.uuid4()), str(uuid.uuid4())
    db.add(ChatSession(id=session_id, profile_id=PROFILE))
    db.add(ChatTurn(
        id=turn_id, session_id=session_id, profile_id=PROFILE,
        turn_index=0, role="assistant", content="an answer",
    ))
    await db.commit()
    return db, engine, session_id, turn_id


async def _post_all(bodies: list[dict]):
    """POST each body in order to one turn. Returns (responses, stored row, audit mock)."""
    db, engine, session_id, turn_id = await _profile_db()
    audit = AsyncMock()
    try:
        with patch.object(feedback_api, "_emit_audit", audit):
            with route_client(feedback_api.router, "/feedback", profile_id=PROFILE) as client:
                async def _override_profile_db():
                    return db

                client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
                responses = [
                    client.post(
                        f"/feedback/turns/{turn_id}",
                        json={"session_id": session_id, **body},
                    )
                    for body in bodies
                ]
        row = (await db.execute(select(ResponseFeedback))).scalars().all()
    finally:
        await db.close()
        await engine.dispose()
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    assert len(row) == 1
    return responses, row[0], audit


@pytest.mark.asyncio
async def test_hc_fbk_001_a_body_that_leaves_the_fields_out_keeps_them():
    _, row, _ = await _post_all([
        {"rating": -1, "correction_text": "the right answer", "feedback_tags": ["inaccurate"]},
        {"rating": 1},
    ])
    assert row.correction_text == "the right answer"
    assert row.feedback_tags == ["inaccurate"]
    assert row.rating == 1


@pytest.mark.asyncio
async def test_hc_fbk_002_an_explicit_null_clears_both_fields():
    _, row, _ = await _post_all([
        {"rating": -1, "correction_text": "the right answer", "feedback_tags": ["inaccurate"]},
        {"rating": -1, "correction_text": None, "feedback_tags": None},
    ])
    assert row.correction_text is None
    assert row.feedback_tags is None


@pytest.mark.asyncio
async def test_hc_fbk_003_a_new_correction_replaces_the_old_one():
    _, row, _ = await _post_all([
        {"rating": -1, "correction_text": "first", "feedback_tags": ["inaccurate"]},
        {"rating": -1, "correction_text": "second", "feedback_tags": ["unsafe"]},
    ])
    assert row.correction_text == "second"
    assert row.feedback_tags == ["unsafe"]


@pytest.mark.asyncio
async def test_hc_fbk_004_first_post_without_the_fields_creates_none_and_none():
    _, row, audit = await _post_all([{"rating": 1}])
    assert row.correction_text is None
    assert row.feedback_tags is None
    assert audit.await_args.kwargs["details"]["has_correction"] is False
