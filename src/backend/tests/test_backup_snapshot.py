"""HC-BKUP-056..057 — an encrypted vault is backed up consistently (BKUP-TORN).

Security review M1 on PR #89: a keyless open of an encrypted vault fails, so
the backup fell back to a plain file copy with no lock held. A commit landing
mid-copy left a backup whose pages came from two different states. These tests
force that interleave deterministically: the first page is copied, a second
connection commits a rewrite of the table, then the rest is copied.

The assertions do not care how the snapshot is taken. They open the backed-up
vault with the profile's key and require `PRAGMA integrity_check` = ok and a
row set that is wholly the before-state or wholly the after-state.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sqlite3
import threading
from contextlib import closing, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import aiosqlite.core
import pytest
from sqlalchemy import text

import api.backup as backup_api
import core.sqlcipher_driver as sqlcipher_driver
from core.config import settings
from core.profile_database import get_profile_db_manager
from core.security import generate_encryption_key, seal_key_with_dpapi
from modules.backup_scheduler import run_due_backups
from scripts import backup as backup_script
from tests.support.routes import route_client

PROFILE = "hc-bkup-torn-profile"
PASSWORD = "Torn-Pass-2026"
BEFORE_ROWS = 300
AFTER_ROWS = 600


def _require_sqlcipher() -> None:
    if sqlcipher_driver.is_sqlcipher_available():
        return
    if os.environ.get("CI", "").lower() == "true" or os.environ.get("HC_REQUIRE_SQLCIPHER") == "1":
        pytest.fail("BKUP-TORN needs sqlcipher3 in CI", pytrace=False)
    pytest.skip("BKUP-TORN needs sqlcipher3 (Linux wheel only)")


@pytest.fixture
def vault(tmp_path, monkeypatch):
    _require_sqlcipher()
    monkeypatch.setattr(aiosqlite.core, "sqlite3", aiosqlite.core.sqlite3)
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "database_encryption_required", True)
    vault_dir = tmp_path / "vaults" / PROFILE
    vault_dir.mkdir(parents=True)
    key = generate_encryption_key()
    sealed, method = seal_key_with_dpapi(key, fallback_password=PASSWORD, force_password=True)
    (vault_dir / "key.bin").write_bytes(sealed)
    (vault_dir / "key.method").write_text(method)
    # The master row a profile-scoped restore re-applies.
    with closing(sqlite3.connect(tmp_path / "asclexis.db")) as master:
        master.execute("CREATE TABLE profiles (id TEXT)")
        master.execute("INSERT INTO profiles VALUES (?)", (PROFILE,))
        master.commit()
    # Test-side writer key, in the format the app's PRAGMA key uses.
    hex_key = get_profile_db_manager()._key_to_hex(key)
    return SimpleNamespace(data_dir=tmp_path, db=vault_dir / "vault.db", hex_key=hex_key)


def _keyed(db: Path, hex_key: str):
    conn = sqlcipher_driver.get_sqlcipher_module().connect(str(db), timeout=30)
    conn.execute(f"PRAGMA key = \"x'{hex_key}'\"")
    return conn


def _rewrite_table(db: Path, hex_key: str) -> None:
    """A second writer rewrites the table to the other row count and commits.

    Flipping the count changes the page layout, so a copy that mixes pages
    from both sides of any one commit is structurally torn.
    """
    conn = _keyed(db, hex_key)
    try:
        conn.execute("BEGIN IMMEDIATE")
        count = conn.execute("SELECT count(*) FROM torn").fetchone()[0]
        rows = AFTER_ROWS if count == BEFORE_ROWS else BEFORE_ROWS
        conn.execute("DELETE FROM torn")
        conn.executemany(
            "INSERT INTO torn (n, pad) VALUES (?, ?)",
            [(i, os.urandom(400)) for i in range(rows)],
        )
        conn.commit()
    finally:
        conn.close()


async def _open_and_seed() -> None:
    connection = await get_profile_db_manager().open_profile_database(PROFILE, PASSWORD)
    async with connection.get_session() as session:
        await session.execute(text("CREATE TABLE torn (n INTEGER, pad BLOB)"))
        for i in range(BEFORE_ROWS):
            await session.execute(
                text("INSERT INTO torn (n, pad) VALUES (:n, :p)"),
                {"n": i, "p": os.urandom(400)},
            )


@contextmanager
def _writes_during_backup(vault):
    """Commit while the vault is being backed up, whichever way it is copied.

    Deterministic for a file copy: a commit lands after the first page. For
    any other method, a second writer commits rewrites in a loop for the whole
    backup; at least one must land, or the test proved nothing.
    """
    real_copy2 = shutil.copy2
    stop = threading.Event()
    exclusive = threading.Lock()
    commits = []

    def copy2(src, dst, *args, **kwargs):
        if Path(src) != vault.db:
            return real_copy2(src, dst, *args, **kwargs)
        # Hold the loop writer off, or it can flip the count back mid-copy.
        with exclusive, open(src, "rb") as fin, open(dst, "wb") as fout:
            fout.write(fin.read(4096))
            _rewrite_table(vault.db, vault.hex_key)
            commits.append("mid-copy")
            fout.write(fin.read())
        return dst

    def writer():
        while not stop.is_set():
            with exclusive:
                _rewrite_table(vault.db, vault.hex_key)
            commits.append("loop")

    thread = threading.Thread(target=writer, daemon=True)
    with patch.object(backup_script.shutil, "copy2", copy2):
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=60)
    assert commits, "no commit overlapped the backup"


def _assert_consistent_vault(backup_path: Path, hex_key: str) -> None:
    db = backup_path / "vaults" / PROFILE / "vault.db"
    # Still ciphertext: no plaintext header, unreadable without the key.
    assert db.read_bytes()[:16] != b"SQLite format 3\x00"
    with pytest.raises(Exception, match="file is not a database"):
        sqlcipher_driver.get_sqlcipher_module().connect(str(db)).execute(
            "SELECT count(*) FROM sqlite_master"
        ).fetchone()
    conn = _keyed(db, hex_key)
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "torn backup"
        rows = sorted(r[0] for r in conn.execute("SELECT n FROM torn"))
    finally:
        conn.close()
    assert rows in (list(range(BEFORE_ROWS)), list(range(AFTER_ROWS))), (
        f"backup holds a mixed state: {len(rows)} rows"
    )


async def _close():
    await get_profile_db_manager().close_profile_database(PROFILE)


@pytest.mark.asyncio
async def test_hc_bkup_056_route_backup_of_a_vault_under_write_is_consistent(vault):
    await _open_and_seed()
    try:
        with _writes_during_backup(vault), route_client(
            backup_api.router, "/backup", profile_id=PROFILE
        ) as client:
            # Off this loop: the app runs on the TestClient's loop.
            response = await asyncio.to_thread(client.post, "/backup/")
        assert response.status_code == 201, response.text
        backup_path = vault.data_dir / "backups" / PROFILE / response.json()["backup_id"]
        _assert_consistent_vault(backup_path, vault.hex_key)

        # Restore contract unchanged: the existing file-copy restore puts it
        # back and the app's own keyed open reads it.
        await _close()
        vault.db.write_bytes(b"clobbered")
        assert backup_script.restore(backup_path, vault.data_dir, PROFILE).success
        connection = await get_profile_db_manager().open_profile_database(PROFILE, PASSWORD)
        async with connection.get_session() as session:
            count = (await session.execute(text("SELECT count(*) FROM torn"))).scalar_one()
        assert count in (BEFORE_ROWS, AFTER_ROWS)
    finally:
        await _close()


@pytest.mark.asyncio
async def test_hc_bkup_057_scheduled_backup_of_a_vault_under_write_is_consistent(vault):
    """Same guarantee on the scheduler path: one invariant, both callers."""
    await _open_and_seed()
    schedule = SimpleNamespace(
        profile_id=PROFILE, frequency="daily", enabled=True, last_run_at=None,
        last_result="never_run", last_file_count=0, retention_days=0,
    )
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [schedule])
    )
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    try:
        with _writes_during_backup(vault), patch("core.database.async_session_maker", return_value=db):
            outcomes = await run_due_backups()
        assert outcomes[0].result == "success"
        (backup_path,) = (vault.data_dir / "backups" / PROFILE).iterdir()
        _assert_consistent_vault(backup_path, vault.hex_key)
        manifest = json.loads((backup_path / "manifest.json").read_text())
        vault_entry = next(f for f in manifest["files"] if f["path"].endswith("vault.db"))
        assert vault_entry["method"] != "file_copy"
    finally:
        await _close()


def _open_fds_to(path: Path) -> list[str]:
    fd_dir = Path("/proc/self/fd")
    found = []
    for fd in fd_dir.iterdir():
        try:
            if Path(os.readlink(fd)) == path:
                found.append(fd.name)
        except OSError:
            continue
    return found


@pytest.mark.asyncio
async def test_hc_bkup_058_snapshot_after_logout_does_not_reopen_the_vault(vault):
    """Security review finding 1: a snapshotter built while the profile was
    open must not re-key a fresh connection after logout/lock, which would
    leave keyed vault access alive with nothing to close it."""
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("needs /proc to count open file descriptors")
    await _open_and_seed()
    snapshot = backup_script.keyed_snapshotter(PROFILE)
    await _close()
    assert _open_fds_to(vault.db) == []

    dest = vault.data_dir / "snap.db"
    took = await asyncio.to_thread(snapshot, dest)

    assert took is False, "snapshot ran against a closed profile"
    assert not dest.exists()
    assert _open_fds_to(vault.db) == [], "a keyed vault connection outlived logout"
