"""plan node (Phase 1, story S1-3; expanded Phase 2, story S2-2).

Choose the next tool + typed args, or decide enough evidence exists to draft
(or, now that the loop closes in S2, that the run should abstain outright,
e.g. an analyte confirmed "unverified" with nothing further to try). Emits an
``agent.plan`` audit event recording the choice.

S1/S2 ship a DETERMINISTIC planner — no live LLM is available in tests (no
GGUF model present) and none is called here. The planner is injectable (the
``planner`` parameter) so a future LLM-backed planner can be swapped in later
without changing callers; ``plan()`` itself never calls a real model.
"""

from __future__ import annotations

from typing import Callable, Literal

from pydantic import BaseModel

from ..audit import AgentAuditEvent, emit_audit_event
from ..state import RunLog, ToolContext

# A small set of analyte synonyms recognized by the deterministic planner.
# Maps a lowercase synonym/alias found in the question to the canonical
# analyte name used to filter query_observations. Intentionally small for
# S1 — richer NLU is out of scope (modules/normalize.py owns full canon-
# icalization at ingest time; this is just question-side keyword matching).
_ANALYTE_KEYWORDS: dict[str, str] = {
    "ldl": "LDL",
    "ldl-c": "LDL",
    "ldl cholesterol": "LDL",
    "hdl": "HDL",
    "hdl-c": "HDL",
    "hdl cholesterol": "HDL",
    "cholesterol": "Cholesterol",
    "triglycerides": "Triglycerides",
    "glucose": "Glucose",
    "a1c": "HbA1c",
    "hba1c": "HbA1c",
    "hemoglobin a1c": "HbA1c",
    "tsh": "TSH",
    "creatinine": "Creatinine",
    "potassium": "Potassium",
    "sodium": "Sodium",
    "vitamin d": "Vitamin D",
    "hemoglobin": "Hemoglobin",
}


class PlanDecision(BaseModel):
    action: Literal["call_tool", "draft", "abstain"]
    tool_name: str | None = None
    tool_args: dict | None = None
    abstain_reason: str | None = None


# Keyword cues recognized by the deterministic planner for a "how has X
# changed over time" trend question. Intentionally small (same spirit as
# _ANALYTE_KEYWORDS) — richer NLU is out of scope for the deterministic S1/S2
# planner; an LLM-backed planner is the injectable seam for that later.
_TREND_KEYWORDS = ("trend", "changed", "change", "over time", "over the last")


def _detect_analyte(question: str) -> str | None:
    """Best-effort, deterministic analyte detection from the question text."""
    lowered = question.lower()
    # Check longer phrases first so e.g. "ldl cholesterol" wins over "ldl".
    for keyword in sorted(_ANALYTE_KEYWORDS, key=len, reverse=True):
        if keyword in lowered:
            return _ANALYTE_KEYWORDS[keyword]
    return None


def _is_trend_question(question: str) -> bool:
    lowered = question.lower()
    return any(keyword in lowered for keyword in _TREND_KEYWORDS)


def _last_act(run_log: RunLog) -> dict | None:
    """The payload of the most recent ``act`` step, or ``None``."""
    for step in reversed(run_log.steps):
        if step.node == "act":
            return step.payload
    return None


def _default_planner(question: str, run_log: RunLog) -> PlanDecision:
    """Deterministic plan, now multi-turn (S2-2): react to prior act results.

    Turn 1:
      - A trend question ("how has X changed / trend / over time") with a
        detected analyte plans ``compute_trend`` directly — there is no need
        to call ``query_observations`` first since ``compute_trend`` already
        selects verified rows itself.
      - Otherwise plans ``query_observations``, scoped to a detected analyte
        if the question names one (no filter otherwise, so a non-biomarker
        question still gets a chance to find verified data before
        abstaining).

    Turn 2+ (after one ``act``):
      - If the prior tool was ``query_observations`` and it found NO verified
        rows for a named analyte, plan ``check_verification`` for that
        analyte next — this is what distinguishes "no data at all" from
        "data exists but isn't verified yet" (golden case
        ``abstain-unverified-ldl``: "value not yet verified" is only
        knowable via this follow-up lookup, since query_observations never
        surfaces unverified rows by design).
      - If the prior tool was ``check_verification`` and status is
        "unverified", abstain immediately with that reason rather than
        looping again with nothing new to try.
      - Otherwise (evidence already gathered, or nothing further to try),
        decide to draft and let ``reflect``/``draft`` work with what exists.
    """
    analyte = _detect_analyte(question)

    last = _last_act(run_log)

    if last is None:
        if analyte is not None and _is_trend_question(question):
            return PlanDecision(
                action="call_tool", tool_name="compute_trend", tool_args={"analyte": analyte}
            )

        tool_args: dict = {}
        if analyte is not None:
            tool_args["analyte"] = analyte
        return PlanDecision(action="call_tool", tool_name="query_observations", tool_args=tool_args)

    last_tool = last.get("tool_name")
    last_output = last.get("output", {})

    if last_tool == "query_observations" and analyte is not None and not last_output.get("rows"):
        return PlanDecision(
            action="call_tool", tool_name="check_verification", tool_args={"analyte": analyte}
        )

    if last_tool == "check_verification" and last_output.get("status") == "unverified":
        return PlanDecision(action="abstain", abstain_reason="value not yet verified")

    return PlanDecision(action="draft")


# Injectable seam: swap this for an LLM-backed planner later without touching
# call sites. Must keep the same signature (question, run_log) -> PlanDecision.
Planner = Callable[[str, RunLog], PlanDecision]


async def plan(
    question: str,
    run_log: RunLog,
    ctx: ToolContext,
    *,
    planner: Planner = _default_planner,
) -> PlanDecision:
    """Choose the next tool+args or decide to draft. Emits ``agent.plan``."""
    decision = planner(question, run_log)

    await emit_audit_event(
        AgentAuditEvent(
            run_id=ctx.run_id,
            node="plan",
            profile_id=ctx.profile_id,
            event_type="agent.plan",
            action=f"plan:{decision.action}"
            + (f":{decision.tool_name}" if decision.tool_name else ""),
            step_index=ctx.step_index,
            details={
                "action": decision.action,
                "tool_name": decision.tool_name,
                "abstain_reason": decision.abstain_reason,
            },
        ),
        db=getattr(ctx, "audit_db", None),
    )

    return decision
