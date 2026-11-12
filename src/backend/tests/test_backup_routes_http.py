"""HTTP route tests for backup schedule, verify, prune and restore refusals (BACKUP-ROUTES-HTTP).

Every test goes through `route_client`, so FastAPI's dependency graph runs. The master DB is a
real in-memory SQLite session (not a mock), so audit rows are read back from the table.
Would NOT notice: a route that audits correctly but with details_json carrying PHI (only the
schedule route's action/row count is checked here), and the real SQLCipher vault (backups here
snapshot plain-SQLite vaults, same as test_backup_routes.py).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.backup as backup_api
from core.database import Base
from core.time import utcnow
from models import AuditLog, Profile
from tests.support.routes import route_client

PROFILES = ("profile-a", "profile-b")


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """app_data_path -> tmp dir with two seeded profiles (same shape as test_backup_routes.py)."""
    monkeypatch.setattr(
        type(backup_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    for pid in PROFILES:
        vault = tmp_path / "vaults" / pid
        vault.mkdir(parents=True)
        conn = sqlite3.connect(vault / "vault.db")
        conn.execute("CREATE TABLE observations (id TEXT)")
        conn.commit()
        conn.close()
        (vault / "key.bin").write_bytes(b"sealed-" + pid.encode())
        (vault / "key.method").write_text("password")
    conn = sqlite3.connect(tmp_path / "asclexis.db")
    conn.execute("CREATE TABLE profiles (id TEXT)")
    conn.executemany("INSERT INTO profiles VALUES (?)", [(p,) for p in PROFILES])
    conn.commit()
    conn.close()
    return tmp_path


@pytest_asyncio.fixture
async def real_master():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.fixture(autouse=True)
def _fresh_rate_limiter():
    for pid in PROFILES:
        backup_api.auth_rate_limiter.reset(f"restore:testclient:{pid}")
    yield
    for pid in PROFILES:
        backup_api.auth_rate_limiter.reset(f"restore:testclient:{pid}")


async def _rows(db, event_type):
    return (
        (await db.execute(select(AuditLog).where(AuditLog.event_type == event_type)))
        .scalars()
        .all()
    )


def _make_backup(client) -> str:
    resp = client.post("/backup/")
    assert resp.status_code == 201, resp.text
    return resp.json()["backup_id"]


def _age(root, backup_id, new_id, days):
    """Copy a real backup to `new_id` and back-date its manifest `days` days."""
    dest = root / new_id
    shutil.copytree(root / backup_id, dest)
    manifest = json.loads((dest / "manifest.json").read_text())
    manifest["created_at"] = (utcnow() - timedelta(days=days)).isoformat() + "Z"
    (dest / "manifest.json").write_text(json.dumps(manifest))
    return dest


def _first_backed_up_file(path):
    manifest = json.loads((path / "manifest.json").read_text())
    return path / manifest["files"][0]["path"]


# --------------------------------------------------------------------------- schedule


@pytest.mark.asyncio
async def test_hc_brh_001_put_schedule_stores_echoes_and_audits_once(real_master, caplog):
    """PUT /backup/schedule: 200, GET echoes it, one registered audit row.
    Would NOT notice: the audit row's profile_id is checked only for profile-a."""
    with route_client(backup_api.router, "/backup", master_db=real_master) as client:
        put = client.put(
            "/backup/schedule",
            json={"enabled": True, "frequency": "weekly", "retention_days": 14},
        )
        got = client.get("/backup/schedule")
    assert put.status_code == 200, put.text
    assert (put.json()["enabled"], put.json()["frequency"], put.json()["retention_days"]) == (
        True, "weekly", 14,
    )
    assert got.status_code == 200, got.text
    assert (got.json()["enabled"], got.json()["frequency"], got.json()["retention_days"]) == (
        True, "weekly", 14,
    )
    assert not [r for r in caplog.records if "Unregistered audit action" in r.getMessage()]
    rows = await _rows(real_master, "backup.schedule")
    assert len(rows) == 1, [r.event_type for r in rows]
    assert rows[0].action == "Updated backup schedule"
    assert rows[0].profile_id == "profile-a"
    assert rows[0].entity_id == "schedule"


@pytest.mark.asyncio
async def test_hc_brh_002_invalid_frequency_is_400_and_stored_value_unchanged(real_master):
    with route_client(backup_api.router, "/backup", master_db=real_master) as client:
        ok = client.put(
            "/backup/schedule",
            json={"enabled": True, "frequency": "daily", "retention_days": 7},
        )
        bad = client.put(
            "/backup/schedule",
            json={"enabled": True, "frequency": "hourly", "retention_days": 99},
        )
        got = client.get("/backup/schedule")
    assert ok.status_code == 200, ok.text
    assert bad.status_code == 400, bad.text
    assert got.json()["frequency"] == "daily"
    assert got.json()["retention_days"] == 7
    assert got.json()["enabled"] is True
    assert len(await _rows(real_master, "backup.schedule")) == 1, "rejected PUT must not audit a change"


@pytest.mark.asyncio
async def test_hc_brh_003_enabled_with_frequency_off_comes_back_disabled(real_master):
    with route_client(backup_api.router, "/backup", master_db=real_master) as client:
        put = client.put(
            "/backup/schedule",
            json={"enabled": True, "frequency": "off", "retention_days": 30},
        )
        got = client.get("/backup/schedule")
    assert put.status_code == 200, put.text
    assert put.json()["enabled"] is False
    assert put.json()["frequency"] == "off"
    assert got.json()["enabled"] is False


# --------------------------------------------------------------------------- verify


@pytest.mark.asyncio
async def test_hc_brh_004_verify_valid_then_corrupt_each_audited(data_dir, real_master):
    root = data_dir / "backups" / "profile-a"
    with route_client(backup_api.router, "/backup", master_db=real_master) as client:
        backup_id = _make_backup(client)
        first = client.post(f"/backup/{backup_id}/verify")
        assert first.status_code == 200, first.text
        assert first.json()["valid"] is True
        assert first.json()["errors"] == []
        assert first.json()["files_checked"] > 0

        _first_backed_up_file(root / backup_id).write_bytes(b"corrupted")
        second = client.post(f"/backup/{backup_id}/verify")
    assert second.status_code == 200, second.text
    assert second.json()["valid"] is False
    assert second.json()["errors"], "a corrupt backup must say why"
    rows = await _rows(real_master, "backup.verify")
    assert len(rows) == 2, [r.event_type for r in rows]
    assert all(r.action == "Verified backup" and r.profile_id == "profile-a" for r in rows)
    assert all(r.entity_id == backup_id for r in rows)


@pytest.mark.asyncio
async def test_hc_brh_005_verify_refuses_other_profile_and_bad_ids(data_dir, real_master):
    with route_client(
        backup_api.router, "/backup", profile_id="profile-b", master_db=real_master
    ) as client_b:
        b_id = _make_backup(client_b)
    with route_client(backup_api.router, "/backup", master_db=real_master) as client_a:
        other = client_a.post(f"/backup/{b_id}/verify")
        missing = client_a.post("/backup/backup_19990101_000000/verify")
        traversal = client_a.post(f"/backup/..%2Fprofile-b%2F{b_id}/verify")
    assert other.status_code == 404, other.text
    assert missing.status_code == 404, missing.text
    # Starlette may decode %2F before routing (no route -> 404) or the handler may refuse (400).
    assert traversal.status_code in (400, 404), traversal.text
    assert not await _rows(real_master, "backup.verify"), "refusals must not audit a verify"


# --------------------------------------------------------------------------- prune


@pytest.mark.asyncio
async def test_hc_brh_006_prune_removes_only_old_backups_of_this_profile(data_dir, real_master):
    root_a = data_dir / "backups" / "profile-a"
    root_b = data_dir / "backups" / "profile-b"
    with route_client(
        backup_api.router, "/backup", profile_id="profile-b", master_db=real_master
    ) as client_b:
        b_seed = _make_backup(client_b)
    with route_client(backup_api.router, "/backup", master_db=real_master) as client_a:
        a_new = _make_backup(client_a)
        _age(root_a, a_new, "backup_20000101_000000", days=400)
        _age(root_a, a_new, "backup_20000102_000000", days=400)
        _age(root_b, b_seed, "backup_20000101_000000", days=400)
        resp = client_a.post("/backup/prune", json={"retention_days": 30})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"removed": 2}
    assert sorted(p.name for p in root_a.iterdir()) == [a_new]
    assert sorted(p.name for p in root_b.iterdir()) == sorted(
        [b_seed, "backup_20000101_000000"]
    ), "another profile's old backup must survive"
    rows = await _rows(real_master, "backup.prune")
    assert len(rows) == 1 and rows[0].profile_id == "profile-a"


# --------------------------------------------------------------------------- restore refusals


def _restore_body(password="CorrectHorse1", phrase=None):
    return {
        "password": password,
        "confirmation_phrase": phrase or backup_api.BACKUP_RESTORE_CONFIRMATION,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case,expected",
    [("password", 401), ("phrase", 400), ("corrupt", 400)],
)
async def test_hc_brh_007_restore_refusals_have_exact_codes(
    data_dir, real_master, monkeypatch, case, expected
):
    """Order in the route: password (401), then phrase (400), then verify (400). Each case
    changes only its own input; the vault must be untouched after a refusal."""
    real_master.add(
        Profile(
            id="profile-a", display_name="T", encryption_key_id="k", password_hash="x",
            created_at=utcnow(), updated_at=utcnow(),
        )
    )
    await real_master.commit()
    ok_user = AsyncMock(return_value=SimpleNamespace(id="profile-a"))
    monkeypatch.setattr(backup_api, "authenticate_profile", ok_user)
    close = AsyncMock()
    monkeypatch.setattr(backup_api, "close_profile_database_on_logout", close)
    vault_db = data_dir / "vaults" / "profile-a" / "vault.db"

    with route_client(backup_api.router, "/backup", master_db=real_master) as client:
        backup_id = _make_backup(client)
        before = vault_db.read_bytes()
        body = _restore_body()
        if case == "password":
            monkeypatch.setattr(
                backup_api, "authenticate_profile", AsyncMock(return_value=None)
            )
        elif case == "phrase":
            body = _restore_body(phrase="yes please")
        else:
            _first_backed_up_file(data_dir / "backups" / "profile-a" / backup_id).write_bytes(
                b"corrupted"
            )
        resp = client.post(f"/backup/{backup_id}/restore", json=body)
    assert resp.status_code == expected, resp.text
    assert vault_db.read_bytes() == before
    close.assert_not_called()
    assert not await _rows(real_master, "backup.restore"), "a refusal must not record a restore"


# --------------------------------------------------------------------------- auth


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "/backup/", None),
        ("post", "/backup/", None),
        ("post", "/backup/backup_x/verify", None),
        ("get", "/backup/backup_x/download", None),
        ("post", "/backup/backup_x/restore", _restore_body()),
        ("post", "/backup/prune", {"retention_days": 30}),
        ("get", "/backup/schedule", None),
        ("put", "/backup/schedule", {"enabled": True, "frequency": "daily", "retention_days": 7}),
    ],
)
def test_hc_brh_008_every_route_is_401_without_a_session(data_dir, method, path, body):
    with route_client(backup_api.router, "/backup", real_auth=True) as client:
        resp = getattr(client, method)(path, **({"json": body} if body is not None else {}))
    assert resp.status_code == 401, resp.text
