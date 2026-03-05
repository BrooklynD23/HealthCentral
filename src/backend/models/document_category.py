"""Document classification and entity extraction models.

INGEST-EPIC-001: Imaging, pathology, and visit note document support.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase


class DocumentCategory(ProfileDatabaseBase):
    """Primary category classification for a document."""

    __tablename__ = "document_category"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(Text, ForeignKey("documents.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    classified_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DocumentCategory(doc_id={self.doc_id}, category={self.category})>"


class DocumentEntity(ProfileDatabaseBase):
    """Extracted entity from a document."""

    __tablename__ = "document_entity"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(Text, ForeignKey("documents.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_bbox_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DocumentEntity(doc_id={self.doc_id}, type={self.entity_type})>"
