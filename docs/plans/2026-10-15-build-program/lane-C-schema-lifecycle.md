# Lane C: Schema and Data Lifecycle (Build Program 2026-10-15)

**Last Updated:** 2026-10-15
**Owner:** repository owner
**Status:** DESIGN. Nothing here is approved for execution. Every owner gate in the Owner gates section is **unasked** unless a signed row is quoted. No approval is recorded here.
**Base measured:** `origin/main` @ `3b2236c` (2026-10-15, worktree `hc-wave6-design`). Every `file:line` below was read at that base unless marked otherwise. Collected-count slot: `CLAUDE.md:30` says **1574 backend tests collected** (the orchestrator note said 1501; the slot wins; pytest was not run).
**Refresh Trigger:** any file added under `src/backend/migrations/profile/versions/`; a merge of P6, P7, W-2, #84, AUDIT-ORDER follow-ups, or any wearables (#94) migration PR; an owner answer to a gate below; any edit to `scripts/backup.py`, `api/profiles.py` reset route, `core/audit.py` allowlist.

Lane C owns the profile schema chain, FK enforcement, the test-reset tuple, export persistence, backup robustness and two small evidence/audit fixes. It also publishes the profile-migration numbering contract **C-PMIG** that wearables (#94) and gamification task 2b consume.

## 1. Items

| ID | Item | Kind | Source | Readiness | Depends on | Owner gates |
|----|------|------|--------|-----------|------------|-------------|
| C-PMIG | Profile-migration numbering contract | DOCS | this doc §3.0; wearables A11 / OW-W13 | ready | none | OW-W13 (order confirm, optional) |
| C-P6 | FK enforcement: orphan audit, migration `013`, pragma on both engines | PRODUCT | [plan 06](../../../audit/2026-09-25/plans/06-sql-fk-audit.md), [SQL-FK-001 audit](../2026-09-08-sql-fk-001-foreign-key-audit.md), [P6 pack](../../../audit/2026-09-25/waves/scaffold/P6.md) | blocked-on-owner (Task 1 code is ready) | none on main (P1, S-1, P5 merged) | D5 signed; P6-Q1, P6-Q3, P6-Q4, P6-Q5, P6-ORPHAN unasked |
| C-P7 | Test-reset covers every profile table | PRODUCT | [plan 07](../../../audit/2026-09-25/plans/07-test-reset-tables.md), [P7 pack](../../../audit/2026-09-25/waves/scaffold/P7.md) | blocked-on-item | C-P6 | P7-ROUTE signed; RESET-AUDIT-OWNER signed; N-02 unasked |
| C-GAM2B | Gamification v2 task 2b: `streaks_hidden` + settings pair + migration | PRODUCT | [GAMIFICATION-V2 §2b](../../../audit/2026-09-25/waves/scaffold/GAMIFICATION-V2.md), GAM2-PLAN-APPROVAL | ready (GAM2B-PATH answered, `owner-decisions:208`; #84 merged) | #84; C-PMIG | GAM2-PLAN-APPROVAL signed; GAM2B-PATH answered (accept recommended: `/settings/model/gamification`) |
| C-GC1 | Export artifacts survive restart | PRODUCT | [W11b G-C1](../2026-09-27-W11b-roadmap-items-gc1-gc4.md) Tasks C1.0-C1.5, [G-C1 pack](../../../audit/2026-09-25/waves/scaffold/G-C1.md) | blocked-on-owner | W-2, C-P6, C-P7 | S-C1-1, S-C1-2 unasked |
| C-BKUP | Backup: failed run leaves orphan folder; L1 busy-wait deadline | PRODUCT | [BKUP-TORN response](../../reviews/2026-10-13/BKUP-TORN-response.md) row 3; [SQLITE-MIX response](../../reviews/2026-10-13/SQLITE-MIX-diff-response.md) L1 | blocked-on-owner | none | BKUP-FOLLOWUPS unasked |
| C-VAULTSC | VAULT-SIDECAR: make the ciphertext scan non-vacuous | PRODUCT (tests) | [implementation program](../../capstone-report/implementation-program.md) owner item VAULT-SIDECAR; [wave-2-L1-C](../../../audit/2026-09-25/waves/wave-2-L1-C.md) findings 1-3 | blocked-on-owner | none | VAULT-SIDECAR signed |
| C-DUPAUD | Import audit row drops `duplicate_warning` | PRODUCT | `api/documents.py:537` vs `core/audit.py:69-75,103` (orchestrator cited `:540`) | blocked-on-owner | none | DUP-AUDIT-KEY signed |

Ordering on shared files:

- `api/profiles.py`: C-P6 (comment only, `:939-942`) → C-P7 (reset route) → then, in any order, C-GC1 (reset tuple + S-C1-2 docstring), lane E E-2 (W-11a PR-1, OG-1) and wearables (RESET-APPEND, OW-W12). E-2 does **not** wait for C-GC1. The second lander rebases.
- `src/backend/migrations/profile/versions/` and the head literal: by merge order under C-PMIG. This includes lane D D-2.
- `tests/support/routes.py`: C-P7 → lane E E-2 (W-11a PR-1). Lane B B-5 (W-7) only reads it.
- `scripts/backup.py`: C-BKUP only.
- `tests/test_audit_order_guard.py`: C-GAM2B, C-GC1, lane E E-2 and lane B B-5 each add or edit only their own CLASSIFICATION rows. They are not ordered; the second lander rebases.
- `src/frontend/src/pages/SettingsPage.tsx`, `components/medication-coach/AchievementsWidget.tsx`: #84 → C-GAM2B. #74 (lane E E-4) and lane B B-1 also edit these files, and either may land before or after C-GAM2B. The second lander rebases. If C-GAM2B lands before #74, E-4's drift scan covers the new switch.
- `core/audit.py` `STRING_DETAIL_KEYS`: C-DUPAUD (option b) and the wearables WEAR-D4 / OW-W11 exact diffs. Whichever lands second re-anchors without changing its content.

## 2. Per-item design or delta

### 2.1 C-P6: delta on plan 06 (plan stays valid; do not rewrite it)

**What changed on main since plan 06 (`40f590e`) and the P6 pack (`6b4dd84`):**

| Change | Effect on plan 06 |
|---|---|
| P5 merged (#54) | P6 pack blocker is gone. |
| DDI (#41): `Observation.interpretation` has `cascade="all, delete"` with a comment saying the DB ondelete is inert (`models/observation.py:107-116`) | P6 makes that comment false. Add `models/observation.py` (comment only; keep the ORM cascade). P6-Q4. |
| SQLITE-MIX: profile engine now built with `async_creator` (`core/profile_database.py:314`); key listener `set_sqlite_pragma` at `:331-373` | The FK listener goes after `:373`, before `session_maker` (`:376`). The `connect` event still fires for `async_creator` connections (SQLITE-MIX secrev check 1). |
| AUDIT-ORDER (#78): `delete_document` and `reprocess_document` are A2 routes | No conflict; FK actions change the DB, not the audit order. |
| CARE-QUOTE fix on main: `update(CarePlanTask)` in `delete_document` (`api/documents.py:1877`) | Plan 06 "branch1 `45ac889`" caveat is closed. |
| Head literals | Four, not two: `tests/test_care_tasks.py:809,825`, `tests/test_profile_migrations_sqlcipher_fallback.py:41`, `tests/test_source_spans.py:313`. `tests/test_pinboards.py:270` checks the 012 file text, not the head; leave it. |

**Corrected `file:line` (main @ `3b2236c`):**

- master engine `core/database.py:44-48` (`hide_parameters=True` at `:47`).
- core deletes that bypass ORM cascade: `api/documents.py:630` (`delete(Observation)`), `:869` (`delete(Chunk)`), `:1202-1203` and `:1862-1863` (entity/category), `:90` (pin prune, child side).
- "pragma set nowhere" comments: `api/profiles.py:939-942`, `tests/test_profile_deletion.py:413`.
- restore's delete-then-insert of the profile row stays on raw stdlib `sqlite3`: `scripts/backup.py:578-583`. Still required: never route it through a hooked engine.
- unnamed FKs to rebuild: `migrations/profile/versions/004_document_categories_entities.py:25,36`, `011_care_plan_tasks.py:32-33`; `document_entity` columns from `004` plus `010_entity_source_spans.py`.

**Still valid as written:** Global Constraints, Tasks 1-5, D5 semantics (P14/P15 CASCADE, P16/P17 SET NULL), migration engines stay pragma-OFF, Task 3 Step 5 superseded by P7.

**Changes to plan 06 (apply when executing):**

1. **Task 1 script uses the public open path.** Do not call `manager._load_encryption_key` and a raw sqlcipher connect. Copy the owner-chosen backup to a scratch dir, point `settings.app_data_path` at it, call `get_profile_db_manager().open_profile_database(profile_id, password)` and run `find_orphans` on `connection.get_session()`. No new key handling; it runs migrations on the **copy** only. Never point the script at the live vault.
2. **Add HC-FKA-004 (coverage):** every `ForeignKey` in `ProfileDatabaseBase.metadata` and `Base.metadata` has a row in `PROFILE_CHECKS` / `MASTER_CHECKS`. A later migration that adds an FK without a check row goes red.
3. **Carry the head literal as one constant** (C-PMIG carrier): create `src/backend/tests/support/migrations.py` with `PROFILE_HEAD = "013_fk_cascade_alignment"` and replace the four literals with it. The value stays hard-coded, so no assertion is weakened; later migrations edit one line.
4. **Do not edit `scripts/backup.py`** (plan 06 Task 3 Step 6 comment). C-BKUP owns that file; it adds the "pragma stays OFF here" comment.
5. **Update the DDI comment** at `models/observation.py:111-113` to say the DB cascade is now enforced too (P6-Q4 option a).
6. **REPROCESS-INTERP-ORPHAN:** add one `route_client` test that reprocesses a document with a `LabInterpretation` and asserts 0 orphan rows after (P6-Q5 option a). PANEL-INTERP-STALE is not an FK and stays open.

**Predicted blast radius (fix in setup or code, never in the constraint):** test fixtures that insert `audit_logs` rows with a `profile_id` absent from `profiles` on the real master engine (M1 now enforced); any fixture that deletes a parent before its children on a pragma-ON engine.

**Acceptance:**

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/<p6-worktree>/src/backend
~/venvs/asclexis-311/bin/python -m pytest tests/test_fk_audit.py tests/test_fk_migration_013.py tests/test_fk_enforcement.py -p no:cacheprovider -q
~/venvs/asclexis-311/bin/python scripts/fk_orphan_audit.py --master          # exit 0, M1/M2: 0 orphans
grep -rn "PRAGMA foreign_keys=ON" core/ | wc -l                                # >= 1
# full suite under the box's pytest flock; failures ⊆ P6-start failures; collected = start + new
```

**Rollback:** revert; `alembic downgrade` to the previous head on any vault that ran `013`; restore a real vault from its pre-phase backup.

### 2.2 C-P7: delta on plan 07

**Changed since plan 07:**

- RESET-AUDIT-OWNER (signed 2026-10-09, `owner-decisions-2026-09-27.md:89`): **drop Task 2 Step 3's audit call and the `get_db` dependency.** W-11a PR-1 owns the audit row. The route stays unaudited until then.
- `route_client` (`tests/support/routes.py:27-60`) hard-codes `profile_name="T"` and has since gained `raise_server_exceptions: bool = True` (`:32`). **Append the two plan-07 keywords after it:** `profile_name: str = "T"` and `profile_db: Optional[async_sessionmaker] = None`. When `profile_db` is given, `get_profile_db_session` is overridden to yield a session from it. Every existing caller passes keywords only (checked with `grep -rn "route_client(" tests` at `3b2236c`), so appending them breaks none. `profile_db` stays because W-11a PR-1 (lane E E-2) calls it and STOPs without it (W11a plan `:282`, stop gate 12). *(Peer review: an earlier draft dropped `profile_db`.)*
- `api/profiles.py` lines: imports `:51-71`, prefix constant `:81`, route `:476-532`, tuple `:498-515`, `{exc}` echo `:529`.
- The model set is unchanged: 23 profile tables, the same 6 missing (`care_plan_task`, `chat_sessions`, `chat_turns`, `response_feedback`, `pinboard`, `pinboard_item`). `badge_definition` stays (seed data).
- `test_audit_order_guard.py:111` already classifies `reset_synthetic_test_profile` as excluded; no change.

**Still valid:** `_SYNTHETIC_RESET_MODELS` order in Task 2 Step 2, HC-RESET-001…010, 404/403 guard tests, collected = start + 7.

**N-02 gate before HC-RESET-010:** `search_records` / `search_records_fts` (`modules/search.py:29-50`). Recommended (a): two raw `DELETE` statements in the reset plus one assertion.

**Acceptance:** `pytest tests/test_profile_test_reset.py -v` → 7 passed; break-it: remove `ChatTurn` from the tuple → HC-RESET-010 red; restore → green.

**Rollback:** revert.

### 2.3 C-GAM2B: delta on GAMIFICATION-V2 task 2b

**Plan source:** `audit/2026-09-25/waves/scaffold/GAMIFICATION-V2.md:35,83,90`; approved (GAM2-PLAN-APPROVAL, `owner-decisions-2026-09-27.md:134`).

**Corrections:**

1. **Route path.** The plan says `/settings/gamification`, modelled on `/settings/voice`. The voice routes are really `/settings/model/voice` (`api/__init__.py:56` prefix; `api/model_settings.py:987,1001`; frontend `services/modelSettings.ts:298,302`). Same router → `GET`/`PATCH /settings/model/gamification`. GAM2B-PATH asks the owner to accept the real path.
2. **Not blocked by P6.** The owner accepted the race ("whichever lands second renumbers", `:134`). Number per C-PMIG; expected `014_streaks_hidden` if P6 lands first, else `013_streaks_hidden`.
3. **Blocked by #84:** both edit `AchievementsWidget.tsx`, `StreakDisplay.tsx` (via `AdherenceDashboard.tsx`) and `services/modelSettings.ts`.
4. **Audit without an ask-first edit.** Use `audit_and_commit(master_db, create_audit_log, event_type="settings.gamification.view" | "settings.gamification.update", entity_type="settings", entity_id="gamification", details={"changed_fields": ["streaks_hidden"]})`. The action string is not in `ALLOWED_ACTIONS`, so `_scrub_action` stores the event type; `core/audit.py` is not edited.
5. **Guard rows:** add `api/model_settings.py::get_gamification_settings` (`excluded: read route, audit_and_commit only`) and `::update_gamification_settings` (`C`) to `tests/test_audit_order_guard.py` CLASSIFICATION, or HC-AUD-ORD-030 goes red.
6. Column only, so no P7 tuple change (`UserModelSettings` is already reset).

**Design:**

- `models/model_settings.py`: `streaks_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)` (pattern `agent_enabled`, `:132-137`).
- Migration `NNN_streaks_hidden.py`, pattern `009_agent_enabled.py` (`op.add_column` / `op.drop_column`).
- Routes after `:1018` in `api/model_settings.py`.

**Test-first:** migration round trip on a tmp vault (pattern `tests/test_care_tasks.py:795-826`, downgrade target read from the file); HTTP via `route_client`: 401 unauthenticated, default `false`, PATCH persists, profile A's PATCH invisible to profile B, one audit row per call; frontend: Settings switch toggles, both streak surfaces hidden while badges stay.

**Plan delta (2026-10-17, PR #146 Task 0 block).** Run 1 stopped on a head pin the C-PMIG literal list missed. `tests/test_notification_scheduler_wiring.py::test_hc_sched_tz_005_migration_clears_windows_and_round_trips` (D-2) finds `*_adaptive_windows_local.py` by glob, reads its `revision` into `rev` by regex, runs `command.upgrade(config, "head")` and asserts `get_profile_current_revision(vault, key) == rev` twice (`:771`, `:789`). That holds only while D-2 is head. A grep for `013_adaptive_windows_local` cannot find it. Measured on `ea7f50c`: `pytest tests/test_notification_scheduler_wiring.py -k tz_005` → `AssertionError: assert '014_streaks_hidden' == '013_adaptive_windows_local'`, `1 failed`. Moving the head is the signed scope (GAM2-PLAN-APPROVAL accepts the race, `owner-decisions:135`; C-PMIG §3.0 item 5 and contracts §c item 2: every migration PR updates the head pins), so this is a missed head literal, not new scope. **Fix (test only, HC-SCHED-TZ-005 only):** both head asserts compare against `ScriptDirectory.from_config(config).get_current_head()` (import `from alembic.script import ScriptDirectory`; `get_current_head()` raises on more than one head, so the check gets no weaker). Drop the `rev` regex line if nothing else reads it (ruff F841). Keep unchanged: the slug glob and `len(files) == 1`, the `down` regex, both `downgrade(config, down)` steps, the `adaptive_window_tz` present / absent asserts and both row-value asserts. Nothing else in that file changes. After this, no later profile migration edits that test. **New tests:** none (HC-SCHED-TZ-005 keeps its id and is rewritten, not added). RED is the measured failure above; GREEN = `pyslot.sh` run of `tests/test_notification_scheduler_wiring.py` plus `tests/test_gamification_settings.py`. **Expected collected delta:** this delta **0**; the item overall **+9** (HC-GAMSET-001..007, 9 collected with parametrisation; measured `1725` on `origin/main` @ `0440045` by Task 0, `1734 tests collected` on `ea7f50c`).

**Acceptance:** `pytest tests/test_gamification_settings.py tests/test_audit_order_guard.py tests/test_notification_scheduler_wiring.py -q` green; `npx vitest run src/__tests__/Gamification.test.tsx` (Windows, per the WSL vitest note).

**Rollback:** revert; downgrade drops the column.

### 2.4 C-GC1: delta on W11b Tasks C1.0-C1.5

**Changed since W11b (`40f590e`) and the G-C1 pack (`6b4dd84`):**

| Change | Effect |
|---|---|
| P5 merged | Blocker gone. |
| W-2 still not on main (`grep redact_summary_data api/export.py` → 0; no `tests/test_export_redaction.py`; no open PR) | Still blocks: G-C1 persists the redacted doctor-summary dict. |
| AUDIT-ORDER merged: `tests/test_audit_order_guard.py:46-54` classifies all export generate/download handlers as `excluded: read route, audit_and_commit only`; `api/pinboards.py::export_pinboard_packet` is `A2` (`:107`) | After G-C1 the generate handlers commit the vault. Reclassify `generate_doctor_summary`, `generate_visit_prep`, `generate_fhir_export` as `C`; keep the pinboard route's A2 intent pair intact. |
| RL-EXPORTS (pack Q5) | Closed on main: `.gitignore:78` ignores `src/backend/rl_exports/`, and `delete_profile` sweeps it (`api/profiles.py:791-805`). Drop Q5. |
| Migration number | Per C-PMIG, not hard-coded `014`. Task C1.0 Step 2 already measures the head; keep that step. |

**Corrected `file:line`:** stores `api/export.py:46-52`; summary store `:448`, load `:500`; visit-prep store `:802`, load `:843`; FHIR store `:1231`, load `:1271`; `api/pinboards.py:13` import, `:511` store; S-C1-2 docstring `api/profiles.py:800-805`.

**Still valid:** the `export_artifact` table, `_save_artifact` / `_load_artifact`, stage → audit commit → vault commit, HC-EXPA-001…010 (16 collected), break-it list, F-6 handling.

**Acceptance:** plan Task C1.5 unchanged, plus HC-AUD-ORD-030 green after reclassification.

### 2.5 C-BKUP: new design (no plan exists)

**Goal:** a failed backup leaves nothing on disk; a stuck SQLite lock cannot pin the backup thread (and with it `_BACKUP_LOCK`) forever.

**Evidence (main @ `3b2236c`):**

- `scripts/backup.py:390-392`: `backup_{%Y%m%d_%H%M%S}` with `mkdir(exist_ok=True)`. Two runs in one second share a dir, even under `_BACKUP_LOCK` (`:355`).
- Any exception after `:392` (snapshot, `_backup_sqlite`, `_scope_master_to_profile`, checksum, disk full) leaves a manifest-less dir. `prune` skips dirs with no manifest (`:767-768`), so the copy (master rows plus maybe a vault) is never pruned. `list_backups` lists it (`api/backup.py:214-219`).
- `_backup_sqlite` (`:173-194`): `src_conn.backup(dst_conn)` retries BUSY forever (SQLITE-MIX L1), and any exception falls back to `shutil.copy2`. A deadline exception must not take that fallback, or it would store the torn copy BKUP-TORN removed.

**Design (one file, `scripts/backup.py`):**

1. **Unique dir:** try `backup_{ts}`, then `backup_{ts}_1`, `_2`… with `mkdir(exist_ok=False)`. Common-case name unchanged, so no reader changes (`api/backup.py:67`, tests with `backup_20200101_000000`).
2. **Cleanup on failure:** wrap everything after the mkdir in `try/except BaseException: shutil.rmtree(dest_dir, ignore_errors=True); raise`. Safe now because the dir was created by this call (the reason row 3 was deferred is gone).
3. **Deadline:** `BACKUP_BUSY_TIMEOUT_S = 600` (same value as `SNAPSHOT_TIMEOUT_S`, `:198`), `class BackupBusyTimeout(Exception)`. Pass `progress=` to `Connection.backup`; the callback raises `BackupBusyTimeout` once `time.monotonic()` passes the deadline. CPython calls `progress` after every step, including BUSY. In `_backup_sqlite`, `except BackupBusyTimeout: raise` comes before the generic fallback.
4. Comment at `_reapply_profile_row` (`:578`): "PRAGMA foreign_keys stays OFF here: restore deletes then re-inserts the profile row (SQL-FK-001)."

Route and scheduler need no change: the route turns the exception into a 500 (existing), the scheduler records `failed` (`modules/backup_scheduler.py:153-158`). Skipped: cleanup of orphan dirs already on disk; the zero-database early return at `:401-408` (unreachable for profile-scoped calls).

**Test-first (`tests/test_backup.py`):**

- HC-BKUP-060: monkeypatch `_compute_sha256` to raise → `backup()` raises and `backup_dir` is empty. Red today.
- HC-BKUP-061: freeze `scripts.backup.utcnow` → two backups → two dirs, both with manifests, the first manifest unchanged. Red today.
- HC-BKUP-062: hold `BEGIN EXCLUSIVE` on a tmp DB, set `BACKUP_BUSY_TIMEOUT_S=0.5`, run `_backup_sqlite` in a thread with `join(5)` → raises `BackupBusyTimeout`, no `file_copy`. Red today (thread still alive at join). Release the lock in `finally`.
- Task 0 probe: `sqlcipher3` `Connection.backup` accepts `progress=`; if not, STOP and report.

**Acceptance:** `pytest tests/test_backup.py tests/test_backup_api.py tests/test_backup_snapshot.py -q` green; break-it: remove the `rmtree` → 060 red; remove the re-raise → 062 red.

**Rollback:** revert one file.

### 2.6 C-VAULTSC: new design (tests only)

**Goal:** each ciphertext check in `tests/security/test_vault_ciphertext.py` can fail, and `vaults/<id>/docs/` is covered.

**Evidence:** `_assert_vault_ciphertext` (`:48-63`) globs `vault.db*` (`:54`), but the vault uses `journal_mode=delete`, so after close only `vault.db` exists. HC-KEYCT-003 (`:115-124`) is caught by the header check first; the canary check has no negative control of its own. The stdlib "not a database" check (`:58-62`) cannot fire alone: SQLite will not open a file without the plaintext header, so it is covered by the header check. Document that instead of inventing a control.

**Design:**

1. HC-KEYCT-006 (journal): commit the canary, then in a second transaction `UPDATE hc_keyct_probe SET note='x'` and flush, read `vault.db-journal` while the transaction is open (it holds the old page with the canary), assert the file exists and the canary is absent, then roll back. If the journal is not on disk mid-transaction, STOP and report; fallback (b): assert `PRAGMA journal_mode` = `delete` and narrow the docstring.
2. HC-KEYCT-007 (canary control): a file with a non-SQLite header that contains the canary → the helper raises `canary found`.
3. HC-KEYCT-008 (docs): `IngestModule(vault, encryption_key=generate_encryption_key())` stores a canary document; the `.bin` lacks the canary. Negative: `encryption_key=None` → the canary is present (`modules/ingest.py:186-201`).

No encryption code is touched. **Acceptance:** `HC_REQUIRE_SQLCIPHER=1 pytest tests/security/test_vault_ciphertext.py -v` → 10 passed on Linux; break-it for each new test. **Rollback:** revert.

### 2.7 C-DUPAUD: new design

**Bug:** the import route sends `"duplicate_warning": duplicate_warning.match_type` (a string, `api/documents.py:537`). `duplicate_warning` is allowlisted only as a boolean (`core/audit.py:103`), not in `STRING_DETAIL_KEYS` (`:69-75`), so `_scrub_details` drops it and adds `_scrubbed`. `docs/features/TASK_LIST.md:681-682` says the audit row "records the warning type", which is false today.

**Options:**

- **(b) Recommended:** add `"duplicate_warning"` to `STRING_DETAIL_KEYS` (one word). Values are the literals `content_hash` / `same_date` (`api/documents.py:268`), which match `_ENUM_VALUE_RE`. The doc claim becomes true. This edits `core/audit.py`, treated as ask-first since AO-ASKFIRST.
- (a) Change the route to `duplicate_warning is not None` (bool) and correct `TASK_LIST.md:681-682`. No gate, loses the type.

**Test-first:** in `tests/test_audit_phi_minimization.py`, `_scrub_details({"duplicate_warning": "content_hash"}) == {"duplicate_warning": "content_hash"}` (red today). In `tests/test_documents_api.py`, a duplicate import over `route_client` with a recording master (pattern HC-CAREQ-004, `:760-840`) asserts the AuditLog details hold `duplicate_warning == "content_hash"` and no `_scrubbed`.

**Acceptance:** both tests green; break-it: revert the one word → both red. **Rollback:** revert.

## 3. Provides

### 3.0 C-PMIG: the profile-migration numbering contract

1. **Chain:** `src/backend/migrations/profile/versions/`. Head on `origin/main` @ `3b2236c`: `012_pinboards` (`012_pinboards.py:13`, `down_revision = "011_care_plan_tasks"`).
2. **Name:** file stem = `revision` = `NNN_<slug>`, `NNN` zero-padded to 3 digits = numeric prefix of the head on `origin/main` at the PR's **final rebase** + 1. `down_revision` = that head's exact revision string. The docstring `Revision ID:` / `Revises:` lines match.
3. **Fixed slugs; numbers by merge order.** The numbers below are illustrative, not reservations. Peers should cite the slug plus "head+1 at final rebase", never a fixed number. Lane D D-2 adds a migration too. Its prerequisites (#97, D-1) are PRs and items, not owner gates, so it may well be the first to land and take `013`. In that case every row below shifts by one.

   | Expected | Slug | Item | Notes |
   |---|---|---|---|
   | 013 or later | `adaptive_windows_local` | lane D D-2 | data-only (`UPDATE medication_schedules … = NULL`), downgrade no-op; lane D's doc hard-codes `013` / `012_pinboards`, see Peer review |
   | 013 | `fk_cascade_alignment` | C-P6 | |
   | 014 | `streaks_hidden` | C-GAM2B | may land before C-P6 (owner-accepted race) |
   | 015 | `export_artifacts` | C-GC1 | W11b hard-codes `014`; its Task C1.0 re-measures |
   | 016 | `wearables` | WEAR-02 (#94) | |
   | 017 | `symptom_journal` | WEAR-15a (#94) | after WEAR-02 |
   | — | `audit_outbox` | AUDIT-ORDER option B | **withdrawn**: the owner chose design D (AO-DESIGN, `owner-decisions-2026-09-27.md:93`; AO-ASKFIRST "no migration", `:101`); merged as #78 with no migration. Wearables plans 00/02/15 still list `015_audit_outbox`; drop it on their next refresh. |

4. **Second lander renumbers:** rebase, rename the file, update `revision`, `down_revision`, the docstring and the head literal, then re-run its round-trip test. Never edit a merged migration file.
5. **Head literal:** every new profile migration moves the head, so every migration PR updates it, data-only ones (D-2) included. Before C-P6 merges, update the 4 literals (`tests/test_care_tasks.py:809,825`, `tests/test_profile_migrations_sqlcipher_fallback.py:41`, `tests/test_source_spans.py:313`); these tests go red otherwise. After C-P6, update one constant: `src/backend/tests/support/migrations.py::PROFILE_HEAD: str`.
6. **Pre-merge check (all three must hold):**

   ```bash
   cd src/backend
   grep -h "^down_revision" migrations/profile/versions/*.py | sort | uniq -d          # empty
   ~/venvs/asclexis-311/bin/python -c "from alembic.script import ScriptDirectory; from core.migrations import _get_alembic_config as c; print(ScriptDirectory.from_config(c('profile')).get_heads())"   # exactly one
   ```

   When W-11a PR-3 merges, its `tests/test_migration_heads.py` HC-MIGHEAD-001 replaces the second command; WEAR HC-WRB-217 / HC-WRB-1515 can then be dropped as duplicates.
7. **FKs after C-P6:** every new FK declares `ondelete=` explicitly in model and DDL (NO ACTION now raises on parent delete), and gets a row in `core/fk_audit.py::PROFILE_CHECKS` (HC-FKA-004 enforces it).
8. **New tables after C-P7:** append the model to `api.profiles._SYNTHETIC_RESET_MODELS`, child before parent (HC-RESET-010 enforces). That edits ask-first `api/profiles.py`; owner gate RESET-APPEND. Column-only migrations skip this.
9. **Round trip:** the existing chain walk `tests/test_care_tasks.py:795-826` (head → downgrade to `010_entity_source_spans` → upgrade head) already walks every migration above `010` down and back up, so it counts as each new migration's round trip once the head literal is updated (item 5). A migration adds its own test only for its schema or data effect (a column exists, a rebuild keeps rows, windows are cleared).
10. Migration engines stay `PRAGMA foreign_keys` OFF (`core/migrations.py`, `migrations/profile/env.py`), so batch rebuilds work.

### 3.1 Interfaces other lanes may code against (after the named item merges)

| Interface | Signature / value | From |
|---|---|---|
| `core.database.install_sqlite_foreign_keys` | `(sync_engine) -> None`; registers a `connect` listener running `PRAGMA foreign_keys=ON` | C-P6 |
| `core.fk_audit` | `FkCheck(check_id, child_table, child_column, parent_table, parent_column="id", scope="profile", enforced=True, where=None)`; `MASTER_CHECKS`, `PROFILE_CHECKS`, `LOGICAL_CHECKS: list[FkCheck]`; `async find_orphans(session, checks) -> list[OrphanFinding]`; `find_orphans_dbapi(conn, checks)` | C-P6 |
| `tests.support.db.fk_profile_engine` | `() -> AsyncEngine`, in-memory, FK pragma on | C-P6 |
| `tests.support.migrations.PROFILE_HEAD` | `str`, current profile head | C-P6 |
| FK actions | `document_category.doc_id`, `document_entity.doc_id` → CASCADE; `care_plan_task.source_document_id`, `.source_entity_id` → SET NULL | C-P6 (`013`) |
| `api.profiles._SYNTHETIC_RESET_MODELS` | `tuple[type, ...]`, child-first; HC-RESET-010 pins it to `ProfileDatabaseBase.metadata` minus `badge_definition` | C-P7 |
| `tests.support.routes.route_client(router, prefix, profile_id="profile-a", master_db=None, raise_server_exceptions=True, profile_name: str = "T", profile_db: Optional[async_sessionmaker] = None)` | two appended keywords; `profile_db` overrides `get_profile_db_session`; existing callers unchanged (additive, so readers such as W-7 need not wait for C-P7) | C-P7 |
| `UserModelSettings.streaks_hidden` | `bool`, default `False` | C-GAM2B |
| `GET` / `PATCH /settings/model/gamification` | body/response `{"streaks_hidden": bool}`; audited `settings.gamification.view` / `.update` | C-GAM2B |
| `models.export_artifact.ExportArtifact` | `(id: str, kind: str, profile_id: str, payload_json: str, created_at: datetime)`; `EXPORT_ARTIFACT_KINDS = ("doctor_summary", "visit_prep", "fhir_r4")` | C-GC1 |
| `api.export._save_artifact` / `_load_artifact` | keyword-only, as in W11b Task C1.3 Step 1 | C-GC1 |
| `scripts.backup.BackupBusyTimeout`, `BACKUP_BUSY_TIMEOUT_S = 600` | `backup()` raises on failure and leaves no `backup_*` dir | C-BKUP |

## 4. Consumes

| Need | From | Used by |
|---|---|---|
| W-2 merged: `ExportModule.redact_summary_data(self, summary_data: dict) -> dict` in `modules/export.py`, called by `POST /export/doctor-summary` in `api/export.py` before `_summary_store` | lane E E-1 | C-GC1 |
| #84 merged (gam v2 tasks 2, 4) | open PR (lane D D-0 merges it last in its chain) | C-GAM2B |
| W-11a PR-1 writes the reset-route audit row (RESET-AUDIT-OWNER) | lane E E-2 | C-P7 leaves the route unaudited |
| W-11a PR-3 `tests/test_migration_heads.py` (HC-MIGHEAD; asserts structure, not names) | lane E E-3 | C-PMIG check 6 |
| Measured collected count after lane D D-0's chain (main slot 1574 at `3b2236c`) | lane D D-0 | every C item's count delta (SLOT-RULE, `owner-decisions-2026-09-27.md:31`) |
| Wearables plans adopt C-PMIG and drop `015_audit_outbox` | #94 | C-PMIG |
| Owner-chosen real vault backup and its password, on the owner's machine | owner | C-P6 Task 1 |

None of the open PRs #95, #97, #99, #82, #72, #68 or #61 touches a lane-C file (`git diff --stat origin/main...origin/<branch> -- src/backend/migrations` is empty for each). The two frontend overlaps, both on C-GAM2B files: #84 (`AchievementsWidget.tsx`, `StreakDisplay.tsx`, `services/modelSettings.ts`) and #74 (`pages/SettingsPage.tsx` 78 lines, `AchievementsWidget.tsx` 2 lines; local `origin/feat/tailwind4` ref, not re-fetched because the network was down).

## 5. Owner gates

Ask-first files touched: `core/profile_database.py`, `core/migrations.py` (C-P6); `api/profiles.py` (C-P6 comment, C-P7, C-GC1); `core/audit.py` (C-DUPAUD option b); `tests/security/test_vault_ciphertext.py` (encryption tests, C-VAULTSC). No change to `interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, `core/auth.py` or `core/security.py`.

| Gate | Question | Recommended | State |
|---|---|---|---|
| P6-Q1 | D5 covers the FK listener in ask-first `core/profile_database.py` (after `:373`) and comment-only lines in `core/migrations.py` / `migrations/profile/env.py`? | yes | unasked |
| P6-Q3 | Which real vault backup may Task 1 read (copy only, owner's machine)? | owner names it | unasked |
| P6-ORPHAN | After Task 1's report: proceed to `013`, clean orphans first (each its own approval), or stop? | depends on report | unasked |
| P6-Q4 / P6-Q5 | Reword the DDI comment; add the reprocess-orphan HTTP test and close REPROCESS-INTERP-ORPHAN | (a) / (a) | unasked |
| N-02 | Reset clears `search_records` / `search_records_fts` and asserts it | (a) clear | unasked |
| RESET-APPEND | Standing approval: appending a new profile model (that tuple line plus its import) to `_SYNTHETIC_RESET_MODELS` | approve | unasked |
| GAM2B-PATH | Accept `/settings/model/gamification` (real router prefix) instead of `/settings/gamification` | accept | unasked |
| S-C1-1, S-C1-2 | G-C1 go + vault-table storage; one-sentence `delete_profile` docstring | as in G-C1 pack Q1/Q4 | unasked |
| BKUP-FOLLOWUPS | Fix both deferred backup findings in one PR, with a 600 s busy deadline | approve, 600 s | unasked |
| VAULT-SIDECAR | Edit the encryption test file (tests only) as in §2.6 | approve | signed |
| DUP-AUDIT-KEY | Add `duplicate_warning` to `STRING_DETAIL_KEYS` in `core/audit.py` | (b) | signed |
| OW-W13 | Confirm profile-migration merge order (C-PMIG table) | confirm | unasked (wearables tickets) |

Signed and relied on: D5 (`owner-decisions-2026-09-27.md:14`), P7-ROUTE (`:32`), RESET-AUDIT-OWNER (`:89`), GAM2-PLAN-APPROVAL (`:134`), SLOT-RULE (`:31`).

## 6. Open questions

1. C-PMIG puts GAM2-2b (`014`) before G-C1, because G-C1 waits on W-2 and S-C1-1 while 2b waits only on #84. The wearables draft order (OW-W13) puts G-C1 first. Numbers follow merge order either way. Confirm, or name a different order.
2. C-P6's orphan audit must run on the owner's machine against a backup copy. Is a seeded dev vault acceptable as a stand-in if no real backup is offered?
3. C-BKUP: should the route also write a failure audit row on a backup exception? Not designed (create_backup is classified excluded); add only if asked.
4. Orphan `backup_*` dirs already on disk from past failures stay. Add a one-off sweep of manifest-less dirs, or leave them?
5. C-DUPAUD: if DUP-AUDIT-KEY is declined, take option (a) (bool + `TASK_LIST.md:681-682` correction)?

## 7. Peer review (2026-10-15)

Each item was checked against the other five lane docs and against the repo at `3b2236c`. This round records **no owner approval**. Every gate in §5 is still unasked.

**Changes made to this doc:**

1. **C-P7 `route_client`:** restored plan 07's `profile_db` keyword and appended both keywords after `raise_server_exceptions` (§2.2, §3.1). Lane E E-2 / W-11a PR-1 consumes `profile_db` and STOPs without it (W11a plan `:282`).
2. **C-PMIG:** added lane D D-2 (`adaptive_windows_local`) to the chain and marked the numbers as illustrative (§3.0 item 3). Item 5 now says every migration PR updates the head literal, data-only ones included. Item 9 now accepts the existing chain walk (`tests/test_care_tasks.py:795-826`) as the round trip.
3. **Shared-file order (§1):** E-2 no longer appears to wait on C-GC1 in the `api/profiles.py` chain. Added order rules for `test_audit_order_guard.py` (including B-5), for `SettingsPage.tsx` / `AchievementsWidget.tsx` (#74, B-1, C-GAM2B) and for `core/audit.py` (C-DUPAUD vs WEAR-D4).
4. **Consumes (§4):** named the lane that provides each input: W-2 = E-1 with the real `ExportModule.redact_summary_data` signature in `modules/export.py`, W-11a PR-1 = E-2, PR-3 = E-3, count base = D-0. Corrected the open-PR overlap note: #74 also touches C-GAM2B files.
5. **Answer to lane B's open question 1:** C-P7's `route_client` change is additive (keyword-only appends). W-7 (B-5) only reads `route_client`, so B-5 may drop C-P7, and with it C-P6, as a hard dependency. The W07 plan's own prerequisite list is P1, P5, P7; it does not name P6. L0 ruled: dropped ([contracts](contracts.md#e-rulings-on-peer-review-conflicts) R-6). Lane B's open question 1 is closed.

**Raised to peers (not edited here):** lane D D-2 hard-codes `013` / `012_pinboards` and omits the 4 head-literal files. Lane B B-5 adds a committing handler but does not list `test_audit_order_guard.py`. Lane F's `core/audit.py` consumer row omits C-DUPAUD. Lane E E-4's drift scan should include C-GAM2B's Settings switch. The owner should answer OW-W13 once for all six profile migrations.
