"""
Document management API endpoints.

Handles document import, listing, and viewing.
All endpoints require authentication.

Phase 3: Documents are now stored in per-profile encrypted databases.
Uses ProfileDbSession for database access instead of master database.
"""

import json
import logging
import re
import threading
import time
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from typing import Literal, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings, user_ocr_preference_enabled, compute_ocr_effective
from core.audit import log_document_event, audit_and_commit
from core.auth import RequireAuth, Session, ProfileDbSession
from core.document_crypto import get_decrypted_document, get_profile_encryption_key
from core.time import utcnow
from models import (
    CarePlanTask,
    Chunk,
    Document,
    Embedding,
    Observation,
    PinboardItem,
    UserModelSettings,
)
from modules.extract import ExtractModule
from modules.normalize import NormalizeModule
from modules.chunking import ChunkingModule
from modules.embeddings import EmbeddingsModule
from modules.document_classifier import classify_document
from modules.extract_imaging import extract_imaging_entities
from modules.extract_pathology import extract_pathology_entities
from modules.extract_visit_notes import extract_visit_note_entities, llm_assist_visit_entities
from modules.highlights import Highlight, derive_highlights
from modules.import_structured import parse_fhir_bundle, parse_lab_csv
from models.document_category import DocumentCategory, DocumentEntity

# Doc types handled by the structured-import pipeline (HC-M23) instead of the
# OCR/regex extraction + rule-based classification pipeline.
_STRUCTURED_IMPORT_DOC_TYPES = ("lab_csv", "fhir_bundle")

logger = logging.getLogger(__name__)

# Shared normalizer instance
_normalizer = NormalizeModule()


async def _prune_document_pin_targets(
    profile_db: AsyncSession,
    document_id: str,
    *,
    include_document: bool,
) -> None:
    """Delete pins for targets removed with a document in the same transaction."""
    observation_ids = select(Observation.id).where(Observation.doc_id == document_id)
    entity_ids = select(DocumentEntity.id).where(DocumentEntity.doc_id == document_id)
    conditions = [
        and_(
            PinboardItem.item_type.in_(("observation", "question")),
            PinboardItem.item_id.in_(observation_ids),
        ),
        and_(
            PinboardItem.item_type == "question",
            PinboardItem.item_id.in_(entity_ids),
        ),
    ]
    if include_document:
        conditions.append(
            and_(
                PinboardItem.item_type == "document",
                PinboardItem.item_id == document_id,
            )
        )
    await profile_db.execute(delete(PinboardItem).where(or_(*conditions)))

# ---------------------------------------------------------------------------
# Page image rendering cache (F-005)
# ---------------------------------------------------------------------------

_PAGE_IMAGE_CACHE_TTL_SECONDS = 300
_PAGE_IMAGE_CACHE_MAX_ENTRIES = 32
_PAGE_IMAGE_CACHE_MAX_ITEM_BYTES = 2_000_000  # avoid unbounded memory growth

_PageImageCacheKey = tuple[str, str, int, int]  # (profile_id, document_id, page_number, resolution)
_page_image_cache: "OrderedDict[_PageImageCacheKey, tuple[float, bytes]]" = OrderedDict()
_page_image_cache_lock = threading.Lock()


def _page_image_cache_get(key: _PageImageCacheKey) -> bytes | None:
    now = time.time()
    with _page_image_cache_lock:
        expired = [k for k, (expires_at, _) in _page_image_cache.items() if expires_at <= now]
        for k in expired:
            _page_image_cache.pop(k, None)

        entry = _page_image_cache.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= now:
            _page_image_cache.pop(key, None)
            return None
        _page_image_cache.move_to_end(key)
        return value


def _page_image_cache_set(key: _PageImageCacheKey, value: bytes) -> None:
    if len(value) > _PAGE_IMAGE_CACHE_MAX_ITEM_BYTES:
        return
    now = time.time()
    with _page_image_cache_lock:
        expired = [k for k, (expires_at, _) in _page_image_cache.items() if expires_at <= now]
        for k in expired:
            _page_image_cache.pop(k, None)

        _page_image_cache[key] = (now + _PAGE_IMAGE_CACHE_TTL_SECONDS, value)
        _page_image_cache.move_to_end(key)
        while len(_page_image_cache) > _PAGE_IMAGE_CACHE_MAX_ENTRIES:
            _page_image_cache.popitem(last=False)


def _parse_date_string(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a date string from extraction into a datetime object.

    Accepts all formats produced by ExtractModule._extract_dates(), including
    the canonical ISO-8601 output (YYYY-MM-DD) as well as legacy raw strings
    that may still be present in re-processed documents.

    Plausibility check: rejects dates outside 1950..today+1 day.
    """
    if not date_str:
        return None

    from datetime import date as _date, timedelta
    _MIN_DATE = _date(1950, 1, 1)

    formats = [
        # ISO 8601 (canonical output of _extract_dates)
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        # US slash formats
        "%m/%d/%Y",
        "%m/%d/%y",
        # US dash formats
        "%m-%d-%Y",
        "%m-%d-%y",
        # Named-month formats
        "%B %d, %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%b %d %Y",
        # European DD-Mon-YYYY
        "%d-%b-%Y",
    ]

    raw = date_str.strip()
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt)
            # Plausibility guard
            if _MIN_DATE <= parsed.date() <= _date.today() + timedelta(days=1):
                return parsed
        except ValueError:
            continue
    return None


# UUID validation pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def validate_uuid(value: str, field_name: str = "ID") -> str:
    """Validate that a string is a valid UUID format to prevent path traversal."""
    if not UUID_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format"
        )
    return value


def verify_document_access(document: Document, session: Session) -> None:
    """
    Verify that the session has access to the document.

    Args:
        document: The document to check access for
        session: The authenticated session

    Raises:
        HTTPException: 403 if access is denied
    """
    if document.profile_id != session.profile_id:
        logger.warning(
            f"Document access denied: session profile {session.profile_id} "
            f"attempted to access document {document.id} belonging to {document.profile_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this document"
        )


router = APIRouter()


class DocumentResponse(BaseModel):
    """Response model for document data."""
    id: str
    profile_id: str
    doc_type: str
    source: Optional[str] = None
    status: str
    page_count: Optional[int] = None
    collection_date: Optional[str] = None
    imported_at: str
    parsed_at: Optional[str] = None
    verified_at: Optional[str] = None
    extraction_confidence: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(
        cls,
        doc: Document,
        extraction_confidence: Optional[float] = None,
    ) -> "DocumentResponse":
        return cls(
            id=doc.id,
            profile_id=doc.profile_id,
            doc_type=doc.doc_type,
            source=doc.source,
            status=doc.status,
            page_count=doc.page_count,
            collection_date=doc.collection_date.isoformat() if doc.collection_date else None,
            imported_at=doc.imported_at.isoformat(),
            parsed_at=doc.parsed_at.isoformat() if doc.parsed_at else None,
            verified_at=doc.verified_at.isoformat() if doc.verified_at else None,
            extraction_confidence=extraction_confidence,
        )


class DuplicateWarning(BaseModel):
    """Non-blocking notice that an import resembles an existing document."""

    match_type: Literal["content_hash", "same_date"]
    document_id: str
    title: Optional[str] = None


class ImportSummary(BaseModel):
    """Summary of a structured import (CSV/FHIR) for the client (HC-M23)."""

    source_kind: Literal["lab_csv", "fhir_bundle"]
    observations_imported: int
    entities_imported: int
    skipped: list[dict] = Field(default_factory=list)


class DocumentImportResponse(BaseModel):
    """Response model for document import."""
    document: DocumentResponse
    observations_extracted: int
    needs_verification: bool
    duplicate_warning: Optional[DuplicateWarning] = None
    # Only set for CSV/FHIR structured imports (HC-M23); optional so
    # existing PDF/image import clients are unaffected.
    import_summary: Optional[ImportSummary] = None


class DocumentVerifyResponse(BaseModel):
    """Response model for document-level verification."""
    document: DocumentResponse
    verified_count: int


async def _document_extraction_confidences(
    profile_db: AsyncSession,
    profile_id: str,
    document_ids: list[str],
) -> dict[str, float]:
    """Return each document's lowest stored observation/entity confidence."""
    if not document_ids:
        return {}

    confidences: dict[str, list[float]] = {}
    observation_rows = (
        await profile_db.execute(
            select(Observation.doc_id, Observation.extraction_confidence).where(
                Observation.profile_id == profile_id,
                Observation.doc_id.in_(document_ids),
                Observation.extraction_confidence.is_not(None),
            )
        )
    ).all()
    entity_rows = (
        await profile_db.execute(
            select(DocumentEntity.doc_id, DocumentEntity.confidence)
            .join(Document, Document.id == DocumentEntity.doc_id)
            .where(
                Document.profile_id == profile_id,
                DocumentEntity.doc_id.in_(document_ids),
                # Rejected extractions no longer count toward the displayed
                # confidence — the user has already resolved them.
                DocumentEntity.verified_by_user.is_not(False),
            )
        )
    ).all()

    for doc_id, confidence in [*observation_rows, *entity_rows]:
        if confidence is not None:
            confidences.setdefault(doc_id, []).append(confidence)
    return {doc_id: min(values) for doc_id, values in confidences.items()}


async def _find_duplicate_warning(
    profile_db: AsyncSession,
    profile_id: str,
    *,
    content_hash: str,
    collection_date: Optional[datetime],
    exclude_document_id: Optional[str] = None,
) -> Optional[DuplicateWarning]:
    """Find a profile-local duplicate signal without ever blocking import."""
    try:
        hash_query = select(Document).where(
            Document.profile_id == profile_id,
            Document.content_hash == content_hash,
        )
        if exclude_document_id is not None:
            hash_query = hash_query.where(Document.id != exclude_document_id)
        hash_query = hash_query.order_by(Document.imported_at.desc()).limit(1)
        hash_match = (await profile_db.execute(hash_query)).scalar_one_or_none()
        if hash_match is not None and hash_match.profile_id == profile_id:
            return DuplicateWarning(
                match_type="content_hash",
                document_id=hash_match.id,
                title=hash_match.source,
            )

        if collection_date is None:
            return None

        day_start = datetime.combine(collection_date.date(), datetime.min.time())
        day_end = day_start + timedelta(days=1)
        date_query = select(Document).where(
            Document.profile_id == profile_id,
            Document.collection_date >= day_start,
            Document.collection_date < day_end,
        )
        if exclude_document_id is not None:
            date_query = date_query.where(Document.id != exclude_document_id)
        date_query = date_query.order_by(Document.imported_at.desc()).limit(1)
        date_match = (await profile_db.execute(date_query)).scalar_one_or_none()
        if date_match is not None and date_match.profile_id == profile_id:
            return DuplicateWarning(
                match_type="same_date",
                document_id=date_match.id,
                title=date_match.source,
            )
    except Exception as exc:
        logger.warning("Duplicate warning check failed; import will continue: %s", exc)
    return None


def _split_extracted_text_pages(extracted_text: Optional[str]) -> list[str]:
    """Split extraction text into page-like segments."""
    if not extracted_text:
        return []
    return [p for p in extracted_text.split("\f") if p and p.strip()]


class PageResponse(BaseModel):
    """Response model for document page content."""
    page_number: int
    text: str
    has_tables: bool


@router.post(
    "/import",
    response_model=DocumentImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_document(
    session: RequireAuth,
    file: UploadFile = File(...),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Import a document (PDF or image) into the authenticated profile.

    Phase 3: Document metadata stored in per-profile encrypted database.

    Process:
    1. Validate file type and size
    2. Compute content hash for deduplication
    3. Encrypt and store document
    4. Extract text and observations
    5. Create audit log entry (in master db)

    Returns extracted observations count and verification status.
    """
    profile_id = session.profile_id

    # Import using ingest module with encryption
    from modules import IngestModule

    vault_path = Path(settings.app_data_path) / "vaults" / profile_id
    encryption_key = get_profile_encryption_key(profile_id)
    if not encryption_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile vault not available - please log in again"
        )
    ingest = IngestModule(vault_path, encryption_key=encryption_key)

    try:
        import_result = await ingest.import_document(
            file=file.file,
            filename=file.filename or "unknown",
            profile_id=profile_id,
            source=file.filename,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    duplicate_warning = await _find_duplicate_warning(
        profile_db,
        profile_id,
        content_hash=import_result.content_hash,
        collection_date=None,
    )

    # Create document record in per-profile encrypted database
    document = Document(
        id=import_result.document_id,
        profile_id=profile_id,
        path_hash=import_result.path_hash,
        content_hash=import_result.content_hash,
        doc_type=import_result.doc_type,
        source=file.filename,
        status="pending",
        page_count=import_result.page_count,
        metadata_json=json.dumps(import_result.metadata),
        imported_at=utcnow(),
    )

    profile_db.add(document)
    await profile_db.commit()

    # Trigger extraction pipeline
    observations_extracted = 0
    needs_verification = True
    extracted_text: Optional[str] = None
    import_summary: Optional[ImportSummary] = None

    if import_result.doc_type in _STRUCTURED_IMPORT_DOC_TYPES:
        # CSV/FHIR structured import (HC-M23): parse + persist directly,
        # skipping OCR/regex extraction and rule-based classification —
        # there is no document text to run either over.
        structured_outcome = await _run_structured_import_pipeline(
            profile_db=profile_db,
            profile_id=profile_id,
            document=document,
        )
        observations_extracted = structured_outcome["observations_extracted"]
        needs_verification = structured_outcome["needs_verification"]
        import_summary = structured_outcome["import_summary"]
    else:
        extraction_outcome = await _run_extraction_pipeline(
            profile_db=profile_db,
            profile_id=profile_id,
            document=document,
            refresh_existing=False,
        )
        if extraction_outcome is not None:
            observations_extracted = extraction_outcome["observations_extracted"]
            needs_verification = extraction_outcome["needs_verification"]
            extracted_text = extraction_outcome.get("extracted_text")

        # Classify document and extract entities (runs for all doc types)
        await _classify_and_extract_entities(
            profile_db=profile_db,
            profile_id=profile_id,
            doc_id=import_result.document_id,
            doc_type=import_result.doc_type,
            pre_extracted_text=extracted_text,
        )

    if duplicate_warning is None:
        duplicate_warning = await _find_duplicate_warning(
            profile_db,
            profile_id,
            content_hash=import_result.content_hash,
            collection_date=document.collection_date,
            exclude_document_id=document.id,
        )

    confidence_by_doc = await _document_extraction_confidences(
        profile_db,
        profile_id,
        [document.id],
    )

    # Create audit log in master database
    audit_details = {
        "doc_type": import_result.doc_type,
        "encrypted": import_result.encrypted,
        "observations_extracted": observations_extracted,
        "duplicate_warning": duplicate_warning.match_type if duplicate_warning else None,
    }
    if import_summary is not None:
        audit_details.update({
            "source_kind": import_summary.source_kind,
            "observations_imported": import_summary.observations_imported,
            "entities_imported": import_summary.entities_imported,
            "skipped_count": len(import_summary.skipped),
        })
    await log_document_event(
        db=master_db,
        event="import",
        profile_id=profile_id,
        document_id=import_result.document_id,
        filename=file.filename,
        details=audit_details,
    )
    await master_db.commit()

    return DocumentImportResponse(
        document=DocumentResponse.from_model(
            document,
            confidence_by_doc.get(document.id),
        ),
        observations_extracted=observations_extracted,
        needs_verification=needs_verification,
        duplicate_warning=duplicate_warning,
        import_summary=import_summary,
    )



async def _run_extraction_pipeline(
    profile_db: AsyncSession,
    profile_id: str,
    document: Document,
    *,
    refresh_existing: bool,
) -> Optional[dict]:
    """Run lab extraction for a document and persist observations/chunks."""
    if document.doc_type not in ("lab_pdf", "lab_pdf_scanned", "lab_image"):
        return None

    user_settings_row = (
        await profile_db.execute(
            select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
        )
    ).scalar_one_or_none()
    user_pref = user_ocr_preference_enabled(user_settings_row)
    ocr_effective, _ = compute_ocr_effective(user_pref)

    if document.doc_type in ("lab_pdf_scanned", "lab_image") and not ocr_effective:
        document.status = "pending_ocr"
        document.parsed_at = None
        document.verified_at = None
        await profile_db.commit()
        return {
            "observations_extracted": 0,
            "needs_verification": True,
            "extracted_text": None,
        }

    try:
        decrypted_doc = get_decrypted_document(profile_id, document.id)
        extract_module = ExtractModule()
        if document.doc_type == "lab_pdf":
            extraction_result = await extract_module.extract_from_pdf(decrypted_doc, document.id)
        elif document.doc_type == "lab_pdf_scanned":
            extraction_result = await extract_module.extract_from_scanned_pdf(
                decrypted_doc,
                document.id,
                effective_ocr=ocr_effective,
            )
        else:
            extraction_result = await extract_module.extract_from_image(
                decrypted_doc,
                document.id,
                effective_ocr=ocr_effective,
            )

        if extraction_result.ocr_unavailable:
            document.status = "pending_ocr"
            document.parsed_at = None
            document.verified_at = None
            await profile_db.commit()
            return {
                "observations_extracted": 0,
                "needs_verification": True,
                "extracted_text": extraction_result.extracted_text,
            }

        if refresh_existing:
            await profile_db.execute(
                delete(Observation).where(Observation.doc_id == document.id)
            )

        import uuid

        for extracted_obs in extraction_result.observations:
            normalized = _normalizer.normalize_analyte(extracted_obs.analyte_raw)
            observation = Observation(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                doc_id=document.id,
                analyte_canonical=normalized.canonical_name,
                analyte_raw=extracted_obs.analyte_raw,
                value=extracted_obs.value,
                value_text=extracted_obs.value_text,
                unit=extracted_obs.unit,
                ref_low=extracted_obs.ref_low,
                ref_high=extracted_obs.ref_high,
                ref_range_text=extracted_obs.ref_range_text,
                flag=extracted_obs.flag,
                is_abnormal=extracted_obs.flag is not None,
                extraction_confidence=extracted_obs.confidence,
                source_page=extracted_obs.provenance.page if extracted_obs.provenance else None,
                source_bbox_json=json.dumps(list(extracted_obs.provenance.bbox))
                if extracted_obs.provenance and extracted_obs.provenance.bbox
                else None,
                collected_at=_parse_date_string(extracted_obs.collected_at),
                user_verified=False,
            )
            profile_db.add(observation)

        if extraction_result.collection_dates:
            parsed_dates = [_parse_date_string(d) for d in extraction_result.collection_dates]
            valid_dates = [d for d in parsed_dates if d is not None]
            document.collection_date = min(valid_dates) if valid_dates else None
        else:
            document.collection_date = None

        observations_extracted = len(extraction_result.observations)
        needs_verification = _compute_needs_verification(extraction_result.observations)
        document.status = "parsed"
        document.parsed_at = utcnow()
        document.verified_at = None

        try:
            chunks_created = await _create_chunks_and_embeddings(
                profile_db=profile_db,
                profile_id=profile_id,
                doc_id=document.id,
                extracted_text=extraction_result.extracted_text,
                refresh_existing=refresh_existing,
            )
            logger.info(
                f"Created {chunks_created} chunks with embeddings for document {document.id}"
            )
        except Exception as chunk_error:
            logger.warning(f"Chunking failed for document {document.id}: {chunk_error}")

        await profile_db.commit()
        logger.info(
            f"Extracted {observations_extracted} observations from document {document.id}"
        )
        return {
            "observations_extracted": observations_extracted,
            "needs_verification": needs_verification,
            "extracted_text": extraction_result.extracted_text,
        }
    except Exception as e:
        logger.error(f"Extraction failed for document {document.id}: {e}")
        document.status = "extraction_failed"
        document.parsed_at = None
        document.verified_at = None
        await profile_db.commit()
        return {
            "observations_extracted": 0,
            "needs_verification": True,
            "extracted_text": None,
        }


async def _run_structured_import_pipeline(
    profile_db: AsyncSession,
    profile_id: str,
    document: Document,
) -> dict:
    """Parse a lab_csv/fhir_bundle document and persist observations/entities.

    HC-M23: replaces the OCR/regex extraction pipeline AND rule-based
    classification (`_run_extraction_pipeline` + `_classify_and_extract_entities`)
    for structured imports — parsing is pure stdlib csv/json
    (`modules/import_structured.py`), so there is no text to OCR or classify.
    Persisted fields mirror `_run_extraction_pipeline`'s shape exactly:
    `user_verified=False` always, the undated rule (no dated observations ->
    `document.collection_date = None`), and `extraction_confidence` from the
    parser (flat 0.6 — imported facts are not source-graded the way OCR
    spans are).
    """
    import uuid

    decrypted_doc = get_decrypted_document(profile_id, document.id)
    raw_bytes = decrypted_doc.read()
    text = raw_bytes.decode("utf-8", errors="replace")

    if document.doc_type == "lab_csv":
        result = parse_lab_csv(text)
    else:
        # JSON is already known-good ("resourceType": "Bundle") by the time
        # a Document row exists — IngestModule.detect_doc_type rejected
        # anything else with a 400 before we got here.
        result = parse_fhir_bundle(text)

    for obs_data in result.observations:
        normalized = _normalizer.normalize_analyte(obs_data["analyte_raw"])
        observation = Observation(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            doc_id=document.id,
            analyte_canonical=normalized.canonical_name,
            analyte_raw=obs_data["analyte_raw"],
            value=obs_data.get("value"),
            value_text=obs_data.get("value_text"),
            unit=obs_data.get("unit"),
            ref_low=obs_data.get("ref_low"),
            ref_high=obs_data.get("ref_high"),
            ref_range_text=obs_data.get("ref_range_text"),
            flag=obs_data.get("flag"),
            is_abnormal=obs_data.get("flag") is not None,
            extraction_confidence=obs_data.get("confidence"),
            collected_at=_parse_date_string(obs_data.get("collected_at")),
            user_verified=False,
        )
        profile_db.add(observation)

    for ent_data in result.entities:
        entity_record = DocumentEntity(
            id=str(uuid.uuid4()),
            doc_id=document.id,
            category=ent_data["category"],
            entity_type=ent_data["entity_type"],
            entity_value=ent_data["entity_value"],
            confidence=ent_data.get("confidence"),
            quote=ent_data.get("quote"),
            verified_by_user=None,
            extraction_version="import-v1",
        )
        profile_db.add(entity_record)

    # DocumentCategory is one row per document (get_document_category uses
    # scalar_one_or_none(), which raises on >1 row). Only the four existing
    # category values are valid: prefer "lab" when any observations were
    # produced, else "visit_notes" when entities exist, else no category.
    if result.observations:
        category = "lab"
    elif result.entities:
        category = "visit_notes"
    else:
        category = None

    if category:
        profile_db.add(DocumentCategory(
            id=str(uuid.uuid4()),
            doc_id=document.id,
            category=category,
            confidence=1.0,
            classified_by="import",
        ))

    # Undated rule, mirroring _run_extraction_pipeline (:619-624): never
    # invent a date. document.collection_date is the earliest dated
    # observation, or None if none were dated.
    parsed_dates = [
        _parse_date_string(o["collected_at"])
        for o in result.observations
        if o.get("collected_at")
    ]
    valid_dates = [d for d in parsed_dates if d is not None]
    document.collection_date = min(valid_dates) if valid_dates else None

    document.status = "parsed"
    document.parsed_at = utcnow()
    document.verified_at = None

    await profile_db.commit()

    observations_extracted = len(result.observations)
    return {
        "observations_extracted": observations_extracted,
        # Imported data is always unverified -> always needs review.
        "needs_verification": True,
        "extracted_text": None,
        "import_summary": ImportSummary(
            source_kind=result.source_kind,
            observations_imported=observations_extracted,
            entities_imported=len(result.entities),
            skipped=result.skipped,
        ),
    }


async def _create_chunks_and_embeddings(
    profile_db,
    profile_id: str,
    doc_id: str,
    extracted_text: Optional[str] = None,
    refresh_existing: bool = False,
) -> int:
    """
    Sprint 6: Create text chunks and embeddings for RAG.

    Extracts text from PDF, chunks it, generates embeddings, and persists to DB.

    Args:
        profile_db: Profile database session
        profile_id: Profile ID (for document decryption)
        doc_id: Document ID

    Returns:
        Number of chunks created
    """
    import pdfplumber

    chunker = ChunkingModule()
    embedder = EmbeddingsModule()

    pages_text = _split_extracted_text_pages(extracted_text)
    if not pages_text:
        decrypted_doc = get_decrypted_document(profile_id, doc_id)
        with pdfplumber.open(decrypted_doc) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)

    # Chunk across all pages
    all_chunks = chunker.chunk_pdf_pages(doc_id=doc_id, pages=pages_text)

    if not all_chunks:
        return 0

    if refresh_existing:
        await profile_db.execute(delete(Chunk).where(Chunk.doc_id == doc_id))

    # Generate embeddings
    embeddings = embedder.embed_chunks(all_chunks)

    # Persist chunks and embeddings
    for chunk_data, emb_data in zip(all_chunks, embeddings):
        chunk = Chunk(
            id=chunk_data["chunk_id"],
            doc_id=doc_id,
            chunk_index=chunk_data["chunk_index"],
            text=chunk_data["text"],
            page_number=chunk_data.get("page_number"),
            start_char=chunk_data.get("start_char"),
            end_char=chunk_data.get("end_char"),
            token_count=chunk_data.get("token_count"),
            chunk_type=chunk_data.get("chunk_type", "text"),
        )
        profile_db.add(chunk)

        embedding = Embedding(
            chunk_id=chunk_data["chunk_id"],
            model_name=emb_data["model_name"],
            vector_blob=embedder.vector_to_blob(emb_data["vector"]),
            dimensions=emb_data["dimensions"],
        )
        profile_db.add(embedding)

    await profile_db.commit()

    return len(all_chunks)


def _compute_needs_verification(observations: list) -> bool:
    """
    Determine if observations need user verification.

    Returns True if:
    - Any observation has low confidence (< 0.8)
    - Any observation is flagged as abnormal
    - No observations were extracted
    """
    if not observations:
        return True

    for obs in observations:
        if obs.confidence < 0.8:
            return True
        if obs.flag:
            return True

    return False


_CATEGORY_EXTRACTORS = {
    "imaging": extract_imaging_entities,
    "pathology": extract_pathology_entities,
    "visit_notes": extract_visit_note_entities,
}


async def _classify_and_extract_entities(
    profile_db: AsyncSession,
    profile_id: str,
    doc_id: str,
    doc_type: str,
    pre_extracted_text: Optional[str] = None,
    llm_assist: bool = False,
) -> None:
    """Classify a document and persist category + extracted entities.

    Extracts text from the decrypted document, runs the rule-based classifier,
    and if a category is found, runs the appropriate entity extractor. When
    *llm_assist* is explicitly enabled (default OFF), visit notes also get a
    hard-validated LLM proposal pass on top of the rule-based entities.
    Fully non-fatal: every stage (text extraction, classification, entity
    extraction, DB persistence) is wrapped so failures never propagate to
    the caller.
    """
    import uuid as _uuid

    # --- Stage 1: text extraction ---
    try:
        text = pre_extracted_text or _get_document_text(profile_id, doc_id, doc_type)
    except Exception as e:
        logger.warning(f"Cannot extract text for classification of {doc_id}: {e}")
        return

    if not text or not text.strip():
        return

    # --- Stage 2: classification ---
    try:
        result = classify_document(text)
    except Exception as e:
        logger.warning(f"Classification failed for {doc_id}: {e}")
        return

    if result.category == "unknown":
        return

    # --- Stage 3: entity extraction ---
    entities: list[dict] = []
    extractor = _CATEGORY_EXTRACTORS.get(result.category)
    if extractor:
        try:
            entities = extractor(text)
        except Exception as e:
            logger.warning(
                f"Entity extraction failed for {doc_id} "
                f"(category={result.category}): {e}"
            )
            # Continue — we can still persist the category without entities

    if llm_assist and result.category == "visit_notes":
        try:
            entities.extend(await llm_assist_visit_entities(text, entities))
        except Exception as e:
            logger.warning(f"LLM-assist entity pass failed for {doc_id}: {e}")

    # --- Stage 4: DB persistence ---
    try:
        category_record = DocumentCategory(
            id=str(_uuid.uuid4()),
            doc_id=doc_id,
            category=result.category,
            confidence=result.confidence,
            classified_by=result.classified_by,
        )
        profile_db.add(category_record)

        for ent in entities:
            entity_record = DocumentEntity(
                id=str(_uuid.uuid4()),
                doc_id=doc_id,
                category=result.category,
                entity_type=ent["entity_type"],
                entity_value=ent["entity_value"],
                confidence=ent["confidence"],
                source_page=ent.get("source_page"),
                char_start=ent.get("char_start"),
                char_end=ent.get("char_end"),
                quote=ent.get("quote"),
                extraction_version=ent.get("extraction_version"),
            )
            profile_db.add(entity_record)

        await profile_db.commit()
        logger.info(
            f"Classified document {doc_id} as {result.category} "
            f"(confidence={result.confidence})"
        )
    except Exception as e:
        logger.warning(
            f"Failed to persist classification for {doc_id} "
            f"(category={result.category}): {e}"
        )
        try:
            await profile_db.rollback()
        except Exception as rb_err:
            logger.warning(f"Rollback after classification failure for {doc_id}: {rb_err}")


def _get_document_text(profile_id: str, doc_id: str, doc_type: str) -> str:
    """Extract plain text from a document for classification.

    Used as a fallback when pre_extracted_text is not available.
    For text-based PDFs, uses pdfplumber. For scanned/image docs,
    text should be supplied via pre_extracted_text from the extraction
    pipeline to avoid duplicate OCR.

    Returns empty string on failure.
    """
    # Default: text-based PDF extraction via pdfplumber
    try:
        import pdfplumber

        decrypted_doc = get_decrypted_document(profile_id, doc_id)
        with pdfplumber.open(decrypted_doc) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
            return "\f".join(pages_text)
    except Exception:
        return ""



@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    session: RequireAuth,
    doc_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    List documents for the authenticated profile.

    Phase 3: Queries per-profile encrypted database.
    Supports filtering by status and document type.
    """
    profile_id = session.profile_id

    # Build query - documents are in per-profile database
    query = select(Document).where(Document.profile_id == profile_id)

    if doc_status:
        query = query.where(Document.status == doc_status)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)

    query = query.order_by(Document.imported_at.desc())

    result = await profile_db.execute(query)
    documents = result.scalars().all()
    confidence_by_doc = await _document_extraction_confidences(
        profile_db,
        profile_id,
        [doc.id for doc in documents],
    )

    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=profile_id,
        document_id="all",
        details={
            "action": "list",
            "count": len(documents),
            "status": doc_status,
            "doc_type": doc_type,
        },
    )

    return [
        DocumentResponse.from_model(doc, confidence_by_doc.get(doc.id))
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Get document details from per-profile encrypted database."""
    # Validate document_id format (path traversal protection)
    validate_uuid(document_id, "document_id")

    result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Verify session has access to this document
    verify_document_access(document, session)

    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
    )

    return DocumentResponse.from_model(document)


@router.post("/{document_id}/reprocess", response_model=DocumentImportResponse)
async def reprocess_document(
    document_id: str,
    session: RequireAuth,
    llm_assist: bool = False,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Retry extraction/OCR and rebuild observations/chunks for a document.

    ``llm_assist`` (query, default False) additionally runs the hard-validated
    LLM entity-proposal pass for visit notes; rule-based extraction always runs.
    """
    validate_uuid(document_id, "document_id")

    result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    verify_document_access(document, session)

    if document.doc_type in _STRUCTURED_IMPORT_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Reprocessing is not available for imported structured documents "
                "(CSV/FHIR). Delete and re-import the file instead."
            ),
        )

    # A user's rejection of an extraction is a safety decision; remember the
    # rejected (entity_type, quote) pairs so re-extraction of the same span
    # under a new UUID does not resurface it as unreviewed.
    rejected_rows = await profile_db.execute(
        select(DocumentEntity.entity_type, DocumentEntity.quote).where(
            DocumentEntity.doc_id == document_id,
            DocumentEntity.verified_by_user.is_(False),
        )
    )
    rejected_extractions = set(rejected_rows.all())

    # Reclassify from clean state after extraction refresh.
    await _prune_document_pin_targets(
        profile_db, document_id, include_document=False
    )
    await profile_db.execute(delete(DocumentEntity).where(DocumentEntity.doc_id == document_id))
    await profile_db.execute(delete(DocumentCategory).where(DocumentCategory.doc_id == document_id))

    extraction_outcome = await _run_extraction_pipeline(
        profile_db=profile_db,
        profile_id=session.profile_id,
        document=document,
        refresh_existing=True,
    )
    observations_extracted = extraction_outcome["observations_extracted"] if extraction_outcome else 0
    needs_verification = extraction_outcome["needs_verification"] if extraction_outcome else True
    extracted_text = extraction_outcome.get("extracted_text") if extraction_outcome else None

    await _classify_and_extract_entities(
        profile_db=profile_db,
        profile_id=session.profile_id,
        doc_id=document_id,
        doc_type=document.doc_type,
        pre_extracted_text=extracted_text,
        llm_assist=llm_assist,
    )

    if rejected_extractions:
        recreated = await profile_db.execute(
            select(DocumentEntity).where(DocumentEntity.doc_id == document_id)
        )
        for entity in recreated.scalars():
            if (entity.entity_type, entity.quote) in rejected_extractions:
                entity.verified_by_user = False

    # Ensure target cleanup is committed even when classification returns
    # early (for example, empty text or an unknown category).
    await profile_db.commit()

    await log_document_event(
        db=master_db,
        event="parse",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={
            "action": "reprocess",
            "status": document.status,
            "observations_extracted": observations_extracted,
            "llm_assist": llm_assist,
        },
    )
    await master_db.commit()

    return DocumentImportResponse(
        document=DocumentResponse.from_model(document),
        observations_extracted=observations_extracted,
        needs_verification=needs_verification,
    )


@router.post("/{document_id}/verify", response_model=DocumentVerifyResponse)
async def verify_document(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Mark all observations for a document as verified."""
    validate_uuid(document_id, "document_id")

    doc_result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    verify_document_access(document, session)

    result = await profile_db.execute(
        select(Observation).where(Observation.doc_id == document_id)
    )
    observations = result.scalars().all()
    now = utcnow()
    for obs in observations:
        obs.user_verified = True
        obs.verified_at = now
        obs.version += 1

    document.status = "verified"
    document.verified_at = now
    await profile_db.commit()

    await log_document_event(
        db=master_db,
        event="verify",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={"verified_count": len(observations)},
    )
    await master_db.commit()

    return DocumentVerifyResponse(
        document=DocumentResponse.from_model(document),
        verified_count=len(observations),
    )


class DocumentCategoryResponse(BaseModel):
    """Response model for document category."""
    id: str
    doc_id: str
    category: str
    confidence: float
    classified_by: str

    model_config = ConfigDict(from_attributes=True)


class DocumentEntityResponse(BaseModel):
    """Response model for document entity."""
    id: str
    doc_id: str
    category: str
    entity_type: str
    entity_value: str
    confidence: float
    source_page: Optional[int] = None
    # CITE-SRC-001: stored since HC-M12 but never returned, so the frontend
    # could not highlight an entity's region the way it can an observation's.
    source_bbox_json: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    quote: Optional[str] = None
    verified_by_user: Optional[bool] = None
    extraction_version: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/{document_id}/category", response_model=DocumentCategoryResponse)
async def get_document_category(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Get the classification category for a document."""
    validate_uuid(document_id, "document_id")

    # Verify document exists and user has access
    doc_result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    verify_document_access(document, session)

    result = await profile_db.execute(
        select(DocumentCategory).where(DocumentCategory.doc_id == document_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No category found for this document")

    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={"action": "category"},
    )

    return DocumentCategoryResponse(
        id=category.id,
        doc_id=category.doc_id,
        category=category.category,
        confidence=category.confidence,
        classified_by=category.classified_by,
    )


@router.get("/{document_id}/entities", response_model=list[DocumentEntityResponse])
async def get_document_entities(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Get extracted entities for a document."""
    validate_uuid(document_id, "document_id")

    # Verify document exists and user has access
    doc_result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    verify_document_access(document, session)

    result = await profile_db.execute(
        select(DocumentEntity).where(DocumentEntity.doc_id == document_id)
    )
    entities = result.scalars().all()

    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={"action": "entities", "count": len(entities)},
    )

    return [DocumentEntityResponse.model_validate(ent) for ent in entities]


class EntityVerificationRequest(BaseModel):
    """Request body for setting an entity's user verification state.

    verified: true = verified, false = rejected, null = reset to unreviewed.
    """
    verified: Optional[bool] = None


@router.patch(
    "/{document_id}/entities/{entity_id}/verification",
    response_model=DocumentEntityResponse,
)
async def set_entity_verification(
    document_id: str,
    entity_id: str,
    payload: EntityVerificationRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Set the user verification state of an extracted entity."""
    validate_uuid(document_id, "document_id")
    validate_uuid(entity_id, "entity_id")

    # Verify document exists and user has access
    doc_result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    verify_document_access(document, session)

    result = await profile_db.execute(
        select(DocumentEntity).where(
            DocumentEntity.id == entity_id,
            DocumentEntity.doc_id == document_id,
        )
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    entity.verified_by_user = payload.verified
    await profile_db.commit()

    await log_document_event(
        db=master_db,
        event="verify",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={
            "action": "entity_verification",
            "entity_id": entity_id,
            "entity_type": entity.entity_type,
            "verified": payload.verified,
        },
    )
    await master_db.commit()

    return DocumentEntityResponse.model_validate(entity)


# ---------------------------------------------------------------------------
# Smart highlights (HC-M16) — derived on read, never persisted
# ---------------------------------------------------------------------------

_HIGHLIGHTS_SUMMARY_MAX_DOCS = 50


class HighlightResponse(BaseModel):
    """A derived organizational tag resolving to its source row (HC-M16)."""

    highlight_type: str
    doc_id: str
    source_kind: str  # 'entity' | 'observation'
    source_id: str
    quote: Optional[str] = None
    confidence: Optional[float] = None
    verification_state: str

    @classmethod
    def from_highlight(cls, highlight: Highlight) -> "HighlightResponse":
        return cls(**asdict(highlight))


class DocumentHighlightSummary(BaseModel):
    """Highlight-type counts for one document (inbox chips)."""

    doc_id: str
    counts: dict[str, int]


@router.get("/highlights/summary", response_model=list[DocumentHighlightSummary])
async def get_highlights_summary(
    session: RequireAuth,
    limit: int = Query(
        20,
        ge=1,
        le=_HIGHLIGHTS_SUMMARY_MAX_DOCS,
        description="Most recently imported documents to summarize",
    ),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Per-document highlight-type counts for recent documents.

    Bounded: only the *limit* most recently imported documents are
    considered; documents with no highlights are omitted.
    """
    doc_result = await profile_db.execute(
        select(Document.id)
        .where(Document.profile_id == session.profile_id)
        .order_by(Document.imported_at.desc())
        .limit(limit)
    )
    doc_ids = list(doc_result.scalars().all())

    counts_by_doc: dict[str, dict[str, int]] = {doc_id: {} for doc_id in doc_ids}
    if doc_ids:
        entity_result = await profile_db.execute(
            select(DocumentEntity).where(DocumentEntity.doc_id.in_(doc_ids))
        )
        obs_result = await profile_db.execute(
            select(Observation).where(Observation.doc_id.in_(doc_ids))
        )
        for highlight in derive_highlights(
            entity_result.scalars().all(), obs_result.scalars().all()
        ):
            counts = counts_by_doc[highlight.doc_id]
            counts[highlight.highlight_type] = counts.get(highlight.highlight_type, 0) + 1

    summaries = [
        DocumentHighlightSummary(doc_id=doc_id, counts=counts_by_doc[doc_id])
        for doc_id in doc_ids
        if counts_by_doc[doc_id]
    ]

    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=session.profile_id,
        document_id="all",
        details={
            "action": "highlights_summary",
            "limit": limit,
            "count": len(summaries),
        },
    )

    return summaries


@router.get("/{document_id}/highlights", response_model=list[HighlightResponse])
async def get_document_highlights(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Derived highlights for one document (computed on read)."""
    validate_uuid(document_id, "document_id")

    doc_result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    verify_document_access(document, session)

    entity_result = await profile_db.execute(
        select(DocumentEntity).where(DocumentEntity.doc_id == document_id)
    )
    obs_result = await profile_db.execute(
        select(Observation).where(Observation.doc_id == document_id)
    )
    highlights = derive_highlights(
        entity_result.scalars().all(), obs_result.scalars().all()
    )

    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={"action": "highlights", "count": len(highlights)},
    )

    return [HighlightResponse.from_highlight(h) for h in highlights]


@router.get("/{document_id}/pages", response_model=list[PageResponse])
async def get_document_pages(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Get document pages for provenance viewing.

    Phase 3: Queries per-profile encrypted database.
    Returns text content per page for citation display.
    """
    # Validate document_id format (path traversal protection)
    validate_uuid(document_id, "document_id")

    result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Verify session has access to this document
    verify_document_access(document, session)

    pages = []

    if document.doc_type == "lab_pdf":
        try:
            import pdfplumber
            # Decrypt document for page extraction
            decrypted_doc = get_decrypted_document(document.profile_id, document_id)
            with pdfplumber.open(decrypted_doc) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    tables = page.extract_tables()
                    pages.append(PageResponse(
                        page_number=i + 1,
                        text=text,
                        has_tables=len(tables) > 0,
                    ))
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )
        except PermissionError as e:
            logger.error(f"Permission denied accessing document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access document - session may have expired"
            )
        except Exception as e:
            # Log the actual error for debugging but return generic message
            logger.error(f"Failed to extract pages from document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to extract document pages"
            )
    else:
        # For scanned/image docs, prefer OCR/chunk text if available.
        chunk_result = await profile_db.execute(
            select(Chunk)
            .where(Chunk.doc_id == document_id)
            .order_by(Chunk.page_number.asc(), Chunk.chunk_index.asc())
        )
        chunks = chunk_result.scalars().all()
        if chunks:
            page_to_text: dict[int, list[str]] = {}
            for chunk in chunks:
                page = chunk.page_number or 1
                page_to_text.setdefault(page, []).append(chunk.text)
            for page_num in sorted(page_to_text.keys()):
                pages.append(
                    PageResponse(
                        page_number=page_num,
                        text="\n\n".join(page_to_text[page_num]),
                        has_tables=False,
                    )
                )
        else:
            if document.status == "pending_ocr":
                text = "[Document requires OCR processing. Enable OCR in Settings to extract data.]"
            else:
                text = "[Image document]"
            pages.append(
                PageResponse(
                    page_number=1,
                    text=text,
                    has_tables=False,
                )
            )

    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={"action": "pages", "count": len(pages)},
    )

    return pages


@router.get("/{document_id}/pages/{page_number}/image")
async def get_page_image(
    document_id: str,
    page_number: int,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Render a PDF page as a PNG image for bounding-box citation overlay.

    OCR-BOX-001: Returns the page as image/png for visual provenance display.
    """
    validate_uuid(document_id, "document_id")

    result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    verify_document_access(document, session)

    if page_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be >= 1",
        )

    resolution = 150
    cache_key: _PageImageCacheKey = (
        document.profile_id,
        document_id,
        page_number,
        resolution,
    )
    cached = _page_image_cache_get(cache_key)
    content: bytes
    is_freshly_rendered = False
    try:
        if cached is not None:
            content = cached
        else:
            import pdfplumber
            from io import BytesIO

            decrypted_doc = get_decrypted_document(document.profile_id, document_id)
            with pdfplumber.open(decrypted_doc) as pdf:
                if page_number > len(pdf.pages):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Page {page_number} not found (document has {len(pdf.pages)} pages)",
                    )
                page = pdf.pages[page_number - 1]
                img = page.to_image(resolution=resolution)

                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                content = buf.getvalue()
                is_freshly_rendered = True
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found",
        )
    except Exception as e:
        logger.error(f"Failed to render page image for document {document_id}, page {page_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to render page image",
        )

    # Cache only after the view has been successfully audited: if the
    # audit write fails, a freshly rendered page isn't left sitting in
    # the cache unable to ever be served (the fail-closed audit means
    # every serve, cache hit or not, must succeed its audit anyway).
    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={"action": "page_image", "page_number": page_number},
    )

    if is_freshly_rendered:
        _page_image_cache_set(cache_key, content)

    return Response(
        content=content,
        media_type="image/png",
        headers={"Cache-Control": f"private, max-age={_PAGE_IMAGE_CACHE_TTL_SECONDS}"},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Delete a document and its associated data.

    Phase 3: Deletes from per-profile encrypted database.
    Creates audit log entry in master database.
    """
    # Validate document_id format (path traversal protection)
    validate_uuid(document_id, "document_id")

    result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Verify session has access to this document
    verify_document_access(document, session)

    profile_id = document.profile_id
    filename = document.source

    await _prune_document_pin_targets(
        profile_db, document_id, include_document=True
    )

    # Entities/categories have no ORM cascade from Document (and SQLite FK
    # enforcement is off); delete them explicitly so entity quotes — verbatim
    # document text — cannot outlive the document into exports or pins.
    await profile_db.execute(delete(DocumentEntity).where(DocumentEntity.doc_id == document_id))
    await profile_db.execute(delete(DocumentCategory).where(DocumentCategory.doc_id == document_id))

    # CARE-QUOTE-001: `care_plan_task.source_quote` is verbatim clinician text
    # and falls under the same rule as the entity quotes above — it must not
    # outlive the document. The task itself is kept: a follow-up the patient
    # still has to do does not stop being real because they deleted the PDF.
    # Only the provenance and the quote go.
    #
    # Deliberately NOT mirrored into the reprocess path: there the document
    # still exists, so the retention rationale does not apply, and
    # `get_care_task_candidates` keys duplicate detection on
    # (source_document_id, source_quote) — clearing either would resurface
    # already-accepted tasks as fresh candidates on every reprocess.
    await profile_db.execute(
        update(CarePlanTask)
        .where(CarePlanTask.source_document_id == document_id)
        .values(source_document_id=None, source_entity_id=None, source_quote=None)
    )

    # Delete document record from profile database (cascades to observations,
    # their interpretations, and chunks)
    await profile_db.delete(document)
    await profile_db.commit()

    # DOC-DELETE-INTERP: remove the encrypted file only after the rows are
    # committed. A failed commit must never leave a document row whose file
    # is already gone. A failed unlink here leaves only ciphertext under the
    # profile's own vault (swept by profile deletion); log it without the path
    # and still write the audit row below.
    vault_path = Path(settings.app_data_path) / "vaults" / profile_id / "docs"
    doc_path = vault_path / f"{document_id}.bin"
    try:
        if doc_path.exists():
            doc_path.unlink()
    except OSError as exc:
        logger.warning(
            "Document %s deleted but its encrypted file could not be removed: %s",
            document_id,
            type(exc).__name__,
        )

    # Create audit log in master database
    await log_document_event(
        db=master_db,
        event="delete",
        profile_id=profile_id,
        document_id=document_id,
        filename=filename,
    )
    await master_db.commit()
