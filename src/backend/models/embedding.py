"""
Embedding model for vector storage.

Stores vector embeddings for RAG similarity search.

Phase 3: This model lives in per-profile encrypted databases,
not the master database.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.profile_database import ProfileDatabaseBase
from core.time import utcnow

if TYPE_CHECKING:
    from .chunk import Chunk


class Embedding(ProfileDatabaseBase):
    """
    Vector embedding for a text chunk.

    Stores the embedding vector for similarity search.
    Vector is stored as binary blob (more efficient than JSON).

    Phase 3: Stored in per-profile encrypted SQLCipher database.
    """

    __tablename__ = "embeddings"

    # Primary key - auto-generated UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign key to chunk (one-to-one)
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Embedding model used
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Vector storage (binary blob for efficiency)
    vector_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # Vector dimensions (for validation)
    dimensions: Mapped[int] = mapped_column(nullable=False)

    # Optional: JSON representation for debugging
    vector_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    # Relationship
    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="embedding")

    def __repr__(self) -> str:
        return f"<Embedding(id={self.id!r}, chunk={self.chunk_id!r}, dims={self.dimensions})>"
