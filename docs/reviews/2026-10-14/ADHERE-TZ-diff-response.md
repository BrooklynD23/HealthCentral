# ADHERE-TZ diff — author response to code review

| # | Decision | What was done |
|---|----------|---------------|
| 1 | Fixed (conservative) | The route no longer passes the profile tz to `update_adaptive_windows`, so stored adaptive windows stay in the UTC frame the scheduler reads. No reminder timing changes. Comment in `api/medications.py` names follow-up SCHED-TZ (scheduler reads profile-local `now`, then windows move to local). Test 001 now asserts the stored window brackets 15:00Z-16:00Z; mutation (passing tz) fails it: `assert datetime.time(8, 0) > datetime.time(16, 0)`. Fixing the scheduler was out of scope (owner: list other sites, do not fix). |
| 2 | Deferred, tracked | ID STREAK-TZ, recorded in `docs/agentic/recurring-failures.md` mode #9 with SCHED-TZ. |
| 3 | No change | Same package, existing helper; avoids a further copy of the conversion. |
| 4 | No change | Unreachable: `taken_at` is naive UTC (MED-UTC). |
| 5 | Deferred | Pre-existing helper shared with DOSE-VAR; write side validates. Not touched to keep the diff surgical. |

Blind spots: scheduler and notifications-streak gaps are the SCHED-TZ/STREAK-TZ follow-ups; others accepted for this PR.
