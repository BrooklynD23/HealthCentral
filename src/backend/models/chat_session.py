"""
ChatSession and ChatTurn models for persistent conversation history.

ASSIST-HIST-001: Per-profile encrypted storage of assistant conversations.
Stored in per-profile SQLCipher databases for privacy isolation.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.profile_database import ProfileDatabaseBase


class ChatSession(ProfileDatabaseBase):
    """
    A single named conversation session with the assistant.

    Conversations are bounded to one profile.  Clients may create explicit
    sessions or rely on the backend to create an implicit one per-request.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # Human-readable label set by the client or auto-generated from first question
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationship to turns (lazy loaded to avoid N+1 in list endpoints)
    turns: Mapped[list["ChatTurn"]] = relationship(
        "ChatTurn",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatTurn.turn_index",
        lazy="select",
    )


class ChatTurn(ProfileDatabaseBase):
    """
    A single user→assistant exchange within a ChatSession.

    Both user and assistant messages are stored so the full conversation
    can be reconstructed for multi-turn context injection.
    """

    __tablename__ = "chat_turns"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # Sequential index within the session (0-based)
    turn_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # "user" or "assistant"
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="turns",
    )
