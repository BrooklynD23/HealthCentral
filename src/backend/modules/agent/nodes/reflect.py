"""reflect node (Phase 2, story S2-2).

"Do I have grounding for an answer yet?" -> loop or proceed. Enforces the hard
step budget: if continuing would exceed MAX_STEPS, terminate gracefully with an
``abstain`` ("insufficient evidence within budget") — never spin. Emits an
``agent.reflect`` audit event recording the decision + remaining budget.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..audit import AgentAuditEvent, emit_audit_event
from ..state import MAX_STEPS, RunLog, ToolContext


class ReflectDecision(BaseModel):
    decision: Literal["loop", "draft", "abstain_budget"]
    remaining_budget: int


def _has_grounding(run_log: RunLog) -> bool:
    """Has at least one ``act`` step produced evidence worth drafting from?

    "Evidence" means a tool call that actually returned rows/points/chunks —
    an empty result (e.g. ``check_verification`` reporting "absent") is not
    grounding to draft an answer from; the planner gets another turn (if
    budget remains) or the run abstains on budget exhaustion.
    """
    for step in run_log.steps:
        if step.node != "act":
            continue
        output = step.payload.get("output", {})
        if output.get("rows") or output.get("points") or output.get("chunks"):
            return True
        # check_verification's status alone is enough to decide an abstain
        # ("value not yet verified") downstream in draft/guard — treat a
        # definitive status answer as grounding too so the loop can stop.
        if output.get("status") in ("unverified", "verified"):
            return True
    return False


async def reflect(run_log: RunLog, ctx: ToolContext) -> ReflectDecision:
    """Decide loop|draft|abstain_budget after the most recent ``act`` step.

    Honors the hard MAX_STEPS budget: if grounding is already sufficient,
    decide ``draft``. Otherwise, if another ``act`` call would exceed
    MAX_STEPS, decide ``abstain_budget`` (graceful, never a spin/crash). Else
    decide ``loop`` so ``plan`` gets another turn. Emits ``agent.reflect``
    recording the decision + remaining budget.
    """
    remaining = max(0, MAX_STEPS - run_log.act_count())

    if _has_grounding(run_log):
        decision: Literal["loop", "draft", "abstain_budget"] = "draft"
    elif remaining <= 0:
        decision = "abstain_budget"
    else:
        decision = "loop"

    result = ReflectDecision(decision=decision, remaining_budget=remaining)

    await emit_audit_event(
        AgentAuditEvent(
            run_id=ctx.run_id,
            node="reflect",
            profile_id=ctx.profile_id,
            event_type="agent.reflect",
            action=f"reflect:{decision}",
            step_index=ctx.step_index,
            details={
                "decision": decision,
                "remaining_budget": remaining,
            },
        ),
        db=getattr(ctx, "audit_db", None),
    )

    return result
