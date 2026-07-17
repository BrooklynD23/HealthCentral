"""query_medication_changes tool (HC-M24, Phase E: bounded agentic queries).

Read-only. Answers "show all medication changes"-shaped questions by reading
verified ``medication_change`` ``DocumentEntity`` rows for the current
profile, joined to their ``Document`` for the document's collection date.
Unverified/rejected entities (``verified_by_user in (None, False)``) are
NEVER returned — only ``verified_by_user == True`` rows, mirroring
``query_observations``'s verified-only contract. ``entity_value``/``quote``
are extraction-derived, attacker-influenceable free text, so both are
scrubbed through the SAME sanitizer ``nodes/draft.py`` already applies to
observation fields (HC-M05); see
``guardrails/redaction_gate.sanitize_untrusted_field``. Output is capped at
50 rows so a bounded record-navigation query stays bounded.
"""

from __future__ import annotations

from datetime import date
from typing import ClassVar

from pydantic import Field
from sqlalchemy import select

from ..audit import AgentAuditEvent, emit_audit_event
from ..guardrails.redaction_gate import sanitize_untrusted_field
from ..state import ToolContext
from .base import ToolInput, ToolOutput

_MAX_ROWS = 50
_ENTITY_TYPE = "medication_change"


class QueryMedicationChangesInput(ToolInput):
    since_date: date | None = None


class MedicationChangeRow(ToolOutput):
    entity_id: str
    doc_id: str
    entity_value: str
    quote: str | None = None
    document_date: date | None = None


class QueryMedicationChangesOutput(ToolOutput):
    rows: list[MedicationChangeRow] = Field(default_factory=list)


class QueryMedicationChangesTool:
    name: ClassVar[str] = "query_medication_changes"
    InputModel: ClassVar[type[ToolInput]] = QueryMedicationChangesInput
    OutputModel: ClassVar[type[ToolOutput]] = QueryMedicationChangesOutput

    async def run(
        self, args: QueryMedicationChangesInput, ctx: ToolContext
    ) -> QueryMedicationChangesOutput:
        """Read verified medication-change entities for the current profile. READ ONLY.

        Selects ``DocumentEntity`` rows with ``entity_type == "medication_change"
        AND verified_by_user == True`` (unverified/rejected never returned),
        joined to ``Document`` for the document's ``collection_date``,
        optionally filtered to ``Document.collection_date >= since_date``,
        ordered newest-first, capped at ``_MAX_ROWS``. ``entity_value``/
        ``quote`` are sanitized before leaving the tool. Emits one
        ``agent.act`` audit event (handles/counts only — never the raw
        entity_value/quote text).
        """
        from models.document import Document
        from models.document_category import DocumentEntity

        stmt = (
            select(DocumentEntity, Document.collection_date)
            .join(Document, DocumentEntity.doc_id == Document.id)
            .where(
                DocumentEntity.entity_type == _ENTITY_TYPE,
                DocumentEntity.verified_by_user == True,  # noqa: E712
            )
        )
        if args.since_date is not None:
            stmt = stmt.where(Document.collection_date >= args.since_date)
        stmt = stmt.order_by(Document.collection_date.desc()).limit(_MAX_ROWS)

        async with ctx.db_session() as session:
            result = await session.execute(stmt)
            pairs = result.all()

        rows = [
            MedicationChangeRow(
                entity_id=entity.id,
                doc_id=entity.doc_id,
                entity_value=sanitize_untrusted_field(entity.entity_value),
                quote=sanitize_untrusted_field(entity.quote),
                document_date=collection_date.date() if collection_date else None,
            )
            for entity, collection_date in pairs
        ]

        await emit_audit_event(
            AgentAuditEvent(
                run_id=ctx.run_id,
                node="act",
                profile_id=ctx.profile_id,
                event_type="agent.act",
                action="query_medication_changes",
                step_index=ctx.step_index,
                details={
                    "tool_name": self.name,
                    "entity_ids": [r.entity_id for r in rows],
                    "since_date": args.since_date.isoformat() if args.since_date else None,
                    "count": len(rows),
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return QueryMedicationChangesOutput(rows=rows)
