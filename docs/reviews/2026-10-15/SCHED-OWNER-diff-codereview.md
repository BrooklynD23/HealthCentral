# SCHED-OWNER diff code review

Reviewer: code-reviewer subagent (Opus 5.5), 2026-10-15. Diff: `_schedule_for_medication` guard in `src/backend/api/medications.py` used by `log_dose` and `learn_patterns`; HTTP tests `test_hc_med_http_012`–`015`. Read-only review; reviewer ran no tests.

Verdict: **APPROVE.** No CRITICAL or HIGH findings.

## What was verified
| Check | Result |
|---|---|
| Guard before any write in `log_dose` | Yes. Runs before `profile_db.add`/`commit`; test 012 asserts zero dose rows. |
| Guard before any write in `learn_patterns` | Yes. Runs before `learn_all_patterns`/`save_patterns`/`update_adaptive_windows`. |
| Order vs 404/403 | 422 only after the medication is found and access verified; reveals nothing new. |
| Unknown `schedule_id` | Unchanged (201, stored as-is, no variance). Pinned by test 014. |
| Profile data access | Only through the route's `ProfileDbSession`. |
| Other routes taking `schedule_id` | PATCH/DELETE `/{medication_id}/schedules/{schedule_id}` already filter by `medication_id`. No other route in `api/` takes a client schedule id. |
| Status code | 422 fits: 400 in this file means malformed input; 422 means well-formed but semantically invalid (as `api/search.py`, `api/model_settings.py`). 404 would contradict accepting unknown ids. |

## Findings
| # | Sev | Where | Issue | Fix |
|---|---|---|---|---|
| 1 | MEDIUM | test 015 | `leaked == 0` could never fail: no doses seeded, learner needs ≥7 samples, and missed-days/streak rows use `schedule_id=None`. Only the 422 assertion caught the bug. | Seed ≥7 recent doses on med A tagged `sched_b`. |
| 2 | LOW | `learn_patterns` | Unknown `schedule_id` can still yield `AdherencePattern` rows with a dangling id (if doses carry the same dangling id). Consistent with the decision. | Record for any later "reject unknown ids" change; cover both routes together. |
| 3 | LOW | test 015 | No test for learn-patterns without `schedule_id`. | Add an unscoped call asserting 200. |
| 4 | LOW | audit | Neither route audits today; pre-existing, not introduced. | Track separately. |
