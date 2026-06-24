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

S1 scope was a single-step run only (plan -> act -> draft, no looping). S2
(story S2-2) wires the real loop in: plan can now also decide to ``act``
again, and ``reflect`` runs after every ``act`` to decide ``loop`` (back to
plan), ``draft`` (enough grounding gathered), or ``abstain_budget`` (another
``act`` would exceed MAX_STEPS — graceful abstain, never a spin or a crash).
``plan`` itself can also decide ``abstain`` directly (e.g. an analyte
confirmed "unverified" via ``check_verification`` with nothing further to
try) — that bypasses ``act``/``reflect`` entirely for that turn.

``guard`` (story S3-1..S3-4) is the real ``guardrails.guard.guard`` four-step
gate (advice -> groundedness -> confidence -> audit). A second, SHARED advice
check also runs pre-model, at the very top of ``run_agent``, on the incoming
question itself — bait can enter before any tool ever runs, so a single
on-draft check is insufficient (skills/healthcentral-guardrails). Both checks
call the same ``classify_advice`` so behavior can't drift between them.

If no evidence is ever gathered (no verified observations, no resolvable
trend, etc.), the run abstains using the FIXED ``ABSTAIN_TEMPLATE`` (never
model-generated prose) — abstain is a first-class success, not an error path.
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .guardrails.classifier import classify_advice
from .guardrails.guard import guard as run_guard
from .guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE
from .metrics import record_node_timing
from .nodes.act import act
from .nodes.draft import draft
from .nodes.plan import plan
from .nodes.reflect import reflect
from .schemas import AgentTerminal
from .state import MAX_STEPS, RunLog, RunStep, ToolContext


@contextmanager
def _timed_node(node: str):
    """Time one node's execution and surface it via ``record_node_timing``
    (story S5-3). Trivial overhead: one ``time.monotonic()`` pair plus a
    dict append in the metrics collector — never on the critical path of
    grounding/guard decisions, just observed around them.
    """
    start = time.monotonic()
    try:
        yield
    finally:
        record_node_timing(node, time.monotonic() - start)


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


async def _guard_draft(*, question: str, draft_result, ctx: ToolContext) -> AgentTerminal:
    """Call site for the real guard (story S3-1..S3-4).

    Thin adapter from the graph's ``Draft``/``ToolContext`` shapes to
    ``guardrails.guard.guard``'s keyword args. The call site's SHAPE was
    fixed back in S1/S2 (``_passthrough_guard``) precisely so S3 only had to
    swap the body, not every caller; this is that swap. The four-step order
    (advice -> groundedness -> confidence -> audit) lives entirely in
    ``guardrails/guard.py`` — this graph module never inlines guard logic.
    """
    return await run_guard(
        question=question,
        draft_sentences=draft_result.sentences,
        citations=draft_result.citations,
        run_id=ctx.run_id,
        profile_id=ctx.profile_id,
        audit_db=getattr(ctx, "audit_db", None),
        step_index=ctx.step_index,
    )


def _record_plan_step(run_log: RunLog, ctx: ToolContext, decision) -> None:
    run_log.steps.append(
        RunStep(
            step_index=ctx.step_index,
            node="plan",
            payload={
                "action": decision.action,
                "tool_name": decision.tool_name,
                "abstain_reason": decision.abstain_reason,
            },
            timestamp=datetime.utcnow(),
        )
    )


def _record_reflect_step(run_log: RunLog, ctx: ToolContext, decision) -> None:
    run_log.steps.append(
        RunStep(
            step_index=ctx.step_index,
            node="reflect",
            payload={"decision": decision.decision, "remaining_budget": decision.remaining_budget},
            timestamp=datetime.utcnow(),
        )
    )


async def run_agent(question: str, ctx: ToolContext) -> AgentTerminal:
    """Execute one read-only agent run end-to-end and return its terminal.

    The real loop (story S2-2): plan -> act -> reflect -> (loop back to plan |
    draft) -> guard -> terminal. ``plan`` may also decide ``abstain`` directly
    (skipping act/reflect for that turn). The loop can run at most MAX_STEPS
    ``act`` calls — ``reflect`` enforces this by returning ``abstain_budget``
    before a call that would exceed the cap, and as a defense-in-depth
    backstop this function's own ``for`` loop is itself bounded to MAX_STEPS
    iterations so a planner bug can never spin forever. Emits one audit event
    per node visited via each node's own ``emit_audit_event`` call. Each node
    visited (plan/act/reflect/draft/guard) also has its wall-clock duration
    recorded via ``record_node_timing`` (story S5-3), surfacing per-node
    p50/p95/p99 on ``/api/v1/monitoring/metrics``.

    PRE-MODEL advice gate (story S3-1): the incoming question is checked by
    the SAME ``classify_advice`` the guard node re-checks the draft with,
    BEFORE any plan/act/draft node runs. An advice-seeking question
    short-circuits immediately to ``escalate`` with the FIXED
    ``ESCALATE_TEMPLATE`` — no tool call, no draft, no model-generated prose
    of any kind, which is what guarantees advice_leakage == 0 for bait
    questions (golden cases ``advice-stop-statin``/``advice-is-this-
    dangerous``).
    """
    pre_model_verdict = classify_advice(question)
    if pre_model_verdict.is_advice_seeking:
        return AgentTerminal(
            terminal="escalate", text=ESCALATE_TEMPLATE, citations=[], run_id=ctx.run_id
        )

    run_log = RunLog(run_id=ctx.run_id, profile_id=ctx.profile_id)

    for _ in range(MAX_STEPS + 1):  # defense-in-depth: loop itself is bounded
        # --- plan: choose the next tool, decide to draft, or abstain ----
        ctx.step_index = len(run_log.steps)
        with _timed_node("plan"):
            decision = await plan(question, run_log, ctx)
        _record_plan_step(run_log, ctx, decision)

        if decision.action == "abstain":
            terminal = AgentTerminal(
                terminal="abstain", text=ABSTAIN_TEMPLATE, citations=[], run_id=ctx.run_id
            )
            run_log.terminal = terminal
            return terminal

        if decision.action == "draft":
            break

        # decision.action == "call_tool": execute exactly one tool call ----
        ctx.step_index = len(run_log.steps)
        with _timed_node("act"):
            await act(decision.tool_name, decision.tool_args or {}, run_log, ctx)

        # --- reflect: loop back to plan, proceed to draft, or hit budget -
        ctx.step_index = len(run_log.steps)
        with _timed_node("reflect"):
            reflect_decision = await reflect(run_log, ctx)
        _record_reflect_step(run_log, ctx, reflect_decision)

        if reflect_decision.decision == "abstain_budget":
            terminal = AgentTerminal(
                terminal="abstain", text=ABSTAIN_TEMPLATE, citations=[], run_id=ctx.run_id
            )
            run_log.terminal = terminal
            return terminal

        if reflect_decision.decision == "draft":
            break

        # decision.decision == "loop": fall through, plan gets another turn

    # --- draft: compose the grounded answer from gathered evidence -----
    ctx.step_index = len(run_log.steps)
    with _timed_node("draft"):
        draft_result = await draft(question, run_log, ctx)

    # --- guard: advice gate (re-check) -> groundedness -> confidence -----
    ctx.step_index = len(run_log.steps)
    with _timed_node("guard"):
        terminal = await _guard_draft(question=question, draft_result=draft_result, ctx=ctx)
    run_log.terminal = terminal

    return terminal


def new_run_id() -> str:
    """Generate a fresh run id for a ``RunLog``/``RunContext``."""
    return str(uuid.uuid4())


def replay(run_log: RunLog) -> AgentTerminal:
    """Deterministically reconstruct a completed run's terminal (story S2-3).

    Replays ``run_log.steps`` WITHOUT re-calling any tool: every node's
    decision/output is already captured in each step's ``payload`` (handles
    only, never raw PHI — state.py's ``RunStep`` contract), so replay is pure
    reconstruction over already-logged data, never live I/O. This makes
    replay deterministic and safe to run outside the original profile-scoped
    session.

    Mirrors ``run_agent``'s node order (plan -> act -> reflect -> draft ->
    guard) but reads each node's decision back from the log instead of
    invoking the node function:
      - a logged ``plan`` step with ``action == "abstain"`` reproduces the
        abstain terminal immediately (matching ``run_agent``'s own early
        return for that case);
      - a logged ``reflect`` step with ``decision == "abstain_budget"``
        reproduces the abstain terminal at that point;
      - otherwise, every logged ``act`` step's tool output is replayed
        through draft's own log-reading helpers (``_observation_rows_from_log``
        / ``_trend_sentences``), and the same trivial "any sentences+citations
        -> answer, else abstain" reconstruction below decides the final
        terminal from that draft (replay never re-runs the real S3 guard —
        it is pure reconstruction over the already-logged decision, never
        live I/O; S3's advice/groundedness/confidence gates ran once, at
        original `run_agent` time, and their outcome is what got logged).

    Raises ``ValueError`` if ``run_log`` has no steps to replay (nothing to
    reconstruct from).
    """
    if not run_log.steps:
        raise ValueError("replay: run_log has no steps to reconstruct from")

    for step in run_log.steps:
        if step.node == "plan" and step.payload.get("action") == "abstain":
            return AgentTerminal(
                terminal="abstain", text=ABSTAIN_TEMPLATE, citations=[], run_id=run_log.run_id
            )
        if step.node == "reflect" and step.payload.get("decision") == "abstain_budget":
            return AgentTerminal(
                terminal="abstain", text=ABSTAIN_TEMPLATE, citations=[], run_id=run_log.run_id
            )

    from .nodes.draft import _observation_rows_from_log, _trend_sentences
    from .schemas import Citation

    sentences: list[str] = []
    citations: list[Citation] = []

    trend_sentences, trend_citations = _trend_sentences(run_log)
    sentences.extend(trend_sentences)
    citations.extend(trend_citations)

    cited_observation_ids = {c.source_id for c in citations}
    for row in _observation_rows_from_log(run_log):
        if row["observation_id"] in cited_observation_ids:
            continue
        unit = f" {row['unit']}" if row.get("unit") else ""
        sentences.append(
            f"Your verified {row['analyte']} result was {row['value']}{unit} "
            f"(collected {row['collected_at']})."
        )
        citations.append(
            Citation(source_type="document", source_id=row["observation_id"], locator=row["observation_id"])
        )

    if not sentences or not citations:
        return AgentTerminal(
            terminal="abstain", text=ABSTAIN_TEMPLATE, citations=[], run_id=run_log.run_id
        )

    return AgentTerminal(
        terminal="answer", text=" ".join(sentences), citations=citations, run_id=run_log.run_id
    )
