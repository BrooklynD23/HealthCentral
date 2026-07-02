# AI / LLM Pipeline & Safety

**Owner:** Project Lead
**Refresh Trigger:** New model tier added, or an agent phase/sprint status changes

## Scope

The local-first LLM provider layer (`core/llm/`), hardware-tier model selection, RAG/grounding
pipeline, the hand-rolled agent state machine (`modules/agent/` — **not** LangGraph), and its
guardrails (groundedness, redaction gate, PHI gate).

## Start here

- [`docs/04_local_models_inference_plan.md`](../04_local_models_inference_plan.md) — inference architecture
- [`docs/model_tiers/README.md`](../model_tiers/README.md) — hardware-tier overview
  ([tier1_low](../model_tiers/tier1_low.md) · [tier2_mid](../model_tiers/tier2_mid.md) · [tier3_high](../model_tiers/tier3_high.md))
- [`docs/prd/PRD_agent_overhaul.md`](../prd/PRD_agent_overhaul.md) — active PRD driving the agent phases below
- [`docs/prd/phases/`](../prd/phases/) — `PHASE_0_foundation.md` through `PHASE_7_lora_stretch.md` (Phase 7 is an explicit stretch goal, deferred pending sign-off)
- [`docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md`](../plans/2026-06-30-tech-upgrade-survey-9-areas.md) — open-source tech survey (faithfulness/NLI, retrieval, redaction, OCR, agent orchestration)
- [`../../skills/healthcentral-agent/SKILL.md`](../../skills/healthcentral-agent/SKILL.md), [`../../skills/healthcentral-guardrails/SKILL.md`](../../skills/healthcentral-guardrails/SKILL.md), [`../../skills/healthcentral-evals/SKILL.md`](../../skills/healthcentral-evals/SKILL.md) — project skills for this domain

## Related roles

- [`security-and-compliance.md`](security-and-compliance.md) — PHI redaction, no-medical-advice invariants
- [`data-and-migrations.md`](data-and-migrations.md) — where embeddings/observations/memory live
