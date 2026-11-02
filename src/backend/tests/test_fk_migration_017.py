"""C-P6 / SQL-FK-001: profile migration 017_fk_cascade_alignment.

HC-FKM: the three rebuilt tables carry the audited FK actions and keep their
rows, columns and indexes.
HC-FKC: the migration first removes orphan rows (children only; P16/P17 are
SET NULL repairs) so the pragma can be switched on over an old vault.

Every test builds a *file* vault at 016, seeds it with ``PRAGMA foreign_keys``
OFF (the state every real vault was written in), then upgrades to head through
Alembic. In-memory ``create_all`` engines cannot show any of this: they never
ran 004/010/011.
"""

from __future__ import annotations

import ast
import contextlib
import logging
import logging.config
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402

from core import migrations  # noqa: E402
from core.config import settings  # noqa: E402
from core.fk_audit import PROFILE_CHECKS  # noqa: E402
from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available  # noqa: E402
from tests.support.migrations import PROFILE_HEAD  # noqa: E402

KEY = b"0" * 32
REV_016 = "016_strict_safety_mode"
REBUILT = ("document_category", "document_entity", "care_plan_task")
CLEANUP_LOGGER = "alembic.fk_cleanup"
SENTINEL = "SENTINEL-PHI-7f3a"


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------


def _alembic_cfg(vault: Path, key: bytes = KEY):
    cfg = migrations._get_alembic_config("profile")
    cfg.attributes["vault_path"] = vault
    cfg.attributes["encryption_key"] = key
    return cfg


def _connect(vault: Path, key: bytes = KEY):
    """Raw DBAPI connection with the vault key set and the FK pragma OFF."""
    if is_sqlcipher_available():
        conn = get_sqlcipher_module().connect(str(vault))
        conn.execute(f"PRAGMA key = \"x'{migrations._key_to_hex(key)}'\"")
    else:
        import sqlite3

        conn = sqlite3.connect(str(vault))
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


@pytest.fixture
def vault016(tmp_path, monkeypatch):
    """(vault path, alembic config) for a file vault at 016, nothing seeded."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    cfg = _alembic_cfg(path)
    command.upgrade(cfg, REV_016)
    return path, cfg


@pytest.fixture
def fk_log(monkeypatch, caplog):
    """Records of the cleanup logger, surviving env.py's fileConfig().

    env.py calls the real ``fileConfig`` on every migration run, which strips
    handlers from the root logger and from every ``alembic.*`` child. Wrap it
    so the production logging config still runs (and the logger inherits INFO
    from alembic.ini, as in production) and only re-attach caplog afterwards.
    """
    real = logging.config.fileConfig

    def _wrapped(*args, **kwargs):
        real(*args, **kwargs)
        logging.getLogger(CLEANUP_LOGGER).addHandler(caplog.handler)

    monkeypatch.setattr(logging.config, "fileConfig", _wrapped)
    yield lambda: [r for r in caplog.records if r.name == CLEANUP_LOGGER]
    logging.getLogger(CLEANUP_LOGGER).removeHandler(caplog.handler)


_DUMMY = (
    ("BOOL", 0),
    ("INT", 1),
    ("FLOAT", 0.5),
    ("DATETIME", "2026-01-01 00:00:00.000000"),
    ("DATE", "2026-01-01"),
    ("TIME", "08:00:00"),
    ("BLOB", b"\x00"),
)


def _insert(conn, table: str, **values) -> str:
    """Insert one row, filling every other NOT NULL column without a default."""
    row = dict(values)
    for _cid, name, ctype, notnull, default, _pk in conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall():
        if name in row or not notnull or default is not None:
            continue
        upper = (ctype or "").upper()
        row[name] = next((v for key, v in _DUMMY if key in upper), f"v-{name}")
    cols = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(row.values()))
    return row["id"]


def _snapshot(conn) -> dict[str, list[tuple]]:
    """Every row of every application table (cells compared as stored)."""
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%' ORDER BY name"
        )
    ]
    return {
        t: sorted((tuple(r) for r in conn.execute(f"SELECT * FROM {t}")), key=repr)
        for t in tables
    }


def _fk_actions(conn, table: str) -> dict[str, str]:
    # foreign_key_list: id, seq, table, from, to, on_update, on_delete, match
    return {r[3]: r[6] for r in conn.execute(f"PRAGMA foreign_key_list({table})")}


def _structure(conn, table: str):
    """(table_info, {index name: columns}) with autoindex names ignored."""
    info = [tuple(r) for r in conn.execute(f"PRAGMA table_info({table})")]
    idx = {}
    for r in conn.execute(f"PRAGMA index_list({table})").fetchall():
        name = r[1]
        if name.startswith("sqlite_autoindex"):
            continue
        idx[name] = (
            bool(r[2]),
            tuple(c[2] for c in conn.execute(f"PRAGMA index_info({name})")),
        )
    return info, idx


# --------------------------------------------------------------------------
# planted orphans: one valid child and one orphan child per enforced check
# --------------------------------------------------------------------------

# check id -> (child table, extra columns of a valid child, FK column to break)
_PLAN = {
    "P1": ("observations", {"doc_id": "D1"}, "doc_id"),
    "P2": ("chunks", {"doc_id": "D1"}, "doc_id"),
    "P3": ("embeddings", {"chunk_id": "C1"}, "chunk_id"),
    "P4": ("lab_interpretations", {"observation_id": "OB1"}, "observation_id"),
    "P5": ("chat_turns", {"session_id": "CS1"}, "session_id"),
    "P6": ("medication_schedules", {"medication_id": "M1"}, "medication_id"),
    "P7": ("doses_taken", {"medication_id": "M1"}, "medication_id"),
    "P8": ("doses_taken", {"medication_id": "M1", "schedule_id": "S1"}, "schedule_id"),
    "P9": ("adherence_patterns", {"medication_id": "M1"}, "medication_id"),
    "P10": ("adherence_patterns", {"medication_id": "M1", "schedule_id": "S1"}, "schedule_id"),
    "P11": ("reminder_logs", {"medication_id": "M1"}, "medication_id"),
    "P12": ("reminder_logs", {"medication_id": "M1", "schedule_id": "S1"}, "schedule_id"),
    "P13": ("pinboard_item", {"pinboard_id": "PB1", "item_type": "note", "item_id": "x"}, "pinboard_id"),
    "P14": ("document_category", {"doc_id": "D1"}, "doc_id"),
    "P15": ("document_entity", {"doc_id": "D1"}, "doc_id"),
    "P18": ("earned_badge", {"badge_id": "B1"}, "badge_id"),
}
DELETE_CHECKS = list(_PLAN)
REPAIR_CHECKS = ["P16", "P17"]
ALL_CHECKS = [f"P{i}" for i in range(1, 19)]


def _seed_base(conn) -> None:
    """Valid parents. No orphan is created here."""
    _insert(conn, "documents", id="D1")
    _insert(conn, "chunks", id="C1", doc_id="D1")
    _insert(conn, "observations", id="OB1", doc_id="D1")
    _insert(conn, "medications", id="M1")
    _insert(conn, "medication_schedules", id="S1", medication_id="M1")
    _insert(conn, "chat_sessions", id="CS1")
    _insert(conn, "pinboard", id="PB1")
    _insert(conn, "badge_definition", id="B1")
    _insert(conn, "document_entity", id="E1", doc_id="D1")


def _plant(conn, check_id: str) -> tuple[str, str]:
    """Add one valid child and one orphan for ``check_id``; (table, orphan id)."""
    if check_id in REPAIR_CHECKS:
        valid = dict(
            source_document_id="D1", source_entity_id="E1", source_quote="valid quote"
        )
        _insert(conn, "care_plan_task", id=f"V-{check_id}", title="valid", **valid)
        if check_id == "P16":
            orphan = dict(
                source_document_id="MISSING", source_entity_id="E1", source_quote="Q16"
            )
        else:
            orphan = dict(
                source_document_id="D1", source_entity_id="MISSING", source_quote="Q17"
            )
        _insert(conn, "care_plan_task", id=f"O-{check_id}", title="orphan", **orphan)
        return "care_plan_task", f"O-{check_id}"
    table, extra, break_col = _PLAN[check_id]
    _insert(conn, table, id=f"V-{check_id}", **extra)
    _insert(conn, table, id=f"O-{check_id}", **{**extra, break_col: "MISSING"})
    return table, f"O-{check_id}"


def _seed(path: Path, check_ids, key: bytes = KEY) -> dict[str, tuple[str, str]]:
    conn = _connect(path, key)
    try:
        _seed_base(conn)
        planted = {cid: _plant(conn, cid) for cid in check_ids}
        conn.commit()
        return planted
    finally:
        conn.close()


def _read(path: Path):
    conn = _connect(path)
    try:
        return _snapshot(conn), conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()


def _expected_after(before: dict, planted: dict) -> dict:
    """``before`` with each deleted orphan removed and each repair applied."""
    after = {t: list(rows) for t, rows in before.items()}
    for cid, (table, orphan_id) in planted.items():
        if cid in REPAIR_CHECKS:
            continue
        after[table] = [r for r in after[table] if r[0] != orphan_id]
    return after


def _task_row(path: Path, task_id: str) -> dict:
    conn = _connect(path)
    try:
        cur = conn.execute(
            "SELECT source_document_id, source_entity_id, source_quote, title "
            "FROM care_plan_task WHERE id = ?",
            (task_id,),
        )
        row = cur.fetchone()
        return None if row is None else dict(zip(
            ("source_document_id", "source_entity_id", "source_quote", "title"), row
        ))
    finally:
        conn.close()


def _upgrade_head(cfg) -> dict:
    command.upgrade(cfg, "head")
    return cfg.attributes.get("fk_cleanup_counts")


# --------------------------------------------------------------------------
# HC-FKM: constraint actions, rows and structure survive the rebuild
# --------------------------------------------------------------------------


def test_hc_fkm_001_constraint_actions_aligned(vault016):
    path, cfg = vault016
    conn = _connect(path)
    try:
        assert _fk_actions(conn, "document_category")["doc_id"] == "NO ACTION"
        assert _fk_actions(conn, "document_entity")["doc_id"] == "NO ACTION"
    finally:
        conn.close()

    command.upgrade(cfg, "head")
    assert migrations.get_profile_current_revision(path, KEY) == PROFILE_HEAD

    conn = _connect(path)
    try:
        assert _fk_actions(conn, "document_category")["doc_id"] == "CASCADE"
        assert _fk_actions(conn, "document_entity")["doc_id"] == "CASCADE"
        assert _fk_actions(conn, "care_plan_task") == {
            "source_document_id": "SET NULL",
            "source_entity_id": "SET NULL",
        }
    finally:
        conn.close()

    # downgrade rebuilds back to NO ACTION
    command.downgrade(cfg, REV_016)
    conn = _connect(path)
    try:
        assert _fk_actions(conn, "document_category")["doc_id"] == "NO ACTION"
        assert _fk_actions(conn, "document_entity")["doc_id"] == "NO ACTION"
        assert set(_fk_actions(conn, "care_plan_task").values()) == {"NO ACTION"}
    finally:
        conn.close()


def test_hc_fkm_002_rows_survive_rebuild(vault016):
    path, cfg = vault016
    conn = _connect(path)
    try:
        _seed_base(conn)
        _insert(conn, "document_category", id="K1", doc_id="D1", category="visit_notes")
        _insert(
            conn, "document_entity", id="E2", doc_id="D1",
            char_start=3, char_end=9, quote="a quote", verified_by_user=1,
            extraction_version="v1", source_page=2, source_bbox_json="[1,2]",
        )
        _insert(
            conn, "care_plan_task", id="T1", title="Repeat CBC",
            source_document_id="D1", source_entity_id="E2",
            source_quote="repeat CBC", user_note="n", due_date="2026-03-01",
            due_date_confidence=0.7, status="done",
        )
        conn.commit()
        before = _snapshot(conn)
        structure = {t: _structure(conn, t) for t in REBUILT}
    finally:
        conn.close()
    assert structure["care_plan_task"][1], "fixture expects the 011 indexes"

    command.upgrade(cfg, "head")

    conn = _connect(path)
    try:
        assert _snapshot(conn) == before
        assert {t: _structure(conn, t) for t in REBUILT} == structure
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()
    assert cfg.attributes["fk_cleanup_counts"] == {}


# --------------------------------------------------------------------------
# HC-FKC: orphan cleanup
# --------------------------------------------------------------------------


@pytest.mark.parametrize("check_id", ALL_CHECKS)
def test_hc_fkc_001_planted_orphan_cleaned_per_check(vault016, check_id):
    path, cfg = vault016
    planted = _seed(path, [check_id])
    before, _ = _read(path)
    table, orphan_id = planted[check_id]
    assert any(r[0] == orphan_id for r in before[table]), "fixture did not plant"

    counts = _upgrade_head(cfg)

    after, fk_violations = _read(path)
    assert counts == {check_id: 1}
    assert fk_violations == []
    if check_id in REPAIR_CHECKS:
        # the care task is kept, same id and same row count; only links change
        assert len(after["care_plan_task"]) == len(before["care_plan_task"]) == 2
        orphan = _task_row(path, orphan_id)
        if check_id == "P16":
            assert orphan["source_document_id"] is None
            assert orphan["source_entity_id"] is None
            assert orphan["source_quote"] is None
        else:
            assert orphan["source_entity_id"] is None
            assert orphan["source_document_id"] == "D1"
            assert orphan["source_quote"] == "Q17"
        # the valid task and every other table are untouched
        assert _task_row(path, f"V-{check_id}") == {
            "source_document_id": "D1", "source_entity_id": "E1",
            "source_quote": "valid quote", "title": "valid",
        }
        others = {t: rows for t, rows in after.items() if t != "care_plan_task"}
        assert others == {t: rows for t, rows in before.items() if t != "care_plan_task"}
    else:
        # orphan gone; parent, valid child and every other row unchanged
        assert after == _expected_after(before, planted)
        assert any(r[0] == f"V-{check_id}" for r in after[table])


def test_hc_fkc_002_chained_orphans_removed_in_one_upgrade(vault016):
    path, cfg = vault016
    conn = _connect(path)
    try:
        _seed_base(conn)
        # orphan chunk carrying an embedding (P2 then P3)
        _insert(conn, "chunks", id="OC", doc_id="MISSING")
        _insert(conn, "embeddings", id="OE", chunk_id="OC")
        # orphan schedule carrying a dose (P6 then P8)
        _insert(conn, "medication_schedules", id="OS", medication_id="MISSING")
        _insert(conn, "doses_taken", id="OD", medication_id="M1", schedule_id="OS")
        conn.commit()
    finally:
        conn.close()

    counts = _upgrade_head(cfg)

    assert counts == {"P2": 1, "P3": 1, "P6": 1, "P8": 1}
    after, fk_violations = _read(path)
    assert fk_violations == []
    for table, rid in (
        ("chunks", "OC"), ("embeddings", "OE"),
        ("medication_schedules", "OS"), ("doses_taken", "OD"),
    ):
        assert all(r[0] != rid for r in after[table]), f"{table}.{rid} survived"
    # the valid parents are untouched
    assert [r[0] for r in after["chunks"]] == ["C1"]
    assert [r[0] for r in after["medication_schedules"]] == ["S1"]


def test_hc_fkc_003_logged_counts_no_content(vault016, fk_log):
    path, cfg = vault016
    conn = _connect(path)
    try:
        _seed_base(conn)
        planted = {cid: _plant(conn, cid) for cid in ALL_CHECKS}
        # sentinel PHI in text columns of rows the cleanup deletes and keeps
        conn.execute("UPDATE chunks SET text = ?", (SENTINEL,))
        conn.execute("UPDATE observations SET analyte_canonical = ?", (SENTINEL,))
        conn.commit()
        seeded_ids = {r[0] for rows in _snapshot(conn).values() for r in rows}
    finally:
        conn.close()
    assert len(planted) == 18

    _upgrade_head(cfg)

    messages = [(r.levelno, r.getMessage()) for r in fk_log()]
    per_check = {}
    for level, msg in messages:
        if " check=" in msg:
            cid = msg.split("check=")[1].split()[0]
            assert cid not in per_check, f"two records for {cid}"
            per_check[cid] = (level, msg)
    assert sorted(per_check, key=lambda c: int(c[1:])) == ALL_CHECKS
    for cid, (level, msg) in per_check.items():
        word = "repaired" if cid in REPAIR_CHECKS else "removed"
        other = "removed" if cid in REPAIR_CHECKS else "repaired"
        assert level == logging.WARNING
        assert msg == f"fk_orphan_cleanup check={cid} {word}=1", msg
        assert other not in msg

    summaries = [(lv, m) for lv, m in messages if " total=" in m]
    assert summaries == [(logging.WARNING, "fk_orphan_cleanup total=18 checks=18")]

    blob = "\n".join(m for _lv, m in messages)
    assert SENTINEL not in blob
    assert str(path) not in blob and path.name not in blob
    assert not [i for i in seeded_ids if i in blob], "a row id reached the log"


def test_hc_fkc_004_out_of_scope_rows_survive(vault016):
    """L1 (no constraint) and L3 (polymorphic item_id) are report-only."""
    path, cfg = vault016
    conn = _connect(path)
    try:
        _seed_base(conn)
        _insert(conn, "response_feedback", id="L1", session_id="NO-SESSION", turn_id="NO-TURN")
        _insert(
            conn, "pinboard_item", id="L3", pinboard_id="PB1",
            item_type="document", item_id="NO-DOCUMENT",
        )
        conn.commit()
        before = _snapshot(conn)
    finally:
        conn.close()

    counts = _upgrade_head(cfg)

    after, fk_violations = _read(path)
    assert counts == {}
    assert fk_violations == []
    assert after == before
    assert [r[0] for r in after["response_feedback"]] == ["L1"]
    assert [r[0] for r in after["pinboard_item"]] == ["L3"]


def test_hc_fkc_005_clean_vault_is_a_noop(vault016, fk_log):
    path, cfg = vault016
    conn = _connect(path)
    try:
        _seed_base(conn)
        for cid in ALL_CHECKS:  # valid children only: nothing to clean
            if cid in REPAIR_CHECKS:
                continue
            table, extra, _col = _PLAN[cid]
            _insert(conn, table, id=f"V-{cid}", **extra)
        _insert(conn, "care_plan_task", id="V-T", title="t",
                source_document_id="D1", source_entity_id="E1", source_quote="q")
        conn.commit()
        before = _snapshot(conn)
    finally:
        conn.close()

    counts = _upgrade_head(cfg)

    after, fk_violations = _read(path)
    assert counts == {}
    assert fk_violations == []
    assert after == before
    records = fk_log()
    assert [(r.levelno, r.getMessage()) for r in records] == [
        (logging.INFO, "fk_orphan_cleanup total=0 checks=0")
    ]
    assert not [r for r in records if r.levelno >= logging.WARNING]


def test_hc_fkc_006_rerun_after_downgrade_finds_nothing(vault016, fk_log):
    path, cfg = vault016
    _seed(path, ALL_CHECKS)

    first = _upgrade_head(cfg)
    assert sum(first.values()) == 18
    after_first, _ = _read(path)

    command.downgrade(cfg, REV_016)
    second = _upgrade_head(cfg)

    assert second == {}
    after_second, fk_violations = _read(path)
    assert fk_violations == []
    assert after_second == after_first
    last = [r for r in fk_log() if " total=" in r.getMessage()][-1]
    assert (last.levelno, last.getMessage()) == (
        logging.INFO, "fk_orphan_cleanup total=0 checks=0"
    )


def test_hc_fkc_007_frozen_list_matches_fk_audit(vault016):
    _path, cfg = vault016
    module = ScriptDirectory.from_config(cfg).get_revision(
        "017_fk_cascade_alignment"
    ).module
    frozen = {c.check_id: c for c in module._CLEANUP_CHECKS}

    assert list(frozen) == ALL_CHECKS, "P1-P18, each once, P16 before P17"
    audit = {c.check_id: c for c in PROFILE_CHECKS}
    for cid, row in frozen.items():
        live = audit[cid]
        assert live.enforced, cid
        assert (row.child_table, row.child_column, row.parent_table, row.parent_column) == (
            live.child_table, live.child_column, live.parent_table, live.parent_column,
        ), cid
    # no app-code import: the migration module keeps its own tuple
    tree = ast.parse(Path(module.__file__).read_text())
    imported = {
        (n.module or "") if isinstance(n, ast.ImportFrom) else a.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.Import, ast.ImportFrom))
        for a in getattr(n, "names", [])
    }
    app_roots = {"core", "models", "api", "modules"}
    assert not {m for m in imported if m.split(".")[0] in app_roots}, imported


def test_hc_fkc_011_failed_rebuild_rolls_everything_back_and_logs_nothing(
    vault016, fk_log
):
    """A rebuild that fails after the cleanup leaves the vault exactly at 016.

    Measured on SQLCipher: the whole upgrade rolls back, so the orphan is still
    there, the log has no removed= line (the rows were not removed) and no
    counts are handed to the audit-row writer. The third rebuild is made to
    fail by occupying the temp table name batch_alter_table needs.
    """
    path, cfg = vault016
    conn = _connect(path)
    try:
        _seed_base(conn)
        _table, orphan_id = _plant(conn, "P2")
        conn.execute("CREATE TABLE _alembic_tmp_care_plan_task (x INTEGER)")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(Exception):
        command.upgrade(cfg, "head")

    conn = _connect(path)
    try:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == REV_016
        assert conn.execute("SELECT 1 FROM chunks WHERE id = ?", (orphan_id,)).fetchone()
        assert set(_fk_actions(conn, "document_category").values()) == {"NO ACTION"}
    finally:
        conn.close()
    assert not [r.getMessage() for r in fk_log() if "removed=" in r.getMessage()]
    assert "fk_cleanup_counts" not in cfg.attributes


# --------------------------------------------------------------------------
# HC-FKC-009: counts-only master audit row (P6-CLEANUP-AUDIT)
# --------------------------------------------------------------------------

_PASSWORD = "Fkc-Audit-Pass-9!"


def _plant_sealed_vault(data_dir: Path, pid: str, check_ids) -> bytes:
    """Sealed vault ``data_dir/vaults/<pid>`` at 016 holding ``check_ids`` orphans.

    Returns the vault key. The pragma is OFF while seeding, as in every real vault.
    """
    from core.security import generate_encryption_key, seal_key_with_dpapi

    key = generate_encryption_key()
    vault_dir = data_dir / "vaults" / pid
    vault_dir.mkdir(parents=True)
    sealed, method = seal_key_with_dpapi(key, fallback_password=_PASSWORD, force_password=True)
    (vault_dir / "key.bin").write_bytes(sealed)
    (vault_dir / "key.method").write_text(method)
    vault = vault_dir / "vault.db"
    command.upgrade(_alembic_cfg(vault, key), REV_016)
    if check_ids:
        _seed(vault, check_ids, key)
    return key


@contextlib.asynccontextmanager
async def _planted_vault_client(tmp_path, monkeypatch, check_ids):
    """Real master DB + real sealed vault at 016 holding ``check_ids`` orphans.

    Yields a namespace with an HTTP ``client`` on the profiles router (real
    master session), the profile ``pid``, the vault ``key`` and ``rows()``, the
    master cleanup audit rows read back.
    """
    from types import SimpleNamespace

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    import models  # noqa: F401  registers every master model
    from api.profiles import router as profiles_router
    from core.database import Base
    from core.profile_database import get_profile_db_manager
    from core.security import hash_password
    from core.time import utcnow
    from models.audit import AuditLog
    from models.profile import Profile
    from tests.support.db import fk_profile_engine
    from tests.support.routes import route_client

    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "database_encryption_required", False)
    pid = str(uuid.uuid4())
    key = _plant_sealed_vault(tmp_path, pid, check_ids)

    engine = fk_profile_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    master = AsyncSession(engine, expire_on_commit=False)
    master.add(Profile(
        id=pid, display_name="Fkc Nine", encryption_key_id="k1",
        password_hash=hash_password(_PASSWORD), password_salt="s",
        is_locked=True, created_at=utcnow(), updated_at=utcnow(),
    ))
    await master.commit()

    async def rows():
        return (await master.execute(
            select(AuditLog).where(AuditLog.event_type == "profile.fk_orphan_cleanup")
        )).scalars().all()

    manager = get_profile_db_manager()
    try:
        with route_client(
            profiles_router, "/profiles", master_db=master, raise_server_exceptions=False
        ) as client:
            yield SimpleNamespace(client=client, pid=pid, key=key, rows=rows)
    finally:
        await manager.close_profile_database(pid)
        await master.close()
        await engine.dispose()


def _details(rows) -> list:
    import json

    return [json.loads(r.details_json) if r.details_json else None for r in rows]


async def _unlock_with_planted_vault(tmp_path, monkeypatch, check_ids, *, path, payload_for):
    """Drive ``path`` twice over HTTP (the second call reuses the cached
    connection); return (cleanup audit rows, their details, the responses)."""
    async with _planted_vault_client(tmp_path, monkeypatch, check_ids) as ctx:
        responses = [
            ctx.client.post(path.format(pid=ctx.pid), json=payload_for(ctx.pid))
            for _ in range(2)
        ]
        rows = await ctx.rows()
        return rows, _details(rows), responses, ctx.pid


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,payload_for",
    [
        ("/profiles/{pid}/unlock", lambda pid: {"password": _PASSWORD}),
        ("/profiles/login", lambda pid: {"profile_id": pid, "password": _PASSWORD}),
    ],
    ids=["unlock", "login"],
)
async def test_hc_fkc_009_cleanup_writes_one_counts_only_audit_row(
    tmp_path, monkeypatch, path, payload_for
):
    from core.audit import _scrub_details

    rows, details, responses, pid = await _unlock_with_planted_vault(
        tmp_path, monkeypatch, ["P2", "P3", "P16"], path=path, payload_for=payload_for
    )

    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    # one row for one migration, not one per login (the second call reused the
    # cached connection and must not re-announce the same cleanup)
    assert len(rows) == 1
    row = rows[0]
    assert row.action == "profile.fk_orphan_cleanup"
    # attached to the profile that was migrated: a row under None would outlive
    # that profile's delete purge, a row under another id would be misfiled
    assert row.profile_id == row.entity_id == pid
    assert row.entity_type == "profile"
    assert details[0] == {"resource_counts": {"P2": 1, "P3": 1, "P16": 1}, "count": 3}
    assert _scrub_details(details[0]) == details[0], "scrubbing changed the details"
    blob = " ".join(str(getattr(row, c.name)) for c in row.__table__.columns)
    for planted_id in ("O-P2", "O-P3", "O-P16"):
        assert planted_id not in blob


@pytest.mark.asyncio
async def test_hc_fkc_009b_clean_vault_writes_no_cleanup_row(tmp_path, monkeypatch):
    rows, _d, responses, _pid = await _unlock_with_planted_vault(
        tmp_path, monkeypatch, [], path="/profiles/{pid}/unlock",
        payload_for=lambda pid: {"password": _PASSWORD},
    )
    assert [r.status_code for r in responses] == [200, 200]
    assert rows == []


# The create site (api/profiles.py create_profile) is not driven here: a vault
# created a moment earlier has no orphans, so the cleanup counts are always
# empty there and the call is unreachable in practice. login, unlock and
# recovery open old vaults and are driven.


@pytest.mark.asyncio
async def test_hc_fkc_009c_recovery_site_writes_the_cleanup_row(tmp_path, monkeypatch):
    """/profiles/{pid}/recover opens the vault too; dropping its audit call must
    fail a test."""
    import api.profiles as profiles_api

    async with _planted_vault_client(tmp_path, monkeypatch, ["P2", "P16"]) as ctx:
        code = profiles_api._issue_recovery_code(ctx.pid, ctx.key)
        resp = ctx.client.post(
            f"/profiles/{ctx.pid}/recover",
            json={"recovery_code": code, "new_password": "Brand-New-Pass-7!"},
        )
        rows = await ctx.rows()

    assert resp.status_code == 200, resp.text
    assert len(rows) == 1
    assert _details(rows) == [{"resource_counts": {"P2": 1, "P16": 1}, "count": 2}]
    assert rows[0].profile_id == rows[0].entity_id == ctx.pid
    assert rows[0].entity_type == "profile"


@pytest.mark.asyncio
async def test_hc_fkc_009d_failed_audit_write_is_retried_on_next_login(tmp_path, monkeypatch):
    """The cleanup already deleted rows. If the audit write fails, the counts
    must stay on the cached connection so the next login still records it."""
    import api.profiles as profiles_api

    real = profiles_api.create_audit_log
    calls = {"cleanup": 0}

    async def _flaky(*args, **kwargs):
        if kwargs.get("event_type") == "profile.fk_orphan_cleanup":
            calls["cleanup"] += 1
            if calls["cleanup"] == 1:
                raise RuntimeError("master audit write failed")
        return await real(*args, **kwargs)

    monkeypatch.setattr(profiles_api, "create_audit_log", _flaky)

    async with _planted_vault_client(tmp_path, monkeypatch, ["P3"]) as ctx:
        login = {"profile_id": ctx.pid, "password": _PASSWORD}
        first = ctx.client.post("/profiles/login", json=login)
        after_failure = await ctx.rows()
        second = ctx.client.post("/profiles/login", json=login)
        after_retry = await ctx.rows()
        third = ctx.client.post("/profiles/login", json=login)
        after_third = await ctx.rows()

    assert first.status_code == 500
    assert after_failure == []
    assert second.status_code == 200, second.text
    assert len(after_retry) == 1
    assert _details(after_retry) == [{"resource_counts": {"P3": 1}, "count": 1}]
    assert third.status_code == 200
    assert len(after_third) == 1, "written once, not on every later login"


# --------------------------------------------------------------------------
# scripts/fk_orphan_audit.py: opening the copy runs 017, which cleans it
# --------------------------------------------------------------------------


def _run_audit_script(monkeypatch, capsys, data_dir: Path, pid: str):
    import importlib.util

    script = Path(__file__).parent.parent / "scripts" / "fk_orphan_audit.py"
    spec = importlib.util.spec_from_file_location("fk_orphan_audit_under_test", script)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)

    monkeypatch.setattr(settings, "database_encryption_required", False)
    # main() patches these two fields on the shared settings object; restore them
    monkeypatch.setattr(settings, "app_mode", settings.app_mode)
    monkeypatch.setattr(settings, "sqlite_database_path", settings.sqlite_database_path)
    monkeypatch.setattr(
        sys, "argv",
        ["fk_orphan_audit.py", "--profile", pid, "--source", str(data_dir), "--password", _PASSWORD],
    )
    rc = audit.main()
    return rc, capsys.readouterr().out


def test_hc_fkc_010_audit_script_reports_orphans_017_cleaned_on_the_copy(
    tmp_path, monkeypatch, capsys
):
    """On a pre-017 vault the tool must not print '0 orphans' and exit 0 just
    because opening the copy ran the cleanup first."""
    data_dir = tmp_path / "data"
    pid = str(uuid.uuid4())
    key = _plant_sealed_vault(data_dir, pid, ["P2", "P3", "P16"])
    before = _snapshot_of(data_dir, pid, key)

    rc, out = _run_audit_script(monkeypatch, capsys, data_dir, pid)

    assert rc == 1, out
    assert "cleaned by 017 on the copy" in out
    for check_id in ("P2", "P3", "P16"):
        assert f"{check_id}: 1" in out, out
    assert "O-P2" not in out and "O-P16" not in out, "counts only, no row ids"
    assert _snapshot_of(data_dir, pid, key) == before, "the source vault must stay untouched"


def test_hc_fkc_010b_audit_script_clean_vault_exits_zero(tmp_path, monkeypatch, capsys):
    data_dir = tmp_path / "data"
    pid = str(uuid.uuid4())
    _plant_sealed_vault(data_dir, pid, [])

    rc, out = _run_audit_script(monkeypatch, capsys, data_dir, pid)

    assert rc == 0, out
    assert "cleaned by 017" not in out


def _snapshot_of(data_dir: Path, pid: str, key: bytes):
    conn = _connect(data_dir / "vaults" / pid / "vault.db", key)
    try:
        return _snapshot(conn)
    finally:
        conn.close()


def test_hc_fkc_010c_audit_script_master_missing_exits_2_not_clean(
    tmp_path, monkeypatch, capsys
):
    """No master DB means the audit did not run; that must not read as clean (0)."""
    import importlib.util

    script = Path(__file__).parent.parent / "scripts" / "fk_orphan_audit.py"
    spec = importlib.util.spec_from_file_location("fk_orphan_audit_master", script)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    monkeypatch.setattr(settings, "app_mode", "server")
    monkeypatch.setattr(settings, "sqlite_database_path", str(tmp_path / "absent.db"))

    rc = audit._master()

    assert rc == 2, capsys.readouterr().out
