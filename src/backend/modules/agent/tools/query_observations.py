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
from sqlalchemy import case, func, or_, select

from modules.normalize import NormalizeModule

from ..audit import AgentAuditEvent, emit_audit_event
from ..state import ChatFilters, ToolContext
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

        # ASSIST-AGENT-DATES (owner AAD-ROW + AAD-SEMANTICS): dates narrow;
        # selected analytes are ADDED to the asked analyte, never replace it.
        filters = getattr(ctx, "filters", None) or ChatFilters()
        adding = bool(args.analyte and filters.analytes)
        asked = func.lower(Observation.analyte_canonical).in_({args.analyte.lower(), *NormalizeModule.canonical_keys_for(args.analyte)}) if args.analyte else None
        # With a selection, each row carries whether it is of the ASKED analyte,
        # computed by the same predicate that selects it (one matcher).
        stmt = select(Observation, asked.label("is_asked")) if adding else select(Observation)
        stmt = stmt.where(Observation.user_verified == True)  # noqa: E712
        if adding:
            stmt = stmt.where(or_(
                asked,
                # Selected rows need a date: ObservationRow.collected_at is
                # required, so a NULL-dated selected row must not join.
                func.lower(Observation.analyte_canonical).in_(filters.analytes)
                & Observation.collected_at.isnot(None),
            ))
            # The asked analyte's rows first, so the limit can never cut them.
            stmt = stmt.order_by(case((asked, 0), else_=1))
        elif asked is not None:
            stmt = stmt.where(asked)
        if filters.from_dt is not None:
            stmt = stmt.where(Observation.collected_at >= filters.from_dt)
        if filters.to_dt is not None:
            stmt = stmt.where(Observation.collected_at <= filters.to_dt)
        if asked is None:
            # Open question (no analyte named, nothing adding): the LATEST
            # verified row per analyte, over the same filters, so the limit
            # cuts analytes rather than an arbitrary slice of rows. NULL-dated
            # rows never win "latest".
            ranked = (
                stmt.where(Observation.collected_at.isnot(None))
                .with_only_columns(
                    Observation.id.label("oid"),
                    func.row_number().over(
                        partition_by=Observation.analyte_canonical,
                        order_by=Observation.collected_at.desc(),
                    ).label("rn"),
                )
                .subquery()
            )
            stmt = (
                select(Observation)
                .join(ranked, Observation.id == ranked.c.oid)
                .where(ranked.c.rn == 1)
                .order_by(Observation.collected_at.desc())
            )
        stmt = stmt.limit(args.limit)

        async with ctx.db_session() as session:
            result = await session.execute(stmt)
            if adding:
                fetched = result.all()
                obs_rows = [r[0] for r in fetched]
                has_asked = any(r.is_asked for r in fetched)
            else:
                obs_rows = result.scalars().all()

        if adding and not has_asked:
            # Nothing of the ASKED analyte: return nothing, as without a
            # selection, so the planner still runs check_verification and a
            # "value not yet verified" abstain is never replaced by an answer
            # about a different analyte (lane A §ASSIST-AGENT-DATES).
            obs_rows = []

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
                    "analyte_filter_present": args.analyte is not None,
                    "count": len(rows),
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return QueryObservationsOutput(rows=rows)
