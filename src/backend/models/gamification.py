"""Gamification models — badge definitions and earned badges.

Stored in per-profile encrypted database for data isolation.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase


class BadgeDefinition(ProfileDatabaseBase):
    """Badge definition with criteria for earning."""

    __tablename__ = "badge_definition"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(Text, nullable=False)
    criteria_type: Mapped[str] = mapped_column(Text, nullable=False)
    criteria_json: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<BadgeDefinition(id={self.id}, name={self.name})>"


class EarnedBadge(ProfileDatabaseBase):
    """Record of a badge earned by a profile.

    medication_id='' for global badges (First Log, Multi-Med Master, Comeback Kid).
    Uses empty string instead of NULL to avoid SQLite NULL uniqueness bug
    where multiple NULLs are allowed in UNIQUE constraints.
    """

    __tablename__ = "earned_badge"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "badge_id", "medication_id",
            name="uq_earned_badge",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    profile_id: Mapped[str] = mapped_column(Text, nullable=False)
    badge_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("badge_definition.id"),
        nullable=False,
    )
    medication_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<EarnedBadge(badge_id={self.badge_id}, "
            f"profile_id={self.profile_id})>"
        )
