"""Opt-in data donation tables, stored in the per-profile encrypted database.

RSI1-DONATE PR-1. ``donated_records`` holds redacted text only: there is no
raw-text column, and ``source_id`` is an opaque reference with no foreign key.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase
from core.time import utcnow


class DonationConsent(ProfileDatabaseBase):
    """One consent record per grant. Revoke sets revoked_at; rows are never deleted.

    revoked_at also closes a row superseded by a grant of a new
    consent_text_version, so a closed row is not always a patient revoke.

    At most one active row (revoked_at IS NULL) per (profile, purpose); a
    re-grant after a revoke inserts a new row so the dated revoke survives.
    """

    __tablename__ = "donation_consents"
    __table_args__ = (
        Index(
            "uq_donation_consents_active",
            "profile_id",
            "purpose",
            unique=True,
            sqlite_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    consent_text_version: Mapped[str] = mapped_column(String(64), nullable=False)


class DonatedRecord(ProfileDatabaseBase):
    """A strict-redacted record donated for one purpose."""

    __tablename__ = "donated_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)  # real | synthetic | canary
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    prompt_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    response_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    strict_redaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
