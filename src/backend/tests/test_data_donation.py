"""RSI1-DONATE PR-1 schema: donation_consents and donated_records (HC-DON-001..003)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.script import ScriptDirectory

TABLES = ("donation_consents", "donated_records")
RAW_COLUMN = re.compile(r"raw|original|unredacted|plain", re.I)


def _tables(vault_path: Path, key: bytes) -> set[str]:
    from sqlalchemy import inspect

    engine = _engine(vault_path, key)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _active_index_sql(vault_path: Path, key: bytes) -> str | None:
    from sqlalchemy import text

    engine = _engine(vault_path, key)
    try:
        with engine.connect() as conn:
            return conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_donation_consents_active'")
            ).scalar()
    finally:
        engine.dispose()


def _table_info(vault_path: Path, key: bytes, table: str) -> list[tuple]:
    from sqlalchemy import text

    engine = _engine(vault_path, key)
    try:
        with engine.connect() as conn:
            return [tuple(r) for r in conn.execute(text(f"PRAGMA table_info({table})"))]
    finally:
        engine.dispose()


def _engine(vault_path: Path, key: bytes):
    from sqlalchemy import create_engine, event

    from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available

    url = f"sqlite:///{vault_path}"
    if is_sqlcipher_available():
        mod = get_sqlcipher_module()
        engine = create_engine(url, creator=lambda: mod.connect(str(vault_path)))
    else:
        engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def _key(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA cipher_version")
        row = cur.fetchone()
        if row and row[0]:
            cur.execute(f"PRAGMA key = \"x'{key.hex()}'\"")
        cur.close()

    return engine


def test_hc_don_001_migration_round_trip_single_head(tmp_path, monkeypatch):
    from alembic import command

    from core import migrations
    from core.config import settings

    monkeypatch.setattr(settings, "database_encryption_required", False)
    vault, key = tmp_path / "vault.db", b"0" * 32
    migrations.run_profile_migration(vault, key)
    cfg = migrations._get_alembic_config("profile")
    cfg.attributes["vault_path"] = vault
    cfg.attributes["encryption_key"] = key

    script = ScriptDirectory.from_config(cfg)
    assert len(script.get_heads()) == 1
    rev = script.get_revision("015_data_donation")
    assert rev.down_revision == "014_streaks_hidden"

    assert migrations.get_profile_current_revision(vault, key) == script.get_current_head()
    assert set(TABLES) <= _tables(vault, key)

    # The migrated vault (not just model metadata) must keep the partial unique
    # index; a full unique index would 500 on grant -> revoke -> grant.
    sql = " ".join((_active_index_sql(vault, key) or "").split()).upper()
    assert "CREATE UNIQUE INDEX" in sql
    assert "(PROFILE_ID, PURPOSE)" in sql
    assert "WHERE REVOKED_AT IS NULL" in sql

    # PRAGMA table_info rows: (cid, name, type, notnull, dflt_value, pk).
    from models.data_donation import DonatedRecord

    info = {r[1]: r for r in _table_info(vault, key, "donated_records")}
    assert "correction_redacted" in info
    assert info["correction_redacted"][2].upper() == "TEXT"
    assert info["correction_redacted"][3] == 0  # nullable
    # The migrated column set must equal the model's: kills model/migration drift.
    assert set(info) == set(DonatedRecord.__table__.columns.keys())

    command.downgrade(cfg, "014_streaks_hidden")
    assert not set(TABLES) & _tables(vault, key)

    command.upgrade(cfg, "head")
    assert set(TABLES) <= _tables(vault, key)


def test_hc_don_002_no_raw_text_column():
    from models.data_donation import DonatedRecord, DonationConsent

    for model in (DonationConsent, DonatedRecord):
        bad = [c.name for c in model.__table__.columns if RAW_COLUMN.search(c.name)]
        assert not bad, f"{model.__tablename__} has raw-text-looking columns: {bad}"
    assert {"prompt_redacted", "response_redacted"} <= set(DonatedRecord.__table__.columns.keys())
    assert not DonatedRecord.__table__.foreign_keys
    assert not DonationConsent.__table__.foreign_keys
    assert any(i.unique and i.name == "uq_donation_consents_active" for i in DonationConsent.__table__.indexes)


def test_hc_don_003_profile_metadata_only():
    import models  # noqa: F401  (registers every model)
    from core.database import Base
    from core.profile_database import ProfileDatabaseBase

    for t in TABLES:
        assert t in ProfileDatabaseBase.metadata.tables
        assert t not in Base.metadata.tables


# ---------------------------------------------------------------------------
# PR-2 Task 4: collect (HC-DON-014..016)
# ---------------------------------------------------------------------------

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import event, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from core.profile_database import ProfileDatabaseBase  # noqa: E402
from models.chat_session import ChatTurn  # noqa: E402
from models.data_donation import DonatedRecord, DonationConsent  # noqa: E402
from models.response_feedback import ResponseFeedback  # noqa: E402

PID = "profile-a"
PURPOSE = "fine_tune"
GAP_TEXT = "The portal logged a visit from IP 192.168.1.1 yesterday."  # strict leaves IPv4 intact


@pytest_asyncio.fixture
async def vault():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    statements: list[str] = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _spy(conn, cursor, statement, *a):
        statements.append(statement)

    session = AsyncSession(engine, expire_on_commit=False)
    session.statements = statements
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _consent(db, version=None, revoked=False):
    from datetime import datetime

    from modules.data_donation import CURRENT_CONSENT_TEXT_VERSION

    db.add(DonationConsent(
        profile_id=PID, purpose=PURPOSE,
        consent_text_version=version or CURRENT_CONSENT_TEXT_VERSION,
        revoked_at=datetime(2026, 1, 1) if revoked else None,
    ))
    await db.commit()


async def _feedback(db, prompt, response="Your result is in range.", correction=None, session_id="s1"):
    turn_id = f"t-{len(db.statements)}-{id(prompt)}"
    db.add(ChatTurn(id=turn_id, session_id=session_id, profile_id=PID,
                    turn_index=0, role="assistant", content="a"))
    row = ResponseFeedback(
        profile_id=PID, session_id=session_id, turn_id=turn_id,
        rating=1, prompt_snapshot=prompt, response_text=response, correction_text=correction,
    )
    db.add(row)
    await db.commit()
    return row.id


async def _donated(db):
    return (await db.execute(select(DonatedRecord))).scalars().all()


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["none", "revoked", "stale"])
async def test_hc_don_014_collect_fails_closed_without_current_consent(vault, state):
    from modules.data_donation import collect

    await _feedback(vault, "What is my LDL?")
    if state == "revoked":
        await _consent(vault, revoked=True)
    elif state == "stale":
        await _consent(vault, version="2026-10-01-v1")
    vault.statements.clear()

    counts = await collect(vault, PID, PURPOSE)

    assert counts.collected == 0 and counts.dropped_total == 0
    assert not [s for s in vault.statements if "response_feedback" in s or "donated_records" in s]
    assert await _donated(vault) == []


@pytest.mark.asyncio
async def test_hc_don_015_collect_stores_only_redacted_text(vault):
    from modules.data_donation import collect

    await _consent(vault)
    src = "Patient Name: Jane Doe, phone 555-123-4567. What does my LDL mean?"
    await _feedback(vault, src, response="Your LDL is 162 mg/dL.", correction="Call 555-123-4567.")

    counts = await collect(vault, PID, PURPOSE)

    assert counts.collected == 1 and counts.dropped_total == 0 and counts.strict_redaction_count > 0
    (rec,) = await _donated(vault)
    assert (rec.origin, rec.source_kind, rec.purpose) == ("real", "response_feedback", PURPOSE)
    stored = " ".join(str(getattr(rec, c.name)) for c in DonatedRecord.__table__.columns)
    for secret in ("Jane", "Doe", "555-123-4567"):
        assert secret not in stored
    assert "LDL" in rec.prompt_redacted  # lab content survives


@pytest.mark.asyncio
async def test_hc_don_015b_collect_is_idempotent(vault):
    from modules.data_donation import collect

    await _consent(vault)
    await _feedback(vault, "What does a high LDL mean?")
    first = await collect(vault, PID, PURPOSE)
    second = await collect(vault, PID, PURPOSE)
    assert (first.collected, second.collected, second.skipped_existing) == (1, 0, 1)
    assert len(await _donated(vault)) == 1


@pytest.mark.asyncio
async def test_hc_don_016_strict_gap_is_dropped_and_counted_by_category(vault):
    from modules.data_donation import collect
    from modules.redaction import RedactionEngine

    # Task 0: the known strict gap used here is a bare IPv4 address.
    assert "192.168.1.1" in RedactionEngine(policy_level="strict").redact(GAP_TEXT).text

    await _consent(vault)
    await _feedback(vault, GAP_TEXT)
    await _feedback(vault, "What does a high LDL mean?")

    counts = await collect(vault, PID, PURPOSE)

    assert counts.collected == 1
    assert counts.dropped == {"ip_address": 1}
    stored = " ".join(r.prompt_redacted for r in await _donated(vault))
    assert "192.168.1.1" not in stored


@pytest.mark.asyncio
async def test_collect_skips_orphaned_feedback_and_counts_incomplete(vault):
    from modules.data_donation import collect

    await _consent(vault)
    await _feedback(vault, "What is my LDL?")
    await _feedback(vault, "")  # incomplete: no prompt
    # feedback whose assistant turn was deleted with its session
    vault.add(ResponseFeedback(profile_id=PID, session_id="gone", turn_id="no-such-turn",
                               rating=1, prompt_snapshot="q", response_text="r"))
    await vault.commit()
    counts = await collect(vault, PID, PURPOSE)
    assert (counts.collected, counts.skipped_incomplete) == (1, 1)
    assert len((await _donated(vault))) == 1
