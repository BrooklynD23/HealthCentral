"""
MemoryItem model for persistent assistant memory store.

ASSIST-MEM-001: Per-profile encrypted memory items with CRUD support.
Stored in per-profile SQLCipher databases for privacy.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase


class MemoryItem(ProfileDatabaseBase):
    """
    Persistent memory item for the assistant.

    Stored in the per-profile encrypted database.
    Users can view, edit, and delete these items.
    """

    __tablename__ = "memory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    profile_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    value: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
