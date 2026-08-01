"""The guard node (Phase 3, stories S3-1..S3-4).

Runs in this ORDER (skills/asclexis-guardrails):
  1. Advice gate (on the draft; the question is also checked pre-model) ->
     terminal ``escalate`` with the FIXED template. Never generate the prose.
  2. Groundedness mapping -> drop unmapped sentences; zero survivors -> ``abstain``.
  3. Confidence threshold -> below -> ``abstain``. Do NOT hedge.
  4. Emit an audit event (which gate fired, what was dropped).

Returns a schema-validated ``answer | abstain | escalate`` (AgentTerminal).
abstain/escalate are first-class SUCCESSES, never error paths.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from ..audit import AgentAuditEvent, emit_audit_event
from ..schemas import AgentTerminal, Citation
from .classifier import classify_advice
from .groundedness import map_sentences
from .templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE

# Confidence threshold (story S3-3/S3-4; PRD §10 Q2 leaves the exact value
# open). Reuses modules.faithfulness.FaithfulnessConfig.min_overall_score —
# the existing "below this, flag as unfaithful" cutoff already used elsewhere
# in the codebase — rather than inventing a second, divergent threshold.
# Below this value the guard abstains; it never hedges. Flagged here for
# reconciliation if a different sprint later wants a guard-specific value.
from modules.faithfulness import FaithfulnessConfig

CONFIDENCE_THRESHOLD = FaithfulnessConfig().min_overall_score  # 0.6


class GuardDecision(BaseModel):
    terminal: Literal["answer", "abstain", "escalate"]
    surviving_sentences: list[str]
    dropped_sentences: list[str]
    gate_fired: Literal["advice", "groundedness", "confidence", "none"]


def groundedness_confidence(surviving: list[str], citations: list[Citation]) -> float:
    """Deterministic confidence signal fed to the guard's threshold gate.

    IMPORTANT: this is NOT the surviving/total-sentence ratio. Dropping an
    unmapped sentence is the EXPECTED, healthy outcome of gate 2 — a draft
    that mixes one grounded claim with one ungrounded claim (golden case
    ``mixed-partial-grounding``: LDL grounded, kidney-function claim has no
    source and must be dropped) should still answer with the surviving
    grounded sentence, not have that healthy drop double-penalized into a
    second, redundant abstain via the confidence gate. Each SURVIVING
    sentence already cleared groundedness (>=1 real citation, by
    construction of ``map_sentences``), so confidence here reflects whether
    survivors are backed by *non-empty* citation handles specifically:
    1.0 when every surviving citation carries a real ``source_id``, 0.0 if
    somehow none do (defense-in-depth; ``map_sentences`` should never let
    that happen, but the threshold gate must not blindly trust upstream).
    Zero surviving sentences is handled entirely by gate 2 (groundedness)
    before this function is ever called.
    """
    if not surviving or not citations:
        return 0.0
    return 1.0 if all(c.source_id for c in citations) else 0.0


async def guard(
    *,
    question: str,
    draft_sentences: list[str],
    citations: list[Citation],
    confidence: float | None = None,
    run_id: str,
    profile_id: str,
    audit_db: Any = None,
    step_index: int = 0,
) -> AgentTerminal:
    """Run the four-step guard order and return a schema-validated terminal.

    Order (skills/asclexis-guardrails, guardrails/guard.py docstring):
      1. Advice gate on the DRAFT (the question itself is also checked
         pre-model by the same classifier, at the top of ``run_agent`` —
         see graph.py). Any advice-seeking sentence -> ``escalate`` with the
         FIXED template; the model's drafted prose is discarded, never sent.
      2. Groundedness mapping -> drop sentences with no real source handle.
         Zero survivors -> ``abstain`` (FIXED template).
      3. Confidence threshold (``CONFIDENCE_THRESHOLD``) -> below -> abstain
         (FIXED template). No hedging — abstention is the only safe output
         below threshold.
      4. Emit ``agent.guard`` recording which gate fired + drop counts
         (handles/counts only — no raw PHI, per audit.py's contract).

    ``confidence`` may be passed explicitly (e.g. by tests exercising the
    threshold gate directly); when omitted it is derived mechanically from
    the surviving citations' handles via ``groundedness_confidence`` (see
    that function's docstring for why this is NOT a survival ratio).
    """
    gate_fired: Literal["advice", "groundedness", "confidence", "none"] = "none"
    dropped_for_advice: list[str] = []

    # --- 1. advice gate on the draft -----------------------------------
    for sentence in draft_sentences:
        verdict = classify_advice(sentence)
        if verdict.is_advice_seeking:
            gate_fired = "advice"
            dropped_for_advice = list(draft_sentences)
            break

    if gate_fired == "advice":
        terminal = AgentTerminal(
            terminal="escalate", text=ESCALATE_TEMPLATE, citations=[], run_id=run_id
        )
        await _emit_guard_audit(
            run_id=run_id,
            profile_id=profile_id,
            step_index=step_index,
            gate_fired=gate_fired,
            terminal=terminal.terminal,
            surviving_count=0,
            dropped_count=len(dropped_for_advice),
            audit_db=audit_db,
        )
        return terminal

    # --- 2. groundedness mapping ----------------------------------------
    mapping = map_sentences(draft_sentences, citations)

    if not mapping.surviving:
        gate_fired = "groundedness"
        terminal = AgentTerminal(
            terminal="abstain", text=ABSTAIN_TEMPLATE, citations=[], run_id=run_id
        )
        await _emit_guard_audit(
            run_id=run_id,
            profile_id=profile_id,
            step_index=step_index,
            gate_fired=gate_fired,
            terminal=terminal.terminal,
            surviving_count=0,
            dropped_count=len(mapping.dropped),
            audit_db=audit_db,
        )
        return terminal

    # --- 3. confidence threshold -----------------------------------------
    effective_confidence = (
        confidence
        if confidence is not None
        else groundedness_confidence(mapping.surviving, mapping.citations)
    )

    if effective_confidence < CONFIDENCE_THRESHOLD:
        gate_fired = "confidence"
        terminal = AgentTerminal(
            terminal="abstain", text=ABSTAIN_TEMPLATE, citations=[], run_id=run_id
        )
        await _emit_guard_audit(
            run_id=run_id,
            profile_id=profile_id,
            step_index=step_index,
            gate_fired=gate_fired,
            terminal=terminal.terminal,
            surviving_count=len(mapping.surviving),
            dropped_count=len(mapping.dropped),
            audit_db=audit_db,
        )
        return terminal

    # --- 4. answer (all gates passed) ------------------------------------
    terminal = AgentTerminal(
        terminal="answer",
        text=" ".join(mapping.surviving),
        citations=mapping.citations,
        run_id=run_id,
    )
    await _emit_guard_audit(
        run_id=run_id,
        profile_id=profile_id,
        step_index=step_index,
        gate_fired="none",
        terminal=terminal.terminal,
        surviving_count=len(mapping.surviving),
        dropped_count=len(mapping.dropped),
        audit_db=audit_db,
    )
    return terminal


async def _emit_guard_audit(
    *,
    run_id: str,
    profile_id: str,
    step_index: int,
    gate_fired: str,
    terminal: str,
    surviving_count: int,
    dropped_count: int,
    audit_db: Any,
) -> None:
    """Emit the ``agent.guard`` audit event — handles/counts only, no raw PHI."""
    await emit_audit_event(
        AgentAuditEvent(
            run_id=run_id,
            node="guard",
            profile_id=profile_id,
            event_type="agent.guard",
            action=f"guard:{terminal}",
            step_index=step_index,
            details={
                "gate_fired": gate_fired,
                "terminal": terminal,
                "surviving_count": surviving_count,
                "dropped_count": dropped_count,
            },
        ),
        db=audit_db,
    )
