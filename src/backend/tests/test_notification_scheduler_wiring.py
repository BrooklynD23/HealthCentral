"""Wiring tests for the notification scheduler (HC-NSW-*).

The scheduler existed fully built but never started and never received
profile sessions (audit 2026-09-25 §11.2). These tests pin the wiring:
lifespan start/stop, register-on-unlock / unregister-on-lock, skipped_locked
accounting, end-to-end delivery, and the PHI boundary.
"""

import asyncio
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add backend to path for imports (same convention as test_phase3_notifications.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import modules.notification_scheduler as ns_module
from modules.notification_scheduler import (
    NotificationScheduler,
    ProfileVaultLockedError,
    profile_session_factory,
)
from modules.platform_notifications import MockProvider, NotificationService
from core.profile_database import ProfileDatabaseBase
from models import (
    AdherencePattern,
    DoseTaken,
    Medication,
    MedicationSchedule,
    ReminderLog,
)


def run(coro):
    """Drive a coroutine on a fresh loop (repo's existing test style — no
    pytest-asyncio dependency)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_scheduler() -> NotificationScheduler:
    """Scheduler wired to a recording mock provider."""
    provider = MockProvider()
    service = NotificationService(providers=[provider])
    scheduler = NotificationScheduler(notification_service=service)
    return scheduler


def test_hc_nsw_001_register_on_vault_open(monkeypatch):
    """open_profile_database_on_login registers the profile's session factory."""
    scheduler = make_scheduler()
    monkeypatch.setattr(ns_module, "_notification_scheduler", scheduler)

    manager = AsyncMock()
    manager.open_profile_database = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr("core.auth.get_profile_db_manager", lambda: manager)

    from core.auth import open_profile_database_on_login

    run(open_profile_database_on_login("profile-1", "pw"))

    assert "profile-1" in scheduler._profile_sessions


def test_hc_nsw_002_unregister_on_vault_close(monkeypatch):
    """close_profile_database_on_logout unregisters before closing."""
    scheduler = make_scheduler()
    monkeypatch.setattr(ns_module, "_notification_scheduler", scheduler)
    scheduler._profile_sessions["profile-1"] = AsyncMock()

    manager = AsyncMock()
    manager.close_profile_database = AsyncMock()
    monkeypatch.setattr("core.auth.get_profile_db_manager", lambda: manager)

    from core.auth import close_profile_database_on_logout

    run(close_profile_database_on_logout("profile-1"))

    assert "profile-1" not in scheduler._profile_sessions
    manager.close_profile_database.assert_awaited_once_with("profile-1")


def test_hc_nsw_003_factory_raises_when_vault_locked(monkeypatch):
    """A registered factory whose connection disappeared raises
    ProfileVaultLockedError, which Task 2's loop counts as skipped_locked."""
    manager = SimpleNamespace(get_connection=lambda pid: None)
    monkeypatch.setattr(
        "core.profile_database.get_profile_db_manager", lambda: manager
    )

    factory = profile_session_factory("profile-locked")

    with pytest.raises(ProfileVaultLockedError):
        run(factory())


def test_hc_nsw_003b_factory_yields_live_session(monkeypatch):
    """The factory returns the connection's session context manager."""

    @asynccontextmanager
    async def fake_session():
        yield AsyncMock()

    conn = SimpleNamespace(get_session=fake_session)
    manager = SimpleNamespace(get_connection=lambda pid: conn)
    monkeypatch.setattr(
        "core.profile_database.get_profile_db_manager", lambda: manager
    )

    factory = profile_session_factory("profile-1")

    async def go():
        cm = await factory()
        async with cm as db:
            return db

    assert run(go()) is not None


def test_hc_nsw_004_pass_records_skipped_locked():
    """A factory whose vault locked mid-session is counted, not error-logged."""
    scheduler = make_scheduler()

    async def locked_factory():
        raise ProfileVaultLockedError("profile-locked vault is locked")

    scheduler._profile_sessions["profile-locked"] = locked_factory

    run(scheduler._check_all_schedules())

    assert scheduler._last_pass_results == {"profile-locked": "skipped_locked"}
    assert scheduler.last_pass_skipped_locked == 1


def test_hc_nsw_005_status_endpoint_reports_skipped_locked(monkeypatch):
    """GET /notifications/scheduler/status exposes skipped_locked over HTTP."""
    from api.notifications import router as notifications_router
    from tests.support.routes import route_client

    scheduler = make_scheduler()
    scheduler._last_pass_results = {
        "a": "skipped_locked",
        "b": "checked",
        "c": "skipped_locked",
    }
    monkeypatch.setattr(ns_module, "_notification_scheduler", scheduler)

    with route_client(notifications_router, "/notifications") as client:
        resp = client.get("/notifications/scheduler/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "stopped"
    assert body["skipped_locked"] == 2
    assert body["registered_profiles"] == 0


def test_hc_nsw_006_lifespan_starts_and_stops_scheduler(monkeypatch):
    """main.lifespan starts the notification scheduler on boot and stops it
    on shutdown — same fail-soft contract as the backup scheduler."""
    import main as main_module
    from fastapi import FastAPI

    started = AsyncMock()
    stopped = AsyncMock()
    # Imported lazily inside lifespan — patch at the source modules.
    monkeypatch.setattr(
        ns_module, "start_notification_scheduler", started
    )
    monkeypatch.setattr(
        ns_module, "stop_notification_scheduler", stopped
    )
    monkeypatch.setattr(
        "modules.backup_scheduler.start_backup_scheduler", AsyncMock()
    )
    monkeypatch.setattr(
        "modules.backup_scheduler.stop_backup_scheduler", AsyncMock()
    )
    monkeypatch.setattr(main_module, "init_database", AsyncMock())
    monkeypatch.setattr(main_module, "close_database", AsyncMock())
    monkeypatch.setattr(
        main_module, "run_master_migrations_async", AsyncMock()
    )
    monkeypatch.setattr(
        "core.db_migration.migrate_master_db_filename", MagicMock()
    )
    monkeypatch.setattr(
        "scripts.seed_knowledge_base.seed_all", AsyncMock(return_value={})
    )
    # Replace the settings object wholesale — instance may be immutable.
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            validate_startup=lambda: [], app_data_path="/tmp/hc-nsw-test"
        ),
    )

    async def drive():
        async with main_module.lifespan(FastAPI()):
            started.assert_awaited_once()
            stopped.assert_not_awaited()

    run(drive())

    started.assert_awaited_once()
    stopped.assert_awaited_once()


def test_hc_nsw_009_no_phi_in_logs_or_master_schema(tmp_path, monkeypatch, caplog):
    """The send path must not write the medication name to logs, and the
    reminder tables must live only on the per-profile (encrypted) base."""
    # Model-level isolation invariant — reminder data never enters master.
    for model in (
        Medication,
        MedicationSchedule,
        DoseTaken,
        AdherencePattern,
        ReminderLog,
    ):
        assert issubclass(model, ProfileDatabaseBase)

    provider = MockProvider()
    scheduler = NotificationScheduler(
        notification_service=NotificationService(providers=[provider])
    )
    monkeypatch.setattr(
        ns_module,
        "get_pattern_learner",
        lambda: SimpleNamespace(
            calculate_streak=AsyncMock(
                return_value=SimpleNamespace(current_streak=0, longest_streak=0)
            )
        ),
    )

    db_path = tmp_path / "vault.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    profile_id = "profile-1"
    med_id = str(uuid.uuid4())
    sched_id = str(uuid.uuid4())

    async def scenario():
        async with engine.begin() as conn:
            await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
        session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        now = datetime.utcnow()
        async with session_maker() as db:
            db.add(
                Medication(
                    id=med_id,
                    profile_id=profile_id,
                    name="Metformin",
                    is_active=True,
                    reminder_enabled=True,
                )
            )
            db.add(
                MedicationSchedule(
                    id=sched_id,
                    medication_id=med_id,
                    schedule_label="morning",
                    target_time=now.time(),
                    is_active=True,
                    reminder_offset_minutes=15,
                )
            )
            await db.commit()

        async def factory():
            return session_maker()

        scheduler._profile_sessions[profile_id] = factory
        await scheduler._check_all_schedules()

    caplog.set_level(logging.INFO)
    run(scenario())

    assert len(provider.sent_notifications) == 1
    assert "Metformin" not in caplog.text


def _seed_due_medication(db, profile_id, med_id, sched_id):
    """Insert an active medication with a schedule due right now."""
    now = datetime.utcnow()
    db.add(
        Medication(
            id=med_id,
            profile_id=profile_id,
            name="Metformin",
            is_active=True,
            reminder_enabled=True,
        )
    )
    db.add(
        MedicationSchedule(
            id=sched_id,
            medication_id=med_id,
            schedule_label="morning",
            target_time=now.time(),
            is_active=True,
            reminder_offset_minutes=15,
        )
    )


def _stub_pattern_learner(monkeypatch):
    """Isolate the scheduler from adherence_patterns internals."""
    monkeypatch.setattr(
        ns_module,
        "get_pattern_learner",
        lambda: SimpleNamespace(
            calculate_streak=AsyncMock(
                return_value=SimpleNamespace(current_streak=0, longest_streak=0)
            )
        ),
    )


def test_hc_nsw_007_fires_reminder_for_unlocked_profile(tmp_path, monkeypatch):
    """A due schedule on a registered (unlocked) profile produces one toast
    and one ReminderLog row in the profile vault."""
    provider = MockProvider()
    scheduler = NotificationScheduler(
        notification_service=NotificationService(providers=[provider])
    )
    _stub_pattern_learner(monkeypatch)

    db_path = tmp_path / "vault.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    profile_id = "profile-1"
    med_id = str(uuid.uuid4())
    sched_id = str(uuid.uuid4())

    async def scenario():
        async with engine.begin() as conn:
            await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
        session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_maker() as db:
            _seed_due_medication(db, profile_id, med_id, sched_id)
            await db.commit()

        async def factory():
            return session_maker()

        scheduler._profile_sessions[profile_id] = factory
        await scheduler._check_all_schedules()

        async with session_maker() as db:
            rows = (
                (await db.execute(select(ReminderLog))).scalars().all()
            )
        return rows

    rows = run(scenario())

    assert len(provider.sent_notifications) == 1
    payload = provider.sent_notifications[0]
    assert payload.medication_id == med_id
    assert "Metformin" in payload.body or "Metformin" in payload.title
    assert len(rows) == 1
    from modules.message_generator import ReminderPriority

    assert rows[0].reminder_type == ReminderPriority.INITIAL.value
    assert rows[0].profile_id == profile_id
    assert scheduler._last_pass_results == {profile_id: "checked"}


def test_hc_nsw_008_second_pass_does_not_resend(tmp_path, monkeypatch):
    """Dedup/idempotency: ReminderLog rows already written today suppress a
    duplicate initial reminder on the next pass."""
    provider = MockProvider()
    scheduler = NotificationScheduler(
        notification_service=NotificationService(providers=[provider])
    )
    _stub_pattern_learner(monkeypatch)

    db_path = tmp_path / "vault.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    profile_id = "profile-1"

    async def scenario():
        async with engine.begin() as conn:
            await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
        session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_maker() as db:
            _seed_due_medication(
                db, profile_id, str(uuid.uuid4()), str(uuid.uuid4())
            )
            await db.commit()

        async def factory():
            return session_maker()

        scheduler._profile_sessions[profile_id] = factory
        await scheduler._check_all_schedules()
        await scheduler._check_all_schedules()

        async with session_maker() as db:
            count = len(
                (await db.execute(select(ReminderLog))).scalars().all()
            )
        return count

    count = run(scenario())

    assert count == 1
    assert len(provider.sent_notifications) == 1
    assert scheduler._notifications_sent_this_hour == 1


# ---------------------------------------------------------------------------
# HC-NSW-010 — close waits for an in-flight pass (owner gate P2-INFLIGHT)
# ---------------------------------------------------------------------------

_NSW010_PASSWORD = "CorrectHorse1"


def _nsw010_make_vault(root: Path, profile_id: str) -> Path:
    """Seal a generated key into vaults/<pid>/ (real key files, no mocks)."""
    from core.security import generate_encryption_key, seal_key_with_dpapi

    vault = root / "vaults" / profile_id
    vault.mkdir(parents=True)
    sealed, method = seal_key_with_dpapi(
        generate_encryption_key(),
        fallback_password=_NSW010_PASSWORD,
        force_password=True,
    )
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)
    return vault


def test_hc_nsw_010_close_waits_for_inflight_pass_and_vault_not_recreated(
    tmp_path, monkeypatch
):
    """A pass in flight during lock must finish before the engine is disposed.

    Otherwise its next query checks out a fresh connection, the engine's
    `connect` listener re-runs PRAGMA key, and an erased vault file is
    recreated.
    """
    import core.auth as auth_module
    from sqlalchemy import text
    from core.config import settings
    from core.profile_database import get_profile_db_manager

    monkeypatch.setattr(
        type(settings), "app_data_path", property(lambda self: tmp_path)
    )
    pid = str(uuid.uuid4())
    vault_file = _nsw010_make_vault(tmp_path, pid) / "vault.db"

    scheduler = make_scheduler()
    monkeypatch.setattr(ns_module, "_notification_scheduler", scheduler)

    in_pass = asyncio.Event()
    release = asyncio.Event()

    async def fake_check(profile_id, db):
        await db.execute(text("SELECT 1"))
        # End the txn so the connection returns to the pool, as a real pass
        # does between queries; the next query must check out a fresh one.
        await db.commit()
        in_pass.set()
        await release.wait()
        await db.execute(text("SELECT count(*) FROM sqlite_master"))
        await db.commit()

    monkeypatch.setattr(scheduler, "_check_profile_schedules", fake_check)

    async def scenario():
        await auth_module.open_profile_database_on_login(pid, _NSW010_PASSWORD)
        try:
            assert pid in scheduler._profile_sessions
            pass_task = asyncio.create_task(scheduler._check_all_schedules())
            await in_pass.wait()
            close_task = asyncio.create_task(
                auth_module.close_profile_database_on_logout(pid)
            )
            await asyncio.wait({close_task}, timeout=0.5)
            closed_early = close_task.done()
            if closed_early:
                # Simulated crypto-erase right after the (premature) close.
                vault_file.unlink(missing_ok=True)
            release.set()
            await pass_task
            await close_task
            if not closed_early:
                vault_file.unlink(missing_ok=True)
            return closed_early
        finally:
            release.set()
            await get_profile_db_manager().close_profile_database(pid)

    closed_early = run(scenario())

    assert not vault_file.exists(), "vault file recreated after close + erase"
    assert not closed_early, "close returned while a reminder pass was in flight"
    assert scheduler._last_pass_results == {pid: "checked"}
    assert pid not in scheduler._profile_sessions
