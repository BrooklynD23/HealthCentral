"""C-P6 / SQL-FK-001: PRAGMA foreign_keys is ON on every application engine.

SQLite defaults the pragma OFF per connection, so every ``ondelete=`` in the
models was inert. HC-FK-001..003 pin the pragma on *more than one distinct
physical connection* per engine (one session proves one connection and
silently misses the rest of the pool).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))


async def _fk_pragma_on_distinct_connections(engine) -> int:
    """Hold two pooled connections at once; return the number of distinct ones.

    Asserts ``PRAGMA foreign_keys`` is 1 on each.
    """
    async with engine.connect() as c1, engine.connect() as c2:
        raw1 = await c1.get_raw_connection()
        raw2 = await c2.get_raw_connection()
        assert raw1.driver_connection is not raw2.driver_connection
        for conn in (c1, c2):
            assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    return 2


# --------------------------------------------------------------------------
# HC-FK-001: master engine
# --------------------------------------------------------------------------


def test_hc_fk_001_master_engine_registers_the_pragma_listener():
    """The real master engine must run PRAGMA foreign_keys=ON on connect.

    GATE-12 forbids opening the real master DB in a test, so the pool's
    ``connect`` listeners are driven with a recording stand-in for the DBAPI
    connection instead of a real connection.
    """
    from core.database import engine

    if engine.sync_engine.url.get_backend_name() != "sqlite":
        pytest.skip("master engine is not SQLite in this configuration")

    class _Cursor:
        def __init__(self, log):
            self.log = log

        def execute(self, sql, *a):
            self.log.append(sql)

        def close(self):
            pass

    class _Dbapi:
        def __init__(self):
            self.log = []

        def cursor(self):
            return _Cursor(self.log)

        def __getattr__(self, name):  # the dialect's own on-connect hook
            return lambda *a, **k: None

    fake = _Dbapi()
    for fn in list(engine.sync_engine.pool.dispatch.connect):
        try:
            fn(fake, None)
        except AttributeError:
            pass  # the dialect's own hook wants a real sqlite3 connection
    assert "PRAGMA foreign_keys=ON" in fake.log


@pytest.mark.asyncio
async def test_hc_fk_001b_install_helper_sets_pragma_on_every_connection(tmp_path):
    """install_sqlite_foreign_keys on a file engine: >1 distinct connection."""
    from core.database import install_sqlite_foreign_keys

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'm.db'}")
    try:
        install_sqlite_foreign_keys(engine.sync_engine)
        assert await _fk_pragma_on_distinct_connections(engine) == 2
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_fk_001c_engine_without_helper_has_pragma_off(tmp_path):
    """Control: the check above can fail. A bare engine reports 0."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'bare.db'}")
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 0
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# HC-FK-002: profile engine (the real open path)
# --------------------------------------------------------------------------

_PASSWORD = "Fk-Enforce-Pass-1!"


def _make_vault(root: Path, profile_id: str) -> Path:
    """Seal a generated key into vaults/<pid>/ (real key files, no mocks)."""
    from core.security import generate_encryption_key, seal_key_with_dpapi

    vault = root / "vaults" / profile_id
    vault.mkdir(parents=True)
    sealed, method = seal_key_with_dpapi(
        generate_encryption_key(),
        fallback_password=_PASSWORD,
        force_password=True,
    )
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)
    return vault


@pytest.mark.asyncio
async def test_hc_fk_002_profile_engine_pragma_on_after_key_and_migration(
    tmp_path, monkeypatch
):
    from core.config import settings
    from core.profile_database import get_profile_db_manager

    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    pid = str(uuid.uuid4())
    _make_vault(tmp_path, pid)
    manager = get_profile_db_manager()
    try:
        connection = await manager.open_profile_database(pid, _PASSWORD)
        assert await _fk_pragma_on_distinct_connections(connection.engine) == 2
        # the key listener still runs first: the migrated schema is readable
        async with connection.engine.connect() as conn:
            n = (await conn.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE name='care_plan_task'"
            ))).scalar()
            assert n == 1
    finally:
        await manager.close_profile_database(pid)


# --------------------------------------------------------------------------
# HC-FK-003: test factory
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hc_fk_003_fk_profile_engine_factory_enforces():
    from tests.support.db import fk_profile_engine

    engine = fk_profile_engine()
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    finally:
        await engine.dispose()
