"""INTERP-WITHHOLD-MSG: a withheld lab card is recorded and the grounded route
answers with the escalation message instead of a bare 500.

Plan: docs/plans/2026-10-15-build-program/lane-B-interpretation-eval.md,
"Delta 2026-10-31 (INTERP-WITHHOLD-MSG: show the withheld message)", Task 1.
Signed gate: INTERP-ENFORCE-DIFF ("Merge, then show message").

HC-IWM-001/002/005: grounded route, 201 withheld answer (no card, no rag.query).
HC-IWM-003/004: plain route, unchanged 500 plus one `interpretation.withheld` row.
HC-IWM-006: `checks_failed` survives the audit allowlist, prose does not.
HC-IWM-007: Task 3 (signed gate OQ-IWM-CRIT), a withheld critical card keeps the
physician-review flag; the value and its reason string are never sent or audited.
HC-IWM-008: positive control, a non-withheld failure keeps the 500 mapping.

Every route test goes through HTTP via tests/support/routes.py::route_client
with a real in-memory master DB (audit rows) and profile DB.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.interpretations as I
import models  # noqa: F401  register every table on both bases
from api.interpretations import router as interpretations_router
from core.audit import _scrub_details
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import LabInterpretation, Observation
from models.audit import AuditLog
from modules.agent.guardrails.templates import ESCALATE_TEMPLATE
from modules.interpret import InterpretationResult, InterpretModule
from modules.interpret_safety import InterpretationSafetyGuard
from tests.support.routes import route_client

PROFILE_ID = "profile-a"  # route_client's default session profile_id
ANALYTE = "ldl"
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)
DOSING_TEXT = (
    "Your LDL is 190 mg/dL [KB:ldl]. You should take 20 mg atorvastatin daily."
)
# Cited, names exactly one disclaimer group ("doctor") and gives no advice, so
# the guard fails it on missing_disclaimers alone (asserted in HC-IWM-002).
ONE_GROUP_TEXT = (
    "Your LDL Cholesterol result is listed as 120 mg/dL [KB:ldl]. "
    "Ask your doctor what it means for you."
)


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


# Copied from tests/test_safe_interp_grounded.py (not imported across modules).
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


async def _cards(profile_db) -> list[LabInterpretation]:
    profile_db.expire_all()
    return list((await profile_db.execute(select(LabInterpretation))).scalars().all())


def _patch_generated_text(text: str):
    return patch.object(
        InterpretModule, "_generate_interpretation", AsyncMock(return_value=(text, None))
    )


def _guard_verdict(text: str):
    """The guard's own verdict for `text`, computed the way the module computes it."""
    guard = InterpretationSafetyGuard()
    final_text, final_advice = guard.add_required_disclaimers(
        interpretation_text=text, advice_text=None
    )
    return guard.validate_interpretation(
        interpretation_text=final_text, advice_text=final_advice, require_citations=True
    )


def _rag_spy():
    """A stand-in RAG module whose query must never run for a withheld card."""
    rag = MagicMock()
    rag.query = AsyncMock()
    return rag


def _grounded_url(obs_id: str, query: str = "") -> str:
    return f"/interpretations/observations/{obs_id}/interpret-grounded{query}"


def _plain_url(obs_id: str, query: str = "") -> str:
    return f"/interpretations/observations/{obs_id}/interpret{query}"


def _grounded_withheld(dbs_tuple, text: str, caplog=None):
    profile_db, master_db, obs_id = dbs_tuple
    rag = _rag_spy()
    with _patch_generated_text(text), \
            patch.object(I, "get_rag_module", return_value=rag), \
            patch.object(I, "get_strict_rag_module", return_value=rag):
        resp = _call(profile_db, master_db, "POST", _grounded_url(obs_id))
    return resp, rag


def _assert_withheld_answer(resp, rag):
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["withheld"] is True
    assert body["interpretation"] is None
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert [(s["segment_type"], s["content"]) for s in body["grounded_segments"]] == [
        ("uncertainty", ESCALATE_TEMPLATE)
    ]
    assert body["is_valid"] is False
    rag.query.assert_not_awaited()


def _assert_withheld_row(
    row: AuditLog, obs_id: str, expected_checks: list[str], status: str | None = None
):
    """Ids and check type names only, no prose. `status` is "completed" when the
    row closes a regenerate's `started` row, and absent on a first generate."""
    assert row.event_type == "interpretation.withheld"
    assert row.profile_id == PROFILE_ID
    assert row.entity_type == "observation"
    assert row.entity_id == obs_id
    expected = {
        "reason": "safety_check_failed", "decision": "escalate", "checks_failed": expected_checks,
    }
    if status is not None:
        expected["status"] = status
    assert json.loads(row.details_json) == expected
    blob = _row_blob(row).lower()
    for leaked in ("atorvastatin", "ldl", "cholesterol", "mg/dl", "120.0", "20 mg", "ask your doctor"):
        assert leaked not in blob, leaked


async def _assert_one_withheld_row(master_db, obs_id: str, expected_checks: list[str]):
    """First generate writes no `started` row, so the withheld row stands alone."""
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == ["interpretation.withheld"]
    _assert_withheld_row(rows[0], obs_id, expected_checks)


# ──────────────────────────────────────────────────────────────────────────────
# HC-IWM-001 / HC-IWM-002: grounded route answers 201 with the escalation message
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hc_iwm_001_grounded_route_answers_withheld_card_with_message(dbs, caplog):
    caplog.set_level(logging.DEBUG)
    profile_db, master_db, obs_id = dbs
    resp, rag = _grounded_withheld(dbs, DOSING_TEXT)
    _assert_withheld_answer(resp, rag)
    assert await _cards(profile_db) == []
    assert "atorvastatin" not in resp.text.lower()
    assert "atorvastatin" not in caplog.text.lower()
    await _assert_one_withheld_row(master_db, obs_id, _guard_verdict(DOSING_TEXT).checks_failed)

    # Same withhold decision at the model-path site (no route caller today):
    # the result must carry withheld=True there too (recurring-failures #9).
    selector = MagicMock()
    selector.get_model_for_inference = AsyncMock(return_value=(object(), "standard"))
    selector.run_inference = AsyncMock(return_value={"choices": [{"text": DOSING_TEXT}]})
    model_result = await InterpretModule(model_selector=selector).interpret_with_model(
        observation_id=obs_id, profile_id=PROFILE_ID,
        profile_db=profile_db, master_db=master_db,
    )
    selector.run_inference.assert_awaited()
    assert model_result.success is False
    assert model_result.withheld is True


@pytest.mark.asyncio
async def test_hc_iwm_002_grounded_route_disclaimer_only_failure_is_withheld(dbs, caplog):
    caplog.set_level(logging.DEBUG)
    profile_db, master_db, obs_id = dbs
    # Precondition (HC-ISE-002): this exact text is a disclaimer-only failure.
    assert _guard_verdict(ONE_GROUP_TEXT).checks_failed == ["missing_disclaimers"]

    resp, rag = _grounded_withheld(dbs, ONE_GROUP_TEXT)
    _assert_withheld_answer(resp, rag)
    assert await _cards(profile_db) == []
    assert "what it means for you" not in resp.text
    assert "what it means for you" not in caplog.text
    await _assert_one_withheld_row(master_db, obs_id, ["missing_disclaimers"])


# ──────────────────────────────────────────────────────────────────────────────
# HC-IWM-003 / HC-IWM-004: plain route keeps its 500 and writes the audit row
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hc_iwm_003_plain_route_500_unchanged_and_one_withheld_audit_row(dbs):
    profile_db, master_db, obs_id = dbs
    expected = _guard_verdict(DOSING_TEXT).checks_failed
    assert expected, "precondition: the guard must fail the dosing text"

    with _patch_generated_text(DOSING_TEXT):
        resp = _call(profile_db, master_db, "POST", _plain_url(obs_id))
    assert resp.status_code == 500, resp.text
    assert resp.json()["detail"] == ESCALATE_TEMPLATE

    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == ["interpretation.withheld"]
    (row,) = rows
    assert row.profile_id == PROFILE_ID
    assert row.entity_type == "observation"
    assert row.entity_id == obs_id
    assert json.loads(row.details_json) == {
        "reason": "safety_check_failed", "decision": "escalate", "checks_failed": expected,
    }
    blob = _row_blob(row).lower()
    for leaked in ("atorvastatin", "ldl", "cholesterol", "mg/dl", "120.0", "20 mg"):
        assert leaked not in blob, leaked


@pytest.mark.asyncio
async def test_hc_iwm_004_plain_regenerate_withhold_closes_the_started_row(dbs):
    profile_db, master_db, obs_id = dbs
    first = _call(profile_db, master_db, "POST", _plain_url(obs_id))
    assert first.status_code == 201, first.text
    (old,) = await _cards(profile_db)
    old_id, old_text, old_count = old.id, old.interpretation_text, old.regeneration_count
    before = len(await _audit_rows(master_db))

    with _patch_generated_text(DOSING_TEXT):
        resp = _call(profile_db, master_db, "POST", _plain_url(obs_id, "?force_regenerate=true"))
    assert resp.status_code == 500, resp.text
    assert resp.json()["detail"] == ESCALATE_TEMPLATE

    rows = (await _audit_rows(master_db))[before:]
    assert [(r.event_type, json.loads(r.details_json)["status"]) for r in rows] == [
        ("interpretation.generate", "started"),
        ("interpretation.withheld", "completed"),
    ]
    _assert_withheld_row(
        rows[1], obs_id, _guard_verdict(DOSING_TEXT).checks_failed, status="completed"
    )
    (kept,) = await _cards(profile_db)
    assert (kept.id, kept.interpretation_text, kept.regeneration_count) == (
        old_id, old_text, old_count,
    )


# ──────────────────────────────────────────────────────────────────────────────
# HC-IWM-005: grounded regenerate closes the started row too
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hc_iwm_005_grounded_regenerate_withhold_closes_the_started_row(dbs):
    profile_db, master_db, obs_id = dbs
    first = _call(profile_db, master_db, "POST", _plain_url(obs_id))
    assert first.status_code == 201, first.text
    (old,) = await _cards(profile_db)
    old_id, old_text = old.id, old.interpretation_text
    before = len(await _audit_rows(master_db))

    rag = _rag_spy()
    with _patch_generated_text(DOSING_TEXT), \
            patch.object(I, "get_rag_module", return_value=rag), \
            patch.object(I, "get_strict_rag_module", return_value=rag):
        resp = _call(profile_db, master_db, "POST", _grounded_url(obs_id, "?force_regenerate=true"))
    _assert_withheld_answer(resp, rag)

    rows = (await _audit_rows(master_db))[before:]
    assert [(r.event_type, json.loads(r.details_json)["status"]) for r in rows] == [
        ("interpretation.grounded", "started"),
        ("interpretation.withheld", "completed"),
    ]
    _assert_withheld_row(
        rows[1], obs_id, _guard_verdict(DOSING_TEXT).checks_failed, status="completed"
    )
    (kept,) = await _cards(profile_db)
    assert (kept.id, kept.interpretation_text) == (old_id, old_text)


# ──────────────────────────────────────────────────────────────────────────────
# HC-IWM-006: the audit allowlist keeps check type names and nothing else
# ──────────────────────────────────────────────────────────────────────────────


def test_hc_iwm_006_checks_failed_survives_scrub_but_prose_does_not():
    kept = _scrub_details(
        {"checks_failed": ["prohibited_dosing_recommendation", "missing_disclaimers"]}
    )
    assert kept == {"checks_failed": ["prohibited_dosing_recommendation", "missing_disclaimers"]}

    dropped = _scrub_details({"checks_failed": ["take 500 mg daily"]})
    assert dropped == {"_scrubbed": 1}


# ──────────────────────────────────────────────────────────────────────────────
# HC-IWM-007: a withheld card still reports "a clinician should review this"
# ──────────────────────────────────────────────────────────────────────────────

# potassium's default critical_high is 6.5 (InterpretationSafetyGuard). The value
# strings cannot occur in the analyte name, the fixed text or the escalation text.
CRITICAL_VALUE = 7.35
NORMAL_VALUE = 4.15


async def _make_potassium(profile_db, obs_id: str, value: float) -> None:
    obs = (
        await profile_db.execute(select(Observation).where(Observation.id == obs_id))
    ).scalar_one()
    obs.analyte_canonical = "potassium"
    obs.analyte_raw = "Potassium"
    obs.value = value
    obs.unit = "mmol/L"
    obs.ref_low = 3.5
    obs.ref_high = 5.0
    await profile_db.commit()


def _assert_value_and_reason_not_sent(resp, rows: list[AuditLog], caplog, value: float):
    value_str = str(value)
    assert value_str not in ESCALATE_TEMPLATE
    assert value_str not in DOSING_TEXT
    assert value_str not in resp.text
    for phrase in ("Critical high value", "Critical low value", "critical threshold", "threshold of"):
        assert phrase.lower() not in resp.text.lower(), phrase
    for row in rows:
        blob = _row_blob(row)
        assert value_str not in blob
        for phrase in ("Critical high value", "Critical low value", "threshold of"):
            assert phrase.lower() not in blob.lower(), phrase
    for record in caplog.records:
        assert value_str not in record.getMessage()
        assert value_str not in str(record.args)


@pytest.mark.asyncio
async def test_hc_iwm_007_withheld_critical_card_keeps_the_physician_review_flag(dbs, caplog):
    caplog.set_level(logging.DEBUG)
    profile_db, master_db, obs_id = dbs
    await _make_potassium(profile_db, obs_id, CRITICAL_VALUE)
    caplog.clear()  # the seeding UPDATE's own driver DEBUG line carries the value

    resp, rag = _grounded_withheld(dbs, DOSING_TEXT)
    _assert_withheld_answer(resp, rag)
    assert resp.json().get("withheld_physician_review") is True
    assert await _cards(profile_db) == []
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == ["interpretation.withheld"]
    _assert_withheld_row_ids_only(rows[0], obs_id)
    _assert_value_and_reason_not_sent(resp, rows, caplog, CRITICAL_VALUE)

    # The model-path site (no route caller today) reorders the same check.
    selector = MagicMock()
    selector.get_model_for_inference = AsyncMock(return_value=(object(), "standard"))
    selector.run_inference = AsyncMock(return_value={"choices": [{"text": DOSING_TEXT}]})
    model_result = await InterpretModule(model_selector=selector).interpret_with_model(
        observation_id=obs_id, profile_id=PROFILE_ID,
        profile_db=profile_db, master_db=master_db,
    )
    selector.run_inference.assert_awaited()
    assert model_result.withheld is True
    assert model_result.safety_validation.requires_physician_review is True
    assert await _cards(profile_db) == []
    for record in caplog.records:
        assert str(CRITICAL_VALUE) not in record.getMessage()
        assert str(CRITICAL_VALUE) not in str(record.args)


@pytest.mark.asyncio
async def test_hc_iwm_007_withheld_non_critical_card_has_no_physician_review_flag(dbs, caplog):
    caplog.set_level(logging.DEBUG)
    profile_db, master_db, obs_id = dbs
    await _make_potassium(profile_db, obs_id, NORMAL_VALUE)
    caplog.clear()

    resp, rag = _grounded_withheld(dbs, DOSING_TEXT)
    _assert_withheld_answer(resp, rag)
    assert resp.json().get("withheld_physician_review") is False
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == ["interpretation.withheld"]
    _assert_value_and_reason_not_sent(resp, rows, caplog, NORMAL_VALUE)


def _assert_withheld_row_ids_only(row: AuditLog, obs_id: str):
    assert row.event_type == "interpretation.withheld"
    assert row.entity_id == obs_id
    assert set(json.loads(row.details_json)) == {"reason", "decision", "checks_failed"}


# ──────────────────────────────────────────────────────────────────────────────
# HC-IWM-008: positive control, only a withheld result gets the new answer
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hc_iwm_008_non_withheld_failure_keeps_the_500_mapping(dbs):
    profile_db, master_db, obs_id = dbs
    # "boom" is an ordinary failure; the second message is the escalation string
    # on a result that is NOT flagged withheld: the route keys on the flag, never
    # on the error_message string.
    for message in ("boom", ESCALATE_TEMPLATE):
        failed = InterpretationResult(success=False, error_message=message)
        rag = _rag_spy()
        with patch.object(InterpretModule, "interpret_observation", AsyncMock(return_value=failed)), \
                patch.object(I, "get_rag_module", return_value=rag), \
                patch.object(I, "get_strict_rag_module", return_value=rag):
            resp = _call(profile_db, master_db, "POST", _grounded_url(obs_id))
        assert resp.status_code == 500, (message, resp.text)
        assert resp.json()["detail"] == message
        rag.query.assert_not_awaited()
        assert "interpretation.withheld" not in [
            r.event_type for r in await _audit_rows(master_db)
        ]

    # Same control on the plain route: an unflagged failure, even one carrying
    # the escalation string, keeps its 500 and writes no withheld row.
    for message in ("boom", ESCALATE_TEMPLATE):
        failed = InterpretationResult(success=False, error_message=message)
        with patch.object(InterpretModule, "interpret_observation", AsyncMock(return_value=failed)):
            resp = _call(profile_db, master_db, "POST", _plain_url(obs_id))
        assert resp.status_code == 500, (message, resp.text)
        assert resp.json()["detail"] == message
        assert "interpretation.withheld" not in [
            r.event_type for r in await _audit_rows(master_db)
        ]
