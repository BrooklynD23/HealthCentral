**PLAN ONLY, NOT APPROVED** — owner decision GAMIFICATION (2026-10-09) "Fix slice + plan v2". The fix slice ships separately (branch `fix/gamification-badges`). Nothing here is signed; the owner questions in section 7 gate every task.

# GAMIFICATION-V2 — profile streak UI + local-only engagement measure · plan

**Measured:** 2026-10-09, worktree `hc-gam-v2`, `origin/main` = `eb7de28`. **Source PRD:** [`docs/plans/2026-03-04-prd-voice-gamification-ingest-design.md`](../../../../docs/plans/2026-03-04-prd-voice-gamification-ingest-design.md) §2 (`:110-160`, out-of-scope `:295`). **Kind:** frontend code + docs + small backend (naive-UTC streak fix, mandatory audit rows, engagement fields). No ask-first file is edited.

## 1. Where v1 stands (measured)

| Fact | Command / location | Result |
|---|---|---|
| `GET /gamification/streaks` exists | `src/backend/api/gamification.py:120-156` | returns `current_streak_days`, `longest_streak_days`, `timezone`, `as_of_date` |
| It has no frontend consumer | `grep -rn "streaks" src/frontend/src --include=*.ts --include=*.tsx` | 0 hits; `services/gamification.ts` exports only `useBadges` |
| `StreakDisplay` is per-medication only | `components/medication-coach/AdherenceDashboard.tsx:98-99` | fed by `GET /medications/{id}/stats` |
| The streaks test bypasses HTTP | `src/backend/tests/test_gamification_api.py:101` | `await get_streaks(session=..., profile_db=...)` — the recurring-failures #1 shape |
| Gamification routes write no audit rows | `git grep -c audit origin/main -- src/backend/api/gamification.py` | 0 (exit 1) |
| Badge data is outside export | `git grep -c -i badge origin/main -- src/backend/api/export.py src/backend/modules/export.py docs/compliance/data-privacy.md` | 0 in all three |
| P5 merged, TIME-03 included | `git grep -c time_source_lint origin/main -- .github/workflows/ci.yml` → 1; `owner-decisions-2026-09-27.md:67` "Include TIME-03" | badge `earned_at` is naive UTC on both the badge list and the dose response |
| No engagement measurement anywhere | `git grep -n -i "engagement" origin/main -- src/` | no engagement instrumentation; "retention" matches in `src/` are backup, audit and secret-retention code, none about usage |
| Streak dates use the machine's local zone for stored values | `modules/streak_engine.py:26-27` calls `dt.astimezone(tz)` on `DoseTaken.taken_at`, a naive `DateTime` (`models/medication.py:204`) | Python reads a naive value as **machine-local**, not UTC. On a desktop outside UTC every streak/badge day can shift. Existing tests pass aware in-memory values (`test_gamification_api.py:84`), so they cannot see it. **v1 bug (Codex finding).** Mechanism reproduced: with `TZ=America/New_York`, `datetime(2026,3,5,3,0).astimezone(ZoneInfo('UTC'))` → `2026-03-05 08:00:00+00:00` (should be 03:00). End-to-end through a stored dose not reproduced |
| Logout clears the query cache; login/unlock does not | `services/profiles.ts:201,206,235` `queryClient.clear()`; `:152,:176` invalidate only the profiles key; `staleTime` 5 min (`App.tsx:74`) | gamification keys carry no profile id; a switch path without logout could show the previous profile's cached badges/streak |

Fix slice (separate PR `fix/gamification-badges`, not this plan): every badge in `newly_earned_badges` is toasted, not just `[0]`; `AchievementsWidget` reads offset-less `earned_at` as UTC; first render tests for `AchievementsWidget`, `BadgeToast`, `StreakDisplay`.

## 2. Scope v2

### 2a. Profile-level streak UI

0. Fix the naive-`taken_at` bug first (section 1): treat a naive value as UTC before `astimezone` in `streak_engine._dose_dates`; RED test with persisted (naive) timestamps across a DST boundary, run with a non-UTC `TZ`. Profile streak UI is wrong without it.
1. `services/gamification.ts`: add `useStreaks()` (React Query, key `['gamification','streaks', profileId]`; move the badges key to `['gamification','badges', profileId]` too, section 1 cache row; `apiGet<StreakResponse>('/gamification/streaks')`); add `StreakResponse` to `services/types.ts`. No API change.
2. Invalidate `['gamification','streaks']` next to the existing badges invalidation in `services/medications.ts:304` (dose log success; prefix match keeps working). Test: switch profiles without logout while cache is fresh → second profile never sees the first one's numbers.
3. Render the existing `StreakDisplay` with profile data at the top of `AchievementsWidget` (reuse; no new component). Label it "All medications" so it is not confused with the per-medication card.
4. When `timezone === 'UTC'` (the default, PRD decision 4), show one line: "Streak days are counted in UTC. Set your time zone in Settings." linking to the existing picker (`SettingsPage.tsx:104,228`). Day boundaries are otherwise silently wrong for most users.
5. Copy is neutral on a broken streak: when `currentStreak === 0`, `StreakDisplay` shows "New streak starts today" instead of "0 Day streak", and the caution/flame tint stays off (`StreakDisplay.tsx:22,34-36`). Never "you missed" or anything that reads as advice to take a dose. Section 5, risk 1.
6. Ended medications: the profile route aggregates every non-skipped dose through today (`api/gamification.py:137-148`) with no `min(today, ended_at)` rule (PRD `:124,:146`). Q2 sets the meaning; tests assert it.

### 2b. Local-only engagement measure

The owner asked for retention measurement. Under local-first there is **no cross-user retention number**: nothing leaves the device, so no one can aggregate. What can exist is a per-profile measure the user sees, and that the owner can read only on a vault they hold (their own, or a tester's vault opened locally with consent).

Two designs; Q1 picks.

| | A. Derived, no new storage **(recommended)** | B. Stored engagement events |
|---|---|---|
| What | "Active days in the last 28" and "weeks with any log" computed on read from `DoseTaken.taken_at` (already stored), plus existing streak and badge counts | New profile table `engagement_event(id, profile_id, kind, occurred_at)` for app opens (recorded after unlock, attributed to the unlocked profile), toast views, badge-grid views |
| Where computed | Extend `GET /gamification/streaks` response with additive fields, or a sibling `GET /gamification/engagement` (Q3) | Same, plus a write on each event |
| New data stored | **none** | behavioural timestamps for every session |
| Migration | none | new profile migration; collides with P6's planned `013` (scaffold `P6.md:58`) — must queue behind P6 with linear `down_revision` |
| Measures retention? | only as "does this person keep logging doses" — confounded with adherence itself | measures app use independent of logging |
| Privacy surface | unchanged | new row in `data-privacy.md` (tier to pick: health-adjacent behaviour, not Tier 2 metadata); **rewrite** "does not collect … usage data" (`data-privacy.md:270`) to "no usage data leaves the device"; retention rule; export decision; deletion with profile |

Privacy and audit implications (both designs):

- **Storage:** per-profile SQLCipher DB via `ProfileDbSession` only; never the master `get_db()`.
- **Network:** none. No telemetry endpoint, no beacon, no external runner path. A lint grep in the test plan enforces it.
- **Audit (mandatory, not an owner choice):** both gamification GETs read profile data, and the hard invariant (`CLAUDE.md` "Audit logging") requires a row. Today they write none (section 1). v2 adds `view` rows to both via the existing `audit_and_commit` helper (`core/audit.py:474`; calling it is not an edit to `core/audit.py`). It fails the request if the row cannot commit (`core/audit.py:479`) — test that through HTTP. Disclose: rows go to the unencrypted master DB, retained indefinitely (`data-privacy.md:33`). Audit rows themselves go to the master DB (`data-privacy.md:33`), so B's per-event writes must **not** emit an audit row each, or every app open lands in the master DB.
- **Retention (B only):** at most 90 days in the live DB, enforced by a prune on every write and on unlock (prune-on-read alone leaves unread profiles unbounded); deleted with the profile (profile delete destroys the sealed key and vault, `api/profiles.py:780-787`). Not bounded in backups: app backups follow backup retention, which can be `0` = never prune (`data-privacy.md:62`); app backups are deleted with the profile, downloaded archives are not (`data-privacy.md:172,177`). The doc must say so. Q4.
- **Export / redaction:** counters and timestamps carry no free text, so `modules/redaction.py` is not on the path. Whether badges / engagement join the JSON export is Q5; default leaves export unchanged (it carries no badge data today). Backups copy the whole profile DB, so B's table is in backups automatically — say so in `data-privacy.md`. If Q5 = no, B's event history is also absent from JSON export.

### 2c. PRD out-of-scope items (`:295`) — all stay out

| Item | Stays out because |
|---|---|
| Points | PRD decision 1 chose streaks + badges; no new signal |
| Leaderboards | needs other users' data → network → breaks local-first |
| Badge sharing | same; also discloses medication adherence |
| Custom badges | no request; YAGNI |
| Badge revocation | PRD: earned badges are permanent; revocation for deleted backdated doses would need its own decision |
| Schedule history tracking | needed only to make Perfect Week exact across schedule edits; separate item if it bites |

### 2d. Not gamification

`components/documents/CategoryBadge.tsx` is the document-category chip from INGEST-EPIC-001 (PRD `:480`). It shares the word "badge" only. Out of this plan; do not touch it, and do not count it in any gamification test or grep.

## 3. Tasks (after sign-off)

| # | Task | Files | Gate |
|---|---|---|---|
| 0 | Re-measure section 1 at current main; stop on any mismatch | — | Q1-Q6 answered |
| 0b | RED → GREEN: naive `taken_at` read as UTC in `_dose_dates`; persisted-timestamp DST test with non-UTC `TZ` | `modules/streak_engine.py`, `tests/test_streak_engine.py` | — (bug fix; can ship ahead of v2) |
| 1 | RED: route tests for both gamification GETs through HTTP (`tests/support/routes.py::route_client`), incl. 401 without auth, 2-profile isolation, audit row written, request fails if the audit row cannot commit, ended-medication rule per Q2 | `src/backend/tests/test_gamification_api.py` | — |
| 2 | RED → GREEN: `useStreaks` + profile-keyed queries + profile `StreakDisplay` in `AchievementsWidget`, zero-streak copy, UTC hint | `services/gamification.ts`, `services/types.ts`, `services/medications.ts`, `AchievementsWidget.tsx`, `StreakDisplay.tsx` | Q6 |
| 3 | Audit `view` rows on both gamification routes (invariant; not optional) | `api/gamification.py` | — |
| 4 | Engagement measure per Q1 (A: additive response fields; B: table + migration after P6) | `api/gamification.py`, `modules/streak_engine.py`; B adds `models/gamification.py`, `migrations/profile/versions/0NN_*.py` | Q1, Q3, Q4 |
| 5 | Docs: `data-privacy.md` row (B only), PRD v2 status line | `docs/compliance/data-privacy.md` (W-10 / W-10b own other lines: serial), PRD | Q4, Q5 |

## 4. Test plan

- Backend: HTTP route tests (task 1); A: active-days computation across DST and profile timezone edges, ended medications, skipped doses excluded (`was_skipped`); B: migration up/down, prune at 90 days, profile isolation through HTTP.
- Frontend: `useStreaks` hook test; `AchievementsWidget` shows profile streak and UTC hint only when `timezone === 'UTC'`; invalidation after dose log; profile switch without logout shows no stale numbers; zero-streak copy; framer-motion mocked with prop filtering (`PageImageOverlay.test.tsx:10` pattern).
- Local-first guard: `git grep -n -E "fetch\(|axios|https?://" -- src/frontend/src/services/gamification.ts` shows only `apiGet` to the local backend.
- Break-check: each new test is run once against the unfixed code and must go red (recurring-failures #1).
- Baselines re-measured, not copied: backend collected count, vitest file count.

## 5. Risks

1. **Streak pressure in a health app.** A streak can nudge a user to log a dose they did not take, or to take one to "save" the streak. Mitigations: neutral copy, no loss-framing, no reminder that mentions the streak; owner may choose to hide streaks entirely (Q6).
6. **Naive-UTC streak bug (section 1).** Until task 0b lands, every v1 streak and streak badge on a non-UTC desktop may count the wrong day. Mechanism reproduced (section 1), end-to-end not; task 0b starts with a RED test.
2. **Engagement measure confounded with adherence (A).** Days-with-a-log measures logging, which is also the adherence signal. It cannot tell "stopped using the app" from "medication ended". Report it as such; do not call it retention.
3. **Migration collision (B).** P6 plans profile migration `013`; B must queue behind it.
4. **Audit volume (B).** Per-event audit rows would flood the master DB with behavioural timestamps; only read routes get audit rows.
5. **Timezone default.** With `UTC` default, a US-evening log counts toward the next day; the UTC hint mitigates, it does not fix.

## 6. Ask-first touches

None. `core/audit.py` is called, not edited. `interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, auth and encryption files are untouched.

## 7. Owner questions (unsigned; do not decide)

| # | Question | Recommended | Downside of the recommendation |
|---|---|---|---|
| Q1 | Engagement design: A (derived, no new storage) or B (stored events)? | **A** | Cannot measure app opens; the number is logging, not retention |
| Q2 | Profile-level streak with ended medications: count a day if any medication (active or ended-on-that-day) had a dose, with no streak contribution after each `ended_at`? | **Yes** (per-medication PRD rule applied per dose) | When every medication has ended, the profile streak just stops; no "paused" state |
| Q3 | Expose the measure as additive fields on `/gamification/streaks`, or a new `/gamification/engagement` route? | **Additive fields** | Couples two concerns in one response; harder to drop later |
| Q4 | If B: keep events 90 days, prune on read, nothing else stored? | **Yes (90 d)** | Under 90 days of history, long-run trends invisible |
| Q5 | Add badges / engagement to the JSON export? | **No** (export unchanged) | User cannot take their badge history to another tool |
| Q6 | Show the profile streak at all, given risk 1? | **Yes, neutral zero-streak copy; no hide toggle in v2** | A user who finds streaks stressful cannot turn them off until a later toggle |

Codex review (gpt-6-luna, xhigh): `audit/2026-09-25/swarm-2026-09-27/reviews/GAMIFICATION-V2-codex.txt`; 7 findings, all folded (audit made mandatory; profile-keyed queries; naive-UTC streak bug; ended-medication rule → Q2; B retention/backup/no-analytics wording; zero-streak copy, hide toggle dropped; evidence fixes).

Next action: ask the owner Q1 and Q2.
