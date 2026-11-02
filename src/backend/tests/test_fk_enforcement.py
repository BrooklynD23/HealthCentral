"""C-P6 / SQL-FK-001: PRAGMA foreign_keys is ON on every application engine.

SQLite defaults the pragma OFF per connection, so every ``ondelete=`` in the
models was inert. HC-FK-001..003 pin the pragma on *more than one distinct
physical connection* per engine (one session proves one connection and
silently misses the rest of the pool).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))


async def _fk_pragma_on_distinct_connections(engine) -> int:
    """Hold two pooled connections at once; return the number of distinct ones.

    Asserts ``PRAGMA foreign_keys`` is 1 on each.
    """
    async with engine.connect() as c1, engine.connect() as c2:
        raw1 = await c1.get_raw_connection()
        raw2 = await c2.get_raw_connection()
        assert raw1.driver_connection is not raw2.driver_connection
        for conn in (c1, c2):
            assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    return 2


# --------------------------------------------------------------------------
# HC-FK-001: master engine
# --------------------------------------------------------------------------


def test_hc_fk_001_master_engine_registers_the_pragma_listener():
    """The real master engine must run PRAGMA foreign_keys=ON on connect.

    GATE-12 forbids opening the real master DB in a test, so the pool's
    ``connect`` listeners are driven with a recording stand-in for the DBAPI
    connection instead of a real connection.
    """
    from core.database import engine

    if engine.sync_engine.url.get_backend_name() != "sqlite":
        pytest.skip("master engine is not SQLite in this configuration")

    class _Cursor:
        def __init__(self, log):
            self.log = log

        def execute(self, sql, *a):
            self.log.append(sql)

        def close(self):
            pass

    class _Dbapi:
        def __init__(self):
            self.log = []

        def cursor(self):
            return _Cursor(self.log)

        def __getattr__(self, name):  # the dialect's own on-connect hook
            return lambda *a, **k: None

    fake = _Dbapi()
    for fn in list(engine.sync_engine.pool.dispatch.connect):
        try:
            fn(fake, None)
        except AttributeError:
            pass  # the dialect's own hook wants a real sqlite3 connection
    assert "PRAGMA foreign_keys=ON" in fake.log


@pytest.mark.asyncio
async def test_hc_fk_001b_install_helper_sets_pragma_on_every_connection(tmp_path):
    """install_sqlite_foreign_keys on a file engine: >1 distinct connection."""
    from core.database import install_sqlite_foreign_keys

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'm.db'}")
    try:
        install_sqlite_foreign_keys(engine.sync_engine)
        assert await _fk_pragma_on_distinct_connections(engine) == 2
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_fk_001c_engine_without_helper_has_pragma_off(tmp_path):
    """Control: the check above can fail. A bare engine reports 0."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'bare.db'}")
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 0
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# HC-FK-002: profile engine (the real open path)
# --------------------------------------------------------------------------

_PASSWORD = "Fk-Enforce-Pass-1!"


def _make_vault(root: Path, profile_id: str) -> Path:
    """Seal a generated key into vaults/<pid>/ (real key files, no mocks)."""
    from core.security import generate_encryption_key, seal_key_with_dpapi

    vault = root / "vaults" / profile_id
    vault.mkdir(parents=True)
    sealed, method = seal_key_with_dpapi(
        generate_encryption_key(),
        fallback_password=_PASSWORD,
        force_password=True,
    )
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)
    return vault


@pytest.mark.asyncio
async def test_hc_fk_002_profile_engine_pragma_on_after_key_and_migration(
    tmp_path, monkeypatch
):
    from core.config import settings
    from core.profile_database import get_profile_db_manager

    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    pid = str(uuid.uuid4())
    _make_vault(tmp_path, pid)
    manager = get_profile_db_manager()
    try:
        connection = await manager.open_profile_database(pid, _PASSWORD)
        assert await _fk_pragma_on_distinct_connections(connection.engine) == 2
        # the key listener still runs first: the migrated schema is readable
        async with connection.engine.connect() as conn:
            n = (await conn.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE name='care_plan_task'"
            ))).scalar()
            assert n == 1
    finally:
        await manager.close_profile_database(pid)


# --------------------------------------------------------------------------
# HC-FK-003: test factory
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hc_fk_003_fk_profile_engine_factory_enforces():
    from tests.support.db import fk_profile_engine

    engine = fk_profile_engine()
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Enforcement proofs: the pragma changes behaviour, not just a setting
# --------------------------------------------------------------------------

import models  # noqa: E402,F401  registers every model on both metadatas
import models.response_feedback  # noqa: E402,F401  not exported by models/__init__
from core.profile_database import ProfileDatabaseBase  # noqa: E402


_DUMMY = (
    ("BOOL", 0), ("INT", 1), ("FLOAT", 0.5),
    ("DATETIME", "2026-01-01 00:00:00.000000"), ("DATE", "2026-01-01"),
    ("TIME", "08:00:00"), ("BLOB", b"\x00"),
)


def _row(sc, table: str, **values) -> str:
    """Insert one row on a sync Connection, filling other NOT NULL columns."""
    row = dict(values)
    for _cid, name, ctype, notnull, default, _pk in sc.exec_driver_sql(
        f"PRAGMA table_info({table})"
    ).fetchall():
        if name in row or not notnull or default is not None:
            continue
        upper = (ctype or "").upper()
        row[name] = next((v for key, v in _DUMMY if key in upper), f"v-{name}")
    sc.exec_driver_sql(
        f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join('?' for _ in row)})",
        tuple(row.values()),
    )
    return row["id"]


async def _count(conn, table: str, where: str = "1=1") -> int:
    return (await conn.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"))).scalar()


async def _profile_engine(fk: bool):
    from tests.support.db import fk_profile_engine

    engine = fk_profile_engine() if fk else create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    return engine


@pytest.mark.asyncio
@pytest.mark.parametrize("fk,survivors", [(True, 0), (False, 1)], ids=["pragma-on", "pragma-off-control"])
async def test_hc_fk_010_cascade_removes_children_of_a_core_delete(fk, survivors):
    """A core ``delete(Chunk)`` (the shape api/documents.py uses) now removes
    the chunk's embedding. With the pragma off the embedding is orphaned: the
    control row proves this assertion can fail."""
    from sqlalchemy import delete

    from models import Chunk

    engine = await _profile_engine(fk)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sc: (
                _row(sc, "documents", id="D1"),
                _row(sc, "chunks", id="C1", doc_id="D1"),
                _row(sc, "embeddings", id="E1", chunk_id="C1"),
            ))
        async with engine.begin() as conn:
            await conn.execute(delete(Chunk).where(Chunk.doc_id == "D1"))
        async with engine.connect() as conn:
            assert await _count(conn, "chunks") == 0
            assert await _count(conn, "embeddings") == survivors
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_fk_011_set_null_keeps_the_dose_and_undeclared_relations_do_nothing():
    from sqlalchemy import delete

    from models import ChatSession, MedicationSchedule

    engine = await _profile_engine(True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sc: (
                _row(sc, "medications", id="M1"),
                _row(sc, "medication_schedules", id="S1", medication_id="M1"),
                _row(sc, "doses_taken", id="DT1", medication_id="M1", schedule_id="S1"),
                # response_feedback.session_id has NO declared FK (logical L1)
                _row(sc, "chat_sessions", id="CS1"),
                _row(sc, "response_feedback", id="RF1", session_id="CS1", turn_id="T1"),
            ))
        async with engine.begin() as conn:
            await conn.execute(delete(MedicationSchedule).where(MedicationSchedule.id == "S1"))
            await conn.execute(delete(ChatSession).where(ChatSession.id == "CS1"))
        async with engine.connect() as conn:
            assert await _count(conn, "medication_schedules") == 0
            assert await _count(conn, "doses_taken", "id='DT1' AND schedule_id IS NULL") == 1
            # no phantom enforcement: the logical relation is untouched
            assert await _count(conn, "response_feedback", "id='RF1' AND session_id='CS1'") == 1
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Crypto-erase on the real master schema with the pragma ON
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hc_fk_012_profile_delete_still_erases_with_master_pragma_on(tmp_path, monkeypatch):
    """delete_profile's master transaction (audit purge, schedule, profile row,
    tombstone with ``profile_id=None``) must not be reordered or broken by FK
    enforcement. Master schema via ``Base.metadata`` on a pragma-ON engine; the
    other profile's rows must survive."""
    from datetime import datetime
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    import api.profiles as profiles_api
    from api.profiles import PROFILE_DELETE_CONFIRMATION
    from core.database import Base
    from models.audit import AuditLog
    from models.backup_schedule import BackupSchedule
    from models.profile import Profile
    from tests.support.db import fk_profile_engine
    from tests.support.routes import route_client

    monkeypatch.setattr(type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path))
    engine = fk_profile_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    now = datetime(2026, 1, 1)
    async with AsyncSession(engine, expire_on_commit=False) as db:
        for pid in ("profile-a", "profile-b"):
            db.add(Profile(
                id=pid, display_name=pid, encryption_key_id="k", password_hash="h",
                password_salt="s", is_locked=False, created_at=now, updated_at=now,
            ))
        await db.commit()
        for pid in ("profile-a", "profile-b"):
            db.add(AuditLog(profile_id=pid, event_type="profile.login", action="profile.login"))
            db.add(BackupSchedule(id=f"bs-{pid}", profile_id=pid))
            (tmp_path / "vaults" / pid).mkdir(parents=True)
        await db.commit()

        # over HTTP so Depends(require_profile_access(), get_db) really runs
        with patch.object(profiles_api, "authenticate_profile", AsyncMock(return_value=SimpleNamespace(id="profile-a"))), \
             patch.object(profiles_api, "close_profile_database_on_logout", AsyncMock()), \
             patch.object(profiles_api, "revoke_jwt_token", MagicMock()), \
             route_client(profiles_api.router, "/profiles", profile_id="profile-a", master_db=db) as client:
            resp = client.request(
                "DELETE", "/profiles/profile-a",
                json={
                    "password": "CorrectHorse1",
                    "confirmation_phrase": PROFILE_DELETE_CONFIRMATION,
                    "export_acknowledged": True,
                },
            )
        assert resp.status_code == 204, resp.text

        audit = (await db.execute(select(AuditLog))).scalars().all()
        assert [a.profile_id for a in audit if a.event_type == "profile.delete"] == [None], "one tombstone"
        assert {a.profile_id for a in audit if a.profile_id} == {"profile-b"}
        assert [r.profile_id for r in (await db.execute(select(BackupSchedule))).scalars()] == ["profile-b"]
        assert [p.id for p in (await db.execute(select(Profile))).scalars()] == ["profile-b"]
        async with engine.connect() as conn:
            assert (await conn.execute(text("PRAGMA foreign_key_check"))).fetchall() == []
    await engine.dispose()


# --------------------------------------------------------------------------
# /profiles/test/reset with the pragma ON
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hc_fk_013_test_reset_does_not_500_and_records_what_it_leaves(tmp_path, monkeypatch):
    """The reset tuple has no CarePlanTask. Before 017 the document delete hit
    ``care_plan_task`` with NO ACTION and raised under the pragma; now it SET NULLs.

    The survivors are recorded, not "fixed": the tuple is deliberately NOT
    expanded here (audit P2 / plan 07). When it is, the survivor dict below
    must go to all zeros.
    """
    from datetime import datetime, timedelta, timezone

    import api.profiles as profiles_api
    from core.auth import Session, get_profile_db_session, require_auth
    from tests.support.routes import route_client

    monkeypatch.setattr(type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path))
    engine = await _profile_engine(True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sc: (
                _row(sc, "documents", id="D1", profile_id="profile-a"),
                _row(sc, "document_entity", id="E1", doc_id="D1"),
                _row(sc, "document_category", id="K1", doc_id="D1"),
                _row(sc, "care_plan_task", id="T1", title="t", source_document_id="D1", source_entity_id="E1"),
                _row(sc, "chunks", id="C1", doc_id="D1"),
                _row(sc, "embeddings", id="EM1", chunk_id="C1"),
                _row(sc, "observations", id="OB1", doc_id="D1"),
                _row(sc, "lab_interpretations", id="LI1", observation_id="OB1"),
                _row(sc, "medications", id="M1"),
                _row(sc, "medication_schedules", id="S1", medication_id="M1"),
                _row(sc, "doses_taken", id="DT1", medication_id="M1", schedule_id="S1"),
                _row(sc, "chat_sessions", id="CS1"),
                _row(sc, "chat_turns", id="CT1", session_id="CS1"),
                _row(sc, "response_feedback", id="RF1", session_id="CS1", turn_id="CT1"),
                _row(sc, "pinboard", id="PB1"),
                _row(sc, "pinboard_item", id="PI1", pinboard_id="PB1", item_type="document", item_id="D1"),
            ))
        from sqlalchemy.ext.asyncio import AsyncSession

        profile_db = AsyncSession(engine, expire_on_commit=False)

        with route_client(profiles_api.router, "/profiles", raise_server_exceptions=False) as client:
            async def _auth():
                return Session(
                    profile_id="profile-a", profile_name="Playwright E2E reset",
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1), token_jti="j",
                )

            async def _db():
                return profile_db

            client.app.dependency_overrides[require_auth] = _auth
            client.app.dependency_overrides[get_profile_db_session] = _db
            resp = client.post("/profiles/test/reset")
        await profile_db.close()

        assert resp.status_code == 204, resp.text
        async with engine.connect() as conn:
            wiped = ["documents", "document_entity", "document_category", "chunks", "embeddings",
                     "observations", "lab_interpretations", "medications", "medication_schedules", "doses_taken"]
            assert {t: await _count(conn, t) for t in wiped} == {t: 0 for t in wiped}
            left = ["care_plan_task", "chat_sessions", "chat_turns", "response_feedback", "pinboard", "pinboard_item"]
            assert {t: await _count(conn, t) for t in left} == {t: 1 for t in left}
            # the care task kept its row; its links were nulled by SET NULL
            assert await _count(conn, "care_plan_task", "source_document_id IS NULL AND source_entity_id IS NULL") == 1
            assert (await conn.execute(text("PRAGMA foreign_key_check"))).fetchall() == []
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# HC-FKC-008: deleting a document from a migrated *file* vault, pragma ON
# --------------------------------------------------------------------------

from alembic import command  # noqa: E402

from core import migrations  # noqa: E402
from core.config import settings as _settings  # noqa: E402
from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available  # noqa: E402
from tests.test_fk_migration_017 import (  # noqa: E402
    KEY, REV_016, _alembic_cfg, _connect, _insert,
)

DOC_ID = "3f2c9d1e-0000-4000-8000-000000000001"


def _pragma_on_vault_engine(vault: Path):
    """Async engine on a keyed file vault with the production FK listener."""
    from core.database import install_sqlite_foreign_keys

    kwargs = {}
    if is_sqlcipher_available():
        import aiosqlite

        module = get_sqlcipher_module()

        async def _connect_vault():
            conn = aiosqlite.Connection(lambda: module.connect(str(vault)), 64)
            conn._thread.daemon = True
            return await conn

        kwargs["async_creator"] = _connect_vault
    engine = create_async_engine(f"sqlite+aiosqlite:///{vault}", **kwargs)

    @event.listens_for(engine.sync_engine, "connect")
    def _key(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA cipher_version")
        row = cursor.fetchone()
        if row and row[0]:
            cursor.execute(f"PRAGMA key = \"x'{migrations._key_to_hex(KEY)}'\"")
        cursor.close()

    install_sqlite_foreign_keys(engine.sync_engine)
    return engine


def _vault_with_care_task(tmp_path, monkeypatch, *, upgrade: bool, orphans: bool = True):
    """File vault at 016: doc, entity E1, category K1, care task T1 -> (doc, E1),
    plus planted orphans P3 and P4. Optionally upgraded to head."""
    monkeypatch.setattr(_settings, "database_encryption_required", False)
    vault = tmp_path / "vault.db"
    cfg = _alembic_cfg(vault)
    command.upgrade(cfg, REV_016)
    conn = _connect(vault)
    try:
        _insert(conn, "documents", id=DOC_ID, profile_id="profile-a", doc_type="visit_note_pdf")
        _insert(conn, "document_entity", id="E1", doc_id=DOC_ID)
        _insert(conn, "document_category", id="K1", doc_id=DOC_ID, category="visit_notes")
        _insert(conn, "care_plan_task", id="T1", title="Repeat CBC", source_document_id=DOC_ID,
                source_entity_id="E1", source_quote="repeat CBC")
        if orphans:
            _insert(conn, "embeddings", id="OE", chunk_id="MISSING")  # P3
            _insert(conn, "lab_interpretations", id="OI", observation_id="MISSING")  # P4
        conn.commit()
    finally:
        conn.close()
    if upgrade:
        command.upgrade(cfg, "head")
    return vault


async def _delete_document_over_http(
    vault: Path, tmp_path, monkeypatch, doc_id: str, raised: list | None = None
):
    """DELETE /documents/{id}. With ``raised`` given, server exceptions propagate
    out of the app; the one that did is appended to it and the response is None."""
    from unittest.mock import AsyncMock, MagicMock

    from sqlalchemy.ext.asyncio import AsyncSession

    from api import documents as documents_api
    from api.documents import router as documents_router
    from core.auth import get_profile_db_session
    from tests.support.routes import route_client

    monkeypatch.setattr(type(documents_api.settings), "app_data_path", property(lambda self: tmp_path))
    engine = _pragma_on_vault_engine(vault)
    master = MagicMock()
    master.commit = AsyncMock()
    master.rollback = AsyncMock()
    master.execute = AsyncMock()
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        with route_client(
            documents_router, "/documents", profile_id="profile-a",
            master_db=master, raise_server_exceptions=raised is not None,
        ) as client:
            async def _db():
                return session

            client.app.dependency_overrides[get_profile_db_session] = _db
            resp = None
            try:
                resp = client.delete(f"/documents/{doc_id}")
            except Exception as exc:  # only reachable with ``raised``
                if raised is None:
                    raise
                raised.append(exc)
        await session.close()
        async with engine.connect() as conn:
            state = {
                "tasks": (await conn.execute(text(
                    "SELECT id, source_document_id, source_entity_id FROM care_plan_task"
                ))).fetchall(),
                "documents": await _count(conn, "documents", f"id='{doc_id}'"),
                "fk_check": (await conn.execute(text("PRAGMA foreign_key_check"))).fetchall(),
            }
        return resp, state
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_fkc_008_document_delete_after_migration_is_204(tmp_path, monkeypatch):
    vault = _vault_with_care_task(tmp_path, monkeypatch, upgrade=True)

    resp, state = await _delete_document_over_http(vault, tmp_path, monkeypatch, DOC_ID)

    assert resp.status_code == 204, resp.text
    assert state["documents"] == 0
    assert [tuple(r) for r in state["tasks"]] == [("T1", None, None)], "care task must be kept, links NULL"
    # P3/P4 orphans were removed by the 017 cleanup, so nothing dangles
    assert state["fk_check"] == []


@pytest.mark.asyncio
async def test_hc_fkc_008b_same_delete_on_a_016_vault_is_a_500(tmp_path, monkeypatch):
    """RED control: pragma ON over an un-migrated vault. ``delete(DocumentEntity)``
    runs before the care-task update while ``care_plan_task.source_entity_id`` is
    still NO ACTION, so the delete fails. This is the failure 017 exists to prevent."""
    vault = _vault_with_care_task(tmp_path, monkeypatch, upgrade=False)
    raised: list = []

    resp, state = await _delete_document_over_http(
        vault, tmp_path, monkeypatch, DOC_ID, raised=raised
    )

    # the cause, not just "some 500": a broken fixture would also give a 500
    assert resp is None and len(raised) == 1
    # SQLAlchemy's IntegrityError, or the driver's own (sqlcipher3 / sqlite3) when
    # it surfaces unwrapped; either way the constraint is the cause
    assert type(raised[0]).__name__ == "IntegrityError", repr(raised[0])
    assert "FOREIGN KEY constraint failed" in str(raised[0])
    assert state["documents"] == 1, "the failed delete must roll back"


@pytest.mark.asyncio
async def test_hc_fkc_008c_orphans_alone_do_not_break_a_delete(tmp_path, monkeypatch):
    """Recorded finding: planted orphans (P3, P4) on an un-migrated vault, pragma
    ON, no care task pointing at the document. SQLite checks only the violations
    a statement itself causes, so deleting an unrelated healthy document works."""
    vault = _vault_with_care_task(tmp_path, monkeypatch, upgrade=False)
    conn = _connect(vault)
    try:
        conn.execute("DELETE FROM care_plan_task")
        conn.commit()
    finally:
        conn.close()

    resp, state = await _delete_document_over_http(vault, tmp_path, monkeypatch, DOC_ID)

    assert resp.status_code == 204, resp.text
    assert state["documents"] == 0
    # the untouched orphans are still there for the migration to clean
    assert {r[0] for r in state["fk_check"]} == {"embeddings", "lab_interpretations"}
