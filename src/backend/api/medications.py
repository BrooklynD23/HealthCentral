"""
Medication management API endpoints.

Handles CRUD operations for medications, schedules, dose logging,
and adherence statistics.

Phase 2: Core Medication Management
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
    DoseTaken,
    AdherencePattern,
    ReminderLog,
)

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


def verify_medication_access(medication: Medication, session: Session) -> None:
    """Verify session has access to the medication."""
    if medication.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this medication"
        )


# Request/Response Models


class MedicationCreate(BaseModel):
    """Request to create a new medication."""
    name: str = Field(..., min_length=1, max_length=255)
    generic_name: Optional[str] = Field(None, max_length=255)
    dosage_amount: Optional[float] = Field(None, gt=0)
    dosage_unit: Optional[str] = Field(None, max_length=50)
    dosage_form: Optional[str] = Field(None, max_length=50)
    frequency: str = Field("once_daily", pattern="^(once_daily|twice_daily|three_times_daily|four_times_daily|every_other_day|weekly|as_needed|custom)$")
    instructions: Optional[str] = None
    reminder_enabled: bool = False
    started_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class MedicationUpdate(BaseModel):
    """Request to update a medication."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    generic_name: Optional[str] = Field(None, max_length=255)
    dosage_amount: Optional[float] = Field(None, gt=0)
    dosage_unit: Optional[str] = Field(None, max_length=50)
    dosage_form: Optional[str] = Field(None, max_length=50)
    frequency: Optional[str] = Field(None, pattern="^(once_daily|twice_daily|three_times_daily|four_times_daily|every_other_day|weekly|as_needed|custom)$")
    instructions: Optional[str] = None
    reminder_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    ended_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class ScheduleCreate(BaseModel):
    """Request to create a medication schedule."""
    schedule_label: str = Field(..., pattern="^(morning|midday|afternoon|evening|bedtime|custom)$")
    target_time: str = Field(..., description="Time in HH:MM format")
    reminder_offset_minutes: int = Field(15, ge=0, le=120)
    days_of_week: Optional[list[int]] = Field(None, description="ISO weekday numbers (0=Mon, 6=Sun)")
    is_active: bool = True


class ScheduleUpdate(BaseModel):
    """Request to update a schedule."""
    schedule_label: Optional[str] = Field(None, pattern="^(morning|midday|afternoon|evening|bedtime|custom)$")
    target_time: Optional[str] = Field(None, description="Time in HH:MM format")
    reminder_offset_minutes: Optional[int] = Field(None, ge=0, le=120)
    days_of_week: Optional[list[int]] = None
    is_active: Optional[bool] = None


class DoseLog(BaseModel):
    """Request to log a dose."""
    taken_at: datetime
    log_method: str = Field("manual", pattern="^(manual|notification_tap|voice|quick_log|bulk_log)$")
    dosage_amount: Optional[float] = None
    dosage_unit: Optional[str] = None
    notes: Optional[str] = None
    was_skipped: bool = False
    skip_reason: Optional[str] = Field(None, pattern="^(forgot|side_effects|ran_out|felt_unnecessary|doctor_advised|other)?$")


class ScheduleResponse(BaseModel):
    """Response for medication schedule."""
    id: str
    medication_id: str
    schedule_label: str
    target_time: str
    adaptive_window_start: Optional[str] = None
    adaptive_window_end: Optional[str] = None
    reminder_offset_minutes: int
    days_of_week: Optional[list[int]] = None
    is_active: bool
    created_at: str

    @classmethod
    def from_model(cls, schedule: MedicationSchedule) -> "ScheduleResponse":
        """Convert from ORM model."""
        days = None
        if schedule.days_of_week_json:
            try:
                days = json.loads(schedule.days_of_week_json)
            except json.JSONDecodeError:
                pass

        return cls(
            id=schedule.id,
            medication_id=schedule.medication_id,
            schedule_label=schedule.schedule_label,
            target_time=schedule.target_time.strftime("%H:%M"),
            adaptive_window_start=schedule.adaptive_window_start.strftime("%H:%M") if schedule.adaptive_window_start else None,
            adaptive_window_end=schedule.adaptive_window_end.strftime("%H:%M") if schedule.adaptive_window_end else None,
            reminder_offset_minutes=schedule.reminder_offset_minutes,
            days_of_week=days,
            is_active=schedule.is_active,
            created_at=schedule.created_at.isoformat(),
        )


class MedicationResponse(BaseModel):
    """Response for medication data."""
    id: str
    profile_id: str
    name: str
    generic_name: Optional[str] = None
    dosage_amount: Optional[float] = None
    dosage_unit: Optional[str] = None
    dosage_form: Optional[str] = None
    frequency: str
    instructions: Optional[str] = None
    is_active: bool
    reminder_enabled: bool
    started_at: str
    ended_at: Optional[str] = None
    created_at: str
    updated_at: str
    schedules: list[ScheduleResponse] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, med: Medication, include_schedules: bool = True) -> "MedicationResponse":
        """Convert from ORM model."""
        schedules = []
        if include_schedules and med.schedules:
            schedules = [ScheduleResponse.from_model(s) for s in med.schedules]

        return cls(
            id=med.id,
            profile_id=med.profile_id,
            name=med.name,
            generic_name=med.generic_name,
            dosage_amount=med.dosage_amount,
            dosage_unit=med.dosage_unit,
            dosage_form=med.dosage_form,
            frequency=med.frequency,
            instructions=med.instructions,
            is_active=med.is_active,
            reminder_enabled=med.reminder_enabled,
            started_at=med.started_at.isoformat(),
            ended_at=med.ended_at.isoformat() if med.ended_at else None,
            created_at=med.created_at.isoformat(),
            updated_at=med.updated_at.isoformat(),
            schedules=schedules,
        )


class DoseResponse(BaseModel):
    """Response for dose record."""
    id: str
    medication_id: str
    schedule_id: Optional[str] = None
    taken_at: str
    log_method: str
    dosage_amount: Optional[float] = None
    dosage_unit: Optional[str] = None
    variance_minutes: Optional[int] = None
    notes: Optional[str] = None
    was_skipped: bool
    skip_reason: Optional[str] = None
    logged_at: str

    @classmethod
    def from_model(cls, dose: DoseTaken) -> "DoseResponse":
        """Convert from ORM model."""
        return cls(
            id=dose.id,
            medication_id=dose.medication_id,
            schedule_id=dose.schedule_id,
            taken_at=dose.taken_at.isoformat(),
            log_method=dose.log_method,
            dosage_amount=dose.dosage_amount,
            dosage_unit=dose.dosage_unit,
            variance_minutes=dose.variance_minutes,
            notes=dose.notes,
            was_skipped=dose.was_skipped,
            skip_reason=dose.skip_reason,
            logged_at=dose.logged_at.isoformat(),
        )


class AdherenceStats(BaseModel):
    """Adherence statistics for a medication."""
    medication_id: str
    current_streak_days: int
    longest_streak_days: int
    last_7_days_adherence: float
    last_30_days_adherence: float
    total_doses_taken: int
    total_doses_skipped: int
    total_doses_expected: int


# Medication CRUD Endpoints


@router.post(
    "/",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_medication(
    medication: MedicationCreate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Create a new medication.

    Creates a medication record with the specified details.
    Optionally enable reminders for this medication.
    """
    med = Medication(
        id=str(uuid.uuid4()),
        profile_id=session.profile_id,
        name=medication.name,
        generic_name=medication.generic_name,
        dosage_amount=medication.dosage_amount,
        dosage_unit=medication.dosage_unit,
        dosage_form=medication.dosage_form,
        frequency=medication.frequency,
        instructions=medication.instructions,
        is_active=True,
        reminder_enabled=medication.reminder_enabled,
        metadata_json=json.dumps(medication.metadata) if medication.metadata else None,
        started_at=medication.started_at or datetime.utcnow(),
    )

    profile_db.add(med)
    await profile_db.commit()
    await profile_db.refresh(med)

    # Audit log
    await log_document_event(
        db=master_db,
        event="medication_create",
        profile_id=session.profile_id,
        document_id=med.id,
        details={"medication_name": med.name},
    )
    await master_db.commit()

    logger.info(f"Created medication {med.id}: {med.name}")
    return MedicationResponse.from_model(med)


@router.get(
    "/",
    response_model=list[MedicationResponse],
)
async def list_medications(
    session: RequireAuth,
    active_only: bool = Query(True, description="Only show active medications"),
    profile_db: ProfileDbSession = None,
):
    """
    List medications for the authenticated profile.

    Returns all medications or only active ones based on filter.
    """
    query = select(Medication).where(
        Medication.profile_id == session.profile_id
    )

    if active_only:
        query = query.where(Medication.is_active == True)

    query = query.order_by(Medication.name)

    result = await profile_db.execute(query)
    medications = result.scalars().unique().all()

    return [MedicationResponse.from_model(m) for m in medications]


@router.get(
    "/{medication_id}",
    response_model=MedicationResponse,
)
async def get_medication(
    medication_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Get a single medication by ID."""
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

    verify_medication_access(medication, session)
    return MedicationResponse.from_model(medication)


@router.patch(
    "/{medication_id}",
    response_model=MedicationResponse,
)
async def update_medication(
    medication_id: str,
    update: MedicationUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Update a medication.

    Partial update - only provided fields are changed.
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

    verify_medication_access(medication, session)

    # Apply updates
    if update.name is not None:
        medication.name = update.name
    if update.generic_name is not None:
        medication.generic_name = update.generic_name
    if update.dosage_amount is not None:
        medication.dosage_amount = update.dosage_amount
    if update.dosage_unit is not None:
        medication.dosage_unit = update.dosage_unit
    if update.dosage_form is not None:
        medication.dosage_form = update.dosage_form
    if update.frequency is not None:
        medication.frequency = update.frequency
    if update.instructions is not None:
        medication.instructions = update.instructions
    if update.reminder_enabled is not None:
        medication.reminder_enabled = update.reminder_enabled
    if update.is_active is not None:
        medication.is_active = update.is_active
    if update.ended_at is not None:
        medication.ended_at = update.ended_at
    if update.metadata is not None:
        medication.metadata_json = json.dumps(update.metadata)

    await profile_db.commit()
    await profile_db.refresh(medication)

    logger.info(f"Updated medication {medication_id}")
    return MedicationResponse.from_model(medication)


@router.delete(
    "/{medication_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_medication(
    medication_id: str,
    session: RequireAuth,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Delete (deactivate) a medication.

    By default performs a soft delete (sets is_active=False).
    Use hard_delete=True to permanently remove.
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

    verify_medication_access(medication, session)

    if hard_delete:
        await profile_db.delete(medication)
        event_type = "medication_delete"
    else:
        medication.is_active = False
        medication.ended_at = datetime.utcnow()
        event_type = "medication_deactivate"

    await profile_db.commit()

    # Audit log
    await log_document_event(
        db=master_db,
        event=event_type,
        profile_id=session.profile_id,
        document_id=medication_id,
        details={"medication_name": medication.name},
    )
    await master_db.commit()

    logger.info(f"{'Deleted' if hard_delete else 'Deactivated'} medication {medication_id}")


# Schedule Endpoints


@router.post(
    "/{medication_id}/schedules",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    medication_id: str,
    schedule: ScheduleCreate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Create a schedule for a medication.

    Defines when the medication should be taken.
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

    verify_medication_access(medication, session)

    # Parse time
    try:
        hours, minutes = map(int, schedule.target_time.split(":"))
        target_time = time(hour=hours, minute=minutes)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid time format. Use HH:MM"
        )

    sched = MedicationSchedule(
        id=str(uuid.uuid4()),
        medication_id=medication_id,
        schedule_label=schedule.schedule_label,
        target_time=target_time,
        reminder_offset_minutes=schedule.reminder_offset_minutes,
        days_of_week_json=json.dumps(schedule.days_of_week) if schedule.days_of_week else None,
        is_active=schedule.is_active,
    )

    profile_db.add(sched)
    await profile_db.commit()
    await profile_db.refresh(sched)

    logger.info(f"Created schedule {sched.id} for medication {medication_id}")
    return ScheduleResponse.from_model(sched)


@router.get(
    "/{medication_id}/schedules",
    response_model=list[ScheduleResponse],
)
async def list_schedules(
    medication_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """List all schedules for a medication."""
    validate_uuid(medication_id, "medication_id")

    # Verify access
    med_result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = med_result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    verify_medication_access(medication, session)

    result = await profile_db.execute(
        select(MedicationSchedule).where(
            MedicationSchedule.medication_id == medication_id
        ).order_by(MedicationSchedule.target_time)
    )
    schedules = result.scalars().all()

    return [ScheduleResponse.from_model(s) for s in schedules]


@router.patch(
    "/{medication_id}/schedules/{schedule_id}",
    response_model=ScheduleResponse,
)
async def update_schedule(
    medication_id: str,
    schedule_id: str,
    update: ScheduleUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Update a medication schedule."""
    validate_uuid(medication_id, "medication_id")
    validate_uuid(schedule_id, "schedule_id")

    # Verify medication access
    med_result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = med_result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    verify_medication_access(medication, session)

    # Get schedule
    sched_result = await profile_db.execute(
        select(MedicationSchedule).where(
            MedicationSchedule.id == schedule_id,
            MedicationSchedule.medication_id == medication_id,
        )
    )
    schedule = sched_result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Apply updates
    if update.schedule_label is not None:
        schedule.schedule_label = update.schedule_label
    if update.target_time is not None:
        try:
            hours, minutes = map(int, update.target_time.split(":"))
            schedule.target_time = time(hour=hours, minute=minutes)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time format. Use HH:MM"
            )
    if update.reminder_offset_minutes is not None:
        schedule.reminder_offset_minutes = update.reminder_offset_minutes
    if update.days_of_week is not None:
        schedule.days_of_week_json = json.dumps(update.days_of_week)
    if update.is_active is not None:
        schedule.is_active = update.is_active

    await profile_db.commit()
    await profile_db.refresh(schedule)

    return ScheduleResponse.from_model(schedule)


@router.delete(
    "/{medication_id}/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_schedule(
    medication_id: str,
    schedule_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Delete a medication schedule."""
    validate_uuid(medication_id, "medication_id")
    validate_uuid(schedule_id, "schedule_id")

    # Verify medication access
    med_result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = med_result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    verify_medication_access(medication, session)

    # Get and delete schedule
    sched_result = await profile_db.execute(
        select(MedicationSchedule).where(
            MedicationSchedule.id == schedule_id,
            MedicationSchedule.medication_id == medication_id,
        )
    )
    schedule = sched_result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    await profile_db.delete(schedule)
    await profile_db.commit()

    logger.info(f"Deleted schedule {schedule_id}")


# Dose Logging Endpoints


@router.post(
    "/{medication_id}/doses",
    response_model=DoseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_dose(
    medication_id: str,
    dose: DoseLog,
    session: RequireAuth,
    schedule_id: Optional[str] = Query(None, description="Schedule ID if applicable"),
    profile_db: ProfileDbSession = None,
):
    """
    Log a dose taken (or skipped).

    Records when a medication dose was taken or skipped.
    Optionally link to a specific schedule for variance tracking.
    """
    validate_uuid(medication_id, "medication_id")
    if schedule_id:
        validate_uuid(schedule_id, "schedule_id")

    # Verify medication access
    med_result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = med_result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    verify_medication_access(medication, session)

    # Calculate variance if schedule provided
    variance_minutes = None
    if schedule_id:
        sched_result = await profile_db.execute(
            select(MedicationSchedule).where(MedicationSchedule.id == schedule_id)
        )
        schedule = sched_result.scalar_one_or_none()
        if schedule:
            # Calculate minutes from midnight for comparison
            target_minutes = schedule.target_time.hour * 60 + schedule.target_time.minute
            actual_minutes = dose.taken_at.hour * 60 + dose.taken_at.minute
            variance_minutes = actual_minutes - target_minutes

    dose_record = DoseTaken(
        id=str(uuid.uuid4()),
        medication_id=medication_id,
        schedule_id=schedule_id,
        taken_at=dose.taken_at,
        log_method=dose.log_method,
        dosage_amount=dose.dosage_amount or medication.dosage_amount,
        dosage_unit=dose.dosage_unit or medication.dosage_unit,
        variance_minutes=variance_minutes,
        notes=dose.notes,
        was_skipped=dose.was_skipped,
        skip_reason=dose.skip_reason if dose.was_skipped else None,
        logged_at=datetime.utcnow(),
    )

    profile_db.add(dose_record)
    await profile_db.commit()
    await profile_db.refresh(dose_record)

    logger.info(
        f"Logged dose for {medication_id}: "
        f"{'skipped' if dose.was_skipped else 'taken'} at {dose.taken_at}"
    )
    return DoseResponse.from_model(dose_record)


@router.get(
    "/{medication_id}/doses",
    response_model=list[DoseResponse],
)
async def list_doses(
    medication_id: str,
    session: RequireAuth,
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=100),
    profile_db: ProfileDbSession = None,
):
    """List dose records for a medication."""
    validate_uuid(medication_id, "medication_id")

    # Verify medication access
    med_result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = med_result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    verify_medication_access(medication, session)

    # Build query
    query = select(DoseTaken).where(DoseTaken.medication_id == medication_id)

    if from_date:
        query = query.where(DoseTaken.taken_at >= from_date)
    if to_date:
        query = query.where(DoseTaken.taken_at <= to_date)

    query = query.order_by(DoseTaken.taken_at.desc()).limit(limit)

    result = await profile_db.execute(query)
    doses = result.scalars().all()

    return [DoseResponse.from_model(d) for d in doses]


@router.get(
    "/{medication_id}/stats",
    response_model=AdherenceStats,
)
async def get_adherence_stats(
    medication_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Get adherence statistics for a medication.

    Returns streak data, adherence rates, and totals.
    """
    validate_uuid(medication_id, "medication_id")

    # Verify medication access
    med_result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = med_result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    verify_medication_access(medication, session)

    # Get dose counts
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # Count doses in last 7 days
    result_7d = await profile_db.execute(
        select(func.count(DoseTaken.id)).where(
            DoseTaken.medication_id == medication_id,
            DoseTaken.taken_at >= seven_days_ago,
            DoseTaken.was_skipped == False,
        )
    )
    taken_7d = result_7d.scalar() or 0

    result_7d_skipped = await profile_db.execute(
        select(func.count(DoseTaken.id)).where(
            DoseTaken.medication_id == medication_id,
            DoseTaken.taken_at >= seven_days_ago,
            DoseTaken.was_skipped == True,
        )
    )
    skipped_7d = result_7d_skipped.scalar() or 0

    # Count doses in last 30 days
    result_30d = await profile_db.execute(
        select(func.count(DoseTaken.id)).where(
            DoseTaken.medication_id == medication_id,
            DoseTaken.taken_at >= thirty_days_ago,
            DoseTaken.was_skipped == False,
        )
    )
    taken_30d = result_30d.scalar() or 0

    result_30d_skipped = await profile_db.execute(
        select(func.count(DoseTaken.id)).where(
            DoseTaken.medication_id == medication_id,
            DoseTaken.taken_at >= thirty_days_ago,
            DoseTaken.was_skipped == True,
        )
    )
    skipped_30d = result_30d_skipped.scalar() or 0

    # Total counts
    result_total = await profile_db.execute(
        select(func.count(DoseTaken.id)).where(
            DoseTaken.medication_id == medication_id,
            DoseTaken.was_skipped == False,
        )
    )
    total_taken = result_total.scalar() or 0

    result_total_skipped = await profile_db.execute(
        select(func.count(DoseTaken.id)).where(
            DoseTaken.medication_id == medication_id,
            DoseTaken.was_skipped == True,
        )
    )
    total_skipped = result_total_skipped.scalar() or 0

    # Calculate expected doses (simplified - assumes once daily)
    days_since_start = (now - medication.started_at).days + 1
    expected_7d = min(7, days_since_start)
    expected_30d = min(30, days_since_start)

    # Frequency multiplier
    freq_multiplier = {
        "once_daily": 1,
        "twice_daily": 2,
        "three_times_daily": 3,
        "four_times_daily": 4,
        "every_other_day": 0.5,
        "weekly": 1/7,
        "as_needed": 0,
    }.get(medication.frequency, 1)

    expected_total = int(days_since_start * freq_multiplier)
    expected_7d = int(expected_7d * freq_multiplier)
    expected_30d = int(expected_30d * freq_multiplier)

    # Calculate adherence rates
    total_7d = taken_7d + skipped_7d
    total_30d = taken_30d + skipped_30d
    adherence_7d = taken_7d / max(total_7d, expected_7d, 1)
    adherence_30d = taken_30d / max(total_30d, expected_30d, 1)

    # Calculate streak (simplified)
    current_streak = await _calculate_current_streak(medication_id, profile_db)
    longest_streak = await _calculate_longest_streak(medication_id, profile_db)

    return AdherenceStats(
        medication_id=medication_id,
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        last_7_days_adherence=min(adherence_7d, 1.0),
        last_30_days_adherence=min(adherence_30d, 1.0),
        total_doses_taken=total_taken,
        total_doses_skipped=total_skipped,
        total_doses_expected=max(expected_total, 1),
    )


async def _calculate_current_streak(medication_id: str, db: AsyncSession) -> int:
    """Calculate current consecutive days with dose taken."""
    result = await db.execute(
        select(DoseTaken).where(
            DoseTaken.medication_id == medication_id,
            DoseTaken.was_skipped == False,
        ).order_by(DoseTaken.taken_at.desc()).limit(60)
    )
    doses = result.scalars().all()

    if not doses:
        return 0

    streak = 0
    today = datetime.utcnow().date()
    current_date = today

    # Group doses by date
    doses_by_date = {}
    for dose in doses:
        dose_date = dose.taken_at.date()
        doses_by_date[dose_date] = True

    # Count consecutive days backwards
    while current_date in doses_by_date:
        streak += 1
        current_date -= timedelta(days=1)

    return streak


async def _calculate_longest_streak(medication_id: str, db: AsyncSession) -> int:
    """Calculate longest consecutive days with dose taken."""
    result = await db.execute(
        select(DoseTaken).where(
            DoseTaken.medication_id == medication_id,
            DoseTaken.was_skipped == False,
        ).order_by(DoseTaken.taken_at.asc())
    )
    doses = result.scalars().all()

    if not doses:
        return 0

    # Get unique dates
    dates = sorted(set(dose.taken_at.date() for dose in doses))

    if not dates:
        return 0

    longest = 1
    current = 1

    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


# Pattern Learning Endpoint


class LearnPatternsResponse(BaseModel):
    """Response from pattern learning."""
    patterns_created: int
    schedules_updated: int
    time_window: Optional[dict] = None
    weekday_pattern: Optional[dict] = None
    missed_days: Optional[list[dict]] = None
    streak: Optional[dict] = None


@router.post(
    "/{medication_id}/learn-patterns",
    response_model=LearnPatternsResponse,
)
async def learn_patterns(
    medication_id: str,
    session: RequireAuth,
    schedule_id: Optional[str] = Query(None, description="Specific schedule to learn"),
    profile_db: ProfileDbSession = None,
):
    """
    Trigger pattern learning for a medication.

    Analyzes dose history to learn behavioral patterns:
    - Time window: When user typically takes medication
    - Weekday vs weekend: Different patterns for different day types
    - Missed days: Days of week with higher miss rates
    - Streaks: Consecutive adherence tracking

    Patterns are used to adjust reminder timing adaptively.
    """
    from modules.adherence_patterns import get_pattern_learner

    validate_uuid(medication_id, "medication_id")
    if schedule_id:
        validate_uuid(schedule_id, "schedule_id")

    # Verify medication access
    med_result = await profile_db.execute(
        select(Medication).where(Medication.id == medication_id)
    )
    medication = med_result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    verify_medication_access(medication, session)

    # Learn patterns
    learner = get_pattern_learner()
    patterns = await learner.learn_all_patterns(
        medication_id=medication_id,
        schedule_id=schedule_id,
        db=profile_db,
    )

    # Save patterns to database
    pattern_ids = await learner.save_patterns(
        medication_id=medication_id,
        schedule_id=schedule_id,
        patterns=patterns,
        db=profile_db,
    )

    # Update adaptive windows
    schedules_updated = await learner.update_adaptive_windows(
        medication_id=medication_id,
        db=profile_db,
    )

    # Format response
    response = LearnPatternsResponse(
        patterns_created=len(pattern_ids),
        schedules_updated=schedules_updated,
    )

    if "time_window" in patterns:
        tw = patterns["time_window"]
        response.time_window = {
            "avg_time": f"{tw.avg_minutes // 60:02d}:{tw.avg_minutes % 60:02d}",
            "window_start": tw.window_start.strftime("%H:%M"),
            "window_end": tw.window_end.strftime("%H:%M"),
            "confidence": round(tw.confidence, 2),
            "sample_size": tw.sample_size,
        }

    if "weekday_pattern" in patterns:
        wp = patterns["weekday_pattern"]
        response.weekday_pattern = {
            "weekday_avg": f"{wp.weekday_avg_minutes // 60:02d}:{wp.weekday_avg_minutes % 60:02d}",
            "weekend_avg": f"{wp.weekend_avg_minutes // 60:02d}:{wp.weekend_avg_minutes % 60:02d}",
            "is_significantly_different": wp.is_significantly_different,
            "confidence": round(wp.confidence, 2),
        }

    if "missed_days" in patterns:
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        response.missed_days = [
            {
                "day": day_names[md.day_of_week],
                "miss_rate": round(md.miss_rate, 2),
                "confidence": round(md.confidence, 2),
            }
            for md in patterns["missed_days"]
        ]

    if "streak" in patterns:
        streak = patterns["streak"]
        response.streak = {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "total_adherent_days": streak.total_adherent_days,
        }

    logger.info(
        f"Learned patterns for medication {medication_id}: "
        f"{len(pattern_ids)} patterns, {schedules_updated} schedules updated"
    )

    return response
