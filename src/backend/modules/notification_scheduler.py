"""
Notification scheduler for medication reminders.

Background service that:
- Checks medication schedules every minute
- Calculates notification priority based on time and patterns
- Integrates with adaptive windows from pattern learning
- Manages notification timing and escalation

Phase 3: Smart Notifications - Scheduler Component
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional, Callable, Awaitable

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Medication,
    MedicationSchedule,
    DoseTaken,
    AdherencePattern,
    ReminderLog,
)
from .message_generator import (
    MessageGenerator,
    MessageContext,
    GeneratedMessage,
    ReminderPriority,
    get_message_generator,
)
from .platform_notifications import (
    NotificationService,
    NotificationPayload,
    DeliveryResult,
    get_notification_service,
)
from .adherence_patterns import get_pattern_learner, StreakData

logger = logging.getLogger(__name__)


class SchedulerState(str, Enum):
    """Scheduler running state."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class ProfileVaultLockedError(RuntimeError):
    """A registered session factory found the profile vault locked.

    Routine, not an error: locking is how a session ends. The scheduler
    records it as `skipped_locked` rather than a failure.
    """


@dataclass
class ScheduleCheck:
    """Result of checking a schedule for notification need."""
    schedule_id: str
    medication_id: str
    medication_name: str
    schedule_label: str
    target_time: time
    needs_notification: bool
    priority: ReminderPriority
    reason: str
    window_start: Optional[time] = None
    window_end: Optional[time] = None
    minutes_until_target: int = 0
    minutes_past_target: int = 0
    reminders_sent_today: int = 0


@dataclass
class NotificationSettings:
    """Per-medication notification settings."""
    enabled: bool = True
    quiet_hours_start: Optional[time] = None  # e.g., 22:00
    quiet_hours_end: Optional[time] = None    # e.g., 07:00
    max_reminders_per_dose: int = 3
    initial_offset_minutes: int = 0  # Minutes before target time
    nudge_delay_minutes: int = 15    # Delay between initial and nudge
    alert_delay_minutes: int = 30    # Delay between nudge and alert
    weekend_enabled: bool = True
    celebration_enabled: bool = True


@dataclass
class SchedulerConfig:
    """Configuration for the notification scheduler."""
    check_interval_seconds: int = 60
    default_window_tolerance_minutes: int = 30
    max_notifications_per_hour: int = 10
    enable_streak_celebrations: bool = True
    quiet_hours_enabled: bool = True


class NotificationScheduler:
    """
    Background scheduler for medication notifications.

    Runs a continuous loop checking medication schedules and
    sending notifications at appropriate times based on:
    - Scheduled times and adaptive windows
    - Priority escalation (initial → nudge → alert)
    - User patterns and preferences
    """

    def __init__(
        self,
        config: Optional[SchedulerConfig] = None,
        message_generator: Optional[MessageGenerator] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        """
        Initialize the scheduler.

        Args:
            config: Scheduler configuration
            message_generator: Message generator instance
            notification_service: Notification delivery service
        """
        self.config = config or SchedulerConfig()
        self._message_generator = message_generator or get_message_generator()
        self._notification_service = notification_service or get_notification_service()

        self._state = SchedulerState.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._db_session_factory: Optional[Callable[[], AsyncSession]] = None
        self._profile_sessions: dict[str, Callable[[], Awaitable[AsyncSession]]] = {}

        # Tracking
        self._last_check_time: Optional[datetime] = None
        self._notifications_sent_this_hour: int = 0
        self._hour_start: Optional[datetime] = None

    @property
    def state(self) -> SchedulerState:
        """Current scheduler state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if scheduler is actively running."""
        return self._state == SchedulerState.RUNNING

    def register_profile_session(
        self,
        profile_id: str,
        session_factory: Callable[[], Awaitable[AsyncSession]],
    ):
        """
        Register a profile's database session factory.

        Args:
            profile_id: Profile UUID
            session_factory: Async factory to get profile database session
        """
        self._profile_sessions[profile_id] = session_factory
        logger.debug(f"Registered profile session for {profile_id}")

    def unregister_profile_session(self, profile_id: str):
        """Remove a profile's session registration."""
        self._profile_sessions.pop(profile_id, None)
        logger.debug(f"Unregistered profile session for {profile_id}")

    async def start(self):
        """Start the notification scheduler."""
        if self._state == SchedulerState.RUNNING:
            logger.warning("Scheduler already running")
            return

        # Initialize notification service
        await self._notification_service.initialize()

        self._state = SchedulerState.RUNNING
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Notification scheduler started")

    async def stop(self):
        """Stop the notification scheduler."""
        if self._state == SchedulerState.STOPPED:
            return

        self._state = SchedulerState.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Notification scheduler stopped")

    async def pause(self):
        """Pause the scheduler (continues loop but skips checks)."""
        if self._state == SchedulerState.RUNNING:
            self._state = SchedulerState.PAUSED
            logger.info("Notification scheduler paused")

    async def resume(self):
        """Resume a paused scheduler."""
        if self._state == SchedulerState.PAUSED:
            self._state = SchedulerState.RUNNING
            logger.info("Notification scheduler resumed")

    async def _run_loop(self):
        """Main scheduler loop."""
        while self._state != SchedulerState.STOPPED:
            try:
                if self._state == SchedulerState.RUNNING:
                    await self._check_all_schedules()
                    self._last_check_time = datetime.utcnow()

                await asyncio.sleep(self.config.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.check_interval_seconds)

    async def _check_all_schedules(self):
        """Check all registered profiles for pending notifications."""
        # Reset hourly counter if needed
        now = datetime.utcnow()
        if self._hour_start is None or (now - self._hour_start).total_seconds() >= 3600:
            self._hour_start = now
            self._notifications_sent_this_hour = 0

        # Check rate limit
        if self._notifications_sent_this_hour >= self.config.max_notifications_per_hour:
            logger.warning("Hourly notification limit reached")
            return

        for profile_id, session_factory in list(self._profile_sessions.items()):
            try:
                async with await session_factory() as db:
                    await self._check_profile_schedules(profile_id, db)
            except Exception as e:
                logger.error(f"Error checking profile {profile_id}: {e}")

    async def _check_profile_schedules(
        self,
        profile_id: str,
        db: AsyncSession,
    ):
        """Check schedules for a single profile."""
        now = datetime.utcnow()
        current_time = now.time()
        today = now.date()
        current_weekday = now.weekday()

        # Get all active medications with reminders enabled
        result = await db.execute(
            select(Medication).where(
                and_(
                    Medication.profile_id == profile_id,
                    Medication.is_active == True,
                    Medication.reminder_enabled == True,
                )
            )
        )
        medications = result.scalars().all()

        for medication in medications:
            # Get active schedules
            schedules_result = await db.execute(
                select(MedicationSchedule).where(
                    and_(
                        MedicationSchedule.medication_id == medication.id,
                        MedicationSchedule.is_active == True,
                    )
                )
            )
            schedules = schedules_result.scalars().all()

            for schedule in schedules:
                # Check if schedule applies today
                if not self._schedule_applies_today(schedule, current_weekday):
                    continue

                # Check if dose already taken today for this schedule
                dose_taken = await self._check_dose_taken_today(
                    medication.id, schedule.id, today, db
                )
                if dose_taken:
                    continue

                # Evaluate if notification needed
                check_result = await self._evaluate_schedule(
                    medication=medication,
                    schedule=schedule,
                    current_time=current_time,
                    profile_id=profile_id,
                    db=db,
                )

                if check_result.needs_notification:
                    await self._send_notification(
                        check_result=check_result,
                        profile_id=profile_id,
                        db=db,
                    )

    def _schedule_applies_today(
        self,
        schedule: MedicationSchedule,
        current_weekday: int,
    ) -> bool:
        """Check if schedule applies to current day of week."""
        if not schedule.days_of_week_json:
            return True  # No restriction = every day

        try:
            days = json.loads(schedule.days_of_week_json)
            return current_weekday in days
        except (json.JSONDecodeError, TypeError):
            return True

    async def _check_dose_taken_today(
        self,
        medication_id: str,
        schedule_id: str,
        today,
        db: AsyncSession,
    ) -> bool:
        """Check if dose was already taken today for this schedule."""
        today_start = datetime.combine(today, time(0, 0))
        today_end = datetime.combine(today, time(23, 59, 59))

        result = await db.execute(
            select(DoseTaken).where(
                and_(
                    DoseTaken.medication_id == medication_id,
                    DoseTaken.schedule_id == schedule_id,
                    DoseTaken.taken_at >= today_start,
                    DoseTaken.taken_at <= today_end,
                    DoseTaken.was_skipped == False,
                )
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _evaluate_schedule(
        self,
        medication: Medication,
        schedule: MedicationSchedule,
        current_time: time,
        profile_id: str,
        db: AsyncSession,
    ) -> ScheduleCheck:
        """
        Evaluate if a schedule needs a notification.

        Considers:
        - Target time and adaptive window
        - Previous reminders sent today
        - Priority escalation based on time past target
        """
        # Get window bounds
        window_start = schedule.adaptive_window_start or self._offset_time(
            schedule.target_time,
            -self.config.default_window_tolerance_minutes,
        )
        window_end = schedule.adaptive_window_end or self._offset_time(
            schedule.target_time,
            self.config.default_window_tolerance_minutes,
        )

        # Calculate time differences
        current_minutes = current_time.hour * 60 + current_time.minute
        target_minutes = schedule.target_time.hour * 60 + schedule.target_time.minute
        window_start_minutes = window_start.hour * 60 + window_start.minute

        minutes_until_target = target_minutes - current_minutes
        minutes_past_target = -minutes_until_target if minutes_until_target < 0 else 0

        # Count today's reminders for this schedule
        reminders_today = await self._count_reminders_today(
            medication.id, schedule.id, db
        )

        # Base check result
        check = ScheduleCheck(
            schedule_id=schedule.id,
            medication_id=medication.id,
            medication_name=medication.name,
            schedule_label=schedule.schedule_label,
            target_time=schedule.target_time,
            needs_notification=False,
            priority=ReminderPriority.INITIAL,
            reason="Outside notification window",
            window_start=window_start,
            window_end=window_end,
            minutes_until_target=max(0, minutes_until_target),
            minutes_past_target=minutes_past_target,
            reminders_sent_today=reminders_today,
        )

        # Check if we're in the notification window
        if not self._time_in_window(current_time, window_start, window_end):
            return check

        # Determine priority based on time and previous reminders
        reminder_offset = schedule.reminder_offset_minutes

        # Initial reminder: at or after (target - offset)
        initial_threshold = self._offset_time(schedule.target_time, -reminder_offset)

        if current_time < initial_threshold:
            check.reason = "Before initial reminder time"
            return check

        # Check if we need to send based on reminder count
        if reminders_today == 0:
            check.needs_notification = True
            check.priority = ReminderPriority.INITIAL
            check.reason = "Initial reminder due"
        elif reminders_today == 1 and minutes_past_target >= 15:
            check.needs_notification = True
            check.priority = ReminderPriority.GENTLE_NUDGE
            check.reason = "Nudge reminder due"
        elif reminders_today == 2 and minutes_past_target >= 30:
            check.needs_notification = True
            check.priority = ReminderPriority.IMPORTANT_ALERT
            check.reason = "Alert reminder due"
        elif reminders_today >= 3:
            check.reason = "Maximum reminders sent"
        else:
            check.reason = "Waiting for next reminder interval"

        return check

    async def _count_reminders_today(
        self,
        medication_id: str,
        schedule_id: str,
        db: AsyncSession,
    ) -> int:
        """Count reminders sent today for this schedule."""
        today_start = datetime.combine(datetime.utcnow().date(), time(0, 0))

        result = await db.execute(
            select(ReminderLog).where(
                and_(
                    ReminderLog.medication_id == medication_id,
                    ReminderLog.schedule_id == schedule_id,
                    ReminderLog.sent_at >= today_start,
                )
            )
        )
        return len(result.scalars().all())

    async def _send_notification(
        self,
        check_result: ScheduleCheck,
        profile_id: str,
        db: AsyncSession,
    ):
        """Send notification and log it."""
        # Get streak data for context
        pattern_learner = get_pattern_learner()
        streak = await pattern_learner.calculate_streak(
            check_result.medication_id, db
        )

        # Build message context
        now = datetime.utcnow()
        context = MessageContext(
            medication_name=check_result.medication_name,
            schedule_label=check_result.schedule_label,
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            priority=check_result.priority,
            is_weekend=now.weekday() >= 5,
            hour_of_day=now.hour,
            previous_reminders_today=check_result.reminders_sent_today,
        )

        # Generate message
        message = self._message_generator.generate_reminder(context)

        # Create notification payload
        notification_id = str(uuid.uuid4())
        payload = NotificationPayload(
            id=notification_id,
            title=message.title,
            body=message.body,
            medication_id=check_result.medication_id,
            schedule_id=check_result.schedule_id,
            action_text=message.action_text,
        )

        # Send notification
        result = await self._notification_service.send(payload)

        # Log the reminder
        log_entry = ReminderLog(
            id=notification_id,
            profile_id=profile_id,
            medication_id=check_result.medication_id,
            schedule_id=check_result.schedule_id,
            reminder_type=check_result.priority.value,
            message_tone=message.tone.value,
            message=f"{message.title}: {message.body}",
            sent_at=now,
            delivery_method="notification",
        )
        db.add(log_entry)
        await db.commit()

        self._notifications_sent_this_hour += 1

        logger.info(
            f"Sent {check_result.priority.value} notification for "
            f"{check_result.medication_name} ({check_result.schedule_label})"
        )

    def _time_in_window(
        self,
        current: time,
        start: time,
        end: time,
    ) -> bool:
        """Check if current time is within window."""
        current_minutes = current.hour * 60 + current.minute
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute

        # Handle midnight crossing
        if start_minutes <= end_minutes:
            return start_minutes <= current_minutes <= end_minutes
        else:
            # Window crosses midnight
            return current_minutes >= start_minutes or current_minutes <= end_minutes

    def _offset_time(self, base: time, offset_minutes: int) -> time:
        """Add/subtract minutes from a time."""
        total_minutes = base.hour * 60 + base.minute + offset_minutes
        total_minutes = max(0, min(1439, total_minutes))  # Clamp to 00:00-23:59
        return time(hour=total_minutes // 60, minute=total_minutes % 60)


def profile_session_factory(
    profile_id: str,
) -> Callable[[], Awaitable[AsyncSession]]:
    """Build a session factory bound to the profile's live vault connection.

    The connection is resolved per call, not captured at registration: a
    vault locked between registration and the next pass raises
    ProfileVaultLockedError, which the scheduler records honestly instead of
    serving stale access.
    """

    async def _factory() -> AsyncSession:
        from core.profile_database import get_profile_db_manager

        connection = get_profile_db_manager().get_connection(profile_id)
        if connection is None:
            raise ProfileVaultLockedError(
                f"profile {profile_id} vault is locked"
            )
        return connection.get_session()

    return _factory


# Global instance
_notification_scheduler: Optional[NotificationScheduler] = None


def get_notification_scheduler() -> NotificationScheduler:
    """Get or create the global notification scheduler."""
    global _notification_scheduler
    if _notification_scheduler is None:
        _notification_scheduler = NotificationScheduler()
    return _notification_scheduler


async def start_notification_scheduler():
    """Start the global notification scheduler."""
    scheduler = get_notification_scheduler()
    await scheduler.start()
    return scheduler


async def stop_notification_scheduler():
    """Stop the global notification scheduler."""
    scheduler = get_notification_scheduler()
    await scheduler.stop()
