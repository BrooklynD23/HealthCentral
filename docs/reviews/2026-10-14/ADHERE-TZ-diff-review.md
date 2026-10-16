# ADHERE-TZ diff — code review

Reviewer: code-reviewer subagent (Opus 5.5), read-only, 2026-10-14. Reviewed the diff before the HIGH-1 response (see the response file). Read the diff and tests; did not run the suite.

**Verdict: APPROVE with 1 HIGH to settle before merge.** Bucketing logic is correct.

| # | Sev | File:line | Finding |
|---|-----|-----------|---------|
| 1 | HIGH | `modules/adherence_patterns.py:498-499`, `modules/notification_scheduler.py:315,427-431,474` | Learned `adaptive_window_*` moved from UTC to local wall time, but the scheduler compares it with UTC `now.time()`. An LA user's 08:00 window would fire at 08:00Z (00:00 PST): a reminder regression. Convert scheduler `now` to profile tz, or get owner sign-off. |
| 2 | MEDIUM | `api/notifications.py:453`, `modules/notification_scheduler.py:529` | Mode #9: `calculate_streak` still uses UTC days there, so learn-patterns and notification streaks can disagree. Track with an ID. |
| 3 | LOW | `modules/adherence_patterns.py:23` | Importing private `_dose_dates` from a sibling module is acceptable; could rename public or use `_local`. |
| 4 | LOW | `modules/adherence_patterns.py:34-36` | `_local` relabels any tzinfo as UTC; unreachable today (column is naive UTC), same as `_dose_dates`. |
| 5 | LOW | `api/medications.py:70-79` | Existing tz helper catches only `ZoneInfoNotFoundError`; a corrupt `""`/`"../x"` row raises `ValueError` (500). Write side rejects these. |

Q1 DST/naive UTC: correct, per-dose offsets, test 001 crosses DST. Q2 missed sites: none in the module; remaining `utcnow()` uses are UTC cutoffs/`valid_until`.

Test blind spots: no scheduler test after a learned window; LA only (no positive/half-hour offset, no near-midnight window — pre-existing wrap bug); test 001 has stdev 0; no notifications streak test; test 006 skips the `ValueError` path.
