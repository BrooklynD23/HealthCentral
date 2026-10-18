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
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add backend to path for imports (same convention as test_phase3_notifications.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import modules.notification_scheduler as ns_module
from core.profile_database import ProfileDatabaseBase
from core.time import to_local, utcnow
from models import (
    AdherencePattern,
    DoseTaken,
    Medication,
    MedicationSchedule,
    ReminderLog,
    UserModelSettings,
)
from modules.notification_scheduler import (
    NotificationScheduler,
    ProfileVaultLockedError,
    profile_session_factory,
)
from modules.platform_notifications import MockProvider, NotificationService


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
    from fastapi import FastAPI

    import main as main_module

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
        now = utcnow()
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


def _seed_due_medication(db, profile_id, med_id, sched_id, tz="UTC"):
    """Insert an active medication with a schedule due right now (in tz)."""
    now = to_local(utcnow(), tz)
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
            target_time=now.time().replace(tzinfo=None),
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
    from sqlalchemy import text

    import core.auth as auth_module
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


def test_hc_streak_tz_004_scheduler_passes_profile_zone_to_calculate_streak(tmp_path, monkeypatch):
    """One scheduler pass awaits calculate_streak with the profile's zone."""
    provider = MockProvider()
    scheduler = NotificationScheduler(
        notification_service=NotificationService(providers=[provider])
    )
    spy = AsyncMock(return_value=SimpleNamespace(current_streak=0, longest_streak=0))
    monkeypatch.setattr(
        ns_module, "get_pattern_learner", lambda: SimpleNamespace(calculate_streak=spy)
    )

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'vault.db'}")
    profile_id = "profile-1"

    async def scenario():
        async with engine.begin() as conn:
            await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
        session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_maker() as db:
            _seed_due_medication(
                db, profile_id, str(uuid.uuid4()), str(uuid.uuid4()),
                tz="America/Los_Angeles",
            )
            db.add(UserModelSettings(profile_id=profile_id, timezone="America/Los_Angeles"))
            await db.commit()

        async def factory():
            return session_maker()

        scheduler._profile_sessions[profile_id] = factory
        await scheduler._check_all_schedules()

    run(scenario())

    assert spy.await_count == 1
    assert spy.await_args.kwargs["tz_name"] == "America/Los_Angeles"


# ---------------------------------------------------------------------------
# HC-SCHED-TZ — scheduler reads the profile-local clock (D-2)
# ---------------------------------------------------------------------------

from datetime import date, datetime, time  # noqa: E402

import modules.adherence_patterns as _ap_module  # noqa: E402

_TZ_PID = "profile-tz"
_LA = "America/Los_Angeles"


async def _tz_setup(tmp_path, monkeypatch, tz, now, stub=True):
    """Tmp vault + scheduler with frozen UTC clock and a profile time zone."""
    monkeypatch.setattr(ns_module, "utcnow", lambda: now)
    monkeypatch.setattr(_ap_module, "utcnow", lambda: now)
    if stub:
        _stub_pattern_learner(monkeypatch)
    provider = MockProvider()
    scheduler = NotificationScheduler(
        notification_service=NotificationService(providers=[provider])
    )
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'vault.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as db:
        db.add(UserModelSettings(profile_id=_TZ_PID, timezone=tz))
        await db.commit()

    async def factory():
        return sm()

    scheduler._profile_sessions[_TZ_PID] = factory
    return scheduler, provider, sm


async def _tz_add_schedule(
    sm, target, *, med_id=None, days=None, active=True, window=None, marker=None
):
    """Add a medication (or reuse med_id) plus one schedule; returns ids."""
    med_id = med_id or str(uuid.uuid4())
    sched_id = str(uuid.uuid4())
    async with sm() as db:
        if not (await db.execute(select(Medication).where(Medication.id == med_id))).first():
            db.add(
                Medication(
                    id=med_id, profile_id=_TZ_PID, name="Metformin",
                    is_active=True, reminder_enabled=True,
                )
            )
            await db.flush()
        db.add(
            MedicationSchedule(
                id=sched_id, medication_id=med_id, schedule_label="morning",
                target_time=target, is_active=active, reminder_offset_minutes=15,
                days_of_week_json=None if days is None else str(days),
                adaptive_window_start=window[0] if window else None,
                adaptive_window_end=window[1] if window else None,
                **({"adaptive_window_tz": marker} if marker else {}),
            )
        )
        await db.commit()
    return med_id, sched_id


def _sent_after(tmp_path, monkeypatch, tz, now, target, **kw):
    async def scenario():
        scheduler, provider, sm = await _tz_setup(tmp_path, monkeypatch, tz, now)
        await _tz_add_schedule(sm, target, **kw)
        await scheduler._check_all_schedules()
        return len(provider.sent_notifications)

    return run(scenario())


@pytest.mark.parametrize(
    "now,expected",
    [(datetime(2026, 1, 5, 16, 0), 1), (datetime(2026, 1, 5, 8, 0), 0)],
)
def test_hc_sched_tz_001_reminder_fires_at_local_target(
    tmp_path, monkeypatch, now, expected
):
    """08:00 target in LA fires at 16:00Z (08:00 PST), not at 08:00Z."""
    assert _sent_after(tmp_path, monkeypatch, _LA, now, time(8, 0)) == expected


def test_hc_sched_tz_002_dose_found_inside_local_day(tmp_path, monkeypatch):
    """A 20:00 PST dose (04:00Z next day) belongs to the local day."""
    now = datetime(2026, 1, 6, 4, 10)  # 20:10 PST Jan 5

    async def scenario():
        scheduler, provider, sm = await _tz_setup(tmp_path, monkeypatch, _LA, now)
        med_id, sched_id = await _tz_add_schedule(sm, time(20, 15))
        async with sm() as db:
            db.add(DoseTaken(
                id=str(uuid.uuid4()), medication_id=med_id, schedule_id=sched_id,
                taken_at=datetime(2026, 1, 6, 4, 0), log_method="manual",
                was_skipped=False,
            ))
            await db.commit()
        await scheduler._check_all_schedules()
        async with sm() as db:
            taken = await scheduler._check_dose_taken_today(
                med_id, sched_id, date(2026, 1, 5), _LA, db
            )
        return len(provider.sent_notifications), taken

    sent, taken = run(scenario())
    assert sent == 0
    assert taken is True


def test_hc_sched_tz_003_yesterday_local_reminders_do_not_count(tmp_path, monkeypatch):
    """3 logs at 23:30 PST yesterday (07:30Z today) are outside today's cap."""
    now = datetime(2026, 1, 6, 16, 0)  # 08:00 PST Jan 6

    async def scenario():
        scheduler, provider, sm = await _tz_setup(tmp_path, monkeypatch, _LA, now)
        med_id, sched_id = await _tz_add_schedule(sm, time(8, 0))
        async with sm() as db:
            for _ in range(3):
                db.add(ReminderLog(
                    id=str(uuid.uuid4()), profile_id=_TZ_PID, medication_id=med_id,
                    schedule_id=sched_id, reminder_type="initial",
                    message_tone="friendly", message="x",
                    sent_at=datetime(2026, 1, 6, 7, 30), delivery_method="notification",
                ))
            await db.commit()
            counted = await scheduler._count_reminders_today(
                med_id, sched_id, date(2026, 1, 6), _LA, db
            )
        await scheduler._check_all_schedules()
        return counted, len(provider.sent_notifications)

    counted, sent = run(scenario())
    assert counted == 0
    assert sent == 1


def test_hc_sched_tz_004_weekday_is_local(tmp_path, monkeypatch):
    """Friday 20:00 PST is Saturday 04:00Z; days_of_week [4] still applies."""
    now = datetime(2026, 1, 10, 4, 0)
    assert _sent_after(tmp_path, monkeypatch, _LA, now, time(20, 0), days=[4]) == 1


def _raw_insert(con, table, **vals):
    """Insert a row, filling any other NOT NULL column without a default."""
    cols = con.execute(f"PRAGMA table_info({table})").fetchall()
    for _cid, name, ctype, notnull, default, _pk in cols:
        if name not in vals and notnull and default is None:
            vals[name] = 0 if "INT" in ctype.upper() or "BOOL" in ctype.upper() else "x"
    names = ", ".join(vals)
    marks = ", ".join("?" for _ in vals)
    con.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(vals.values()))


def test_hc_sched_tz_005_migration_clears_windows_and_round_trips(tmp_path, monkeypatch):
    """Migration found by slug: stale UTC windows cleared, marker column added,
    downgrade clears local windows again and drops the column."""
    import re
    import sqlite3

    from alembic import command
    from alembic.script import ScriptDirectory

    import core.sqlcipher_driver as driver
    from core import migrations
    from core.config import settings

    monkeypatch.setattr(settings, "database_encryption_required", False)
    monkeypatch.setattr(driver, "SQLCIPHER_AVAILABLE", False)  # plain sqlite vault

    versions = Path(__file__).parent.parent / "migrations/profile/versions"
    files = list(versions.glob("*_adaptive_windows_local.py"))
    assert len(files) == 1
    text = files[0].read_text()
    down = re.search(r'^down_revision[^=]*=\s*"([^"]+)"', text, re.M).group(1)

    vault, key = tmp_path / "vault.db", b"0" * 32
    migrations.run_profile_migration(vault, key)
    config = migrations._get_alembic_config("profile")
    config.attributes["vault_path"] = vault
    config.attributes["encryption_key"] = key
    head = ScriptDirectory.from_config(config).get_current_head()

    command.downgrade(config, down)
    con = sqlite3.connect(vault)
    _raw_insert(con, "medications", id="m1", profile_id="p", name="Metformin")
    _raw_insert(
        con, "medication_schedules", id="s1", medication_id="m1",
        schedule_label="morning", target_time="08:00:00",
        adaptive_window_start="16:00:00", adaptive_window_end="17:00:00",
    )
    con.commit()
    con.close()

    def row():
        c = sqlite3.connect(vault)
        try:
            cols = [r[1] for r in c.execute("PRAGMA table_info(medication_schedules)")]
            q = "SELECT target_time, adaptive_window_start, adaptive_window_end"
            q += ", adaptive_window_tz" if "adaptive_window_tz" in cols else ""
            return cols, c.execute(q + " FROM medication_schedules").fetchone()
        finally:
            c.close()

    command.upgrade(config, "head")
    assert migrations.get_profile_current_revision(vault, key) == head
    cols, r = row()
    assert "adaptive_window_tz" in cols
    assert r == ("08:00:00", None, None, None)

    con = sqlite3.connect(vault)
    con.execute(
        "UPDATE medication_schedules SET adaptive_window_start='08:00:00',"
        " adaptive_window_end='08:30:00', adaptive_window_tz='America/Los_Angeles'"
    )
    con.commit()
    con.close()
    command.downgrade(config, down)
    cols, r = row()
    assert "adaptive_window_tz" not in cols
    assert r == ("08:00:00", None, None)

    command.upgrade(config, "head")
    assert migrations.get_profile_current_revision(vault, key) == head


# ---------------------------------------------------------------------------
# HC-SCHED-TZ rev 2 — automatic re-learn of unmarked adaptive windows (D-2)
# ---------------------------------------------------------------------------

_RELEARN_NOW = datetime(2026, 1, 15, 16, 0)  # 08:00 PST


async def _tz_add_doses(sm, med_id, sched_id, n=10):
    """n daily doses at 08:00 PST (16:00Z) ending the day before _RELEARN_NOW."""
    async with sm() as db:
        for d in range(15 - n, 15):
            db.add(DoseTaken(
                id=str(uuid.uuid4()), medication_id=med_id, schedule_id=sched_id,
                taken_at=datetime(2026, 1, d, 16, 0), log_method="manual",
                was_skipped=False,
            ))
        await db.commit()


async def _tz_schedule_row(sm, sched_id):
    async with sm() as db:
        return (
            await db.execute(select(MedicationSchedule).where(MedicationSchedule.id == sched_id))
        ).scalar_one()


def _spy_relearn(monkeypatch):
    """Wrap the real learner's relearn method; record awaits and results."""
    from modules.adherence_patterns import get_pattern_learner

    learner = get_pattern_learner()
    orig = learner.relearn_unmarked_windows
    results: list = []

    async def wrapped(*args, **kwargs):
        results.append(await orig(*args, **kwargs))
        return results[-1]

    monkeypatch.setattr(learner, "relearn_unmarked_windows", wrapped)
    return results


async def _unlock_cycle(scheduler):
    factory = scheduler._profile_sessions[_TZ_PID]
    await scheduler.unregister_profile_session_and_wait(_TZ_PID)
    scheduler.register_profile_session(_TZ_PID, factory)


def test_hc_sched_tz_006_pass_relearns_window_in_local_frame(tmp_path, monkeypatch):
    async def scenario():
        scheduler, _, sm = await _tz_setup(tmp_path, monkeypatch, _LA, _RELEARN_NOW, stub=False)
        med_id, sched_id = await _tz_add_schedule(sm, time(8, 0))
        await _tz_add_doses(sm, med_id, sched_id)
        await scheduler._check_all_schedules()
        return await _tz_schedule_row(sm, sched_id)

    row = run(scenario())
    assert row.adaptive_window_start <= time(8, 0) <= row.adaptive_window_end
    assert row.adaptive_window_tz == _LA


def test_hc_sched_tz_007_relearn_runs_once_per_unlock(tmp_path, monkeypatch):
    async def scenario():
        scheduler, _, sm = await _tz_setup(tmp_path, monkeypatch, _LA, _RELEARN_NOW, stub=False)
        results = _spy_relearn(monkeypatch)
        med_id, sched_id = await _tz_add_schedule(sm, time(8, 0))
        await _tz_add_doses(sm, med_id, sched_id)
        await scheduler._check_all_schedules()
        await scheduler._check_all_schedules()
        after_two = list(results)
        await _unlock_cycle(scheduler)
        await scheduler._check_all_schedules()
        return after_two, results

    after_two, results = run(scenario())
    assert after_two == [1]
    assert results == [1, 0]


def test_hc_sched_tz_008_relearn_failure_is_fail_soft_and_retried_on_unlock(
    tmp_path, monkeypatch, caplog
):
    from modules.adherence_patterns import get_pattern_learner

    async def scenario():
        scheduler, provider, sm = await _tz_setup(
            tmp_path, monkeypatch, _LA, _RELEARN_NOW, stub=False
        )
        learner = get_pattern_learner()
        boom = AsyncMock(side_effect=RuntimeError("Metformin"))
        monkeypatch.setattr(learner, "relearn_unmarked_windows", boom)
        med_id, sched_id = await _tz_add_schedule(sm, time(8, 0))
        await _tz_add_doses(sm, med_id, sched_id)
        await scheduler._check_all_schedules()
        sent_after_fail = len(provider.sent_notifications)
        failed_row = await _tz_schedule_row(sm, sched_id)
        await scheduler._check_all_schedules()
        awaits_same_session = boom.await_count
        monkeypatch.undo()  # real learner again (and real clock: re-freeze below)
        monkeypatch.setattr(ns_module, "utcnow", lambda: _RELEARN_NOW)
        monkeypatch.setattr(_ap_module, "utcnow", lambda: _RELEARN_NOW)
        await _unlock_cycle(scheduler)
        await scheduler._check_all_schedules()
        return (
            sent_after_fail, failed_row.adaptive_window_tz, awaits_same_session,
            await _tz_schedule_row(sm, sched_id),
        )

    caplog.set_level(logging.WARNING)
    sent, marker, awaits, healed = run(scenario())
    assert sent == 1  # reminder still fires on target_time +/- tolerance
    assert marker is None
    assert awaits == 1
    assert "Metformin" not in caplog.text
    assert healed.adaptive_window_tz == _LA


def test_hc_sched_tz_009_inactive_and_low_sample_schedules_are_marked(tmp_path, monkeypatch):
    async def scenario():
        scheduler, _, sm = await _tz_setup(tmp_path, monkeypatch, _LA, _RELEARN_NOW, stub=False)
        med_id, inactive_id = await _tz_add_schedule(sm, time(8, 0), active=False)
        _, few_id = await _tz_add_schedule(sm, time(9, 0), med_id=med_id)
        await _tz_add_doses(sm, med_id, few_id, n=3)  # < MIN_SAMPLES_FOR_PATTERN
        await scheduler._check_all_schedules()
        return await _tz_schedule_row(sm, inactive_id), await _tz_schedule_row(sm, few_id)

    for row in run(scenario()):
        assert row.adaptive_window_tz == _LA
        assert row.adaptive_window_start is None
        assert row.adaptive_window_end is None


def test_hc_sched_tz_010_concurrent_passes_relearn_once(tmp_path, monkeypatch):
    async def scenario():
        scheduler, _, sm = await _tz_setup(tmp_path, monkeypatch, _LA, _RELEARN_NOW, stub=False)
        results = _spy_relearn(monkeypatch)
        med_id, sched_id = await _tz_add_schedule(sm, time(8, 0))
        await _tz_add_doses(sm, med_id, sched_id)
        await asyncio.gather(scheduler._check_all_schedules(), scheduler._check_all_schedules())
        return results

    assert run(scenario()) == [1]


def test_hc_sched_tz_011_marked_sibling_schedule_is_left_alone(tmp_path, monkeypatch):
    async def scenario():
        scheduler, _, sm = await _tz_setup(tmp_path, monkeypatch, _LA, _RELEARN_NOW, stub=False)
        med_id, a_id = await _tz_add_schedule(
            sm, time(16, 0), window=(time(16, 0), time(17, 0)), marker="UTC"
        )
        _, b_id = await _tz_add_schedule(sm, time(8, 0), med_id=med_id)
        await _tz_add_doses(sm, med_id, b_id)
        await scheduler._check_all_schedules()
        return await _tz_schedule_row(sm, a_id), await _tz_schedule_row(sm, b_id)

    a, b = run(scenario())
    assert (a.adaptive_window_start, a.adaptive_window_end) == (time(16, 0), time(17, 0))
    assert a.adaptive_window_tz == "UTC"
    assert b.adaptive_window_start <= time(8, 0) <= b.adaptive_window_end
    assert b.adaptive_window_tz == _LA
