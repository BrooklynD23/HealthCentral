"""compute_trend tool (Phase 2, story S2-1). Read-only, profile-scoped, audited."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import Field

from ..state import ToolContext
from .base import ToolInput, ToolOutput


class ComputeTrendInput(ToolInput):
    analyte: str
    window_days: int | None = Field(default=None, ge=1)


class TrendPoint(ToolOutput):
    # observation_id is the source handle the draft/guard cites for THIS point.
    # A trend sentence must map to a real source (groundedness mapping), and a
    # manually entered observation has no document chunk — so the supporting
    # observation handle travels with each point or the answer can't be cited.
    observation_id: str
    collected_at: datetime
    value: float


class ComputeTrendOutput(ToolOutput):
    analyte: str
    points: list[TrendPoint] = Field(default_factory=list)
    direction: Literal["up", "down", "flat"] = "flat"


class ComputeTrendTool:
    name: ClassVar[str] = "compute_trend"
    InputModel: ClassVar[type[ToolInput]] = ComputeTrendInput
    OutputModel: ClassVar[type[ToolOutput]] = ComputeTrendOutput

    async def run(self, args: ComputeTrendInput, ctx: ToolContext) -> ComputeTrendOutput:
        """SCAFFOLD: Sprint 2 (S2-1). Trend over VERIFIED observations only; emits agent.act."""
        raise NotImplementedError("S2-1: compute trend over verified observations")
