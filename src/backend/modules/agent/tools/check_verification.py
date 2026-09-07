"""check_verification tool (Phase 2, story S2-1).

Read-only verification-status lookup. Two discovery modes, exactly one per call:

- by ``observation_id`` — status of a known row, or
- by ``analyte`` — status metadata for an analyte WITHOUT exposing any
  unverified value.

The analyte mode exists because ``query_observations`` deliberately hides
unverified rows (its output pins ``verified == True``). Without a status-only
lookup, an unverified LDL would be indistinguishable from no LDL at all, and the
agent could not produce the required "value not yet verified" abstention for a
question that only names an analyte (golden case ``abstain-unverified-ldl``).
This tool returns only a status + counts — never the unverified value itself —
so the read-only-over-clinical-data invariant and the "don't surface unverified
values" rule both hold.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import model_validator
from sqlalchemy import select

from ..audit import AgentAuditEvent, emit_audit_event
from ..state import ToolContext
from .base import ToolInput, ToolOutput


class CheckVerificationInput(ToolInput):
    observation_id: str | None = None
    analyte: str | None = None

    @model_validator(mode="after")
    def _exactly_one_selector(self) -> "CheckVerificationInput":
        if bool(self.observation_id) == bool(self.analyte):
            raise ValueError("provide exactly one of observation_id or analyte")
        return self


class CheckVerificationOutput(ToolOutput):
    observation_id: str | None = None
    analyte: str | None = None
    # status, not the value: "absent" (no matching row), "unverified" (present
    # but not user-verified -> abstain "value not yet verified"), or "verified".
    status: Literal["absent", "unverified", "verified"]
    verified: bool
    verified_at: datetime | None = None
    # counts let the agent reason about presence without seeing any value
    match_count: int = 0


class CheckVerificationTool:
    name: ClassVar[str] = "check_verification"
    InputModel: ClassVar[type[ToolInput]] = CheckVerificationInput
    OutputModel: ClassVar[type[ToolOutput]] = CheckVerificationOutput

    async def run(self, args: CheckVerificationInput, ctx: ToolContext) -> CheckVerificationOutput:
        """Look up verification status by ``observation_id`` or ``analyte``. READ ONLY.

        Reads ``user_verified``/``verified_at`` for the matching observation(s)
        scoped to ``ctx``'s profile session. Never returns the underlying
        ``value`` — only status ("absent"/"unverified"/"verified") + counts.
        Emits one ``agent.act`` audit event (handles/counts only).
        """
        from models.observation import Observation

        if args.observation_id:
            stmt = select(Observation).where(Observation.id == args.observation_id)
        else:
            stmt = select(Observation).where(
                Observation.analyte_canonical.ilike(args.analyte)
            )

        async with ctx.db_session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        match_count = len(rows)
        verified_row = next((row for row in rows if row.user_verified), None)

        if match_count == 0:
            status: Literal["absent", "unverified", "verified"] = "absent"
            verified = False
            verified_at = None
        elif verified_row is not None:
            status = "verified"
            verified = True
            verified_at = verified_row.verified_at
        else:
            status = "unverified"
            verified = False
            verified_at = None

        output = CheckVerificationOutput(
            observation_id=args.observation_id,
            analyte=args.analyte,
            status=status,
            verified=verified,
            verified_at=verified_at,
            match_count=match_count,
        )

        await emit_audit_event(
            AgentAuditEvent(
                run_id=ctx.run_id,
                node="act",
                profile_id=ctx.profile_id,
                event_type="agent.act",
                action="check_verification",
                step_index=ctx.step_index,
                details={
                    "tool_name": self.name,
                    "observation_id": args.observation_id,
                    # AUDIT-PHI-001: analyte names are clinical content.
                    "status": status,
                    "match_count": match_count,
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return output
