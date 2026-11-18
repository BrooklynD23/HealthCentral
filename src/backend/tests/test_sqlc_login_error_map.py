"""HC-SLEM — a failed vault open at login is a clear 503, never a bare 500 or a leak
(SQLC-LOGIN-ERROR-MAP, owner BUILD-1114, 2026-11-14).

`core.auth.open_profile_database_on_login` is the one choke point for login, unlock,
create and recover. A `ProfileDatabaseEncryptionError` carrying one of the seven fixed,
path-free messages of `core.vault_conversion` reaches the user as 503 with that exact
text. Any other `ProfileDatabaseEncryptionError` (a path, a key, a how-to-turn-encryption-off
hint) gets one fixed generic sentence. Every request goes through HTTP against a real,
file-backed master DB; only the per-profile vault manager is a stub.
"""

from __future__ import annotations

import base64
import logging

import pytest
from sqlalchemy.orm import Session as SyncSession

import api.profiles as profiles_api
import core.auth as auth_module
from core import vault_conversion as vc
from core.profile_database import ProfileDatabaseEncryptionError
from core.security import hash_password
from core.time import utcnow
from models import Profile
from tests.support.master_db import make_master_db, use_master
from tests.support.routes import route_client

PASSWORD = "Testing123!"
PROFILE_ID = "p-slem"
GENERIC = "Encrypted storage could not be opened for this profile. Your data was not changed."
CONSTANTS = [
    vc.FIXED_MESSAGE,
    vc.MSG_UNVERIFIED,
    vc.MSG_RECOVER,
    vc.MSG_PENDING,
    vc.MSG_HELD,
    vc.MSG_BUSY,
    vc.MSG_REPLACE_LOST,
]
SQLCIPHER_TEXT = (
    "SQLCipher is not available but database encryption is required. Install it or "
    "set DATABASE_ENCRYPTION_REQUIRED=false to continue without encryption."
)
PATH_KEY_TEXT = r"vault at C:\Users\x\vault.db key=ABCD"


class _StubManager:
    """Stands in for the profile DB manager; its open raises the given error."""

    def __init__(self, error: Exception):
        self.error = error
        self.calls = 0

    async def open_profile_database(self, profile_id, password):
        self.calls += 1
        raise self.error


def _seed(db) -> None:
    now = utcnow()
    with SyncSession(db.sync_engine()) as session:
        session.add(
            Profile(
                id=PROFILE_ID,
                display_name="Slem",
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


@pytest.fixture
def master(tmp_path, monkeypatch):
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    for key in ("login:testclient", "unlock:testclient"):
        profiles_api.auth_rate_limiter.reset(key)
    db = make_master_db(tmp_path)
    _seed(db)
    return db


def _stub(monkeypatch, error: Exception) -> _StubManager:
    stub = _StubManager(error)
    monkeypatch.setattr(auth_module, "get_profile_db_manager", lambda: stub)
    return stub


def _login(client, password: str = PASSWORD):
    return client.post("/profiles/login", json={"profile_id": PROFILE_ID, "password": password})


@pytest.mark.parametrize("message", CONSTANTS)
def test_hc_slem_001_conversion_message_reaches_the_user_as_503(master, monkeypatch, message):
    _stub(monkeypatch, ProfileDatabaseEncryptionError(message))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == message


def test_hc_slem_002_encryption_setup_hint_is_replaced_by_generic_text(master, monkeypatch):
    _stub(monkeypatch, ProfileDatabaseEncryptionError(SQLCIPHER_TEXT))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == GENERIC
    for leaked in ("DATABASE_ENCRYPTION_REQUIRED", "SQLCipher", "false"):
        assert leaked not in response.text


def test_hc_slem_003_unknown_encryption_error_leaks_no_path_or_key(master, monkeypatch):
    _stub(monkeypatch, ProfileDatabaseEncryptionError(PATH_KEY_TEXT))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == GENERIC
    assert "C:\\" not in response.text
    assert "ABCD" not in response.text


def test_hc_slem_004_other_errors_are_still_a_500(master, monkeypatch):
    _stub(monkeypatch, RuntimeError("boom"))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 500, response.text
    assert response.json()["detail"] == "Failed to open profile database"


def test_hc_slem_005_wrong_password_is_still_401_and_never_opens_the_vault(master, monkeypatch):
    stub = _stub(monkeypatch, ProfileDatabaseEncryptionError(vc.MSG_HELD))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client, password="Wrong-password-1")

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Invalid credentials"
    assert stub.calls == 0


def test_hc_slem_006_unlock_goes_through_the_same_mapping(master, monkeypatch):
    _stub(monkeypatch, ProfileDatabaseEncryptionError(vc.MSG_HELD))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = client.post(f"/profiles/{PROFILE_ID}/unlock", json={"password": PASSWORD})

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == vc.MSG_HELD


def test_hc_slem_007_log_line_names_profile_and_class_not_the_message(
    master, monkeypatch, caplog
):
    _stub(monkeypatch, ProfileDatabaseEncryptionError(PATH_KEY_TEXT))
    with caplog.at_level(logging.ERROR, logger="core.auth"):
        with route_client(profiles_api.router, "/profiles") as client:
            use_master(client, master)
            _login(client)

    lines = [r.getMessage() for r in caplog.records if r.name == "core.auth"]
    mapped = [m for m in lines if "could not be opened" in m]
    assert len(mapped) == 1, lines
    assert PROFILE_ID in mapped[0]
    assert "ProfileDatabaseEncryptionError" in mapped[0]
    assert "ABCD" not in mapped[0]
    assert "C:\\" not in mapped[0]
