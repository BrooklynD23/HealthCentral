"""plan node (Phase 1, story S1-3).

Choose the next tool + typed args, or decide enough evidence exists to draft.
Emits an ``agent.plan`` audit event recording the choice.

S1 ships a DETERMINISTIC planner — no live LLM is available in tests (no GGUF
model present) and none is called here. The planner is injectable (the
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
    action: Literal["call_tool", "draft"]
    tool_name: str | None = None
    tool_args: dict | None = None


def _detect_analyte(question: str) -> str | None:
    """Best-effort, deterministic analyte detection from the question text."""
    lowered = question.lower()
    # Check longer phrases first so e.g. "ldl cholesterol" wins over "ldl".
    for keyword in sorted(_ANALYTE_KEYWORDS, key=len, reverse=True):
        if keyword in lowered:
            return _ANALYTE_KEYWORDS[keyword]
    return None


def _default_planner(question: str, run_log: RunLog) -> PlanDecision:
    """Deterministic plan: call query_observations once, then draft.

    If an ``act`` step is already in the run log, enough evidence has been
    gathered for a single-step run — decide to draft. Otherwise, plan a
    ``query_observations`` call, scoped to a detected analyte if the question
    names one (no filter otherwise, so a non-biomarker-specific question still
    gets a chance to find verified data before abstaining).
    """
    if run_log.act_count() > 0:
        return PlanDecision(action="draft")

    analyte = _detect_analyte(question)
    tool_args: dict = {}
    if analyte is not None:
        tool_args["analyte"] = analyte

    return PlanDecision(action="call_tool", tool_name="query_observations", tool_args=tool_args)


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
            },
        ),
        db=getattr(ctx, "audit_db", None),
    )

    return decision
