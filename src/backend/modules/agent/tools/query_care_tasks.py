"""query_care_tasks tool (HC-M24, Phase E: bounded agentic queries).

Read-only. Answers "which follow-up tasks are open?"-shaped questions by
reading ``care_plan_task`` rows for the current profile, optionally filtered
by status. Free text (``title``/``source_quote``) originates from document
extraction — attacker-influenceable input a drafted sentence would otherwise
surface verbatim — so both fields are scrubbed through the SAME sanitizer
``nodes/draft.py`` already applies to observation fields (HC-M05); see
``guardrails/redaction_gate.sanitize_untrusted_field``. Output is capped at
50 rows so a bounded record-navigation query stays bounded.
"""

from __future__ import annotations

from datetime import date
from typing import ClassVar, Literal

from pydantic import Field
from sqlalchemy import select

from ..audit import AgentAuditEvent, emit_audit_event
from ..guardrails.redaction_gate import sanitize_untrusted_field
from ..state import ToolContext
from .base import ToolInput, ToolOutput

_MAX_ROWS = 50

CareTaskStatus = Literal["open", "done", "ignored", "needs_review"]


class QueryCareTasksInput(ToolInput):
    status_filter: CareTaskStatus | None = None


class CareTaskRow(ToolOutput):
    task_id: str
    title: str
    status: str
    due_date: date | None = None
    source_document_id: str | None = None
    source_quote: str | None = None


class QueryCareTasksOutput(ToolOutput):
    rows: list[CareTaskRow] = Field(default_factory=list)


class QueryCareTasksTool:
    name: ClassVar[str] = "query_care_tasks"
    InputModel: ClassVar[type[ToolInput]] = QueryCareTasksInput
    OutputModel: ClassVar[type[ToolOutput]] = QueryCareTasksOutput

    async def run(self, args: QueryCareTasksInput, ctx: ToolContext) -> QueryCareTasksOutput:
        """Read care-plan tasks for the current profile. READ ONLY.

        Optionally filters by ``status``, orders newest-first, and caps at
        ``_MAX_ROWS``. ``title``/``source_quote`` are sanitized before
        leaving the tool — the draft node composes them verbatim into the
        terminal text, so they must already be safe by the time they're
        logged. Emits one ``agent.act`` audit event (handles/counts only —
        never the raw title/quote text).
        """
        from models.care_plan_task import CarePlanTask

        stmt = select(CarePlanTask)
        if args.status_filter:
            stmt = stmt.where(CarePlanTask.status == args.status_filter)
        stmt = stmt.order_by(CarePlanTask.created_at.desc()).limit(_MAX_ROWS)

        async with ctx.db_session() as session:
            result = await session.execute(stmt)
            task_rows = result.scalars().all()

        rows = [
            CareTaskRow(
                task_id=task.id,
                title=sanitize_untrusted_field(task.title),
                status=task.status,
                due_date=task.due_date,
                source_document_id=task.source_document_id,
                source_quote=sanitize_untrusted_field(task.source_quote),
            )
            for task in task_rows
        ]

        await emit_audit_event(
            AgentAuditEvent(
                run_id=ctx.run_id,
                node="act",
                profile_id=ctx.profile_id,
                event_type="agent.act",
                action="query_care_tasks",
                step_index=ctx.step_index,
                details={
                    "tool_name": self.name,
                    "task_ids": [r.task_id for r in rows],
                    "status_filter": args.status_filter,
                    "count": len(rows),
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return QueryCareTasksOutput(rows=rows)
