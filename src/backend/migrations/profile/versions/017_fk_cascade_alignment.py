"""Align four foreign-key actions with live code paths and clean orphans first.

SQL-FK-001 (C-P6): SQLite ignores foreign keys unless ``PRAGMA foreign_keys=ON``
is set on each connection, and it never was. This revision exists so that the
pragma can be switched on over vaults written without it.

1. ``upgrade()`` first removes orphan rows (a child whose parent is gone) so the
   pragma does not turn a historic leftover into a failing delete. Only child
   rows are ever deleted. ``care_plan_task`` rows are never deleted: P16/P17
   null the dangling link instead (owner decision P6-CLEANUP-SETNULL).
2. It then rebuilds ``document_category`` and ``document_entity`` (doc_id ->
   CASCADE) and ``care_plan_task`` (source_document_id and source_entity_id ->
   SET NULL). SQLite cannot ALTER a constraint, and the original constraints are
   unnamed, so each table is rebuilt from a complete ``copy_from`` definition.

The pragma itself is runtime, not DDL, and is not set here: migration engines
stay pragma-OFF (batch rebuilds require it).

Downgrade rebuilds the three tables back to NO ACTION. It does NOT restore the
orphan rows that ``upgrade()`` deleted or the links it nulled; only a backup
taken before the upgrade can.

Revision ID: 017_fk_cascade_alignment
Revises: 016_strict_safety_mode
Create Date: 2026-11-02
"""
import logging
from typing import NamedTuple, Optional, Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "017_fk_cascade_alignment"
down_revision: Union[str, None] = "016_strict_safety_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Inherits INFO from alembic.ini's [logger_alembic]. Logs counts only: never row
# ids, column values, table contents, profile names or the vault path.
_log = logging.getLogger("alembic.fk_cleanup")


class _Check(NamedTuple):
    check_id: str
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str


# Frozen copy of core.fk_audit.PROFILE_CHECKS (P1-P18) as of this revision. It is
# deliberately not imported: migrations never import app code, and a later check
# row for a table that does not exist at 017 would break this revision on an old
# vault. HC-FKC-007 pins the parity. Order matters: P16 runs before P17.
_CLEANUP_CHECKS: tuple[_Check, ...] = (
    _Check("P1", "observations", "doc_id", "documents", "id"),
    _Check("P2", "chunks", "doc_id", "documents", "id"),
    _Check("P3", "embeddings", "chunk_id", "chunks", "id"),
    _Check("P4", "lab_interpretations", "observation_id", "observations", "id"),
    _Check("P5", "chat_turns", "session_id", "chat_sessions", "id"),
    _Check("P6", "medication_schedules", "medication_id", "medications", "id"),
    _Check("P7", "doses_taken", "medication_id", "medications", "id"),
    _Check("P8", "doses_taken", "schedule_id", "medication_schedules", "id"),
    _Check("P9", "adherence_patterns", "medication_id", "medications", "id"),
    _Check("P10", "adherence_patterns", "schedule_id", "medication_schedules", "id"),
    _Check("P11", "reminder_logs", "medication_id", "medications", "id"),
    _Check("P12", "reminder_logs", "schedule_id", "medication_schedules", "id"),
    _Check("P13", "pinboard_item", "pinboard_id", "pinboard", "id"),
    _Check("P14", "document_category", "doc_id", "documents", "id"),
    _Check("P15", "document_entity", "doc_id", "documents", "id"),
    _Check("P16", "care_plan_task", "source_document_id", "documents", "id"),
    _Check("P17", "care_plan_task", "source_entity_id", "document_entity", "id"),
    _Check("P18", "earned_badge", "badge_id", "badge_definition", "id"),
)

# P16/P17 repair instead of delete. P16 clears the quote as well, exactly as
# api/documents.py delete_document does; P17 keeps document id and quote.
_REPAIR_SET = {
    "P16": "source_document_id = NULL, source_entity_id = NULL, source_quote = NULL",
    "P17": "source_entity_id = NULL",
}


def _orphan_ids_sql(c: _Check) -> str:
    """Same predicate as core.fk_audit.orphan_sql, minus the ORDER BY."""
    return (
        f"SELECT c.id FROM {c.child_table} c "
        f"LEFT JOIN {c.parent_table} p ON c.{c.child_column} = p.{c.parent_column} "
        f"WHERE c.{c.child_column} IS NOT NULL AND p.{c.parent_column} IS NULL"
    )


def _fix_sql(c: _Check) -> str:
    """The statement for one check. Its only target is ``c.child_table``."""
    orphans = _orphan_ids_sql(c)
    if c.check_id in _REPAIR_SET:
        return (
            f"UPDATE {c.child_table} SET {_REPAIR_SET[c.check_id]} "
            f"WHERE id IN ({orphans})"
        )
    return f"DELETE FROM {c.child_table} WHERE id IN ({orphans})"


def _cleanup_orphans(bind) -> dict[str, int]:
    """Repeat full passes until one finds nothing; return per-check totals.

    Deleting an orphan can orphan its own children (chunk then embedding), hence
    the repeat. The pragma is OFF here, so nothing cascades by itself. Alembic
    reports non-transactional DDL, but measured on SQLCipher a failure in any of
    the three rebuilds rolled the whole upgrade back (orphans still present,
    revision 016). Do not rely on that: the cleanup is idempotent, so a re-run
    after a partial failure finds fewer or no orphans and still converges.
    """
    counts: dict[str, int] = {}
    for _ in range(len(_CLEANUP_CHECKS) + 1):
        pass_total = 0
        for check in _CLEANUP_CHECKS:
            n = bind.execute(sa.text(_fix_sql(check))).rowcount or 0
            if n:
                counts[check.check_id] = counts.get(check.check_id, 0) + n
                pass_total += n
        if pass_total == 0:
            return counts
    raise RuntimeError("fk orphan cleanup did not converge")


def _log_counts(counts: dict[str, int]) -> None:
    for check in _CLEANUP_CHECKS:  # stable order
        n = counts.get(check.check_id)
        if n:
            word = "repaired" if check.check_id in _REPAIR_SET else "removed"
            _log.warning("fk_orphan_cleanup check=%s %s=%d", check.check_id, word, n)
    total = sum(counts.values())
    level = logging.WARNING if total > 0 else logging.INFO
    _log.log(level, "fk_orphan_cleanup total=%d checks=%d", total, len(counts))


# --- table definitions, verbatim from 004 / 010 / 011 -----------------------
# Each copy_from table must list every column, index and server_default of the
# original, or the rebuild silently drops it. HC-FKM-002 compares PRAGMA
# table_info and index_list before and after.


def _document_category(ondelete: Optional[str]) -> sa.Table:
    md = sa.MetaData()
    sa.Table("documents", md, sa.Column("id", sa.Text(), primary_key=True))
    t = sa.Table(
        "document_category",
        md,
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("doc_id", sa.Text(), sa.ForeignKey("documents.id", ondelete=ondelete), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("classified_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    sa.Index("idx_doc_category_doc_id", t.c.doc_id)
    return t


def _document_entity(ondelete: Optional[str]) -> sa.Table:
    md = sa.MetaData()
    sa.Table("documents", md, sa.Column("id", sa.Text(), primary_key=True))
    t = sa.Table(
        "document_entity",
        md,
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("doc_id", sa.Text(), sa.ForeignKey("documents.id", ondelete=ondelete), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_bbox_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        # 010 (added after created_at, so they sit last in the live table)
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("verified_by_user", sa.Boolean(), nullable=True),
        sa.Column("extraction_version", sa.Text(), nullable=True),
    )
    sa.Index("idx_doc_entity_doc_id", t.c.doc_id)
    sa.Index("idx_doc_entity_type", t.c.entity_type)
    return t


def _care_plan_task(ondelete: Optional[str]) -> sa.Table:
    md = sa.MetaData()
    sa.Table("documents", md, sa.Column("id", sa.Text(), primary_key=True))
    sa.Table("document_entity", md, sa.Column("id", sa.Text(), primary_key=True))
    t = sa.Table(
        "care_plan_task",
        md,
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("due_date_confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("source_document_id", sa.Text(), sa.ForeignKey("documents.id", ondelete=ondelete), nullable=True),
        sa.Column("source_entity_id", sa.Text(), sa.ForeignKey("document_entity.id", ondelete=ondelete), nullable=True),
        sa.Column("source_quote", sa.Text(), nullable=True),
        sa.Column("user_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    sa.Index("idx_care_plan_task_status", t.c.status)
    sa.Index("idx_care_plan_task_source_doc", t.c.source_document_id)
    sa.Index("idx_care_plan_task_source_entity", t.c.source_entity_id)
    return t


def _rebuild(table: sa.Table) -> None:
    # recreate="always": with no column operations "auto" would skip the rebuild.
    with op.batch_alter_table(table.name, copy_from=table, recreate="always"):
        pass


def _rebuild_all(cascade: Optional[str], set_null: Optional[str]) -> None:
    # document_entity before care_plan_task, which references it.
    _rebuild(_document_category(cascade))
    _rebuild(_document_entity(cascade))
    _rebuild(_care_plan_task(set_null))


def upgrade() -> None:
    counts = _cleanup_orphans(op.get_bind())
    _rebuild_all("CASCADE", "SET NULL")
    # Only after the rebuilds succeed: a failed upgrade must not log removed=<n>
    # or hand counts to the audit-row writer for rows that are still there.
    _log_counts(counts)
    # Read by core.migrations.run_profile_migration for the master audit row.
    context.config.attributes["fk_cleanup_counts"] = counts


def downgrade() -> None:
    """Back to NO ACTION. Orphans deleted (and links nulled) by upgrade stay gone."""
    _rebuild_all(None, None)
