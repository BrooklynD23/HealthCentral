"""UTC-SWEEP: client datetimes outside medications are normalised to naive UTC.

SQLite drops tzinfo when binding, so an un-normalised "+05:00" value is
compared/stored as local wall-clock time. Every case goes through HTTP.

Fixture: one hemoglobin observation at 2026-03-01 19:45 (naive UTC).
"2026-03-02T00:30:00+05:00" == 19:30Z Mar 1 (just before it, previous UTC day);
"2026-03-02T01:00:00+05:00" == 20:00Z Mar 1 (just after it).
"""

import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.export as export_api
import api.interpretations as interp_api
import api.notifications as notif_api
import api.observations as obs_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Document, Medication, Observation, ReminderLog
from tests.support.routes import route_client

PROFILE = "profile-a"
OBS_AT = datetime(2026, 3, 1, 19, 45)

# (filter param, value sent, observation included?) - offset near midnight,
# plus Z and naive inputs that must behave exactly as before.
FILTER_CASES = [
    ("from_date", "2026-03-02T00:30:00+05:00", True),
    ("from_date", "2026-03-02T01:00:00+05:00", False),
    ("from_date", "2026-03-01T19:30:00Z", True),
    ("from_date", "2026-03-01T20:00:00", False),
    ("to_date", "2026-03-02T00:30:00+05:00", False),
    ("to_date", "2026-03-02T01:00:00+05:00", True),
    ("to_date", "2026-03-01T20:00:00Z", True),
    ("to_date", "2026-03-01T19:30:00", False),
]


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


async def _seed_obs(db: AsyncSession) -> str:
    doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
    db.add(Document(
        id=doc_id, profile_id=PROFILE, path_hash="p" * 64, content_hash="c" * 64,
        doc_type="lab_report", status="verified", imported_at=OBS_AT,
    ))
    db.add(Observation(
        id=obs_id, profile_id=PROFILE, doc_id=doc_id, analyte_canonical="hemoglobin",
        analyte_raw="Hemoglobin", value=9.0, unit="g/dL", ref_low=12.0, ref_high=16.0,
        flag="L", is_abnormal=True, user_verified=True, collected_at=OBS_AT,
    ))
    await db.commit()
    return obs_id


def _get(router, prefix, profile_db, method, url, **kwargs):
    with route_client(router, prefix, profile_id=PROFILE) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.request(method, url, **kwargs)


# --- observations.py ---------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sent", "stored"),
    [
        ("2026-03-02T00:30:00+05:00", datetime(2026, 3, 1, 19, 30)),
        ("2026-03-01T19:30:00Z", datetime(2026, 3, 1, 19, 30)),
        ("2026-03-01T19:30:00", datetime(2026, 3, 1, 19, 30)),
    ],
)
async def test_hc_utc_001_verify_collected_at_stored_naive_utc(profile_db, sent, stored):
    obs_id = await _seed_obs(profile_db)
    resp = _get(obs_api.router, "/observations", profile_db, "POST",
                f"/observations/{obs_id}/verify", json={"collected_at": sent})
    assert resp.status_code == 200, resp.text
    assert resp.json()["collected_at"] == stored.isoformat()
    profile_db.expire_all()
    obs = (await profile_db.execute(select(Observation))).scalar_one()
    assert obs.collected_at == stored


@pytest.mark.asyncio
@pytest.mark.parametrize(("param", "sent", "included"), FILTER_CASES)
async def test_hc_utc_002_list_observations_date_filter_in_utc(profile_db, param, sent, included):
    await _seed_obs(profile_db)
    resp = _get(obs_api.router, "/observations", profile_db, "GET",
                "/observations/", params={param: sent})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == int(included)


@pytest.mark.asyncio
@pytest.mark.parametrize(("param", "sent", "included"), FILTER_CASES)
async def test_hc_utc_003_trend_date_filter_in_utc(profile_db, param, sent, included):
    await _seed_obs(profile_db)
    resp = _get(obs_api.router, "/observations", profile_db, "GET",
                "/observations/trends/hemoglobin", params={param: sent})
    # The route 404s when the window holds no points.
    assert resp.status_code == (200 if included else 404), resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sent", "found"),
    [
        ("2026-03-02T00:30:00+05:00", True),  # 19:30Z Mar 1 -> UTC day Mar 1
        ("2026-03-01T22:00:00Z", True),
        ("2026-03-02T10:00:00", False),  # naive = UTC Mar 2, unchanged
    ],
)
async def test_hc_utc_004_panel_collection_date_day_in_utc(profile_db, sent, found):
    await _seed_obs(profile_db)
    resp = _get(obs_api.router, "/observations", profile_db, "GET",
                "/observations/panels/cbc", params={"collection_date": sent})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["observations"]) == int(found)


# --- notifications.py --------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(("param", "sent", "included"), FILTER_CASES)
async def test_hc_utc_005_notification_history_date_filter_in_utc(profile_db, param, sent, included):
    med_id = str(uuid.uuid4())
    profile_db.add(Medication(id=med_id, profile_id=PROFILE, name="Metformin",
                              frequency="once_daily", is_active=True, reminder_enabled=False))
    profile_db.add(ReminderLog(
        id=str(uuid.uuid4()), profile_id=PROFILE, medication_id=med_id,
        reminder_type="initial", message_tone="friendly", message="Time for Metformin",
        sent_at=OBS_AT, delivery_method="in_app",
    ))
    await profile_db.commit()
    resp = _get(notif_api.router, "/notifications", profile_db, "GET",
                "/notifications/history", params={param: sent})
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == int(included)


# --- interpretations.py ------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sent", "day"),
    [
        ("2026-03-02T00:30:00+05:00", "2026-03-01"),
        ("2026-03-01T22:00:00Z", "2026-03-01"),
        ("2026-03-02T10:00:00", "2026-03-02"),
    ],
)
async def test_hc_utc_006_panel_interpret_collected_at_day_in_utc(profile_db, sent, day):
    # Empty profile: the 404 names the UTC day the route searched.
    resp = _get(interp_api.router, "/interpretations", profile_db, "POST",
                "/interpretations/panels/cbc/interpret", params={"collected_at": sent})
    assert resp.status_code == 404, resp.text
    assert f"on {day}" in resp.json()["detail"]


# --- export.py ---------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(("param", "sent", "included"), FILTER_CASES)
async def test_hc_utc_007_export_csv_date_filter_in_utc(profile_db, param, sent, included):
    await _seed_obs(profile_db)
    resp = _get(export_api.router, "/export", profile_db, "GET",
                "/export/csv", params={param: sent})
    assert resp.status_code == 200, resp.text
    assert ("hemoglobin" in resp.text.lower()) is included


@pytest.mark.asyncio
@pytest.mark.parametrize(("param", "sent", "included"), FILTER_CASES)
async def test_hc_utc_008_export_json_date_filter_in_utc(profile_db, param, sent, included):
    await _seed_obs(profile_db)
    resp = _get(export_api.router, "/export", profile_db, "GET",
                "/export/json", params={param: sent})
    assert resp.status_code == 200, resp.text
    assert ("hemoglobin" in resp.text.lower()) is included


@pytest.mark.asyncio
@pytest.mark.parametrize(("param", "sent", "included"), FILTER_CASES)
async def test_hc_utc_009_questions_date_filter_in_utc(profile_db, param, sent, included):
    await _seed_obs(profile_db)
    resp = _get(export_api.router, "/export", profile_db, "POST",
                "/export/questions", params={param: sent})
    assert resp.status_code == 200, resp.text
    assert any(q["category"] == "abnormal" for q in resp.json()) is included


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("param", "sent", "included", "label"),
    [
        ("from_date", "2026-03-02T00:30:00+05:00", True, "Since 2026-03-01"),
        ("from_date", "2026-03-02T01:00:00+05:00", False, "Since 2026-03-01"),
        ("from_date", "2026-03-01T19:30:00Z", True, "Since 2026-03-01"),
        ("from_date", "2026-03-01T20:00:00", False, "Since 2026-03-01"),
        ("to_date", "2026-03-02T00:30:00+05:00", False, "Until 2026-03-01"),
        ("to_date", "2026-03-02T01:00:00+05:00", True, "Until 2026-03-01"),
        ("to_date", "2026-03-01T20:00:00Z", True, "Until 2026-03-01"),
        ("to_date", "2026-03-01T19:30:00", False, "Until 2026-03-01"),
    ],
)
async def test_hc_utc_010_doctor_summary_date_range_in_utc(profile_db, param, sent, included, label):
    await _seed_obs(profile_db)
    resp = _get(export_api.router, "/export", profile_db, "POST",
                "/export/doctor-summary", json={param: sent})
    assert resp.status_code == 200, resp.text
    assert resp.json()["abnormal_count"] == int(included)
    assert resp.json()["date_range"] == label


@pytest.mark.asyncio
@pytest.mark.parametrize(("param", "sent", "included"), FILTER_CASES)
async def test_hc_utc_011_visit_prep_date_filter_in_utc(profile_db, param, sent, included):
    await _seed_obs(profile_db)
    resp = _get(export_api.router, "/export", profile_db, "POST",
                "/export/visit-prep", json={param: sent, "confirm": True})
    assert resp.status_code == 200, resp.text
    assert ("hemoglobin" in resp.json()["markdown"].lower()) is included
