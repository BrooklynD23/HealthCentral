"""VERIFY-UNDO-NOOP: unverify on a row that is not verified is refused.

Owner answer VERIFY-NOOP "(a) Skip what is done; refuse an empty undo" (2026-11-11).
An unverified row answers 409 and changes nothing: no version bump, no audit
row, no document write. A verified row behaves as HC-UNV-001. Over HTTP.
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
OTHER = "profile-b"
AT = datetime(2026, 3, 1, 19, 45)
VERIFIED_AT = datetime(2026, 3, 2, 8, 0)


@pytest.fixture
def master(tmp_path):
    db = make_master_db(tmp_path)
    seed_profile(db, PROFILE, "Own")
    seed_profile(db, OTHER, "Other")
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


async def _seed(db: AsyncSession, *, owner=PROFILE, doc_status="verified",
                verified=True, sibling_unverified=False) -> tuple[str, str]:
    """A verified row whose user edit (value 15.2, snapshot of 18.0) must survive."""
    doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
    db.add(Document(
        id=doc_id, profile_id=owner, path_hash="p" * 64, content_hash="c" * 64,
        doc_type="lab_report", status=doc_status, imported_at=AT,
        verified_at=VERIFIED_AT if doc_status == "verified" else None,
    ))
    db.add(Observation(
        id=obs_id, profile_id=owner, doc_id=doc_id, analyte_canonical="hemoglobin",
        analyte_raw="Hemoglobin", value=15.2, unit="g/dL", ref_low=12.0, ref_high=16.0,
        flag=None, is_abnormal=False, user_verified=verified,
        verified_at=VERIFIED_AT if verified else None, version=3,
        original_value_json='{"value": 18.0}', collected_at=AT,
    ))
    if sibling_unverified:
        db.add(Observation(
            id=str(uuid.uuid4()), profile_id=owner, doc_id=doc_id, analyte_canonical="ldl",
            analyte_raw="LDL", value=90.0, unit="mg/dL", user_verified=False, collected_at=AT,
        ))
    await db.commit()
    return doc_id, obs_id


def _call(profile_db, master, method, url, **kwargs):
    with route_client(obs_api.router, "/observations", profile_id=PROFILE) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        use_master(client, master)
        return client.request(method, url, **kwargs)


async def _obs(db, obs_id) -> Observation:
    db.expire_all()
    return (await db.execute(select(Observation).where(Observation.id == obs_id))).scalar_one()


async def _doc(db, doc_id) -> Document:
    db.expire_all()
    return (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one()


@pytest.mark.asyncio
async def test_hc_unvn_001_unverified_row_refused_nothing_written(profile_db, master):
    doc_id, obs_id = await _seed(profile_db, verified=False, doc_status="parsed")
    resp = _call(profile_db, master, "POST", f"/observations/{obs_id}/unverify")
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == "Observation is not verified"

    obs = await _obs(profile_db, obs_id)
    assert obs.version == 3
    assert obs.user_verified is False and obs.verified_at is None
    assert obs.value == 15.2 and obs.original_value_json == '{"value": 18.0}'
    assert (await _doc(profile_db, doc_id)).status == "parsed"
    assert audit_rows(master) == []


@pytest.mark.asyncio
async def test_hc_unvn_002_verified_row_still_unverifies_once(profile_db, master):
    _, obs_id = await _seed(profile_db)
    resp = _call(profile_db, master, "POST", f"/observations/{obs_id}/unverify")
    assert resp.status_code == 200, resp.text
    obs = await _obs(profile_db, obs_id)
    assert obs.user_verified is False and obs.version == 4
    rows = audit_rows(master)
    assert [r.event_type for r in rows] == ["observation.unverify"]
    assert json.loads(rows[0].details_json) == {"changed_fields": ["user_verified"]}

    # A second Undo on the now-unverified row is the empty undo: refused, no second bump or row.
    again = _call(profile_db, master, "POST", f"/observations/{obs_id}/unverify")
    assert again.status_code == 409, again.text
    assert (await _obs(profile_db, obs_id)).version == 4
    assert len(audit_rows(master)) == 1
