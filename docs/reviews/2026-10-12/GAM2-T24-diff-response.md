# GAM2-T24 diff — author response to code review

Reviewer: code-reviewer subagent (Opus 5.5), verdict approve. Review: [GAM2-T24-diff-codereview.md](GAM2-T24-diff-codereview.md).

| Finding | Action |
|---|---|
| LOW-1 DST test cannot tell ZoneInfo from a fixed EST offset | Fixed: `test_hc_gam_http_011` adds a dose at `2026-03-20 04:30Z` (Mar 20 00:30 EDT). Break-check: with `America/New_York` forced to a fixed UTC-5 offset in `_dose_dates`, `http_011` fails (1 failed). |
| LOW-2 invalidation tests assert call arguments, not the real key | Fixed differently from the suggestion: seeding a hand-written key would also miss a key-shape change. Both tests now mount the real `useStreaks`/`useBadges` hooks and assert they refetch after the mutation. Break-checks: key changed to `['gamification', profileId, 'streaks']` → 2 failed; streak invalidation removed from dose log and time-zone save → 2 failed. |
| LOW-3 ongoing streak reads 0 until today's dose is logged | Not done: predates this diff (`compute_streak`), needs an owner decision. Follow-up. |
