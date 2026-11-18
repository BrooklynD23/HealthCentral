"""HC-PGUARD — require_profile_access on api/profiles.py, over HTTP (ISO-02, C-ISO-1/2).

A route test that calls a handler as a function never runs Depends(...)
(recurring-failures #1). Every test here goes through FastAPI.
HC-PGUARD-005 removes the guard and asserts that the same requests then get
through. That proves HC-PGUARD-001's 403 comes from the guard.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

import api.profiles as profiles_api
from core import denial_audit
from core.auth import Session, require_auth
from tests.support.master_db import (
    MasterDb,
    audit_rows,
    make_master_db,
    profile_row,
    seed_profile,
    use_master,
)
from tests.support.routes import route_client

OWN = "profile-a"
OTHER = "profile-b"
WRONG_PASSWORD = "Wrong-Horse-42"

# (method, path template, JSON body) for every route that carries the guard.
GUARDED = [
    pytest.param("POST", "/{pid}/recovery-code", {"password": WRONG_PASSWORD}, id="recovery-code"),
    pytest.param(
        "DELETE",
        "/{pid}",
        {
            "password": WRONG_PASSWORD,
            "confirmation_phrase": profiles_api.PROFILE_DELETE_CONFIRMATION,
            "export_acknowledged": True,
        },
        id="delete",
    ),
    pytest.param("GET", "/{pid}", None, id="get"),
    pytest.param("POST", "/{pid}/lock", None, id="lock"),
    pytest.param(
        "POST",
        "/{pid}/change-password",
        {"current_password": WRONG_PASSWORD, "new_password": "Brand-New-Pass-9"},
        id="change-password",
    ),
]

GUARDED_KEYS = {
    ("POST", "/{profile_id}/recovery-code"),
    ("DELETE", "/{profile_id}"),
    ("GET", "/{profile_id}"),
    ("POST", "/{profile_id}/lock"),
    ("POST", "/{profile_id}/change-password"),
}
# Unauthenticated by design: recover (lost password, api/profiles.py docstring
# "Unauthenticated by necessity") and unlock (password in the body).
UNAUTHENTICATED_BY_DESIGN = {
    ("POST", "/{profile_id}/recover"),
    ("POST", "/{profile_id}/unlock"),
}


@pytest.fixture
def master(tmp_path, monkeypatch) -> MasterDb:
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    db = make_master_db(tmp_path)
    seed_profile(db, OWN, "Own Profile")
    seed_profile(db, OTHER, "Other Profile")
    # I-12 / lane-E 2.2 #1: a cross-profile 403 makes core.auth call audit_denial
    # with no db, which opens core.database.async_session_maker(). Point it at the
    # test master DB so no test can write into a developer's real master DB, and
    # clear the in-process denial counter so the cap never carries across tests.
    monkeypatch.setattr("core.database.async_session_maker", db.maker)
    denial_audit._state.clear()
    yield db
    denial_audit._state.clear()
    # Task 1 bypass requests may count a failed delete re-auth; do not leak it.
    profiles_api.auth_rate_limiter.reset(f"delete:testclient:{OTHER}")


def _send(client: TestClient, method: str, path: str, body, pid: str = OTHER):
    url = "/profiles" + path.format(pid=pid)
    if body is None:
        return client.request(method, url)
    return client.request(method, url, json=body)


def _assert_one_denial_row(master: MasterDb) -> None:
    """The guard's second observable (#78): exactly one denial row, attributed to
    the caller's own profile, naming the artifact kind but never the target id."""
    rows = audit_rows(master)
    assert len(rows) == 1, [(r.event_type, r.profile_id) for r in rows]
    row = rows[0]
    assert row.event_type == "denial.cross_profile"
    assert row.profile_id == OWN
    assert row.entity_type == "profile"
    assert row.entity_id is None


def _dependency_calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _dependency_calls(dep)


def _is_guarded(route) -> bool:
    return any(
        getattr(call, "__name__", "") == "verify_profile_access"
        for call in _dependency_calls(route.dependant)
    )


@pytest.mark.parametrize(("method", "path", "body"), GUARDED)
def test_hc_pguard_001_cross_profile_request_is_refused(master, method, path, body):
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = _send(client, method, path, body)

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Access denied to this profile"
    # Nothing behind the guard ran: the other profile is untouched.
    other = profile_row(master, OTHER)
    assert other is not None and other.is_locked is False
    _assert_one_denial_row(master)


def test_hc_pguard_002_own_profile_passes_the_guard(master):
    """Positive control: the guard reads the right path param. A guard that read a
    missing param would 400 every request (the restore-endpoint bug)."""
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get(f"/profiles/{OWN}")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == OWN
    # A 200 writes no denial row. (It does write its own profile.view row, AUD-02.)
    assert [r for r in audit_rows(master) if r.event_type.startswith("denial.")] == []


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}],
    ids=["no-token", "malformed-token"],
)
def test_hc_pguard_003_unauthenticated_request_is_401(master, headers):
    """route_client(real_auth=True): the real require_auth -> get_current_session
    chain runs, so a missing or malformed token must be refused before the guard."""
    with route_client(profiles_api.router, "/profiles", real_auth=True) as client:
        assert require_auth not in client.app.dependency_overrides  # harness really opted out
        use_master(client, master)
        response = client.get(f"/profiles/{OTHER}", headers=headers)

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Not authenticated"  # core/auth.py require_auth


def test_hc_pguard_004_every_profile_id_route_is_guarded():
    guarded_seen = set()
    all_keys = set()
    for route in profiles_api.router.routes:
        for method in route.methods:
            key = (method, route.path)
            all_keys.add(key)
            guarded = _is_guarded(route)
            if guarded:
                assert "{profile_id}" in route.path, (
                    f"{key} carries require_profile_access but has no {{profile_id}} "
                    "path param: every request would 400 (recurring-failures #1)"
                )
            if "{profile_id}" in route.path and key not in UNAUTHENTICATED_BY_DESIGN:
                assert guarded, f"{key} takes a profile_id but is not behind require_profile_access"
                guarded_seen.add(key)

    assert guarded_seen == GUARDED_KEYS
    assert UNAUTHENTICATED_BY_DESIGN <= all_keys


# What each handler does once the guard is gone (session = OWN, path = OTHER).
# OTHER is seeded with password_hash=None, so authenticate_profile() refuses
# every password. Strings verified at main@40f590e api/profiles.py (unchanged
# at B/A): :611, :828, :1103. Task 0 Step 7 re-verifies them post-P5/P7.
BYPASS_EXPECT = [
    pytest.param("POST", "/{pid}/recovery-code", {"password": WRONG_PASSWORD},
                 401, "Incorrect password", id="recovery-code"),
    pytest.param("DELETE", "/{pid}",
                 {"password": WRONG_PASSWORD,
                  "confirmation_phrase": profiles_api.PROFILE_DELETE_CONFIRMATION,
                  "export_acknowledged": True},
                 401, "Incorrect password", id="delete"),
    pytest.param("GET", "/{pid}", None, 200, None, id="get"),
    pytest.param("POST", "/{pid}/lock", None, 200, None, id="lock"),
    pytest.param("POST", "/{pid}/change-password",
                 {"current_password": WRONG_PASSWORD, "new_password": "Brand-New-Pass-9"},
                 401, "Current password is incorrect", id="change-password"),
]


@pytest.mark.parametrize(("method", "path", "body", "status", "detail"), BYPASS_EXPECT)
def test_hc_pguard_005_without_the_guard_the_same_request_gets_through(
    master, monkeypatch, method, path, body, status, detail
):
    """Mutation control (break-it, kept in CI): override every guard instance with
    a pass-through, then assert the EXACT response each handler gives and the
    side effect it has. A 500, a 422 or any other surprise fails here, so this
    cannot pass by accident."""
    monkeypatch.setattr(profiles_api, "revoke_jwt_token", lambda *a, **k: None)
    monkeypatch.setattr(profiles_api, "close_profile_database_on_logout", AsyncMock())

    # No timestamp is built here. The pass-through hands back the Session that
    # route_client's require_auth override already produced, so this test never
    # constructs a datetime. (Session.expires_at is compared against an AWARE
    # now in core/auth.py Session.is_expired; a naive core.time.utcnow() value
    # there would raise TypeError, so neither form is written in this file.)
    async def _pass_through(session: Session = Depends(require_auth)) -> Session:
        return session

    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        overridden = 0
        for route in profiles_api.router.routes:
            for call in _dependency_calls(route.dependant):
                if getattr(call, "__name__", "") == "verify_profile_access":
                    client.app.dependency_overrides[call] = _pass_through
                    overridden += 1
        assert overridden == 5, f"expected 5 guard instances, overrode {overridden}"
        response = _send(client, method, path, body)

    assert response.status_code == status, response.text
    other = profile_row(master, OTHER)
    vault_dir = master.path.parent / "vaults" / OTHER
    if detail is not None:
        # The handler ran and refused on its own re-auth, before any file or row change.
        assert response.json()["detail"] == detail
        assert other is not None and other.is_locked is False and other.password_hash is None
        assert not vault_dir.exists(), f"handler touched {vault_dir} before re-auth"
        assert audit_rows(master) == []
    elif method == "GET":
        # The leak the guard prevents: OWN's session reads OTHER's profile.
        assert response.json()["id"] == OTHER
        assert response.json()["display_name"] == "Other Profile"
    else:  # lock
        # The side effect HC-PGUARD-001 checks for is real: OWN's session locks
        # OTHER, and the lock is committed and audited under OTHER's id.
        assert other.is_locked is True
        assert [(r.event_type, r.profile_id) for r in audit_rows(master)] == [
            ("profile.lock", OTHER)
        ]


def test_hc_pguard_006_profile_id_match_is_exact(master):
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get(f"/profiles/{OWN.upper()}")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Access denied to this profile"
    _assert_one_denial_row(master)
