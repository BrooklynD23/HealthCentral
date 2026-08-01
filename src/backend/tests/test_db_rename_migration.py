"""Master DB filename migration (Phase B / B1a).

The master DB is the only index of which profiles exist and the only home of
password_hash and encryption_key_id. Point the app at a filename that is not
there and Alembic creates an empty one: the profile list renders empty and every
vault on disk becomes unreachable. Nothing is destroyed; all of it becomes
invisible. These tests are the guard on that.

Test IDs: HC-DBMIG-001..005.
"""

from __future__ import annotations

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
