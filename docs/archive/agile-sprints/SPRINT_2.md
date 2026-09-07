# Sprint 2 — The loop closes (07-06 → 07-12)

> Historical Reference: this sprint record is retained for history and is not an active tracker; the sprint completed and is not maintained going forward. For active remaining work, use [`docs/features/TASK_LIST.md`](../../features/TASK_LIST.md).

**Last Updated:** 2026-06-24
**Owner:** [Owner]
**Refresh Trigger:** S2 story scope/AC changes, step-budget value, or run-log shape moves
**Release:** R1 — **SHIPPED 2026-06-24** (commit fbb4fe7) · **Epic:** E1 · **Phase:** [PHASE_2](../prd-phases/PHASE_2_loop.md)

## Goal
Multi-step reflect with a hard budget; replayable runs; the eval-harness skeleton.

## Status: delivered (commit fbb4fe7) — agent suite 30 passed / 12 skipped

## Stories
| ID | Story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| S2-1 | `compute_trend`, `retrieve_chunks`, `lookup_reference`, `check_verification` | each typed + read-only + audited | 5 | **Delivered** — all four implemented + registered. AC deviations: `retrieve_chunks` uses a deterministic text-match fallback (no `Embedding` rows in test fixtures for the real RAG vector retriever); `lookup_reference` reads the master DB directly via `core.database.async_session_maker`, not `ctx.db_session` (profile-scoped). See RECONCILIATION.md R-10, R-11. |
| S2-2 | Reflect node with hard step budget (≤5) | budget exceeded → graceful terminal state | 3 | **Delivered** — `MAX_STEPS=5`; over-budget → graceful abstain (`ABSTAIN_TEMPLATE`); bounded loop as defense-in-depth. |
| S2-3 | Replayability: per-step log reconstructs a run | failed run reproducible from log | 3 | **Delivered** — `graph.replay` reconstructs the terminal from `RunLog.steps` without re-calling any tool; verified by a test that makes `registry.get` raise during replay. |
| S2-4 | Eval harness skeleton + 2 seed cases (1 grounded, 1 abstain) | both pass locally | 2 | **Delivered** — `tests/agent/eval_harness.py` materializes a golden case's vault into an in-memory profile DB and runs `run_agent`; `grounded-ldl-trend` and `abstain-unverified-ldl` both pass. |

## DoR / DoD
- **DoR:** AC + touched-files + proving tests in `test_s2_loop.py`.
- **DoD:** green CI; each new tool/node audited; flag-off regression green; proof
  bundle passes. **R1 exit criteria met** (AGILE_PLAN §5): one tool end-to-end,
  audited, flag off = no change. — **MET.** All four S2 stories delivered;
  RELEASE_CHECKLIST rows 1, 2, 8 (R1's backing rows) flipped `[x]` at this close-out.
  **R1 SHIPS.**

## Test-coverage plan
- **Eval axes:** axis 1 (groundedness) + axis 3 (abstention correctness — seed
  abstain case). **Guard/answer-path rule:** grounded + abstain + advice-bait
  cases present. **Unit suites:** `test_s2_loop.py` — budget accounting (FR-6) ✓
  live; four tools declare typed schemas (FR-5) ✓ live; over-budget abstain ✓ live;
  run-log replay ✓ live; seed evals ✓ live (3 skip-stubs flipped: over-budget
  abstain, run-log replay, seed evals). `tests/agent/` now 30 passed, 12 skipped
  (was 27/15). Coverage target for S2 code: **≥ 85%**.

## Code templates (committed scaffolds)
- `modules/agent/tools/{compute_trend,retrieve_chunks,lookup_reference,check_verification}.py`
  (typed, read-only; `retrieve_chunks` filters to `Document.status == "verified"`).
- `modules/agent/nodes/reflect.py` (budget), `nodes/draft.py` (grounded draft),
  `state.py` (`RunStep`, `RunLog.budget_exceeded`), `graph.py` (`replay`).
- Golden seeds: `tests/agent/golden/grounded-ldl-trend.json`, `abstain-unverified-ldl.json`.

## Standup / retro pointers
- STANDUP daily; RETRO Sunday. **R1 review:** demo flag-on agent answering a real
  biomarker question with citations; accept/reject S2 stories.
