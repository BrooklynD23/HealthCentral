"""User-curated pinboards stored in each encrypted profile database."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.profile_database import ProfileDatabaseBase
from core.time import utcnow


PINBOARD_ITEM_TYPES = ("document", "observation", "care_task", "question")


class Pinboard(ProfileDatabaseBase):
    __tablename__ = "pinboard"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
    items: Mapped[list["PinboardItem"]] = relationship(
        back_populates="pinboard", cascade="all, delete-orphan"
    )


class PinboardItem(ProfileDatabaseBase):
    __tablename__ = "pinboard_item"
    __table_args__ = (
        UniqueConstraint(
            "pinboard_id", "item_type", "item_id", name="uq_pinboard_item_target"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    pinboard_id: Mapped[str] = mapped_column(
        Text, ForeignKey("pinboard.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    item_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    pinboard: Mapped[Pinboard] = relationship(back_populates="items")
