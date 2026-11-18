"""AUDIT-CHAT-LEGACY: the legacy chat answer and the no-model fallback are audited.

Plan: docs/plans/2026-11-06-docs-audit-rows-plan.md, section "AUDIT-CHAT-LEGACY".

POST /assistant/chat on the legacy path (agent off, or the agent raised) used to
write an audit row only when a prohibited-pattern or advice gate fired. A served
legacy answer, a G-B5 abstention and the knowledge-base fallback left no trace.
These tests drive the route over HTTP (tests/support/routes.py::route_client) with
a real in-memory profile DB and a recording master DB. Only retrieval and
generation are stubbed. The rows carry ids and enums only.

HC-ACL-001  clean verified answer     -> one assistant.chat.legacy row, decision=answer
HC-ACL-002  invalid answer, G-B5      -> one assistant.chat.legacy row, decision=abstain
HC-ACL-003  rag.query raises          -> one assistant.chat.fallback row, no details
HC-ACL-004  audit commit fails        -> 500, no turn stored, answer not served (both paths)
HC-ACL-005  no question or answer text in any row field or app log (both paths)
"""

from __future__ import annotations

import json
import logging
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
from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE
from modules.rag import ModelUnavailableError, ValidatedResponse, VerificationMetadata
from modules.rag import ResponseSegment as RagSegment
from tests.support.routes import route_client

QUESTION = "What was my LDL result?"
Q_SENTINEL = "ACL-QUESTION-SENTINEL-5e1d"
ANSWER_SENTINEL = "ACL-ANSWER-SENTINEL-c07b"
FALLBACK_SENTINEL = "ACL-FALLBACK-SENTINEL-82aa"


class _RecordingMasterDb:
    """Master-DB double: records added rows and commit calls."""

    def __init__(self, *, fail_commit: bool = False) -> None:
        self.added: list = []
        self.commits = 0
        self.fail_commit = fail_commit

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("audit store down")
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


def _answer(*, valid: bool) -> ValidatedResponse:
    return ValidatedResponse(
        segments=[RagSegment(segment_type="report_facts", content=ANSWER_SENTINEL, citations=[])],
        is_valid=valid,
        validation_errors=[] if valid else ["unverified_claim"],
        verification=VerificationMetadata(
            verification_enabled=True,
            total_claims=1,
            verified_claims=1 if valid else 0,
            failed_claims=0 if valid else 1,
            faithfulness_score=0.9,
            authority_score=0.5,
            verification_summary="stub",
        ),
    )


async def _post_chat(
    *,
    mode: str,
    question: str = QUESTION,
    valid: bool = True,
    master=None,
    raise_server_exceptions: bool = True,
):
    """POST one chat question. mode: "legacy" (rag.query answers) or "fallback"
    (rag.query raises ModelUnavailableError and the knowledge-base fallback runs)."""
    master = master if master is not None else _RecordingMasterDb()
    rag = MagicMock()
    if mode == "legacy":
        rag.query = AsyncMock(return_value=_answer(valid=valid))
    else:
        rag.query = AsyncMock(side_effect=ModelUnavailableError("no model"))
    fallback = A.ChatResponse(
        segments=[],
        full_response=FALLBACK_SENTINEL,
        verification=A.VerificationInfo(enabled=False),
    )
    profile_db, engine = await _profile_db()
    try:
        with patch.object(A, "get_rag_module", return_value=rag), \
             patch.object(A, "get_strict_rag_module", return_value=rag), \
             patch.object(A, "is_agent_enabled", return_value=False), \
             patch.object(A, "_build_knowledge_fallback", AsyncMock(return_value=fallback)):
            with route_client(
                assistant_router,
                "/assistant",
                profile_id="profile-a",
                master_db=master,
                raise_server_exceptions=raise_server_exceptions,
            ) as client:

                async def _override_profile_db():
                    return profile_db

                client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
                resp = client.post("/assistant/chat", json={"question": question})
        profile_db.expire_all()
        turns = list((await profile_db.execute(select(ChatTurn))).scalars().all())
        return resp, turns, master
    finally:
        await profile_db.close()
        await engine.dispose()


def _audit_rows(master) -> list:
    return [o for o in master.added if type(o).__name__ == "AuditLog"]


@pytest.mark.asyncio
async def test_hc_acl_001_clean_legacy_answer_is_audited_once_as_answer():
    resp, turns, master = await _post_chat(mode="legacy", valid=True)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert ANSWER_SENTINEL in body["full_response"]
    assert body["is_valid"] is True
    rows = _audit_rows(master)
    assert [r.event_type for r in rows] == ["assistant.chat.legacy"]
    row = rows[0]
    assert row.action == "assistant.chat.legacy"
    assert row.profile_id == "profile-a"
    assert row.entity_type == "chat_session"
    assert row.entity_id == body["session_id"]
    assert json.loads(row.details_json) == {"decision": "answer"}
    assert master.commits >= 1
    assert any(ANSWER_SENTINEL in t.content for t in turns if t.role == "assistant")


@pytest.mark.asyncio
async def test_hc_acl_002_invalid_answer_replaced_by_abstain_is_audited_as_abstain():
    resp, turns, master = await _post_chat(mode="legacy", valid=False)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # G-B5 still withholds the answer: the row records that it did.
    assert ABSTAIN_TEMPLATE in body["full_response"]
    assert ANSWER_SENTINEL not in resp.text
    rows = _audit_rows(master)
    assert [r.event_type for r in rows] == ["assistant.chat.legacy"]
    assert rows[0].entity_type == "chat_session"
    assert rows[0].entity_id == body["session_id"]
    assert json.loads(rows[0].details_json) == {"decision": "abstain"}
    assert all(ANSWER_SENTINEL not in t.content for t in turns)


@pytest.mark.asyncio
async def test_hc_acl_003_no_model_fallback_is_audited_once_without_details():
    resp, turns, master = await _post_chat(mode="fallback")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["full_response"] == FALLBACK_SENTINEL
    rows = _audit_rows(master)
    assert [r.event_type for r in rows] == ["assistant.chat.fallback"]
    row = rows[0]
    assert row.action == "assistant.chat.fallback"
    assert row.profile_id == "profile-a"
    assert row.entity_type == "chat_session"
    assert row.entity_id == body["session_id"]
    assert row.details_json is None
    assert master.commits >= 1
    assert [t.content for t in turns if t.role == "assistant"] == [FALLBACK_SENTINEL]


@pytest.mark.parametrize("mode", ["legacy", "fallback"])
@pytest.mark.asyncio
async def test_hc_acl_004_audit_failure_fails_closed(mode):
    master = _RecordingMasterDb(fail_commit=True)
    resp, turns, _m = await _post_chat(
        mode=mode, master=master, raise_server_exceptions=False
    )
    assert resp.status_code == 500, (mode, resp.text)
    assert turns == [], f"a turn was stored although the audit failed (mode={mode})"
    assert ANSWER_SENTINEL not in resp.text
    assert FALLBACK_SENTINEL not in resp.text
    # Non-vacuous: the route reached the audit write and it was the write that failed.
    assert len(_audit_rows(master)) == 1


@pytest.mark.parametrize("mode", ["legacy", "fallback"])
@pytest.mark.asyncio
async def test_hc_acl_005_rows_and_logs_hold_no_question_or_answer_text(mode, caplog):
    caplog.set_level(logging.DEBUG)
    question = f"{QUESTION} {Q_SENTINEL}"
    resp, _turns, master = await _post_chat(mode=mode, question=question)
    assert resp.status_code == 200, resp.text
    rows = _audit_rows(master)
    expected = "assistant.chat.legacy" if mode == "legacy" else "assistant.chat.fallback"
    assert [r.event_type for r in rows] == [expected]  # non-vacuous
    sentinels = (Q_SENTINEL, ANSWER_SENTINEL, FALLBACK_SENTINEL, QUESTION)
    for row in rows:
        for field in ("action", "entity_id", "details_json"):
            value = str(getattr(row, field))
            for s in sentinels:
                assert s not in value, (field, s)
    # SQL bound-parameter debug lines from the DB drivers are excluded: any insert logs them.
    app_logs = " ".join(
        r.getMessage()
        for r in caplog.records
        if not r.name.startswith(("aiosqlite", "sqlalchemy"))
    )
    for s in sentinels:
        assert s not in app_logs, s
