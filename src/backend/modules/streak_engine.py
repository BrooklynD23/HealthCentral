"""Timezone-aware streak computation engine.

All streak calculations group DoseTaken.taken_at by calendar date
in the user's stored IANA timezone.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo


class HasTakenAt(Protocol):
    """Protocol for objects with taken_at and was_skipped."""
    taken_at: object  # datetime
    was_skipped: bool


def _dose_dates(doses: list[HasTakenAt], tz_name: str) -> set[date]:
    """Extract unique calendar dates from doses in the given timezone."""
    tz = ZoneInfo(tz_name)
    dates: set[date] = set()
    for dose in doses:
        if not dose.was_skipped:
            dt = dose.taken_at
            if hasattr(dt, 'astimezone'):
                dt = dt.astimezone(tz)
            dates.add(dt.date() if hasattr(dt, 'date') else dt)
    return dates


def compute_streak(doses: list[HasTakenAt], tz_name: str, as_of_date: date) -> int:
    """Count consecutive days with at least one non-skipped dose, backward from as_of_date."""
    dose_dates = _dose_dates(doses, tz_name)
    if not dose_dates:
        return 0

    streak = 0
    current = as_of_date
    while current in dose_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


def compute_longest_streak(doses: list[HasTakenAt], tz_name: str) -> int:
    """Calculate longest consecutive days with dose taken."""
    dose_dates = _dose_dates(doses, tz_name)
    if not dose_dates:
        return 0

    sorted_dates = sorted(dose_dates)
    longest = 1
    current = 1

    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


def detect_comeback_gap(doses: list[HasTakenAt], tz_name: str) -> bool:
    """Detect if the most recent dose follows a 3+ calendar day gap.

    Returns True if the latest dose was preceded by a gap of 3+ days
    (i.e., the second-to-last dose date is 4+ days before the latest).
    """
    dose_dates = sorted(_dose_dates(doses, tz_name))
    if len(dose_dates) < 2:
        return False

    latest = dose_dates[-1]
    previous = dose_dates[-2]
    return (latest - previous).days >= 4  # 3 full gap days means diff >= 4
