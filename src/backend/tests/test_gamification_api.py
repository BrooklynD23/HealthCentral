"""Tests for gamification API response models and routes."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.gamification import (
    BadgeListResponse,
    BadgeResponse,
    get_streaks,
)
from core.auth import Session
from models import UserModelSettings


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


@pytest.mark.asyncio
async def test_get_streaks_returns_profile_summary():
    profile_id = str(uuid.uuid4())
    settings = UserModelSettings(profile_id=profile_id, timezone="UTC")
    doses = [
        _StreakDose(datetime(2026, 3, 2, 8, 0, tzinfo=timezone.utc)),
        _StreakDose(datetime(2026, 3, 3, 8, 0, tzinfo=timezone.utc)),
        _StreakDose(datetime(2026, 3, 4, 8, 0, tzinfo=timezone.utc)),
    ]
    profile_db = _StreakProfileDb(settings, doses)
    session = Session(
        profile_id=profile_id,
        profile_name="Test",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 3, 4, 12, 0, tzinfo=tz or timezone.utc)

    with patch("api.gamification.datetime", _FrozenDateTime):
        response = await get_streaks(session=session, profile_db=profile_db)

    assert response.current_streak_days == 3
    assert response.longest_streak_days == 3
    assert response.timezone == "UTC"
    assert response.as_of_date == "2026-03-04"
