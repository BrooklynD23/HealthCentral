"""Route-level tests for the backup API (HC-BKUP-033+).

These go through HTTP so FastAPI's dependency graph actually executes. The
direct-call tests in test_backup_api.py cover handler logic; these cover
whether the endpoint is reachable at all.
"""

from __future__ import annotations

import sqlite3

import pytest

import api.backup as backup_api
from tests.support.routes import route_client


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point app_data_path at a temp dir with two seeded profiles."""
    monkeypatch.setattr(
        type(backup_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    for pid in ("profile-a", "profile-b"):
        vault = tmp_path / "vaults" / pid
        vault.mkdir(parents=True)
        conn = sqlite3.connect(vault / "vault.db")
        conn.execute("CREATE TABLE observations (id TEXT)")
        conn.commit()
        conn.close()
        (vault / "key.bin").write_bytes(b"sealed-" + pid.encode())
        (vault / "key.method").write_text("password")
    conn = sqlite3.connect(tmp_path / "healthcentral.db")
    conn.execute("CREATE TABLE profiles (id TEXT)")
    conn.commit()
    conn.close()
    return tmp_path


def test_hc_bkup_033_harness_resolves_dependencies(data_dir):
    """The harness must actually run Depends(...) — otherwise it is no better
    than a direct call. GET /backup/ requires auth; a 200 proves the override
    resolved rather than the dependency being skipped."""
    with route_client(backup_api.router, "/backup") as client:
        response = client.get("/backup/")

    assert response.status_code == 200, response.text
