"""Gamification API — badge listing and settings.

GET /gamification/badges — list all badge definitions with earned status.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select

from core.auth import RequireAuth, ProfileDbSession
from models.gamification import BadgeDefinition, EarnedBadge

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
