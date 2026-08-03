"""
Notification management API endpoints.

Handles notification settings, history, and test notifications
for the medication reminder system.

Phase 3: Smart Notifications
"""

import json
import logging
import re
import uuid
from typing import Optional
from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.audit import log_document_event
from core.auth import RequireAuth, Session, ProfileDbSession
from models import (
    Medication,
    MedicationSchedule,
    ReminderLog,
)
from modules.notification_scheduler import (
    get_notification_scheduler,
    NotificationSettings,
)
from modules.message_generator import (
    get_message_generator,
    MessageContext,
    ReminderPriority,
)
from modules.platform_notifications import (
    get_notification_service,
    NotificationPayload,
)
from modules.adherence_patterns import get_pattern_learner

logger = logging.getLogger(__name__)

router = APIRouter()

# UUID validation pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def validate_uuid(value: str, field_name: str = "ID") -> str:
    """Validate that a string is a valid UUID format."""
    if not UUID_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format"
        )
    return value


# Request/Response Models


class NotificationSettingsUpdate(BaseModel):
    """Request to update notification settings."""
    enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(None, description="Time in HH:MM format")
    quiet_hours_end: Optional[str] = Field(None, description="Time in HH:MM format")
    max_reminders_per_dose: Optional[int] = Field(None, ge=1, le=5)
    initial_offset_minutes: Optional[int] = Field(None, ge=0, le=60)
    nudge_delay_minutes: Optional[int] = Field(None, ge=5, le=60)
    alert_delay_minutes: Optional[int] = Field(None, ge=10, le=120)
    weekend_enabled: Optional[bool] = None
    celebration_enabled: Optional[bool] = None


class NotificationSettingsResponse(BaseModel):
    """Response for notification settings."""
    medication_id: str
    enabled: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    max_reminders_per_dose: int
    initial_offset_minutes: int
    nudge_delay_minutes: int
    alert_delay_minutes: int
    weekend_enabled: bool
    celebration_enabled: bool


class ReminderLogResponse(BaseModel):
    """Response for reminder log entry."""
    id: str
    medication_id: str
    medication_name: str
    schedule_id: Optional[str] = None
    reminder_type: str
    message_tone: str
    message: str
    sent_at: str
    delivery_method: str
    was_interacted: bool
    interaction_type: Optional[str] = None
    interacted_at: Optional[str] = None


class NotificationHistoryResponse(BaseModel):
    """Response for notification history."""
    total: int
    reminders: list[ReminderLogResponse]
    stats: dict


class TestNotificationRequest(BaseModel):
    """Request to send a test notification."""
    title: Optional[str] = "Test Notification"
    body: Optional[str] = "This is a test notification from Asclexis."


class TestNotificationResponse(BaseModel):
    """Response for test notification."""
    success: bool
    platform: str
    message: str


class SchedulerStatusResponse(BaseModel):
    """Response for scheduler status."""
    state: str
    active_platform: Optional[str] = None
    registered_profiles: int
    notifications_sent_this_hour: int
    last_check: Optional[str] = None


# Endpoints


@router.get(
    "/settings/{medication_id}",
    response_model=NotificationSettingsResponse,
)
async def get_notification_settings(
    medication_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Get notification settings for a medication.

    Returns current notification preferences including quiet hours,
    reminder frequency, and celebration settings.
    """
    validate_uuid(medication_id, "medication_id")

    result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    if medication.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get settings from metadata
    settings = _get_settings_from_medication(medication)

    return NotificationSettingsResponse(
        medication_id=medication_id,
        enabled=medication.reminder_enabled,
        quiet_hours_start=settings.quiet_hours_start.strftime("%H:%M") if settings.quiet_hours_start else None,
        quiet_hours_end=settings.quiet_hours_end.strftime("%H:%M") if settings.quiet_hours_end else None,
        max_reminders_per_dose=settings.max_reminders_per_dose,
        initial_offset_minutes=settings.initial_offset_minutes,
        nudge_delay_minutes=settings.nudge_delay_minutes,
        alert_delay_minutes=settings.alert_delay_minutes,
        weekend_enabled=settings.weekend_enabled,
        celebration_enabled=settings.celebration_enabled,
    )


@router.patch(
    "/settings/{medication_id}",
    response_model=NotificationSettingsResponse,
)
async def update_notification_settings(
    medication_id: str,
    update: NotificationSettingsUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Update notification settings for a medication.

    Allows configuring quiet hours, reminder frequency,
    and other notification preferences.
    """
    validate_uuid(medication_id, "medication_id")

    result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    if medication.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get current settings
    current_metadata = {}
    if medication.metadata_json:
        try:
            current_metadata = json.loads(medication.metadata_json)
        except json.JSONDecodeError:
            pass

    notification_settings = current_metadata.get("notification_settings", {})

    # Update enabled flag
    if update.enabled is not None:
        medication.reminder_enabled = update.enabled

    # Update settings
    if update.quiet_hours_start is not None:
        notification_settings["quiet_hours_start"] = update.quiet_hours_start
    if update.quiet_hours_end is not None:
        notification_settings["quiet_hours_end"] = update.quiet_hours_end
    if update.max_reminders_per_dose is not None:
        notification_settings["max_reminders_per_dose"] = update.max_reminders_per_dose
    if update.initial_offset_minutes is not None:
        notification_settings["initial_offset_minutes"] = update.initial_offset_minutes
    if update.nudge_delay_minutes is not None:
        notification_settings["nudge_delay_minutes"] = update.nudge_delay_minutes
    if update.alert_delay_minutes is not None:
        notification_settings["alert_delay_minutes"] = update.alert_delay_minutes
    if update.weekend_enabled is not None:
        notification_settings["weekend_enabled"] = update.weekend_enabled
    if update.celebration_enabled is not None:
        notification_settings["celebration_enabled"] = update.celebration_enabled

    current_metadata["notification_settings"] = notification_settings
    medication.metadata_json = json.dumps(current_metadata)

    await profile_db.commit()
    await profile_db.refresh(medication)

    # Return updated settings
    settings = _get_settings_from_medication(medication)

    logger.info(f"Updated notification settings for medication {medication_id}")

    return NotificationSettingsResponse(
        medication_id=medication_id,
        enabled=medication.reminder_enabled,
        quiet_hours_start=settings.quiet_hours_start.strftime("%H:%M") if settings.quiet_hours_start else None,
        quiet_hours_end=settings.quiet_hours_end.strftime("%H:%M") if settings.quiet_hours_end else None,
        max_reminders_per_dose=settings.max_reminders_per_dose,
        initial_offset_minutes=settings.initial_offset_minutes,
        nudge_delay_minutes=settings.nudge_delay_minutes,
        alert_delay_minutes=settings.alert_delay_minutes,
        weekend_enabled=settings.weekend_enabled,
        celebration_enabled=settings.celebration_enabled,
    )


@router.get(
    "/history",
    response_model=NotificationHistoryResponse,
)
async def get_notification_history(
    session: RequireAuth,
    medication_id: Optional[str] = Query(None, description="Filter by medication"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    profile_db: ProfileDbSession = None,
):
    """
    Get notification history for the profile.

    Returns past reminders with interaction data and statistics.
    """
    if medication_id:
        validate_uuid(medication_id, "medication_id")

    # Build query
    query = select(ReminderLog).where(
        ReminderLog.profile_id == session.profile_id
    )

    if medication_id:
        query = query.where(ReminderLog.medication_id == medication_id)
    if from_date:
        query = query.where(ReminderLog.sent_at >= from_date)
    if to_date:
        query = query.where(ReminderLog.sent_at <= to_date)

    # Get total count
    count_query = select(func.count(ReminderLog.id)).where(
        ReminderLog.profile_id == session.profile_id
    )
    if medication_id:
        count_query = count_query.where(ReminderLog.medication_id == medication_id)
    if from_date:
        count_query = count_query.where(ReminderLog.sent_at >= from_date)
    if to_date:
        count_query = count_query.where(ReminderLog.sent_at <= to_date)

    count_result = await profile_db.execute(count_query)
    total = count_result.scalar() or 0

    # Get reminders
    query = query.order_by(ReminderLog.sent_at.desc()).offset(offset).limit(limit)
    result = await profile_db.execute(query)
    reminders = result.scalars().all()

    # Get medication names for display
    medication_names = {}
    if reminders:
        med_ids = list(set(r.medication_id for r in reminders))
        med_result = await profile_db.execute(
            select(Medication).where(Medication.id.in_(med_ids))
        )
        medications = med_result.scalars().all()
        medication_names = {m.id: m.name for m in medications}

    # Build response
    reminder_responses = []
    for r in reminders:
        reminder_responses.append(ReminderLogResponse(
            id=r.id,
            medication_id=r.medication_id,
            medication_name=medication_names.get(r.medication_id, "Unknown"),
            schedule_id=r.schedule_id,
            reminder_type=r.reminder_type,
            message_tone=r.message_tone,
            message=r.message,
            sent_at=r.sent_at.isoformat(),
            delivery_method=r.delivery_method,
            was_interacted=r.was_interacted,
            interaction_type=r.interaction_type,
            interacted_at=r.interacted_at.isoformat() if r.interacted_at else None,
        ))

    # Calculate stats
    stats = await _calculate_notification_stats(
        session.profile_id,
        medication_id,
        profile_db,
    )

    return NotificationHistoryResponse(
        total=total,
        reminders=reminder_responses,
        stats=stats,
    )


@router.post(
    "/test",
    response_model=TestNotificationResponse,
)
async def send_test_notification(
    request: TestNotificationRequest,
    session: RequireAuth,
):
    """
    Send a test notification.

    Useful for verifying notification delivery is working correctly.
    """
    service = get_notification_service()

    # Initialize if not already
    await service.initialize()

    payload = NotificationPayload(
        id=str(uuid.uuid4()),
        title=request.title or "Test Notification",
        body=request.body or "This is a test notification from Asclexis.",
        medication_id="test",
    )

    result = await service.send(payload)

    return TestNotificationResponse(
        success=result.success,
        platform=result.platform.value if result.platform else "none",
        message=result.error_message if not result.success else "Notification sent successfully",
    )


@router.post(
    "/test/{medication_id}",
    response_model=TestNotificationResponse,
)
async def send_test_medication_notification(
    medication_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Send a test notification for a specific medication.

    Generates a realistic reminder message based on the medication's
    current streak and schedule.
    """
    validate_uuid(medication_id, "medication_id")

    result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    if medication.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get streak data
    pattern_learner = get_pattern_learner()
    streak = await pattern_learner.calculate_streak(medication_id, profile_db)

    # Generate message
    now = datetime.utcnow()
    context = MessageContext(
        medication_name=medication.name,
        schedule_label="test",
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        priority=ReminderPriority.INITIAL,
        is_weekend=now.weekday() >= 5,
        hour_of_day=now.hour,
        previous_reminders_today=0,
    )

    generator = get_message_generator()
    message = generator.generate_reminder(context)

    # Send notification
    service = get_notification_service()
    await service.initialize()

    payload = NotificationPayload(
        id=str(uuid.uuid4()),
        title=message.title,
        body=message.body,
        medication_id=medication_id,
        action_text=message.action_text,
    )

    delivery_result = await service.send(payload)

    return TestNotificationResponse(
        success=delivery_result.success,
        platform=delivery_result.platform.value if delivery_result.platform else "none",
        message=delivery_result.error_message if not delivery_result.success else f"Sent: {message.title}",
    )


@router.get(
    "/scheduler/status",
    response_model=SchedulerStatusResponse,
)
async def get_scheduler_status(
    session: RequireAuth,
):
    """
    Get the status of the notification scheduler.

    Returns scheduler state, active platform, and statistics.
    """
    scheduler = get_notification_scheduler()
    service = get_notification_service()

    return SchedulerStatusResponse(
        state=scheduler.state.value,
        active_platform=service.active_platform.value if service.active_platform else None,
        registered_profiles=len(scheduler._profile_sessions),
        notifications_sent_this_hour=scheduler._notifications_sent_this_hour,
        last_check=scheduler._last_check_time.isoformat() if scheduler._last_check_time else None,
    )


@router.post(
    "/{reminder_id}/interaction",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def record_reminder_interaction(
    reminder_id: str,
    session: RequireAuth,
    interaction_type: str = Query(..., pattern="^(dismissed|snoozed|marked_taken|opened_app)$"),
    snooze_minutes: Optional[int] = Query(None, ge=5, le=60),
    profile_db: ProfileDbSession = None,
):
    """
    Record user interaction with a reminder.

    Called when user interacts with a notification (dismiss, snooze, mark taken).
    """
    validate_uuid(reminder_id, "reminder_id")

    result = await profile_db.execute(
        select(ReminderLog).where(ReminderLog.id == reminder_id)
    )
    reminder = result.scalar_one_or_none()

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )

    if reminder.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    reminder.was_interacted = True
    reminder.interaction_type = interaction_type
    reminder.interacted_at = datetime.utcnow()

    if interaction_type == "snoozed" and snooze_minutes:
        reminder.snooze_minutes = snooze_minutes

    await profile_db.commit()

    logger.info(f"Recorded interaction {interaction_type} for reminder {reminder_id}")


# Helper functions


def _get_settings_from_medication(medication: Medication) -> NotificationSettings:
    """Extract notification settings from medication metadata."""
    settings = NotificationSettings()

    if medication.metadata_json:
        try:
            metadata = json.loads(medication.metadata_json)
            ns = metadata.get("notification_settings", {})

            if "quiet_hours_start" in ns:
                try:
                    h, m = map(int, ns["quiet_hours_start"].split(":"))
                    settings.quiet_hours_start = time(hour=h, minute=m)
                except (ValueError, AttributeError):
                    pass

            if "quiet_hours_end" in ns:
                try:
                    h, m = map(int, ns["quiet_hours_end"].split(":"))
                    settings.quiet_hours_end = time(hour=h, minute=m)
                except (ValueError, AttributeError):
                    pass

            if "max_reminders_per_dose" in ns:
                settings.max_reminders_per_dose = ns["max_reminders_per_dose"]
            if "initial_offset_minutes" in ns:
                settings.initial_offset_minutes = ns["initial_offset_minutes"]
            if "nudge_delay_minutes" in ns:
                settings.nudge_delay_minutes = ns["nudge_delay_minutes"]
            if "alert_delay_minutes" in ns:
                settings.alert_delay_minutes = ns["alert_delay_minutes"]
            if "weekend_enabled" in ns:
                settings.weekend_enabled = ns["weekend_enabled"]
            if "celebration_enabled" in ns:
                settings.celebration_enabled = ns["celebration_enabled"]

        except json.JSONDecodeError:
            pass

    return settings


async def _calculate_notification_stats(
    profile_id: str,
    medication_id: Optional[str],
    db: AsyncSession,
) -> dict:
    """Calculate notification statistics."""
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    base_filter = [ReminderLog.profile_id == profile_id]
    if medication_id:
        base_filter.append(ReminderLog.medication_id == medication_id)

    # Total sent last 7 days
    result_7d = await db.execute(
        select(func.count(ReminderLog.id)).where(
            and_(*base_filter, ReminderLog.sent_at >= seven_days_ago)
        )
    )
    sent_7d = result_7d.scalar() or 0

    # Total sent last 30 days
    result_30d = await db.execute(
        select(func.count(ReminderLog.id)).where(
            and_(*base_filter, ReminderLog.sent_at >= thirty_days_ago)
        )
    )
    sent_30d = result_30d.scalar() or 0

    # Interaction rate last 7 days
    result_interacted = await db.execute(
        select(func.count(ReminderLog.id)).where(
            and_(
                *base_filter,
                ReminderLog.sent_at >= seven_days_ago,
                ReminderLog.was_interacted == True,
            )
        )
    )
    interacted_7d = result_interacted.scalar() or 0

    # Breakdown by type
    result_by_type = await db.execute(
        select(
            ReminderLog.reminder_type,
            func.count(ReminderLog.id),
        ).where(
            and_(*base_filter, ReminderLog.sent_at >= thirty_days_ago)
        ).group_by(ReminderLog.reminder_type)
    )
    type_counts = {row[0]: row[1] for row in result_by_type}

    return {
        "sent_last_7_days": sent_7d,
        "sent_last_30_days": sent_30d,
        "interaction_rate_7d": round(interacted_7d / max(sent_7d, 1), 2),
        "by_type": type_counts,
    }
