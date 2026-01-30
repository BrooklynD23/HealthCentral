"""
Pattern learning engine for medication adherence.

Learns behavioral patterns from dose history to enable
adaptive reminder scheduling.

Phase 2: Core Medication Management - Pattern Learning Component
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from statistics import mean, stdev
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Medication,
    MedicationSchedule,
    DoseTaken,
    AdherencePattern,
)

logger = logging.getLogger(__name__)


@dataclass
class TimeWindowPattern:
    """Learned time window for medication taking."""
    avg_minutes: int  # Minutes since midnight
    std_dev_minutes: float
    earliest_minutes: int
    latest_minutes: int
    confidence: float
    sample_size: int

    def to_time(self, minutes: int) -> time:
        """Convert minutes since midnight to time object."""
        hours = minutes // 60
        mins = minutes % 60
        return time(hour=min(hours, 23), minute=mins)

    @property
    def avg_time(self) -> time:
        return self.to_time(self.avg_minutes)

    @property
    def window_start(self) -> time:
        """Start of adaptive window (avg - 1.5 std dev)."""
        start_minutes = max(0, int(self.avg_minutes - 1.5 * self.std_dev_minutes))
        return self.to_time(start_minutes)

    @property
    def window_end(self) -> time:
        """End of adaptive window (avg + 1.5 std dev)."""
        end_minutes = min(1439, int(self.avg_minutes + 1.5 * self.std_dev_minutes))
        return self.to_time(end_minutes)


@dataclass
class WeekdayPattern:
    """Pattern for weekday vs weekend timing."""
    weekday_avg_minutes: int
    weekday_std_dev: float
    weekday_sample_size: int
    weekend_avg_minutes: int
    weekend_std_dev: float
    weekend_sample_size: int
    confidence: float

    @property
    def is_significantly_different(self) -> bool:
        """Check if weekday and weekend patterns are meaningfully different."""
        diff = abs(self.weekday_avg_minutes - self.weekend_avg_minutes)
        # More than 30 minutes difference
        return diff > 30 and self.confidence > 0.7


@dataclass
class MissedDayPattern:
    """Pattern for frequently missed days."""
    day_of_week: int  # 0=Monday, 6=Sunday
    miss_rate: float  # 0.0-1.0
    total_opportunities: int
    total_misses: int
    confidence: float


@dataclass
class StreakData:
    """Streak tracking data."""
    current_streak: int
    longest_streak: int
    last_break_date: Optional[datetime] = None
    total_adherent_days: int = 0


class PatternLearner:
    """
    Learns behavioral patterns from medication dose history.

    Patterns learned:
    - Time window: When user typically takes medication
    - Weekday vs weekend: Different patterns for different day types
    - Missed days: Days of week with higher miss rates
    - Streaks: Consecutive adherence tracking
    """

    # Minimum samples needed to establish reliable patterns
    MIN_SAMPLES_FOR_PATTERN = 7
    MIN_SAMPLES_FOR_WEEKDAY_PATTERN = 5

    # Confidence thresholds
    CONFIDENCE_THRESHOLD = 0.70

    # Outlier detection
    OUTLIER_THRESHOLD_STDEV = 2.5

    def __init__(self):
        """Initialize the pattern learner."""
        pass

    async def learn_all_patterns(
        self,
        medication_id: str,
        schedule_id: Optional[str],
        db: AsyncSession,
    ) -> dict:
        """
        Learn all patterns for a medication schedule.

        Args:
            medication_id: Medication UUID
            schedule_id: Optional schedule UUID
            db: Database session

        Returns:
            Dictionary with all learned patterns
        """
        patterns = {}

        # Learn time window
        time_window = await self.learn_time_window(
            medication_id=medication_id,
            schedule_id=schedule_id,
            db=db,
        )
        if time_window:
            patterns["time_window"] = time_window

        # Learn weekday vs weekend
        weekday_pattern = await self.learn_weekday_pattern(
            medication_id=medication_id,
            schedule_id=schedule_id,
            db=db,
        )
        if weekday_pattern:
            patterns["weekday_pattern"] = weekday_pattern

        # Learn missed day patterns
        missed_days = await self.learn_missed_day_pattern(
            medication_id=medication_id,
            db=db,
        )
        if missed_days:
            patterns["missed_days"] = missed_days

        # Calculate streak data
        streak = await self.calculate_streak(
            medication_id=medication_id,
            db=db,
        )
        patterns["streak"] = streak

        return patterns

    async def learn_time_window(
        self,
        medication_id: str,
        schedule_id: Optional[str],
        db: AsyncSession,
        days_lookback: int = 30,
    ) -> Optional[TimeWindowPattern]:
        """
        Learn the typical time window for taking a medication.

        Uses mean ± 1.5 standard deviations to capture ~86% of typical doses.
        """
        # Get recent non-skipped doses
        cutoff = datetime.utcnow() - timedelta(days=days_lookback)

        query = select(DoseTaken).where(
            and_(
                DoseTaken.medication_id == medication_id,
                DoseTaken.was_skipped == False,
                DoseTaken.taken_at >= cutoff,
            )
        )

        if schedule_id:
            query = query.where(DoseTaken.schedule_id == schedule_id)

        result = await db.execute(query.order_by(DoseTaken.taken_at.desc()))
        doses = result.scalars().all()

        if len(doses) < self.MIN_SAMPLES_FOR_PATTERN:
            logger.debug(
                f"Not enough samples for time window pattern: {len(doses)} < {self.MIN_SAMPLES_FOR_PATTERN}"
            )
            return None

        # Convert to minutes since midnight
        minutes_list = []
        for dose in doses:
            minutes = dose.taken_at.hour * 60 + dose.taken_at.minute
            minutes_list.append(minutes)

        # Remove outliers
        if len(minutes_list) >= 5:
            avg = mean(minutes_list)
            std = stdev(minutes_list) if len(minutes_list) > 1 else 0

            if std > 0:
                filtered = [
                    m for m in minutes_list
                    if abs(m - avg) / std <= self.OUTLIER_THRESHOLD_STDEV
                ]
                if len(filtered) >= self.MIN_SAMPLES_FOR_PATTERN:
                    minutes_list = filtered

        # Calculate statistics
        avg_minutes = int(mean(minutes_list))
        std_minutes = stdev(minutes_list) if len(minutes_list) > 1 else 30.0  # Default 30min std
        earliest = min(minutes_list)
        latest = max(minutes_list)

        # Calculate confidence based on consistency
        # Lower std dev = higher confidence
        confidence = max(0.0, min(1.0, 1.0 - (std_minutes / 120)))  # 2 hours = 0 confidence

        return TimeWindowPattern(
            avg_minutes=avg_minutes,
            std_dev_minutes=std_minutes,
            earliest_minutes=earliest,
            latest_minutes=latest,
            confidence=confidence,
            sample_size=len(minutes_list),
        )

    async def learn_weekday_pattern(
        self,
        medication_id: str,
        schedule_id: Optional[str],
        db: AsyncSession,
        days_lookback: int = 60,
    ) -> Optional[WeekdayPattern]:
        """
        Learn if weekday and weekend patterns differ.

        Returns pattern only if there's a meaningful difference.
        """
        cutoff = datetime.utcnow() - timedelta(days=days_lookback)

        query = select(DoseTaken).where(
            and_(
                DoseTaken.medication_id == medication_id,
                DoseTaken.was_skipped == False,
                DoseTaken.taken_at >= cutoff,
            )
        )

        if schedule_id:
            query = query.where(DoseTaken.schedule_id == schedule_id)

        result = await db.execute(query)
        doses = result.scalars().all()

        # Separate by weekday/weekend
        weekday_minutes = []
        weekend_minutes = []

        for dose in doses:
            minutes = dose.taken_at.hour * 60 + dose.taken_at.minute
            # Python weekday: Monday=0, Sunday=6
            if dose.taken_at.weekday() < 5:
                weekday_minutes.append(minutes)
            else:
                weekend_minutes.append(minutes)

        # Need minimum samples for both
        if (len(weekday_minutes) < self.MIN_SAMPLES_FOR_WEEKDAY_PATTERN or
            len(weekend_minutes) < self.MIN_SAMPLES_FOR_WEEKDAY_PATTERN):
            return None

        weekday_avg = int(mean(weekday_minutes))
        weekday_std = stdev(weekday_minutes) if len(weekday_minutes) > 1 else 30.0
        weekend_avg = int(mean(weekend_minutes))
        weekend_std = stdev(weekend_minutes) if len(weekend_minutes) > 1 else 30.0

        # Confidence based on sample size and consistency
        min_samples = min(len(weekday_minutes), len(weekend_minutes))
        sample_confidence = min(1.0, min_samples / 20)  # Max confidence at 20 samples
        consistency_confidence = max(0.0, 1.0 - (weekday_std + weekend_std) / 240)

        confidence = (sample_confidence + consistency_confidence) / 2

        return WeekdayPattern(
            weekday_avg_minutes=weekday_avg,
            weekday_std_dev=weekday_std,
            weekday_sample_size=len(weekday_minutes),
            weekend_avg_minutes=weekend_avg,
            weekend_std_dev=weekend_std,
            weekend_sample_size=len(weekend_minutes),
            confidence=confidence,
        )

    async def learn_missed_day_pattern(
        self,
        medication_id: str,
        db: AsyncSession,
        days_lookback: int = 60,
    ) -> Optional[list[MissedDayPattern]]:
        """
        Learn which days of the week have higher miss rates.

        Returns list of days with miss rates above average.
        """
        cutoff = datetime.utcnow() - timedelta(days=days_lookback)

        # Get all doses (taken and skipped)
        result = await db.execute(
            select(DoseTaken).where(
                and_(
                    DoseTaken.medication_id == medication_id,
                    DoseTaken.taken_at >= cutoff,
                )
            )
        )
        doses = result.scalars().all()

        if len(doses) < self.MIN_SAMPLES_FOR_PATTERN:
            return None

        # Count by day of week
        day_counts = {i: {"taken": 0, "skipped": 0} for i in range(7)}

        for dose in doses:
            day = dose.taken_at.weekday()
            if dose.was_skipped:
                day_counts[day]["skipped"] += 1
            else:
                day_counts[day]["taken"] += 1

        # Calculate miss rates
        patterns = []
        total_misses = sum(d["skipped"] for d in day_counts.values())
        total_taken = sum(d["taken"] for d in day_counts.values())
        overall_miss_rate = total_misses / max(total_taken + total_misses, 1)

        for day, counts in day_counts.items():
            total = counts["taken"] + counts["skipped"]
            if total < 2:
                continue

            miss_rate = counts["skipped"] / total

            # Only report days with above-average miss rate
            if miss_rate > overall_miss_rate and miss_rate > 0.1:
                confidence = min(1.0, total / 10)  # Higher sample = higher confidence
                patterns.append(MissedDayPattern(
                    day_of_week=day,
                    miss_rate=miss_rate,
                    total_opportunities=total,
                    total_misses=counts["skipped"],
                    confidence=confidence,
                ))

        return patterns if patterns else None

    async def calculate_streak(
        self,
        medication_id: str,
        db: AsyncSession,
    ) -> StreakData:
        """
        Calculate current and longest adherence streaks.
        """
        # Get all non-skipped doses ordered by date
        result = await db.execute(
            select(DoseTaken).where(
                and_(
                    DoseTaken.medication_id == medication_id,
                    DoseTaken.was_skipped == False,
                )
            ).order_by(DoseTaken.taken_at.asc())
        )
        doses = result.scalars().all()

        if not doses:
            return StreakData(
                current_streak=0,
                longest_streak=0,
                total_adherent_days=0,
            )

        # Get unique dates
        dates = sorted(set(dose.taken_at.date() for dose in doses))
        total_adherent_days = len(dates)

        # Calculate longest streak
        longest = 1
        current = 1
        last_break_date = None

        for i in range(1, len(dates)):
            gap = (dates[i] - dates[i-1]).days
            if gap == 1:
                current += 1
                longest = max(longest, current)
            else:
                if current >= longest // 2:  # Significant streak break
                    last_break_date = datetime.combine(dates[i-1], time())
                current = 1

        # Calculate current streak (counting backwards from today)
        today = datetime.utcnow().date()
        current_streak = 0
        check_date = today

        date_set = set(dates)
        while check_date in date_set:
            current_streak += 1
            check_date -= timedelta(days=1)

        return StreakData(
            current_streak=current_streak,
            longest_streak=longest,
            last_break_date=last_break_date,
            total_adherent_days=total_adherent_days,
        )

    async def update_adaptive_windows(
        self,
        medication_id: str,
        db: AsyncSession,
    ) -> int:
        """
        Update adaptive windows for all schedules of a medication.

        Returns count of schedules updated.
        """
        # Get all active schedules
        result = await db.execute(
            select(MedicationSchedule).where(
                and_(
                    MedicationSchedule.medication_id == medication_id,
                    MedicationSchedule.is_active == True,
                )
            )
        )
        schedules = result.scalars().all()

        updated_count = 0

        for schedule in schedules:
            pattern = await self.learn_time_window(
                medication_id=medication_id,
                schedule_id=schedule.id,
                db=db,
            )

            if pattern and pattern.confidence >= self.CONFIDENCE_THRESHOLD:
                schedule.adaptive_window_start = pattern.window_start
                schedule.adaptive_window_end = pattern.window_end
                updated_count += 1

                logger.info(
                    f"Updated adaptive window for schedule {schedule.id}: "
                    f"{pattern.window_start} - {pattern.window_end}"
                )

        if updated_count > 0:
            await db.commit()

        return updated_count

    async def save_patterns(
        self,
        medication_id: str,
        schedule_id: Optional[str],
        patterns: dict,
        db: AsyncSession,
    ) -> list[str]:
        """
        Save learned patterns to the database.

        Returns list of created pattern IDs.
        """
        created_ids = []

        # Delete existing patterns for this medication/schedule
        existing = await db.execute(
            select(AdherencePattern).where(
                and_(
                    AdherencePattern.medication_id == medication_id,
                    AdherencePattern.schedule_id == schedule_id if schedule_id else True,
                )
            )
        )
        for pattern in existing.scalars().all():
            await db.delete(pattern)

        # Save time window pattern
        if "time_window" in patterns:
            tw = patterns["time_window"]
            pattern = AdherencePattern(
                id=str(uuid.uuid4()),
                medication_id=medication_id,
                schedule_id=schedule_id,
                pattern_type="time_window",
                pattern_data_json=json.dumps({
                    "avg_minutes": tw.avg_minutes,
                    "std_dev_minutes": tw.std_dev_minutes,
                    "earliest": tw.earliest_minutes,
                    "latest": tw.latest_minutes,
                }),
                confidence=tw.confidence,
                sample_size=tw.sample_size,
                valid_until=datetime.utcnow() + timedelta(days=14),
            )
            db.add(pattern)
            created_ids.append(pattern.id)

        # Save weekday pattern
        if "weekday_pattern" in patterns:
            wp = patterns["weekday_pattern"]
            if wp.is_significantly_different:
                # Save weekday
                weekday_pattern = AdherencePattern(
                    id=str(uuid.uuid4()),
                    medication_id=medication_id,
                    schedule_id=schedule_id,
                    pattern_type="weekday_pattern",
                    pattern_data_json=json.dumps({
                        "avg_minutes": wp.weekday_avg_minutes,
                        "std_dev_minutes": wp.weekday_std_dev,
                        "sample_size": wp.weekday_sample_size,
                    }),
                    confidence=wp.confidence,
                    sample_size=wp.weekday_sample_size,
                    valid_until=datetime.utcnow() + timedelta(days=14),
                )
                db.add(weekday_pattern)
                created_ids.append(weekday_pattern.id)

                # Save weekend
                weekend_pattern = AdherencePattern(
                    id=str(uuid.uuid4()),
                    medication_id=medication_id,
                    schedule_id=schedule_id,
                    pattern_type="weekend_pattern",
                    pattern_data_json=json.dumps({
                        "avg_minutes": wp.weekend_avg_minutes,
                        "std_dev_minutes": wp.weekend_std_dev,
                        "sample_size": wp.weekend_sample_size,
                    }),
                    confidence=wp.confidence,
                    sample_size=wp.weekend_sample_size,
                    valid_until=datetime.utcnow() + timedelta(days=14),
                )
                db.add(weekend_pattern)
                created_ids.append(weekend_pattern.id)

        # Save missed day patterns
        if "missed_days" in patterns:
            for md in patterns["missed_days"]:
                pattern = AdherencePattern(
                    id=str(uuid.uuid4()),
                    medication_id=medication_id,
                    schedule_id=None,  # Missed days are medication-wide
                    pattern_type="missed_day_pattern",
                    pattern_data_json=json.dumps({
                        "day_of_week": md.day_of_week,
                        "miss_rate": md.miss_rate,
                        "total_opportunities": md.total_opportunities,
                        "total_misses": md.total_misses,
                    }),
                    confidence=md.confidence,
                    sample_size=md.total_opportunities,
                    valid_until=datetime.utcnow() + timedelta(days=14),
                )
                db.add(pattern)
                created_ids.append(pattern.id)

        # Save streak data
        if "streak" in patterns:
            streak = patterns["streak"]
            pattern = AdherencePattern(
                id=str(uuid.uuid4()),
                medication_id=medication_id,
                schedule_id=None,
                pattern_type="streak",
                pattern_data_json=json.dumps({
                    "current": streak.current_streak,
                    "longest": streak.longest_streak,
                    "last_break": streak.last_break_date.isoformat() if streak.last_break_date else None,
                    "total_adherent_days": streak.total_adherent_days,
                }),
                confidence=1.0,  # Streak is factual, not probabilistic
                sample_size=streak.total_adherent_days,
            )
            db.add(pattern)
            created_ids.append(pattern.id)

        await db.commit()
        return created_ids


# Global instance
_pattern_learner: Optional[PatternLearner] = None


def get_pattern_learner() -> PatternLearner:
    """Get or create the global pattern learner instance."""
    global _pattern_learner
    if _pattern_learner is None:
        _pattern_learner = PatternLearner()
    return _pattern_learner
