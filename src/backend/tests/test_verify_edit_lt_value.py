"""VERIFY-EDIT-LT-VALUE: a value_text-only verify edit no longer leaves the old number.

A {"value_text": "<0.5"} edit used to update value_text and keep the stale
value, so the old number read as checked and a flag could be computed from it
(an unflagged 18.0 against 12-16 was stored as H). Owner answer
VERIFY-EDIT-LT-VALUE-SEMANTICS "Clear value + recompute (Recommended)"
(2026-11-08): a non-numeric value_text clears value, flag and is_abnormal,
because nothing numeric remains to compare. A value_text that parses as a
finite number (HC-LTV-005) is the named extension: the stored number follows
what the user typed. Every case goes through HTTP and asserts STORED columns.
"""

import json
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.observations as obs_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Document, Observation
from tests.support.master_db import audit_rows, make_master_db, seed_profile, use_master
from tests.support.routes import route_client

PROFILE = "profile-a"
OBS_AT = datetime(2026, 3, 1, 19, 45)


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _seed_obs(db: AsyncSession, *, flag, is_abnormal, value,
                    ref_low=12.0, ref_high=16.0) -> str:
    doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
    db.add(Document(
        id=doc_id, profile_id=PROFILE, path_hash="p" * 64, content_hash="c" * 64,
        doc_type="lab_report", status="verified", imported_at=OBS_AT,
    ))
    db.add(Observation(
        id=obs_id, profile_id=PROFILE, doc_id=doc_id, analyte_canonical="hemoglobin",
        analyte_raw="Hemoglobin", value=value, unit="g/dL", ref_low=ref_low,
        ref_high=ref_high, flag=flag, is_abnormal=is_abnormal, user_verified=False,
        collected_at=OBS_AT,
    ))
    await db.commit()
    return obs_id


def _post_verify(profile_db, obs_id, body, master=None):
    with route_client(obs_api.router, "/observations", profile_id=PROFILE) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        if master is not None:
            use_master(client, master)
        return client.post(f"/observations/{obs_id}/verify", json=body)


async def _verify_and_load(profile_db, obs_id, body, master=None) -> Observation:
    resp = _post_verify(profile_db, obs_id, body, master)
    assert resp.status_code == 200, resp.text
    profile_db.expire_all()
    obs = (
        await profile_db.execute(select(Observation).where(Observation.id == obs_id))
    ).scalar_one()
    assert obs.user_verified is True
    return obs


@pytest.mark.asyncio
async def test_hc_ltv_001_less_than_text_clears_stale_value_and_flag(profile_db):
    obs_id = await _seed_obs(profile_db, flag="L", is_abnormal=True, value=9.0)
    obs = await _verify_and_load(profile_db, obs_id, {"value_text": "<0.5"})
    assert obs.value_text == "<0.5"
    assert obs.value is None
    assert obs.flag is None
    assert obs.is_abnormal is False


@pytest.mark.asyncio
async def test_hc_ltv_002_unflagged_stale_number_is_not_flagged_high(profile_db):
    obs_id = await _seed_obs(profile_db, flag=None, is_abnormal=False, value=18.0)
    obs = await _verify_and_load(profile_db, obs_id, {"value_text": "<0.5"})
    assert obs.value is None
    assert obs.flag is None  # not "H", computed from the number that no longer exists
    assert obs.is_abnormal is False


@pytest.mark.asyncio
async def test_hc_ltv_003_in_range_stale_number_cleared_too(profile_db):
    obs_id = await _seed_obs(profile_db, flag=None, is_abnormal=False, value=2.0,
                             ref_low=1.0, ref_high=3.0)
    obs = await _verify_and_load(profile_db, obs_id, {"value_text": "<0.5"})
    assert (obs.value, obs.flag, obs.is_abnormal) == (None, None, False)


@pytest.mark.asyncio
async def test_hc_ltv_004_value_with_text_unchanged_and_kept_flag_cleared(profile_db):
    # Control: a request that carries its own number takes the old path.
    a_id = await _seed_obs(profile_db, flag=None, is_abnormal=False, value=14.0)
    a = await _verify_and_load(profile_db, a_id, {"value": 0.4, "value_text": "<0.5"})
    assert a.value == 0.4
    assert a.value_text == "<0.5"
    assert (a.flag, a.is_abnormal) == ("L", True)

    # A printed flag described the old number; with no number it does not survive.
    b_id = await _seed_obs(profile_db, flag="CRITICAL", is_abnormal=True, value=14.0)
    b = await _verify_and_load(profile_db, b_id, {"value_text": "<0.5"})
    assert (b.value, b.flag, b.is_abnormal) == (None, None, False)


@pytest.mark.asyncio
async def test_hc_ltv_005_numeric_text_sets_value_comma_decimal_is_text(profile_db):
    a_id = await _seed_obs(profile_db, flag=None, is_abnormal=False, value=14.0)
    a = await _verify_and_load(profile_db, a_id, {"value_text": "18.5"})
    assert a.value == 18.5
    assert (a.flag, a.is_abnormal) == ("H", True)

    b_id = await _seed_obs(profile_db, flag="H", is_abnormal=True, value=18.0)
    b = await _verify_and_load(profile_db, b_id, {"value_text": "12,5"})
    assert (b.value, b.flag, b.is_abnormal) == (None, None, False)

    # Python's float() accepts digit-group underscores; the UI does not.
    c_id = await _seed_obs(profile_db, flag="H", is_abnormal=True, value=18.0)
    c = await _verify_and_load(profile_db, c_id, {"value_text": "1_0"})
    assert (c.value, c.flag, c.is_abnormal) == (None, None, False)


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["nan", "inf", "-Infinity", "negative", "  "])
async def test_hc_ltv_006_non_finite_or_blank_text_is_cleared(profile_db, text):
    obs_id = await _seed_obs(profile_db, flag="H", is_abnormal=True, value=18.0)
    obs = await _verify_and_load(profile_db, obs_id, {"value_text": text})
    assert (obs.value, obs.flag, obs.is_abnormal) == (None, None, False)


@pytest.mark.asyncio
async def test_hc_ltv_007_audit_names_fields_never_values(profile_db, tmp_path):
    master = make_master_db(tmp_path)
    seed_profile(master, PROFILE, "Own")
    obs_id = await _seed_obs(profile_db, flag="CRITICAL", is_abnormal=True, value=14.0)
    await _verify_and_load(profile_db, obs_id, {"value_text": "<0.5"}, master)
    rows = audit_rows(master)
    assert [r.event_type for r in rows] == ["observation.verify"]
    details = json.loads(rows[0].details_json)
    assert details == {"changed_fields": ["flag", "is_abnormal", "value", "value_text"]}
    assert "14.0" not in rows[0].details_json and "CRITICAL" not in rows[0].details_json
