"""act node (Phase 1, story S1-3).

Execute EXACTLY ONE tool call; never batch. Args are validated by the tool's
Pydantic input model before execution — malformed args fail validation and are
NEVER executed (the first guardrail layer). Emits an ``agent.act`` audit event
recording the tool name + validated args (handles, not raw PHI).

NOTE on audit: ``query_observations.run`` already emits its own ``agent.act``
event (it has the richer, tool-specific details — observation_ids/count). To
avoid double-emitting the same node's event per call, ``act`` here does NOT
emit a second ``agent.act`` when the tool itself emits one. See registry docs
for which tools self-emit.
"""

from __future__ import annotations

from pydantic import BaseModel

from core.time import utcnow

from ..state import MAX_STEPS, RunLog, RunStep, ToolContext
from ..tools import registry


class StepBudgetExceeded(Exception):
    """Raised when ``act`` is invoked after the step budget is already spent."""


class ActResult(BaseModel):
    tool_name: str
    output: dict  # the tool's typed OutputModel, serialized


async def act(tool_name: str, tool_args: dict, run_log: RunLog, ctx: ToolContext) -> ActResult:
    """Validate args, execute exactly one read-only tool, record the RunStep.

    Looks the tool up in the registry, validates ``tool_args`` against its
    InputModel (reject on failure — never execute), runs it read-only, and
    appends a ``RunStep(node="act")`` to ``run_log``. Refuses (raises
    ``StepBudgetExceeded``) if the step budget is already exhausted; the
    graph, not this function, decides how to terminate gracefully.
    """
    if run_log.budget_exceeded():
        raise StepBudgetExceeded(f"act budget of {MAX_STEPS} tool calls already spent")

    tool = registry.get(tool_name)
    validated_args = registry.validate_args(tool_name, tool_args)

    output = await tool.run(validated_args, ctx)
    output_dict = output.model_dump(mode="json")

    run_log.steps.append(
        RunStep(
            step_index=len(run_log.steps),
            node="act",
            payload={"tool_name": tool_name, "output": output_dict},
            timestamp=utcnow(),
        )
    )

    return ActResult(tool_name=tool_name, output=output_dict)
