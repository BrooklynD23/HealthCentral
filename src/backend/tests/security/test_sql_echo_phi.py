"""S-1 — SQL echo must never print bound PHI.

With the default development config (DEBUG=true) both runtime engines were
created with ``echo=settings.debug``. SQLAlchemy then logged every statement
**with its bound parameters**: lab values, chat text, document text, display
names and bcrypt hashes reached stderr.

Why not ``caplog``: both Alembic ``env.py`` files call
``logging.config.fileConfig``, which removes every root handler (caplog's
included) and every handler on ``sqlalchemy.engine``. A caplog assertion made
after a migration ran can only pass. These tests capture in ways fileConfig
cannot undo, and each proves its capture is still alive (a canary) before
trusting an empty result.

Test IDs: HC-SQLECHO-001..004.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import APIRouter

import core.database as core_db
from core.config import Settings, settings
from core.profile_database import get_profile_db_manager
from core.security import generate_encryption_key, seal_key_with_dpapi

PASSWORD = "S1echo-Pass-123!"
SENT_ANALYTE = "S1ECHO_ANALYTE_hba1c"
SENT_VALUE = 731.0419  # repr appears verbatim in echoed params
SENT_DOCTEXT = "S1ECHO_DOCTEXT HIV-1 RNA detected"
SENT_CHAT = "S1ECHO_CHAT is my result dangerous"
SENT_NAME = "S1ECHO_NAME Jane Doe"
SENT_NOTE = "S1ECHO_NOTE_VIA_HTTP"
CANARY = "S1ECHO_CANARY"


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


class _SqlLogTap:
    """Record every ``sqlalchemy.*`` record that reaches ``Logger.handle``.

    Patched on the Logger class, so a fileConfig run in the middle of a request
    (the vault open inside profile creation runs the profile migration) cannot
    detach it. Anything recorded here was on its way to a real sink.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.lines: list[str] = []
        original = logging.Logger.handle
        tap = self

        def handle(logger_self: logging.Logger, record: logging.LogRecord):
            if record.name.startswith("sqlalchemy") and not logger_self.disabled:
                tap.lines.append(record.getMessage())
            return original(logger_self, record)

        monkeypatch.setattr(logging.Logger, "handle", handle)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def _assert_absent(text: str, needles: list[str]) -> None:
    leaked = [n for n in needles if n in text]
    assert not leaked, f"PHI reached the SQL log: {leaked}"


def _make_vault(root: Path, profile_id: str) -> None:
    vault = root / "vaults" / profile_id
    vault.mkdir(parents=True)
    # Test fixture: password seal keeps the test deterministic on every OS.
    sealed, method = seal_key_with_dpapi(
        generate_encryption_key(), fallback_password=PASSWORD, force_password=True
    )
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)


async def _seed_vault(conn, profile_id: str) -> str:
    from models.chat_session import ChatSession, ChatTurn
    from models.chunk import Chunk
    from models.document import Document
    from models.observation import Observation

    doc_id, obs_id, sess_id = (str(uuid.uuid4()) for _ in range(3))
    async with conn.session_maker() as s:
        s.add(Document(id=doc_id, profile_id=profile_id, path_hash="a" * 64,
                       content_hash="b" * 64, doc_type="lab", source="s1echo.pdf",
                       status="parsed", imported_at=datetime(2026, 9, 27)))
        await s.flush()
        s.add(Chunk(id=str(uuid.uuid4()), doc_id=doc_id, chunk_index=0, text=SENT_DOCTEXT))
        s.add(Observation(id=obs_id, profile_id=profile_id, doc_id=doc_id,
                          analyte_canonical="hba1c", analyte_raw=SENT_ANALYTE,
                          value=SENT_VALUE, unit="%", collected_at=datetime(2026, 9, 1)))
        s.add(ChatSession(id=sess_id, profile_id=profile_id, title="t"))
        await s.flush()
        s.add(ChatTurn(id=str(uuid.uuid4()), session_id=sess_id, profile_id=profile_id,
                       turn_index=0, role="user", content=SENT_CHAT))
        await s.commit()
    return obs_id


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: root))
    return root


@pytest.mark.asyncio
async def test_hc_sqlecho_001_vault_writes_do_not_echo_phi(data_root, monkeypatch):
    """Default dev config (debug on): vault row values and the key never reach the SQL log."""
    monkeypatch.setattr(settings, "debug", True)  # the configuration that leaked
    mgr = get_profile_db_manager()
    pid = str(uuid.uuid4())
    _make_vault(data_root, pid)

    conn = await mgr.open_profile_database(pid, PASSWORD)  # runs fileConfig
    cap = _Capture()
    sa_logger = logging.getLogger("sqlalchemy.engine")
    sa_logger.addHandler(cap)  # attached AFTER the migration's fileConfig
    try:
        hex_key = mgr._key_to_hex(conn._encryption_key)
        await _seed_vault(conn, pid)
        await conn.engine.dispose()  # next query opens a new connection -> key hook
        async with conn.session_maker() as s:
            from sqlalchemy import text
            await s.execute(text("SELECT count(*) FROM observations"))
        logging.getLogger("sqlalchemy.engine.Engine").warning(CANARY)
    finally:
        sa_logger.removeHandler(cap)
        await mgr.close_profile_database(pid)

    assert CANARY in cap.text, "capture handler was detached; result would be vacuous"
    _assert_absent(cap.text, [SENT_ANALYTE, repr(SENT_VALUE), SENT_DOCTEXT, SENT_CHAT, hex_key])
    assert conn.engine.sync_engine.echo is False  # built from sql_echo, not debug


def test_hc_sqlecho_002_http_create_and_verify_do_not_echo_phi(data_root, monkeypatch):
    """Master + vault engines through HTTP: display name, bcrypt hash, notes stay out.

    The module-level master engine is NOT used for I/O: SQLAlchemy resolves its
    relative sqlite path to an absolute one at import time, so it always points
    at <cwd-at-import>/data/<name>.db, a developer's real master DB. A tmp
    engine is built with the product engine's own logging flags instead.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from api.observations import router as observations_router
    from api.profiles import router as profiles_router
    from core.auth import Session, require_auth
    from core.migrations import run_master_migrations
    from tests.support.routes import route_client

    assert settings.debug is True, (
        "precondition: this test proves the default dev config (DEBUG unset/true) "
        "does not leak; with DEBUG=false it would pass without testing anything"
    )
    run_master_migrations()  # tmp master DB via the patched app_data_path; runs fileConfig
    master_file = data_root / settings.master_db_filename
    assert master_file.exists()
    product = core_db.engine.sync_engine
    tmp_engine = create_async_engine(
        f"sqlite+aiosqlite:///{master_file}",
        echo=product.echo,
        hide_parameters=product.hide_parameters,
    )
    master_session = async_sessionmaker(tmp_engine, class_=AsyncSession,
                                        expire_on_commit=False)()
    tap = _SqlLogTap(monkeypatch)

    parent = APIRouter()
    parent.include_router(profiles_router, prefix="/profiles")
    parent.include_router(observations_router, prefix="/observations")
    mgr = get_profile_db_manager()
    pid = None

    with route_client(parent, "/api/v1", master_db=master_session) as client:
        try:
            r = client.post("/api/v1/profiles/",
                            json={"display_name": SENT_NAME, "password": PASSWORD})
            assert r.status_code == 201, r.text
            pid = r.json()["profile_id"]

            async def _auth() -> Session:
                return Session(profile_id=pid, profile_name="T",
                               expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                               token_jti="jti-test")

            client.app.dependency_overrides[require_auth] = _auth
            obs_id = client.portal.call(_seed_vault, mgr.get_connection(pid), pid)
            r = client.post(f"/api/v1/observations/{obs_id}/verify",
                            json={"value": 7.77, "notes": SENT_NOTE})
            assert r.status_code == 200, r.text
            logging.getLogger("sqlalchemy.engine.Engine").warning(CANARY)
        finally:
            client.portal.call(master_session.close)
            if pid is not None:
                client.portal.call(mgr.close_profile_database, pid)
            client.portal.call(tmp_engine.dispose)

    assert CANARY in tap.text, "log tap was detached; result would be vacuous"
    _assert_absent(tap.text, [SENT_NAME, "$2b$", SENT_NOTE])


def test_hc_sqlecho_003_sql_echo_is_decoupled_from_debug(monkeypatch):
    """SQL echo is its own opt-in; debug=True no longer turns it on."""
    monkeypatch.delenv("SQL_ECHO", raising=False)
    s = Settings(app_env="development", debug=True)
    assert s.debug is True
    assert s.sql_echo is False
    monkeypatch.setenv("SQL_ECHO", "true")
    assert Settings(app_env="development").sql_echo is True
    assert core_db.engine.sync_engine.echo is False  # master engine built from sql_echo
