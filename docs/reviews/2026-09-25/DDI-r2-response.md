# DDI round 2 — response (L1-A, 2026-10-04)

Codex verdict: **REVISE** (1 BLOCKER, 8 MAJOR, 1 MINOR). Output: [DDI-r2-codex.txt](DDI-r2-codex.txt). Round 2 is the last round allowed; the plan was amended and not re-reviewed. Each finding was checked against the repo first.

| # | Finding | Disposition | Evidence / change |
|---|---|---|---|
| 1 | [BLOCKER] r1 rejection wrong: W3-SEC-SCHED does not approve editing `recurring-failures.md` | **Accepted (conservative)** | Owner-decisions approvals are verbatim scope. The plan no longer edits `recurring-failures.md`; the §9 paragraph goes to L0 in the wave report as a proposal. `docs/agentic` added to the Task 3 Step 3 unchanged-paths check. Reverses r1 disposition 1. |
| 2 | [MAJOR] §9 entry not in the fix commit (same-commit rule) | **Moot** | Follows from 1; flagged to L0 that `CLAUDE.md:49-52` and W3-SEC-SCHED conflict for this phase. |
| 3 | [MAJOR] refresh check omits P6 files | **Accepted** | `implementation-program.md:154` orders `core/database.py`, `core/profile_database.py` P1 → S-1 → P6. Added to Task 0 Step 1 diff. |
| 4 | [MAJOR] must rebase, not merge | **Rejected** | `docs/agentic/orchestration.md:24` (the binding process for L1, newer): "each PR after the first merges `origin/main`, re-measures and rewrites the count slots". Program `:137` "rebases" predates it. The plan cites both and follows orchestration. |
| 5 | [MAJOR] failing targeted suite still permits commit | **Accepted** | Step 3 writes `$LOG/green.rc`; Step 5 gate requires it to be `0` and `collect.txt` to end with `1350 tests collected`. |
| 6 | [MAJOR] full-suite command masks rc; bare grep fails under `set -e` | **Accepted** | Captures `rc`, prints it, computes unexpected failures with `|| true`, exits 1 only if any failure other than `test_api_rag_index_002b`. |
| 7 | [MAJOR] Steps 2-4 not self-contained | **Accepted** | Header + `cd "$WT"` blocks added to Steps 2-3; Step 4 states its directory, header and test command. |
| 8 | [MAJOR] whole reviews dir as pathspec | **Accepted** | Exact six `DDI-r1/r2-*` paths listed. |
| 9 | [MAJOR] HC-DDI-001 does not pin cross-profile isolation | **Accepted** | Review Focus 4 narrowed to "another document in the same profile"; cross-profile isolation is structural (one vault per profile) and not claimed. |
| 10 | [MINOR] probe counts lack command | **Accepted** | Finding row 9 now gives both pytest commands; facts 7-8 marked as scratch-probe output reproduced by HC-DDI-001/004. |
