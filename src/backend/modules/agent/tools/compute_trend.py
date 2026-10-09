"""compute_trend tool (Phase 2, story S2-1). Read-only, profile-scoped, audited."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import ClassVar, Literal

from pydantic import Field
from sqlalchemy import select

from core.time import utcnow

from ..audit import AgentAuditEvent, emit_audit_event
from ..state import ToolContext
from .base import ToolInput, ToolOutput


class ComputeTrendInput(ToolInput):
    analyte: str
    window_days: int | None = Field(default=None, ge=1)


class TrendPoint(ToolOutput):
    # observation_id is the source handle the draft/guard cites for THIS point.
    # A trend sentence must map to a real source (groundedness mapping), and a
    # manually entered observation has no document chunk — so the supporting
    # observation handle travels with each point or the answer can't be cited.
    observation_id: str
    collected_at: datetime
    value: float


class ComputeTrendOutput(ToolOutput):
    analyte: str
    points: list[TrendPoint] = Field(default_factory=list)
    direction: Literal["up", "down", "flat"] = "flat"


class ComputeTrendTool:
    name: ClassVar[str] = "compute_trend"
    InputModel: ClassVar[type[ToolInput]] = ComputeTrendInput
    OutputModel: ClassVar[type[ToolOutput]] = ComputeTrendOutput

    async def run(self, args: ComputeTrendInput, ctx: ToolContext) -> ComputeTrendOutput:
        """Compute a trend over VERIFIED observations for one analyte. READ ONLY.

        Selects ``Observation`` rows with ``user_verified == True`` for the
        analyte (case-insensitive match on ``analyte_canonical``), optionally
        windowed to the last ``window_days``, ordered by ``collected_at``
        ascending. Each row becomes a ``TrendPoint`` carrying its own
        ``observation_id`` as the source handle a draft sentence can cite.
        Direction is derived from the first vs. last point's value. Emits one
        ``agent.act`` audit event (handles/counts only).
        """
        from models.observation import Observation

        stmt = select(Observation).where(
            Observation.user_verified == True,  # noqa: E712
            Observation.analyte_canonical.ilike(args.analyte),
        )
        if args.window_days is not None:
            cutoff = utcnow() - timedelta(days=args.window_days)
            stmt = stmt.where(Observation.collected_at >= cutoff)
        stmt = stmt.order_by(Observation.collected_at.asc())

        async with ctx.db_session() as session:
            result = await session.execute(stmt)
            obs_rows = result.scalars().all()

        points = [
            TrendPoint(observation_id=row.id, collected_at=row.collected_at, value=row.value)
            for row in obs_rows
            if row.value is not None
        ]

        direction: Literal["up", "down", "flat"] = "flat"
        if len(points) >= 2:
            delta = points[-1].value - points[0].value
            if delta > 0:
                direction = "up"
            elif delta < 0:
                direction = "down"

        output = ComputeTrendOutput(analyte=args.analyte, points=points, direction=direction)

        await emit_audit_event(
            AgentAuditEvent(
                run_id=ctx.run_id,
                node="act",
                profile_id=ctx.profile_id,
                event_type="agent.act",
                action="compute_trend",
                step_index=ctx.step_index,
                details={
                    "tool_name": self.name,
                    "analyte": args.analyte,
                    "observation_ids": [p.observation_id for p in points],
                    "count": len(points),
                    "direction": direction,
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return output
