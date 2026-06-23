"""reflect node (Phase 2, story S2-2).

"Do I have grounding for an answer yet?" -> loop or proceed. Enforces the hard
step budget: if continuing would exceed MAX_STEPS, terminate gracefully with an
``abstain`` ("insufficient evidence within budget") — never spin. Emits an
``agent.reflect`` audit event recording the decision + remaining budget.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..state import RunLog, ToolContext


class ReflectDecision(BaseModel):
    decision: Literal["loop", "draft", "abstain_budget"]
    remaining_budget: int


async def reflect(run_log: RunLog, ctx: ToolContext) -> ReflectDecision:
    """SCAFFOLD: implemented in Sprint 2 (S2-2). Must honor MAX_STEPS and emit agent.reflect."""
    raise NotImplementedError("S2-2: loop/proceed decision with hard step budget")
