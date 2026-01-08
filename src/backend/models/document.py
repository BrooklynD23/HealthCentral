"""
Document model for imported medical documents.

Stores metadata; actual document files are encrypted on disk.

Phase 3: This model lives in per-profile encrypted databases,
not the master database. No foreign key to Profile since they're
in separate databases.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.profile_database import ProfileDatabaseBase

if TYPE_CHECKING:
    from .observation import Observation
    from .chunk import Chunk


class Document(ProfileDatabaseBase):
    """
    Imported medical document metadata.

    The actual document is stored encrypted in the vault directory.
    This record tracks metadata, processing status, and relationships.

    Phase 3: Stored in per-profile encrypted SQLCipher database.
    """

    __tablename__ = "documents"

    # Primary key - UUID string
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Profile ID (stored but not a FK since profiles are in master DB)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # Hashes for deduplication and integrity
    path_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Document type (lab_pdf, lab_image, etc.)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Source information
    source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Processing status (pending, parsed, verified, error)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    # Document metadata
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    collection_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing timestamps
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Encryption metadata
    encryption_iv: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Relationships (within profile database only)
    observations: Mapped[list["Observation"]] = relationship(
        "Observation",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id!r}, type={self.doc_type!r}, status={self.status!r})>"
