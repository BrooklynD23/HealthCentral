"""HTTP tests for medication CRUD: MedicationResponse reads med.schedules,
which must be loaded eagerly under async SQLAlchemy (else MissingGreenlet/500)."""

import uuid
from datetime import time

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api.medications import router as med_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Medication, MedicationSchedule
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
