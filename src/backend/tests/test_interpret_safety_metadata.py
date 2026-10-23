"""INTERP-SAFETY-META — the stored safety_validation_json describes the text
that ships.

Disclaimers are appended to the interpretation, so the safety check must run on
that final text. Before the fix the check ran first and recorded
`missing_disclaimers` (passed=false) for text that shipped with them.

Plan: docs/plans/2026-10-15-build-program/lane-B-interpretation-eval.md
Gate INTERP-DISC-ORDER (a) "Check the final text".

HC-ISV-003 is green by design: a prohibited sentence must still fail the check.
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

import models  # noqa: F401  register every table on both bases
from api.interpretations import router as interpretations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import LabInterpretation, Observation
from modules.interpret import InterpretModule
from tests.support.routes import route_client

PROFILE_ID = "profile-a"  # route_client's default session profile_id
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)
BENIGN_MODEL_TEXT = (
    "Your LDL Cholesterol result is listed as 120 mg/dL, within the reference "
    "range shown on your report [KB:ldl]."
)
DOSING_TEXT = (
    "Your LDL is 190 mg/dL [KB:ldl]. You should take 20 mg atorvastatin daily."
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
        analyte_canonical="ldl", analyte_raw="LDL Cholesterol", value=120.0,
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


async def _post_interpret(profile_db, master_db, obs_id):
    with route_client(
        interpretations_router, "/interpretations", profile_id=PROFILE_ID, master_db=master_db
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.post(f"/interpretations/observations/{obs_id}/interpret")


async def _stored_safety(profile_db) -> dict:
    profile_db.expire_all()
    rows = (await profile_db.execute(select(LabInterpretation))).scalars().all()
    assert len(rows) == 1
    return json.loads(rows[0].safety_validation_json)


def _assert_disclaimers_recorded(safety: dict) -> None:
    assert safety["passed"] is True, safety
    assert "has_required_disclaimers" in safety["checks_passed"], safety
    assert "missing_disclaimers" not in safety["checks_failed"], safety


@pytest.mark.asyncio
async def test_hc_isv_001_template_route_records_disclaimers_present(dbs):
    profile_db, master_db, obs_id = dbs
    resp = await _post_interpret(profile_db, master_db, obs_id)
    assert resp.status_code == 201, resp.text
    _assert_disclaimers_recorded(await _stored_safety(profile_db))


@pytest.mark.asyncio
async def test_hc_isv_002_model_path_records_disclaimers_present(dbs):
    profile_db, master_db, obs_id = dbs
    selector = MagicMock()
    selector.get_model_for_inference = AsyncMock(return_value=(object(), "standard"))
    selector.run_inference = AsyncMock(
        return_value={"choices": [{"text": BENIGN_MODEL_TEXT}]}
    )
    module = InterpretModule(model_selector=selector)
    result = await module.interpret_with_model(
        observation_id=obs_id, profile_id=PROFILE_ID,
        profile_db=profile_db, master_db=master_db,
    )
    assert result.success, result.error_message
    selector.run_inference.assert_awaited()  # the model path ran, not the template fallback
    _assert_disclaimers_recorded(await _stored_safety(profile_db))


@pytest.mark.asyncio
async def test_hc_isv_003_template_path_dosing_text_still_fails(dbs):
    profile_db, master_db, obs_id = dbs
    with patch.object(
        InterpretModule, "_generate_interpretation",
        AsyncMock(return_value=(DOSING_TEXT, None)),
    ):
        resp = await _post_interpret(profile_db, master_db, obs_id)
    assert resp.status_code == 201, resp.text
    safety = await _stored_safety(profile_db)
    assert safety["passed"] is False, safety
    assert any(c.startswith("prohibited_") for c in safety["checks_failed"]), safety
