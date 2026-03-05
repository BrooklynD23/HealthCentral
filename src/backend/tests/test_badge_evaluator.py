"""Tests for badge evaluation logic."""

import uuid
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from modules.badge_evaluator import evaluate_badges_after_dose, BadgeEvalResult


def _make_dose(taken_at_str, medication_id="med-1", was_skipped=False, variance_minutes=None, schedule_id=None):
    class MockDose:
        pass
    d = MockDose()
    d.taken_at = datetime.fromisoformat(taken_at_str)
    d.medication_id = medication_id
    d.was_skipped = was_skipped
    d.variance_minutes = variance_minutes
    d.schedule_id = schedule_id
    return d


class TestFirstLogBadge:
    @pytest.mark.asyncio
    async def test_first_dose_earns_first_log(self):
        """First ever dose should earn 'first-log' badge."""
        doses_for_med = [_make_dose("2026-03-04T10:00:00+00:00")]
        all_doses = doses_for_med
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses_for_med,
            all_profile_doses=all_doses,
            timezone="UTC",
            existing_badge_keys=set(),
            db=AsyncMock(),
        )
        badge_ids = [b.badge_id for b in result]
        assert "first-log" in badge_ids


class TestStreakBadges:
    @pytest.mark.asyncio
    async def test_seven_day_streak_earns_week_warrior(self):
        doses = [
            _make_dose(f"2026-02-{26 + i:02d}T08:00:00+00:00")
            for i in range(7)
        ]
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses,
            all_profile_doses=doses,
            timezone="UTC",
            existing_badge_keys={"first-log:"},
            db=AsyncMock(),
        )
        badge_ids = [b.badge_id for b in result]
        assert "week-warrior" in badge_ids

    @pytest.mark.asyncio
    async def test_already_earned_badge_not_duplicated(self):
        doses = [
            _make_dose(f"2026-02-{26 + i:02d}T08:00:00+00:00")
            for i in range(7)
        ]
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses,
            all_profile_doses=doses,
            timezone="UTC",
            existing_badge_keys={"first-log:", "week-warrior:med-1"},
            db=AsyncMock(),
        )
        badge_ids = [b.badge_id for b in result]
        assert "week-warrior" not in badge_ids


class TestComebackKid:
    @pytest.mark.asyncio
    async def test_comeback_after_gap(self):
        doses = [
            _make_dose("2026-02-25T08:00:00+00:00"),
            # 3+ day gap
            _make_dose("2026-03-04T08:00:00+00:00"),
        ]
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses,
            all_profile_doses=doses,
            timezone="UTC",
            existing_badge_keys={"first-log:"},
            db=AsyncMock(),
        )
        badge_ids = [b.badge_id for b in result]
        assert "comeback-kid" in badge_ids
