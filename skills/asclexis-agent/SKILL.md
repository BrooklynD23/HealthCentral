---
name: asclexis-agent
description: Conventions for building and editing the HealthCentral agent in the fix/agent-overhaul branch. Use whenever creating or modifying anything under src/backend/modules/agent/ — the graph runner, nodes (plan/act/reflect/draft), the tool registry, the read-only tools over the profile vault, the step budget, or audit hooks. Triggers include any work mentioning "agent loop", "plan act reflect", "tool registry", "agent node", "step budget", or wiring the agent into the /assistant/ route.
---

# HealthCentral Agent — build conventions

This skill governs the agent graph. The companion `AGILE_PLAN.md` (docs/agile)
owns *what* to build and when; this owns *how*. The single most important rule is
below — everything else serves it.

## The one inviolable rule

**The agent is READ-ONLY over clinical data.** It may read observations, trends,
chunks, and curated references. It may NEVER write observations, interpretations,
medications, or any clinical row. Only the existing human-verification flow writes
clinical data. Any request to give the agent write capability is a NEW epic, never
a story inside the agent epic — do not bend this rule to ship faster.

## Graph shape

`plan → act → reflect → (loop | draft) → guard → terminal`. Keep it a small
hand-rolled state machine in `modules/agent/graph.py` — no LangGraph dependency
unless the client explicitly approves it (local-first footprint stays clean).

- **plan**: choose the next tool + typed args, or decide enough evidence exists.
- **act**: execute exactly one tool call; never batch.
- **reflect**: "do I have grounding for an answer yet?" → loop or proceed.
- **draft**: compose answer; every sentence must carry a source handle.
- **guard**: owned by `asclexis-guardrails`; the agent calls it, never inlines it.
- **terminal**: `answer | abstain | escalate` — all three are first-class successes.

## Tool registry

Every tool registers with a Pydantic input AND output schema in
`modules/agent/tools/`. Malformed args fail validation and are NEVER executed —
this is the first guardrail layer, not an afterthought. Current read-only tools:
`query_observations`, `compute_trend`, `retrieve_chunks`, `lookup_reference`,
`check_verification`. New tools must be read-only and profile-scoped to the
unlocked vault session.

## Step budget & replay

- Hard cap: ≤ 5 tool calls per question. Exceeding it is a graceful terminal
  (`abstain` with "insufficient evidence within budget"), never a crash or a spin.
- Every node appends a structured step to a run log so any failed run is
  reconstructable. Replayability is a feature requirement, not a debug nicety.

## Audit (non-negotiable)

Every node emits a structured event through the existing `monitoring/` + security
audit logging — plan choices, tool calls + args, guard decisions, terminal state.
The audit trail IS the governance deliverable. A node with no audit event is not done.

## Feature flag

All agent behavior sits behind `agent_enabled` in model settings. When off,
`/assistant/` MUST behave exactly as the legacy single-shot path. Verify both
states before marking any agent story done.

## Verify before done

`PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest src/backend/tests/agent/`;
audit-emission assertion passes; flag-off regression passes; run log replays.

## Never

Write clinical data · batch tool calls · skip the typed output schema · inline the
guard logic · let the loop exceed budget · ship a node without an audit event ·
call an external LLM without the redaction gate (see `asclexis-guardrails`).
