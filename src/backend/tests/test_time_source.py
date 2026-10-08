"""HC-TIME-001…005 — pin the naive-UTC semantics the codebase relies on.

CLAUDE.md names core.time.utcnow the single timestamp helper. These tests pin
WHY the datetime.utcnow() migration is safe: stored timestamps are naive, and
utcnow() must stay naive so comparisons never raise TypeError.
"""
import re
from datetime import datetime, time, timedelta
from types import SimpleNamespace

import pytest

from core.time import UTC, utcfromtimestamp, utcnow

NAIVE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{6})?$")


def test_hc_time_001_utcnow_returns_naive_utc():
    now = utcnow()
    assert now.tzinfo is None
    # Same instant as aware now, minus the tzinfo — the utcnow() contract.
    aware_now = datetime.now(UTC)
    assert abs((aware_now.replace(tzinfo=None) - now).total_seconds()) < 2


def test_hc_time_002_utcnow_compares_against_stored_naive_values():
    # Rows come back from DateTime columns as naive datetimes. If utcnow()
    # ever went aware, this subtraction (and every cutoff comparison in
    # adherence_patterns / notification_scheduler) would raise TypeError.
    stored = datetime(2026, 1, 1, 12, 0, 0)
    assert utcnow() - stored > timedelta(0)


def test_hc_time_003_scheduler_day_boundary_stays_naive():
    # notification_scheduler builds today_start = combine(utcnow().date(), 0:00)
    # and compares it to naive stored reminder times.
    today_start = datetime.combine(utcnow().date(), time(0, 0))
    stored_reminder = datetime(2026, 9, 25, 8, 30)
    _ = stored_reminder < today_start  # must not raise TypeError


def test_hc_time_004_utcfromtimestamp_is_naive_too():
    assert utcfromtimestamp(0).tzinfo is None
    assert utcfromtimestamp(0) == datetime(1970, 1, 1, 0, 0, 0)


def test_hc_time_005_profile_responses_serialize_naive_iso():
    # D13: the auth-file swaps must not change what the profile routes return.
    # ProfileResponse.from_model is what create_profile / login / unlock return.
    from api.profiles import ProfileResponse

    profile = SimpleNamespace(
        id="p1",
        display_name="T",
        is_locked=False,
        password_hash=None,
        created_at=utcnow(),
        last_accessed_at=utcnow(),
    )
    body = ProfileResponse.from_model(profile)
    assert NAIVE_ISO.match(body.created_at), body.created_at
    assert NAIVE_ISO.match(body.last_accessed_at), body.last_accessed_at
    # Same shape the deprecated helper produced: no offset, no "Z".
    assert NAIVE_ISO.match(datetime(2026, 1, 1, 12, 0, 0, 123456).isoformat())


class _RecordingDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


@pytest.mark.asyncio
async def test_hc_time_006_badge_earned_at_is_naive_utc():
    # TIME-03 (owner row P5-SCOPE): the badge timestamp is persisted to a naive
    # DateTime column, so it must be naive UTC like every other timestamp.
    from models.gamification import EarnedBadge
    from modules.badge_evaluator import evaluate_badges_after_dose

    dose = SimpleNamespace(
        medication_id="m1",
        taken_at=utcnow(),
        schedule_id=None,
        variance_minutes=None,
        was_skipped=False,
    )
    db = _RecordingDb()
    results = await evaluate_badges_after_dose(
        profile_id="p1",
        medication_id="m1",
        doses_for_medication=[dose],
        all_profile_doses=[dose],
        timezone="UTC",
        existing_badge_keys=set(),
        db=db,
    )
    assert "first-log" in [r.badge_id for r in results]
    assert all(r.earned_at.tzinfo is None for r in results)
    recorded = [o for o in db.added if isinstance(o, EarnedBadge)]
    assert recorded
    for badge in recorded:
        assert badge.earned_at.tzinfo is None
        assert abs((utcnow() - badge.earned_at).total_seconds()) < 2
