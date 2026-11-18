"""VERIFY-UNDO: POST /observations/{id}/unverify (flag-only).

Owner answers: VERIFY-UNDO "Build unverify route (Recommended)" (2026-11-08) and
VERIFY-UNDO-SCOPE "Flag-only unverify (Recommended)" (2026-11-10). The route
clears user_verified and verified_at, keeps the user's edits (and
original_value_json), re-opens the row in the verify queue, drops a verified
parent document back to parsed, and audits observation.unverify with field
names only. Every case goes through HTTP and reads the STORED columns and the
committed audit rows.
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
async def test_hc_unv_001_flag_cleared_edits_kept_one_audit_row_no_values(profile_db, master):
    _, obs_id = await _seed(profile_db)
    resp = _call(profile_db, master, "POST", f"/observations/{obs_id}/unverify")
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_verified"] is False

    obs = await _obs(profile_db, obs_id)
    assert obs.user_verified is False
    assert obs.verified_at is None
    assert obs.version == 4
    # Flag-only: the user's edit and the original snapshot are untouched.
    assert obs.value == 15.2
    assert obs.original_value_json == '{"value": 18.0}'

    rows = audit_rows(master)
    assert [(r.event_type, r.entity_type, r.entity_id, r.profile_id) for r in rows] == [
        ("observation.unverify", "observation", obs_id, PROFILE)
    ]
    # AUDIT-PHI-001: field names only, no lab value anywhere in the row.
    assert json.loads(rows[0].details_json) == {"changed_fields": ["user_verified"]}
    blob = f"{rows[0].action} {rows[0].details_json}".lower()
    assert "15.2" not in blob and "18.0" not in blob and "hemoglobin" not in blob

    # The row is back in the verify queue.
    queue = _call(profile_db, master, "GET", "/observations/?needs_verification=true")
    assert obs_id in [o["id"] for o in queue.json()]


@pytest.mark.asyncio
async def test_hc_unv_002_verified_document_drops_back_to_parsed(profile_db, master):
    doc_id, obs_id = await _seed(profile_db)
    assert _call(profile_db, master, "POST", f"/observations/{obs_id}/unverify").status_code == 200
    doc = await _doc(profile_db, doc_id)
    assert doc.status == "parsed"
    assert doc.verified_at is None

    # A document that was never verified is left exactly as it was.
    doc2, obs2 = await _seed(profile_db, doc_status="parsed", sibling_unverified=True)
    assert _call(profile_db, master, "POST", f"/observations/{obs2}/unverify").status_code == 200
    assert (await _doc(profile_db, doc2)).status == "parsed"


@pytest.mark.asyncio
async def test_hc_unv_003_second_verify_remarks_row_and_document(profile_db, master):
    doc_id, obs_id = await _seed(profile_db)
    assert _call(profile_db, master, "POST", f"/observations/{obs_id}/unverify").status_code == 200
    resp = _call(profile_db, master, "POST", f"/observations/{obs_id}/verify", json={})
    assert resp.status_code == 200, resp.text
    obs = await _obs(profile_db, obs_id)
    assert obs.user_verified is True and obs.verified_at is not None
    assert obs.value == 15.2
    assert (await _doc(profile_db, doc_id)).status == "verified"
    assert [r.event_type for r in audit_rows(master)] == [
        "observation.unverify", "observation.verify"
    ]


@pytest.mark.asyncio
async def test_hc_unv_004_bad_id_missing_and_foreign_rows_refused_without_audit(profile_db, master):
    _, mine = await _seed(profile_db)
    _, foreign = await _seed(profile_db, owner=OTHER)

    bad = _call(profile_db, master, "POST", "/observations/not-a-uuid/unverify")
    assert bad.status_code == 400
    missing = _call(profile_db, master, "POST", f"/observations/{uuid.uuid4()}/unverify")
    assert missing.status_code == 404
    other = _call(profile_db, master, "POST", f"/observations/{foreign}/unverify")
    assert other.status_code == 403

    # Nothing moved and nothing was audited.
    assert (await _obs(profile_db, foreign)).user_verified is True
    assert (await _obs(profile_db, mine)).user_verified is True
    assert audit_rows(master) == []
