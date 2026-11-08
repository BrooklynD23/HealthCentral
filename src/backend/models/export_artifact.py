"""Downloadable export artifacts, persisted in each encrypted profile vault.

G-C1 / PRIV-08: a doctor summary, visit-prep or pinboard packet, or FHIR bundle
must still download after a backend restart. Rows hold the redacted dict the
download routes render from. They live in the profile vault (never the master
DB) and are erased with it by DELETE /profiles/{id} (AGENT.md flow 5, step 4).

Retention (owner answer EXPORT-ARTIFACT-RETENTION, 2026-11-07): a row is served
for at most `api.export._EXPORT_TTL` after `created_at`, and is removed at
logout, lock and profile delete. No foreign key: a row is self-contained.

Session binding (EXPORT-SESSION-BIND, 2026-11-07): `session_jti` is the JWT `jti` of
the session that generated the row. It is served only to that session while the jti
is unrevoked. NULL (or empty) is never served: it fails closed.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase
from core.time import utcnow

EXPORT_ARTIFACT_KINDS = ("doctor_summary", "visit_prep", "fhir_r4")


class ExportArtifact(ProfileDatabaseBase):
    __tablename__ = "export_artifact"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    profile_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    session_jti: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
