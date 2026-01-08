"""
Chunk model for RAG text segments.

Stores text chunks extracted from documents for vector search.

Phase 3: This model lives in per-profile encrypted databases,
not the master database.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.profile_database import ProfileDatabaseBase

if TYPE_CHECKING:
    from .document import Document
    from .embedding import Embedding


class Chunk(ProfileDatabaseBase):
    """
    Text chunk for RAG pipeline.

    Documents are split into chunks for:
    - Vector embedding and similarity search
    - Provenance tracking (page/position references)
    - Citation generation

    Phase 3: Stored in per-profile encrypted SQLCipher database.
    """

    __tablename__ = "chunks"

    # Primary key - auto-generated UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign key to document
    doc_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk sequence within document
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Text content
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Source location
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_char: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_char: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Chunk metadata
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_type: Mapped[str] = mapped_column(
        String(50), default="text", nullable=False
    )  # text, table, header

    # Processing timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    embedding: Mapped[Optional["Embedding"]] = relationship(
        "Embedding",
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<Chunk(id={self.id!r}, doc={self.doc_id!r}, text={preview!r})>"
