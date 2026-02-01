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
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from core.audit import log_document_event
from core.auth import RequireAuth, Session, ProfileDbSession
from models import Document, Observation, Chunk, Embedding
from modules.extract import ExtractModule
from modules.chunking import ChunkingModule
from modules.embeddings import EmbeddingsModule

logger = logging.getLogger(__name__)

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

    class Config:
        from_attributes = True

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


class PageResponse(BaseModel):
    """Response model for document page content."""
    page_number: int
    text: str
    has_tables: bool


@router.post("/import", response_model=DocumentImportResponse, status_code=status.HTTP_201_CREATED)
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

    # Import using ingest module
    from modules import IngestModule

    vault_path = Path(settings.app_data_path) / "vaults" / profile_id
    ingest = IngestModule(vault_path)

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

    # Sprint 2: Trigger extraction pipeline
    observations_extracted = 0
    needs_verification = True

    if import_result.doc_type == "lab_pdf":
        try:
            doc_path = vault_path / "docs" / f"{import_result.document_id}.bin"
            extract_module = ExtractModule()
            extraction_result = await extract_module.extract_from_pdf(
                doc_path, import_result.document_id
            )

            # Persist observations to profile database
            import uuid
            for extracted_obs in extraction_result.observations:
                observation = Observation(
                    id=str(uuid.uuid4()),
                    profile_id=profile_id,
                    doc_id=import_result.document_id,
                    analyte_canonical=_canonicalize_analyte(extracted_obs.analyte_raw),
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
                    user_verified=False,
                )
                profile_db.add(observation)

            observations_extracted = len(extraction_result.observations)

            # Compute needs_verification
            needs_verification = _compute_needs_verification(extraction_result.observations)

            # Update document status to parsed
            document.status = "parsed"
            document.parsed_at = datetime.utcnow()

            await profile_db.commit()

            logger.info(
                f"Extracted {observations_extracted} observations from document {import_result.document_id}"
            )

            # Sprint 6: Create chunks and embeddings for RAG
            try:
                chunks_created = await _create_chunks_and_embeddings(
                    profile_db=profile_db,
                    doc_id=import_result.document_id,
                    doc_path=doc_path,
                )
                logger.info(
                    f"Created {chunks_created} chunks with embeddings for document {import_result.document_id}"
                )
            except Exception as chunk_error:
                logger.warning(
                    f"Chunking failed for document {import_result.document_id}: {chunk_error}"
                )
                # Don't fail import if chunking fails - RAG just won't work for this doc

        except Exception as e:
            logger.error(f"Extraction failed for document {import_result.document_id}: {e}")
            # Keep status as pending, don't fail the import
            document.status = "extraction_failed"
            await profile_db.commit()

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


def _canonicalize_analyte(raw_name: str) -> str:
    """
    Convert raw analyte name to canonical form.

    Sprint 2: Simple canonicalization - lowercase and normalize spacing.
    Future: Use a proper analyte mapping/ontology.
    """
    canonical = raw_name.lower().strip()
    # Normalize common variations
    canonical = canonical.replace("hemoglobin a1c", "hba1c")
    canonical = canonical.replace("hemoglobin", "hgb")
    canonical = canonical.replace(",", "")
    canonical = canonical.replace("  ", " ")
    return canonical


async def _create_chunks_and_embeddings(
    profile_db,
    doc_id: str,
    doc_path: Path,
) -> int:
    """
    Sprint 6: Create text chunks and embeddings for RAG.

    Extracts text from PDF, chunks it, generates embeddings, and persists to DB.

    Args:
        profile_db: Profile database session
        doc_id: Document ID
        doc_path: Path to the document file

    Returns:
        Number of chunks created
    """
    import pdfplumber

    chunker = ChunkingModule()
    embedder = EmbeddingsModule()

    # Extract text from each page
    pages_text = []
    with pdfplumber.open(doc_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)

    # Chunk across all pages
    all_chunks = chunker.chunk_pdf_pages(doc_id=doc_id, pages=pages_text)

    if not all_chunks:
        return 0

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


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    session: RequireAuth,
    doc_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    profile_db: ProfileDbSession = None,
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

    return [DocumentResponse.from_model(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
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

    return DocumentResponse.from_model(document)


@router.get("/{document_id}/pages", response_model=list[PageResponse])
async def get_document_pages(
    document_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
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

    # Get document file path
    vault_path = Path(settings.app_data_path) / "vaults" / document.profile_id / "docs"
    doc_path = vault_path / f"{document_id}.bin"

    if not doc_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found"
        )

    pages = []

    if document.doc_type == "lab_pdf":
        try:
            import pdfplumber
            with pdfplumber.open(doc_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    tables = page.extract_tables()
                    pages.append(PageResponse(
                        page_number=i + 1,
                        text=text,
                        has_tables=len(tables) > 0,
                    ))
        except Exception as e:
            # Log the actual error for debugging but return generic message
            logger.error(f"Failed to extract pages from document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to extract document pages"
            )
    else:
        # For images, return single "page"
        pages.append(PageResponse(
            page_number=1,
            text="[Image document - OCR not yet implemented]",
            has_tables=False,
        ))

    return pages


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
