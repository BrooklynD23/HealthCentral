"""Audited CRUD and focused packet export for profile-scoped pinboards."""

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.documents import validate_uuid, verify_document_access
from api.export import _compute_trends, _packet_store
from core.audit import audit_and_commit, log_pinboard_event
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from core.time import utcnow
from models import CarePlanTask, Document, Observation, Pinboard, PinboardItem
from models.document_category import DocumentEntity
from modules.export import ExportModule


router = APIRouter()
ItemType = Literal["document", "observation", "care_task", "question"]


class PinboardCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Pinboard name cannot be blank")
        return value


class PinboardUpdateRequest(PinboardCreateRequest):
    pass


class PinboardResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, board: Pinboard) -> "PinboardResponse":
        return cls(
            id=board.id,
            name=board.name,
            created_at=board.created_at.isoformat(),
            updated_at=board.updated_at.isoformat(),
        )


class PinboardItemCreateRequest(BaseModel):
    item_type: ItemType
    item_id: str


class PinboardItemResponse(BaseModel):
    id: str
    pinboard_id: str
    item_type: ItemType
    item_id: str
    created_at: str

    @classmethod
    def from_model(cls, item: PinboardItem) -> "PinboardItemResponse":
        return cls(
            id=item.id,
            pinboard_id=item.pinboard_id,
            item_type=item.item_type,
            item_id=item.item_id,
            created_at=item.created_at.isoformat(),
        )


class PinboardExportRequest(BaseModel):
    reason_for_visit: Optional[str] = None
    confirm: bool = False


class PinboardExportResponse(BaseModel):
    packet_id: str
    profile_id: str
    generated_at: str
    section_titles: list[str]
    markdown: str
    redaction_count: int


async def _board_or_404(profile_db: AsyncSession, pinboard_id: str) -> Pinboard:
    validate_uuid(pinboard_id, "pinboard_id")
    result = await profile_db.execute(select(Pinboard).where(Pinboard.id == pinboard_id))
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=404, detail="Pinboard not found")
    return board


async def _validate_item_target(
    profile_db: AsyncSession, payload: PinboardItemCreateRequest, session
) -> None:
    validate_uuid(payload.item_id, "item_id")
    if payload.item_type == "document":
        result = await profile_db.execute(select(Document).where(Document.id == payload.item_id))
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        verify_document_access(document, session)
        return
    if payload.item_type == "observation":
        result = await profile_db.execute(
            select(Observation).where(
                Observation.id == payload.item_id,
                Observation.profile_id == session.profile_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Observation not found")
        return
    if payload.item_type == "care_task":
        result = await profile_db.execute(
            select(CarePlanTask).where(CarePlanTask.id == payload.item_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Care task not found")
        return

    # HC-M17 questions are derived rather than stored. A question pin keeps
    # the UUID of its verified observation/entity or accepted care task.
    for model in (Observation, CarePlanTask, DocumentEntity):
        result = await profile_db.execute(select(model).where(model.id == payload.item_id))
        source = result.scalar_one_or_none()
        if source is not None:
            if isinstance(source, Observation) and (
                source.profile_id != session.profile_id or not source.user_verified
            ):
                continue
            if isinstance(source, DocumentEntity) and source.verified_by_user is not True:
                continue
            return
    raise HTTPException(status_code=404, detail="Verified question source not found")


@router.post("/", response_model=PinboardResponse, status_code=status.HTTP_201_CREATED)
async def create_pinboard(
    payload: PinboardCreateRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    now = utcnow()
    board = Pinboard(id=str(uuid.uuid4()), name=payload.name, created_at=now, updated_at=now)
    profile_db.add(board)
    await profile_db.commit()
    await audit_and_commit(
        master_db, log_pinboard_event, event="create", profile_id=session.profile_id,
        pinboard_id=board.id,
    )
    return PinboardResponse.from_model(board)


@router.get("/", response_model=list[PinboardResponse])
async def list_pinboards(
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    result = await profile_db.execute(select(Pinboard).order_by(Pinboard.updated_at.desc()))
    boards = result.scalars().all()
    await audit_and_commit(
        master_db, log_pinboard_event, event="view", profile_id=session.profile_id,
        pinboard_id="all", details={"action": "list", "count": len(boards)},
    )
    return [PinboardResponse.from_model(board) for board in boards]


@router.patch("/{pinboard_id}", response_model=PinboardResponse)
async def rename_pinboard(
    pinboard_id: str,
    payload: PinboardUpdateRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    board = await _board_or_404(profile_db, pinboard_id)
    board.name = payload.name
    board.updated_at = utcnow()
    await profile_db.commit()
    await audit_and_commit(
        master_db, log_pinboard_event, event="update", profile_id=session.profile_id,
        pinboard_id=board.id, details={"name_changed": True},
    )
    return PinboardResponse.from_model(board)


@router.delete("/{pinboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pinboard(
    pinboard_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    board = await _board_or_404(profile_db, pinboard_id)
    await profile_db.delete(board)
    await profile_db.commit()
    await audit_and_commit(
        master_db, log_pinboard_event, event="delete", profile_id=session.profile_id,
        pinboard_id=pinboard_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{pinboard_id}/items", response_model=PinboardItemResponse,
             status_code=status.HTTP_201_CREATED)
async def add_pinboard_item(
    pinboard_id: str,
    payload: PinboardItemCreateRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    board = await _board_or_404(profile_db, pinboard_id)
    await _validate_item_target(profile_db, payload, session)
    duplicate = await profile_db.execute(
        select(PinboardItem).where(
            PinboardItem.pinboard_id == board.id,
            PinboardItem.item_type == payload.item_type,
            PinboardItem.item_id == payload.item_id,
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Item is already on this pinboard")
    item = PinboardItem(
        id=str(uuid.uuid4()), pinboard_id=board.id, item_type=payload.item_type,
        item_id=payload.item_id, created_at=utcnow(),
    )
    profile_db.add(item)
    board.updated_at = utcnow()
    try:
        await profile_db.commit()
    except IntegrityError as exc:
        await profile_db.rollback()
        raise HTTPException(
            status_code=409, detail="Item is already on this pinboard"
        ) from exc
    await audit_and_commit(
        master_db, log_pinboard_event, event="item_add", profile_id=session.profile_id,
        pinboard_id=board.id,
        details={"item_type": item.item_type, "item_id": item.item_id},
    )
    return PinboardItemResponse.from_model(item)


@router.get("/{pinboard_id}/items", response_model=list[PinboardItemResponse])
async def list_pinboard_items(
    pinboard_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    board = await _board_or_404(profile_db, pinboard_id)
    result = await profile_db.execute(
        select(PinboardItem).where(PinboardItem.pinboard_id == board.id)
        .order_by(PinboardItem.created_at.desc())
    )
    items = result.scalars().all()
    await audit_and_commit(
        master_db, log_pinboard_event, event="view", profile_id=session.profile_id,
        pinboard_id=board.id, details={"action": "list_items", "count": len(items)},
    )
    return [PinboardItemResponse.from_model(item) for item in items]


@router.delete("/{pinboard_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_pinboard_item(
    item_id: str,
    pinboard_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    board = await _board_or_404(profile_db, pinboard_id)
    validate_uuid(item_id, "item_id")
    result = await profile_db.execute(
        select(PinboardItem).where(
            PinboardItem.id == item_id, PinboardItem.pinboard_id == board.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Pinboard item not found")
    await profile_db.delete(item)
    board.updated_at = utcnow()
    await profile_db.commit()
    await audit_and_commit(
        master_db, log_pinboard_event, event="item_remove", profile_id=session.profile_id,
        pinboard_id=board.id,
        details={"item_type": item.item_type, "item_id": item.item_id},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _observation_dict(obs: Observation) -> dict:
    return {
        "id": obs.id, "analyte_canonical": obs.analyte_canonical,
        "analyte_raw": obs.analyte_raw, "value": obs.value,
        "value_text": obs.value_text, "unit": obs.unit, "ref_low": obs.ref_low,
        "ref_high": obs.ref_high, "flag": obs.flag, "is_abnormal": obs.is_abnormal,
        "user_verified": obs.user_verified, "collected_at": obs.collected_at,
    }


@router.post("/{pinboard_id}/export", response_model=PinboardExportResponse)
async def export_pinboard_packet(
    pinboard_id: str,
    payload: PinboardExportRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    if payload.confirm is not True:
        raise HTTPException(status_code=400, detail="Pinboard export requires confirm=true.")
    board = await _board_or_404(profile_db, pinboard_id)
    item_result = await profile_db.execute(
        select(PinboardItem).where(PinboardItem.pinboard_id == board.id)
    )
    items = item_result.scalars().all()
    ids_by_type = {
        item_type: [item.item_id for item in items if item.item_type == item_type]
        for item_type in ("document", "observation", "care_task", "question")
    }

    documents = []
    if ids_by_type["document"]:
        result = await profile_db.execute(
            select(Document).where(
                Document.id.in_(ids_by_type["document"]),
                Document.profile_id == session.profile_id,
            )
        )
        documents = [
            {"id": doc.id, "source": doc.source, "collection_date": doc.collection_date}
            for doc in result.scalars().all()
        ]

    observations = []
    if ids_by_type["observation"]:
        result = await profile_db.execute(
            select(Observation).where(
                Observation.id.in_(ids_by_type["observation"]),
                Observation.profile_id == session.profile_id,
            )
        )
        observations = [_observation_dict(obs) for obs in result.scalars().all()]

    tasks = []
    if ids_by_type["care_task"]:
        result = await profile_db.execute(
            select(CarePlanTask).where(
                CarePlanTask.id.in_(ids_by_type["care_task"]),
                CarePlanTask.status.in_(("open", "needs_review")),
            )
        )
        tasks = [
            {"id": task.id, "title": task.title, "status": task.status,
             "due_date": task.due_date, "source_quote": task.source_quote,
             "source_entity_id": task.source_entity_id}
            for task in result.scalars().all()
        ]

    question_observations: list[dict] = []
    question_tasks: list[dict] = []
    question_entities: list[dict] = []
    question_ids = ids_by_type["question"]
    if question_ids:
        obs_result = await profile_db.execute(
            select(Observation).where(
                Observation.id.in_(question_ids), Observation.profile_id == session.profile_id,
                Observation.user_verified.is_(True),
            )
        )
        question_observations = [_observation_dict(obs) for obs in obs_result.scalars().all()]
        task_result = await profile_db.execute(
            select(CarePlanTask).where(CarePlanTask.id.in_(question_ids))
        )
        question_tasks = [
            {"id": task.id, "title": task.title, "status": task.status,
             "due_date": task.due_date, "source_quote": task.source_quote,
             "source_entity_id": task.source_entity_id}
            for task in task_result.scalars().all()
        ]
        entity_result = await profile_db.execute(
            select(DocumentEntity).where(
                DocumentEntity.id.in_(question_ids),
                DocumentEntity.verified_by_user.is_(True),
            )
        )
        question_entities = [
            {"id": ent.id, "entity_type": ent.entity_type,
             "entity_value": ent.entity_value, "quote": ent.quote,
             "verified_by_user": ent.verified_by_user}
            for ent in entity_result.scalars().all()
        ]

    export_module = ExportModule()
    questions = export_module.generate_questions(
        question_observations, _compute_trends(question_observations),
        care_tasks=question_tasks, entities=question_entities,
    ) if question_ids else []
    packet = export_module.compose_visit_prep_packet(
        profile_id=session.profile_id,
        reason_for_visit=payload.reason_for_visit,
        observations=observations if ids_by_type["observation"] else None,
        care_tasks=tasks if ids_by_type["care_task"] else None,
        questions=questions if question_ids else None,
        selected_documents=documents if ids_by_type["document"] else None,
        packet_title="Pinboard Packet",
    )
    _packet_store[packet["packet_id"]] = packet
    await audit_and_commit(
        master_db, log_pinboard_event, event="export", profile_id=session.profile_id,
        pinboard_id=board.id,
        details={"packet_id": packet["packet_id"], "item_count": len(items),
                 "redaction_count": packet["redaction_count"]},
    )
    return PinboardExportResponse(
        packet_id=packet["packet_id"], profile_id=session.profile_id,
        generated_at=packet["generated_at"],
        section_titles=[section["title"] for section in packet["sections"]],
        markdown=packet["markdown"], redaction_count=packet["redaction_count"],
    )
