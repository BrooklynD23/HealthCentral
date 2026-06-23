"""query_observations tool (Phase 1, story S1-2).

Read-only. Returns ONLY verified observations (``Observation.user_verified ==
True``) for the current profile, scoped to the unlocked vault session. Never
returns unverified rows — the output model pins ``verified`` to True so an
unverified row cannot be represented.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import Field

from ..state import ToolContext
from .base import ToolInput, ToolOutput


class QueryObservationsInput(ToolInput):
    analyte: str | None = None
    limit: int = Field(default=20, le=100, ge=1)


class ObservationRow(ToolOutput):
    observation_id: str
    analyte: str
    value: float
    unit: str | None = None
    collected_at: datetime
    verified: Literal[True]  # only verified rows are ever emitted


class QueryObservationsOutput(ToolOutput):
    rows: list[ObservationRow] = Field(default_factory=list)


class QueryObservationsTool:
    name: ClassVar[str] = "query_observations"
    InputModel: ClassVar[type[ToolInput]] = QueryObservationsInput
    OutputModel: ClassVar[type[ToolOutput]] = QueryObservationsOutput

    async def run(self, args: QueryObservationsInput, ctx: ToolContext) -> QueryObservationsOutput:
        """SCAFFOLD: Sprint 1 (S1-2).

        Runs ``select(Observation).where(Observation.user_verified == True)``
        scoped to ``ctx`` profile session, applies the optional analyte filter
        and limit, and emits an agent.act audit event. READ ONLY.
        """
        raise NotImplementedError("S1-2: query verified observations for current profile")
