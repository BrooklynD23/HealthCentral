"""Medication reconciliation API endpoint (HC-M19).

Read-only: reports where a document's medication_change entities differ from
the profile's medication list ("the note says X, your list has Y"). There is
deliberately NO accept/apply endpoint here — updating the medication list
happens only through the existing /medications endpoints, initiated by the
user in the UI. The app never changes the list on its own and never advises
taking, stopping, or changing anything.

All data access goes through the per-profile encrypted database
(ProfileDbSession); viewing a reconciliation writes an audit entry to the
master DB.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.documents import validate_uuid, verify_document_access
from core.audit import audit_and_commit, log_document_event
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from models import Document, Medication
from models.document_category import DocumentEntity
from modules.med_reconcile import derive_reconciliation_suggestions

logger = logging.getLogger(__name__)

router = APIRouter()


class MedReconcileSuggestionResponse(BaseModel):
    """One reported difference between a document and the medication list.

    ``source_quote``/``entity_value`` are the source's verbatim words;
    ``current_list_summary`` is built only from the user's own list entry
    (or the fixed phrase "not on your list"). Record-keeping only — never
    a recommendation.
    """

    suggestion_type: str
    source_entity_id: Optional[str] = None
    source_quote: Optional[str] = None
    entity_value: str
    drug_name: Optional[str] = None
    matched_medication_id: Optional[str] = None
    current_list_summary: str
    confidence: float
    reason: Optional[str] = None


@router.get("/", response_model=list[MedReconcileSuggestionResponse])
async def get_med_reconciliation(
    session: RequireAuth,
    doc_id: str = Query(..., description="Document to reconcile against"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Compare a document's medication lines with the medication list.

    Computed on read; nothing is persisted. Entities the user rejected
    (verified_by_user == False) are excluded.
    """
    validate_uuid(doc_id, "doc_id")

    doc_result = await profile_db.execute(
        select(Document).where(Document.id == doc_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    verify_document_access(document, session)

    entity_result = await profile_db.execute(
        select(DocumentEntity).where(
            DocumentEntity.doc_id == doc_id,
            DocumentEntity.entity_type == "medication_change",
        )
    )
    entities = entity_result.scalars().all()

    med_result = await profile_db.execute(
        select(Medication).where(Medication.profile_id == session.profile_id)
    )
    medications = med_result.scalars().unique().all()

    suggestions = derive_reconciliation_suggestions(entities, medications)

    await audit_and_commit(
        master_db,
        log_document_event,
        event="med_reconcile",
        profile_id=session.profile_id,
        document_id=doc_id,
        filename=document.source,
        details={"action": "view_reconciliation", "count": len(suggestions)},
    )

    return [MedReconcileSuggestionResponse(**s) for s in suggestions]
