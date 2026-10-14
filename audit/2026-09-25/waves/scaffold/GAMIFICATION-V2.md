**PLAN — owner questions answered 2026-10-10 (section 7); not yet approved for execution.** Owner decision GAMIFICATION (2026-10-09) "Fix slice + plan v2". The fix slice ships separately (PR #66). Task 0b ships as its own fix PR ahead of v2. v2 tasks 1-5 are dispatch-ready once 0b merges; task 2b's profile migration is serial with P6 on the profile chain.

# GAMIFICATION-V2 — profile streak UI + local-only engagement measure · plan

**Measured:** 2026-10-09, worktree `hc-gam-v2`, `origin/main` = `eb7de28`. **Source PRD:** [`docs/plans/2026-03-04-prd-voice-gamification-ingest-design.md`](../../../../docs/plans/2026-03-04-prd-voice-gamification-ingest-design.md) §2 (`:110-160`, out-of-scope `:295`). **Kind:** frontend code + docs + small backend (naive-UTC streak fix, mandatory audit rows, engagement fields, streak hide setting + one profile migration). No ask-first file is edited.

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
6. Ended medications (Q2 = yes): a day counts if any medication has a non-skipped dose that day; doses after a medication's `ended_at` never count. Today the profile route aggregates every non-skipped dose through today (`api/gamification.py:137-148`) with no `min(today, ended_at)` rule (PRD `:124,:146`). When every medication has ended, the profile streak stops; no "paused" state.
7. Hide toggle (Q6 = "Add a hide toggle"): a per-profile `streaks_hidden` boolean (default `false`) on `UserModelSettings`, read/written through a `GET`/`PATCH /settings/gamification` pair modelled on `/settings/voice` (`api/model_settings.py:987-1018`). Settings page gets one switch "Show streaks". When hidden: no profile streak in `AchievementsWidget` and no per-medication `StreakDisplay` in `AdherenceDashboard.tsx:98`; badges (including streak badges) and their toasts still show. Neutral copy stays when shown. Stored server-side, not `localStorage`, so it is per-profile, survives backup/restore, and follows the existing voice-setting pattern. Needs a new profile migration (`add_column`, `server_default=false`), next free number with linear `down_revision`; serial with P6, which also plans profile migration `013` (scaffold `P6.md:58`). Not in JSON export (Q5).

### 2b. Local-only engagement measure

The owner asked for retention measurement. Under local-first there is **no cross-user retention number**: nothing leaves the device, so no one can aggregate. What can exist is a per-profile measure the user sees, and that the owner can read only on a vault they hold (their own, or a tester's vault opened locally with consent).

Two designs; **owner chose A (Q1, 2026-10-10)**. B is kept below for the record only; its retention/backup notes do not apply.

| | A. Derived, no new storage **(chosen)** | B. Stored engagement events (not chosen) |
|---|---|---|
| What | "Active days in the last 28" and "weeks with any log" computed on read from `DoseTaken.taken_at` (already stored), plus existing streak and badge counts | New profile table `engagement_event(id, profile_id, kind, occurred_at)` for app opens (recorded after unlock, attributed to the unlocked profile), toast views, badge-grid views |
| Where computed | Additive fields on `GET /gamification/streaks` (Q3 default, owner did not object) | Same, plus a write on each event |
| New data stored | **none** | behavioural timestamps for every session |
| Migration | none | new profile migration; collides with P6's planned `013` (scaffold `P6.md:58`) — must queue behind P6 with linear `down_revision` |
| Measures retention? | only as "does this person keep logging doses" — confounded with adherence itself | measures app use independent of logging |
| Privacy surface | unchanged | new row in `data-privacy.md` (tier to pick: health-adjacent behaviour, not Tier 2 metadata); **rewrite** "does not collect … usage data" (`data-privacy.md:270`) to "no usage data leaves the device"; retention rule; export decision; deletion with profile |

Privacy and audit implications (both designs):

- **Storage:** per-profile SQLCipher DB via `ProfileDbSession` only; never the master `get_db()`.
- **Network:** none. No telemetry endpoint, no beacon, no external runner path. A lint grep in the test plan enforces it.
- **Audit (mandatory, not an owner choice):** both gamification GETs read profile data, and the hard invariant (`CLAUDE.md` "Audit logging") requires a row. Today they write none (section 1). v2 adds `view` rows to both via the existing `audit_and_commit` helper (`core/audit.py:474`; calling it is not an edit to `core/audit.py`). It fails the request if the row cannot commit (`core/audit.py:479`) — test that through HTTP. Disclose: rows go to the unencrypted master DB, retained indefinitely (`data-privacy.md:33`). Audit rows themselves go to the master DB (`data-privacy.md:33`), so B's per-event writes must **not** emit an audit row each, or every app open lands in the master DB.
- **Retention (B only):** at most 90 days in the live DB, enforced by a prune on every write and on unlock (prune-on-read alone leaves unread profiles unbounded); deleted with the profile (profile delete destroys the sealed key and vault, `api/profiles.py:780-787`). Not bounded in backups: app backups follow backup retention, which can be `0` = never prune (`data-privacy.md:62`); app backups are deleted with the profile, downloaded archives are not (`data-privacy.md:172,177`). The doc must say so. Q4.
- **Export / redaction:** counters and timestamps carry no free text, so `modules/redaction.py` is not on the path. Badges, engagement and the hide preference stay out of the JSON export (Q5 = no; export carries no badge data today). Backups copy the whole profile DB, so B's table is in backups automatically — say so in `data-privacy.md`. If Q5 = no, B's event history is also absent from JSON export.

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
| 0 | Re-measure section 1 at current main; stop on any mismatch | — | Q1-Q6 answered (done 2026-10-10) |
| 0b | **Separate fix PR, ahead of v2 (owner 2026-10-10).** RED → GREEN: naive `taken_at` read as UTC in `_dose_dates`; persisted-timestamp DST test with non-UTC `TZ` | `modules/streak_engine.py`, `tests/test_streak_engine.py` | none — dispatch now |
| 1 | RED: route tests for both gamification GETs through HTTP (`tests/support/routes.py::route_client`), incl. 401 without auth, 2-profile isolation, audit row written, request fails if the audit row cannot commit, ended-medication rule per Q2 | `src/backend/tests/test_gamification_api.py` | — |
| 2 | RED → GREEN: `useStreaks` + profile-keyed queries + profile `StreakDisplay` in `AchievementsWidget`, zero-streak copy, UTC hint | `services/gamification.ts`, `services/types.ts`, `services/medications.ts`, `AchievementsWidget.tsx`, `StreakDisplay.tsx` | 0b merged |
| 2b | RED → GREEN: streak hide toggle (scope item 7): profile migration + `streaks_hidden` column, `GET`/`PATCH /settings/gamification` with HTTP route tests (401, 2-profile isolation, default `false`, PATCH persists), Settings switch, both streak surfaces hidden while badges stay | `models/model_settings.py`, `migrations/profile/versions/0NN_streaks_hidden.py`, `api/model_settings.py`, `services/modelSettings.ts`, `pages/SettingsPage.tsx`, `AchievementsWidget.tsx`, `AdherenceDashboard.tsx` | serial with P6 on the profile migration chain |
| 3 | Audit `view` rows on both gamification routes (invariant; not optional) | `api/gamification.py` | — |
| 4 | Engagement measure A: additive fields on `/gamification/streaks` (active days in last 28, weeks with any log), ended-medication rule per Q2 | `api/gamification.py`, `modules/streak_engine.py` | 0b merged |
| 5 | Docs: PRD v2 status line; `data-privacy.md` unchanged (A stores nothing new; the hide flag is a preference, not health data) | PRD | — |

## 4. Test plan

- Backend: HTTP route tests (task 1); A: active-days computation across DST and profile timezone edges, ended medications, skipped doses excluded (`was_skipped`); hide toggle: migration up/down on a profile DB, `/settings/gamification` through HTTP (401, isolation, default, persist).
- Frontend: `useStreaks` hook test; `AchievementsWidget` shows profile streak and UTC hint only when `timezone === 'UTC'`; invalidation after dose log; profile switch without logout shows no stale numbers; zero-streak copy; hide toggle hides the profile streak and the per-medication `StreakDisplay` but not badges or badge toasts; framer-motion mocked with prop filtering (`PageImageOverlay.test.tsx:10` pattern).
- Local-first guard: `git grep -n -E "fetch\(|axios|https?://" -- src/frontend/src/services/gamification.ts` shows only `apiGet` to the local backend.
- Break-check: each new test is run once against the unfixed code and must go red (recurring-failures #1).
- Baselines re-measured, not copied: backend collected count, vitest file count.

## 5. Risks

1. **Streak pressure in a health app.** A streak can nudge a user to log a dose they did not take, or to take one to "save" the streak. Mitigations: neutral copy, no loss-framing, no reminder that mentions the streak; user can hide streaks in Settings (Q6, task 2b).
2. **Engagement measure confounded with adherence (A).** Days-with-a-log measures logging, which is also the adherence signal. It cannot tell "stopped using the app" from "medication ended". Report it as such; do not call it retention.
3. **Migration collision (task 2b).** P6 plans profile migration `013`; whichever lands second renumbers and repoints `down_revision`.
4. **Settings routes are unaudited.** The existing `/settings/voice` and `/settings/timezone` routes write no audit rows (`grep -n audit src/backend/api/model_settings.py` → none). Task 2b follows the invariant and audits its new pair; fixing the existing settings routes is out of scope and noted here, not done.
5. **Timezone default.** With `UTC` default, a US-evening log counts toward the next day; the UTC hint mitigates, it does not fix.
6. **Naive-UTC streak bug (section 1).** Until task 0b lands, every v1 streak and streak badge on a non-UTC desktop may count the wrong day. Mechanism reproduced (section 1), end-to-end not; task 0b starts with a RED test.

## 6. Ask-first touches

None. `core/audit.py` is called, not edited. `interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, auth and encryption files are untouched.

## 7. Owner answers (2026-10-10, relayed by L0; rows on #60)

| # | Question | Plan recommended | Owner answer | Effect |
|---|---|---|---|---|
| Q1 | Engagement design A (derived) or B (stored events)? | A | "A: derive from DoseTaken" | B dropped; no new engagement storage |
| Q2 | Profile streak with ended medications: any medication counts, nothing after its `ended_at`? | Yes | "Yes" | scope item 6; tasks 1, 4 test it |
| Q3 | Additive fields on `/gamification/streaks` or a new route? | Additive fields | not asked; L0 told the owner this default, no objection | task 4 |
| Q4 | B retention 90 days? | Yes | n/a (B not chosen) | — |
| Q5 | Badges / engagement in JSON export? | No | "No" | export unchanged; hide flag also not exported |
| Q6 | Show the profile streak; hide toggle? | Yes, no toggle in v2 | **"Add a hide toggle"** (differs from recommendation) | scope item 7, task 2b; neutral copy kept |

Task 0b: owner — keep as a separate fix ahead of v2.

Codex review (gpt-6-luna, xhigh): `audit/2026-09-25/swarm-2026-09-27/reviews/GAMIFICATION-V2-codex.txt`; 7 findings, all folded (audit made mandatory; profile-keyed queries; naive-UTC streak bug; ended-medication rule → Q2; B retention/backup/no-analytics wording; zero-streak copy; evidence fixes). The hide toggle Codex flagged as unplanned was first dropped, then restored as task 2b after the owner's Q6 answer.

Next action: dispatch task 0b as its own fix PR; dispatch tasks 1-5 after it merges, with 2b serial against P6's profile migration.
