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


@pytest.fixture(autouse=True)
def _model_that_finds_nothing(monkeypatch):
    """Collect tests run with a loaded model that finds nothing: no bundle needed.

    HC-DON-025 replaces this with the real loader (no bundle, bad sha) and a control.
    """
    import modules.phi_second_pass as psp

    monkeypatch.setattr(psp, "_MODEL_OVERRIDE", _NoSpans())


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


_TURN_INDEX = __import__("itertools").count()


async def _feedback(db, prompt, response="Your result is in range.", correction=None, session_id="s1",
                    snapshot=None):
    """``prompt`` is the user turn text; ``snapshot`` (default: same) is the client-supplied prompt_snapshot."""
    turn_id = f"t-{len(db.statements)}-{id(prompt)}"
    n = 2 * next(_TURN_INDEX)
    db.add(ChatTurn(id=f"u{turn_id}", session_id=session_id, profile_id=PID,
                    turn_index=n, role="user", content=prompt))
    db.add(ChatTurn(id=turn_id, session_id=session_id, profile_id=PID,
                    turn_index=n + 1, role="assistant", content=response))
    row = ResponseFeedback(
        profile_id=PID, session_id=session_id, turn_id=turn_id,
        rating=1, prompt_snapshot=snapshot if snapshot is not None else prompt,
        response_text=response, correction_text=correction,
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

    assert counts.collected == 0 and counts.dropped_records == 0
    assert not [s for s in vault.statements if "response_feedback" in s or "donated_records" in s]
    assert await _donated(vault) == []


@pytest.mark.asyncio
async def test_hc_don_015_collect_stores_only_redacted_text(vault):
    from modules.data_donation import collect

    await _consent(vault)
    src = "Patient Name: Jane Doe, phone 555-123-4567. What does my LDL mean?"
    await _feedback(vault, src, response="Your LDL is 162 mg/dL.", correction="Call 555-123-4567.")

    counts = await collect(vault, PID, PURPOSE)

    assert counts.collected == 1 and counts.dropped_records == 0 and counts.strict_redaction_count > 0
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


@pytest.mark.asyncio
async def test_collect_donates_user_turn_not_prompt_snapshot(vault):
    from modules.data_donation import collect

    await _consent(vault)
    await _feedback(vault, "What does a high LDL mean?",
                    snapshot="CONTEXT: LDL 162 mg/dL from lab report. What does a high LDL mean?")
    assert (await collect(vault, PID, PURPOSE)).collected == 1
    assert [r.prompt_redacted for r in await _donated(vault)] == ["What does a high LDL mean?"]


@pytest.mark.asyncio
async def test_collect_donates_server_answer_not_client_response_text(vault):
    from modules.data_donation import collect

    await _consent(vault)
    row_id = await _feedback(vault, "What does a high LDL mean?", response="Server answer about LDL.")
    row = (await vault.execute(select(ResponseFeedback).where(ResponseFeedback.id == row_id))).scalars().one()
    row.response_text = "CLIENT-SUPPLIED retrieved record text"
    await vault.commit()

    assert (await collect(vault, PID, PURPOSE)).collected == 1
    (rec,) = await _donated(vault)
    assert rec.response_redacted == "Server answer about LDL."


@pytest.mark.asyncio
async def test_collect_skips_ambiguous_duplicate_turn_index(vault):
    from modules.data_donation import collect

    await _consent(vault)
    row_id = await _feedback(vault, "What does a high LDL mean?")
    row = (await vault.execute(select(ResponseFeedback).where(ResponseFeedback.id == row_id))).scalars().one()
    a = (await vault.execute(select(ChatTurn).where(ChatTurn.id == row.turn_id))).scalars().one()
    vault.add(ChatTurn(id="dup-user", session_id=a.session_id, profile_id=PID,
                       turn_index=a.turn_index - 1, role="user", content="A different question"))
    await vault.commit()

    counts = await collect(vault, PID, PURPOSE)

    assert (counts.collected, counts.skipped_incomplete) == (0, 1)
    assert await _donated(vault) == []


@pytest.mark.asyncio
async def test_collect_rolls_back_when_consent_revoked_before_commit(vault, monkeypatch):
    import modules.data_donation as dd

    await _consent(vault)
    await _feedback(vault, "What does a high LDL mean?")
    real = dd.has_current_consent
    calls = []

    async def _revoked_after_first(db, pid, purpose):
        calls.append(1)
        return await real(db, pid, purpose) if len(calls) == 1 else False

    monkeypatch.setattr(dd, "has_current_consent", _revoked_after_first)

    counts = await dd.collect(vault, PID, PURPOSE)

    assert counts.collected == 0 and len(calls) == 2
    assert await _donated(vault) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("bundle", ["missing", "sha_mismatch"])
async def test_hc_don_025_bad_model_bundle_stores_nothing_with_fixed_reason(vault, monkeypatch, tmp_path, bundle):
    import modules.phi_second_pass as psp
    from core.config import settings
    from modules.data_donation import DONATION_UNAVAILABLE_REASON, collect

    if bundle == "sha_mismatch":
        model_dir = tmp_path / "deid"
        model_dir.mkdir()
        for name in psp.PHI_NER_FETCH_FILES:
            (model_dir / name).write_bytes(b"not the pinned weights")
    else:
        model_dir = tmp_path / "absent"
    monkeypatch.setattr(psp, "_MODEL_OVERRIDE", None)
    monkeypatch.setattr(psp, "_MODEL_CACHE", None)
    monkeypatch.setattr(settings, "phi_ner_model_path", str(model_dir))

    await _consent(vault)
    await _feedback(vault, "What does a high LDL mean?")
    vault.statements.clear()

    counts = await collect(vault, PID, PURPOSE)

    assert counts.collected == 0 and counts.reason == DONATION_UNAVAILABLE_REASON
    assert not [s for s in vault.statements if "donated_records" in s]
    assert await _donated(vault) == []


@pytest.mark.asyncio
async def test_hc_don_025_positive_control_same_profile_with_model_stores_rows(vault, monkeypatch):
    import modules.phi_second_pass as psp
    from modules.data_donation import collect

    monkeypatch.setattr(psp, "_MODEL_OVERRIDE", _NoSpans())
    await _consent(vault)
    await _feedback(vault, "What does a high LDL mean?")

    counts = await collect(vault, PID, PURPOSE)

    assert counts.collected >= 1 and counts.reason is None


class _NoSpans:
    """A loaded model that finds nothing: keeps the rule-level tests bundle-independent."""

    def labelled_spans(self, text: str) -> list[tuple[str, str]]:
        return []


# ---- Delta 2026-10-20, second: RunLog isolation (positive control, canary, mutant) ----
RUNLOG_CANARY = "RUNLOG-CANARY-DON-5b1e7d02"


async def _rated_agent_turn(vault, monkeypatch):
    """Agent chat over HTTP with a canary in a tool output the draft never renders; then a +1 rating.

    Returns the RunLogs recorded during the chat (used by the scratch mutant only).
    """
    from unittest.mock import AsyncMock, patch

    import api.assistant as A
    import api.feedback as F
    import modules.agent.cache as agent_cache
    import modules.agent.graph as agent_graph
    from api.assistant import router as assistant_router
    from api.feedback import router as feedback_router
    from core.auth import get_profile_db_session
    from modules.agent.state import RunLog
    from modules.agent.tools.query_observations import (
        QueryObservationsOutput,
        QueryObservationsTool,
    )
    from tests.support.routes import route_client

    class _CanaryOutput(QueryObservationsOutput):
        unrendered_note: str = RUNLOG_CANARY

    real_run = QueryObservationsTool.run

    async def _run_with_canary(self, args, ctx):
        out = await real_run(self, args, ctx)
        return _CanaryOutput(rows=out.rows)  # rows stay empty: the draft prints no calendar date

    run_logs: list = []

    def _recording_run_log(**kwargs):
        run_log = RunLog(**kwargs)
        run_logs.append(run_log)
        return run_log

    # No observation rows: a row would print its collection date ("Jan 15, 2026"), and
    # the date rule correctly drops any record that carries a calendar date (Safe Harbor).
    agent_cache.clear_cache()

    async def _db():
        return vault

    audit_spy = AsyncMock()
    with patch.object(A, "is_agent_enabled", return_value=True), \
         patch.object(QueryObservationsTool, "run", _run_with_canary), \
         patch.object(agent_graph, "RunLog", _recording_run_log), \
         patch.object(A, "create_audit_log", audit_spy), \
         patch.object(F, "_emit_audit", AsyncMock()):
        with route_client(assistant_router, "/assistant", profile_id=PID) as client:
            client.app.dependency_overrides[get_profile_db_session] = _db
            resp = client.post("/assistant/chat", json={"question": "what is my glucose?"})
        assert resp.status_code == 200, resp.text
        turn = (await vault.execute(
            select(ChatTurn).where(ChatTurn.role == "assistant", ChatTurn.profile_id == PID)
        )).scalars().one()
        with route_client(feedback_router, "/feedback", profile_id=PID) as client:
            client.app.dependency_overrides[get_profile_db_session] = _db
            resp = client.post(
                f"/feedback/turns/{turn.id}", json={"session_id": turn.session_id, "rating": 1},
            )
        assert resp.status_code == 200, resp.text
    agent_cache.clear_cache()
    return run_logs


def _donated_text(rows) -> str:
    return " ".join(str(getattr(r, c.name)) for r in rows for c in DonatedRecord.__table__.columns)


@pytest.mark.asyncio
async def test_runlog_payload_never_reaches_donated_rows(vault, monkeypatch):
    from modules.data_donation import collect

    await _consent(vault)
    run_logs = await _rated_agent_turn(vault, monkeypatch)

    counts = await collect(vault, PID, PURPOSE)

    # Positive control: the canary really reached the run's act steps, so the check below means something.
    acts = [s for log in run_logs for s in log.steps if s.node == "act"]
    assert any(RUNLOG_CANARY in str(s.payload) for s in acts), "canary missing from the RunLog"
    # The rated agent turn is donated (an empty collection fails here).
    assert counts.collected >= 1, counts
    rows = await _donated(vault)
    assert any("glucose" in (r.prompt_redacted or "").lower() for r in rows), [r.prompt_redacted for r in rows]
    # The canary sits only in a tool output the draft never renders: it must not be donated.
    assert RUNLOG_CANARY not in _donated_text(rows)


@pytest.mark.asyncio
async def test_hc_don_014d_v2_grant_collects_nothing_and_v3_regrant_collects(vault):
    """Delta 2026-10-20, second + DON-COPY-V3: a rated turn under the superseded v2 wording donates 0 rows."""
    from datetime import datetime

    from modules.data_donation import collect

    await _consent(vault, version="2026-10-20-v2")
    await _feedback(vault, "What does a high LDL mean?")

    stale = await collect(vault, PID, PURPOSE)
    assert stale.collected == 0 and await _donated(vault) == []

    row = await get_active_consent_row(vault)
    row.revoked_at = datetime(2026, 10, 28)
    await vault.commit()
    await _consent(vault)  # re-agreed on the current (v3) wording

    fresh = await collect(vault, PID, PURPOSE)
    assert fresh.collected == 1


async def get_active_consent_row(db):
    return (await db.execute(
        select(DonationConsent).where(DonationConsent.profile_id == PID, DonationConsent.revoked_at.is_(None))
    )).scalars().one()
