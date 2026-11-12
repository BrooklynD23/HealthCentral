"""FLAG-OLD-ON-REWRITE: the verify snapshot keeps the printed flag and the audit names recalculated fields."""
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
AT = datetime(2026, 3, 1, 19, 45)


@pytest.fixture
def master(tmp_path):
    db = make_master_db(tmp_path)
    seed_profile(db, PROFILE, "Own")
    return db


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


async def _seed(db, *, flag, is_abnormal, value, verified=False, version=1):
    doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
    db.add(Document(id=doc_id, profile_id=PROFILE, path_hash="p" * 64, content_hash="c" * 64,
                    doc_type="lab_report", status="parsed", imported_at=AT))
    db.add(Observation(id=obs_id, profile_id=PROFILE, doc_id=doc_id, analyte_canonical="hemoglobin",
                       analyte_raw="Hemoglobin", value=value, unit="g/dL", ref_low=12.0, ref_high=16.0,
                       flag=flag, is_abnormal=is_abnormal, user_verified=verified,
                       verified_at=AT if verified else None, version=version, collected_at=AT))
    await db.commit()
    return obs_id


def _call(profile_db, master, method, url, **kw):
    with route_client(obs_api.router, "/observations", profile_id=PROFILE) as client:
        async def _p():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _p
        use_master(client, master)
        return client.request(method, url, **kw)


async def _obs(db, obs_id):
    db.expire_all()
    return (await db.execute(select(Observation).where(Observation.id == obs_id))).scalar_one()


async def _verify(profile_db, master, obs_id, body):
    resp = _call(profile_db, master, "POST", f"/observations/{obs_id}/verify", json=body)
    assert resp.status_code == 200, resp.text
    return json.loads(audit_rows(master)[0].details_json or "null")


@pytest.mark.asyncio
async def test_hc_vfr_001_snapshot_keeps_printed_hh(profile_db, master):
    obs_id = await _seed(profile_db, flag="HH", is_abnormal=True, value=18.0)
    await _verify(profile_db, master, obs_id, {"value": 17.0})
    obs = await _obs(profile_db, obs_id)
    assert obs.flag == "H"
    snap = json.loads(obs.original_value_json)
    assert snap["flag"] == "HH"
    assert snap["is_abnormal"] is True


@pytest.mark.asyncio
async def test_hc_vfr_002_cleared_flag_is_recorded(profile_db, master):
    obs_id = await _seed(profile_db, flag="H", is_abnormal=True, value=18.0)
    details = await _verify(profile_db, master, obs_id, {"value": 14.0})
    obs = await _obs(profile_db, obs_id)
    assert obs.flag is None and obs.is_abnormal is False
    assert json.loads(obs.original_value_json)["flag"] == "H"
    assert details["changed_fields"] == ["flag", "is_abnormal", "value"]


@pytest.mark.asyncio
async def test_hc_vfr_003_plain_verify_of_kept_flag_has_no_details(profile_db, master):
    obs_id = await _seed(profile_db, flag="H", is_abnormal=True, value=18.0)
    details = await _verify(profile_db, master, obs_id, {})
    obs = await _obs(profile_db, obs_id)
    assert obs.flag == "H"
    assert details is None
    assert json.loads(obs.original_value_json)["flag"] == "H"


@pytest.mark.asyncio
async def test_hc_vfr_004_second_edit_keeps_first_snapshot(profile_db, master):
    obs_id = await _seed(profile_db, flag="HH", is_abnormal=True, value=18.0)
    await _verify(profile_db, master, obs_id, {"value": 17.0})
    resp = _call(profile_db, master, "POST", f"/observations/{obs_id}/verify", json={"value": 13.0})
    assert resp.status_code == 200, resp.text
    obs = await _obs(profile_db, obs_id)
    snap = json.loads(obs.original_value_json)
    assert snap["flag"] == "HH" and snap["value"] == 18.0


@pytest.mark.asyncio
async def test_hc_vfr_005_plain_verify_of_unflagged_out_of_range_audits_recalculation(profile_db, master):
    """L0 ruling R14: the audit records every field the route changes, including a recalculated flag."""
    obs_id = await _seed(profile_db, flag=None, is_abnormal=False, value=18.0)
    details = await _verify(profile_db, master, obs_id, {})
    obs = await _obs(profile_db, obs_id)
    assert obs.flag == "H" and obs.is_abnormal is True  # unchanged behaviour
    assert details["changed_fields"] == ["flag", "is_abnormal"]
