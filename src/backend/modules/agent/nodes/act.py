"""act node (Phase 1, story S1-3).

Execute EXACTLY ONE tool call; never batch. Args are validated by the tool's
Pydantic input model before execution — malformed args fail validation and are
NEVER executed (the first guardrail layer). Emits an ``agent.act`` audit event
recording the tool name + validated args (handles, not raw PHI).
"""

from __future__ import annotations

from pydantic import BaseModel

from ..state import RunLog, ToolContext


class ActResult(BaseModel):
    tool_name: str
    output: dict  # the tool's typed OutputModel, serialized


async def act(tool_name: str, tool_args: dict, run_log: RunLog, ctx: ToolContext) -> ActResult:
    """SCAFFOLD: implemented in Sprint 1 (S1-3).

    Looks the tool up in the registry, validates ``tool_args`` against its
    InputModel (reject on failure — never execute), runs it read-only, and emits
    agent.act. Refuses if the step budget is already exhausted (graceful abstain
    is handled by the graph, not here).
    """
    raise NotImplementedError("S1-3: validate args, execute one read-only tool, emit agent.act")
