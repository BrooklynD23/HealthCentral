"""Scheduled backups (BKUP-UX-001).

**The constraint that shapes this whole module:** a background task cannot open
a locked profile vault. The encryption key only exists in memory while the user
is signed in, so a scheduled backup can only actually run for a profile that is
currently unlocked.

That is why the schedule lives in the master database (see
`models/backup_schedule.py`) and why "due but the vault is locked" is a
first-class outcome recorded as `skipped_locked` rather than being papered over.
Telling a patient their data was backed up when it was not is the one failure
mode this feature must never have.

Missed runs are caught up **once** on the next opportunity, not replayed per
missed interval — a laptop closed for a fortnight should produce one backup,
not fourteen.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import select

from core.config import settings
from core.time import utcnow

logger = logging.getLogger(__name__)

# How often the loop wakes to look for due schedules. Backups are a daily/weekly
# concern, so checking every 15 minutes is ample and stays cheap.
CHECK_INTERVAL_SECONDS = 15 * 60

_FREQUENCY_INTERVALS: dict[str, timedelta] = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
}


@dataclass(frozen=True)
class ScheduleRunOutcome:
    """What happened for one profile on one pass."""

    profile_id: str
    result: str  # one of models.backup_schedule.BACKUP_RESULTS
    file_count: int = 0


def is_due(frequency: str, last_run_at: Optional[datetime], now: datetime) -> bool:
    """Whether a backup is due.

    A schedule that has never run is due immediately — otherwise turning
    backups on would appear to do nothing for a day.
    """
    interval = _FREQUENCY_INTERVALS.get(frequency)
    if interval is None:  # "off" or an unknown value
        return False
    if last_run_at is None:
        return True
    reference = last_run_at
    if reference.tzinfo is None and now.tzinfo is not None:
        reference = reference.replace(tzinfo=now.tzinfo)
    return (now - reference) >= interval


def _is_profile_unlocked(profile_id: str) -> bool:
    """Whether this profile's encrypted DB is currently open.

    Deliberately asks the live connection manager rather than a database flag:
    the manager is the only thing that actually knows whether the key is in
    memory, and a stale flag would make us claim a backup we could not take.
    """
    try:
        from core.profile_database import get_profile_db_manager

        manager = get_profile_db_manager()
        checker = getattr(manager, "is_profile_open", None)
        if callable(checker):
            return bool(checker(profile_id))
        # Fall back to inspecting the manager's open-connection registry.
        connections = getattr(manager, "_connections", None)
        if isinstance(connections, dict):
            return profile_id in connections
    except Exception:  # pragma: no cover - never let a probe break the loop
        logger.debug("Could not determine unlock state for a profile", exc_info=True)
    return False


async def run_due_backups(now: Optional[datetime] = None) -> list[ScheduleRunOutcome]:
    """Run one pass: back up every profile whose schedule is due and unlocked.

    Returns an outcome per profile it considered, so the caller (and tests) can
    see what was skipped and why.
    """
    now = now or utcnow()
    outcomes: list[ScheduleRunOutcome] = []

    from core.database import async_session_maker
    from models import BackupSchedule
    from scripts import backup as backup_script

    async with async_session_maker() as db:
        result = await db.execute(
            select(BackupSchedule).where(BackupSchedule.enabled.is_(True))
        )
        schedules = list(result.scalars().all())

        for schedule in schedules:
            if not is_due(schedule.frequency, schedule.last_run_at, now):
                continue

            if not _is_profile_unlocked(schedule.profile_id):
                # Due, but we genuinely cannot read the vault. Record it as
                # such; the UI surfaces "a backup is due — unlock to run it".
                schedule.last_result = "skipped_locked"
                outcomes.append(
                    ScheduleRunOutcome(schedule.profile_id, "skipped_locked")
                )
                continue

            try:
                data_dir = Path(settings.app_data_path)
                backup_dir = data_dir / "backups" / schedule.profile_id
                backup_dir.mkdir(parents=True, exist_ok=True)

                outcome = backup_script.backup(
                    data_dir=data_dir,
                    backup_dir=backup_dir,
                    profile_id=schedule.profile_id,
                )
                schedule.last_run_at = now
                schedule.last_result = "success" if outcome.success else "failed"
                schedule.last_file_count = outcome.files_backed_up
                outcomes.append(
                    ScheduleRunOutcome(
                        schedule.profile_id,
                        schedule.last_result,
                        outcome.files_backed_up,
                    )
                )

                if outcome.success and schedule.retention_days > 0:
                    backup_script.prune(backup_dir, schedule.retention_days)
            except Exception:
                # A failure for one profile must not stop the others.
                logger.exception("Scheduled backup failed for a profile")
                schedule.last_run_at = now
                schedule.last_result = "failed"
                outcomes.append(ScheduleRunOutcome(schedule.profile_id, "failed"))

        await db.commit()

    return outcomes


class BackupScheduler:
    """Periodic backup runner, modelled on `notification_scheduler`."""

    def __init__(self, check_interval_seconds: int = CHECK_INTERVAL_SECONDS) -> None:
        self._interval = check_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            logger.warning("Backup scheduler already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Backup scheduler started")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Backup scheduler stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await run_due_backups()
            except asyncio.CancelledError:
                raise
            except Exception:
                # The loop outliving a bad pass matters more than the pass.
                logger.exception("Backup scheduler pass failed")
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                raise


_scheduler: Optional[BackupScheduler] = None


def get_backup_scheduler() -> BackupScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackupScheduler()
    return _scheduler


async def start_backup_scheduler() -> BackupScheduler:
    scheduler = get_backup_scheduler()
    await scheduler.start()
    return scheduler


async def stop_backup_scheduler() -> None:
    scheduler = get_backup_scheduler()
    await scheduler.stop()
