"""HC-PAUD — the four previously unaudited profile routes write committed,
PHI-free audit rows (AUD-02, C-AUDIT-1). Rows are read back through a separate
connection, so an audit row that was only add()ed and never committed is missed."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import api.profiles as profiles_api
import models  # noqa: F401  registers every profile model on ProfileDatabaseBase
import models.response_feedback  # noqa: F401  not re-exported by models/__init__ (plan 07)
from core.profile_database import ProfileDatabaseBase
from tests.support.master_db import audit_rows, make_master_db, seed_profile, use_master
from tests.support.routes import route_client

OWN = "profile-a"
OTHER = "profile-b"
OWN_NAME = "Jane Canary Own"                   # must never reach an audit row
PLAYWRIGHT_NAME = "Playwright E2E Jane Canary"  # passes the reset name gate


@pytest.fixture
def master(tmp_path, monkeypatch):
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    db = make_master_db(tmp_path)
    seed_profile(db, OWN, OWN_NAME)
    seed_profile(db, OTHER, "Other Canary")
    return db


@pytest.fixture
def vault_maker(tmp_path):
    """A plain SQLite profile DB with every ORM profile table. If P7's reset also
    clears the FTS `search_records*` tables (N-02), create them here the same way
    tests/test_profile_test_reset.py does."""
    path = tmp_path / "vault.db"
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    ProfileDatabaseBase.metadata.create_all(engine)
    engine.dispose()
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    return path, async_sessionmaker(async_engine, expire_on_commit=False)


def _summary(rows):
    return [(r.event_type, r.profile_id, r.entity_type, r.entity_id) for r in rows]


def test_hc_paud_001_get_me_writes_a_committed_audit_row(master):
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get("/profiles/me")

    assert response.status_code == 200, response.text
    assert _summary(audit_rows(master)) == [("profile.view", OWN, "profile", OWN)]


def test_hc_paud_002_get_profile_writes_a_committed_audit_row(master):
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get(f"/profiles/{OWN}")

    assert response.status_code == 200, response.text
    assert _summary(audit_rows(master)) == [("profile.view", OWN, "profile", OWN)]


def test_hc_paud_003_test_reset_writes_a_committed_audit_row(master, vault_maker, monkeypatch):
    monkeypatch.setattr(profiles_api.settings, "app_env", "development")
    _, maker = vault_maker
    with route_client(
        profiles_api.router, "/profiles",
        profile_id=OWN, profile_name=PLAYWRIGHT_NAME, profile_db=maker,
    ) as client:
        use_master(client, master)
        response = client.post("/profiles/test/reset")

    assert response.status_code == 204, response.text
    rows = audit_rows(master)
    assert _summary(rows) == [("profile.test_reset", OWN, "profile", OWN)]
    assert json.loads(rows[0].details_json) == {
        "count": len(profiles_api._SYNTHETIC_RESET_MODELS)
    }


def test_hc_paud_004_failed_reset_leaves_no_reset_audit_row(master, vault_maker, monkeypatch):
    """Order of effects: the row is written only after the vault commit succeeds."""
    monkeypatch.setattr(profiles_api.settings, "app_env", "development")
    path, maker = vault_maker
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE embeddings"))  # delete(Embedding) now raises
    engine.dispose()

    with route_client(
        profiles_api.router, "/profiles",
        profile_id=OWN, profile_name=PLAYWRIGHT_NAME, profile_db=maker,
    ) as client:
        use_master(client, master)
        response = client.post("/profiles/test/reset")

    assert response.status_code == 500, response.text
    assert response.json()["detail"].startswith("Synthetic profile reset failed")
    assert [r.event_type for r in audit_rows(master)] == []


def test_hc_paud_005_profile_audit_rows_carry_no_display_name(master, vault_maker, monkeypatch):
    monkeypatch.setattr(profiles_api.settings, "app_env", "development")
    _, maker = vault_maker
    with route_client(
        profiles_api.router, "/profiles",
        profile_id=OWN, profile_name=PLAYWRIGHT_NAME, profile_db=maker,
    ) as client:
        use_master(client, master)
        assert client.get("/profiles/me").status_code == 200
        assert client.get(f"/profiles/{OWN}").status_code == 200
        assert client.post("/profiles/test/reset").status_code == 204

    rows = audit_rows(master)
    assert len(rows) == 3, "expected one row per request"
    for row in rows:
        blob = " ".join(
            str(v) for v in (row.event_type, row.action, row.entity_type,
                             row.entity_id, row.details_json, row.client_info)
        )
        assert "Canary" not in blob, f"display name leaked into audit row: {blob}"


def test_hc_paud_006_list_profiles_writes_one_unattributed_audit_row(master):
    """Q-AUD-LIST option (a) only. Delete this test if the owner chose (b)."""
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get("/profiles/")

    assert response.status_code == 200, response.text
    rows = audit_rows(master)
    assert [(r.event_type, r.profile_id) for r in rows] == [("profile.list", None)]
    assert json.loads(rows[0].details_json) == {"count": 2}


def test_hc_paud_007_audit_failure_does_not_serve_the_profile(master, monkeypatch):
    """audit_and_commit is fail-closed: a read that cannot be audited is not served."""
    async def _boom(**_kwargs):
        raise RuntimeError("audit store down")

    monkeypatch.setattr(profiles_api, "log_profile_event", _boom)
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        with pytest.raises(RuntimeError, match="audit store down"):
            client.get("/profiles/me")
