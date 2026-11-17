"""VERIFY-ALL-RECALC: Verify all recalculates each row's flag exactly as a plain single Verify.

Before this row, POST /documents/{id}/verify only set user_verified/verified_at/version.
POST /observations/{id}/verify with an empty body also stores original_value_json and
recalculates flag/is_abnormal for a row with no flag or a normal word. A row with no flag,
value 300 and range 70-100 ended H/abnormal after a single Verify but unflagged after
Verify all. Every test goes through HTTP (route_client) and reads the STORED columns.
HC-VAR-001 is the parity matrix: the same rows on both routes must end identical, so a
later change to one route that is not mirrored fails it.
"""
import json
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.documents as docs_api
import api.observations as obs_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Document, Observation
from tests.support.master_db import audit_rows, make_master_db, seed_profile, use_master
from tests.support.routes import route_client

PROFILE = "profile-a"
EARLIER = datetime(2026, 3, 1, 19, 45)

# (name, flag, is_abnormal, value, ref_low, ref_high)
CASES = [
    ("none_300_in_70_100", None, False, 300.0, 70.0, 100.0),
    ("none_50_in_70_100", None, False, 50.0, 70.0, 100.0),
    ("none_80_in_70_100", None, False, 80.0, 70.0, 100.0),
    ("N_300_in_70_100", "N", False, 300.0, 70.0, 100.0),
    ("WNL_50_in_70_open", "WNL", False, 50.0, 70.0, None),
    ("H_80_in_70_100_kept", "H", True, 80.0, 70.0, 100.0),
    ("HIGH_50_in_70_100_kept", "HIGH", True, 50.0, 70.0, 100.0),
    ("text_flag_no_value", "abnormal-text", True, None, 70.0, 100.0),
    ("none_no_value", None, False, None, 70.0, 100.0),
    ("none_300_no_range", None, False, 300.0, None, None),
]


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


async def _seed_doc(db):
    doc_id = str(uuid.uuid4())
    db.add(Document(id=doc_id, profile_id=PROFILE, path_hash="p" * 64, content_hash="c" * 64,
                    doc_type="lab_report", status="parsed", imported_at=EARLIER))
    await db.commit()
    return doc_id


async def _seed_obs(db, doc_id, case, *, verified=False, version=1):
    _name, flag, is_abnormal, value, low, high = case
    obs_id = str(uuid.uuid4())
    db.add(Observation(id=obs_id, profile_id=PROFILE, doc_id=doc_id, analyte_canonical="glucose",
                       analyte_raw="Glucose", value=value, unit="mg/dL", ref_low=low, ref_high=high,
                       flag=flag, is_abnormal=is_abnormal, user_verified=verified,
                       verified_at=EARLIER if verified else None, version=version,
                       collected_at=EARLIER))
    await db.commit()
    return obs_id


async def _obs(db, obs_id):
    db.expire_all()
    return (await db.execute(select(Observation).where(Observation.id == obs_id))).scalar_one()


def _state(obs):
    return (obs.flag, obs.is_abnormal,
            json.loads(obs.original_value_json) if obs.original_value_json else None)


def _call(profile_db, master, router, prefix, url):
    with route_client(router, prefix, profile_id=PROFILE) as client:
        async def _p():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _p
        use_master(client, master)
        return client.post(url, json={}) if router is obs_api.router else client.post(url)


def _verify_all(profile_db, master, doc_id):
    return _call(profile_db, master, docs_api.router, "/documents", f"/documents/{doc_id}/verify")


def _verify_one(profile_db, master, obs_id):
    return _call(profile_db, master, obs_api.router, "/observations",
                 f"/observations/{obs_id}/verify")


@pytest.mark.asyncio
async def test_hc_var_001_verify_all_matches_single_verify_per_case(profile_db, master):
    doc_a, doc_b = await _seed_doc(profile_db), await _seed_doc(profile_db)
    a_ids = {c[0]: await _seed_obs(profile_db, doc_a, c) for c in CASES}
    b_ids = {c[0]: await _seed_obs(profile_db, doc_b, c) for c in CASES}
    assert _verify_all(profile_db, master, doc_a).status_code == 200
    for obs_id in b_ids.values():
        resp = _verify_one(profile_db, master, obs_id)
        assert resp.status_code == 200, resp.text
    mismatches = []
    for name in a_ids:
        a, b = _state(await _obs(profile_db, a_ids[name])), _state(await _obs(profile_db, b_ids[name]))
        if a != b:
            mismatches.append((name, a, b))
    assert not mismatches, mismatches
    # The matrix must exercise a real recalculation, not only "both unchanged".
    flags = {n: (await _obs(profile_db, i)).flag for n, i in a_ids.items()}
    assert flags["none_300_in_70_100"] == "H" and flags["none_50_in_70_100"] == "L"
    assert flags["N_300_in_70_100"] == "H" and flags["WNL_50_in_70_open"] == "L"
    assert flags["H_80_in_70_100_kept"] == "H" and flags["HIGH_50_in_70_100_kept"] == "HIGH"


@pytest.mark.asyncio
async def test_hc_var_002_unflagged_out_of_range_row_gets_h_and_keeps_printed_state(profile_db, master):
    doc_id = await _seed_doc(profile_db)
    obs_id = await _seed_obs(profile_db, doc_id, CASES[0])
    assert _verify_all(profile_db, master, doc_id).status_code == 200
    obs = await _obs(profile_db, obs_id)
    assert obs.flag == "H" and obs.is_abnormal is True
    original = json.loads(obs.original_value_json)
    assert original["flag"] is None and original["is_abnormal"] is False
    assert original["value"] == 300.0 and original["ref_high"] == 100.0


@pytest.mark.asyncio
async def test_hc_var_003_already_checked_row_is_not_recalculated(profile_db, master):
    doc_id = await _seed_doc(profile_db)
    done = await _seed_obs(profile_db, doc_id, CASES[0], verified=True, version=2)
    todo = await _seed_obs(profile_db, doc_id, CASES[0], verified=False, version=2)
    assert _verify_all(profile_db, master, doc_id).status_code == 200
    kept = await _obs(profile_db, done)
    assert (kept.flag, kept.is_abnormal, kept.version) == (None, False, 2)
    assert kept.original_value_json is None and kept.verified_at == EARLIER
    fresh = await _obs(profile_db, todo)
    assert fresh.user_verified is True and fresh.version == 3


@pytest.mark.asyncio
async def test_hc_var_004_audit_details_stay_exactly_the_count(profile_db, master):
    doc_id = await _seed_doc(profile_db)
    for case in CASES[:3]:
        await _seed_obs(profile_db, doc_id, case)
    resp = _verify_all(profile_db, master, doc_id)
    assert resp.status_code == 200 and resp.json()["verified_count"] == 3
    rows = audit_rows(master)
    assert [r.event_type for r in rows] == ["document.verify"]
    assert json.loads(rows[0].details_json) == {"verified_count": 3}


@pytest.mark.asyncio
async def test_hc_var_005_second_verify_all_changes_nothing(profile_db, master):
    doc_id = await _seed_doc(profile_db)
    ids = [await _seed_obs(profile_db, doc_id, c) for c in CASES]
    assert _verify_all(profile_db, master, doc_id).status_code == 200
    first = []
    for i in ids:
        o = await _obs(profile_db, i)
        first.append((_state(o), o.version, o.verified_at))
    resp = _verify_all(profile_db, master, doc_id)
    assert resp.status_code == 200 and resp.json()["verified_count"] == 0
    second = []
    for i in ids:
        o = await _obs(profile_db, i)
        second.append((_state(o), o.version, o.verified_at))
    assert second == first
