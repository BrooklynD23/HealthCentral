"""The agent graph runner (Phase 1–2).

A small hand-rolled state machine — NO LangGraph dependency unless the client
explicitly approves it (local-first footprint stays clean;
skills/healthcentral-agent).

Shape::

    plan -> act -> reflect -> (loop | draft) -> guard -> terminal

- plan:    choose the next tool + typed args, or decide enough evidence exists
- act:     execute exactly ONE tool call; never batch
- reflect: "do I have grounding for an answer yet?" -> loop or proceed
- draft:   compose answer; every sentence carries a source handle
- guard:   owned by guardrails/; the agent CALLS it, never inlines it
- terminal: answer | abstain | escalate (all first-class successes)

Every node emits an audit event (audit.emit_audit_event). The loop honors the
MAX_STEPS budget from state.py.

S1 scope: a single-step run — plan decides to call ``query_observations``
once, act executes it, draft composes the answer from whatever verified rows
came back. The ``reflect`` node (loop/budget decision, Sprint 2 S2-2) and the
``guard`` node (advice/groundedness/confidence gates, Sprint 3 S3-1..S3-4) are
NOT wired into this single-step path yet:

  * ``reflect`` is simply not called — S1 never loops, so there is nothing
    for it to decide yet. S2 wires it in between act and draft.
  * ``guard`` has a trivial passthrough seam below (``_passthrough_guard``)
    that S3 will replace with the real advice/groundedness/confidence gates.
    It exists so the call site (here) doesn't change shape when S3 lands —
    only the function body swaps.

If ``act`` finds no verified observations, the run abstains using the FIXED
``ABSTAIN_TEMPLATE`` (never model-generated prose) — abstain is a first-class
success, not an error path.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .guardrails.templates import ABSTAIN_TEMPLATE
from .nodes.act import act
from .nodes.draft import draft
from .nodes.plan import plan
from .schemas import AgentTerminal
from .state import RunLog, RunStep, ToolContext


@dataclass
class RunContext:
    """Concrete ``ToolContext`` the graph owns for the duration of one run.

    ``step_index`` is mutated by the graph as it advances node-to-node so
    each emitted audit event/RunStep carries the right index. ``db_session``
    is supplied by the caller (FastAPI's profile-scoped session in
    production; a test fixture's session factory in tests).
    """

    profile_id: str
    run_id: str
    db_session_factory: Any  # callable -> async context manager yielding an AsyncSession
    audit_db: Any = None
    step_index: int = 0

    def db_session(self) -> Any:
        return self.db_session_factory()


def _passthrough_guard(*, draft_result, run_id: str) -> AgentTerminal:
    """SEAM for Sprint 3 (S3-1..S3-4): advice gate, groundedness, confidence.

    S1 placeholder only — does NOT implement any guard logic. It trivially
    passes every drafted sentence through as the answer when there is at
    least one citation, otherwise abstains. S3 replaces this function's body
    (not its call site) with the real four-step guard order.
    """
    if not draft_result.sentences or not draft_result.citations:
        return AgentTerminal(terminal="abstain", text=ABSTAIN_TEMPLATE, citations=[], run_id=run_id)

    return AgentTerminal(
        terminal="answer",
        text=" ".join(draft_result.sentences),
        citations=draft_result.citations,
        run_id=run_id,
    )


async def run_agent(question: str, ctx: ToolContext) -> AgentTerminal:
    """Execute one read-only agent run end-to-end and return its terminal.

    S1 scope: a single plan -> act -> draft step (see module docstring for why
    reflect/guard aren't wired in yet). Emits one audit event per node
    (plan, act, draft) via each node's own ``emit_audit_event`` call. Never
    exceeds MAX_STEPS tool calls — S1's deterministic planner only ever
    issues one ``call_tool`` decision before deciding to draft, so the budget
    cannot be exceeded in this sprint's path.
    """
    run_log = RunLog(run_id=ctx.run_id, profile_id=ctx.profile_id)

    # --- plan: decide to call query_observations -----------------------
    ctx.step_index = len(run_log.steps)
    decision = await plan(question, run_log, ctx)
    run_log.steps.append(
        RunStep(
            step_index=ctx.step_index,
            node="plan",
            payload={"action": decision.action, "tool_name": decision.tool_name},
            timestamp=datetime.utcnow(),
        )
    )

    # --- act: execute exactly one tool call (S1 never batches/loops) ----
    if decision.action == "call_tool" and decision.tool_name:
        ctx.step_index = len(run_log.steps)
        await act(decision.tool_name, decision.tool_args or {}, run_log, ctx)

    # --- draft: compose the grounded answer from gathered evidence -----
    ctx.step_index = len(run_log.steps)
    draft_result = await draft(question, run_log, ctx)

    # --- guard seam (S3 fills this in; S1 uses the trivial passthrough) -
    terminal = _passthrough_guard(draft_result=draft_result, run_id=ctx.run_id)
    run_log.terminal = terminal

    return terminal


def new_run_id() -> str:
    """Generate a fresh run id for a ``RunLog``/``RunContext``."""
    return str(uuid.uuid4())


def replay(run_log: RunLog) -> AgentTerminal:
    """Reconstruct a run's terminal from its structured log (story S2-3)."""
    raise NotImplementedError("S2-3: deterministic replay from RunLog.steps")
