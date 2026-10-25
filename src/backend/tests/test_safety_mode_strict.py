"""SAFETY-MODE-STRICT: a profile's strict safety mode raises the legacy RAG
verification bar from 0.6 to STRICT_MIN_SCORE (0.75) on the chat legacy path
and on interpret-grounded. OFF is today's behaviour; ON is only ever stricter.

Plan: docs/plans/2026-10-24-safety-mode-build-plan.md (SAFETY-MODE-STRICT).

HTTP tests go through tests/support/routes.py::route_client with a real
in-memory master DB (audit rows) and a real in-memory profile DB. The setting
is switched on through PATCH /assistant/safety-mode. Modules come from the
production factories (get_rag_module, get_strict_rag_module), so their
thresholds are the real ones. Stubs sit below rag.query: retrieval and
generation only. HC-SMA-006 also runs the real verification pipeline.
"""

from __future__ import annotations

import json
import re
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as A
import api.interpretations as I
import models  # noqa: F401  register every table on both bases
from api.assistant import ResponseSegment, VerificationInfo
from api.assistant import router as assistant_router
from api.interpretations import GroundedVerificationResponse
from api.interpretations import router as interpretations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import Observation
from models.audit import AuditLog
from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE
from modules.rag import RetrievedChunk, VerificationMetadata
from tests.legacy_eval.harness import build_chunks
from tests.support.routes import route_client

PROFILE_ID = "profile-a"  # route_client's default session profile_id
ANALYTE = "ldl"
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)
QUESTION = "what is my ldl?"
CHAT_URL = "/assistant/chat"
STATUS_URL = "/assistant/verification-status"
SAFETY_URL = "/assistant/safety-mode"

SERVED = "SMA-SERVED-7d21"
SERVED_ANSWER = f"REPORT FACTS:\nYour LDL result is listed as 120 mg/dL [cite:1]. {SERVED}"
PROHIBITED = "SMA-PROHIBITED-b40e"
PROHIBITED_ANSWER = (
    "REPORT FACTS:\nYour LDL is 190 mg/dL [cite:1].\n\n"
    "IMPLICATIONS:\nThis means you have hyperlipidemia and you should take "
    f"20 mg atorvastatin daily {PROHIBITED}."
)
# HC-SMA-006: the real pipeline scores this at 0.662 (both claims verified, no
# failed claims). The test asserts that number, so fixture drift fails loudly.
GLUCOSE_ANSWER = (
    "REPORT FACTS:\nYour glucose was 95 mg/dL [cite:1].\n\n"
    "GENERAL INFO:\nFasting glucose values are often discussed with a reference interval, "
    "and the typical range is roughly 70 to 100 mg/dL [cite:2]."
)
AGENT_TEXT = "SMA-AGENT-3f9a"

_VOLATILE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$|^\d{4}-\d{2}-\d{2}[T ]"
)

# A profile that existed at 015_data_donation. Its row predates the 016 column,
# so strict_safety_mode takes the column's server default ("0"); no ORM default runs.
_INSERT_015_ROW = text(
    "INSERT INTO user_model_settings (id, profile_id, preferred_tier, auto_detect_enabled, "
    "use_external_api, external_api_provider, external_api_key_encrypted, timezone, "
    "voice_logging_enabled, voice_modal_seen, ocr_preference_enabled, assistant_memory_enabled, "
    "created_at, updated_at) VALUES (:id, :pid, 'low', 1, 0, '', '', 'UTC', 0, 0, 1, 1, "
    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
)


@pytest.fixture(autouse=True)
def _fresh_rag_singletons(monkeypatch):
    """The factories cache one module each. Every test builds its own."""
    monkeypatch.setattr(A, "_rag_module", None, raising=False)
    monkeypatch.setattr(A, "_strict_rag_module", None, raising=False)


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


@asynccontextmanager
async def _dbs(*, observation: bool = True):
    """A fresh profile DB and master DB. Yields (profile_db, master_db, observation_id)."""
    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    try:
        obs_id = None
        if observation:
            obs = Observation(
                id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
                analyte_canonical=ANALYTE, analyte_raw="LDL Cholesterol", value=120.0,
                unit="mg/dL", ref_low=0.0, ref_high=130.0, collected_at=COLLECTED,
            )
            profile_db.add(obs)
            await profile_db.commit()
            obs_id = obs.id
        yield profile_db, master_db, obs_id
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


def _blob(row: AuditLog) -> str:
    return " ".join(str(getattr(row, c.name)) for c in row.__table__.columns)


# ---------------------------------------------------------------------------
# Modules: production factories, stubbed below rag.query
# ---------------------------------------------------------------------------

def _ldl_chunks() -> list[RetrievedChunk]:
    return [RetrievedChunk(
        chunk_id="c1", source_type="reference", doc_id=None, doc_title="LDL reference",
        page=None, text="LDL cholesterol reference text.", relevance_score=0.9,
    )]


def _verification(score: float, *, failed: int = 0) -> VerificationMetadata:
    return VerificationMetadata(
        verification_enabled=True, total_claims=1, verified_claims=1 - failed,
        failed_claims=failed, claims_with_issues=[], faithfulness_score=score,
        authority_score=0.5, verification_summary="stub",
    )


def _module(factory, answer: str, verification: VerificationMetadata | None = None, *,
            chunks=None, real_pipeline: bool = False):
    """Build a module with the production factory, then stub retrieval and
    generation. The verification pipeline is stubbed unless real_pipeline."""
    with patch("modules.rag.get_model_runner") as runner, patch("modules.rag.EmbeddingsModule"):
        runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        rag = factory()
    rag.retrieve_context = AsyncMock(return_value=chunks if chunks is not None else _ldl_chunks())
    rag._generate_with_runner = AsyncMock(return_value=answer)
    if not real_pipeline:
        rag._run_verification_pipeline = MagicMock(return_value=verification)
    return rag


@contextmanager
def _route_modules(module, off, on):
    """Chat (module A) or interpret-grounded (module I). The default factory
    returns `off`, the strict factory returns `on`. A route that picks the
    wrong one serves a different body, so the test fails."""
    with patch.object(module, "get_rag_module", return_value=off), \
         patch.object(module, "get_strict_rag_module", return_value=on, create=True):
        yield


# ---------------------------------------------------------------------------
# Routes, over HTTP
# ---------------------------------------------------------------------------

def _set_strict(profile_db, value: bool) -> None:
    """Switch the setting through PATCH /assistant/safety-mode, with its own master DB."""
    master = MagicMock()
    master.commit = AsyncMock()
    with route_client(assistant_router, "/assistant", profile_id=PROFILE_ID, master_db=master) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        resp = client.patch(SAFETY_URL, json={"strict_safety_mode": value})
    assert resp.status_code == 200, resp.text


def _chat(profile_db, master):
    with route_client(assistant_router, "/assistant", profile_id=PROFILE_ID, master_db=master) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        return client.post(CHAT_URL, json={"question": QUESTION})


def _interp(profile_db, master, obs_id):
    with route_client(interpretations_router, "/interpretations", profile_id=PROFILE_ID, master_db=master) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        return client.post(f"/interpretations/observations/{obs_id}/interpret-grounded")


def _status(profile_db, master):
    with route_client(assistant_router, "/assistant", profile_id=PROFILE_ID, master_db=master) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        return client.get(STATUS_URL)


def _serve(route: str, profile_db, master, obs_id, off, on=None):
    """The legacy chat path (agent disabled) or interpret-grounded, with the
    module factories routed to the given stubs. OFF calls pass no strict stub,
    so a route that builds the strict module while OFF is caught by a None."""
    if route == "chat":
        with _route_modules(A, off, on), patch.object(A, "is_agent_enabled", return_value=False):
            return _chat(profile_db, master)
    with _route_modules(I, off, on):
        return _interp(profile_db, master, obs_id)


def _normalise(value):
    """Mask the ids and timestamps a route generates, so two bodies compare whole."""
    if isinstance(value, dict):
        return {k: _normalise(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalise(v) for v in value]
    if isinstance(value, str) and _VOLATILE.match(value):
        return "<volatile>"
    return value


# ---------------------------------------------------------------------------
# HC-SMA-001: chat legacy path, faithfulness 0.70 is served when OFF and withheld when ON
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_sma_001_chat_legacy_withholds_0_70_only_when_strict_on():
    off = _module(A.get_rag_module, SERVED_ANSWER, _verification(0.70))
    async with _dbs(observation=False) as (profile_db, master, _):
        resp_off = _serve("chat", profile_db, master, None, off)
        _set_strict(profile_db, True)
        assert await A.is_strict_safety_mode(profile_db) is True
        on = _module(A.get_strict_rag_module, SERVED_ANSWER, _verification(0.70))
        resp_on = _serve("chat", profile_db, master, None, off, on)

    assert resp_off.status_code == 200, resp_off.text
    assert resp_off.json()["is_valid"] is True
    assert SERVED in resp_off.json()["full_response"]

    assert resp_on.status_code == 200, resp_on.text
    body = resp_on.json()
    assert body["is_valid"] is False
    assert [s["content"] for s in body["segments"]] == [ABSTAIN_TEMPLATE]
    assert SERVED not in json.dumps(body)


# ---------------------------------------------------------------------------
# HC-SMA-002: interpret-grounded, same stub. ON abstains and writes one strict audit row.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_sma_002_interpret_grounded_abstains_with_one_strict_audit_row():
    off = _module(A.get_rag_module, SERVED_ANSWER, _verification(0.70))

    async with _dbs() as (profile_db, master, obs_id):
        resp_off = _serve("interpret", profile_db, master, obs_id, off)
        assert resp_off.status_code == 201, resp_off.text
        assert resp_off.json()["is_valid"] is True
        assert SERVED in resp_off.json()["full_response"]
        assert [r.event_type for r in await _audit_rows(master)] == ["interpretation.grounded"]

    async with _dbs() as (profile_db, master, obs_id):
        _set_strict(profile_db, True)
        assert await A.is_strict_safety_mode(profile_db) is True
        on = _module(A.get_strict_rag_module, SERVED_ANSWER, _verification(0.70))
        resp_on = _serve("interpret", profile_db, master, obs_id, off, on)
        assert resp_on.status_code == 201, resp_on.text
        body = resp_on.json()
        assert SERVED not in json.dumps(body), "withheld text reached the client"
        assert [s["content"] for s in body["grounded_segments"]] == [ABSTAIN_TEMPLATE]
        assert body["full_response"] == ABSTAIN_TEMPLATE
        assert body["verification"] == GroundedVerificationResponse().model_dump()
        assert body["is_valid"] is False

        rows = await _audit_rows(master)
        assert sorted(r.event_type for r in rows) == [
            "interpretation.grounded", "interpretation.strict_abstained",
        ]
        strict = [r for r in rows if r.event_type == "interpretation.strict_abstained"]
        assert len(strict) == 1
        assert strict[0].profile_id == PROFILE_ID
        blob = _blob(strict[0])
        assert SERVED not in blob and "Explain my lab result" not in blob
        assert ANALYTE not in blob.lower()
        assert json.loads(strict[0].details_json) == {
            "reason": "strict_validation_failed", "decision": "abstain",
        }


# ---------------------------------------------------------------------------
# HC-SMA-003: faithfulness 0.50 is withheld on the chat path in both modes.
# interpret-grounded OFF still serves the segments with is_valid false (today).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_sma_003_faithfulness_0_50_withheld_on_chat_in_both_modes():
    off = _module(A.get_rag_module, SERVED_ANSWER, _verification(0.50))
    async with _dbs(observation=False) as (profile_db, master, _):
        resp_off = _serve("chat", profile_db, master, None, off)
    assert resp_off.status_code == 200, resp_off.text
    assert SERVED not in json.dumps(resp_off.json())
    assert [s["content"] for s in resp_off.json()["segments"]] == [ABSTAIN_TEMPLATE]

    async with _dbs(observation=False) as (profile_db, master, _):
        _set_strict(profile_db, True)
        on = _module(A.get_strict_rag_module, SERVED_ANSWER, _verification(0.50))
        resp_on = _serve("chat", profile_db, master, None, off, on)
    assert resp_on.status_code == 200, resp_on.text
    assert SERVED not in json.dumps(resp_on.json())
    assert [s["content"] for s in resp_on.json()["segments"]] == [ABSTAIN_TEMPLATE]


@pytest.mark.asyncio
async def test_hc_sma_003_interpret_grounded_off_serves_invalid_on_withholds():
    off = _module(A.get_rag_module, SERVED_ANSWER, _verification(0.50))

    async with _dbs() as (profile_db, master, obs_id):
        resp_off = _serve("interpret", profile_db, master, obs_id, off)
        assert resp_off.status_code == 201, resp_off.text
        assert resp_off.json()["is_valid"] is False
        assert SERVED in json.dumps(resp_off.json()["grounded_segments"])

    async with _dbs() as (profile_db, master, obs_id):
        _set_strict(profile_db, True)
        on = _module(A.get_strict_rag_module, SERVED_ANSWER, _verification(0.50))
        resp_on = _serve("interpret", profile_db, master, obs_id, off, on)
        assert resp_on.status_code == 201, resp_on.text
        assert [s["content"] for s in resp_on.json()["grounded_segments"]] == [ABSTAIN_TEMPLATE]
        assert SERVED not in json.dumps(resp_on.json())


# ---------------------------------------------------------------------------
# HC-SMA-004: a prohibited answer under ON still escalates, with one block row and no strict row.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("route", "status_code", "expected_events"),
    [
        ("chat", 200, ["assistant.prohibited_blocked"]),
        ("interpret", 201, ["interpretation.grounded", "interpretation.prohibited_blocked"]),
    ],
)
async def test_hc_sma_004_prohibited_under_strict_escalates_with_one_block_row(
    route, status_code, expected_events,
):
    off = _module(A.get_rag_module, PROHIBITED_ANSWER, _verification(0.90))
    async with _dbs() as (profile_db, master, obs_id):
        _set_strict(profile_db, True)
        assert await A.is_strict_safety_mode(profile_db) is True
        on = _module(A.get_strict_rag_module, PROHIBITED_ANSWER, _verification(0.90))
        resp = _serve(route, profile_db, master, obs_id, off, on)
        rows = await _audit_rows(master)

    assert resp.status_code == status_code, resp.text
    body = resp.json()
    assert PROHIBITED not in json.dumps(body), "prohibited answer text reached the client"
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert sorted(r.event_type for r in rows) == sorted(expected_events)
    assert not [r for r in rows if "strict" in r.event_type]
    blocked = [r for r in rows if r.event_type.endswith("prohibited_blocked")]
    assert len(blocked) == 1
    assert json.loads(blocked[0].details_json) == {
        "reason": "prohibited_pattern", "decision": "escalate",
    }


# ---------------------------------------------------------------------------
# HC-SMA-005: OFF bodies are identical for the setting absent, false, and a 015-migrated profile.
# ---------------------------------------------------------------------------

async def _off_body(route: str, state: str):
    off = _module(A.get_rag_module, SERVED_ANSWER, _verification(0.70))
    async with _dbs() as (profile_db, master, obs_id):
        if state == "false":
            _set_strict(profile_db, False)
        elif state == "migrated_015":
            await _insert_015_row(profile_db)
        assert await A.is_strict_safety_mode(profile_db) is False
        resp = _serve(route, profile_db, master, obs_id, off)
    assert resp.status_code in (200, 201), resp.text
    assert SERVED in json.dumps(resp.json()), "OFF must serve the answer"
    return _normalise(resp.json())


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["chat", "interpret"])
async def test_hc_sma_005_off_whole_bodies_identical_for_absent_false_and_015(route):
    absent = await _off_body(route, "absent")
    assert await _off_body(route, "false") == absent
    assert await _off_body(route, "migrated_015") == absent


# ---------------------------------------------------------------------------
# HC-SMA-006: real verification pipeline. Only retrieval and generation are stubbed.
# The glucose answer scores between 0.6 and 0.75: served when OFF, withheld when ON.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("route", "status_code"),
    [("chat", 200), ("interpret", 201)],
)
async def test_hc_sma_006_real_pipeline_band_0_6_to_0_75_served_off_withheld_on(route, status_code):
    off = _module(A.get_rag_module, GLUCOSE_ANSWER, chunks=build_chunks("glucose"), real_pipeline=True)

    async with _dbs() as (profile_db, master, obs_id):
        resp_off = _serve(route, profile_db, master, obs_id, off)
    assert resp_off.status_code == status_code, resp_off.text
    body_off = resp_off.json()
    score = body_off["verification"]["faithfulness_score"]
    assert 0.6 <= score < 0.75, f"fixture left the band: {score}"
    assert body_off["is_valid"] is True
    assert "95 mg/dL" in body_off["full_response"]

    async with _dbs() as (profile_db, master, obs_id):
        _set_strict(profile_db, True)
        assert await A.is_strict_safety_mode(profile_db) is True
        on = _module(A.get_strict_rag_module, GLUCOSE_ANSWER, chunks=build_chunks("glucose"), real_pipeline=True)
        resp_on = _serve(route, profile_db, master, obs_id, off, on)
    assert resp_on.status_code == status_code, resp_on.text
    body_on = resp_on.json()
    assert body_on["is_valid"] is False
    assert "95 mg/dL" not in json.dumps(body_on)
    segments = body_on["segments"] if route == "chat" else body_on["grounded_segments"]
    assert [s["content"] for s in segments] == [ABSTAIN_TEMPLATE]


# ---------------------------------------------------------------------------
# HC-SMA-007: the default agent path returns the same body whether ON or OFF.
# The agent graph is stubbed at _serve_via_agent. Neither legacy module runs.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_sma_007_default_agent_path_identical_on_and_off():
    async def _agent_body(strict: bool):
        off, on = MagicMock(), MagicMock()
        off.query, on.query = AsyncMock(), AsyncMock()
        agent = AsyncMock(return_value=(
            [ResponseSegment(segment_type="report_facts", content=AGENT_TEXT)],
            AGENT_TEXT,
            VerificationInfo(),
        ))
        async with _dbs(observation=False) as (profile_db, master, _):
            if strict:
                _set_strict(profile_db, True)
            assert await A.is_strict_safety_mode(profile_db) is strict
            with _route_modules(A, off, on), patch.object(A, "_serve_via_agent", agent):
                resp = _chat(profile_db, master)
        off.query.assert_not_awaited()
        on.query.assert_not_awaited()
        agent.assert_awaited_once()
        assert resp.status_code == 200, resp.text
        assert AGENT_TEXT in resp.json()["full_response"]
        return _normalise(resp.json())

    assert await _agent_body(strict=True) == await _agent_body(strict=False)


# ---------------------------------------------------------------------------
# HC-SMA-008: GET /assistant/verification-status reports the profile's threshold and audits each read.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_sma_008_verification_status_reports_threshold_and_audits_each_read():
    async with _dbs(observation=False) as (profile_db, master, _):
        with patch.object(A, "get_rag_module", return_value=MagicMock(enable_verification=True)):
            resp_off = _status(profile_db, master)
            assert resp_off.status_code == 200, resp_off.text
            assert resp_off.json()["configuration"]["min_faithfulness_score"] == 0.6

            _set_strict(profile_db, True)
            resp_on = _status(profile_db, master)
            assert resp_on.status_code == 200, resp_on.text
            assert resp_on.json()["configuration"]["min_faithfulness_score"] == 0.75

        rows = await _audit_rows(master)

    assert sorted(r.action for r in rows) == ["verification_status_viewed"] * 2
    for row in rows:
        assert row.profile_id == PROFILE_ID
        assert row.details_json is None
