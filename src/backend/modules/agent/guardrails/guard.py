"""The guard node (Phase 3, stories S3-1..S3-4).

Runs in this ORDER (skills/healthcentral-guardrails):
  1. Advice gate (on the draft; the question is also checked pre-model) ->
     terminal ``escalate`` with the FIXED template. Never generate the prose.
  2. Groundedness mapping -> drop unmapped sentences; zero survivors -> ``abstain``.
  3. Confidence threshold -> below -> ``abstain``. Do NOT hedge.
  4. Emit an audit event (which gate fired, what was dropped).

Returns a schema-validated ``answer | abstain | escalate`` (AgentTerminal).
abstain/escalate are first-class SUCCESSES, never error paths.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..schemas import AgentTerminal, Citation


class GuardDecision(BaseModel):
    terminal: Literal["answer", "abstain", "escalate"]
    surviving_sentences: list[str]
    dropped_sentences: list[str]
    gate_fired: Literal["advice", "groundedness", "confidence", "none"]


async def guard(
    *,
    question: str,
    draft_sentences: list[str],
    citations: list[Citation],
    confidence: float,
    run_id: str,
    profile_id: str,
) -> AgentTerminal:
    """SCAFFOLD: Sprint 3.

    Implements the four-step guard order above and emits agent.guard. The
    confidence threshold value is an open question (PRD §10 Q2) — proposed reuse
    of the existing faithfulness threshold.
    """
    raise NotImplementedError("S3-1..S3-4: advice gate ×2, groundedness drop, confidence abstain, audit")
