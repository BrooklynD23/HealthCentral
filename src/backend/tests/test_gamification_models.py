"""Tests for gamification models — badge definitions and earned badges.

RED phase: These tests define the expected behavior of BadgeDefinition
and EarnedBadge models before implementation is verified.
"""

import uuid
from datetime import datetime

import pytest

from models.gamification import BadgeDefinition, EarnedBadge


class TestBadgeDefinition:
    def test_fields(self):
        badge = BadgeDefinition(
            id="week-warrior",
            name="Week Warrior",
            description="7 consecutive days of adherence",
            icon="flame",
            criteria_type="streak",
            criteria_json='{"streak_days": 7}',
            sort_order=2,
        )
        assert badge.id == "week-warrior"
        assert badge.name == "Week Warrior"
        assert badge.criteria_type == "streak"
        assert badge.sort_order == 2

    def test_repr(self):
        badge = BadgeDefinition(id="first-log", name="First Log",
                                description="", icon="spark",
                                criteria_type="count", criteria_json="{}")
        assert "first-log" in repr(badge)
        assert "First Log" in repr(badge)


class TestEarnedBadge:
    def test_medication_specific_badge(self):
        eb = EarnedBadge(
            id=str(uuid.uuid4()),
            profile_id="profile-1",
            badge_id="week-warrior",
            medication_id="med-1",
            earned_at=datetime.utcnow(),
        )
        assert eb.medication_id == "med-1"
        assert eb.badge_id == "week-warrior"

    def test_global_badge_uses_empty_string(self):
        """Global badges use medication_id='' to avoid SQLite NULL uniqueness bug."""
        eb = EarnedBadge(
            id=str(uuid.uuid4()),
            profile_id="profile-1",
            badge_id="first-log",
            medication_id="",
        )
        assert eb.medication_id == ""

    def test_default_id_generated(self):
        eb = EarnedBadge(
            profile_id="p1",
            badge_id="first-log",
        )
        assert eb.id is not None
        assert len(eb.id) == 36  # UUID format

    def test_repr(self):
        eb = EarnedBadge(
            id="test-id",
            profile_id="p1",
            badge_id="week-warrior",
        )
        assert "week-warrior" in repr(eb)
        assert "p1" in repr(eb)
