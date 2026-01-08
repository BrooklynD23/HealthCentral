"""
Profile model for user accounts.

Each profile represents a user with their own encrypted vault.

Phase 3: Profile stays in master database (for login/listing).
Profile-specific data (documents, observations) are in per-profile
encrypted SQLCipher databases.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from .audit import AuditLog


class Profile(Base):
    """
    User profile with encrypted vault.

    Each profile has:
    - Unique encryption key (sealed with DPAPI or password-derived key)
    - Isolated document storage in per-profile encrypted database
    - Audit trail in master database

    Phase 3: Profile metadata remains in master database for:
    - Profile listing (before login)
    - Password authentication
    - Session validation

    Sensitive data (documents, observations) are in separate
    per-profile SQLCipher-encrypted databases.
    """

    __tablename__ = "profiles"

    # Primary key - UUID string
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Profile info
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Encryption key reference (key stored in vault, not DB)
    encryption_key_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Authentication (Phase 2: add password hash)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_salt: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Lock status
    is_locked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships (only to models in master database)
    # Note: Documents and Observations are now in per-profile encrypted databases
    # and cannot have cross-database foreign key relationships

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Profile(id={self.id!r}, name={self.display_name!r})>"
