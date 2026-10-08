# datetime.utcnow → core.time.utcnow Migration Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-03/F-06):** the inventory units are reconciled under "Audit anchor", and the baseline is now measured at plan start instead of hard-coded. Nothing about the plan's semantics changed: naive UTC is correct. **Staging and ask-first (contracts review, 2026-09-27):**
> - The directory adds at Task 1 (`git add src/backend/models/`), Task 9 (`src/backend/modules/agent/`) and Task 12 (`src/backend/tests/`) are allowed only after `git status --short <dir>` shows this task's changes and nothing else (contract C-GATE-3).
> - Task 5 edits auth flows in `api/profiles.py` (`create_profile`, `login`, `unlock_profile`, `change_password`). CLAUDE.md §1 requires an explicit owner yes for those hunks, even though the swap is mechanical (program P5).

> **2026-10-08 amendments (Wave 4 L1-A)** — sources: owner rows **P5-SCOPE** ("Include TIME-03") and **P5-IMPORT** ("Yes, remove it") in [owner-decisions](../../../docs/capstone-report/owner-decisions-2026-09-27.md); the Codex plan review in [`waves/scaffold/REVIEWS-2026-10-07.md`](../waves/scaffold/REVIEWS-2026-10-07.md) §2; the readiness pack [`waves/scaffold/P5.md`](../waves/scaffold/P5.md) §4. Each item was re-checked against `origin/main@777adf5` before it was applied.
> 1. **TIME-03 is in scope, for one site.** Task 12b converts `modules/badge_evaluator.py:84` to `utcnow()`. This supersedes item 2 of the Wave-3 banner below and the first "Out of scope" line for that site only. The other aware sites (`core/auth.py`, `core/security.py`, `core/token_revocation.py`, `api/export.py`, `api/model_settings.py:343`, `api/gamification.py:148`, `api/medications.py:84`) stay untouched.
> 2. **One response string changes, and only one.** `BadgeInfo.earned_at` in the dose-log response (`api/medications.py:285`) loses its `+00:00` suffix. The owner accepted this (P5-SCOPE). Every other serialized value must stay byte-identical (D13).
> 3. **Unused imports.** After the swap `from datetime import datetime` is unused in 4 product files and 2 test files; Tasks 5, 9, 10 and 12 delete those lines. `api/profiles.py:13` is covered by P5-IMPORT.
> 4. **The lint is an AST scan** (Task 13). The line-regex in the first version matched the docstring at `src/backend/core/time.py:18`, so the clean tree failed its own gate.
> 5. **Task 13 fixes:** the CI step name is quoted (an unquoted `Lint: …` is invalid YAML); the step goes after `Repo hygiene check` (`ci.yml:30-31`); the seeded-gate command uses real paths.
> 6. **Moved line numbers** are corrected in Tasks 2, 3, 4, 5, 6 and 11; Task 1 lists 13 files, not 14; Task 12 covers 7 files and 18 sites.
> 7. **Collected count.** This plan adds 7 tests: HC-TIME-001…005 (Task 0) and HC-TIME-006…007 (Task 12b). Each commit that adds tests rewrites the collected slots (`CLAUDE.md:30`, `:35`; the `AGENT.md` backend-tests line) to the number measured on that commit.
> 8. **Not edited here:** `docs/architecture/ci-and-quality-gates.md:17` (the `docs-lint` box does not list the new step). W-11a PR-3 Task 9 owns that file; it is recorded as an open item in the PR.

> **Wave-3 integration banner (2026-09-28)** — sources: `audit/2026-09-25/swarm-2026-09-27/wave3/3a-integration.md` B-4, `wave3/3b-evidence.md` MINOR 1 (re-checked against `40f590e` before this banner was written).
> 1. **Collected-count slots (3a B-4; owner-gated SLOT-RULE).** Task 0 adds HC-TIME-001…004 (`tests/test_time_source.py`), and its commit does not stage `CLAUDE.md`/`AGENT.md`. If the owner signs SLOT-RULE: every commit that changes the collected count also updates the collected slots in `CLAUDE.md` and `AGENT.md`, in the same commit, with the number measured on that commit's tree. Collected slots only; pass sentences are left as they are and flagged in the PR. Without the rule, W-2 (which starts after P5) STOPs on a stale slot.
> 2. **Aware datetimes are out of scope (3b MINOR 1; matrix TIME-03, unowned).** Product code has 7 aware `datetime.now(timezone.utc)` sites in 5 files: `core/auth.py:73,144`, `core/security.py:136`, `core/token_revocation.py:51`, `api/export.py:949,1005`, `api/model_settings.py:332` (`git grep -n "datetime.now(timezone.utc)" 40f590e -- src/backend ':!src/backend/tests'`). This plan replaces `datetime.utcnow` only and does not touch them. Do not "fix" them in passing: `core/auth.py:73` (`Session.is_expired`) compares against the aware `expires_at` built at `:144`, so swapping in naive `utcnow()` there raises `TypeError`, and `core/auth.py`/`core/security.py` are ask-first. TIME-03 stays unowned until the owner assigns it. (Task 0's migration risk statement and the out-of-scope list already name the two `dt_timezone.utc` sites in `gamification.py`/`badge_evaluator.py`; these 7 are additional. Wave-7 re-check: `git grep -nE '(dt_)?timezone\.utc' 40f590e -- 'src/backend/*.py' ':!src/backend/tests' ':!src/backend/core/time.py'` → **12 lines in 8 files**: 9 aware `now(…utc)` calls in 7 files plus 3 aware conversions, `core/auth.py:207`, `api/medications.py:84`, `modules/badge_evaluator.py:54`.) **One aware value is persisted:** `modules/badge_evaluator.py:84` `now = datetime.now(dt_timezone.utc)` → `earned_at=now` (`:101`) → `EarnedBadge(earned_at=…)` (`:157-163`), a naive `DateTime` column (`models/gamification.py:64-68`), reached from the dose route `api/medications.py:1000`. The program's owner item **TIME-03** proposes adding that `badge_evaluator.py` site to P5 scope (not ask-first); the owner decides, and until then this plan leaves it alone. `core/auth.py` and `core/security.py` stay ask-first either way.
> 3. **Task numbers in the 2026-09-27 banner above were off by one** for three items and are corrected in place: the directory adds are at Tasks 9 and 12 (pre-banner `:318`, `:368`), and the `api/profiles.py` auth hunks are Task 5.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every `datetime.utcnow()` call site and `default=datetime.utcnow` column default in `src/backend` with `core.time.utcnow`, and add a CI lint gate so the deprecated helper cannot re-enter the codebase.

**Architecture:** `core.time.utcnow()` returns `datetime.now(UTC).replace(tzinfo=None)` — a **naive UTC** datetime, semantically identical to the deprecated `datetime.utcnow()`. Every change is therefore a drop-in symbol swap plus one import line per file. No DB migration, no comparison-behavior change, and no serialization change except the one the owner accepted under P5-SCOPE (Task 12b: the dose-log `earned_at` string). A stdlib-only lint script (`scripts/time_source_lint.py`) is wired into the existing `docs-lint` CI job, matching the repo's one-script-one-check convention (`docs_lint.py`, `feature_list_lint.py`, `security_gate.py`).

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
- **Serialization formats must not change, with one named exception.** `.isoformat()`, `.isoformat() + "Z"`, and `strftime` outputs are byte-identical because the values are identical. The exception (owner row P5-SCOPE, Task 12b): `BadgeInfo.earned_at` in the dose-log response (`api/medications.py:285`) changes from `2026-03-04T08:00:00.123456+00:00` to `2026-03-04T08:00:00.123456`. If any other site would produce different output, stop and flag it.
- **Do not touch ask-first files** (`modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`) — none contain violations anyway (verified: none appear in the enumeration below).
- **Baseline:** `python -m pytest tests/ -p no:cacheprovider -q` collects **1245** tests at main@`40f590e` (re-measured 2026-09-27); all pass in CI. *Corrected 2026-09-27:* this plan runs after plans 01–04, so its start count is whatever that tree collects (the post-merge tree collected 1,291 on 2026-09-27). Measure the count before Task 1 and use that number. On WSL, clear `__pycache__` first: `find src/backend -name __pycache__ -type d -exec rm -rf {} +`. The env-only failure `test_api_rag_index_002b` (needs a real embedding model) is not yours — do not touch it.
- **Import placement:** `from core.time import utcnow` goes in the first-party import group. Ruff isort config (`src/backend/pyproject.toml`) declares `known-first-party = ["api", "core", "models", "modules", "scripts"]`. Prior art in already-migrated files: `models/pinboard.py:10`, `models/care_plan_task.py:20`, `models/backup_schedule.py:28`, `api/assistant.py:29`, `api/profiles.py:23`.
- **`datetime` imports.** Most violating files also use `datetime` for other things (`timedelta`, `datetime.combine`, `Mapped[datetime]`, `datetime(...)` literals): leave their `from datetime import ...` line alone. Six files end with zero remaining `datetime` references (measured at `777adf5`); delete the import line in each, in the task that swaps the file: `api/profiles.py:13` (owner row P5-IMPORT: "P5 deletes the unused import: a 7th changed line in api/profiles.py, no behaviour change. If any use of datetime remains in the file at execution time, the import stays and I report it."), `modules/agent/graph.py:48`, `modules/agent/nodes/act.py:17`, `modules/ingest.py:17`, `tests/test_memory_crud.py:10`, `tests/test_notification_scheduler_wiring.py:14`. Before deleting, run `grep -n "datetime" <file>`: if anything other than the import line and `core.time` remains, keep the import and report it.

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
"""HC-TIME-001…005 — pin the naive-UTC semantics the codebase relies on.

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

Add a fifth test to the same file (2026-10-08; D13 says "tests must show identical serialization", and the four tests above do not look at a response):

```python
import re
from types import SimpleNamespace

NAIVE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{6})?$")


def test_hc_time_005_profile_responses_serialize_naive_iso():
    # D13: the auth-file swaps must not change what the profile routes return.
    # ProfileResponse.from_model is what create_profile / login / unlock return.
    from api.profiles import ProfileResponse

    profile = SimpleNamespace(
        id="p1",
        display_name="T",
        is_locked=False,
        password_hash=None,
        created_at=utcnow(),
        last_accessed_at=utcnow(),
    )
    body = ProfileResponse.from_model(profile)
    assert NAIVE_ISO.match(body.created_at), body.created_at
    assert NAIVE_ISO.match(body.last_accessed_at), body.last_accessed_at
    # Same shape the deprecated helper produced: no offset, no "Z".
    assert NAIVE_ISO.match(datetime(2026, 1, 1, 12, 0, 0, 123456).isoformat())
```

If `ProfileResponse.from_model` needs other attributes at execution time, add them to the `SimpleNamespace`; do not change the assertions.

- [ ] **Step 2: Run it — expected PASS (it pins existing behavior, it does not drive a change)**

Run: `cd src/backend && HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_time_source.py -p no:cacheprovider -v`
Expected: 5 passed

These five tests pass before and after the migration. They cannot see a missed swap; only the Task 13 lint can. Say so in the commit body.

- [ ] **Step 3: Commit** (the collected count changes by +5: rewrite the slots to the measured number in this commit)

```bash
git add src/backend/tests/test_time_source.py CLAUDE.md AGENT.md
git commit -m "test(time): pin naive-UTC semantics of core.time.utcnow"
```

---

### Task 1: `models/` — column defaults (13 files, 41 sites)

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

- [ ] **Step 1: Add the import to each of the 13 files**

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

**Exact sites (re-measured 2026-10-08 @ `777adf5`):**
- `:471` `imported_at=datetime.utcnow(),` → `imported_at=utcnow(),`
- `:670` `document.parsed_at = datetime.utcnow()` → `document.parsed_at = utcnow()`
- `:808` `document.parsed_at = datetime.utcnow()` → `document.parsed_at = utcnow()`
- `:1273` `now = datetime.utcnow()` → `now = utcnow()` — **timestamp-sensitive**: this is the verify-all transaction; `now` is written to `obs.verified_at` and `document.verified_at` in the same commit. Naive→naive, unchanged.

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
- `interpretations.py:618` `interpretation.viewed_at = datetime.utcnow()` → `utcnow()` (was `:559`)

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
- `:455` `now = datetime.utcnow()` → `now = utcnow()`
- `:553` `reminder.interacted_at = datetime.utcnow()` → `utcnow()`
- `:614` `now = datetime.utcnow()` → `now = utcnow()` — used for `seven_days_ago`/`thirty_days_ago` notification-stat windows compared against naive stored timestamps.

- [ ] **Step 1:** Add `from core.time import utcnow`.
- [ ] **Step 2:** Apply the three replacements.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/ -k "notif or reminder" -q` — expect PASS. If the probe selects zero tests, note it and rely on Task 14's full suite.
- [ ] **Step 4:** Commit: `git add src/backend/api/notifications.py && git commit -m "fix(api): use core.time.utcnow in notification routes"`

---

### Task 5: `api/profiles.py` + `api/model_settings.py` (8 sites + 1 import line)

`profiles.py` already imports `utcnow` (`:23`) and already uses it at `:733` — finish the partial migration. The existing source-assertion test `test_hc_recov_025` (`tests/test_profile_recovery.py:342`) already proved `recover_profile` is clean; these are the remaining sites elsewhere in the file.

**Files:**
- Modify: `src/backend/api/profiles.py`
- Modify: `src/backend/api/model_settings.py` (imports at `:15` `from datetime import datetime, timezone` — `timezone` may be used elsewhere; keep)

**Exact sites today:**
- `profiles.py:311-313` `created_at=`/`updated_at=`/`last_accessed_at=datetime.utcnow(),` (3 lines) → `utcnow()`
- `profiles.py:391` `profile.last_accessed_at = datetime.utcnow()` → `utcnow()`
- `profiles.py:1052` `profile.last_accessed_at = datetime.utcnow()` → `utcnow()`
- `profiles.py:1153` `profile.updated_at = datetime.utcnow()` → `utcnow()`
- `model_settings.py:664` `started_at=datetime.utcnow(),` → `utcnow()` — job progress timestamp (`start_model_download`; was `:649`)
- `model_settings.py:880` `started_at=datetime.utcnow(),` → `utcnow()` (`_write_download_status`; was `:865`)
- `profiles.py:13` `from datetime import datetime` → **delete the line** (P5-IMPORT). Check first: `grep -n "datetime" src/backend/api/profiles.py` must show only line 13 and the six swap lines.

**`api/profiles.py` is an auth file (ask-first).** The diff of that file must be exactly 7 changed lines: the six swaps (D13) and the deleted import (P5-IMPORT). Paste `git diff origin/main...HEAD -- src/backend/api/profiles.py` in the PR body. Both `model_settings.py` sites sit outside the encryption handler `save_external_api_settings`.

- [ ] **Step 1:** Add `from core.time import utcnow` to `model_settings.py` only (profiles.py has it).
- [ ] **Step 2:** Apply the eight replacements and delete `profiles.py:13`.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/test_profile_recovery.py tests/test_time_source.py -q && python -m pytest tests/ -k "profile or model_settings" -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/api/profiles.py src/backend/api/model_settings.py && git commit -m "fix(api): finish core.time.utcnow migration in profiles/model_settings"`

---

### Task 6: `modules/notification_scheduler.py` — scheduler timing (5 sites, timestamp-sensitive)

This is the most timing-sensitive file in the migration (audit hint: reminders). `now`/`_last_check_time`/`today_start` are compared against naive stored reminder timestamps and `timedelta` arithmetic. Semantics unchanged.

**Files:**
- Modify: `src/backend/modules/notification_scheduler.py` (imports at `:18` `from datetime import datetime, time, timedelta`)

**Exact sites today:**
- `:260` `self._last_check_time = datetime.utcnow()` → `utcnow()`
- `:273` `now = datetime.utcnow()` → `utcnow()`
- `:313` `now = datetime.utcnow()` → `utcnow()`
- `:506` `today_start = datetime.combine(datetime.utcnow().date(), time(0, 0))` → `datetime.combine(utcnow().date(), time(0, 0))`
- `:533` `now = datetime.utcnow()` → `utcnow()`

(Line numbers re-measured 2026-10-08; they were `:215,:228,:251,:444,:471` before P2.) `datetime` stays imported (`datetime.combine`, `Optional[datetime]` annotations at `:145,:147` remain).

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
- [ ] **Step 2:** Apply the four replacements. Then delete the now-unused `from datetime import datetime` at `graph.py:48` and `nodes/act.py:17` (check with `grep -n "datetime"` first; `compute_trend.py:5` stays: `timedelta` and `collected_at: datetime` are used).
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
- [ ] **Step 2:** Apply the four replacements. Then delete the now-unused `from datetime import datetime` at `ingest.py:17` (check with `grep -n "datetime"` first; `rl_dataset.py:32` stays).
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/test_export_api.py tests/test_export_questions.py tests/test_fhir_export.py tests/test_rl_feedback.py -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/modules/export.py src/backend/modules/ingest.py src/backend/modules/rl_dataset.py && git commit -m "fix(modules): use core.time.utcnow at export/ingest serialization sites"`

---

### Task 11: `modules/hardware_detection.py` + `modules/model_selector.py` (17 sites)

**Files:**
- Modify: `src/backend/modules/hardware_detection.py` (imports at `:18`):
  - `:203` `detection_timestamp: datetime = field(default_factory=datetime.utcnow)` → `field(default_factory=utcnow)` — callable ref, not a call
  - `:228` `timestamp = datetime.utcnow()` → `utcnow()`
  - `:304` `detection_timestamp=datetime.utcnow(),` → `utcnow()`
- Modify: `src/backend/modules/model_selector.py` (imports at `:16`): 14 sites at `:284,:291,:292,:322,:323,:331,:332,:333,:695,:705,:718,:805,:806,:818` (each +18 since P1) — `updated_at`/`created_at`/`last_detection_at`/`started_at`/`completed_at` assignments and kwargs, all `datetime.utcnow()` → `utcnow()`.

- [ ] **Step 1:** Add `from core.time import utcnow` to both files.
- [ ] **Step 2:** Apply all replacements; verify `grep -n "datetime.utcnow" src/backend/modules/model_selector.py src/backend/modules/hardware_detection.py` → empty.
- [ ] **Step 3:** Run: `cd src/backend && python -m pytest tests/ -k "hardware or detection or model_selector or download" -q` — expect PASS.
- [ ] **Step 4:** Commit: `git add src/backend/modules/hardware_detection.py src/backend/modules/model_selector.py && git commit -m "fix(modules): use core.time.utcnow in hardware detection and model selector"`

---

### Task 12: `tests/` cleanup — 7 files, 18 sites (consistency, not gated)

The lint gate (Task 13) excludes `src/backend/tests/` (matching bandit's `-x src/backend/tests/` precedent, and because `test_profile_recovery.py` legitimately contains the literal string in a source assertion). Migrate anyway for consistency — same import + swap. Compliant prior art: `tests/test_chat_sessions.py:24-26` and `tests/test_rl_feedback.py:34-36` already wrap `core.time.utcnow` in `_utcnow()`.

**Files:**
- `tests/agent/conftest.py:95,129,193,194,225`
- `tests/agent/test_agentic_queries.py:34`
- `tests/agent/test_s2_loop.py:16`
- `tests/test_documents_api.py:117,282,325,363,413,458`
- `tests/test_export_api.py:323,346`
- `tests/test_memory_crud.py:66`
- `tests/test_notification_scheduler_wiring.py:262,300` (added by P2)

- [ ] **Step 1:** Add `from core.time import utcnow` per file; replace all 18 `datetime.utcnow()` with `utcnow()`. Delete the now-unused `from datetime import datetime` at `tests/test_memory_crud.py:10` and `tests/test_notification_scheduler_wiring.py:14` (check with `grep -n "datetime"` first). Do not touch `tests/test_profile_recovery.py:344,350`: those are string literals in a source assertion.
- [ ] **Step 2:** Run: `cd src/backend && python -m pytest tests/agent/ tests/test_documents_api.py tests/test_export_api.py tests/test_memory_crud.py tests/test_notification_scheduler_wiring.py -q` — expect PASS.
- [ ] **Step 3:** Commit: `git add src/backend/tests/ && git commit -m "test: use core.time.utcnow in remaining test helpers"`

---

### Task 12b: TIME-03 — the badge timestamp (owner row P5-SCOPE; test first)

Owner, verbatim: "P5 also converts the badge timestamp, accepting a change in the medications API date string. Needs a frontend check."

**What changes.** `modules/badge_evaluator.py:84` `now = datetime.now(dt_timezone.utc)` → `now = utcnow()` (add `from core.time import utcnow`; `dt_timezone` stays imported, `_to_local_date` uses it at `:54`).

**Readers and writers of that value (traced 2026-10-08 @ `777adf5`):**

| Use | Line | Effect of a naive value |
|---|---|---|
| `today = as_of_date or _to_local_date(now, tz)` | `badge_evaluator.py:86` | none: `_to_local_date` treats a naive value as UTC (`:53-54`) |
| `BadgeEvalResult(earned_at=now)` | `:101` | carries the naive value |
| `EarnedBadge(earned_at=…)` | `:157-163` | the column is naive `DateTime` (`models/gamification.py:64-68`; migration `003_gamification_voice_settings.py:70`). SQLite stored the aware value without its offset already, so the stored text is the same |
| `BadgeInfo.from_result` → `earned_at=badge.earned_at.isoformat()` | `api/medications.py:285` | **the accepted change:** the string loses `+00:00` |
| comparisons | none | `now` is compared with nothing; no naive/aware comparison is created |

`api/gamification.py:102` already returns the naive form for the same badge read back from the database, so after this task the two endpoints agree.

**Frontend check (required by the owner).** `BadgeInfo.earned_at` (`src/frontend/src/services/types.ts:454`) has no reader: `grep -rn "earned_at" src/frontend/src` finds only `types.ts:454`, `:469` and `components/medication-coach/AchievementsWidget.tsx:43,45`, and the widget renders `BadgeStatus` from `GET /gamification/badges`, not the dose-log response. `BadgeToast.tsx` shows name and description only. So no rendered date changes. Run the frontend suite on Windows anyway and record the result: `npm ci; npx vitest run` (195 passed in 34 files before this plan).

**Pre-existing, not changed here (open item for the owner):** `AchievementsWidget.tsx:45` calls `new Date(badge.earned_at)` on a string with no offset, which browsers read as local time, so a badge earned near midnight UTC can show the neighbouring day. That string was already naive before this plan. If the frontend check finds any reader of the dose-log `earned_at`, STOP and report.

**Files:**
- Modify: `src/backend/modules/badge_evaluator.py`
- Test: `src/backend/tests/test_time_source.py` (HC-TIME-006), `src/backend/tests/test_medications_dose_logging.py` (HC-TIME-007)

- [ ] **Step 1 (RED):** add two tests.
  - `test_hc_time_006_badge_earned_at_is_naive_utc` in `tests/test_time_source.py`: call `evaluate_badges_after_dose` so that `first-log` is awarded (one dose, a `db` whose `add` records its argument); assert every returned `earned_at.tzinfo is None`, every recorded `EarnedBadge.earned_at.tzinfo is None`, and the value is within 2 seconds of `utcnow()`.
  - `test_hc_time_007_dose_log_badge_string_has_no_offset` in `tests/test_medications_dose_logging.py`, using that file's existing `log_dose` harness: assert `response.newly_earned_badges[0].earned_at` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{6})?$`.
  - Run both: expected **FAIL** before the change (the value is aware; the string ends in `+00:00`). Paste the failure.
- [ ] **Step 2 (GREEN):** apply the one-line change and the import. Run: `cd src/backend && python -m pytest tests/test_time_source.py tests/test_medications_dose_logging.py tests/test_gamification_api.py tests/test_gamification_models.py -q` and `python -m pytest tests/ -k "badge or gamif or streak or dose" -q` — expect PASS.
- [ ] **Step 3:** Commit (collected +2: rewrite the slots to the measured number):

```bash
git add src/backend/modules/badge_evaluator.py src/backend/tests/test_time_source.py src/backend/tests/test_medications_dose_logging.py CLAUDE.md AGENT.md
git commit -m "fix(gamification): store and return the badge timestamp as naive UTC"
```

---

### Task 13: Lint gate — `scripts/time_source_lint.py` + CI step

**Files:**
- Create: `scripts/time_source_lint.py` (repo-root `scripts/`, alongside `docs_lint.py`/`feature_list_lint.py` — NOT `src/backend/scripts/`)
- Modify: `.github/workflows/ci.yml` — add one step to the `docs-lint` job after the `Repo hygiene check` step (`ci.yml:30-31`). That job already has Python and zero install steps — the right home for a stdlib gate.

Design choices (state in review; revised 2026-10-08): the gate is an **AST scan** for attribute references `datetime.utcnow` / `datetime.utcfromtimestamp` (also `datetime.datetime.utcnow`). It has no trailing-call requirement, so it also catches `default=datetime.utcnow` reference-form reintroduction; `utcfromtimestamp` is the same deprecation class and `core.time.utcfromtimestamp` exists. An AST scan ignores comments and docstrings, so the docstring at `src/backend/core/time.py:18` (which names the deprecated helper) is not a violation and `core/time.py` needs no exclusion. Scan root is `src/backend/` **excluding** `tests/` and `__pycache__` (only the top-level `src/backend/tests/` is excluded; `__pycache__` at any depth; the name of a parent directory cannot switch the scan off) — bandit already excludes tests in this CI file, and `test_profile_recovery.py:344,350` legitimately contains the literal string in a source assertion. A file that does not parse is reported as a violation. The script exits 1 when the scan root is missing or when it scanned no file, so it cannot pass without checking anything (security review, 2026-10-08; the listing below is the committed script). Known limit: an aliased import (`from datetime import datetime as dt; dt.utcnow()`) is not seen. Ruff was rejected as the gate mechanism: it is configured (`pyproject.toml` `select = ["F","I","W"]`) but **ungated** (audit §13), and enabling `DTZ` would also flag the out-of-scope `datetime.now()` sites in `gamification.py`/`source_authority.py`.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Fail on deprecated datetime timestamp helpers in src/backend product code.

CLAUDE.md hard invariant: core.time.utcnow is the single timestamp helper
(core.time.utcfromtimestamp for POSIX timestamps). datetime.utcnow() and
datetime.utcfromtimestamp() are also deprecated from Python 3.12.

AST scan: only executable references count, so comments and docstrings that
name the deprecated helpers (core/time.py does) are not violations.

Scans src/backend/ excluding tests/ (which legitimately mention the literal
string in source assertions, e.g. test_hc_recov_025), matching the bandit
-x src/backend/tests/ precedent in ci.yml.

Usage: python3 scripts/time_source_lint.py
Exit 0 when clean; exit 1 listing file:line for each violation.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO_ROOT / "src" / "backend"
EXCLUDE_DIR_NAMES = {"tests", "__pycache__"}
BANNED_ATTRS = {"utcnow", "utcfromtimestamp"}


def _is_datetime(node: ast.expr) -> bool:
    """True for the names `datetime` and `<anything>.datetime`."""
    if isinstance(node, ast.Name):
        return node.id == "datetime"
    return isinstance(node, ast.Attribute) and node.attr == "datetime"


def _violations_in(path: Path) -> list[str]:
    rel = path.relative_to(REPO_ROOT)
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{rel}:{exc.lineno}: cannot parse ({exc.msg})"]
    lines = source.splitlines()
    return [
        f"{rel}:{node.lineno}: {lines[node.lineno - 1].strip()}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in BANNED_ATTRS
        and _is_datetime(node.value)
    ]


def _is_excluded(path: Path) -> bool:
    """Skip the top-level tests/ dir and __pycache__ at any depth."""
    parts = path.relative_to(SCAN_ROOT).parts
    return parts[0] == "tests" or "__pycache__" in parts


def find_violations() -> tuple[list[str], int]:
    """Return (violations, number of files scanned)."""
    violations: list[str] = []
    scanned = 0
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        if _is_excluded(path):
            continue
        scanned += 1
        violations.extend(sorted(set(_violations_in(path))))
    return violations, scanned


def main() -> int:
    if not SCAN_ROOT.is_dir():
        print(f"time_source_lint ERROR: scan root {SCAN_ROOT} is not a directory.")
        return 1
    violations, scanned = find_violations()
    if scanned == 0:
        print(f"time_source_lint ERROR: scanned 0 .py files under {SCAN_ROOT}.")
        return 1
    if violations:
        print("Deprecated datetime timestamp helpers found "
              "(use core.time.utcnow / core.time.utcfromtimestamp):")
        for line in violations:
            print(f"  {line}")
        return 1
    print("time_source_lint passed: no datetime.utcnow/utcfromtimestamp "
          f"in {scanned} src/backend product files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Prove the gate fails on a planted violation**

Run from the worktree root (all paths are relative to it):

```bash
printf 'from datetime import datetime\nx = datetime.utcnow()\n' > src/backend/_planted_lint_probe.py
python3 scripts/time_source_lint.py; echo "exit=$?"     # expected: exit=1, lists src/backend/_planted_lint_probe.py:2
rm src/backend/_planted_lint_probe.py
python3 scripts/time_source_lint.py; echo "exit=$?"     # expected: exit=0 and the pass line
```

Both halves are required evidence: the clean tree exits 0 (the docstring at `core/time.py:18` is not reported), and a seeded `datetime.utcnow()` exits 1. Run the clean-tree half only after Tasks 1-12b are done; before that the lint lists the remaining sites.

- [ ] **Step 3: Add the CI step** to the `docs-lint` job in `.github/workflows/ci.yml`, as the last step of the job, after `Repo hygiene check` (`ci.yml:30-31`). The name is quoted because it contains `: `:

```yaml
      - name: "Lint: deprecated datetime helpers banned in backend"
        run: python3 scripts/time_source_lint.py
```

Check the file still parses: `~/venvs/asclexis-311/bin/python -c "import yaml; d = yaml.safe_load(open('.github/workflows/ci.yml')); print([s.get('name') for s in d['jobs']['docs-lint']['steps']])"` — the new name must be the last entry.

- [ ] **Step 4: Commit**

```bash
git add scripts/time_source_lint.py .github/workflows/ci.yml
git commit -m "ci: gate src/backend on core.time.utcnow helper"
```

Note for reviewers: running the gate mid-migration doubles as a progress checklist — it prints every remaining violation.

---

### Task 14: Final verification

- [ ] **Step 1:** `find src/backend -name __pycache__ -type d -exec rm -rf {} +` (WSL/9p stale-bytecode guard).
- [ ] **Step 2:** three greps, each with its exact expected output:
  - `grep -rn "datetime\.utcnow" src/backend --include="*.py" | grep -v "src/backend/tests/" | wc -l` → **0** (was 101).
  - `grep -rn "datetime\.utcfromtimestamp" src/backend --include="*.py" | grep -v "src/backend/tests/"` → **exactly one line**, the docstring at `src/backend/core/time.py:18`. It is prose, not a call; the AST lint does not report it.
  - `grep -rn "datetime\.utcnow" src/backend/tests --include="*.py"` → **exactly three lines**: `tests/test_profile_recovery.py:344` and `:350` (string literals in a source assertion) and `tests/test_time_source.py:4` (the docstring of the Task 0 test, which names the migration). Corrected 2026-10-08 after execution: the first amendment said two and forgot the docstring this plan itself adds.
- [ ] **Step 3:** `python3 scripts/time_source_lint.py` → exit 0.
- [ ] **Step 4:** `cd src/backend && HF_HUB_OFFLINE=1 flock /tmp/claude-1000/hc-pytest.lock ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q` → **the start-of-plan collected count plus any tests this plan added** (corrected 2026-09-27; was "1245 collected"), no new failures (env-only `test_api_rag_index_002b` failure is pre-existing and not yours).
- [ ] **Step 5:** `cd src/backend && python -c "from main import app"` → boots clean. Then, from the repo root, `timeout 600 python3 scripts/agent_eval_gate.py; echo "rc=$?"`: record the verdict and the exit code (GATE-14; this plan edits three files under `modules/agent/`).
- [ ] **Step 6:** Log the session in `docs/features/TASK_LIST.md` Session Notes; re-read `docs/agentic/recurring-failures.md` — if any listed mode recurred (e.g. a green suite masking a path the tests never exercise), record it in the same commit.
- [ ] **Step 7:** Commit: `git commit -m "docs: log utcnow migration session"` (or fold into the last code commit).

---

## Out of scope (recorded, not migrated here)

- `api/gamification.py:148` — aware `datetime.now(dt_timezone.utc)`, used only for `.astimezone(...)`; a naive value there would be read as local time, so it stays aware. (`modules/badge_evaluator.py:84` was on this line until 2026-10-08; it is now Task 12b, owner row P5-SCOPE.)
- The other aware sites: `core/auth.py:73,144,207`, `core/security.py:136`, `core/token_revocation.py:51` (auth, ask-first; token expiry compares aware with aware), `api/export.py:949,1005`, `api/model_settings.py:343`, `api/medications.py:84`. If a task seems to need one of them, STOP and report.
- `modules/source_authority.py:216` — `datetime.now().year` uses local time, not UTC.
- `core/time.py` itself — defines the helpers; not a violation. Its docstring at `:18` names the deprecated helper in prose; the AST lint ignores it.

## Execution record (2026-10-08, Wave 4 L1-A)

Executed on `fix/p5-utcnow-migration` from `origin/main@777adf5`; Tasks 0-13 by an L2 implementer, Task 14 by the L1 orchestrator. Commands and outputs are in [`waves/wave-4-L1-A.md`](../waves/wave-4-L1-A.md).

- Product lines with `datetime.utcnow`: 101 → 0. Lint: clean tree exit 0 (173 files scanned); seeded file exit 1; one reverted swap (`models/audit.py`) exit 1; an empty scan root exit 1.
- Collected: 1370 → 1377 (+7: HC-TIME-001…007). Full suite: `1377 passed`.
- One response string changed, as accepted under P5-SCOPE: the dose-log `earned_at`.
- `api/profiles.py`: 7 changed lines (6 swaps, 1 deleted import).
- Deviation from the plan text: Task 14 Step 2's third grep prints three lines, not two (corrected above).
