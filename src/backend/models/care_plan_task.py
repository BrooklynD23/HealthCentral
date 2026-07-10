"""Care-plan task model (HC-M15).

A checklist item derived from a clinician's recorded instruction in a visit
note (follow-up, ordered test, referral). Tasks exist only after explicit
user acceptance of a derived candidate — nothing is auto-created. Each task
keeps the verbatim source quote so the UI can always show the clinician's
exact words.

Stored in per-profile encrypted databases (patient data).
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase
from core.time import utcnow

# Allowed task states.
CARE_PLAN_TASK_STATUSES = ("open", "done", "ignored", "needs_review")


class CarePlanTask(ProfileDatabaseBase):
    """A user-accepted follow-up task with source provenance."""

    __tablename__ = "care_plan_task"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # Due dates are never invented: null unless the source text supported one.
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # open | done | ignored | needs_review
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open", index=True)
    source_document_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("documents.id"), nullable=True, index=True
    )
    source_entity_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("document_entity.id"), nullable=True, index=True
    )
    # Verbatim clinician wording the task was derived from.
    source_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return f"<CarePlanTask(id={self.id!r}, status={self.status!r}, title={self.title!r})>"
