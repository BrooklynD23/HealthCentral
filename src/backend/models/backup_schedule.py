"""Per-profile backup schedule (BKUP-UX-001).

**Why this lives in the master database, not the profile vault.**

The obvious home would be `UserModelSettings` alongside every other per-profile
preference. It cannot go there: profile settings live inside the SQLCipher
vault, which is only readable while that profile is *unlocked*, and a
background scheduler needs to know a backup is due precisely when nobody is
signed in. A schedule stored in the vault is invisible at the only moment it
matters.

So this is operational metadata in the master DB, keyed by profile id.

**The master DB is not encrypted**, which means the same rule applies here as
to audit rows (AUDIT-PHI-001): no health data, no display names, no
user-supplied text of any kind. Everything below is an id, an enum, a count or
a timestamp. If a field is ever added here, it must clear that bar.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from core.time import utcnow


# Interval values. Stored as a short enum string rather than a number of
# seconds so the intent stays readable in the row.
BACKUP_FREQUENCIES = ("off", "daily", "weekly")

# Outcome of the last attempt. "skipped_locked" is a real, expected outcome —
# a scheduled backup cannot run for a locked vault, and recording that honestly
# is better than pretending the backup happened.
BACKUP_RESULTS = ("never_run", "success", "failed", "skipped_locked")


class BackupSchedule(Base):
    """One row per profile that has ever configured backups."""

    __tablename__ = "backup_schedules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # "off" | "daily" | "weekly"
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="off")

    # How many backups to keep when pruning. 0 means "never prune".
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # One of BACKUP_RESULTS — an enum, never an error message, which could
    # contain a filesystem path derived from user data.
    last_result: Mapped[str] = mapped_column(
        String(24), nullable=False, default="never_run"
    )

    # Number of files in the last successful backup. A count, not a manifest.
    last_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<BackupSchedule profile={self.profile_id} "
            f"frequency={self.frequency} enabled={self.enabled}>"
        )
