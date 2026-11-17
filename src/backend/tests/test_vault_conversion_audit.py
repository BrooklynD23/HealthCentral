"""HC-VCA — a one-time vault conversion leaves one master audit row
(VAULT-CONVERSION-AUDIT, owner WAVE-1116-EXTRA "Login audit accuracy", 2026-11-16).

`open_profile_database` converts a plaintext vault to SQLCipher on the first login
after SQLCipher becomes available (SQLCIPHER-WHEEL). The return value was thrown
away and nothing wrote a master audit row for either outcome. Now the manager records
`"converted"` or `"failed"` per profile, and login / unlock / recover write one
`profile.vault_conversion` row carrying that single word (`details.status`) and nothing else.

The key is `status`, not `outcome`: `core.audit._scrub_details` (AUDIT-PHI-001) drops every
key that is not on its allowlist and `outcome` is not on it, while `status` is.

These tests use real vault files and a real `sqlcipher3`, and real HTTP login against
a file-backed master DB. Only the platform gate is widened to every platform, as in
tests/test_vault_conversion.py. Without `sqlcipher3` the module skips, and fails under
CI or `HC_REQUIRE_SQLCIPHER=1`.
"""

from __future__ import annotations

import base64
import importlib
import json
import os
from pathlib import Path

import aiosqlite.core
import pytest
from sqlalchemy.orm import Session as SyncSession

import api.profiles as profiles_api
import core.profile_database as pdb
import core.sqlcipher_driver as sqlcipher_driver
from core.config import settings
from core.profile_database import ProfileDatabaseEncryptionError, get_profile_db_manager
from core.security import generate_encryption_key, hash_password, seal_key_with_dpapi
from core.time import utcnow
from models import AuditLog, Profile
from tests.support.master_db import audit_rows, make_master_db, profile_row, use_master
from tests.support.routes import route_client

PLAIN_HEADER = b"SQLite format 3\x00"
PROFILE_ID = "p-vca"
DISPLAY_NAME = "Vca Display Name"
PASSWORD = "Vca-Pass-2026"
EVENT = "profile.vault_conversion"


def _vc():
    return importlib.import_module("core.vault_conversion")


def _require_sqlcipher() -> None:
    if sqlcipher_driver.is_sqlcipher_available():
        return
    if os.environ.get("CI", "").lower() == "true" or os.environ.get("HC_REQUIRE_SQLCIPHER") == "1":
        pytest.fail("sqlcipher3 is not importable but CI / HC_REQUIRE_SQLCIPHER=1 requires it", pytrace=False)
    pytest.skip("needs sqlcipher3 (not importable in this venv); set HC_REQUIRE_SQLCIPHER=1 to make this a failure")


@pytest.fixture(autouse=True)
def _sqlcipher_needed(monkeypatch):
    _require_sqlcipher()
    # The product gate is Windows only; these tests run the conversion on every platform.
    monkeypatch.setattr(_vc(), "_CONVERSION_PLATFORMS", ("win32", "linux", "darwin"), raising=False)
    monkeypatch.setattr(_vc(), "_FAILURES", {}, raising=False)  # no cooldown carried between tests


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A sealed key, an (empty) vault dir, a real master DB with one locked profile."""
    monkeypatch.setattr(aiosqlite.core, "sqlite3", aiosqlite.core.sqlite3)  # restore at teardown
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "database_encryption_required", True)
    for key in ("login:testclient", "unlock:testclient"):
        profiles_api.auth_rate_limiter.reset(key)

    vault_dir = tmp_path / "vaults" / PROFILE_ID
    vault_dir.mkdir(parents=True)
    key = generate_encryption_key()
    sealed, method = seal_key_with_dpapi(key, fallback_password=PASSWORD, force_password=True)
    (vault_dir / "key.bin").write_bytes(sealed)
    (vault_dir / "key.method").write_text(method)
    hex_key = get_profile_db_manager()._key_to_hex(key)

    master = make_master_db(tmp_path)
    now = utcnow()
    with SyncSession(master.sync_engine()) as session:
        session.add(
            Profile(
                id=PROFILE_ID,
                display_name=DISPLAY_NAME,
                encryption_key_id=f"key-{PROFILE_ID}",
                password_hash=hash_password(PASSWORD),
                password_salt=base64.b64encode(b"\x00" * 16).decode("ascii"),
                is_locked=True,
                created_at=now,
                updated_at=now,
                last_accessed_at=None,
            )
        )
        session.commit()

    manager = get_profile_db_manager()
    manager._conversion_outcomes = {}
    yield vault_dir, key, hex_key, master
    # An open connection would outlive the test: close it through the loop-free path.
    import asyncio

    asyncio.run(manager.close_profile_database(PROFILE_ID))


def _plain_vault(vault_dir: Path, key: bytes, monkeypatch) -> Path:
    """Run the REAL profile migrations to head with SQLCipher switched off: a plain vault."""
    import core.migrations as migrations

    vault = vault_dir / "vault.db"
    with monkeypatch.context() as m:
        m.setattr(settings, "database_encryption_required", False)
        m.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)
        migrations.run_profile_migration(vault, key)
    assert vault.read_bytes()[:16] == PLAIN_HEADER
    return vault


def _login(client):
    return client.post("/profiles/login", json={"profile_id": PROFILE_ID, "password": PASSWORD})


def _unlock(client):
    return client.post(f"/profiles/{PROFILE_ID}/unlock", json={"password": PASSWORD})


def _close(manager) -> None:
    import asyncio

    asyncio.run(manager.close_profile_database(PROFILE_ID))


def _conversion_rows(master) -> list[AuditLog]:
    return [r for r in audit_rows(master) if r.event_type == EVENT]


def _events(master) -> list[str]:
    return [r.event_type for r in audit_rows(master)]


def test_hc_vca_001_login_on_a_plain_vault_converts_and_writes_one_row_before_the_login_row(
    env, monkeypatch
):
    vault_dir, key, _hex, master = env
    vault = _plain_vault(vault_dir, key, monkeypatch)

    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 200, response.text
    assert vault.read_bytes()[:16] != PLAIN_HEADER
    rows = _conversion_rows(master)
    assert len(rows) == 1
    assert json.loads(rows[0].details_json) == {"status": "converted"}
    events = _events(master)
    assert events.index(EVENT) < events.index("profile.login")


def test_hc_vca_002_a_failed_conversion_is_a_503_with_one_failed_row_and_no_login(env, monkeypatch):
    vault_dir, key, _hex, master = env
    vault = _plain_vault(vault_dir, key, monkeypatch)
    vc = _vc()

    def boom(*args, **kwargs):
        raise RuntimeError("verification blew up")

    monkeypatch.setattr(vc, "_verify_encrypted_copy", boom)
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 503, response.text
    assert response.json()["detail"] in {
        vc.FIXED_MESSAGE, vc.MSG_UNVERIFIED, vc.MSG_RECOVER, vc.MSG_PENDING,
        vc.MSG_HELD, vc.MSG_BUSY, vc.MSG_REPLACE_LOST,
    }
    rows = _conversion_rows(master)
    assert len(rows) == 1
    assert json.loads(rows[0].details_json) == {"status": "failed"}
    assert "profile.login" not in _events(master)
    assert profile_row(master, PROFILE_ID).is_locked is True
    assert vault.read_bytes()[:16] == PLAIN_HEADER, "the original vault stays plain and intact"


def test_hc_vca_003_a_second_login_writes_no_second_conversion_row(env, monkeypatch):
    vault_dir, key, _hex, master = env
    _plain_vault(vault_dir, key, monkeypatch)

    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        assert _login(client).status_code == 200
        assert _login(client).status_code == 200  # cached connection
        _close(get_profile_db_manager())
        assert _login(client).status_code == 200  # re-opened, already encrypted

    assert len(_conversion_rows(master)) == 1


def test_hc_vca_004a_an_already_encrypted_vault_writes_no_conversion_row(env, monkeypatch):
    vault_dir, key, hex_key, master = env
    vault = _plain_vault(vault_dir, key, monkeypatch)
    assert _vc().convert_plaintext_vault_if_needed(vault, hex_key) is True  # done before login
    assert vault.read_bytes()[:16] != PLAIN_HEADER

    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 200, response.text
    assert _conversion_rows(master) == []


def test_hc_vca_004b_off_windows_a_plain_vault_writes_no_conversion_row(env, monkeypatch):
    vault_dir, key, _hex, master = env
    vault = _plain_vault(vault_dir, key, monkeypatch)
    vc = _vc()
    monkeypatch.setattr(vc, "_CONVERSION_PLATFORMS", ("win32",))
    monkeypatch.setattr(vc, "_current_platform", lambda: "linux", raising=False)

    with route_client(profiles_api.router, "/profiles", raise_server_exceptions=False) as client:
        use_master(client, master)
        _login(client)  # whatever the open does with a plain vault, it is not a conversion

    assert _conversion_rows(master) == []
    assert vault.read_bytes()[:16] == PLAIN_HEADER, "nothing converted it"


def test_hc_vca_005_unlock_on_a_plain_vault_writes_the_converted_row_too(env, monkeypatch):
    vault_dir, key, _hex, master = env
    _plain_vault(vault_dir, key, monkeypatch)

    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _unlock(client)

    assert response.status_code == 200, response.text
    rows = _conversion_rows(master)
    assert len(rows) == 1
    assert json.loads(rows[0].details_json) == {"status": "converted"}
    events = _events(master)
    assert events.index(EVENT) < events.index("profile.unlock")


def test_hc_vca_006_the_row_carries_no_path_name_or_key(env, monkeypatch, tmp_path):
    vault_dir, key, hex_key, master = env
    _plain_vault(vault_dir, key, monkeypatch)

    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        assert _login(client).status_code == 200

    (row,) = _conversion_rows(master)
    whole = json.dumps(
        {c.name: str(getattr(row, c.name)) for c in AuditLog.__table__.columns}, sort_keys=True
    )
    for banned in (str(tmp_path), "vault.db", "key.bin", DISPLAY_NAME, hex_key, hex_key.lower(), PASSWORD):
        assert banned not in whole, banned
    # The only free-form field is the details, and it is one status word.
    assert json.loads(row.details_json) == {"status": "converted"}
    assert "vault" not in row.details_json.lower()
    assert row.action == EVENT


@pytest.mark.asyncio
async def test_hc_vca_007_outcome_is_popped_once_and_a_failure_reraises_the_original(env, monkeypatch):
    vault_dir, key, _hex, _master = env
    _plain_vault(vault_dir, key, monkeypatch)
    manager = get_profile_db_manager()

    connection = await manager.open_profile_database(PROFILE_ID, PASSWORD)
    assert connection is not None
    assert manager.pop_conversion_outcome(PROFILE_ID) == "converted"
    assert manager.pop_conversion_outcome(PROFILE_ID) is None
    await manager.close_profile_database(PROFILE_ID)

    # A failed conversion: the same exception object comes out, message untouched.
    original = ProfileDatabaseEncryptionError(_vc().MSG_HELD)

    def failing(path, hex_key):
        raise original

    plain_dir = vault_dir.parent / "vca-plain"
    plain_dir.mkdir()
    (plain_dir / "key.bin").write_bytes((vault_dir / "key.bin").read_bytes())
    (plain_dir / "key.method").write_text((vault_dir / "key.method").read_text())
    _plain_vault(plain_dir, key, monkeypatch)
    monkeypatch.setattr(pdb, "convert_plaintext_vault_if_needed", failing)

    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        await manager.open_profile_database("vca-plain", PASSWORD)

    assert info.value is original
    assert str(info.value) == _vc().MSG_HELD
    assert manager.pop_conversion_outcome("vca-plain") == "failed"
    assert manager.pop_conversion_outcome("vca-plain") is None


def test_hc_vca_008_an_audit_failure_on_the_failure_path_still_yields_the_original_503(env, monkeypatch):
    vault_dir, key, _hex, master = env
    _plain_vault(vault_dir, key, monkeypatch)
    vc = _vc()

    def boom(*args, **kwargs):
        raise RuntimeError("verification blew up")

    monkeypatch.setattr(vc, "_verify_encrypted_copy", boom)
    real = profiles_api.create_audit_log
    attempts: list[str] = []

    async def flaky(*args, **kwargs):
        if kwargs.get("event_type") == EVENT:
            attempts.append(EVENT)
            raise RuntimeError("audit write failed")
        return await real(*args, **kwargs)

    monkeypatch.setattr(profiles_api, "create_audit_log", flaky)
    with route_client(profiles_api.router, "/profiles", raise_server_exceptions=False) as client:
        use_master(client, master)
        response = _login(client)

    assert attempts == [EVENT], "the failure-path audit write must have been attempted"
    assert response.status_code == 503, response.text
    assert response.json()["detail"] != "audit write failed"
    assert response.json()["detail"] in {
        vc.FIXED_MESSAGE, vc.MSG_UNVERIFIED, vc.MSG_RECOVER, vc.MSG_PENDING,
        vc.MSG_HELD, vc.MSG_BUSY, vc.MSG_REPLACE_LOST,
    }
    assert _conversion_rows(master) == []
    assert "profile.login" not in _events(master)


def test_hc_vca_009_recover_on_a_plain_vault_writes_the_converted_row_after_the_rotation_rows(
    env, monkeypatch
):
    vault_dir, key, _hex, master = env
    vault = _plain_vault(vault_dir, key, monkeypatch)
    code = profiles_api._issue_recovery_code(PROFILE_ID, key)

    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = client.post(
            f"/profiles/{PROFILE_ID}/recover",
            json={"recovery_code": code, "new_password": "Brand-New-Pass-77"},
        )

    assert response.status_code == 200, response.text
    assert vault.read_bytes()[:16] != PLAIN_HEADER
    rows = _conversion_rows(master)
    assert len(rows) == 1
    assert json.loads(rows[0].details_json) == {"status": "converted"}
    # The open runs after the credential change and the rotation (RECOVER-ORDER-COMMIT).
    assert _events(master) == [
        "profile.recovered",
        "profile.recovery_code_generated",
        EVENT,
    ]
    assert profile_row(master, PROFILE_ID).is_locked is False
