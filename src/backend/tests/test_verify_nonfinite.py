"""VERIFY-NONFINITE: /verify rejects non-finite numbers and inverted ranges.

POST /observations/{id}/verify accepted {"value": NaN} — Python's json emits
the JS NaN/Infinity/-Infinity literals and pydantic v2 takes them for
Optional[float]. The flag recalculation then compared a NaN, every comparison
was False, and a stored "CRITICAL" flag on a row at 18 against 12-16 was erased
to (None, False) with the value stored as NULL. Fail closed: a non-finite
value/ref_low/ref_high is a 400 (a schema-level Field(allow_inf_nan=False)
would be a 422, so the check lives in the handler). A patient-typed inverted
pair (both bounds sent, ref_low > ref_high) is a 400 too — the patient typed
it; reject, never silently reorder (owner answer RANGE-ORDER-STORE-VERIFY,
2026-11-07). Every case goes through HTTP and asserts the STORED columns, not
only the response. HC-VNF-004 and HC-VNF-005 are pins: GREEN before the fix.
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


async def _seed_obs(db: AsyncSession, *, flag, is_abnormal, value, ref_low, ref_high,
                    user_verified=False) -> str:
    doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
    db.add(Document(
        id=doc_id, profile_id=PROFILE, path_hash="p" * 64, content_hash="c" * 64,
        doc_type="lab_report", status="verified", imported_at=OBS_AT,
    ))
    db.add(Observation(
        id=obs_id, profile_id=PROFILE, doc_id=doc_id, analyte_canonical="hemoglobin",
        analyte_raw="Hemoglobin", value=value, unit="g/dL", ref_low=ref_low,
        ref_high=ref_high, flag=flag, is_abnormal=is_abnormal, user_verified=user_verified,
        collected_at=OBS_AT,
    ))
    await db.commit()
    return obs_id


async def _seed_critical(profile_db: AsyncSession) -> str:
    """The row the queue measured: CRITICAL flag, value 18 against 12-16."""
    return await _seed_obs(profile_db, flag="CRITICAL", is_abnormal=True,
                           value=18.0, ref_low=12.0, ref_high=16.0)


def _get(router, prefix, profile_db, method, url, master_db=None, **kwargs):
    with route_client(router, prefix, profile_id=PROFILE, master_db=master_db) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.request(method, url, **kwargs)


def _post_verify(profile_db, obs_id, body):
    # The crafted request carries the literal NaN/Infinity/-Infinity tokens.
    # stdlib json.dumps emits them (allow_nan=True); httpx's json= kwarg does
    # not (0.28 hardcodes allow_nan=False), so the body is sent as content.
    return _get(obs_api.router, "/observations", profile_db, "POST",
                f"/observations/{obs_id}/verify",
                content=json.dumps(body),
                headers={"Content-Type": "application/json"})


async def _load(profile_db, obs_id) -> Observation:
    profile_db.expire_all()
    return (
        await profile_db.execute(select(Observation).where(Observation.id == obs_id))
    ).scalar_one()


def _assert_row_unchanged(obs: Observation) -> None:
    """The seeded CRITICAL row, untouched: the reject precedes every write."""
    assert obs.value == 18.0
    assert obs.ref_low == 12.0
    assert obs.ref_high == 16.0
    assert obs.flag == "CRITICAL"
    assert obs.is_abnormal is True
    assert obs.user_verified is False
    # Rejected before the original-values snapshot write, so audit fields are
    # absent too.
    assert obs.original_value_json is None


@pytest.mark.asyncio
async def test_hc_vnf_001_nan_value_rejected_row_unchanged(profile_db):
    obs_id = await _seed_critical(profile_db)
    resp = _post_verify(profile_db, obs_id, {"value": float("nan")})
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "value must be a finite number"
    _assert_row_unchanged(await _load(profile_db, obs_id))


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [float("inf"), float("-inf")], ids=["inf", "-inf"])
async def test_hc_vnf_002_nonfinite_value_rejected(profile_db, bad):
    obs_id = await _seed_critical(profile_db)
    resp = _post_verify(profile_db, obs_id, {"value": bad})
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "value must be a finite number"
    _assert_row_unchanged(await _load(profile_db, obs_id))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,field",
    [
        ({"ref_low": float("nan")}, "ref_low"),
        ({"ref_high": float("-inf")}, "ref_high"),
    ],
    ids=["ref_low-nan", "ref_high--inf"],
)
async def test_hc_vnf_003_nonfinite_bound_rejected(profile_db, body, field):
    obs_id = await _seed_critical(profile_db)
    resp = _post_verify(profile_db, obs_id, body)
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == f"{field} must be a finite number"
    _assert_row_unchanged(await _load(profile_db, obs_id))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,flag,is_abnormal",
    [
        ({"value": 18.5, "ref_low": 12.0, "ref_high": 16.0}, "H", True),
        ({"value": 0.0}, "L", True),
        ({"value": -1.0}, "L", True),
    ],
    ids=["value-18.5", "value-0.0", "value--1.0"],
)
async def test_hc_vnf_004_finite_edits_still_verify(profile_db, body, flag, is_abnormal):
    """Pin: finite edits recalculate and verify exactly as before the fix."""
    obs_id = await _seed_critical(profile_db)
    resp = _post_verify(profile_db, obs_id, body)
    assert resp.status_code == 200, resp.text
    obs = await _load(profile_db, obs_id)
    assert obs.user_verified is True
    assert obs.flag == flag
    assert obs.is_abnormal is is_abnormal


@pytest.mark.asyncio
async def test_hc_vnf_005_empty_body_verifies(profile_db):
    """Pin: absent fields skip the check; a plain Verify keeps the flag."""
    obs_id = await _seed_critical(profile_db)
    resp = _post_verify(profile_db, obs_id, {})
    assert resp.status_code == 200, resp.text
    obs = await _load(profile_db, obs_id)
    assert obs.user_verified is True
    assert obs.flag == "CRITICAL"
    assert obs.is_abnormal is True


@pytest.mark.asyncio
async def test_hc_vnf_006_inverted_patient_typed_range_rejected(profile_db):
    """RANGE-ORDER-STORE-VERIFY: both bounds sent inverted is a 400."""
    obs_id = await _seed_critical(profile_db)
    resp = _post_verify(profile_db, obs_id, {"ref_low": 99.0, "ref_high": 70.0})
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "ref_low must not exceed ref_high"
    _assert_row_unchanged(await _load(profile_db, obs_id))

    # Pin: a normal pair still verifies.
    obs_id = await _seed_critical(profile_db)
    resp = _post_verify(profile_db, obs_id, {"ref_low": 70.0, "ref_high": 99.0})
    assert resp.status_code == 200, resp.text
    obs = await _load(profile_db, obs_id)
    assert obs.ref_low == 70.0
    assert obs.ref_high == 99.0

    # Pin: one bound alone passes the check — it needs both (the other bound
    # may already be stored).
    obs_id = await _seed_critical(profile_db)
    resp = _post_verify(profile_db, obs_id, {"ref_low": 99.0})
    assert resp.status_code == 200, resp.text
