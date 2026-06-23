"""plan node (Phase 1, story S1-3).

Choose the next tool + typed args, or decide enough evidence exists to draft.
Emits an ``agent.plan`` audit event recording the choice.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..state import RunLog, ToolContext


class PlanDecision(BaseModel):
    action: Literal["call_tool", "draft"]
    tool_name: str | None = None
    tool_args: dict | None = None


async def plan(question: str, run_log: RunLog, ctx: ToolContext) -> PlanDecision:
    """SCAFFOLD: implemented in Sprint 1 (S1-3). Must emit agent.plan audit event."""
    raise NotImplementedError("S1-3: choose next tool+args or decide to draft")
