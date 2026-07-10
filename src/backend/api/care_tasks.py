"""Care-plan task API endpoints (HC-M15).

Follow-up instructions, ordered tests, and referrals extracted from visit
notes are surfaced as task *candidates* computed on read. A task is persisted
ONLY through explicit user acceptance (POST /care-tasks/accept) — there is no
auto-creation on upload. Every persisted task keeps the verbatim source quote
so the UI always shows the clinician's exact words, never app advice.

All data access goes through the per-profile encrypted database
(ProfileDbSession); every route writes an audit entry to the master DB.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.documents import validate_uuid, verify_document_access
from core.audit import audit_and_commit, log_care_task_event
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from core.time import utcnow
from models import CarePlanTask, Document
from models.care_plan_task import CARE_PLAN_TASK_STATUSES
from models.document_category import DocumentEntity
from modules.care_tasks import TASK_ENTITY_TYPES, derive_task_candidates

logger = logging.getLogger(__name__)

router = APIRouter()

_STATUS_PATTERN = "^(open|done|ignored|needs_review)$"


class CarePlanTaskResponse(BaseModel):
    """Response model for a persisted care-plan task."""

    id: str
    title: str
    due_date: Optional[str] = None
    due_date_confidence: Optional[float] = None
    status: str
    source_document_id: Optional[str] = None
    source_entity_id: Optional[str] = None
    source_quote: Optional[str] = None
    user_note: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, task: CarePlanTask) -> "CarePlanTaskResponse":
        return cls(
            id=task.id,
            title=task.title,
            due_date=task.due_date.isoformat() if task.due_date else None,
            due_date_confidence=task.due_date_confidence,
            status=task.status,
            source_document_id=task.source_document_id,
            source_entity_id=task.source_entity_id,
            source_quote=task.source_quote,
            user_note=task.user_note,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
        )


class TaskCandidateResponse(BaseModel):
    """A derived (not persisted) task candidate awaiting user acceptance."""

    title: str
    source_entity_id: Optional[str] = None
    source_document_id: Optional[str] = None
    source_quote: Optional[str] = None
    due_date: Optional[str] = None
    due_date_confidence: Optional[float] = None
    suggested_status: str

    @classmethod
    def from_candidate(cls, candidate: dict) -> "TaskCandidateResponse":
        due = candidate["due_date"]
        return cls(
            title=candidate["title"],
            source_entity_id=candidate["source_entity_id"],
            source_document_id=candidate["source_document_id"],
            source_quote=candidate["source_quote"],
            due_date=due.isoformat() if due else None,
            due_date_confidence=candidate["due_date_confidence"],
            suggested_status=candidate["suggested_status"],
        )


class AcceptTaskRequest(BaseModel):
    """Explicit user acceptance of a derived candidate.

    The server re-derives the candidate from the stored entity; the payload
    quote must match the entity's stored quote exactly.
    """

    source_entity_id: str
    source_document_id: str
    source_quote: Optional[str] = None
    user_note: Optional[str] = None


class CareTaskUpdateRequest(BaseModel):
    """Status transition and/or user-note edit for a task."""

    status: Optional[str] = Field(None, pattern=_STATUS_PATTERN)
    user_note: Optional[str] = None


async def _load_document_or_404(profile_db, document_id: str, session) -> Document:
    result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    verify_document_access(document, session)
    return document


@router.get("/", response_model=list[CarePlanTaskResponse])
async def list_care_tasks(
    session: RequireAuth,
    task_status: Optional[str] = Query(None, alias="status", description="Filter by task status"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """List persisted care-plan tasks, optionally filtered by status."""
    if task_status is not None and task_status not in CARE_PLAN_TASK_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status filter",
        )

    query = select(CarePlanTask)
    if task_status:
        query = query.where(CarePlanTask.status == task_status)
    query = query.order_by(CarePlanTask.created_at.desc())

    result = await profile_db.execute(query)
    tasks = result.scalars().all()

    await audit_and_commit(
        master_db,
        log_care_task_event,
        event="view",
        profile_id=session.profile_id,
        task_id="all",
        details={"action": "list", "count": len(tasks), "status": task_status},
    )

    return [CarePlanTaskResponse.from_model(task) for task in tasks]


@router.get("/candidates", response_model=list[TaskCandidateResponse])
async def get_care_task_candidates(
    session: RequireAuth,
    doc_id: str = Query(..., description="Document to derive candidates from"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Derive task candidates for a document (computed on read, not persisted).

    Excludes entities already linked to a persisted task and entities the
    user rejected (verified_by_user == False).
    """
    validate_uuid(doc_id, "doc_id")
    document = await _load_document_or_404(profile_db, doc_id, session)

    entity_result = await profile_db.execute(
        select(DocumentEntity).where(DocumentEntity.doc_id == doc_id)
    )
    entities = entity_result.scalars().all()

    task_result = await profile_db.execute(
        select(CarePlanTask).where(CarePlanTask.source_document_id == doc_id)
    )
    linked_entity_ids = {
        task.source_entity_id for task in task_result.scalars().all() if task.source_entity_id
    }
    excluded = linked_entity_ids | {
        ent.id for ent in entities if ent.verified_by_user is False
    }

    candidates = [
        cand
        for cand in derive_task_candidates(entities, document)
        if cand["source_entity_id"] not in excluded
    ]

    await audit_and_commit(
        master_db,
        log_care_task_event,
        event="view",
        profile_id=session.profile_id,
        task_id="candidates",
        details={"action": "candidates", "doc_id": doc_id, "count": len(candidates)},
    )

    return [TaskCandidateResponse.from_candidate(cand) for cand in candidates]


@router.post("/accept", response_model=CarePlanTaskResponse, status_code=status.HTTP_201_CREATED)
async def accept_care_task(
    payload: AcceptTaskRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Persist a task from a candidate — the ONLY way a task is created.

    The server re-derives the candidate from the stored entity and validates
    that the payload quote matches the entity's stored quote.
    """
    validate_uuid(payload.source_document_id, "source_document_id")
    validate_uuid(payload.source_entity_id, "source_entity_id")
    document = await _load_document_or_404(profile_db, payload.source_document_id, session)

    entity_result = await profile_db.execute(
        select(DocumentEntity).where(
            DocumentEntity.id == payload.source_entity_id,
            DocumentEntity.doc_id == payload.source_document_id,
        )
    )
    entity = entity_result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    if entity.entity_type not in TASK_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entity type cannot become a task",
        )
    if entity.verified_by_user is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entity was rejected by the user",
        )
    if (payload.source_quote or None) != (entity.quote or None):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quote does not match the entity's stored quote",
        )

    existing_result = await profile_db.execute(
        select(CarePlanTask).where(CarePlanTask.source_entity_id == entity.id)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A task already exists for this entity",
        )

    # Re-derive server-side (title, due date, status) — never trust a
    # client-supplied due date.
    all_entities_result = await profile_db.execute(
        select(DocumentEntity).where(DocumentEntity.doc_id == payload.source_document_id)
    )
    all_entities = all_entities_result.scalars().all()
    candidate = next(
        (
            cand
            for cand in derive_task_candidates(all_entities, document)
            if cand["source_entity_id"] == entity.id
        ),
        None,
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate could not be re-derived for this entity",
        )

    now = utcnow()
    task = CarePlanTask(
        id=str(uuid.uuid4()),
        title=candidate["title"],
        due_date=candidate["due_date"],
        due_date_confidence=candidate["due_date_confidence"],
        status=candidate["suggested_status"],
        source_document_id=document.id,
        source_entity_id=entity.id,
        source_quote=entity.quote,
        user_note=payload.user_note,
        created_at=now,
        updated_at=now,
    )
    profile_db.add(task)
    await profile_db.commit()

    await log_care_task_event(
        db=master_db,
        event="create",
        profile_id=session.profile_id,
        task_id=task.id,
        details={
            "source_document_id": document.id,
            "source_entity_id": entity.id,
            "entity_type": entity.entity_type,
            "status": task.status,
        },
    )
    await master_db.commit()

    return CarePlanTaskResponse.from_model(task)


@router.patch("/{task_id}", response_model=CarePlanTaskResponse)
async def update_care_task(
    task_id: str,
    payload: CareTaskUpdateRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Update a task's status (open|done|ignored|needs_review) or user note."""
    validate_uuid(task_id, "task_id")

    result = await profile_db.execute(select(CarePlanTask).where(CarePlanTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if payload.status is not None:
        task.status = payload.status
    if payload.user_note is not None:
        task.user_note = payload.user_note
    task.updated_at = utcnow()
    await profile_db.commit()

    await log_care_task_event(
        db=master_db,
        event="update",
        profile_id=session.profile_id,
        task_id=task.id,
        details={
            "status": payload.status,
            "user_note_changed": payload.user_note is not None,
        },
    )
    await master_db.commit()

    return CarePlanTaskResponse.from_model(task)
