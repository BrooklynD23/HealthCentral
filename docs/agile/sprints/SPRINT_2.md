# Sprint 2 — The loop closes (07-06 → 07-12)

**Last Updated:** 2026-06-23
**Owner:** [Owner]
**Refresh Trigger:** S2 story scope/AC changes, step-budget value, or run-log shape moves
**Release:** R1 (**R1 ships**) · **Epic:** E1 · **Phase:** [PHASE_2](../../prd/phases/PHASE_2_loop.md)

## Goal
Multi-step reflect with a hard budget; replayable runs; the eval-harness skeleton.

## Stories
| ID | Story | Acceptance criteria | Pts |
|---|---|---|---|
| S2-1 | `compute_trend`, `retrieve_chunks`, `lookup_reference`, `check_verification` | each typed + read-only + audited | 5 |
| S2-2 | Reflect node with hard step budget (≤5) | budget exceeded → graceful terminal state | 3 |
| S2-3 | Replayability: per-step log reconstructs a run | failed run reproducible from log | 3 |
| S2-4 | Eval harness skeleton + 2 seed cases (1 grounded, 1 abstain) | both pass locally | 2 |

## DoR / DoD
- **DoR:** AC + touched-files + proving tests in `test_s2_loop.py`.
- **DoD:** green CI; each new tool/node audited; flag-off regression green; proof
  bundle passes. **R1 exit criteria met** (AGILE_PLAN §5): one tool end-to-end,
  audited, flag off = no change.

## Test-coverage plan
- **Eval axes:** axis 1 (groundedness) + axis 3 (abstention correctness — seed
  abstain case). **Guard/answer-path rule:** grounded + abstain + advice-bait
  cases present. **Unit suites:** `test_s2_loop.py` — budget accounting (FR-6) ✓
  live; four tools declare typed schemas (FR-5) ✓ live; skip-marked: over-budget
  abstain, run-log replay, seed evals. Coverage target for S2 code: **≥ 85%**.

## Code templates (committed scaffolds)
- `modules/agent/tools/{compute_trend,retrieve_chunks,lookup_reference,check_verification}.py`
  (typed, read-only; `retrieve_chunks` filters to `Document.status == "verified"`).
- `modules/agent/nodes/reflect.py` (budget), `nodes/draft.py` (grounded draft),
  `state.py` (`RunStep`, `RunLog.budget_exceeded`), `graph.py` (`replay`).
- Golden seeds: `tests/agent/golden/grounded-ldl-trend.json`, `abstain-unverified-ldl.json`.

## Standup / retro pointers
- STANDUP daily; RETRO Sunday. **R1 review:** demo flag-on agent answering a real
  biomarker question with citations; accept/reject S2 stories.
