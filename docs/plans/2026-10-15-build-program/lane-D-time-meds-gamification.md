# Lane D — Time Zones, Medications, Gamification — Build Design

**Last Updated:** 2026-10-17 (MED-STREAK-GRACE, AUDIT-MISSING-MED, EXPORT-TODAY-TZ planned); 2026-10-16 (D-2 rev 2, owner Q1)
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
| D-4 | CORRELATION-NORMALISE: canonical form of an inbound correlation ID | `implementation-program.md:500`; `audit/2026-09-25/waves/wave-3-L1-A.md:176` | no | — | blocked-on-owner |
| MED-STREAK-GRACE | per-medication and reminder streaks count through yesterday (Q2) | queue status 2026-10-16 second batch | [§3](#med-streak-grace--the-per-medication-streak-still-resets-each-morning-owner-ruling--q2) | D-3 (merged #109) | blocked-on-owner (MSG-SCOPE) |
| AUDIT-MISSING-MED | audit rows on `GET /medications/{id}/stats` and `POST /notifications/test/{id}` | queue status 2026-10-16 second batch; CLAUDE.md audit invariant | [§3](#audit-missing-med--two-profile-data-routes-write-no-audit-row) | D-1 (merged #104); rebase after #130 | ready |
| EXPORT-TODAY-TZ | export questions window and generated-on dates use the profile-local day | queue status 2026-10-16 second batch; recurring-failures #9 | [§3](#export-today-tz--export-dates-use-the-utc-calendar-day) | D-1 helpers (merged) | ready |

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

**Order:** never beside C-GC1 (`api/export.py`, `api/pinboards.py`). E-1 is merged (#106).

---

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
| Ask-first files | none: no item touches `interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, `core/auth.py` or encryption code | — |
| PR merges | D-0: #95, #97, #99, #82, #84 in that order | owner merges each |
| CORRELATION-NORMALISE go | D-4 | **not given**; owner item, "none is approved" |
| Re-learn method (Q1) | D-2 | **answered 2026-10-16: "Re-learn automatically"** — see D-2 rev 2 (no `core/auth.py` edit) |
| Grace scope (Q2) = **MSG-SCOPE** | D-3 applies only to `GET /gamification/streaks`; MED-STREAK-GRACE asks whether to widen it | not asked; options in §3 MED-STREAK-GRACE (planned 2026-10-17) |

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
