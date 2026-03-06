"""Gamification API — badge listing and settings.

GET /gamification/badges — list all badge definitions with earned status.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select

from core.auth import RequireAuth, ProfileDbSession
from models import BadgeDefinition, DoseTaken, EarnedBadge, Medication, UserModelSettings
from modules.streak_engine import compute_longest_streak, compute_streak

logger = logging.getLogger(__name__)

router = APIRouter()


class BadgeResponse(BaseModel):
    """Single badge with earned status."""
    id: str
    name: str
    description: str
    icon: str
    criteria_type: str
    earned: bool
    earned_at: Optional[str] = None
    medication_id: Optional[str] = None


class BadgeListResponse(BaseModel):
    """List of all badges."""
    badges: list[BadgeResponse]


class StreakResponse(BaseModel):
    """Profile-level streak summary for gamification surfaces."""
    current_streak_days: int
    longest_streak_days: int
    timezone: str
    as_of_date: str


def _profile_timezone_name(settings: Optional[UserModelSettings]) -> str:
    """Return a valid profile timezone or UTC if persisted data is invalid."""
    timezone_name = settings.timezone if settings and settings.timezone else "UTC"
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        logger.warning("Invalid profile timezone '%s'; falling back to UTC", timezone_name)
        return "UTC"
    return timezone_name


@router.get(
    "/badges",
    response_model=BadgeListResponse,
)
async def list_badges(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """List all badge definitions with earned status for current profile."""
    profile_id = session.profile_id

    # Fetch all definitions
    defs_result = await profile_db.execute(
        select(BadgeDefinition).order_by(BadgeDefinition.sort_order)
    )
    definitions = defs_result.scalars().all()

    # Fetch earned badges for this profile
    earned_result = await profile_db.execute(
        select(EarnedBadge).where(EarnedBadge.profile_id == profile_id)
    )
    earned_badges = earned_result.scalars().all()

    # Build lookup: badge_id -> list of earned records
    earned_map: dict[str, list[EarnedBadge]] = {}
    for eb in earned_badges:
        earned_map.setdefault(eb.badge_id, []).append(eb)

    badges: list[BadgeResponse] = []
    for defn in definitions:
        earned_list = earned_map.get(defn.id, [])
        if earned_list:
            for eb in earned_list:
                badges.append(BadgeResponse(
                    id=defn.id,
                    name=defn.name,
                    description=defn.description,
                    icon=defn.icon,
                    criteria_type=defn.criteria_type,
                    earned=True,
                    earned_at=eb.earned_at.isoformat(),
                    medication_id=eb.medication_id or None,
                ))
        else:
            badges.append(BadgeResponse(
                id=defn.id,
                name=defn.name,
                description=defn.description,
                icon=defn.icon,
                criteria_type=defn.criteria_type,
                earned=False,
                earned_at=None,
                medication_id=None,
            ))

    return BadgeListResponse(badges=badges)


@router.get(
    "/streaks",
    response_model=StreakResponse,
)
async def get_streaks(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Return current and longest streaks across all logged medications."""
    profile_id = session.profile_id

    settings_result = await profile_db.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
    )
    profile_settings = settings_result.scalar_one_or_none()
    timezone_name = _profile_timezone_name(profile_settings)

    doses_result = await profile_db.execute(
        select(DoseTaken)
        .join(Medication, Medication.id == DoseTaken.medication_id)
        .where(
            Medication.profile_id == profile_id,
            DoseTaken.was_skipped.is_(False),
        )
        .order_by(DoseTaken.taken_at.desc())
    )
    doses = list(doses_result.scalars().all())

    now = datetime.now(dt_timezone.utc)
    as_of_date = now.astimezone(ZoneInfo(timezone_name)).date()

    return StreakResponse(
        current_streak_days=compute_streak(doses, timezone_name, as_of_date),
        longest_streak_days=compute_longest_streak(doses, timezone_name),
        timezone=timezone_name,
        as_of_date=as_of_date.isoformat(),
    )
