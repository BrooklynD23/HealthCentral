"""query_timeline tool (HC-M24, Phase E: bounded agentic queries).

Read-only. Answers "what changed since my last visit?"/"summarize my visit
history"-shaped questions by delegating to the EXISTING timeline read model
(``modules/timeline.build_timeline``) — no new derivation logic here, this
tool is a thin, bounded, audited wrapper. ``title`` is extraction-derived,
attacker-influenceable free text, so it is scrubbed through the SAME
sanitizer ``nodes/draft.py`` already applies to observation fields (HC-M05);
see ``guardrails/redaction_gate.sanitize_untrusted_field``. Output is capped
at 50 events (``build_timeline`` already returns newest-first) so a bounded
record-navigation query stays bounded.
"""

from __future__ import annotations

from datetime import date
from typing import ClassVar

from pydantic import Field

from ..audit import AgentAuditEvent, emit_audit_event
from ..guardrails.redaction_gate import sanitize_untrusted_field
from ..state import ToolContext
from .base import ToolInput, ToolOutput

_MAX_ROWS = 50


class QueryTimelineInput(ToolInput):
    date_from: date | None = None
    date_to: date | None = None
    event_type: str | None = None


class TimelineRow(ToolOutput):
    event_id: str
    event_type: str
    event_date: str | None = None
    title: str
    doc_id: str | None = None
    related_ids: list[str] = Field(default_factory=list)
    verification_status: str = "n/a"


class QueryTimelineOutput(ToolOutput):
    rows: list[TimelineRow] = Field(default_factory=list)


class QueryTimelineTool:
    name: ClassVar[str] = "query_timeline"
    InputModel: ClassVar[type[ToolInput]] = QueryTimelineInput
    OutputModel: ClassVar[type[ToolOutput]] = QueryTimelineOutput

    async def run(self, args: QueryTimelineInput, ctx: ToolContext) -> QueryTimelineOutput:
        """Read the derived timeline for the current profile. READ ONLY.

        Delegates to ``modules.timeline.build_timeline`` for the actual
        event derivation (no new logic here), takes only its dated
        ``events`` (already newest-first), caps at ``_MAX_ROWS``, and
        sanitizes each event's ``title``. Emits one ``agent.act`` audit
        event (handles/counts only — never the raw title text).
        """
        from modules.timeline import build_timeline

        async with ctx.db_session() as session:
            result = await build_timeline(
                session,
                ctx.profile_id,
                event_type=args.event_type,
                date_from=args.date_from,
                date_to=args.date_to,
            )

        events = result.events[:_MAX_ROWS]

        rows = [
            TimelineRow(
                event_id=event.event_id,
                event_type=event.event_type,
                event_date=event.event_date,
                title=sanitize_untrusted_field(event.title),
                doc_id=event.doc_id,
                related_ids=list(event.related_ids),
                verification_status=event.verification_status,
            )
            for event in events
        ]

        await emit_audit_event(
            AgentAuditEvent(
                run_id=ctx.run_id,
                node="act",
                profile_id=ctx.profile_id,
                event_type="agent.act",
                action="query_timeline",
                step_index=ctx.step_index,
                details={
                    "tool_name": self.name,
                    "event_ids": [r.event_id for r in rows],
                    "event_type_filter": args.event_type,
                    "count": len(rows),
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return QueryTimelineOutput(rows=rows)
