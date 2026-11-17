"""HC-LOO — the vault is opened before the master DB says "signed in"
(LOGIN-OPEN-ORDER, owner WAVE-1116-EXTRA "Login audit accuracy", 2026-11-16).

Before this, `login` and `unlock_profile` set `is_locked = False`, wrote the
`profile.login` / `profile.unlock` audit row and committed, and only then opened
the per-profile vault. A vault that failed to open (a 503 since SQLC-LOGIN-ERROR-MAP)
left the master record saying "login" and the profile unlocked, with no session.

`recover_profile` keeps its credential commit and its recovery-code rotation where
they are (RECOVER-ORDER-COMMIT): the password really did change before the open.
Only the unlock flag moves to after a successful open.

Every request goes through HTTP against a real, file-backed master DB. Only the
per-profile vault manager is a stub. Its `open_profile_database` records what the
master DB said at the moment of the open, which is what these tests assert on.
"""

from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

import api.profiles as profiles_api
import core.auth as auth_module
from core import vault_conversion as vc
from core.profile_database import ProfileDatabaseEncryptionError, get_profile_db_manager
from core.security import generate_encryption_key, hash_password, verify_password
from core.time import utcnow
from models import Profile
from tests.support.master_db import audit_rows, make_master_db, profile_row, use_master
from tests.support.routes import route_client

PASSWORD = "Testing123!"
NEW_PASSWORD = "Brand-New-Pass-77"
PROFILE_ID = "p-loo"


class _Manager:
    """Stands in for the profile DB manager.

    Path and key-file helpers come from the real singleton (they only read
    `settings.app_data_path`, which the fixture points at tmp_path). `open` and
    `close` are the stub.
    """

    def __init__(self, master, error: Exception | None = None):
        self.master = master
        self.error = error
        self.opened: list[dict] = []
        self.closed: list[str] = []
        self.after_open = None

    def __getattr__(self, name):
        return getattr(get_profile_db_manager(), name)

    async def open_profile_database(self, profile_id, password):
        row = profile_row(self.master, profile_id)
        self.opened.append(
            {
                "is_locked": row.is_locked,
                "last_accessed_at": row.last_accessed_at,
                "events": [r.event_type for r in audit_rows(self.master)],
            }
        )
        if self.error is not None:
            raise self.error
        if self.after_open is not None:
            self.after_open()
        return SimpleNamespace(fk_cleanup_counts={})

    async def close_profile_database(self, profile_id):
        self.closed.append(profile_id)


def _seed(db) -> None:
    now = utcnow()
    with SyncSession(db.sync_engine()) as session:
        session.add(
            Profile(
                id=PROFILE_ID,
                display_name="Loo Display Name",
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
    (tmp_path / "vaults" / PROFILE_ID).mkdir(parents=True)
    for key in ("login:testclient", "unlock:testclient"):
        profiles_api.auth_rate_limiter.reset(key)
    profiles_api.recovery_rate_limiter.reset(f"recover:testclient:{PROFILE_ID}")
    db = make_master_db(tmp_path)
    _seed(db)
    return db


def _install(monkeypatch, master, error: Exception | None = None) -> _Manager:
    manager = _Manager(master, error)
    monkeypatch.setattr(auth_module, "get_profile_db_manager", lambda: manager)
    monkeypatch.setattr(profiles_api, "get_profile_db_manager", lambda: manager)
    return manager


def _login(client):
    return client.post("/profiles/login", json={"profile_id": PROFILE_ID, "password": PASSWORD})


def _unlock(client):
    return client.post(f"/profiles/{PROFILE_ID}/unlock", json={"password": PASSWORD})


def _events(master) -> list[str]:
    return [r.event_type for r in audit_rows(master)]


def _recovery_code(manager) -> str:
    """Seal a real recovery copy of a real key, as `issue_recovery_code` does."""
    dek = generate_encryption_key()
    return profiles_api._issue_recovery_code(PROFILE_ID, dek)


def _recover(client, code: str):
    return client.post(
        f"/profiles/{PROFILE_ID}/recover",
        json={"recovery_code": code, "new_password": NEW_PASSWORD},
    )


def test_hc_loo_001_login_failed_open_leaves_master_locked_with_no_login_row(master, monkeypatch):
    before = profile_row(master, PROFILE_ID).last_accessed_at
    _install(monkeypatch, master, ProfileDatabaseEncryptionError(vc.MSG_HELD))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == vc.MSG_HELD
    row = profile_row(master, PROFILE_ID)
    assert row.is_locked is True
    assert row.last_accessed_at == before
    assert "profile.login" not in _events(master)


def test_hc_loo_002_login_success_opens_first_then_marks_signed_in(master, monkeypatch):
    manager = _install(monkeypatch, master)
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 200, response.text
    assert len(manager.opened) == 1
    at_open = manager.opened[0]
    assert at_open["is_locked"] is True
    assert at_open["last_accessed_at"] is None
    assert "profile.login" not in at_open["events"]
    row = profile_row(master, PROFILE_ID)
    assert row.is_locked is False
    assert row.last_accessed_at is not None
    assert _events(master).count("profile.login") == 1


def test_hc_loo_003_unlock_failed_open_leaves_master_locked_with_no_unlock_row(master, monkeypatch):
    _install(monkeypatch, master, ProfileDatabaseEncryptionError(vc.MSG_HELD))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _unlock(client)

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == vc.MSG_HELD
    assert profile_row(master, PROFILE_ID).is_locked is True
    assert "profile.unlock" not in _events(master)


def test_hc_loo_004_unlock_success_opens_first_then_marks_unlocked(master, monkeypatch):
    manager = _install(monkeypatch, master)
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _unlock(client)

    assert response.status_code == 200, response.text
    assert manager.opened[0]["is_locked"] is True
    assert "profile.unlock" not in manager.opened[0]["events"]
    assert profile_row(master, PROFILE_ID).is_locked is False
    assert _events(master).count("profile.unlock") == 1


def test_hc_loo_005_recover_failed_open_keeps_credential_rows_but_stays_locked(master, monkeypatch):
    manager = _install(monkeypatch, master, ProfileDatabaseEncryptionError(vc.MSG_HELD))
    code = _recovery_code(manager)
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _recover(client, code)

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == vc.MSG_HELD
    events = _events(master)
    # The password really did change, so its rows stay (RECOVER-ORDER-COMMIT).
    assert "profile.recovered" in events
    assert "profile.recovery_code_generated" in events
    row = profile_row(master, PROFILE_ID)
    assert row.is_locked is True
    # The new password is committed even though the open failed.
    assert verify_password(NEW_PASSWORD, row.password_hash)


def test_hc_loo_006_recover_success_unlocks_after_open_and_keeps_row_order(master, monkeypatch):
    manager = _install(monkeypatch, master)
    code = _recovery_code(manager)
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _recover(client, code)

    assert response.status_code == 200, response.text
    assert manager.opened[0]["is_locked"] is True
    assert manager.opened[0]["events"] == ["profile.recovered", "profile.recovery_code_generated"]
    assert profile_row(master, PROFILE_ID).is_locked is False
    assert _events(master) == ["profile.recovered", "profile.recovery_code_generated"]


def test_hc_loo_007_login_unexpected_open_error_is_500_and_stays_locked(master, monkeypatch):
    _install(monkeypatch, master, RuntimeError("boom"))
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _login(client)

    assert response.status_code == 500, response.text
    assert response.json()["detail"] == "Failed to open profile database"
    assert profile_row(master, PROFILE_ID).is_locked is True
    assert "profile.login" not in _events(master)


def test_hc_loo_008_master_commit_failure_after_open_closes_the_vault(master, monkeypatch):
    manager = _install(monkeypatch, master)
    real_commit = AsyncSession.commit
    state = {"armed": False, "raised": 0}

    async def flaky_commit(self):
        if state["armed"] and not state["raised"]:
            state["raised"] += 1
            raise RuntimeError("master commit failed")
        return await real_commit(self)

    monkeypatch.setattr(AsyncSession, "commit", flaky_commit)
    manager.after_open = lambda: state.update(armed=True)

    with route_client(profiles_api.router, "/profiles", raise_server_exceptions=False) as client:
        use_master(client, master)
        response = _login(client)

    assert state["raised"] == 1
    assert response.status_code == 500, response.text
    assert manager.closed == [PROFILE_ID]
    assert profile_row(master, PROFILE_ID).is_locked is True
    assert "profile.login" not in _events(master)
