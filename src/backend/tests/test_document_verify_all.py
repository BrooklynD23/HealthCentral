"""DOC-VERIFY-ALL-KEEPS (owner answer VERIFY-NOOP (a)): Verify all skips what is done.

Every test goes through HTTP (route_client) so the dependency graph runs.
"""
import json
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.documents as docs_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Document, Observation
from tests.support.master_db import audit_rows, make_master_db, seed_profile, use_master
from tests.support.routes import route_client

PROFILE = "profile-a"
EARLIER = datetime(2026, 3, 1, 19, 45)
SOURCE_NAME = "secret_lab_2026.pdf"


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


async def _seed_doc(db, *, status="parsed", doc_verified_at=None, owner=PROFILE):
    doc_id = str(uuid.uuid4())
    db.add(Document(id=doc_id, profile_id=owner, path_hash="p" * 64, content_hash="c" * 64,
                    doc_type="lab_report", status=status, source=SOURCE_NAME,
                    imported_at=EARLIER, verified_at=doc_verified_at))
    await db.commit()
    return doc_id


async def _seed_obs(db, doc_id, *, verified, version):
    obs_id = str(uuid.uuid4())
    db.add(Observation(id=obs_id, profile_id=PROFILE, doc_id=doc_id, analyte_canonical="hemoglobin",
                       analyte_raw="Hemoglobin", value=14.0, unit="g/dL", ref_low=12.0, ref_high=16.0,
                       user_verified=verified, verified_at=EARLIER if verified else None,
                       version=version, collected_at=EARLIER))
    await db.commit()
    return obs_id


async def _obs(db, obs_id):
    db.expire_all()
    return (await db.execute(select(Observation).where(Observation.id == obs_id))).scalar_one()


async def _doc(db, doc_id):
    db.expire_all()
    return (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one()


def _post(profile_db, master, doc_id):
    with route_client(docs_api.router, "/documents", profile_id=PROFILE) as client:
        async def _p():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _p
        use_master(client, master)
        return client.post(f"/documents/{doc_id}/verify")


@pytest.mark.asyncio
async def test_hc_dva_001_already_verified_row_keeps_date_and_version(profile_db, master):
    doc_id = await _seed_doc(profile_db)
    done = await _seed_obs(profile_db, doc_id, verified=True, version=2)
    todo = await _seed_obs(profile_db, doc_id, verified=False, version=2)
    resp = _post(profile_db, master, doc_id)
    assert resp.status_code == 200, resp.text
    kept = await _obs(profile_db, done)
    assert kept.verified_at == EARLIER
    assert kept.version == 2
    fresh = await _obs(profile_db, todo)
    assert fresh.user_verified is True
    assert fresh.verified_at is not None and fresh.verified_at > EARLIER
    assert fresh.version == 3


@pytest.mark.asyncio
async def test_hc_dva_002_count_in_audit_and_response_is_rows_checked_now(profile_db, master):
    doc_id = await _seed_doc(profile_db)
    await _seed_obs(profile_db, doc_id, verified=True, version=2)
    await _seed_obs(profile_db, doc_id, verified=False, version=2)
    resp = _post(profile_db, master, doc_id)
    assert resp.status_code == 200, resp.text
    assert resp.json()["verified_count"] == 1
    rows = audit_rows(master)
    assert [r.event_type for r in rows] == ["document.verify"]
    assert json.loads(rows[0].details_json) == {"verified_count": 1}


@pytest.mark.asyncio
async def test_hc_dva_003_route_audits_once_scopes_and_hides_filename(profile_db, master):
    doc_id = await _seed_doc(profile_db)
    await _seed_obs(profile_db, doc_id, verified=False, version=1)
    resp = _post(profile_db, master, doc_id)
    assert resp.status_code == 200, resp.text
    assert (await _doc(profile_db, doc_id)).status == "verified"
    rows = audit_rows(master)
    assert len(rows) == 1 and rows[0].entity_id == doc_id
    blob = " ".join(str(getattr(rows[0], c.name)) for c in rows[0].__table__.columns)
    assert SOURCE_NAME not in blob and "secret_lab" not in blob
    assert _post(profile_db, master, str(uuid.uuid4())).status_code == 404
    other = await _seed_doc(profile_db, owner="profile-b")
    assert _post(profile_db, master, other).status_code == 403


@pytest.mark.asyncio
async def test_hc_dva_004_second_verify_all_keeps_document_date_and_counts_zero(profile_db, master):
    doc_id = await _seed_doc(profile_db)
    await _seed_obs(profile_db, doc_id, verified=False, version=1)
    assert _post(profile_db, master, doc_id).status_code == 200
    first = (await _doc(profile_db, doc_id)).verified_at
    assert first is not None
    resp = _post(profile_db, master, doc_id)
    assert resp.status_code == 200, resp.text
    assert (await _doc(profile_db, doc_id)).verified_at == first
    assert resp.json()["verified_count"] == 0
    rows = audit_rows(master)
    assert [json.loads(r.details_json)["verified_count"] for r in rows] == [1, 0]
