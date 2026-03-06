"""Tests for badge evaluation logic."""

from datetime import datetime, date, timedelta, timezone as dt_timezone
from unittest.mock import MagicMock

import pytest

from modules.badge_evaluator import evaluate_badges_after_dose


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
            db=MagicMock(),
            as_of_date=date(2026, 3, 4),
        )
        badge_ids = [b.badge_id for b in result]
        assert "first-log" in badge_ids


class TestStreakBadges:
    @pytest.mark.asyncio
    async def test_seven_day_streak_earns_week_warrior(self):
        start = date(2026, 2, 26)
        doses = [
            _make_dose(
                datetime.combine(
                    start + timedelta(days=i),
                    datetime.min.time(),
                    tzinfo=dt_timezone.utc,
                ).replace(hour=8).isoformat()
            )
            for i in range(7)
        ]
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses,
            all_profile_doses=doses,
            timezone="UTC",
            existing_badge_keys={"first-log:"},
            db=MagicMock(),
            as_of_date=date(2026, 3, 4),
        )
        badge_ids = [b.badge_id for b in result]
        assert "week-warrior" in badge_ids

    @pytest.mark.asyncio
    async def test_already_earned_badge_not_duplicated(self):
        start = date(2026, 2, 26)
        doses = [
            _make_dose(
                datetime.combine(
                    start + timedelta(days=i),
                    datetime.min.time(),
                    tzinfo=dt_timezone.utc,
                ).replace(hour=8).isoformat()
            )
            for i in range(7)
        ]
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses,
            all_profile_doses=doses,
            timezone="UTC",
            existing_badge_keys={"first-log:", "week-warrior:med-1"},
            db=MagicMock(),
            as_of_date=date(2026, 3, 4),
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
            db=MagicMock(),
            as_of_date=date(2026, 3, 4),
        )
        badge_ids = [b.badge_id for b in result]
        assert "comeback-kid" in badge_ids
