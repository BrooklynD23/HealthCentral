"""VERIFY-KEEPS-FLAG: a plain Verify keeps the lab's printed flag.

POST /observations/{id}/verify used to recompute flag/is_abnormal from
value vs ref_low/ref_high on every call. A report's own flag ("CRITICAL",
or "H" with no printed range) was erased by a Verify click that changed
nothing. The flag is recalculated only when this request changes value,
ref_low or ref_high. Every case goes through HTTP and asserts the STORED
columns, not only the response.
"""

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


async def _seed_obs(db: AsyncSession, *, flag, is_abnormal, value, ref_low, ref_high) -> str:
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


def _get(router, prefix, profile_db, method, url, **kwargs):
    with route_client(router, prefix, profile_id=PROFILE) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.request(method, url, **kwargs)


async def _verify_and_load(profile_db, obs_id, body) -> Observation:
    """POST verify, assert 200, then re-read the stored row from the DB."""
    resp = _get(obs_api.router, "/observations", profile_db, "POST",
                f"/observations/{obs_id}/verify", json=body)
    assert resp.status_code == 200, resp.text
    profile_db.expire_all()
    obs = (
        await profile_db.execute(select(Observation).where(Observation.id == obs_id))
    ).scalar_one()
    # A kept flag must not come from a verify that did nothing.
    assert obs.user_verified is True
    return obs


@pytest.mark.asyncio
async def test_hc_vkf_001_critical_flag_kept_when_value_in_range(profile_db):
    obs_id = await _seed_obs(profile_db, flag="CRITICAL", is_abnormal=True,
                             value=14.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert obs.flag == "CRITICAL"
    assert obs.is_abnormal is True


@pytest.mark.asyncio
async def test_hc_vkf_002_flag_kept_when_report_printed_no_range(profile_db):
    obs_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                             value=14.0, ref_low=None, ref_high=None)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert obs.flag == "H"
    assert obs.is_abnormal is True


@pytest.mark.asyncio
async def test_hc_vkf_003_flag_kept_when_value_inside_printed_range(profile_db):
    obs_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                             value=14.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert obs.flag == "H"
    assert obs.is_abnormal is True


@pytest.mark.asyncio
async def test_hc_vkf_004_resending_same_numbers_keeps_flag(profile_db):
    # Case a: flagged H, value above ref_high; the UI re-sends the same numbers.
    a_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                           value=18.0, ref_low=12.0, ref_high=16.0)
    a = await _verify_and_load(
        profile_db, a_id, {"value": 18.0, "ref_low": 12.0, "ref_high": 16.0})
    assert a.flag == "H"
    assert a.is_abnormal is True

    # Case b: flagged H but value inside the range (today's rule clears it).
    b_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                           value=14.0, ref_low=12.0, ref_high=16.0)
    b = await _verify_and_load(
        profile_db, b_id, {"value": 14.0, "ref_low": 12.0, "ref_high": 16.0})
    assert b.flag == "H"
    assert b.is_abnormal is True


@pytest.mark.asyncio
async def test_hc_vkf_005_edited_value_out_of_range_is_flagged(profile_db):
    # Seeded with a different printed flag so only the changed-value check
    # (not the "no flag" fallback of 008) can trigger the recalculation.
    hi_id = await _seed_obs(profile_db, flag="L", is_abnormal=True,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    hi = await _verify_and_load(profile_db, hi_id, {"value": 18.0})
    assert hi.is_abnormal is True
    assert hi.flag == "H"

    lo_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    lo = await _verify_and_load(profile_db, lo_id, {"value": 9.0})
    assert lo.is_abnormal is True
    assert lo.flag == "L"


@pytest.mark.asyncio
async def test_hc_vkf_006_edited_value_back_in_range_clears_flag(profile_db):
    obs_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                             value=18.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {"value": 14.0})
    assert obs.is_abnormal is False
    assert obs.flag is None


@pytest.mark.asyncio
async def test_hc_vkf_007_edited_range_flags_unchanged_value(profile_db):
    # Rows carry a (different) printed flag so only the changed-range check,
    # not the "no flag" fallback of 008, can trigger the recalculation.
    # ref_high edited so the unchanged value is now above it.
    obs_id = await _seed_obs(profile_db, flag="L", is_abnormal=True,
                             value=14.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {"ref_high": 13.0})
    assert obs.is_abnormal is True
    assert obs.flag == "H"

    # ref_low edited so the unchanged value is now below it.
    lo_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    lo = await _verify_and_load(profile_db, lo_id, {"ref_low": 15.0})
    assert lo.is_abnormal is True
    assert lo.flag == "L"


@pytest.mark.asyncio
async def test_hc_vkf_008_unflagged_out_of_range_row_is_flagged_by_plain_verify(profile_db):
    # The extractor never derives a flag from the range, and ingest sets
    # is_abnormal = flag is not None. A report line with no printed flag but a
    # value outside its printed range must still be flagged by a plain Verify
    # (what origin/main did). Only a row with NO flag is recalculated; a flag
    # the lab printed is never overwritten (001-004).
    hi_id = await _seed_obs(profile_db, flag=None, is_abnormal=False,
                            value=18.0, ref_low=12.0, ref_high=16.0)
    hi = await _verify_and_load(profile_db, hi_id, {})
    assert hi.is_abnormal is True
    assert hi.flag == "H"

    lo_id = await _seed_obs(profile_db, flag=None, is_abnormal=False,
                            value=9.0, ref_low=12.0, ref_high=16.0)
    lo = await _verify_and_load(profile_db, lo_id, {})
    assert lo.is_abnormal is True
    assert lo.flag == "L"

    # An unflagged row inside its range stays unflagged.
    ok_id = await _seed_obs(profile_db, flag=None, is_abnormal=False,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    ok = await _verify_and_load(profile_db, ok_id, {})
    assert ok.is_abnormal is False
    assert ok.flag is None
