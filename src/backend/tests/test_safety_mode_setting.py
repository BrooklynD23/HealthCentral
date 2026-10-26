"""SAFETY-MODE-SETTING: per-profile strict_safety_mode toggle.

GET/PATCH /assistant/safety-mode. Every HTTP test goes through route_client
with a real SQLite profile DB, so FastAPI's dependency graph runs
(recurring-failures #1, CLAUDE.md section 4).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.assistant as assistant_api
import api.profiles as profiles_api
from core.auth import get_profile_db_session, require_auth
from core.profile_database import ProfileDatabaseBase
from models.model_settings import UserModelSettings
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


def _call(method, profile_db, profile_id=PROFILE_A, json=None, commit_error=None):
    master_db = _master_db(commit_error)
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


def _lock_profile(profile_id: str, close_profile_db) -> object:
    """POST /profiles/{id}/lock through the real profiles router."""
    profile = SimpleNamespace(
        id=profile_id, display_name="T", is_locked=False, password_hash="x",
        created_at=datetime(2026, 10, 24), last_accessed_at=None,
    )
    found = MagicMock()
    found.scalar_one_or_none.return_value = profile
    master = MagicMock()
    master.execute = AsyncMock(return_value=found)
    master.commit = AsyncMock()
    with patch.object(profiles_api, "close_profile_database_on_logout", close_profile_db), \
         patch.object(profiles_api, "log_profile_event", AsyncMock()), \
         patch.object(profiles_api, "revoke_jwt_token", MagicMock()), \
         route_client(profiles_api.router, "/profiles", profile_id=profile_id,
                      master_db=master) as client:
        return client.post(f"/profiles/{profile_id}/lock")


@pytest.mark.asyncio
async def test_hc_sms_001_new_profile_reads_false(vault):
    resp, _ = _call("GET", vault)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"strict_safety_mode": False}
    assert await assistant_api.is_strict_safety_mode(vault) is False


@pytest.mark.asyncio
async def test_hc_sms_002_patch_true_persists_and_reads_back(vault):
    resp, _ = _call("PATCH", vault, json={"strict_safety_mode": True})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"strict_safety_mode": True}
    resp, _ = _call("GET", vault)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"strict_safety_mode": True}
    assert await assistant_api.is_strict_safety_mode(vault) is True
    resp, _ = _call("PATCH", vault, json={"strict_safety_mode": False})
    assert resp.status_code == 200, resp.text
    assert await assistant_api.is_strict_safety_mode(vault) is False

    # Two first-time writers can each insert a row for one profile: profile_id
    # is indexed, not unique. Here the OFF row is returned first. The helper
    # must still fail closed and report ON.
    engine, racy = await _open_vault("sqlite+aiosqlite://")
    try:
        racy.add(UserModelSettings(id="race-off", profile_id=PROFILE_A, strict_safety_mode=False))
        await racy.commit()
        racy.add(UserModelSettings(id="race-on", profile_id=PROFILE_A, strict_safety_mode=True))
        await racy.commit()
        assert await assistant_api.is_strict_safety_mode(racy) is True
    finally:
        await racy.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_sms_003_value_survives_lock_and_unlock(tmp_path):
    # File-backed vault, so a real close really drops the connection. Lock runs
    # through POST /profiles/{id}/lock. Only the per-profile close hook is
    # stubbed, and the stub disposes this vault's engine. Unlock reopens the
    # same file.
    url = f"sqlite+aiosqlite:///{Path(tmp_path) / 'vault.db'}"
    engine, vault = await _open_vault(url)
    closed: list[str] = []

    async def _close_profile_db(profile_id: str) -> None:
        closed.append(profile_id)
        await vault.close()
        await engine.dispose()

    try:
        resp, _ = _call("PATCH", vault, json={"strict_safety_mode": True})
        assert resp.status_code == 200, resp.text
        lock = _lock_profile(PROFILE_A, _close_profile_db)
        assert lock.status_code == 200, lock.text
        assert closed == [PROFILE_A]
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
    # Production keeps one vault per profile (vaults/<profile_id>). Check the
    # helper that way: A's vault is ON and B's vault is OFF.
    engine_b, vault_b = await _open_vault("sqlite+aiosqlite://")
    try:
        resp, _ = _call("PATCH", vault, PROFILE_A, json={"strict_safety_mode": True})
        assert resp.status_code == 200, resp.text
        assert await assistant_api.is_strict_safety_mode(vault) is True
        assert await assistant_api.is_strict_safety_mode(vault_b) is False
        resp, _ = _call("GET", vault_b, PROFILE_B)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"strict_safety_mode": False}
    finally:
        await vault_b.close()
        await engine_b.dispose()

    # One shared DB on purpose: a dropped profile_id filter would leak A's row
    # to B at the route. Stricter than production, which never shares a vault.
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
    master.commit.assert_awaited_once()
    assert rows[0].action == "safety_mode_viewed"
    assert rows[0].profile_id == PROFILE_A
    assert rows[0].details_json is None

    resp, master = _call("PATCH", vault, json={"strict_safety_mode": True})
    assert resp.status_code == 200, resp.text
    rows = _audit_rows(master)
    assert len(rows) == 1
    master.commit.assert_awaited_once()
    assert rows[0].action == "safety_mode_updated"
    assert rows[0].profile_id == PROFILE_A
    # Field names and an enum status only. The boolean itself is not logged:
    # `strict_safety_mode` is not in the audit allowlist, so it would be scrubbed.
    details = json.loads(rows[0].details_json)
    assert details == {"changed_fields": ["strict_safety_mode"], "status": "enabled"}
    assert "_scrubbed" not in details

    resp, master = _call("PATCH", vault, json={"strict_safety_mode": False})
    assert resp.status_code == 200, resp.text
    rows = _audit_rows(master)
    assert len(rows) == 1
    master.commit.assert_awaited_once()
    details = json.loads(rows[0].details_json)
    assert details == {"changed_fields": ["strict_safety_mode"], "status": "disabled"}
    assert "_scrubbed" not in details

    # Fail closed: an audit commit that raises fails the request. A GET serves
    # no value. A PATCH logs AUDIT-ORDER, because the change commits first.
    resp, _ = _call("GET", vault, commit_error=RuntimeError("audit down"))
    assert resp.status_code == 500
    assert "strict_safety_mode" not in resp.text

    with patch.object(assistant_api, "logger") as log:
        resp, _ = _call(
            "PATCH", vault, json={"strict_safety_mode": True},
            commit_error=RuntimeError("audit down"),
        )
    assert resp.status_code == 500
    assert any("AUDIT-ORDER" in str(c.args[0]) for c in log.error.call_args_list)


@pytest.mark.asyncio
async def test_hc_sms_006_unauthenticated_requests_match_memory_settings_and_write_nothing(vault):
    statuses = {}
    with route_client(
        assistant_api.router, PREFIX,
        master_db=_master_db(), raise_server_exceptions=False,
    ) as client:
        client.app.dependency_overrides.pop(require_auth)

        async def _profile_db():
            return vault
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        statuses["safety_get"] = client.get(PATH).status_code
        statuses["memory_get"] = client.get(MEMORY_PATH).status_code
        statuses["safety_patch"] = client.patch(
            PATH, json={"strict_safety_mode": True},
        ).status_code
    assert statuses["safety_get"] == statuses["memory_get"] == 401
    assert statuses["safety_patch"] == 401
    # The 401 must stop the write before it reaches the profile DB.
    rows = (await vault.execute(select(UserModelSettings))).scalars().all()
    assert rows == []


def test_hc_sms_007_migration_round_trip_from_015(tmp_path, monkeypatch):
    from alembic import command
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine, event, inspect, text

    from core import migrations
    from core.config import settings
    from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available

    monkeypatch.setattr(settings, "database_encryption_required", False)
    vault_path = tmp_path / "vault.db"
    key = b"0" * 32
    revision = "016_strict_safety_mode"

    migrations.run_profile_migration(vault_path, key)
    cfg = migrations._get_alembic_config("profile")
    script = ScriptDirectory.from_config(cfg)
    # Use the revision's own parent, not the moving head, so a later migration
    # does not break this test. The parent is the I-7 contract.
    prior = script.get_revision(revision).down_revision
    assert prior == "015_data_donation"
    assert migrations.get_profile_current_revision(vault_path, key) == script.get_current_head()

    def _engine():
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

        return engine

    def _columns():
        engine = _engine()
        try:
            return {c["name"] for c in inspect(engine).get_columns("user_model_settings")}
        finally:
            engine.dispose()

    def _query(sql, params=None):
        engine = _engine()
        try:
            with engine.begin() as conn:
                result = conn.execute(text(sql), params or {})
                return [tuple(r) for r in result.fetchall()] if result.returns_rows else []
        finally:
            engine.dispose()

    cfg.attributes["vault_path"] = vault_path
    cfg.attributes["encryption_key"] = key
    command.downgrade(cfg, prior)
    assert migrations.get_profile_current_revision(vault_path, key) == prior
    assert "strict_safety_mode" not in _columns()

    # A profile that already exists before 016 gets a row without the column.
    _query(
        "INSERT INTO user_model_settings (id, profile_id, preferred_tier, "
        "auto_detect_enabled, use_external_api, external_api_provider, "
        "external_api_key_encrypted, timezone, voice_logging_enabled, "
        "voice_modal_seen, ocr_preference_enabled, assistant_memory_enabled, "
        "agent_enabled, streaks_hidden, created_at, updated_at) "
        "VALUES (:id, :pid, 'low', 1, 0, '', '', 'UTC', 0, 0, 1, 1, 1, 0, "
        "'2026-10-01 00:00:00', '2026-10-01 00:00:00')",
        {"id": "pre-016-row", "pid": PROFILE_A},
    )

    command.upgrade(cfg, revision)
    assert migrations.get_profile_current_revision(vault_path, key) == revision
    assert "strict_safety_mode" in _columns()
    # The existing row must read OFF after the upgrade (server_default "0").
    assert _query(
        "SELECT strict_safety_mode FROM user_model_settings WHERE id = 'pre-016-row'"
    ) == [(0,)]
