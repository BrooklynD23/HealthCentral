"""
ResponseFeedback model for RL feedback capture.

RL-FEED-001: Per-profile encrypted storage of human feedback on assistant responses.
Supports DPO/GRPO-ready preference dataset export.
Stored in per-profile SQLCipher databases for privacy isolation.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase


class ResponseFeedback(ProfileDatabaseBase):
    """
    Human feedback on a single assistant turn.

    Records thumbs up/down, optional correction text, and tags.
    Upsertable: one row per (profile_id, turn_id).
    Captures prompt_snapshot so preference pairs are reproducible offline.
    """

    __tablename__ = "response_feedback"

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

    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # FK to chat_turns assistant turn (logical — no DB-level FK enforcement on
    # SQLite to keep migration simple; enforced at application layer)
    turn_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # +1 = thumbs up, -1 = thumbs down
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Optional user-supplied improved answer (used as "chosen" in DPO pairs)
    correction_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # JSON list of tags e.g. ["inaccurate", "too_technical"]
    feedback_tags: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Fully-composed prompt (with retrieved context) at the time of inference.
    # Stored so preference pairs can be reconstructed reproducibly.
    prompt_snapshot: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # The assistant's response text at the time of rating
    response_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Model/provider metadata for bandit-style strategy analysis
    model_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    provider: Mapped[Optional[str]] = mapped_column(
        String(100),
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
