"""Terminal contract + shared schemas for the agent (Phase 0).

Every answer the agent produces is one of three first-class terminals:
``answer | abstain | escalate``. ``abstain`` and ``escalate`` are SUCCESSES,
never error paths (skills/asclexis-guardrails, asclexis-agent).
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
    # CITE-SRC-001: `source_id` is heterogeneous — an observation, care-task,
    # entity or timeline-event id, all carried as source_type="document".
    # Without a discriminator the API layer cannot tell which deep-link target
    # it holds, and would have to guess from the id's shape.
    source_kind: Literal["observation", "task", "entity", "event", "reference"] | None = Field(
        default=None, description="Which kind of row source_id refers to"
    )


class AgentTerminal(BaseModel):
    """Schema-validated terminal output of a single agent run.

    For ``abstain``/``escalate`` the ``text`` is a FIXED template constant from
    ``guardrails/templates.py`` — never model-generated prose.

    ``surviving_count``/``dropped_count`` (A1, roadmap 2026-09-10) are the
    guard node's ``groundedness.map_sentences`` counts: how many DRAFT
    SENTENCES were backed by a real source handle (survived) versus had none
    and were dropped before the user ever saw them. They are sentence
    counts, not citation counts — ``map_sentences`` can legitimately emit
    MORE citations than sentences (a trend summary cites every point it
    summarizes), so counting citations over- or under-states what actually
    got verified. They are ``None`` whenever no mapping ran for this
    terminal — the pre-model advice-gate escalate, any terminal ``graph.py``
    builds outside the guard node, or a terminal read back out of the
    semantic cache/a log that predates this field — and optional with a
    default so those old/short-circuited terminals keep validating.
    Downstream (``api/assistant.py::_agent_terminal_to_response_parts``),
    ``None`` is the honest signal that no verifier ran: it must report
    ``VerificationInfo(enabled=False)``, never a guessed or carried-over
    score.
    """

    terminal: Literal["answer", "abstain", "escalate"]
    text: str
    citations: list[Citation] = Field(default_factory=list)
    run_id: str
    surviving_count: int | None = None
    dropped_count: int | None = None
