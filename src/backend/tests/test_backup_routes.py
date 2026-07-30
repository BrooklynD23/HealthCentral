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


def test_hc_bkup_034_restore_route_is_reachable(data_dir, monkeypatch):
    """The regression that 32 direct-call tests could not see: the route used
    Depends(require_profile_access()), which reads path_params["profile_id"] —
    a parameter this route does not have — so every request 400'd before any
    handler logic ran."""
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    with route_client(backup_api.router, "/backup") as client:
        created = client.post("/backup/")
        assert created.status_code == 201, created.text
        backup_id = created.json()["backup_id"]

        monkeypatch.setattr(
            backup_api,
            "authenticate_profile",
            AsyncMock(return_value=SimpleNamespace(id="profile-a")),
        )
        monkeypatch.setattr(
            backup_api, "close_profile_database_on_logout", AsyncMock()
        )

        response = client.post(
            f"/backup/{backup_id}/restore",
            json={
                "password": "CorrectHorse1",
                "confirmation_phrase": backup_api.BACKUP_RESTORE_CONFIRMATION,
            },
        )

    assert response.status_code == 200, response.text
    assert response.json()["files_restored"] > 0


def test_hc_bkup_035_download_carries_only_this_profile(data_dir):
    """A profile-scoped backup keeps the master DB on disk because restore needs
    the password hash. The download must NOT: it leaves the device, and the
    master DB holds every profile's row and the whole audit trail."""
    import io
    import zipfile

    master = data_dir / "healthcentral.db"
    conn = sqlite3.connect(master)
    conn.execute("DROP TABLE IF EXISTS profiles")
    conn.execute(
        "CREATE TABLE profiles (id TEXT, display_name TEXT, password_hash TEXT)"
    )
    conn.executemany(
        "INSERT INTO profiles VALUES (?, ?, ?)",
        [
            ("profile-a", "Ann", "hash-a"),
            ("profile-b", "Bob", "hash-b"),
        ],
    )
    conn.commit()
    conn.close()

    with route_client(backup_api.router, "/backup") as client:
        created = client.post("/backup/")
        assert created.status_code == 201, created.text
        backup_id = created.json()["backup_id"]

        response = client.get(f"/backup/{backup_id}/download")

    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))

    # The vault must still be there — scoping the master must not gut the zip.
    assert any(n.endswith("vault.db") for n in archive.namelist())
    assert any(n.endswith("key.bin") for n in archive.namelist())

    # The assertion HC-BKUP-014 could not make: open the master DB *inside* the
    # archive and confirm it names exactly one profile.
    extracted = archive.read("healthcentral.db")
    scratch = data_dir / "from_zip.db"
    scratch.write_bytes(extracted)
    conn = sqlite3.connect(scratch)
    rows = conn.execute("SELECT id, display_name FROM profiles").fetchall()
    conn.close()

    assert rows == [("profile-a", "Ann")], f"leaked other profiles: {rows}"


def test_hc_bkup_036_download_scopes_audit_and_schedule_tables(data_dir):
    """HC-BKUP-035 only opened `profiles`, so the other two scoped tables went
    unchecked — and one of them has a NULL case. `audit_logs.profile_id` is
    nullable for system events, and profile deletion writes a `profile_id=None`
    tombstone. Under SQL three-valued logic `NULL != 'profile-a'` is NULL, not
    TRUE, so a plain `!=` predicate leaves those rows in the archive: other
    people's deletion events and purge counts, riding out on this user's
    download.
    """
    import io
    import zipfile

    master = data_dir / "healthcentral.db"
    conn = sqlite3.connect(master)
    conn.execute("DROP TABLE IF EXISTS profiles")
    conn.execute(
        "CREATE TABLE profiles (id TEXT, display_name TEXT, password_hash TEXT)"
    )
    conn.executemany(
        "INSERT INTO profiles VALUES (?, ?, ?)",
        [("profile-a", "Ann", "hash-a"), ("profile-b", "Bob", "hash-b")],
    )
    conn.execute(
        "CREATE TABLE audit_logs (id TEXT, profile_id TEXT, event_type TEXT)"
    )
    conn.executemany(
        "INSERT INTO audit_logs VALUES (?, ?, ?)",
        [
            ("aud-1", "profile-a", "backup.create"),
            ("aud-2", "profile-b", "document.view"),
            # The system-event tombstone: profiles.py writes profile_id=None
            # when a profile is erased, so the row outlives its subject.
            ("aud-3", None, "profile.delete"),
        ],
    )
    conn.execute(
        "CREATE TABLE backup_schedules (id TEXT, profile_id TEXT, frequency TEXT)"
    )
    conn.executemany(
        "INSERT INTO backup_schedules VALUES (?, ?, ?)",
        [("sch-1", "profile-a", "daily"), ("sch-2", "profile-b", "weekly")],
    )
    conn.commit()
    conn.close()

    with route_client(backup_api.router, "/backup") as client:
        created = client.post("/backup/")
        assert created.status_code == 201, created.text
        backup_id = created.json()["backup_id"]

        response = client.get(f"/backup/{backup_id}/download")

    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    scratch = data_dir / "from_zip_036.db"
    scratch.write_bytes(archive.read("healthcentral.db"))
    conn = sqlite3.connect(scratch)
    try:
        profiles = conn.execute("SELECT id FROM profiles").fetchall()
        audits = conn.execute("SELECT id, profile_id FROM audit_logs").fetchall()
        schedules = conn.execute("SELECT id FROM backup_schedules").fetchall()
    finally:
        conn.close()

    assert profiles == [("profile-a",)], f"leaked other profiles: {profiles}"
    assert schedules == [("sch-1",)], f"leaked other schedules: {schedules}"
    assert audits == [("aud-1", "profile-a")], f"leaked audit rows: {audits}"


def test_hc_bkup_038_partial_restore_500_does_not_claim_nothing_changed(
    data_dir, monkeypatch
):
    """The 500 the user actually sees. A partial restore has already replaced
    the vault and sealed keys, so the response must not read like a clean
    failure: it has to say the data was replaced, which password now applies,
    and that safety copies exist. Both cases stay HTTP 500."""
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from scripts.backup import RestoreResult

    with route_client(backup_api.router, "/backup") as client:
        created = client.post("/backup/")
        assert created.status_code == 201, created.text
        backup_id = created.json()["backup_id"]

        monkeypatch.setattr(
            backup_api,
            "authenticate_profile",
            AsyncMock(return_value=SimpleNamespace(id="profile-a")),
        )
        monkeypatch.setattr(
            backup_api, "close_profile_database_on_logout", AsyncMock()
        )
        monkeypatch.setattr(
            backup_api.backup_script,
            "restore",
            lambda **kwargs: RestoreResult(
                success=False,
                partial=True,
                files_restored=3,
                safety_copies=[Path("vault.db.bak"), Path("key.bin.bak")],
                error="Could not re-apply the profile row: boom",
            ),
        )

        response = client.post(
            f"/backup/{backup_id}/restore",
            json={
                "password": "CorrectHorse1",
                "confirmation_phrase": backup_api.BACKUP_RESTORE_CONFIRMATION,
            },
        )

    assert response.status_code == 500, response.text
    detail = response.json()["detail"]
    assert "nothing was changed" not in detail.lower(), (
        f"the vault and sealed keys were already replaced, so this is false: {detail!r}"
    )
    assert "replaced" in detail.lower()
    assert "password" in detail.lower()
    assert "2 safety copy/copies" in detail
