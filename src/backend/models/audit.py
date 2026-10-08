"""
Audit log model for tracking all operations.

HIPAA-compliant audit trail for security and compliance.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.time import utcnow

if TYPE_CHECKING:
    from .profile import Profile


class AuditLog(Base):
    """
    Audit trail entry.

    Records all significant operations for HIPAA compliance:
    - Profile access and modifications
    - Document imports, views, and deletes
    - Observation edits and verifications
    - Export operations
    """

    __tablename__ = "audit_logs"

    # Primary key - auto-generated UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign key to profile (nullable for system events)
    profile_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Event classification
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(500), nullable=False)

    # Entity affected
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Additional details as JSON
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Client information
    client_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamp (indexed for queries)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, index=True
    )

    # Relationship
    profile: Mapped[Optional["Profile"]] = relationship(
        "Profile", back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id!r}, type={self.event_type!r}, action={self.action!r})>"
