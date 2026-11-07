"""G-C1 / PRIV-08: export artifacts survive a restart (HC-EXPA-NNN).

Downloadable doctor summaries, visit-prep / pinboard packets and FHIR bundles
are profile data, so they live in the profile vault (`export_artifact`) as well
as in the in-process dicts. L0 ruling (EXPORT-ARTIFACT-RETENTION, #537 comment
6712823856): rows obey the existing 30-minute `_EXPORT_TTL` and are purged at
logout, lock and profile delete.

Every status assertion goes through HTTP (`tests/support/routes.py::route_client`,
recurring-failures #1). A "restart" empties the in-process dicts; the next
request reads the same vault file through a fresh engine. Row-level assertions
query the `export_artifact` table, never filenames.

Each test's docstring or comment names what it would fail to notice.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import api.export as export_api
import api.pinboards as pinboards_api
import api.profiles as profiles_api
from api.profiles import PROFILE_DELETE_CONFIRMATION
from core import time as core_time
from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available
from core.profile_database import (
    ProfileDatabaseBase,
    ProfileDatabaseConnection,
    get_profile_db_manager,
)
from models import Document, Observation, Pinboard, PinboardItem
from tests.support.routes import route_client
from tests.test_export_store_purge import _db_with_profile, _profiles_client
from tests.test_profile_deletion import _FakeMasterDb, _make_vault

PROFILE_A = "profile-a"
PROFILE_B = "profile-b"
NEW_HEAD = "019_export_artifacts"
PREV_HEAD = "018_ocr_opt_in"
T0 = datetime(2026, 11, 7, 12, 0, 0)

# (id, generate path, body, id key, download path, download audit type)
CASES = [
    ("summary", "/export/doctor-summary", {"format": "text"}, "summary_id",
     "/export/doctor-summary/{id}/download?format=text", "summary_download"),
    ("packet", "/export/visit-prep", {"confirm": True}, "packet_id",
     "/export/visit-prep/{id}/download?format=markdown", "visit_prep_download"),
    ("fhir", "/export/fhir", {"confirm": True}, "export_id",
     "/export/fhir/{id}/download", "fhir_r4_download"),
]
CASE_IDS = [c[0] for c in CASES]


def _engine(path: Path):
    return create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)


async def _create_vault(path: Path, profile_id: str, marker: str, unit: str = "mg/dL") -> dict:
    """Real file-backed vault: every profile table, one document, two verified
    observations (one abnormal, carrying `marker` and `unit`), one pinboard."""
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = _engine(path)
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
        s.add(Document(id=doc_id, profile_id=profile_id, path_hash="x" * 64, content_hash="y" * 64,
                       doc_type="lab_report", source="lab.pdf", status="verified",
                       collection_date=datetime(2024, 3, 15), imported_at=datetime(2024, 3, 16)))
        s.add(Observation(id=obs_id, profile_id=profile_id, doc_id=doc_id, analyte_canonical=marker,
                          analyte_raw=marker, value=250.0, unit=unit, ref_low=70.0, ref_high=99.0,
                          flag="H", is_abnormal=True, collected_at=datetime(2024, 3, 15),
                          user_verified=True))
        s.add(Observation(id=str(uuid.uuid4()), profile_id=profile_id, doc_id=doc_id,
                          analyte_canonical="glucose", analyte_raw="glucose", value=95.0,
                          unit="mg/dL", ref_low=70.0, ref_high=99.0, flag=None, is_abnormal=False,
                          collected_at=datetime(2024, 1, 10), user_verified=True))
        board = Pinboard(name="Visit")
        s.add(board)
        await s.flush()
        s.add(PinboardItem(pinboard_id=board.id, item_type="observation", item_id=obs_id))
        await s.commit()
        ids = {"pinboard_id": board.id}
    await engine.dispose()
    return ids


class _Result:
    def __init__(self, obj):
        self._obj = obj

    def scalar_one_or_none(self):
        return self._obj


def _master_db(profile_id: str = PROFILE_A, commit_error: Exception | None = None):
    db = AsyncMock()  # the FHIR route reads Profile from master
    db.execute.return_value = _Result(SimpleNamespace(id=profile_id, display_name="Jane Doe"))
    if commit_error is not None:
        db.commit.side_effect = commit_error
    return db


@contextmanager
def _client(router, prefix: str, vault: Path | None, profile_id: str = PROFILE_A, master_db=None):
    """route_client over a real vault file. `vault=None` leaves the real
    `get_profile_db_session` in place (no connection open = locked vault)."""
    maker = async_sessionmaker(_engine(vault), expire_on_commit=False) if vault else None
    with route_client(router, prefix, profile_id=profile_id,
                      master_db=master_db or _master_db(profile_id), profile_db=maker) as client:
        yield client


def _raw_connect(vault: Path, key: bytes):
    """Raw DBAPI connection the way the repo's migration tests open a vault."""
    from core import migrations
    if is_sqlcipher_available():
        conn = get_sqlcipher_module().connect(str(vault))
        conn.execute(f"PRAGMA key = \"x'{migrations._key_to_hex(key)}'\"")
        return conn
    return sqlite3.connect(vault)


def _simulate_restart() -> None:
    """Drop all in-process export state; only the vault file survives."""
    for store in (export_api._summary_store, export_api._packet_store,
                  export_api._fhir_store, pinboards_api._packet_store):
        store.clear()


async def _rows(path: Path) -> list:
    from models.export_artifact import ExportArtifact
    engine = _engine(path)
    async with engine.connect() as conn:
        rows = (await conn.execute(select(ExportArtifact))).all()
    await engine.dispose()
    return rows


def _register_open_vault(monkeypatch, profile_id: str, path: Path) -> None:
    """Make `path` the profile's open vault connection in the real manager, as
    login does, so the purge at logout / lock / delete finds it."""
    engine = _engine(path)
    connection = ProfileDatabaseConnection(
        profile_id=profile_id, engine=engine,
        session_maker=async_sessionmaker(engine, expire_on_commit=False),
        _encryption_key=b"0" * 32,
    )
    monkeypatch.setitem(get_profile_db_manager()._connections, profile_id, connection)


@pytest.fixture(autouse=True)
def _isolated_stores(monkeypatch):
    for name in ("_summary_store", "_packet_store", "_fhir_store"):
        monkeypatch.setattr(export_api, name, {})
    monkeypatch.setattr(pinboards_api, "_packet_store", export_api._packet_store)
    monkeypatch.setattr(export_api, "log_export_event", AsyncMock())


@pytest.mark.parametrize("kind,gen,body,idkey,dl,dl_type", CASES, ids=CASE_IDS)
def test_hc_expa_001_download_survives_restart(tmp_path, monkeypatch, kind, gen, body, idkey, dl, dl_type):
    """Would not notice: a real SQLCipher reopen with the unsealed key (the suite runs
    unencrypted), or the SPA losing the id after re-login."""
    audit = AsyncMock()
    monkeypatch.setattr(export_api, "log_export_event", audit)
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    with _client(export_api.router, "/export", vault) as client:
        created = client.post(gen, json=body)
        assert created.status_code == 200, created.text
        art_id = created.json()[idkey]
        before = client.get(dl.format(id=art_id))
        assert before.status_code == 200, before.text
    _simulate_restart()
    with _client(export_api.router, "/export", vault) as client:
        after = client.get(dl.format(id=art_id))
    assert after.status_code == 200, after.text
    assert after.content == before.content
    types = [c.kwargs["export_type"] for c in audit.await_args_list]
    assert types.count(dl_type) == 2  # both downloads audited (C-AUDIT-1)


def test_hc_expa_002_pinboard_packet_survives_restart(tmp_path, monkeypatch):
    """Would not notice: a pinboard packet whose items are not observations."""
    monkeypatch.setattr(pinboards_api, "log_pinboard_event", AsyncMock())
    vault = tmp_path / "vault.db"
    ids = asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    with _client(pinboards_api.router, "/pinboards", vault) as client:
        created = client.post(f"/pinboards/{ids['pinboard_id']}/export", json={"confirm": True})
        assert created.status_code == 200, created.text
    _simulate_restart()
    with _client(export_api.router, "/export", vault) as client:
        after = client.get(f"/export/visit-prep/{created.json()['packet_id']}/download?format=markdown")
    assert after.status_code == 200, after.text
    assert after.content.decode("utf-8") == created.json()["markdown"]


@pytest.mark.parametrize("kind,gen,body,idkey,dl,dl_type", CASES, ids=CASE_IDS)
def test_hc_expa_003_other_profiles_vault_cannot_serve_it(tmp_path, kind, gen, body, idkey, dl, dl_type):
    """After a restart profile B's vault holds no such row: 404. Before a restart B
    meets A's in-process entry: 403 (existing behaviour). Either way B never reads it.
    Would not notice: a vault that is shared between profiles by mistake (each test
    vault is its own file)."""
    vault_a, vault_b = tmp_path / "a" / "vault.db", tmp_path / "b" / "vault.db"
    asyncio.run(_create_vault(vault_a, PROFILE_A, "zzmarkera"))
    asyncio.run(_create_vault(vault_b, PROFILE_B, "zzmarkerb"))
    with _client(export_api.router, "/export", vault_a) as client:
        art_id = client.post(gen, json=body).json()[idkey]
    with _client(export_api.router, "/export", vault_b, profile_id=PROFILE_B) as client:
        live = client.get(dl.format(id=art_id))
    assert live.status_code == 403, live.text
    assert "zzmarkera" not in live.text
    _simulate_restart()
    with _client(export_api.router, "/export", vault_b, profile_id=PROFILE_B) as client:
        restarted = client.get(dl.format(id=art_id))
    assert restarted.status_code == 404, restarted.text
    assert "zzmarkera" not in restarted.text


FOREIGN_ROW_CASES = [
    ("doctor_summary", "/export/doctor-summary/{id}/download?format=text", "Access denied to this summary"),
    ("visit_prep", "/export/visit-prep/{id}/download?format=markdown", "Access denied to this packet"),
    ("fhir_r4", "/export/fhir/{id}/download", "Access denied to this export"),
]


@pytest.mark.parametrize("kind,dl,detail", FOREIGN_ROW_CASES, ids=[c[0] for c in FOREIGN_ROW_CASES])
def test_hc_expa_004_row_owned_by_another_profile_is_refused(tmp_path, monkeypatch, kind, dl, detail):
    """Would not notice: a foreign row that is also in the in-process dict (that path
    is HC-DENIAL's)."""
    from models.export_artifact import ExportArtifact
    audit = AsyncMock()
    monkeypatch.setattr(export_api, "log_export_event", audit)
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = str(uuid.uuid4())

    async def _insert():
        engine = _engine(vault)
        async with async_sessionmaker(engine)() as s:
            s.add(ExportArtifact(id=art_id, kind=kind, profile_id=PROFILE_B,
                                 payload_json=json.dumps({"profile_id": PROFILE_B, "id": art_id})))
            await s.commit()
        await engine.dispose()

    asyncio.run(_insert())
    with _client(export_api.router, "/export", vault) as client:
        response = client.get(dl.format(id=art_id))
    assert response.status_code == 403
    assert response.json()["detail"] == detail
    audit.assert_not_awaited()  # a refused download writes no download audit row


def test_hc_expa_005_artifact_id_is_bound_to_its_kind(tmp_path):
    """Would not notice: kind confusion between visit_prep and a pinboard packet
    (both are stored as visit_prep by design)."""
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    with _client(export_api.router, "/export", vault) as client:
        summary_id = client.post("/export/doctor-summary", json={"format": "text"}).json()["summary_id"]
    _simulate_restart()  # force the vault path: the dicts are per-kind already
    with _client(export_api.router, "/export", vault) as client:
        as_fhir = client.get(f"/export/fhir/{summary_id}/download")
        as_packet = client.get(f"/export/visit-prep/{summary_id}/download?format=markdown")
    assert (as_fhir.status_code, as_packet.status_code) == (404, 404)


def test_hc_expa_006_failed_audit_commit_leaves_no_artifact(tmp_path):
    """Order is stage, audit commit, vault commit. Read through a fresh engine, so the
    check is commit-level, not session-level. Would not notice: a failure after both
    commits."""
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    master = _master_db(commit_error=RuntimeError("audit commit failed"))
    with _client(export_api.router, "/export", vault, master_db=master) as client:
        with pytest.raises(RuntimeError, match="audit commit failed"):
            client.post("/export/doctor-summary", json={"format": "text"})
    assert asyncio.run(_rows(vault)) == []


def test_hc_expa_007_crypto_erase_removes_persisted_artifacts(tmp_path, monkeypatch):
    """Content-level, not filename-level: no file left under the data dir contains the
    artifact id or the seeded marker. Would not notice: copies outside the data dir
    (backups the user took, OS swap, filesystem journals)."""
    from tests.test_profile_deletion import _delete
    monkeypatch.setattr(type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path))
    vaults = {p: tmp_path / "vaults" / p / "vault.db" for p in (PROFILE_A, PROFILE_B)}
    art = {}
    for profile_id, marker in ((PROFILE_A, "zzerasemarkera"), (PROFILE_B, "zzerasemarkerb")):
        asyncio.run(_create_vault(vaults[profile_id], profile_id, marker))
        (vaults[profile_id].parent / "key.bin").write_bytes(b"sealed-key")
        (vaults[profile_id].parent / "key.method").write_text("password")
        with _client(export_api.router, "/export", vaults[profile_id], profile_id=profile_id) as client:
            art[profile_id] = client.post("/export/doctor-summary", json={"format": "text"}).json()["summary_id"]
    needles = (art[PROFILE_A].encode(), b"zzerasemarkera")

    def _leaks():
        return [p for p in tmp_path.rglob("*") if p.is_file() and any(n in p.read_bytes() for n in needles)]

    assert _leaks(), "the scan must see A's content before the erase, or it proves nothing"
    _register_open_vault(monkeypatch, PROFILE_A, vaults[PROFILE_A])
    _simulate_restart()
    asyncio.run(_delete(profile_id=PROFILE_A))
    assert not (tmp_path / "vaults" / PROFILE_A).exists()
    assert _leaks() == []
    assert [r.id for r in asyncio.run(_rows(vaults[PROFILE_B]))] == [art[PROFILE_B]]


def test_hc_expa_008_profile_migration_matches_model(tmp_path, monkeypatch):
    """Would not notice: column types or defaults (only the name set is compared)."""
    from alembic import command
    from core import migrations
    from core.config import settings
    from models.export_artifact import ExportArtifact
    monkeypatch.setattr(settings, "database_encryption_required", False)
    vault, key = tmp_path / "vault.db", b"0" * 32
    migrations.run_profile_migration(vault, key)
    assert migrations.get_profile_current_revision(vault, key) == NEW_HEAD
    with closing(_raw_connect(vault, key)) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(export_artifact)")}
    assert cols == set(ExportArtifact.__table__.columns.keys())
    config = migrations._get_alembic_config("profile")
    config.attributes["vault_path"] = vault
    config.attributes["encryption_key"] = key
    command.downgrade(config, PREV_HEAD)
    with closing(_raw_connect(vault, key)) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='export_artifact'").fetchall() == []
    command.upgrade(config, "head")
    assert migrations.get_profile_current_revision(vault, key) == NEW_HEAD


PHI_UNIT = "mmol/L (Patient: Jane Doe) DOB: 01/02/1980 MRN: A12345"
PHI_TOKENS = ("Jane", "Doe", "01/02/1980", "A12345")


@pytest.mark.parametrize("kind,gen,body,idkey,dl,dl_type", CASES, ids=CASE_IDS)
def test_hc_expa_009_persisted_payload_is_redacted(tmp_path, kind, gen, body, idkey, dl, dl_type):
    """I-10: the stored `payload_json` is the redacted output, not the raw text. The
    vault holds PHI in the unit field; the row (read raw, through a fresh engine) must
    not. Would not notice: PHI in a field this fixture does not seed, or a redactor
    that misses a shape (HC-EXPR owns the shapes)."""
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera", unit=PHI_UNIT))
    with _client(export_api.router, "/export", vault) as client:
        created = client.post(gen, json=body)
        assert created.status_code == 200, created.text
    rows = asyncio.run(_rows(vault))
    assert len(rows) == 1
    for token in PHI_TOKENS:
        assert token not in rows[0].payload_json, token
    assert "zzmarkera" in rows[0].payload_json  # the row is not simply empty


def test_hc_expa_010_download_with_locked_vault_is_403():
    """After a real restart no vault connection exists until re-login. Would not
    notice: a locked vault with a live in-process entry (the purge at lock clears it)."""
    manager = get_profile_db_manager()
    assert not manager.is_profile_connected(PROFILE_A)
    with _client(export_api.router, "/export", vault=None) as client:  # real get_profile_db_session
        response = client.get(f"/export/doctor-summary/{uuid.uuid4()}/download?format=text")
    assert response.status_code == 403
    assert "log in again" in response.json()["detail"]


# ---------------------------------------------------------------------------
# EXPORT-ARTIFACT-RETENTION (L0 ruling) - the four new HTTP tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind,gen,body,idkey,dl,dl_type", CASES, ids=CASE_IDS)
def test_hc_expa_011_row_older_than_ttl_is_not_served_and_is_deleted(
    tmp_path, monkeypatch, kind, gen, body, idkey, dl, dl_type
):
    """(a) The 30-minute `_EXPORT_TTL` applies to persisted rows: 29 minutes serves,
    31 minutes is the same 404 as an expired in-memory entry, and the row is gone from
    the table afterwards. Would not notice: clock skew between the vault file's
    `created_at` and the process clock, or a row with no `created_at`."""
    clock = {"now": T0}
    monkeypatch.setattr(core_time, "utcnow", lambda: clock["now"])
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    with _client(export_api.router, "/export", vault) as client:
        art_id = client.post(gen, json=body).json()[idkey]
    assert [r.id for r in asyncio.run(_rows(vault))] == [art_id]
    _simulate_restart()
    clock["now"] = T0 + timedelta(minutes=29)
    with _client(export_api.router, "/export", vault) as client:
        assert client.get(dl.format(id=art_id)).status_code == 200
    _simulate_restart()
    clock["now"] = T0 + timedelta(minutes=31)
    with _client(export_api.router, "/export", vault) as client:
        assert client.get(dl.format(id=art_id)).status_code == 404
    assert asyncio.run(_rows(vault)) == []  # deleted on read, not merely refused


def test_hc_expa_012_a_later_write_prunes_expired_rows(tmp_path, monkeypatch):
    """Rows past the TTL go on any later write, so the table cannot grow without
    bound. Would not notice: rows nobody ever writes or reads again (no job is
    licensed to sweep them; they stay until the profile is deleted)."""
    clock = {"now": T0}
    monkeypatch.setattr(core_time, "utcnow", lambda: clock["now"])
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    with _client(export_api.router, "/export", vault) as client:
        first = client.post("/export/doctor-summary", json={"format": "text"}).json()["summary_id"]
        clock["now"] = T0 + timedelta(minutes=31)
        second = client.post("/export/doctor-summary", json={"format": "text"}).json()["summary_id"]
    assert [r.id for r in asyncio.run(_rows(vault))] == [second]
    assert first != second


def _seed_all_kinds(vault: Path, profile_id: str) -> dict:
    """One artifact of each kind through the generate routes; returns {kind: id}."""
    ids = {}
    with _client(export_api.router, "/export", vault, profile_id=profile_id) as client:
        for kind, gen, body, idkey, _dl, _t in CASES:
            ids[kind] = client.post(gen, json=body).json()[idkey]
    return ids


def _assert_a_gone_b_intact(vaults: dict, b_ids: dict) -> None:
    assert asyncio.run(_rows(vaults[PROFILE_A])) == []
    assert sorted(r.id for r in asyncio.run(_rows(vaults[PROFILE_B]))) == sorted(b_ids.values())


@pytest.fixture
def two_open_vaults(tmp_path, monkeypatch):
    """A and B, each with three persisted artifacts, both open in the manager.
    Dicts are emptied so only the vault rows remain (a purge that clears memory
    alone would leave them)."""
    monkeypatch.setattr(type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path))
    vaults = {p: tmp_path / "vf" / p / "vault.db" for p in (PROFILE_A, PROFILE_B)}
    ids = {}
    for profile_id, marker in ((PROFILE_A, "zzmarkera"), (PROFILE_B, "zzmarkerb")):
        asyncio.run(_create_vault(vaults[profile_id], profile_id, marker))
        ids[profile_id] = _seed_all_kinds(vaults[profile_id], profile_id)
        assert len(asyncio.run(_rows(vaults[profile_id]))) == 3
        _register_open_vault(monkeypatch, profile_id, vaults[profile_id])
    _simulate_restart()
    return SimpleNamespace(vaults=vaults, ids=ids, root=tmp_path)


def test_hc_expa_013_logout_removes_the_profiles_rows_only(two_open_vaults):
    """(b)+(c) logout. Would not notice: rows in a vault that is not the open connection
    at logout (post-restart logout cannot reach a closed vault)."""
    with _profiles_client(PROFILE_A, _db_with_profile(None)) as prof:
        assert prof.post("/profiles/logout").status_code == 200
    _assert_a_gone_b_intact(two_open_vaults.vaults, two_open_vaults.ids[PROFILE_B])


def test_hc_expa_014_lock_removes_the_profiles_rows_only(two_open_vaults):
    """(b)+(c) lock. Same blind spot as HC-EXPA-013."""
    profile = SimpleNamespace(id=PROFILE_A, display_name="T", is_locked=False, password_hash="x",
                              created_at=T0, last_accessed_at=None)
    with _profiles_client(PROFILE_A, _db_with_profile(profile)) as prof:
        assert prof.post(f"/profiles/{PROFILE_A}/lock").status_code == 200
    _assert_a_gone_b_intact(two_open_vaults.vaults, two_open_vaults.ids[PROFILE_B])


def test_hc_expa_015_delete_removes_the_profiles_rows_only(two_open_vaults):
    """(b)+(c) delete. The vault file here sits outside the swept `vaults/<id>` dir, so
    the table query proves the purge itself removed the rows, not the directory sweep.
    Would not notice: the sweep of the real vault directory (HC-EXPA-007)."""
    _make_vault(two_open_vaults.root, PROFILE_A)
    profile = SimpleNamespace(id=PROFILE_A, display_name="T")
    with patch.object(profiles_api, "_load_profile_for_delete", AsyncMock(return_value=profile)), \
         patch.object(profiles_api, "authenticate_profile", AsyncMock(return_value=profile)), \
         _profiles_client(PROFILE_A, _FakeMasterDb()) as prof:
        resp = prof.request(
            "DELETE", f"/profiles/{PROFILE_A}",
            json={"password": "CorrectHorse1", "confirmation_phrase": PROFILE_DELETE_CONFIRMATION,
                  "export_acknowledged": True},
        )
    assert resp.status_code == 204, resp.text
    _assert_a_gone_b_intact(two_open_vaults.vaults, two_open_vaults.ids[PROFILE_B])


def test_hc_expa_016_a_purge_that_cannot_delete_fails_loudly(two_open_vaults):
    """A vault delete that errors must surface (500), never be swallowed, and it must run
    before the close. Would not notice: a purge that fails only on some rows."""
    from sqlalchemy import text

    async def _break_table():
        engine = _engine(two_open_vaults.vaults[PROFILE_A])
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE export_artifact RENAME TO export_artifact_gone"))
        await engine.dispose()

    asyncio.run(_break_table())
    close = AsyncMock()
    with _profiles_client(PROFILE_A, _db_with_profile(None), close=close) as prof:
        with pytest.raises(Exception, match="export_artifact"):
            prof.post("/profiles/logout")
    close.assert_not_awaited()  # the failed purge stopped the logout before the close
