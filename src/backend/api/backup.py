"""Backup and restore API (BKUP-UX-001).

`scripts/backup.py` has had working backup/verify/restore/prune for a while,
but only as a developer CLI — no patient was ever going to run it, so device
loss destroyed the whole record. This wraps that script rather than
reimplementing it.

Two decisions worth stating up front:

**Backups are not redacted.** Every other export path in this app passes
through `modules/redaction.py`, and that is correct: those exports go to a
third party. A backup is the opposite — it is the user's own full-fidelity
record, going to their own machine, and a redacted backup cannot be restored,
which defeats the entire feature. This is the one export-shaped path that is
deliberately unredacted. Do not "fix" it to match `export.py`.

**Restore is destructive and gated accordingly.** It overwrites live vaults, so
it requires password re-auth plus a confirmation phrase, closes the profile
session first, and relies on the safety copies `scripts/backup.py` already
makes.
"""

import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import audit_and_commit, create_audit_log, log_export_event
from core.auth import (
    RequireAuth,
    Session,
    authenticate_profile,
    close_profile_database_on_logout,
    require_profile_access,
)
from core.config import settings
from core.database import get_db
from core.rate_limiter import auth_rate_limiter
from core.time import utcfromtimestamp, utcnow
from models import BackupSchedule, Profile
from scripts import backup as backup_script

logger = logging.getLogger(__name__)

router = APIRouter()

# Restoring overwrites live health data, so it takes the same shape of gate as
# profile deletion: a fixed phrase the user must type, not a checkbox.
BACKUP_RESTORE_CONFIRMATION = "RESTORE MY DATA"

VALID_FREQUENCIES = ("off", "daily", "weekly")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BackupSummary(BaseModel):
    """One backup on disk."""

    backup_id: str  # the directory name, e.g. "backup_20260728_101500"
    created_at: str
    file_count: int
    size_bytes: int
    verified: Optional[bool] = None


class BackupListResponse(BaseModel):
    backups: list[BackupSummary]
    backup_directory: str
    last_backup_at: Optional[str] = None


class CreateBackupResponse(BaseModel):
    backup_id: str
    file_count: int
    method: str
    created_at: str


class VerifyBackupResponse(BaseModel):
    backup_id: str
    valid: bool
    files_checked: int
    errors: list[str]


class RestoreRequest(BaseModel):
    password: str
    confirmation_phrase: str


class RestoreResponse(BaseModel):
    files_restored: int
    safety_copy_count: int


class PruneRequest(BaseModel):
    retention_days: int = Field(default=30, ge=0, le=3650)


class PruneResponse(BaseModel):
    removed: int


class ScheduleResponse(BaseModel):
    enabled: bool
    frequency: str
    retention_days: int
    last_run_at: Optional[str] = None
    last_result: str
    last_file_count: int


class ScheduleRequest(BaseModel):
    enabled: bool
    frequency: str = "off"
    retention_days: int = Field(default=30, ge=0, le=3650)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    return Path(settings.app_data_path)


def _backup_root() -> Path:
    """The managed backup directory, alongside the vaults it protects."""
    return _data_dir() / "backups"


def _profile_backup_root(profile_id: str) -> Path:
    """Backups are stored per profile.

    Per-profile isolation applies to backups exactly as it applies to vaults:
    one profile must never be able to list, download or restore another's.
    Keying the directory by profile id makes that structural rather than a
    filter someone can forget to apply.
    """
    return _backup_root() / profile_id


def _resolve_backup_dir(profile_id: str, backup_id: str) -> Path:
    """Resolve a backup id to a directory, refusing anything that escapes.

    `backup_id` arrives from the client, so it is treated as hostile: the
    resolved path must stay inside this profile's backup root.
    """
    root = _profile_backup_root(profile_id).resolve()
    candidate = (root / backup_id).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup id"
        )
    if not candidate.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found"
        )
    return candidate


def _summarize(path: Path) -> BackupSummary:
    files = [f for f in path.rglob("*") if f.is_file()]
    return BackupSummary(
        backup_id=path.name,
        created_at=utcfromtimestamp(path.stat().st_mtime).isoformat() + "Z",
        file_count=max(len(files) - 1, 0),  # manifest.json is bookkeeping
        size_bytes=sum(f.stat().st_size for f in files),
    )


async def _get_or_create_schedule(profile_id: str, db: AsyncSession) -> BackupSchedule:
    result = await db.execute(
        select(BackupSchedule).where(BackupSchedule.profile_id == profile_id)
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        schedule = BackupSchedule(profile_id=profile_id)
        db.add(schedule)
        await db.flush()
    return schedule


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_model=BackupListResponse)
async def list_backups(
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """List this profile's backups, newest first."""
    root = _profile_backup_root(session.profile_id)
    backups = (
        sorted(
            (_summarize(p) for p in root.iterdir() if p.is_dir()),
            key=lambda b: b.created_at,
            reverse=True,
        )
        if root.is_dir()
        else []
    )

    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type="backup.view",
        action="Viewed backups",
        profile_id=session.profile_id,
        entity_type="backup",
        entity_id="all",
        details={"count": len(backups)},
    )

    return BackupListResponse(
        backups=backups,
        backup_directory=str(root),
        last_backup_at=backups[0].created_at if backups else None,
    )


@router.post("/", response_model=CreateBackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """Create a backup of this profile now.

    Delegates to `scripts.backup.backup`, which snapshots the master DB, this
    profile's vault database and — since the fixes in this cycle — its sealed
    key files. Without those keys a restored vault is ciphertext with no way in.
    """
    root = _profile_backup_root(session.profile_id)
    root.mkdir(parents=True, exist_ok=True)

    result = backup_script.backup(
        data_dir=_data_dir(), backup_dir=root, profile_id=session.profile_id
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backup failed",
        )

    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type="backup.create",
        action="Created backup",
        profile_id=session.profile_id,
        entity_type="backup",
        entity_id=result.backup_path.name,
        details={"count": result.files_backed_up, "format": result.method},
    )

    return CreateBackupResponse(
        backup_id=result.backup_path.name,
        file_count=result.files_backed_up,
        method=result.method,
        created_at=utcnow().isoformat() + "Z",
    )


@router.post("/{backup_id}/verify", response_model=VerifyBackupResponse)
async def verify_backup(
    backup_id: str,
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """Re-check a backup's files against the SHA256s in its manifest."""
    path = _resolve_backup_dir(session.profile_id, backup_id)
    result = backup_script.verify(path)

    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type="backup.verify",
        action="Verified backup",
        profile_id=session.profile_id,
        entity_type="backup",
        entity_id=backup_id,
        details={"count": result.files_checked, "verified": result.valid},
    )

    return VerifyBackupResponse(
        backup_id=backup_id,
        valid=result.valid,
        files_checked=result.files_checked,
        errors=result.errors,
    )


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: str,
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """Stream a backup as a zip so it can leave the device.

    A backup that never leaves the machine does not survive the device loss it
    exists to protect against, so this is the half that makes the feature real.

    The archive is built in memory rather than written to a temp file: a second
    plaintext-on-disk copy of an entire vault, with no owner responsible for
    deleting it, is exactly the kind of artifact this app should not create.
    Backups are small (the vault DB plus key files), so this is affordable.

    Not redacted — see the module docstring.
    """
    path = _resolve_backup_dir(session.profile_id, backup_id)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, arcname=str(file_path.relative_to(path)))
    buffer.seek(0)

    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=session.profile_id,
        export_type="backup_archive",
        details={"export_id": backup_id},
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{backup_id}.zip"'},
    )


@router.post("/{backup_id}/restore", response_model=RestoreResponse)
async def restore_backup(
    backup_id: str,
    payload: RestoreRequest,
    request: Request,
    session: Session = Depends(require_profile_access()),
    master_db: AsyncSession = Depends(get_db),
):
    """Restore this profile from a backup. **Overwrites live data.**

    Guards, in order:
    1. password re-auth — a session token alone is not enough to overwrite a
       health record
    2. an exact confirmation phrase
    3. the profile database is closed and its in-memory key cleared before any
       file is touched, so nothing is holding a handle to a file being replaced

    `scripts.backup.restore` writes `.bak` safety copies of whatever it
    replaces; those are the undo path and are reported back.

    One consequence the UI must state: restoring an older vault also restores
    that backup's sealed key files, so afterwards the password *and the
    recovery code* that work are the ones from the backup, not the current ones.
    """
    result_row = await master_db.execute(
        select(Profile).where(Profile.id == session.profile_id)
    )
    if result_row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"restore:{client_ip}:{session.profile_id}"
    decision = auth_rate_limiter.check(rate_key)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many restore attempts. Try again later.",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    if await authenticate_profile(session.profile_id, payload.password, master_db) is None:
        auth_rate_limiter.add_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )

    if payload.confirmation_phrase != BACKUP_RESTORE_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmation phrase must be exactly '{BACKUP_RESTORE_CONFIRMATION}'",
        )

    path = _resolve_backup_dir(session.profile_id, backup_id)

    # Refuse to restore something we know is corrupt — overwriting a working
    # vault with a broken snapshot is the worst outcome this route can produce.
    check = backup_script.verify(path)
    if not check.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This backup failed verification and was not restored.",
        )

    # Release file handles and clear the in-memory key before overwriting.
    await close_profile_database_on_logout(session.profile_id)

    result = backup_script.restore(backup_path=path, data_dir=_data_dir())
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Restore failed; safety copies were left in place.",
        )

    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type="backup.restore",
        action="Restored from backup",
        profile_id=session.profile_id,
        entity_type="backup",
        entity_id=backup_id,
        details={"count": result.files_restored},
    )

    return RestoreResponse(
        files_restored=result.files_restored,
        safety_copy_count=len(result.safety_copies),
    )


@router.post("/prune", response_model=PruneResponse)
async def prune_backups(
    payload: PruneRequest,
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """Delete this profile's backups older than the retention window."""
    root = _profile_backup_root(session.profile_id)
    removed = backup_script.prune(root, payload.retention_days) if root.is_dir() else 0

    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type="backup.prune",
        action="Pruned backups",
        profile_id=session.profile_id,
        entity_type="backup",
        entity_id="all",
        details={"count": removed, "limit": payload.retention_days},
    )

    return PruneResponse(removed=removed)


@router.get("/schedule", response_model=ScheduleResponse)
async def get_schedule(
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """Get this profile's backup schedule."""
    schedule = await _get_or_create_schedule(session.profile_id, master_db)
    await master_db.commit()
    return ScheduleResponse(
        enabled=schedule.enabled,
        frequency=schedule.frequency,
        retention_days=schedule.retention_days,
        last_run_at=schedule.last_run_at.isoformat() + "Z" if schedule.last_run_at else None,
        last_result=schedule.last_result,
        last_file_count=schedule.last_file_count,
    )


@router.put("/schedule", response_model=ScheduleResponse)
async def set_schedule(
    payload: ScheduleRequest,
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """Set this profile's backup schedule."""
    if payload.frequency not in VALID_FREQUENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"frequency must be one of {', '.join(VALID_FREQUENCIES)}",
        )

    schedule = await _get_or_create_schedule(session.profile_id, master_db)
    schedule.frequency = payload.frequency
    schedule.retention_days = payload.retention_days
    # "off" and "enabled" would be contradictory; treat frequency as the truth.
    schedule.enabled = payload.enabled and payload.frequency != "off"

    await create_audit_log(
        db=master_db,
        event_type="backup.schedule",
        action="Updated backup schedule",
        profile_id=session.profile_id,
        entity_type="backup",
        entity_id="schedule",
        details={"status": schedule.frequency, "verified": schedule.enabled},
    )
    await master_db.commit()

    return ScheduleResponse(
        enabled=schedule.enabled,
        frequency=schedule.frequency,
        retention_days=schedule.retention_days,
        last_run_at=schedule.last_run_at.isoformat() + "Z" if schedule.last_run_at else None,
        last_result=schedule.last_result,
        last_file_count=schedule.last_file_count,
    )
