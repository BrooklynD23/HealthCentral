# Release Checklist — Agent Overhaul

**Last Updated:** 2026-06-24
**Owner:** [Owner] (accepts stories at review)
**Refresh Trigger:** A backing story is accepted/rejected, or a Report 0 dimension changes

> Seeded directly from **audience Report 0's executive comparison matrix**
> (`audience_expectations_main_vs_branch.md`). That matrix doubles as the
> acceptance gate: **a row is `true` only when its backing story in
> `AGILE_PLAN.md` is accepted** at review. No new metrics are invented here — these
> are the same dimensions the audience was promised. Update the Status box at
> acceptance, not at code-complete.
>
> Status legend: `[ ]` not started · `[~]` in progress · `[x]` accepted ·
> `(gated)` = unproven until its eval/CI gate is green.

| # | Report 0 dimension (target) | Backing stories | Release | Status |
|---|---|---|---|---|
| 1 | Plan→act→reflect loop, up to 5 read-only lookups | S1-3, S2-2 | R1 | `[ ]` |
| 2 | Combines multiple values / trends / references | S2-1, S1-3 | R1 | `[ ]` |
| 3 | Mechanical guard node: advice gate ×2, unmapped-claim drop, abstain/escalate | S3-1, S3-2, S3-3 | R2 | `[ ]` |
| 4 | First-class **abstain / escalate** behavior | S3-3, S3-4 | R2 | `[ ]` *(gated)* |
| 5 | Golden eval suite, 4 axes, CI gate | S6-1, S6-2, S6-3 | R3 | `[ ]` *(gated)* |
| 6 | Local-first + explicit PHI redaction gate + offline-verified loop | S4-1, S4-2 | R2 | `[ ]` |
| 7 | Speed capped + cached; p95 ≤ main + 50% | S2-2, S5-2, S5-3 | R2 | `[ ]` |
| 8 | Every agent decision emits a structured audit event | S0-3, S1-4 (+ per-node throughout) | R1 | `[~]` *(S0-3 persistence helper done & tested; per-node emission from S1-4 onward still pending)* |
| 9 | Behind a flag; legacy path kept one release (rollback safety) | S0-2, S5-1 | R2 | `[~]` *(S0-2 flag helper done, defaults OFF, tested; no live caller wired yet — S5-1 cutover pending, see RECONCILIATION R-8)* |

## Success-metric gates (AGILE_PLAN §1 — release-level, do not redefine)
These are the numeric bars the gated rows above must clear before flipping `true`:

| Metric | Target | Backing | Status |
|---|---|---|---|
| Groundedness rate | 100% of answer sentences map to a source | eval axis 1 (S6-2) | `[ ]` |
| Advice leakage | 0 across the golden set | eval axis 4, zero-tolerance (S6-3) | `[ ]` |
| Abstention correctness | ≥ 95% on insufficient-evidence cases | eval axis 3 (S6-2) | `[ ]` |
| p95 local latency | ≤ single-shot path + 50% | LLMOps timing (S5-3) | `[ ]` |
| Offline operation | full loop runs network-disabled | S4-2 + CI | `[ ]` |
| Audit completeness | every node emits a structured event | audit assertion (S1-4) | `[ ]` |

## Release exit criteria (AGILE_PLAN §5 — fixed for R1/R2)
- **R1 (S0–S2):** one tool end-to-end, audited, flag off = no change. → rows 1, 2, 8.
- **R2 (S3–S5):** guard node enforces; `/assistant/` served by agent; cache on. →
  rows 3, 4, 6, 7, 9.
- **R3 (S6–S7):** evals gate CI; (stretch) LoRA ≥ base on golden set. → row 5 + metric gates.
