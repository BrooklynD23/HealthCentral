"""ADHERE-TZ: pattern learning buckets doses in the profile time zone.

taken_at is stored naive UTC (MED-UTC); time-of-day and day-of-week buckets
must be computed on the profile's local wall clock, through HTTP.
"""

import uuid
from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import select

import modules.adherence_patterns as adherence_patterns
from models import DoseTaken, MedicationSchedule, UserModelSettings
from tests.test_medications_routes_http import _client, _seed, profile_db  # noqa: F401

LA = "America/Los_Angeles"


async def _setup(db, tz, doses, monkeypatch, now):
    """Seed a medication with one schedule, profile tz, and naive-UTC doses."""
    med_id = await _seed(db, with_schedule=True)
    sched = (await db.execute(select(MedicationSchedule))).scalar_one()
    db.add(UserModelSettings(profile_id="profile-a", timezone=tz))
    for taken_at, skipped in doses:
        db.add(DoseTaken(
            id=str(uuid.uuid4()), medication_id=med_id, schedule_id=sched.id,
            taken_at=taken_at, log_method="manual", was_skipped=skipped,
        ))
    await db.commit()
    monkeypatch.setattr(adherence_patterns, "utcnow", lambda: now)
    return med_id, sched


def _learn(db, med_id):
    ctx, client = _client(db)
    try:
        resp = client.post(f"/medications/{med_id}/learn-patterns")
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_hc_adhere_tz_001_morning_across_dst_is_local_morning(profile_db, monkeypatch):
    # 08:00 LA daily Mar 2-13 2026; DST starts Mar 8 -> 16:00Z before, 15:00Z after.
    doses = [
        (datetime(2026, 3, d, 16 if d < 8 else 15, 0), False) for d in range(2, 14)
    ]
    med_id, sched = await _setup(profile_db, LA, doses, monkeypatch, datetime(2026, 3, 14, 0, 0))
    body = _learn(profile_db, med_id)
    assert body["time_window"]["avg_time"] == "08:00"
    assert body["time_window"]["window_start"] == "08:00"
    assert body["time_window"]["window_end"] == "08:00"
    # SCHED-TZ: the stored adaptive window is in the profile-local frame.
    assert body["schedules_updated"] == 1
    await profile_db.refresh(sched)
    assert sched.adaptive_window_start <= time(8, 0) <= sched.adaptive_window_end
    assert sched.adaptive_window_tz == LA


@pytest.mark.asyncio
async def test_hc_adhere_tz_002_weekday_weekend_split_uses_local_day(profile_db, monkeypatch):
    # Jan 2026 (PST, UTC-8). Weekdays 20:00 local (= 04:00Z next day, so Fri
    # evening is Sat in UTC); weekends 10:00 local (= 18:00Z same day).
    doses = []
    for d in range(5, 26):  # Mon Jan 5 .. Sun Jan 25
        local_day = datetime(2026, 1, d)
        if local_day.weekday() < 5:
            doses.append((local_day + timedelta(hours=20 + 8), False))
        else:
            doses.append((local_day + timedelta(hours=10 + 8), False))
    med_id, _ = await _setup(profile_db, LA, doses, monkeypatch, datetime(2026, 1, 27, 0, 0))
    body = _learn(profile_db, med_id)
    assert body["weekday_pattern"]["weekday_avg"] == "20:00"
    assert body["weekday_pattern"]["weekend_avg"] == "10:00"


@pytest.mark.asyncio
async def test_hc_adhere_tz_003_missed_day_is_local_weekday(profile_db, monkeypatch):
    # Daily 20:00 PST (= 04:00Z next day); every local Monday is skipped.
    doses = []
    for d in range(5, 26):
        local_day = datetime(2026, 1, d)
        doses.append((local_day + timedelta(hours=28), local_day.weekday() == 0))
    med_id, _ = await _setup(profile_db, LA, doses, monkeypatch, datetime(2026, 1, 27, 0, 0))
    body = _learn(profile_db, med_id)
    assert [m["day"] for m in body["missed_days"]] == ["Monday"]


@pytest.mark.asyncio
async def test_hc_adhere_tz_004_streak_counts_local_today(profile_db, monkeypatch):
    # 09:00 PST Jan 13-15 (17:00Z). Now = Jan 15 17:00 PST = Jan 16 01:00Z:
    # locally today has a dose, so the streak is 3 (UTC "today" would give 0).
    # Extra 16:30 PST Jan 15 dose is Jan 16 in UTC: still one local day.
    doses = [(datetime(2026, 1, d, 17, 0), False) for d in (13, 14, 15)]
    doses.append((datetime(2026, 1, 16, 0, 30), False))
    med_id, _ = await _setup(profile_db, LA, doses, monkeypatch, datetime(2026, 1, 16, 1, 0))
    body = _learn(profile_db, med_id)
    assert body["streak"]["current_streak"] == 3
    assert body["streak"]["total_adherent_days"] == 3


@pytest.mark.asyncio
async def test_hc_adhere_tz_005_utc_profile_unchanged(profile_db, monkeypatch):
    doses = [(datetime(2026, 3, d, 8, 0), False) for d in range(2, 14)]
    med_id, _ = await _setup(profile_db, "UTC", doses, monkeypatch, datetime(2026, 3, 14, 0, 0))
    assert _learn(profile_db, med_id)["time_window"]["avg_time"] == "08:00"


@pytest.mark.asyncio
async def test_hc_adhere_tz_006_invalid_zone_falls_back_to_utc(profile_db, monkeypatch):
    doses = [(datetime(2026, 3, d, 15, 0), False) for d in range(2, 14)]
    med_id, _ = await _setup(profile_db, "Mars/Olympus", doses, monkeypatch, datetime(2026, 3, 14, 0, 0))
    assert _learn(profile_db, med_id)["time_window"]["avg_time"] == "15:00"
