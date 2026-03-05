"""Tests for timezone-aware streak computation engine."""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import pytest

from modules.streak_engine import compute_streak, compute_longest_streak, detect_comeback_gap


def _make_dose(taken_at_str: str):
    """Helper: create a mock dose with taken_at as datetime."""
    class MockDose:
        def __init__(self, taken_at):
            self.taken_at = taken_at
            self.was_skipped = False
    return MockDose(datetime.fromisoformat(taken_at_str))


class TestComputeStreak:
    def test_empty_doses_returns_zero(self):
        assert compute_streak([], "UTC", date(2026, 3, 4)) == 0

    def test_single_dose_today(self):
        doses = [_make_dose("2026-03-04T10:00:00+00:00")]
        assert compute_streak(doses, "UTC", date(2026, 3, 4)) == 1

    def test_three_day_streak(self):
        doses = [
            _make_dose("2026-03-02T08:00:00+00:00"),
            _make_dose("2026-03-03T09:00:00+00:00"),
            _make_dose("2026-03-04T10:00:00+00:00"),
        ]
        assert compute_streak(doses, "UTC", date(2026, 3, 4)) == 3

    def test_gap_breaks_streak(self):
        doses = [
            _make_dose("2026-03-01T08:00:00+00:00"),
            # gap on March 2
            _make_dose("2026-03-03T09:00:00+00:00"),
            _make_dose("2026-03-04T10:00:00+00:00"),
        ]
        assert compute_streak(doses, "UTC", date(2026, 3, 4)) == 2

    def test_timezone_shifts_date_boundary(self):
        """Dose at 23:30 UTC = March 5 in UTC, but still March 4 in US/Pacific (UTC-7)."""
        doses = [_make_dose("2026-03-04T23:30:00+00:00")]
        # In UTC, this is March 4 → streak on March 4
        assert compute_streak(doses, "UTC", date(2026, 3, 4)) == 1
        # In US/Pacific (UTC-7), 23:30 UTC = 16:30 Pacific on March 4
        assert compute_streak(doses, "America/Los_Angeles", date(2026, 3, 4)) == 1

    def test_ended_medication_as_of_date(self):
        """Streak computed as-of min(today, ended_at)."""
        doses = [
            _make_dose("2026-02-28T08:00:00+00:00"),
            _make_dose("2026-03-01T08:00:00+00:00"),
        ]
        # ended March 1, today is March 4 → compute as-of March 1
        assert compute_streak(doses, "UTC", date(2026, 3, 1)) == 2


class TestComputeLongestStreak:
    def test_empty(self):
        assert compute_longest_streak([], "UTC") == 0

    def test_single_dose(self):
        doses = [_make_dose("2026-03-04T10:00:00+00:00")]
        assert compute_longest_streak(doses, "UTC") == 1

    def test_gap_resets(self):
        doses = [
            _make_dose("2026-03-01T08:00:00+00:00"),
            _make_dose("2026-03-02T08:00:00+00:00"),
            # gap
            _make_dose("2026-03-04T08:00:00+00:00"),
            _make_dose("2026-03-05T08:00:00+00:00"),
            _make_dose("2026-03-06T08:00:00+00:00"),
        ]
        assert compute_longest_streak(doses, "UTC") == 3


class TestDetectComebackGap:
    def test_no_gap(self):
        doses = [
            _make_dose("2026-03-03T08:00:00+00:00"),
            _make_dose("2026-03-04T08:00:00+00:00"),
        ]
        assert detect_comeback_gap(doses, "UTC") is False

    def test_three_day_gap(self):
        doses = [
            _make_dose("2026-02-28T08:00:00+00:00"),
            # gap: March 1, 2, 3
            _make_dose("2026-03-04T08:00:00+00:00"),
        ]
        assert detect_comeback_gap(doses, "UTC") is True
