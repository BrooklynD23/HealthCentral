"""SAFETY-MODE-SETTING: per-profile strict_safety_mode toggle.

GET/PATCH /assistant/safety-mode. Every HTTP test goes through route_client
with a real SQLite profile DB, so FastAPI's dependency graph runs
(recurring-failures #1, CLAUDE.md section 4).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.assistant as assistant_api
from core.auth import get_profile_db_session, require_auth
from core.profile_database import ProfileDatabaseBase
from tests.support.routes import route_client

PREFIX = "/assistant"
PATH = f"{PREFIX}/safety-mode"
MEMORY_PATH = f"{PREFIX}/memory-settings"
PROFILE_A = "profile-a"
PROFILE_B = "profile-b"


def _master_db(commit_error: Exception | None = None) -> MagicMock:
    db = MagicMock()
    db.commit = AsyncMock(side_effect=commit_error)
    return db


async def _open_vault(url: str):
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    return engine, AsyncSession(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def vault():
    engine, session = await _open_vault("sqlite+aiosqlite://")
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _call(method, profile_db, profile_id=PROFILE_A, json=None):
    master_db = _master_db()
    with route_client(
        assistant_api.router, PREFIX,
        profile_id=profile_id, master_db=master_db,
        raise_server_exceptions=False,
    ) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        resp = client.request(method, PATH, json=json)
    return resp, master_db


def _audit_rows(master_db):
    return [c.args[0] for c in master_db.add.call_args_list]


@pytest.mark.asyncio
async def test_hc_sms_001_new_profile_reads_false(vault):
    resp, _ = _call("GET", vault)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"strict_safety_mode": False}


@pytest.mark.asyncio
async def test_hc_sms_002_patch_true_persists_and_reads_back(vault):
    resp, _ = _call("PATCH", vault, json={"strict_safety_mode": True})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"strict_safety_mode": True}
    resp, _ = _call("GET", vault)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"strict_safety_mode": True}


@pytest.mark.asyncio
async def test_hc_sms_003_value_survives_lock_and_unlock(tmp_path):
    # A file-backed vault, so closing the engine really drops the connection.
    # Lock closes the profile DB; unlock reopens it from the same file.
    url = f"sqlite+aiosqlite:///{Path(tmp_path) / 'vault.db'}"
    engine, vault = await _open_vault(url)
    try:
        resp, _ = _call("PATCH", vault, json={"strict_safety_mode": True})
        assert resp.status_code == 200, resp.text
    finally:
        await vault.close()
        await engine.dispose()

    engine, vault = await _open_vault(url)
    try:
        resp, _ = _call("GET", vault)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"strict_safety_mode": True}
    finally:
        await vault.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_sms_004_profile_isolation(vault):
    # One shared DB on purpose: a dropped profile_id filter would leak A's row
    # to B. Production keeps one DB per profile, so this is the stricter form.
    resp, _ = _call("PATCH", vault, PROFILE_A, json={"strict_safety_mode": True})
    assert resp.status_code == 200, resp.text
    resp, _ = _call("GET", vault, PROFILE_A)
    assert resp.json() == {"strict_safety_mode": True}
    resp, _ = _call("GET", vault, PROFILE_B)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"strict_safety_mode": False}


@pytest.mark.asyncio
async def test_hc_sms_005_get_and_patch_each_write_one_audit_row_without_text(vault):
    resp, master = _call("GET", vault)
    assert resp.status_code == 200, resp.text
    rows = _audit_rows(master)
    assert len(rows) == 1
    assert rows[0].action == "safety_mode_viewed"
    assert rows[0].profile_id == PROFILE_A
    assert rows[0].details_json is None

    resp, master = _call("PATCH", vault, json={"strict_safety_mode": True})
    assert resp.status_code == 200, resp.text
    rows = _audit_rows(master)
    assert len(rows) == 1
    assert rows[0].action == "safety_mode_updated"
    assert rows[0].profile_id == PROFILE_A
    # The boolean only. A free-text value would be dropped by the allowlist.
    assert json.loads(rows[0].details_json) == {"strict_safety_mode": True}


def test_hc_sms_006_unauthenticated_get_matches_memory_settings():
    statuses = {}
    with route_client(
        assistant_api.router, PREFIX,
        master_db=_master_db(), raise_server_exceptions=False,
    ) as client:
        client.app.dependency_overrides.pop(require_auth)
        statuses["safety"] = client.get(PATH).status_code
        statuses["memory"] = client.get(MEMORY_PATH).status_code
    assert statuses["safety"] == statuses["memory"]
    assert statuses["safety"] == 401


def test_hc_sms_007_migration_round_trip_from_015(tmp_path, monkeypatch):
    from alembic import command
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine, event, inspect

    from core import migrations
    from core.config import settings
    from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available

    monkeypatch.setattr(settings, "database_encryption_required", False)
    vault_path = tmp_path / "vault.db"
    key = b"0" * 32

    migrations.run_profile_migration(vault_path, key)
    cfg = migrations._get_alembic_config("profile")
    head = ScriptDirectory.from_config(cfg).get_current_head()
    assert head == "016_strict_safety_mode"
    assert migrations.get_profile_current_revision(vault_path, key) == head

    def _columns():
        url = f"sqlite:///{vault_path}"
        if is_sqlcipher_available():
            mod = get_sqlcipher_module()
            engine = create_engine(url, creator=lambda: mod.connect(str(vault_path)))
        else:
            engine = create_engine(url)

        @event.listens_for(engine, "connect")
        def _key(dbapi_conn, _rec):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA cipher_version")
            row = cur.fetchone()
            if row and row[0]:
                cur.execute(f"PRAGMA key = \"x'{key.hex()}'\"")
            cur.close()

        try:
            return {c["name"] for c in inspect(engine).get_columns("user_model_settings")}
        finally:
            engine.dispose()

    cfg.attributes["vault_path"] = vault_path
    cfg.attributes["encryption_key"] = key
    command.downgrade(cfg, "015_data_donation")
    assert migrations.get_profile_current_revision(vault_path, key) == "015_data_donation"
    assert "strict_safety_mode" not in _columns()
    command.upgrade(cfg, "head")
    assert migrations.get_profile_current_revision(vault_path, key) == head
    assert "strict_safety_mode" in _columns()
