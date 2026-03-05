"""Badge evaluation engine.

Runs inline after each dose log to check if new badges were earned.
Returns list of newly earned badges to include in dose response.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone as dt_timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from models.gamification import EarnedBadge
from modules.streak_engine import compute_streak, detect_comeback_gap


@dataclass
class BadgeEvalResult:
    """Result of a badge evaluation — one newly earned badge."""
    badge_id: str
    name: str
    description: str
    icon: str
    medication_id: str  # '' for global badges
    earned_at: datetime


# Badge definitions (mirrors seed data — avoids DB lookup on hot path)
BADGE_DEFS = {
    "first-log": {"name": "First Log", "description": "Log your first dose", "icon": "spark", "type": "count"},
    "3-day-streak": {"name": "3-Day Streak", "description": "3 consecutive days of adherence", "icon": "flame", "type": "streak", "days": 3},
    "week-warrior": {"name": "Week Warrior", "description": "7 consecutive days of adherence", "icon": "flame", "type": "streak", "days": 7},
    "two-week-titan": {"name": "Two-Week Titan", "description": "14 consecutive days of adherence", "icon": "trophy", "type": "streak", "days": 14},
    "month-master": {"name": "Month Master", "description": "30 consecutive days of adherence", "icon": "trophy", "type": "streak", "days": 30},
    "perfect-week": {"name": "Perfect Week", "description": "All scheduled doses on time for 7 days", "icon": "star", "type": "pattern"},
    "multi-med-master": {"name": "Multi-Med Master", "description": "7-day streak on 2+ medications", "icon": "shield", "type": "multi_med"},
    "comeback-kid": {"name": "Comeback Kid", "description": "Resume logging after a 3+ day gap", "icon": "heart", "type": "gap"},
}


def _badge_key(badge_id: str, medication_id: str) -> str:
    """Unique key for dedup: 'badge_id:medication_id'."""
    return f"{badge_id}:{medication_id}"


async def evaluate_badges_after_dose(
    profile_id: str,
    medication_id: str,
    doses_for_medication: list,
    all_profile_doses: list,
    timezone: str,
    existing_badge_keys: set[str],
    db: AsyncSession,
) -> list[BadgeEvalResult]:
    """Evaluate all badge criteria after a dose log.

    Args:
        profile_id: Current user profile ID.
        medication_id: Medication the dose was logged for.
        doses_for_medication: All non-skipped doses for this medication.
        all_profile_doses: All non-skipped doses across all medications.
        timezone: IANA timezone string for date grouping.
        existing_badge_keys: Set of 'badge_id:medication_id' already earned.
        db: Async database session for persisting new badges.

    Returns:
        List of newly earned badges.
    """
    now = datetime.now(dt_timezone.utc)
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).date()
    newly_earned: list[BadgeEvalResult] = []
    seen_keys = set(existing_badge_keys)

    def _try_award(badge_id: str, med_id: str) -> Optional[BadgeEvalResult]:
        key = _badge_key(badge_id, med_id)
        if key in seen_keys:
            return None
        defn = BADGE_DEFS[badge_id]
        result = BadgeEvalResult(
            badge_id=badge_id,
            name=defn["name"],
            description=defn["description"],
            icon=defn["icon"],
            medication_id=med_id,
            earned_at=now,
        )
        seen_keys.add(key)
        return result

    # 1. First Log (global)
    if len(all_profile_doses) >= 1:
        r = _try_award("first-log", "")
        if r:
            newly_earned.append(r)

    # 2. Streak-based badges (per medication)
    streak = compute_streak(doses_for_medication, timezone, today)
    for badge_id, defn in BADGE_DEFS.items():
        if defn.get("type") == "streak" and "days" in defn:
            if streak >= defn["days"]:
                r = _try_award(badge_id, medication_id)
                if r:
                    newly_earned.append(r)

    # 3. Comeback Kid (global)
    if detect_comeback_gap(doses_for_medication, timezone):
        r = _try_award("comeback-kid", "")
        if r:
            newly_earned.append(r)

    # 4. Multi-Med Master (global)
    meds_with_7day: set[str] = set()
    doses_by_med: dict[str, list] = {}
    for dose in all_profile_doses:
        doses_by_med.setdefault(dose.medication_id, []).append(dose)
    for mid, med_doses in doses_by_med.items():
        if compute_streak(med_doses, timezone, today) >= 7:
            meds_with_7day.add(mid)
    if len(meds_with_7day) >= 2:
        r = _try_award("multi-med-master", "")
        if r:
            newly_earned.append(r)

    # 5. Perfect Week (per medication) — requires schedule-linked doses
    scheduled_doses = [d for d in doses_for_medication if d.schedule_id and d.variance_minutes is not None]
    if len(scheduled_doses) >= 7:
        # Check last 7 days: every day has all scheduled doses within ±60 min
        perfect_days = 0
        for day_offset in range(7):
            check_date = today - timedelta(days=day_offset)
            day_doses = [d for d in scheduled_doses if d.taken_at.astimezone(tz).date() == check_date]
            if day_doses and all(abs(d.variance_minutes) <= 60 for d in day_doses):
                perfect_days += 1
        if perfect_days >= 7:
            r = _try_award("perfect-week", medication_id)
            if r:
                newly_earned.append(r)

    # Persist newly earned badges
    for badge_result in newly_earned:
        earned = EarnedBadge(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            badge_id=badge_result.badge_id,
            medication_id=badge_result.medication_id,
            earned_at=badge_result.earned_at,
        )
        db.add(earned)

    return newly_earned
