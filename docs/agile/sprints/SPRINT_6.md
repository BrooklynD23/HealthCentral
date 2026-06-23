# Sprint 6 — Evals gate CI (08-03 → 08-09)

**Last Updated:** 2026-06-23
**Owner:** [Owner] · **Safety:** [Safety-reviewer]
**Refresh Trigger:** S6 story scope/AC, scoring-axis definitions, or the CI gate condition changes
**Release:** R3 (**R3 core ships**) · **Epic:** E3 · **Phase:** [PHASE_6](../../prd/phases/PHASE_6_evals_ci.md)

## Goal
It provably behaves: 50–100 golden cases, automated 4-axis scoring, a CI gate that
fails on advice leakage or groundedness drop.

## Stories
| ID | Story | Acceptance criteria | Pts |
|---|---|---|---|
| S6-1 | Golden set to 50–100 cases with synthetic vault states | coverage across panels + edge cases | 5 |
| S6-2 | Automated scoring of all 4 axes | groundedness/citation/abstention/advice scored numerically | 5 |
| S6-3 | `.github/workflows` job fails PR on advice leakage > 0 or groundedness < 100% | red PR on a planted regression | 3 |

## DoR / DoD
- **DoR:** AC + touched-files + proving tests in `test_s6_evals.py`. Branch name for
  the CI trigger resolved (RECONCILIATION R-1).
- **DoD:** green CI; the gate is **seen to fail** on a planted regression then pass;
  scorers are scripts (no eyeballing); proof bundle passes. **R3 core exit met.**

## Test-coverage plan
- **Eval axes:** **all four scored numerically and gating** — groundedness (<100%
  fails), citation accuracy, abstention (≥95%), advice leakage (zero tolerance, whole
  run fails on any). This is the sprint that turns the axes into a gate.
- **Guard/answer-path rule:** the 50–100 set spans grounded, abstain, advice-bait,
  mixed/partial across panels.
- **Unit suites:** `test_s6_evals.py` — golden cases well-formed ✓ live; set not
  all-happy-path ✓ live; advice-bait demands zero leakage ✓ live; skip-marked: set
  size 50–100, four-axis scoring, CI-gate-fails-on-regression. Coverage target: **≥ 90%**.

## Code templates (committed scaffolds)
- CI: new `agent-evals` job in `.github/workflows/ci.yml` (see Phase 6) +
  `scripts/score_agent_evals.py` (scorer — to be added in S6-2; report JSON stays out
  of repo root per `repo_hygiene_check.py`).
- Golden growth under `tests/agent/golden/` (descriptive names only).

## Standup / retro pointers
- STANDUP daily; RETRO Sunday — iteration Q1 ("did the eval set catch what mattered?"):
  the growth loop starts here. Any real miss → first story next sprint reproduces it.
