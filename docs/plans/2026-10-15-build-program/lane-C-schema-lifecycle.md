# Lane C: Schema and Data Lifecycle (Build Program 2026-10-15)

**Last Updated:** 2026-11-04 (BATCH-1104A: C-P6 done, #454 merged as `4ea62500`; owner answers P6-CLEANUP-DIFF and P6-RETENTION recorded, the readings are L0's); 2026-11-04 (BATCH-1103D: C-P6 rulings 6615915762 and 6626122374 on #454 recorded); 2026-11-03 (BATCH-1103B: C-P6 licence for the three Codex findings on #454, L0 ruling 6603412162); 2026-11-03 (BATCH-1102F: C-P6 licence for `purge_pre017_snapshot` in `reset_synthetic_test_profile`, ruling on #454); 2026-11-02 (post-merge batch: C-P6 Delta 2026-11-02 corrected from comment 6592196350: option (b) for `api/backup.py`, the accepted Task 0 points and the three PR-body items); 2026-11-02 (C-P6 Delta 2026-11-02 added: owner answers P6-P8P12, P6-SNAPSHOT, P6-STAMP; the rollback wording at the "Pragma OFF, idempotent" bullet corrected); 2026-11-02 (C-P6 Delta 2026-11-01 amended: owner P6-CLEANUP-SETNULL "Keep task, null links" and P6-CLEANUP-AUDIT "Yes, write audit row"; P16/P17 are SET NULL repairs, HC-FKC-009 in scope, licensed files widened by the named audit edits); 2026-11-01 (C-P6 [Delta 2026-11-01](#delta-2026-11-01-p6-cleanup-the-fk-migration-cleans-orphans): owner P6-ORPHAN-SYNTH and P6-CLEANUP; FK migration renumbered `017_fk_cascade_alignment`; §2.1 and §3.0 `file:line` re-measured on `094b81c9`); 2026-10-15
**Owner:** repository owner
**Status:** DESIGN. Nothing here is approved for execution. Every owner gate in the Owner gates section is **unasked** unless a signed row is quoted. No approval is recorded here.
**Base measured:** `origin/main` @ `3b2236c` (2026-10-15, worktree `hc-wave6-design`). Every `file:line` below was read at that base unless marked otherwise. Collected-count slot: `CLAUDE.md:30` says **1574 backend tests collected** (the orchestrator note said 1501; the slot wins; pytest was not run).
**Refresh Trigger:** any file added under `src/backend/migrations/profile/versions/`; a merge of P6, P7, W-2, #84, AUDIT-ORDER follow-ups, or any wearables (#94) migration PR; an owner answer to a gate below; any edit to `scripts/backup.py`, `api/profiles.py` reset route, `core/audit.py` allowlist.

Lane C owns the profile schema chain, FK enforcement, the test-reset tuple, export persistence, backup robustness and two small evidence/audit fixes. It also publishes the profile-migration numbering contract **C-PMIG** that wearables (#94) and gamification task 2b consume.

## 1. Items

| ID | Item | Kind | Source | Readiness | Depends on | Owner gates |
|----|------|------|--------|-----------|------------|-------------|
| C-PMIG | Profile-migration numbering contract | DOCS | this doc §3.0; wearables A11 / OW-W13 | ready | none | OW-W13 (order confirm, optional) |
| C-P6 | FK enforcement: orphan audit, migration `017` (was `013`; see [Delta 2026-11-01](#delta-2026-11-01-p6-cleanup-the-fk-migration-cleans-orphans)), pragma on both engines | PRODUCT | [plan 06](../../../audit/2026-09-25/plans/06-sql-fk-audit.md), [SQL-FK-001 audit](../2026-09-08-sql-fk-001-foreign-key-audit.md), [P6 pack](../../../audit/2026-09-25/waves/scaffold/P6.md) | **done** 2026-11-04 (#454, merged as `4ea62500`; merge-only gate P6-CLEANUP-DIFF answered "Yes, merge it", 2026-11-04); history: ready for Tasks 2-5 (Task 1 merged, #113); merge-only gate P6-CLEANUP-DIFF | none on main (P1, S-1, P5 merged) | D5 signed; P6-Q1, P6-Q3, P6-Q4, P6-Q5 signed 2026-10-16; P6-ORPHAN answered by P6-ORPHAN-SYNTH and P6-CLEANUP (2026-11-01) |
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
| CARE-QUOTE fix on main: `update(CarePlanTask)` in `delete_document` (`api/documents.py:1895`; `:1877` at `3b2236c`) | Plan 06 "branch1 `45ac889`" caveat is closed. |
| Head literals | Four, not two: `tests/test_care_tasks.py:808,824`, `tests/test_profile_migrations_sqlcipher_fallback.py:41`, `tests/test_source_spans.py:312` (each now `"016_strict_safety_mode"`, re-measured on `094b81c9`). `tests/test_pinboards.py:272-274` checks the 012 file text, not the head; leave it. |

**Corrected `file:line` (main @ `3b2236c`; re-measured on `094b81c9` 2026-11-01, drifted lines updated, old line in brackets):**

- master engine `core/database.py:44-48` (`hide_parameters=True` at `:47`).
- core deletes that bypass ORM cascade: `api/documents.py:640` [`:630`] (`delete(Observation)`), `:905` [`:869`] (`delete(Chunk)`), `:1213-1214` [`:1202-1203`] and `:1880-1881` [`:1862-1863`] (entity/category), `:90` (pin prune, child side).
- "pragma set nowhere" comments: `api/profiles.py:942-945` [`:939-942`], `tests/test_profile_deletion.py:411-414` [`:413`] (HC-PDEL-017 docstring).
- restore's delete-then-insert of the profile row stays on raw stdlib `sqlite3`: `scripts/backup.py:618-623` [`:578-583`] (`_reapply_profile_row`; C-BKUP already added the "PRAGMA foreign_keys stays OFF here" comment at `:580`). Still required: never route it through a hooked engine.
- unnamed FKs to rebuild: `migrations/profile/versions/004_document_categories_entities.py:25,36`, `011_care_plan_tasks.py:32-33`; `document_entity` columns from `004` plus `010_entity_source_spans.py`.

**Still valid as written:** Global Constraints, Tasks 1-5, D5 semantics (P14/P15 CASCADE, P16/P17 SET NULL), migration engines stay pragma-OFF, Task 3 Step 5 superseded by P7.

**Changes to plan 06 (apply when executing):**

1. **Task 1 script uses the public open path.** Do not call `manager._load_encryption_key` and a raw sqlcipher connect. Copy the owner-chosen backup to a scratch dir, point `settings.app_data_path` at it, call `get_profile_db_manager().open_profile_database(profile_id, password)` and run `find_orphans` on `connection.get_session()`. No new key handling; it runs migrations on the **copy** only. Never point the script at the live vault.
2. **Add HC-FKA-004 (coverage):** every `ForeignKey` in `ProfileDatabaseBase.metadata` and `Base.metadata` has a row in `PROFILE_CHECKS` / `MASTER_CHECKS`. A later migration that adds an FK without a check row goes red.
3. **Carry the head literal as one constant** (C-PMIG carrier): create `src/backend/tests/support/migrations.py` with `PROFILE_HEAD = "017_fk_cascade_alignment"` (was `013`; Delta 2026-11-01) and replace the four literals with it. The value stays hard-coded, so no assertion is weakened; later migrations edit one line.
4. **Do not edit `scripts/backup.py`** (plan 06 Task 3 Step 6 comment). C-BKUP owns that file; it adds the "pragma stays OFF here" comment.
5. **Update the DDI comment** at `models/observation.py:111-113` to say the DB cascade is now enforced too (P6-Q4 option a).
6. **REPROCESS-INTERP-ORPHAN:** add one `route_client` test that reprocesses a document with a `LabInterpretation` and asserts 0 orphan rows after (P6-Q5 option a). PANEL-INTERP-STALE is not an FK and stays open.

**Predicted blast radius (fix in setup or code, never in the constraint):** test fixtures that insert `audit_logs` rows with a `profile_id` absent from `profiles` on the real master engine (M1 now enforced); any fixture that deletes a parent before its children on a pragma-ON engine.

**Acceptance:**

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/<p6-worktree>/src/backend
~/venvs/asclexis-311/bin/python -m pytest tests/test_fk_audit.py tests/test_fk_migration_017.py tests/test_fk_enforcement.py -p no:cacheprovider -q
~/venvs/asclexis-311/bin/python scripts/fk_orphan_audit.py --master          # exit 0, M1/M2: 0 orphans
grep -rn "PRAGMA foreign_keys=ON" core/ | wc -l                                # >= 1
# full suite under the box's pytest flock; failures ⊆ P6-start failures; collected = start + new
```

**Rollback:** revert; `alembic downgrade` to the previous head (`016_strict_safety_mode`) on any vault that ran `017`; restore a real vault from its pre-phase backup. The downgrade does not bring back orphan rows the cleanup deleted (Delta 2026-11-01).

#### Delta 2026-11-01 (P6-CLEANUP): the FK migration cleans orphans

**Source:** owner rows P6-ORPHAN-SYNTH and P6-CLEANUP ([owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md), answered 2026-11-01), amended 2026-11-02 by P6-CLEANUP-SETNULL ("Keep task, null links") and P6-CLEANUP-AUDIT ("Yes, write audit row"). **Base measured:** `origin/main` @ `094b81c9`. This delta adds to §2.1 and plan 06 Tasks 2-5; it does not rewrite them. Where it conflicts with plan 06, this delta wins.

**What the owner answered.** A synthetic vault built through the real API (4 lab PDFs, 13 observations, 10 interpretations, 2 documents deleted with `DELETE /api/v1/documents/{id}`) audited at 0 orphans on every check, P1-P18, L1-L5, M1-M2. Only P1-P4 and P14 held data, and no pre-fix vault exists, so the historic delete-bug leftovers are untested. The owner chose "Proceed, migration cleans (Recommended)": Tasks 2-5 build, and the migration itself handles orphans on an older vault (report + delete only orphans, logged) instead of letting deletes fail with a 500.

**1. Migration revision: `017_fk_cascade_alignment`.** `ls src/backend/migrations/profile/versions/` on `094b81c9` lists `001_initial_schema.py` … `016_strict_safety_mode.py`, so the head is `016_strict_safety_mode` and the next free number is `017` (C-PMIG §3.0: re-measure at the final rebase; if another profile migration lands first, take head+1). `down_revision = "016_strict_safety_mode"`. Plan 06's `013` names map as follows: the file is `017_fk_cascade_alignment.py`; the test file is `tests/test_fk_migration_017.py`; `PROFILE_HEAD = "017_fk_cascade_alignment"`; plan 06 Task 2's `_build_vault_at_012` builds at `016_strict_safety_mode`; the four head literals are `tests/test_care_tasks.py:808,824`, `tests/test_profile_migrations_sqlcipher_fallback.py:41` and `tests/test_source_spans.py:312`, each now `"016_strict_safety_mode"`. Plan 06's model lines moved too: `models/document_category.py:23,39` (was `:22,38`) and `models/care_plan_task.py:38-43` (the two `ForeignKey`s are at `:39` and `:42`).

**2. Cleanup rule (Task 2, first step of `upgrade()`, before any batch rebuild).**

- **Same checks as `core/fk_audit.py`, frozen.** The migration carries a literal tuple `_CLEANUP_CHECKS` of the 18 enforced profile checks, P1-P18, copied from `core/fk_audit.py::PROFILE_CHECKS` (`check_id`, `child_table`, `child_column`, `parent_table`, `parent_column`). It uses the same orphan predicate as `fk_audit.orphan_sql`: `c.<child_column> IS NOT NULL AND p.<parent_column> IS NULL` over a `LEFT JOIN`. It does not import `core.fk_audit`. No file in `migrations/profile/versions/` imports app code, and a later `PROFILE_CHECKS` row for a table created after `017` would otherwise break `017` on an old vault. HC-FKC-007 pins the parity.
- **Children only.** For each check except P16/P17 (next bullet): `DELETE FROM <child_table> WHERE id IN (SELECT c.id FROM <child_table> c LEFT JOIN <parent_table> p ON … WHERE <orphan predicate>)`. The statement builder takes its target only from `child_table` in the frozen tuple, so a parent table is never a `DELETE` target.
- **Never deleted:** rows that only the logical checks L1-L5 find (`enforced=False`; report-only, `pinboard_item.item_id` is polymorphic), and anything in the master DB. M1 (`audit_logs`) and M2 (`backup_schedules`) stay report-only; a profile migration never opens the master DB, and audit rows are never deleted by this rule.
- **P16/P17 are SET NULL repairs, never deletes (P6-CLEANUP-SETNULL, answered 2026-11-02: "Keep task, null links").** Their children are `care_plan_task` rows and D5 makes both columns `SET NULL`. No care task is ever deleted. P16 orphans: `UPDATE care_plan_task SET source_document_id = NULL, source_entity_id = NULL, source_quote = NULL WHERE id IN (<orphan select>)`, exactly as `delete_document` does (`api/documents.py:1894-1897`). P17 orphans: `UPDATE care_plan_task SET source_entity_id = NULL WHERE id IN (<orphan select>)` only, keeping `source_document_id` and `source_quote` for dedup (plan 06 risk register). Their counts are logged as `repaired`, not `removed`. Run P16 before P17 in each pass.
- **Chained orphans.** Deleting an orphan can orphan that row's own children: P2 chunk then P3 embedding, P1 then P4, P6 then P8/P10/P12, P15 then P17. Repeat full passes over the tuple until a pass removes nothing. Cap the passes at `len(_CLEANUP_CHECKS) + 1` and raise if the cap is reached. Counts are summed per check id.
- **Pragma OFF, idempotent.** The migration engine stays pragma-OFF (plan 06 Global Constraints), so these deletes do not cascade. Do not rely on a rollback: Alembic's SQLite dialect has `transactional_ddl = False`, `core/migrations.py` has no restore or rollback step for a failed `command.upgrade`, and `downgrade()` restores neither the deleted rows nor the nulled links (017's docstring says so). Nothing undoes the cleanup once it has run; only a copy taken before the upgrade can (Delta 2026-11-02, P6-SNAPSHOT). The cleanup is idempotent instead: if a later step fails, the cleanup's deletes and nulls stay done, the next open re-runs `017`, and the cleanup step finds 0. Whether a failure part-way through the table rebuilds leaves the vault usable on that re-run is not shown here.
- **Logging, no content.** The logger is `logging.getLogger("alembic.fk_cleanup")`, which inherits INFO from `alembic.ini`'s `[logger_alembic]`; the root logger is WARN. Each check with a non-zero count logs one WARNING, `fk_orphan_cleanup check=<id> removed=<n>` (`repaired=<n>` for P16/P17). One summary line follows: `fk_orphan_cleanup total=<n> checks=<k>`, at WARNING if `n > 0` and INFO if not. Logs never contain row ids, column values, table contents, profile names or the vault path (`run_profile_migration` already logs the path at `core/migrations.py:210`).

**3. Audit trail.** `core/audit.py` exists, but it is not a vault-level mechanism. `create_audit_log` (`core/audit.py:202`) writes `audit_logs` in the **master** DB through an `AsyncSession` (`models/audit.py:21-32`, master `Base`). No profile-DB audit table exists. The migration runs in a worker thread on its own sync engine (`core/migrations.py:194-334`, through `run_profile_migration_async` `:337-352`, called from `core/profile_database.py:384`), with no master session. So the plan does not invent a vault-level audit. The owner chose a master audit row (P6-CLEANUP-AUDIT, answered 2026-11-02: "Yes, write audit row"; counts only, no row content, ids or PHI), written without touching `core/audit.py`: use `event_type="profile.fk_orphan_cleanup"` with `action` equal to the event type (the `_scrub_action` path, `:174-193`) and `details={"resource_counts": {<check_id>: n}, "count": total}`, both keys already allowlisted (`:86`, `:96`). The licensed edits, exactly these and no others:
- `core/migrations.py`: the migration writes its counts to `context.config.attributes["fk_cleanup_counts"]`, and `run_profile_migration` / `_async` return them;
- `core/profile_database.py`: a field on `ProfileDatabaseConnection` carries them;
- `api/profiles.py`: the four `open_profile_database_on_login` call sites (`:331` create, `:406` login, `:757` recovery, `:1094` unlock) read the returned connection and write the row when `total > 0`.

`core/auth.py` (`:363-400`) is ask-first, is not in the row, and must not be edited. The call sites use the connection it already returns. `core/audit.py` is not edited either. The log lines stay as well; the audit row is in addition to them, not instead.

**4. Downgrade is not reversible for deleted orphans.** `downgrade()` rebuilds the three tables back to NO ACTION (plan 06 Task 2 Step 3) and restores nothing that the cleanup removed. The docstring says so, and the PR body repeats it. Recovery of a removed row is only from a pre-upgrade backup. Four existing tests downgrade from head through `017` and stay unedited, so `017.downgrade()` must succeed on their vaults: `tests/test_data_donation.py:113`, `tests/test_safety_mode_setting.py:324`, `tests/test_gamification_settings.py:195`, `tests/test_notification_scheduler_wiring.py:753,787`.

**5. Tests (`tests/test_fk_migration_017.py` unless noted; each RED before GREEN).** Each test builds a file vault at `016_strict_safety_mode` (`_get_alembic_config("profile")` with `vault_path` and `encryption_key` attributes, `command.upgrade(cfg, "016_strict_safety_mode")`), seeds rows with the pragma OFF, then runs `command.upgrade(cfg, "head")`.
- **HC-FKC-001 planted orphans per enforced class.** Parametrised over P1-P18. Seed one valid parent with one valid child, plus one orphan child, for the check under test. After upgrade: for P1-P15 and P18 the orphan is gone; for P16/P17 the orphan care task **still exists** (same id, same row count in `care_plan_task`) with its links nulled: P16 has `source_document_id`, `source_entity_id` and `source_quote` all NULL; P17 has `source_entity_id` NULL while `source_document_id` and `source_quote` keep their seeded values. In every case the parent and the valid child are present and unchanged, and `PRAGMA foreign_key_check` returns no rows.
- **HC-FKC-002 chained orphans.** An orphan chunk carrying an embedding, and an orphan schedule carrying a dose: all are removed in one upgrade, with counts P2=1, P3=1, P6=1, P8=1.
- **HC-FKC-003 logged counts, no content.** Use `caplog` on `alembic.fk_cleanup`. Each planted check gives exactly one record with the right `removed=<n>`, or `repaired=<n>` for P16/P17 (and never `removed` for them), and the summary total matches. No record contains a seeded row id or a sentinel string seeded into a text column (for example `SENTINEL-PHI-7f3a` in `chunks.text` and `observations.analyte`).
- **HC-FKC-004 out-of-scope rows survive.** A planted L1 (`response_feedback` with a missing session) and L3 (`pinboard_item` pointing at a missing document) are still present after upgrade.
- **HC-FKC-005 clean vault is a no-op.** A vault with valid rows only has the same per-table row counts and row contents before and after (compared by primary key), logs a single INFO summary with `total=0`, and logs no WARNING.
- **HC-FKC-006 idempotent re-run.** After HC-FKC-001's upgrade, `downgrade` to `016_strict_safety_mode` and `upgrade` again: `total=0`, and the earlier valid rows are unchanged.
- **HC-FKC-007 frozen-list parity.** The migration's check ids are exactly P1-P18. Each `_CLEANUP_CHECKS` entry equals the `core.fk_audit.PROFILE_CHECKS` entry with that id, on (`child_table`, `child_column`, `parent_table`, `parent_column`), and that entry is `enforced`. This is a subset check, so a later check row for a newer table does not turn this test red.
- **HC-FKC-008 delete after migration is not a 500 (route test, `tests/test_fk_enforcement.py`).** Use `route_client(documents_router, "/documents", raise_server_exceptions=False)` and override `get_profile_db_session` with a session on the migrated vault file with the FK pragma ON (Task 3's listener or `tests/support/db.py`), as `tests/test_documents_api.py:804-811` does. Seed at `016`: document D with entity E and category K, a care task T whose `source_document_id` is D and `source_entity_id` is E, plus planted orphans (P3, P4). Upgrade, then `DELETE /documents/D` → **204**. T remains with NULL source references, and `PRAGMA foreign_key_check` returns no rows. RED: on a `016` vault with the pragma ON, the same request returns 500, because `delete(DocumentEntity)` (`api/documents.py:1880`) runs before the care-task update (`:1895`) while `care_plan_task.source_entity_id` is still NO ACTION. The PR also records whether planted orphans alone make any delete fail with the pragma ON and no cleanup. The plan does not assume it: SQLite checks only the new violations a statement causes.
- **HC-FKC-009 audit row (in scope: P6-CLEANUP-AUDIT, answered 2026-11-02).** A `route_client` unlock with a real master session on a vault holding planted orphans writes one `profile.fk_orphan_cleanup` row. Its `details_json` holds `resource_counts` and `count` only, with no ids, and passes `_scrub_details` unchanged. A clean vault writes no such row.

**Planner checklist (RUNBOOK §10.1).**
- **Tests that must change:** the four head literals become `PROFILE_HEAD` (allowed edit: the literal only); the `tests/test_profile_deletion.py:411-414` HC-PDEL-017 docstring (comment only; the explicit delete and its assert stay); `tests/test_audit_order_guard.py:195-196` (the reason string for key `core/migrations.py::run_profile_migration_async::asyncio.to_thread(run_profile_migration)` says "schema only"; the allowed edit is that reason text only, to "schema plus 017 orphan cleanup; own connection, no audit session").
- **Tests that stay unedited:** `test_fk_audit.py` (HC-FKA-001..004), `test_audit_phi_minimization.py`, `test_migration_logging_not_disabled.py` and the four downgrade-through tests in item 4.
- **No RED run here:** the planner ran no pytest (docs-only planning brief), so the implementer captures RED for each new id.

**6. Ask-first scope. Do not widen it quietly.**
- **Already licensed** by D5 ("pragma ON for master + profile engines"), P6-Q1 and P6-Q4/Q5:
  - the master-engine FK listener in `core/database.py` (`install_sqlite_foreign_keys`, applied to the engine at `:44-49`);
  - the profile-engine FK listener in `core/profile_database.py`, placed after the key listener (`:331-373`) and before `session_maker` (`:376`); both lines are unchanged on `094b81c9`;
  - comment-only lines in `core/migrations.py` and `migrations/profile/env.py`;
  - the `api/profiles.py:942-945` comment;
  - the `models/observation.py:111-113` DDI comment;
  - the reprocess-orphan HTTP test.
- **Needs no ask-first edit:** the cleanup itself lives entirely in the new migration file and its tests.
- **Licensed by P6-CLEANUP-AUDIT (answered 2026-11-02), exactly the item 3 edits:** `core/migrations.py` (return the counts from `config.attributes` through `run_profile_migration` / `_async`), `core/profile_database.py` (one field on `ProfileDatabaseConnection` carrying them), and `api/profiles.py` (one `profile.fk_orphan_cleanup` audit write at each of `:331`, `:406`, `:757`, `:1094` when the total is non-zero). Any other non-comment change to those files is not licensed.
- **Licensed by L0 ruling on #454 (2026-11-03):** `reset_synthetic_test_profile` calls `purge_pre017_snapshot`. The owner's rule is that the snapshot goes with the profile's data, and a reset removes that data; it is not the withdrawn rotation purge. L0 lists it for the owner in the P6-CLEANUP-DIFF.
- **Licensed by L0 ruling on #454 (comment 6603412162, 2026-11-03, Codex's three findings on `2d470854`):** `core/migrations.py` and its tests, plus `docs/compliance/data-privacy.md` for the retention wording; never `core/audit.py` or `core/auth.py`. (1) The snapshot age purge moves after the migration succeeds and the vault is confirmed at revision 017 or later; a vault already at head still purges on open; a refused or failed migration keeps the snapshot at any age (consequence, for the owner: a vault that cannot complete 017 keeps its snapshot past 30 days, until it completes or the profile is deleted). (2) A snapshot that fails verification is never overwritten and never deleted: it and its sidecars move aside to one fixed name, byte for byte, then a new snapshot is taken; if the aside name is occupied, refuse with the existing log-only refusal, touching nothing; the aside file falls under the 30-day purge, `purge_pre017_snapshot` and profile deletion, with a sweep of anything else that enumerates the vault directory or these names. (3) Non-empty means any user table (excluding `alembic_version` and the derived search-index tables the schema match already ignores, `96dab82d`): every non-empty unversioned file goes through `_match_unversioned_vault`; no match means refuse with no write and no stamp (inside P6-STAMP). Tests RED first with deliberate breaks, the full suite, the security-lens review and a Codex adversarial review of the new head; the PR stops as `[blocked:claude]` awaiting P6-CLEANUP-DIFF, with the owner ask rewritten at the final head.
- **L0 ruling on #454 (comment 6615915762, 2026-11-03, IOERR and the round 3 findings):** (1) IOERR (10) is not damage: it leaves `_DAMAGE_RESULT_CODES`, so an unreadable snapshot is refused like PERM and CANTOPEN and nothing is moved; the report's "IOERR 10 (L0 ruling)" label goes, the two HC-FKS-026 IOERR cases move to the refuse list, RED first (a behaviour change by ruling, not a relaxed test); cost, which L0 states to the owner in the P6-CLEANUP-DIFF ask: a persistent fault on the first read keeps the vault closed until the fault is repaired. (2) A mid-file fault still reports CORRUPT 11 and still moves the file (kept, not deleted); `data-privacy.md:103` says so in one sentence. (3) `data-privacy.md` `:120`, `:141-142`, `:326`: removing the aside files lets the open continue, the vault opens only if 017 then completes, and if 017 still fails it stays closed and the removed file may be the only intact pre-017 copy; a third closed state at `:141-146` and `:325-329` (an unreadable snapshot keeps the vault closed until the fault is repaired); `:106` "The aside file follows". (4) Test and comment minors: skip the mid-page flip case when `is_sqlcipher_available()` is false; skip `_no_free_fds` when `/proc/self/fd` is absent; the CORRUPT_VTAB id is `11 | (1 << 8)` (267); fix the stale wording at `migrations.py:407`, `:212`, `test_fk_migration_017.py:2109`, `:2139`. A sweep lists any other place that treats IOERR or "a database error" as damage. Then stop as `[blocked:claude]`.
- **L0 ruling on #454 (comment 6626122374, 2026-11-04, Codex's `[high]` on `da5240bb`):** no code change; the purge stays as built and the choice goes to the owner. Under ruling 6603412162 item 1 the original snapshot, already aged, also purges on the first open after 017 succeeds, so in any late-success case the patient has no recovery window, with or without an aside file; P6-SNAPSHOT makes the retention rule L0's, shown to the owner in the final diff. `data-privacy.md:129-132` gets one or two sentences (the snapshot is a frozen copy of the vault as it was when taken; a replacement taken after a failed attempt is only as complete as the live vault it was copied from; a copy already 30 days old is removed on the first open after 017 completes, so no recovery window remains). Owner ask, under "Consequences to weigh", a numbered item with a choice: (A) as built, copies purge on their own age; (B) restart the 30 days when 017 succeeds by resetting the mtime of both copies, bytes unchanged (a recovery window always exists, deleted documents stay readable up to 30 days longer, and the head moves again); the ask states from `upgrade()` what a partly cleaned vault could have lost, and L0's recommendation goes in after L0 reads that list. Readings in 6624975683: (1) and (2) correct, (3) correct (list, do not edit), (4) overruled: merge `origin/main` after the docs commit. The Frontend Tests failure (`window is not defined`, a sonner timer in `ui-care.test.tsx`) is judged by L0 after the merge reruns CI. Then stop as `[blocked:claude]`; L0 runs the FK audits on that head and takes P6-CLEANUP-DIFF to the owner. **Answered 2026-11-04 (owner row P6-RETENTION, the reading is L0's): (A) as built.** L0 recommended B; the owner chose A knowing that (a partly cleaned vault could lose `observations` and `doses_taken` rows). No mtime reset is added, and the retention rule P6-SNAPSHOT left to L0 is settled as built for this case. P6-CLEANUP-DIFF answered "Yes, merge it" the same day; #454 merged as `4ea62500`.
- **Not touched under any answer:** `core/auth.py`, `core/audit.py`, `core/security.py`, `scripts/backup.py`.
- **Escalate:** if the implementer finds that the cleanup or the listener needs any other ask-first line, it stops and escalates. It does not fold that line into this row.

**7. Gates.** **P6-CLEANUP-SETNULL** and **P6-CLEANUP-AUDIT** were answered 2026-11-02 (both recommended options), so the build needs no further pre-start answer. The merge waits on the merge-only gate **P6-CLEANUP-DIFF**: L0 shows the owner the exact cleanup diff (the `_CLEANUP_CHECKS` tuple, the delete statements, the P16/P17 null updates, the pass loop, the log lines and the audit plumbing), and the owner says yes before merge.

#### Delta 2026-11-02 (L0 ruling on #454, comment 6591885248): owner answers to the C-P6 questions

**Source:** owner rows P6-P8P12, P6-SNAPSHOT, P6-STAMP and P6-LOGIN-AUDIT ([owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md), answered 2026-11-02 in chat to L0). These are direction, **not** the P6-CLEANUP-DIFF yes: the exact new diff goes back to the owner, and #454 does not merge before that yes. Item 4 (login fail-closed, no code change) is in the queue row.

1. **P8 and P12: "Keep, clear the link (Recommended)".** Both join `_REPAIR_SET` next to P16/P17: doses and reminder logs are kept with `schedule_id` NULL, not deleted. HC-FKC-001 and -002 are updated. The PR body says which rows `upgrade()` can still delete after this, with the counts of the checks. This narrows item 2 above ("Children only") for P8 and P12.
2. **Backup: "Snapshot first (Recommended)".** Licensed: `core/profile_database.py`, `core/migrations.py` and the profile-delete and reset paths needed for the purge. Before revision 017 runs on an existing non-empty vault: copy the encrypted vault file after flushing the WAL, verify the copy opens with the same key and passes `PRAGMA quick_check`, then migrate. If any step fails, refuse the migration, leave the vault untouched and return the existing open-failure path with a clear message. A vault with no pending 017 takes no snapshot. The retention rule is L0's, not the owner's words, and the owner sees it in the final diff: the snapshot lives in the profile's own folder, one per profile, never decrypted or written in plain text; every path that deletes or resets the profile deletes it (a test for each, plus a sweep for other paths that remove a vault file, recurring failure 9); it is purged on the first open 30 days or more after it was made; no purge on password or recovery-code rotation (withdrawn, comment 6592196350: rotation re-seals the same DEK, and no rekey path exists), and no edit to the rotation routes or `api/backup.py`; it is excluded from backups and exports unless a backup copies the folder wholesale, in which case the implementer stops and tells L0; `data-privacy.md` states all of this. If it needs `core/audit.py`, `core/auth.py` or an encryption change, stop and tell L0. Tests: a real snapshot on a pragma-OFF 016 fixture; a corrupt or unwritable snapshot refuses and leaves the vault at 016; each purge; deliberate breaks RED. This is the only recovery for the rows and links that item 4 of Delta 2026-11-01 says nothing else restores.
3. **Old vaults: "Fix in this PR (Recommended)".** The `core/migrations.py` stamp logic is licensed (ask-first, owner yes). An unversioned vault is no longer stamped straight to head (`core/migrations.py:299-307`, the profile DB baseline): detect the schema, stamp the newest revision it actually matches, then upgrade through 017; if it matches no known revision, refuse rather than guess and say so in the log. Vaults created from scratch must still reach head. Regression test through `route_client`: an unversioned pre-017 vault with P14-P17 relationships and planted orphans opens, is aligned and cleaned, a document delete succeeds, and the snapshot rule applies to it.

**Correction (L0, comment 6592196350, on the Task 0 stop of comment 6592076162).** Item 2's rotation purge is withdrawn (above) and the backup question is answered option (b): no edit to `api/backup.py`; the 30-day purge covers a restore, and `data-privacy.md` says plainly that a snapshot can survive a restore. Accepted as Task 0 proposed: the refusal message goes to the log only (`core/auth.py` stays off limits; the patient sees the existing fixed 500); the snapshot is named `vault.pre017.snapshot`, never ends in `.db`, with a test that a real backup leaves it out; its time is set explicitly and compared with `core.time`; temp name, fsync, verify with the key and `quick_check`, then `os.replace`; an unversioned vault is snapshotted before `stamp`; schema match compares tables, columns and FK actions, with a test that all 17 fingerprints differ; `/test/reset` purges explicitly; tests go in `test_fk_migration_017.py` or `test_fk_enforcement.py`; P8 and P12 join `_REPAIR_SET` (4 repair checks and 14 delete checks). The PR body shows the owner in the final diff: (1) the rotation purge was withdrawn, and why; (2) the new recovery trigger: `recover_profile` commits the new password and rotated code before opening the vault (`api/profiles.py:791`), so a refused snapshot returns 500 and that new code is lost; (3) strict matching can refuse a real pre-Alembic vault that matches no revision: login returns 500 with the data untouched, and no such vault exists to measure.

Sonnet implements; the security lens reviews and Codex re-reviews if available. The PR stops as `[blocked:claude]` "awaiting P6-CLEANUP-DIFF owner yes" with the exact new diff in the body. Migration number: recheck at the final merge of main. The queue row's file cell, the `test_care_tasks.py` limit and the rollback wording at `:97` were corrected in the same docs batch as this delta.

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
   | 017 | `fk_cascade_alignment` | C-P6 | measured 2026-11-01: `013`-`016` merged first (D-2, C-GAM2B, RSI1-DONATE, `016_strict_safety_mode`); see Delta 2026-11-01 |
   | 014 | `streaks_hidden` | C-GAM2B | may land before C-P6 (owner-accepted race) |
   | 015 | `export_artifacts` | C-GC1 | W11b hard-codes `014`; its Task C1.0 re-measures |
   | 016 | `wearables` | WEAR-02 (#94) | |
   | 017 | `symptom_journal` | WEAR-15a (#94) | after WEAR-02 |
   | — | `audit_outbox` | AUDIT-ORDER option B | **withdrawn**: the owner chose design D (AO-DESIGN, `owner-decisions-2026-09-27.md:93`; AO-ASKFIRST "no migration", `:101`); merged as #78 with no migration. Wearables plans 00/02/15 still list `015_audit_outbox`; drop it on their next refresh. |

4. **Second lander renumbers:** rebase, rename the file, update `revision`, `down_revision`, the docstring and the head literal, then re-run its round-trip test. Never edit a merged migration file.
5. **Head literal:** every new profile migration moves the head, so every migration PR updates it, data-only ones (D-2) included. Before C-P6 merges, update the 4 literals (`tests/test_care_tasks.py:808,824`, `tests/test_profile_migrations_sqlcipher_fallback.py:41`, `tests/test_source_spans.py:312`, on `094b81c9`); these tests go red otherwise. After C-P6, update one constant: `src/backend/tests/support/migrations.py::PROFILE_HEAD: str`.
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
| FK actions | `document_category.doc_id`, `document_entity.doc_id` → CASCADE; `care_plan_task.source_document_id`, `.source_entity_id` → SET NULL | C-P6 (`017`) |
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
| P6-ORPHAN | After Task 1's report: proceed to `013`, clean orphans first (each its own approval), or stop? | depends on report | answered 2026-11-01 by P6-ORPHAN-SYNTH (synthetic vault, all checks 0) and P6-CLEANUP ("Proceed, migration cleans"); see Delta 2026-11-01 |
| P6-CLEANUP-DIFF | Merge-only: yes to the exact cleanup diff in migration `017` | yes if the diff matches the delta | named 2026-11-01, asked with the PR |
| P6-CLEANUP-SETNULL | P16/P17 orphans are care tasks whose D5 action is SET NULL: delete them (rule as worded) or null the dangling reference and keep the task? | null, keep the task | answered 2026-11-02: "Keep task, null links (Recommended)" |
| P6-CLEANUP-AUDIT | Write a master audit row for a non-zero cleanup (edits beyond the D5 / P6-Q1 licence), or log only? | audit row | answered 2026-11-02: "Yes, write audit row (Recommended)" |
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
