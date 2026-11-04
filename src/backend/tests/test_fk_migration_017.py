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
import errno
import hashlib
import json
import logging
import logging.config
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402

from core import migrations  # noqa: E402
from core.config import settings  # noqa: E402
from core.fk_audit import PROFILE_CHECKS  # noqa: E402
from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available  # noqa: E402
from core.time import UTC  # noqa: E402
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
ALL_CHECKS = [f"P{i}" for i in range(1, 19)]
# P8/P12 (doses, reminder logs: schedule_id -> NULL) and P16/P17 (care tasks) are
# kept and repaired; every other check deletes the orphan child (P6-P8P12).
SCHEDULE_REPAIR_CHECKS = ["P8", "P12"]
CARE_REPAIR_CHECKS = ["P16", "P17"]
REPAIR_CHECKS = SCHEDULE_REPAIR_CHECKS + CARE_REPAIR_CHECKS
DELETE_CHECKS = [c for c in ALL_CHECKS if c not in REPAIR_CHECKS]


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
    if check_id in CARE_REPAIR_CHECKS:
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


def _row_cols(path: Path, table: str, row_id: str, cols: tuple[str, ...]):
    """The named columns of one row, or None when the row is gone."""
    conn = _connect(path)
    try:
        row = conn.execute(
            f"SELECT {', '.join(cols)} FROM {table} WHERE id = ?", (row_id,)
        ).fetchone()
        return None if row is None else dict(zip(cols, row))
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
    if check_id in SCHEDULE_REPAIR_CHECKS:
        # the dose / reminder log is kept: same row, same id, same medication;
        # only the dangling schedule link is cleared (P6-P8P12)
        assert len(after[table]) == len(before[table]) == 2
        cols = ("schedule_id", "medication_id")
        assert _row_cols(path, table, orphan_id, cols) == {
            "schedule_id": None, "medication_id": "M1",
        }
        # the valid child still points at its schedule
        assert _row_cols(path, table, f"V-{check_id}", cols) == {
            "schedule_id": "S1", "medication_id": "M1",
        }
        others = {t: rows for t, rows in after.items() if t != table}
        assert others == {t: rows for t, rows in before.items() if t != table}
    elif check_id in CARE_REPAIR_CHECKS:
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
        # orphan schedule carrying a dose (P6 deletes the schedule, then P8 keeps
        # the dose and clears its link)
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
        ("chunks", "OC"), ("embeddings", "OE"), ("medication_schedules", "OS"),
    ):
        assert all(r[0] != rid for r in after[table]), f"{table}.{rid} survived"
    # the dose outlived its deleted schedule: kept, link cleared, medication intact
    assert _row_cols(path, "doses_taken", "OD", ("schedule_id", "medication_id")) == {
        "schedule_id": None, "medication_id": "M1",
    }
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
            if cid in CARE_REPAIR_CHECKS:
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
async def _planted_vault_client(tmp_path, monkeypatch, check_ids, *, relative=False):
    """Real master DB + real sealed vault at 016 holding ``check_ids`` orphans.

    Yields a namespace with an HTTP ``client`` on the profiles router (real
    master session), the profile ``pid``, the vault ``key``, ``vault`` (its
    absolute path) and ``rows()``, the master cleanup audit rows read back.
    ``relative``: app_data_path is the relative ``Path("data")``, the default in
    local mode, with the working directory at ``tmp_path``; the app then builds
    every vault path relative.
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

    if relative:
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: Path("data")))
    else:
        data_dir = tmp_path
        monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "database_encryption_required", False)
    pid = str(uuid.uuid4())
    key = _plant_sealed_vault(data_dir, pid, check_ids)

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
            yield SimpleNamespace(
                client=client, pid=pid, key=key, rows=rows,
                vault=data_dir / "vaults" / pid / "vault.db",
            )
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


def test_hc_fkc_010d_audit_script_refuses_when_the_copy_override_did_not_take(
    tmp_path, monkeypatch, capsys
):
    """The tool must only ever migrate its temp copy. If the data-dir override
    did not land there, it must exit 2 and touch nothing; a bare ``assert`` would
    vanish under ``python -O`` and the live vault would be cleaned and snapshotted."""
    data_dir = tmp_path / "data"
    pid = str(uuid.uuid4())
    key = _plant_sealed_vault(data_dir, pid, ["P2"])
    before = _snapshot_of(data_dir, pid, key)
    monkeypatch.setattr(
        type(settings), "app_data_path", property(lambda self: tmp_path / "somewhere-else")
    )

    rc, out = _run_audit_script(monkeypatch, capsys, data_dir, pid)

    assert rc == 2, out
    assert "refusing" in out
    assert _snapshot_of(data_dir, pid, key) == before, "the source vault must stay untouched"
    assert list(data_dir.rglob("vault.pre017*")) == []


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


# --------------------------------------------------------------------------
# HC-FKS: verified encrypted snapshot before 017 (P6-SNAPSHOT)
# --------------------------------------------------------------------------

SNAP_NAME = "vault.pre017.snapshot"
TMP_NAME = "vault.pre017.snapshot.tmp"
ASIDE_NAME = "vault.pre017.snapshot.aside"
MIGRATIONS_LOGGER = "core.migrations"


def _snap(vault: Path) -> Path:
    return vault.with_name(SNAP_NAME)


def _leftovers(vault: Path) -> list[str]:
    """Every ``vault.pre017*`` file except the snapshot itself (temp, sidecars)."""
    return sorted(p.name for p in vault.parent.glob("vault.pre017*") if p.name != SNAP_NAME)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rev(path: Path, key: bytes = KEY):
    return migrations.get_profile_current_revision(path, key)


@pytest.fixture
def mig_log():
    """Records of ``core.migrations``. env.py's fileConfig() strips root handlers
    on every migration run, so a handler on the logger itself is what survives.
    The level is NOT raised: a record reaches the list only if the app's own
    logging configuration lets it through (recurring failure 1)."""
    records: list[logging.LogRecord] = []

    class _Collect(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger(MIGRATIONS_LOGGER)
    handler = _Collect()
    logger.addHandler(handler)
    yield records
    logger.removeHandler(handler)


def _assert_refusal_leaks_nothing(path: Path, exc, records, *, step_words, error_class):
    """One ERROR record naming the step and the exception class; no path, key or
    hex anywhere in the refusal's text or in any WARNING-or-worse record."""
    errors = [r for r in records if r.levelno >= logging.ERROR]
    assert len(errors) == 1, [r.getMessage() for r in errors]
    message = errors[0].getMessage()
    classes = (error_class,) if isinstance(error_class, str) else error_class
    assert any(f"({c})" in message for c in classes), (classes, message)
    assert any(w in message for w in step_words), message
    texts = [str(exc)] + [r.getMessage() for r in records if r.levelno >= logging.WARNING]
    for r in records:
        if r.levelno >= logging.WARNING:
            assert r.exc_info is None and not r.exc_text, "a traceback would carry the path"
    forbidden = [str(path), str(path.parent), path.parent.name, KEY.hex().upper(), KEY.hex(), repr(KEY)]
    for text in texts:
        for needle in forbidden:
            assert needle not in text, f"{needle!r} leaked into {text!r}"
    assert exc.__cause__ is None


def _assert_untouched_at_016(path: Path, sha_before: str, key: bytes = KEY):
    assert _sha(path) == sha_before, "a refused migration must not touch the vault"
    assert _rev(path, key) == REV_016
    assert not _snap(path).exists()
    assert _leftovers(path) == []


def _enospc(src, dst, *args, **kwargs):
    """A copy that runs out of space part-way, leaving a half-written temp."""
    Path(dst).write_bytes(b"\x00" * 10)
    raise OSError(errno.ENOSPC, "No space left on device", str(dst))


def _corrupt_whole(_src: Path, dst: Path) -> None:
    dst.write_bytes(b"\xa5" * dst.stat().st_size)  # same size, nothing opens


def _corrupt_empty(_src: Path, dst: Path) -> None:
    dst.write_bytes(b"")  # an empty file is a valid empty database to SQLite


def _corrupt_table_page(src: Path, dst: Path) -> None:
    """Page 1 and sqlite_master stay readable, so only a full scan sees this."""
    conn = _connect(src)
    try:
        root = int(conn.execute("SELECT rootpage FROM sqlite_master WHERE name='chunks'").fetchone()[0])
        psize = int(conn.execute("PRAGMA page_size").fetchone()[0])
    finally:
        conn.close()
    with open(dst, "r+b") as f:
        f.seek((root - 1) * psize)
        f.write(b"\xa5" * psize)


def _copy_then(corrupt):
    real = shutil.copy2

    def _copy(src, dst, *args, **kwargs):
        out = real(src, dst, *args, **kwargs)
        corrupt(Path(src), Path(dst))
        return out

    return _copy


def test_hc_fks_001_real_snapshot_of_the_pre_017_vault(vault016):
    path, _cfg = vault016
    _seed(path, ALL_CHECKS)
    sha_before = _sha(path)

    counts = migrations.run_profile_migration(path, KEY)

    assert sum(counts.values()) == 18
    snap = _snap(path)
    assert snap.is_file()
    assert _leftovers(path) == [], "no temp or sidecar may stay behind"
    # the copy is the vault exactly as it was before the upgrade
    assert _sha(snap) == sha_before
    conn = _connect(snap)  # same key opens it
    try:
        assert [tuple(r) for r in conn.execute("PRAGMA quick_check")] == [("ok",)]
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == REV_016
        rows = _snapshot(conn)
    finally:
        conn.close()
    # every planted orphan is still in the snapshot ...
    for cid in ALL_CHECKS:
        table, orphan_id = (
            ("care_plan_task", f"O-{cid}") if cid in CARE_REPAIR_CHECKS
            else (_PLAN[cid][0], f"O-{cid}")
        )
        assert any(r[0] == orphan_id for r in rows[table]), f"{cid} orphan missing from snapshot"
    # ... and gone from the live vault, which is at head
    assert _rev(path) == PROFILE_HEAD
    live, fk_violations = _read(path)
    assert fk_violations == []
    assert all(r[0] != "O-P2" for r in live["chunks"])
    if is_sqlcipher_available():
        with pytest.raises(Exception):
            wrong = _connect(snap, b"1" * 32)
            try:
                wrong.execute("SELECT count(*) FROM sqlite_master").fetchall()
            finally:
                wrong.close()
        assert snap.read_bytes()[:16] != b"SQLite format 3\x00", "snapshot must stay encrypted"


def test_hc_fks_002_no_snapshot_for_a_new_vault_or_a_vault_at_head(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    new = tmp_path / "new" / "vault.db"

    migrations.run_profile_migration(new, KEY)  # empty -> head
    assert _rev(new) == PROFILE_HEAD
    assert list(new.parent.glob("vault.pre017*")) == []

    migrations.run_profile_migration(new, KEY)  # already at head
    assert list(new.parent.glob("vault.pre017*")) == []


def _config_with_a_later_revision(tmp_path: Path, upgrade_body: str = "pass"):
    """A profile script directory with a made-up 018 on top of 017."""
    src = Path(migrations.__file__).parent.parent / "migrations" / "profile"
    dst = tmp_path / "scripts018"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    (dst / "versions" / "018_next.py").write_text(
        'revision = "018_next"\ndown_revision = "017_fk_cascade_alignment"\n'
        "branch_labels = None\ndepends_on = None\n"
        f"def upgrade():\n    {upgrade_body}\ndef downgrade():\n    pass\n"
    )
    cfg = migrations._get_alembic_config("profile")
    cfg.set_main_option("script_location", str(dst))
    return cfg


def test_hc_fks_002b_pending_helper_is_about_017_not_about_head(tmp_path):
    pending = migrations._pre017_snapshot_pending
    cfg = migrations._get_alembic_config("profile")
    assert migrations._SNAPSHOT_REVISION == "017_fk_cascade_alignment"

    assert pending(cfg, REV_016) is True
    assert pending(cfg, "010_entity_source_spans") is True
    assert pending(cfg, "001_initial") is True
    assert pending(cfg, "017_fk_cascade_alignment") is False

    # once an 018 exists, a vault at 018 or at 017 must still not be "pending"
    later = _config_with_a_later_revision(tmp_path)
    assert pending(later, "018_next") is False
    assert pending(later, "017_fk_cascade_alignment") is False
    assert pending(later, REV_016) is True
    # unknown revision: fail closed, which here means take the snapshot
    assert pending(cfg, "no_such_revision") is True


@pytest.mark.parametrize(
    "corrupt,error_class",
    [
        (_corrupt_whole, "DatabaseError"),  # the key check cannot read page 1
        (_corrupt_empty, "_SnapshotInvalid"),  # opens fine, holds nothing
        (_corrupt_table_page, ("OperationalError", "DatabaseError", "_SnapshotInvalid")),  # only a full scan sees it
    ],
    ids=["garbage", "empty", "table_page"],
)
def test_hc_fks_003_corrupt_copy_refuses_and_leaves_the_vault_alone(
    vault016, monkeypatch, mig_log, corrupt, error_class
):
    path, _cfg = vault016
    _seed(path, ["P2"])
    sha_before = _sha(path)
    monkeypatch.setattr(migrations.shutil, "copy2", _copy_then(corrupt))

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    _assert_untouched_at_016(path, sha_before)
    _assert_refusal_leaks_nothing(
        path, exc.value, mig_log, step_words=("verify",), error_class=error_class
    )


def test_hc_fks_004_unwritable_destination_refuses_and_leaves_the_vault_alone(
    vault016, monkeypatch, mig_log
):
    path, _cfg = vault016
    _seed(path, ["P2"])
    sha_before = _sha(path)
    monkeypatch.setattr(migrations.shutil, "copy2", _enospc)

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    _assert_untouched_at_016(path, sha_before)
    _assert_refusal_leaks_nothing(
        path, exc.value, mig_log, step_words=("copy",), error_class="OSError"
    )


def _enable_wal_with_rows_only_in_the_wal(path: Path):
    """Switch the vault to WAL and commit a row that lives only in ``-wal``.

    The returned connection must stay open: the last close checkpoints and
    deletes the WAL, which would remove the very thing under test.
    """
    hold = _connect(path)
    assert hold.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
    hold.execute("PRAGMA wal_autocheckpoint=0")
    _insert(hold, "documents", id="WAL-ONLY")
    hold.commit()
    assert Path(str(path) + "-wal").stat().st_size > 0
    return hold


def test_hc_fks_005_rows_only_in_the_wal_reach_the_snapshot(vault016, tmp_path):
    path, _cfg = vault016
    hold = _enable_wal_with_rows_only_in_the_wal(path)
    try:
        # premise: the main file alone does not hold the row
        alone = tmp_path / "main-file-only.db"
        shutil.copy2(path, alone)
        conn = _connect(alone)
        try:
            assert conn.execute("SELECT count(*) FROM documents WHERE id='WAL-ONLY'").fetchone()[0] == 0
        finally:
            conn.close()

        migrations.run_profile_migration(path, KEY)
    finally:
        hold.close()

    conn = _connect(_snap(path))
    try:
        assert conn.execute("SELECT count(*) FROM documents WHERE id='WAL-ONLY'").fetchone()[0] == 1
        assert [tuple(r) for r in conn.execute("PRAGMA quick_check")] == [("ok",)]
    finally:
        conn.close()
    assert _rev(path) == PROFILE_HEAD
    assert _leftovers(path) == []


def test_hc_fks_005b_a_busy_checkpoint_refuses(vault016, monkeypatch, mig_log):
    path, _cfg = vault016
    monkeypatch.setattr(migrations, "_SNAPSHOT_BUSY_TIMEOUT_S", 0.2)
    hold = _enable_wal_with_rows_only_in_the_wal(path)
    reader = _connect(path)
    reader.execute("BEGIN")
    reader.execute("SELECT * FROM documents").fetchone()  # read transaction stays open
    try:
        with pytest.raises(migrations.ProfileMigrationRefused) as exc:
            migrations.run_profile_migration(path, KEY)
    finally:
        reader.close()
        hold.close()

    assert _rev(path) == REV_016
    assert not _snap(path).exists()
    assert _leftovers(path) == []
    _assert_refusal_leaks_nothing(
        path, exc.value, mig_log, step_words=("checkpoint",), error_class="_SnapshotInvalid"
    )


def _vault_with_orphan_and_blocker(vault016):
    """016 vault with a P2 orphan and a table that makes the third rebuild fail
    (the HC-FKC-011 failure)."""
    path, cfg = vault016
    conn = _connect(path)
    try:
        _seed_base(conn)
        _table, orphan_id = _plant(conn, "P2")
        conn.execute("CREATE TABLE _alembic_tmp_care_plan_task (x INTEGER)")
        conn.commit()
    finally:
        conn.close()
    return path, orphan_id


def test_hc_fks_008_keep_first_a_retry_does_not_overwrite_the_pristine_copy(vault016):
    path, orphan_id = _vault_with_orphan_and_blocker(vault016)

    with pytest.raises(Exception) as first:
        migrations.run_profile_migration(path, KEY)
    assert not isinstance(first.value, migrations.ProfileMigrationRefused), "the upgrade failed, not the snapshot"
    snap = _snap(path)
    first_bytes = snap.read_bytes()
    assert _rev(path) == REV_016

    # a partly cleaned vault and the blocker gone: the retry now succeeds
    conn = _connect(path)
    try:
        conn.execute("DROP TABLE _alembic_tmp_care_plan_task")
        conn.execute("DELETE FROM chunks WHERE id = ?", (orphan_id,))
        conn.commit()
    finally:
        conn.close()
    migrations.run_profile_migration(path, KEY)

    assert _rev(path) == PROFILE_HEAD
    assert snap.read_bytes() == first_bytes, "the first, pristine snapshot must be kept"
    conn = _connect(snap)
    try:
        assert conn.execute("SELECT 1 FROM chunks WHERE id = ?", (orphan_id,)).fetchone(), (
            "the snapshot must still hold the orphan the live vault lost"
        )
    finally:
        conn.close()


@pytest.mark.parametrize(
    "existing", [b"not a database" * 100, b""], ids=["garbage", "zero_bytes"]
)
def test_hc_fks_008b_a_snapshot_that_does_not_verify_is_moved_aside_not_replaced(vault016, existing):
    """A 0-byte file opens as a valid empty database and passes quick_check, so
    only the has-tables check in the verifier can reject it. (HC-FKS-003[empty]
    cannot see that check: the size comparison on a fresh copy fires first.)
    The damaged file is kept, byte for byte, under the aside name."""
    path, _cfg = vault016
    _seed(path, ["P2"])
    sha_before = _sha(path)
    _snap(path).write_bytes(existing)

    migrations.run_profile_migration(path, KEY)

    assert _sha(_snap(path)) == sha_before, "a fresh, verified copy took its place"
    assert path.with_name(ASIDE_NAME).read_bytes() == existing, "the damaged file is kept, not replaced"
    assert _leftovers(path) == [ASIDE_NAME]


def test_hc_fks_008c_a_failed_attempt_never_touches_the_final_name(vault016, monkeypatch):
    path, _cfg = vault016
    _seed(path, ["P2"])
    snap = _snap(path)
    snap.write_bytes(b"not a database" * 100)
    existing = snap.read_bytes()
    monkeypatch.setattr(migrations.shutil, "copy2", _enospc)

    with pytest.raises(migrations.ProfileMigrationRefused):
        migrations.run_profile_migration(path, KEY)

    assert not snap.exists(), "only a verified temp may publish: the failed copy published nothing"
    assert path.with_name(ASIDE_NAME).read_bytes() == existing, "the damaged file was moved aside, not lost"
    assert _leftovers(path) == [ASIDE_NAME], "no temp is left"
    assert _rev(path) == REV_016


@pytest.mark.parametrize("scoped", [False, True], ids=["full", "scoped"])
def test_hc_fks_009_a_real_backup_leaves_the_snapshot_temp_and_aside_out(
    tmp_path, monkeypatch, scoped
):
    from scripts.backup import backup

    monkeypatch.setattr(settings, "database_encryption_required", False)
    pid = "p9"
    data = tmp_path / "data"
    vault_dir = data / "vaults" / pid
    vault_dir.mkdir(parents=True)
    vault = vault_dir / "vault.db"
    command.upgrade(_alembic_cfg(vault), REV_016)
    _seed(vault, ["P2"])
    migrations.run_profile_migration(vault, KEY)
    (vault_dir / TMP_NAME).write_bytes(b"an interrupted attempt")
    # a real aside: a real encrypted vault copy under the aside name, and a sidecar
    shutil.copy2(vault_dir / SNAP_NAME, vault_dir / ASIDE_NAME)
    (vault_dir / (ASIDE_NAME + "-wal")).write_bytes(b"an aside sidecar")
    on_disk = [p.name for p in vault_dir.glob("vault.pre017*")]
    assert len(on_disk) == 4, f"fixture needs a snapshot, a temp, an aside and a sidecar: {on_disk}"

    result = backup(data, tmp_path / "backups", profile_id=pid if scoped else None)

    assert result.success
    stored = [p.name for p in result.backup_path.rglob("*") if p.is_file()]
    assert "vault.db" in stored, stored
    assert not [n for n in stored if n.startswith("vault.pre017")], stored
    manifest = json.loads(result.manifest_path.read_text())
    assert not [f for f in manifest["files"] if "pre017" in f["path"]]


@pytest.mark.asyncio
async def test_hc_fks_012_login_with_the_snapshot_refused_is_the_fixed_500(
    tmp_path, monkeypatch
):
    from core.profile_database import get_profile_db_manager

    async with _planted_vault_client(tmp_path, monkeypatch, ["P2"]) as ctx:
        vault = tmp_path / "vaults" / ctx.pid / "vault.db"
        sha_before = _sha(vault)
        login = {"profile_id": ctx.pid, "password": _PASSWORD}

        with monkeypatch.context() as patched:
            patched.setattr(migrations.shutil, "copy2", _enospc)
            refused = ctx.client.post("/profiles/login", json=login)

        assert refused.status_code == 500
        assert refused.json()["detail"] == "Failed to open profile database"
        assert str(tmp_path) not in refused.text
        assert ctx.pid not in get_profile_db_manager()._connections, "no cached connection"
        _assert_untouched_at_016(vault, sha_before, ctx.key)
        assert await ctx.rows() == [], "nothing was cleaned, so nothing is audited"

        ok = ctx.client.post("/profiles/login", json=login)
        assert ok.status_code == 200, ok.text
        assert len(await ctx.rows()) == 1
        assert _snap(vault).is_file()


@pytest.mark.asyncio
async def test_hc_fks_013_recovery_with_the_snapshot_refused_loses_the_new_code(
    tmp_path, monkeypatch
):
    """Pins the accepted limit (item 2 of the owner ask): recover_profile commits
    the new password and the rotated code before it opens the vault, so a refused
    snapshot returns a 500 with no code in it, and the code the patient typed is
    already spent."""
    import api.profiles as profiles_api

    new_password = "Brand-New-Pass-7!"
    async with _planted_vault_client(tmp_path, monkeypatch, ["P2"]) as ctx:
        vault = tmp_path / "vaults" / ctx.pid / "vault.db"
        code = profiles_api._issue_recovery_code(ctx.pid, ctx.key)
        body = {"recovery_code": code, "new_password": new_password}

        with monkeypatch.context() as patched:
            patched.setattr(migrations.shutil, "copy2", _enospc)
            refused = ctx.client.post(f"/profiles/{ctx.pid}/recover", json=body)

        assert refused.status_code == 500
        assert "recovery_code" not in refused.text, "the rotated code never reached the patient"
        assert _rev(vault, ctx.key) == REV_016
        # the code that was typed is spent, so it cannot be retried ...
        again = ctx.client.post(f"/profiles/{ctx.pid}/recover", json=body)
        assert again.status_code == 401
        # ... but the new password was committed and opens the vault
        login = ctx.client.post(
            "/profiles/login", json={"profile_id": ctx.pid, "password": new_password}
        )
        assert login.status_code == 200, login.text
        assert _rev(vault, ctx.key) == PROFILE_HEAD


# --------------------------------------------------------------------------
# HC-FKS: age and purge of the snapshot
# --------------------------------------------------------------------------


@pytest.fixture
def local_tz():
    """Switch the process time zone for one test; always restore it."""
    old = os.environ.get("TZ")

    def _set(name: str) -> None:
        os.environ["TZ"] = name
        time.tzset()

    yield _set
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


@pytest.mark.parametrize(
    "tz_name", ["UTC", "Pacific/Kiritimati", "America/Los_Angeles"],
)
def test_hc_fks_006_snapshot_age_counts_from_when_it_was_made(vault016, local_tz, tz_name):
    """copy2 keeps the vault's mtime, so a snapshot of a 60-day-old vault would
    look 60 days old and be purged on the next open. The explicit time is also
    computed as UTC: a naive utcnow().timestamp() reads as local time, which is
    hours off in any zone but UTC."""
    local_tz(tz_name)
    path, _cfg = vault016
    _seed(path, ["P2"])
    sixty_days_ago = time.time() - 60 * 86400
    os.utime(path, (sixty_days_ago, sixty_days_ago))

    migrations.run_profile_migration(path, KEY)

    snap = _snap(path)
    assert abs(snap.stat().st_mtime - time.time()) < 120, "the snapshot is as old as its own creation"
    migrations.run_profile_migration(path, KEY)  # the next open, vault at head
    assert snap.is_file(), "a fresh snapshot must survive the next open"


def _head_vault(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(settings, "database_encryption_required", False)
    vault = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(vault), "head")
    return vault


def _utc_ts(moment: datetime) -> float:
    return moment.replace(tzinfo=UTC).timestamp()


MADE_AT = datetime(2026, 10, 1, 12, 0, 0)


@pytest.mark.parametrize(
    "age,purged",
    [
        (timedelta(days=30), True),
        (timedelta(days=30, seconds=1), True),
        (timedelta(days=29, hours=23), False),
        (timedelta(0), False),
    ],
    ids=["exactly-30d", "30d-1s", "29d-23h", "just-made"],
)
def test_hc_fks_007_snapshot_purged_at_thirty_days_on_the_next_open(
    tmp_path, monkeypatch, age, purged
):
    vault = _head_vault(tmp_path, monkeypatch)
    snap = _snap(vault)
    snap.write_bytes(b"a snapshot")
    os.utime(snap, (_utc_ts(MADE_AT), _utc_ts(MADE_AT)))
    monkeypatch.setattr(migrations, "utcnow", lambda: MADE_AT + age)

    migrations.run_profile_migration(vault, KEY)  # an open of a vault already at head

    assert snap.exists() is (not purged)
    assert _rev(vault) == PROFILE_HEAD


def test_hc_fks_007b_a_stale_temp_is_removed_at_any_age(tmp_path, monkeypatch):
    vault = _head_vault(tmp_path, monkeypatch)
    snap = _snap(vault)
    snap.write_bytes(b"a young snapshot")
    stale = [vault.with_name(TMP_NAME + suffix) for suffix in ("", "-wal", "-shm")]
    for path in stale:
        path.write_bytes(b"interrupted")  # mtime is now: age does not matter

    migrations.run_profile_migration(vault, KEY)

    assert [p.name for p in stale if p.exists()] == []
    assert snap.exists(), "only the temp goes; a young snapshot stays"


def test_hc_fks_007c_a_failing_purge_does_not_block_the_open(tmp_path, monkeypatch, mig_log):
    vault = _head_vault(tmp_path, monkeypatch)
    snap = _snap(vault)
    snap.write_bytes(b"an old snapshot")
    os.utime(snap, (_utc_ts(MADE_AT), _utc_ts(MADE_AT)))
    monkeypatch.setattr(migrations, "utcnow", lambda: MADE_AT + timedelta(days=45))
    real_unlink = Path.unlink

    def _locked(self, *args, **kwargs):
        if self.name.startswith("vault.pre017"):
            raise PermissionError(errno.EACCES, "locked", str(self))
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _locked)

    migrations.run_profile_migration(vault, KEY)  # must not raise

    assert snap.exists(), "the purge failed, so the file is still there"
    warnings = [r.getMessage() for r in mig_log if r.levelno == logging.WARNING]
    assert any("PermissionError" in w for w in warnings), warnings
    for w in warnings:
        assert str(vault.parent) not in w
    assert not [r for r in mig_log if r.levelno >= logging.ERROR]


def _apply_alembic_ini_logging() -> None:
    """The level the running app has: alembic.ini's fileConfig (root WARN), as
    env.py applies it on every migration run. No setLevel anywhere in the tests."""
    ini = migrations._get_alembic_config("profile").config_file_name
    logging.config.fileConfig(ini, disable_existing_loggers=False)
    assert logging.getLogger(MIGRATIONS_LOGGER).isEnabledFor(logging.WARNING)
    assert not logging.getLogger(MIGRATIONS_LOGGER).isEnabledFor(logging.INFO)


def _event_infos(records) -> list[str]:
    """Snapshot event lines. WARNING, because INFO never reaches the log in the
    running app (root is WARN in alembic.ini and nothing raises core.migrations)."""
    return [r.getMessage() for r in records if r.levelno == logging.WARNING and "napshot" in r.getMessage()]


def test_hc_fks_014_a_made_snapshot_is_logged_without_a_path(vault016, mig_log):
    """A full copy of the vault is written with no audit row, so the log line is
    the only trace that the retention rule started. Event words only."""
    path, _cfg = vault016
    _seed(path, ["P2"])
    _apply_alembic_ini_logging()

    migrations.run_profile_migration(path, KEY)

    infos = _event_infos(mig_log)
    assert len(infos) == 1, infos
    assert "created" in infos[0]
    for needle in (str(path.parent), path.parent.name, SNAP_NAME, KEY.hex()):
        assert needle not in infos[0], infos[0]


def test_hc_fks_015_a_purged_snapshot_is_logged_without_a_path(tmp_path, monkeypatch, mig_log):
    vault = _head_vault(tmp_path, monkeypatch)
    snap = _snap(vault)
    snap.write_bytes(b"an old snapshot")
    os.utime(snap, (_utc_ts(MADE_AT), _utc_ts(MADE_AT)))
    monkeypatch.setattr(migrations, "utcnow", lambda: MADE_AT + timedelta(days=30))
    _apply_alembic_ini_logging()

    migrations.run_profile_migration(vault, KEY)

    assert not snap.exists()
    infos = _event_infos(mig_log)
    assert len(infos) == 1, infos
    assert "purged" in infos[0]
    for needle in (str(vault.parent), vault.parent.name, SNAP_NAME):
        assert needle not in infos[0], infos[0]


def test_hc_fks_007d_public_purge_removes_everything_and_raises_on_failure(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    names = [
        base + s
        for base in (SNAP_NAME, TMP_NAME, ASIDE_NAME)
        for s in ("", "-wal", "-shm", "-journal")
    ]

    def _plant_all():
        for name in names:
            (tmp_path / name).write_bytes(b"x")
        vault.write_bytes(b"the vault itself")

    _plant_all()
    migrations.purge_pre017_snapshot(vault)
    assert [p.name for p in tmp_path.iterdir()] == ["vault.db"], "only the vault stays"
    migrations.purge_pre017_snapshot(vault)  # nothing left: not an error

    for locked_name in (SNAP_NAME, ASIDE_NAME):
        _plant_all()
        real_unlink = Path.unlink

        def _locked(self, *args, _locked_name=locked_name, **kwargs):
            if self.name == _locked_name:
                raise PermissionError(errno.EACCES, "locked", str(self))
            return real_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", _locked)
        with pytest.raises(PermissionError):
            migrations.purge_pre017_snapshot(vault)
        monkeypatch.undo()
        assert sorted(p.name for p in tmp_path.iterdir()) == sorted(["vault.db", locked_name]), (
            "one failure must not stop the other files from being removed"
        )
        (tmp_path / locked_name).unlink()


# --------------------------------------------------------------------------
# HC-FKS-016..018: the age purge waits until the vault is confirmed at 017
# --------------------------------------------------------------------------


def _set_age(path: Path, made: datetime) -> None:
    os.utime(path, (_utc_ts(made), _utc_ts(made)))


def _state(path: Path) -> tuple[bytes, int]:
    """Bytes and mtime: a purge-and-recopy that keeps the bytes still changes the mtime."""
    return path.read_bytes(), path.stat().st_mtime_ns


def test_hc_fks_016_a_failed_017_keeps_an_aged_snapshot_until_it_completes(vault016, monkeypatch):
    """The snapshot is the only copy of rows 017 deletes. While 017 has not
    completed it must survive any age, and the open that completes 017 must not
    purge it either: that call has just deleted rows."""
    path, _orphan_id = _vault_with_orphan_and_blocker(vault016)
    with pytest.raises(Exception) as first:
        migrations.run_profile_migration(path, KEY)
    assert not isinstance(first.value, migrations.ProfileMigrationRefused), "the upgrade failed, not the snapshot"
    snap = _snap(path)
    _set_age(snap, MADE_AT)
    monkeypatch.setattr(migrations, "utcnow", lambda: MADE_AT + timedelta(days=31))
    before = _state(snap)

    with pytest.raises(Exception) as retry:  # still blocked, snapshot is 31 days old
        migrations.run_profile_migration(path, KEY)

    assert not isinstance(retry.value, migrations.ProfileMigrationRefused)
    assert snap.is_file(), "a failed retry must not purge the snapshot"
    assert _state(snap) == before, "not purged and re-copied either"
    assert _rev(path) == REV_016

    conn = _connect(path)
    try:
        conn.execute("DROP TABLE _alembic_tmp_care_plan_task")
        conn.commit()
    finally:
        conn.close()
    migrations.run_profile_migration(path, KEY)  # the open that completes 017

    assert _rev(path) == PROFILE_HEAD
    assert snap.is_file() and _state(snap) == before, "the open that completes 017 keeps the aged snapshot"

    migrations.run_profile_migration(path, KEY)  # the next open: confirmed at 017

    assert not snap.exists(), "purged on the first open after success"
    assert _leftovers(path) == []


def _refused_no_match(tmp_path, monkeypatch, request):
    request.getfixturevalue("fast_references")
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_016)
    conn = _connect(path)
    try:
        conn.execute("ALTER TABLE documents ADD COLUMN stray_column TEXT")
        conn.commit()
    finally:
        conn.close()
    _unversioned(path)
    return path, migrations.ProfileMigrationRefused, [SNAP_NAME]


def _failed_with_018_pending(tmp_path, monkeypatch, request):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), "head")  # confirmed at 017
    later = _config_with_a_later_revision(tmp_path, upgrade_body="raise RuntimeError('018 fails')")
    monkeypatch.setattr(migrations, "_get_alembic_config", lambda section="master": later)
    return path, Exception, [SNAP_NAME]


def _refused_aside_occupied(tmp_path, monkeypatch, request):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_016)
    _seed(path, ["P2"])
    # the planted snapshot is garbage (fails verification) and the aside is taken
    return path, migrations.ProfileMigrationRefused, [SNAP_NAME, ASIDE_NAME]


_REFUSED_CASES = {
    "unversioned-no-match": _refused_no_match,
    "failed-018-after-017": _failed_with_018_pending,
    "damaged-snapshot-aside-occupied": _refused_aside_occupied,
}


@pytest.mark.parametrize("case", list(_REFUSED_CASES))
def test_hc_fks_017_a_refused_or_failed_open_keeps_an_aged_snapshot(
    tmp_path, monkeypatch, request, case
):
    path, expected, aged = _REFUSED_CASES[case](tmp_path, monkeypatch, request)
    for name in aged:
        planted = path.with_name(name)
        planted.write_bytes(b"planted " + name.encode())
        _set_age(planted, MADE_AT)
    monkeypatch.setattr(migrations, "utcnow", lambda: MADE_AT + timedelta(days=45))
    before = {name: _state(path.with_name(name)) for name in aged}

    with pytest.raises(expected):
        migrations.run_profile_migration(path, KEY)

    for name in aged:
        assert path.with_name(name).is_file(), f"{name} was purged by a refused or failed open"
        assert _state(path.with_name(name)) == before[name]


def _purge_case_at_head(tmp_path, monkeypatch):
    return _head_vault(tmp_path, monkeypatch), PROFILE_HEAD


def _purge_case_017_with_018_pending(tmp_path, monkeypatch):
    vault = _head_vault(tmp_path, monkeypatch)
    later = _config_with_a_later_revision(tmp_path)
    monkeypatch.setattr(migrations, "_get_alembic_config", lambda section="master": later)
    return vault, "018_next"


@pytest.mark.parametrize(
    "where", [_purge_case_at_head, _purge_case_017_with_018_pending], ids=["at-head", "017-with-018-pending"]
)
@pytest.mark.parametrize(
    "snap_days,aside_days,snap_kept,aside_kept",
    [
        (45, None, False, None),
        (3, None, True, None),
        (45, 45, False, False),
        (3, 45, True, False),
        (45, 3, False, True),
        (3, 3, True, True),
    ],
    ids=[
        "snapshot-aged", "snapshot-young", "both-aged", "aside-aged-snapshot-young",
        "snapshot-aged-aside-young", "both-young",
    ],
)
def test_hc_fks_018_a_vault_confirmed_at_017_purges_what_is_aged(
    tmp_path, monkeypatch, where, snap_days, aside_days, snap_kept, aside_kept
):
    """At head the purge runs. At 017 with a newer revision pending it runs after
    that upgrade succeeded (a stubbed 018 stands in for a future revision). The
    snapshot and the aside are judged separately, each by its own mtime."""
    vault, final_rev = where(tmp_path, monkeypatch)
    now = MADE_AT + timedelta(days=60)
    planted = {SNAP_NAME: (snap_days, snap_kept), ASIDE_NAME: (aside_days, aside_kept)}
    for name, (days, _kept) in planted.items():
        if days is not None:
            vault.with_name(name).write_bytes(b"planted " + name.encode())
            _set_age(vault.with_name(name), now - timedelta(days=days))
    monkeypatch.setattr(migrations, "utcnow", lambda: now)

    migrations.run_profile_migration(vault, KEY)

    assert _rev(vault) == final_rev
    for name, (days, kept) in planted.items():
        if days is not None:
            assert vault.with_name(name).exists() is kept, name


@pytest.mark.parametrize("aside_days", [3, 45], ids=["young-aside", "aged-aside"])
def test_hc_fks_018_a_vault_below_017_keeps_the_aside_whatever_its_age(
    vault016, monkeypatch, aside_days
):
    path, _cfg = vault016
    _seed(path, ["P2"])
    now = MADE_AT + timedelta(days=60)
    aside = path.with_name(ASIDE_NAME)
    aside.write_bytes(b"planted aside")
    _set_age(aside, now - timedelta(days=aside_days))
    before = _state(aside)
    monkeypatch.setattr(migrations, "utcnow", lambda: now)

    migrations.run_profile_migration(path, KEY)  # completes 017 on this call

    assert _rev(path) == PROFILE_HEAD
    assert _snap(path).is_file(), "the new snapshot is there"
    assert aside.is_file() and _state(aside) == before, "no purge in a call that began below 017"


# --------------------------------------------------------------------------
# HC-FKS-019..021: a snapshot that fails verification is moved aside (P6-SNAPSHOT)
# --------------------------------------------------------------------------

ASIDE_SIDECARS = ("-wal", "-shm", "-journal")


def _damaged_garbage(_vault: Path) -> bytes:
    return b"not a database" * 100


def _damaged_head_zeroed(vault: Path) -> bytes:
    """A real encrypted vault copy whose first 8 KB (header and first pages) is zeroed."""
    real = vault.read_bytes()
    assert len(real) > 8192
    return bytes(8192) + real[8192:]


def _damaged_zero_bytes(_vault: Path) -> bytes:
    return b""


def _damaged_mid_page_flip(vault: Path) -> bytes:
    """A real encrypted vault copy with one byte flipped inside a page, past the
    header. The page's HMAC then fails: the driver raises OperationalError (code
    1, "SQL logic error"), not NOTADB. A rule that read every OperationalError as
    "not damage" would turn this real damage into a lockout. Plain SQLite has no
    page HMAC, so without SQLCipher a flipped byte is not detected: skipped."""
    if not is_sqlcipher_available():
        pytest.skip("plain SQLite has no page HMAC")
    real = bytearray(vault.read_bytes())
    assert len(real) > 3 * 4096
    real[2 * 4096 + 100] ^= 0xFF
    return bytes(real)


_DAMAGED = {
    "garbage": _damaged_garbage,
    "head-zeroed": _damaged_head_zeroed,
    "zero-bytes": _damaged_zero_bytes,
    "mid-page-flip": _damaged_mid_page_flip,
}


def _plant_damaged_snapshot(path: Path, damaged: bytes) -> dict[str, bytes]:
    """The damaged main file and all three sidecars, each with its own bytes."""
    planted = {SNAP_NAME: damaged}
    for suffix in ASIDE_SIDECARS:
        planted[SNAP_NAME + suffix] = f"damaged sidecar {suffix} ".encode() * 7
    for name, data in planted.items():
        path.with_name(name).write_bytes(data)
        _set_age(path.with_name(name), MADE_AT)
    return planted


@pytest.mark.parametrize("damage", list(_DAMAGED))
def test_hc_fks_019_a_corrupted_snapshot_is_moved_aside_and_a_new_one_taken(
    vault016, mig_log, damage
):
    path, _cfg = vault016
    _seed(path, ["P2"])
    sha_vault = _sha(path)
    planted = _plant_damaged_snapshot(path, _DAMAGED[damage](path))
    originals = dict(planted)
    mtimes = {name: path.with_name(name).stat().st_mtime_ns for name in originals}
    with tempfile.TemporaryDirectory() as probe:  # the damage must really fail verification
        shutil.copy2(_snap(path), Path(probe) / "probe")
        with pytest.raises(Exception):
            migrations._verify_snapshot(Path(probe) / "probe", migrations._key_to_hex(KEY))
    _apply_alembic_ini_logging()

    migrations.run_profile_migration(path, KEY)

    for name, data in originals.items():
        moved = path.with_name(name.replace(SNAP_NAME, ASIDE_NAME, 1))
        assert moved.read_bytes() == data, f"{name} was not moved byte for byte"
        assert moved.stat().st_mtime_ns == mtimes[name], "the aside is not stamped: its age is the original's"
    for suffix in ASIDE_SIDECARS:
        assert not path.with_name(SNAP_NAME + suffix).exists(), "no sidecar is left at the snapshot name"
    migrations._verify_snapshot(_snap(path), migrations._key_to_hex(KEY))  # raises if not good
    assert _sha(_snap(path)) == sha_vault, "the new snapshot is a copy of the vault as it was"
    assert _rev(path) == PROFILE_HEAD
    assert _leftovers(path) == sorted([ASIDE_NAME] + [ASIDE_NAME + s for s in ASIDE_SIDECARS])

    events = [r.getMessage() for r in mig_log if r.levelno == logging.WARNING and "aside" in r.getMessage().lower()]
    assert len(events) == 1, events
    for needle in (str(path), str(path.parent), path.parent.name, SNAP_NAME, ASIDE_NAME, "vault.db", KEY.hex(), KEY.hex().upper()):
        assert needle not in events[0], events[0]
    # the exception class (and only the class) is logged, as in every refusal: a
    # moved-aside line without it cannot tell damage from a bug
    assert events[0].endswith(("(_SnapshotInvalid)", "(DatabaseError)", "(OperationalError)")), events[0]
    assert not [r for r in mig_log if r.levelno >= logging.ERROR]


def _tree_shas(folder: Path) -> dict[str, str]:
    return {p.name: _sha(p) for p in sorted(folder.iterdir()) if p.is_file()}


@pytest.mark.parametrize("occupant", [ASIDE_NAME + s for s in ("",) + ASIDE_SIDECARS])
def test_hc_fks_020_an_occupied_aside_name_refuses_and_touches_nothing(vault016, mig_log, occupant):
    path, _cfg = vault016
    _seed(path, ["P2"])
    _snap(path).write_bytes(b"not a database" * 100)
    path.with_name(occupant).write_bytes(b"an earlier damaged copy")
    before = _tree_shas(path.parent)

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    assert _tree_shas(path.parent) == before, "no file was added, changed or removed"
    assert _rev(path) == REV_016
    assert "alembic_version" in _tables(path)
    _assert_refusal_leaks_nothing(
        path, exc.value, mig_log, step_words=("aside-occupied",), error_class="_SnapshotInvalid"
    )


@pytest.mark.parametrize("fails_on", ["first-move", "main-file"])
def test_hc_fks_021_a_failed_move_refuses_and_keeps_the_damaged_snapshot(
    vault016, mig_log, monkeypatch, fails_on
):
    path, _cfg = vault016
    _seed(path, ["P2"])
    damaged = b"not a database" * 100
    _snap(path).write_bytes(damaged)
    path.with_name(SNAP_NAME + "-wal").write_bytes(b"damaged wal")
    sha_vault = _sha(path)
    real_replace = os.replace
    moves: list[str] = []

    def _replace(src, dst, *args, **kwargs):
        if Path(dst).name.startswith(ASIDE_NAME):
            moves.append(Path(dst).name)
            if fails_on == "first-move" or Path(dst).name == ASIDE_NAME:
                raise OSError(errno.EACCES, "locked", str(dst))
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(migrations.os, "replace", _replace)

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    assert moves, "the move was attempted"
    kept = [p for p in (_snap(path), path.with_name(ASIDE_NAME)) if p.exists() and p.read_bytes() == damaged]
    assert len(kept) == 1, "the damaged main file must still be readable at exactly one of the two names"
    assert _sha(path) == sha_vault and _rev(path) == REV_016
    assert not path.with_name(TMP_NAME).exists()
    _assert_refusal_leaks_nothing(
        path, exc.value, mig_log, step_words=("move-aside",), error_class="PermissionError"
    )


# --------------------------------------------------------------------------
# HC-FKS-008r/016r/019r, 022: review round 2 (relative vault path, verifier errors,
# purge order, the aside refusal over HTTP)
# --------------------------------------------------------------------------


@pytest.fixture
def vault016_rel(tmp_path, monkeypatch):
    """(RELATIVE vault path, alembic config) at 016. Local mode's app_data_path is
    the relative ``Path("data")``, so in local mode every vault path is relative
    (server mode's is the absolute parent of its database path); every other
    fixture here uses an absolute tmp_path and cannot see what that breaks."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    monkeypatch.chdir(tmp_path)
    path = Path("data/vaults/p/vault.db")
    path.parent.mkdir(parents=True)
    assert not path.is_absolute()
    cfg = _alembic_cfg(path)
    command.upgrade(cfg, REV_016)
    return path, cfg


def test_hc_fks_008r_relative_vault_two_failed_opens_keep_the_pristine_snapshot(vault016_rel):
    path, orphan_id = _vault_with_orphan_and_blocker(vault016_rel)
    snap = _snap(path)

    with pytest.raises(Exception) as first:
        migrations.run_profile_migration(path, KEY)
    assert not isinstance(first.value, migrations.ProfileMigrationRefused), "the upgrade failed, not the snapshot"
    before = _state(snap)

    with pytest.raises(Exception) as second:  # still blocked: the existing snapshot is verified again
        migrations.run_profile_migration(path, KEY)

    assert not isinstance(second.value, migrations.ProfileMigrationRefused), second.value
    assert _state(snap) == before, "a good snapshot must be kept, not moved aside and re-copied"
    assert _leftovers(path) == [], "nothing was moved aside"

    conn = _connect(path)
    try:
        conn.execute("DROP TABLE _alembic_tmp_care_plan_task")
        conn.commit()
    finally:
        conn.close()
    migrations.run_profile_migration(path, KEY)

    assert _rev(path) == PROFILE_HEAD
    assert _state(snap) == before and _leftovers(path) == []
    conn = _connect(snap)
    try:
        assert conn.execute("SELECT 1 FROM chunks WHERE id = ?", (orphan_id,)).fetchone()
    finally:
        conn.close()


def test_hc_fks_016r_relative_vault_a_failed_017_keeps_an_aged_snapshot_until_it_completes(
    vault016_rel, monkeypatch
):
    path, _orphan_id = _vault_with_orphan_and_blocker(vault016_rel)
    with pytest.raises(Exception):
        migrations.run_profile_migration(path, KEY)
    snap = _snap(path)
    _set_age(snap, MADE_AT)
    monkeypatch.setattr(migrations, "utcnow", lambda: MADE_AT + timedelta(days=31))
    before = _state(snap)

    with pytest.raises(Exception) as retry:
        migrations.run_profile_migration(path, KEY)

    assert not isinstance(retry.value, migrations.ProfileMigrationRefused), retry.value
    assert _state(snap) == before and _leftovers(path) == []
    conn = _connect(path)
    try:
        conn.execute("DROP TABLE _alembic_tmp_care_plan_task")
        conn.commit()
    finally:
        conn.close()
    migrations.run_profile_migration(path, KEY)
    assert _rev(path) == PROFILE_HEAD and _state(snap) == before

    migrations.run_profile_migration(path, KEY)
    assert not snap.exists() and _leftovers(path) == []


@pytest.mark.parametrize("damage", list(_DAMAGED))
def test_hc_fks_019r_relative_vault_a_corrupted_snapshot_is_moved_aside_and_a_new_one_taken(
    vault016_rel, mig_log, damage
):
    path, _cfg = vault016_rel
    _seed(path, ["P2"])
    sha_vault = _sha(path)
    planted = _plant_damaged_snapshot(path, _DAMAGED[damage](path))
    _apply_alembic_ini_logging()

    migrations.run_profile_migration(path, KEY)

    for name, data in planted.items():
        assert path.with_name(name.replace(SNAP_NAME, ASIDE_NAME, 1)).read_bytes() == data
    migrations._verify_snapshot(_snap(path), migrations._key_to_hex(KEY))
    assert _sha(_snap(path)) == sha_vault
    assert _rev(path) == PROFILE_HEAD
    events = [r.getMessage() for r in mig_log if r.levelno == logging.WARNING and "aside" in r.getMessage().lower()]
    assert len(events) == 1, events


@pytest.mark.parametrize(
    "error",
    [ValueError("a relative path"), RuntimeError("encryption required")],
    ids=["ValueError", "RuntimeError"],
)
def test_hc_fks_022_a_verifier_error_that_says_nothing_about_the_file_refuses_and_moves_nothing(
    vault016, mig_log, monkeypatch, error
):
    """Only a failed check (the verifier's own refusal, or a driver error whose
    code is on the damage list) means the snapshot is damaged. Anything else
    (here a bug) says nothing about the file, so the good snapshot must not be
    moved. An environment fault from the driver is HC-FKS-024..026."""
    path, _orphan_id = _vault_with_orphan_and_blocker(vault016)
    with pytest.raises(Exception):
        migrations.run_profile_migration(path, KEY)  # the failed 017 leaves a good snapshot
    before = _tree_shas(path.parent)
    real_verify = migrations._verify_snapshot

    def _verify(target, hex_key, read_only=False):
        if read_only:
            raise error
        return real_verify(target, hex_key, read_only=read_only)

    monkeypatch.setattr(migrations, "_verify_snapshot", _verify)
    mig_log.clear()

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    assert _tree_shas(path.parent) == before, "nothing was moved, added or removed"
    assert _leftovers(path) == []
    assert _rev(path) == REV_016
    _assert_refusal_leaks_nothing(
        path, exc.value, mig_log, step_words=("verify-existing",), error_class=type(error).__name__
    )


def test_hc_fks_023_a_database_error_from_the_verifier_counts_as_damage(vault016, monkeypatch):
    """The other side of HC-FKS-022: a driver error whose code is on the damage list
    (here the DatabaseError a garbage file raises, NOTADB) is damage and the file
    is moved aside. The code decides, not the class."""
    path, _cfg = vault016
    _seed(path, ["P2"])
    damaged = b"not a database" * 100
    _snap(path).write_bytes(damaged)
    seen: list[str] = []
    real_verify = migrations._verify_snapshot

    def _verify(target, hex_key, read_only=False):
        try:
            return real_verify(target, hex_key, read_only=read_only)
        except Exception as exc:
            seen.append(type(exc).__name__)
            raise

    monkeypatch.setattr(migrations, "_verify_snapshot", _verify)

    migrations.run_profile_migration(path, KEY)

    assert seen == ["DatabaseError"], seen
    assert path.with_name(ASIDE_NAME).read_bytes() == damaged
    assert _rev(path) == PROFILE_HEAD


# --------------------------------------------------------------------------
# HC-FKS-024..026: an environment fault is not damage (review round 3)
# --------------------------------------------------------------------------


def _require_proc_fd():
    if not os.path.isdir("/proc/self/fd"):
        pytest.skip("needs /proc/self/fd (Linux only)")


@contextlib.contextmanager
def _no_free_fds():
    """Every file descriptor this process may open is taken, so the next open()
    fails with EMFILE. Linux only: it counts the open descriptors through
    /proc/self/fd. Callers skip first (``_require_proc_fd``), before the migration
    runs, so this check never fires inside the migration's own handlers."""
    _require_proc_fd()
    resource = pytest.importorskip("resource")
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    held: list[int] = []
    resource.setrlimit(resource.RLIMIT_NOFILE, (len(os.listdir("/proc/self/fd")) + 4, hard))
    try:
        try:
            while True:
                held.append(os.open(os.devnull, os.O_RDONLY))
        except OSError:
            pass
        yield
    finally:
        for fd in held:
            os.close(fd)
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def _vault_with_good_snapshot(vault016):
    """A failed 017 leaves a good snapshot; returns (path, the tree's shas)."""
    path, _orphan_id = _vault_with_orphan_and_blocker(vault016)
    with pytest.raises(Exception):
        migrations.run_profile_migration(path, KEY)
    migrations._verify_snapshot(_snap(path), migrations._key_to_hex(KEY))
    return path, _tree_shas(path.parent)


def _assert_refused_nothing_moved(path, before, exc, mig_log, error_class):
    assert _tree_shas(path.parent) == before, "nothing was moved, added or removed"
    assert _leftovers(path) == []
    assert _rev(path) == REV_016
    _assert_refusal_leaks_nothing(
        path, exc.value, mig_log, step_words=("verify-existing",), error_class=error_class
    )


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root ignores file modes")
def test_hc_fks_024_an_unreadable_good_snapshot_refuses_and_is_not_moved_aside(vault016, mig_log):
    """Real chmod 000. The driver raises OperationalError "unable to open database
    file" (CANTOPEN). The snapshot is intact; moving it aside would let the next
    fault hit an occupied aside name with a second full copy on disk."""
    path, before = _vault_with_good_snapshot(vault016)
    mig_log.clear()
    os.chmod(_snap(path), 0)
    try:
        with pytest.raises(migrations.ProfileMigrationRefused) as exc:
            migrations.run_profile_migration(path, KEY)
    finally:
        os.chmod(_snap(path), 0o600)

    _assert_refused_nothing_moved(path, before, exc, mig_log, "OperationalError")


def test_hc_fks_025_a_snapshot_that_cannot_be_opened_for_lack_of_file_handles_is_not_moved_aside(
    vault016, mig_log, monkeypatch
):
    """Real descriptor exhaustion (RLIMIT_NOFILE) around the one read-only verify."""
    _require_proc_fd()  # here, not only in the helper: the helper runs inside the migration
    path, before = _vault_with_good_snapshot(vault016)
    real_verify = migrations._verify_snapshot

    def _verify(target, hex_key, read_only=False):
        if read_only:
            with _no_free_fds():
                return real_verify(target, hex_key, read_only=read_only)
        return real_verify(target, hex_key, read_only=read_only)

    monkeypatch.setattr(migrations, "_verify_snapshot", _verify)
    mig_log.clear()

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    _assert_refused_nothing_moved(path, before, exc, mig_log, "OperationalError")


def _driver_error(code):
    """The driver's own error class (the one ``_database_errors`` catches), with
    ``sqlite_errorcode`` set as the driver sets it, or left unset when ``code`` is None."""
    cls = get_sqlcipher_module().OperationalError if is_sqlcipher_available() else sqlite3.OperationalError
    error = cls("injected")
    if code is not None:
        error.sqlite_errorcode = code
    return error


# SQLite result codes: PERM 3, BUSY 5, LOCKED 6, IOERR 10, CANTOPEN 14 are the
# environment (IOERR: the disk failed to answer, which says nothing about the
# file); ERROR 1 (a page that fails its HMAC), CORRUPT 11 and NOTADB 26 are the
# file. Extended codes carry the primary code in the low byte.
@pytest.mark.parametrize(
    "code",
    [None, 3, 5, 6, 14, 5 | (1 << 8), 14 | (2 << 8), 8, 13, 10, 10 | (1 << 8)],
    ids=[
        "no-code", "PERM", "BUSY", "LOCKED", "CANTOPEN", "BUSY_RECOVERY", "CANTOPEN_ISDIR",
        "READONLY", "FULL", "IOERR", "IOERR_READ",
    ],
)
def test_hc_fks_026_a_driver_error_code_that_is_not_damage_refuses_and_moves_nothing(
    vault016, mig_log, monkeypatch, code
):
    path, before = _vault_with_good_snapshot(vault016)
    real_verify = migrations._verify_snapshot

    def _verify(target, hex_key, read_only=False):
        if read_only:
            raise _driver_error(code)
        return real_verify(target, hex_key, read_only=read_only)

    monkeypatch.setattr(migrations, "_verify_snapshot", _verify)
    mig_log.clear()

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    _assert_refused_nothing_moved(path, before, exc, mig_log, "OperationalError")


@pytest.mark.parametrize(
    "code", [1, 11, 26, 11 | (1 << 8)],
    ids=["ERROR", "CORRUPT", "NOTADB", "CORRUPT_VTAB"],
)
def test_hc_fks_026_a_driver_error_code_that_is_damage_moves_the_snapshot_aside(
    vault016, monkeypatch, code
):
    """ERROR, CORRUPT and NOTADB name the file as damaged, so it is moved aside.
    IOERR is not here: it is on the refuse list above."""
    path, _cfg = vault016
    _seed(path, ["P2"])
    damaged = b"stands in for a snapshot the driver cannot read" * 50
    _snap(path).write_bytes(damaged)
    real_verify = migrations._verify_snapshot

    def _verify(target, hex_key, read_only=False):
        if read_only:
            raise _driver_error(code)
        return real_verify(target, hex_key, read_only=read_only)

    monkeypatch.setattr(migrations, "_verify_snapshot", _verify)

    migrations.run_profile_migration(path, KEY)

    assert path.with_name(ASIDE_NAME).read_bytes() == damaged
    assert _rev(path) == PROFILE_HEAD


def test_hc_fks_018c_the_age_purge_removes_sidecars_first_and_the_main_file_last(tmp_path, monkeypatch, mig_log):
    """If a sidecar will not go, the main file stays, so the next open still finds
    it, ages it and tries again. Main first would leave a sidecar nothing ages."""
    vault = _head_vault(tmp_path, monkeypatch)
    now = MADE_AT + timedelta(days=60)
    names = [SNAP_NAME, SNAP_NAME + "-wal", ASIDE_NAME, ASIDE_NAME + "-journal"]
    for name in names:
        vault.with_name(name).write_bytes(b"planted " + name.encode())
        _set_age(vault.with_name(name), now - timedelta(days=45))
    monkeypatch.setattr(migrations, "utcnow", lambda: now)
    real_unlink = Path.unlink
    locked = {SNAP_NAME + "-wal", ASIDE_NAME + "-journal"}

    def _locked(self, *args, **kwargs):
        if self.name in locked:
            raise PermissionError(errno.EACCES, "locked", str(self))
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _locked)
    migrations.run_profile_migration(vault, KEY)  # must not raise

    assert _snap(vault).exists() and vault.with_name(ASIDE_NAME).exists(), (
        "a main file goes last: its sidecar could not be removed, so it stays"
    )
    monkeypatch.setattr(Path, "unlink", real_unlink)
    migrations.run_profile_migration(vault, KEY)

    assert _leftovers(vault) == [], "the next open finished the purge"


def test_hc_fks_018d_sidecars_with_no_main_file_are_purged_once_017_is_confirmed(tmp_path, monkeypatch):
    vault = _head_vault(tmp_path, monkeypatch)
    orphans = [SNAP_NAME + "-wal", SNAP_NAME + "-shm", ASIDE_NAME + "-journal"]
    for name in orphans:
        vault.with_name(name).write_bytes(b"a sidecar with no main file")  # young: mtime is now
    keeper = vault.with_name(SNAP_NAME + ".keep")  # not one of the names: must stay
    keeper.write_bytes(b"not ours")

    migrations.run_profile_migration(vault, KEY)

    assert [p.name for p in vault.parent.glob("vault.pre017*")] == [keeper.name]


@pytest.mark.asyncio
async def test_hc_fks_012b_login_with_the_aside_occupied_is_the_fixed_500_with_no_token(
    tmp_path, monkeypatch
):
    """The state with no in-app exit: nothing is opened, so no token exists, and
    the refusal says nothing about where anything is."""
    from core.profile_database import get_profile_db_manager

    async with _planted_vault_client(tmp_path, monkeypatch, ["P2"]) as ctx:
        folder = ctx.vault.parent
        _snap(ctx.vault).write_bytes(b"not a database" * 100)
        (folder / (ASIDE_NAME + "-wal")).write_bytes(b"an earlier damaged copy")
        before = _tree_shas(folder)
        login = {"profile_id": ctx.pid, "password": _PASSWORD}

        refused = ctx.client.post("/profiles/login", json=login)

        assert refused.status_code == 500
        assert refused.json() == {"detail": "Failed to open profile database"}
        assert str(tmp_path) not in refused.text and ASIDE_NAME not in refused.text
        assert "set-cookie" not in refused.headers
        assert ctx.pid not in get_profile_db_manager()._connections, "no cached connection"
        assert _tree_shas(folder) == before, "nothing was touched"
        assert _rev(ctx.vault, ctx.key) == REV_016
        assert await ctx.rows() == []


@pytest.mark.asyncio
async def test_hc_fks_012c_relative_app_data_path_two_failed_logins_keep_the_snapshot(
    tmp_path, monkeypatch
):
    """Local mode's default app_data_path is relative. Two failed 017 logins must
    not move the good snapshot aside, and a login after the cause clears must open."""
    async with _planted_vault_client(tmp_path, monkeypatch, ["P2"], relative=True) as ctx:
        folder = ctx.vault.parent
        conn = _connect(ctx.vault, ctx.key)
        try:
            conn.execute("CREATE TABLE _alembic_tmp_care_plan_task (x INTEGER)")
            conn.commit()
        finally:
            conn.close()
        login = {"profile_id": ctx.pid, "password": _PASSWORD}

        first = ctx.client.post("/profiles/login", json=login)
        assert first.status_code == 500
        snap = _snap(ctx.vault)
        before = _state(snap)
        second = ctx.client.post("/profiles/login", json=login)

        assert second.status_code == 500
        assert second.json() == {"detail": "Failed to open profile database"}
        assert _state(snap) == before, "the good snapshot is kept"
        assert _leftovers(ctx.vault) == [], "nothing moved aside"

        conn = _connect(ctx.vault, ctx.key)
        try:
            conn.execute("DROP TABLE _alembic_tmp_care_plan_task")
            conn.commit()
        finally:
            conn.close()
        ok = ctx.client.post("/profiles/login", json=login)

        assert ok.status_code == 200, ok.text
        assert _rev(ctx.vault, ctx.key) == PROFILE_HEAD
        assert _state(snap) == before and sorted(p.name for p in folder.glob("vault.pre017*")) == [SNAP_NAME]


# --------------------------------------------------------------------------
# HC-FKB: an unversioned vault is stamped at the revision it matches (P6-STAMP)
# --------------------------------------------------------------------------

REV_010 = "010_entity_source_spans"


@pytest.fixture(scope="module")
def reference_fingerprints():
    """The throwaway-vault walk, run once for the module (several seconds)."""
    started = time.perf_counter()
    refs = migrations._reference_fingerprints()
    refs_seconds = time.perf_counter() - started
    return refs, refs_seconds


@pytest.fixture
def fast_references(monkeypatch, reference_fingerprints):
    """Reuse the module's walk instead of repeating it in every test."""
    refs, _seconds = reference_fingerprints
    monkeypatch.setattr(migrations, "_reference_fingerprints", lambda: list(refs))


@pytest.fixture
def stamps(monkeypatch):
    """Revisions passed to ``command.stamp`` (the real stamp still runs)."""
    seen: list[str] = []
    real = command.stamp

    def _spy(config, revision, *args, **kwargs):
        seen.append(revision)
        return real(config, revision, *args, **kwargs)

    monkeypatch.setattr(command, "stamp", _spy)
    return seen


def _unversioned(path: Path, key: bytes = KEY) -> None:
    """Drop ``alembic_version``: what is left is a vault Alembic never saw."""
    conn = _connect(path, key)
    try:
        conn.execute("DROP TABLE alembic_version")
        conn.commit()
    finally:
        conn.close()


def _tables(path: Path, key: bytes = KEY) -> set[str]:
    conn = _connect(path, key)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def test_hc_fkb_001_every_revision_has_its_own_fingerprint(reference_fingerprints):
    refs, seconds = reference_fingerprints
    script = ScriptDirectory.from_config(migrations._get_alembic_config("profile"))
    revisions = [r.revision for r in script.walk_revisions()]

    assert [rev for rev, _fp in refs] == revisions, "newest first, one per revision"
    assert len(revisions) >= 17
    assert len({fp for _rev, fp in refs}) == len(revisions), "two revisions share a schema"
    # 016 and 017 differ only in foreign-key actions: columns alone would tie
    by_rev = dict(refs)
    assert by_rev[REV_016] != by_rev["017_fk_cascade_alignment"]
    print(f"throwaway walk over {len(revisions)} revisions: {seconds:.2f}s")


def _plant_older_orphans(path: Path, *, with_care_task: bool) -> dict[str, int]:
    """Orphans that exist in every revision from 004 on; returns the expected counts."""
    conn = _connect(path)
    try:
        _insert(conn, "documents", id="D1")
        _insert(conn, "chunks", id="OC", doc_id="MISSING")  # P2
        _insert(conn, "embeddings", id="OE", chunk_id="OC")  # P3 once OC is gone
        _insert(conn, "medications", id="M1")
        _insert(conn, "doses_taken", id="OD", medication_id="M1", schedule_id="MISSING")  # P8
        _insert(conn, "document_category", id="OK", doc_id="MISSING", category="visit_notes")  # P14
        expected = {"P2": 1, "P3": 1, "P8": 1, "P14": 1}
        if with_care_task:
            _insert(conn, "care_plan_task", id="OT", title="t", source_document_id="MISSING")  # P16
            expected["P16"] = 1
        conn.commit()
        return expected
    finally:
        conn.close()


@pytest.mark.parametrize(
    "revision,real_walk",
    [(REV_016, True), (REV_010, False)],
    ids=["016", "010"],
)
def test_hc_fkb_002_unversioned_vault_is_stamped_where_it_is_then_upgraded(
    tmp_path, monkeypatch, stamps, revision, real_walk, request
):
    if not real_walk:
        request.getfixturevalue("fast_references")
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), revision)
    expected = _plant_older_orphans(path, with_care_task=revision == REV_016)
    _unversioned(path)
    sha_before = _sha(path)

    counts = migrations.run_profile_migration(path, KEY)

    assert stamps == [revision], "stamped where the schema is, not at head"
    assert counts == expected
    assert _rev(path) == PROFILE_HEAD
    conn = _connect(path)
    try:
        assert _fk_actions(conn, "document_category")["doc_id"] == "CASCADE"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("SELECT count(*) FROM chunks").fetchone()[0] == 0  # OC deleted
        # P8: the dose is kept, its link cleared
        assert conn.execute("SELECT schedule_id FROM doses_taken WHERE id='OD'").fetchone()[0] is None
    finally:
        conn.close()
    # the snapshot is the vault as it was: orphans in, and no alembic_version yet
    assert _sha(_snap(path)) == sha_before
    assert "alembic_version" not in _tables(_snap(path))
    assert _leftovers(path) == []


def test_hc_fkb_003_unversioned_vault_already_at_017_is_stamped_only(
    tmp_path, monkeypatch, stamps, fast_references
):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), "head")
    conn = _connect(path)
    try:
        _insert(conn, "chunks", id="OC", doc_id="MISSING")  # an orphan nobody cleans now
        conn.commit()
    finally:
        conn.close()
    _unversioned(path)

    counts = migrations.run_profile_migration(path, KEY)

    assert stamps == [PROFILE_HEAD]
    assert counts == {}
    assert _rev(path) == PROFILE_HEAD
    assert list(path.parent.glob("vault.pre017*")) == [], "no snapshot: 017 is not pending"
    conn = _connect(path)
    try:
        assert conn.execute("SELECT count(*) FROM chunks WHERE id='OC'").fetchone()[0] == 1, (
            "stamp only: the 017 cleanup must not run"
        )
    finally:
        conn.close()


def test_hc_fkb_004_a_schema_that_matches_nothing_is_refused_untouched(
    tmp_path, monkeypatch, stamps, fast_references, mig_log
):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_016)
    conn = _connect(path)
    try:
        conn.execute("ALTER TABLE documents ADD COLUMN stray_column TEXT")
        conn.commit()
    finally:
        conn.close()
    _unversioned(path)
    sha_before = _sha(path)

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    assert _sha(path) == sha_before
    assert "alembic_version" not in _tables(path)
    assert stamps == []
    assert list(path.parent.glob("vault.pre017*")) == []
    errors = [r.getMessage() for r in mig_log if r.levelno >= logging.ERROR]
    assert errors == ["Profile migration refused: the schema of an unversioned vault matches no known revision"]
    for text in [str(exc.value)] + errors:
        assert str(path.parent) not in text and KEY.hex() not in text.lower()


def test_hc_fkb_005_a_refused_snapshot_leaves_no_alembic_version(
    tmp_path, monkeypatch, stamps, fast_references
):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_016)
    _plant_older_orphans(path, with_care_task=True)
    _unversioned(path)
    sha_before = _sha(path)
    monkeypatch.setattr(migrations.shutil, "copy2", _enospc)

    with pytest.raises(migrations.ProfileMigrationRefused):
        migrations.run_profile_migration(path, KEY)

    assert _sha(path) == sha_before
    assert "alembic_version" not in _tables(path), "stamp must come after the snapshot"
    assert stamps == []
    assert list(path.parent.glob("vault.pre017*")) == []


def test_hc_fkb_007_a_failing_reference_walk_refuses_before_any_write(
    tmp_path, monkeypatch, stamps, mig_log
):
    """If the throwaway walk itself fails (disk, SQLCipher), the vault is not
    guessed at: refuse with the same exception, nothing stamped, no path in the
    text."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_016)
    _unversioned(path)
    sha_before = _sha(path)

    def _boom():
        raise OSError(errno.ENOSPC, "No space left on device", str(path))

    monkeypatch.setattr(migrations, "_reference_fingerprints", _boom)

    with pytest.raises(migrations.ProfileMigrationRefused) as exc:
        migrations.run_profile_migration(path, KEY)

    assert _sha(path) == sha_before
    assert stamps == []
    assert "alembic_version" not in _tables(path)
    assert list(path.parent.glob("vault.pre017*")) == []
    _assert_refusal_leaks_nothing(
        path, exc.value, mig_log, step_words=("build-references",), error_class="OSError"
    )


def test_hc_fkb_008_the_runtime_search_index_is_not_part_of_the_schema_match(
    tmp_path, monkeypatch, stamps, fast_references
):
    """modules/search.py creates search_records and its FTS5 mirror at run time
    ("derived, rebuildable, no migration"). A real vault that has used search must
    still match its revision, or a login after losing alembic_version refuses."""
    from modules import search as search_module

    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_016)
    conn = _connect(path)
    try:
        conn.execute(search_module._CREATE_RECORDS_SQL)
        conn.execute(search_module._CREATE_FTS_SQL)
        conn.commit()
        extra = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'search_records%'")}
    finally:
        conn.close()
    assert {"search_records", "search_records_fts"} <= extra, extra
    _unversioned(path)

    migrations.run_profile_migration(path, KEY)

    assert stamps == [REV_016]
    assert _rev(path) == PROFILE_HEAD
    assert {"search_records", "search_records_fts"} <= _tables(path), "the index itself is left alone"


def test_hc_fkb_008b_any_other_extra_table_still_refuses(
    tmp_path, monkeypatch, stamps, fast_references
):
    """The search carve-out is by name, not a general tolerance for extra tables."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_016)
    conn = _connect(path)
    try:
        conn.execute("CREATE TABLE search_records_other (x INTEGER)")
        conn.commit()
    finally:
        conn.close()
    _unversioned(path)

    with pytest.raises(migrations.ProfileMigrationRefused):
        migrations.run_profile_migration(path, KEY)
    assert stamps == []


# --------------------------------------------------------------------------
# HC-FKB-009..012: any user table makes an unversioned file non-empty
# --------------------------------------------------------------------------

# Tables that profile revisions create but the old 12-table baseline list did not
# name. A file holding only one of them used to count as empty and was written to.
SINGLE_TABLES = (
    "badge_definition", "care_plan_task", "chat_sessions", "chat_turns",
    "document_category", "document_entity", "donated_records", "donation_consents",
    "earned_badge", "memory_items", "pinboard", "pinboard_item", "response_feedback",
)


def _file_with_tables(path: Path, tables, *, rowless_alembic_version: bool = False) -> None:
    """A vault file holding only ``tables``, one row each (and, optionally, an
    ``alembic_version`` table with no row)."""
    conn = _connect(path)
    try:
        if rowless_alembic_version:
            conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        for name in tables:
            conn.execute(f'CREATE TABLE "{name}" (id TEXT PRIMARY KEY)')
            conn.execute(f'INSERT INTO "{name}" VALUES (?)', ("row-1",))
        conn.commit()
    finally:
        conn.close()


def _version_rows(path: Path) -> int:
    conn = _connect(path)
    try:
        return conn.execute("SELECT count(*) FROM alembic_version").fetchone()[0]
    finally:
        conn.close()


def _assert_refused_and_untouched(path, stamps, *, before_sha, before_tables, rowless: bool = False):
    assert _sha(path) == before_sha, "a refused file must not be touched"
    assert _tables(path) == before_tables, "no table was added"
    if rowless:
        assert "alembic_version" in _tables(path) and _version_rows(path) == 0
    else:
        assert "alembic_version" not in _tables(path)
    assert stamps == []
    assert list(path.parent.glob("vault.pre017*")) == []


# The 12 tables the old baseline check named (core/migrations.py at 2d470854).
OLD_TWELVE = {
    "documents", "observations", "chunks", "embeddings", "lab_interpretations",
    "panel_interpretations", "medications", "medication_schedules", "doses_taken",
    "adherence_patterns", "reminder_logs", "user_model_settings",
}


def test_hc_fkb_009_the_single_table_list_is_every_table_the_old_check_missed(tmp_path, monkeypatch):
    """Read from a real vault built at 017_fk_cascade_alignment, not at head: a
    table a later revision adds is not a table this fix has to name, and must not
    turn this test red."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    vault = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(vault), "017_fk_cascade_alignment")
    missed = {
        t for t in _tables(vault)
        if t != "alembic_version" and not migrations._is_runtime_search_table(t)
    } - OLD_TWELVE
    assert OLD_TWELVE <= _tables(vault), "the old list names real tables"
    assert len(SINGLE_TABLES) == 13 and len(set(SINGLE_TABLES)) == 13
    assert set(SINGLE_TABLES) == missed


@pytest.mark.parametrize("table", SINGLE_TABLES)
def test_hc_fkb_009_a_file_with_one_unlisted_table_is_refused_untouched(
    tmp_path, monkeypatch, stamps, fast_references, table
):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    _file_with_tables(path, [table])
    sha_before, tables_before = _sha(path), _tables(path)

    with pytest.raises(migrations.ProfileMigrationRefused):
        migrations.run_profile_migration(path, KEY)

    _assert_refused_and_untouched(path, stamps, before_sha=sha_before, before_tables=tables_before)
    assert tables_before == {table}


def test_hc_fkb_010_a_file_with_two_unlisted_tables_is_refused_untouched(
    tmp_path, monkeypatch, stamps, fast_references
):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    _file_with_tables(path, ["pinboard", "pinboard_item"])
    sha_before, tables_before = _sha(path), _tables(path)

    with pytest.raises(migrations.ProfileMigrationRefused):
        migrations.run_profile_migration(path, KEY)

    _assert_refused_and_untouched(path, stamps, before_sha=sha_before, before_tables=tables_before)


def test_hc_fkb_011_a_rowless_alembic_version_with_a_user_table_is_unversioned(
    tmp_path, monkeypatch, stamps, fast_references
):
    """``alembic_version`` with no row has no revision, so the file is unversioned
    and goes through the schema match like any other. It used to skip the match
    and be upgraded in place."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    _file_with_tables(path, ["pinboard"], rowless_alembic_version=True)
    sha_before, tables_before = _sha(path), _tables(path)

    with pytest.raises(migrations.ProfileMigrationRefused):
        migrations.run_profile_migration(path, KEY)

    _assert_refused_and_untouched(
        path, stamps, before_sha=sha_before, before_tables=tables_before, rowless=True
    )


def test_hc_fkb_011b_a_rowless_alembic_version_on_a_matching_vault_is_stamped(
    tmp_path, monkeypatch, stamps, fast_references
):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_016)
    _plant_older_orphans(path, with_care_task=True)
    conn = _connect(path)
    try:
        conn.execute("DELETE FROM alembic_version")
        conn.commit()
    finally:
        conn.close()
    assert _version_rows(path) == 0
    sha_before = _sha(path)

    migrations.run_profile_migration(path, KEY)

    assert stamps == [REV_016], "matched like any unversioned vault, stamped where it is"
    assert _rev(path) == PROFILE_HEAD
    assert _sha(_snap(path)) == sha_before, "and snapshotted before 017 ran"


def _absent(path: Path) -> None:
    assert not path.exists()


def _zero_bytes(path: Path) -> None:
    path.write_bytes(b"")


def _rowless_only(path: Path) -> None:
    _file_with_tables(path, [], rowless_alembic_version=True)


def _search_only(path: Path) -> None:
    """Only the derived search index: modules/search.py makes it at run time."""
    from modules import search as search_module

    conn = _connect(path)
    try:
        conn.execute(search_module._CREATE_RECORDS_SQL)
        conn.execute(search_module._CREATE_FTS_SQL)
        conn.commit()
    finally:
        conn.close()


@pytest.mark.parametrize(
    "build", [_absent, _zero_bytes, _rowless_only, _search_only],
    ids=["absent", "zero-bytes", "rowless-alembic-version-only", "search-index-only"],
)
def test_hc_fkb_012_a_file_with_no_user_table_is_new_and_reaches_head_without_a_snapshot(
    tmp_path, monkeypatch, stamps, build
):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    build(path)
    search_before = {t for t in _tables(path) if t.startswith("search_records")} if path.exists() else set()

    migrations.run_profile_migration(path, KEY)

    assert _rev(path) == PROFILE_HEAD
    assert stamps == [], "created through the upgrade, not stamped"
    assert list(path.parent.glob("vault.pre017*")) == [], "no snapshot of an empty file"
    assert {t for t in _tables(path) if t.startswith("search_records")} == search_before
    assert {"documents", "chunks", "care_plan_task"} <= _tables(path)
