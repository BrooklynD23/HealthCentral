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
        """SCAFFOLD: Sprint 2 (S2-1).

        Reads ``user_verified``/``verified_at`` for the matching observation(s)
        scoped to ``ctx`` profile. In analyte mode, returns status + match_count
        WITHOUT the value. Emits an agent.act audit event. READ ONLY.
        """
        raise NotImplementedError("S2-1: verification status by observation_id or analyte (no values)")
