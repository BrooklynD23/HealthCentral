"""HC-PNU — POST /profiles refuses a second profile with the same display name
(PROFILE-NAME-UNIQUE, owner request 2026-11-13).

Names compare after strip, internal-whitespace collapse and casefold. A refusal
is a 409 that leaves no vault on disk and no "profile created" audit row.
Profiles that already share a name are untouched: they still list and log in.
All requests go through HTTP against a real, file-backed master DB.
"""

from __future__ import annotations

import asyncio
import base64

import httpx
import pytest
from sqlalchemy.orm import Session as SyncSession

import api.profiles as profiles_api
from core.security import hash_password
from core.time import utcnow
from models import Profile
from tests.support.master_db import audit_rows, make_master_db, use_master
from tests.support.routes import route_client

PASSWORD = "Testing123!"
EXISTING = "Brooklyn D23"


def _seed(db, profile_id: str, display_name: str) -> None:
    now = utcnow()
    with SyncSession(db.sync_engine()) as session:
        session.add(
            Profile(
                id=profile_id,
                display_name=display_name,
                encryption_key_id=f"key-{profile_id}",
                password_hash=hash_password(PASSWORD),
                password_salt=base64.b64encode(b"\x00" * 16).decode("ascii"),
                is_locked=True,
                created_at=now,
                updated_at=now,
                last_accessed_at=None,
            )
        )
        session.commit()


def _profile_names(db) -> list[str]:
    with SyncSession(db.sync_engine()) as session:
        return sorted(p.display_name for p in session.query(Profile).all())


@pytest.fixture
def master(tmp_path, monkeypatch):
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )

    # The per-profile SQLCipher vault is out of scope here; the name gate runs
    # before it. A plain object has no fk_cleanup_counts, so no cleanup audit.
    async def _no_vault_open(profile_id, password):
        return object()

    monkeypatch.setattr(profiles_api, "open_profile_database_on_login", _no_vault_open)
    profiles_api.auth_rate_limiter.reset("login:testclient")
    return make_master_db(tmp_path)


def _vault_dirs(tmp_path) -> list[str]:
    vaults = tmp_path / "vaults"
    return sorted(p.name for p in vaults.iterdir()) if vaults.exists() else []


def _create(client, name: str):
    return client.post("/profiles/", json={"display_name": name, "password": PASSWORD})


def test_hc_pnu_001_exact_duplicate_is_409_and_leaves_no_vault(master, tmp_path):
    _seed(master, "p-existing", EXISTING)
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _create(client, EXISTING)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        f"A profile named {EXISTING} already exists. Choose a different name."
    )
    assert _vault_dirs(tmp_path) == []
    assert _profile_names(master) == [EXISTING]
    assert [r.event_type for r in audit_rows(master)] == []


@pytest.mark.parametrize(
    "existing, typed",
    [
        ("brooklynd23", "  brooklynd23 "),
        ("brooklynd23", "BrooklynD23"),
        ("Brooklyn D23", "Brooklyn  D23"),
        ("Brooklyn D23", "\tbROOKLYN   d23\n"),
    ],
)
def test_hc_pnu_002_case_and_whitespace_variants_are_409(master, tmp_path, existing, typed):
    _seed(master, "p-existing", existing)
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _create(client, typed)

    assert response.status_code == 409, response.text
    # The message echoes what the user typed, never the stored name.
    assert response.json()["detail"] == (
        f"A profile named {typed} already exists. Choose a different name."
    )
    assert _vault_dirs(tmp_path) == []
    assert _profile_names(master) == [existing]


def test_hc_pnu_003_distinct_name_is_created_as_today(master, tmp_path):
    _seed(master, "p-existing", EXISTING)
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        response = _create(client, "Brooklyn D24")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["access_token"]
    assert body["recovery_code"]
    assert _profile_names(master) == [EXISTING, "Brooklyn D24"]
    assert len(_vault_dirs(tmp_path)) == 1
    assert "profile.create" in [r.event_type for r in audit_rows(master)]


def test_hc_pnu_004_existing_duplicates_still_list_and_log_in(master):
    _seed(master, "p-one", EXISTING)
    _seed(master, "p-two", "brooklyn  d23")
    with route_client(profiles_api.router, "/profiles") as client:
        use_master(client, master)
        listed = client.get("/profiles/")
        logins = [
            client.post("/profiles/login", json={"profile_id": pid, "password": PASSWORD})
            for pid in ("p-one", "p-two")
        ]

    assert listed.status_code == 200, listed.text
    assert sorted(p["id"] for p in listed.json()) == ["p-one", "p-two"]
    assert [r.status_code for r in logins] == [200, 200], [r.text for r in logins]
    assert _profile_names(master) == sorted([EXISTING, "brooklyn  d23"])


def test_hc_pnu_005_concurrent_duplicate_creates_exactly_one_succeeds(master, tmp_path):
    """Each commit sleeps first, so without serialisation both requests would
    pass the name check before either row is committed."""
    with route_client(profiles_api.router, "/profiles") as client:
        app = client.app

    async def _slow_commit_session():
        async with master.maker() as session:
            real_commit = session.commit

            async def _commit():
                await asyncio.sleep(0.2)
                await real_commit()

            session.commit = _commit
            yield session

    app.dependency_overrides[profiles_api.get_db] = _slow_commit_session

    async def _race():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            return await asyncio.gather(
                *(
                    ac.post("/profiles/", json={"display_name": name, "password": PASSWORD})
                    for name in ("Same Name", "same  name")
                )
            )

    responses = asyncio.run(_race())

    assert sorted(r.status_code for r in responses) == [201, 409], [r.text for r in responses]
    assert len(_profile_names(master)) == 1
    assert len(_vault_dirs(tmp_path)) == 1
