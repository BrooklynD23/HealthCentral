"""Terminal contract + shared schemas for the agent (Phase 0).

Every answer the agent produces is one of three first-class terminals:
``answer | abstain | escalate``. ``abstain`` and ``escalate`` are SUCCESSES,
never error paths (skills/healthcentral-guardrails, healthcentral-agent).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A source handle attached to an answer sentence by draft/guard."""

    source_type: Literal["document", "reference"]
    source_id: str
    locator: str | None = Field(
        default=None, description="page+span for documents, handle for references"
    )


class AgentTerminal(BaseModel):
    """Schema-validated terminal output of a single agent run.

    For ``abstain``/``escalate`` the ``text`` is a FIXED template constant from
    ``guardrails/templates.py`` — never model-generated prose.
    """

    terminal: Literal["answer", "abstain", "escalate"]
    text: str
    citations: list[Citation] = Field(default_factory=list)
    run_id: str
