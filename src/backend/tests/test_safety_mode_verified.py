"""SAFETY-MODE-VERIFIED: with strict safety mode on, the interpretation routes in
api/interpretations.py refuse, or leave out, any observation whose user_verified
flag is false. OFF is today's behaviour; ON is only ever stricter.

Plan: docs/plans/2026-10-24-safety-mode-build-plan.md (SAFETY-MODE-VERIFIED).

HTTP tests go through tests/support/routes.py::route_client with a real
in-memory master DB (audit rows) and a real in-memory profile DB. The setting is
switched on through PATCH /assistant/safety-mode. Stubs sit below rag.query:
retrieval and generation only, so the real RAGModule runs its own checks.
"""

from __future__ import annotations

import json
import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as A
import api.interpretations as I
import models  # noqa: F401  register every table on both bases
from api.assistant import router as assistant_router
from api.interpretations import router as interpretations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import LabInterpretation, Observation, PanelInterpretation
from models.audit import AuditLog
from modules.interpret import InterpretModule
from modules.rag import RAGModule, RetrievedChunk, VerificationMetadata
from tests.support.routes import route_client

PROFILE_ID = "profile-a"  # route_client's default session profile_id
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)
LATER_SAME_DAY = datetime(2026, 3, 1, 17, 30, 0)
NEXT_DAY = datetime(2026, 3, 2, 9, 0, 0)
COLLECTED_TXT = "2026-03-01T09:00:00"
NEXT_DAY_TXT = "2026-03-02T09:00:00"
OLDER = datetime(2026, 3, 1, 10, 0, 0)
NEWER = datetime(2026, 3, 2, 10, 0, 0)
SAFETY_URL = "/assistant/safety-mode"
ROUTES = ["interpret", "interpret-grounded"]

REFUSAL = {"code": "observation_unverified", "message": "Verify this result first."}
REFUSED_EVENT = "interpretation.unverified_refused"
ROW_DETAILS = {"reason": "observation_unverified", "decision": "refuse"}
BATCH_ERROR = "Verify this result first"
RAW_LABEL = {"ldl": "LDL Cholesterol", "hdl": "HDL Cholesterol"}

# (analyte, value, collected_at, user_verified). Index 0 is the verified row.
SAME_TIME_ROWS = [
    ("ldl", 120.0, COLLECTED, True),
    ("hdl", 52.0, COLLECTED, False),
]
# Same day as the panel's collected_at, but the unverified member is at another time.
LATER_ROWS = [
    ("ldl", 120.0, COLLECTED, True),
    ("hdl", 52.0, LATER_SAME_DAY, False),
]
ALL_VERIFIED_ROWS = [
    ("ldl", 120.0, COLLECTED, True),
    ("hdl", 52.0, LATER_SAME_DAY, True),
]

# A profile that existed at 015_data_donation. Its row predates the 016 column,
# so strict_safety_mode takes the column's server default ("0"); no ORM default runs.
_INSERT_015_ROW = text(
    "INSERT INTO user_model_settings (id, profile_id, preferred_tier, auto_detect_enabled, "
    "use_external_api, external_api_provider, external_api_key_encrypted, timezone, "
    "voice_logging_enabled, voice_modal_seen, ocr_preference_enabled, assistant_memory_enabled, "
    "created_at, updated_at) VALUES (:id, :pid, 'low', 1, 0, '', '', 'UTC', 0, 0, 1, 1, "
    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
)

ANSWER = "REPORT FACTS:\nYour LDL result is listed as 120 mg/dL [cite:1]."


@pytest.fixture(autouse=True)
def _stub_rag(monkeypatch):
    """Both factories return one real RAGModule with retrieval and generation stubbed.
    Thresholds are not under test here (SAFETY-MODE-STRICT owns them)."""
    rag = _rag_stub()
    monkeypatch.setattr(I, "get_rag_module", lambda: rag)
    monkeypatch.setattr(I, "get_strict_rag_module", lambda: rag)


def _rag_stub() -> RAGModule:
    with patch("modules.rag.get_model_runner") as runner, patch("modules.rag.EmbeddingsModule"):
        runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        rag = RAGModule(enable_verification=True)
    rag.retrieve_context = AsyncMock(return_value=[RetrievedChunk(
        chunk_id="c1", source_type="reference", doc_id=None, doc_title="LDL reference",
        page=None, text="LDL cholesterol reference text.", relevance_score=0.9,
    )])
    rag._generate_with_runner = AsyncMock(return_value=ANSWER)
    rag._run_verification_pipeline = MagicMock(return_value=VerificationMetadata(
        verification_enabled=True, total_claims=1, verified_claims=1, failed_claims=0,
        claims_with_issues=[], faithfulness_score=0.9, authority_score=0.5,
        verification_summary="stub",
    ))
    return rag


# ---------------------------------------------------------------------------
# Databases
# ---------------------------------------------------------------------------

async def _engine_session(base):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


@dataclass
class Db:
    profile: AsyncSession
    master: AsyncSession
    ids: list[str]

    @property
    def verified(self) -> str:
        return self.ids[0]

    @property
    def unverified(self) -> str:
        return self.ids[1]


@asynccontextmanager
async def _dbs(rows=SAME_TIME_ROWS):
    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    try:
        ids = []
        for analyte, value, collected_at, verified in rows:
            obs = Observation(
                id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
                analyte_canonical=analyte, analyte_raw=RAW_LABEL[analyte], value=value,
                unit="mg/dL", ref_low=0.0, ref_high=200.0, collected_at=collected_at,
                user_verified=verified,
            )
            profile_db.add(obs)
            ids.append(obs.id)
        await profile_db.commit()
        yield Db(profile_db, master_db, ids)
    finally:
        await profile_db.close()
        await master_db.close()
        await p_engine.dispose()
        await m_engine.dispose()


async def _insert_015_row(profile_db) -> None:
    await profile_db.execute(_INSERT_015_ROW, {"id": str(uuid.uuid4()), "pid": PROFILE_ID})
    await profile_db.commit()
    flag = (await profile_db.execute(
        text("SELECT strict_safety_mode FROM user_model_settings")
    )).scalar_one()
    assert flag == 0, "a 015 row must read the server default"


async def _audit_rows(master_db) -> list[AuditLog]:
    master_db.expire_all()
    return list((await master_db.execute(select(AuditLog))).scalars().all())


async def _interp_rows(profile_db, obs_id: str) -> list[LabInterpretation]:
    profile_db.expire_all()
    return list((await profile_db.execute(
        select(LabInterpretation).where(LabInterpretation.observation_id == obs_id)
    )).scalars().all())


async def _panel_rows(profile_db) -> list[PanelInterpretation]:
    profile_db.expire_all()
    return list((await profile_db.execute(select(PanelInterpretation))).scalars().all())


async def _age(profile_db, obs_id: str, created: datetime) -> None:
    await profile_db.execute(
        update(LabInterpretation)
        .where(LabInterpretation.observation_id == obs_id)
        .values(created_at=created)
    )
    await profile_db.commit()


def _blob(row: AuditLog) -> str:
    return " ".join(str(getattr(row, c.name)) for c in row.__table__.columns)


# ---------------------------------------------------------------------------
# Routes, over HTTP
# ---------------------------------------------------------------------------

def _call(profile_db, master, method: str, url: str, *, router=interpretations_router,
          prefix: str = "/interpretations", **kwargs):
    with route_client(router, prefix, profile_id=PROFILE_ID, master_db=master) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        return client.request(method, url, **kwargs)


async def _set_strict(profile_db, value: bool) -> None:
    """Switch the setting through PATCH /assistant/safety-mode, with a throwaway master DB
    so the setting's own audit row never reaches the rows these tests count."""
    master = MagicMock()
    master.commit = AsyncMock()
    resp = _call(profile_db, master, "PATCH", SAFETY_URL, router=assistant_router,
                 prefix="/assistant", json={"strict_safety_mode": value})
    assert resp.status_code == 200, resp.text


def _interp_url(obs_id: str, route: str) -> str:
    return f"/interpretations/observations/{obs_id}/{route}"


def _post_interp(db: Db, obs_id: str, route: str, **kwargs):
    return _call(db.profile, db.master, "POST", _interp_url(obs_id, route), **kwargs)


def _get_interp(db: Db, obs_id: str):
    return _call(db.profile, db.master, "GET", f"/interpretations/observations/{obs_id}/interpretation")


def _panel(db: Db, collected_txt: str):
    return _call(db.profile, db.master, "POST", "/interpretations/panels/lipid/interpret",
                 params={"collected_at": collected_txt})


def _batch(db: Db, ids: list[str], force: bool = False):
    return _call(db.profile, db.master, "POST", "/interpretations/batch",
                 json={"observation_ids": ids, "force_regenerate": force})


def _normalise(value):
    """Mask the ids and timestamps a route generates, so two bodies compare whole."""
    volatile = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$|^\d{4}-\d{2}-\d{2}[T ]"
    )
    if isinstance(value, dict):
        return {k: _normalise(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalise(v) for v in value]
    if isinstance(value, str) and volatile.match(value):
        return "<volatile>"
    return value


# ---------------------------------------------------------------------------
# HC-SMD-001: OFF serves both observations on both POST routes, and OFF bodies are identical
# for the setting absent, false, and a 015-migrated profile.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_hc_smd_001_off_serves_verified_and_unverified_on_post_routes(route):
    async with _dbs() as db:
        for obs_id in db.ids:
            resp = _post_interp(db, obs_id, route)
            assert resp.status_code == 201, resp.text
        rows = await _audit_rows(db.master)
    assert REFUSED_EVENT not in [r.event_type for r in rows]


async def _off_body(route: str, state: str):
    async with _dbs() as db:
        if state == "false":
            await _set_strict(db.profile, False)
        elif state == "migrated_015":
            await _insert_015_row(db.profile)
        assert await A.is_strict_safety_mode(db.profile) is False
        resp = _post_interp(db, db.unverified, route)
    assert resp.status_code == 201, resp.text
    return _normalise(resp.json())


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_hc_smd_001_off_whole_bodies_identical_for_absent_false_and_015(route):
    absent = await _off_body(route, "absent")
    assert await _off_body(route, "false") == absent
    assert await _off_body(route, "migrated_015") == absent


# ---------------------------------------------------------------------------
# HC-SMD-002: ON refuses the unverified observation on both POST routes, with the
# exact 409 shape, generates nothing for it, and still serves the verified one.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_hc_smd_002_on_refuses_unverified_and_serves_verified(route):
    async with _dbs() as db:
        await _set_strict(db.profile, True)
        assert await A.is_strict_safety_mode(db.profile) is True
        refused = _post_interp(db, db.unverified, route)
        served = _post_interp(db, db.verified, route)
        stored = await _interp_rows(db.profile, db.unverified)

    assert refused.status_code == 409, refused.text
    assert refused.json() == {"detail": REFUSAL}
    assert stored == [], "an unverified observation was generated"
    assert served.status_code == 201, served.text


# ---------------------------------------------------------------------------
# HC-SMD-003: a row stored under OFF is not returned under ON with force_regenerate=false.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_smd_003_on_refuses_stored_unverified_row_on_both_post_routes():
    async with _dbs() as db:
        stored = _post_interp(db, db.unverified, "interpret")
        assert stored.status_code == 201, stored.text
        stored_id = stored.json()["id"]

        await _set_strict(db.profile, True)
        for route in ROUTES:
            resp = _post_interp(db, db.unverified, route)
            assert resp.status_code == 409, resp.text
            assert resp.json() == {"detail": REFUSAL}
            assert stored_id not in resp.text, "the stored row was returned"

        rows = await _interp_rows(db.profile, db.unverified)
    assert [r.id for r in rows] == [stored_id], "the refusal must not delete the stored row"


# ---------------------------------------------------------------------------
# HC-SMD-004: GET /interpretation refuses an unverified observation even when a row exists.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_smd_004_on_get_refuses_stored_row_and_does_not_mark_it_viewed():
    async with _dbs() as db:
        created = _post_interp(db, db.unverified, "interpret")
        assert created.status_code == 201, created.text
        stored_id = created.json()["id"]

        await _set_strict(db.profile, True)
        refused = _get_interp(db, db.unverified)
        assert refused.status_code == 409, refused.text
        assert refused.json() == {"detail": REFUSAL}
        assert stored_id not in refused.text
        rows = await _interp_rows(db.profile, db.unverified)
        assert [r.viewed_at for r in rows] == [None], "a refused GET marked the row viewed"

        await _set_strict(db.profile, False)
        served = _get_interp(db, db.unverified)
    assert served.status_code == 200, served.text
    assert served.json()["id"] == stored_id


# ---------------------------------------------------------------------------
# HC-SMD-008: every refusal writes exactly one audit row, with ids and enums only.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_smd_008_observation_refusals_write_one_row_each_without_text():
    async with _dbs() as db:
        await _set_strict(db.profile, True)
        u = db.unverified
        generate = _post_interp(db, u, "interpret")
        grounded = _post_interp(db, u, "interpret-grounded")
        view = _get_interp(db, u)
        rows = await _audit_rows(db.master)

    for resp in (generate, grounded, view):
        assert resp.status_code == 409, resp.text

    # One refusal row per refused request, and nothing else: no "started" or view row.
    assert sorted(r.event_type for r in rows) == [REFUSED_EVENT] * 3
    for row in rows:
        assert row.profile_id == PROFILE_ID
        assert row.entity_type == "observation"
        assert row.entity_id == u
        assert json.loads(row.details_json) == ROW_DETAILS
        blob = _blob(row).lower()
        assert "hdl" not in blob and "cholesterol" not in blob, "analyte text in an audit row"
