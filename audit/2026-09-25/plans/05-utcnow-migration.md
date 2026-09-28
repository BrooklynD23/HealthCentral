# datetime.utcnow → core.time.utcnow Migration Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-03/F-06):** the inventory units are reconciled under "Audit anchor", and the baseline is now measured at plan start instead of hard-coded. Nothing about the plan's semantics changed: naive UTC is correct. **Staging and ask-first (contracts review, 2026-09-27):**
> - The directory adds at Task 1 (`git add src/backend/models/`), Task 8 (`src/backend/modules/agent/`) and Task 11 (`src/backend/tests/`) are allowed only after `git status --short <dir>` shows this task's changes and nothing else (contract C-GATE-3).
> - Task 4 edits auth flows in `api/profiles.py` (`create_profile`, `login`, `unlock_profile`, `change_password`). CLAUDE.md §1 requires an explicit owner yes for those hunks, even though the swap is mechanical (program P5).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every `datetime.utcnow()` call site and `default=datetime.utcnow` column default in `src/backend` with `core.time.utcnow`, and add a CI lint gate so the deprecated helper cannot re-enter the codebase.

**Architecture:** `core.time.utcnow()` returns `datetime.now(UTC).replace(tzinfo=None)` — a **naive UTC** datetime, semantically identical to the deprecated `datetime.utcnow()`. Every change is therefore a drop-in symbol swap plus one import line per file. No DB migration, no serialization change, no comparison-behavior change. A stdlib-only lint script (`scripts/time_source_lint.py`) is wired into the existing `docs-lint` CI job, matching the repo's one-script-one-check convention (`docs_lint.py`, `feature_list_lint.py`, `security_gate.py`).

**Tech Stack:** Python 3.11+, SQLAlchemy `DateTime` columns (all naive — zero `DateTime(timezone=True)` anywhere in `src/backend`), SQLite/SQLCipher, pytest, GitHub Actions (`ci.yml`).

**Audit anchor:** `audit/2026-09-25/Devin-Audit-report.md` §11 P1 item 4 ("`datetime.utcnow()` systemic breach — ~50 sites/13 files vs the `core.time.utcnow` invariant") and §16 workstream 4. The real count is larger than the audit estimated: **101 call sites / 30 product files**, plus 16 sites in 6 test files (enumerated below — verified by grep on 2026-09-25).

> **2026-09-27 reconciliation ([review F-03](../review/2026-09-27-followup.md)):** "101" counts **lines**, not references. Re-measured at main@`40f590e`:
>
> | Method | Product | Tests |
> |---|---|---|
> | `grep -rn "datetime.utcnow" src/backend --include=*.py` (lines) | **101 lines / 30 files** | 18 lines, 2 of them string literals in `test_profile_recovery.py` |
> | AST scan of `datetime.utcnow` attribute nodes | **109 references** (some lines hold two, e.g. `default=` + `onupdate=`) | 16 references in 6 files |
>
> Every file the grep finds is named in this plan's enumeration, checked by basename on 2026-09-27. The zero-hit gates below grep `datetime.utcnow` *without* `()`, so they also catch `default=datetime.utcnow`. The review's "short by eight" is a line-versus-reference difference; no site is missing. Read "call sites" below as "lines".

## Global Constraints

- **Hard invariant (CLAUDE.md):** use `core.time.utcnow` as the single timestamp helper. `datetime.utcnow` is also deprecated in Python 3.12+ — this migration is deprecation cleanup as well as invariant enforcement.
- **Pinned semantic: naive UTC.** `core.time.utcnow()` returns naive UTC, identical to `datetime.utcnow()`. Every replacement must preserve that exactly — do **not** return aware datetimes, do **not** add `tzinfo` anywhere.
- **Surgical edits only.** In each file: add one import line, swap `datetime.utcnow()` → `utcnow()` / `default=datetime.utcnow` → `default=utcnow`. No other changes.
- **Serialization formats must not change.** `.isoformat()`, `.isoformat() + "Z"`, and `strftime` outputs are byte-identical because the values are identical. If any site would produce different output, stop and flag it.
- **Do not touch ask-first files** (`modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`) — none contain violations anyway (verified: none appear in the enumeration below).
- **Baseline:** `python -m pytest tests/ -p no:cacheprovider -q` collects **1245** tests at main@`40f590e` (re-measured 2026-09-27); all pass in CI. *Corrected 2026-09-27:* this plan runs after plans 01–04, so its start count is whatever that tree collects (the post-merge tree collected 1,291 on 2026-09-27). Measure the count before Task 1 and use that number. On WSL, clear `__pycache__` first: `find src/backend -name __pycache__ -type d -exec rm -rf {} +`. The env-only failure `test_api_rag_index_002b` (needs a real embedding model) is not yours — do not touch it.
- **Import placement:** `from core.time import utcnow` goes in the first-party import group. Ruff isort config (`src/backend/pyproject.toml`) declares `known-first-party = ["api", "core", "models", "modules", "scripts"]`. Prior art in already-migrated files: `models/pinboard.py:10`, `models/care_plan_task.py:20`, `models/backup_schedule.py:28`, `api/assistant.py:29`, `api/profiles.py:23`.
- **Keep `datetime` imports.** Every violating file also uses `datetime` for other things (`timedelta`, `datetime.combine`, `Mapped[datetime]`, `datetime(...)` literals). Leave `from datetime import ...` in place unless a file ends with zero remaining `datetime` references — only then trim it to keep ruff F401 clean.

---

### Task 0: Pin the semantics — naive-UTC, and write the pin test

**Evidence for the decision (already verified — do not re-litigate):**

1. `src/backend/core/time.py:9-11` — `utcnow()` returns `datetime.now(UTC).replace(tzinfo=None)`: **naive UTC**.
2. `datetime.utcnow()` returns **naive UTC**. Same type, same value range, same `isoformat()` output.
3. Zero `DateTime(timezone=True)` columns in `src/backend` — every timestamp column is naive `DateTime`. Existing stored values are naive; SQLite stores them as-is.
4. Therefore: **drop-in replacement, no shim, no `.replace(tzinfo=...)` per-site handling, no DB migration.** Comparisons between new `utcnow()` values and old stored values are naive↔naive, exactly as before.

**Migration risk statement (explicit):** None introduced by this change. The audit's "latent naive/aware comparison bugs" are **pre-existing**, not created here: `api/gamification.py:148` and `modules/badge_evaluator.py:84` already use *aware* `datetime.now(dt_timezone.utc)`, and `modules/source_authority.py:216` uses *local-time* `datetime.now().year`. Those are **out of scope** for this plan (they are not `datetime.utcnow` sites) but are recorded here so the next workstream (audit §16 item 8, systemic UTC audit) has the pointer. If any Task-N edit reveals a site where a naive result is compared against an aware one, stop and record it — do not "fix" by adding `tzinfo`.

**Files:**
- Create: `src/backend/tests/test_time_source.py`

- [ ] **Step 1: Write the pin test**

```python
"""HC-TIME-001/002/003 — pin the naive-UTC semantics the codebase relies on.

CLAUDE.md names core.time.utcnow the single timestamp helper. These tests pin
WHY the datetime.utcnow() migration is safe: stored timestamps are naive, and
utcnow() must stay naive so comparisons never raise TypeError.
"""
from datetime import datetime, time, timedelta

from core.time import UTC, utcfromtimestamp, utcnow


def test_hc_time_001_utcnow_returns_naive_utc():
    now = utcnow()
    assert now.tzinfo is None
    # Same instant as aware now, minus the tzinfo — the utcnow() contract.
    aware_now = datetime.now(UTC)
    assert abs((aware_now.replace(tzinfo=None) - now).total_seconds()) < 2


def test_hc_time_002_utcnow_compares_against_stored_naive_values():
    # Rows come back from DateTime columns as naive datetimes. If utcnow()
    # ever went aware, this subtraction (and every cutoff comparison in
    # adherence_patterns / notification_scheduler) would raise TypeError.
    stored = datetime(2026, 1, 1, 12, 0, 0)
    assert utcnow() - stored > timedelta(0)


def test_hc_time_003_scheduler_day_boundary_stays_naive():
    # notification_scheduler builds today_start = combine(utcnow().date(), 0:00)
    # and compares it to naive stored reminder times.
    today_start = datetime.combine(utcnow().date(), time(0, 0))
    stored_reminder = datetime(2026, 9, 25, 8, 30)
    _ = stored_reminder < today_start  # must not raise TypeError


def test_hc_time_004_utcfromtimestamp_is_naive_too():
    assert utcfromtimestamp(0).tzinfo is None
    assert utcfromtimestamp(0) == datetime(1970, 1, 1, 0, 0, 0)
```

- [ ] **Step 2: Run it — expected PASS (it pins existing behavior, it does not drive a change)**

Run: `cd src/backend && python -m pytest tests/test_time_source.py -v`
Expected: 4 passed

- [ ] **Step 3: Commit**

```bash
git add src/backend/tests/test_time_source.py
git commit -m "test(time): pin naive-UTC semantics of core.time.utcnow"
```

---

### Task 1: `models/` — column defaults (14 files, 41 sites)

All 41 sites are callable references (`default=datetime.utcnow`, `onupdate=datetime.utcnow`), never calls. Same swap in every file: add the import, replace each `datetime.utcnow` token with `utcnow`.

**Files:**
- Modify: `src/backend/models/audit.py:62`
- Modify: `src/backend/models/chat_session.py:49,55,56,118`
- Modify: `src/backend/models/chunk.py:70`
- Modify: `src/backend/models/document_category.py:26,52`
- Modify: `src/backend/models/embedding.py:63`
- Modify: `src/backend/models/gamification.py:67`
- Modify: `src/backend/models/interpretation.py:110,113,193,196`
- Modify: `src/backend/models/knowledge_base.py:92,99,102,174,177,242,245`
- Modify: `src/backend/models/medication.py:73,79,82,152,155,229,301,369,387`
- Modify: `src/backend/models/memory_item.py:50,55,56`
- Modify: `src/backend/models/model_settings.py:142,147,148`
- Modify: `src/backend/models/observation.py:96,99`
- Modify: `src/backend/models/response_feedback.py:101,107,108`

- [ ] **Step 1: Add the import to each of the 14 files**

In each file, insert into the first-party import group (alphabetical; `core.time` sorts after `api`/`config` imports):

```python
from core.time import utcnow
```

Note: `models/document_category.py` uses `Mapped[datetime]`/`mapped_column` style — same import, same swap.

- [ ] **Step 2: Replace every `datetime.utcnow` with `utcnow`**

Example diff shape (applies to all 41 lines):

```python
# before
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
# after
created_at = Column(DateTime, default=utcnow, nullable=False)
updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
```

Verify no stragglers: `grep -n "datetime.utcnow" src/backend/models/` → empty.

- [ ] **Step 3: Run the model-touching tests**

Run: `cd src/backend && python -m pytest tests/test_gamification_models.py tests/test_chat_sessions.py tests/test_memory_crud.py tests/test_rl_feedback.py tests/test_med_reconcile.py -q`
Then: `python -m pytest tests/ -k "model or session or memory or feedback or medication or observation" -q`
Expected: all selected tests pass; defaults still fire on insert.

- [ ] **Step 4: Commit**

```bash
git add src/backend/models/
git commit -m "fix(models): use core.time.utcnow for all column defaults"
```

---

### Task 2: `api/documents.py` — document pipeline timestamps (4 sites)

**Files:**
- Modify: `src/backend/api/documents.py` — import block at line 20 (`from datetime import datetime, timedelta`)
- Test: `src/backend/tests/test_documents_api.py`

**Exact sites today:**
- `:470` `imported_at=datetime.utcnow(),` → `imported_at=utcnow(),`
- `:669` `document.parsed_at = datetime.utcnow()` → `document.parsed_at = utcnow()`
- `:807` `document.parsed_at = datetime.utcnow()` → `document.parsed_at = utcnow()`
- `:1272` `now = datetime.utcnow()` → `now = utcnow()` — **timestamp-sensitive**: this is the verify-all transaction; `now` is written to `obs.verified_at` and `document.verified_at` in the same commit. Naive→naive, unchanged.

- [ ] **Step 1:** Add `from core.time import utcnow` to the first-party imports.
- [ ] **Step 2:** Apply the four replacements above.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/test_documents_api.py tests/test_source_spans.py -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/api/documents.py && git commit -m "fix(api): use core.time.utcnow in documents routes"`

---

### Task 3: `api/observations.py` + `api/interpretations.py` — verification timestamps (3 sites)

**Timestamp-sensitive:** `verified_at`/`viewed_at` are user-facing audit fields; value semantics unchanged (naive UTC).

**Files:**
- Modify: `src/backend/api/observations.py` (imports at `:16` `from datetime import date, datetime`)
- Modify: `src/backend/api/interpretations.py` (imports at `:14` `from datetime import datetime`)

**Exact sites today:**
- `observations.py:459` `observation.verified_at = datetime.utcnow()` → `utcnow()`
- `observations.py:489` `document.verified_at = datetime.utcnow()` → `utcnow()`
- `interpretations.py:559` `interpretation.viewed_at = datetime.utcnow()` → `utcnow()`

- [ ] **Step 1:** Add `from core.time import utcnow` in each file's first-party group.
- [ ] **Step 2:** Apply the three replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/ -k "observ or interpret or verif" -q` — expect PASS (probe: tests covering verify/view endpoints).
- [ ] **Step 4:** Commit: `git add src/backend/api/observations.py src/backend/api/interpretations.py && git commit -m "fix(api): use core.time.utcnow for verification timestamps"`

---

### Task 4: `api/notifications.py` — reminder paths (3 sites, timestamp-sensitive)

`now` feeds `MessageContext(is_weekend=now.weekday() >= 5, hour_of_day=now.hour)` — the migration must not shift the value (it doesn't: same instant, same fields).

**Files:**
- Modify: `src/backend/api/notifications.py` (imports at `:15` `from datetime import datetime, time, timedelta`)

**Exact sites today:**
- `:454` `now = datetime.utcnow()` → `now = utcnow()`
- `:551` `reminder.interacted_at = datetime.utcnow()` → `utcnow()`
- `:612` `now = datetime.utcnow()` → `now = utcnow()` — used for `seven_days_ago`/`thirty_days_ago` notification-stat windows compared against naive stored timestamps.

- [ ] **Step 1:** Add `from core.time import utcnow`.
- [ ] **Step 2:** Apply the three replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/ -k "notif or reminder" -q` — expect PASS. If the probe selects zero tests, note it and rely on Task 14's full suite.
- [ ] **Step 4:** Commit: `git add src/backend/api/notifications.py && git commit -m "fix(api): use core.time.utcnow in notification routes"`

---

### Task 5: `api/profiles.py` + `api/model_settings.py` (8 sites)

`profiles.py` already imports `utcnow` (`:23`) and already uses it at `:733` — finish the partial migration. The existing source-assertion test `test_hc_recov_025` (`tests/test_profile_recovery.py:342`) already proved `recover_profile` is clean; these are the remaining sites elsewhere in the file.

**Files:**
- Modify: `src/backend/api/profiles.py`
- Modify: `src/backend/api/model_settings.py` (imports at `:15` `from datetime import datetime, timezone` — `timezone` may be used elsewhere; keep)

**Exact sites today:**
- `profiles.py:311-313` `created_at=`/`updated_at=`/`last_accessed_at=datetime.utcnow(),` (3 lines) → `utcnow()`
- `profiles.py:391` `profile.last_accessed_at = datetime.utcnow()` → `utcnow()`
- `profiles.py:1052` `profile.last_accessed_at = datetime.utcnow()` → `utcnow()`
- `profiles.py:1153` `profile.updated_at = datetime.utcnow()` → `utcnow()`
- `model_settings.py:649` `started_at=datetime.utcnow(),` → `utcnow()` — job progress timestamp
- `model_settings.py:865` `started_at=datetime.utcnow(),` → `utcnow()`

- [ ] **Step 1:** Add `from core.time import utcnow` to `model_settings.py` only (profiles.py has it).
- [ ] **Step 2:** Apply the eight replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/test_profile_recovery.py -q && python -m pytest tests/ -k "profile or model_settings" -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/api/profiles.py src/backend/api/model_settings.py && git commit -m "fix(api): finish core.time.utcnow migration in profiles/model_settings"`

---

### Task 6: `modules/notification_scheduler.py` — scheduler timing (5 sites, timestamp-sensitive)

This is the most timing-sensitive file in the migration (audit hint: reminders). `now`/`_last_check_time`/`today_start` are compared against naive stored reminder timestamps and `timedelta` arithmetic. Semantics unchanged.

**Files:**
- Modify: `src/backend/modules/notification_scheduler.py` (imports at `:18` `from datetime import datetime, time, timedelta`)

**Exact sites today:**
- `:215` `self._last_check_time = datetime.utcnow()` → `utcnow()`
- `:228` `now = datetime.utcnow()` → `utcnow()`
- `:251` `now = datetime.utcnow()` → `utcnow()`
- `:444` `today_start = datetime.combine(datetime.utcnow().date(), time(0, 0))` → `datetime.combine(utcnow().date(), time(0, 0))`
- `:471` `now = datetime.utcnow()` → `utcnow()`

`datetime` stays imported (`datetime.combine`, `Optional[datetime]` annotations at `:134,:136` remain).

- [ ] **Step 1:** Add `from core.time import utcnow`.
- [ ] **Step 2:** Apply the five replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/ -k "scheduler or reminder or notif" -q` — expect PASS; if zero collected, rely on Task 0 pin tests + Task 14 suite and say so in the commit body.
- [ ] **Step 4:** Commit: `git add src/backend/modules/notification_scheduler.py && git commit -m "fix(modules): use core.time.utcnow in notification scheduler"`

---

### Task 7: `modules/adherence_patterns.py` — cutoffs, streaks, `valid_until` (8 sites, timestamp-sensitive)

`cutoff` values are compared against naive `DoseTaken.taken_at` column values; `valid_until` is persisted. All naive↔naive, unchanged.

**Files:**
- Modify: `src/backend/modules/adherence_patterns.py` (imports at `:14` `from datetime import datetime, time, timedelta`)

**Exact sites today:**
- `:194` `cutoff = datetime.utcnow() - timedelta(days=days_lookback)` → `utcnow() - ...`
- `:266` same pattern → `utcnow()`
- `:332` same pattern → `utcnow()`
- `:430` `today = datetime.utcnow().date()` → `utcnow().date()` — streak "counting backwards from today"
- `:533,:555,:573,:594` `valid_until=datetime.utcnow() + timedelta(days=14),` (4 lines) → `utcnow() + ...`

- [ ] **Step 1:** Add `from core.time import utcnow`.
- [ ] **Step 2:** Apply the eight replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/test_med_reconcile.py -q && python -m pytest tests/ -k "adher or streak or pattern" -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/modules/adherence_patterns.py && git commit -m "fix(modules): use core.time.utcnow in adherence patterns"`

---

### Task 8: `modules/platform_notifications.py` — `delivered_at` (4 sites)

**Files:**
- Modify: `src/backend/modules/platform_notifications.py` (imports at `:16` `from datetime import datetime`)

**Exact sites today:** `:174,:282,:359` inside blocks and `:418` — all `delivered_at=datetime.utcnow(),` → `delivered_at=utcnow(),`.

- [ ] **Step 1:** Add `from core.time import utcnow`.
- [ ] **Step 2:** Apply the four replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/ -k "notif or platform" -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/modules/platform_notifications.py && git commit -m "fix(modules): use core.time.utcnow in platform notifications"`

---

### Task 9: `modules/agent/` — run-step timestamps and trend cutoff (4 sites, 3 files)

**Files:**
- Modify: `src/backend/modules/agent/graph.py:128,139` — `timestamp=datetime.utcnow(),` → `utcnow()` (RunStep audit timestamps; imports at `:48`)
- Modify: `src/backend/modules/agent/nodes/act.py:57` — same shape (imports at `:17`)
- Modify: `src/backend/modules/agent/tools/compute_trend.py:60` — `cutoff = datetime.utcnow() - timedelta(days=args.window_days)` → `utcnow() - ...` (imports at `:5`)

- [ ] **Step 1:** Add `from core.time import utcnow` to all three files.
- [ ] **Step 2:** Apply the four replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/agent/ -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/modules/agent/ && git commit -m "fix(agent): use core.time.utcnow for step timestamps and trend cutoff"`

---

### Task 10: Serialization sites — `modules/export.py`, `modules/ingest.py`, `modules/rl_dataset.py` (4 sites)

**Format watch (explicit flag):** all three produce serialized timestamps. Because `utcnow()` is value-identical to `datetime.utcnow()`, output is byte-identical — `.isoformat()` stays offset-free, the `"Z"` suffixes are literal appends, and the `strftime` footer is unchanged. No format change is being made; if the review shows otherwise, stop.

**Files:**
- Modify: `src/backend/modules/export.py:164` — `generated_at=datetime.utcnow(),` → `utcnow()`; `:352` — f-string `{datetime.utcnow().strftime('%B %d, %Y')}` → `{utcnow().strftime('%B %d, %Y')}`. File already imports `utcnow` (`:19`).
- Modify: `src/backend/modules/ingest.py:320` — `"imported_at": datetime.utcnow().isoformat(),` → `utcnow().isoformat()` (imports at `:17`)
- Modify: `src/backend/modules/rl_dataset.py:258` — `"exported_at": datetime.utcnow().isoformat() + "Z",` → `utcnow().isoformat() + "Z"` (imports at `:32`)

- [ ] **Step 1:** Add `from core.time import utcnow` to `ingest.py` and `rl_dataset.py` only.
- [ ] **Step 2:** Apply the four replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/test_export_api.py tests/test_export_questions.py tests/test_fhir_export.py tests/test_rl_feedback.py -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/modules/export.py src/backend/modules/ingest.py src/backend/modules/rl_dataset.py && git commit -m "fix(modules): use core.time.utcnow at export/ingest serialization sites"`

---

### Task 11: `modules/hardware_detection.py` + `modules/model_selector.py` (17 sites)

**Files:**
- Modify: `src/backend/modules/hardware_detection.py` (imports at `:18`):
  - `:203` `detection_timestamp: datetime = field(default_factory=datetime.utcnow)` → `field(default_factory=utcnow)` — callable ref, not a call
  - `:228` `timestamp = datetime.utcnow()` → `utcnow()`
  - `:304` `detection_timestamp=datetime.utcnow(),` → `utcnow()`
- Modify: `src/backend/modules/model_selector.py` (imports at `:16`): 14 sites at `:266,:273,:274,:304,:305,:313,:314,:315,:677,:687,:700,:787,:788,:800` — `updated_at`/`created_at`/`last_detection_at`/`started_at`/`completed_at` assignments and kwargs, all `datetime.utcnow()` → `utcnow()`.

- [ ] **Step 1:** Add `from core.time import utcnow` to both files.
- [ ] **Step 2:** Apply all replacements; verify `grep -n "datetime.utcnow" src/backend/modules/model_selector.py src/backend/modules/hardware_detection.py` → empty.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/ -k "hardware or detection or model_selector or download" -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/modules/hardware_detection.py src/backend/modules/model_selector.py && git commit -m "fix(modules): use core.time.utcnow in hardware detection and model selector"`

---

### Task 12: `tests/` cleanup — 6 files, 16 sites (consistency, not gated)

The lint gate (Task 13) excludes `src/backend/tests/` (matching bandit's `-x src/backend/tests/` precedent, and because `test_profile_recovery.py` legitimately contains the literal string in a source assertion). Migrate anyway for consistency — same import + swap. Compliant prior art: `tests/test_chat_sessions.py:24-26` and `tests/test_rl_feedback.py:34-36` already wrap `core.time.utcnow` in `_utcnow()`.

**Files:**
- `tests/agent/conftest.py:95,129,193,194,225`
- `tests/agent/test_agentic_queries.py:34`
- `tests/agent/test_s2_loop.py:16`
- `tests/test_documents_api.py:116,281,324,362,412,457`
- `tests/test_export_api.py:323,346`
- `tests/test_memory_crud.py:66`

- [ ] **Step 1:** Add `from core.time import utcnow` per file; replace all 16 `datetime.utcnow()` with `utcnow()`.
- [ ] **Step 2:** Run: `cd src/backend && python -m pytest tests/agent/ tests/test_documents_api.py tests/test_export_api.py tests/test_memory_crud.py -q` — expect PASS.
- [ ] **Step 3:** Commit: `git add src/backend/tests/ && git commit -m "test: use core.time.utcnow in remaining test helpers"`

---

### Task 13: Lint gate — `scripts/time_source_lint.py` + CI step

**Files:**
- Create: `scripts/time_source_lint.py` (repo-root `scripts/`, alongside `docs_lint.py`/`feature_list_lint.py` — NOT `src/backend/scripts/`)
- Modify: `.github/workflows/ci.yml` — add one step to the `docs-lint` job after the `feature_list_lint` step (line ~28). That job already has Python and zero install steps — the right home for a stdlib gate.

Design choices (state in review): pattern is `datetime\.(utcnow|utcfromtimestamp)` — no trailing `\(` so it also catches `default=datetime.utcnow` reference-form reintroduction; `utcfromtimestamp` is the same deprecation class and `core.time.utcfromtimestamp` exists. Scan root is `src/backend/` **excluding** `tests/` and `__pycache__` — bandit already excludes tests in this CI file, and `test_profile_recovery.py:344,350` legitimately contains the literal string in a source assertion. Ruff was rejected as the gate mechanism: it is configured (`pyproject.toml` `select = ["F","I","W"]`) but **ungated** (audit §13), and enabling `DTZ` would also flag the out-of-scope `datetime.now()` sites in `gamification.py`/`source_authority.py`.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Fail on deprecated datetime timestamp helpers in src/backend product code.

CLAUDE.md hard invariant: core.time.utcnow is the single timestamp helper
(core.time.utcfromtimestamp for POSIX timestamps). datetime.utcnow() and
datetime.utcfromtimestamp() are also deprecated from Python 3.12.

Scans src/backend/ excluding tests/ (which legitimately mention the literal
string in source assertions, e.g. test_hc_recov_025) — matching the bandit
-x src/backend/tests/ precedent in ci.yml.

Usage: python3 scripts/time_source_lint.py
Exit 0 when clean; exit 1 listing file:line for each violation.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO_ROOT / "src" / "backend"
EXCLUDE_DIR_NAMES = {"tests", "__pycache__"}
PATTERN = re.compile(r"datetime\.(utcnow|utcfromtimestamp)")


def find_violations() -> list[str]:
    violations: list[str] = []
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if PATTERN.search(line):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}"
                )
    return violations


def main() -> int:
    violations = find_violations()
    if violations:
        print("Deprecated datetime timestamp helpers found "
              "(use core.time.utcnow / core.time.utcfromtimestamp):")
        for line in violations:
            print(f"  {line}")
        return 1
    print("time_source_lint passed: no datetime.utcnow/utcfromtimestamp "
          "in src/backend product code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Prove the gate fails on a planted violation**

Run: `cd /tmp && echo 'from datetime import datetime; x = datetime.utcnow()' > /tmp/planted.py && cp /tmp/planted.py <repo>/src/backend/_planted_lint_probe.py && python3 scripts/time_source_lint.py; echo "exit=$?"`
Expected: exit=1, output lists `src/backend/_planted_lint_probe.py:1`.
Then remove it: `rm src/backend/_planted_lint_probe.py` and re-run → expect exit=0 pass line.

- [ ] **Step 3: Add the CI step** to the `docs-lint` job in `.github/workflows/ci.yml`, after the `feature_list_lint` step:

```yaml
      - name: Lint: deprecated datetime helpers banned in backend
        run: python3 scripts/time_source_lint.py
```

- [ ] **Step 4: Commit**

```bash
git add scripts/time_source_lint.py .github/workflows/ci.yml
git commit -m "ci: gate src/backend on core.time.utcnow helper"
```

Note for reviewers: running the gate mid-migration doubles as a progress checklist — it prints every remaining violation.

---

### Task 14: Final verification

- [ ] **Step 1:** `find src/backend -name __pycache__ -type d -exec rm -rf {} +` (WSL/9p stale-bytecode guard).
- [ ] **Step 2:** `grep -rn "datetime\.utcnow\|datetime\.utcfromtimestamp" src/backend --include="*.py" | grep -v "src/backend/tests/"` → **0 hits outside `tests/`**; inside `tests/` only `test_profile_recovery.py`'s source-assertion literals remain.
- [ ] **Step 3:** `python3 scripts/time_source_lint.py` → exit 0.
- [ ] **Step 4:** `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` → **the start-of-plan collected count plus any tests this plan added** (corrected 2026-09-27; was "1245 collected"), no new failures (env-only `test_api_rag_index_002b` failure is pre-existing and not yours).
- [ ] **Step 5:** `cd src/backend && python -c "from main import app"` → boots clean.
- [ ] **Step 6:** Log the session in `docs/features/TASK_LIST.md` Session Notes; re-read `docs/agentic/recurring-failures.md` — if any listed mode recurred (e.g. a green suite masking a path the tests never exercise), record it in the same commit.
- [ ] **Step 7:** Commit: `git commit -m "docs: log utcnow migration session"` (or fold into the last code commit).

---

## Out of scope (recorded, not migrated here)

- `api/gamification.py:148`, `modules/badge_evaluator.py:84` — aware `datetime.now(dt_timezone.utc)`; feeding aware values into naive-UTC comparisons/columns is the audit's suspected latent bug. Belongs to workstream §16 item 8 (systemic UTC audit), not this drop-in migration.
- `modules/source_authority.py:216` — `datetime.now().year` uses local time, not UTC.
- `core/time.py` itself — defines the helpers; not a violation.
