"""
Document management API endpoints.

Handles document import, listing, and viewing.
All endpoints require authentication.
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
from core.auth import RequireAuth, Session
from models import Document, Profile

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
    db: AsyncSession = Depends(get_db),
):
    """
    Import a document (PDF or image) into the authenticated profile.

    Process:
    1. Validate file type and size
    2. Compute content hash for deduplication
    3. Encrypt and store document
    4. Extract text and observations
    5. Create audit log entry

    Returns extracted observations count and verification status.
    """
    profile_id = session.profile_id

    # Verify profile exists
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

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

    # Create document record
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

    db.add(document)

    # Create audit log
    await log_document_event(
        db=db,
        event="import",
        profile_id=profile_id,
        document_id=import_result.document_id,
        filename=file.filename,
        details={"doc_type": import_result.doc_type, "encrypted": import_result.encrypted},
    )

    await db.commit()

    return DocumentImportResponse(
        document=DocumentResponse.from_model(document),
        observations_extracted=0,  # Will be filled after extraction
        needs_verification=True,
    )


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    session: RequireAuth,
    doc_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    db: AsyncSession = Depends(get_db),
):
    """
    List documents for the authenticated profile.

    Supports filtering by status and document type.
    """
    profile_id = session.profile_id

    # Build query - only show documents for authenticated profile
    query = select(Document).where(Document.profile_id == profile_id)

    if doc_status:
        query = query.where(Document.status == doc_status)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)

    query = query.order_by(Document.imported_at.desc())

    result = await db.execute(query)
    documents = result.scalars().all()

    return [DocumentResponse.from_model(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: RequireAuth,
    db: AsyncSession = Depends(get_db),
):
    """Get document details."""
    # Validate document_id format (path traversal protection)
    validate_uuid(document_id, "document_id")

    result = await db.execute(select(Document).where(Document.id == document_id))
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
    db: AsyncSession = Depends(get_db),
):
    """
    Get document pages for provenance viewing.

    Returns text content per page for citation display.
    """
    # Validate document_id format (path traversal protection)
    validate_uuid(document_id, "document_id")

    result = await db.execute(select(Document).where(Document.id == document_id))
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
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a document and its associated data.

    Creates audit log entry.
    """
    # Validate document_id format (path traversal protection)
    validate_uuid(document_id, "document_id")

    result = await db.execute(select(Document).where(Document.id == document_id))
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

    # Delete document record (cascades to observations, chunks)
    await db.delete(document)

    # Create audit log
    await log_document_event(
        db=db,
        event="delete",
        profile_id=profile_id,
        document_id=document_id,
        filename=filename,
    )

    await db.commit()
