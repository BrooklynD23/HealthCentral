"""EXPORT-STORE-PURGE: in-memory export stores die with the session (HC-ESP-NNN).

`_summary_store`, `_packet_store` and `_fhir_store` hold redacted export
bodies keyed by id. They must not outlive logout, lock or profile deletion,
and must expire on their own after 30 minutes. L0 ruling (comment 6380418672):
an entry with no `created_at` counts as fresh (legacy fixtures write none).

Route tests go through HTTP (tests/support/routes.py::route_client). Logout,
lock and delete use a profiles-router client; export routes use an export
client. The module-level stores are shared in-process.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import api.export as export_api
import api.profiles as profiles_api
from api.profiles import PROFILE_DELETE_CONFIRMATION
from tests.support.routes import route_client
from tests.test_export_redaction import _export_client
from tests.test_profile_deletion import _FakeMasterDb, _make_vault

A = "profile-a"
B = "profile-b"
T0 = datetime(2026, 10, 23, 12, 0, 0)
FHIR_ID = "00000000-0000-4000-8000-0000000000f1"
PACKET_ID = "00000000-0000-4000-8000-0000000000a1"
OTHER_SUMMARY = "00000000-0000-4000-8000-0000000000b1"
OTHER_PACKET = "00000000-0000-4000-8000-0000000000b2"
OTHER_FHIR = "00000000-0000-4000-8000-0000000000b3"


@pytest.fixture(autouse=True)
def _fresh_stores(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_api, "_summary_store", {})
    monkeypatch.setattr(export_api, "_packet_store", {})
    monkeypatch.setattr(export_api, "_fhir_store", {})


def _create_summary(client) -> str:
    created = client.post("/export/doctor-summary", json={"format": "text"})
    assert created.status_code == 200, created.text
    return created.json()["summary_id"]


def _download(client, summary_id: str):
    return client.get(f"/export/doctor-summary/{summary_id}/download")


def _db_with_profile(profile) -> MagicMock:
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = profile
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    return db


@contextmanager
def _profiles_client(profile_id: str, master_db):
    with patch.object(profiles_api, "close_profile_database_on_logout", AsyncMock()), \
         patch.object(profiles_api, "revoke_jwt_token", MagicMock()), \
         patch.object(profiles_api, "log_profile_event", AsyncMock()), \
         route_client(profiles_api.router, "/profiles", profile_id=profile_id,
                      master_db=master_db) as client:
        yield client


def test_hc_esp_001_logout_purges_summary():
    with _export_client(A) as exp:
        sid = _create_summary(exp)
        assert _download(exp, sid).status_code == 200  # served before logout
        with _profiles_client(A, _db_with_profile(None)) as prof:
            assert prof.post("/profiles/logout").status_code == 200
        assert _download(exp, sid).status_code == 404


def test_hc_esp_002_lock_purges_summary():
    profile = SimpleNamespace(
        id=A, display_name="T", is_locked=False, password_hash="x",
        created_at=T0, last_accessed_at=None,
    )
    with _export_client(A) as exp:
        sid = _create_summary(exp)
        assert _download(exp, sid).status_code == 200
        with _profiles_client(A, _db_with_profile(profile)) as prof:
            assert prof.post(f"/profiles/{A}/lock").status_code == 200
        assert _download(exp, sid).status_code == 404


def test_hc_esp_003_delete_purges_all_three_stores_for_that_profile_only(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    _make_vault(tmp_path, A)
    export_api._summary_store["s-a"] = {"profile_id": A}
    export_api._packet_store[PACKET_ID] = {"profile_id": A}
    export_api._fhir_store[FHIR_ID] = {"profile_id": A, "bundle": {}}
    export_api._summary_store[OTHER_SUMMARY] = {"profile_id": B}
    export_api._packet_store[OTHER_PACKET] = {"profile_id": B}
    export_api._fhir_store[OTHER_FHIR] = {"profile_id": B, "bundle": {}}

    profile = SimpleNamespace(id=A, display_name="T")
    with patch.object(profiles_api, "_load_profile_for_delete",
                      AsyncMock(return_value=profile)), \
         patch.object(profiles_api, "authenticate_profile",
                      AsyncMock(return_value=profile)), \
         _profiles_client(A, _FakeMasterDb()) as prof:
        resp = prof.request(
            "DELETE", f"/profiles/{A}",
            json={"password": "CorrectHorse1",
                  "confirmation_phrase": PROFILE_DELETE_CONFIRMATION,
                  "export_acknowledged": True},
        )
    assert resp.status_code == 204, resp.text

    for store in (export_api._summary_store, export_api._packet_store,
                  export_api._fhir_store):
        assert all(v["profile_id"] != A for v in store.values())
    assert OTHER_SUMMARY in export_api._summary_store
    assert OTHER_PACKET in export_api._packet_store
    assert OTHER_FHIR in export_api._fhir_store


def test_hc_esp_004_entry_older_than_30_minutes_is_404(monkeypatch):
    clock = {"now": T0}
    monkeypatch.setattr(export_api, "utcnow", lambda: clock["now"])
    with _export_client(A) as exp:
        sid = _create_summary(exp)
        assert export_api._summary_store[sid]["created_at"] == T0  # stamped on write
        clock["now"] = T0 + timedelta(minutes=29)
        assert _download(exp, sid).status_code == 200  # still fresh
        clock["now"] = T0 + timedelta(minutes=31)
        assert _download(exp, sid).status_code == 404


def test_hc_esp_005_entry_without_created_at_counts_as_fresh(monkeypatch):
    """L0 ruling (iii): legacy fixtures write no created_at and must be served."""
    monkeypatch.setattr(export_api, "utcnow", lambda: T0 + timedelta(days=30))
    with _export_client(A) as exp:
        sid = _create_summary(exp)
        export_api._summary_store[sid].pop("created_at")
        assert _download(exp, sid).status_code == 200
