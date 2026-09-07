"""Master DB filename migration (Phase B / B1a).

The master DB is the only index of which profiles exist and the only home of
password_hash and encryption_key_id. Point the app at a filename that is not
there and Alembic creates an empty one: the profile list renders empty and every
vault on disk becomes unreachable. Nothing is destroyed; all of it becomes
invisible. These tests are the guard on that.

Test IDs: HC-DBMIG-001..009.
"""

from __future__ import annotations

import json
import sqlite3

from core.db_migration import migrate_master_db_filename


def _seed_legacy_master(data_dir, profile_id="profile-a"):
    data_dir.mkdir(parents=True, exist_ok=True)
    legacy = data_dir / "healthcentral.db"
    conn = sqlite3.connect(legacy)
    conn.execute("CREATE TABLE profiles (id TEXT, display_name TEXT)")
    conn.execute("INSERT INTO profiles VALUES (?, ?)", (profile_id, "Ann"))
    conn.commit()
    conn.close()
    return legacy


def test_hc_dbmig_001_legacy_master_is_renamed_with_its_rows(tmp_path):
    """The profile rows must survive — otherwise the user's vaults become
    unreachable even though the files are intact."""
    data_dir = tmp_path / "data"
    _seed_legacy_master(data_dir)

    assert migrate_master_db_filename(data_dir) is True

    new = data_dir / "asclexis.db"
    assert new.exists()
    assert not (data_dir / "healthcentral.db").exists()

    conn = sqlite3.connect(new)
    rows = conn.execute("SELECT id, display_name FROM profiles").fetchall()
    conn.close()
    assert rows == [("profile-a", "Ann")]


def test_hc_dbmig_002_wal_and_shm_sidecars_move_too(tmp_path):
    """SQLite in WAL mode leaves -wal and -shm beside the database. Renaming
    only the main file orphans unflushed transactions."""
    data_dir = tmp_path / "data"
    _seed_legacy_master(data_dir)
    (data_dir / "healthcentral.db-wal").write_bytes(b"wal-content")
    (data_dir / "healthcentral.db-shm").write_bytes(b"shm-content")

    assert migrate_master_db_filename(data_dir) is True

    assert (data_dir / "asclexis.db-wal").read_bytes() == b"wal-content"
    assert (data_dir / "asclexis.db-shm").read_bytes() == b"shm-content"
    assert not (data_dir / "healthcentral.db-wal").exists()
    assert not (data_dir / "healthcentral.db-shm").exists()


def test_hc_dbmig_003_is_a_noop_on_a_fresh_install(tmp_path):
    """No legacy file means nothing to do. Must not create anything."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)

    assert migrate_master_db_filename(data_dir) is False
    assert not (data_dir / "asclexis.db").exists()


def test_hc_dbmig_004_never_overwrites_an_existing_new_db(tmp_path):
    """If both exist the new one wins and the legacy file is left untouched for
    the operator to inspect. Silently clobbering a live database would be the
    worst possible outcome of a cosmetic rename."""
    data_dir = tmp_path / "data"
    _seed_legacy_master(data_dir)
    current = data_dir / "asclexis.db"
    conn = sqlite3.connect(current)
    conn.execute("CREATE TABLE profiles (id TEXT, display_name TEXT)")
    conn.execute("INSERT INTO profiles VALUES ('profile-live', 'Live')")
    conn.commit()
    conn.close()

    assert migrate_master_db_filename(data_dir) is False

    conn = sqlite3.connect(current)
    rows = conn.execute("SELECT id FROM profiles").fetchall()
    conn.close()
    assert rows == [("profile-live",)]
    assert (data_dir / "healthcentral.db").exists()


def test_hc_dbmig_005_is_idempotent(tmp_path):
    """Runs on every boot, so a second call must be a clean no-op."""
    data_dir = tmp_path / "data"
    _seed_legacy_master(data_dir)

    assert migrate_master_db_filename(data_dir) is True
    assert migrate_master_db_filename(data_dir) is False


def test_hc_dbmig_006_restore_accepts_a_pre_rename_backup(tmp_path):
    """Every backup taken before the rename lists healthcentral.db. If restore
    stops recognising it, _reapply_profile_row skips silently and the vault is
    stranded against a mismatched password hash — the BK-01 bug via a side
    door.

    Asserted end to end, not just on the constant: a hand-built pre-rename
    backup (full master under the legacy name, manifest listing it, no
    top-level ``profile_id`` key) must still verify AND still restore.
    """
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    vault = data_dir / "vaults" / "profile-a"
    vault.mkdir(parents=True)
    conn = sqlite3.connect(vault / "vault.db")
    conn.execute("CREATE TABLE observations (id TEXT)")
    conn.commit()
    conn.close()
    (vault / "key.bin").write_bytes(b"sealed")

    # The live master already carries the new name and a *newer* password hash:
    # this is the install that has upgraded and whose user has since changed
    # their password. Reconciliation is the whole point of the exercise.
    live_master = data_dir / "asclexis.db"
    conn = sqlite3.connect(live_master)
    conn.execute(
        "CREATE TABLE profiles (id TEXT, display_name TEXT, encryption_key_id TEXT, "
        "password_hash TEXT, password_salt TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO profiles VALUES ('profile-a','Ann','k','new-hash','salt','2026-01-01')"
    )
    conn.commit()
    conn.close()

    # A backup directory shaped like a pre-rename one: legacy master filename.
    backup_path = tmp_path / "backups" / "backup_20260101_000000"
    backup_path.mkdir(parents=True)
    legacy = backup_path / "healthcentral.db"
    conn = sqlite3.connect(legacy)
    conn.execute(
        "CREATE TABLE profiles (id TEXT, display_name TEXT, encryption_key_id TEXT, "
        "password_hash TEXT, password_salt TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO profiles VALUES ('profile-a','Ann','k','old-hash','salt','2026-01-01')"
    )
    conn.commit()
    conn.close()
    backup_vault = backup_path / "vaults" / "profile-a"
    backup_vault.mkdir(parents=True)
    conn = sqlite3.connect(backup_vault / "vault.db")
    conn.execute("CREATE TABLE observations (id TEXT)")
    conn.execute("INSERT INTO observations VALUES ('obs-from-backup')")
    conn.commit()
    conn.close()
    (backup_vault / "key.bin").write_bytes(b"sealed-at-backup-time")

    def _entry(rel: str):
        f = backup_path / rel
        return {
            "path": rel,
            "sha256": backup_script._compute_sha256(f),
            "size_bytes": f.stat().st_size,
            "method": "file_copy",
        }

    # No top-level "profile_id" key at all — that is what a pre-scoping
    # manifest looks like, and it must read as unscoped.
    manifest = {
        "timestamp": "20260101_000000",
        "created_at": "2026-01-01T00:00:00Z",
        "app_version": "0.1.0",
        "backup_method": "file_copy",
        "files": [
            _entry("healthcentral.db"),
            _entry("vaults/profile-a/vault.db"),
            _entry("vaults/profile-a/key.bin"),
        ],
    }
    (backup_path / "manifest.json").write_text(json.dumps(manifest, indent=2))

    assert "healthcentral.db" in backup_script.MASTER_DB_NAMES, (
        "pre-rename backups must still be recognised"
    )

    verified = backup_script.verify(backup_path)
    assert verified.valid, verified.errors
    assert verified.files_checked == 3

    result = backup_script.restore(backup_path, data_dir, profile_id="profile-a")
    assert result.success, result.error
    assert result.partial is False

    # The legacy-named master was held back, not copied over the live one...
    assert not (data_dir / "healthcentral.db").exists()
    # ...but its row WAS re-applied, so the sealed key and the hash agree again.
    conn = sqlite3.connect(live_master)
    hash_now = conn.execute(
        "SELECT password_hash FROM profiles WHERE id = 'profile-a'"
    ).fetchone()[0]
    conn.close()
    assert hash_now == "old-hash", (
        "the pre-rename backup's profile row must be re-applied, or the "
        "restored key.bin is stranded against a mismatched password hash"
    )
    assert (vault / "key.bin").read_bytes() == b"sealed-at-backup-time"


def test_hc_dbmig_007_unscoped_backup_writes_the_complete_master_under_the_new_name(
    tmp_path,
):
    """An unscoped backup is a backup of the whole install: every profile's row
    must be there, stored under the new filename. Scoping it by accident would
    make the documented whole-install DR procedure silently lossy."""
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    conn = sqlite3.connect(data_dir / "asclexis.db")
    conn.execute("CREATE TABLE profiles (id TEXT, display_name TEXT)")
    conn.execute("INSERT INTO profiles VALUES ('profile-a', 'Ann')")
    conn.execute("INSERT INTO profiles VALUES ('profile-b', 'Bob')")
    conn.commit()
    conn.close()

    result = backup_script.backup(data_dir, tmp_path / "backups", profile_id=None)
    assert result.success

    stored = result.backup_path / "asclexis.db"
    assert stored.exists(), "the master must be stored under the new filename"
    assert not (result.backup_path / "healthcentral.db").exists()

    conn = sqlite3.connect(stored)
    rows = sorted(r[0] for r in conn.execute("SELECT id FROM profiles"))
    conn.close()
    assert rows == ["profile-a", "profile-b"], "an unscoped backup keeps everyone"

    manifest = json.loads((result.backup_path / "manifest.json").read_text())
    assert manifest["profile_id"] is None
    assert "asclexis.db" in {e["path"] for e in manifest["files"]}


def test_hc_dbmig_008_a_populated_legacy_master_still_lists_its_profiles(tmp_path):
    """The failure this whole task exists to prevent: after the rename, the
    profiles the app enumerates must be the same ones that were there before.
    Enumerated through the filename the application derives from settings, not
    a hardcoded literal — a migration that moves the file somewhere the app
    does not look is no migration at all."""
    from core.config import settings

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    legacy = data_dir / "healthcentral.db"
    conn = sqlite3.connect(legacy)
    conn.execute(
        "CREATE TABLE profiles (id TEXT, display_name TEXT, encryption_key_id TEXT, "
        "password_hash TEXT)"
    )
    for pid, name in (("profile-a", "Ann"), ("profile-b", "Bob"), ("profile-c", "Cy")):
        conn.execute(
            "INSERT INTO profiles VALUES (?, ?, ?, ?)",
            (pid, name, f"key-{pid}", f"hash-{pid}"),
        )
    conn.execute("CREATE TABLE audit_logs (id TEXT, profile_id TEXT)")
    conn.execute("INSERT INTO audit_logs VALUES ('a1', 'profile-a')")
    conn.commit()
    conn.close()
    before = legacy.stat().st_size

    assert migrate_master_db_filename(data_dir) is True

    # Open it the way the application will: settings decides the filename.
    migrated = data_dir / settings.master_db_filename
    assert migrated.name == "asclexis.db"
    assert migrated.exists(), "the app must find the master where the migration put it"
    assert migrated.stat().st_size == before, "byte-for-byte the same database"

    conn = sqlite3.connect(migrated)
    profiles = sorted(conn.execute("SELECT id, display_name FROM profiles"))
    audit = conn.execute("SELECT count(*) FROM audit_logs").fetchone()[0]
    encryption_key_ids = sorted(
        r[0] for r in conn.execute("SELECT encryption_key_id FROM profiles")
    )
    conn.close()

    assert profiles == [
        ("profile-a", "Ann"),
        ("profile-b", "Bob"),
        ("profile-c", "Cy"),
    ]
    assert audit == 1
    assert encryption_key_ids == ["key-profile-a", "key-profile-b", "key-profile-c"], (
        "encryption_key_id lives only here; losing it makes every vault "
        "unopenable"
    )


def test_hc_dbmig_009_startup_runs_the_migration_before_any_engine_opens(tmp_path):
    """The migration only helps if it is actually wired, and wired *early*.

    `init_database` is what creates directories and opens the master engine, so
    if the rename does not happen strictly before it, Alembic has already made
    an empty database under the new name and every profile is invisible. This
    asserts the ordering, not merely that the call exists somewhere.
    """
    import asyncio
    from unittest.mock import AsyncMock, patch

    import main as main_module

    calls: list[str] = []

    def _fake_migrate(data_dir):
        calls.append("migrate")
        return False

    async def _fake_init():
        calls.append("init_database")

    class _StopHere(Exception):
        """Aborts the lifespan once the ordering is established, so none of the
        fail-soft startup blocks below run and touch the real data directory."""

    async def _fake_master_migrations():
        calls.append("master_migrations")
        raise _StopHere

    async def _drive():
        with (
            patch("core.db_migration.migrate_master_db_filename", _fake_migrate),
            patch.object(main_module, "init_database", _fake_init),
            patch.object(main_module, "run_master_migrations_async", _fake_master_migrations),
            patch.object(type(main_module.settings), "validate_startup", lambda self: []),
            patch.object(main_module, "close_database", AsyncMock()),
        ):
            try:
                async with main_module.lifespan(main_module.create_app()):
                    pass
            except _StopHere:
                pass

    asyncio.run(_drive())

    assert "migrate" in calls, "startup must run the master-DB filename migration"
    assert calls.index("migrate") < calls.index("init_database"), (
        "the rename must happen before any engine is created, or Alembic "
        "creates an empty master and hides every profile"
    )
    assert calls.index("migrate") < calls.index("master_migrations")
