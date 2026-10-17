"""Tests for gamification API response models and routes."""

from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import api.gamification as gamification_api
from api.gamification import (
    BadgeListResponse,
    BadgeResponse,
)
from core.auth import get_profile_db_session, require_auth
from core.profile_database import ProfileDatabaseBase
from models import BadgeDefinition, DoseTaken, EarnedBadge, Medication, UserModelSettings
from tests.support.routes import route_client


class _ScalarResult:
    def __init__(self, one=None, all_items=None):
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._all_items


class _StreakDose:
    def __init__(self, taken_at: datetime):
        self.taken_at = taken_at
        self.was_skipped = False


class _StreakProfileDb:
    def __init__(self, settings, doses):
        self._settings = settings
        self._doses = doses
        self._execute_calls = 0

    async def execute(self, _stmt):
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _ScalarResult(one=self._settings)
        return _ScalarResult(all_items=self._doses)


def test_badge_response_shape():
    br = BadgeResponse(
        id="week-warrior",
        name="Week Warrior",
        description="7 consecutive days",
        icon="flame",
        criteria_type="streak",
        earned=True,
        earned_at="2026-03-04T10:00:00",
        medication_id="med-1",
    )
    assert br.earned is True
    assert br.id == "week-warrior"


def test_badge_list_response():
    blr = BadgeListResponse(badges=[])
    assert blr.badges == []


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="time.tzset is POSIX-only")
def test_get_streaks_http_naive_utc_on_non_utc_machine(monkeypatch):
    """DoseTaken.taken_at is naive UTC; machine-local TZ must not shift the day."""
    import api.gamification as gamification_api
    from core.auth import get_profile_db_session

    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    try:
        settings = UserModelSettings(profile_id="profile-a", timezone="UTC")
        doses = [
            _StreakDose(datetime(2026, 3, 2, 22, 0)),
            _StreakDose(datetime(2026, 3, 3, 22, 0)),
            _StreakDose(datetime(2026, 3, 4, 22, 0)),
        ]

        class _FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 3, 4, 23, 30, tzinfo=tz or timezone.utc)

        async def _profile_db():
            return _StreakProfileDb(settings, doses)

        monkeypatch.setattr(gamification_api, "datetime", _FrozenDateTime)
        with route_client(gamification_api.router, "/gamification", master_db=_master_db()) as client:
            client.app.dependency_overrides[get_profile_db_session] = _profile_db
            response = client.get("/gamification/streaks")
    finally:
        monkeypatch.undo()
        time.tzset()

    assert response.status_code == 200
    assert response.json()["current_streak_days"] == 3


# --- HTTP route tests (GAMIFICATION-V2 task 1 / task 3) ---------------------
# Through FastAPI's dependency graph (recurring-failures #1): auth, profile
# scoping, mandatory view audit rows (fail-closed), ended-medication rule (Q2).

PROFILE_A = "profile-a"
PROFILE_B = "profile-b"
ROUTES = ["/gamification/badges", "/gamification/streaks"]


def _master_db(commit_error: Exception | None = None) -> MagicMock:
    db = MagicMock()
    db.commit = AsyncMock(side_effect=commit_error)
    return db


class _FrozenNow(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 3, 4, 12, 0, tzinfo=tz or timezone.utc)


@pytest_asyncio.fixture
async def gam_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _seed_med(db, profile_id, days, ended_at=None) -> str:
    med = Medication(
        id=str(uuid.uuid4()), profile_id=profile_id, name="Med",
        frequency="once_daily", is_active=ended_at is None,
        reminder_enabled=False, ended_at=ended_at,
    )
    db.add(med)
    for day in days:
        db.add(DoseTaken(
            id=str(uuid.uuid4()), medication_id=med.id,
            taken_at=datetime(2026, 3, day, 8, 0), log_method="manual",
            was_skipped=False,
        ))
    await db.commit()
    return med.id


def _get(path, profile_db, profile_id=PROFILE_A, master_db=None):
    master_db = master_db if master_db is not None else _master_db()
    with route_client(
        gamification_api.router, "/gamification",
        profile_id=profile_id, master_db=master_db,
    ) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        return client.get(path), master_db


@pytest.mark.parametrize("path", ROUTES)
def test_hc_gam_http_001_requires_auth(path):
    with route_client(gamification_api.router, "/gamification", master_db=_master_db()) as client:
        client.app.dependency_overrides.pop(require_auth)
        response = client.get(path)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hc_gam_http_002_streaks_summary(gam_db, monkeypatch):
    await _seed_med(gam_db, PROFILE_A, [2, 3, 4])
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "current_streak_days": 3, "longest_streak_days": 3,
        "timezone": "UTC", "as_of_date": "2026-03-04",
        "active_days_last_28": 3, "weeks_with_log_last_4": 1,
    }


@pytest.mark.asyncio
async def test_hc_gam_http_013_streak_counts_through_yesterday(gam_db, monkeypatch):
    await _seed_med(gam_db, PROFILE_A, [1, 2, 3])
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    assert response.json()["current_streak_days"] == 3


@pytest.mark.asyncio
async def test_hc_gam_http_014_full_missed_day_ends_streak(gam_db, monkeypatch):
    await _seed_med(gam_db, PROFILE_A, [1, 2])
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    assert response.json()["current_streak_days"] == 0


@pytest.mark.asyncio
async def test_hc_gam_http_015_streak_through_yesterday_in_profile_zone(gam_db, monkeypatch):
    gam_db.add(UserModelSettings(profile_id=PROFILE_A, timezone="America/New_York"))
    await _seed_doses(gam_db, PROFILE_A, [datetime(2026, 3, d, 17, 0) for d in (1, 2, 3)])  # local noon EST
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)  # Mar 4 07:00 EST
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    assert response.json()["current_streak_days"] == 3


@pytest.mark.asyncio
async def test_hc_gam_http_003_streaks_isolated_by_profile(gam_db, monkeypatch):
    await _seed_med(gam_db, PROFILE_A, [4])
    await _seed_med(gam_db, PROFILE_B, [1, 2, 3])
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    assert response.json()["current_streak_days"] == 1
    assert response.json()["longest_streak_days"] == 1


@pytest.mark.asyncio
async def test_hc_gam_http_004_badges_isolated_by_profile(gam_db):
    gam_db.add(BadgeDefinition(
        id="first-log", name="First Log", description="d", icon="star",
        criteria_type="first_log", criteria_json="{}", sort_order=0,
    ))
    gam_db.add(EarnedBadge(
        id=str(uuid.uuid4()), profile_id=PROFILE_B, badge_id="first-log",
        medication_id="", earned_at=datetime(2026, 3, 4, 8, 0),
    ))
    await gam_db.commit()
    response, _ = _get("/gamification/badges", gam_db)
    assert response.status_code == 200, response.text
    badges = response.json()["badges"]
    assert [(b["id"], b["earned"]) for b in badges] == [("first-log", False)]


@pytest.mark.asyncio
@pytest.mark.parametrize("path,event_type", [
    ("/gamification/badges", "gamification.badges.view"),
    ("/gamification/streaks", "gamification.streaks.view"),
])
async def test_hc_gam_http_005_writes_view_audit_row(gam_db, path, event_type):
    response, master_db = _get(path, gam_db)
    assert response.status_code == 200, response.text
    rows = [c.args[0] for c in master_db.add.call_args_list]
    assert [(r.event_type, r.profile_id) for r in rows] == [(event_type, PROFILE_A)]
    # PHI-minimal: static action, no entity id, no details.
    assert (rows[0].action, rows[0].entity_id, rows[0].details_json) == (event_type, None, None)
    master_db.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ROUTES)
async def test_hc_gam_http_006_fails_closed_when_audit_cannot_commit(gam_db, path):
    master_db = _master_db(RuntimeError("audit commit failed"))
    with pytest.raises(RuntimeError, match="audit commit failed"):
        _get(path, gam_db, master_db=master_db)
    master_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_hc_gam_http_007_doses_after_ended_at_do_not_count(gam_db, monkeypatch):
    # Ended Mar 2 23:00 UTC: only Mar 1-2 count, the Mar 3-4 logs never do (Q2).
    await _seed_med(gam_db, PROFILE_A, [1, 2, 3, 4], ended_at=datetime(2026, 3, 2, 23, 0))
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    assert response.json()["longest_streak_days"] == 2
    assert response.json()["current_streak_days"] == 0


@pytest.mark.asyncio
async def test_hc_gam_http_008_active_med_keeps_day_when_other_ended(gam_db, monkeypatch):
    await _seed_med(gam_db, PROFILE_A, [1, 2, 3, 4], ended_at=datetime(2026, 3, 2, 23, 0))
    await _seed_med(gam_db, PROFILE_A, [3, 4])
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    assert response.json()["current_streak_days"] == 4


@pytest.mark.asyncio
async def test_hc_gam_http_009_dose_at_ended_at_counts(gam_db, monkeypatch):
    # Boundary: a dose logged exactly at ended_at still counts (<=, not <).
    await _seed_med(gam_db, PROFILE_A, [3, 4], ended_at=datetime(2026, 3, 4, 8, 0))
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    assert response.json()["current_streak_days"] == 2


# --- Engagement measure A (GAMIFICATION-V2 task 4) ---------------------------
# Derived on read from DoseTaken; window = the 28 profile-local days ending on
# as_of_date, split into four 7-day weeks counted back from as_of_date.


async def _seed_doses(db, profile_id, taken_ats, skipped=()) -> None:
    med = Medication(
        id=str(uuid.uuid4()), profile_id=profile_id, name="Med",
        frequency="once_daily", is_active=True, reminder_enabled=False,
    )
    db.add(med)
    for taken_at in [*taken_ats, *skipped]:
        db.add(DoseTaken(
            id=str(uuid.uuid4()), medication_id=med.id, taken_at=taken_at,
            log_method="manual", was_skipped=taken_at in skipped,
        ))
    await db.commit()


@pytest.mark.asyncio
async def test_hc_gam_http_010_engagement_window_edges(gam_db, monkeypatch):
    # as_of Mar 4 (UTC) -> window Feb 5..Mar 4.
    await _seed_doses(gam_db, PROFILE_A, [
        datetime(2026, 2, 4, 8, 0),    # day 29: out
        datetime(2026, 2, 5, 8, 0),    # day 28: in (week 4)
        datetime(2026, 2, 25, 8, 0),   # day 8: week 2
        datetime(2026, 2, 26, 8, 0),   # day 7: week 1
        datetime(2026, 3, 4, 8, 0),    # as_of: in (week 1)
        datetime(2026, 3, 4, 9, 0),    # same day: counted once
        datetime(2026, 3, 5, 8, 0),    # after as_of: out
    ], skipped=[datetime(2026, 3, 1, 8, 0)])  # skipped: out
    await _seed_doses(gam_db, PROFILE_B, [datetime(2026, 2, 27, 8, 0)])  # other profile
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["active_days_last_28"], body["weeks_with_log_last_4"]) == (4, 3)


class _FrozenAfterDst(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 3, 21, 2, 0, tzinfo=tz or timezone.utc)  # Mar 20 22:00 EDT


@pytest.mark.asyncio
async def test_hc_gam_http_011_engagement_uses_profile_timezone_across_dst(gam_db, monkeypatch):
    # New York, as_of Mar 20 (EDT) -> window Feb 21..Mar 20 spans the Mar 8 DST switch.
    gam_db.add(UserModelSettings(profile_id=PROFILE_A, timezone="America/New_York"))
    await _seed_doses(gam_db, PROFILE_A, [
        datetime(2026, 2, 21, 4, 30),  # Feb 20 23:30 EST: out
        datetime(2026, 2, 21, 5, 30),  # Feb 21 00:30 EST: in (week 4)
        datetime(2026, 3, 9, 3, 30),   # Mar 8 23:30 EDT: week 2
        datetime(2026, 3, 21, 1, 0),   # Mar 20 21:00 EDT: as_of, week 1
        datetime(2026, 3, 20, 4, 30),  # Mar 20 00:30 EDT: same day; fixed EST would read Mar 19
    ])
    monkeypatch.setattr(gamification_api, "datetime", _FrozenAfterDst)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["as_of_date"] == "2026-03-20"
    assert (body["active_days_last_28"], body["weeks_with_log_last_4"]) == (3, 3)


@pytest.mark.asyncio
async def test_hc_gam_http_012_engagement_zero_without_doses(gam_db, monkeypatch):
    monkeypatch.setattr(gamification_api, "datetime", _FrozenNow)
    response, _ = _get("/gamification/streaks", gam_db)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["active_days_last_28"], body["weeks_with_log_last_4"]) == (0, 0)
