"""check_verification tool (Phase 2, story S2-1).

Read-only. Reports whether a given observation is user-verified — the agent uses
this to decide between a grounded answer and an abstain ("value not yet
verified").
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from ..state import ToolContext
from .base import ToolInput, ToolOutput


class CheckVerificationInput(ToolInput):
    observation_id: str


class CheckVerificationOutput(ToolOutput):
    observation_id: str
    verified: bool
    verified_at: datetime | None = None


class CheckVerificationTool:
    name: ClassVar[str] = "check_verification"
    InputModel: ClassVar[type[ToolInput]] = CheckVerificationInput
    OutputModel: ClassVar[type[ToolOutput]] = CheckVerificationOutput

    async def run(self, args: CheckVerificationInput, ctx: ToolContext) -> CheckVerificationOutput:
        """SCAFFOLD: Sprint 2 (S2-1). Reads user_verified/verified_at; emits agent.act."""
        raise NotImplementedError("S2-1: report verification status for an observation")
