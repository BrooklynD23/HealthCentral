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
import time
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import api.export as export_api
import api.pinboards as pinboards_api
import api.profiles as profiles_api
from api.profiles import PROFILE_DELETE_CONFIRMATION
from core import security as core_security
from core import time as core_time
from core.auth import Session, require_auth
from core.profile_database import (
    ProfileDatabaseBase,
    ProfileDatabaseConnection,
    get_profile_db_manager,
)
from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available
from core.token_revocation import TokenRevocationList
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
    db.execute.return_value = _Result(SimpleNamespace(id=profile_id, display_name="Zed Example"))
    if commit_error is not None:
        db.commit.side_effect = commit_error
    return db


ROUTE_CLIENT_JTI = "jti-test"  # the constant session jti route_client hands out


def _set_session_jti(client, profile_id: str, jti: str | None) -> None:
    """Swap the authenticated session for one with another jti (a new login), without
    touching route_client: a second override of the same `require_auth` dependency."""
    async def _auth() -> Session:
        return Session(profile_id=profile_id, profile_name="T",
                       expires_at=datetime.now(timezone.utc) + timedelta(hours=1), token_jti=jti)

    client.app.dependency_overrides[require_auth] = _auth


@contextmanager
def _client(router, prefix: str, vault: Path | None, profile_id: str = PROFILE_A, master_db=None,
            jti: str | None = ROUTE_CLIENT_JTI):
    """route_client over a real vault file. `vault=None` leaves the real
    `get_profile_db_session` in place (no connection open = locked vault). `jti` is
    the session's token jti (route_client's own constant unless a test names one)."""
    maker = async_sessionmaker(_engine(vault), expire_on_commit=False) if vault else None
    with route_client(router, prefix, profile_id=profile_id,
                      master_db=master_db or _master_db(profile_id), profile_db=maker) as client:
        if jti != ROUTE_CLIENT_JTI:
            _set_session_jti(client, profile_id, jti)
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
def _isolated_revocations(tmp_path, monkeypatch):
    """`core.security._jwt_revocation_list` is a cached module global that persists to
    `settings.app_data_path/.jwt_revoked_tokens.json`. Logout and lock revoke the session
    jti, and route_client's jti is the constant "jti-test", so without this a revoked
    "jti-test" would leak to every later test and onto disk. Test-side only."""
    monkeypatch.setattr(core_security, "_jwt_revocation_list",
                        TokenRevocationList(tmp_path / "revocations" / ".jwt_revoked_tokens.json"))


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


def test_hc_expa_010_download_with_locked_vault_is_refused():
    """After a real restart no vault connection exists until re-login. Would not
    notice: a locked vault with a live in-process entry (the purge at lock clears it)."""
    manager = get_profile_db_manager()
    assert not manager.is_profile_connected(PROFILE_A)
    with _client(export_api.router, "/export", vault=None) as client:  # real get_profile_db_session
        response = client.get(f"/export/doctor-summary/{uuid.uuid4()}/download?format=text")
    assert response.status_code == 401
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


async def _break_export_table(vault: Path) -> None:
    """Make every purge delete on `vault` raise (`no such table: export_artifact`)."""
    from sqlalchemy import text
    engine = _engine(vault)
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE export_artifact RENAME TO export_artifact_gone"))
    await engine.dispose()


def test_hc_expa_016_a_purge_that_cannot_delete_fails_loudly(two_open_vaults):
    """EXPORT-LIVE-LOGIN point 3, logout. A vault delete that errors must surface as a
    500, never be swallowed, and the cleanup must still run: the vault is closed and the
    session jti is revoked. Would not notice: a purge that fails only on some rows, or a
    close that is awaited on a different profile (the mock records the argument)."""
    asyncio.run(_break_export_table(two_open_vaults.vaults[PROFILE_A]))
    close = AsyncMock()
    with _end_session_client(PROFILE_A, _db_with_profile(None), "jti-logout-fail",
                             close=close, raise_server_exceptions=False) as prof:
        response = prof.post("/profiles/logout")
    assert response.status_code == 500, response.text
    close.assert_awaited_once_with(PROFILE_A)  # the failed purge no longer skips the close
    assert core_security.is_jwt_token_revoked("jti-logout-fail")


# ---------------------------------------------------------------------------
# EXPORT-SESSION-BIND (L0 ruling, #537 comment 6714721685) - HC-EXPA-017..
#
# An export is served to any live login of the owning profile (EXPORT-LIVE-LOGIN, #537
# comment 6717788852, which replaced the jti-equality rule): unexpired, same profile,
# stored session_jti non-empty and not revoked. A caller with no jti stays refused.
# Anything else is the same 404 as an expired export, and the row is deleted.
# ---------------------------------------------------------------------------


def _end_session_client(profile_id: str, master_db, jti: str, close=None,
                        raise_server_exceptions: bool = True):
    """The profiles router with the REAL `revoke_jwt_token` (the suite's
    `_profiles_client` mocks it), so a logout or lock revokes `jti` in the isolated list.
    Only the vault close and the profile audit are stubbed. `close` is that stub (pass
    one to assert on it); `raise_server_exceptions=False` turns a handler error into a 500."""
    @contextmanager
    def _cm():
        with patch.object(profiles_api, "close_profile_database_on_logout",
                          close if close is not None else AsyncMock()), \
             patch.object(profiles_api, "log_profile_event", AsyncMock()), \
             route_client(profiles_api.router, "/profiles", profile_id=profile_id,
                          master_db=master_db,
                          raise_server_exceptions=raise_server_exceptions) as client:
            _set_session_jti(client, profile_id, jti)
            yield client
    return _cm()


def _export_as(vault: Path, jti: str, case) -> str:
    """Generate one artifact as the session `jti`; returns its id."""
    _kind, gen, body, idkey, _dl, _t = case
    with _client(export_api.router, "/export", vault, jti=jti) as client:
        created = client.post(gen, json=body)
        assert created.status_code == 200, created.text
        return created.json()[idkey]


def _download_as(vault: Path, jti: str | None, url: str):
    with _client(export_api.router, "/export", vault, jti=jti) as client:
        return client.get(url)


def _revoke(jti: str) -> None:
    core_security.revoke_jwt_token(jti, int(time.time()) + 3600)
    assert core_security.is_jwt_token_revoked(jti)  # it really is in the (isolated) list


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_017_relogin_after_logout_is_not_served_and_row_is_deleted(tmp_path, case):
    """(a) The S1-S4 hole: after a backend restart the vault is not open at logout, so
    the purge cannot reach the row. Logout revokes the old jti and a re-login mints a new
    one; the new session must get 404 and the read deletes the row. Would not notice: a
    re-login that happens to reuse the same jti (HC-EXPA-018 owns the revocation check on
    its own), or a purge that does reach the vault (HC-EXPA-013)."""
    _kind, _gen, _body, _idkey, dl, _t = case
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = _export_as(vault, "jti-login-1", case)
    assert _download_as(vault, "jti-login-1", dl.format(id=art_id)).status_code == 200
    _simulate_restart()  # no vault is open in the manager: logout cannot purge the row
    with _end_session_client(PROFILE_A, _db_with_profile(None), "jti-login-1") as prof:
        assert prof.post("/profiles/logout").status_code == 200
    assert core_security.is_jwt_token_revoked("jti-login-1")
    assert [r.id for r in asyncio.run(_rows(vault))] == [art_id]  # the hole: row survived logout
    relogin = _download_as(vault, "jti-login-2", dl.format(id=art_id))
    assert relogin.status_code == 404, relogin.text
    assert "zzmarkera" not in relogin.text
    assert asyncio.run(_rows(vault)) == []  # deleted on that read


@pytest.mark.parametrize("restart", [False, True], ids=["memory_hit", "vault_hit"])
@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_018_revoked_row_jti_is_not_served_even_to_the_same_jti(tmp_path, case, restart):
    """(a) revocation path on its own. The caller presents the row's OWN jti, so the
    equality check passes; only `is_jwt_token_revoked` can refuse it. A new login has a
    new jti, so HC-EXPA-017 alone would pass an implementation that ignores revocation.
    Would not notice: a revocation that happens between the check and the response."""
    _kind, _gen, _body, _idkey, dl, _t = case
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = _export_as(vault, "jti-revoked", case)
    assert _download_as(vault, "jti-revoked", dl.format(id=art_id)).status_code == 200
    if restart:
        _simulate_restart()
    _revoke("jti-revoked")
    response = _download_as(vault, "jti-revoked", dl.format(id=art_id))
    assert response.status_code == 404, response.text
    assert asyncio.run(_rows(vault)) == []


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_019_relogin_after_lock_is_not_served_and_row_is_deleted(tmp_path, case):
    """(b) HC-EXPA-017 with lock instead of logout. Would not notice: the same blind spots
    as HC-EXPA-017."""
    _kind, _gen, _body, _idkey, dl, _t = case
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = _export_as(vault, "jti-lock-1", case)
    _simulate_restart()
    profile = SimpleNamespace(id=PROFILE_A, display_name="T", is_locked=False, password_hash="x",
                              created_at=T0, last_accessed_at=None)
    with _end_session_client(PROFILE_A, _db_with_profile(profile), "jti-lock-1") as prof:
        assert prof.post(f"/profiles/{PROFILE_A}/lock").status_code == 200
    assert core_security.is_jwt_token_revoked("jti-lock-1")
    assert [r.id for r in asyncio.run(_rows(vault))] == [art_id]
    relogin = _download_as(vault, "jti-lock-2", dl.format(id=art_id))
    assert relogin.status_code == 404, relogin.text
    assert asyncio.run(_rows(vault)) == []


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_020_restart_with_the_same_unrevoked_token_still_serves(tmp_path, case):
    """(c) The feature itself: a restart (dicts cleared, vault reopened through a fresh
    engine) with the same, unrevoked session token downloads inside 30 minutes. Would not
    notice: a real JWT round trip (route_client hands a constant jti, so a token whose jti
    changes across a restart is invisible here)."""
    _kind, _gen, _body, _idkey, dl, _t = case
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = _export_as(vault, "jti-restart", case)
    before = _download_as(vault, "jti-restart", dl.format(id=art_id))
    assert before.status_code == 200, before.text
    _simulate_restart()
    assert not core_security.is_jwt_token_revoked("jti-restart")
    after = _download_as(vault, "jti-restart", dl.format(id=art_id))
    assert after.status_code == 200, after.text
    assert after.content == before.content
    assert [r.id for r in asyncio.run(_rows(vault))] == [art_id]  # a served row is kept


async def _unbind_vault_row(path: Path, session_jti: str | None) -> None:
    """Re-insert the single row with the same payload and `session_jti` as given (None
    leaves the column out, so it is NULL), as a row written before this binding existed."""
    from models.export_artifact import ExportArtifact
    engine = _engine(path)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        old = (await s.execute(select(ExportArtifact))).scalar_one()
        fields = dict(id=old.id, kind=old.kind, profile_id=old.profile_id,
                      payload_json=old.payload_json, created_at=old.created_at)
        if session_jti is not None:
            fields["session_jti"] = session_jti
        await s.execute(delete(ExportArtifact))
        s.add(ExportArtifact(**fields))
        await s.commit()
    await engine.dispose()


@pytest.mark.parametrize("bad", [None, ""], ids=["null", "empty"])
@pytest.mark.parametrize("layer", ["vault", "memory"])
@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_021_artifact_without_a_session_jti_is_never_served(tmp_path, case, layer, bad):
    """(d) Fail closed: a NULL or empty `session_jti` (a row from before the binding, or
    a login that carried no jti) is never served. 404, and the row is deleted on read. The
    caller has a perfectly valid jti, so the missing binding is the only reason. Would not
    notice: a caller with no jti either (HC-EXPA-023)."""
    _kind, _gen, _body, _idkey, dl, _t = case
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = _export_as(vault, ROUTE_CLIENT_JTI, case)
    assert _download_as(vault, ROUTE_CLIENT_JTI, dl.format(id=art_id)).status_code == 200
    if layer == "vault":
        _simulate_restart()
        asyncio.run(_unbind_vault_row(vault, bad))
    else:
        for store in (export_api._summary_store, export_api._packet_store, export_api._fhir_store):
            for entry in store.values():
                entry["session_jti"] = bad
    response = _download_as(vault, ROUTE_CLIENT_JTI, dl.format(id=art_id))
    assert response.status_code == 404, response.text
    assert asyncio.run(_rows(vault)) == []
    for store in (export_api._summary_store, export_api._packet_store, export_api._fhir_store):
        assert art_id not in store  # the in-process entry went too


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_022_after_a_logs_out_session_b_is_not_served_and_row_is_deleted(tmp_path, case):
    """EXPORT-LIVE-LOGIN (e), first half. Session A exports and logs out (its jti is
    revoked). Session B of the SAME profile, with a different live jti, gets 404 and the
    read deletes the row. The vault is not open in the manager, so logout's purge cannot
    reach the row (the dicts go, the row stays): only the revoked row jti refuses B. Would
    not notice: a logout whose vault IS open (HC-EXPA-013 deletes the rows itself)."""
    _kind, _gen, _body, _idkey, dl, _t = case
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = _export_as(vault, "jti-session-a", case)
    with _end_session_client(PROFILE_A, _db_with_profile(None), "jti-session-a") as prof:
        assert prof.post("/profiles/logout").status_code == 200
    assert [r.id for r in asyncio.run(_rows(vault))] == [art_id]  # the purge did not reach it
    response = _download_as(vault, "jti-session-b", dl.format(id=art_id))
    assert response.status_code == 404, response.text
    assert "zzmarkera" not in response.text
    assert not core_security.is_jwt_token_revoked("jti-session-b")
    assert asyncio.run(_rows(vault)) == []


@pytest.mark.parametrize("restart", [False, True], ids=["memory_hit", "vault_hit"])
@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_026_a_live_export_is_served_to_another_live_login(tmp_path, case, restart):
    """EXPORT-LIVE-LOGIN (e), second half. A's export is served to B while A is still
    live (neither jti revoked), from the dict and from the vault row, and the row is kept.
    Would not notice: B being a different PROFILE (HC-EXPA-003 and -004 own that 403)."""
    _kind, _gen, _body, _idkey, dl, _t = case
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = _export_as(vault, "jti-session-a", case)
    before = _download_as(vault, "jti-session-a", dl.format(id=art_id))
    assert before.status_code == 200, before.text
    if restart:
        _simulate_restart()
    response = _download_as(vault, "jti-session-b", dl.format(id=art_id))
    assert response.status_code == 200, response.text
    assert response.content == before.content
    assert not core_security.is_jwt_token_revoked("jti-session-a")
    assert [r.id for r in asyncio.run(_rows(vault))] == [art_id]


@pytest.mark.parametrize("stored", ["jti-session-a", None], ids=["bound_row", "null_row"])
@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_023_caller_without_a_jti_is_never_served(tmp_path, case, stored):
    """A caller whose session carries no jti is refused, even against a NULL-bound row
    (None == None must not count as a match). Would not notice: an empty-string jti
    (HC-EXPA-021 covers the empty stored value)."""
    _kind, _gen, _body, _idkey, dl, _t = case
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = _export_as(vault, "jti-session-a", case)
    _simulate_restart()
    asyncio.run(_unbind_vault_row(vault, stored))
    response = _download_as(vault, None, dl.format(id=art_id))
    assert response.status_code == 404, response.text
    assert asyncio.run(_rows(vault)) == []


# ---------------------------------------------------------------------------
# EXPORT-LIVE-LOGIN (L0 ruling, #537 comment 6717788852) - HC-EXPA-024..
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("route", ["lock", "delete"])
def test_hc_expa_024_failed_purge_still_closes_the_vault_and_revokes(two_open_vaults, route):
    """Point 3 for lock and delete: when the export purge raises, the response is a 500,
    the vault is still closed, and the session jti is still revoked (a lock whose purge
    failed used to leave the vault open and the token alive). Would not notice: a close
    that runs but for the wrong profile (the mock is asserted with the profile id), or a
    purge that fails on a vault other than the open one."""
    jti = f"jti-{route}-fail"
    asyncio.run(_break_export_table(two_open_vaults.vaults[PROFILE_A]))
    close = AsyncMock()
    if route == "lock":
        profile = SimpleNamespace(id=PROFILE_A, display_name="T", is_locked=False,
                                  password_hash="x", created_at=T0, last_accessed_at=None)
        with _end_session_client(PROFILE_A, _db_with_profile(profile), jti, close=close,
                                 raise_server_exceptions=False) as prof:
            response = prof.post(f"/profiles/{PROFILE_A}/lock")
    else:
        _make_vault(two_open_vaults.root, PROFILE_A)
        profile = SimpleNamespace(id=PROFILE_A, display_name="T")
        with patch.object(profiles_api, "_load_profile_for_delete", AsyncMock(return_value=profile)), \
             patch.object(profiles_api, "authenticate_profile", AsyncMock(return_value=profile)), \
             _end_session_client(PROFILE_A, _FakeMasterDb(), jti, close=close,
                                 raise_server_exceptions=False) as prof:
            response = prof.request(
                "DELETE", f"/profiles/{PROFILE_A}",
                json={"password": "CorrectHorse1", "confirmation_phrase": PROFILE_DELETE_CONFIRMATION,
                      "export_acknowledged": True},
            )
    assert response.status_code == 500, response.text
    close.assert_awaited_once_with(PROFILE_A)
    assert core_security.is_jwt_token_revoked(jti)


def test_hc_expa_025_lock_revokes_even_when_the_close_raises(two_open_vaults):
    """Point 3, nested finally at lock: the purge works, the close raises, and the jti is
    still revoked; the error propagates as a 500. Would not notice: a close that raises
    after partly clearing keys (the close is a mock here, HC-PDB owns the real one)."""
    profile = SimpleNamespace(id=PROFILE_A, display_name="T", is_locked=False,
                              password_hash="x", created_at=T0, last_accessed_at=None)
    close = AsyncMock(side_effect=RuntimeError("close failed"))
    with _end_session_client(PROFILE_A, _db_with_profile(profile), "jti-close-fail", close=close,
                             raise_server_exceptions=False) as prof:
        response = prof.post(f"/profiles/{PROFILE_A}/lock")
    assert response.status_code == 500, response.text
    close.assert_awaited_once_with(PROFILE_A)
    assert core_security.is_jwt_token_revoked("jti-close-fail")
    assert asyncio.run(_rows(two_open_vaults.vaults[PROFILE_A])) == []  # the purge itself ran


def _login_client(master_db, profile):
    """The profiles router with the REAL login route and the REAL `create_session_token`,
    so every call mints a token with a fresh `jti`. Only password check, vault open and
    the profile audit are stubbed."""
    @contextmanager
    def _cm():
        with patch.object(profiles_api, "authenticate_profile", AsyncMock(return_value=profile)), \
             patch.object(profiles_api, "open_profile_database_on_login", AsyncMock()), \
             patch.object(profiles_api, "_audit_fk_orphan_cleanup", AsyncMock()), \
             patch.object(profiles_api, "log_profile_event", AsyncMock()), \
             route_client(profiles_api.router, "/profiles", profile_id=PROFILE_A,
                          master_db=master_db) as client:
            yield client
    return _cm()


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_027_real_restart_then_new_login_serves_and_old_logout_ends_it(
    tmp_path, monkeypatch, case
):
    """The feature itself, over HTTP. Export under login 1, restart
    (nothing open in the manager, dicts cleared), log in again through /profiles/login:
    a NEW jti. Within 30 minutes the download is 200. Then the OLD token logs out
    (real bearer through the real `require_auth`): its jti is revoked, the row is not yet
    gone, and the next download is 404 and deletes the row. Under the retired equality
    rule the first download was already 404 here, which is the bug. Would not notice: the
    vault being reopened with the SQLCipher key (the suite runs unencrypted), or a
    clock that moves past 30 minutes (HC-EXPA-011 owns that). Also not noticed: the export
    and both downloads use route_client's `require_auth` override with the jti injected
    (`_set_session_jti`), so the real bearer-to-`token_jti` mapping on the second login is
    only exercised by the logins and the final logout; `open_profile_database_on_login`
    is stubbed, so the real `get_profile_db_session` after re-login is not exercised;
    and the revocation list dropping an entry once its token's `exp` passes (open
    finding, needs an L0 ruling)."""
    _kind, _gen, _body, _idkey, dl, _t = case
    monkeypatch.setattr(core_security, "_jwt_secret_cache", "test-secret-" + "x" * 32)
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    profile = SimpleNamespace(id=PROFILE_A, display_name="T", is_locked=False,
                              password_hash="x", created_at=T0, last_accessed_at=None)
    master = _db_with_profile(profile)
    login = {"profile_id": PROFILE_A, "password": "CorrectHorse1"}

    with _login_client(master, profile) as client:
        token1 = client.post("/profiles/login", json=login).json()["access_token"]
    jti1 = core_security.verify_token(token1)["jti"]
    art_id = _export_as(vault, jti1, case)
    first = _download_as(vault, jti1, dl.format(id=art_id))
    assert first.status_code == 200, first.text

    _simulate_restart()  # backend restart: dicts gone, no vault connection open
    assert not get_profile_db_manager().is_profile_connected(PROFILE_A)
    with _login_client(master, profile) as client:
        response = client.post("/profiles/login", json=login)
        assert response.status_code == 200, response.text
        token2 = response.json()["access_token"]
    jti2 = core_security.verify_token(token2)["jti"]
    assert jti2 != jti1  # every login mints a new jti

    after = _download_as(vault, jti2, dl.format(id=art_id))
    assert after.status_code == 200, after.text
    assert after.content == first.content
    assert [r.id for r in asyncio.run(_rows(vault))] == [art_id]

    with _end_session_client(PROFILE_A, master, jti1, close=AsyncMock()) as prof:
        prof.app.dependency_overrides.pop(require_auth)  # the REAL bearer check
        out = prof.post("/profiles/logout", headers={"Authorization": f"Bearer {token1}"})
    assert out.status_code == 200, out.text
    assert core_security.is_jwt_token_revoked(jti1)
    assert not core_security.is_jwt_token_revoked(jti2)
    assert [r.id for r in asyncio.run(_rows(vault))] == [art_id]  # logout did not reach it
    gone = _download_as(vault, jti2, dl.format(id=art_id))
    assert gone.status_code == 404, gone.text
    assert asyncio.run(_rows(vault)) == []


async def _insert_rows(path: Path, rows: list[dict]) -> None:
    from models.export_artifact import ExportArtifact
    engine = _engine(path)
    async with async_sessionmaker(engine)() as s:
        for row in rows:
            s.add(ExportArtifact(kind="doctor_summary", payload_json="{}", **row))
        await s.commit()
    await engine.dispose()


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_hc_expa_028_saving_prunes_this_profiles_dead_rows_only(tmp_path, monkeypatch, case):
    """Each save deletes the saving profile's rows that are expired, have a NULL or empty
    jti, or have a revoked jti. A live row of another login of the same profile stays, the
    new row is there, and every row of ANOTHER profile in the same vault file stays (the
    file is shared on purpose: the prune must filter by profile_id). Asserted by querying
    the table. Would not notice: the pinboard export route (it shares `_save_artifact`;
    HC-PIN-* cover its call), or a row that is dead for two reasons at once."""
    clock = {"now": T0}
    monkeypatch.setattr(core_time, "utcnow", lambda: clock["now"])
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    _revoke("jti-dead")
    fresh, stale = T0 - timedelta(minutes=5), T0 - timedelta(minutes=31)

    def row(id_, profile_id, jti, created):
        return dict(id=id_, profile_id=profile_id, session_jti=jti, created_at=created)

    asyncio.run(_insert_rows(vault, [
        row("a-expired", PROFILE_A, "jti-other-live", stale),
        row("a-null", PROFILE_A, None, fresh),
        row("a-empty", PROFILE_A, "", fresh),
        row("a-revoked", PROFILE_A, "jti-dead", fresh),
        row("a-live", PROFILE_A, "jti-other-live", fresh),
        row("b-expired", PROFILE_B, "jti-other-live", stale),
        row("b-null", PROFILE_B, None, fresh),
        row("b-revoked", PROFILE_B, "jti-dead", fresh),
        row("b-live", PROFILE_B, "jti-other-live", fresh),
    ]))
    new_id = _export_as(vault, "jti-prune-live", case)
    assert {r.id for r in asyncio.run(_rows(vault))} == {
        new_id, "a-live", "b-expired", "b-null", "b-revoked", "b-live"
    }
