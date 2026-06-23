"""Run state, step log, and the hard step budget (Phase 1–2).

Replayability is a feature requirement, not a debug nicety: replaying ``steps``
in order must reproduce the same terminal (skills/healthcentral-agent). The step
budget caps tool calls at MAX_STEPS; exceeding it is a graceful ``abstain``,
never a crash or a spin.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from .audit import AgentNode
from .schemas import AgentTerminal

MAX_STEPS = 5  # hard cap on tool (``act``) calls per question


class ToolContext(Protocol):
    """What a tool needs at call time: a read-only, profile-scoped session.

    At implementation time this is satisfied by the FastAPI ``ProfileDbSession``
    dependency bound to the unlocked vault (see docs/agile/EXPLORATION_SUMMARY.md
    section B). Typed as a Protocol so scaffolds stay import-clean.
    """

    profile_id: str

    def db_session(self) -> Any: ...


class RunStep(BaseModel):
    step_index: int
    node: AgentNode
    payload: dict[str, Any] = Field(default_factory=dict)  # handles, never raw PHI
    timestamp: datetime


class RunLog(BaseModel):
    run_id: str
    profile_id: str
    steps: list[RunStep] = Field(default_factory=list)
    terminal: AgentTerminal | None = None

    def act_count(self) -> int:
        """Number of tool calls so far (budget is measured against MAX_STEPS)."""
        return sum(1 for s in self.steps if s.node == "act")

    def budget_exceeded(self) -> bool:
        return self.act_count() >= MAX_STEPS
