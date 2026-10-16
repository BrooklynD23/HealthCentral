"""Gamification API — badge listing and settings.

GET /gamification/badges — list all badge definitions with earned status.
GET /gamification/streaks — profile-level streak summary.
Both reads write a view audit row to the master DB, fail-closed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import audit_and_commit, create_audit_log
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from core.time import safe_zone_name
from models import BadgeDefinition, DoseTaken, EarnedBadge, Medication, UserModelSettings
from modules.streak_engine import compute_engagement, compute_longest_streak, compute_streak

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
    # Engagement measure A (owner Q1): derived on read, nothing new stored.
    active_days_last_28: int
    weeks_with_log_last_4: int


async def _audit_view(master_db: AsyncSession, event_type: str, profile_id: str) -> None:
    """Mandatory view audit row (CLAUDE.md invariant); fail-closed via audit_and_commit."""
    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type=event_type,
        action=event_type,
        profile_id=profile_id,
        entity_type="gamification",
    )


@router.get(
    "/badges",
    response_model=BadgeListResponse,
)
async def list_badges(
    session: RequireAuth,
    profile_db: ProfileDbSession,
    master_db: AsyncSession = Depends(get_db),
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

    await _audit_view(master_db, "gamification.badges.view", profile_id)
    return BadgeListResponse(badges=badges)


@router.get(
    "/streaks",
    response_model=StreakResponse,
)
async def get_streaks(
    session: RequireAuth,
    profile_db: ProfileDbSession,
    master_db: AsyncSession = Depends(get_db),
):
    """Return current and longest streaks across all logged medications."""
    profile_id = session.profile_id

    settings_result = await profile_db.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
    )
    profile_settings = settings_result.scalar_one_or_none()
    timezone_name = safe_zone_name(profile_settings.timezone if profile_settings else None)

    doses_result = await profile_db.execute(
        select(DoseTaken)
        .join(Medication, Medication.id == DoseTaken.medication_id)
        .where(
            Medication.profile_id == profile_id,
            DoseTaken.was_skipped.is_(False),
            # Q2: a dose logged after its medication ended never counts.
            or_(Medication.ended_at.is_(None), DoseTaken.taken_at <= Medication.ended_at),
        )
        .order_by(DoseTaken.taken_at.desc())
    )
    doses = list(doses_result.scalars().all())

    now = datetime.now(dt_timezone.utc)
    as_of_date = now.astimezone(ZoneInfo(timezone_name)).date()
    active_days, active_weeks = compute_engagement(doses, timezone_name, as_of_date)

    response = StreakResponse(
        current_streak_days=compute_streak(doses, timezone_name, as_of_date)
        or compute_streak(doses, timezone_name, as_of_date - timedelta(days=1)),
        longest_streak_days=compute_longest_streak(doses, timezone_name),
        timezone=timezone_name,
        as_of_date=as_of_date.isoformat(),
        active_days_last_28=active_days,
        weeks_with_log_last_4=active_weeks,
    )
    await _audit_view(master_db, "gamification.streaks.view", profile_id)
    return response
