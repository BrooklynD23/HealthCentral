"""
Medication adherence models for the Adaptive Medication Adherence Coach.

Stores medications, schedules, dose records, and learned behavioral patterns
for intelligent, adaptive medication reminders.

Phase 0: Foundation for Medication Adherence Coach feature.

Note: All medication data is stored in per-profile encrypted databases
since it contains sensitive health information.
"""

from datetime import datetime, time
from typing import Optional

from sqlalchemy import String, Float, Boolean, Integer, DateTime, Time, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.profile_database import ProfileDatabaseBase
from core.time import utcnow


class Medication(ProfileDatabaseBase):
    """
    User's medication record.

    Stores medication identity, dosage, frequency, and reminder preferences.
    Each medication can have multiple schedules (e.g., morning, evening).

    Safety note: This is a reminder tool only. Never stores prescriptions
    or medical advice.
    """

    __tablename__ = "medications"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Profile ID (stored but not FK - profiles in master DB)
    profile_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )

    # Medication identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    generic_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Dosage information (user-provided, not medical advice)
    dosage_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dosage_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "mg", "mcg", "ml", etc.
    dosage_form: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "tablet", "capsule", "liquid"

    # Frequency
    # Values: "once_daily", "twice_daily", "three_times_daily", "four_times_daily",
    #         "every_other_day", "weekly", "as_needed", "custom"
    frequency: Mapped[str] = mapped_column(String(30), nullable=False, default="once_daily")

    # Custom frequency details (JSON for complex schedules)
    frequency_details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # User instructions/notes
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Extended metadata (JSON for flexible storage)
    # Can include: prescriber, pharmacy, refill date, NDC code, etc.
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Medication lifecycle dates
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    schedules: Mapped[list["MedicationSchedule"]] = relationship(
        "MedicationSchedule",
        back_populates="medication",
        cascade="all, delete-orphan",
    )
    doses: Mapped[list["DoseTaken"]] = relationship(
        "DoseTaken",
        back_populates="medication",
        cascade="all, delete-orphan",
    )
    patterns: Mapped[list["AdherencePattern"]] = relationship(
        "AdherencePattern",
        back_populates="medication",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Medication(id={self.id!r}, name={self.name!r}, active={self.is_active})>"


class MedicationSchedule(ProfileDatabaseBase):
    """
    Schedule for when a medication should be taken.

    A medication can have multiple schedules (e.g., morning and evening).
    Schedules include both user-set target times and learned adaptive windows.
    """

    __tablename__ = "medication_schedules"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign key to medication
    medication_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable label
    # Values: "morning", "midday", "afternoon", "evening", "bedtime", "custom"
    schedule_label: Mapped[str] = mapped_column(String(30), nullable=False)

    # User-set target time (baseline)
    target_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Learned adaptive window (updated by pattern learning)
    # If null, use target_time ± default tolerance
    adaptive_window_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    adaptive_window_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # Minutes before target_time to send first reminder
    reminder_offset_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    # Days of week this schedule applies (JSON array)
    # Format: [0, 1, 2, 3, 4] for Mon-Fri, [5, 6] for weekends, null for daily
    # 0=Monday, 6=Sunday (ISO weekday)
    days_of_week_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Whether this schedule is currently active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    medication: Mapped["Medication"] = relationship(
        "Medication", back_populates="schedules"
    )
    doses: Mapped[list["DoseTaken"]] = relationship(
        "DoseTaken", back_populates="schedule"
    )
    patterns: Mapped[list["AdherencePattern"]] = relationship(
        "AdherencePattern", back_populates="schedule"
    )

    def __repr__(self) -> str:
        return f"<MedicationSchedule(id={self.id!r}, label={self.schedule_label!r}, time={self.target_time})>"


class DoseTaken(ProfileDatabaseBase):
    """
    Record of a dose taken (or skipped).

    Captures when doses were actually taken, how they were logged,
    and variance from scheduled time for pattern learning.
    """

    __tablename__ = "doses_taken"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign key to medication
    medication_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional FK to schedule (may be null for as-needed meds)
    schedule_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("medication_schedules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # When the dose was taken (or when it should have been taken if skipped)
    taken_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )

    # How the dose was logged
    # Values: "manual", "notification_tap", "voice", "quick_log", "bulk_log"
    log_method: Mapped[str] = mapped_column(String(30), nullable=False)

    # Actual dosage taken (may differ from medication default)
    dosage_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dosage_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Variance from scheduled time in minutes
    # Positive = late, Negative = early, Null = no schedule
    variance_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # User notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Skip tracking
    was_skipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Skip reasons: "forgot", "side_effects", "ran_out", "felt_unnecessary", "doctor_advised", "other"

    # When the log entry was created (may differ from taken_at for retroactive logging)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    # Relationships
    medication: Mapped["Medication"] = relationship(
        "Medication", back_populates="doses"
    )
    schedule: Mapped[Optional["MedicationSchedule"]] = relationship(
        "MedicationSchedule", back_populates="doses"
    )

    def __repr__(self) -> str:
        status = "skipped" if self.was_skipped else "taken"
        return f"<DoseTaken(id={self.id!r}, medication_id={self.medication_id!r}, {status} at {self.taken_at})>"


class AdherencePattern(ProfileDatabaseBase):
    """
    Learned behavioral patterns for adaptive scheduling.

    Pattern types:
    - time_window: Average time and standard deviation for this schedule
    - weekday_vs_weekend: Different patterns for weekdays vs weekends
    - missed_day_pattern: Frequently missed day of week
    - streak_pattern: Consecutive adherence tracking

    Patterns are recalculated periodically based on recent dose history.
    """

    __tablename__ = "adherence_patterns"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign key to medication
    medication_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional FK to schedule (pattern may apply to specific schedule or whole medication)
    schedule_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("medication_schedules.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Pattern type
    # Values: "time_window", "weekday_pattern", "weekend_pattern",
    #         "missed_day_pattern", "streak", "variance_trend"
    pattern_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Pattern data (JSON object with type-specific fields)
    # time_window: {"avg_minutes": 495, "std_dev_minutes": 23, "earliest": 450, "latest": 540}
    # weekday_pattern: {"avg_minutes": 480, "sample_size": 20}
    # weekend_pattern: {"avg_minutes": 570, "sample_size": 8}
    # missed_day_pattern: {"day_of_week": 2, "miss_rate": 0.4}  # Tuesday
    # streak: {"current": 12, "longest": 24, "last_break": "2025-01-01"}
    pattern_data_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Confidence in this pattern (0.0-1.0)
    # Based on sample size and consistency
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Number of data points used to derive this pattern
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # When this pattern was last calculated
    learned_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    # Pattern validity period (should be recalculated after this date)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    medication: Mapped["Medication"] = relationship(
        "Medication", back_populates="patterns"
    )
    schedule: Mapped[Optional["MedicationSchedule"]] = relationship(
        "MedicationSchedule", back_populates="patterns"
    )

    def __repr__(self) -> str:
        return f"<AdherencePattern(id={self.id!r}, type={self.pattern_type!r}, confidence={self.confidence:.2f})>"


class ReminderLog(ProfileDatabaseBase):
    """
    Log of reminders sent to the user.

    Tracks:
    - What reminders were sent and when
    - Priority level and message content
    - User interaction (dismissed, snoozed, marked taken)

    Used for analyzing reminder effectiveness and avoiding notification fatigue.
    """

    __tablename__ = "reminder_logs"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Profile ID (for querying all reminders across medications)
    profile_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )

    # Foreign key to medication
    medication_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional FK to schedule
    schedule_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("medication_schedules.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Reminder classification
    # Values: "initial", "gentle_nudge", "important_alert"
    reminder_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Message tone
    # Values: "supportive", "friendly", "concerned"
    message_tone: Mapped[str] = mapped_column(String(20), nullable=False)

    # The actual message sent
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # When the reminder was sent
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, index=True
    )

    # Delivery method
    # Values: "notification", "in_app", "voice", "email"
    delivery_method: Mapped[str] = mapped_column(String(20), nullable=False)

    # User interaction tracking
    was_interacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    interaction_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Values: "dismissed", "snoozed", "marked_taken", "opened_app"
    interacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Snooze tracking
    snooze_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ReminderLog(id={self.id!r}, type={self.reminder_type!r}, sent_at={self.sent_at})>"
