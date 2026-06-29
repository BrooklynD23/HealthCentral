"""Tool base contracts (Phase 1, story S1-1).

A tool is the pair (InputModel, OutputModel) plus a read-only ``run``. The
Pydantic input model is the FIRST guardrail layer: malformed args raise
ValidationError and the body is never reached.
"""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

from pydantic import BaseModel

from ..state import ToolContext


class ToolInput(BaseModel):
    """Base for every tool's typed input."""


class ToolOutput(BaseModel):
    """Base for every tool's typed output."""


@runtime_checkable
class ReadOnlyTool(Protocol):
    """Structural contract every registered tool satisfies.

    Implementations MUST NOT write clinical data. ``run`` reads only, scoped to
    ``ctx``'s profile session.
    """

    name: ClassVar[str]
    InputModel: ClassVar[type[ToolInput]]
    OutputModel: ClassVar[type[ToolOutput]]

    async def run(self, args: ToolInput, ctx: ToolContext) -> ToolOutput: ...
