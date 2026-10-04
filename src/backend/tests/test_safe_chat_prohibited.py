"""SAFE-CHAT — the legacy chat path must never return or persist an answer
that matches a prohibited medical-advice pattern.

Plan: docs/plans/2026-10-04-SAFE-CHAT-legacy-prohibited-abstain.md
Owner decision SAFE-CHAT (2026-10-04).

HC-SAFECHAT-001/002/004 drive POST /assistant/chat over HTTP through
tests/support/routes.py::route_client with a real in-memory profile DB and the
real RAGModule.validate_response; only retrieval and generation are stubbed.
"""

from __future__ import annotations

import json
import re
import uuid
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
from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE
from modules.interpret_safety import InterpretationSafetyGuard
from modules.rag import RetrievedChunk, VerificationMetadata
from tests.support.routes import route_client

MARKER = "SAFECHAT-PROHIBITED-7f3a"
PROHIBITED_ANSWER = (
    "REPORT FACTS:\nYour LDL is 190 mg/dL [cite:1].\n\n"
    f"IMPLICATIONS:\nThis means you have hyperlipidemia and you should take "
    f"20 mg atorvastatin daily {MARKER}."
)
CLEAN_MARKER = "SAFECHAT-CLEAN-91b2"
CLEAN_ANSWER = (
    f"REPORT FACTS:\nYour LDL result is listed as 120 mg/dL [cite:1]. {CLEAN_MARKER}"
)


class _RecordingMasterDb:
    """Master-DB double: records added rows and commit calls."""

    def __init__(self, fail_commit: bool = False) -> None:
        self.added: list = []
        self.commits = 0
        self._fail_commit = fail_commit

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        if self._fail_commit:
            raise RuntimeError("simulated master DB failure")
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


def _rag(answer: str):
    with patch("modules.rag.get_model_runner") as runner, patch("modules.rag.EmbeddingsModule"):
        runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        from modules.rag import RAGModule

        rag = RAGModule(enable_verification=True)
    rag.retrieve_context = AsyncMock(return_value=[
        RetrievedChunk(
            chunk_id="c1", source_type="reference", doc_id=None, doc_title="LDL reference",
            page=None, text="LDL cholesterol reference text.", relevance_score=0.9,
        )
    ])
    rag._generate_with_runner = AsyncMock(return_value=answer)
    # Verification output carrying the answer's own claim text: a leak vector.
    rag._run_verification_pipeline = MagicMock(return_value=VerificationMetadata(
        verification_enabled=True, total_claims=1, verified_claims=0, failed_claims=1,
        claims_with_issues=[f"you have hyperlipidemia {MARKER}"],
        faithfulness_score=0.9, authority_score=0.5, verification_summary="stub",
    ))
    return rag


async def _post_chat(answer: str, master) -> tuple[object, list[ChatTurn]]:
    profile_id = "profile-a"  # route_client's default session
    profile_db, engine = await _profile_db()
    try:
        with patch.object(A, "get_rag_module", return_value=_rag(answer)), \
             patch.object(A, "is_agent_enabled", return_value=False):
            with route_client(
                assistant_router, "/assistant", profile_id=profile_id, master_db=master
            ) as client:

                async def _override_profile_db():
                    return profile_db

                client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
                resp = client.post("/assistant/chat", json={"question": "what is my ldl?"})
        profile_db.expire_all()
        turns = (await profile_db.execute(select(ChatTurn))).scalars().all()
        return resp, list(turns)
    finally:
        await profile_db.close()
        await engine.dispose()


def _audit_rows(master) -> list:
    return [o for o in master.added if type(o).__name__ == "AuditLog"]


@pytest.mark.asyncio
async def test_hc_safechat_001_prohibited_answer_replaced_persisted_and_audited():
    master = _RecordingMasterDb()
    resp, turns = await _post_chat(PROHIBITED_ANSWER, master)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert MARKER not in json.dumps(body), "prohibited answer text reached the client"
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert [s["content"] for s in body["segments"]] == [ESCALATE_TEMPLATE]
    assert body["segments"][0]["citations"] == []
    assert body["verification"]["issues"] == []
    assert body["is_valid"] is False
    assistant_turns = [t for t in turns if t.role == "assistant"]
    assert [t.content for t in assistant_turns] == [ESCALATE_TEMPLATE]
    assert all(MARKER not in t.content for t in turns), "prohibited answer persisted"
    rows = _audit_rows(master)
    assert len(rows) == 1 and rows[0].event_type == "assistant.prohibited_blocked"
    assert rows[0].profile_id == "profile-a"
    blob = " ".join(str(getattr(rows[0], c.name)) for c in rows[0].__table__.columns)
    assert MARKER not in blob and "what is my ldl" not in blob
    assert json.loads(rows[0].details_json) == {
        "reason": "prohibited_pattern", "decision": "escalate",
    }
    assert master.commits >= 1


@pytest.mark.asyncio
async def test_hc_safechat_002_clean_answer_untouched_and_not_audited():
    master = _RecordingMasterDb()
    resp, turns = await _post_chat(CLEAN_ANSWER, master)
    assert resp.status_code == 200, resp.text
    assert CLEAN_MARKER in resp.json()["full_response"]
    assert any(CLEAN_MARKER in t.content for t in turns if t.role == "assistant")
    assert _audit_rows(master) == []


@pytest.mark.parametrize("template", [ESCALATE_TEMPLATE, ABSTAIN_TEMPLATE])
def test_hc_safechat_003_templates_do_not_trip_prohibited_patterns(template):
    for pattern, name in InterpretationSafetyGuard.PROHIBITED_PATTERNS:
        assert not re.search(pattern, template, re.IGNORECASE), name


@pytest.mark.asyncio
async def test_hc_safechat_004_audit_failure_fails_closed():
    master = _RecordingMasterDb(fail_commit=True)
    resp, turns = await _post_chat(PROHIBITED_ANSWER, master)
    assert resp.status_code == 500
    assert MARKER not in resp.text
    assert turns == [], "a turn was persisted although the audit write failed"
