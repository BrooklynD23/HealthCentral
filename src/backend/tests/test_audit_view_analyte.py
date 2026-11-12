"""AUDIT-VIEW-ANALYTE: the trend and panel view audit rows must not name the analyte.

Which biomarkers a patient has tested is clinical content (AUDIT-PHI-001); the audit
table lives in the unencrypted master DB. Owner answer AVA-OLD-ROWS (a), 2026-11-11:
new rows write the constant ``"all"``; rows already on disk are left alone.
"""
import json
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.observations as obs_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Document, Observation
from tests.support.master_db import audit_rows, make_master_db, seed_profile, use_master
from tests.support.routes import route_client

PROFILE = "profile-a"
AT = datetime(2026, 3, 1, 19, 45)

# (url, names that must never reach the master DB, expected audit action)
CASES = [
    ("/observations/trends/hiv_viral_load", ("hiv_viral_load", "hiv", "viral"), "trend"),
    ("/observations/panels/thyroid", ("thyroid", "tsh"), "panel"),
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


async def _seed(db: AsyncSession) -> None:
    """One real row per analyte, so both routes return 200 (the trend route 404s on none)."""
    for canon in ("hiv_viral_load", "tsh"):
        doc_id = str(uuid.uuid4())
        db.add(Document(
            id=doc_id, profile_id=PROFILE, path_hash=uuid.uuid4().hex * 2,
            content_hash=uuid.uuid4().hex * 2, doc_type="lab_report",
            status="verified", imported_at=AT,
        ))
        db.add(Observation(
            id=str(uuid.uuid4()), profile_id=PROFILE, doc_id=doc_id,
            analyte_canonical=canon, analyte_raw=canon, value=1.0, unit="x",
            user_verified=True, verified_at=AT, collected_at=AT,
        ))
    await db.commit()


def _get(profile_db, master, url):
    with route_client(obs_api.router, "/observations", profile_id=PROFILE) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        use_master(client, master)
        return client.get(url)


def _blob(row) -> str:
    return " ".join(str(getattr(row, c.name)) for c in row.__table__.columns).lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("url,names,action", CASES)
async def test_hc_ava_001_002_view_audit_row_names_no_analyte(profile_db, master, url, names, action):
    """HC-AVA-001 (trend) and HC-AVA-002 (panel): entity_id is the constant, no column has the name."""
    await _seed(profile_db)
    resp = _get(profile_db, master, url)
    assert resp.status_code == 200, resp.text

    rows = audit_rows(master)
    assert len(rows) == 1, [r.event_type for r in rows]
    row = rows[0]
    assert row.event_type == "observation.view"
    blob = _blob(row)
    for name in names:
        assert name not in blob, f"{name} reached the audit row: {blob}"
    assert row.entity_id == "all"
    assert json.loads(row.details_json) == {"action": action, "count": 1}


@pytest.mark.asyncio
@pytest.mark.parametrize("url,names,action", CASES)
async def test_hc_ava_003_each_get_still_writes_one_committed_row(profile_db, master, url, names, action):
    """HC-AVA-003 (GREEN pin): the route still audits, once per GET, and the row is committed."""
    await _seed(profile_db)
    for expected in (1, 2):
        assert _get(profile_db, master, url).status_code == 200
        assert len(audit_rows(master)) == expected
