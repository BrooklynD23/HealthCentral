"""Tests for gamification API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from api.gamification import (
    BadgeResponse,
    BadgeListResponse,
)


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
