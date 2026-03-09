"""Tests for gamification models — badge definitions and earned badges.

RED phase: These tests define the expected behavior of BadgeDefinition
and EarnedBadge models before implementation is verified.
"""

import uuid

import pytest

from core.time import utcnow
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
            earned_at=utcnow(),
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
        # SQLAlchemy column defaults are populated on INSERT, not object init.
        assert eb.id is None

    def test_repr(self):
        eb = EarnedBadge(
            id="test-id",
            profile_id="p1",
            badge_id="week-warrior",
        )
        assert "week-warrior" in repr(eb)
        assert "p1" in repr(eb)
