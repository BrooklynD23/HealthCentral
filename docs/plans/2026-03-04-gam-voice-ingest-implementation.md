# GAM-001, MED-VOICE-001, INGEST-EPIC-001 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement gamification (streaks + 8 badges), voice dose logging, and document category/entity extraction across backend and frontend.

**Architecture:** Three features built sequentially: Gamification first (shared migration + streak engine + badge evaluation + frontend), then Voice Logging (settings + permissions-policy + SpeechRecognition frontend), then INGEST-EPIC-001 (schema + classifier + 3 extractors + frontend + RAG). All backend models use per-profile SQLCipher databases via ProfileDatabaseBase. Frontend uses React Query hooks + Tailwind + Radix UI + Framer Motion.

**Tech Stack:** FastAPI, SQLAlchemy (async), Alembic, SQLCipher, React 18, TypeScript, Vite, React Query, Tailwind CSS, Framer Motion, Lucide icons.

**PRD:** `docs/plans/2026-03-04-prd-voice-gamification-ingest-design.md`

---

## Phase 1: Gamification v1 (GAM-001)

### Task 1: Alembic Migration — timezone, voice, badge tables

**Files:**
- Create: `src/backend/migrations/profile/versions/003_gamification_voice_settings.py`

**Step 1: Write the migration file**

```python
"""Add timezone, voice settings, and gamification tables.

Revision ID: 003_gamification_voice
Revises: 002_external_api
Create Date: 2026-03-04

Adds:
- timezone, voice_logging_enabled, voice_modal_seen to user_model_settings
- badge_definition table (seed data)
- earned_badge table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_gamification_voice"
down_revision: Union[str, None] = "002_external_api"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BADGE_SEEDS = [
    ("first-log", "First Log", "Log your first dose", "spark", "count", '{"count": 1}', 0),
    ("3-day-streak", "3-Day Streak", "3 consecutive days of adherence", "flame", "streak", '{"streak_days": 3}', 1),
    ("week-warrior", "Week Warrior", "7 consecutive days of adherence", "flame", "streak", '{"streak_days": 7}', 2),
    ("two-week-titan", "Two-Week Titan", "14 consecutive days of adherence", "trophy", "streak", '{"streak_days": 14}', 3),
    ("month-master", "Month Master", "30 consecutive days of adherence", "trophy", "streak", '{"streak_days": 30}', 4),
    ("perfect-week", "Perfect Week", "All scheduled doses on time for 7 days", "star", "pattern", '{"perfect_days": 7, "max_variance_minutes": 60}', 5),
    ("multi-med-master", "Multi-Med Master", "7-day streak on 2+ medications", "shield", "streak", '{"streak_days": 7, "min_medications": 2}', 6),
    ("comeback-kid", "Comeback Kid", "Resume logging after a 3+ day gap", "heart", "gap", '{"gap_days": 3}', 7),
]


def upgrade() -> None:
    # user_model_settings additions
    op.add_column(
        "user_model_settings",
        sa.Column("timezone", sa.Text(), nullable=False, server_default="UTC"),
    )
    op.add_column(
        "user_model_settings",
        sa.Column("voice_logging_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_model_settings",
        sa.Column("voice_modal_seen", sa.Boolean(), nullable=False, server_default="0"),
    )

    # badge_definition
    op.create_table(
        "badge_definition",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.Text(), nullable=False),
        sa.Column("criteria_type", sa.Text(), nullable=False),
        sa.Column("criteria_json", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # earned_badge
    op.create_table(
        "earned_badge",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("profile_id", sa.Text(), nullable=False),
        sa.Column("badge_id", sa.Text(), sa.ForeignKey("badge_definition.id"), nullable=False),
        sa.Column("medication_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("earned_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("profile_id", "badge_id", "medication_id", name="uq_earned_badge"),
    )

    # Seed badge definitions
    badge_table = sa.table(
        "badge_definition",
        sa.column("id", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("icon", sa.Text()),
        sa.column("criteria_type", sa.Text()),
        sa.column("criteria_json", sa.Text()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(badge_table, [
        {"id": b[0], "name": b[1], "description": b[2], "icon": b[3],
         "criteria_type": b[4], "criteria_json": b[5], "sort_order": b[6]}
        for b in BADGE_SEEDS
    ])


def downgrade() -> None:
    op.drop_table("earned_badge")
    op.drop_table("badge_definition")
    op.drop_column("user_model_settings", "voice_modal_seen")
    op.drop_column("user_model_settings", "voice_logging_enabled")
    op.drop_column("user_model_settings", "timezone")
```

**Step 2: Commit**

```bash
git add src/backend/migrations/profile/versions/003_gamification_voice_settings.py
git commit -m "feat(GAM-001): migration for timezone, voice settings, badge tables"
```

---

### Task 2: SQLAlchemy Models — BadgeDefinition, EarnedBadge, UserModelSettings columns

**Files:**
- Create: `src/backend/models/gamification.py`
- Modify: `src/backend/models/model_settings.py:42-104` (add 3 columns)
- Modify: `src/backend/models/__init__.py` (add exports)

**Step 1: Write the failing test**

Create: `src/backend/tests/test_gamification_models.py`

```python
"""Tests for gamification models — badge definitions and earned badges."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from models.gamification import BadgeDefinition, EarnedBadge


@pytest.fixture
def badge_def():
    return BadgeDefinition(
        id="week-warrior",
        name="Week Warrior",
        description="7 consecutive days of adherence",
        icon="flame",
        criteria_type="streak",
        criteria_json='{"streak_days": 7}',
        sort_order=2,
    )


def test_badge_definition_fields(badge_def):
    assert badge_def.id == "week-warrior"
    assert badge_def.criteria_type == "streak"
    assert badge_def.sort_order == 2


def test_earned_badge_fields():
    eb = EarnedBadge(
        id=str(uuid.uuid4()),
        profile_id="profile-1",
        badge_id="week-warrior",
        medication_id="med-1",
        earned_at=datetime.utcnow(),
    )
    assert eb.medication_id == "med-1"


def test_earned_badge_global_uses_empty_string():
    """Global badges use medication_id='' to avoid SQLite NULL uniqueness bug."""
    eb = EarnedBadge(
        id=str(uuid.uuid4()),
        profile_id="profile-1",
        badge_id="first-log",
        medication_id="",
    )
    assert eb.medication_id == ""
```

**Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_gamification_models.py -v`
Expected: FAIL — `models.gamification` not found

**Step 3: Create `src/backend/models/gamification.py`**

```python
"""Gamification models — badge definitions and earned badges.

Stored in per-profile encrypted database for data isolation.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase


class BadgeDefinition(ProfileDatabaseBase):
    """Badge definition with criteria for earning."""

    __tablename__ = "badge_definition"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(Text, nullable=False)
    criteria_type: Mapped[str] = mapped_column(Text, nullable=False)
    criteria_json: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<BadgeDefinition(id={self.id}, name={self.name})>"


class EarnedBadge(ProfileDatabaseBase):
    """Record of a badge earned by a profile.

    medication_id='' for global badges (First Log, Multi-Med Master, Comeback Kid).
    Uses empty string instead of NULL to avoid SQLite NULL uniqueness bug.
    """

    __tablename__ = "earned_badge"
    __table_args__ = (
        UniqueConstraint("profile_id", "badge_id", "medication_id", name="uq_earned_badge"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    profile_id: Mapped[str] = mapped_column(Text, nullable=False)
    badge_id: Mapped[str] = mapped_column(
        Text, ForeignKey("badge_definition.id"), nullable=False,
    )
    medication_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    earned_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<EarnedBadge(badge_id={self.badge_id}, profile_id={self.profile_id})>"
```

**Step 4: Add columns to `src/backend/models/model_settings.py`**

Add after `external_api_key_encrypted` column (line 92), before `created_at`:

```python
    # Timezone for streak/badge computation (Phase: GAM-001)
    timezone: Mapped[str] = mapped_column(
        Text,
        default="UTC",
        nullable=False,
    )

    # Voice logging preferences (Phase: MED-VOICE-001)
    voice_logging_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    voice_modal_seen: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
```

**Step 5: Update `src/backend/models/__init__.py`**

Add import and export:

```python
from .gamification import BadgeDefinition, EarnedBadge
```

Add `BadgeDefinition`, `EarnedBadge` to `__all__`.

**Step 6: Run tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/test_gamification_models.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/backend/models/gamification.py src/backend/models/model_settings.py src/backend/models/__init__.py src/backend/tests/test_gamification_models.py
git commit -m "feat(GAM-001): add BadgeDefinition, EarnedBadge models + UserModelSettings columns"
```

---

### Task 3: Streak Computation Module (timezone-aware)

**Files:**
- Create: `src/backend/modules/streak_engine.py`
- Test: `src/backend/tests/test_streak_engine.py`

**Step 1: Write the failing tests**

```python
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
```

**Step 2: Run to verify failure**

Run: `cd src/backend && python -m pytest tests/test_streak_engine.py -v`
Expected: FAIL — `modules.streak_engine` not found

**Step 3: Write `src/backend/modules/streak_engine.py`**

```python
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


def _dose_dates(doses: list, tz_name: str) -> set[date]:
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


def compute_streak(doses: list, tz_name: str, as_of_date: date) -> int:
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


def compute_longest_streak(doses: list, tz_name: str) -> int:
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


def detect_comeback_gap(doses: list, tz_name: str) -> bool:
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
```

**Step 4: Run tests to verify pass**

Run: `cd src/backend && python -m pytest tests/test_streak_engine.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/backend/modules/streak_engine.py src/backend/tests/test_streak_engine.py
git commit -m "feat(GAM-001): timezone-aware streak computation engine"
```

---

### Task 4: Badge Evaluation Engine

**Files:**
- Create: `src/backend/modules/badge_evaluator.py`
- Test: `src/backend/tests/test_badge_evaluator.py`

**Step 1: Write the failing tests**

```python
"""Tests for badge evaluation logic."""

import uuid
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from modules.badge_evaluator import evaluate_badges_after_dose, BadgeEvalResult


def _make_dose(taken_at_str, medication_id="med-1", was_skipped=False, variance_minutes=None, schedule_id=None):
    class MockDose:
        pass
    d = MockDose()
    d.taken_at = datetime.fromisoformat(taken_at_str)
    d.medication_id = medication_id
    d.was_skipped = was_skipped
    d.variance_minutes = variance_minutes
    d.schedule_id = schedule_id
    return d


class TestFirstLogBadge:
    @pytest.mark.asyncio
    async def test_first_dose_earns_first_log(self):
        """First ever dose should earn 'first-log' badge."""
        doses_for_med = [_make_dose("2026-03-04T10:00:00+00:00")]
        all_doses = doses_for_med
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses_for_med,
            all_profile_doses=all_doses,
            timezone="UTC",
            existing_badge_keys=set(),
            db=AsyncMock(),
        )
        badge_ids = [b.badge_id for b in result]
        assert "first-log" in badge_ids


class TestStreakBadges:
    @pytest.mark.asyncio
    async def test_seven_day_streak_earns_week_warrior(self):
        doses = [
            _make_dose(f"2026-02-{26 + i:02d}T08:00:00+00:00")
            for i in range(7)
        ]
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses,
            all_profile_doses=doses,
            timezone="UTC",
            existing_badge_keys={"first-log:"},
            db=AsyncMock(),
        )
        badge_ids = [b.badge_id for b in result]
        assert "week-warrior" in badge_ids

    @pytest.mark.asyncio
    async def test_already_earned_badge_not_duplicated(self):
        doses = [
            _make_dose(f"2026-02-{26 + i:02d}T08:00:00+00:00")
            for i in range(7)
        ]
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses,
            all_profile_doses=doses,
            timezone="UTC",
            existing_badge_keys={"first-log:", "week-warrior:med-1"},
            db=AsyncMock(),
        )
        badge_ids = [b.badge_id for b in result]
        assert "week-warrior" not in badge_ids


class TestComebackKid:
    @pytest.mark.asyncio
    async def test_comeback_after_gap(self):
        doses = [
            _make_dose("2026-02-25T08:00:00+00:00"),
            # 3+ day gap
            _make_dose("2026-03-04T08:00:00+00:00"),
        ]
        result = await evaluate_badges_after_dose(
            profile_id="p1",
            medication_id="med-1",
            doses_for_medication=doses,
            all_profile_doses=doses,
            timezone="UTC",
            existing_badge_keys={"first-log:"},
            db=AsyncMock(),
        )
        badge_ids = [b.badge_id for b in result]
        assert "comeback-kid" in badge_ids
```

**Step 2: Run to verify failure**

Run: `cd src/backend && python -m pytest tests/test_badge_evaluator.py -v`
Expected: FAIL — `modules.badge_evaluator` not found

**Step 3: Write `src/backend/modules/badge_evaluator.py`**

```python
"""Badge evaluation engine.

Runs inline after each dose log to check if new badges were earned.
Returns list of newly earned badges to include in dose response.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, date
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
    now = datetime.utcnow()
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).date()
    newly_earned: list[BadgeEvalResult] = []

    def _try_award(badge_id: str, med_id: str) -> Optional[BadgeEvalResult]:
        key = _badge_key(badge_id, med_id)
        if key in existing_badge_keys:
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
        existing_badge_keys.add(key)
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
            check_date = today - __import__("datetime").timedelta(days=day_offset)
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
```

**Step 4: Run tests to verify pass**

Run: `cd src/backend && python -m pytest tests/test_badge_evaluator.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/backend/modules/badge_evaluator.py src/backend/tests/test_badge_evaluator.py
git commit -m "feat(GAM-001): badge evaluation engine with all 8 badge criteria"
```

---

### Task 5: Gamification API Router

**Files:**
- Create: `src/backend/api/gamification.py`
- Modify: `src/backend/api/__init__.py:29-41` (add router)
- Modify: `src/backend/api/medications.py:701-773` (update dose response)
- Test: `src/backend/tests/test_gamification_api.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run to verify failure**

Run: `cd src/backend && python -m pytest tests/test_gamification_api.py -v`
Expected: FAIL

**Step 3: Create `src/backend/api/gamification.py`**

```python
"""Gamification API — badge listing and settings.

GET /gamification/badges — list all badge definitions with earned status.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select

from core.dependencies import RequireAuth, ProfileDbSession
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
    profile_db: ProfileDbSession = None,
):
    """List all badge definitions with earned status for current profile."""
    profile_id = session.get("profile_id", "")

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
```

**Step 4: Register router in `src/backend/api/__init__.py`**

Add import:
```python
from .gamification import router as gamification_router
```

Add include:
```python
router.include_router(gamification_router, prefix="/gamification", tags=["gamification"])
```

**Step 5: Update dose log endpoint in `src/backend/api/medications.py`**

Add new response model after `DoseResponse` (line ~242):

```python
class DoseLogResponse(BaseModel):
    """Response for dose logging with badge evaluation."""
    dose: DoseResponse
    newly_earned_badges: list[dict] = []
```

Update the `log_dose` endpoint (line 701-773) to:
1. Change `response_model=DoseLogResponse`
2. After `await profile_db.refresh(dose_record)`, add badge evaluation
3. Return `DoseLogResponse` instead of `DoseResponse`

Key code to add after `await profile_db.refresh(dose_record)` (line 767):

```python
    # Badge evaluation
    from modules.badge_evaluator import evaluate_badges_after_dose
    from models.gamification import EarnedBadge
    from models.model_settings import UserModelSettings

    newly_earned_badges = []
    try:
        # Get profile timezone
        settings_result = await profile_db.execute(
            select(UserModelSettings).where(
                UserModelSettings.profile_id == session.get("profile_id", "")
            )
        )
        settings = settings_result.scalar_one_or_none()
        profile_tz = settings.timezone if settings else "UTC"

        # Get all doses for this medication (non-skipped)
        med_doses_result = await profile_db.execute(
            select(DoseTaken).where(
                DoseTaken.medication_id == medication_id,
                DoseTaken.was_skipped == False,
            ).order_by(DoseTaken.taken_at.desc()).limit(60)
        )
        med_doses = list(med_doses_result.scalars().all())

        # Get all profile doses (non-skipped, last 60)
        all_doses_result = await profile_db.execute(
            select(DoseTaken).where(
                DoseTaken.was_skipped == False,
            ).order_by(DoseTaken.taken_at.desc()).limit(200)
        )
        all_doses = list(all_doses_result.scalars().all())

        # Get existing earned badges
        earned_result = await profile_db.execute(
            select(EarnedBadge).where(
                EarnedBadge.profile_id == session.get("profile_id", "")
            )
        )
        earned = earned_result.scalars().all()
        existing_keys = {f"{e.badge_id}:{e.medication_id}" for e in earned}

        badge_results = await evaluate_badges_after_dose(
            profile_id=session.get("profile_id", ""),
            medication_id=medication_id,
            doses_for_medication=med_doses,
            all_profile_doses=all_doses,
            timezone=profile_tz,
            existing_badge_keys=existing_keys,
            db=profile_db,
        )
        await profile_db.commit()

        newly_earned_badges = [
            {
                "badge_id": b.badge_id,
                "name": b.name,
                "description": b.description,
                "icon": b.icon,
                "medication_id": b.medication_id or None,
                "earned_at": b.earned_at.isoformat(),
            }
            for b in badge_results
        ]
    except Exception as e:
        logger.warning(f"Badge evaluation failed (non-fatal): {e}")

    return DoseLogResponse(
        dose=DoseResponse.from_model(dose_record),
        newly_earned_badges=newly_earned_badges,
    )
```

**Step 6: Run tests**

Run: `cd src/backend && python -m pytest tests/test_gamification_api.py tests/test_badge_evaluator.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/backend/api/gamification.py src/backend/api/__init__.py src/backend/api/medications.py src/backend/tests/test_gamification_api.py
git commit -m "feat(GAM-001): gamification API router + badge eval in dose response"
```

---

### Task 6: Frontend Types + Service for Gamification

**Files:**
- Modify: `src/frontend/src/services/types.ts:288-312` (update DoseResponse, add badge types)
- Create: `src/frontend/src/services/gamification.ts`
- Modify: `src/frontend/src/services/index.ts` (add exports)

**Step 1: Add types to `src/frontend/src/services/types.ts`**

After `AdherenceStats` interface (line ~312), add:

```typescript
// Gamification types
export interface BadgeInfo {
  badge_id: string;
  name: string;
  description: string;
  icon: string;
  medication_id: string | null;
  earned_at: string;
}

export interface DoseLogResponse {
  dose: DoseResponse;
  newly_earned_badges: BadgeInfo[];
}

export interface BadgeStatus {
  id: string;
  name: string;
  description: string;
  icon: string;
  criteria_type: string;
  earned: boolean;
  earned_at: string | null;
  medication_id: string | null;
}

export interface BadgeListResponse {
  badges: BadgeStatus[];
}
```

**Step 2: Create `src/frontend/src/services/gamification.ts`**

```typescript
/**
 * Gamification API Service
 *
 * React Query hooks for badge listing.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet } from './api';
import type { BadgeListResponse } from './types';

const QUERY_KEY = 'gamification';

async function fetchBadges(): Promise<BadgeListResponse> {
  return apiGet<BadgeListResponse>('/gamification/badges');
}

export function useBadges() {
  return useQuery({
    queryKey: [QUERY_KEY, 'badges'],
    queryFn: fetchBadges,
  });
}
```

**Step 3: Update `src/frontend/src/services/medications.ts`**

Update `logDose` return type from `DoseResponse` to `DoseLogResponse`:

```typescript
import type {
  // ... existing imports ...
  DoseLogResponse,
} from './types';

async function logDose(
  medicationId: string,
  data: DoseLog,
  scheduleId?: string
): Promise<DoseLogResponse> {
  const params = scheduleId ? `?schedule_id=${scheduleId}` : '';
  return apiPost<DoseLogResponse, DoseLog>(
    `/medications/${medicationId}/doses${params}`,
    data
  );
}
```

Update `useLogDose` to also invalidate gamification badges:

```typescript
export function useLogDose() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      data,
      scheduleId,
    }: {
      medicationId: string;
      data: DoseLog;
      scheduleId?: string;
    }) => logDose(medicationId, data, scheduleId),
    onSuccess: (_, { medicationId }) => {
      queryClient.invalidateQueries({
        queryKey: ['medications', medicationId, 'doses'],
      });
      queryClient.invalidateQueries({
        queryKey: ['medications', medicationId, 'stats'],
      });
      queryClient.invalidateQueries({
        queryKey: ['gamification', 'badges'],
      });
    },
  });
}
```

**Step 4: Update `src/frontend/src/services/index.ts`**

Add exports:

```typescript
// Gamification hooks
export { useBadges } from './gamification';

export type {
  BadgeInfo,
  DoseLogResponse,
  BadgeStatus,
  BadgeListResponse,
} from './types';
```

**Step 5: Commit**

```bash
git add src/frontend/src/services/types.ts src/frontend/src/services/gamification.ts src/frontend/src/services/medications.ts src/frontend/src/services/index.ts
git commit -m "feat(GAM-001): frontend types and service hooks for gamification"
```

---

### Task 7: Frontend — Badge Toast + Achievements Widget

**Files:**
- Create: `src/frontend/src/components/medication-coach/BadgeToast.tsx`
- Create: `src/frontend/src/components/medication-coach/AchievementsWidget.tsx`
- Modify: `src/frontend/src/components/medication-coach/DoseLoggingModal.tsx` (handle badge response)

**Step 1: Create `BadgeToast.tsx`**

```typescript
/**
 * BadgeToast — Framer Motion slide-in notification on badge earn.
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Award } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { BadgeInfo } from '@/services/types';

const ICON_MAP: Record<string, string> = {
  spark: '⚡',
  flame: '🔥',
  trophy: '🏆',
  star: '⭐',
  shield: '🛡️',
  heart: '❤️',
};

interface BadgeToastProps {
  badge: BadgeInfo | null;
  onDismiss: () => void;
}

export function BadgeToast({ badge, onDismiss }: BadgeToastProps) {
  useEffect(() => {
    if (badge) {
      const timer = setTimeout(onDismiss, 5000);
      return () => clearTimeout(timer);
    }
  }, [badge, onDismiss]);

  return (
    <AnimatePresence>
      {badge && (
        <motion.div
          initial={{ opacity: 0, y: -50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -50, scale: 0.9 }}
          className={cn(
            'fixed top-4 right-4 z-[60] flex items-center gap-3',
            'rounded-xl bg-surface-elevated p-4 shadow-elevated',
            'border border-accent/20'
          )}
          role="status"
          aria-live="polite"
        >
          <span className="text-2xl" aria-hidden>
            {ICON_MAP[badge.icon] ?? '🏅'}
          </span>
          <div>
            <p className="text-sm font-semibold text-ink">Badge Earned!</p>
            <p className="text-sm text-ink-secondary">{badge.name}</p>
          </div>
          <button
            onClick={onDismiss}
            className="ml-2 text-ink-tertiary hover:text-ink"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

**Step 2: Create `AchievementsWidget.tsx`**

```typescript
/**
 * AchievementsWidget — displays earned and unearned badges in a grid.
 */

import { Award, Lock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useBadges } from '@/services';
import type { BadgeStatus } from '@/services/types';

const ICON_MAP: Record<string, string> = {
  spark: '⚡',
  flame: '🔥',
  trophy: '🏆',
  star: '⭐',
  shield: '🛡️',
  heart: '❤️',
};

function BadgeCard({ badge }: { badge: BadgeStatus }) {
  return (
    <div
      className={cn(
        'flex flex-col items-center gap-1.5 rounded-xl p-3 text-center transition-colors',
        badge.earned
          ? 'bg-accent/5 border border-accent/20'
          : 'bg-surface-muted border border-transparent opacity-50'
      )}
    >
      <span className="text-2xl" aria-hidden>
        {badge.earned ? (ICON_MAP[badge.icon] ?? '🏅') : ''}
      </span>
      {!badge.earned && <Lock className="w-5 h-5 text-ink-tertiary" />}
      <p className="text-xs font-medium text-ink">{badge.name}</p>
      {badge.earned && badge.earned_at && (
        <p className="text-[10px] text-ink-tertiary">
          {new Date(badge.earned_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}

export function AchievementsWidget() {
  const { data, isLoading } = useBadges();

  if (isLoading || !data) return null;

  const earned = data.badges.filter((b) => b.earned).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Award className="w-4 h-4 text-accent" />
          Achievements ({earned}/{data.badges.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-2">
          {data.badges.map((badge) => (
            <BadgeCard key={`${badge.id}-${badge.medication_id ?? ''}`} badge={badge} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 3: Update `DoseLoggingModal.tsx` to handle badge response**

The parent component that calls `useLogDose()` needs to handle `newly_earned_badges` from the mutation response. This is done at the call site — typically in the medication detail page. The modal itself doesn't change except that its `onSubmit` callback now receives a `DoseLogResponse` with `newly_earned_badges`.

**Step 4: Commit**

```bash
git add src/frontend/src/components/medication-coach/BadgeToast.tsx src/frontend/src/components/medication-coach/AchievementsWidget.tsx
git commit -m "feat(GAM-001): BadgeToast + AchievementsWidget frontend components"
```

---

### Task 8: Frontend — DoseLoggingModal schedule matching

**Files:**
- Modify: `src/frontend/src/components/medication-coach/DoseLoggingModal.tsx`

**Step 1: Update DoseLoggingModal to auto-match schedule**

Add props and logic to match dose to nearest active schedule:

```typescript
interface DoseLoggingModalProps {
  medicationName: string;
  schedules?: MedicationSchedule[];  // NEW: active schedules for this med
  onSubmit: (data: DoseLog, scheduleId?: string) => void;  // NEW: pass scheduleId
  onClose: () => void;
  isSubmitting?: boolean;
}
```

Add schedule matching inside `handleSubmit`:

```typescript
  const handleSubmit = () => {
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();

    // Auto-match to nearest active schedule
    let matchedScheduleId: string | undefined;
    if (schedules && schedules.length > 0 && mode === 'taken') {
      let closestDist = Infinity;
      for (const sched of schedules) {
        if (!sched.is_active) continue;
        const [h, m] = sched.target_time.split(':').map(Number);
        const schedMinutes = h * 60 + m;
        const dist = Math.abs(nowMinutes - schedMinutes);
        if (dist < closestDist) {
          closestDist = dist;
          matchedScheduleId = sched.id;
        }
      }
    }

    onSubmit(
      {
        taken_at: now.toISOString(),
        log_method: 'manual',
        was_skipped: mode === 'skipped',
        skip_reason: mode === 'skipped' ? skipReason || undefined : undefined,
        notes: notes.trim() || undefined,
      },
      matchedScheduleId,
    );
  };
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/medication-coach/DoseLoggingModal.tsx
git commit -m "feat(GAM-001): DoseLoggingModal auto-matches nearest schedule"
```

---

### Task 9: Timezone Settings API + Frontend

**Files:**
- Modify: `src/backend/api/model_settings.py` (add timezone endpoints)
- Modify: `src/frontend/src/pages/SettingsPage.tsx` (add timezone picker)
- Modify: `src/frontend/src/services/modelSettings.ts` (add timezone hooks)

**Step 1: Add timezone endpoints to `src/backend/api/model_settings.py`**

```python
class TimezoneResponse(BaseModel):
    timezone: str

class TimezoneUpdate(BaseModel):
    timezone: str = Field(..., description="IANA timezone string, e.g. 'America/New_York'")

@router.get("/timezone", response_model=TimezoneResponse)
async def get_timezone(
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Get profile timezone setting."""
    profile_id = session.get("profile_id", "")
    result = await profile_db.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
    )
    settings = result.scalar_one_or_none()
    return TimezoneResponse(timezone=settings.timezone if settings else "UTC")

@router.put("/timezone", response_model=TimezoneResponse)
async def set_timezone(
    data: TimezoneUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Set profile timezone."""
    from zoneinfo import ZoneInfo
    try:
        ZoneInfo(data.timezone)  # validate
    except (KeyError, ValueError):
        raise HTTPException(status_code=422, detail=f"Invalid timezone: {data.timezone}")

    profile_id = session.get("profile_id", "")
    result = await profile_db.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    settings.timezone = data.timezone
    await profile_db.commit()
    return TimezoneResponse(timezone=settings.timezone)
```

**Step 2: Add frontend hooks in `src/frontend/src/services/modelSettings.ts`**

Add functions and hooks for timezone:

```typescript
async function fetchTimezone(): Promise<{ timezone: string }> {
  return apiGet<{ timezone: string }>('/settings/model/timezone');
}

async function saveTimezone(timezone: string): Promise<{ timezone: string }> {
  return apiPut<{ timezone: string }, { timezone: string }>(
    '/settings/model/timezone',
    { timezone }
  );
}

export function useTimezone() {
  return useQuery({
    queryKey: ['settings', 'timezone'],
    queryFn: fetchTimezone,
  });
}

export function useSaveTimezone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (timezone: string) => saveTimezone(timezone),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'timezone'] });
    },
  });
}
```

**Step 3: Add timezone picker to SettingsPage.tsx**

Add a timezone section with a `<select>` dropdown using common IANA timezones. Place it before the model tier section.

**Step 4: Commit**

```bash
git add src/backend/api/model_settings.py src/frontend/src/services/modelSettings.ts src/frontend/src/pages/SettingsPage.tsx
git commit -m "feat(GAM-001): timezone settings API + frontend picker"
```

---

## Phase 2: Voice Logging (MED-VOICE-001)

### Task 10: Update Permissions-Policy Header

**Files:**
- Modify: `src/backend/security/security_headers.py:21`

**Step 1: Write failing test**

Create: `src/backend/tests/test_voice_permissions_policy.py`

```python
"""Test that Permissions-Policy allows microphone=(self)."""

def test_permissions_policy_allows_microphone():
    from security.security_headers import BASE_HEADERS
    pp = dict(BASE_HEADERS).get(b"permissions-policy", b"")
    assert b"microphone=(self)" in pp
    assert b"camera=()" in pp
    assert b"geolocation=()" in pp
```

**Step 2: Run to verify failure**

Run: `cd src/backend && python -m pytest tests/test_voice_permissions_policy.py -v`
Expected: FAIL — microphone=() not microphone=(self)

**Step 3: Update `security_headers.py` line 21**

Change:
```python
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
```
To:
```python
    (b"permissions-policy", b"camera=(), microphone=(self), geolocation=()"),
```

**Step 4: Run test to verify pass**

**Step 5: Commit**

```bash
git add src/backend/security/security_headers.py src/backend/tests/test_voice_permissions_policy.py
git commit -m "feat(MED-VOICE-001): allow microphone=(self) in Permissions-Policy"
```

---

### Task 11: Voice Settings API Endpoints

**Files:**
- Modify: `src/backend/api/model_settings.py` (add voice settings endpoints)
- Test: `src/backend/tests/test_voice_settings_api.py`

**Step 1: Write failing test**

```python
"""Tests for voice settings API response models."""

from api.model_settings import VoiceSettingsResponse, VoiceSettingsUpdate


def test_voice_settings_response():
    r = VoiceSettingsResponse(voice_logging_enabled=False, voice_modal_seen=False)
    assert r.voice_logging_enabled is False

def test_voice_settings_update_partial():
    u = VoiceSettingsUpdate(voice_logging_enabled=True)
    assert u.voice_logging_enabled is True
    assert u.voice_modal_seen is None
```

**Step 2: Run to verify failure**

**Step 3: Add to `src/backend/api/model_settings.py`**

```python
class VoiceSettingsResponse(BaseModel):
    voice_logging_enabled: bool
    voice_modal_seen: bool

class VoiceSettingsUpdate(BaseModel):
    voice_logging_enabled: Optional[bool] = None
    voice_modal_seen: Optional[bool] = None

@router.get("/voice", response_model=VoiceSettingsResponse)
async def get_voice_settings(
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Get voice logging preferences."""
    profile_id = session.get("profile_id", "")
    result = await profile_db.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
    )
    settings = result.scalar_one_or_none()
    return VoiceSettingsResponse(
        voice_logging_enabled=settings.voice_logging_enabled if settings else False,
        voice_modal_seen=settings.voice_modal_seen if settings else False,
    )

@router.patch("/voice", response_model=VoiceSettingsResponse)
async def update_voice_settings(
    data: VoiceSettingsUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Update voice logging preferences."""
    profile_id = session.get("profile_id", "")
    result = await profile_db.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    if data.voice_logging_enabled is not None:
        settings.voice_logging_enabled = data.voice_logging_enabled
    if data.voice_modal_seen is not None:
        settings.voice_modal_seen = data.voice_modal_seen

    await profile_db.commit()
    return VoiceSettingsResponse(
        voice_logging_enabled=settings.voice_logging_enabled,
        voice_modal_seen=settings.voice_modal_seen,
    )
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/backend/api/model_settings.py src/backend/tests/test_voice_settings_api.py
git commit -m "feat(MED-VOICE-001): voice settings GET/PATCH API endpoints"
```

---

### Task 12: Frontend — useSpeechRecognition Hook

**Files:**
- Create: `src/frontend/src/hooks/useSpeechRecognition.ts`
- Test: `src/frontend/src/__tests__/useSpeechRecognition.test.ts`

**Step 1: Write the hook**

```typescript
/**
 * useSpeechRecognition — wraps browser Web Speech API with lifecycle management.
 *
 * Feature-detects SpeechRecognition/webkitSpeechRecognition.
 * Returns null for isSupported when browser doesn't support it.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

type SpeechRecognitionInstance = InstanceType<typeof SpeechRecognition>;

interface UseSpeechRecognitionReturn {
  isSupported: boolean;
  isListening: boolean;
  transcript: string;
  error: string | null;
  start: () => void;
  stop: () => void;
  reset: () => void;
}

const MAX_LISTEN_MS = 30_000;
const SILENCE_TIMEOUT_MS = 5_000;

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
  const SpeechRecognitionAPI =
    typeof window !== 'undefined'
      ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      : null;

  const isSupported = !!SpeechRecognitionAPI;
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const maxTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (maxTimerRef.current) {
      clearTimeout(maxTimerRef.current);
      maxTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // already stopped
      }
      recognitionRef.current = null;
    }
    setIsListening(false);
  }, []);

  const start = useCallback(() => {
    if (!SpeechRecognitionAPI) {
      setError('Speech recognition not supported in this browser.');
      return;
    }

    setError(null);
    setTranscript('');

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      const result = event.results[0]?.[0]?.transcript ?? '';
      setTranscript(result);
    };

    recognition.onerror = (event: any) => {
      const msg =
        event.error === 'not-allowed'
          ? 'Microphone access denied. You can enable it in browser settings.'
          : event.error === 'no-speech'
            ? 'No speech detected. Try again or type manually.'
            : event.error === 'network'
              ? 'Speech recognition unavailable. Try again or type manually.'
              : `Speech error: ${event.error}`;
      setError(msg);
      cleanup();
    };

    recognition.onend = () => {
      cleanup();
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);

    // Max listen duration
    maxTimerRef.current = setTimeout(() => {
      cleanup();
    }, MAX_LISTEN_MS);
  }, [SpeechRecognitionAPI, cleanup]);

  const stop = useCallback(() => {
    cleanup();
  }, [cleanup]);

  const reset = useCallback(() => {
    cleanup();
    setTranscript('');
    setError(null);
  }, [cleanup]);

  // Cleanup on unmount
  useEffect(() => cleanup, [cleanup]);

  return { isSupported, isListening, transcript, error, start, stop, reset };
}
```

**Step 2: Commit**

```bash
git add src/frontend/src/hooks/useSpeechRecognition.ts
git commit -m "feat(MED-VOICE-001): useSpeechRecognition hook with error handling"
```

---

### Task 13: Frontend — Voice Button + First-Use Modal in DoseLoggingModal

**Files:**
- Create: `src/frontend/src/components/medication-coach/VoiceFirstUseModal.tsx`
- Modify: `src/frontend/src/components/medication-coach/DoseLoggingModal.tsx`

**Step 1: Create VoiceFirstUseModal**

```typescript
/**
 * VoiceFirstUseModal — privacy disclosure shown before first mic access.
 *
 * Displayed once per profile. User acknowledges before browser mic prompt fires.
 */

import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { Mic, Shield } from 'lucide-react';

interface VoiceFirstUseModalProps {
  onAccept: () => void;
  onDecline: () => void;
}

export function VoiceFirstUseModal({ onAccept, onDecline }: VoiceFirstUseModalProps) {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" aria-hidden />
      <Card className="relative z-10 w-full max-w-sm shadow-elevated">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Mic className="w-4 h-4 text-accent" />
            Voice Logging
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-3 rounded-xl bg-surface-muted p-3">
            <Shield className="w-5 h-5 text-accent mt-0.5 shrink-0" />
            <div className="text-sm text-ink-secondary space-y-1">
              <p>
                We don't store audio. We store only the text you confirm.
              </p>
              <p>
                Speech recognition may be processed by your browser's speech service.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onDecline} className="flex-1">
              Not Now
            </Button>
            <Button onClick={onAccept} className="flex-1">
              Enable Voice
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 2: Add mic button to DoseLoggingModal**

Add voice recording UI to the notes section of `DoseLoggingModal.tsx`:
- Import `useSpeechRecognition` hook
- Add mic button next to notes textarea
- Show transcript with confirm/discard
- Handle `[Voice]` prefix logic for notes
- Show `VoiceFirstUseModal` if `voice_modal_seen === false`

The voice button only renders when:
```typescript
voiceEnabled && voiceModalSeen && speechRecognition.isSupported
```

**Step 3: Commit**

```bash
git add src/frontend/src/components/medication-coach/VoiceFirstUseModal.tsx src/frontend/src/components/medication-coach/DoseLoggingModal.tsx
git commit -m "feat(MED-VOICE-001): voice button + first-use privacy modal in DoseLoggingModal"
```

---

### Task 14: Frontend — Voice Settings Toggle in Settings Page

**Files:**
- Modify: `src/frontend/src/pages/SettingsPage.tsx`
- Modify: `src/frontend/src/services/modelSettings.ts` (add voice settings hooks)

**Step 1: Add voice settings hooks to modelSettings.ts**

```typescript
async function fetchVoiceSettings(): Promise<{ voice_logging_enabled: boolean; voice_modal_seen: boolean }> {
  return apiGet('/settings/model/voice');
}

async function saveVoiceSettings(data: { voice_logging_enabled?: boolean; voice_modal_seen?: boolean }) {
  return apiPatch('/settings/model/voice', data);
}

export function useVoiceSettings() {
  return useQuery({
    queryKey: ['settings', 'voice'],
    queryFn: fetchVoiceSettings,
  });
}

export function useSaveVoiceSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveVoiceSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'voice'] });
    },
  });
}
```

**Step 2: Add Voice Logging section to SettingsPage**

Add a "Voice Logging" Card section with a toggle switch:

```tsx
{/* Voice Logging Section */}
<Card>
  <CardHeader>
    <CardTitle className="flex items-center gap-2 text-base">
      <Mic className="w-4 h-4 text-accent" />
      Voice Logging
    </CardTitle>
  </CardHeader>
  <CardContent className="space-y-3">
    <p className="text-sm text-ink-secondary">
      Enable voice-to-text for dose logging notes.
    </p>
    <label className="flex items-center justify-between">
      <span className="text-sm font-medium text-ink">Enable Voice Logging</span>
      <input
        type="checkbox"
        checked={voiceSettings?.voice_logging_enabled ?? false}
        onChange={(e) => saveVoice({ voice_logging_enabled: e.target.checked })}
        className="rounded"
      />
    </label>
  </CardContent>
</Card>
```

**Step 3: Commit**

```bash
git add src/frontend/src/pages/SettingsPage.tsx src/frontend/src/services/modelSettings.ts
git commit -m "feat(MED-VOICE-001): voice settings toggle in Settings page"
```

---

### Task 15: Update API Docs

**Files:**
- Modify: `docs/api/endpoints.md:120` (fix dose logging payload docs)

**Step 1: Update the dose logging endpoint documentation**

Fix the `POST /medications/{id}/doses` section to show actual request/response:

Request body: `{ taken_at, log_method, dosage_amount, dosage_unit, notes, was_skipped, skip_reason }`
Query param: `schedule_id` (optional)
Response: `{ dose: {...}, newly_earned_badges: [...] }`

**Step 2: Commit**

```bash
git add docs/api/endpoints.md
git commit -m "docs(MED-VOICE-001): update dose logging API docs to match implementation"
```

---

## Phase 3: INGEST-EPIC-001

### Task 16: INGEST-A — Schema Migration for Document Categories + Entities

**Files:**
- Create: `src/backend/migrations/profile/versions/004_document_categories_entities.py`
- Create: `src/backend/models/document_category.py`
- Modify: `src/backend/models/__init__.py`

**Step 1: Write migration**

```python
"""Add document_category and document_entity tables.

Revision ID: 004_document_categories
Revises: 003_gamification_voice
Create Date: 2026-03-04

INGEST-EPIC-001 Phase A: Schema for document classification and entity extraction.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_document_categories"
down_revision: Union[str, None] = "003_gamification_voice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_category",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("doc_id", sa.Text(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("classified_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("idx_doc_category_doc_id", "document_category", ["doc_id"])

    op.create_table(
        "document_entity",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("doc_id", sa.Text(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_bbox_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("idx_doc_entity_doc_id", "document_entity", ["doc_id"])
    op.create_index("idx_doc_entity_type", "document_entity", ["entity_type"])


def downgrade() -> None:
    op.drop_index("idx_doc_entity_type")
    op.drop_index("idx_doc_entity_doc_id")
    op.drop_table("document_entity")
    op.drop_index("idx_doc_category_doc_id")
    op.drop_table("document_category")
```

**Step 2: Create SQLAlchemy models in `src/backend/models/document_category.py`**

```python
"""Document classification and entity extraction models.

INGEST-EPIC-001: Imaging, pathology, and visit note document support.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase


class DocumentCategory(ProfileDatabaseBase):
    """Primary category classification for a document."""

    __tablename__ = "document_category"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(Text, ForeignKey("documents.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    classified_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DocumentCategory(doc_id={self.doc_id}, category={self.category})>"


class DocumentEntity(ProfileDatabaseBase):
    """Extracted entity from a document."""

    __tablename__ = "document_entity"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(Text, ForeignKey("documents.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_bbox_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DocumentEntity(doc_id={self.doc_id}, type={self.entity_type})>"
```

**Step 3: Update `src/backend/models/__init__.py`**

```python
from .document_category import DocumentCategory, DocumentEntity
```

**Step 4: Commit**

```bash
git add src/backend/migrations/profile/versions/004_document_categories_entities.py src/backend/models/document_category.py src/backend/models/__init__.py
git commit -m "feat(INGEST-A): schema migration + models for document_category and document_entity"
```

---

### Task 17: INGEST-A — Rule-Based Category Classifier

**Files:**
- Create: `src/backend/modules/document_classifier.py`
- Test: `src/backend/tests/test_document_classifier.py`

**Step 1: Write failing tests**

```python
"""Tests for rule-based document category classifier."""

import pytest

from modules.document_classifier import classify_document, ClassificationResult


class TestClassifyDocument:
    def test_imaging_strong_keywords(self):
        text = "RADIOLOGY REPORT\nMRI of lumbar spine\nFINDINGS: No acute abnormality\nIMPRESSION: Normal"
        result = classify_document(text)
        assert result.category == "imaging"
        assert result.confidence >= 0.9

    def test_pathology_strong_keywords(self):
        text = "PATHOLOGY REPORT\nSPECIMEN: Left breast biopsy\nDIAGNOSIS: Invasive ductal carcinoma"
        result = classify_document(text)
        assert result.category == "pathology"
        assert result.confidence >= 0.9

    def test_visit_notes_strong_keywords(self):
        text = "PROGRESS NOTE\nChief Complaint: Follow-up hypertension\nAssessment: BP well controlled\nPlan: Continue lisinopril"
        result = classify_document(text)
        assert result.category == "visit_notes"
        assert result.confidence >= 0.9

    def test_unknown_when_no_keywords(self):
        text = "This is a random document with no medical keywords specific to any category."
        result = classify_document(text)
        assert result.category == "unknown"

    def test_lab_report_returns_lab(self):
        text = "LABORATORY RESULTS\nGlucose: 95 mg/dL\nHemoglobin A1c: 5.7%\nReference Range: 4.0-5.6%"
        result = classify_document(text)
        assert result.category == "lab"

    def test_only_first_two_pages_used(self):
        """Classification should only use first 2 pages of text."""
        # Pages are separated by form feed \f
        page1 = "Some unrelated text"
        page2 = "More unrelated text"
        page3 = "RADIOLOGY REPORT MRI FINDINGS IMPRESSION"
        text = f"{page1}\f{page2}\f{page3}"
        result = classify_document(text)
        # Keywords only on page 3, classifier uses pages 1-2 only
        assert result.category == "unknown"
```

**Step 2: Run to verify failure**

**Step 3: Write `src/backend/modules/document_classifier.py`**

```python
"""Rule-based document category classifier.

Classifies documents into: imaging, pathology, visit_notes, lab, unknown.
Uses keyword matching on first 2 pages of OCR text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

IMAGING_STRONG = re.compile(
    r"\b(MRI|CT\s*scan|X[\-\s]?ray|ultrasound|radiograph|radiology\s+report|fluoroscopy|mammograph|PET\s*scan)\b",
    re.IGNORECASE,
)
IMAGING_SECTION = re.compile(r"\b(FINDINGS|IMPRESSION|TECHNIQUE|COMPARISON)\b")

PATHOLOGY_STRONG = re.compile(
    r"\b(biopsy|specimen|histologic|cytology|surgical\s+pathology|pathology\s+report|gross\s+description|microscopic)\b",
    re.IGNORECASE,
)
PATHOLOGY_SECTION = re.compile(r"\b(DIAGNOSIS|MARGINS|SPECIAL\s+STAINS|IMMUNOHISTOCHEMISTRY)\b")

VISIT_STRONG = re.compile(
    r"\b(chief\s+complaint|progress\s+note|discharge\s+summary|consult\s+note|history\s+of\s+present\s+illness)\b",
    re.IGNORECASE,
)
VISIT_SECTION = re.compile(r"\b(ASSESSMENT|PLAN|VITAL\s+SIGNS|REVIEW\s+OF\s+SYSTEMS)\b")

LAB_STRONG = re.compile(
    r"\b(laboratory\s+results?|reference\s+range|CBC|BMP|CMP|lipid\s+panel|hemoglobin\s+A1c|mg/dL|mmol/L|mEq/L)\b",
    re.IGNORECASE,
)


@dataclass
class ClassificationResult:
    """Result of document classification."""
    category: str       # 'imaging', 'pathology', 'visit_notes', 'lab', 'unknown'
    confidence: float   # 0.0 to 1.0
    classified_by: str  # 'rule'


def _extract_first_two_pages(text: str) -> str:
    """Extract text from first 2 pages (split on form feed)."""
    pages = text.split("\f")
    return "\f".join(pages[:2])


def _score_category(text: str, strong_pattern: re.Pattern, section_pattern: re.Pattern | None = None) -> float:
    """Score a category based on keyword matches."""
    strong_matches = len(strong_pattern.findall(text))
    section_matches = len(section_pattern.findall(text)) if section_pattern else 0

    if strong_matches >= 2:
        return 1.0
    if strong_matches == 1 and section_matches >= 1:
        return 0.9
    if strong_matches == 1:
        return 0.8
    if section_matches >= 2:
        return 0.7
    return 0.0


def classify_document(text: str) -> ClassificationResult:
    """Classify document text into a category.

    Uses first 2 pages only. Returns highest-scoring category above 0.7 threshold.
    """
    first_pages = _extract_first_two_pages(text)

    scores = {
        "imaging": _score_category(first_pages, IMAGING_STRONG, IMAGING_SECTION),
        "pathology": _score_category(first_pages, PATHOLOGY_STRONG, PATHOLOGY_SECTION),
        "visit_notes": _score_category(first_pages, VISIT_STRONG, VISIT_SECTION),
        "lab": _score_category(first_pages, LAB_STRONG),
    }

    best_category = max(scores, key=scores.get)  # type: ignore
    best_score = scores[best_category]

    if best_score < 0.7:
        return ClassificationResult(category="unknown", confidence=0.0, classified_by="rule")

    return ClassificationResult(
        category=best_category,
        confidence=best_score,
        classified_by="rule",
    )
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/backend/modules/document_classifier.py src/backend/tests/test_document_classifier.py
git commit -m "feat(INGEST-A): rule-based document category classifier"
```

---

### Task 18: INGEST-B — Imaging Entity Extractor

**Files:**
- Create: `src/backend/modules/extract_imaging.py`
- Test: `src/backend/tests/test_extract_imaging.py`

Follow the same TDD pattern as Task 17. The extractor uses regex to extract:
- modality, body_region, finding, impression, laterality, contrast_used, ordering_provider, report_date

Each entity returned as `{ entity_type, entity_value, confidence, source_page }`.

**Commit:** `feat(INGEST-B): imaging entity extractor with regex patterns`

---

### Task 19: INGEST-C — Pathology Entity Extractor

**Files:**
- Create: `src/backend/modules/extract_pathology.py`
- Test: `src/backend/tests/test_extract_pathology.py`

Same TDD pattern. Extracts: specimen_type, specimen_site, diagnosis, grade, stage, margins, special_stains, pathologist, report_date.

**Commit:** `feat(INGEST-C): pathology entity extractor`

---

### Task 20: INGEST-D — Visit Notes Entity Extractor

**Files:**
- Create: `src/backend/modules/extract_visit_notes.py`
- Test: `src/backend/tests/test_extract_visit_notes.py`

Same TDD pattern. Extracts: visit_type, chief_complaint, assessment, plan, diagnoses, provider, visit_date, vitals.

**Commit:** `feat(INGEST-D): visit notes entity extractor`

---

### Task 21: INGEST-A Continued — Wire Classifier into Import Pipeline

**Files:**
- Modify: `src/backend/api/documents.py` (add classification after OCR)
- Test: `src/backend/tests/test_document_import_classification.py`

After existing OCR processing, add:

```python
from modules.document_classifier import classify_document
from models.document_category import DocumentCategory

# After OCR text is available:
classification = classify_document(ocr_text)
if classification.category != "unknown":
    doc_cat = DocumentCategory(
        doc_id=document.id,
        category=classification.category,
        confidence=classification.confidence,
        classified_by=classification.classified_by,
    )
    profile_db.add(doc_cat)

    # Run category-specific extractor
    if classification.category == "imaging":
        from modules.extract_imaging import extract_imaging_entities
        entities = extract_imaging_entities(ocr_text)
    elif classification.category == "pathology":
        from modules.extract_pathology import extract_pathology_entities
        entities = extract_pathology_entities(ocr_text)
    elif classification.category == "visit_notes":
        from modules.extract_visit_notes import extract_visit_note_entities
        entities = extract_visit_note_entities(ocr_text)
    else:
        entities = []

    for entity in entities:
        profile_db.add(DocumentEntity(
            doc_id=document.id,
            category=classification.category,
            entity_type=entity["entity_type"],
            entity_value=entity["entity_value"],
            confidence=entity["confidence"],
            source_page=entity.get("source_page"),
            source_bbox_json=entity.get("source_bbox_json"),
        ))
```

**Commit:** `feat(INGEST-A): wire classifier + extractors into document import pipeline`

---

### Task 22: INGEST-E — Frontend Entity Display Components

**Files:**
- Create: `src/frontend/src/components/documents/CategoryBadge.tsx`
- Create: `src/frontend/src/components/documents/EntityDetailView.tsx`
- Modify: Document list component to show category badge
- Create: `src/frontend/src/services/documentCategories.ts`

Components:
- `CategoryBadge`: Colored badge showing document category (imaging=blue, pathology=purple, visit_notes=green, lab=amber)
- `EntityDetailView`: Table of extracted entities per document, low-confidence entities shown with dashed border + warning icon
- Frontend service hooks for fetching categories/entities per document

**Commit:** `feat(INGEST-E): document category badges + entity detail view`

---

### Task 23: INGEST-F — RAG Category-Aware Retrieval

**Files:**
- Modify: `src/backend/modules/` (RAG retrieval module — add category filter)
- Test: `src/backend/tests/test_rag_category_filter.py`

Add optional `category` filter to the RAG retrieval pipeline so assistant queries can scope to specific document types.

**Commit:** `feat(INGEST-F): category-aware RAG retrieval with entity boosting`

---

## Summary

| Task | Feature | Scope | Commit Message |
|------|---------|-------|----------------|
| 1 | GAM-001 | Migration: timezone + voice + badges | `feat(GAM-001): migration for timezone, voice settings, badge tables` |
| 2 | GAM-001 | Models: BadgeDefinition + EarnedBadge | `feat(GAM-001): add BadgeDefinition, EarnedBadge models` |
| 3 | GAM-001 | Streak engine (TZ-aware) | `feat(GAM-001): timezone-aware streak computation engine` |
| 4 | GAM-001 | Badge evaluator (8 badges) | `feat(GAM-001): badge evaluation engine with all 8 badge criteria` |
| 5 | GAM-001 | API: gamification router + dose response | `feat(GAM-001): gamification API router + badge eval in dose response` |
| 6 | GAM-001 | Frontend: types + service | `feat(GAM-001): frontend types and service hooks for gamification` |
| 7 | GAM-001 | Frontend: BadgeToast + AchievementsWidget | `feat(GAM-001): BadgeToast + AchievementsWidget frontend components` |
| 8 | GAM-001 | Frontend: schedule matching in DoseLoggingModal | `feat(GAM-001): DoseLoggingModal auto-matches nearest schedule` |
| 9 | GAM-001 | Timezone settings API + frontend | `feat(GAM-001): timezone settings API + frontend picker` |
| 10 | VOICE | Permissions-Policy header update | `feat(MED-VOICE-001): allow microphone=(self) in Permissions-Policy` |
| 11 | VOICE | Voice settings API endpoints | `feat(MED-VOICE-001): voice settings GET/PATCH API endpoints` |
| 12 | VOICE | useSpeechRecognition hook | `feat(MED-VOICE-001): useSpeechRecognition hook with error handling` |
| 13 | VOICE | Voice button + first-use modal | `feat(MED-VOICE-001): voice button + first-use privacy modal` |
| 14 | VOICE | Voice toggle in Settings page | `feat(MED-VOICE-001): voice settings toggle in Settings page` |
| 15 | VOICE | API docs update | `docs(MED-VOICE-001): update dose logging API docs` |
| 16 | INGEST-A | Schema migration | `feat(INGEST-A): schema migration + models` |
| 17 | INGEST-A | Category classifier | `feat(INGEST-A): rule-based document category classifier` |
| 18 | INGEST-B | Imaging extractor | `feat(INGEST-B): imaging entity extractor` |
| 19 | INGEST-C | Pathology extractor | `feat(INGEST-C): pathology entity extractor` |
| 20 | INGEST-D | Visit notes extractor | `feat(INGEST-D): visit notes entity extractor` |
| 21 | INGEST-A | Wire into import pipeline | `feat(INGEST-A): wire classifier + extractors into import` |
| 22 | INGEST-E | Frontend entity display | `feat(INGEST-E): document category badges + entity detail view` |
| 23 | INGEST-F | RAG category filter | `feat(INGEST-F): category-aware RAG retrieval` |
