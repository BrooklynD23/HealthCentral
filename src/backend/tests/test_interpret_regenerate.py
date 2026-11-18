"""INTERP-REGEN-500 — regenerating an existing interpretation must not 500.

LabInterpretation.observation_id is unique. The regenerate path deleted the old
row and added the new one in a single commit; SQLAlchemy's unit of work emits
the INSERT before the DELETE, so the second POST failed with
`UNIQUE constraint failed: lab_interpretations.observation_id`.

Plan: docs/plans/2026-10-22-mvp-rows-plan.md (INTERP-REGEN-500).

Routes go through HTTP (route_client) against a real in-memory profile DB with
the real schema, so the unique constraint exists. HC-IRG-004 covers the LLM
path (interpret_with_model), which has no route caller yet.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.interpretations as I
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


def _rag_result():
    return SimpleNamespace(
        segments=[], insufficient_context=False, insufficient_reasons=[],
        is_valid=True, validation_errors=[], prohibited_advice=False,
        verification=SimpleNamespace(
            verification_enabled=False, total_claims=0, verified_claims=0,
            failed_claims=0, faithfulness_score=0.0, authority_score=0.0,
            verification_summary="", claims_with_issues=[],
        ),
    )


def _post_twice(profile_db, master_db, url: str):
    with route_client(
        interpretations_router, "/interpretations", profile_id=PROFILE_ID, master_db=master_db
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        first = client.post(url)
        second = client.post(url, params={"force_regenerate": "true"})
        return first, second


async def _rows(profile_db, obs_id) -> list[LabInterpretation]:
    profile_db.expire_all()
    return list((await profile_db.execute(
        select(LabInterpretation).where(LabInterpretation.observation_id == obs_id)
    )).scalars().all())


@pytest.mark.asyncio
async def test_hc_irg_001_template_route_regenerates(dbs):
    profile_db, master_db, obs_id = dbs
    first, second = _post_twice(
        profile_db, master_db, f"/interpretations/observations/{obs_id}/interpret"
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.json()["id"] != first.json()["id"]
    row = (await _rows(profile_db, obs_id))[0]
    assert row.id == second.json()["id"]
    assert row.regeneration_count == 1
    assert row.previous_interpretation_id == first.json()["id"]


@pytest.mark.asyncio
async def test_hc_irg_002_grounded_route_regenerates(dbs):
    profile_db, master_db, obs_id = dbs
    rag = MagicMock()
    rag.query = AsyncMock(return_value=_rag_result())
    with patch.object(I, "get_rag_module", return_value=rag):
        first, second = _post_twice(
            profile_db, master_db,
            f"/interpretations/observations/{obs_id}/interpret-grounded",
        )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    first_id = first.json()["interpretation"]["id"]
    second_id = second.json()["interpretation"]["id"]
    assert second_id != first_id
    row = (await _rows(profile_db, obs_id))[0]
    assert row.id == second_id
    assert row.regeneration_count == 1
    assert row.previous_interpretation_id == first_id


@pytest.mark.asyncio
async def test_hc_irg_003_exactly_one_row_after_regenerate(dbs):
    profile_db, master_db, obs_id = dbs
    first, second = _post_twice(
        profile_db, master_db, f"/interpretations/observations/{obs_id}/interpret"
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert len(await _rows(profile_db, obs_id)) == 1


@pytest.mark.asyncio
async def test_hc_irg_004_model_path_regenerates(dbs):
    profile_db, master_db, obs_id = dbs
    selector = MagicMock()
    selector.get_model_for_inference = AsyncMock(return_value=(object(), "standard"))
    selector.run_inference = AsyncMock(
        return_value={"choices": [{"text": BENIGN_MODEL_TEXT}]}
    )
    module = InterpretModule(model_selector=selector)
    kwargs = dict(
        observation_id=obs_id, profile_id=PROFILE_ID,
        profile_db=profile_db, master_db=master_db,
    )
    first = await module.interpret_with_model(**kwargs)
    assert first.success, first.error_message
    second = await module.interpret_with_model(**kwargs, force_regenerate=True)
    assert second.success, second.error_message
    selector.run_inference.assert_awaited()  # the model path ran, not the template fallback
    rows = await _rows(profile_db, obs_id)
    assert len(rows) == 1
    assert rows[0].regeneration_count == 1
    assert rows[0].previous_interpretation_id == first.interpretation.id
