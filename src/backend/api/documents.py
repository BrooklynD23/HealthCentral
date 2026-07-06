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
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings, user_ocr_preference_enabled, compute_ocr_effective
from core.audit import log_document_event, audit_and_commit
from core.auth import RequireAuth, Session, ProfileDbSession
from core.document_crypto import get_decrypted_document, get_profile_encryption_key
from models import Document, Observation, Chunk, Embedding, UserModelSettings
from modules.extract import ExtractModule
from modules.normalize import NormalizeModule
from modules.chunking import ChunkingModule
from modules.embeddings import EmbeddingsModule
from modules.document_classifier import classify_document
from modules.extract_imaging import extract_imaging_entities
from modules.extract_pathology import extract_pathology_entities
from modules.extract_visit_notes import extract_visit_note_entities
from models.document_category import DocumentCategory, DocumentEntity

logger = logging.getLogger(__name__)

# Shared normalizer instance
_normalizer = NormalizeModule()

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

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, doc: Document) -> "DocumentResponse":
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
        )


class DocumentImportResponse(BaseModel):
    """Response model for document import."""
    document: DocumentResponse
    observations_extracted: int
    needs_verification: bool


class DocumentVerifyResponse(BaseModel):
    """Response model for document-level verification."""
    document: DocumentResponse
    verified_count: int


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
    responses={200: {"model": DocumentImportResponse, "description": "Duplicate document already exists"}},
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

    # Check for duplicate content before creating new record
    existing_result = await profile_db.execute(
        select(Document).where(
            Document.profile_id == profile_id,
            Document.content_hash == import_result.content_hash,
        )
    )
    existing_doc = existing_result.scalar_one_or_none()

    if existing_doc:
        # Clean up the encrypted file that ingest just stored
        vault_path = Path(settings.app_data_path) / "vaults" / profile_id / "docs"
        orphan_path = vault_path / f"{import_result.document_id}.bin"
        if orphan_path.exists():
            orphan_path.unlink()
        # Return existing document with 200 (not 201)
        obs_result = await profile_db.execute(
            select(Observation).where(Observation.doc_id == existing_doc.id)
        )
        obs_count = len(obs_result.scalars().all())
        response_data = DocumentImportResponse(
            document=DocumentResponse.from_model(existing_doc),
            observations_extracted=obs_count,
            needs_verification=False,
        )
        return JSONResponse(
            content=response_data.model_dump(mode="json"),
            status_code=status.HTTP_200_OK,
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
        imported_at=datetime.utcnow(),
    )

    profile_db.add(document)
    await profile_db.commit()

    # Trigger extraction pipeline
    observations_extracted = 0
    needs_verification = True
    extracted_text: Optional[str] = None

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

    # Create audit log in master database
    await log_document_event(
        db=master_db,
        event="import",
        profile_id=profile_id,
        document_id=import_result.document_id,
        filename=file.filename,
        details={
            "doc_type": import_result.doc_type,
            "encrypted": import_result.encrypted,
            "observations_extracted": observations_extracted,
        },
    )
    await master_db.commit()

    return DocumentImportResponse(
        document=DocumentResponse.from_model(document),
        observations_extracted=observations_extracted,
        needs_verification=needs_verification,
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
        document.parsed_at = datetime.utcnow()
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
) -> None:
    """Classify a document and persist category + extracted entities.

    Extracts text from the decrypted document, runs the rule-based classifier,
    and if a category is found, runs the appropriate entity extractor.
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

    return [DocumentResponse.from_model(doc) for doc in documents]


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
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Retry extraction/OCR and rebuild observations/chunks for a document."""
    validate_uuid(document_id, "document_id")

    result = await profile_db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    verify_document_access(document, session)

    # Reclassify from clean state after extraction refresh.
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
    )

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
    now = datetime.utcnow()
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

    return [
        DocumentEntityResponse(
            id=ent.id,
            doc_id=ent.doc_id,
            category=ent.category,
            entity_type=ent.entity_type,
            entity_value=ent.entity_value,
            confidence=ent.confidence,
            source_page=ent.source_page,
        )
        for ent in entities
    ]


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
                _page_image_cache_set(cache_key, content)
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

    await audit_and_commit(
        master_db,
        log_document_event,
        event="view",
        profile_id=session.profile_id,
        document_id=document_id,
        filename=document.source,
        details={"action": "page_image", "page_number": page_number},
    )

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

    # Delete document file
    vault_path = Path(settings.app_data_path) / "vaults" / profile_id / "docs"
    doc_path = vault_path / f"{document_id}.bin"
    if doc_path.exists():
        doc_path.unlink()

    # Delete document record from profile database (cascades to observations, chunks)
    await profile_db.delete(document)
    await profile_db.commit()

    # Create audit log in master database
    await log_document_event(
        db=master_db,
        event="delete",
        profile_id=profile_id,
        document_id=document_id,
        filename=filename,
    )
    await master_db.commit()
