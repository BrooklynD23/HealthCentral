# D-2 rev 2 Plan — Codex Round 1 Response

**Last Updated:** 2026-10-16
**Owner:** repository owner
**Status:** Applied to [lane D §D-2 rev 2](../../plans/2026-10-15-build-program/lane-D-time-meds-gamification.md). No owner approval is recorded here.
**Refresh Trigger:** a Codex round 2 on D-2 rev 2.

Run: `codex exec -s read-only -C <worktree> -o /tmp/claude-1000/d2-codex.txt ... </dev/null` (exit 0, under the 900 s timeout). Verdict: **REVISE**. Findings: 1 BLOCKER, 3 MAJOR, 1 MINOR. Output: `D2-r1-codex.txt`.

| # | Sev | Finding | Verified? | Action |
|---|---|---|---|---|
| 1 | BLOCKER | Downgrade drops the marker but leaves re-learned local windows, which the pre-D-2 scheduler reads as UTC | **Yes.** `notification_scheduler.py:427-434` prefers stored windows; re-learn writes them | Downgrade clears both windows before dropping the column; `_005` now sets windows + marker before downgrading. Self-found while fixing: a plain `git revert` breaks unlock (vault at an unknown revision; upgrade-on-open `core/migrations.py:171,330` → 500 at `core/auth.py:397-402`). Rollback rewritten as forward-only: revert code, add a clear-windows migration as new head |
| 2 | MAJOR | Hourly cap returns before any profile is visited, so re-learn can wait up to 1 h | **Yes.** `notification_scheduler.py:279-282` | Documented, not changed: while capped no reminder fires and the fallback window is correct. Moving the cap check would change pass bookkeeping for no reminder benefit |
| 3 | MAJOR | `update_adaptive_windows` rewrites every active schedule of the medication, so one unmarked schedule re-learns its marked siblings | **Yes.** `adherence_patterns.py:470-479` | Re-learn now calls `learn_time_window` per unmarked row and commits once; new test `_011` (marked + unmarked schedules, different zones) |
| 4 | MAJOR | Concurrency proven only within one scheduler instance | **Partly.** App runs one uvicorn process (`dev.ps1:799,905`, `main.py:188`, no `--workers`) | Documented single-process serving; work is deterministic and single-commit, so a second process writes identical values. No durable claim row (YAGNI) |
| 5 | MINOR | Cost bound counts queries, not rows | **Yes.** `.all()` over 30 days, `adherence_patterns.py:202-216` | Bound restated: S + 1 queries, ~30 rows per schedule at one dose/day, linear beyond, no cap |

Confirmed by Codex: `core/auth.py` needs no edit (D6 hook `:405-420` already registers on unlock; close hook drains); `013` valid only if D-2 is still first at final rebase (contracts §c).
