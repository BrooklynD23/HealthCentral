"""TREND-POINT-RANGE: each trend point carries its own report's reference range.

HC-TPR-001  two reports, two ranges: each point carries its own; the series band is unchanged
HC-TPR-002  a report with no printed range: that point's bounds are None
HC-TPR-003  one printed bound only: the other stays None
HC-TPR-004  unit normalization: bounds are converted with the point (g/L to g/dL); a missing bound is None (002, 003)

All through HTTP (route_client), so the real dependency graph runs.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.observations as obs_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Document, Observation
from tests.support.master_db import make_master_db, seed_profile, use_master
from tests.support.routes import route_client

PROFILE = "profile-a"


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


def _add(db, when, value, lo, hi, unit="g/dL", analyte="hemoglobin"):
    doc_id = str(uuid.uuid4())
    db.add(Document(id=doc_id, profile_id=PROFILE, path_hash=uuid.uuid4().hex * 2,
                    content_hash=uuid.uuid4().hex * 2, doc_type="lab_report",
                    status="verified", imported_at=when))
    db.add(Observation(id=str(uuid.uuid4()), profile_id=PROFILE, doc_id=doc_id,
                       analyte_canonical=analyte, analyte_raw=analyte.title(), value=value,
                       unit=unit, ref_low=lo, ref_high=hi, user_verified=True,
                       verified_at=when, collected_at=when))


def _trend(profile_db, master, analyte="hemoglobin"):
    with route_client(obs_api.router, "/observations", profile_id=PROFILE) as client:
        async def _p():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _p
        use_master(client, master)
        resp = client.get(f"/observations/trends/{analyte}")
    assert resp.status_code == 200, resp.text
    return resp.json()


JAN = datetime(2026, 1, 5)
MAR = datetime(2026, 3, 5)


@pytest.mark.asyncio
async def test_hc_tpr_001_each_point_carries_its_own_report_range(profile_db, master):
    _add(profile_db, JAN, 15.5, 12.0, 16.0)
    _add(profile_db, MAR, 14.0, 13.5, 17.5)
    await profile_db.commit()
    body = _trend(profile_db, master)
    p0, p1 = body["data_points"]
    assert (p0["ref_low"], p0["ref_high"]) == (12.0, 16.0), p0
    assert (p1["ref_low"], p1["ref_high"]) == (13.5, 17.5), p1
    # the series band is unchanged: the latest report that printed both bounds
    assert (body["ref_low"], body["ref_high"]) == (13.5, 17.5)


@pytest.mark.asyncio
async def test_hc_tpr_002_a_report_with_no_range_gives_its_point_no_bounds(profile_db, master):
    _add(profile_db, JAN, 15.5, None, None)
    _add(profile_db, MAR, 14.0, 13.5, 17.5)
    await profile_db.commit()
    body = _trend(profile_db, master)
    p0, p1 = body["data_points"]
    assert p0["ref_low"] is None and p0["ref_high"] is None, p0
    assert (p1["ref_low"], p1["ref_high"]) == (13.5, 17.5)
    assert (body["ref_low"], body["ref_high"]) == (13.5, 17.5)


@pytest.mark.asyncio
async def test_hc_tpr_003_one_printed_bound_leaves_the_other_none(profile_db, master):
    _add(profile_db, JAN, 15.5, None, 16.0)
    await profile_db.commit()
    p0 = _trend(profile_db, master)["data_points"][0]
    assert p0["ref_low"] is None, p0
    assert p0["ref_high"] == 16.0, p0


@pytest.mark.asyncio
async def test_hc_tpr_004_bounds_follow_the_point_into_the_canonical_unit(profile_db, master):
    _add(profile_db, JAN, 150.0, 120.0, 160.0, unit="g/L")
    _add(profile_db, MAR, 14.0, 13.5, 17.5, unit="g/dL")
    await profile_db.commit()
    body = _trend(profile_db, master)
    p0, p1 = body["data_points"]
    assert p0["original_unit"] == "g/L" and p0["unit"] == "g/dL", p0
    assert p0["value"] == pytest.approx(15.0)
    assert p0["ref_low"] == pytest.approx(12.0), p0
    assert p0["ref_high"] == pytest.approx(16.0), p0
    assert (p1["ref_low"], p1["ref_high"]) == (13.5, 17.5)


def test_hc_tpr_default_fields_are_none():
    point = obs_api.TrendPoint(date="2026-03-01T09:00:00", value=1.0, unit="", is_abnormal=False,
                               doc_id="d")
    assert point.ref_low is None and point.ref_high is None
