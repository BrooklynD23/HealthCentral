# Sprint 6 — Evals gate CI (08-03 → 08-09)

**Last Updated:** 2026-06-24 (S6 close-out — R3 core complete, CI workflow pending approval)
**Owner:** [Owner] · **Safety:** [Safety-reviewer]
**Refresh Trigger:** S6 story scope/AC, scoring-axis definitions, or the CI gate condition changes
**Release:** R3 (**R3 core complete — CI workflow pending approval**) · **Epic:** E3 · **Phase:** [PHASE_6](../../prd/phases/PHASE_6_evals_ci.md)

## Goal
It provably behaves: 50–100 golden cases, automated 4-axis scoring, a CI gate that
fails on advice leakage or groundedness drop.

## Stories
| ID | Story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| S6-1 | Golden set to 50–100 cases with synthetic vault states | coverage across panels + edge cases | 5 | **Delivered** (commit 1571927) — grown 30→58 (grounded 18 / advice-bait 15 / abstain 14 / mixed 11); `test_s6_1_golden_set_size` live. |
| S6-2 | Automated scoring of all 4 axes | groundedness/citation/abstention/advice scored numerically | 5 | **Delivered** (commit 1571927) — `src/backend/modules/agent/eval/scorer.py`; `test_s6_2_four_axis_scoring` live, all axes at bar. |
| S6-3 | `.github/workflows` job fails PR on advice leakage > 0 or groundedness < 100% | red PR on a planted regression | 3 | **Logic delivered** (commit 1571927) — runnable gate script `scripts/agent_eval_gate.py`; `test_s6_3_ci_gate_fails_on_regression` live (plants a regression, asserts fail, then asserts clean pass). **The `.github/workflows` wrapper itself is NOT added — pending user approval.** This is the sole remaining R3 item. |

## DoR / DoD
- **DoR:** AC + touched-files + proving tests in `test_s6_evals.py`. Branch name for
  the CI trigger resolved (RECONCILIATION R-1).
- **DoD:** green CI; the gate is **seen to fail** on a planted regression then pass;
  scorers are scripts (no eyeballing); proof bundle passes. **R3 core exit met.**
  **Close-out note (2026-06-24):** the gate-fails-on-regression behavior is
  proven (`test_s6_3_ci_gate_fails_on_regression` plants a regression locally
  and the script exits 1, then exits 0 clean) — but "green CI" in the literal
  sense (an actual `.github/workflows` job gating real PRs) is not yet true,
  because that workflow has not been added: it is **pending user approval**.
  R3 core (golden set + scorer + gate logic) is complete; R3 the release is
  **PENDING** until the workflow lands. See RELEASE_CHECKLIST row 5 and the
  R3 exit-criteria note.

## Test-coverage plan
- **Eval axes:** **all four scored numerically and gating** — groundedness (<100%
  fails), citation accuracy, abstention (≥95%), advice leakage (zero tolerance, whole
  run fails on any). This is the sprint that turns the axes into a gate.
- **Guard/answer-path rule:** the 50–100 set spans grounded, abstain, advice-bait,
  mixed/partial across panels.
- **Unit suites:** `test_s6_evals.py` — golden cases well-formed ✓ live; set not
  all-happy-path ✓ live; advice-bait demands zero leakage ✓ live; **all three
  previously skip-marked tests now live**: `test_s6_1_golden_set_size` (50–100 +
  category coverage), `test_s6_2_four_axis_scoring` (all axes at bar),
  `test_s6_3_ci_gate_fails_on_regression` (plants a regression, asserts the
  gate fails, then asserts a clean pass). Agent suite: **46 passed, 0
  skipped** (was 43/3). Coverage target: **≥ 90%**, met.

## Code templates (committed scaffolds)
- CI: new `agent-evals` job in `.github/workflows/ci.yml` (see Phase 6) +
  `scripts/score_agent_evals.py` (scorer — to be added in S6-2; report JSON stays out
  of repo root per `repo_hygiene_check.py`).
- Golden growth under `tests/agent/golden/` (descriptive names only).

## Standup / retro pointers
- STANDUP daily; RETRO Sunday — iteration Q1 ("did the eval set catch what mattered?"):
  the growth loop starts here. Any real miss → first story next sprint reproduces it.

## Close-out (2026-06-24, commit 1571927)
S6-1/S6-2 fully delivered; S6-3's gate-script LOGIC delivered and proven
(regression-fails, clean-passes). The remaining R3 item — the actual
`.github/workflows` job that wraps `scripts/agent_eval_gate.py` and fails a
real PR — is **pending user approval**, not yet added. R-14 (golden set never
exercised an end-to-end composed-then-dropped sentence) is RESOLVED by
`scorer.score_composed_drop_case()`. See STANDUP, RETRO, and RECONCILIATION
for full close-out detail; RELEASE_CHECKLIST row 5 reflects R3 as **PENDING**,
not shipped.
