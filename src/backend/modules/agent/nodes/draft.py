"""draft node (Phase 2 / Phase 3 boundary).

Compose the answer; EVERY sentence must carry a source handle. The draft is then
handed to the guard node (guardrails/guard.py) which runs the advice gate on it,
drops unmapped sentences, and applies the confidence threshold before anything
reaches the user. The draft node never decides the terminal — guard does.
Emits an ``agent.draft`` audit event.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..schemas import Citation
from ..state import RunLog, ToolContext


class Draft(BaseModel):
    sentences: list[str]
    citations: list[Citation]  # parallel source handles, one+ per sentence


async def draft(question: str, run_log: RunLog, ctx: ToolContext) -> Draft:
    """SCAFFOLD: implemented in Sprint 2. Composes a grounded draft for the guard node."""
    raise NotImplementedError("S2: compose grounded draft; every sentence carries a source handle")
