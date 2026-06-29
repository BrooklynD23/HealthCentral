# Sprint 7 — LoRA distillation (stretch) (08-10 → 08-16)

**Last Updated:** 2026-06-23
**Owner:** [Owner]
**Refresh Trigger:** S7 stretch scope accepted/deferred, or the adapter benchmark bar changes
**Release:** R3 (stretch) · **Epic:** E6 · **Phase:** [PHASE_7](../../prd/phases/PHASE_7_lora_stretch.md)

> **Stretch — deferred by default** (PRD §10 Q5). Pulled in only if R3 core is
> accepted early. R1/R2/R3-core never depend on it. Read-only + governance
> invariants unchanged; this only swaps local generation weights, still behind the
> guard node and the eval gate.

## Goal
Smaller, just as safe: distill grounded refusals into a local LoRA adapter that is
≥ base on all four axes.

## Stories
| ID | Story | Acceptance criteria | Pts |
|---|---|---|---|
| S7-1 | Curate a labeled set of the big model's good grounded refusals | dataset versioned | 3 |
| S7-2 | LoRA/PEFT adapter on the local model for the explain+refuse task | adapter loads in llama.cpp pipeline | 5 |
| S7-3 | Benchmark adapter vs base on golden set | adapter ≥ base on all 4 axes | 3 |

## DoR / DoD
- **DoR:** AC + touched-files + the benchmark harness (reuses `score_agent_evals.py`).
- **DoD:** dataset versioned; adapter loads; **adapter ≥ base on every axis with
  advice leakage 0** or it does not ship; proof bundle passes.

## Test-coverage plan
- **Eval axes:** all four, adapter-vs-base, same golden set. The gate is comparative:
  no axis may regress.
- **Unit suites:** dataset-shape validation; adapter-load smoke; benchmark comparison.
  All implementation-stage (no committed scaffold beyond the doc — stretch).
- Coverage target: **≥ 80%** of any new tooling.

## Code templates (committed scaffolds)
- None committed this sprint (stretch). Dataset lands at `data/agent_lora/dataset.vN.jsonl`;
  benchmark reuses `scripts/score_agent_evals.py` from S6.

## Standup / retro pointers
- STANDUP daily; RETRO Sunday — decide keep/defer for the stretch based on R3-core
  acceptance and remaining capacity.
