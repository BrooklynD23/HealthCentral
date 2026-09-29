# Notification Scheduler Wiring Implementation Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-04/F-06/N-01):** (1) The timestamp premise is corrected in Global Constraints: `core.time.utcnow` is naive UTC. (2) Task 6's broad `git add docs/` is replaced with explicit paths. (3) "Baseline 1245" is main@`40f590e`. This plan runs after plan 01, where the merged tree collected 1,291 on 2026-09-27. Use the count measured on the tree you start from, and report the delta from that number, not "1245 + ~10". (4) Interpreter: `python` is absent in this WSL environment and `/home/danny/venvs/healthcentral-backend` has no SQLAlchemy. Collection worked with the Windows interpreter (`/mnt/c/Python313/python.exe`, 3.13.7). CI uses 3.11 (`.github/workflows/ci.yml:39`). Owner approval for wiring is audit §21 Q1 ("Wire it up"), an agent-recorded owner answer; see the follow-up on provenance. (5) **N-05, ask-first gate:** Task 2 edits `src/backend/core/auth.py:361-419`. CLAUDE.md §1 says to ALWAYS ask before touching anything auth/encryption. "Wire it up" is not an explicit approval of auth-module edits, so get a specific owner yes for the two `core/auth.py` hooks before Task 2 (program decision D6). The Global Constraints list below did not name `core/auth.py`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start the medication-reminder scheduler (`modules/notification_scheduler.py`) at app boot and register/unregister per-profile vault sessions on unlock/lock, so reminders fire for unlocked profiles and are honestly recorded as `skipped_locked` for locked ones.

**Architecture:** The scheduler already exists and is unit-tested; it is simply never started and never given profile sessions. Wire it exactly like `modules/backup_scheduler.py`: start/stop in `main.py` lifespan (fail-soft), and hook session registration into the two existing vault-lifecycle choke points in `core/auth.py` — `open_profile_database_on_login` and `close_profile_database_on_logout` — so every unlock path (login, unlock, create, recover) registers and every close path (logout, lock, delete, restore) unregisters with two small diffs instead of eight call-site edits.

**Tech Stack:** Python 3.11+, FastAPI lifespan, asyncio, SQLAlchemy async (per-profile SQLCipher vaults via `ProfileDatabaseConnection.get_session()`), pytest + `tests/support/routes.py::route_client`.

## Global Constraints

- **Python 3.11+ only** — no 3.12+ syntax or APIs.
- **`core.time.utcnow` for any NEW timestamp code.** Do *not* convert the existing `datetime.utcnow()` calls in `notification_scheduler.py` — the naive timestamps it produces are compared against naive SQLite `DateTime` columns (`ReminderLog.sent_at`, `DoseTaken.taken_at`), and a naive/aware mix is the exact bug class the repo warns about. The wholesale `utcnow` migration is a separate workstream (audit §16 item 4; plan 05). ~~Verify `core.time.utcnow` returns tz-aware UTC before relying on it (`modules/backup_scheduler.py:66-67` normalizes `tzinfo` precisely because it is aware).~~ **Corrected 2026-09-27 ([review F-04](../review/2026-09-27-followup.md)):** `core.time.utcnow` returns **naive** UTC: `datetime.now(UTC).replace(tzinfo=None)` (`src/backend/core/time.py:9-11`, docstring "naive-UTC storage semantics"). `backup_scheduler.py:66-67` only adapts when a caller passes an *aware* `now`; its default `now` is `utcnow()` (`:100`), which is naive. So new scheduler code using `core.time.utcnow` compares naive-to-naive against the naive SQLite `DateTime` columns. Do **not** add timezone normalization on the aware premise.
- **Per-profile data isolation:** reminder/medication data lives in per-profile SQLCipher DBs (`models/medication.py` — every model there subclasses `ProfileDatabaseBase`). **Never** write reminder content, medication names, or dose schedules to the master DB (`get_db()`/`async_session_maker`) — master is unencrypted and medication names are PHI.
- **No PHI in logs or audit details.** Medication names must not appear in log lines; profile/medication/schedule uuids are the established norm in this codebase.
- **Safety-adjacent feature.** Medication reminders can nudge health behavior. Do NOT touch `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, or `core/security.py` — those need explicit owner sign-off per CLAUDE.md.
- **Audit logging** on every new route touching profile data. This plan adds **no new routes** (only extends an existing read-only status response), so no new audit rows are required.
- **Local-first:** no network calls anywhere in this plan. Delivery is the existing OS-toast provider chain (`modules/platform_notifications.py`).
- **Route tests go through HTTP** via `tests/support/routes.py::route_client` — never call route functions directly (recurring-failures: a `Depends(...)` break is invisible to direct calls).
- **Baseline:** `1245` backend tests collected (`pytest tests/ -p no:cacheprovider -q` from `src/backend/`). This plan adds tests — see Task 6 for updating the count in `CLAUDE.md` and `AGENT.md` in the same commit.
- **WSL caveat:** `find src/backend -name __pycache__ -type d -exec rm -rf {} +` before pytest; frontend toolchain (`tsc`, `vitest`) on Windows, not WSL.
- **Test IDs:** use `HC-NSW-NNN` (notification scheduler wiring), matching the repo's `HC-*` convention.
- **Commit style:** `feat(notifications):` / `fix(notifications):` / `docs:` — small, single-purpose commits on a feature branch.

## Design Decision: the locked-vault problem

A background task cannot open a locked profile vault — the DEK exists in memory only while the user is signed in (`core/profile_database.py:88-101`, `259-379`). Three options were evaluated:

- **(a) Session-scoped registration — CHOSEN.** Register a session factory with the scheduler when a vault opens; unregister when it closes. Reminders fire only while the profile is unlocked. Zero PHI outside the vault; a locked profile is simply not served, and the safety-net path (vault closes mid-pass) is recorded as `skipped_locked` — the same honesty contract as `backup_scheduler.run_due_backups` (`modules/backup_scheduler.py:117-124`). This is also exactly what `NotificationScheduler.register_profile_session` / `_profile_sessions` (`modules/notification_scheduler.py:131,148-166`) were built for.
- **(b) Master-DB due-reminder queue — REJECTED.** Persisting "profile X has medication Y due at 08:00" writes PHI (medication names, dosing cadence) into the unencrypted master DB — a direct violation of the per-profile isolation invariant. Even without names, a per-profile reminder schedule is health-adjacent metadata.
- **(c) Hybrid opaque-token queue — REJECTED.** `profile_id + due_at + opaque_token` still leaks reminder count and timing to unencrypted storage, adds a token lifecycle and a second writer, and the detail fetch still requires an unlocked vault — so it cannot actually deliver while locked. YAGNI plus complexity in a safety-adjacent path.

**Consequence to document honestly:** reminders are session-scoped — a locked profile gets no reminders until next unlock. For a local-first desktop app where the user is present, this is the correct trade-off; the alternative is weakening encryption at rest.

## File Structure

- Modify: `src/backend/modules/notification_scheduler.py` — add `ProfileVaultLockedError`, `profile_session_factory()`, per-pass outcome tracking (`_last_pass_results`, `last_pass_skipped_locked`), fix PHI in the send log line.
- Modify: `src/backend/core/auth.py:361-419` — register on `open_profile_database_on_login`, unregister on `close_profile_database_on_logout`.
- Modify: `src/backend/main.py:66-81` — lifespan start/stop, mirroring the backup-scheduler blocks exactly.
- Modify: `src/backend/api/notifications.py:132-139,490-511` — add `skipped_locked` to `SchedulerStatusResponse` and the status endpoint.
- Create: `src/backend/tests/test_notification_scheduler_wiring.py` — all HC-NSW tests.
- Modify: `docs/architecture/README.md:121-124` — the "deliberately not wired" claim becomes false after this lands; rewrite it.
- Modify: whichever `docs/features/` file claims the feature is implemented (locate by grep in Task 6) — it becomes true; verify wording says reminders fire only while unlocked.
- Modify: `docs/features/TASK_LIST.md` — Session Notes entry.
- Modify: `CLAUDE.md` and `AGENT.md` — collected-test baseline (1245 → actual).
- Read: `docs/agentic/recurring-failures.md` — before claiming done; record a new mode only if one is observed.

---

### Task 1: Profile session factory + vault-lifecycle registration hooks

**Files:**
- Modify: `src/backend/modules/notification_scheduler.py` (add `ProfileVaultLockedError` near line 50; add `profile_session_factory()` near line 547 before the globals)
- Modify: `src/backend/core/auth.py:361-419` (`open_profile_database_on_login`, `close_profile_database_on_logout`)
- Test: `src/backend/tests/test_notification_scheduler_wiring.py` (new file)

**Interfaces:**
- Produces: `ProfileVaultLockedError(RuntimeError)` — raised by factories when the vault is locked at call time.
- Produces: `profile_session_factory(profile_id: str) -> Callable[[], Awaitable[AsyncSession]]` — resolves the live connection per call; raises `ProfileVaultLockedError` when the connection is gone.
- Consumes (Task 2): the scheduler loop catches `ProfileVaultLockedError` and records `"skipped_locked"`.

- [ ] **Step 1: Write the failing tests**

Create `src/backend/tests/test_notification_scheduler_wiring.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py -p no:cacheprovider -q`
Expected: FAIL — `ImportError: cannot import name 'ProfileVaultLockedError'` (and `profile_session_factory`).

- [ ] **Step 3: Implement `ProfileVaultLockedError` and `profile_session_factory`**

In `src/backend/modules/notification_scheduler.py`, add after the `SchedulerState` class (after line 55):

```python
class ProfileVaultLockedError(RuntimeError):
    """A registered session factory found the profile vault locked.

    Routine, not an error: locking is how a session ends. The scheduler
    records it as `skipped_locked` rather than a failure.
    """
```

Add at the bottom of the file, before the `# Global instance` block (before line 547):

```python
def profile_session_factory(
    profile_id: str,
) -> Callable[[], Awaitable[AsyncSession]]:
    """Build a session factory bound to the profile's live vault connection.

    The connection is resolved per call, not captured at registration: a
    vault locked between registration and the next pass raises
    ProfileVaultLockedError, which the scheduler records honestly instead of
    serving stale access.
    """

    async def _factory() -> AsyncSession:
        from core.profile_database import get_profile_db_manager

        connection = get_profile_db_manager().get_connection(profile_id)
        if connection is None:
            raise ProfileVaultLockedError(
                f"profile {profile_id} vault is locked"
            )
        return connection.get_session()

    return _factory
```

- [ ] **Step 4: Implement the registration hooks in `core/auth.py`**

In `open_profile_database_on_login` (`src/backend/core/auth.py:361-402`), move `return connection` out of the `try` and insert registration between the `try/except` and the return. The function becomes:

```python
async def open_profile_database_on_login(
    profile_id: str,
    password: str,
) -> ProfileDatabaseConnection:
    """
    Open the per-profile encrypted database during login.

    This should be called after password verification succeeds.

    Args:
        profile_id: The authenticated profile's UUID
        password: The user's password (for key unsealing)

    Returns:
        ProfileDatabaseConnection for the profile

    Raises:
        HTTPException 500: If database cannot be opened
    """
    db_manager = get_profile_db_manager()
    try:
        connection = await db_manager.open_profile_database(profile_id, password)
        logger.info(f"Opened profile database for {profile_id}")
    except KeySealingError as e:
        logger.error(f"Failed to unseal encryption key for {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to access encrypted vault",
        )
    except FileNotFoundError as e:
        logger.error(f"Vault not found for {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile vault not found",
        )
    except Exception as e:
        logger.error(f"Failed to open profile database for {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to open profile database",
        )

    # Medication reminders can only be served while this vault is open —
    # register a session factory so the notification scheduler sees the
    # profile. Fail-soft: a broken scheduler must never break login.
    try:
        from modules.notification_scheduler import (
            get_notification_scheduler,
            profile_session_factory,
        )

        get_notification_scheduler().register_profile_session(
            profile_id, profile_session_factory(profile_id)
        )
    except Exception:
        logger.warning(
            "Could not register profile with notification scheduler",
            exc_info=True,
        )

    return connection
```

In `close_profile_database_on_logout` (`src/backend/core/auth.py:405-419`), unregister BEFORE closing the connection:

```python
async def close_profile_database_on_logout(profile_id: str) -> None:
    """
    Close the per-profile encrypted database during logout/lock.

    This ensures:
    - Database connections are properly closed
    - Encryption keys are cleared from memory
    - No residual access to profile data

    Args:
        profile_id: The profile's UUID
    """
    # Unregister first: the scheduler stops serving this profile before the
    # connection and key disappear. Fail-soft — a broken scheduler must never
    # block logout/lock.
    try:
        from modules.notification_scheduler import get_notification_scheduler

        get_notification_scheduler().unregister_profile_session(profile_id)
    except Exception:
        logger.debug(
            "Could not unregister profile from notification scheduler",
            exc_info=True,
        )

    db_manager = get_profile_db_manager()
    await db_manager.close_profile_database(profile_id)
    logger.info(f"Closed profile database for {profile_id}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py -p no:cacheprovider -q`
Expected: 4 passed (HC-NSW-001, 002, 003, 003b)

- [ ] **Step 6: Commit**

```bash
git add src/backend/modules/notification_scheduler.py src/backend/core/auth.py src/backend/tests/test_notification_scheduler_wiring.py
git commit -m "feat(notifications): register profile vault sessions on unlock/lock"
```

---

### Task 2: Per-pass outcome tracking + `skipped_locked` in scheduler status

**Files:**
- Modify: `src/backend/modules/notification_scheduler.py` (`__init__` :128-136, `_check_all_schedules` :225-243, new property)
- Modify: `src/backend/api/notifications.py:132-139` (`SchedulerStatusResponse`) and `:505-511` (endpoint body)
- Test: `src/backend/tests/test_notification_scheduler_wiring.py` (append)

**Interfaces:**
- Consumes: `ProfileVaultLockedError` (Task 1).
- Produces: `NotificationScheduler._last_pass_results: dict[str, str]` — `profile_id → "checked"|"skipped_locked"|"error"`; `last_pass_skipped_locked -> int` property; `SchedulerStatusResponse.skipped_locked: int`.

- [ ] **Step 1: Write the failing tests**

Append to `src/backend/tests/test_notification_scheduler_wiring.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py -p no:cacheprovider -q`
Expected: FAIL — `AttributeError: 'NotificationScheduler' object has no attribute '_last_pass_results'` (and response has no `skipped_locked` key).

- [ ] **Step 3: Implement outcome tracking**

In `NotificationScheduler.__init__` (`src/backend/modules/notification_scheduler.py`), add after `self._hour_start = None` (line 136):

```python
        # Outcome of the most recent pass, per registered profile
        # ("checked" | "skipped_locked" | "error"). In-memory only — never
        # persisted, so no profile data leaves the vault lifecycle.
        self._last_pass_results: dict[str, str] = {}
```

Add the property after `is_running` (after line 146):

```python
    @property
    def last_pass_skipped_locked(self) -> int:
        """Registered profiles skipped on the last pass because the vault
        was locked — the honest counterpart of backup_scheduler's
        skipped_locked."""
        return sum(
            1 for r in self._last_pass_results.values() if r == "skipped_locked"
        )
```

Replace the profile loop in `_check_all_schedules` (lines 238-243):

```python
        outcomes: dict[str, str] = {}
        for profile_id, session_factory in list(self._profile_sessions.items()):
            try:
                async with await session_factory() as db:
                    await self._check_profile_schedules(profile_id, db)
                outcomes[profile_id] = "checked"
            except ProfileVaultLockedError:
                # Routine: the vault was locked between registration and this
                # pass. Record it honestly; do not alarm the error log.
                outcomes[profile_id] = "skipped_locked"
                logger.debug(
                    "Skipped locked profile %s during reminder pass", profile_id
                )
            except Exception as e:
                outcomes[profile_id] = "error"
                logger.error(f"Error checking profile {profile_id}: {e}")
        self._last_pass_results = outcomes
```

In `src/backend/api/notifications.py`, add the field to `SchedulerStatusResponse` (lines 132-139):

```python
class SchedulerStatusResponse(BaseModel):
    """Response for scheduler status."""
    state: str
    active_platform: Optional[str] = None
    registered_profiles: int
    skipped_locked: int
    notifications_sent_this_hour: int
    last_check: Optional[str] = None
```

And in `get_scheduler_status` (lines 505-511), add the field:

```python
    return SchedulerStatusResponse(
        state=scheduler.state.value,
        active_platform=service.active_platform.value if service.active_platform else None,
        registered_profiles=len(scheduler._profile_sessions),
        skipped_locked=scheduler.last_pass_skipped_locked,
        notifications_sent_this_hour=scheduler._notifications_sent_this_hour,
        last_check=scheduler._last_check_time.isoformat() if scheduler._last_check_time else None,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py -p no:cacheprovider -q`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/backend/modules/notification_scheduler.py src/backend/api/notifications.py src/backend/tests/test_notification_scheduler_wiring.py
git commit -m "feat(notifications): record skipped_locked outcomes per scheduler pass"
```

---

### Task 3: Lifespan start/stop wiring

**Files:**
- Modify: `src/backend/main.py:66-81` (lifespan startup block) and `:77-83` (shutdown block)
- Test: `src/backend/tests/test_notification_scheduler_wiring.py` (append)

**Interfaces:**
- Consumes: `modules.notification_scheduler.start_notification_scheduler` / `stop_notification_scheduler` (already exist, :559/:566).

- [ ] **Step 1: Write the failing test**

Append:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py::test_hc_nsw_006_lifespan_starts_and_stops_scheduler -p no:cacheprovider -q`
Expected: FAIL — `AssertionError: expected await not performed` on `started`.

- [ ] **Step 3: Wire lifespan in `src/backend/main.py`**

Insert immediately after the backup-scheduler start block (after line 73, before `yield`):

```python
    # Medication reminders. Same fail-soft contract as the backup scheduler:
    # a scheduler that cannot start must not stop the app from booting.
    # The scheduler only serves profiles whose vault is currently unlocked —
    # locked vaults are honestly reported as skipped_locked, never opened
    # without the user's password (see modules/notification_scheduler.py).
    try:
        from modules.notification_scheduler import start_notification_scheduler
        await start_notification_scheduler()
    except Exception as _notif_exc:
        logger.warning("Notification scheduler not started: %s", _notif_exc)
```

Insert the shutdown counterpart immediately after `yield` and BEFORE the backup-scheduler stop block (stop in reverse start order — reminder passes write into vaults, so quiesce them first):

```python
    try:
        from modules.notification_scheduler import stop_notification_scheduler
        await stop_notification_scheduler()
    except Exception as _notif_exc:  # pragma: no cover - shutdown best effort
        logger.warning("Notification scheduler shutdown issue: %s", _notif_exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py -p no:cacheprovider -q`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/backend/main.py src/backend/tests/test_notification_scheduler_wiring.py
git commit -m "feat(notifications): start reminder scheduler in app lifespan"
```

---

### Task 4: Remove medication name from scheduler logs (PHI)

**Files:**
- Modify: `src/backend/modules/notification_scheduler.py:517-520` (`_send_notification` log line)
- Test: `src/backend/tests/test_notification_scheduler_wiring.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: log line containing `medication_id`/`schedule_id` uuids instead of `medication_name`.

**Why:** `_send_notification` currently logs `medication_name` at INFO. Application logs are unencrypted files on disk — a medication name there is a PHI leak independent of the vault. Found while wiring; fixing in-scope because it is in the file being wired and is a privacy invariant ("no PHI in logs").

- [ ] **Step 1: Write the failing test**

Append:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py::test_hc_nsw_009_no_phi_in_logs_or_master_schema -p no:cacheprovider -q`
Expected: FAIL — `assert 'Metformin' not in caplog.text` (current line 517-520 logs the name).

- [ ] **Step 3: Fix the log line**

Replace lines 517-520 of `src/backend/modules/notification_scheduler.py`:

```python
        logger.info(
            "Sent %s reminder for medication %s (schedule %s)",
            check_result.priority.value,
            check_result.medication_id,
            check_result.schedule_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py -p no:cacheprovider -q`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/backend/modules/notification_scheduler.py src/backend/tests/test_notification_scheduler_wiring.py
git commit -m "fix(notifications): drop medication name from reminder log line"
```

---

### Task 5: End-to-end delivery + dedup for an unlocked profile

**Files:**
- Modify: nothing — this task is the integration proof of Tasks 1-4.
- Test: `src/backend/tests/test_notification_scheduler_wiring.py` (append)

**Interfaces:**
- Consumes: everything above — `profile_session_factory` semantics exercised through a real (unencrypted test) SQLite vault, the outcome map, and `MockProvider.sent_notifications`.

- [ ] **Step 1: Write the failing tests**

Append:

```python
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
```

- [ ] **Step 2: Run tests**

Run: `cd src/backend && python -m pytest tests/test_notification_scheduler_wiring.py -p no:cacheprovider -q`
Expected: 10 passed. (These exercise already-built logic — they should pass on the first run. If HC-NSW-007 fails, debug with `systematic-debugging`: check `ReminderPriority` values in `modules/message_generator.py`, the `-30/+30` default window in `_evaluate_schedule`, and that `datetime.utcnow()` in the test and the scheduler share a timezone — both naive UTC.)

- [ ] **Step 3: Commit**

```bash
git add src/backend/tests/test_notification_scheduler_wiring.py
git commit -m "test(notifications): end-to-end delivery, dedup, and PHI-boundary coverage"
```

---

### Task 6: Documentation reconciliation + baseline count

**Files:**
- Modify: `docs/architecture/README.md:121-124`
- Modify: features doc(s) claiming implementation (locate in Step 1)
- Modify: `docs/features/TASK_LIST.md` (Session Notes)
- Modify: `CLAUDE.md`, `AGENT.md` (test baseline, if changed)
- Possibly modify: `docs/api/endpoints.md` (if it documents `/notifications/scheduler/status` fields)
- Read: `docs/agentic/recurring-failures.md`

- [ ] **Step 1: Locate every doc claim about the scheduler**

```bash
grep -rn "notification\|reminder\|scheduler" docs/features/ docs/api/endpoints.md docs/00_architecture_plans_index.md | grep -vi "http"
grep -rn "deliberately not wired\|all implemented\|unwired" docs/
```

Confirmed at planning time: `docs/architecture/README.md:121-124` says the scheduler "is deliberately not wired into the lifespan". The audit says a features-index claims it is implemented — find that claim and confirm the file/line before editing.

- [ ] **Step 2: Rewrite `docs/architecture/README.md:121-124`**

Replace the "The only background task..." paragraph with:

```markdown
Two background tasks start with the app: the **backup scheduler**
(BKUP-UX-001) and the **medication-reminder notification scheduler**
(Phase 3). Both share the locked-vault constraint — a background task
cannot open a profile's SQLCipher vault without the user's password — so
both are session-scoped: backups due while locked are recorded
`skipped_locked`, and reminders only fire while the profile is unlocked.
The scheduler registers a per-profile session factory at vault open
(`core/auth.py::open_profile_database_on_login`) and unregisters at close;
`GET /notifications/scheduler/status` reports how many registered profiles
were skipped because they locked mid-session. Reminder content lives only
in the per-profile vault — nothing reminder-related is written to the
master DB.
```

- [ ] **Step 3: Fix the features doc claim**

After this plan lands, "implemented" becomes true — make the wording honest about the session scope. Wherever the features doc asserts reminders are implemented, ensure it says (wordsmith to match surrounding voice): reminders are delivered as OS toasts **while the profile vault is unlocked**; locked profiles are recorded as `skipped_locked`; quiet-hours settings are stored per-medication but not yet enforced by the scheduler (pre-existing gap, unchanged by this work). If the doc instead says "deliberately unwired," update it the same way as Step 2.

- [ ] **Step 4: Update `docs/api/endpoints.md` if it documents the status route**

Check whether `/notifications/scheduler/status` response fields are listed there; if so, add `skipped_locked` to the documented response.

- [ ] **Step 5: Update the test baseline in `CLAUDE.md` and `AGENT.md`**

```bash
cd src/backend && python -m pytest tests/ -p no:cacheprovider -q --collect-only | tail -3
```

If collected ≠ 1245 (this plan adds ~10), update the baseline number in `CLAUDE.md` ("Baseline: **1245 backend tests collected**") and `AGENT.md` ("1245 collected; 1245 pass in CI, 1244 without an embedding model") in the same commit — new count should be 1245 + number of HC-NSW tests added.

- [ ] **Step 6: Re-read `docs/agentic/recurring-failures.md` and record if needed**

Read it in full. This work itself is an instance of a failure mode worth checking against the list: a fully unit-tested feature shipped dead for months because nothing tested the wiring (green suite + zero integration). If the file already covers "tested units, unwired integration," no new entry is needed; if not, add one line following the existing format (mode, evidence, recheck). Also confirm none of the eight listed modes was reproduced by this change — in particular: route tests went through `route_client`, and nothing asserted success without observing it.

- [ ] **Step 7: Session Notes in `docs/features/TASK_LIST.md`**

Append a dated Session Notes entry: notification scheduler wired in lifespan; register/unregister at `core/auth.py` vault open/close; `skipped_locked` outcome accounting; PHI removed from scheduler log line; docs corrected (architecture README + features doc). Note the deliberate scope decisions: session-scoped reminders only (locked-vault constraint), quiet hours still unenforced, `datetime.utcnow()` migration deferred to its own workstream.

- [ ] **Step 8: Commit**

> **Corrected 2026-09-27 ([review follow-up](../review/2026-09-27-followup.md), new finding N-01):** the original `git add docs/ CLAUDE.md AGENT.md` had the same defect as F-01. In this checkout `docs/` contains the owner's uncommitted `docs/INDEX.md` edits and the untracked `docs/capstone-report/`. Stage by explicit path: list only the files Steps 1–7 actually changed.

```bash
git status --short
git add docs/architecture/README.md docs/features/TASK_LIST.md CLAUDE.md AGENT.md   # + the features doc located in Step 1, + docs/api/endpoints.md only if Step 4 edited it
git diff --cached --name-only        # must list exactly the task-owned paths
git commit -m "docs: reconcile notification-scheduler claims with wired reality"
```

---

### Task 7: Full verification (definition of done)

- [ ] **Step 1: Clear stale bytecode (WSL/9p), then run the backend suite**

```bash
find src/backend -name __pycache__ -type d -exec rm -rf {} +
cd src/backend && python -m pytest tests/ -p no:cacheprovider -q
```

Expected: collected = *(measured start-of-plan count)* + number of HC-NSW tests added (corrected 2026-09-27; was "1245 + ~10"); no new failures vs baseline. `test_api_rag_index_002b` failing on embedding similarity is the known environment-only failure — not yours, do not lower the 0.7 threshold.

- [ ] **Step 2: Boot check**

```bash
cd src/backend && python -c "from main import app; print(app.title)"
```

Expected: prints `Asclexis API`.

- [ ] **Step 3: Frontend gates (no frontend changes — but DoD requires seeing output)**

Run on Windows, not WSL:

```powershell
cd src\frontend; npx tsc --noEmit; npx vitest run
```

Expected: clean / all pass.

- [ ] **Step 4: Manual smoke (optional but cheap)**

Boot the app (`.\dev.ps1`), unlock a profile that has a reminder-enabled medication with a schedule in the next few minutes, then `GET /api/v1/notifications/scheduler/status` — expect `state: "running"`, `registered_profiles: 1`. Lock the profile, repeat — `registered_profiles: 0`.

- [ ] **Step 5: Final commit**

```bash
git status   # should be clean; all prior steps committed
```

---

## Delivery surface (reference for the implementer)

- **Primary:** OS toast via `modules/platform_notifications.py` provider chain (Windows Toast → desktop-notifier → plyer). When no provider is available, `NotificationService.send` returns a failed `DeliveryResult`; the scheduler still writes a `ReminderLog` row (pre-existing behavior — the log records the *attempt*).
- **In-app surface:** `GET /api/v1/notifications/history` (per-profile `ReminderLog` rows) — already consumed by the frontend (`src/frontend/src/pages/NotificationSettings.tsx`, `src/frontend/src/services/notifications.ts`). No frontend changes are required by this plan: the only API change is the additive `skipped_locked` field on `/notifications/scheduler/status`.
- **Out of scope (documented, not built):** quiet-hours enforcement, pause/resume wiring, toast-action deep-links into the app, and the `datetime.utcnow()` migration (separate approved workstream).
