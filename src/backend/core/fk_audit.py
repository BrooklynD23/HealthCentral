"""Report-only orphan detection across declared and logical FKs (SQL-FK-001).

The pragma is per-connection and was never set, so vaults can already hold
dangling children. This module finds them; nothing here deletes.
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SAMPLE_LIMIT = 5


@dataclass(frozen=True)
class FkCheck:
    check_id: str  # M1/M2, P1..P18, L1..L5
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str = "id"
    scope: str = "profile"  # "master" | "profile"
    enforced: bool = True  # False = logical relation, no DB constraint
    where: Optional[str] = None  # extra child-side predicate (polymorphic)


@dataclass(frozen=True)
class OrphanFinding:
    check_id: str
    child_table: str
    child_column: str
    parent_table: str
    enforced: bool
    count: int
    sample_ids: list[str]


MASTER_CHECKS: list[FkCheck] = [
    FkCheck("M1", "audit_logs", "profile_id", "profiles", scope="master"),
    FkCheck("M2", "backup_schedules", "profile_id", "profiles", scope="master"),
]

PROFILE_CHECKS: list[FkCheck] = [
    FkCheck("P1", "observations", "doc_id", "documents"),
    FkCheck("P2", "chunks", "doc_id", "documents"),
    FkCheck("P3", "embeddings", "chunk_id", "chunks"),
    FkCheck("P4", "lab_interpretations", "observation_id", "observations"),
    FkCheck("P5", "chat_turns", "session_id", "chat_sessions"),
    FkCheck("P6", "medication_schedules", "medication_id", "medications"),
    FkCheck("P7", "doses_taken", "medication_id", "medications"),
    FkCheck("P8", "doses_taken", "schedule_id", "medication_schedules"),
    FkCheck("P9", "adherence_patterns", "medication_id", "medications"),
    FkCheck("P10", "adherence_patterns", "schedule_id", "medication_schedules"),
    FkCheck("P11", "reminder_logs", "medication_id", "medications"),
    FkCheck("P12", "reminder_logs", "schedule_id", "medication_schedules"),
    FkCheck("P13", "pinboard_item", "pinboard_id", "pinboard"),
    FkCheck("P14", "document_category", "doc_id", "documents"),
    FkCheck("P15", "document_entity", "doc_id", "documents"),
    FkCheck("P16", "care_plan_task", "source_document_id", "documents"),
    FkCheck("P17", "care_plan_task", "source_entity_id", "document_entity"),
    FkCheck("P18", "earned_badge", "badge_id", "badge_definition"),
]

# No DB constraint exists for these; a hit is a data smell, never a migration target.
LOGICAL_CHECKS: list[FkCheck] = [
    FkCheck("L1", "response_feedback", "session_id", "chat_sessions", enforced=False),
    FkCheck("L2", "response_feedback", "turn_id", "chat_turns", enforced=False),
    FkCheck("L3", "pinboard_item", "item_id", "documents", enforced=False,
            where="item_type = 'document'"),
    FkCheck("L4", "pinboard_item", "item_id", "observations", enforced=False,
            where="item_type = 'observation'"),
    FkCheck("L5", "pinboard_item", "item_id", "care_plan_task", enforced=False,
            where="item_type = 'care_task'"),
]


def orphan_sql(c: FkCheck) -> str:
    """SELECT of orphan child ids. Identifiers come from the constant tables above."""
    extra = f" AND c.{c.where}" if c.where else ""
    return (
        f"SELECT c.id FROM {c.child_table} c "
        f"LEFT JOIN {c.parent_table} p ON c.{c.child_column} = p.{c.parent_column} "
        f"WHERE c.{c.child_column} IS NOT NULL AND p.{c.parent_column} IS NULL{extra} "
        f"ORDER BY c.id"
    )


def _finding(c: FkCheck, ids: list) -> Optional[OrphanFinding]:
    if not ids:
        return None
    return OrphanFinding(
        c.check_id, c.child_table, c.child_column, c.parent_table, c.enforced,
        len(ids), [str(i) for i in ids[:SAMPLE_LIMIT]],
    )


def find_orphans_dbapi(conn, checks: list[FkCheck]) -> list[OrphanFinding]:
    """Run checks on a raw DBAPI connection (sqlite3 / sqlcipher). Read-only."""
    out = []
    for c in checks:
        f = _finding(c, [r[0] for r in conn.execute(orphan_sql(c)).fetchall()])
        if f:
            out.append(f)
    return out


async def find_orphans(session: AsyncSession, checks: list[FkCheck]) -> list[OrphanFinding]:
    """Run checks through an AsyncSession. Read-only."""
    out = []
    for c in checks:
        rows = (await session.execute(text(orphan_sql(c)))).fetchall()
        f = _finding(c, [r[0] for r in rows])
        if f:
            out.append(f)
    return out
