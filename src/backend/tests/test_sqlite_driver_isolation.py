"""HC-SQLMIX: one database file, one SQLite library (owner decisions SQLITE-MIX, BKUP-MIX).

Two copies of SQLite in one process (stdlib ``sqlite3`` and the bundled
``sqlcipher3``) do not see each other's locks: POSIX locks never conflict
within a process, and each copy tracks its own. Opening one file through both
lets two writers commit at once, or lets one roll back the other's live
journal. That corrupted the master DB in CI run 38357922673 (E2E,
``disk I/O error`` / ``database disk image is malformed``).

Cause: ``open_profile_database`` used to set ``aiosqlite.core.sqlite3`` to
sqlcipher3 for the whole process, so master connections opened after the
first login came from a different library than the ones opened before it.
"""

from __future__ import annotations

import threading
from pathlib import Path

import aiosqlite.core
import pytest
from sqlalchemy import exc, text
from sqlalchemy.ext.asyncio import create_async_engine

import core.sqlcipher_driver as sqlcipher_driver
from core.config import settings
from core.profile_database import get_profile_db_manager
from core.security import generate_encryption_key, seal_key_with_dpapi
from scripts import backup as backup_script

PROFILE = "hc-sqlmix-profile"
PASSWORD = "Sqlmix-Pass-2026"

pytestmark = pytest.mark.skipif(
    not sqlcipher_driver.is_sqlcipher_available(),
    reason="needs sqlcipher3 (Linux wheel only); CI installs it",
)


@pytest.fixture
def vault_dir(tmp_path, monkeypatch) -> Path:
    # Restore at teardown in case an old build patches aiosqlite globally.
    monkeypatch.setattr(aiosqlite.core, "sqlite3", aiosqlite.core.sqlite3)
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "database_encryption_required", True)
    vault = tmp_path / "vaults" / PROFILE
    vault.mkdir(parents=True)
    sealed, method = seal_key_with_dpapi(
        generate_encryption_key(), fallback_password=PASSWORD, force_password=True
    )
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)
    return vault


async def _driver_module(conn) -> str:
    raw = await conn.get_raw_connection()
    return type(raw.driver_connection._conn).__module__


@pytest.mark.asyncio
async def test_hc_sqlmix_001_opening_a_profile_leaves_master_driver_alone(vault_dir, tmp_path):
    master = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'master.db'}")
    manager = get_profile_db_manager()
    profile = await manager.open_profile_database(PROFILE, PASSWORD)
    try:
        async with master.connect() as conn:
            assert await _driver_module(conn) == "sqlite3"
        # Encryption side unchanged: the vault engine still runs on sqlcipher3.
        async with profile.engine.connect() as conn:
            assert (await _driver_module(conn)).startswith("sqlcipher3")
    finally:
        await manager.close_profile_database(PROFILE)
        await master.dispose()


@pytest.mark.asyncio
async def test_hc_sqlmix_002_master_writers_still_exclude_each_other(vault_dir, tmp_path):
    """The lock check through a real master-style engine: a connection opened
    before a profile login and one opened after must not both hold a write lock."""
    master = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'master.db'}", connect_args={"timeout": 0.2}
    )
    manager = get_profile_db_manager()
    async with master.begin() as conn:
        await conn.execute(text("CREATE TABLE t (x TEXT)"))
    before = await master.connect()
    try:
        await before.execute(text("SELECT 1"))  # opened pre-login
        await manager.open_profile_database(PROFILE, PASSWORD)
        after = await master.connect()  # pool must open a new connection
        try:
            await before.execute(text("INSERT INTO t VALUES ('a')"))  # holds RESERVED
            with pytest.raises(exc.OperationalError, match="database is locked"):
                await after.execute(text("INSERT INTO t VALUES ('b')"))
        finally:
            await after.close()
    finally:
        await before.close()
        await manager.close_profile_database(PROFILE)
        await master.dispose()


def test_hc_sqlmix_003_backup_does_not_break_a_live_vault_write(tmp_path):
    """BKUP-MIX: backing up a vault mid-transaction must not roll back the
    writer's journal. With stdlib sqlite3 on a sqlcipher3-held file it did,
    and the writer's COMMIT failed with ``disk I/O error``.

    The backup runs on another thread, as the route does: on the same library
    it waits for the writer's lock instead of breaking it."""
    sqlcipher = sqlcipher_driver.get_sqlcipher_module()
    data_dir = tmp_path / "data"
    vault = data_dir / "vaults" / PROFILE / "vault.db"
    vault.parent.mkdir(parents=True)
    journal = vault.with_name("vault.db-journal")
    writer = sqlcipher.connect(str(vault), isolation_level=None, check_same_thread=False)
    worker = None
    try:
        writer.execute("PRAGMA key = \"x'%s'\"" % ("AB" * 32))
        writer.execute("CREATE TABLE t (x TEXT)")
        writer.executemany("INSERT INTO t VALUES (?)", [("a" * 500,)] * 300)
        writer.execute("PRAGMA cache_size = 5")  # force journal sync + cache spill
        writer.execute("BEGIN")
        writer.execute("UPDATE t SET x = 'b'")
        assert journal.exists()

        worker = threading.Thread(
            target=backup_script.backup, args=(data_dir, tmp_path / "backups"), daemon=True
        )
        worker.start()
        worker.join(timeout=1.0)  # old code finishes here, having deleted the journal

        assert journal.exists(), "backup deleted a live journal"
        writer.execute("COMMIT")
        assert writer.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        worker.join(timeout=30)
        assert not worker.is_alive(), "backup never finished after the writer committed"
    finally:
        writer.close()
