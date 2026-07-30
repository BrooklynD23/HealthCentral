"""BKUP-UX-001 — backup API, restore guards and the scheduler.

`scripts/backup.py` was a developer CLI no patient would ever run, so device
loss destroyed the whole record. These tests cover the routes that make it
usable and, more importantly, the guards that stop it destroying data.

Test IDs continue from HC-BKUP-008 in tests/test_backup_completeness.py.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import api.backup as backup_api
from core.auth import Session
from modules.backup_scheduler import ScheduleRunOutcome, is_due, run_due_backups


def _session(profile_id: str = "profile-a") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="T",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        token_jti="jti-1",
    )


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point app_data_path at a temp dir with two seeded profiles."""
    monkeypatch.setattr(
        type(backup_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    for pid in ("profile-a", "profile-b"):
        vault = tmp_path / "vaults" / pid
        vault.mkdir(parents=True)
        conn = sqlite3.connect(vault / "vault.db")
        conn.execute("CREATE TABLE observations (id TEXT)")
        conn.commit()
        conn.close()
        (vault / "key.bin").write_bytes(b"sealed-" + pid.encode())
        (vault / "key.method").write_text("password")
    conn = sqlite3.connect(tmp_path / "healthcentral.db")
    conn.execute("CREATE TABLE profiles (id TEXT)")
    conn.commit()
    conn.close()
    return tmp_path


async def _create(profile_id="profile-a"):
    with patch.object(backup_api, "audit_and_commit", AsyncMock()):
        return await backup_api.create_backup(
            session=_session(profile_id), master_db=AsyncMock()
        )


# ---------------------------------------------------------------------------
# HC-BKUP-009..011 — create, list, per-profile isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_bkup_009_create_backup_writes_into_the_profile_directory(data_dir):
    result = await _create()

    assert result.file_count > 0
    created = data_dir / "backups" / "profile-a" / result.backup_id
    assert created.is_dir()
    assert (created / "manifest.json").exists()


@pytest.mark.asyncio
async def test_hc_bkup_010_list_returns_only_this_profiles_backups(data_dir):
    await _create("profile-a")
    await _create("profile-b")

    with patch.object(backup_api, "audit_and_commit", AsyncMock()):
        listing = await backup_api.list_backups(
            session=_session("profile-a"), master_db=AsyncMock()
        )

    assert len(listing.backups) == 1
    assert "profile-a" in listing.backup_directory
    assert "profile-b" not in listing.backup_directory


@pytest.mark.asyncio
async def test_hc_bkup_011_cannot_reach_another_profiles_backup(data_dir):
    """The isolation assertion. Profile B's backup must be unreachable from
    profile A's session, even knowing its exact id."""
    other = await _create("profile-b")

    with pytest.raises(HTTPException) as exc:
        backup_api._resolve_backup_dir("profile-a", other.backup_id)
    assert exc.value.status_code == 404


@pytest.mark.parametrize("hostile", ["../profile-b", "../../etc", "..", "a/../../b"])
def test_hc_bkup_012_path_traversal_in_backup_id_is_refused(data_dir, hostile):
    """`backup_id` comes from the client, so it is treated as hostile."""
    with pytest.raises(HTTPException) as exc:
        backup_api._resolve_backup_dir("profile-a", hostile)
    assert exc.value.status_code in (400, 404)


# ---------------------------------------------------------------------------
# HC-BKUP-013/014 — verify and download
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_bkup_013_verify_detects_a_tampered_backup(data_dir):
    created = await _create()
    path = data_dir / "backups" / "profile-a" / created.backup_id

    with patch.object(backup_api, "audit_and_commit", AsyncMock()):
        good = await backup_api.verify_backup(
            created.backup_id, session=_session(), master_db=AsyncMock()
        )
    assert good.valid is True

    (path / "healthcentral.db").write_bytes(b"corrupted")
    with patch.object(backup_api, "audit_and_commit", AsyncMock()):
        bad = await backup_api.verify_backup(
            created.backup_id, session=_session(), master_db=AsyncMock()
        )
    assert bad.valid is False
    assert bad.errors


@pytest.mark.asyncio
async def test_hc_bkup_014_download_streams_a_complete_zip(data_dir):
    """A backup that cannot leave the device does not survive device loss."""
    created = await _create()

    with patch.object(backup_api, "audit_and_commit", AsyncMock()):
        response = await backup_api.download_backup(
            created.backup_id, session=_session(), master_db=AsyncMock()
        )

    assert response.media_type == "application/zip"
    assert created.backup_id in response.headers["content-disposition"]

    # Consume the actual response body rather than rebuilding the archive —
    # otherwise this asserts on the test's own zip, not the route's.
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
    names = zipfile.ZipFile(BytesIO(b"".join(chunks))).namelist()

    assert "manifest.json" in names
    # The sealed key must be in the archive, or a restore is unopenable.
    assert any(n.endswith("key.bin") for n in names)
    assert any(n.endswith("vault.db") for n in names)
    # A filename check cannot see inside healthcentral.db, which is where the
    # real cross-profile leak lived. Isolation is asserted properly in
    # test_backup_routes.py::test_hc_bkup_035; keep the cheap check here too.
    assert not any("profile-b" in n for n in names)
    assert "healthcentral.db" in names, (
        "the scoped master copy must still be present, or a restore from this "
        "archive cannot re-apply the profile row"
    )


@pytest.mark.asyncio
async def test_hc_bkup_015_download_leaves_no_temp_file_behind(data_dir):
    """The archive is built in memory: a second plaintext copy of a vault on
    disk with no owner responsible for deleting it is exactly what this app
    should not create."""
    created = await _create()
    before = {p for p in data_dir.rglob("*") if p.is_file()}

    with patch.object(backup_api, "audit_and_commit", AsyncMock()):
        await backup_api.download_backup(
            created.backup_id, session=_session(), master_db=AsyncMock()
        )

    after = {p for p in data_dir.rglob("*") if p.is_file()}
    assert after == before


# ---------------------------------------------------------------------------
# HC-BKUP-016..019 — restore guards
# ---------------------------------------------------------------------------

async def _restore(
    backup_id, *, password="CorrectHorse1",
    confirmation=backup_api.BACKUP_RESTORE_CONFIRMATION,
    authenticates=True, profile_exists=True, client_host="127.0.0.1",
):
    master_db = AsyncMock()
    profile = SimpleNamespace(id="profile-a") if profile_exists else None
    master_db.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: profile
    )
    with patch.object(backup_api, "authenticate_profile",
                      AsyncMock(return_value=profile if authenticates else None)), \
         patch.object(backup_api, "close_profile_database_on_logout", AsyncMock()) as closed, \
         patch.object(backup_api, "audit_and_commit", AsyncMock()):
        result = await backup_api.restore_backup(
            backup_id,
            payload=backup_api.RestoreRequest(
                password=password, confirmation_phrase=confirmation
            ),
            request=SimpleNamespace(client=SimpleNamespace(host=client_host)),
            session=_session(),
            master_db=master_db,
        )
    return result, closed


@pytest.mark.asyncio
async def test_hc_bkup_016_restore_requires_password_reauth(data_dir):
    created = await _create()
    with pytest.raises(HTTPException) as exc:
        await _restore(created.backup_id, authenticates=False)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_hc_bkup_017_restore_requires_the_confirmation_phrase(data_dir):
    created = await _create()
    with pytest.raises(HTTPException) as exc:
        await _restore(created.backup_id, confirmation="yes please")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_hc_bkup_018_restore_refuses_a_corrupt_backup(data_dir):
    """Overwriting a working vault with a broken snapshot is the worst thing
    this route could do."""
    created = await _create()
    path = data_dir / "backups" / "profile-a" / created.backup_id
    (path / "healthcentral.db").write_bytes(b"corrupted")

    with pytest.raises(HTTPException) as exc:
        await _restore(created.backup_id)
    assert exc.value.status_code == 400
    assert "verification" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_hc_bkup_019_restore_closes_the_profile_session_first(data_dir):
    """Nothing may hold a handle to a file being replaced, and the in-memory
    key must be cleared before the vault underneath it changes."""
    created = await _create()
    result, closed = await _restore(created.backup_id)

    closed.assert_awaited_once()
    assert result.files_restored > 0


# ---------------------------------------------------------------------------
# HC-BKUP-020..024 — the scheduler
# ---------------------------------------------------------------------------

def test_hc_bkup_020_is_due_semantics():
    now = datetime(2026, 7, 28, tzinfo=timezone.utc)

    assert is_due("daily", None, now) is True, "a new schedule runs immediately"
    assert is_due("off", None, now) is False
    assert is_due("unknown", None, now) is False
    assert is_due("daily", now - timedelta(hours=2), now) is False
    assert is_due("daily", now - timedelta(days=1, minutes=1), now) is True
    assert is_due("weekly", now - timedelta(days=2), now) is False
    assert is_due("weekly", now - timedelta(days=8), now) is True


def test_hc_bkup_021_naive_last_run_is_handled():
    """Stored timestamps may be naive; comparing them must not raise."""
    now = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert is_due("daily", datetime(2026, 7, 20), now) is True


@pytest.mark.asyncio
async def test_hc_bkup_022_locked_profile_is_skipped_not_claimed(data_dir):
    """The most important scheduler behaviour: a background task cannot open a
    locked vault, and must never record a backup it did not take."""
    schedule = SimpleNamespace(
        profile_id="profile-a", frequency="daily", enabled=True,
        last_run_at=None, last_result="never_run", last_file_count=0,
        retention_days=30,
    )
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [schedule])
    )
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    with patch("core.database.async_session_maker", return_value=db), \
         patch("modules.backup_scheduler._is_profile_unlocked", return_value=False), \
         patch("scripts.backup.backup") as ran:
        outcomes = await run_due_backups()

    ran.assert_not_called()
    assert outcomes == [ScheduleRunOutcome("profile-a", "skipped_locked")]
    assert schedule.last_result == "skipped_locked"
    assert schedule.last_run_at is None, "a skipped run must not count as a run"


@pytest.mark.asyncio
async def test_hc_bkup_023_unlocked_due_profile_is_backed_up(data_dir):
    schedule = SimpleNamespace(
        profile_id="profile-a", frequency="daily", enabled=True,
        last_run_at=None, last_result="never_run", last_file_count=0,
        retention_days=0,
    )
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [schedule])
    )
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    with patch("core.database.async_session_maker", return_value=db), \
         patch("modules.backup_scheduler._is_profile_unlocked", return_value=True):
        outcomes = await run_due_backups()

    assert outcomes[0].result == "success"
    assert schedule.last_result == "success"
    assert schedule.last_run_at is not None


@pytest.mark.asyncio
async def test_hc_bkup_024_one_profiles_failure_does_not_stop_the_others(data_dir):
    good = SimpleNamespace(
        profile_id="profile-a", frequency="daily", enabled=True, last_run_at=None,
        last_result="never_run", last_file_count=0, retention_days=0,
    )
    bad = SimpleNamespace(
        profile_id="profile-b", frequency="daily", enabled=True, last_run_at=None,
        last_result="never_run", last_file_count=0, retention_days=0,
    )
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [bad, good])
    )
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    real_backup = __import__("scripts.backup", fromlist=["backup"]).backup

    def flaky(*, data_dir, backup_dir, profile_id):
        if profile_id == "profile-b":
            raise OSError("disk full")
        return real_backup(data_dir=data_dir, backup_dir=backup_dir, profile_id=profile_id)

    with patch("core.database.async_session_maker", return_value=db), \
         patch("modules.backup_scheduler._is_profile_unlocked", return_value=True), \
         patch("scripts.backup.backup", side_effect=flaky):
        outcomes = await run_due_backups()

    results = {o.profile_id: o.result for o in outcomes}
    assert results["profile-b"] == "failed"
    assert results["profile-a"] == "success"


# ---------------------------------------------------------------------------
# HC-BKUP-025 — the schedule row carries no PHI
# ---------------------------------------------------------------------------

def test_hc_bkup_025_schedule_columns_are_phi_free():
    """The schedule lives in the *unencrypted* master DB, so every column must
    be an id, an enum, a count or a timestamp."""
    from models import BackupSchedule

    allowed = {
        "id", "profile_id", "frequency", "retention_days", "enabled",
        "last_run_at", "last_result", "last_file_count", "created_at", "updated_at",
    }
    actual = {c.name for c in BackupSchedule.__table__.columns}

    assert actual == allowed, (
        "a new backup_schedules column must be an id/enum/count/timestamp, "
        "never health data or user text"
    )


# ---------------------------------------------------------------------------
# HC-BKUP-026..029 — restore must not corrupt other profiles (BK-01)
# ---------------------------------------------------------------------------

def _seed_master(path, profiles):
    """Write a master DB holding one row per profile, with password hashes."""
    conn = sqlite3.connect(path)
    # The shared fixture creates a stub `profiles` table; replace it with the
    # column set these tests actually assert on.
    conn.execute("DROP TABLE IF EXISTS profiles")
    conn.execute(
        "CREATE TABLE profiles "
        "(id TEXT PRIMARY KEY, display_name TEXT, encryption_key_id TEXT, "
        "password_hash TEXT, password_salt TEXT, is_locked INTEGER, "
        "created_at TEXT, updated_at TEXT, last_accessed_at TEXT)"
    )
    for pid, pwhash in profiles.items():
        conn.execute(
            "INSERT INTO profiles VALUES (?,?,?,?,?,?,?,?,?)",
            (pid, f"name-{pid}", f"key-{pid}", pwhash, "salt", 0, "2026-01-01", "2026-01-01", None),
        )
    conn.commit()
    conn.close()


def _master_profile_ids(path) -> set[str]:
    conn = sqlite3.connect(path)
    rows = {r[0] for r in conn.execute("SELECT id FROM profiles")}
    conn.close()
    return rows


def _master_password_hash(path, profile_id) -> str | None:
    conn = sqlite3.connect(path)
    row = conn.execute(
        "SELECT password_hash FROM profiles WHERE id = ?", (profile_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


@pytest.mark.asyncio
async def test_hc_bkup_026_restoring_one_profile_leaves_the_other_intact(data_dir):
    """The isolation assertion this feature shipped without.

    A profile-scoped backup includes the SHARED master DB. Restoring it
    wholesale rolls the master back, deleting any profile created since —
    their vault survives on disk, orphaned and unreachable.
    """
    master = data_dir / "healthcentral.db"
    _seed_master(master, {"profile-a": "hash-a-old"})

    created = await _create("profile-a")

    # Profile B is created *after* A's backup.
    _seed_master(master, {"profile-a": "hash-a-old", "profile-b": "hash-b"})

    await _restore(created.backup_id)

    ids = _master_profile_ids(master)
    assert "profile-b" in ids, "restoring profile A must not delete profile B"
    assert "profile-a" in ids


@pytest.mark.asyncio
async def test_hc_bkup_027_restore_reapplies_the_backed_up_password_hash(data_dir):
    """The sealed key travels with the backup but the password hash lives in
    the master DB. If the hash is not rolled back with it, login succeeds and
    the vault then refuses to open."""
    master = data_dir / "healthcentral.db"
    _seed_master(master, {"profile-a": "hash-at-backup-time"})

    created = await _create("profile-a")

    # User changes their password after the backup.
    _seed_master(master, {"profile-a": "hash-changed-later", "profile-b": "hash-b"})

    await _restore(created.backup_id)

    assert _master_password_hash(master, "profile-a") == "hash-at-backup-time"
    # ...without disturbing the other profile's credentials.
    assert _master_password_hash(master, "profile-b") == "hash-b"


@pytest.mark.asyncio
async def test_hc_bkup_028_restore_returns_vault_files(data_dir):
    """The vault itself is still restored verbatim — scoping the master row
    must not turn restore into a no-op."""
    master = data_dir / "healthcentral.db"
    _seed_master(master, {"profile-a": "hash-a"})

    vault_db = data_dir / "vaults" / "profile-a" / "vault.db"
    created = await _create("profile-a")

    original = vault_db.read_bytes()
    vault_db.write_bytes(b"clobbered-since-backup")

    result, _ = await _restore(created.backup_id)

    assert vault_db.read_bytes() == original
    assert result.files_restored > 0


def test_hc_bkup_029_unscoped_restore_still_replaces_the_master(data_dir):
    """Full-install restore (the CLI path) keeps whole-file semantics — that
    is correct when you are rebuilding an entire machine."""
    from scripts import backup as backup_script

    master = data_dir / "healthcentral.db"
    _seed_master(master, {"profile-a": "hash-a"})

    backup_dir = data_dir / "backups" / "full"
    backup_dir.mkdir(parents=True)
    created = backup_script.backup(data_dir=data_dir, backup_dir=backup_dir)

    _seed_master(master, {"profile-a": "hash-a", "profile-b": "hash-b"})

    backup_script.restore(created.backup_path, data_dir)

    # No profile_id given -> the whole master is rolled back, B included.
    assert _master_profile_ids(master) == {"profile-a"}


# ---------------------------------------------------------------------------
# HC-BKUP-030..031 — retention_days=0 means "never prune" (BK-03)
# ---------------------------------------------------------------------------

def test_hc_bkup_030_retention_zero_prunes_nothing(data_dir):
    """`0` used to mean "older than right now" — i.e. delete everything. The
    scheduler already read it as "never prune" and skipped the call, so the
    same number meant opposite things depending on which path you came in
    through. It now means "never prune" in the function itself."""
    from scripts import backup as backup_script

    backup_dir = data_dir / "backups" / "profile-a"
    backup_dir.mkdir(parents=True)
    created = backup_script.backup(data_dir=data_dir, backup_dir=backup_dir)

    # Age it well past any plausible window.
    manifest = created.backup_path / "manifest.json"
    payload = json.loads(manifest.read_text())
    payload["created_at"] = "2020-01-01T00:00:00Z"
    manifest.write_text(json.dumps(payload))

    assert backup_script.prune(backup_dir, retention_days=0) == 0
    assert created.backup_path.is_dir()

    # A real window still prunes it — the guard is about 0, not about prune.
    assert backup_script.prune(backup_dir, retention_days=30) == 1
    assert not created.backup_path.exists()


@pytest.mark.asyncio
async def test_hc_bkup_031_prune_route_honours_retention_zero(data_dir):
    """The route accepts ge=0, so a user who set retention to 0 in Settings —
    where it reads as "keep forever" — could wipe their history by pruning."""
    created = await _create("profile-a")
    backup_path = data_dir / "backups" / "profile-a" / created.backup_id

    manifest = backup_path / "manifest.json"
    payload = json.loads(manifest.read_text())
    payload["created_at"] = "2020-01-01T00:00:00Z"
    manifest.write_text(json.dumps(payload))

    with patch.object(backup_api, "audit_and_commit", AsyncMock()):
        response = await backup_api.prune_backups(
            payload=backup_api.PruneRequest(retention_days=0),
            session=_session("profile-a"),
            master_db=AsyncMock(),
        )

    assert response.removed == 0
    assert backup_path.is_dir()


# ---------------------------------------------------------------------------
# HC-BKUP-032 — a good password clears the restore limiter (SEC-01)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_bkup_032_successful_reauth_resets_the_restore_limiter(data_dir):
    """restore_backup copied delete_profile's pattern, including its omission:
    failures accumulated across successful attempts, so a user who mistyped
    their password a few times over a session got locked out of restoring."""
    from core.rate_limiter import auth_rate_limiter
    from core.config import settings as core_settings

    if not core_settings.auth_rate_limit_enabled:
        pytest.skip("rate limiting disabled in this configuration")

    created = await _create("profile-a")

    key = "restore:1.2.3.4:profile-a"
    auth_rate_limiter.reset(key)
    try:
        for _ in range(auth_rate_limiter._max_attempts - 1):
            auth_rate_limiter.add_failure(key)

        await _restore(created.backup_id, client_host="1.2.3.4")

        auth_rate_limiter.add_failure(key)
        assert auth_rate_limiter.check(key).allowed is True
    finally:
        auth_rate_limiter.reset(key)


# ---------------------------------------------------------------------------
# HC-BKUP-041 — the backup root is not itself a backup
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hostile", [".", "./", "profile-a/.."])
def test_hc_bkup_041_backup_root_is_not_a_backup(data_dir, hostile):
    """`candidate == root` short-circuits the traversal guard, so `.` resolved
    to the profile's whole backup root and the download zipped every backup at
    once. The root is not a backup and must never resolve."""
    (data_dir / "backups" / "profile-a").mkdir(parents=True, exist_ok=True)

    with pytest.raises(HTTPException) as exc:
        backup_api._resolve_backup_dir("profile-a", hostile)
    assert exc.value.status_code in (400, 404)
