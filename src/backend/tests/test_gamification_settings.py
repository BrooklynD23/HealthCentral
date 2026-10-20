"""C-GAM2B: streaks_hidden setting. GET/PATCH /settings/model/gamification (I-19).

Every HTTP test goes through route_client so FastAPI's dependency graph runs
(recurring-failures #1).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.model_settings as model_settings_api
from core.auth import get_profile_db_session, require_auth
from core.profile_database import ProfileDatabaseBase
from tests.support.routes import route_client

PREFIX = "/settings/model"
PATH = f"{PREFIX}/gamification"
PROFILE_A = "profile-a"
PROFILE_B = "profile-b"


def _master_db(commit_error: Exception | None = None) -> MagicMock:
    db = MagicMock()
    db.commit = AsyncMock(side_effect=commit_error)
    return db


async def _new_vault():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    return engine, AsyncSession(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def vault():
    engine, session = await _new_vault()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _call(method, profile_db, profile_id=PROFILE_A, master_db=None, json=None):
    master_db = master_db if master_db is not None else _master_db()
    with route_client(
        model_settings_api.router, PREFIX,
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


@pytest.mark.parametrize("method,body", [("GET", None), ("PATCH", {"streaks_hidden": True})])
def test_hc_gamset_001_requires_auth(method, body):
    with route_client(model_settings_api.router, PREFIX, master_db=_master_db()) as client:
        client.app.dependency_overrides.pop(require_auth)
        resp = client.request(method, PATH, json=body)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_hc_gamset_002_default_is_false(vault):
    resp, _ = _call("GET", vault)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"streaks_hidden": False}


@pytest.mark.asyncio
async def test_hc_gamset_003_patch_persists(vault):
    resp, _ = _call("PATCH", vault, json={"streaks_hidden": True})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"streaks_hidden": True}
    resp, _ = _call("GET", vault)
    assert resp.json() == {"streaks_hidden": True}
    resp, _ = _call("PATCH", vault, json={"streaks_hidden": False})
    assert resp.json() == {"streaks_hidden": False}


@pytest.mark.asyncio
async def test_hc_gamset_004_isolated_by_profile_vault():
    eng_a, vault_a = await _new_vault()
    eng_b, vault_b = await _new_vault()
    try:
        resp, _ = _call("PATCH", vault_a, PROFILE_A, json={"streaks_hidden": True})
        assert resp.status_code == 200, resp.text
        resp, _ = _call("GET", vault_a, PROFILE_A)
        assert resp.json() == {"streaks_hidden": True}
        resp, _ = _call("GET", vault_b, PROFILE_B)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"streaks_hidden": False}
    finally:
        await vault_a.close()
        await vault_b.close()
        await eng_a.dispose()
        await eng_b.dispose()


@pytest.mark.asyncio
async def test_hc_gamset_005_one_master_audit_row_per_call(vault):
    resp, master = _call("GET", vault)
    assert resp.status_code == 200, resp.text
    rows = _audit_rows(master)
    assert len(rows) == 1
    assert rows[0].event_type == "settings.gamification.view"
    assert rows[0].entity_type == "settings"
    assert rows[0].entity_id == "gamification"
    assert rows[0].profile_id == PROFILE_A

    resp, master = _call("PATCH", vault, json={"streaks_hidden": True})
    assert resp.status_code == 200, resp.text
    rows = _audit_rows(master)
    assert len(rows) == 1
    assert rows[0].event_type == "settings.gamification.update"
    assert rows[0].entity_id == "gamification"
    assert "changed_fields" in rows[0].details_json
    assert "streaks_hidden" in rows[0].details_json


@pytest.mark.asyncio
@pytest.mark.parametrize("method,body", [("GET", None), ("PATCH", {"streaks_hidden": True})])
async def test_hc_gamset_006_fails_closed_when_audit_commit_fails(vault, method, body):
    resp, _ = _call(method, vault, master_db=_master_db(RuntimeError("audit down")), json=body)
    assert resp.status_code == 500


def test_hc_gamset_007_migration_round_trip(tmp_path, monkeypatch):
    from alembic import command
    from alembic.script import ScriptDirectory

    from core import migrations
    from core.config import settings

    monkeypatch.setattr(settings, "database_encryption_required", False)
    versions = Path(__file__).parent.parent / "migrations" / "profile" / "versions"
    src = (versions / "014_streaks_hidden.py").read_text()
    prev = re.search(r'^down_revision[^=]*=\s*"([^"]+)"', src, re.M).group(1)
    assert prev == "013_adaptive_windows_local"

    vault_path = tmp_path / "vault.db"
    key = b"0" * 32
    migrations.run_profile_migration(vault_path, key)
    head_cfg = migrations._get_alembic_config("profile")
    head = ScriptDirectory.from_config(head_cfg).get_current_head()
    assert migrations.get_profile_current_revision(vault_path, key) == head

    def _cols():
        from sqlalchemy import create_engine, event, inspect

        from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available

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

    cfg = migrations._get_alembic_config("profile")
    cfg.attributes["vault_path"] = vault_path
    cfg.attributes["encryption_key"] = key

    command.downgrade(cfg, prev)
    assert migrations.get_profile_current_revision(vault_path, key) == prev
    assert "streaks_hidden" not in _cols()
    command.upgrade(cfg, "head")
    assert migrations.get_profile_current_revision(vault_path, key) == head
    assert "streaks_hidden" in _cols()
