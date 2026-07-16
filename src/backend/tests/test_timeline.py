"""HC-M14 health timeline tests (HC-TML-NNN).

Covers the timeline read-model (modules/timeline.py) and the
GET /timeline route (api/timeline.py):

- HC-TML-001: event derivation from a seeded profile DB
- HC-TML-002: date-source precedence and undated handling
- HC-TML-003: event_type and date-range filters
- HC-TML-004: per-profile isolation
- HC-TML-005: audit log entry written on GET
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.profile_database import ProfileDatabaseBase
from models import Document, DocumentCategory, DocumentEntity, Medication, Observation
from modules.timeline import build_timeline

PROFILE_A = "profile-a"
PROFILE_B = "profile-b"

DOC_LAB = str(uuid.uuid4())
DOC_IMAGING = str(uuid.uuid4())
DOC_VISIT = str(uuid.uuid4())
DOC_UNDATED_LAB = str(uuid.uuid4())
DOC_OTHER_PROFILE = str(uuid.uuid4())
MED_ACTIVE = str(uuid.uuid4())
MED_STOPPED = str(uuid.uuid4())


def _document(doc_id: str, profile_id: str, *, collection_date=None, status="parsed",
              imported_at=None, source=None) -> Document:
    return Document(
        id=doc_id,
        profile_id=profile_id,
        path_hash="x" * 64,
        content_hash=doc_id.replace("-", "")[:32].ljust(64, "0"),
        doc_type="lab_pdf",
        source=source,
        status=status,
        collection_date=collection_date,
        imported_at=imported_at or datetime(2024, 6, 1, 12, 0, 0),
    )


def _observation(doc_id: str, profile_id: str, analyte: str, *, collected_at=None,
                 verified=False) -> Observation:
    return Observation(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        doc_id=doc_id,
        analyte_canonical=analyte,
        analyte_raw=analyte.upper(),
        value=1.0,
        unit="mg/dL",
        collected_at=collected_at,
        user_verified=verified,
    )


async def _seed(db: AsyncSession) -> None:
    """Seed a profile DB with observations, classified docs, and medications."""
    # Lab document: 2 analytes collected 2024-03-10, one verified, one not -> mixed
    db.add(_document(DOC_LAB, PROFILE_A, collection_date=datetime(2024, 3, 10)))
    db.add(_observation(DOC_LAB, PROFILE_A, "glucose",
                        collected_at=datetime(2024, 3, 10, 8, 30), verified=True))
    db.add(_observation(DOC_LAB, PROFILE_A, "creatinine",
                        collected_at=datetime(2024, 3, 10, 8, 30), verified=False))

    # Imaging document: no collection_date, but a report_date entity -> entity_date
    db.add(_document(DOC_IMAGING, PROFILE_A, status="verified",
                     imported_at=datetime(2024, 5, 20, 9, 0, 0), source="mri_brain.pdf"))
    db.add(DocumentCategory(doc_id=DOC_IMAGING, category="imaging",
                            confidence=0.95, classified_by="rule"))
    db.add(DocumentEntity(doc_id=DOC_IMAGING, category="imaging",
                          entity_type="report_date", entity_value="04/02/2024",
                          confidence=0.9))

    # Visit note: no collection_date, no dated entity -> falls back to upload date
    db.add(_document(DOC_VISIT, PROFILE_A, imported_at=datetime(2024, 5, 21, 10, 0, 0)))
    db.add(DocumentCategory(doc_id=DOC_VISIT, category="visit_notes",
                            confidence=0.8, classified_by="rule"))

    # Lab document whose observations have no collection date -> undated list
    db.add(_document(DOC_UNDATED_LAB, PROFILE_A))
    db.add(_observation(DOC_UNDATED_LAB, PROFILE_A, "tsh", collected_at=None))

    # Medications: one active (start only), one stopped (start + stop)
    db.add(Medication(id=MED_ACTIVE, profile_id=PROFILE_A, name="Metformin",
                      started_at=datetime(2024, 1, 15)))
    db.add(Medication(id=MED_STOPPED, profile_id=PROFILE_A, name="Lisinopril",
                      started_at=datetime(2023, 11, 1), ended_at=datetime(2024, 4, 20),
                      is_active=False))

    # Another profile's data in the same physical DB must never leak into A's timeline
    db.add(_document(DOC_OTHER_PROFILE, PROFILE_B, collection_date=datetime(2024, 2, 2)))
    db.add(_observation(DOC_OTHER_PROFILE, PROFILE_B, "sodium",
                        collected_at=datetime(2024, 2, 2)))
    db.add(Medication(id=str(uuid.uuid4()), profile_id=PROFILE_B, name="Atorvastatin",
                      started_at=datetime(2024, 2, 3)))

    await db.commit()


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    await _seed(session)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_HC_TML_001_event_derivation(profile_db):
    result = await build_timeline(profile_db, PROFILE_A)
    events = result.events

    by_id = {e.event_id: e for e in events}

    # One lab event per document+collection day, not per analyte
    lab_id = f"lab:{DOC_LAB}:2024-03-10"
    assert lab_id in by_id
    lab = by_id[lab_id]
    assert lab.event_type == "lab_results"
    assert lab.event_date == "2024-03-10"
    assert lab.event_date_source == "recorded_date"
    assert lab.doc_id == DOC_LAB
    assert len(lab.related_ids) == 2
    assert lab.verification_status == "mixed"

    # Classified imaging document event
    img = by_id[f"doc:{DOC_IMAGING}"]
    assert img.event_type == "imaging"
    assert img.event_date == "2024-04-02"
    assert img.verification_status == "verified"

    # Visit note event
    visit = by_id[f"doc:{DOC_VISIT}"]
    assert visit.event_type == "visit_notes"
    assert visit.verification_status == "unverified"

    # Medication start/stop events
    start = by_id[f"med-start:{MED_ACTIVE}"]
    assert start.event_type == "medication_start"
    assert start.event_date == "2024-01-15"
    assert start.verification_status == "n/a"
    assert start.related_ids == [MED_ACTIVE]
    assert start.doc_id is None

    stop = by_id[f"med-stop:{MED_STOPPED}"]
    assert stop.event_type == "medication_stop"
    assert stop.event_date == "2024-04-20"
    assert f"med-start:{MED_STOPPED}" in by_id  # stopped med still has its start

    # Active medication has no stop event
    assert f"med-stop:{MED_ACTIVE}" not in by_id

    # Events sorted newest first
    dates = [e.event_date for e in events]
    assert dates == sorted(dates, reverse=True)

    # Every dated event carries an ISO date and a known source
    for e in events:
        assert e.event_date is not None
        assert e.event_date_source in {
            "document_date", "entity_date", "upload_date", "recorded_date"
        }


@pytest.mark.asyncio
async def test_HC_TML_002_date_source_precedence_and_undated(profile_db):
    result = await build_timeline(profile_db, PROFILE_A)
    by_id = {e.event_id: e for e in result.events}

    # Imaging doc has no collection_date but a parseable report_date entity
    assert by_id[f"doc:{DOC_IMAGING}"].event_date_source == "entity_date"

    # Visit doc has neither -> upload date fallback
    visit = by_id[f"doc:{DOC_VISIT}"]
    assert visit.event_date_source == "upload_date"
    assert visit.event_date == "2024-05-21"

    # Undated lab observations are excluded from the dated stream...
    assert f"lab:{DOC_UNDATED_LAB}:undated" not in by_id
    # ...but present in the undated list
    undated_ids = {e.event_id for e in result.undated}
    assert f"lab:{DOC_UNDATED_LAB}:undated" in undated_ids
    for e in result.undated:
        assert e.event_date is None


@pytest.mark.asyncio
async def test_HC_TML_003_filters(profile_db):
    # event_type filter
    result = await build_timeline(profile_db, PROFILE_A, event_type="lab_results")
    assert result.events, "expected at least one lab event"
    assert all(e.event_type == "lab_results" for e in result.events)
    assert all(e.event_type == "lab_results" for e in result.undated)

    result = await build_timeline(profile_db, PROFILE_A, event_type="medication_start")
    assert {e.event_id for e in result.events} == {
        f"med-start:{MED_ACTIVE}", f"med-start:{MED_STOPPED}",
    }
    assert result.undated == []

    # date range filter (inclusive)
    result = await build_timeline(
        profile_db, PROFILE_A,
        date_from=datetime(2024, 3, 1).date(),
        date_to=datetime(2024, 4, 30).date(),
    )
    ids = {e.event_id for e in result.events}
    assert ids == {
        f"lab:{DOC_LAB}:2024-03-10",
        f"doc:{DOC_IMAGING}",
        f"med-stop:{MED_STOPPED}",
    }


@pytest.mark.asyncio
async def test_HC_TML_004_per_profile_isolation(profile_db):
    result_a = await build_timeline(profile_db, PROFILE_A)
    all_a = result_a.events + result_a.undated
    assert all_a, "profile A should have events"
    for e in all_a:
        assert DOC_OTHER_PROFILE != e.doc_id
        assert "Atorvastatin" not in e.title
        assert "sodium" not in e.title.lower()

    result_b = await build_timeline(profile_db, PROFILE_B)
    b_doc_ids = {e.doc_id for e in result_b.events if e.doc_id}
    assert b_doc_ids == {DOC_OTHER_PROFILE}
    # Profile A's documents/meds never appear in B's timeline
    a_ids = {e.event_id for e in all_a}
    b_ids = {e.event_id for e in result_b.events + result_b.undated}
    assert not (a_ids & b_ids)


def test_HC_TML_005_get_timeline_writes_audit_row(profile_db, monkeypatch):
    import api.timeline as timeline_api
    from api.timeline import router as timeline_router
    from core.auth import Session, get_profile_db_session, require_auth
    from core.database import get_db

    master_db = AsyncMock()
    log_mock = AsyncMock(return_value=object())
    monkeypatch.setattr(timeline_api, "create_audit_log", log_mock)

    app = FastAPI()
    app.include_router(timeline_router, prefix="/timeline")

    async def _override_auth():
        return Session(
            profile_id=PROFILE_A,
            profile_name="T",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    async def _override_profile_db():
        return profile_db

    async def _override_master_db():
        return master_db

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_profile_db_session] = _override_profile_db
    app.dependency_overrides[get_db] = _override_master_db

    with TestClient(app) as client:
        response = client.get("/timeline/")

    assert response.status_code == 200
    body = response.json()
    assert body["events"], "expected dated events"
    assert body["undated"], "expected undated items"

    log_mock.assert_awaited_once()
    assert log_mock.await_args.kwargs["event_type"] == "timeline.view"
    assert log_mock.await_args.kwargs["profile_id"] == PROFILE_A
    master_db.commit.assert_awaited_once()

    # Invalid event_type rejected
    with TestClient(app) as client:
        response = client.get("/timeline/", params={"event_type": "bogus"})
    assert response.status_code == 400
