"""SAFE-INTERP-GROUNDED — interpretation routes: a prohibited grounded answer
is replaced with ESCALATE_TEMPLATE, and every route that reads or writes
profile data writes a text-free audit row.

Plan: docs/plans/2026-10-04-SAFE-INTERP-grounded.md
Owner decision SAFE-INTERP-GROUNDED (2026-10-04).

All tests go through HTTP via tests/support/routes.py::route_client with a
real in-memory master DB (audit rows) and a real in-memory profile DB; for
the grounded route only RAG retrieval and generation are stubbed, so the
real RAGModule.validate_response runs.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.interpretations as I
from api.interpretations import router as interpretations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
import models  # noqa: F401  register every table on both bases
from models import LabInterpretation, Observation
from models.audit import AuditLog
from modules.agent.guardrails.templates import ESCALATE_TEMPLATE
from modules.rag import ModelUnavailableError, RetrievedChunk, VerificationMetadata
from tests.support.routes import route_client

PROFILE_ID = "profile-a"  # route_client's default session profile_id
ANALYTE = "ldl"
MARKER = "SAFEINTERP-PROHIBITED-3c9d"
PROHIBITED_ANSWER = (
    "REPORT FACTS:\nYour LDL is 190 mg/dL [cite:1].\n\n"
    "IMPLICATIONS:\nThis means you have hyperlipidemia and you should take "
    f"20 mg atorvastatin daily {MARKER}."
)
CLEAN_MARKER = "SAFEINTERP-CLEAN-5e1a"
CLEAN_ANSWER = f"REPORT FACTS:\nYour LDL result is listed as 120 mg/dL [cite:1]. {CLEAN_MARKER}"
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)


async def _engine_session(base):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


@pytest_asyncio.fixture
async def dbs():
    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    obs = Observation(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
        analyte_canonical=ANALYTE, analyte_raw="LDL Cholesterol", value=120.0,
        unit="mg/dL", ref_low=0.0, ref_high=130.0, collected_at=COLLECTED,
    )
    profile_db.add(obs)
    await profile_db.commit()
    try:
        yield profile_db, master_db, obs.id
    finally:
        await profile_db.close()
        await master_db.close()
        await p_engine.dispose()
        await m_engine.dispose()


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
    rag._run_verification_pipeline = MagicMock(return_value=VerificationMetadata(
        verification_enabled=True, total_claims=1, verified_claims=0, failed_claims=1,
        claims_with_issues=[f"you have hyperlipidemia {MARKER}"],
        faithfulness_score=0.9, authority_score=0.5, verification_summary="stub",
    ))
    return rag


def _call(profile_db, master_db, method: str, url: str, **kwargs):
    with route_client(
        interpretations_router, "/interpretations", profile_id=PROFILE_ID, master_db=master_db
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.request(method, url, **kwargs)


async def _audit_rows(master_db) -> list[AuditLog]:
    master_db.expire_all()
    return list((await master_db.execute(select(AuditLog))).scalars().all())


def _row_blob(row: AuditLog) -> str:
    return " ".join(str(getattr(row, c.name)) for c in row.__table__.columns)


@pytest.mark.asyncio
async def test_hc_safeinterp_001_prohibited_grounded_answer_replaced_and_audited(dbs):
    profile_db, master_db, obs_id = dbs
    with patch.object(I, "get_rag_module", return_value=_rag(PROHIBITED_ANSWER)):
        resp = _call(profile_db, master_db, "POST",
                     f"/interpretations/observations/{obs_id}/interpret-grounded")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert MARKER not in json.dumps(body), "prohibited answer text reached the client"
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert [s["content"] for s in body["grounded_segments"]] == [ESCALATE_TEMPLATE]
    assert body["grounded_segments"][0]["citations"] == []
    assert body["verification"]["issues"] == []
    assert body["is_valid"] is False
    profile_db.expire_all()
    stored = (await profile_db.execute(select(LabInterpretation))).scalars().all()
    assert all(MARKER not in (i.interpretation_text + (i.advice_text or "")) for i in stored)
    rows = await _audit_rows(master_db)
    assert sorted(r.event_type for r in rows) == [
        "interpretation.grounded", "interpretation.prohibited_blocked",
    ]
    for row in rows:
        assert row.profile_id == PROFILE_ID
        blob = _row_blob(row)
        assert MARKER not in blob and "Explain my lab result" not in blob
        assert "LDL" not in blob and ANALYTE not in json.dumps(row.details_json or "")
    blocked = next(r for r in rows if r.event_type == "interpretation.prohibited_blocked")
    assert json.loads(blocked.details_json) == {
        "reason": "prohibited_pattern", "decision": "escalate",
    }


@pytest.mark.asyncio
async def test_hc_safeinterp_002_clean_grounded_answer_untouched(dbs):
    profile_db, master_db, obs_id = dbs
    with patch.object(I, "get_rag_module", return_value=_rag(CLEAN_ANSWER)):
        resp = _call(profile_db, master_db, "POST",
                     f"/interpretations/observations/{obs_id}/interpret-grounded")
    assert resp.status_code == 201, resp.text
    assert CLEAN_MARKER in resp.json()["full_response"]
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == ["interpretation.grounded"]


@pytest.mark.asyncio
async def test_hc_safeinterp_003_grounded_audit_failure_fails_closed(dbs):
    profile_db, master_db, obs_id = dbs

    async def _failing_commit():
        raise RuntimeError("simulated master DB failure")

    # No handler catches it, so TestClient re-raises the server error (in
    # production: HTTP 500). Either way nothing is returned to the client.
    with patch.object(I, "get_rag_module", return_value=_rag(PROHIBITED_ANSWER)), \
         patch.object(master_db, "commit", _failing_commit), \
         pytest.raises(RuntimeError, match="simulated master DB failure"):
        _call(profile_db, master_db, "POST",
              f"/interpretations/observations/{obs_id}/interpret-grounded")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["interpret", "view", "panel", "recent", "batch"])
async def test_hc_safeinterp_004_profile_data_routes_write_audit_row(dbs, route):
    profile_db, master_db, obs_id = dbs
    if route == "view":
        # Something to view: generate first, then drop that audit row.
        _call(profile_db, master_db, "POST", f"/interpretations/observations/{obs_id}/interpret")
        for row in await _audit_rows(master_db):
            await master_db.delete(row)
        await master_db.commit()
    calls = {
        "interpret": ("POST", f"/interpretations/observations/{obs_id}/interpret", {},
                      "interpretation.generate"),
        "view": ("GET", f"/interpretations/observations/{obs_id}/interpretation", {},
                 "interpretation.view"),
        "panel": ("POST", "/interpretations/panels/lipid/interpret",
                  {"params": {"collected_at": COLLECTED.isoformat()}},
                  "interpretation.panel_generate"),
        "recent": ("GET", "/interpretations/recent", {}, "interpretation.list_recent"),
        "batch": ("POST", "/interpretations/batch",
                  {"json": {"observation_ids": [obs_id]}}, "interpretation.batch_generate"),
    }
    method, url, kwargs, event_type = calls[route]
    resp = _call(profile_db, master_db, method, url, **kwargs)
    assert 200 <= resp.status_code < 300, resp.text
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == [event_type], [r.event_type for r in rows]
    assert rows[0].profile_id == PROFILE_ID
    blob = _row_blob(rows[0])
    assert "LDL" not in blob and "lipid" not in blob.lower()


@pytest.mark.asyncio
async def test_hc_safeinterp_005_view_audit_failure_fails_closed(dbs):
    profile_db, master_db, obs_id = dbs
    _call(profile_db, master_db, "POST", f"/interpretations/observations/{obs_id}/interpret")

    async def _failing_commit():
        raise RuntimeError("simulated master DB failure")

    with patch.object(master_db, "commit", _failing_commit), \
         pytest.raises(RuntimeError, match="simulated master DB failure"):
        _call(profile_db, master_db, "GET",
              f"/interpretations/observations/{obs_id}/interpretation")


@pytest.mark.asyncio
async def test_hc_safeinterp_006_model_unavailable_after_write_still_audited(dbs):
    """interpret_observation has already written the LabInterpretation when
    rag.query raises ModelUnavailableError (501): that write must be audited."""
    profile_db, master_db, obs_id = dbs
    rag = _rag(CLEAN_ANSWER)
    rag._generate_with_runner = AsyncMock(side_effect=ModelUnavailableError("no model"))
    with patch.object(I, "get_rag_module", return_value=rag):
        resp = _call(profile_db, master_db, "POST",
                     f"/interpretations/observations/{obs_id}/interpret-grounded")
    assert resp.status_code == 501, resp.text
    profile_db.expire_all()
    stored = (await profile_db.execute(select(LabInterpretation))).scalars().all()
    assert len(stored) == 1
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == ["interpretation.grounded"]
