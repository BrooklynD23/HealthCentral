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
"""

from __future__ import annotations

from .schemas import AgentTerminal
from .state import RunLog, ToolContext


async def run_agent(question: str, ctx: ToolContext) -> AgentTerminal:
    """Execute one read-only agent run end-to-end and return its terminal.

    SCAFFOLD: built across Sprints 1–2 (S1-3 plan->act->answer; S2-2 reflect +
    budget; S2-3 run-log replay). Must:
      * emit an audit event per node,
      * never exceed MAX_STEPS tool calls (graceful abstain if it would),
      * call the guard node before returning any terminal.
    """
    raise NotImplementedError("S1-3 / S2-2: implement the plan->act->reflect->draft->guard loop")


def replay(run_log: RunLog) -> AgentTerminal:
    """Reconstruct a run's terminal from its structured log (story S2-3)."""
    raise NotImplementedError("S2-3: deterministic replay from RunLog.steps")
