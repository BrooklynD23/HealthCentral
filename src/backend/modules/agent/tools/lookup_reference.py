"""lookup_reference tool (Phase 2, story S2-1).

Read-only lookup of curated reference ranges from the master-DB knowledge base.
Returns a stable ``handle`` that the groundedness mapping accepts as a source.
"""

from __future__ import annotations

from typing import ClassVar

from ..state import ToolContext
from .base import ToolInput, ToolOutput


class LookupReferenceInput(ToolInput):
    analyte: str


class ReferenceRange(ToolOutput):
    analyte: str
    low: float | None = None
    high: float | None = None
    unit: str | None = None


class LookupReferenceOutput(ToolOutput):
    reference: ReferenceRange | None = None
    handle: str  # curated-reference source handle for citations


class LookupReferenceTool:
    name: ClassVar[str] = "lookup_reference"
    InputModel: ClassVar[type[ToolInput]] = LookupReferenceInput
    OutputModel: ClassVar[type[ToolOutput]] = LookupReferenceOutput

    async def run(self, args: LookupReferenceInput, ctx: ToolContext) -> LookupReferenceOutput:
        """SCAFFOLD: Sprint 2 (S2-1). Reads curated references (no PHI); emits agent.act."""
        raise NotImplementedError("S2-1: look up curated reference range + handle")
