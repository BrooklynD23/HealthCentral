# Build Program 2026-10-15 — Cross-Lane Contracts

**Last Updated:** 2026-10-15
**Owner:** repository owner
**Status:** PROPOSED (L0 contracts reconciler). Binding on lanes A–F once the owner or L0 adopts this build program. **No owner approval is recorded here.** Every gate named below keeps the state it has in [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md). Rulings marked **OWNER** need an owner answer; the rest are L0 rulings.
**Refresh Trigger:** any merge of #95, #97, #99, #82, #84, #74, #72, #94 or #68; any lane-doc edit; a merge of any item named in §a; a new file under `src/backend/migrations/*/versions/`; an owner answer to a gate in §e.
**Base measured:** `origin/main` @ `3b2236c` (2026-10-15). Collected slot **1574** (`CLAUDE.md:30`, `:34`; `AGENT.md:76`). pytest was not run here.

Inputs: lane docs [A](lane-A-rag-assistant.md), [B](lane-B-interpretation-eval.md), [C](lane-C-schema-lifecycle.md), [D](lane-D-time-meds-gamification.md), [E](lane-E-privacy-gates-ci.md), [F](lane-F-docs-owner-wearables.md) and their peer-review sections. Execution order lives in [queue.md](queue.md).

Path shorthand: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`. "Rebase" in this program (and in [queue.md](queue.md)) means `git merge origin/main` into the PR branch, never a history rewrite: no force-push (RUNBOOK §9 rule 6; owner PR68-SYNC chose merge over a force-push rebase).

---

## a. Interface contracts

A consumer codes against the signature in this table, never against a lane doc's prose. A provider that has to change a signature stops and raises it with L0 before merging. "Pin" is the test that fails if the contract breaks.

| # | Provider | Symbol / path / signature | Consumers | Pin |
|---|---|---|---|---|
| I-1 | #95 (merged by D-0) | `be/modules/rag.py::_parse_filter_date(value: str) -> Optional[datetime]`, naive UTC, `None` on `ValueError`/`TypeError`/`OverflowError` | W-3 (adjacent hunks), ASSIST-AGENT-DATES | `be/tests/test_assist_utc_http.py` |
| I-2 | #72 (W-4) | `api.assistant._legacy_serve_or_abstain(result: ValidatedResponse) -> ValidatedResponse`; `scripts/legacy_eval_gate.py` (repo root, per #72's diff); CI job id `legacy-evals`; `be/tests/legacy_eval/harness.py` | W-3 Task 7, G-C5 (byte-identical proof), B-3 (adds an ALLOW judge fake to the harness), B-8, F-5 F4 trigger | `legacy-evals` CI job |
| I-3 | #97 | `PatternLearner.calculate_streak(..., tz_name: str = "UTC")`, `learn_time_window(..., tz_name: str)`; `adherence_patterns._local` (replaced by I-6 `to_local` in D-1) | D-1, D-2 | `be/tests/test_adherence_patterns_tz_http.py` |
| I-4 | #99 | `async api.medications._schedule_for_medication(profile_db: AsyncSession, schedule_id: str, medication_id: str) -> Optional[MedicationSchedule]`: `None` for an unknown id, HTTP 422 when the schedule belongs to another medication (shifts `medications.py` by +19 from `:70`) | D-1, D-2 | `be/tests/test_medications_routes_http.py` |
| I-5 | #84 | `api.gamification` `get_streaks` with `compute_engagement` | D-3, C-GAM2B | `be/tests/test_gamification_api.py` |
| I-6 | D-1 | Appended after `core/time.py:27` (cited lines `:12`, `:17`, `:27` do not move): `safe_zone_name(name: str \| None) -> str`; `to_local(value: datetime, tz_name: str) -> datetime` (aware); `local_day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]` (naive UTC, half-open); `async profile_timezone_name(profile_db: AsyncSession, profile_id: str) -> str` (`"UTC"` when there is no row) | D-2, D-3, WEAR-02/03/11/12 (#94) | `be/tests/test_time_source.py` (D-1 adds the cases) |
| I-7 | C-PMIG (lane C §3.0) | Profile revision = file stem = `f"{NNN:03d}_{slug}"`, `NNN` = head on `origin/main` at the PR's final rebase + 1, `down_revision` = that head. Allocation in §c | D-2, C-P6, C-GAM2B, C-GC1, WEAR-02, WEAR-15a | §c check commands; `be/tests/test_migration_heads.py` HC-MIGHEAD-001 after E-3; chain walk `be/tests/test_care_tasks.py:795-826` |
| I-8 | C-P6 | `be/tests/support/migrations.py::PROFILE_HEAD: str`; `core.database.install_sqlite_foreign_keys(sync_engine) -> None` (master + profile engines; migration engines stay OFF); `core.fk_audit.FkCheck`, `MASTER_CHECKS`, `PROFILE_CHECKS`, `find_orphans`; `tests.support.db.fk_profile_engine() -> AsyncEngine` | every later migration PR; WEAR-02 (one `PROFILE_CHECKS` row per new FK, explicit `ondelete=`) | HC-FKA-004 in `be/tests/test_fk_audit.py`; `be/tests/test_fk_enforcement.py` |
| I-9 | C-P7 | `tests.support.routes.route_client(router, prefix, profile_id="profile-a", master_db=None, raise_server_exceptions=True, profile_name: str = "T", profile_db: Optional[async_sessionmaker] = None)`, both keywords **appended**; existing callers unchanged. `api.profiles._SYNTHETIC_RESET_MODELS: tuple[type, ...]`, child-first | E-2 (needs `profile_db`; STOPs without it), C-GC1 and WEAR (append to the tuple under RESET-APPEND); B-5 and lane-A tests only read `route_client` | HC-RESET-010 in `be/tests/test_profile_test_reset.py` |
| I-10 | E-1 (W-2) | `ExportModule.redact_summary_data(self, summary_data: dict) -> dict` in `be/modules/export.py`: returns a new strict-redacted copy with `redaction_count: int`. `POST /export/doctor-summary` stores only that copy. CSV/JSON bytes unchanged | C-GC1 (persists only redacted summaries), F-5 F2 trigger, F-6 | HC-EXPR-001/002/003 in `be/tests/test_export_redaction.py` |
| I-11 | E-3 (W-11a PR-3) | `be/tests/test_migration_heads.py` HC-MIGHEAD-001…003 (structure, not names); `ci.yml` job and step names as in lane E §3 item 2 | C-PMIG check (replaces the manual heads command), W-8 (model-fetch step goes before `Run backend tests (with coverage report)`) | HC-MIGHEAD-001…003; CI required-check list |
| I-12 | lane E (after #78) | Any cross-profile 403 route test patches `core.database.async_session_maker` to the test master maker, clears `core.denial_audit._state`, and asserts exactly one `denial.cross_profile` row | E-1, E-2; any later test that makes a 403 (no lane-A test does today) | HC-EXPR-003, HC-PGUARD-001…006 |
| I-13 | W-3 | `api.observations.TrendPoint.user_verified: bool = False`; `fe/services/types.ts` `TrendPoint.user_verified?: boolean`; `UNVERIFIED_LABEL`, `TrendPointDot`, `UnverifiedTrendNote` from `fe/components/TrendVerificationMarkers.tsx`; legacy RAG filter written literally as `Observation.user_verified == True` (or `.is_(True)`) in `be/modules/rag.py`. If it is written another way, the PR body names the exact line (R-20). Consequence: a test that drives the real legacy `rag.query` or `_build_knowledge_fallback` sees only rows it seeds with `Observation.user_verified=True` and `Document.status="verified"`; W-3 sets the flag in the HC-ASSIST-UTC-001 fixture (plan delta 10) | F-5 F1 trigger, F-6 (W-10b), B-6 (context half) | HC-VER-001…005 in `be/tests/test_verified_only_consumers.py`; HC-VER-FE-001…003 |
| I-14 | W-8 | `modules.embeddings.EmbeddingModelUnavailableError(RuntimeError)`; `local_files_only=True` on each load call; `core.config.settings.embedding_model_path`; `download_models.py embedding` subcommand; `modules.rag.EMBEDDING_UNAVAILABLE_MESSAGE` | G-C5 (if Q5b = A, loader and download pattern), F-5 F5 trigger | `be/tests/test_embedding_bundle.py`, `be/tests/test_embedding_fail_closed_paths.py` |
| I-15 | B-3 | `be/modules/agent/guardrails/advice_judge.py::advice_judge(text: str, runner: ModelRunner) -> Literal["ALLOW","BLOCK","UNAVAILABLE"]` (async), `FROZEN_PROMPT: str`, local runner only; `ValidatedResponse.prohibited_reason: str` (`"prohibited_pattern"` default, `"advice_judge"`, `"advice_judge_unavailable"`); any result other than `ALLOW` withholds the answer (fail closed, owner PARA-R3-Q2Q3 `owner-decisions:117`), and no consumer may serve it; `RAGModule.query(..., judge_runner: Optional[ModelRunner] = None)`, default `get_model_runner()`, never the answer `model_runner`; audit `details.reason`; `core/audit.py` not edited | B-4/MM-2, B-5, every test that drives the real `RAGModule.query` (R-2) | `be/tests/test_advice_judge.py`; B-3 RED list |
| I-16 | RAG-RUNTIME-500 | `POST /interpretations/observations/{id}/interpret-grounded` returns 503 with a fixed detail (no exception text) on `RuntimeError` from `rag.query`; the 501 `ModelUnavailableError` path is unchanged | B-5 (rebases; W-7's own route maps runner `RuntimeError` to its template fallback, W07 `:551`, `:1021`) | 1 `route_client` test in `be/tests/test_safe_interp_grounded.py` |
| I-17 | B-5 (W-7) | `POST /api/v1/interpretations/observations/{observation_id}/interpret-tiered?force_regenerate=bool` → 201 `InterpretationResponse`; HC-AUD-ORD-030 row `generate_tiered_interpretation = A2`; `model_selector.py` no longer imports `llama_cpp` | F-5 F3 trigger | `be/tests/test_interpret_tiered.py`, `be/tests/test_llm_import_boundary.py`, `be/tests/test_audit_order_guard.py` |
| I-18 | ASSIST-AGENT-DATES | Amended 2026-10-17 (owner AAD-ROW + AAD-SEMANTICS; the dates-only form was never built): `modules.agent.state.ChatFilters` (pydantic, frozen, hashable): `from_dt`, `to_dt: datetime \| None = None` (naive UTC, via `modules.rag._parse_filter_date`), `analytes: tuple[str, ...] = ()` (selected ∪ panel members, lowercased, sorted), `category: str \| None = None`; `modules.agent.graph.RunContext.filters: ChatFilters = ChatFilters()`; `modules.agent.cache.CacheKey.filters: ChatFilters = ChatFilters()` (empty filter ⇒ the pre-change key); `api.assistant._serve_via_agent(question, profile_id, profile_db, db, filters: ChatFilters \| None = None)`. No other consumer: on `aed9d50`, `git grep "_serve_via_agent(\|RunContext(\|CacheKey("` finds only `api/assistant.py` (the one call site), `modules/agent/eval/scorer.py:319` and tests constructing `RunContext`/`CacheKey` with keyword args, all of which keep working on the defaults; nothing reads `from_date`/`to_date` on these types | lane A only (internal) | `be/tests/test_assist_agent_dates_http.py` HC-AAD-001…012 |
| I-19 | C-GAM2B | `UserModelSettings.streaks_hidden: bool = False`; `GET`/`PATCH /settings/model/gamification` `{streaks_hidden: bool}`, audited `settings.gamification.view` / `.update` | frontend Settings switch, E-4 drift scan | `be/tests/test_gamification_settings.py` |
| I-20 | C-GC1 | `models.export_artifact.ExportArtifact(id, kind, profile_id, payload_json, created_at)`; `EXPORT_ARTIFACT_KINDS`; `api.export._save_artifact` / `_load_artifact` (keyword-only) | WEAR export paths (#94) | `be/tests/test_export_artifact_persistence.py` |
| I-21 | lane F | Variant-I evidence: W-2 HC-EXPR-003 and W-3 HC-VER-002 call `route_client` inside their own test body; the merged PR body pastes red-first output per new test id and ≥ 1 break-it run. Otherwise `data-privacy.md` stays U | E-1, W-3 PR bodies → F-6 | F-6 reviewer check |
| I-22 | lane F | F-trigger commands F1–F5 (lane F §3 item 3); all return 0 hits on `3b2236c` | each provider runs its trigger after merge and tells lane F | the grep itself |

---

## b. Shared-file edit order

This extends "Shared files are ordered as follows" in [implementation-program.md](../../capstone-report/implementation-program.md) (`:137-161`); that file is not edited here. Where a row below differs from the program list, the row below wins once this build program is adopted, and the orchestrator records it in its next program refresh.

**General rules**

1. At most one **non-draft** PR open per file. The second lander merges `origin/main`, re-greps its anchors by symbol, re-runs its tests and re-measures (§d).
2. **Parked draft (R-5):** a draft PR that waits only on an owner gate does not hold its files. It rebases onto each landing and leaves draft only after a final merge of main. Today this applies only to B-3 (waits on B-4). **OWNER** may veto (§e, owner list item 1).
3. **Exempt from the no-shared-file rule:** the collected-count slot lines (`CLAUDE.md:30`, `:34`, `AGENT.md:76`), which follow §d. Also `docs/INDEX.md` and `docs/_link_graph.json`: on conflict, regenerate with `scripts/generate_docs_index.py`; never hand-merge them.
4. "Own rows" files: each claimant edits only its own row or section, and no claimant ever ticks an owner box.

**Order per file** (→ = must merge before; `{}` = any order)

| File | Order | Supersedes program line |
|---|---|---|
| `be/modules/rag.py` | #95 → W-3 → W-8 → G-C5. B-3 floats (parked draft, R-4) | `:144` (W-5 merged) |
| `be/api/assistant.py` | #72 → W-3 (Task 7) → G-C5. ASSIST-AGENT-DATES any slot after #95. SAFE-CHAT-FALLBACK B / SAFE-CHAT-HISTORY B only if the owner picks them. B-3 floats | `:145` |
| `be/api/interpretations.py` + `be/tests/test_safe_interp_grounded.py` | {B-2, B-6, RAG-RUNTIME-500} in the order their gates are answered, one non-draft at a time → B-3 (floats) → B-5 last (R-3) | `:149` |
| `.github/workflows/ci.yml` | E-3 → E-4 (#74) → #72 → W-8. E-3 and #72 may swap (R-8) | `:142` (drops W-4 → W-11a PR-3) |
| `docs/architecture/ci-and-quality-gates.md` | {E-3 Task 9 (`:19`, `:45`), F-5 F4 (LEGACY node + row), W-8 (`:58`)}; own lines only (R-8) | `:143` (drops W-8 → F4) |
| `be/tests/support/routes.py` | C-P7 → E-2. B-5 and lane-A tests only read it | `:141` (unchanged) |
| `be/api/profiles.py` | C-P6 (comment) → C-P7 → {E-2, C-GC1, WEAR RESET-APPEND / OW-W12} | `:140` (P5 merged) |
| `be/migrations/profile/versions/` + head literal (4 literals before C-P6, `PROFILE_HEAD` after) | merge order under C-PMIG (§c) | new |
| `be/tests/test_audit_order_guard.py` | {C-GAM2B, C-GC1, E-2, B-5}, own CLASSIFICATION rows; each runs the file after its rebase (R-9) | new |
| `be/tests/test_documents_api.py` | {C-P6, C-DUPAUD}; second lander rebases | new |
| `fe/pages/SettingsPage.tsx` | #84 → C-GAM2B; #74 → B-1; C-GAM2B either side of #74 and B-1 (R-10) | new |
| `fe/components/medication-coach/AchievementsWidget.tsx` | #84 → C-GAM2B; #74 either side | new |
| `fe/pages/TrendsDashboard.tsx` | #74 → W-3 Task 5 | new |
| `fe/components/layout/Sidebar.tsx`, `fe/services/index.ts` | #74 and #84 → WEAR-10 / 07b / 08b / 15b | new |
| `be/core/time.py` | D-1 (append after `:27` only) → WEAR plans; lane F refreshes WEAR-03 citations once after D-1 | new |
| `be/modules/notification_scheduler.py`, `be/modules/adherence_patterns.py`, `be/api/medications.py` | #97 → #99 → D-1 → D-2 | new |
| `be/api/gamification.py` | #84 → D-3 | new |
| `be/modules/export.py`, `be/api/export.py` | E-1 → C-GC1 → WEAR export plans | `:146-147` (P5 merged) |
| `be/modules/embeddings.py`, `be/core/config.py`, `config/.env.example`, `be/scripts/download_models.py` | W-8 → G-C5 | `:152-153` (tail) |
| `be/core/audit.py` (`STRING_DETAIL_KEYS`) | {C-DUPAUD, WEAR-D4 / OW-W11 exact diffs}; second lander re-anchors without changing content | new |
| `be/scripts/seed_knowledge_base.py` | lane A only (SAFE-CHAT-FALLBACK C = B-2 (c), R-1) | new |
| `be/tests/legacy_eval/harness.py`, `be/tests/test_safe_chat_prohibited.py` | #72 → B-3 | new |
| `.gitignore` | F-10 (#68) → W-8; own lines only | `:155` (W-1 merged) |
| `be/tests/test_assist_utc_http.py`, `be/tests/test_verified_only_consumers.py` | #95 / W-3 own them; B-3 edits them only to add ALLOW judge fakes (R-2) | new |
| `be/tests/test_claude_agent_definitions.py` | F-10 (#68) → E-6 optional fix | new |
| `docs/features/TASK_LIST.md` | own rows (rule 4) for E-3, C-P6, C-DUPAUD (a), B-9, F-1, F-13, #84, #68; B-9 does **not** wait for F-13 (R-11) | `:158` |
| `docs/capstone-report/implementation-program.md` | E-7 (`:488-489` only), E-5, orchestrator refresh (Sign-off column); own rows | `:159` |
| `docs/capstone-report/claims-ledger.md` | W-8 → F-9 | `:159` |
| `docs/architecture/pipelines.md` | F-1 → F-5 {F1, F2, F4} serial | new |
| `docs/architecture/README.md`, `docs/architecture/backend.md` | F-3 → F-5 {F3, F5} serial | new |
| `docs/compliance/data-privacy.md` | F-6 (W-10b status lines) → WEAR-14 | `:157` |
| `CS4610_Report_Demo/README.md` | F-10 → F-9 | new |

---

## c. Migration revision allocation

**Profile chain** (`be/migrations/profile/versions/`). Head on `3b2236c`: `012_pinboards` (verified: `ls` and the 4 literals at `test_care_tasks.py:809,825`, `test_profile_migrations_sqlcipher_fallback.py:41`, `test_source_spans.py:313`). Numbers go by **merge order**, so nothing is reserved. Peers cite slug + "head+1 at final rebase".

| Slug | Item | Kind | Expected position (illustrative, from [queue.md](queue.md)) |
|---|---|---|---|
| `adaptive_windows_local` | D-2 | column `medication_schedules.adaptive_window_tz` (nullable, re-learn marker) + `UPDATE … windows = NULL`; downgrade drops the column (lane D §D-2 rev 2) | likely first → `013` |
| `streaks_hidden` | C-GAM2B | column | Wave 9 pool |
| `fk_cascade_alignment` | C-P6 | batch rebuild, FK actions per D5 | Wave 10 |
| `export_artifacts` | C-GC1 | new table (+ RESET-APPEND, `PROFILE_CHECKS` row) | Wave 14 |
| `wearables` | WEAR-02 (#94) | new tables | after M0 |
| `symptom_journal` | WEAR-15a (#94) | new table, after WEAR-02 | after M0 |
| ~~`audit_outbox`~~ | AUDIT-ORDER B | **withdrawn** (AO-DESIGN = D, merged as #78 with no migration) | — |

Every migration PR, data-only ones included:
1. Names its file and `revision` `NNN_<slug>` at its final rebase; `down_revision` = head on `origin/main`; docstring `Revision ID:`/`Revises:` match.
2. Updates the head literal in the same PR (4 literals before C-P6; `PROFILE_HEAD` after).
3. Passes both checks before merge:
   ```bash
   cd src/backend
   grep -h "^down_revision" migrations/profile/versions/*.py | sort | uniq -d   # must print nothing
   ~/venvs/asclexis-311/bin/python -c "from alembic.script import ScriptDirectory; from core.migrations import _get_alembic_config as c; print(ScriptDirectory.from_config(c('profile')).get_heads())"   # exactly one head
   ```
   After E-3 merges, HC-MIGHEAD-001 replaces the second command.
4. Never edits a merged migration. The second lander renames its own file.
5. After C-P6: every new FK declares `ondelete=` and gets a `PROFILE_CHECKS` row. After C-P7: every new table is appended to `_SYNTHETIC_RESET_MODELS` (ask-first `api/profiles.py`, gate RESET-APPEND).

OW-W13 (owner order confirmation) is **not** needed for numbering; see R-13.

**Master chain** (`be/migrations/master/versions/`). Head on `3b2236c`: `002_backup_schedules`. **No item in lanes A–F or #94 allocates a master migration.** Any PR that adds one first adds a row here; the same head+1 and single-head rules apply with `c('master')`.

---

## d. Count-slot merge protocol

SLOT-RULE-2 (owner, 2026-10-16) supersedes ground rule 8 / SLOT-RULE (`owner-decisions-2026-09-27.md:31`). Baseline **1604** at `d64c3fb`.

1. **PRs never edit** the slots (`CLAUDE.md` "**N backend tests collected.**" and "if it differs from N", `AGENT.md` "N collected") or the table in `docs/reviews/README.md`. A PR adds its own review files only. **SLOT-RULE-2a (owner, 2026-10-16):** every PR regenerates `docs/INDEX.md` and `docs/_link_graph.json` (`python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`) because `test_docs_index_check_passes_on_real_repo` stays; on an index conflict, regenerate, never hand-merge.
2. **Measure, never predict.** Each PR still measures collection on its head and pastes the line, with its delta from the slot, into the PR body:
   ```bash
   cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 \
     ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1
   ```
3. **Post-merge batch (L0).** After one or more merges, L0 opens one `docs:` PR from fresh `origin/main` that re-measures with step 2, writes the number into all 3 slots and appends the review rows for the merged PRs. Nothing else goes in that PR.
4. **No merge sync for slots.** A PR merges main in for a real code conflict, a real code dependency, or an index conflict (then regenerate); never for the count slots.
5. **CI** also regenerates the index before `docs_lint.py`; the backend test still requires the committed index to be fresh (SLOT-RULE-2a).
6. **Stale slot is expected between batches.** An item that measures a start count different from the slot reports the delta and carries on; it never fixes the slot.

---

## e. Rulings on peer-review conflicts

| R | Conflict (lanes) | Ruling | Reason | Doc edit |
|---|---|---|---|---|
| R-1 | KB seed text: SCF-RULING C vs IBF-1 (c) (A↔B, MAJOR) | **Accept** lane A. Lane A owns `be/scripts/seed_knowledge_base.py`. The owner gets SCF-RULING and IBF-1 in **one** prompt. A seed rewrite is one lane-A PR, cited by both items | one file, one question, one PR | none (both lanes already amended) |
| R-2 | B-3 judge vs tests that fake the runner (A↔B ×2, MINOR) | **Accept**, combined. The second lander fixes it: B-3 re-takes its RED list at its final rebase (it already names `test_verified_only_consumers.py`, `test_assist_utc_http.py:98` and `legacy_eval/harness.py`). After B-3 merges, every new test that drives the real `RAGModule.query` passes `judge_runner=` explicitly. **No blanket bypass** (no env flag, no default ALLOW) | a bypass would weaken a safety check (CLAUDE.md §3) | none |
| R-3 | `api/interpretations.py` + `test_safe_interp_grounded.py`, 5 items (A↔B, MAJOR) | **Modify:** use lane B's file queue (§b). Lane A's "any order, all before B-5" fits inside it | 4 items append to one test file; one non-draft at a time keeps rebases small | none |
| R-4 | `rag.py` / `assistant.py` order with B-3 (A↔B, MAJOR) | **Modify:** lane B wins on B-3's position. Lane A's chain is #95 → W-3 → W-8 → G-C5. B-3 has no fixed slot, rebases on each landing, and lands when B-4 is signed. MM-2 stays valid only under lane B's freeze-validity rule (B-4 step 1) | B-3 cannot merge before the owner signs the B-4 numbers; a fixed slot would block W-8 and G-C5 indefinitely | lane A `:192-193` |
| R-5 | Parked draft (from R-3/R-4) | **New rule** (§b rule 2). Departs from program `:137` "No two open PRs edit the same file" for drafts only | a draft cannot merge, so it cannot race a merge | none; **OWNER** may veto |
| R-6 | W-7 (B-5) hard dependency on C-P6 → C-P7 (B↔C, MAJOR) | **Accept drop.** B-5's plan amendment (already in its file list) changes the W07 Task 0 ancestry check to P1 + P5 and keeps "re-read `route_client` at start". Program edge P7 → G-B (W-7) is dropped; the orchestrator records it | W07's only reason was "P7 may change `route_client`" (W07 `:94`, `:164`). C-P7 now appends two keyword args with defaults (I-9), and B-5 shares no file with C-P6/C-P7 | lane B `:17`, `:107`, `:190`, `:207`; lane C `:304` |
| R-7 | W-3 O-3 = B-6 IUV-1 (B↔A) | **Accept.** Asked once as IUV-1; the answer is recorded under both ids | duplicate question | none |
| R-8 | `ci.yml` order; `ci-and-quality-gates.md` W-8 vs F4 (A↔F, E) | **Accept** lane E: E-3 → #74 → #72 → W-8; E-3 and #72 may swap. `ci-and-quality-gates.md`: any order, own lines. Answers lane E Q-E1: yes, drop W-4 → W-11a PR-3 | the `ci.yml` hunks are disjoint, and #72 waits on an owner model run | none |
| R-9 | `test_audit_order_guard.py` (B↔C) | **Accept:** own rows, any order. The queue never runs two of {C-GAM2B, C-GC1, E-2, B-5} at once | HC-AUD-ORD-030 fails on any unclassified handler | none |
| R-10 | `SettingsPage.tsx` / `AchievementsWidget.tsx` (B↔C, C↔E) | **Accept** lane C: #84 → C-GAM2B; #74 → B-1; C-GAM2B may land on either side; E-4's drift scan covers the switch if C-GAM2B lands first | making C-GAM2B wait for TW4-SHOTS buys nothing | none |
| R-11 | `TASK_LIST.md`: B-9 vs F-13; 6+ claimants (B↔F, E) | **Modify:** own-row rule (lane E P-3) for all claimants. B-9 does **not** wait for F-13; lane B P-7 is superseded | the rows are disjoint; the wait added an owner dependency (#94) for no file reason | lane B `:174`, `:225` |
| R-12 | Profile `013` claim; head literals (C↔D, MAJOR) | **Accept** C-PMIG (§c) | already adopted by lane D | none |
| R-13 | Profile-migration order OW-W13 (C↔owner, F) | **Modify:** numbering needs no owner answer (merge order). OW-W13 is asked once as an optional confirmation covering all six slugs; until it is answered, merge order = readiness order | the order itself decides nothing that C-PMIG does not already handle | none |
| R-14 | `route_client` `profile_db` keyword (C↔E) | **Accept** (lane C restored it) | E-2 STOPs without it | none |
| R-15 | F-12 text "D-2 proposes 013" (D↔F) | **Accept** (lane F §2.12 already reads `NNN_adaptive_windows_local`) | — | none |
| R-16 | `core/time.py` vs WEAR-03 citations (D↔F) | **Accept:** D-1 appends only; lane F refreshes the WEAR-02/03/11/12 citations (`:12`, `:17`, `:27`) once after D-1 | anchors stay put | none |
| R-17 | E-1/E-3 waiting for the D-0 chain (D↔E) | **Accept:** no wait; §d | ground rule 8 needs only a recount at the final merge | none |
| R-18 | Code-slot budget (E→L0, MAJOR) | **Accept, L0 queue:** 2 code L1s box-wide. Wave 6 = E-1 + E-3; the next free slots go to B-3, then D-1; D-2 and D-3 run together only when both slots are free ([queue.md](queue.md)) | E-1/E-3 are ready, need no PR merges and share no file | none |
| R-19 | F-5 F2 trigger (E↔F) | **Accept** (`def redact_summary_data`) | the old grep already hits | none |
| R-20 | F-5 F1 trigger depends on how W-3 writes its filter (F↔A) | **Accept:** I-13 fixes the literal form, or the W-3 PR body names the line | trigger must fire | none |
| R-21 | F-10 count before #68 merges (F↔D) | **Accept:** §d steps 2, 3, 7 | — | none |
| R-22 | B-3 Codex plan review location (lane B OQ2) | **L0:** review §B-3 in place. If Codex returns REVISE with task-level gaps, the B-3 L1 extracts a `docs/plans/` file as the first commit on its branch | no new file unless needed | none |

### Reconciler edits

| Lane doc | Lines | Change | Ruling |
|---|---|---|---|
| A | `:192-193` | `rag.py` order is now #95 → W-3 → W-8 → G-C5, with B-3 floating; replaced the "one lane-A and one lane-B PR open" rule with §b rules 1–2 | R-4, R-5 |
| B | `:17`, `:107`, `:190`, `:207` | B-5 drops P6/P7 as hard dependencies; open question 1 resolved | R-6 |
| B | `:174`, `:225` | B-9 no longer waits for F-13 | R-11 |
| C | `:304` | open answer 5 marked as ruled | R-6 |

### Needs the owner

1. **R-5 parked draft:** may B-3 stay open as a draft PR on `rag.py`, `api/assistant.py` and `api/interpretations.py` while other PRs merge? Default if not vetoed: yes.
2. **R-1 / R-7:** ask SCF-RULING + IBF-1 in one prompt, and IUV-1 (= W-3 O-3) once.
3. **R-13 OW-W13:** an optional confirmation of profile-migration order; nothing blocks on it.
4. **R-6 / R-8:** program edges dropped (P7 → W-7; W-4 → W-11a PR-3; W-8 → F4). These are L0 rulings that the orchestrator records; the owner may veto.
5. **New item, not a conflict:** lane E Q-E3 (GATE-12). After #78, a 403 test that forgets the I-12 patch writes to the developer's real master DB (`be/data/asclexis.db`). No lane owns `tests/conftest.py`. Proposal: register it as an owner item, design only.

Back to: [queue](queue.md) · [implementation program](../../capstone-report/implementation-program.md) · [owner decisions](../../capstone-report/owner-decisions-2026-09-27.md)
