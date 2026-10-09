# AUDIT-ORDER + AUDIT-DENIALS — Audit Write Order and Denied-Request Auditing — Plan

**Last Updated:** 2026-10-09
**Owner:** repository owner
**Status:** PROPOSED — plan only, not approved for execution. Nothing in this plan is implemented. No owner question below is signed.
**Base measured:** `origin/main` @ `98bd3c7` (P5 `utcnow` swaps merged, PR #54). Every `file:line` below was re-read at this base on 2026-10-09 unless marked UNMEASURED. The readiness pack (`audit/2026-09-25/waves/scaffold/AUDIT-ORDER.md`) was measured at `6b4dd84`; its line numbers are superseded by this file.
**Refresh trigger:** any commit to `src/backend/core/audit.py`, `src/backend/models/audit.py`, `src/backend/core/database.py::get_db`, `src/backend/core/profile_database.py::get_session`, or any route in the §3 route table before an option is approved. Brief 4 (audit retention) being signed.
**Review:** none yet. L0 runs the Codex plan review (focus: failure atomicity across two databases, fail-open paths, PHI in any new audit or outbox column, migration order vs P6 and G-C1).

> **For agentic workers:** this file is a decision document. Do not execute any part of it until the owner signs AO-DESIGN, AO-FAIL, AO-SCOPE, AD-DENIALS and AO-ASKFIRST below. When an option is signed, a follow-up revision of this plan turns it into tasks with `- [ ]` steps (format precedent: [DDI plan](2026-10-04-DDI-doc-delete-interpretation.md)).

**Goal:** choose how a write route keeps its audit trail when the master-DB audit commit fails after the patient-data change is already durable, and whether denied requests (403/404) leave an audit row.

**Tech stack:** Python 3.11, FastAPI, SQLAlchemy 2.x async, SQLCipher per-profile vaults, unencrypted master SQLite DB, Alembic dual chains, pytest via `src/backend/tests/support/routes.py::route_client`.

---

## 1. Approval scope

| Item | Text | Source |
|---|---|---|
| Licence (verbatim) | AUDIT-ORDER, **Plan only**: "An architect writes a plan with options (audit-intent row first, outbox, or accept and document) plus a Codex review. It touches ask-first core/audit.py, so nothing is edited until you approve the plan. AUDIT-DENIALS is planned with it." | `docs/capstone-report/owner-decisions-2026-09-27.md:63` |
| AO-BRIEF4 (answered) | "Yes, assume today": "The plan is written now. Downside: if Brief 4 later changes retention, the plan's schema section needs an amendment." | answered in chat 2026-10-08, recorded on branch `docs/wave4-close` (not on `origin/main` at `98bd3c7`) |
| Program rows | AUDIT-ORDER `implementation-program.md:487`; AUDIT-DENIALS `:488`; AUDIT-KEYS-DROPPED `:472`; DOC-OVERCLAIM `:480`; DDI-ORPHAN-BIN `:498`; E2E-MASTER-CORRUPT `:502` | `docs/capstone-report/implementation-program.md` |

**Licensed by this plan:** nothing beyond this file. **Not licensed:** any edit under `src/`, `scripts/`, `config/`, `.github/`, any migration, `CLAUDE.md`, `AGENT.md`, any compliance doc.

**Assumption in force (AO-BRIEF4):** today's retention behaviour stands: audit rows are kept, and profile erase runs `delete(AuditLog)` for that profile (`src/backend/api/profiles.py:907-909`, statement on `:908`) then writes one row with `profile_id=None` (`:927-935`). **Open dependency:** if Brief 4 (`audit/2026-09-25/gated-items-decision-packet.md`, "Brief 4 — Audit Retention", `:204`) changes retention or purge-on-erase, §6 (schema and PHI of each option) needs an amendment before execution.

---

## 2. Measured evidence (`origin/main` @ `98bd3c7`)

### 2.1 Route 1: `DELETE /{document_id}` in `src/backend/api/documents.py`

| Line | What happens |
|---|---|
| `:1814-1820` | decorator and signature: `delete_document(document_id, session: RequireAuth, profile_db: ProfileDbSession = None, master_db: AsyncSession = Depends(get_db))` |
| `:1866-1870` | care-task provenance and quote cleared (`update(CarePlanTask)`) |
| `:1874` | `await profile_db.delete(document)` |
| **`:1875`** | **`await profile_db.commit()`** — patient-data delete durable |
| `:1882-1892` | encrypted file `{document_id}.bin` unlinked at `:1886`; `OSError` logged at WARNING without path (`:1887-1892`) and swallowed |
| `:1895-1901` | `log_document_event(db=master_db, event="delete", …)` — only `db.add` (see 2.3) |
| **`:1902`** | **`await master_db.commit()`** — audit row durable |

Pack lines `:1873/:1874/:1885/:1894-1900/:1901` moved by +1. Order confirmed: profile → file → master.

### 2.2 Route 2: `POST /{observation_id}/verify` in `src/backend/api/observations.py`

| Line | What happens |
|---|---|
| `:381-382` | decorator, `async def verify_observation(` (`profile_db` and `master_db` parameters) |
| `:459` | `observation.user_verified = True` |
| `:488-490` | parent document status set to `verified` |
| **`:492`** | **`await profile_db.commit()`** |
| `:495-506` | `log_observation_event(…, details={"changed_fields": …})` |
| **`:507`** | **`await master_db.commit()`** |

Pack lines `:458/:491/:494/:506` moved by +1. Order confirmed: profile → master.

### 2.3 Audit and session plumbing

| Fact | Evidence |
|---|---|
| `create_audit_log` scrubs action and details, builds the row, `db.add(audit_log)`; no flush, no commit | `src/backend/core/audit.py:201-266` (`_scrub_action` `:239`, `_scrub_details` `:240`, `db.add` `:252`) |
| The master DB is unencrypted; `create_audit_log` is the single PHI choke point (AUDIT-PHI-001) | comment `core/audit.py:23-32`; `ALLOWED_DETAIL_KEYS` `:89-109`; `_scrub_details` `:118-170` |
| `status` is already an allowed string detail key | `core/audit.py:70` (in `STRING_DETAIL_KEYS`) |
| `audit_and_commit`: `log_fn(...)` then `db.commit()`; docstring "a view that cannot be audited must not be served" | `core/audit.py:474-487` (call `:485`, commit `:486`, docstring `:479-484`) |
| Master session commits on normal dependency exit, rolls back on exception | `core/database.py:104-121` (`yield` `:115`, `commit` `:116`, `rollback` `:117-119`) |
| Profile vault session does the same | `core/profile_database.py:74-84` (`yield` `:79`, `commit` `:80`, `rollback` `:81-83`); wired by `core/auth.py:313-335`, `ProfileDbSession` `:339` |
| A locked or closed vault fails the dependency with 403 before the handler runs | `core/auth.py:298-310` (`HTTP_403_FORBIDDEN` `:306`, "Profile database not available") |
| `AuditLog` columns: `id`, `profile_id` (FK `profiles.id`, `ondelete="CASCADE"`), `event_type`, `action`, `entity_type`, `entity_id`, `details_json`, `client_info`, `timestamp`; no status, no correlation id | `src/backend/models/audit.py:32-62` (FK `:42`) |
| Alembic heads | master: `002_backup_schedules` (`migrations/master/versions/002_backup_schedules.py`); profile: `012_pinboards` (`migrations/profile/versions/012_pinboards.py`). Planned: P6 `013_fk_cascade_alignment`, G-C1 `014_export_artifacts` (`docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md:195`, `:255`) |
| A real audit-commit failure is on record | E2E-MASTER-CORRUPT, `implementation-program.md:502` (CI run 37453242129, `core/audit.py:486`); cause UNMEASURED |

**Consequence (measured on the two routes, then on every route in §3):** the two databases commit separately, profile first, with nothing linking them. If the master commit raises, `get_db` rolls back the audit row (`core/database.py:117-119`), the request returns 500, and the patient-data change stays.

**Hidden second commit path:** because `get_db` commits on exit (`core/database.py:116`), an audit row that is only `add`-ed is still persisted when the handler returns normally. An option that "forgets" the explicit commit still writes the row; one that raises after `add` loses it. Every option below must say which path it relies on.

---

## 3. Route table: every route with a profile-side mutation and a master audit write

Method: AST walk of every `@router.{post,put,patch,delete,get}` handler in `src/backend/api/*.py`, listing `.commit()`, `audit_and_commit`, `create_audit_log`, `log_*_event`, `_audit*`, `unlink`, `rmtree` calls, then each hit re-read; commits inside helper functions were followed by grep (`modules/interpret.py`, `api/documents.py` helpers). Paths are the decorator paths; router mount prefixes are UNMEASURED. "Irreversible" = the prior state cannot be restored from the product.

| # | Route (file) | Handler | Profile-side commit(s) | Master audit write → commit | Order | Reversible? |
|---|---|---|---|---|---|---|
| 1 | `POST /import` (`documents.py`) | `:407` | encrypted file written by `ingest.import_document` `:442`; `:476`; helpers `:592`, `:621`, `:688`, `:702` (`_run_extraction_pipeline`) or `:812` (`_run_structured_import_pipeline`); `:1016` (`_classify_and_extract_entities`) | `log_document_event` `:546` → `:554` | file → profile (×n) → master | yes (document can be deleted) |
| 2 | `POST /{document_id}/reprocess` (`documents.py`) | `:1148` | entities/categories deleted `:1195-1196`; helper commits as row 1; `:1227` | `:1229` → `:1242` | profile (×n) → master | **no** (prior entities, categories and extraction replaced) |
| 3 | `POST /{document_id}/verify` (`documents.py`) | `:1252` | `:1282` | `:1284` → `:1292` | profile → master | status change; an un-verify path is UNMEASURED |
| 4 | `PATCH /{document_id}/entities/{entity_id}/verification` (`documents.py`) | `:1423` | `:1453` | `:1455` → `:1468` | profile → master | yes (same route toggles) |
| 5 | `DELETE /{document_id}` (`documents.py`) | `:1815` | `:1875`; unlink `:1886` | `:1895` → `:1902` | profile → file → master | **no** |
| 6 | `POST /{observation_id}/verify` (`observations.py`) | `:382` | `:492` | `:495` → `:507` | profile → master | overwrites values; whether prior values are kept is UNMEASURED |
| 7 | `POST /accept` (`care_tasks.py`) | `:215` | `:309` | `log_care_task_event` `:311` → `:323` | profile → master | yes |
| 8 | `PATCH /{task_id}` (`care_tasks.py`) | `:329` | `:349` | `:351` → `:361` | profile → master | yes (editable) |
| 9 | `POST /` (`medications.py`) | `:315` | `:344` | `log_document_event(event="medication_create")` `:348` → `:356` | profile → master | yes |
| 10 | `DELETE /{medication_id}` (`medications.py`) | `:620` | hard delete `:649` or deactivate `:652-653`; `:656` | `:659` → `:667` | profile → master | **no** when `hard_delete`; yes otherwise |
| 11 | `POST /` (`memory.py`) | `:95` | `:126` | `audit_and_commit` `:129` | profile → master | yes |
| 12 | `PUT /{item_id}` (`memory.py`) | `:208` | `:240` | `audit_and_commit` `:243` | profile → master | overwrite |
| 13 | `DELETE /{item_id}` (`memory.py`) | `:261` | `:286` | `audit_and_commit` `:288` | profile → master | **no** |
| 14 | `POST /` (`pinboards.py`) | `:212` | `:221` | `audit_and_commit` `:222` | profile → master | yes |
| 15 | `PATCH /{pinboard_id}` (`pinboards.py`) | `:245` | `:255` | `audit_and_commit` `:256` | profile → master | yes |
| 16 | `DELETE /{pinboard_id}` (`pinboards.py`) | `:264` | `:272` | `audit_and_commit` `:273` | profile → master | **no** |
| 17 | `POST /{pinboard_id}/items` (`pinboards.py`) | `:282` | `:307` (rollback `:309`) | `audit_and_commit` `:313` | profile → master | yes |
| 18 | `DELETE /{pinboard_id}/items/{item_id}` (`pinboards.py`) | `:344` | `:363` | `audit_and_commit` `:364` | profile → master | yes (re-addable) |
| 19 | `POST /observations/{observation_id}/interpret` (`interpretations.py`) | `:358` | `modules/interpret.py:279` (old row deleted `:276` when `force_regenerate`) | `_audit_interpretation` `:410` (→ `audit_and_commit` `:53`) | profile → master | **no** on regenerate |
| 20 | `POST /observations/{observation_id}/interpret-grounded` (`interpretations.py`) | `:422` | `modules/interpret.py:279` via `:448` (comment `:460` says so) | `:462`; prohibited path `:549` | profile → master | as row 19 |
| 21 | `GET /observations/{observation_id}/interpretation` (`interpretations.py`) | `:571` | `viewed_at` set `:619`, `:620` | `:622` | profile → master | timestamp only |
| 22 | `POST /panels/{panel_name}/interpret` (`interpretations.py`) | `:634` | `modules/interpret.py:445` via `:660` | `:677` | profile → master | UNMEASURED (overwrite semantics of `interpret_panel` not read) |
| 23 | `POST /batch` (`interpretations.py`) | `:751` | `modules/interpret.py:279` once per observation | one row `:814` | profile (×n) → master | as row 19 |
| 24 | `POST /turns/{turn_id}` (`feedback.py`) | `:188` | `:237` | `_emit_audit` `:241` → own `get_db()` session `:44`, commit `:54`; **every exception swallowed `:56-57`** | profile → master, **fail-open** | yes |
| 25 | `POST /chat` (`assistant.py`) | `:730` | `:902` (fallback `:942`) | prohibited path only: `audit_and_commit` `:883` **before** `:902`; ordinary turns write no audit row in this handler | **master → profile** (prohibited path) | turns appended |
| 26 | `POST /{backup_id}/restore` (`backup.py`) | `:364` | no profile-DB session; vault and sealed keys overwritten on disk by `backup_script.restore` `:442` | partial: `audit_and_commit` `:452` before the 500; success: `:480` | files → master | via safety copies (`:462-473`); the master profile-row re-apply inside `scripts/backup.py` is partly read (`scripts/backup.py:60`), not walked |
| 27 | `DELETE /{profile_id}` (`profiles.py`) | `:773` | no profile-DB session; sealed key unlinked `:865`, vault `rmtree` `:882`, backups `rmtree` `:899` | `delete(AuditLog)` `:907-909`; `create_audit_log` `:927`; commit `:936` | files → master | **no** |

Not in the table: `POST /test/reset` (`profiles.py:477`, profile commit `:523`, `rmtree` `:520`) — synthetic E2E profiles only (`:491`), no audit row.

**Irreversible set (rows 2, 5, 10 hard, 13, 16, 19/20/23 on regenerate, 27):** these are the routes where a missing audit row cannot be reconstructed from the remaining data.

### 3.1 Write routes that commit profile data and write no audit row at all

Measured by the same walk (no audit call inside the handler). Whether a called helper audits is UNMEASURED except where noted.

| File | Handler → profile commit |
|---|---|
| `assistant.py` | `create_session` `:395` → `:411`; `delete_session` `:448` → `:465`; `update_memory_settings` `:504` → `:530`; `chat` `:730` ordinary turns → `:902` |
| `medications.py` | `update_medication` `:559` → `:609`; `create_schedule` `:680` → `:727`; `update_schedule` `:774` → `:833`; `delete_schedule` `:843` → `:883`; `log_dose` `:896` → `:956`, `:1014`; `learn_patterns` `:1289` (commits in `modules/adherence_patterns.py:488`, `:620`, call path UNMEASURED) |
| `model_settings.py` | `run_hardware_detection` `:445` → `:461`; `set_model_tier` `:486` → `:519`; `start_model_download` `:634` → `:673`; `save_external_api_settings` `:730` → `:755`; `set_timezone` `:967` → `:983`; `update_voice_settings` `:1002` → `:1016`; `update_ocr_settings` `:1052` → `:1059`; `update_agent_settings` `:1080` → `:1088` |
| `notifications.py` | `update_notification_settings` `:201` → `:267`; `record_reminder_interaction` `:521` → `:559` |
| `profiles.py` | `reset_synthetic_test_profile` `:477` → `:523` (test-only) |

Medication updates, schedules and doses are patient data under the CLAUDE.md "audit logging on every route that touches … profile data" invariant. That gap is **not** AUDIT-ORDER (there is no audit row to order); it is listed so the owner can decide whether AO-SCOPE includes it. It is a candidate new program item (L0's call).

---

## 4. AUDIT-DENIALS, measured

| Fact | Evidence |
|---|---|
| Patient-data routes open the caller's own vault, chosen from the session, not from the path | `core/auth.py:313-335` (`_get_required_profile_connection(session.profile_id)` `:332`) |
| So a request for another profile's record ID finds no row in the caller's vault and returns **404**, not 403 | 404 raise sites per file (grep `HTTP_404_NOT_FOUND\|status_code=404`): documents 15, medications 14, profiles 8, interpretations 6, pinboards 6, observations 5, assistant 4, export 4, notifications 4, care_tasks 3, memory 3, backup 2, feedback 1, med_reconcile 1. A per-site walk of whether each is logged is UNMEASURED; grep for `access_denied` / `.denied` in `api/`, `core/`, `security/` returns 0 hits |
| The in-route ownership 403s are defence in depth (they fire only if a vault held another profile's row) | `documents.py:214-222`, `observations.py:64-72`, `medications.py:62-66`, `interpretations.py:388-392`, `:441-443`, `:597-599`, `notifications.py:174-178`, `:226-228`, `:445-447`, `:546-548` |
| Of those, two log at WARNING with both profile IDs; the rest raise silently | logged: `documents.py:215-218`, `observations.py:65-68`; silent: the other sites above |
| **Reachable** cross-profile 403s: export downloads read process-wide in-memory stores keyed by ID | `export.py:498` + `:507-511` (`_summary_store`), `:840` + `:847-851` (`_packet_store`), `:1267` + `:1274-1278` (`_fhir_store`); no log line, no audit row; all three are GET routes |
| `require_profile_access` (path `profile_id` vs session) logs at WARNING then 403 | `core/auth.py:278-286`; used only on `profiles.py:592`, `:777`, `:945`, `:968`, `:1074` (profile management, not patient-data routes) |
| The security middleware logs mutating methods only, as an INFO line with path and status; no audit row | `security/audit_middleware.py:20`, `:42-44` (GET passes through), `:58-81` |
| `log_to_db` is stored but never read; the docstring's "Optionally persists events to the database" is not implemented | `security/audit_middleware.py:5`, `:31-33`; file ends at `:81`; config default `core/config.py:83` (`audit_security_events_to_db: bool = False`), wired `main.py:131-132` |
| Rate limiting is per client IP | `security/rate_limit_middleware.py:81-97` |

**Correction for the register (L0's edit, not this plan's):** `implementation-program.md:488` "not audited or logged anywhere" is too strong. Measured: no denial writes an audit row; the document and observation ownership 403s and `require_profile_access` log at WARNING with profile IDs; mutating denials get an INFO middleware line; GET 404s and the export-download 403s are not logged.

---

## 5. Existing tests: what would notice a missing audit row

| Test | Through HTTP? | What it asserts | What it cannot notice |
|---|---|---|---|
| `HC-DDI-001` `tests/test_documents_api.py:956` | yes (`_ddi_delete_over_http` `:943`, `route_client`) | one `document.delete` row added and a master commit (`:998-1001`) | master is a fake (`_CommitTrackingMasterDb` `:744`); a master commit failure is never injected |
| `HC-DDI-002` `:1005` | yes | profile commit fails → file kept, no audit row (`:1021-1033`) | the opposite order: profile commit succeeds, master commit fails |
| `HC-DDI-003` `:1037` | yes | unlink fails after commit → audit row still written | as above |
| `HC-OBS-AUDIT-001` `tests/test_observations_audit.py:74` | no (direct call) | read route fails closed when the master commit raises (`:86`, `:94-102`) | write routes; a broken `Depends(...)` |
| `tests/test_memory_audit.py`, `test_backup_routes.py`, `test_safe_chat_prohibited.py`, `test_safe_interp_grounded.py`, `test_external_runner_hardening.py` | use `route_client` (grep) | audit rows on their routes (per-test assertions not walked: UNMEASURED) | grep finds no master-commit failure injection on any write route |

Grep for commit-failure injection across `tests/` (`commit.*side_effect`, `OperationalError`, `disk I/O`): 4 hits — `test_document_import_classification.py:424`, `test_documents_api.py:1022`, `test_observations_audit.py:86`, `test_pinboards.py:288`. None fails the **master** commit on a **write** route. Every option below therefore adds that test first (recurring-failures §1).

---

## 6. Options

All options keep every existing check: `_scrub_action` / `_scrub_details` stay the only way into `audit_logs`; `audit_and_commit` stays fail-closed; no threshold or validation is relaxed. None gives true atomicity across two SQLite files; each moves or narrows the window (pack finding 1, recurring-failures §2).

### Failure injection on paper

Cases: **(a)** the audit write fails (first write for A/A2/D, the only write for C); **(b)** the patient-data change fails; **(c)** the process dies between the two commits; **(d)** the vault is locked or closed.

| Case | Today / C (accept and document) | A (intent row, status column) | A2 (intent as two rows, no schema) | B (outbox in vault) |
|---|---|---|---|---|
| (a) | change durable, no row, 500 (+ ERROR log under C) | intent commit fails → nothing changed, 500 (if AO-FAIL A) | same as A | outbox row is in the change's transaction: both roll back, 500 |
| (b) | profile rollback (`core/profile_database.py:81-83`), no row | `started` row stays; change absent; reader sees an unfinished intent | `started` row alone, no `completed` row | both roll back; nothing recorded |
| (c) | change durable, no row | `started` row, change may or may not be durable: reader must check the vault | same as A | outbox row durable with the change; relayed on next run |
| (d) | dependency 403 before the handler (`core/auth.py:306`); nothing written | same; no intent row (dependency fails first) | same | same for requests; **relay cannot read an unrelayed outbox until the next unlock**, so rows arrive late |

### Option A — intent row first, status column

- **Mechanism:** commit an audit row with `status='started'` in the master DB before the profile commit; after the profile commit, set `status='completed'` and commit.
- **Ask-first edits:** `core/audit.py`: `create_audit_log` (new `status` argument), new helper `begin_audit` / `complete_audit` beside `audit_and_commit`. `models/audit.py`: `AuditLog` gains `status` column. Route call sites in the scoped routes (§3).
- **Migration:** master `003_audit_status` with `down_revision = "002_backup_schedules"`; no profile migration.
- **PHI:** `status` is an enum (`started|completed`); written only through `create_audit_log`, so `_scrub_details` still applies. No new free-text field. The row exists earlier, not with more content.
- **Gain:** a failed or interrupted change is visible as `started`; no relay; one database.
- **Downside:** schema change on the shared audit table (overlaps W-2's `models/audit.py` edits); every scoped route gets two master commits (two write locks per request); a `started` row is ambiguous in case (c); rows are updated in place, which reads against "append-only" (DOC-OVERCLAIM `:480`).
- **Tests (through `route_client`, real in-memory master session):** HC-AUD-ORD-001 master commit fails after profile commit → today RED (change, no row), after fix: request 500, change absent. HC-AUD-ORD-002 profile commit fails → `started` row present, no `completed`. HC-AUD-ORD-003 happy path → one row, `completed`. HC-AUD-ORD-004 intent row carries no non-allowlisted detail (PHI). HC-AUD-ORD-005 migration up/down on the master chain.
- **Break-it:** revert the route to profile-first → HC-AUD-ORD-001 must fail; drop `_scrub_details` from the new helper → HC-AUD-ORD-004 must fail.
- **Rollback:** revert the PR; downgrade `003` (column dropped; `started` rows lose their status).
- **Effort:** M (helper + migration + ~8 call sites for the irreversible set; L for all 27 rows).

### Option A2 — intent as two append-only rows, no schema change

- **Mechanism:** before the change, `audit_and_commit(... details={"status": "started"})`; after the profile commit, a second row with `details={"status": "completed"}`. Uses the existing `status` key (`core/audit.py:70`) and the existing fail-closed helper (`:474-487`).
- **Ask-first edits:** none in `core/audit.py` if call sites pass `details`; optional thin helper there (`audit_intent`) for readability. Route call sites only.
- **Migration:** none.
- **PHI:** none new; both rows go through `create_audit_log`.
- **Gain:** smallest change; append-only preserved; no migration ordering against P6/G-C1; `backup.py:452-461` already uses `details.status` this way (precedent).
- **Downside:** two rows per scoped request (master DB growth); pairing is by `entity_id` + `event_type` + time, with no explicit link; a reader query must handle unpaired `started` rows; the `completed` commit can itself fail, leaving the same ambiguity as A in case (c).
- **Tests:** HC-AUD-ORD-001..004 as A (status read from `details_json`); no migration test.
- **Break-it / rollback:** as A, without the downgrade.
- **Effort:** S for the irreversible set.

### Option B — outbox in the vault

- **Mechanism:** write the audit record into a new vault table inside the same profile transaction as the change; a relay copies it to `audit_logs` and marks it relayed.
- **Ask-first edits:** `core/audit.py` (outbox writer and relay, both through `_scrub_details`); `core/profile_database.py` or the login path in `core/auth.py` if the relay runs on unlock (auth/encryption file, ask-first under CLAUDE.md §1); new `models/` table.
- **Migration:** profile `015_audit_outbox`, `down_revision` = the head after P6 (`013`) and G-C1 (`014`); P7 must add the table to the test-reset tuple (`api/profiles.py:498-515`).
- **PHI:** the outbox lives inside the encrypted vault, so PHI exposure is lower than A; the copy to master still goes through `_scrub_details`.
- **Gain:** the change and its audit record are atomic in one SQLite transaction; case (c) is covered.
- **Downside:** largest change; a locked vault (d) delays rows until next unlock; **profile delete (row 27) and restore (row 26) cannot use it** (the vault is destroyed or replaced), so they need A/A2 anyway; a new relay is a new background path (recurring-failures §10, "never started"); read routes keep `audit_and_commit`, so two audit paths coexist.
- **Tests:** HC-AUD-ORD-010 change + outbox row in one transaction; HC-AUD-ORD-011 relay copies and marks; HC-AUD-ORD-012 relay is idempotent; HC-AUD-ORD-013 locked vault defers; HC-AUD-ORD-014 PHI scrub on relay; HC-AUD-ORD-015 relay is started on unlock (HTTP, not a unit call).
- **Break-it:** commit the outbox row in a separate transaction → HC-AUD-ORD-010 fails; skip the relay start → HC-AUD-ORD-015 fails.
- **Rollback:** revert; downgrade `015` (unrelayed rows lost: relay first).
- **Effort:** L.

### Option C — accept and document

- **Mechanism:** keep the order. Wrap the master commit on write routes so a failure is logged at ERROR (event type and entity id only, no PHI) before re-raising; state the window in the compliance docs.
- **Ask-first edits:** none required; optional `core/audit.py` helper `commit_audit_after_change` that logs and re-raises.
- **Migration:** none.
- **PHI:** the ERROR line is a new plaintext surface: entity id and event type only (same fields as `core/audit.py:257-264`).
- **Docs:** one sentence in `docs/compliance/data-privacy.md`, which W-10 owns: routed through W-10b or a W-10 addendum, not edited here.
- **Gain:** smallest code change; no schema; behaviour already known.
- **Downside:** the irreversible routes (document delete, profile delete) keep a window where a destroyed record has no audit row; a log line is not an audit record (no product log sink: DOC-OVERCLAIM `:480`).
- **Tests:** HC-AUD-ORD-020 master commit fails on a write route → 500 and an ERROR record without PHI (caplog).
- **Effort:** S.

### Option D — hybrid: A2 on the irreversible set, C on the rest (recommended)

- **Scope:** rows 2, 5, 10 (hard delete), 13, 16, 19/20/23 (regenerate), 26, 27 get A2; every other row in §3 gets C.
- **Row 27 note:** the `started` row carries `profile_id`, so `delete(AuditLog)` at `profiles.py:907-909` purges it in the same transaction on success; if the commit at `:936` fails, the purge rolls back and the `started` row survives. This depends on today's retention (AO-BRIEF4); Brief 4 may change it.
- **Gain:** closes the window where the data cannot be reconstructed; no migration; smallest surface for the ask-first file.
- **Downside:** two behaviours to explain; reversible routes keep the window; a later route must be classified correctly or it silently gets C (recurring-failures §9). Mitigation: a test that enumerates `DELETE` handlers and fails on one not in the A2 list.
- **Tests:** HC-AUD-ORD-001..004 per irreversible route (parametrised over the route list), HC-AUD-ORD-020, HC-AUD-ORD-030 route-class guard (every `@router.delete` handler is in the A2 list or an explicit exclusion).
- **Effort:** S-M.

### AUDIT-DENIALS options

| Option | Edits (ask-first) | Gain | Downside |
|---|---|---|---|
| D-A audit row for every 403/404 on patient-data routes | each raise site or an exception handler; `core/auth.py:278-286` | complete trail | grows the unencrypted master DB; any authenticated caller can fill it (rate limit is per IP, `security/rate_limit_middleware.py:81-97`); needs a per-profile cap; 404s are mostly typos, so noise |
| D-B audit row for reachable cross-profile 403s only (export downloads `export.py:507`, `:847`, `:1274`, and `require_profile_access` `core/auth.py:278`) | `api/export.py` (3 sites); `core/auth.py:278-286` | covers the denials that can actually be another patient's data; small | 404 probing stays unaudited; `core/auth.py` is ask-first (auth) |
| D-C log line only: add WARNING lines (no profile IDs beyond the caller's) to the silent 403 sites and the export 403s | `api/*.py` raise sites only | no new audit rows; no DoS surface | a log line is not an audit record (no product log sink) |
| D-D leave as is and document | none | no change | the register row stays open |

PHI for D-A/D-B: denial rows carry `entity_type`, the requested id and the caller's `profile_id`; never the owner's profile id (pack finding 5: today's WARNING at `core/auth.py:279-282` prints both). Tests: HC-AUD-ORD-040 export download by another profile → 403 and one denial row through `route_client`; HC-AUD-ORD-041 cap enforced; HC-AUD-ORD-042 denial row holds no second profile id.

### AUDIT-KEYS-DROPPED (`implementation-program.md:472`)

Same file (`core/audit.py:89-109`). Not folded in: it is an allowlist change with its own owner decision. Any option that edits `core/audit.py` lands in a separate commit so the two can be reviewed apart.

---

## 7. Recommendation

**D (A2 on the irreversible set, C elsewhere), AO-FAIL A, AO-SCOPE B for the first PR, AD-DENIALS D-B.** Reasons: the irreversible routes are where a missing row cannot be reconstructed; A2 uses the existing fail-closed helper and allowed `status` key, so no migration and no ordering against P6/G-C1/W-2's schema edits; B is the only option that covers case (c) but cannot cover profile delete or restore and adds a background path. The owner decides; Codex review may overturn this.

---

## 8. Owner questions (UNSIGNED)

1. **AO-DESIGN** — UNSIGNED. "On write routes the audit row is saved after your data change, in a different database. If saving the audit row fails, the change stays with no record. Which design?"
   - A. Intent row with a status column. Gain: unfinished changes are visible. Downside: master migration, edits `models/audit.py` and `core/audit.py`, rows updated in place.
   - B. Outbox in the patient vault. Gain: change and record commit together. Downside: largest change, new relay, profile vault migration, cannot cover profile delete or restore.
   - C. Accept and document, ERROR log on failure. Gain: smallest. Downside: an irreversible delete can still leave no audit row.
   - D. Two-row intent (started/completed) on irreversible routes, C on the rest **(recommended)**. Gain: no migration, closes the irreversible window. Downside: two behaviours; reversible routes keep the window; twice the rows on those routes.
2. **AO-FAIL** — UNSIGNED. "If the audit row cannot be saved *before* the change, should the request fail and change nothing?"
   - A. Yes, fail closed, as view routes already do (`core/audit.py:479-484`) **(recommended)**. Gain: no unaudited irreversible change. Downside: a master-DB fault (E2E-MASTER-CORRUPT) blocks deletes until fixed.
   - B. Proceed and log an ERROR. Gain: deletes keep working when the master DB is broken. Downside: same window as today on exactly the failure that matters.
3. **AO-SCOPE** — UNSIGNED. "Which routes?"
   - A. All 27 rows in §3. Gain: one rule. Downside: largest diff; reversible routes gain little.
   - B. Irreversible set only (rows 2, 5, 10, 13, 16, 19/20/23, 26, 27) **(recommended first PR)**. Gain: small, highest value. Downside: needs a route-class guard test.
   - C. Documents and observations only (rows 1-6). Gain: matches the original finding. Downside: leaves memory, pinboard, medication and profile deletes out.
   - D. B plus the unaudited writes in §3.1. Gain: closes the CLAUDE.md audit invariant too. Downside: new audit rows on settings routes; bigger PR.
4. **AD-DENIALS** — UNSIGNED. "Denied requests (403 across profiles, 404 on someone else's ID) leave no audit row. What do you want?"
   - A. Audit row for every 403/404 on patient-data routes. Gain: complete. Downside: master DB growth, fill attack, needs a cap.
   - B. Audit row for reachable cross-profile 403s only (export downloads, profile routes) **(recommended)**. Gain: small, targeted. Downside: 404 probing unaudited; edits `core/auth.py`.
   - C. Log line only at the silent 403 sites. Gain: no new rows. Downside: not an audit record.
   - D. Leave as is and document. Gain: no change. Downside: the register row stays open.
5. **AO-ASKFIRST** — UNSIGNED. "The chosen option edits these files. Approve each by name?" One line per file, signed separately:
   - `core/audit.py` — A: `create_audit_log` + new begin/complete helpers; A2/D: optional `audit_intent` helper only; B: outbox writer + relay; C: optional ERROR helper.
   - `models/audit.py` + master migration `003` — A only.
   - new vault model + profile migration `015` + reset tuple (`api/profiles.py:498-515`) — B only.
   - `core/auth.py:278-286` — AD-DENIALS A or B; also B if the relay starts at unlock.
6. **AO-BRIEF4** — answered "Yes, assume today" (chat 2026-10-08, recorded on `docs/wave4-close`). Not re-asked. Brief 4 is an open dependency (§1).

---

## 9. Shared-file ordering

| Other phase | Overlap | Order |
|---|---|---|
| P5 | `api/*.py` `utcnow` swaps | merged (`98bd3c7`); lines above already re-measured |
| W-2 | `core/audit.py` (allowlist, `redaction_count`) and `models/audit.py` (`docs/plans/2026-09-27-W02-doctor-summary-redaction.md`, 6 mentions of `core/audit.py`) | W-2 first; this plan re-measures `core/audit.py` after it. Option A conflicts most |
| W-11a PR-1 | adds audit rows to 4 routes in `api/profiles.py` (per the readiness pack §5; not re-measured here; `docs/plans/2026-09-27-W11a-test-and-gate-hardening.md`) | new call sites inherit whichever order is signed; land W-11a PR-1 first, then include its routes in the scope walk |
| W-7 | interpretation-route audit (OG-3) | rows 19-23 change if W-7 lands; re-walk before execution |
| P6 | profile migration `013_fk_cascade_alignment` | before B (`015`); A's master `003` does not collide |
| G-C1 | profile `014_export_artifacts`; `api/export.py` stores | before B; also before AD-DENIALS B (the export 403 sites move when stores persist) |
| P7 | test-reset tuple `api/profiles.py:498-515` | B's new table goes into the tuple after P7 lands |
| W-10 / W-10b | `docs/compliance/data-privacy.md` | option C's sentence routed through them |
| `docs/INDEX.md`, `docs/_link_graph.json` | every docs PR | generated; the PR that merges second regenerates |

---

## 10. Recurring-failures recheck (`docs/agentic/recurring-failures.md`)

| § | Mode | Applied here |
|---|---|---|
| 1 | green suite that could not have failed | §5: no test fails the master commit on a write route; every option starts with HC-AUD-ORD-001 RED |
| 2 | fix that creates the next bug one layer over | intent rows and outbox rows are new PHI surfaces and new failure points; each option lists them |
| 3 | figures asserted, not measured | every line re-read at `98bd3c7`; UNMEASURED where not |
| 4 | environment-dependent results | master-commit failure is simulated, not reproduced; E2E-MASTER-CORRUPT cause UNMEASURED |
| 8 | stale guidance as authority | pack lines superseded; register row `:488` corrected in §4 |
| 9 | invariant at one site, not its class | §3 covers 27 routes, not just `delete_document`; option D adds a route-class guard (HC-AUD-ORD-030) |
| 10 | unit-tested feature never started | option B's relay needs an HTTP test that it starts (HC-AUD-ORD-015) |

§5-§7 (contaminated tree, unrun commands, SQL three-valued logic): no new instance found; a query for unpaired `started` rows (A2/D) must not use `NOT IN` over a nullable column (§7).

---

## 11. UNMEASURED and out of scope

UNMEASURED:
1. Router mount prefixes for the paths in §3.
2. Per-route test assertions in the five `route_client` audit test files (§5).
3. Whether observation verify (row 6) keeps prior values; `interpret_panel` overwrite semantics (row 22); a document un-verify path (row 3).
4. Agent-node audit events during ordinary chat turns (`modules/agent/audit.py`); `learn_patterns` commit path.
5. The master profile-row re-apply inside `scripts/backup.py::restore` (`:507`), beyond the docstring at `:60`.
6. Per-site logging of every 404 raise site.

Out of scope (reported, not fixed): the fail-open `_emit_audit` in `feedback.py:40-57` (a write route that swallows audit errors) — options C and D bring it under the same rule only if AO-SCOPE includes row 24; the unused `log_to_db` flag (`security/audit_middleware.py:31-33`); AUDIT-KEYS-DROPPED; DDI-ORPHAN-BIN.
