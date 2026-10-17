"""HC-RLEXP-001/002 — RL-EXPORT-EMPTY: feedback must carry the prompt it rates.

Defect (plan `audit/2026-09-25/waves/scaffold/RSI-TPM-MMR.md` §3): the
frontend never sends `prompt_snapshot`, and `upsert_feedback` only copied it
from the request body, so every row was skipped by `rl_dataset` and all three
JSONL exports were empty. The old tests injected `prompt_snapshot` and called
`export_rl_datasets` as a function (recurring-failures #1).

Fix (owner RSI-Q1): the server copies the preceding user `ChatTurn` — same
session, same profile, `turn_index - 1`, `role == "user"`.

Both tests go through HTTP via `tests/support/routes.py::route_client` and
read the exported file, not the module's return value.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.feedback as feedback_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import chat_session, response_feedback  # noqa: F401  register tables
from core.time import utcnow
from models.chat_session import ChatSession, ChatTurn
from models.response_feedback import ResponseFeedback
from tests.support.routes import route_client

PROFILE = "11111111-1111-1111-1111-111111111111"
OTHER_PROFILE = "22222222-2222-2222-2222-222222222222"


async def _profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


async def _seed(db: AsyncSession, turns: list[tuple[str, str, str]]) -> tuple[str, list[str]]:
    """Seed one session; turns are (profile_id, role, content) in index order."""
    session_id = str(uuid.uuid4())
    db.add(ChatSession(id=session_id, profile_id=PROFILE))
    ids = []
    for index, (profile_id, role, content) in enumerate(turns):
        turn_id = str(uuid.uuid4())
        ids.append(turn_id)
        db.add(ChatTurn(
            id=turn_id, session_id=session_id, profile_id=profile_id,
            turn_index=index, role=role, content=content,
        ))
    await db.commit()
    return session_id, ids


def _rate_and_export(db, export_root: Path, ratings: list[tuple[str, str]]):
    """POST feedback for each (session_id, turn_id) without prompt_snapshot,
    then POST /feedback/export. Returns (feedback responses, export response)."""
    with patch.object(feedback_api, "_DEFAULT_EXPORT_DIR", export_root), \
         patch.object(feedback_api, "_emit_audit", AsyncMock()):
        with route_client(feedback_api.router, "/feedback", profile_id=PROFILE) as client:
            async def _override_profile_db():
                return db

            client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
            rated = [
                client.post(
                    f"/feedback/turns/{turn_id}",
                    json={"session_id": session_id, "rating": 1, "response_text": "the answer"},
                )
                for session_id, turn_id in ratings
            ]
            exported = client.post("/feedback/export", json={"confirmed": True})
    return rated, exported


def _grpo_prompts(export_root: Path) -> list[str]:
    path = export_root / f"profile_{PROFILE}" / "grpo_rewards.jsonl"
    return [json.loads(line)["prompt"] for line in path.read_text().splitlines() if line]


@pytest.mark.asyncio
async def test_hc_rlexp_001_export_uses_the_user_turn_right_before_the_rated_answer(tmp_path):
    db, engine = await _profile_db()
    try:
        session_id, ids = await _seed(db, [
            (PROFILE, "user", "FIRST QUESTION about sleep"),
            (PROFILE, "assistant", "first answer"),
            (PROFILE, "user", "Is my LDL of 160 high? Reach me at jane.doe@example.com"),
            (PROFILE, "assistant", "second answer"),
        ])
        rated, exported = _rate_and_export(db, tmp_path, [(session_id, ids[3])])
    finally:
        await db.close()
        await engine.dispose()

    assert rated[0].status_code == 200, rated[0].text
    assert exported.status_code == 200, exported.text
    assert exported.json()["grpo_rewards_count"] == 1, exported.json()
    [prompt] = _grpo_prompts(tmp_path)
    assert "Is my LDL of 160 high?" in prompt
    assert "FIRST QUESTION" not in prompt
    assert "jane.doe@example.com" not in prompt  # strict redaction on export


@pytest.mark.asyncio
async def test_hc_rlexp_002_answer_without_own_preceding_user_turn_is_skipped(tmp_path):
    """Orphan answers are accepted (no 500) and skipped on export. Decoys: the
    turn before is another profile's user turn or an assistant turn; the rated
    turn belongs to another profile or is a user turn; two user turns share the
    preceding index. A valid pair in its own session must export exactly once."""
    db, engine = await _profile_db()
    try:
        foreign_sid, foreign_ids = await _seed(db, [
            (OTHER_PROFILE, "user", "OTHER PROFILE SECRET"),
            (PROFILE, "assistant", "orphan answer 1"),
        ])
        role_sid, role_ids = await _seed(db, [
            (PROFILE, "assistant", "PRIOR ASSISTANT TEXT"),
            (PROFILE, "assistant", "orphan answer 2"),
        ])
        foreign_answer_sid, foreign_answer_ids = await _seed(db, [
            (PROFILE, "user", "QUESTION BEFORE FOREIGN ANSWER"),
            (OTHER_PROFILE, "assistant", "other profile answer"),
        ])
        user_rated_sid, user_rated_ids = await _seed(db, [
            (PROFILE, "user", "QUESTION BEFORE A QUESTION"),
            (PROFILE, "user", "rated user turn"),
        ])
        dup_sid, dup_ids = await _seed(db, [
            (PROFILE, "user", "DUPLICATE INDEX A"),
            (PROFILE, "assistant", "dup answer"),
        ])
        db.add(ChatTurn(
            id=str(uuid.uuid4()), session_id=dup_sid, profile_id=PROFILE,
            turn_index=0, role="user", content="DUPLICATE INDEX B",
        ))
        await db.commit()
        valid_sid, valid_ids = await _seed(db, [
            (PROFILE, "user", "VALID QUESTION"),
            (PROFILE, "assistant", "valid answer"),
        ])
        rated, exported = _rate_and_export(db, tmp_path, [
            (foreign_sid, foreign_ids[1]),
            (role_sid, role_ids[1]),
            (foreign_answer_sid, foreign_answer_ids[1]),
            (user_rated_sid, user_rated_ids[1]),
            (dup_sid, dup_ids[1]),
            (valid_sid, valid_ids[1]),
        ])
    finally:
        await db.close()
        await engine.dispose()

    assert [r.status_code for r in rated] == [200] * 6, [r.text for r in rated]
    assert exported.status_code == 200, exported.text
    assert exported.json()["grpo_rewards_count"] == 1, exported.json()
    assert _grpo_prompts(tmp_path) == ["VALID QUESTION"]


@pytest.mark.asyncio
async def test_hc_rlexp_003_rerating_a_row_stored_without_prompt_backfills_it(tmp_path):
    """Rows written before the fix have prompt_snapshot NULL; re-rating one
    must fill it from the preceding user turn so it reaches the export."""
    db, engine = await _profile_db()
    try:
        session_id, ids = await _seed(db, [
            (PROFILE, "user", "OLD QUESTION"),
            (PROFILE, "assistant", "old answer"),
        ])
        db.add(ResponseFeedback(
            id=str(uuid.uuid4()), profile_id=PROFILE, session_id=session_id,
            turn_id=ids[1], rating=-1, prompt_snapshot=None, response_text="old answer",
            created_at=utcnow(), updated_at=utcnow(),
        ))
        await db.commit()
        rated, exported = _rate_and_export(db, tmp_path, [(session_id, ids[1])])
    finally:
        await db.close()
        await engine.dispose()

    assert rated[0].status_code == 200, rated[0].text
    assert exported.status_code == 200, exported.text
    assert exported.json()["grpo_rewards_count"] == 1, exported.json()
    assert _grpo_prompts(tmp_path) == ["OLD QUESTION"]
