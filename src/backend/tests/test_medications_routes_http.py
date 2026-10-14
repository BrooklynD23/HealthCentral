"""HTTP tests for medication CRUD: MedicationResponse reads med.schedules,
which must be loaded eagerly under async SQLAlchemy (else MissingGreenlet/500)."""

import uuid
from datetime import datetime, time, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.gamification as gamification_api
from api.medications import router as med_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import DoseTaken, Medication, MedicationSchedule
from tests.support.routes import route_client

PROFILE = "profile-a"


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


def _client(profile_db):
    ctx = route_client(med_router, "/medications", profile_id=PROFILE)
    client = ctx.__enter__()

    async def _override_profile_db():
        return profile_db

    client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
    return ctx, client


async def _seed(db: AsyncSession, with_schedule: bool = False) -> str:
    med = Medication(
        id=str(uuid.uuid4()), profile_id=PROFILE, name="Metformin",
        frequency="once_daily", is_active=True, reminder_enabled=False,
    )
    db.add(med)
    await db.commit()
    if with_schedule:
        db.add(MedicationSchedule(
            id=str(uuid.uuid4()), medication_id=med.id,
            schedule_label="morning", target_time=time(8, 0),
            reminder_offset_minutes=15, is_active=True,
        ))
        await db.commit()
    return med.id


@pytest.mark.asyncio
async def test_hc_med_http_001_create_returns_201_with_empty_schedules(profile_db):
    ctx, client = _client(profile_db)
    try:
        resp = client.post("/medications/", json={"name": "Aspirin"})
        assert resp.status_code == 201, resp.text
        assert resp.json()["schedules"] == []
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_med_http_002_create_persists_exactly_one_row(profile_db):
    ctx, client = _client(profile_db)
    try:
        client.post("/medications/", json={"name": "Aspirin"})
        count = (await profile_db.execute(select(func.count()).select_from(Medication))).scalar_one()
        assert count == 1
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_med_http_003_update_returns_200_with_schedules(profile_db):
    med_id = await _seed(profile_db, with_schedule=True)
    ctx, client = _client(profile_db)
    try:
        resp = client.patch(f"/medications/{med_id}", json={"instructions": "with food"})
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["schedules"]) == 1
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_med_http_004_list_returns_schedules(profile_db):
    await _seed(profile_db, with_schedule=True)
    ctx, client = _client(profile_db)
    try:
        resp = client.get("/medications/")
        assert resp.status_code == 200, resp.text
        assert len(resp.json()[0]["schedules"]) == 1
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_med_http_005_get_returns_schedules(profile_db):
    med_id = await _seed(profile_db, with_schedule=True)
    ctx, client = _client(profile_db)
    try:
        resp = client.get(f"/medications/{med_id}")
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["schedules"]) == 1
    finally:
        ctx.__exit__(None, None, None)


# MED-UTC: client datetimes are stored naive UTC. SQLite drops tzinfo, so an
# un-normalised "-07:00" value would be stored as local wall-clock time.
@pytest.mark.asyncio
async def test_hc_med_http_006_update_ended_at_offset_stored_naive_utc(profile_db):
    med_id = await _seed(profile_db)
    ctx, client = _client(profile_db)
    try:
        resp = client.patch(f"/medications/{med_id}", json={"ended_at": "2026-03-02T23:00:00-07:00"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["ended_at"] == "2026-03-03T06:00:00"
    finally:
        ctx.__exit__(None, None, None)
    profile_db.expire_all()
    med = (await profile_db.execute(select(Medication).where(Medication.id == med_id))).scalar_one()
    assert med.ended_at == datetime(2026, 3, 3, 6, 0)


@pytest.mark.asyncio
async def test_hc_med_http_007_create_started_at_offset_stored_naive_utc(profile_db):
    ctx, client = _client(profile_db)
    try:
        resp = client.post("/medications/", json={"name": "Aspirin", "started_at": "2026-03-02T23:00:00-07:00"})
        assert resp.status_code == 201, resp.text
        assert resp.json()["started_at"] == "2026-03-03T06:00:00"
    finally:
        ctx.__exit__(None, None, None)
    med = (await profile_db.execute(select(Medication))).scalar_one()
    assert med.started_at == datetime(2026, 3, 3, 6, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sent", "stored"),
    [
        ("2026-03-02T23:30:00-07:00", datetime(2026, 3, 3, 6, 30)),  # local evening = next UTC day
        ("2026-03-03T06:30:00Z", datetime(2026, 3, 3, 6, 30)),  # frontend toISOString()
        ("2026-03-02T23:30:00", datetime(2026, 3, 2, 23, 30)),  # naive = already UTC, unchanged
    ],
)
async def test_hc_med_http_008_log_dose_taken_at_stored_naive_utc(profile_db, sent, stored):
    med_id = await _seed(profile_db)
    ctx, client = _client(profile_db)
    try:
        resp = client.post(f"/medications/{med_id}/doses", json={"taken_at": sent})
        assert resp.status_code == 201, resp.text
        assert resp.json()["dose"]["taken_at"] == stored.isoformat()
        listed = client.get(f"/medications/{med_id}/doses")
        assert listed.status_code == 200, listed.text
        assert listed.json()[0]["taken_at"] == stored.isoformat()
    finally:
        ctx.__exit__(None, None, None)
    dose = (await profile_db.execute(select(DoseTaken))).scalar_one()
    assert dose.taken_at == stored


@pytest.mark.asyncio
async def test_hc_med_http_009_list_doses_offset_filter_compares_in_utc(profile_db):
    med_id = await _seed(profile_db)
    profile_db.add(DoseTaken(
        id=str(uuid.uuid4()), medication_id=med_id, taken_at=datetime(2026, 3, 3, 6, 30),
        log_method="manual", was_skipped=False, logged_at=datetime(2026, 3, 3, 6, 30),
    ))
    await profile_db.commit()
    ctx, client = _client(profile_db)
    try:
        # 23:00-07:00 == 06:00Z (dose after), 23:45-07:00 == 06:45Z (dose before)
        inside = client.get(f"/medications/{med_id}/doses", params={"from_date": "2026-03-02T23:00:00-07:00"})
        after = client.get(f"/medications/{med_id}/doses", params={"from_date": "2026-03-02T23:45:00-07:00"})
    finally:
        ctx.__exit__(None, None, None)
    assert inside.status_code == 200, inside.text
    assert len(inside.json()) == 1
    assert after.status_code == 200, after.text
    assert after.json() == []


class _FrozenMar3(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 3, 3, 12, 0, tzinfo=tz or timezone.utc)


@pytest.mark.asyncio
async def test_hc_med_http_010_offset_ended_at_cutoff_in_streaks(profile_db, monkeypatch):
    # Ended 20:00-07:00 == 03:00Z Mar 3. A 01:00Z Mar 3 dose is before the end
    # and must count; storing 20:00 Mar 2 would wrongly cut it off (Q2).
    med_id = await _seed(profile_db)
    ctx, client = _client(profile_db)
    try:
        assert client.patch(f"/medications/{med_id}", json={"ended_at": "2026-03-02T20:00:00-07:00"}).status_code == 200
        assert client.post(f"/medications/{med_id}/doses", json={"taken_at": "2026-03-03T01:00:00Z"}).status_code == 201
    finally:
        ctx.__exit__(None, None, None)

    async def _override_profile_db():
        return profile_db

    monkeypatch.setattr(gamification_api, "datetime", _FrozenMar3)
    with route_client(gamification_api.router, "/gamification", profile_id=PROFILE) as gclient:
        gclient.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = gclient.get("/gamification/streaks")
    assert resp.status_code == 200, resp.text
    assert resp.json()["current_streak_days"] == 1
