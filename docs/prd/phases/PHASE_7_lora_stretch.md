# Phase 7 — LoRA Distillation (stretch)

**Last Updated:** 2026-06-23
**Owner:** [Owner]
**Refresh Trigger:** Stretch scope is accepted/deferred, or the adapter benchmark bar changes

| Map | Value |
|---|---|
| Release | **R3 — Measured & tuned** (stretch) |
| Epic | **E6 — Fine-tuning (stretch)** |
| Sprint | **S7** (S7-1…S7-3) |
| Binding skills | `healthcentral-evals`, `healthcentral-backend` |

## Objective
Distill the big model's good grounded-refusal behavior into a small local LoRA adapter so
the offline default is smaller and **just as safe** — gated by the same golden set, never
weaker on any axis.

> **Stretch.** Deferred by default (PRD §10 open question 5). R1/R2 and R3-core do not
> depend on this. Read-only and governance invariants are unchanged; this only swaps the
> local generation weights, still behind the guard node and the eval gate.

## Exit criteria
- Curated, **versioned** dataset of the big model's good grounded refusals (S7-1).
- LoRA/PEFT adapter loads in the llama.cpp pipeline (S7-2).
- Adapter **≥ base on all four axes** on the golden set (S7-3) — if it regresses any axis,
  it does not ship.

## CONTRACTS

### API / routes
No new routes; `endpoints.md` diff: **none**. Adapter selection lives in model settings
(tier routing, not hardcoded — backend skill).

### Data-shape — distillation dataset
`data/agent_lora/dataset.vN.jsonl` (versioned), each row: `{question, vault_state,
grounded_refusal_or_answer, terminal}`. Sourced only from cases the big model handled
correctly (the eval suite is the labeler).

### Benchmark contract
Reuses `scripts/score_agent_evals.py` (Phase 6) — adapter vs base, same golden set, same
four axes. Adapter ships only if `adapter_axis >= base_axis` for **every** axis and
advice_leakage stays 0.

### Audit-event schema
Generation node records `model_variant: Literal["base","lora"]` in `agent.act`/`agent.terminal`
details so runs are attributable to the weights that produced them.

## CONTACTS (RACI)
| Role | Who |
|---|---|
| Responsible | [Owner] |
| Accountable | [Owner] |
| Consulted | [Safety-reviewer] (no axis regression), [Reviewer] (llama.cpp integration) |
| Informed | [Reviewer] |

## Dependencies
Phase 6 (the eval suite is both the labeler and the acceptance gate for the adapter).

## Risk + mitigation
| Risk | Mitigation |
|---|---|
| Adapter erodes safety to gain speed | Hard rule: ≥ base on all four axes or it doesn't ship |
| Local footprint grows | Adapter is small (PEFT); base stays the fallback tier |
| Stretch crowds out R3 core | Deferred by default; only pulled in if R3 core is accepted early |
