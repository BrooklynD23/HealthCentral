VERDICT up front: **approve** — 0 CRITICAL, 0 HIGH, 0 MEDIUM, 3 LOW. Fixing the LOWs is optional and does not block merge.

# GAM2-T24 diff code review: commit 7c1c6c4 (base 4884d38)

Scope reviewed: `git diff 4884d38..7c1c6c4`, 15 files, +333/-21. Plan: `audit/2026-09-25/waves/scaffold/GAMIFICATION-V2.md` §2a items 1-5, §2b design A, tasks 2 and 4. I ran no test suites, as instructed. I took the author's results as given: backend 1480 passed / 1480 collected; touched vitest files 19 passed; tsc and lint clean.

## Checks

| Check | Result | Evidence |
|---|---|---|
| Window arithmetic (28 days, ends on as_of) | correct | `modules/streak_engine.py:69-77`. Ages are computed as `date - date` on calendar dates that are already in the profile tz, so DST cannot shift them. `0 <= age < 28` covers the window, and `age // 7` puts each day in one of weeks 0..3 |
| Future doses | excluded | negative ages are filtered out. Test 010 covers this with a Mar 5 dose when as_of is Mar 4 |
| Profile tz | used | `api/gamification.py:174-176` passes `timezone_name` and the as_of date in the profile tz |
| Skipped doses / ended-medication rule | unchanged | excluded by the SQL filter (Q2 shipped in #83) and again by `_dose_dates` |
| Profile isolation | holds | the query is scoped by `Medication.profile_id`. Test 010 seeds PROFILE_B on Feb 27. If isolation broke, that dose would make active days 5 instead of 4, so the test would fail |
| Audit invariant | unchanged | `_audit_view(... "gamification.streaks.view" ...)` is still called after the response is built |
| Route tests via HTTP | yes | `_get` → `tests/support/routes.py::route_client` |
| Copy is non-advisory | yes | "New streak starts today", "All medications", and "Streak days are counted in UTC. Set your time zone in Settings." None of these give dosing advice, use loss framing or say "you missed". The caution tint was already off at 0 (`StreakDisplay.tsx:22,28`) |
| framer-motion mock | OK | `Gamification.test.tsx:9-24` already has the prop-filtering Proxy mock. `GamificationService.test.tsx` renders hooks only (no `motion.*`), so it needs no mock |
| `/settings` link target | exists | `App.tsx:129` `<Route path="settings">`. The widget is mounted inside the router at `pages/MedicationCoach.tsx:362` |
| Count lines | consistent | `CLAUDE.md` and `AGENT.md` both say 1477 → 1480, which matches the 3 new backend tests (010, 011, 012) |
| Simplicity | good | `compute_engagement` is 3 lines and reuses `_dose_dates`. Nothing new is stored, there is no migration and no new component (`StreakDisplay` is reused). The query keys carry `profileId` and invalidation uses a prefix match, as the plan says |

## Mutation sensitivity: would each new test fail if the behavior broke?

| Mutation | Caught by |
|---|---|
| Window `< 28` → `<= 28` or `< 27` | test 010 (Feb 4 at age 28 must be out; Feb 5 at age 27 must be in) |
| `// 7` → `// 8` | test 010 (weeks would become 2, not 3) |
| Week boundary at age 6 vs 7 | test 010 (Feb 26 at age 6 and Feb 25 at age 7 land in different weeks) |
| Drop the future-dose filter | test 010 (Mar 5 would add 1 day) |
| Use UTC instead of profile tz | test 011 (Feb 21 04:30Z is Feb 20 in New York → out) |
| Fixed EST offset instead of ZoneInfo | **not caught**, see LOW-1 |
| Drop profileId from the query key | service test "profile switch ...". With a 5-min staleTime nothing refetches, so `apiGet` call count 2 times out |
| Drop the streak invalidation on dose log or tz save | service tests at lines 95 and 107 |
| Change the key shape so the prefix no longer matches | **not caught**, see LOW-2 |
| Zero-streak copy reverted | `Gamification.test.tsx` "broken streak uses neutral copy" |
| UTC hint shown regardless of tz | `Gamification.test.tsx` UTC hint test, which also renders with Europe/Berlin |

## Author addition: `useSaveTimezone` invalidates `['gamification','streaks']`

**Justified.** All of the following depend on the profile tz and come from the server response: `timezone` (which drives the UTC hint), `as_of_date`, current and longest streak day buckets, and the engagement windows. Without the invalidation, the hint and the numbers stay stale for up to 5 minutes (`staleTime`) after a save. The change is 1 line (`services/modelSettings.ts:291-292`) and has a test. Badges do not need the same invalidation: `earned_at` is stored and does not depend on tz.

## Findings

### CRITICAL
None.

### HIGH
None.

### MEDIUM
None.

### LOW

**LOW-1: the DST test does not tell ZoneInfo apart from a fixed-EST offset**
- File: `src/backend/tests/test_gamification_api.py:333-348` (dose at `:339`)
- Cause: every dose and the frozen "now" fall on the same local date under real EDT and under a fixed UTC-5. For example, `2026-03-09 03:30Z` is Mar 8 23:30 EDT and Mar 8 22:30 EST. So a regression to a fixed standard offset would pass a test whose name says "across DST". (A fixed EDT offset is caught, by the Feb 21 04:30Z dose.)
- Fix: add one dose that changes date between EDT and EST and collides with a date already counted:
  ```python
  datetime(2026, 3, 20, 4, 30),  # Mar 20 00:30 EDT (same day as as_of -> no new day); fixed EST would read Mar 19 -> 4 days
  ```
  The expected `(3, 3)` stays the same.

**LOW-2: the invalidation tests check the call arguments, not that the profile-keyed query was invalidated**
- File: `src/frontend/src/__tests__/GamificationService.test.tsx:95-117`
- Cause: `expect(spy).toHaveBeenCalledWith({ queryKey: ['gamification', 'streaks'] })` still passes if `useStreaks` changes its key to a shape the prefix no longer matches, for example `['gamification', profileId, 'streaks']`. The real invalidation would then silently do nothing.
- Fix: seed the real key and assert its state:
  ```ts
  queryClient.setQueryData(['gamification', 'streaks', 'profile-a'], streak(3));
  // ...mutate...
  expect(queryClient.getQueryState(['gamification', 'streaks', 'profile-a'])?.isInvalidated).toBe(true);
  ```

**LOW-3 (existing before this diff, out of scope, follow-up): an ongoing streak shows "New streak starts today" until today's dose is logged**
- File: `src/backend/modules/streak_engine.py:35-46` (`compute_streak` counts back from `as_of_date` and returns 0 if today has no dose yet)
- Cause: a user with a 10-day streak through yesterday sees the zero-streak copy every morning. The new copy is neutral, so this is a UX oddity, not a safety issue. It is not introduced by this diff.
- Fix (separate ticket, needs an owner decision): when `as_of_date` has no dose, start counting from `as_of_date - 1`. Do not fold it into this PR.

## Out of scope (L0 decision, not reviewed)
1. Q2 ended-medication rule (shipped in #83).
2. Task 2b hide toggle and profile migration.
3. The tz-aware storage bug at `api/medications.py:609,962`.

## Files reviewed
`AGENT.md`, `CLAUDE.md`, `docs/features/TASK_LIST.md`, `src/backend/api/gamification.py`, `src/backend/modules/streak_engine.py`, `src/backend/tests/test_gamification_api.py`, `src/frontend/src/__tests__/Gamification.test.tsx`, `src/frontend/src/__tests__/GamificationService.test.tsx`, `src/frontend/src/components/medication-coach/AchievementsWidget.tsx`, `src/frontend/src/components/medication-coach/StreakDisplay.tsx`, `src/frontend/src/services/gamification.ts`, `src/frontend/src/services/index.ts`, `src/frontend/src/services/medications.ts`, `src/frontend/src/services/modelSettings.ts`, `src/frontend/src/services/types.ts` (all under `/mnt/c/Users/DangT/Documents/GitHub/hc-gam-v2-t24/`).

Next action: add the one-line Mar 20 04:30Z dose to `test_hc_gam_http_011` (LOW-1), or merge as is.

VERDICT: approve
