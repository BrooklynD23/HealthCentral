"""query_observations tool (Phase 1, story S1-2).

Read-only. Returns ONLY verified observations (``Observation.user_verified ==
True``) for the current profile, scoped to the unlocked vault session. Never
returns unverified rows — the output model pins ``verified`` to True so an
unverified row cannot be represented.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import Field
from sqlalchemy import select

from ..audit import AgentAuditEvent, emit_audit_event
from ..state import ToolContext
from .base import ToolInput, ToolOutput


class QueryObservationsInput(ToolInput):
    analyte: str | None = None
    limit: int = Field(default=20, le=100, ge=1)


class ObservationRow(ToolOutput):
    observation_id: str
    analyte: str
    value: float
    unit: str | None = None
    collected_at: datetime
    verified: Literal[True]  # only verified rows are ever emitted


class QueryObservationsOutput(ToolOutput):
    rows: list[ObservationRow] = Field(default_factory=list)


class QueryObservationsTool:
    name: ClassVar[str] = "query_observations"
    InputModel: ClassVar[type[ToolInput]] = QueryObservationsInput
    OutputModel: ClassVar[type[ToolOutput]] = QueryObservationsOutput

    async def run(self, args: QueryObservationsInput, ctx: ToolContext) -> QueryObservationsOutput:
        """Query verified observations for the current profile. READ ONLY.

        Runs ``select(Observation).where(Observation.user_verified == True)``
        scoped to ``ctx``'s profile session, applies the optional analyte
        filter (case-insensitive match on ``analyte_canonical``) and limit,
        and emits an ``agent.act`` audit event (handles/counts only — no raw
        PHI beyond what the row legitimately carries).
        """
        from models.observation import Observation

        stmt = select(Observation).where(Observation.user_verified == True)  # noqa: E712
        if args.analyte:
            stmt = stmt.where(Observation.analyte_canonical.ilike(args.analyte))
        stmt = stmt.limit(args.limit)

        async with ctx.db_session() as session:
            result = await session.execute(stmt)
            obs_rows = result.scalars().all()

        rows = [
            ObservationRow(
                observation_id=row.id,
                analyte=row.analyte_canonical,
                value=row.value,
                unit=row.unit,
                collected_at=row.collected_at,
                verified=True,
            )
            for row in obs_rows
        ]

        await emit_audit_event(
            AgentAuditEvent(
                run_id=ctx.run_id,
                node="act",
                profile_id=ctx.profile_id,
                event_type="agent.act",
                action="query_observations",
                step_index=ctx.step_index,
                details={
                    "tool_name": self.name,
                    "observation_ids": [r.observation_id for r in rows],
                    "analyte_filter": args.analyte,
                    "count": len(rows),
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return QueryObservationsOutput(rows=rows)
