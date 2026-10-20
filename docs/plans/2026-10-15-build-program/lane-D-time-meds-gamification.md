# Lane D — Time Zones, Medications, Gamification — Build Design

**Last Updated:** 2026-10-20 (PR #202 review round 1: MSET-EXT-NOKEY-PIN planned, EXPORT-TZ-PINS done); 2026-10-19 (AUDIT-GUARD-MINORS planned; EXPORT-TZ-PINS HC-EXPTZ-008 check reworded from `source_id` to the task title, PR #198); 2026-10-18 (AUDIT-C-CLASS planned and split into AUDIT-C-MED, AUDIT-C-ASSIST, AUDIT-C-MSET, AUDIT-C-MSET-EXT); 2026-10-18 (AUDIT-NOTIF-ALL planned; EXPORT-TODAY-TZ Design 2 rev for owner EXPORT-TODAY-TZ-DESIGN = B; AUDIT-C-CLASS row); 2026-10-17 (MED-STREAK-GRACE, AUDIT-MISSING-MED, EXPORT-TODAY-TZ planned); 2026-10-16 (D-2 rev 2, owner Q1)
**Owner:** repository owner
**Refresh Trigger:** any merge of #95, #97, #99, #82 or #84; any commit to `src/backend/core/time.py`, `src/backend/modules/notification_scheduler.py`, `src/backend/modules/adherence_patterns.py`, `src/backend/modules/streak_engine.py`, `src/backend/api/medications.py`, `src/backend/api/gamification.py`, `src/backend/api/notifications.py`, `src/backend/monitoring/correlation.py`; a new profile migration after `012_pinboards`.
**Status:** DESIGN. Nothing here is implemented. Owner answers cited below are quoted from `docs/capstone-report/owner-decisions-2026-09-27.md`; this file records no new approval.
**Base measured:** `origin/main` @ `3b2236c` (2026-10-15). Every `file:line` is at this base unless marked `after #NN`. Open PR branches read with `git show origin/<branch>` on 2026-10-15.

> **For agentic workers:** one item = one PR on its own branch. RED test first (`test-driven-development` skill). Route tests go through `tests/support/routes.py::route_client`. Never pick a side in a count-slot conflict: recount.

---

## 1. Items

| ID | Item | Source | Plan on main? | Depends on | Readiness |
|---|---|---|---|---|---|
| D-0 | SYNC: merge order #95 → #97 → #99 → #82 → #84, recount each | open PRs; `docs/agentic/orchestration.md:24` (serial merges, re-measure count slots) | no (ops) | — | ready |
| D-1 | STREAK-TZ + the profile time-zone helper (§2) | owner row STREAK-TZ (`owner-decisions-2026-09-27.md:174`) | no | #97, #99 merged | blocked-on-PR |
| D-2 | SCHED-TZ: scheduler on profile-local now/today; adaptive windows stored local | owner row SCHED-TZ (`:173`); #97 comment at `api/medications.py` learn_patterns (after #97) | no | D-1, #97 | blocked-on-item |
| D-3 | GAM2-STREAK0: ongoing streak counts through yesterday | owner row GAM2-STREAK0 (`:145`); #84 review LOW-3 (`docs/reviews/2026-10-12/GAM2-T24-diff-codereview.md:76-79` on `feat/gamification-v2-t24`) | no | #84, D-1 | blocked-on-PR |
| D-4 | CORRELATION-NORMALISE: canonical form of an inbound correlation ID | `implementation-program.md:500`; `audit/2026-09-25/waves/wave-3-L1-A.md:176` | no | — | done (#138) |
| MED-STREAK-GRACE | per-medication and reminder streaks count through yesterday (Q2) | queue status 2026-10-16 second batch | [§3](#med-streak-grace--the-per-medication-streak-still-resets-each-morning-owner-ruling--q2) | D-3 (merged #109) | blocked-on-owner (MSG-SCOPE) |
| AUDIT-MISSING-MED | audit rows on `GET /medications/{id}/stats` and `POST /notifications/test/{id}` | queue status 2026-10-16 second batch; CLAUDE.md audit invariant | [§3](#audit-missing-med--two-profile-data-routes-write-no-audit-row) | D-1 (merged #104); rebase after #130 | ready |
| EXPORT-TODAY-TZ | export questions window and generated-on dates use the profile-local day | queue status 2026-10-16 second batch; recurring-failures #9 | [§3](#export-today-tz--export-dates-use-the-utc-calendar-day) | D-1 helpers (merged) | ready (Design 2 rev: owner EXPORT-TODAY-TZ-DESIGN = B) |
| AUDIT-NOTIF-ALL | audit rows on the four profile-data routes of `api/notifications.py` that AUDIT-MISSING-MED does not cover | queue status 2026-10-17; recurring-failures #9 | [§3](#audit-notif-all--apinotificationspy-writes-no-audit-row-on-any-route) | AUDIT-MISSING-MED (merged #165) | ready |
| AUDIT-C-MED | audit rows on 6 `api/medications.py` handlers; `delete_schedule` becomes A2 | AUDIT-C-CLASS split, 2026-10-18; recurring-failures #9 | [§3](#audit-c-class--17-c-handlers-write-no-audit-row-split-audit-c-med-audit-c-assist-audit-c-mset-audit-c-mset-ext) | AUDIT-NOTIF-ALL merged (shared guard file) | ready after AUDIT-NOTIF-ALL |
| AUDIT-C-ASSIST | audit rows on 3 `api/assistant.py` handlers; `delete_session` becomes A2 | same | [§3](#audit-c-class--17-c-handlers-write-no-audit-row-split-audit-c-med-audit-c-assist-audit-c-mset-audit-c-mset-ext) | AUDIT-NOTIF-ALL merged; never beside AUDIT-C-MED | ready after AUDIT-NOTIF-ALL |
| AUDIT-C-MSET | audit rows on 7 `api/model_settings.py` settings handlers | same | [§3](#audit-c-class--17-c-handlers-write-no-audit-row-split-audit-c-med-audit-c-assist-audit-c-mset-audit-c-mset-ext) | — | ready |
| AUDIT-C-MSET-EXT | audit row on `save_external_api_settings` (encryption code, ask-first; AUDIT-EXT-ASKFIRST = A) | same | [§3](#audit-c-class--17-c-handlers-write-no-audit-row-split-audit-c-med-audit-c-assist-audit-c-mset-audit-c-mset-ext) | AUDIT-C-MSET | ready after AUDIT-C-MSET merges |
| AUDIT-GUARD-TEST | guard test: every `"C"`/`"A2"` row reaches an audit call | AUDIT-C-CLASS plan follow-up (PR #174); recurring-failures #9 | [§3](#audit-guard-test--the-audit-order-guard-checks-the-class-not-that-the-class-is-true) | — | ready |
| MSET-EXT-NOKEY-TEST | HTTP test: external-API save with no key and switch-off | PR #181 "would fail to notice"; owner MSET-EXT-DIFF | [§3](#mset-ext-nokey-test--no-test-saves-external-api-settings-without-a-key) | — | ready |
| EXPORT-TZ-PINS | HTTP pins for `today=local_today` on the pinboard and visit-prep question callers | PR #155 review minors 1-2 | [§3](#export-tz-pins--no-test-pins-todaylocal_today-on-the-pinboard-and-visit-prep-question-callers) | — | **done** 2026-10-20 (#198, `adb22f0`) |
| AUDIT-GUARD-MINORS | guard break-it on the overlay graph with an `"A2"` row; `excluded:` labels checked (HC-AUD-ORD-031); `get_schedule` audit or relabel | PR #193 review MINORs | [§3](#audit-guard-minors--the-guards-break-it-uses-the-wrong-graph-and-no-a2-row-excluded-labels-are-never-checked) | — | blocked-on-owner (AUDIT-SCHED-READ) |
| MSET-EXT-NOKEY-PIN | HC-AUDCMS-005 reads the key with `populate_existing=True`; the vacuous canary line is replaced | PR #194 review MINORs; PR #202 review round 1 | [§3](#mset-ext-nokey-pin--hc-audcms-005s-re-select-returns-the-cached-row-so-a-key-wipe-in-the-database-passes) | — | ready |

Dependency graph: `D-0 → D-1 → {D-2, D-3}`; D-4 is independent. D-2 and D-3 touch disjoint product files and may run as the 2 allowed code L1s at once.

---

## 2. Profile time-zone helper contract (used by D-1, D-2, D-3)

**Where the zone comes from:** `UserModelSettings.timezone` (`src/backend/models/model_settings.py:96`) in the **profile** DB, one row per `profile_id`. Written only by `PUT /settings/model/timezone` (`api/model_settings.py:966-984`; prefix `api/__init__.py:56`), which validates with `ZoneInfo`. No row, NULL, empty, unknown or malformed name → `"UTC"`.

**Why one helper:** the same lookup is copied twice today — `api/gamification.py:57-65` and `api/medications.py:70-78` (`_profile_timezone_name`), plus `api/medications.py:81-86` (`_local_date_for_timezone`) and, after #97, `modules/adherence_patterns.py::_local`. Both copies catch only `ZoneInfoNotFoundError`; a stored `ValueError`-class name would 500.

**Home:** `src/backend/core/time.py` (already the single timestamp helper per CLAUDE.md). No new module. **Append** the helpers after `to_naive_utc` (`:27`) and add new imports to the existing import lines only, so `utcnow` (`:12`), `utcfromtimestamp` (`:17`) and `to_naive_utc` (`:27`) keep their line numbers (wearables plans 02, 03, 07, 11, 12 cite them; WEAR-03 lists "any edit to `core/time.py`" as a refresh trigger, so the D-1 PR body names that trigger).

```python
# core/time.py — additions (Python 3.11; stdlib + sqlalchemy only)
def safe_zone_name(name: str | None) -> str:
    """Valid IANA name, else "UTC". Catches ZoneInfoNotFoundError and ValueError; logs a warning."""

def to_local(value: datetime, tz_name: str) -> datetime:
    """Naive-UTC storage value (or aware value) -> aware datetime in tz_name."""

def local_day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]:
    """Naive-UTC [start, end) of local calendar day `day`. DST days are 23 h or 25 h."""

async def profile_timezone_name(profile_db: AsyncSession, profile_id: str) -> str:
    """safe_zone_name(UserModelSettings.timezone) for profile_id; "UTC" when no row."""
```

- `profile_timezone_name` imports `models.UserModelSettings` inside the function body: 16 files under `models/` import `core.time`, so a module-level import would cycle. Mark it `# ponytail: lazy import breaks the models -> core.time cycle`.
- Stored timestamps stay naive UTC (MED-UTC, UTC-SWEEP). The helper converts on read only. No column changes.
- Callers that already loaded the settings row call `safe_zone_name(settings.timezone if settings else None)` instead of querying again.
- `scripts/time_source_lint.py` stays clean: no `datetime.utcnow`.

**Introduced by D-1.** D-1 deletes `_profile_timezone_name` and `_local_date_for_timezone` from `api/medications.py` and `_local` from `modules/adherence_patterns.py`, switching their callers. D-3 deletes the copy in `api/gamification.py`. After D-3, `grep -rn "_profile_timezone_name" src/backend` → 0 hits.

---

## 3. Per-item design

### D-0 — SYNC (#95, #97, #99, #82, #84)

**Measured 2026-10-15** (`git merge-tree --write-tree origin/main origin/<branch>`):

| PR | Branch | Base count → PR count | Delta | Conflicts vs main @`3b2236c` | Product files |
|---|---|---|---|---|---|
| #95 | `fix/assistant-utc` | 1487 → 1501 | +14 (1 parametrized test) | `AGENT.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/_link_graph.json`, `docs/reviews/README.md` | `modules/rag.py` |
| #97 | `fix/adherence-patterns-tz` | 1487 → 1493 | +6 | `AGENT.md`, `CLAUDE.md`, `docs/INDEX.md` | `api/medications.py`, `modules/adherence_patterns.py` |
| #99 | `fix/dose-schedule-ownership` | 1501 → 1505 | +4 | `AGENT.md`, `CLAUDE.md` | `api/medications.py` |
| #82 | `fix/rl-export-prompt-snapshot` | 1477 → 1480 | +3 | `AGENT.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/_link_graph.json`, `docs/reviews/README.md` | `api/feedback.py` |
| #84 | `feat/gamification-v2-t24` | 1477 → 1480 | +3 | same five as #82 | `api/gamification.py`, `modules/streak_engine.py`, frontend (11 files) |

**Correction to the dispatch brief:** main's count slot is **1574**, not 1501 (`CLAUDE.md:30`, `AGENT.md:76` @`3b2236c`; UTC-SWEEP took it 1487 → 1560, then BKUP-TORN and DOSE-VAR merges).

**The count-slot trap:** every PR's slot conflicts with 1574, and each PR's own number is wrong for the merged tree. Taking either side ("ours" or "theirs") gives a wrong baseline that no test catches. Predicted chain, to be confirmed by measurement, never written from this table:

`1574 → #95 1588 → #97 1594 → #99 1598 → #82 1601 → #84 1604`

**Product-code overlap:** #97 and #99 both edit `api/medications.py::learn_patterns` right after `verify_medication_access`. `git merge-tree origin/fix/adherence-patterns-tz origin/fix/dose-schedule-ownership` auto-merges `api/medications.py` (conflicts only in the two count files and `docs/INDEX.md`). Semantic check after merge: the SCHED-OWNER guard (`_schedule_for_medication`) runs before the ADHERE-TZ zone lookup; both stay. #97's test imports `_client, _seed, profile_db` from `tests/test_medications_routes_http.py`; #99 adds to that file but does not change those three names.

**Steps per PR, in order** (agent; the owner merges):

1. `git fetch origin && git merge origin/main` on the PR branch (no rebase, no force-push).
2. Resolve `CLAUDE.md:30,34` and `AGENT.md:76` by **measuring**: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1`. Write that number to all 3 slots.
3. Regenerate, never hand-merge: `python3 scripts/generate_docs_index.py`, `python3 scripts/docs_lint.py --link-graph`, then `python3 scripts/docs_lint.py` must print `Docs lint passed.`. For `docs/reviews/README.md`, keep both sides' rows.
4. Run the PR's own tests plus its neighbours: `-k "adhere_tz or med_http or gam_http or assist_utc or rl_export"` under the same `flock`.
5. Push; the owner merges; the next PR starts at step 1.

**Acceptance:** after #84 merges, `CLAUDE.md` slot equals the measured `--collect-only` count on main; `docs_lint` passes on main.

**Also queued (not this lane's code):** #72 needs the MM-1 20-question run; #61 closes after #72 (PR61-CLOSE); #68 merges last (PR68-SYNC); #74 waits for the owner's screenshot comparison (TW4-SHOTS). Each still follows steps 1–3 when its turn comes.

### D-1 — STREAK-TZ (+ helper)

**Owner answer (`:174`):** "Pass the profile time zone to calculate_streak at every caller; one invariant, tested per site through HTTP."

**Sites, corrected lines** (owner text cited `medications.py:1245,1251,1276` before DOSE-VAR shifted them):

| Site | Main @`3b2236c` | After #99 | Bug |
|---|---|---|---|
| `api/medications.py::_calculate_current_streak` | `:1236-1264` (`today = utcnow().date()` `:1250`; `dose.taken_at.date()` `:1256`) | +19 lines | UTC "today" and UTC dose dates |
| `api/medications.py::_calculate_longest_streak` | `:1267-1290` (`:1281`) | +19 | UTC dose dates |
| `api/notifications.py::send_test_medication_notification` | `calculate_streak` `:453`; `is_weekend` / `hour_of_day` `:463-464` | — | no `tz_name` → `"UTC"` default (after #97) |
| `modules/notification_scheduler.py::_send_notification` | `calculate_streak` `:529-531` | — | same |
| `modules/adherence_patterns.py::calculate_streak` | `:385-445` | fixed by #97 (`tz_name` param, `_dose_dates`) | callers above must pass it |

**Design (smallest root-cause fix):**

1. Add the §2 helpers to `core/time.py`.
2. Replace the bodies of `_calculate_current_streak` / `_calculate_longest_streak` with `modules.streak_engine.compute_streak(doses, tz, to_local(utcnow(), tz).date())` and `compute_longest_streak(doses, tz)`. The route `get_adherence_stats` gets `tz = await profile_timezone_name(profile_db, session.profile_id)`. This deletes about 40 lines of duplicate streak logic; one engine, one invariant.
3. `api/notifications.py:453`: pass `tz_name=await profile_timezone_name(profile_db, session.profile_id)`; compute `is_weekend` / `hour_of_day` from `to_local(utcnow(), tz)` (same function, same zone).
4. `modules/notification_scheduler.py:529`: pass `tz_name=await profile_timezone_name(db, profile_id)`. D-2 later threads the zone it already loaded.
5. `api/medications.py`: delete `_profile_timezone_name` and `_local_date_for_timezone`; callers at `:960`, `:995`, `:1035`, and learn_patterns (after #97) use `safe_zone_name` / `to_local`. `modules/adherence_patterns.py`: replace `_local` with `core.time.to_local`.

**Test-first (RED each before the change):**

| Test | File | Asserts |
|---|---|---|
| `test_hc_time_007` / `_008` | `tests/test_time_source.py` (existing `_001`–`_006`) | `local_day_bounds_utc(date(2026,3,8), "America/Los_Angeles")` spans 23 h; `safe_zone_name("Mars/Olympus") == safe_zone_name("") == "UTC"` |
| `test_hc_streak_tz_001` | `tests/test_medications_routes_http.py` | LA profile, 09:00 PST doses Jan 13–15 (17:00Z), frozen now Jan 15 17:00 PST (Jan 16 01:00Z): `GET /medications/{id}/stats` → `current_streak_days == 3` (UTC gives 0) |
| `test_hc_streak_tz_002` | same | 16:30 PST doses on 3 consecutive local days (00:30Z next day): `longest_streak_days == 3` |
| `test_hc_streak_tz_003` | `tests/test_notification_routes_http.py` (new; `route_client`) | `POST /notifications/test/{id}` with the tz_001 seed: monkeypatched `get_message_generator().generate_reminder` receives `current_streak == 3` |
| `test_hc_streak_tz_004` | `tests/test_notification_scheduler_wiring.py` | scheduler pass (nsw_007 harness) with a spy learner: `calculate_streak` awaited with `tz_name="America/Los_Angeles"`. No route exists for the scheduler, so this is the one non-HTTP site test. |

Freeze time with `monkeypatch.setattr(<module>, "utcnow", ...)` as #97's tests do. UTC profiles must keep today's values: existing `test_hc_med_http_*`, `test_hc_nsw_007/008`, `test_hc_adhere_tz_*` stay green unchanged.

**Acceptance:** `pytest tests/ -k "hc_time or streak_tz or med_http or nsw or adhere_tz or gam_http" -q` green; `python3 scripts/time_source_lint.py` exit 0; collected count = previous + 6, written to the 3 slots.

**Rollback:** revert the single PR. No migration, no stored-data change.

### D-2 — SCHED-TZ

**Owner answer (`:173`):** "Scheduler reads profile-local now/today; then stored windows move to local time with a one-time re-learn. RED test first."

**Bug, at main @`3b2236c`:** `modules/notification_scheduler.py:314-317` takes `current_time`, `today`, `current_weekday` from `utcnow()`. `MedicationSchedule.target_time` is local wall-clock (DOSE-VAR, `api/medications.py:953-957`). Result: for an LA user, a reminder for 08:00 fires near 08:00 UTC (00:00/01:00 local), even without adaptive windows. `_check_dose_taken_today` (`:386-408`) and `_count_reminders_today` (`:500-518`, `utcnow().date()` at `:507`) use UTC day bounds. `_send_notification` builds `is_weekend` / `hour_of_day` from UTC now (`:534-542`). #97 kept learned windows in UTC on purpose (comment in learn_patterns after #97; `test_hc_adhere_tz_001` asserts the UTC frame).

**Design:**

1. `_check_profile_schedules`: `tz = await profile_timezone_name(db, profile_id)`; `local_now = to_local(utcnow(), tz)`; `current_time = local_now.time().replace(tzinfo=None)`, `today = local_now.date()`, `current_weekday = local_now.weekday()`. Thread `tz` into the 3 helpers below. The pass-level rate-limit clock in `_check_all_schedules` (`:274`) stays UTC.
2. `_check_dose_taken_today(..., today, tz, db)`: `start, end = local_day_bounds_utc(today, tz)`; filter `taken_at >= start, taken_at < end`. This also replaces the `23:59:59` inclusive end.
3. `_count_reminders_today(..., today, tz, db)`: `sent_at >= start, sent_at < end` from the same bounds. `ReminderLog.sent_at` stays naive UTC.
4. `_send_notification(..., tz)`: `local_now` for `is_weekend` / `hour_of_day`; pass `tz_name=tz` to `calculate_streak` (replaces D-1's lookup there).
5. `modules/adherence_patterns.py::update_adaptive_windows`: add `tz_name: str = "UTC"` and pass it to `learn_time_window`. `api/medications.py::learn_patterns` passes `tz_name`; delete #97's "Stays UTC on purpose" comment. Windows are now stored and shown (`ScheduleEditor.tsx:90-92`) in local time.
6. **One-time re-learn:** new profile migration `NNN_adaptive_windows_local`, numbered by lane C's C-PMIG contract (`lane-C-schema-lifecycle.md` §3.0): `NNN` = numeric prefix of the profile head on `origin/main` at this PR's final merge of main + 1, `down_revision` = that head string (`013` with `012_pinboards` only if nothing else landed first). Same PR updates the head literal: the 4 literals (`tests/test_care_tasks.py:809,825`, `tests/test_profile_migrations_sqlcipher_fallback.py:41`, `tests/test_source_spans.py:313`) before C-P6 merges, else the one constant `tests/support/migrations.py::PROFILE_HEAD`. Column data only: no FK (no `PROFILE_CHECKS` row), no new table (no `_SYNTHETIC_RESET_MODELS` / RESET-APPEND). Migration body: `UPDATE medication_schedules SET adaptive_window_start = NULL, adaptive_window_end = NULL`. Downgrade is a no-op (UTC-frame values cannot be rebuilt; documented in the file). Until the user presses "Learn patterns" again (`pages/MedicationDetail.tsx:116`), the scheduler uses `target_time ± default_window_tolerance_minutes` (`:427-434`), which step 1 makes correct. See open question Q1.

**Test-first** (harness: `tests/test_notification_scheduler_wiring.py` nsw_007 — tmp vault, `MockProvider`, `_stub_pattern_learner`; freeze `ns_module.utcnow`):

| Test | Asserts |
|---|---|
| `test_hc_sched_tz_001` | LA profile, `target_time=08:00`, now = 16:00Z (08:00 PST) → 1 notification; now = 08:00Z (00:00 PST) → 0 |
| `test_hc_sched_tz_002` | dose at 20:00 PST Jan 5 (04:00Z Jan 6), schedule 20:15 local, now 20:10 PST → no reminder (dose found inside the local day) |
| `test_hc_sched_tz_003` | 3 `ReminderLog` rows at 23:30 PST yesterday (07:30Z today) do not count toward today's cap |
| `test_hc_sched_tz_004` | `days_of_week_json=[4]` (Friday) and now = Friday 20:00 PST (Saturday 04:00Z) → schedule applies |
| `test_hc_sched_tz_005` | file found by slug (`glob("*_adaptive_windows_local.py")`, exactly 1), never by number; round trip upgrade → downgrade → upgrade on a seeded tmp vault (C-PMIG §3.0 #9, pattern `tests/test_care_tasks.py:795-826`, downgrade target read from the file's `down_revision`); after upgrade both window columns are NULL and `target_time` is unchanged |
| update `test_hc_adhere_tz_001` | after `learn-patterns`, `sched.adaptive_window_start <= time(8,0) <= sched.adaptive_window_end` (local frame). Intended change of #97's UTC-frame assertion, licensed by the owner's SCHED-TZ answer; not a weakening. |

**Acceptance:** `pytest tests/ -k "sched_tz or nsw or adhere_tz or phase3" -q` green; UTC-profile tests `nsw_007/008` unchanged; C-PMIG §3.0 #6 pre-merge check holds (no duplicate `down_revision`, exactly one profile head; HC-MIGHEAD-001 once E-3 merges); head-literal tests (`test_care_tasks`, `test_profile_migrations_sqlcipher_fallback`, `test_source_spans`) green; count slots re-measured.

**Rollback:** revert the PR. The migration's cleared windows stay cleared (they were in the wrong frame); the user re-learns.

### D-2 rev 2 — automatic re-learn (owner Q1, 2026-10-16)

**Owner answer (Q1, 2026-10-16):** "Re-learn automatically" — "Re-learn every schedule on first unlock (per-profile startup job while the vault is unlocked). No user action, but more code and a startup cost." This section **replaces step 6** of D-2 above and adds to its tests. Steps 1–5 (local clock, local day bounds, local `is_weekend`/`hour_of_day`, `tz_name` into `update_adaptive_windows`) stay as written.

**Base re-measured:** `origin/main` @ `527bc22` (2026-10-16, after D-1 #104 and D-3 #109). Profile head still `012_pinboards`; `tests/support/migrations.py` does not exist yet (C-P6 not merged), so the 4 head literals apply.

#### Trace

| Piece | Where (main @`527bc22`) | Fact that shapes the design |
|---|---|---|
| Learner | `modules/adherence_patterns.py::update_adaptive_windows` `:459-504` | Already takes `tz_name` (D-1). Learns **active** schedules only (`:474-475`) and writes a window **only when confident** (`:491`); otherwise the old window stays. Commits only if something changed (`:501`). |
| Learner core | `learn_time_window` `:188-261` | One `DoseTaken` query per schedule, 30-day lookback (`:202`), buckets by `to_local(taken_at, tz_name)` (`:227`). |
| Route | `api/medications.py::learn_patterns` `:1277`; window update `:1341-1346` | Computes `tz_name` (`:1321`) but does **not** pass it to `update_adaptive_windows` (comment "Stays UTC on purpose"). Rev 1 step 5 fixes this. |
| Storage | `models/medication.py::MedicationSchedule` `:137-138` | `adaptive_window_start/end` are `Time`, nullable; NULL means `target_time ± default_window_tolerance_minutes` (`notification_scheduler.py:427-434`). No profile-level key/value table exists in the profile DB. |
| Scheduler pass | `notification_scheduler.py::_check_all_schedules` `:271-306` | One pass every 60 s (`:263`) per registered profile, **inside the per-profile `asyncio.Lock`** (`:286`, P2-INFLIGHT), with its own try/except per profile (`:291-305`). |
| Unlock hook | `core/auth.py::open_profile_database_on_login` `:405-420` | Already registers the profile with the scheduler on unlock (D6), fail-soft. Close hook `:438-450` awaits `unregister_profile_session_and_wait`. |
| Migration on open | `core/profile_database.py:382-384` | Profile migrations run when the vault opens, so the new column exists before the first scheduler pass. |

#### Design (smallest correct version)

1. **Marker = one nullable column, per schedule:** `MedicationSchedule.adaptive_window_tz: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)` — the zone the stored window was learned in. NULL = "not yet re-learned in local time". Per-schedule rather than per-profile because the profile DB has no key/value table and `user_model_settings` may have no row for the profile; a per-schedule column needs no new table, no FK and no RESET-APPEND. "Per-profile marker" is then "no schedule of this profile has `adaptive_window_tz IS NULL`".
2. **Migration still marks windows stale: yes.** `NNN_adaptive_windows_local` (C-PMIG, contracts §c: `NNN` = profile head on `origin/main` at final merge of main + 1; today that is `013`, `down_revision = "012_pinboards"`). Upgrade: `op.add_column("medication_schedules", sa.Column("adaptive_window_tz", sa.String(64), nullable=True))` then `UPDATE medication_schedules SET adaptive_window_start = NULL, adaptive_window_end = NULL`. Downgrade: `UPDATE medication_schedules SET adaptive_window_start = NULL, adaptive_window_end = NULL`, then `op.drop_column(...)` (via `batch_alter_table`). Clearing again on downgrade matters: after a re-learn the windows are local-frame, and the pre-D-2 scheduler would read them as UTC (Codex r1 #1). Original UTC-frame values are not restored (cannot be rebuilt; docstring says so). Why still clear: between upgrade and the first successful re-learn the scheduler must not read UTC-frame windows as local; clearing makes the fail-soft fallback (`target_time ± tolerance`, `:427-434`) automatic with **zero** scheduler code, and the UI (`ScheduleEditor.tsx:90-92`) stops showing wrong-frame windows.
3. **Learner method** (`modules/adherence_patterns.py`, ~15 lines): `PatternLearner.relearn_unmarked_windows(profile_id, db, tz_name) -> int`. Loads the `MedicationSchedule` rows joined to `Medication` where `Medication.profile_id == profile_id` and `adaptive_window_tz IS NULL` (active **and** inactive). For each row only: `pattern = await self.learn_time_window(row.medication_id, row.id, db, tz_name=tz_name)` (reuse; no new learning code); if `pattern and pattern.confidence >= self.CONFIDENCE_THRESHOLD`, set both window columns; always set `row.adaptive_window_tz = tz_name`. **One `commit` at the end**, so a failure part-way leaves nothing half-done. It does **not** call `update_adaptive_windows`: that method rewrites every active schedule of the medication (`:470-479`), so one new unmarked schedule would re-learn its already-marked siblings (Codex r1 #3). Marking every loaded row — including inactive and low-confidence schedules — is what makes it run once; otherwise those rows would be retried every unlock. Returns the number of rows marked. `update_adaptive_windows` also sets `schedule.adaptive_window_tz = tz_name` on each window it writes (1 line), so a manual "Learn patterns" records its frame too.
4. **Trigger = the existing scheduler pass, not `core/auth.py`.** In `_check_profile_schedules`, right after rev 1 step 1 computes `tz`, call `await self._relearn_windows_once(profile_id, tz, db)` before the medication query, so this same pass already uses the fresh windows. `_relearn_windows_once` (scheduler, ~15 lines):
   - returns at once if `profile_id in self._relearn_attempted` (a `set[str]`); else adds it, then calls the learner method;
   - on any `Exception`: `await db.rollback()`, `logger.warning("Adaptive-window re-learn failed for profile %s (%s); retrying on next unlock", profile_id, type(exc).__name__)` — class name only, no `exc_info`, no message (SQLAlchemy messages carry bound parameters; S01) and **no medication names** (P2 rule) — and returns; the reminder pass continues on `target_time ± tolerance`;
   - `unregister_profile_session` and `unregister_profile_session_and_wait` also `self._relearn_attempted.discard(profile_id)`, so a failed attempt retries on the **next unlock**, not every 60 s (no log spam). A successful attempt persists its marker, so later unlocks cost one probe query that returns 0 rows.
5. **Concurrency.** Same profile unlocked twice (two tabs, two logins): `register_profile_session` just replaces the dict entry; the single scheduler runs passes under the per-profile lock (`:286`), and the attempted-set is checked inside that lock, so the job runs once. Re-learn racing a manual `POST /medications/{id}/learn-patterns`: both compute the same windows from the same doses in the same zone; last write wins with identical values. Different profiles use different vault files. Cross-process: the app runs one uvicorn process (`dev.ps1:799,905` and `main.py:188` pass no `--workers`), so one scheduler serves a vault. A second process would recompute identical values from identical inputs and commit them in one transaction each, so the result is the same; no durable claim row (YAGNI; add one only if multi-worker serving is ever supported) (Codex r1 #4).
6. **`core/auth.py`: not touched.** The D6 registration hook already runs on every unlock and the scheduler pass is the "per-profile startup job while the vault is unlocked". No D2-AUTH gate is needed. Cost: the re-learn happens on the first pass after unlock (≤ `check_interval_seconds` = 60 s later), not inside the login request. Exception: while the global hourly cap (`max_notifications_per_hour` = 10) is reached, `_check_all_schedules` returns before visiting any profile (`:279-282`), so the re-learn waits for the hourly reset (≤ 1 h). Accepted, not changed: during that wait no reminder is sent anyway and windows fall back to `target_time ± tolerance`, which rev 1 step 1 makes correct (Codex r1 #2, documented rather than moving the cap check).
7. **Not done (YAGNI):** re-learn when the user later changes time zone (`adaptive_window_tz != tz`). The stored zone makes it a one-condition change; see Q5. No API or UI field for `adaptive_window_tz`.

**Startup-cost bound:** off the login path (login latency +0). Once per profile, on the first pass after unlock: 1 query loading the unmarked schedules + 1 `DoseTaken` query per schedule + 1 commit — S + 1 queries for S schedules (21 for 10 medications × 2 schedules). Each `DoseTaken` query loads every non-skipped dose of that schedule in the last 30 days with `.all()` (`:202-216`): about 30 rows at one dose a day; rows logged more often scale it linearly, with no cap (Codex r1 #5). It holds the profile lock, so it delays that pass's reminders by the same amount. After success: 1 probe per unlock, 0 per pass.

#### Test-first (RED each before the change; adds to rev 1's `sched_tz_001`–`_004`, replaces `_005`)

Harness: `tests/test_notification_scheduler_wiring.py` nsw_007 (tmp vault, `MockProvider`, freeze `ns_module.utcnow`). Tests that need the real learner do **not** call `_stub_pattern_learner`; the stub tests stay as they are (the stub has no `relearn_unmarked_windows`, so they also exercise the fail-soft path; they must stay green).

| Test | File | Asserts |
|---|---|---|
| `test_hc_sched_tz_005` (replaces rev 1) | `tests/test_notification_scheduler_wiring.py` | migration found by slug (`glob("*_adaptive_windows_local.py")`, exactly 1); upgrade → downgrade → upgrade on a seeded tmp vault (pattern `tests/test_care_tasks.py:795-826`, downgrade target from the file's `down_revision`); after upgrade both window columns are NULL, `adaptive_window_tz` exists and is NULL, `target_time` unchanged; then set local windows + marker (as a re-learn would) and downgrade → both window columns NULL and the column gone |
| `test_hc_sched_tz_006` | same | LA profile, schedule with `adaptive_window_tz = NULL`, 10 doses at 08:00 PST (16:00Z); one pass → `adaptive_window_start <= time(8,0) <= adaptive_window_end` and `adaptive_window_tz == "America/Los_Angeles"` |
| `test_hc_sched_tz_007` | same | runs once: spy on `relearn_unmarked_windows`; two passes → awaited once; after `unregister_profile_session_and_wait` + re-register, a third pass probes and marks nothing (returns 0) |
| `test_hc_sched_tz_008` | same | fail-soft: learner `relearn_unmarked_windows` raises `RuntimeError("Metformin")`; the pass still sends 1 reminder at `target_time` (fallback window), marker stays NULL, `"Metformin" not in caplog.text`; second pass in the same session does not retry; after unlock cycle with a working learner → marker set |
| `test_hc_sched_tz_009` | same | inactive schedule and a schedule with < `MIN_SAMPLES_FOR_PATTERN` doses both end with `adaptive_window_tz` set and windows NULL |
| `test_hc_sched_tz_010` | same | two concurrent `_check_all_schedules()` via `asyncio.gather` → learner awaited once |
| `test_hc_sched_tz_011` | same | one medication, schedule A marked `UTC` with window 16:00–17:00, schedule B unmarked; LA profile; one pass → A's window and marker unchanged, B learned in LA and marked |
| update `test_hc_adhere_tz_001` | `tests/test_adherence_patterns_tz_http.py` (HTTP, existing `_client`) | after `POST /medications/{id}/learn-patterns`, window holds `time(8,0)` (local frame) and `adaptive_window_tz == LA` — intended change licensed by SCHED-TZ, not a weakening |

The only route touched is `learn-patterns`, covered over HTTP above. Login is not changed, so no new login test; existing auth route tests must stay green.

#### Files

`be/models/medication.py` (1 column), `be/migrations/profile/versions/NNN_adaptive_windows_local.py` (new), `be/modules/adherence_patterns.py`, `be/modules/notification_scheduler.py`, `be/api/medications.py` (rev 1 step 5), `be/tests/test_notification_scheduler_wiring.py`, `be/tests/test_adherence_patterns_tz_http.py`, head literals (`be/tests/test_care_tasks.py:809,825`, `be/tests/test_profile_migrations_sqlcipher_fallback.py:41`, `be/tests/test_source_spans.py:313`; or `be/tests/support/migrations.py::PROFILE_HEAD` if C-P6 lands first), count slots. Not touched: `core/auth.py`, any ask-first file.

#### Acceptance

```bash
cd "$(git rev-parse --show-toplevel)/src/backend"
"$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ -k "sched_tz or nsw or adhere_tz or phase3 or care_tasks or sqlcipher_fallback or source_spans" -q
grep -h "^down_revision" migrations/profile/versions/*.py | sort | uniq -d    # prints nothing
~/venvs/asclexis-311/bin/python -c "from alembic.script import ScriptDirectory; from core.migrations import _get_alembic_config as c; print(ScriptDirectory.from_config(c('profile')).get_heads())"   # exactly one head
python3 ../../scripts/time_source_lint.py    # exit 0
"$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q | tail -1   # previous + 11 (sched_tz_001–011) → write to slots
```

Full backend suite under `flock /tmp/claude-1000/hc-pytest.lock` before merge; `nsw_007/008` and UTC-profile tests unchanged.

**Rollback (forward-only for the migration):** do **not** `git revert` the whole PR. Vaults upgrade on open (`core/migrations.py:171,330` `command.upgrade(config, "head")`); a vault already at `NNN_adaptive_windows_local` opened by a build without that file fails with an unknown-revision error, and unlock returns 500 (`core/auth.py:397-402`). Instead revert only the code (`notification_scheduler.py`, `adherence_patterns.py`, `api/medications.py`, the model column may stay) and add a new head migration `NNN+1_clear_adaptive_windows` that sets both window columns to NULL, so the pre-D-2 UTC scheduler never reads a local-frame window as UTC; it falls back to `target_time ± tolerance`. The extra nullable `adaptive_window_tz` column is harmless to old code. The file's own `downgrade()` (clear windows, drop column) is for dev/test round trips (`_005`). Users can press "Learn patterns". No data other than learned windows is changed. (Rev 1's "revert the PR" had the same hazard; this replaces it.)

### D-3 — GAM2-STREAK0

**Owner answer (`:145`):** "Count through yesterday (Recommended)": "Streak stays at N until the day ends with no dose; separate small PR after #84 merges."

**Bug:** `modules/streak_engine.py:35-46` `compute_streak` returns 0 when `as_of_date` has no dose, so `GET /gamification/streaks` (`api/gamification.py:172-175`, after #84 `:173-178`) shows "New streak starts today" every morning.

**Design (1 line, route only):** in `get_streaks`,
`current = compute_streak(doses, tz, as_of_date) or compute_streak(doses, tz, as_of_date - timedelta(days=1))`.
`compute_streak` returns 0 exactly when `as_of_date` has no dose, so `or` is the owner's rule. `compute_streak` itself is unchanged, so badge evaluation (`modules/badge_evaluator.py:114,134`, called with the logged dose's own date) is unchanged. Also replace `_profile_timezone_name` (`api/gamification.py:57-65`) with `safe_zone_name` (§2).

**Test-first** (`tests/test_gamification_api.py`, `_FrozenNow` = Mar 4 12:00Z):

| Test | Asserts |
|---|---|
| `test_hc_gam_http_013` | doses Mar 1–3, none Mar 4 → `current_streak_days == 3` (RED: 0 today) |
| `test_hc_gam_http_014` | doses Mar 1–2, none Mar 3–4 → `0` (a full day without a dose ends it) |

Existing `test_hc_gam_http_002/003/007/008/009` keep their values (checked: none has an ongoing streak that ends yesterday).

**Acceptance:** `pytest tests/ -k "gam_http or streak_engine or badge" -q` green; Vitest `Gamification.test.tsx` unchanged and green (copy at 0 is unchanged).

**Rollback:** revert; no data.

### D-4 — CORRELATION-NORMALISE

**Source:** security-reviewer LOW-2 on PR #45 (`wave-3-L1-A.md:165-176`): `monitoring/correlation.py:50` stores `raw`, so `{…}`, `urn:uuid:…` and upper-case forms pass the `uuid.UUID(raw)` check and are echoed and logged non-canonically.

**Design (1 line):** `correlation_id = str(uuid.UUID(raw))` at `monitoring/correlation.py:50`.

**Test-first:** `tests/monitoring/test_correlation.py::test_hc_obsv_005` parametrized over `urn:uuid:<u>`, `{<U>}`, upper-case `<U>` → response header and `get_correlation_id()` equal `str(uuid.UUID(<u>))`; a canonical input is echoed unchanged.

**Acceptance:** `pytest tests/monitoring/test_correlation.py tests/security/test_audit_middleware.py -q` green. F-2 / O-C3-4 (INFO logs not visible) stays out of scope.

**Rollback:** revert.

**Gate:** registered under "Program owner items", which says each is owner-gated and none is approved (`implementation-program.md:456`). Dispatch only after an owner go.

### MED-STREAK-GRACE — the per-medication streak still resets each morning (owner ruling = Q2)

**Source:** queue status 2026-10-16 (second batch), a D-3 follow-up; open question Q2 in §7. Planned on `origin/main` @ `b54f105`.

**Fact (re-read on `b54f105`):** three surfaces compute "current streak", and only one applies the owner's GAM2-STREAK0 rule ("Count through yesterday", `owner-decisions:146`):

| Surface | Code | Missed-morning value |
|---|---|---|
| Gamification widget `GET /gamification/streaks` | `api/gamification.py:169-171`: `compute_streak(as_of) or compute_streak(as_of - 1 day)` | N (grace) |
| Per-medication `GET /medications/{id}/stats` (`AdherenceDashboard.tsx:97-100` → `StreakDisplay`) | `api/medications.py:1234-1244` `_calculate_current_streak` → `compute_streak(doses, tz, today)` | **0** |
| Reminder text: `POST /notifications/test/{id}` (`api/notifications.py:454`) and the scheduler (`modules/notification_scheduler.py:564`) | `modules/adherence_patterns.py:441-452` `calculate_streak`: its own loop from `today` | **0**; a reminder fires only when today's dose is not logged, so under today's rule it always says 0 |

**Owner gate MSG-SCOPE (= Q2).** Options:
- **(a) Recommended:** apply the grace at all three. `_calculate_current_streak` returns `compute_streak(.., today) or compute_streak(.., today - 1)`. `calculate_streak` replaces its own current-streak loop (`:441-452`) with the same two `compute_streak` calls (one engine, recurring-failures #9). `compute_streak` and badges stay unchanged, as in D-3.
- (b) Stats route only, so the dashboard matches the widget. Reminder text keeps 0.
- (c) No change. Close the row.

**Test-first** (RED on `b54f105`; doses at 17:00Z = 09:00 PST, profile `America/Los_Angeles`, using the STREAK-TZ helpers `_seed_la_doses` / `_freeze_utcnow` in `tests/test_medications_routes_http.py:383-401`):

| Id | File | Assertion | RED? |
|---|---|---|---|
| HC-MSG-001 | `tests/test_medications_routes_http.py` | doses Jan 13–15, now Jan 16 18:00Z (10:00 PST, no dose today) → `GET /medications/{id}/stats` `current_streak_days == 3` | yes (0) |
| HC-MSG-002 | same | doses Jan 13–14, now Jan 16 18:00Z (Jan 15 had none) → `0` | no (pin: a full day without a dose ends it) |
| HC-MSG-003 | same | same seed as 001, single medication → stats `current_streak_days` == `GET /gamification/streaks` `current_streak_days` (both routes over `route_client`) | yes (0 vs 3) |
| HC-MSG-004 (a only) | `tests/test_notification_routes_http.py` | seed as 001 → `POST /notifications/test/{id}` passes `MessageContext.current_streak == 3` (spy pattern of `test_hc_streak_tz_003`) | yes (0) |

**Files:** `src/backend/api/medications.py`, `src/backend/modules/adherence_patterns.py` (a only), `src/backend/tests/test_medications_routes_http.py`, `src/backend/tests/test_notification_routes_http.py` (a only).

**Expected collected delta:** +4 under (a), +3 under (b).

**Acceptance:** `pyt tests/test_medications_routes_http.py tests/test_notification_routes_http.py tests/test_gamification_api.py tests/test_streak_engine.py tests/test_adherence_patterns_tz_http.py tests/test_notification_scheduler_wiring.py -q`: 0 failed. Existing `hc_streak_tz_001/002` keep their values. `hc_streak_tz_003` keeps 3, because today has a dose there. Full suite per RUNBOOK §6. **Rollback:** revert; no data.

**Order:** never beside AUDIT-MISSING-MED (`api/medications.py`, both test files).

### AUDIT-MISSING-MED — two profile-data routes write no audit row

**Source:** queue status 2026-10-16 (second batch), a D-1 follow-up; CLAUDE.md hard invariant "Audit logging on every route that touches documents, observations, or profile data".

**Fact (`b54f105`):**
- `GET /medications/{medication_id}/stats` (`api/medications.py:1101-1105` `get_adherence_stats`) reads doses and returns adherence and streaks. It has no audit call and takes no `master_db`. The middleware does not cover it: `security/audit_middleware.py` logs only mutating methods (`MUTATING_METHODS`, `:20`), and only to the log (`tests/security/test_audit_middleware.py:83` `test_get_skipped`).
- `POST /notifications/test/{medication_id}` (`api/notifications.py:417-421` `send_test_medication_notification`) reads the medication and its streak, then sends a notification. No audit call. The middleware writes a `SECURITY_AUDIT` log line, not an audit row.
- **Found while planning (wider than the row):** `api/notifications.py` has **no** audit call at all. `log_document_event` is imported at `:23` and never used. Yet `tests/test_audit_order_guard.py:92-93` classifies `update_notification_settings` and `record_reminder_interaction` as `"C"` (audit after change). Those two handlers commit (`:267`, `:560`) and write no row. The guard checks that a handler is classified, not that the class is true: recurring-failures #9. Not fixed here; new unplanned row **AUDIT-NOTIF-ALL** (queue).
- PR #130 (E-3a ruff cleanup) may delete the unused `log_document_event` import. This item re-adds what it needs after #130 merges.

**Design (pattern of `get_medication_correlations`, `api/medications.py:524-531`):**
1. `get_adherence_stats` takes `master_db: AsyncSession = Depends(get_db)`. After the access check, and before the response is built, it calls `await audit_and_commit(master_db, log_document_event, event="view", profile_id=session.profile_id, document_id=medication_id, details={"entity_type": "medication_adherence_stats"})`. This is fail-closed: an audit failure fails the request.
2. `send_test_medication_notification` takes `master_db` the same way and makes the same call with `"entity_type": "medication_test_notification"`, **before** the notification is generated and sent, so an unaudited read never reaches the OS notifier. Import `audit_and_commit` from `core.audit`.
3. Both handlers now commit, so `tests/test_audit_order_guard.py` (HC-AUD-ORD-030) fails until they are classified. Add `"api/medications.py::get_adherence_stats"` and `"api/notifications.py::send_test_medication_notification"` as `"excluded: read route, audit_and_commit only"`.
4. No `core/audit.py` edit: action "Viewed document" and detail key `entity_type` are already allowlisted (`core/audit.py:36-60`, `:89`).

**Test-first** (over HTTP with `route_client`; spy = `monkeypatch.setattr(<module>, "log_document_event", spy)`, because `audit_and_commit` calls the `log_fn` object it is handed):

| Id | File | Assertion | RED? |
|---|---|---|---|
| HC-AUDMED-001 | `tests/test_medications_routes_http.py` | `GET /medications/{id}/stats` → 200 and exactly one spy call with `event="view"`, `profile_id=PROFILE`, `document_id=med_id`, `details["entity_type"] == "medication_adherence_stats"`; the master session's `commit` awaited | yes |
| HC-AUDMED-002 | same | spy raises → the stats body is not served (`raise_server_exceptions=False`, status 500) | yes (200 today) |
| HC-AUDMED-003 | `tests/test_notification_routes_http.py` | `POST /notifications/test/{id}` → one spy call with `entity_type == "medication_test_notification"`, recorded before `service.send` (call-order list) | yes |
| HC-AUDMED-004 | same | spy raises → `service.send` never awaited, response not 200 | yes |

**Files:** `src/backend/api/medications.py`, `src/backend/api/notifications.py`, `src/backend/tests/test_medications_routes_http.py`, `src/backend/tests/test_notification_routes_http.py`, `src/backend/tests/test_audit_order_guard.py` (2 classification rows).

**Expected collected delta:** +4.

**Acceptance:** the four tests above; `pyt tests/test_audit_order_guard.py tests/test_audit_phi_minimization.py tests/test_audit_order.py tests/test_medications_routes_http.py tests/test_notification_routes_http.py -q`: 0 failed. Full suite per RUNBOOK §6. **Rollback:** revert.

**Order:** never beside MED-STREAK-GRACE, and never beside another open PR on `tests/test_audit_order_guard.py` (C-GAM2B, E-2, B-5, C-GC1, RSI1-DONATE). Rebase after #130.

### EXPORT-TODAY-TZ — export dates use the UTC calendar day

**Source:** queue status 2026-10-16 (second batch); recurring-failures #9 names `modules/export.py:454` as the one remaining UTC-date hit.

**Fact (re-read on `b54f105`; the queue row's wording is corrected here):**
- `modules/export.py:454` `today = today or utcnow().date()` sets the 14-day near-due window (`NEAR_DUE_WINDOW_DAYS`, `:68`; used `:504`) for **open care-task questions**. The doctor-summary route does not pass care tasks (`api/export.py:417-420`), so `:454` does **not** change the doctor summary. It changes `POST /export/questions` (`api/export.py:653-658`), the visit-prep packet (`:782-787`) and the pinboard packet (`api/pinboards.py:497-500`). None of them passes `today`.
- What **does** date the doctor summary in UTC is the HTML footer, `Generated by Asclexis • {utcnow().strftime('%B %d, %Y')}` (`modules/export.py:401`, `render_html_summary`; PDF renders from it, `:407`). It is the same class as the visit-prep line `Generated: {generated_at.date().isoformat()}` (`:703`).
- Not in scope: stored timestamps (`generated_at=utcnow()`, `:164`, `:693`, `:717`; naive UTC is the storage rule), and observation dates rendered as `collected_at.strftime("%Y-%m-%d")` (`:203`, `:302`). Whether a lab's collection date should show in local time is a separate display question (new unplanned row **EXPORT-COLLECTED-TZ** if wanted).

**Design:** the routes compute `local_today = to_local(utcnow(), await profile_timezone_name(profile_db, profile_id)).date()` once (D-1 helpers, §2) and pass it:
1. `generate_questions(..., today=local_today)` at all four call sites (3 in `api/export.py`, 1 in `api/pinboards.py`).
2. `render_html_summary(summary_data, today: Optional[date] = None)` uses `today` for the footer. The two callers (`api/export.py:534`, `:882`) pass `local_today`.
3. `compose_visit_prep_packet(..., today: Optional[date] = None)` uses it for the `Generated:` line. `generated_at` itself stays UTC.

Defaults stay `utcnow().date()`, so module-level callers and tests are unchanged.

**Test-first** (profile `America/Los_Angeles`; freeze `api.export.utcnow`, `api.pinboards.utcnow` and `modules.export.utcnow` at `2026-01-16 01:00Z` = Jan 15 17:00 PST; RED on `b54f105`):

| Id | File | Assertion | RED? |
|---|---|---|---|
| HC-EXPTZ-001 | `tests/test_export_questions.py` | over HTTP (`route_client`), an open care task due `2026-01-30` (= UTC today + 14, local today + 15) → `POST /export/questions` has **no** follow-up question for it | yes (UTC window includes it) |
| HC-EXPTZ-002 | same | a task due `2026-01-29` (local + 14) → the follow-up question is present | no (pin: the window still includes its last day) |
| HC-EXPTZ-003 | `tests/test_export_redaction.py` (its doctor-summary HTTP fixture, `test_hc_expr_003` `:423`) | the HTML download footer contains `January 15, 2026`, not `January 16, 2026` | yes |
| HC-EXPTZ-004 | `tests/test_visit_prep_packet.py` | the packet markdown has `Generated: 2026-01-15` | yes |

**Files:** `src/backend/modules/export.py`, `src/backend/api/export.py`, `src/backend/api/pinboards.py`, `src/backend/tests/test_export_questions.py`, `src/backend/tests/test_export_redaction.py`, `src/backend/tests/test_visit_prep_packet.py`.

**Expected collected delta:** +4.

**Acceptance:** `pyt tests/test_export_questions.py tests/test_export_redaction.py tests/test_visit_prep_packet.py tests/test_export_api.py tests/test_fhir_export.py -q`: 0 failed. HC-EXPR-002 (CSV/JSON byte-for-byte) still green. `scripts/time_source_lint.py` clean. The recurring-failures #9 recheck grep returns no `utcnow().date()` in `modules/export.py`. Full suite per RUNBOOK §6. **Rollback:** revert.

**Order:** never beside C-GC1 (`api/export.py`, `api/pinboards.py`) or E-1b (`tests/test_export_redaction.py`). E-1 is merged (#106).

#### EXPORT-TODAY-TZ Design 2 rev — store the local date at generate (owner EXPORT-TODAY-TZ-DESIGN = B, 2026-10-18)

**Why a rev:** the build stopped at Task 0 on draft PR #155 ("blocked: tell L0" comment). Design 2 above has `api/export.py:534` and `:882` pass `local_today`. Those calls are in the download routes `download_summary` (`api/export.py:488-489`) and `download_visit_prep` (`:831-832`), and those routes have no `profile_db`, so they cannot look up the zone. Adding `ProfileDbSession` to them would run the vault dependency before the ownership check. The cross-profile 403 would then come from the dependency, with no `denial.cross_profile` row, and `tests/test_denial_audit.py:66-92` (HC-AUD-ORD-040/042) would fail. The owner chose (B) (owner-decisions row EXPORT-TODAY-TZ-DESIGN): "Record the local date when the summary or packet is generated and print that."

**Replaces Design 2 (the footer). Design 1 (`generate_questions(today=)`) and Design 3 (`compose_visit_prep_packet(today=)`) stand.** Lines below are at `b8a47c7` (main after #165).
1. **Routes compute the local date once.** These are the routes that have `ProfileDbSession`: `generate_doctor_summary` (`api/export.py:380-381`), `generate_questions` (`POST /export/questions`, `:614-615`; Design 1 only), `generate_visit_prep` (`:705-706`) and `export_pinboard_packet` (`api/pinboards.py:397`). Each computes `local_today = to_local(utcnow(), await profile_timezone_name(profile_db, profile_id)).date()` and uses it for Design 1 and, where it applies, Design 3. In `generate_visit_prep` and `export_pinboard_packet`, the lookup goes **after** the `confirm is not True` check (`api/pinboards.py:404`). HC-PKT-009 (`tests/test_visit_prep_packet.py:290-303`) and HC-PIN-004 (`tests/test_pinboards.py:195-204`) pass a bare `AsyncMock()` vault and expect the 400 first.
2. **Doctor summary:** after `redact_summary_data` (`api/export.py:450`) and before `_summary_store[...] = summary_data` (`:451`), set `summary_data["generated_on"] = local_today.isoformat()`. It is added after redaction, so `redact_summary_data` (I-10) and HC-EXPR-001/002/003 keep their semantics. The value is a bare ISO date with no user text. Note for C-GC1: the persisted `payload_json` gains this one key.
3. **Footer:** `render_html_summary(summary_data)` (`modules/export.py:401`) prints `date.fromisoformat(summary_data["generated_on"]).strftime('%B %d, %Y')` when the key is present, and `utcnow()` as today when it is absent. The fallback covers module-level callers (`tests/test_export_api.py:387`, `:403`) and store dicts seeded without the key. There is no `today` parameter. `download_summary` (`:533`) and the PDF path (`modules/export.py:407`) are unchanged: they render the stored dict. The footer now shows the **generation** date, not the download date.
4. **Visit prep:** `compose_visit_prep_packet(..., today=local_today)` (Design 3) also stores `packet["generated_on"] = (today or utcnow().date()).isoformat()` next to `generated_at` (`modules/export.py:718`). The `Generated:` line (`:704`) prints the same date.
5. **Visit-prep header (L0 ruling: in scope):** `download_visit_prep` builds `"date_range": f"Visit Prep Packet — {packet['generated_at'][:10]}"` (`api/export.py:874`). It now uses `packet.get("generated_on") or packet["generated_at"][:10]`, and the dict it hands to `render_html_summary` (`:873-878`) carries the same `generated_on`, so the header and the footer agree. Pinboard packets share `_packet_store` (`api/pinboards.py:13`, `:510`) and the same download route.
6. **Ownership and denial-audit order unchanged:** neither download route gains a dependency. `tests/test_denial_audit.py` is untouched; it seeds store dicts without `generated_on` and gets a 403 before any render.
7. **Seen, not in scope:** the text download's `Generated: {summary_data['generated_at']}` (`api/export.py:565`) prints the full UTC ISO timestamp, not a calendar day. Leave it; a new row if wanted.

**Tests (replace HC-EXPTZ-003; HC-EXPTZ-001/002/004 stand):** freeze `api.export.utcnow`, `api.pinboards.utcnow` and `modules.export.utcnow` at `2026-01-16 01:00Z` (Jan 15 17:00 PST), with profile zone `America/Los_Angeles`.

| Id | File | Assertion | RED? |
|---|---|---|---|
| HC-EXPTZ-003 | `tests/test_export_redaction.py` (`_export_client`, `:133-152`) | generate, then download HTML: footer `January 15, 2026`, not `January 16, 2026` | yes |
| HC-EXPTZ-005 | same | generate at the frozen time, move `utcnow` to `2026-01-18 12:00Z`, then download: footer is still `January 15, 2026`. This pins "the stored generation date" | yes |
| HC-EXPTZ-006 | `tests/test_visit_prep_packet.py` | over HTTP (`route_client`), `POST /export/visit-prep`, then `GET .../download?format=html`: body has `Visit Prep Packet — 2026-01-15` and `January 15, 2026` | yes |
| HC-EXPTZ-007 | same | a `_packet_store` entry seeded without `generated_on` still downloads as HTML with the `generated_at[:10]` header. Pins the fallback | no (pin) |

**Tests that pin changed behaviour (must be edited):**
- `tests/test_export_redaction.py`: `_FakeProfileDb.execute` returns the fixture rows for any query (`:107-114`), so the new zone lookup in `generate_doctor_summary` cannot read a settings row. `_export_client` (`:133-152`) patches `api.export.profile_timezone_name` to return `"UTC"`, or the test's zone for HC-EXPTZ-003/005. This keeps HC-EXPR-001/002/003 green.
- `tests/test_visit_prep_packet.py`: about ten `await generate_visit_prep(request, _make_session(), AsyncMock(), AsyncMock())` calls pass an `AsyncMock` vault. Patch `api.export.profile_timezone_name` to return `"UTC"` in `_patch_fetchers` (`:265-283`).

- `tests/test_pinboards.py`: HC-PIN-005 (`:208-262`) calls `export_pinboard_packet` directly with an `AsyncMock` vault whose `execute.side_effect` is a fixed list of 3 results (`:237-240`). An extra `execute` would shift or exhaust that list. Add `monkeypatch.setattr("api.pinboards.profile_timezone_name", AsyncMock(return_value="UTC"))` in HC-PIN-005. HC-PIN-004 needs no edit (see step 1).
- `tests/test_export_questions.py`: HC-QGN-013 (`:324-356`) calls the questions route with `profile_db=AsyncMock()`. Add the `api.export.profile_timezone_name` stub returning `"UTC"` there. This edit is required.

**Re-run, not edited** (their vaults are real SQLite with `ProfileDatabaseBase.metadata.create_all`, so the lookup returns `"UTC"`; the real-SQLite pinboard export path is `tests/test_audit_order.py:598`):
- `tests/test_utc_sweep_http.py` (`:229`, `:240`)
- `tests/test_rl_export_prompt_snapshot.py`
- `tests/test_audit_order.py`
- `tests/test_export_api.py` (module-level `render_html_summary`, fallback path)
- `tests/test_denial_audit.py`
- `tests/test_fhir_export.py`

**Files (rev):** `src/backend/modules/export.py`, `src/backend/api/export.py`, `src/backend/api/pinboards.py`, `src/backend/tests/test_export_questions.py`, `src/backend/tests/test_export_redaction.py`, `src/backend/tests/test_visit_prep_packet.py`, `src/backend/tests/test_pinboards.py`, slots. **Expected collected delta:** +7 (HC-EXPTZ-001…007).

**Acceptance (rev):** the base acceptance above, plus `tests/test_denial_audit.py tests/test_pinboards.py tests/test_utc_sweep_http.py tests/test_rl_export_prompt_snapshot.py tests/test_audit_order.py` with 0 failed and `git diff origin/main -- src/backend/tests/test_denial_audit.py` empty.

### AUDIT-NOTIF-ALL — `api/notifications.py` writes no audit row on any route

**Source:** queue status 2026-10-17 (found while planning AUDIT-MISSING-MED), queue row AUDIT-NOTIF-ALL; CLAUDE.md hard invariant "Audit logging on every route that touches documents, observations, or profile data"; recurring-failures #9.

**After AUDIT-MISSING-MED (merged #165, `d427868`).** That item covered exactly one notifications route, `POST /notifications/test/{medication_id}` (`send_test_medication_notification`), and its guard row (`tests/test_audit_order_guard.py:94`, `excluded: read route`). This item does not touch that handler or that row. The imports it needs are on main: `Depends` (`api/notifications.py:17`), `audit_and_commit, log_document_event` (`:22`) and `get_db` (`:24`).

**Fact (`b8a47c7`, main after #165):**
- The only audit call in `api/notifications.py` is AUDIT-MISSING-MED's, inside `send_test_medication_notification` (`:452`).
- Every route in the file (prefix `/notifications`, `api/__init__.py:53`):

| Route | Handler | Profile data touched | Audit today | This item |
|---|---|---|---|---|
| `GET /settings/{medication_id}` | `get_notification_settings` `:145-193` | reads `Medication` (vault) | none | **add** read audit |
| `PATCH /settings/{medication_id}` | `update_notification_settings` `:196-285` | writes `Medication.reminder_enabled` and `metadata_json`; vault commit `:266` | none; the guard says `"C"` (`tests/test_audit_order_guard.py:93`) | **add** C audit |
| `GET /history` | `get_notification_history` `:288-379` | reads `ReminderLog` and `Medication` | none | **add** read audit |
| `POST /test` | `send_test_notification` `:382-413` | none: no `profile_db`, text comes from the request | none | none (no profile data) |
| `POST /test/{medication_id}` | `send_test_medication_notification` `:416-500` | reads `Medication`, the streak | `audit_and_commit` view row (`:452`, #165) | done by AUDIT-MISSING-MED (HC-AUDMED-003/004) |
| `GET /scheduler/status` | `get_scheduler_status` `:503-525` | none: process-wide scheduler counters | none | none (no profile data) |
| `POST /{reminder_id}/interaction` | `record_reminder_interaction` `:528-572` | writes `ReminderLog`; vault commit `:570` | none; the guard says `"C"` (`:95`) | **add** C audit |

- The guard (HC-AUD-ORD-030) checks that a committing handler is *classified*, not that the class is true. `security/audit_middleware.py` logs mutating methods to the app log only, never as an audit row (`tests/security/test_audit_middleware.py:83`).
- **Found while planning (wider than this row, not fixed here):** the recurring-failures #9 recheck, applied to every `"C"` and `"A2"` row of the guard, also finds 17 handlers with no audit call in their body and none reached through a helper. They are `api/assistant.py` `create_session` `:430`, `delete_session` `:483`, `update_memory_settings` `:539`; `api/medications.py` `update_medication` `:561`, `create_schedule` `:696`, `update_schedule` `:790`, `delete_schedule` `:859`, `log_dose` `:912`, `learn_patterns` `:1285`; `api/model_settings.py` `run_hardware_detection` `:445`, `set_model_tier` `:486`, `start_model_download` `:634`, `save_external_api_settings` `:730`, `set_timezone` `:967`, `update_voice_settings` `:1002`, `update_ocr_settings` `:1105`, `update_agent_settings` `:1133`. The `api/interpretations.py` rows audit through `_audit_interpretation`, so they are not in the list. Method: an AST walk of each handler body for `audit_and_commit`, `audit_intent`, `log_*_event(`, `create_audit_log(`, `_emit_audit(`. Re-checked on `b8a47c7` (main after #165): same 17. They are now queue row **AUDIT-C-CLASS** (unplanned), and recurring-failures #9 records them.

**Design (helpers and event shapes already in use; no new helper, no `core/audit.py` edit):**
1. **C routes: the AUDIT-ORDER C pattern of `delete_medication`'s soft-delete branch (`api/medications.py:667-685`).** The handler commits the vault, then calls `log_document_event(db=master_db, ...)` (outside the `try`), then runs `master_db.commit()` inside `try`, as `api/medications.py:673-683` does. On failure it logs `logger.error("AUDIT-ORDER: audit commit failed after change (event=%s, entity=%s)", event, id)` (ids only) and re-raises. Result: the change stays durable, the request returns 500 and there is an ERROR line. This is AUDIT-ORDER plan `:205` (`docs/plans/2026-10-09-AUDIT-ORDER.md`). Event names follow the `medication_*` shape of `create_medication` (`:348-356`). `log_document_event` (`core/audit.py:306`) maps an unknown event to action `document.<event>`, equal to its `event_type`, so `_scrub_action` (`:174-193`) keeps it and does not warn (HC-AUD-010).
   - `update_notification_settings` takes `master_db: AsyncSession = Depends(get_db)`. After `:266-267`, it audits `event="notification_settings_update"`, `profile_id=session.profile_id`, `document_id=medication_id`, `details={"changed_fields": sorted(update.model_dump(exclude_none=True))}`. The details hold field names only, never values. `changed_fields` is allowlisted (`core/audit.py:80-83`), and `update_gamification_settings` uses the same shape (`api/model_settings.py:1063-1072`).
   - `record_reminder_interaction` takes `master_db` the same way. After `:570`, it audits `event="reminder_interaction"`, `document_id=reminder_id`, `details={"entity_type": "reminder_interaction"}`. The `interaction_type` (`marked_taken`, ...) is left out on purpose. It is adherence behaviour, and the master DB is unencrypted (AUDIT-PHI-001). Adding it later is one allowlisted `"action"` key.
2. **Read routes: the pattern of `get_medication_correlations` (`api/medications.py:522-529`).** The handler takes `master_db` and, after the access check and before the response is built, calls `await audit_and_commit(master_db, log_document_event, event="view", ...)`. This fails closed: an audit failure fails the request.
   - `get_notification_settings`: `document_id=medication_id`, `details={"entity_type": "notification_settings"}`.
   - `get_notification_history`: `document_id=medication_id or "all"` (the `"all"` handle follows `list_documents`, `api/documents.py:1093-1099`), `details={"entity_type": "notification_history", "count": len(reminders)}`.
   - Action "Viewed document" and the keys `entity_type` and `count` are already allowlisted (`core/audit.py:42`, `:70`, `:96`).
3. **Guard:** the two `"C"` rows (`tests/test_audit_order_guard.py:93`, `:95`) stay, and now they are true. The two read handlers now commit, so HC-AUD-ORD-030 fails until they are classified. Add `"api/notifications.py::get_notification_settings"` and `"api/notifications.py::get_notification_history"` as `"excluded: read route, audit_and_commit only"`, in file order.

**Test-first** (`tests/test_notification_routes_http.py`, all over HTTP):
- **Client:** every row uses `route_client(notif_router, "/notifications", profile_id=PROFILE, master_db=master)` with an explicit `master = AsyncMock()`, so `master.commit` can be asserted. This is the HC-AUDMED-003 shape (`:90-101`). The `profile_db` fixture override follows `:45-49`.
- **Failure rows:** set `master.commit.side_effect = RuntimeError` (002/004), or make the spy raise (006/008). Both add `raise_server_exceptions=False`.
- **Seeds:** the shared `profile_db` fixture seeds nothing by itself. Each test inserts what it needs: a `Medication(id=med_id, profile_id=PROFILE, name="Metformin", frequency="once_daily", is_active=True, reminder_enabled=True)` and, for 003/004/007/008, a `ReminderLog(...)` for that medication. Copy the HC-UTC-005 seed (`tests/test_utc_sweep_http.py:146-153`) as a local insert, then `await profile_db.commit()`.
- **Spy:** `monkeypatch.setattr(notif_api, "log_document_event", spy)`. The spy records its kwargs and appends `"audit"` to an order list.
- **Vault order:** wrap `profile_db.commit` with `monkeypatch.setattr` so each call appends `"vault"`, installed after seeding.
- Every row is RED on `b8a47c7`.

| Id | Route | Assertion | RED? |
|---|---|---|---|
| HC-AUDNTF-001 | `PATCH /notifications/settings/{id}` `{"enabled": false, "quiet_hours_start": "22:00"}` | 200; one spy call with `event="notification_settings_update"`, `profile_id=PROFILE`, `document_id=med_id`, `details == {"changed_fields": ["enabled", "quiet_hours_start"]}`; order `["vault", "audit"]`; `master.commit` awaited | yes (no call) |
| HC-AUDNTF-002 | same, master commit raises | 500; the vault row is still changed (`reminder_enabled is False` on re-select); exactly one ERROR record containing `AUDIT-ORDER` and `med_id`; the medication name is not in `caplog.text` | yes (200 today) |
| HC-AUDNTF-003 | `POST /notifications/{reminder_id}/interaction?interaction_type=snoozed&snooze_minutes=10` | 204; one spy call with `event="reminder_interaction"`, `document_id=reminder_id`, `details == {"entity_type": "reminder_interaction"}`; order `["vault", "audit"]` | yes |
| HC-AUDNTF-004 | same, master commit raises | 500; `ReminderLog.was_interacted` is True on re-select; one `AUDIT-ORDER` ERROR record with `reminder_id` | yes (204 today) |
| HC-AUDNTF-005 | `GET /notifications/settings/{id}` | 200; one spy call with `event="view"`, `document_id=med_id`, `details == {"entity_type": "notification_settings"}`; `master.commit` awaited | yes |
| HC-AUDNTF-006 | same, spy raises | status 500, the settings body is not served | yes (200 today) |
| HC-AUDNTF-007 ×2 | `GET /notifications/history`, parametrized: no filter / `?medication_id=<id>` | 200; one spy call with `event="view"`, `document_id == "all"` / `== med_id`, `details == {"entity_type": "notification_history", "count": 1}` | yes ×2 |
| HC-AUDNTF-008 | `GET /notifications/history`, spy raises | status 500 | yes (200 today) |

What these tests would not notice: the stored row's columns. The spy sees the helper's kwargs, not the `AuditLog` row, and `log_document_event` hard-codes `entity_type="document"`, as for every medication row today. The helper's row shape is pinned by HC-AUD-004 (`tests/test_audit_phi_minimization.py:180`), not here.

**Files:** `src/backend/api/notifications.py`; `src/backend/tests/test_notification_routes_http.py`; `src/backend/tests/test_audit_order_guard.py` (2 new `excluded:` rows; the `"C"` rows `:93`, `:95` unchanged); `docs/agentic/recurring-failures.md` (#9: mark the notifications instance fixed; keep the AUDIT-C-CLASS list); slots. **Re-run, not edited:** `src/backend/tests/test_utc_sweep_http.py` (HC-UTC-005 calls `GET /notifications/history` through `route_client`, whose default `AsyncMock` master absorbs the new audit write) and `src/backend/tests/test_notification_scheduler_wiring.py` (`GET /scheduler/status`, unchanged).

**Expected collected delta:** +9 (8 ids, HC-AUDNTF-007 parametrized ×2).

**Acceptance:** the nine tests above; `pyt tests/test_notification_routes_http.py tests/test_audit_order_guard.py tests/test_audit_order.py tests/test_audit_phi_minimization.py tests/test_utc_sweep_http.py tests/test_notification_scheduler_wiring.py -q`: 0 failed. The recurring-failures #9 recheck run on `api/notifications.py` hits inside both `"C"` handlers. `cd src/backend && python -c "from main import app"`. Full suite per RUNBOOK §6. **Rollback:** revert; no data.

**Order:** AUDIT-MISSING-MED is merged (#165). Never beside MED-STREAK-GRACE (option (a) edits `tests/test_notification_routes_http.py`), AUDIT-C-MED or AUDIT-C-ASSIST (AUDIT-C-MSET is file-disjoint), and never beside another open PR on `tests/test_audit_order_guard.py` (E-2, B-5, C-GC1, RSI1-DONATE).

### AUDIT-C-CLASS — 17 `"C"` handlers write no audit row (split: AUDIT-C-MED, AUDIT-C-ASSIST, AUDIT-C-MSET, AUDIT-C-MSET-EXT)

**Source:** queue row AUDIT-C-CLASS (found planning AUDIT-NOTIF-ALL, PR #166, `f8ef7f8`); CLAUDE.md hard invariant "Audit logging on every route that touches documents, observations, or profile data"; recurring-failures #9. AUDIT-ORDER §3.1 (`docs/plans/2026-10-09-AUDIT-ORDER.md:130-142`) listed the same routes on 2026-10-09 as "write no audit row at all" and left them as a candidate item. Its execution decision 3 (`:452`) then classified them `"C"` "with no code change", so the guard row asserts an audit that was never written.

**Fact (`f8ef7f8`, re-walked for this plan).** Method: an AST walk of every `"C"`/`"A2"` row in `tests/test_audit_order_guard.py`. Each handler body, plus every same-file function it calls (transitively), is searched for a call to `audit_and_commit`, `audit_intent`, `log_*_event`, `create_audit_log`, `_emit_audit` or `_audit*`. There are 19 misses: the 2 `api/notifications.py` handlers that AUDIT-NOTIF-ALL (#172, in flight) fixes, plus the same 17 as on `b8a47c7`. Only `learn_patterns` moved (`:1285` → `:1288`, MED-STREAK-GRACE #167). Lines below are at `f8ef7f8`.

| File | Handler (lines) | Route | Vault commit | Planned class | Row |
|---|---|---|---|---|---|
| `api/medications.py` | `update_medication` `:561-616` | `PATCH /medications/{id}` | `:611` | C | AUDIT-C-MED |
| | `create_schedule` `:696-747` | `POST /medications/{id}/schedules` | `:743` | C | AUDIT-C-MED |
| | `update_schedule` `:790-852` | `PATCH /medications/{id}/schedules/{sid}` | `:849` | C | AUDIT-C-MED |
| | `delete_schedule` `:859-901` | `DELETE /medications/{id}/schedules/{sid}` | `:899` | **A2** (guard row changes) | AUDIT-C-MED |
| | `log_dose` `:912-1051` | `POST /medications/{id}/doses` | `:979` (dose), `:1036` (badges, best effort) | C | AUDIT-C-MED |
| | `learn_patterns` `:1288-1407` | `POST /medications/{id}/learn-patterns` | in `modules/adherence_patterns.py` (`save_patterns` `:668`, `update_adaptive_windows` `:500`/`:537`) | C | AUDIT-C-MED |
| `api/assistant.py` | `create_session` `:430-452` | `POST /assistant/sessions` | `:446` | C | AUDIT-C-ASSIST |
| | `delete_session` `:483-500` | `DELETE /assistant/sessions/{id}` | `:500` (turns go by ORM cascade, `models/chat_session.py:61-64`) | **A2** (guard row changes) | AUDIT-C-ASSIST |
| | `update_memory_settings` `:539-570` | `PATCH /assistant/memory-settings` | `:565` | C | AUDIT-C-ASSIST |
| `api/model_settings.py` | `run_hardware_detection` `:445-477` | `POST /settings/model/detect` | `:461` | C | AUDIT-C-MSET |
| | `set_model_tier` `:486-531` | `POST /settings/model/tier` | `:519` | C | AUDIT-C-MSET |
| | `start_model_download` `:634-692` | `POST /settings/model/download` | `:673` (none on the already-downloaded early return `:651-657`) | C | AUDIT-C-MSET |
| | `set_timezone` `:967-984` | `PUT /settings/model/timezone` | `:983` | C | AUDIT-C-MSET |
| | `update_voice_settings` `:1002-1020` | `PATCH /settings/model/voice` | `:1016` | C | AUDIT-C-MSET |
| | `update_ocr_settings` `:1105-1119` | `PATCH /settings/model/ocr` | `:1112` | C | AUDIT-C-MSET |
| | `update_agent_settings` `:1133-1142` | `PATCH /settings/model/agent` | `:1141` | C | AUDIT-C-MSET |
| | `save_external_api_settings` `:730-762` | `PUT /settings/model/external-api` | `:755` | C | **AUDIT-C-MSET-EXT (AUDIT-EXT-ASKFIRST = A)** |

**Ask-first check (CLAUDE.md §1).**
- `save_external_api_settings` is **encryption code**. It takes `ProfileEncryptionManager` (`:734`) and Fernet-encrypts the cloud API key (`:749-753`). It also switches the opt-in external runner on (`use_external_api`, D12). So it is ask-first. It is its own row, AUDIT-C-MSET-EXT, licensed by the owner's answer AUDIT-EXT-ASKFIRST = A (2026-10-18, PR #175; question below).
- `update_memory_settings` is **not** auth or encryption code. It flips one boolean on `UserModelSettings`, which decides whether stored memory items are injected into prompts (`_effective_use_memory`). It reads no credential, key or session token and calls nothing in `core/auth.py`, `modules/redaction.py` or the external runner. Not gated.
- `start_model_download` hands `_download_model_task` (`:894`, `hf_hub_download`) to `BackgroundTasks`: an existing outbound path, not an ask-first file. This plan does not touch it, and the tests patch it to a no-op.
- No other handler here touches `interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, `core/auth.py` or encryption. `api/model_settings.py` imports `redaction_bypass_active` (`:26`), but none of the 7 AUDIT-C-MSET handlers calls it.

**Design (shared by all four rows; no new `core/audit.py` helper or edit, no migration):**
1. **C pattern.** This is the template AUDIT-NOTIF-ALL uses: the soft-delete branch of `delete_medication` (`api/medications.py:666-683`). The vault commit runs first. Then the handler writes the audit row on `master_db` (outside a `try`) and runs `master_db.commit()` inside `try`. If that commit fails, it logs `logger.error("AUDIT-ORDER: audit commit failed after change (event=%s, entity=%s)", event, entity_id)` (ids only) and re-raises. The change stays durable, the request returns 500 and there is an ERROR line (AUDIT-ORDER plan `:205`, case (a) under C). Each handler gains `master_db: AsyncSession = Depends(get_db)`. All three files already import `Depends`, `AsyncSession` and `get_db`.
2. **One module-private helper per file, used at 5 sites (MED) or 7 sites (MSET).** The try/ERROR block repeats, so it lives once per file. The helper is not an abstraction over `core/audit.py`. AUDIT-C-ASSIST has 2 C sites and inlines them. Existing call sites (`delete_medication`, `create_medication`, `update_gamification_settings`) are **not** rewritten to use it (surgical edits).
   - `api/medications.py`: `async def _audit_after_change(master_db, event, profile_id, document_id, details=None)` calls `log_document_event(db=master_db, ...)`, then the try/commit/ERROR block.
   - `api/model_settings.py`: `async def _audit_settings_change(master_db, profile_id, event_type, entity_id, details=None)` calls `create_audit_log(db=master_db, event_type=event_type, action=event_type, profile_id=profile_id, entity_type="settings", entity_id=entity_id, details=details)`, then the same block. `action == event_type`, so `_scrub_action` keeps it and does not warn (`core/audit.py:174-193`). This is the `settings.<x>.<verb>` shape of `update_gamification_settings` (`:1063-1072`).
3. **A2 for the two hard deletes.** `delete_schedule` and `delete_session` destroy rows that the product cannot restore: a schedule's learned adaptive windows, and a chat session with its turns. Owner-signed AUDIT-ORDER option D says "A2 on the irreversible set, C on the rest" (`AUDIT-ORDER.md:270-276`), and its siblings `delete_memory_item` and `delete_pinboard` are A2. So both get `audit_intent(master_db, "started", ...)` before the delete and `"completed"` after the vault commit, as the hard branch of `delete_medication` does (`:655-665`). Their guard rows change `"C"` → `"A2"`. `test_hc_aud_ord_030_a2_handlers_reach_audit_intent` then enforces the call. This is a planner ruling under the signed option, not a new approval. The owner confirmed it: AUDIT-C-A2 = A (2026-10-18, PR #175). A2 is the conservative choice: a failed audit stops the delete.
4. **Details: field names and ids only, never values.** No medication name, dosage, instructions, schedule time or label, dose time, skip reason or note. No chat title, time-zone name, tier name, provider or key. `changed_fields` (`core/audit.py:80-83`) holds request field names only: `sorted(update.model_dump(exclude_none=True))`, matching the `is not None` checks in each handler. Adherence behaviour (`was_skipped`) is left out, as AUDIT-NOTIF-ALL leaves out `interaction_type` (AUDIT-PHI-001: the master DB is unencrypted).

**Event table (all new names; `log_document_event` maps an unknown event to action `document.<event>` = its `event_type`, so no warning, HC-AUD-010):**

| Handler | Helper call | `document_id` / `entity_id` | `details` | Placement |
|---|---|---|---|---|
| `update_medication` | `_audit_after_change(event="medication_update")` | `medication_id` | `{"changed_fields": [...]}` | after `:611-613`, before the response |
| `create_schedule` | `event="medication_schedule_create"` | `sched.id` | `None` | after `:743-744` |
| `update_schedule` | `event="medication_schedule_update"` | `schedule_id` | `{"changed_fields": [...]}` | after `:849-850` |
| `delete_schedule` | `audit_intent(..., log_document_event, event="medication_schedule_delete")` started/completed | `schedule_id` | `None` (+ `status`) | started after the 404 checks, before `:898`; completed after `:899` |
| `log_dose` | `event="medication_dose_log"` | `dose_record.id` | `None` | after the badge block (`:983-1042`), before `logger.info`. A master failure then cannot skip badge evaluation, and badges keep their best-effort rule |
| `learn_patterns` | `event="medication_learn_patterns"` | `medication_id` | `None` | after `update_adaptive_windows` returns (`:1352-1356`), before the response is built |
| `create_session` | inline `create_audit_log(event_type="assistant.session.create", action=same, entity_type="chat_session")` + try/ERROR | `new_session.id` | `None` | after `:446-447` |
| `delete_session` | `audit_intent(..., create_audit_log, event_type="assistant.session.delete", action=same, entity_type="chat_session")` | `session_id` | `None` (+ `status`) | started after the 404 check, before `:499`; completed after `:500` |
| `update_memory_settings` | inline, `event_type="settings.assistant_memory.update"`, `entity_type="settings"` | `"assistant_memory"` | `{"changed_fields": ["assistant_memory_enabled"]}` | after `:565-566` |
| `run_hardware_detection` | `_audit_settings_change("settings.hardware.detect")` | `"hardware"` | `None` | after `:461` |
| `set_model_tier` | `"settings.model_tier.update"` | `"model_tier"` | `{"changed_fields": ["tier"]}` | after `:519` (no row on the 400 path) |
| `start_model_download` | `"settings.model_download.start"` | `"model_download"` | `None` | after `:673`, before `background_tasks.add_task` (no row on the already-downloaded return, which commits nothing) |
| `set_timezone` | `"settings.timezone.update"` | `"timezone"` | `{"changed_fields": ["timezone"]}` | after `:983` |
| `update_voice_settings` | `"settings.voice.update"` | `"voice"` | `{"changed_fields": sorted(data.model_dump(exclude_none=True))}` | after `:1016` |
| `update_ocr_settings` | `"settings.ocr.update"` | `"ocr"` | `{"changed_fields": ["ocr_preference_enabled"]}` | after `:1112` |
| `update_agent_settings` | `"settings.agent.update"` | `"agent"` | `{"changed_fields": sorted(data.model_dump(exclude_none=True))}` | after `:1141` |
| `save_external_api_settings` (gated) | `"settings.external_api.update"` | `"external_api"` | `{"changed_fields": sorted(["provider", "use_external_api"] + (["api_key"] if request.api_key else []))}`: the handler assigns `use_external_api` and `provider` every time (`:743-744`) and the key only when it is truthy (`:749`); `model` is accepted but never stored, so it is not listed. Never the key, never the provider value | after `:755`; the encryption call `:749-753` is not touched |

`"api_key"` in `changed_fields` is a field name, and `_scrub_details` keeps id-list values only if they match `_ENUM_VALUE_RE` (`core/audit.py:113`), which a name does.

**Test pattern (all rows, over HTTP).**
- **Client:** `route_client(<router>, <prefix>, profile_id=PROFILE, master_db=master)` with an explicit `master` whose `commit` is an `AsyncMock`. This is the `_master_db()` shape of `tests/test_gamification_settings.py:31-34`, or a plain `AsyncMock()` as in HC-AUDMED-003. The vault is a real in-memory SQLite session installed with `client.app.dependency_overrides[get_profile_db_session]`, like the existing `profile_db` fixture of `tests/test_medications_routes_http.py:22-40`.
- **Spy and order:** `monkeypatch.setattr(<api module>, "log_document_event" | "create_audit_log", spy)`. The handlers and the per-file helpers look the name up in the module at call time, and `audit_intent` calls the `log_fn` it is handed. The spy records kwargs and appends `"audit"` (or `"audit:<status>"`) to an order list. `profile_db.commit` is wrapped after seeding, so each call appends `"vault"`.
- **Failure rows:** `master.commit.side_effect = RuntimeError` with `raise_server_exceptions=False`. Assert 500, the vault change on re-select, exactly one `AUDIT-ORDER` ERROR record containing the entity id, and that `caplog.text` holds no seeded clinical string (`"Metformin"`, the chat title, `"America/New_York"`).
- **A2 rows** reuse the parametrised harness in `tests/test_audit_order.py` (`Case`, `:96-154`; HC-AUD-ORD-001a/001b/002/003, real in-memory master with `FailingCommitSession`). The two new `Case`s are **appended** to `CASES`, because `test_hc_aud_ord_020` reads `CASES[1]`. They need a `seed`/`url`/`present` branch each: `schedule` seeds a `Medication` plus a `MedicationSchedule` and keeps the parent id on the case for `url`. `chat_session` seeds a `ChatSession` with one `ChatTurn`, and its `url` is `/assistant/sessions/{id}`.
- **What these tests would not notice:** the stored row's columns for spy-based C rows. The A2 rows use a real master and do see `entity_id`. No test pins the stored shape of the new `log_document_event` C rows: HC-AUD-004 (`tests/test_audit_phi_minimization.py:180`) only checks that the actions in its parametrised list are registered, and that list does not include these events. HC-GAMSET-005 (`tests/test_gamification_settings.py:118`) pins one `create_audit_log` row with `entity_type="settings"`, the shape AUDIT-C-MSET reuses. They also would not notice a new committing handler added later without an audit call: the guard still checks classification, not truth (follow-up below).

**Follow-up, not a row:** once all four rows (and AUDIT-NOTIF-ALL) have merged, add `test_hc_aud_ord_030_c_handlers_reach_an_audit_call` to the guard. For each `"C"` row it asserts `_G.reaches(_REACH[k], n)` for some `n` in `{create_audit_log, log_document_event, audit_and_commit, ...}` (`tests/support/callgraph.py:96`). That turns the recurring-failures #9 recheck into a test. It is L0's call. Until AUDIT-C-MSET-EXT merges it would fail on `save_external_api_settings`.

---

#### AUDIT-C-MED — `api/medications.py`, 6 handlers

**Files (edited):** `src/backend/api/medications.py`; `src/backend/tests/test_medications_routes_http.py` (new C tests); `src/backend/tests/test_medications_dose_logging.py`, which calls `log_dose` directly at `:91` and `:131`. Once `master_db` defaults to the `Depends(get_db)` object, those two calls fail, so each passes `master_db=MagicMock(commit=AsyncMock())`; behaviour assertions are unchanged (session handoff 2026-10-18, harness-defects table row 6: "row file lists omit pinning tests"). Also `src/backend/tests/test_audit_order.py` (new `schedule` Case), `src/backend/tests/test_audit_order_guard.py` (`:70` `delete_schedule` `"C"` → `"A2"`; the other five `"C"` rows stay and are now true), and slots.
**Re-run, not edited:** `src/backend/tests/test_adherence_patterns_tz_http.py` (`POST learn-patterns` through `route_client`, whose default `AsyncMock` master absorbs the write), `src/backend/tests/test_medication_correlations.py`, `src/backend/tests/test_gamification_api.py`, `src/backend/tests/test_audit_phi_minimization.py`.

| Id | Route | Assertion | RED on `f8ef7f8`? |
|---|---|---|---|
| HC-AUDCMED-001 ×5 | parametrised: `PATCH /medications/{id}` `{"dosage_amount": 20, "instructions": "with food"}`; `POST .../schedules` `{"schedule_label": "morning", "target_time": "08:00"}`; `PATCH .../schedules/{sid}` `{"target_time": "09:00"}`; `POST .../doses` `{"taken_at": "2026-07-15T09:00:00Z"}`; `POST .../learn-patterns` | 2xx; exactly one spy call with the event and `document_id` of the event table, `profile_id=PROFILE`, details exactly as in the table (`["dosage_amount", "instructions"]`, `["target_time"]`, or `None`); order ends `["vault", "audit"]`; `master.commit` awaited | yes ×5 (no call) |
| HC-AUDCMED-002 ×5 | same five, master commit raises | 500; the vault change is present on re-select (dosage 20 / schedule row / `target_time` 09:00 / dose row / `AdherencePattern` rows). For learn-patterns, the test seeds 8 taken `DoseTaken` rows on 8 consecutive days at 08:00 local, at least `MIN_SAMPLES_FOR_PATTERN = 7` (`modules/adherence_patterns.py:117`), so `time_window` is learned and at least one row exists; one `AUDIT-ORDER` ERROR with the entity id; `"Metformin"` and `"with food"` not in `caplog.text` | yes ×5 (2xx today) |
| HC-AUD-ORD-001a/001b/002/003 `[schedule]` | `DELETE /medications/{id}/schedules/{sid}` via the new Case | the four existing A2 assertions (intent fails → schedule kept, no row; completion fails → schedule gone, `["started"]`; vault fails → kept, `["started"]`; happy → 204, `["started", "completed"]`, `entity_id == sid`) | yes ×4 (204 and no rows today) |

**Expected collected delta:** +14.
**Acceptance:** `pyt tests/test_medications_routes_http.py tests/test_medications_dose_logging.py tests/test_audit_order.py tests/test_audit_order_guard.py tests/test_audit_phi_minimization.py tests/test_adherence_patterns_tz_http.py tests/test_medication_correlations.py tests/test_gamification_api.py -q`: 0 failed. The #9 walk above prints no `api/medications.py` line. `cd src/backend && python -c "from main import app"`. Full suite per RUNBOOK §6. **Rollback:** revert; no data.
**Order:** after AUDIT-NOTIF-ALL (#172) merges, which shares `test_audit_order_guard.py`. Never beside MED-STREAK-GRACE (merged #167; `api/medications.py`, `test_medications_routes_http.py`), AUDIT-C-ASSIST (`test_audit_order.py`, `test_audit_order_guard.py`) or another open PR on either guard file (E-2, B-5, C-GC1, RSI1-DONATE). No other open or ready row shares `api/medications.py`, `test_medications_routes_http.py` or `test_adherence_patterns_tz_http.py`: D-1 (#104), D-2 (#115) and MED-STREAK-GRACE (#167) are merged (checked with `gh pr view` on 2026-10-18), and no open PR (#155, #159, #164, #168, #172) touches those files.

#### AUDIT-C-ASSIST — `api/assistant.py`, 3 handlers

**Files (edited):** `src/backend/api/assistant.py` (adds `audit_intent` to the `core.audit` import, `:28`); `src/backend/tests/test_chat_sessions.py` (new HTTP tests; its existing tests call helpers, not these handlers); `src/backend/tests/test_audit_order.py` (new `chat_session` Case); `src/backend/tests/test_audit_order_guard.py` (`:16` `delete_session` `"C"` → `"A2"`; `:15`, `:17` stay `"C"`, now true); slots.
**Re-run, not edited:** `src/backend/tests/test_assist_utc_http.py` (being edited by W-8, #168; chat only), `src/backend/tests/test_assist_agent_dates_http.py`, `src/backend/tests/test_audit_phi_minimization.py`. No other test calls these three routes or handlers (grep on `f8ef7f8`).

| Id | Route | Assertion | RED? |
|---|---|---|---|
| HC-AUDCAS-001 | `POST /assistant/sessions` `{"title": "Chest pain questions"}` | 201; one spy call `event_type == action == "assistant.session.create"`, `entity_type="chat_session"`, `entity_id == body["session_id"]`, `details is None`; the title is in no spy kwarg; order `["vault", "audit"]` | yes |
| HC-AUDCAS-002 | same, master commit raises | 500; the `ChatSession` row exists; one `AUDIT-ORDER` ERROR with its id; the title not in `caplog.text` | yes (201 today) |
| HC-AUDCAS-003 | `PATCH /assistant/memory-settings` `{"assistant_memory_enabled": false}` | 200; one spy call `event_type="settings.assistant_memory.update"`, `entity_id="assistant_memory"`, `details == {"changed_fields": ["assistant_memory_enabled"]}`; order `["vault", "audit"]` | yes |
| HC-AUDCAS-004 | same, master commit raises | 500; `UserModelSettings.assistant_memory_enabled is False` on re-select; one `AUDIT-ORDER` ERROR | yes (200 today) |
| HC-AUD-ORD-001a/001b/002/003 `[chat_session]` | `DELETE /assistant/sessions/{id}` via the new Case | the four A2 assertions. `present` also checks the seeded `ChatTurn`: kept when the intent fails, gone on success | yes ×4 |

**Expected collected delta:** +8.
**Acceptance:** `pyt tests/test_chat_sessions.py tests/test_audit_order.py tests/test_audit_order_guard.py tests/test_audit_phi_minimization.py tests/test_assist_utc_http.py tests/test_assist_agent_dates_http.py -q`: 0 failed; app import; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** after AUDIT-NOTIF-ALL merges. Never beside AUDIT-C-MED (two shared test files; run MED first, since medications are patient data). Never beside B-3 (ready; edits `api/assistant.py`), SAFE-CHAT-FALLBACK (B) or SAFE-CHAT-HISTORY (B), G-C5, or any open PR on `api/assistant.py` or either guard file.

#### AUDIT-C-MSET — `api/model_settings.py`, 7 handlers (not `save_external_api_settings`)

**Files (edited):** `src/backend/api/model_settings.py`; `src/backend/tests/test_model_settings_api.py`. That file gets the new HTTP tests, and it calls three of these handlers directly: `set_timezone` `:269`, `update_voice_settings` `:286`, `update_ocr_settings` `:305`. Each of those calls passes `master_db=MagicMock(commit=AsyncMock())`, with assertions unchanged (session handoff 2026-10-18, harness-defects table row 6: "row file lists omit pinning tests"). Slots.
**Not edited:** `tests/test_audit_order_guard.py` (the 7 rows stay `"C"` and become true; no handler changes class or starts committing; the named dynamic exclusion `start_model_download::background_tasks.add_task(_download_model_task)` is unchanged). **Re-run:** `src/backend/tests/test_audit_order_guard.py`, `src/backend/tests/test_gamification_settings.py`, `src/backend/tests/test_tier_capabilities.py`, `src/backend/tests/test_hardware_detection.py`, `src/backend/tests/test_voice_settings_api.py`, `src/backend/tests/test_audit_phi_minimization.py`.
**Stubs:** `run_hardware_detection`, `set_model_tier` and `start_model_download` call `get_model_selector()`. The tests use `monkeypatch.setattr(model_settings_api, "get_model_selector", lambda: stub)`, where the stub's `save_hardware_detection`, `set_user_preference`, `is_model_available` (False, so download gets past the early return `:651-657`) and `update_download_progress` are fakes that record calls. `detect_hardware_tier` returns a real `modules.hardware_detection.HardwareProfile` (`:171`), because `run_hardware_detection` builds `HardwareInfoResponse` from its fields. `api.model_settings.can_run_tier` is patched to return True, as HC-CAP-007 does (`tests/test_tier_capabilities.py:91`). Otherwise `set_model_tier`'s `logger.warning` (`:503-505`) writes the tier name to the log and breaks HC-AUDCMS-002's `"mid"` check for a reason that has nothing to do with the audit. `_download_model_task` is patched to an async no-op, so no download or network call runs (local-first).

| Id | Route | Assertion | RED? |
|---|---|---|---|
| HC-AUDCMS-001 ×7 | parametrised over the 7 routes with a valid body (`{"tier": "mid"}`, `{"timezone": "America/New_York"}`, `{"voice_logging_enabled": true}`, `{"ocr_preference_enabled": false}`, `{"agent_enabled": false}`, `{"tier": "mid"}` for download (`TierDownloadRequest.tier` is required, `:128-134`; an empty body would 422 before the handler), empty for detect) | 200; exactly one spy call (`create_audit_log`) with `event_type == action ==` the table value, `entity_type="settings"`, the table `entity_id` and `details`; `profile_id=PROFILE`; order `["vault", "audit"]`; `master.commit` awaited | yes ×7 |
| HC-AUDCMS-002 ×7 | same, master commit raises | 500; the vault change on re-select (the `UserModelSettings` column for the four direct writes; the recorded stub call for the three selector routes); one `AUDIT-ORDER` ERROR with the entity id; `"America/New_York"` and `"mid"` not in `caplog.text` | yes ×7 (200 today) |

**Expected collected delta:** +14.
**Acceptance:** `pyt tests/test_model_settings_api.py tests/test_gamification_settings.py tests/test_tier_capabilities.py tests/test_hardware_detection.py tests/test_voice_settings_api.py tests/test_audit_order_guard.py tests/test_audit_phi_minimization.py -q`: 0 failed. The #9 walk prints only `save_external_api_settings` for this file. App import; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** file-disjoint from AUDIT-NOTIF-ALL, AUDIT-C-MED and AUDIT-C-ASSIST, so it may run beside any of them. Never beside AUDIT-C-MSET-EXT or any open PR on `api/model_settings.py` or `tests/test_model_settings_api.py`.

#### AUDIT-C-MSET-EXT — `save_external_api_settings` (ask-first; AUDIT-EXT-ASKFIRST = A)

**Licensed by owner answer AUDIT-EXT-ASKFIRST = A (2026-10-18, recorded by PR #175).** Before that answer this plan did not license the edit. On **B**, the row becomes a one-line guard reclassification. On any answer, the encryption call `:749-753` and the consent check `:737-741` are not touched.
**Files (edited, under A):** `src/backend/api/model_settings.py` (one `_audit_settings_change` call after `:755`, plus the `master_db` parameter); `src/backend/tests/test_model_settings_api.py` (2 new HTTP tests; `test_put_external_api_persists` `:100` passes `master_db=MagicMock(commit=AsyncMock())`; `test_put_external_api_requires_consent` `:80` raises 400 before the audit and is left alone); slots. **Re-run:** `src/backend/tests/test_external_runner_hardening.py` (`PUT /settings/model/external-api` through `route_client` at `:285-295`), `src/backend/tests/test_external_runner.py`, `src/backend/tests/test_audit_order_guard.py`.

| Id | Assertion | RED? |
|---|---|---|
| HC-AUDCMS-003 | `PUT /settings/model/external-api` `{"use_external_api": true, "provider": "openai", "api_key": "sk-canary-123", "consent_acknowledged": true}` → 200; one spy call `event_type="settings.external_api.update"`, `entity_id="external_api"`, `details == {"changed_fields": ["api_key", "provider", "use_external_api"]}`; `"sk-canary-123"` and `"openai"` in no spy kwarg; order `["vault", "audit"]` | yes |
| HC-AUDCMS-004 | same, master commit raises → 500; the encrypted key is stored (re-select, starts `gAAAAA`); one `AUDIT-ORDER` ERROR; `"sk-canary-123"` not in `caplog.text` | yes |

**Expected collected delta:** +2. **Est:** 0.5 h. **Order:** after AUDIT-C-MSET merges (same two files).

**Owner questions.**
1. **AUDIT-EXT-ASKFIRST — answered A, 2026-10-18 (PR #175).** "`PUT /settings/model/external-api` (`save_external_api_settings`, `api/model_settings.py:730`) encrypts the cloud API key and turns the opt-in external runner on or off (D12), so CLAUDE.md §1 makes it ask-first. It writes no audit row today, although the audit-order guard says it does. May an agent add one audit row after the settings are saved? The row would hold event `settings.external_api.update` and the names of the changed fields (`use_external_api`, `provider`, `api_key`), never the key or the provider. The encryption and consent code would not change. A. Yes, as planned (recommended): every change to the cloud-runner switch becomes attributable. B. No: leave it unaudited and reclassify the guard row as `excluded:` with a reason; the gap stays documented."
2. **AUDIT-C-A2 — answered A (keep A2), 2026-10-18 (PR #175).** "Deleting a medication schedule or a chat session cannot be undone. Under your signed AUDIT-ORDER option D, the plan gives both the two-row started/completed audit, so a failed audit stops the delete. A. Keep A2 (default, recommended). B. Use the single after-change row (C) instead: smaller, but a failed audit leaves a deleted schedule or chat with no row."

**Recurring-failures #9:** none of these rows edits `docs/agentic/recurring-failures.md`. Each row would otherwise share it with every other row and with AUDIT-NOTIF-ALL. When the last of AUDIT-C-MED / -ASSIST / -MSET merges, L0's post-merge batch rewrites the "17 more" sentence: what was fixed, and what is still waiting on AUDIT-EXT-ASKFIRST. The heading of this section keeps the anchor that #9's "queue row AUDIT-C-CLASS" reference resolves to.

### Follow-ups found 2026-10-18 (planned 2026-10-19 on `origin/main` @ `a9978e8`)

Three test-only rows. None edits product code; each adds the pin a review said was missing. `pyt` = `scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest`, run from `src/backend`. A pin test passes on `main` by design, so "fails before the fix" is shown by a **mutant**: a temporary product edit in the worktree that the test must turn RED, with the output pasted in the PR body and the edit reverted (`git diff origin/main -- src/backend/api src/backend/modules` empty at the end). **Exception, MSET-EXT-NOKEY-TEST:** its handler is ask-first, so its mutants are monkeypatches in a scratch test, never edits to the file (L0 ruling below).

#### AUDIT-GUARD-TEST — the audit-order guard checks the class, not that the class is true

**Source:** the AUDIT-C-CLASS plan above ("Follow-up, not a row": add `test_hc_aud_ord_030_c_handlers_reach_an_audit_call`, written for PR #174, `17040dd`); recurring-failures #9 (audit paragraph).

**Fact (`a9978e8`):** `tests/test_audit_order_guard.py` checks that every committing handler is classified (`test_hc_aud_ord_030_every_committing_handler_is_classified`, `:188-196`) and that every `"A2"` row reaches `audit_intent` (`:198-204`). Nothing checks that a `"C"` row reaches any audit call; that gap let 19 `"C"` handlers write no row (AUDIT-NOTIF-ALL, AUDIT-C-*). **Measured today** with the guard's own graph (`_G.reaches(_REACH[k], name)`): all 49 `"C"` / `"A2"` rows (35 C, 14 A2) reach one of `create_audit_log`, `audit_and_commit` or `audit_intent`; none misses. Reaching through a helper counts, because `_REACH` already holds every same-tree function a handler calls (for example `_audit_settings_change`, `log_document_event` → `create_audit_log`). The 3-name sink set alone covers all 49 rows, so `log_*_event` and `_audit*` names need not be listed.

**Design (test file only):**
1. Add `_AUDIT_SINKS = frozenset({"create_audit_log", "audit_and_commit", "audit_intent"})` and a helper `_rows_without_audit(classification, reach, g) -> list[str]`: the sorted keys whose class is `"C"` or `"A2"` and whose `reach` list reaches none of the sinks.
2. `test_hc_aud_ord_030_c_and_a2_handlers_reach_an_audit_call`: `_rows_without_audit(CLASSIFICATION, _REACH, _G) == []`.
3. `test_hc_aud_ord_030_break_it_c_handler_without_audit(tmp_path)`: with the existing `_overlay`, a handler `h` that only `await profile_db.commit()`s → `_rows_without_audit({"api/zz.py::h": "C"}, reach, g) == ["api/zz.py::h"]`; a second overlay handler that also calls `await create_audit_log(...)` → `[]`.

| Id | Assertion | Fails before? |
|---|---|---|
| `test_hc_aud_ord_030_c_and_a2_handlers_reach_an_audit_call` | no `"C"`/`"A2"` row without an audit sink | passes on `main` (all 49 reach). **Mutant:** delete the `log_document_event(...)` call in `api/notifications.py::update_notification_settings` (added by AUDIT-NOTIF-ALL; it reaches `create_audit_log`) → this test fails naming that key, while `..._every_committing_handler_is_classified` stays green. That pair is the proof |
| `test_hc_aud_ord_030_break_it_c_handler_without_audit` | the synthetic C handler with no audit is flagged; with an audit it is not | RED (helper does not exist); behaviourally pinned by the mutant above |

**Also edit:** `docs/agentic/recurring-failures.md` #9, the audit paragraph's recheck: add one sentence after the grep recheck saying the class is now a test (`test_hc_aud_ord_030_c_and_a2_handlers_reach_an_audit_call`), so a new unaudited `"C"` row fails CI. Leave the rest of #9 alone.

**Files:** `src/backend/tests/test_audit_order_guard.py`, `docs/agentic/recurring-failures.md` (#9 audit paragraph only), slots. **Re-run, not edited:** `tests/test_audit_order.py`, `tests/test_audit_phi_minimization.py`.
**Expected collected delta:** +2. **Est:** 1 h.
**Acceptance:** `pyt tests/test_audit_order_guard.py tests/test_audit_order.py -q -rfE`: 0 failed; the mutant run output in the PR body; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside any open PR on `tests/test_audit_order_guard.py` (E-2, B-5, C-GC1, RSI1-DONATE are blocked today) or on `docs/agentic/recurring-failures.md`. A row that adds a `"C"` row later must now also add the audit call, which is the point. **Recurring-failures #12 recheck:** after this merges, L0 runs the new gate (`tests/test_audit_order_guard.py`) on `origin/main` and on every open PR built before it, and rebases or fixes those PRs before merging the rest of the group. Any open PR that adds a `"C"`/`"A2"` row without an audit call fails it.

#### MSET-EXT-NOKEY-TEST — no test saves external-API settings without a key

**Source:** PR #181 (AUDIT-C-MSET-EXT) "What the new tests would fail to notice", HC-AUDCMS-003: "The no-key branch is untested. A mutant that always lists `"api_key"` passes ... The switch-off case (`use_external_api: false`) is not tested." Owner MSET-EXT-DIFF: "The two notes become follow-ups."

**Fact (`a9978e8`):** `save_external_api_settings` (`src/backend/api/model_settings.py:776-820`) encrypts and stores a key only `if request.api_key:` (`:795-800`; `api_key` defaults to `""`, `:205`), and audits `changed_fields` `sorted(["provider", "use_external_api"] + (["api_key"] if request.api_key else []))` (`:809`). HC-AUDCMS-003/004 (`tests/test_model_settings_api.py:537-590`) send only `_EXT_BODY`, which always carries `api_key`.

**Design (test file only; the handler is ask-first and is not edited):**
1. Give `_ext_put(vault, master)` (`:523-534`) an optional `body` argument defaulting to `_EXT_BODY`; HC-AUDCMS-003/004 keep calling it unchanged.
2. **HC-AUDCMS-005:** PUT `_EXT_BODY` with `_ext_put` (stores a key), then a second `_ext_put` with `{"use_external_api": false, "provider": "openai", "consent_acknowledged": false}` (no `api_key`) → both 200. The second spy call has `details == {"changed_fields": ["provider", "use_external_api"]}`; the second response has `api_key_configured is True`; the re-selected row keeps the first encrypted key byte for byte and has `use_external_api is False`. That covers the no-key branch and the switch-off case.

| Id | Assertion | Fails before? |
|---|---|---|
| HC-AUDCMS-005 | as above | passes on `main`. **Mutants (monkeypatch only, in a scratch test file that is not committed):** (1) wrap `api.model_settings._audit_settings_change` so it always adds `"api_key"` to `details["changed_fields"]` before calling the real one → HC-AUDCMS-005's body run under that patch fails on `details`; (2) wrap it so it also clears `external_api_key_encrypted` on the profile's `UserModelSettings` row and commits → fails on the kept key. Paste both RED outputs in the PR body |

**Files:** `src/backend/tests/test_model_settings_api.py`, slots. **Ask-first:** `api/model_settings.py::save_external_api_settings` is **never edited, not even temporarily** (L0 ruling 2026-10-19, PR #189 review round 1, under CLAUDE.md §1). `git diff origin/main -- src/backend/api` is empty at every step. **Re-run, not edited:** `tests/test_external_runner_hardening.py`, `tests/test_external_runner.py`.
**Expected collected delta:** +1. **Est:** 0.5 h.
**Acceptance:** `pyt tests/test_model_settings_api.py tests/test_external_runner_hardening.py tests/test_external_runner.py -q -rfE`: 0 failed; both mutant outputs in the PR body; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside an open PR on `tests/test_model_settings_api.py` (none on `a9978e8`).

#### EXPORT-TZ-PINS — no test pins `today=local_today` on the pinboard and visit-prep question callers

**Source:** PR #155 (EXPORT-TODAY-TZ) review, open minors 1-2: "No test would notice if the pinboard route (`api/pinboards.py:501`, `:512`) or the visit-prep `generate_questions` call (`api/export.py:799`) dropped `today=local_today`. The reviewers' break-it mutations left the suite green."

**Fact (`a9978e8`):** `export_pinboard_packet` computes `local_today` (`src/backend/api/pinboards.py:406-408`) and passes it to `generate_questions` (`:499-502`) and `compose_visit_prep_packet` (`:503-513`). The visit-prep route passes it to `generate_questions` (`src/backend/api/export.py:794-800`) and to the packet (`:810-820`). HC-EXPTZ-001/002 (`tests/test_export_questions.py:429-445`) cover only `POST /export/questions`; HC-EXPTZ-006 (`tests/test_visit_prep_packet.py:720-741`) covers the visit-prep packet date, not its questions. `tests/test_pinboards.py` has no time-zone test (HC-PIN-005 stubs the zone to `"UTC"`, `:248-250`). Without `today=`, `generate_questions` falls back to the UTC day (`modules/export.py:460`, `today or now.date()`). The open-task window is `due <= today + timedelta(days=NEAR_DUE_WINDOW_DAYS)` (14 days, `modules/export.py:510`).

**Design (tests only; same frozen moment as HC-EXPTZ-001: `2026-01-16 01:00Z` = Jan 15 17:00 `America/Los_Angeles`, frozen on `api.export.utcnow`, `api.pinboards.utcnow` and `modules.export.utcnow`):** two open care tasks, due **Jan 29** (local today + 14: in the window either way) and **Jan 30** (local today + 15: outside the local window, but UTC today + 14, so inside the UTC window). With `today=local_today`, only the Jan 29 task yields a `follow_up` question; without it, both do. The Jan 29 question also proves the questions section is not empty, so the absence check cannot pass vacuously.

| Id | File | Assertion | Fails before? |
|---|---|---|---|
| HC-EXPTZ-008 | `tests/test_pinboards.py` (`real_profile_db`, `route_client` on the pinboards router; new import of `tests.support.routes.route_client` and `get_profile_db_session`) | a `UserModelSettings` row with `America/Los_Angeles`; a pinboard with the two tasks pinned as `item_type="question"`; `POST /pinboards/{id}/export` `{"confirm": true}` → 200; the stored packet (`api.export._packet_store[packet_id]`) has a `follow_up` question whose text names the Jan 29 task's title and none naming the Jan 30 task's (the stored packet keeps only `{question, category}`, `modules/export.py:730-733`, so the task title is the handle; PR #198); the response `markdown` contains `Generated: 2026-01-15` | passes on `main`. **Mutants:** drop `today=local_today` at `api/pinboards.py:501` → Jan 30 question appears; at `:512` → `Generated: 2026-01-16` |
| HC-EXPTZ-009 | `tests/test_visit_prep_packet.py` (`real_profile_db`, `route_client`, as HC-EXPTZ-006) | same zone and tasks (unpinned, status `open`); `POST /export/visit-prep` `{"confirm": true, "include_tasks": true, "include_questions": true}` → 200; the stored packet's questions include the Jan 29 `follow_up` and not the Jan 30 one | passes on `main`. **Mutant:** drop `today=local_today` at `api/export.py:799` → Jan 30 question appears |

**Files:** `src/backend/tests/test_pinboards.py`, `src/backend/tests/test_visit_prep_packet.py`, slots. **Re-run, not edited:** `tests/test_export_questions.py`, `tests/test_export_redaction.py`, `tests/test_export_api.py`, `tests/test_audit_order.py`.
**Expected collected delta:** +2. **Est:** 1 h.
**Acceptance:** `pyt tests/test_pinboards.py tests/test_visit_prep_packet.py tests/test_export_questions.py tests/test_export_api.py -q -rfE`: 0 failed; the three mutant outputs in the PR body; `git diff origin/main -- src/backend/api src/backend/modules` empty; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside C-GC1 (`tests/test_visit_prep_packet.py`) or E-1c (adds a visit-prep test to `tests/test_visit_prep_packet.py`).

---

### Follow-ups found 2026-10-19 (planned 2026-10-19 on `origin/main` @ `d42dba9`)

Two rows: AUDIT-GUARD-MINORS (from the #193 review MINORs) and MSET-EXT-NOKEY-PIN (from the #194 review MINORs). MSET-EXT-NOKEY-PIN was won't-plan in the first pass; PR #202 review round 1 showed the evidence was wrong, and it is re-measured below.

#### AUDIT-GUARD-MINORS — the guard's break-it uses the wrong graph and no `"A2"` row; `excluded:` labels are never checked

**Source:** PR #193 (AUDIT-GUARD-TEST) review MINORs: the new recurring-failures sentence "sits before 'that recheck' and is unwrapped"; "the break-it passes real-tree `_G` with the overlay's `reach`"; "it covers only a `"C"` row, so narrowing `{"C","A2"}` to `{"C"}` stays green"; "`excluded:` rows are unchecked (`api/backup.py::get_schedule` reaches no sink)".

**Facts (`d42dba9`):**
1. `docs/agentic/recurring-failures.md:364`: the sentence "The class is now a test (…)" is one long unwrapped line between the grep recheck (`:360-363`) and "Applied to every … that recheck finds 17 more" (`:365`), so "that recheck" now reads as if it meant the test.
2. `test_hc_aud_ord_030_break_it_c_handler_without_audit` (`src/backend/tests/test_audit_order_guard.py:293-303`) takes `reach` from the overlay but passes the real-tree `_G` to `_rows_without_audit` (`:302-303`). It still works, because the overlay handler names `create_audit_log` directly, but a sink reached only through an overlay helper would not be found.
3. The same test classifies only `"C"` rows (`:301`).
4. Each `excluded:` row in `CLASSIFICATION` carries a reason string; nothing checks it.

**Measured** (scratch tests importing the guard's own `CLASSIFICATION`, `_G`, `_REACH` and `_overlay`; not committed):
- A copy of `_rows_without_audit` narrowed to `{"C"}` passes the break-it's two assertions unchanged.
- 47 rows say `excluded: read route, audit_and_commit only`. Five of them never reach `audit_and_commit`: `api/backup.py::get_schedule` reaches **no** audit sink at all, and `api/model_settings.py::get_model_settings`, `::list_tiers`, `::get_environment_diagnostics`, `::recheck_environment_diagnostics` reach `create_audit_log` instead (a wrong label, not a missing audit). The only other `excluded:` row that reaches no sink is `api/profiles.py::reset_synthetic_test_profile`, whose label ("test-only reset (3.1)") claims no audit; its audit belongs to E-2 (RESET-AUDIT-OWNER).
- `get_schedule` (`src/backend/api/backup.py:531-546`) reads, and may create, this profile's backup-schedule row in the master DB, commits, and writes no audit row. Every other backup read route (`list_backups`, `verify_backup`, `download_backup`) is labelled and wired `audit_and_commit`.

**Owner gate AUDIT-SCHED-READ** (execution; open; exact wording to ask): "AUDIT-SCHED-READ: `GET /backup/schedule` returns this profile's backup schedule (and creates a default row on first read) but writes no audit row, while the audit-order guard labels it 'read route, audit_and_commit only'. The other backup read routes do audit. Should it? (a) Yes: add the same `audit_and_commit` read audit the other backup routes use (Recommended: matches its siblings and the guard's label; one call in `api/backup.py`). (b) No: the schedule is backup configuration, not profile data; relabel the guard row to say it writes no audit row."

**Design:**
1. `recurring-failures.md` #9: move the sentence to the end of the paragraph (after "walk each handler body instead.") and wrap it to the file's width. Change no other words.
2. Break-it (`:293-303`): build the overlay graph (`g = Graph(tmp_path, ("api", "core", "modules"))`, as the other break-its do) and pass `g`, not `_G`. Add a third overlay handler `h2` (commit only) classified `"A2"` and assert it is reported too.
3. New `test_hc_aud_ord_031_excluded_rows_reach_the_sink_they_name`: for every `excluded:` row whose reason names one of `_AUDIT_SINKS`, the handler reaches that sink in `_G`. Relabel the four `api/model_settings.py` rows to `excluded: read route, create_audit_log only`.
4. `get_schedule`: under (a), add `await audit_and_commit(master_db, create_audit_log, …)` in the same form as `list_backups` (`api/backup.py:224-232`; for example `event_type="backup.schedule.view"`, `entity_type="backup_schedule"`), with ids only in `details`; under (b), relabel the row `excluded: read of the master-only backup schedule; no audit row` (and HC-AUD-ORD-031 then skips it because the label names no sink).

**Test-first:**

| Id | File | Assertion | RED today? |
|---|---|---|---|
| `test_hc_aud_ord_030_break_it_c_handler_without_audit` (edited) | `tests/test_audit_order_guard.py` | overlay graph; `"A2"` bare handler also reported | no (pin; the `{"C"}`-only mutant of `_rows_without_audit` now fails it, measured passing today) |
| HC-AUD-ORD-031 | same | every `excluded:` row that names a sink reaches it | yes (5 rows, measured) |
| HC-BKUP-064 (under (a)) | `tests/test_backup_routes.py` | through `route_client`: `GET /backup/schedule` → 200 and exactly one audit row for the caller's profile, with no schedule values in `details` | yes (no audit row) |

**Files:** `src/backend/tests/test_audit_order_guard.py`, `docs/agentic/recurring-failures.md` (#9 audit paragraph only), under (a) also `src/backend/api/backup.py` (`get_schedule` only) and `src/backend/tests/test_backup_routes.py`, slots. **Re-run, not edited:** `tests/test_audit_order.py`, `tests/test_audit_phi_minimization.py`, `tests/test_backup_api.py`.
**Expected collected delta:** (a) +2; (b) +1. **Est:** 1 h after AUDIT-SCHED-READ.
**Acceptance:** `pyt tests/test_audit_order_guard.py tests/test_audit_order.py tests/test_backup_routes.py tests/test_backup_api.py -q -rfE`: 0 failed; the `{"C"}`-only mutant output in the PR body; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** blocked on AUDIT-SCHED-READ. Never beside E-2, B-5, C-GC1 or RSI1-DONATE (`tests/test_audit_order_guard.py`), or any open PR on `docs/agentic/recurring-failures.md`. **Recurring-failures #12 recheck:** HC-AUD-ORD-031 is a new guard. After it merges, L0 runs `tests/test_audit_order_guard.py` on `origin/main` and on every open PR built before it: a PR that adds an `excluded:` row naming a sink it does not reach now fails.

#### MSET-EXT-NOKEY-PIN — HC-AUDCMS-005's re-select returns the cached row, so a key wipe in the database passes

**Source:** PR #194 (MSET-EXT-NOKEY-TEST) review MINORs (queue bullet MSET-EXT-NOKEY-MINORS). PR #202 review round 1 MAJOR: the first planning pass called minor 1 "did not reproduce". That was wrong. Its scratch mutant dropped the test's reference to the row, so the identity map no longer held the object.

**Facts (`5750a97`):**
1. `aud_vault` is an `AsyncSession(engine, expire_on_commit=False)` (`src/backend/tests/test_model_settings_api.py:398`).
2. HC-AUDCMS-005 keeps `row` from its first select (`:607-609`). After the second PUT it re-selects into the same variable (`:623-625`) and asserts `row.external_api_key_encrypted == stored_key` (`:626`). While `row` is alive, the re-select returns the identity-mapped object with its cached attributes. Nothing refreshes it.
3. `"sk-canary-123" not in repr(calls[1])` (`:628`) cannot fail, because the second PUT body carries no key.

**Measured on `5750a97`** (scratch tests that hold `row` exactly as HC-AUDCMS-005 does; monkeypatch only, the handler is not edited):
- **Mutant A:** a raw-SQL `UPDATE user_model_settings SET external_api_key_encrypted = ''` inside request 2, just before the vault commit (`aud_vault.commit` wrapped).
- **Mutant B:** the same `UPDATE` at the start of request 2 (`api.model_settings._get_user_settings` wrapped).
- Under both mutants, **every** HC-AUDCMS-005 assertion passes: status 200, `api_key_configured` True, the `changed_fields` details, the key equal to `stored_key`, and `use_external_api` False.
- After either mutant, `select(...).execution_options(populate_existing=True)` and a raw `SELECT external_api_key_encrypted` both read `''`.

**Design (test file only; `save_external_api_settings` is ask-first and is not edited, even temporarily: L0 ruling 2026-10-19 on MSET-EXT-NOKEY-TEST):**
1. Change HC-AUDCMS-005's post-PUT-2 re-select to `execution_options(populate_existing=True)`, so the key check reads the database.
2. Replace the vacuous `:628` line with `assert "sk-canary-123" not in resp2.text`. The canary from PUT 1 must not come back in the response. Do not delete a check without replacing it.

| Id | Assertion | RED today? |
|---|---|---|
| HC-AUDCMS-005 (edited) | as today, but the key is read with `populate_existing=True` | no (pin). **Mutants A and B, as monkeypatches in a scratch test that is not committed:** today's version passes both (measured); the edited version must fail both. Paste the 2 × 2 outputs in the PR body |

**Files:** `src/backend/tests/test_model_settings_api.py` (HC-AUDCMS-005 only), slots. **Re-run, not edited:** `tests/test_external_runner_hardening.py`, `tests/test_external_runner.py`.
**Expected collected delta:** 0. **Est:** 0.5 h.
**Acceptance:** `pyt tests/test_model_settings_api.py tests/test_external_runner_hardening.py tests/test_external_runner.py -q -rfE`: 0 failed; both mutant outputs in the PR body; `git diff origin/main -- src/backend/api` empty; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside another PR on `tests/test_model_settings_api.py` (none open on `5750a97`).

## 4. Provides

| What | Exact surface | From |
|---|---|---|
| Zone validation | `core.time.safe_zone_name(name: str \| None) -> str` | D-1 |
| Storage → local | `core.time.to_local(value: datetime, tz_name: str) -> datetime` (aware) | D-1 |
| Local day → UTC query bounds | `core.time.local_day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]`, naive UTC, half-open | D-1 |
| Profile zone lookup | `async core.time.profile_timezone_name(profile_db: AsyncSession, profile_id: str) -> str` | D-1 |
| One streak engine | `GET /medications/{id}/stats` streaks computed by `modules.streak_engine` in the profile zone | D-1 |
| Local reminder clock | `NotificationScheduler` compares `target_time` and adaptive windows with profile-local time; `MedicationSchedule.adaptive_window_*` are local wall-clock | D-2 |
| Profile migration | `NNN_adaptive_windows_local` per C-PMIG (slug fixed, number = head + 1 at final merge of main; data-only, no FK, no table) | D-2 |
| Streak grace | `GET /gamification/streaks.current_streak_days` counts through yesterday when today has no dose | D-3 |
| Canonical correlation ID | `monitoring.correlation.get_correlation_id()` always returns `str(uuid.UUID(...))` form | D-4 |
| Measured count chain | count slot after each of #95, #97, #99, #82, #84 | D-0 |

## 5. Consumes

1. #97 merged: `PatternLearner.calculate_streak(..., tz_name: str = "UTC")`, `learn_time_window(..., tz_name)`, `streak_engine._dose_dates` import in `adherence_patterns.py`.
2. #99 merged: `api/medications.py::_schedule_for_medication` (shifts medications.py lines by +19 from `:70`).
3. #84 merged: `api/gamification.py` `compute_engagement` lines (D-3 edits the same function).
4. Lane C C-PMIG (§3.0): numbering by merge order, head-literal carrier `tests.support.migrations.PROFILE_HEAD` (after C-P6), pre-merge single-head check. D-2 reserves no number.
5. Code-slot budget: at most 2 code L1s at once; full suites under `flock /tmp/claude-1000/hc-pytest.lock`.

## 6. Owner gates

| Gate | Item | State |
|---|---|---|
| Ask-first files | none, except AUDIT-C-MSET-EXT: `save_external_api_settings` holds the API-key encryption call (licensed by AUDIT-EXT-ASKFIRST = A); no item touches `interpret_safety`, `redaction`, `faithfulness`, `verifier_agent` or `core/auth.py` | — |
| AUDIT-EXT-ASKFIRST | AUDIT-C-MSET-EXT | **answered 2026-10-18: A** (yes, as planned; recorded by PR #175) |
| AUDIT-C-A2 | AUDIT-C-MED, AUDIT-C-ASSIST (`delete_schedule`, `delete_session` as A2) | **answered 2026-10-18: A** (keep A2; recorded by PR #175) |
| PR merges | D-0: #95, #97, #99, #82, #84 in that order | owner merges each |
| CORRELATION-NORMALISE go | D-4 | **given** |
| Re-learn method (Q1) | D-2 | **answered 2026-10-16: "Re-learn automatically"** — see D-2 rev 2 (no `core/auth.py` edit) |
| Grace scope (Q2) = **MSG-SCOPE** | D-3 applies only to `GET /gamification/streaks`; MED-STREAK-GRACE asks whether to widen it | not asked; options in §3 MED-STREAK-GRACE (planned 2026-10-17) |
| **AUDIT-SCHED-READ** (new) | AUDIT-GUARD-MINORS | **open** (planned 2026-10-19): (a) audit `GET /backup/schedule` like the other backup reads (recommended) / (b) relabel the guard row as unaudited; exact wording in §3 AUDIT-GUARD-MINORS |

## 7. Open questions

1. **Q1 (D-2):** "One-time re-learn": the default is a migration that clears stored windows, so reminders use `target_time ± tolerance` until the user presses "Learn patterns". The other option is to re-learn automatically for every schedule in the migration or on first unlock. That needs the learner inside a migration, or a per-profile startup job while the vault is unlocked. Recommendation: clear. **Answered 2026-10-16: re-learn automatically on first unlock → D-2 rev 2.**
2. **Q2 (D-1/D-3):** should "count through yesterday" also apply to `/medications/{id}/stats` and to the streak in reminder messages? A reminder fires only when today's dose is not yet logged, so under today's rule it always reports the streak as 0. Default: gamification route only (the owner's literal scope). Widening it later is the same one-line `or` at 2 more call sites. **Now planned as MED-STREAK-GRACE (gate MSG-SCOPE), 2026-10-17.**
3. **Q3 (D-2, out of scope):** quiet hours are stored (`api/notifications.py:73-74,247-248`) but `notification_scheduler.py` never reads them. Register as a separate item?
4. **Q4 (D-2 edge):** a `target_time` that does not exist on a spring-forward day (02:00–02:59 local) gets no reminder that day. This matches the clamp behaviour of `_offset_time` (`:605-610`). Accept as is?
5. **Q5 (D-2 rev 2, not asked yet):** re-learn windows automatically when the user later changes time zone? `adaptive_window_tz` makes it a one-condition change (`IS NULL OR != tz`). Default: no (owner asked for a one-time re-learn).

---

## 8. Peer review (2026-10-15)

Checked against lanes A, B, C, E, F surfaces and the repo at `3b2236c`.

**Changes made to this doc:**

1. D-2 migration adopts lane C's C-PMIG contract: `NNN_adaptive_windows_local`, numbered at final merge of main; no hard-coded `013` / `012_pinboards` (was a collision with C-P6 `013_fk_cascade_alignment` and C-GAM2B).
2. D-2 now updates the profile head literal in the same PR: 4 literals before C-P6, `tests/support/migrations.py::PROFILE_HEAD` after. Added those files to D-2's touch list.
3. `test_hc_sched_tz_005` finds the file by slug and runs an upgrade → downgrade → upgrade round trip (C-PMIG §3.0 #9) instead of a text check on a fixed parent.
4. D-2 acceptance uses the C-PMIG §3.0 #6 single-head check (HC-MIGHEAD-001 after E-3).
5. §2: helpers are appended to `core/time.py` so cited line anchors stay put; the D-1 PR body names the WEAR-03 refresh trigger.

**Raised to other lanes (not edited here):**

| With | Subject | Proposal |
|---|---|---|
| C | C-PMIG §3.0 #3 table omits D-2 | Add row `adaptive_windows_local` / D-2 / "data-only, any position"; C-GAM2B note "013 if P6 lands later" also becomes "head + 1" |
| F | F-12 text "D-2 proposes `013_adaptive_windows_local`" | Read as `NNN_adaptive_windows_local` per C-PMIG; Q-F5 owner answer covers D-2 too |
| E | E-1 / E-3 wait on the whole D-0 chain | Ground rule 8 only needs a recount at each PR's final merge of main; E-1/E-3 need not wait for 5 owner merges |
| F | WEAR-03 refresh trigger "any edit to `core/time.py`" | D-1 append-only keeps cited lines; refresh WEAR-03 citations once after D-1 merges (they already cite pre-UTC-SWEEP lines `:9,:14,:24`; main is `:12,:17,:27`) |
