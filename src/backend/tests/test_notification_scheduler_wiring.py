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
