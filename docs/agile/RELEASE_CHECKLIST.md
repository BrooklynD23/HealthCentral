# Release Checklist — Agent Overhaul

**Last Updated:** 2026-06-24 (S3 close-out)
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
| 1 | Plan→act→reflect loop, up to 5 read-only lookups | S1-3, S2-2 | R1 | `[x]` *(S2-2 lands the real plan→act→reflect→(loop\|draft)→guard→terminal loop with a hard MAX_STEPS=5 budget; over-budget → graceful abstain. Verified by `test_s2_loop.py`'s over-budget-abstains-gracefully assertion, now live.)* |
| 2 | Combines multiple values / trends / references | S2-1, S1-3 | R1 | `[x]` *(S2-1 lands `compute_trend` (trend, each point cites `observation_id`), `lookup_reference` (master-DB reference ranges), `retrieve_chunks` (verified-doc chunks), and `check_verification` (status/count only) — all typed, read-only, audited, registered. The seed eval `grounded-ldl-trend` exercises the multi-tool combination live.)* |
| 3 | Mechanical guard node: advice gate ×2, unmapped-claim drop, abstain/escalate | S3-1, S3-2, S3-3 | R2 | `[x]` *(S3-1 advice classifier shared by both call sites — pre-model on the question, short-circuits to `escalate` with the fixed `ESCALATE_TEMPLATE`, zero tools/prose; and on the draft inside `guard()`. S3-2 groundedness mapping drops unmapped sentences mechanically. S3-3 guard node runs the 4-step order and replaced `graph.py`'s S2 passthrough. All behaviorally implemented and unit-tested live in `test_s3_guardrails.py`. Note: this is the **mechanism**, proven on unit fixtures — the zero-tolerance CI eval gate over the full golden set is S6/R3 scope, see row 5 and metric gates below.)* |
| 4 | First-class **abstain / escalate** behavior | S3-3, S3-4 | R2 | `[~]` *(S3-3 terminal schema (`answer\|abstain\|escalate`) and S3-4 confidence-threshold abstain (fixed `ABSTAIN_TEMPLATE`, never hedged) are both implemented and unit-tested. Kept `[~]` rather than `[x]`: one golden case (`mixed-partial-grounding`) does not yet resolve end-to-end through `run_agent` — a planner analyte-detection gap, not a guard defect, see RECONCILIATION R-12 — and the abstention-correctness metric gate is still S6-scoped against the full ~30/50-100 golden set, not just the 6 seed fixtures that exist today.)* |
| 5 | Golden eval suite, 4 axes, CI gate | S6-1, S6-2, S6-3 | R3 | `[ ]` *(gated)* |
| 6 | Local-first + explicit PHI redaction gate + offline-verified loop | S4-1, S4-2 | R2 | `[ ]` |
| 7 | Speed capped + cached; p95 ≤ main + 50% | S2-2, S5-2, S5-3 | R2 | `[ ]` |
| 8 | Every agent decision emits a structured audit event | S0-3, S1-4 (+ per-node throughout) | R1 | `[x]` *(S0-3 persistence helper + S1-4 per-node emission both done & tested — plan/act/draft each emit exactly one audit event per run, verified by `test_s1_first_tool.py`; S2 extends coverage to reflect (`agent.reflect`) and terminal (`agent.terminal`) plus the four new tools, each self-auditing per Phase 2's audit-event schema. Still confirmed live via `test_s1_first_tool.py` + `test_s2_loop.py`.)* |
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
| Audit completeness | every node emits a structured event | audit assertion (S1-4) | `[x]` *(asserted live in `test_s1_first_tool.py` for plan/act/draft; remaining nodes — reflect, guard — land in S2/S3)* |

## Release exit criteria (AGILE_PLAN §5 — fixed for R1/R2)
- **R1 (S0–S2):** one tool end-to-end, audited, flag off = no change. → rows 1, 2, 8.
  **R1 SHIPPED 2026-06-24** — all three backing rows (1, 2, 8) accepted `[x]` at S2
  close-out (commit fbb4fe7). Exit criteria met: plan→act→reflect→draft loop closes
  with a hard 5-step budget and graceful abstain; multi-tool trend/reference
  combination is live; every node (plan/act/reflect/draft + the four S2 tools) emits
  a structured audit event. Note: the eval harness (S2-4) exists and the two seed
  cases pass locally, but the **CI eval gate is S6/R3 scope** — row 5 and the
  success-metric gates below remain `[ ]`/`(gated)` until S6 wires them into CI.
- **R2 (S3–S5):** guard node enforces; `/assistant/` served by agent; cache on. →
  rows 3, 4, 6, 7, 9.
- **R3 (S6–S7):** evals gate CI; (stretch) LoRA ≥ base on golden set. → row 5 + metric gates.
