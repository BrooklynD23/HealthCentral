# WEAR-02 — Data Contract, Profile Migration and Shared Registries — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0 and the gates in Task 0)
**Base measured:** `origin/main` @ `8234990`. Every `file:line` below was re-read on the plan worktree (`a985390`, docs-only on top of that base) on 2026-10-13.
**Refresh trigger:** any profile migration merges (P6 `013`, G-C1 `014`, AUDIT-ORDER `015`, GAM2 2b); any edit to `core/audit.py`, `core/profile_database.py`, `models/__init__.py`, `api/profiles.py`; the owner answers D1; OM-1 notes change a metric or unit.
**Program:** [00-program](2026-10-13-wearables-00-program.md) A2, A3, A5, A5b, A8, A11, A12
**Depends on:** program M0. Runs parallel to WEAR-01 and WEAR-03 (disjoint files except `core/config.py`, which this plan does not touch).
**Owner decisions it depends on (resolved):** WEAR-D1 (owner, 2026-10-14; commit `c53ba44`, PR #92): "(b) Hash + extracted rows only (Recommended)" — no raw-ZIP column, no vault path column. WEAR-D4 (owner, 2026-10-14; commit `c53ba44`, PR #92): "(a) Per-path cap; approve both diffs as planned (Recommended)" — the `core/audit.py` vocabulary + `log_wearable_event` diff in this plan is approved **exactly as written**; any deviation during implementation needs a new owner question.
**Size target:** M, about 350 lines of diff (about 150 product, 200 test). If the audit vocabulary plus models push past 400, split the audit part into WEAR-02b and say so in the PR.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, then superpowers:subagent-driven-development. Domain skill for backend work: `asclexis-backend`. Steps use `- [ ]` checkboxes.

**Goal:** the three wearable tables exist (empty, flag-independent), a pure contract validator exists for WEAR-06 to call before any write, shared registries (create_all list, synthetic reset, audit vocabulary) are owned here once, and a static guard proves no existing read path can reach the new table.

## 1. Scope

**This plan does:**
- Add `models/wearable.py` (3 models), register them, add one profile migration.
- Add pure `modules/wearables/contract.py::validate_summary`.
- Reserve the whole audit vocabulary for the wearables module in `core/audit.py`.
- Add the 3 models to the synthetic-reset tuple, with a reset test.
- Add the static import guard (program A3) with an explicit allow-list.
- Update the 4 head-literal assertions in 3 existing test files.

**This plan does NOT license:**
- `wearables_min_days` (D3): WEAR-07 adds it to `core/config.py`.
- Any parser, route or aggregation code (WEAR-03..07).
- Any change to `api/observations.py`, `modules/rag.py`, `modules/timeline.py`, `api/export.py` (the guard only reads them).
- Any ask-first file (section 4).
- Writing rows in `observations` or `documents` for wearable data (A2, A3).
- Turning on `PRAGMA foreign_keys` (P6 owns that; here every delete is explicit).

## 2. Evidence

| Fact | Path:line @8234990 |
|---|---|
| Profile head is `012_pinboards`, `down_revision = "011_care_plan_tasks"` | `src/backend/migrations/profile/versions/012_pinboards.py:13-14` |
| Newest migration file on disk is 012 | `ls src/backend/migrations/profile/versions` (last entry `012_pinboards.py`) |
| Migration style: `op.create_table`, `sa.ForeignKey(..., ondelete="CASCADE")`, `op.create_index`, `downgrade` drops indexes then tables | `src/backend/migrations/profile/versions/012_pinboards.py:21-47` |
| Model style: `ProfileDatabaseBase`, `Mapped`/`mapped_column`, `default=lambda: str(uuid.uuid4())`, `default=utcnow`, `UniqueConstraint` | `src/backend/models/pinboard.py:1-45` |
| `ProfileDatabaseBase` | `src/backend/core/profile_database.py:45` |
| create_all import list (test-only schema builder): `from models import (` | `src/backend/core/profile_database.py:409-417` |
| Models are re-exported and listed in `__all__` | `src/backend/models/__init__.py:63` (last import), `:103-105` (`__all__` tail) |
| Synthetic reset deletes listed models, children before parents; list ends at `EarnedBadge` | `src/backend/api/profiles.py:498-515` |
| Reset route requires session name starting `Playwright E2E`, 404 in production | `src/backend/api/profiles.py:81,476-488` |
| Reset imports come from one `from models import (` block | `src/backend/api/profiles.py:51-66` |
| FK cascade is not enforced: no `PRAGMA foreign_keys`; delete code is explicit | `src/backend/api/profiles.py:939-942` |
| `ALLOWED_ACTIONS` closed set; unlisted action is replaced by the event type | `src/backend/core/audit.py:36-48,181` |
| `STRING_DETAIL_KEYS` lacks `import_id`, `vendor`, `metric` | `src/backend/core/audit.py:69-76` |
| `ALLOWED_DETAIL_KEYS` count/boolean groups; none of the wearable counts present | `src/backend/core/audit.py:89-109` |
| Scrubber keeps a string only if key is in `STRING_DETAIL_KEYS` and value matches `^[A-Za-z0-9_.:/\-]{1,64}$` | `src/backend/core/audit.py:112,139-144` |
| `audit_and_commit` is the fail-closed writer | `src/backend/core/audit.py:474` |
| Existing poisoned-details test to mirror (HC-AUD-001) | `src/backend/tests/test_audit_phi_minimization.py:58-78` (test at `:62`) |
| Up/down/up migration test pattern | `src/backend/tests/test_care_tasks.py:795-826` |
| Head literals to update | `tests/test_care_tasks.py:809,825`; `tests/test_profile_migrations_sqlcipher_fallback.py:41`; `tests/test_source_spans.py:313` |
| `tests/test_pinboards.py:268-270` reads the 012 file text only; not a head literal, leave alone | `src/backend/tests/test_pinboards.py:268-270` |
| `vault` fixture pattern: in-memory aiosqlite plus `ProfileDatabaseBase.metadata.create_all` | `src/backend/tests/test_audit_order.py:88-98` |
| Time helper | `src/backend/core/time.py:9` (`utcnow`) |
| Skip-reason shape and field cap precedent | `src/backend/modules/import_structured.py:41,55-59` (`_MAX_FIELD_LEN = 2000`, `_cap`) |
| Files the guard must watch import nothing wearable today | `src/backend/api/observations.py`, `modules/rag.py`, `modules/timeline.py`, `api/export.py` (guard test proves it) |
| `_fetch_observations`, trends and RAG do not filter `user_verified` (why the separate table is the exclusion) | `src/backend/api/export.py:131`; `src/backend/api/observations.py:512,532-535`; `src/backend/modules/rag.py:272-456` |
| Baseline collected | `CLAUDE.md:30` (1487) |


INFERRED: the migration number. Task 0 reads the real head; this plan writes `0NN`.

## 3. Files to touch

| Path | New/edit | Why | Approx lines |
|---|---|---|---|
| `src/backend/models/wearable.py` | new | `WearableImport`, `WearableDailyMetric`, `WearableMetricReview` | +85 |
| `src/backend/models/__init__.py` | edit | import and `__all__` entries | +5 |
| `src/backend/core/profile_database.py` | edit | add `wearable` to the `:409-417` import list | +1 |
| `src/backend/migrations/profile/versions/0NN_wearables.py` | new | 3 tables, unique constraint, indexes | +75 |
| `src/backend/modules/wearables/__init__.py` | new | package marker | +1 |
| `src/backend/modules/wearables/contract.py` | new | `validate_summary`, enums, caps | +90 |
| `src/backend/api/profiles.py` | edit | import 3 models; add to reset tuple (children first) | +6 |
| `src/backend/core/audit.py` | edit | actions, string keys, count keys | +12 |
| `src/backend/tests/test_wearables_contract.py` | new | HC-WRB-201..206 | +90 |
| `src/backend/tests/test_wearables_schema.py` | new | HC-WRB-207..211 | +110 |
| `src/backend/tests/test_wearables_guard.py` | new | HC-WRB-212..215 | +70 |
| 3 existing test files | edit | head literals | +4 / -4 |
| `CLAUDE.md`, `AGENT.md` | edit | collected-count slots | +2 |

## 4. Ask-first files touched

None of the CLAUDE.md ask-first list (`interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, `core/auth.py`, `core/security.py`, encryption). Two review gates apply instead:
- `core/audit.py` is guarded by the AUDIT-ORDER owner sign-off on that file. This plan only adds vocabulary (no change to scrub logic or write order). **security-reviewer pass is required on this diff** (program A12). If the owner reads the AUDIT-ORDER ask-first as covering any `core/audit.py` edit, this part waits for that gate (Q2 in the report).
- Migrations are not ask-first, but they are the collision point (section 6).

## 5. Data contract

Profile DB only. One migration. All dates are plain `Date` (the patient's local day from the record's own offset, program A6). All timestamps are naive UTC from `core.time.utcnow`.

### `wearable_imports`

| Column | Type | Notes |
|---|---|---|
| `id` | String(36) PK | uuid4 |
| `profile_id` | String(36), index | from the session, never from the file |
| `source_vendor` | String(20) | enum `apple`, `garmin` |
| `schema_version` | String(8) | `"wdm-1"` |
| `content_hash` | String(64) | sha256 hex of the uploaded bytes. UNIQUE (`profile_id`, `content_hash`) |
| `filename` | String(255) | capped; app-only, never in the packet, never in audit |
| `imported_at` | DateTime | `utcnow` |
| `records_read`, `records_skipped`, `days_covered` | Integer | counts |
| `skipped_reasons_json` | Text | JSON map reason to count, counts only |
| `first_local_date`, `last_local_date` | Date | |

### `wearable_daily_metrics`

| Column | Type | Notes |
|---|---|---|
| `id` | String(36) PK | |
| `profile_id` | String(36), index | |
| `import_id` | String(36) FK `wearable_imports.id` ON DELETE CASCADE | declared only; not enforced (A2) |
| `source_vendor` | String(20) | |
| `metric` | String(40) | enum `resting_heart_rate`, `sleep_asleep_minutes`, `step_count` |
| `local_date` | Date | |
| `value` | Float | the one daily value (A5) |
| `unit` | String(16) | fixed per metric: `bpm`, `min`, `count` |
| `utc_offset_minutes` | Integer | |
| `tz_changed` | Boolean | more than one offset that day |
| `n_records` | Integer | |
| `device_class` | String(20) | enum `apple_watch`, `iphone`, `garmin_device`, `other` |
| `source_name` | String(255) | capped; app-only (A7) |
| `duplicate_sources` | Integer | other sources seen that day; never summed |
| `created_at` | DateTime | `utcnow` |

UNIQUE (`import_id`, `metric`, `local_date`). Rows are immutable per import (A5b).

### `wearable_metric_reviews`

Rows are created by WEAR-06's import route (one stub per metric that has rows), not by WEAR-02. PK (`import_id` FK cascade, `metric`); `patient_reviewed_at` DateTime nullable; `include_in_packet` Boolean, default False. "Reviewed" never means "verified" (A4).

### Parser output accepted by `validate_summary(summary: dict) -> list[str]`

`{schema:"hc.wearable-summary", version:"1.0", rows:[...], records_read:int, skipped:{reason:int}}`; each row has the 11 fields of `wearable_daily_metrics` that a parser sets (`source_vendor, metric, local_date, value, unit, utc_offset_minutes, tz_changed, n_records, device_class, source_name, duplicate_sources`).

Validator rules, closed and static:
- `schema == "hc.wearable-summary"` and `version == "1.0"`.
- `source_vendor`, `metric`, `device_class` in their enums; `unit` equals the fixed unit for the metric.
- `local_date` is `YYYY-MM-DD`, parsed with `date.fromisoformat` and rejected if not a real date; no time part.
- `value` is `int` or `float`, **not `bool`**, finite, and `>= 0`. No upper bound (a bound is a threshold; none is licensed).
- `utc_offset_minutes` int in `[-720, 840]`; `n_records` int `>= 1`; `duplicate_sources` int `>= 0`; `tz_changed` is a real `bool`.
- `source_name` is `str` with `len <= 255`; `len(rows) <= MAX_ROWS` (placeholder 100000, 3 metrics x about 33 years; owner may resize from OM-1).
- No duplicate (`source_vendor`, `metric`, `local_date`) inside one summary (the DB unique key would fail late).
- `skipped` is `{str: int >= 0}` with each key `len <= 64`.
- **Errors are static codes with a row index** (`"row 3: metric_invalid"`). The function never echoes an input value, so a 422 body or log line cannot leak a name or number from the file.
- It imports only the standard library (A8). It does not call `core.*` or `models.*`.

### Audit vocabulary reserved once (A12)

| Kind | Additions |
|---|---|
| `ALLOWED_ACTIONS` | `Imported wearable data`, `Reviewed wearable data`, `Deleted wearable import`, `Viewed wearable metrics` |
| `STRING_DETAIL_KEYS` | `import_id`, `vendor` (not `metric`: which metric a patient reviewed stays out of the master audit log, Codex plans R2-6) |
| `ALLOWED_DETAIL_KEYS` (ints) | `rows_written`, `records_read`, `records_skipped`, `days_covered`, `metrics_reviewed`, `metrics_included` |

Plus helper `log_wearable_event(db, event, profile_id, details)` in `core/audit.py`, same pattern as `log_document_event` (`src/backend/core/audit.py:305-312`); it passes `details` through `create_audit_log` so the scrubber still applies. The four actions cover import, review, delete and metrics view (list, summary and trends routes). Test HC-WRB-216 (guard file): `log_wearable_event` with a poisoned details dict writes a row whose scrubbed details keep only the reserved keys. No filename, source name, value or date key is added. `import_id` is a uuid and matches the scrubber regex.

## 6. Migration numbering and coordination

| Claimant | Number | Source |
|---|---|---|
| P6 FK cascade alignment | `013_fk_cascade_alignment` | `docs/capstone-report/implementation-program.md:343` |
| G-C1 export artifacts | `014_export_artifacts` | `docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md:195` |
| AUDIT-ORDER outbox | `015_audit_outbox` | `docs/plans/2026-10-09-AUDIT-ORDER.md:249` |
| GAM2 task 2b | unnumbered; "whichever lands second renumbers" | `docs/capstone-report/owner-decisions-2026-09-27.md:134` |
| WEAR-02 | head + 1 at merge | this plan |

Rules: Task 0 reads the head on `origin/main` the same day; the file name and `revision` use the next free number; `down_revision` is the real head; the chain stays linear. If another migration merges while this PR is open, rebase, renumber file, `revision`, `down_revision`, the 3 head literals and `HC-WRB-208`, then re-run the round-trip test. The wearable tables do not depend on P6 (explicit deletes), so there is no ordering constraint, only the renumber.

## 7. TDD test list

Test IDs `HC-WRB-2NN`. Route tests go through HTTP; isolation and absence tests assert on returned rows and values.

| ID | File | Assertion | RED reason |
|---|---|---|---|
| HC-WRB-201 | contract | valid one-row-per-metric summary (3 rows, both vendors in separate summaries) returns `[]` | module missing |
| HC-WRB-202 | contract | parametrized: unknown `metric`, `source_vendor`, `device_class`; `unit` wrong for metric (`step_count` with `bpm`); wrong `schema`/`version` each give a non-empty list | module missing |
| HC-WRB-203 | contract | `"2026-02-30"`, `"2026-07-01T10:00:00"`, `"07/01/2026"` rejected; `nan`, `inf`, `-1`, `True` as value rejected; `0` and `0.0` accepted | module missing |
| HC-WRB-204 | contract | `source_name` of 256 chars, offset `841`, `n_records` 0, `tz_changed` as `1`, duplicate key in two rows, 100001 rows each rejected | module missing |
| HC-WRB-205 | contract | with `source_name="Jane's Apple Watch"` and `value=-5` in the input, no returned error string contains `Jane`, `Apple` or `5` beyond the row index (assert `all(re.fullmatch(r"row \d+: [a-z_]+|[a-z_]+", e) for e in errors)`) | module missing |
| HC-WRB-206 | contract | AST of `contract.py` imports only names in `sys.stdlib_module_names` (A8) | module missing |
| HC-WRB-207 | schema | `ProfileDatabaseBase.metadata.create_all` on in-memory aiosqlite creates the 3 tables; inserting a second (`import_id`, `metric`, `local_date`) raises `IntegrityError`; a second (`profile_id`, `content_hash`) raises `IntegrityError`; same hash for profile B succeeds | models missing |
| HC-WRB-208 | schema | on a real tmp vault (pattern `test_care_tasks.py:795-826`): upgrade to head creates the 3 tables and `get_profile_current_revision` equals `0NN_wearables`; downgrade to the previous head removes them; upgrade again restores them | migration missing |
| HC-WRB-209 | schema | after migration upgrade, `PRAGMA table_info` column names equal `Model.__table__.columns.keys()` for each of the 3 tables (model and migration cannot drift) | migration missing |
| HC-WRB-210 | schema | reset: insert import, metric rows and review rows for a profile; override `require_auth` with a session named `Playwright E2E x`; `POST /profiles/test/reset` via `route_client(profiles_router, "/profiles")` returns 204; `select count()` on each of the 3 tables is `0`. Order matters: with the tuple order reversed this fails on a foreign-key-enabled connection (see break B3) | models not in tuple: rows remain (assert on counts, not on a 204 alone) |
| HC-WRB-211 | schema | `models` package exports `WearableImport`, `WearableDailyMetric`, `WearableMetricReview`; `core.profile_database` import list includes `wearable` (source check of `:409-417` region) | missing |
| HC-WRB-212 | guard | `_scrub_details({"import_id": uuid, "vendor": "apple", "rows_written": 3, "records_read": 9, "records_skipped": 1, "days_covered": 2, "metrics_reviewed": 3, "metrics_included": 1})` keeps all 8 keys, unchanged; the same call with an added `"metric": "step_count"` drops `metric` (minimisation, Codex plans R2-6) | keys dropped today (`_scrubbed` set) |
| HC-WRB-213 | guard | same call plus `filename`, `source_name`, `value`, `local_date`, and `vendor="Jane's Apple Watch"` (has spaces): the 4 extra keys dropped, the spaced vendor dropped, counts kept; `_scrub_action` keeps all 4 new action strings | keys/actions missing |
| HC-WRB-214 | guard | static import guard: for each file in the watch list, `find_wearable_imports(source) == allowed[file]`, where `allowed = {"api/export.py": set(), ...}` and every other file maps to `set()`. Detects `import models.wearable`, `from models.wearable import X`, `from models import WearableImport` (any of the 3 names), `from . import wearable`, and `from models import *`. Self-test in the same file: a literal source string that imports the model makes the checker return a non-empty set (the guard can fail) | module absent |
| HC-WRB-215 | guard | watch list is exactly `api/observations.py`, `modules/rag.py`, `modules/timeline.py`, `api/export.py`; each file exists (a rename must fail the test, not silently shrink it) | file list absent |
| HC-WRB-216 | guard | `log_wearable_event` with a poisoned details dict writes a row whose scrubbed details keep only the reserved keys; **and** HC-AUD-004 (`tests/test_audit_phi_minimization.py:140-185`) gains a `log_wearable_event` row whose 4 events all map to registered actions | helper missing / unregistered action |

Research mapping: covers research HC-WRB-014 in part (schema and cross-profile uniqueness in HC-WRB-207; the HTTP isolation half is WEAR-06/07); supports HC-WRB-015 (count). WEAR-09 later changes `allowed["api/export.py"]` to `{"WearableDailyMetric", "WearableMetricReview", "WearableImport"}`-only-for-the-packet-path: it must edit the allow-list in the same PR and add a second test that `_fetch_observations` source does not mention the wearable names. That edit is WEAR-09's, not this plan's.

## 8. Tasks

### Task 0 — gates

- [ ] 0.1 `git fetch origin && git merge-base --is-ancestor 8234990 origin/main`. Exit 0.
- [ ] 0.2 Program M0 met; plan set approved; `docs/plans/2026-10-13-wearables-02-contract-migration.md` on the branch.
- [ ] 0.3 Read the head: `ls src/backend/migrations/profile/versions | sort | tail -3` and `grep -n "^revision\|^down_revision" ` on the newest file. Choose `0NN = head + 1`. Write it at the top of the PR description. If any of 013/014/015 is open, check whether it renumbered.
- [ ] 0.4 Rows WEAR-D1 and WEAR-D4 are on `origin/main` (PR #92). The `core/audit.py` diff written matches this plan exactly; any difference → STOP and ask the owner.
- [ ] 0.5 `git grep -n "wearable" src/backend` is empty apart from WEAR-01 files. Start count N: `python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1`.
- [ ] 0.6 Branch `feat/wear-02-contract-migration`.

### Task 1 — RED

- [ ] 1.1 Write the 3 test files (HC-WRB-201..215). Build `contract` fixtures as small dict literals; build the reset fixture with the `vault` pattern (`test_audit_order.py:88-98`).
- [ ] 1.2 Run: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_contract.py tests/test_wearables_schema.py tests/test_wearables_guard.py -p no:cacheprovider -q`
- [ ] 1.3 Expect failures listed in the RED column (`ModuleNotFoundError`, `ImportError`, missing tables, `_scrubbed` key). Paste the summary line into the PR. 215 minus tests that already pass (none expected).

### Task 2 — GREEN: contract

- [ ] 2.1 `modules/wearables/contract.py` with enums as tuples, `UNIT_FOR_METRIC` dict, `MAX_ROWS`, `validate_summary`. Accumulate error codes; return the list; never raise on bad input types.
- [ ] 2.2 Run `tests/test_wearables_contract.py`: expect 6 passed.

### Task 3 — GREEN: models, migration, registries

- [ ] 3.1 `models/wearable.py` per section 5 (style of `models/pinboard.py`). Add the unique constraints and indexes by name (`uq_wearable_import_hash`, `uq_wearable_metric_day`).
- [ ] 3.2 `models/__init__.py`: import and `__all__`. `core/profile_database.py:409-417`: add `wearable`.
- [ ] 3.3 `migrations/profile/versions/0NN_wearables.py` mirroring `012_pinboards.py`; `downgrade` drops indexes, then reviews, metrics, imports (children first).
- [ ] 3.4 Update the head literals: `test_care_tasks.py:809,825`, `test_profile_migrations_sqlcipher_fallback.py:41`, `test_source_spans.py:313` (the comment at `:310` mentions 012; refresh it). Do not edit the downgrade targets.
- [ ] 3.5 `api/profiles.py`: add the 3 names to the `from models import (` block and to the reset tuple **before** `Embedding` (reviews, metrics, imports in that order; children before parents).
- [ ] 3.6 Run `tests/test_wearables_schema.py`: expect 5 passed; then the 3 edited existing files unchanged except literals.

### Task 4 — GREEN: audit vocabulary and guard

- [ ] 4.1 `core/audit.py`: add the 4 actions to `ALLOWED_ACTIONS` (`:36-48`), the 3 string keys to `STRING_DETAIL_KEYS` (`:69-76`), the 6 count keys to the counts group in `ALLOWED_DETAIL_KEYS` (`:89-109`). No logic change.
- [ ] 4.2 Run `tests/test_audit_phi_minimization.py` (existing, must stay green) and `tests/test_wearables_guard.py`.
- [ ] 4.3 Spawn `security-reviewer` on the `core/audit.py` diff only. Paste its verdict in the PR.

### Task 5 — full suite and count

- [ ] 5.1 `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest tests/ -p no:cacheprovider -q`
- [ ] 5.2 Only `test_api_rag_index_002b` may fail (`CLAUDE.md:30-33`).
- [ ] 5.3 Collected = N + 16 (HC-WRB-201..216; parametrized cases may raise the pytest count above 16, so state the exact number from `--collect-only`). Update `CLAUDE.md:30` and `AGENT.md:76` in the same commit (SLOT-RULE). Read `docs/agentic/recurring-failures.md` before claiming done. `git diff --stat` must show `modules/redaction.py`, `modules/interpret_safety.py` untouched.

## 9. Mutation and break checks

All temporary. After each revert run `git diff --stat` and confirm only the intended files differ.

| # | Break | Expected red |
|---|---|---|
| B1 | Remove `UniqueConstraint("import_id","metric","local_date")` from the model (and migration) | HC-WRB-207 and HC-WRB-209 fail |
| B2 | In `validate_summary`, replace `math.isfinite(v)` with `True` | HC-WRB-203 fails (`nan`, `inf` accepted) |
| B3 | Put the 3 wearable models after `Document` in the reset tuple, or remove them | HC-WRB-210 fails (rows remain, or children after parents on an FK-enabled connection) |
| B4 | Add `from models import WearableImport` to `modules/timeline.py` | HC-WRB-214 fails naming that file |
| B5 | Remove `import_id` from `STRING_DETAIL_KEYS` | HC-WRB-212 fails (`_scrubbed` present) |
| B6 | In the migration change a column name | HC-WRB-209 fails |

## 10. Acceptance criteria

- The three new test files print `N passed` with the exact number from `--collect-only`; output pasted.
- Existing `test_audit_phi_minimization.py`, `test_care_tasks.py`, `test_source_spans.py`, `test_profile_migrations_sqlcipher_fallback.py`, `test_pinboards.py` green; output pasted.
- Migration round trip (HC-WRB-208) green on a tmp vault; `alembic` head equals `0NN_wearables`.
- Full suite: only the known embedding failure; collected count recorded; slots updated.
- B1-B6 each seen red and reverted.
- security-reviewer verdict on the `core/audit.py` diff is attached.
- `git diff --stat origin/main` lists exactly section 3's files.

## 11. Rollback

Revert the PR. For a database that already ran the migration, `alembic downgrade` to the previous head drops the three tables (children first); no other table is touched. Because the tables are empty until WEAR-06 and gated by the flag, an unreverted migration is harmless. If a later package merged, revert in reverse order (06 before 02).

## 12. What these tests cannot see

- **Recurring-failures #1.** HC-WRB-214 reads source text. It proves no import statement, not that a view or raw SQL never joins the table, and not that a new file (not on the watch list) reads it. The watch list is explicit on purpose; a new reader of observations must be added by whoever adds it. The self-test inside HC-WRB-214 shows the checker can fail.
- **Recurring-failures #9.** Explicit child deletes are a class rule: reset (here), delete import (WEAR-07), profile delete (the vault file goes away). This plan covers reset only. WEAR-07 must test its own delete.
- **Recurring-failures #2.** Reserving audit keys makes the scrubber keep them, but no route writes them yet; whether WEAR-06/07 pass only counts is their test.
- **Recurring-failures #4.** The count N + 16 is relative; parametrized cases change the exact figure.
- **Recurring-failures #10.** Models exist but nothing starts them: dead until WEAR-06.
- The validator proves shape, not truth. A well-formed row from a wrong parser passes (WEAR-03..05 own correctness; OM-1 owns real formats).
- The Alembic test runs with `database_encryption_required=False`; SQLCipher behaviour on a real vault is not exercised here.
- The reset test uses an in-memory DB without `PRAGMA foreign_keys`, matching production. It cannot see a future P6 that turns enforcement on.

## 13. Owner and model-machine items

None new. WEAR-D1 and WEAR-D4 are answered (2026-10-14); OW-W0 (OM-1 notes) may change enum values or units before merge.
