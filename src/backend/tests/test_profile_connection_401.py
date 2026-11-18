"""HC-SRE-005: a valid JWT with no open profile connection returns 401.

After a backend restart the JWT still verifies but the per-profile SQLCipher
connection is gone. The frontend only routes 401 to the unlock screen, so this
must be 401 and not 403. Goes through HTTP with the real `get_profile_db_session`
(no `profile_db=` override), so `_get_required_profile_connection` actually runs.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import APIRouter

import core.auth as auth_module
from api.observations import router as observations_router
from core.auth import ProfileEncryptionManager
from tests.support.routes import route_client

DETAIL = "Profile database not available. Please log in again."


@pytest.fixture
def no_profile_connection(monkeypatch):
    """Profile DB manager with no open connection for any profile."""
    seen: list[str] = []

    def _get_connection(profile_id: str):
        seen.append(profile_id)
        return None

    monkeypatch.setattr(
        auth_module,
        "get_profile_db_manager",
        lambda: SimpleNamespace(get_connection=_get_connection),
    )
    return seen


def test_hc_sre_005_missing_profile_connection_returns_401(no_profile_connection):
    with route_client(observations_router, "/observations") as client:
        resp = client.get("/observations/")

    assert resp.status_code == 401
    assert resp.json()["detail"] == DETAIL
    # The guard ran for the authenticated profile, not some other path.
    assert no_profile_connection == ["profile-a"]


def test_hc_sre_005b_encryption_manager_dependency_returns_401(no_profile_connection):
    router = APIRouter()

    @router.get("/probe")
    async def probe(encryption_manager: ProfileEncryptionManager):
        return {"ok": True}

    with route_client(router, "/t") as client:
        resp = client.get("/t/probe")

    assert resp.status_code == 401
    assert resp.json()["detail"] == DETAIL
    assert no_profile_connection == ["profile-a"]
