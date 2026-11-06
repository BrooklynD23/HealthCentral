# Docs-audit rows 2026-11-06: plans for AUDIT-READ-ROUTES, AUDIT-CHAT-LEGACY, AUDIT-DB-SETTING-DEAD, MODEL-INT-TIER, MODELS-INIT-FEEDBACK, ONBOARDING-LANDS-OVERVIEW, FE-STALE-LINKS and DOCSTRINGS-1106

**Last Updated:** 2026-11-06 (Opus planner on `0f0cd100`, from the "Proposed, not edited" findings of DOCS-AUDIT-1106 (#521); BATCH-1106C records the owner answers AUDIT-DB-SETTING, LANDING-OVERVIEW and QUESTION-INJECTION in the rows below)
**Owner:** repository owner
**Status:** PLANNED (Opus planner; owner answers recorded 2026-11-06). Docs only. **No owner approval is recorded here;** every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). The gate names AUDIT-DB-SETTING, QUESTION-INJECTION, UTC-HELPER-SCOPE, BOOTSTRAP-AGENT-MODEL, D7-RULE-TEXT and LANDING-OVERVIEW were proposed by the planner and assigned by L0; all six are answered. **Open L0 rulings (not the owner):** PROVIDER-AUDIT (AUDIT-READ-ROUTES Task 3) and SAFECHAT-002-LICENCE (AUDIT-CHAT-LEGACY, the HC-SAFECHAT-002 `:174` licence).
**Base measured:** `origin/main` @ `0f0cd100` (#516 merged). Every `file:line` below was re-read on that commit from a `git archive` copy. Product code was read only. Two scripts ran on that copy: an AST route inventory, and `tests/support/callgraph.py::Graph` (the HC-AUD-ORD-030 graph), both listed under AUDIT-READ-ROUTES.
**Refresh Trigger:** a merge that edits `src/backend/api/assistant.py`, `src/backend/api/feedback.py`, `src/backend/api/medications.py`, `src/backend/api/model_settings.py`, `src/backend/tests/test_audit_order_guard.py`, `src/backend/security/audit_middleware.py`, `src/backend/core/llm/llama_cpp_provider.py`, `src/backend/models/__init__.py`, `src/frontend/src/pages/ProfileSetup.tsx` or `src/frontend/src/pages/RecoverProfile.tsx`; a new route under `src/backend/api/`; E-2 or B-5 landing.

Queue rows: [queue.md, "Planned 2026-11-06, docs-audit rows (#521)"](2026-10-15-build-program/queue.md#planned-2026-11-06-docs-audit-rows-521). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`.

**Open PRs checked 2026-11-06** (`gh pr diff <n> --name-only`): #521 (docs only, now merged); #517 (`fe/pages/settings/AdvancedSection.tsx`, `e2e/ui-settings.spec.ts`); #514 draft (`e2e/ui-shell.spec.ts`); #316 draft (`dev.ps1`, `dev.sh`, `README.md`, `be/tests/test_dev_sh_prereqs.py`); #264 B-3 parked draft (`be/api/assistant.py`, `be/api/interpretations.py`, `be/modules/rag.py`, `be/tests/test_audit_order_guard.py`, `be/tests/test_safe_chat_prohibited.py`, `be/tests/test_rag_pipeline.py` and 14 more); #239 blocked draft (`be/api/assistant.py`, `be/api/feedback.py`, `be/core/config.py`, `be/tests/test_audit_order_guard.py`, `be/tests/test_rl_feedback.py`, `config/.env.example` and 12 more). No non-draft PR shares a file with any row. The drafts rebase onto these rows (contracts §b rules 1-2).

**Test-id prefixes:** HC-ARR, HC-ACL, HC-ADBS, HC-MTIER, HC-MIF, HC-OLO, HC-FSL had 0 hits each on 2026-11-06 with `git grep -il "hc[-_]<p>[-_]" origin/main -- .`. (HC-MTIER, not HC-MIT, so it cannot be read as the existing HC-MINT-001…011.)

## What held, what changed, what was dropped (the planner's verdicts)

| Audit item | Verdict | Why |
|---|---|---|
| P1 vault reads with no audit (`medications.py:362,391,784,1114`, `assistant.py:432,509,580`, `feedback.py:294`) | **holds** | 8 handlers, read on `0f0cd100`; none takes a master session, none calls a `core/audit.py` sink. |
| P1 `POST /profiles/test/reset` (`profiles.py:557`) | **holds, already planned** | Owned by **E-2** (W-11a PR-1), owner RESET-AUDIT-OWNER (2026-10-09): `profile.test_reset`. E-2 also owns `GET /`, `GET /me`, `GET /{profile_id}` (also unaudited; the audit did not list them). Not in these rows. |
| P1 legacy chat success return (`assistant.py:1309`) | **holds, wider** | The legacy branch writes no row when it answers or abstains (`:1202-1285`), and the no-model fallback (`:1321-1340`) writes none either. Agent, advice-gate and prohibited paths do audit. |
| P1 `PUT /settings/model/provider` (`model_settings.py:921`) | **corrected** | Writes no row, but it is a process-wide runtime switch that touches no profile data (`:932-970`), so the CLAUDE.md invariant does not require it. Planned as an optional task under an L0 ruling. |
| P1 "every route" | **corrected** | 136 handlers; 23 reach no audit sink: 8 vault reads (above), 4 master-profile routes (E-2), 1 provider switch, and 10 that read no profile data and get labels. Chat is not among the 23 (some of its paths audit) but has two unaudited paths. Full list: Appendix A. |
| P2 `log_to_db` dead | **holds** | `security/audit_middleware.py:31-33` stores it; nothing reads it; `main.py:133` passes `settings.audit_security_events_to_db` (`core/config.py:83`). Already tracked as AUDIT-MW-DOCSTRING (`docs/capstone-report/implementation-program.md:505`). |
| P3 question not injection-filtered | **holds** | `modules/rag.py:762-771`; history (`:776-790`) and chunks (`:808-830`) are filtered. No owner decision on the question was found. Owner question: answered 2026-11-06 ([owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). |
| P4 `datetime.now(timezone.utc)` | **holds, wider, and a mechanical fix would break login** | `core.time.utcnow` returns a **naive** datetime (`core/time.py:12-14`); `Session.expires_at` and the JWT expiry are **aware** (`core/auth.py:73`, `:144`), so swapping in `utcnow()` would compare naive with aware and raise `TypeError`. More sites than the audit listed: `api/model_settings.py:382`, `api/export.py:1017`, `:1073`, and `modules/source_authority.py:216` (`datetime.now().year`, local time). Owner question: answered 2026-11-06 ([owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). |
| P5 `windows-bootstrap-engineer` on opus | **holds** | `.claude/agents/windows-bootstrap-engineer.md:4-5`: `tools: Read, Grep, Glob, Edit`, `model: opus`. Owner question: answered 2026-11-06 ([owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). |
| P6 D7 path not named beside D12 | **corrected** | D7 is not a licence. Owner D7 (`owner-decisions:20`) says "Route via ModelRunner", and row B-5 (blocked) removes the import (contract I-17: "`model_selector.py` no longer imports `llama_cpp`"). `model_selector.py:456` is a known violation that is waiting on B-5, not an exception. The owner answered D7-RULE-TEXT (2026-11-06) and CLAUDE.md §3 now says so. |
| P7, P8 stale dated records | **holds** | Dated-record notes, applied in BATCH-1106C (queue section). Not rows. |
| P9 `llm_model_tier` | **holds, corrected cause** | `core/llm/llama_cpp_provider.py:164` reads `llm_model_tier`, which does not exist, so it always checks against "low". But **neither** candidate setting is the active tier. `default_model_tier` (`core/config.py:97`) is never read anywhere, and the per-profile `preferred_tier` (`models/model_settings.py:45`) drives `ModelSelector` only. The provider is a process-wide singleton that loads the first GGUF its glob finds (`llama_cpp_provider.py:99-127`). The only true key is the loaded file itself. **No runtime effect today:** every chat-tier pin in `config/model_manifest.json` is `null`, so every load reports UNPINNED whatever the tier. |
| P10 docstrings | **holds, one path corrected, two sites added** | `scripts/agent_eval_gate.py` is at the repo root, not `be/scripts/`. `scripts/__init__.py` is `be/scripts/__init__.py`. Added: `be/modules/agent/eval/scorer.py:1`, `:102` ("Four-axis"; the scorer has six axes plus two end-to-end checks). `core/auth.py:331` is ask-first. `models/__init__.py:7-11` moves to MODELS-INIT-FEEDBACK. |
| P11 `models/__init__.py` lacks `response_feedback` | **holds as a latent footgun, not a runtime bug** | Runtime schema comes from hand-written migrations (`008_response_feedback.py`). `migrations/profile/env.py:110-125` refuses to run without a vault path and key, so CLI autogenerate does not run there. `_init_profile_schema_for_tests` is deprecated (`core/profile_database.py:408-430`). The real cost: any metadata-driven check misses the table unless something imported `models.response_feedback` first. Four tests already import it by hand with the comment "not exported by models/__init__" (`test_fk_audit.py:8`, `test_profile_test_reset.py:28`, `test_fk_enforcement.py:176`, `test_rl_export_prompt_snapshot.py:31`). |
| P12 sign-in lands on `/inbox` | **holds; not intended** | Plan `2026-10-23-frontend-revamp-plan.md:224`: Overview "Replaces landing on an empty Inbox". Already the candidate bullet ONBOARDING-LANDS-INBOX (`queue.md:749`). It is owner-visible, so it gets an owner question. |
| P12 "Reminders" never highlights | **dropped as a row** | By design until UI-MICRO. Plan `:238` ("until UI-MICRO, 'Reminders' stays listed under Care"); the UI-MICRO plan lists "`navConfig.ts` (the transition 'Reminders' entry removed)" (plan `:879`). It is UI-MICRO's work. |
| P12 `MedicationDetail.tsx:372` links `/trends` | **holds, wider** | Also `MedicationDetail.tsx:381` (`/trends?analyte=`), `pages/SearchPage.tsx:35`, `pages/TimelinePage.tsx:51`. Each works through the `replace` redirect (`App.tsx:218`, `:251`), so nothing visible breaks. |
| P12 `@types` alias to a missing dir | **holds** | `tsconfig.json:27`, `vite.config.ts:41`, `vitest.config.ts:34` → `./src/types` (absent); 0 imports of `@types/…` under `fe/` or `e2e/`. |
| P13 `dev.bat:12` | **holds, softened** | "pick the next free port" is incomplete rather than false: `dev.ps1:762-784` first stops the process on the port (`Stop-ProcessOnPort`), then falls back to `Find-FreePort`. `dev.bat`/`dev.ps1` belong to #316 and the `windows-bootstrap-engineer` write scope. No row: give it to #316. |
| P14 `ci.yml:412-413` port 3000 vs 4173 | **dropped (false finding)** | The comment explains why the ui-auth G3 titles are **excluded**: they "need the real backend and a preview on port 3000 (ui-auth.spec.ts:14-17), and this job runs no backend". `ui-auth.spec.ts:14-17` says the same: the backend's CORS list is port 3000 only. The job serves 4173 because it runs only the mocked specs. The comment is correct. |
| P15 `core/config.py:42` unused | **holds; skip** | `database_encryption_enabled` is read by no code, but it is encryption config (CLAUDE.md §1 ask-first) and is written by `config/.env.example:43`, `dev.ps1:577` and `dev.sh:175` (both #316's). Skipped, reported. |
| P15 `core/model_runner.py:85-88` unused ctor args | **holds; comment only** | Stored, never read. `tests/test_rag_pipeline.py:1261` passes `model_path=`, so removing them breaks a test. That test asserts `is_available() is False or … is True`, which cannot fail (recurring-failures §1). Docstring note folded into DOCSTRINGS-1106. |
| P15 `core/rate_limiter.py:31` name | **holds; skip** | `FixedWindowRateLimiter` is a sliding log, and its own docstring (`:32`) already says so. Renaming moves auth-limiter code (`:84`, `:93`) for no behaviour change. |

**Found while verifying (for L0, not rows; BATCH-1106C fixes the E-2 and ADVICE-CLASSIFIER-FIX statuses and records the rest as candidates or notes):**
- **E-2's status is stale.** The row (`queue.md:304`) reads "blocked: owner OG-1, Q-AUD-LIST", but both gates were answered on 2026-10-17 (`owner-decisions:236-237`), and C-P6 and C-P7 are done. If nothing else holds it, E-2 is ready. It owns the four `api/profiles.py` audit gaps.
- **ADVICE-CLASSIFIER-FIX is merged.** `origin/main` `0f0cd100` is "Merge pull request #516", but its row still reads "in flight: #516".
- **`config/model_manifest.json` "mid" is stale.** It names `microsoft/Phi-3-mini-4k-instruct-gguf`; `TIER_MODEL_CONFIG["mid"]` is now `bartowski/microsoft_Phi-4-mini-instruct-GGUF` (`modules/model_selector.py:101-104`). Whoever pins "mid" must use the right repo.
- **A test that cannot fail:** `tests/test_rag_pipeline.py:1268` `assert runner.is_available() is False or runner.is_available() is True` (recurring-failures §1). The file is shared with parked #264.
- **Panel names in the app log:** `SecurityAuditMiddleware` logs the raw path of every mutating request (`audit_middleware.py:46`, `:62-81`). `POST /interpretations/panels/{panel_name}/interpret` therefore puts a panel name in `SECURITY_AUDIT` lines. This is beside SEARCH-LOG-SCRUB's "For L0" note on path segments.
- `default_model_tier` (`core/config.py:97`) and `audit_log_enabled` (`:144`, also `config/.env.example:138`) are never read.

---

## Plans

**Rules that hold for every row here.**
- No row lowers a threshold, relaxes a guard or weakens an assertion to pass. A test named as "must change" changes only as written. Any other test that goes RED stops for L0 with its ids.
- Route tests go through `tests/support/routes.py::route_client`.
- **Audit rows carry ids, counts, enums and booleans only, never patient text.** `create_audit_log` scrubs `details` (`core/audit.py:119-171`, AUDIT-PHI-001), but the scrubber keeps any enum-shaped string under an allowed key, so a single-word drug name or session title would pass it. Callers pass no name, title, question, answer, dose, note, analyte or file name, in `details` or in `entity_id`. Each audit test seeds sentinel strings in those fields and asserts that none of them appears in `action`, `entity_id`, `details_json` or the app log (prior art: HC-MEM-AUDIT-006, `tests/test_memory_audit.py:150`).
- **AUDIT-ORDER.** A read audits with `audit_and_commit` after the read and before the response. It fails closed: a view that cannot be audited is not served (`core/audit.py:475-488`). A reversible write is "C": the audit comes after the vault commit, and a failed audit commit is logged with ids and re-raised (`api/medications.py:558-576`). An irreversible change is "A2", the started/completed pair (`audit_intent`, owner AO-DESIGN D, AO-FAIL). Chat writes its audit row before the turn is stored, as both existing chat branches do (`api/assistant.py:1192`, `:1277`). Every handler that newly commits gets a `CLASSIFICATION` row in `test_audit_order_guard.py`, or HC-AUD-ORD-030 goes RED.

### AUDIT-READ-ROUTES

**Source:** DOCS-AUDIT-1106 P1 (PR #521); CLAUDE.md hard invariant "Audit logging on every route that touches documents, observations, or profile data". Kind: PRODUCT, privacy. MVP **P1**.

**Facts (re-read on `0f0cd100`).**
- The inventory, an AST scan of every `@router.<method>` in `be/api/*.py` (Appendix A), finds 136 handlers. The HC-AUD-ORD-030 call graph (`tests/support/callgraph.py::Graph`, run on the archive) finds **23** that reach none of `create_audit_log`, `audit_and_commit`, `audit_intent`. The AST scan finds the same 23.
- Vault data, no audit (this row): `assistant.py` `list_sessions` (`:432`, chat session titles; a title is the first question, `_get_or_create_session`), `get_session_history` (`:509`, every turn's text), `get_memory_settings` (`:580`, per-profile flag); `feedback.py` `get_feedback_stats` (`:294`, counts and tag/model distributions from `response_feedback`); `medications.py` `list_medications` (`:362`), `get_medication` (`:391`), `list_schedules` (`:784`), `list_doses` (`:1114`). None of the eight takes a master session today.
- E-2's (not this row): `profiles.py` `list_profiles` (`:318`), `get_current_profile` (`:495`), `reset_synthetic_test_profile` (`:557`), `get_profile` (`:1049`). Gates OG-1 and Q-AUD-LIST were answered 2026-10-17; RESET-AUDIT-OWNER gives the reset row to W-11a PR-1 (E-2).
- No profile data, get a label (Task 2): `assistant.py` `get_test_intent`, `get_glossary_term` (static modules); `interpretations.py` `get_biomarker_knowledge` (master KB, "Public knowledge - not patient-specific data", `:1012`); `model_settings.py` `list_tiers`, `get_llm_provider`, `get_environment_diagnostics`, `recheck_environment_diagnostics` (owner AUDIT-READ-SCOPE: "read no profile data") and `get_download_progress` (owner AUDIT-READ-SCOPE (a): "labelled exception"); `notifications.py` `send_test_notification` (an OS toast with request text), `get_scheduler_status` (process-wide counts).
- `set_llm_provider` (`model_settings.py:921-970`): any authenticated profile switches the process-wide provider and model; the only trace is an app-log line with the profile id (`:961-966`). No profile data is read or written.
- Prior art for event names: dotted `<area>.<thing>.<verb>` (`settings.model.view` `model_settings.py:413`, `backup.schedule.view`, `donation.consent.view`, `settings.assistant_memory.update` `assistant.py:634`). Medications use `log_document_event(event="view", document_id=<medication id or "all">, details={"entity_type": …})` (`medications.py:522-529`, `:1189-1196`). Keep that, so every medication read row has the same shape.
- HC-AUD-ORD-030 checks committing handlers only (`test_audit_order_guard.py:225-247`). A read handler that never commits is invisible to it, which is how these eight shipped. This is a new instance of recurring-failures §9 ("an invariant enforced at one site, not across its class"), recorded in the same commit.

**Main gets right today (must stay).**
1. 113 of 136 handlers audit; the AUDIT-PHI-001 allowlist sits in the one choke point (`create_audit_log`). Not edited.
2. The labels of owner AUDIT-READ-SCOPE: `/download-progress` stays unaudited (polled every 2 s), and `/tiers`, `/provider` GET and the diagnostics routes stay unaudited. This row adds no audit to them; it only names them in `UNAUDITED_ROUTES` with the owner row as the reason.
3. RESET-AUDIT-OWNER and OG-1: `api/profiles.py` is E-2's. Its four handlers sit in `UNAUDITED_ROUTES` with the reason "E-2 owns it (OG-1, Q-AUD-LIST)". The stale-entry check makes E-2 delete them when it lands, so the two rows cannot drift (E-2's file list gains `be/tests/test_audit_read_routes.py`: tell L0).
4. Every existing `CLASSIFICATION` row stays as it is; only rows are added.
5. Existing response bodies and status codes do not change. `test_medications_routes_http.py`, `test_fk_enforcement.py:646` (HC-FK, `GET …/doses` through `route_client`), `test_chat_sessions.py:802-829` and `test_medication_correlations.py` stay unedited and green. `route_client`'s default `AsyncMock` master accepts the new rows.
6. Read audits fail closed, as on every other read route; the new routes join that rule, which is a behaviour change only when the master DB cannot commit.

**Task 1: the eight reads (RED first).**
1. `tests/test_audit_read_routes.py`, through `route_client` with a recording master (the `_RecordingMasterDb` shape of `test_memory_audit.py:31-49`) and a real in-memory vault (`ProfileDatabaseBase.metadata.create_all`, with `import models.response_feedback` until MODELS-INIT-FEEDBACK lands):
   - HC-ARR-001…008: one per route, a 200 response writes exactly one `AuditLog` with the session `profile_id` and the event below. RED on main: zero rows.

     | route | `event_type` / helper | `entity_type` / `entity_id` | `details` |
     |---|---|---|---|
     | `GET /assistant/sessions` | `assistant.session.list` (`create_audit_log`, `action` = `event_type`) | `chat_session` / `"all"` | `{"count": n}` |
     | `GET /assistant/sessions/{id}` | `assistant.session.view` | `chat_session` / session id | `{"count": turns}` |
     | `GET /assistant/memory-settings` | `settings.assistant_memory.view` | `settings` / `"assistant_memory"` (same id as the update row) | none |
     | `GET /feedback/stats` | `feedback.stats.view` | `response_feedback` / `"all"` | `{"count": total}` |
     | `GET /medications/` | `log_document_event("view")` | `document_id="all"` | `{"entity_type": "medication_list", "count": n}` |
     | `GET /medications/{id}` | `log_document_event("view")` | medication id | `{"entity_type": "medication"}` |
     | `GET /medications/{id}/schedules` | `log_document_event("view")` | medication id | `{"entity_type": "medication_schedules", "count": n}` |
     | `GET /medications/{id}/doses` | `log_document_event("view")` | medication id | `{"entity_type": "medication_doses", "count": n, "date_filter": bool}` |

     The names are the planner's proposal; L0 may rename before the build. A 404 or 403 writes no view row (the audit comes after `verify_medication_access`, as at `:1187`).
   - HC-ARR-009: the vault holds sentinels (session title and turn text `SENTINEL-QUESTION-ldl`, medication name `SENTINELDRUG`, dosage note, feedback tag and correction text). After all eight GETs, there is one row per GET, checked first so the test is not vacuous, and no sentinel appears in any row's `action`, `entity_id` or `details_json`, nor in `caplog` (excluding `aiosqlite`/`sqlalchemy` records, as HC-LAG does).
   - HC-ARR-010: fail closed. With a master whose `commit` raises (`FailingCommitSession` with `fail_on`, `test_audit_order.py:64-75`, `raise_server_exceptions=False`), each GET returns 5xx and its body holds no sentinel. RED on main: 200 with the data.
2. Code: per route, add `master_db: AsyncSession = Depends(get_db)` and one `audit_and_commit` after the read and before the return. `api/feedback.py` imports `audit_and_commit` and `get_db` from `core.audit` and `core.database`. The stats read is fail-closed like every read; the fail-open `_emit_audit` stays for the two write routes (AO-SCOPE). Nothing else in these handlers changes.
3. `tests/test_rl_feedback.py:274`, `:293` call `get_feedback_stats` directly. They gain `master_db=<recording fake>` at the call site; their assertions stay as they are.
4. `test_audit_order_guard.py` `CLASSIFICATION`: the eight handlers as `"excluded: read route, audit_and_commit only"` (HC-AUD-ORD-031 then checks that each reaches `audit_and_commit`).

**Task 2: the route-inventory guard (the class, not the sites).**
- HC-ARR-011: every handler from `Graph().handlers()` reaches an audit sink, or is in `UNAUDITED_ROUTES: dict[str, str]` (key `api/<file>.py::<handler>`, value a reason naming the owner row or "no profile data: <what it reads>"). Stale entries fail too (an entry that now reaches a sink, or that names no handler). RED on main: the eight Task 1 handlers are unlisted. With Task 1 in, 15 entries remain (the ten no-profile-data handlers, the four E-2 handlers and `set_llm_provider` under PROVIDER-AUDIT "no"), or 14 under "yes".
- HC-ARR-012, break-it: a synthetic `@router.get` handler in an overlay tree (the `_overlay` helper of `test_audit_order_guard.py:305-313`) that reads `profile_db` and audits nothing is reported.
- **Blind spot, written into the test docstring:** the graph links calls by name and over-approximates (`test_audit_order_guard.py:273-281`), so a handler can look audited through a name collision; and the guard sees handlers, not paths, so a handler that audits on one branch passes (that is exactly AUDIT-CHAT-LEGACY's gap). The per-route HTTP tests are the proof; this guard only stops a new unaudited handler from appearing silently.

**Task 3: `PUT /settings/model/provider` (L0 ruling PROVIDER-AUDIT).**
- (a, planner's recommendation) Audit it: `settings.provider.update`, `entity_type="settings"`, `entity_id` the provider enum (`llama_cpp`/`ollama`, validated by `ProviderSetRequest`), `details` none. **Never** the model name (free text). Use `audit_and_commit` after the switch, plus a `CLASSIFICATION` row `"excluded: runtime provider switch, no vault write; audit_and_commit only"`. HC-ARR-013: one row per PUT, and the model-name sentinel is absent. Reason: every other settings write audits, and this one changes which local runner sees every profile's text.
- (b) Label it in `UNAUDITED_ROUTES` with "process-wide runtime switch, no profile data". Reason: the invariant does not cover it; no code changes.

**Tests that move, and how:** `test_rl_feedback.py:274`, `:293` (call sites only); `test_audit_order_guard.py` `CLASSIFICATION` (rows added only).
**Stay unedited and green:** `test_audit_phi_minimization.py` (HC-AUD-004…), `test_memory_audit.py`, `test_audit_order.py`, `test_medications_routes_http.py`, `test_medication_correlations.py`, `test_fk_enforcement.py`, `test_chat_sessions.py`, `test_provider_switch_nonblocking.py`, `test_provider_info_probe.py`, every other test in `test_audit_order_guard.py`.
**Adjacent, not folded:** E-2 (profiles); the fail-open `_emit_audit` on feedback writes (AO-SCOPE); `api/assistant.py::get_test_intent` puts the analyte in its path segment (the access log; SEARCH-LOG-SCRUB's "For L0" note).

### AUDIT-CHAT-LEGACY

**Source:** DOCS-AUDIT-1106 P1 ("legacy chat success return"). Kind: PRODUCT. MVP **P1**.

**Facts (re-read on `0f0cd100`).** `POST /assistant/chat` (`api/assistant.py:1089-1350`) has five ways out:

| path | lines | audit today |
|---|---|---|
| agent success | `:1150-1180` | agent node rows (`modules/agent/audit.py:49-80`), committed at `:1179-1180` (HC-AUD-ORD-060) |
| legacy pre-model advice gate | `:1182-1201` | one `assistant.prohibited_blocked`, `reason=pre_model_advice` |
| legacy, prohibited answer | `:1273-1285` | one `assistant.prohibited_blocked`, `reason=prohibited_pattern` |
| legacy, answer or G-B5 abstain | `:1202-1272`, out at `:1309` | **none** (`rag.query` writes no audit: `modules/rag.py` has no audit call) |
| no model (`ModelUnavailableError`) | `:1321-1340` | **none** (`_build_knowledge_fallback` reads observations, care tasks and medications, `:1715-1745`) |

The legacy path runs when the agent is off or the agent fails (`:1162-1173`). It reads the vault (observations, chunks, memory, history) and stores two turns.

**Main gets right today (must stay).**
1. HC-AUD-ORD-060 (`test_audit_order.py:874-878`): on agent success, `master.commits == 1` and the rows are exactly the agent's. **No new row on the agent path.**
2. HC-LAG (`test_legacy_advice_gate.py:188-244`): exactly one `prohibited_blocked` per gated turn. **No new row on the gate path.**
3. HC-SAFECHAT-001 (`test_safe_chat_prohibited.py:149-150`) and HC-SMA-004's chat case (`test_safety_mode_strict.py:374`, `:395-396`): exactly one row on a prohibited answer. **No new row when `result.prohibited_advice` is true.**
4. No question or answer text in any row or app log line (HC-LAG's caplog check `:225-235`).
5. The no-LLM fallback keeps answering whenever the master DB can commit (AGENT.md flow 2).
6. Order: audit before the turn is stored, as in both existing branches, so a failed audit stores no turn and serves nothing.

**Steps (RED first).**
1. `tests/test_audit_chat_legacy.py`, with the `_post_chat` shape of `test_safe_chat_prohibited.py:105-127` (agent off, stub RAG, recording master, real vault):
   - HC-ACL-001: a clean, verified legacy answer writes exactly one `assistant.chat.legacy` row, `entity_type="chat_session"`, `entity_id` the session id, `details == {"decision": "answer"}`. RED: zero rows.
   - HC-ACL-002: an invalid answer that G-B5 replaces with the abstain template writes one row with `{"decision": "abstain"}`. RED.
   - HC-ACL-003: with `rag.query` raising `ModelUnavailableError`, one `assistant.chat.fallback` row, no `details`. RED.
   - HC-ACL-004: the master commit raises. On the legacy answer path and on the fallback path the response is 5xx (`raise_server_exceptions=False`), no turn is stored, and the answer sentinel is not in the body. RED: 200 and two turns. (An exception raised in the `except ModelUnavailableError` block is not caught by the later `except Exception` at `:1341`, so it surfaces as a 500 from FastAPI; the test asserts the status, not the detail.)
   - HC-ACL-005: question and answer sentinels are in no row (row count asserted first) and in no `caplog` record.
2. Code: the two `audit_and_commit` calls named in the row, with event names as above (planner's proposal; L0 may rename). `decision` comes from whether `_legacy_serve_or_abstain` replaced the answer. No other line in `chat` moves.
3. HC-SAFECHAT-002 `:174`, under SAFECHAT-002-LICENCE: `assert _audit_rows(master) == []` becomes "exactly one `assistant.chat.legacy` row with `{"decision": "answer"}` and no `prohibited_blocked` row". The test then also checks the row exists, which is stricter on the prohibited side. Without the licence the row stops.

**Stay unedited and green:** HC-AUD-ORD-060, HC-LAG-*, HC-SAFECHAT-001 and -003, HC-SMA-001…008, `test_legacy_abstain.py`, `test_rag_timeout_answer.py`, `test_chat_sessions.py` (its direct `A.chat(...)` calls pass an `AsyncMock` master), the legacy eval harness (`tests/legacy_eval/harness.py`, no audit assertions).

### AUDIT-DB-SETTING-DEAD

**Source:** DOCS-AUDIT-1106 P2; AUDIT-MW-DOCSTRING (LOW, 2026-10-09, `implementation-program.md:505`). MVP **P3**.

**Facts.** `SecurityAuditMiddleware.__init__` stores `log_to_db` (`audit_middleware.py:31-33`) and never reads it; the module docstring says it "Optionally persists events to the database via core.audit" (`:5`). `main.py:131-134` passes `settings.audit_security_events_to_db` (`core/config.py:83`, default `False`). No other reader (`git grep` on `origin/main`). `Settings` has `extra="ignore"` (`core/config.py:18-22`), so a `.env` that still sets the key keeps starting after a removal. The middleware runs before auth (`main.py:120-140`, outermost to innermost), so it has no profile id. It logs the raw `scope["path"]`, which for `POST /interpretations/panels/{panel_name}/interpret` carries a panel name.

**Main gets right (must stay):** the `SECURITY_AUDIT` app-log line, its event classification (`:72-76`) and the six tests in `tests/security/test_audit_middleware.py`; no audit row from middleware ("audit rows come from handlers", #521 F23).

**Owner answer AUDIT-DB-SETTING (2026-11-06): "Remove it (Recommended)".** The row takes option (A), remove, and nothing else. The draft's option (B), wiring the flag to a master-DB row, is not planned and is not part of this row (no `core/audit.py` edit, no HC-ADBS-1xx tests, no retention change). Option (A): constructor without `log_to_db`, `main.py` without the keyword, `core/config.py:83` gone, docstring "Logs structured security events for mutating HTTP requests to the app log." RED: HC-ADBS-001 `SecurityAuditMiddleware(app, log_to_db=True)` raises `TypeError`; HC-ADBS-002 `"audit_security_events_to_db" not in Settings.model_fields`; both fail on main.


### MODEL-INT-TIER

**Source:** DOCS-AUDIT-1106 P9. MVP **P3**.

**Facts (re-read on `0f0cd100`).**
- `llama_cpp_provider.py:164`: `verify_and_log(model_path, getattr(self._settings, "llm_model_tier", "low"))`. `Settings` has no `llm_model_tier`, so the tier is always `"low"`.
- What is the active tier? Not a setting. `default_model_tier` (`core/config.py:97`) has no reader. The per-profile `preferred_tier` (`models/model_settings.py:45`, written by `ModelSelector`, `model_selector.py:283`) chooses what `ModelSelector.get_model_path` and the dormant D7 `load_model` use (`:377-404`, `:456`); the chat provider never reads it. `get_provider()` (`core/llm/factory.py:24-70`) builds one process-wide `LlamaCppProvider(model_path=None, …)`, and `_find_model_path` (`:99-127`) takes the first GGUF matching `default_chat_model*`, then Phi-4-mini on CPU, then gemma4, phi-3, llama, mistral, qwen, then `*.gguf`. So the loaded file is the only true key.
- `config/model_manifest.json`: only "low" has a `filename` (`qwen2.5-0.5b-instruct-q4_k_m.gguf`). "mid", "high" and the gemma entries have `filename: null` with the shared pattern `q4_k_m`, so a pattern match cannot tell them apart. Every chat `sha256` is `null`. The manifest's own note for "mid" says the pin "must record the exact resolved filename".
- Effect today: every load logs UNPINNED for tier 'low', whatever loaded. Once a chat pin exists, a mid or high model would be checked against "low": a false MISMATCH at ERROR, or a false UNPINNED. A false VERIFIED is impossible, because the hash would have to equal low's pin.

**Main gets right (must stay):** the integrity check never blocks loading (the `try/except` at `:161-166`); nothing is hashed when there is no pin (cost: a 7 GB GGUF); HC-MINT-001…011 (`test_model_integrity.py`) unedited; HC-MPATH-001 (`test_model_path_logs.py:28-44`) monkeypatches `modules.model_integrity.verify_and_log`, so the provider keeps importing it at call time and keeps calling it with `(path, key)`.

**Rule.** The key is the manifest entry whose `filename` equals the loaded file's name, compared case-folded (Windows paths). With no such entry the key is `"unrecognised"`, which `verify_model_file` reports as UNKNOWN_TIER ("identity not verified"), logged at WARNING as today. No pattern matching and no hash-against-all-pins (both are ambiguous or costly).

**RED tests (`tests/test_model_int_tier.py`; patch `model_integrity._DEFAULT_MANIFEST` to a temp manifest, `_load_llama_class` to a fake, `_find_model_path` to a temp file).**
- HC-MTIER-001: the manifest entry "mid" has `filename` = the temp file's name and `sha256` = its hash. The load logs VERIFIED for 'mid'. RED on main: tier 'low', no such entry in the temp manifest, so UNKNOWN_TIER.
- HC-MTIER-002: "low" is pinned, and an unrelated file `other.gguf` is loaded. Result UNKNOWN_TIER, no ERROR record. RED on main: MISMATCH for 'low' at ERROR (a false alarm).
- HC-MTIER-003: the file is named as "low" with wrong bytes. MISMATCH for 'low' at ERROR. Green on main too: this pins what main gets right.
- HC-MTIER-004: `compute_sha256` is called 0 times when no entry names the file (spy).

### MODELS-INIT-FEEDBACK

**Source:** DOCS-AUDIT-1106 P11. MVP **P3**.

**Facts.** `models/__init__.py` imports every model module except `response_feedback` (`:14-41`). It is registered only when something imports it: `api/feedback.py:37`, `api/profiles.py:81`, and four tests by hand (§0). Runtime schema is migration-built, so nothing at runtime depends on this. Anything that reads `ProfileDatabaseBase.metadata` does: the anti-drift tests HC-RESET-010 (`test_profile_test_reset.py:189-199`) and the FK declared-set check (`test_fk_audit.py:63-68`) hold only because their files import it by hand. `migrations/profile/env.py:30-40` takes its metadata from the `models` package. `response_feedback.py` imports only `core.profile_database` and `core.time`, the same as `chat_session.py`, so the import adds no cycle.

**Main gets right (must stay):** no migration; the four hand imports stay (harmless; not edited); `python -c "from main import app"` boots; HC-RESET-010, HC-RESET-011, HC-FKA-* unedited.

**RED tests (`tests/test_models_init_feedback.py`). They run in a subprocess:** pytest collection already imports `models.response_feedback` through other test modules, so an in-process assert would pass on main.
- HC-MIF-001: `subprocess.run([sys.executable, "-c", "import models; from core.profile_database import ProfileDatabaseBase; print('response_feedback' in ProfileDatabaseBase.metadata.tables)"], cwd=<backend>)` prints `True`. RED on main: `False`.
- HC-MIF-002, anti-drift: in the same kind of subprocess, after `import models`, the union of `Base.metadata.tables` and `ProfileDatabaseBase.metadata.tables` equals the set of `__tablename__` values found by an AST scan of `models/*.py`. RED on main: `response_feedback` missing.

### ONBOARDING-LANDS-OVERVIEW

**Source:** DOCS-AUDIT-1106 P12; candidate bullet ONBOARDING-LANDS-INBOX (`queue.md:749`, #507 review finding 4, comment 6684886023). Owner answer LANDING-OVERVIEW (2026-11-06): "Land on Overview (Recommended)", so unlock, new profile and recovery all land on Overview. MVP **P2**.

**Facts.** `ProfileSetup.tsx:219` (unlock), `:310` (after a new profile's recovery code) and `RecoverProfile.tsx:74` (after a reset password's new code) `navigate('/inbox')`. The index route is `/overview` (`App.tsx:246-247`). The plan says Overview replaces "landing on an empty Inbox" (`2026-10-23-frontend-revamp-plan.md:224`). Overview fetches documents (`OverviewPage.tsx:339`), so the e2e waits on `GET /documents` (`session-reentry.spec.ts:69-78`, `session-lock-now.spec.ts:100-106`) still hold.

**Main gets right (must stay):** `queryClient.clear()` before navigating (`ProfileSetup.tsx:217`); the Lift (`beginLift()`, `:218`); the recovery-code acknowledge gate; 401 and 429 handling; `openAuthenticatedPage`'s default `'/inbox'` (`e2e/support/auth.ts:93`, a `goto` after seeding storage, not a post-login landing; unchanged); `RecoverProfile`'s 401 path (RECOVER-401-REDIRECT, `reauth: true`).

**RED tests.** HC-OLO-001…003 (vitest): unlock, create (acknowledge) and recover (acknowledge) each call `navigate('/overview')`. RED on main. The existing literals listed in the row change from `'/inbox'` to `'/overview'` (a contract change, each as strict as before). The e2e literals change the same way. `session-reentry.spec.ts:81` asserts the Overview h1 in place of "Document Inbox". The ui-auth titles that say "/inbox" are renamed. The `(timing)` ones (G5 `:438` and the Lift timing) run on the quiet box (`/tmp/claude-1000/quiet_run.sh`), because Overview mounts more queries than Inbox.

### FE-STALE-LINKS

**Source:** DOCS-AUDIT-1106 P12 (items 3 and 4). MVP **P3**. L0 may fold it into UI-MICRO.

**Facts.** Four links go to the redirect-only `/trends`: `MedicationDetail.tsx:372` (`navigate('/trends')`), `:381` (`/trends?analyte=…`), `SearchPage.tsx:35` and `TimelinePage.tsx:51` (`link: '/trends'`). `RedirectToResults` keeps the query string and uses `replace` (`App.tsx:212-219`), so users see no difference. `@types` → `./src/types` is in `tsconfig.json:27`, `vite.config.ts:41` and `vitest.config.ts:34`; the directory does not exist and nothing imports from it.

**Main gets right (must stay):** the redirects themselves (HC-UIRES-001, `ui-results.test.tsx:318-361`; `e2e/ui-shell.spec.ts:47`, `:70`, `:83`); `?analyte=` carried; link labels.

**RED tests (`fe/__tests__/fe-stale-links.test.tsx`).** HC-FSL-001: MedicationDetail's empty-state button navigates to `/results`, and a related-lab link's `href` is `/results?analyte=<a>`. HC-FSL-002: the Search and Timeline observation links point to `/results`. HC-FSL-003: a source scan finds no `'/trends'` or `'/interpret'` route literal under `fe/` outside `App.tsx` and `__tests__/`. All three are RED on main. The alias removal is checked by `npx tsc --noEmit`, `npm run build` and `npx vitest run` staying clean.

### DOCSTRINGS-1106

**Source:** DOCS-AUDIT-1106 P10, plus P15's `ModelRunner` args and the QUESTION-INJECTION comment at `be/modules/rag.py:762-771`. Comments only. MVP **P3**.

| file:line | says | true on `0f0cd100` |
|---|---|---|
| `be/core/database.py:35-39` | "Only Profile and AuditLog use this base" | also `BackupSchedule`, `BiomarkerKnowledge`, `InterventionMapping`, `BiomarkerRelationship` (6 master tables) |
| `be/migrations/master/env.py:4-8` | profiles, audit_logs, KB | plus `backup_schedules` (`002_backup_schedules`) |
| `be/migrations/profile/env.py:4-9` | 12 profile tables | 25 vault tables; point at the `models` package, not a list |
| `be/api/backup.py:10-15` | "This is the one export-shaped path that is deliberately unredacted" | `GET /export/csv` and `/export/json` are exempt too (owner D3, CLAUDE.md); keep "Do not 'fix' it to match `export.py`" |
| `scripts/agent_eval_gate.py:3-8`, `:18-28` | "four axes"; "a future CI workflow step … NOT part of this change" | six axes plus the R-14 and injection-compose checks (`scorer.py:114-133`); CI's "Agent Eval Gate" job runs it (`ci.yml:247`, `:270`) |
| `be/modules/agent/eval/scorer.py:1`, `:102` | "Four-axis" | six axes |
| `be/scripts/__init__.py:1-6` | lists `seed_knowledge_base` only | nine scripts; say "see the directory" |
| `fe/utils/correlation.ts:15-17` | "which TrendsDashboard needs" | `pages/ResultsPage.tsx:49` imports it |
| `be/modules/rag.py:762-771` (comment only; owner answer QUESTION-INJECTION, 2026-11-06, "Intended; write it down (Recommended)") | (silent) | the user's question is not injection-filtered on the legacy path, on purpose: history (`:776-790`) and chunks (`:808-830`) are filtered; the question is not. The comment says so, and that the output checks (advice gate, citation validation, prohibited-pattern check) are the backstop. The docs sentence is in `docs/agentic/evals.md` (this docs batch) |
| `be/core/model_runner.py:60-76` | (silent) | `model_path`, `n_ctx`, `n_threads` (`:77-88`) are stored and never read; the provider comes from `get_provider()` |
| `be/core/auth.py:331` (L0 licence only) | "HTTPException 403" | `_get_required_profile_connection` raises 401 (`:307-308`) |

**Check:** the diff adds or removes only comment and docstring lines (`be/modules/rag.py` gets a comment only; B-3 (#264) also edits that file and rebases on it) (the PR pastes `git diff -U0` and states that every `+`/`-` line is inside a docstring or a comment); the backend collected count delta is 0; `npx tsc --noEmit` is clean. No new test: comments cannot be tested, and saying so is the honest gap.


---

## Appendix A — every route under `src/backend/api/` on `0f0cd100`

Method: AST scan of each `@router.<get|post|put|patch|delete>` handler. "How" lists the audit calls in the handler body and in same-file helpers it calls. The HC-AUD-ORD-030 call graph (`Graph().handlers()`, sinks `create_audit_log`/`audit_and_commit`/`audit_intent`) gives the same 23 non-auditing handlers. Line = the `def` line (the decorator is 1-5 lines above). Path = router prefix from `api/__init__.py:48-72` + decorator path.

| # | file:def line | method | path | handler | audits today, and how |
|---|---|---|---|---|---|
| 1 | `assistant.py:433` | GET | `/assistant/sessions` | `list_sessions` | **no** -> AUDIT-READ-ROUTES T1 (`assistant.session.list`) |
| 2 | `assistant.py:465` | POST | `/assistant/sessions` | `create_session` | yes: `create_audit_log` |
| 3 | `assistant.py:510` | GET | `/assistant/sessions/{session_id}` | `get_session_history` | **no** -> AUDIT-READ-ROUTES T1 (`assistant.session.view`) |
| 4 | `assistant.py:537` | DELETE | `/assistant/sessions/{session_id}` | `delete_session` | yes: `audit_intent` |
| 5 | `assistant.py:581` | GET | `/assistant/memory-settings` | `get_memory_settings` | **no** -> AUDIT-READ-ROUTES T1 (`settings.assistant_memory.view`) |
| 6 | `assistant.py:603` | PATCH | `/assistant/memory-settings` | `update_memory_settings` | yes: `create_audit_log` |
| 7 | `assistant.py:685` | GET | `/assistant/safety-mode` | `get_safety_mode` | yes: `audit_and_commit` |
| 8 | `assistant.py:707` | PATCH | `/assistant/safety-mode` | `update_safety_mode` | yes: `create_audit_log` |
| 9 | `assistant.py:1090` | POST | `/assistant/chat` | `chat` | partly: agent path (agent node rows, HC-AUD-ORD-060), advice gate and prohibited branch (`assistant.prohibited_blocked`); **legacy success/abstain and the no-model fallback write none** -> AUDIT-CHAT-LEGACY |
| 10 | `assistant.py:1477` | GET | `/assistant/test-intent/{analyte}` | `get_test_intent` | no; static reference lookup, no profile data (label) |
| 11 | `assistant.py:1513` | GET | `/assistant/glossary/{term}` | `get_glossary_term` | no; static glossary lookup, no profile data (label) |
| 12 | `assistant.py:1539` | GET | `/assistant/verification-status` | `get_verification_status` | yes: `audit_and_commit` |
| 13 | `backup.py:209` | GET | `/backup/` | `list_backups` | yes: `audit_and_commit` |
| 14 | `backup.py:244` | POST | `/backup/` | `create_backup` | yes: `audit_and_commit` |
| 15 | `backup.py:290` | POST | `/backup/{backup_id}/verify` | `verify_backup` | yes: `audit_and_commit` |
| 16 | `backup.py:319` | GET | `/backup/{backup_id}/download` | `download_backup` | yes: `audit_and_commit`, `log_export_event` |
| 17 | `backup.py:369` | POST | `/backup/{backup_id}/restore` | `restore_backup` | yes: `audit_and_commit`, `audit_intent` |
| 18 | `backup.py:508` | POST | `/backup/prune` | `prune_backups` | yes: `audit_and_commit` |
| 19 | `backup.py:532` | GET | `/backup/schedule` | `get_schedule` | yes: `audit_and_commit` |
| 20 | `backup.py:558` | PUT | `/backup/schedule` | `set_schedule` | yes: `create_audit_log` |
| 21 | `care_tasks.py:126` | GET | `/care-tasks/` | `list_care_tasks` | yes: `audit_and_commit`, `log_care_task_event` |
| 22 | `care_tasks.py:160` | GET | `/care-tasks/candidates` | `get_care_task_candidates` | yes: `audit_and_commit`, `log_care_task_event` |
| 23 | `care_tasks.py:215` | POST | `/care-tasks/accept` | `accept_care_task` | yes: `log_care_task_event` |
| 24 | `care_tasks.py:329` | PATCH | `/care-tasks/{task_id}` | `update_care_task` | yes: `log_care_task_event` |
| 25 | `documents.py:412` | POST | `/documents/import` | `import_document` | yes: `log_document_event` |
| 26 | `documents.py:1085` | GET | `/documents/` | `list_documents` | yes: `audit_and_commit`, `log_document_event` |
| 27 | `documents.py:1139` | GET | `/documents/{document_id}` | `get_document` | yes: `audit_and_commit`, `log_document_event` |
| 28 | `documents.py:1174` | POST | `/documents/{document_id}/reprocess` | `reprocess_document` | yes: `audit_intent`, `log_document_event` |
| 29 | `documents.py:1283` | POST | `/documents/{document_id}/verify` | `verify_document` | yes: `log_document_event` |
| 30 | `documents.py:1364` | GET | `/documents/{document_id}/category` | `get_document_category` | yes: `audit_and_commit`, `log_document_event` |
| 31 | `documents.py:1408` | GET | `/documents/{document_id}/entities` | `get_document_entities` | yes: `audit_and_commit`, `log_document_event` |
| 32 | `documents.py:1454` | PATCH | `/documents/{document_id}/entities/{entity_id}/verification` | `set_entity_verification` | yes: `log_document_event` |
| 33 | `documents.py:1535` | GET | `/documents/highlights/summary` | `get_highlights_summary` | yes: `audit_and_commit`, `log_document_event` |
| 34 | `documents.py:1596` | GET | `/documents/{document_id}/highlights` | `get_document_highlights` | yes: `audit_and_commit`, `log_document_event` |
| 35 | `documents.py:1635` | GET | `/documents/{document_id}/pages` | `get_document_pages` | yes: `audit_and_commit`, `log_document_event` |
| 36 | `documents.py:1744` | GET | `/documents/{document_id}/pages/{page_number}/image` | `get_page_image` | yes: `audit_and_commit`, `log_document_event` |
| 37 | `documents.py:1851` | DELETE | `/documents/{document_id}` | `delete_document` | yes: `audit_intent`, `log_document_event` |
| 38 | `donation.py:123` | GET | `/donation/consents` | `list_consents` | yes: `audit_and_commit` |
| 39 | `donation.py:152` | PUT | `/donation/consents/{purpose}` | `set_consent` | yes: `audit_and_commit`, `audit_intent` |
| 40 | `export.py:414` | POST | `/export/doctor-summary` | `generate_doctor_summary` | yes: `audit_and_commit`, `log_export_event` via `generate_questions->audit_and_commit`, `generate_questions->log_export_event` |
| 41 | `export.py:530` | GET | `/export/doctor-summary/{summary_id}/download` | `download_summary` | yes: `audit_and_commit`, `audit_denial`, `log_export_event` |
| 42 | `export.py:658` | POST | `/export/questions` | `generate_questions` | yes: `audit_and_commit`, `log_export_event` |
| 43 | `export.py:753` | POST | `/export/visit-prep` | `generate_visit_prep` | yes: `audit_and_commit`, `log_export_event` via `generate_questions->audit_and_commit`, `generate_questions->log_export_event` |
| 44 | `export.py:886` | GET | `/export/visit-prep/{packet_id}/download` | `download_visit_prep` | yes: `audit_and_commit`, `audit_denial`, `log_export_event` |
| 45 | `export.py:973` | GET | `/export/csv` | `export_csv` | yes: `audit_and_commit`, `log_export_event` |
| 46 | `export.py:1029` | GET | `/export/json` | `export_json` | yes: `audit_and_commit`, `log_export_event` |
| 47 | `export.py:1217` | POST | `/export/fhir` | `generate_fhir_export` | yes: `audit_and_commit`, `log_export_event` |
| 48 | `export.py:1324` | GET | `/export/fhir/{export_id}/download` | `download_fhir_export` | yes: `audit_and_commit`, `audit_denial`, `log_export_event` |
| 49 | `feedback.py:218` | POST | `/feedback/turns/{turn_id}` | `upsert_feedback` | yes, fail-open: via `_emit_audit->create_audit_log` (swallows errors, AO-SCOPE) |
| 50 | `feedback.py:299` | GET | `/feedback/stats` | `get_feedback_stats` | **no** -> AUDIT-READ-ROUTES T1 (`feedback.stats.view`) |
| 51 | `feedback.py:345` | POST | `/feedback/export` | `export_dataset` | yes, fail-open: via `_emit_audit->create_audit_log` (swallows errors) |
| 52 | `gamification.py:77` | GET | `/gamification/badges` | `list_badges` | yes: `_audit_view` via `_audit_view->audit_and_commit` |
| 53 | `gamification.py:137` | GET | `/gamification/streaks` | `get_streaks` | yes: `_audit_view` via `_audit_view->audit_and_commit` |
| 54 | `interpretations.py:456` | POST | `/interpretations/observations/{observation_id}/interpret` | `generate_interpretation` | yes: `_audit_interpretation`, `_audit_withheld` via `_audit_interpretation->audit_and_commit`, `_audit_interpretation->audit_intent` |
| 55 | `interpretations.py:540` | POST | `/interpretations/observations/{observation_id}/interpret-grounded` | `generate_grounded_interpretation` | yes: `_audit_interpretation`, `_audit_withheld` via `_audit_interpretation->audit_and_commit`, `_audit_interpretation->audit_intent` |
| 56 | `interpretations.py:753` | GET | `/interpretations/observations/{observation_id}/interpretation` | `get_interpretation` | yes: `_audit_interpretation`, `_audit_withheld` via `_audit_interpretation->audit_and_commit`, `_audit_interpretation->audit_intent` |
| 57 | `interpretations.py:851` | POST | `/interpretations/panels/{panel_name}/interpret` | `generate_panel_interpretation` | yes: `_audit_interpretation`, `_audit_withheld` via `_audit_interpretation->audit_and_commit`, `_audit_interpretation->audit_intent` |
| 58 | `interpretations.py:965` | GET | `/interpretations/recent` | `get_recent_interpretations` | yes: `_audit_interpretation` via `_audit_interpretation->audit_and_commit`, `_audit_interpretation->audit_intent` |
| 59 | `interpretations.py:1001` | GET | `/interpretations/knowledge/biomarker/{analyte_canonical}` | `get_biomarker_knowledge` | no; master knowledge base, "Public knowledge - not patient-specific" (label) |
| 60 | `interpretations.py:1034` | POST | `/interpretations/batch` | `batch_generate_interpretations` | yes: `_audit_interpretation`, `_audit_unverified_refusal`, `_audit_withheld` via `_audit_interpretation->audit_and_commit`, `_audit_interpretation->audit_intent` |
| 61 | `med_reconcile.py:57` | GET | `/med-reconciliation/` | `get_med_reconciliation` | yes: `audit_and_commit`, `log_document_event` |
| 62 | `medications.py:314` | POST | `/medications/` | `create_medication` | yes: `log_document_event` |
| 63 | `medications.py:366` | GET | `/medications/` | `list_medications` | **no** -> AUDIT-READ-ROUTES T1 (`document.view`, `entity_type=medication_list`) |
| 64 | `medications.py:395` | GET | `/medications/{medication_id}` | `get_medication` | **no** -> AUDIT-READ-ROUTES T1 (`document.view`, `entity_type=medication`) |
| 65 | `medications.py:457` | GET | `/medications/{medication_id}/correlations` | `get_medication_correlations` | yes: `audit_and_commit`, `log_document_event` |
| 66 | `medications.py:583` | PATCH | `/medications/{medication_id}` | `update_medication` | yes: `_audit_after_change` via `_audit_after_change->log_document_event` |
| 67 | `medications.py:652` | DELETE | `/medications/{medication_id}` | `delete_medication` | yes: `audit_intent`, `log_document_event` |
| 68 | `medications.py:725` | POST | `/medications/{medication_id}/schedules` | `create_schedule` | yes: `_audit_after_change` via `_audit_after_change->log_document_event` |
| 69 | `medications.py:788` | GET | `/medications/{medication_id}/schedules` | `list_schedules` | **no** -> AUDIT-READ-ROUTES T1 (`document.view`, `entity_type=medication_schedules`) |
| 70 | `medications.py:824` | PATCH | `/medications/{medication_id}/schedules/{schedule_id}` | `update_schedule` | yes: `_audit_after_change` via `_audit_after_change->log_document_event` |
| 71 | `medications.py:899` | DELETE | `/medications/{medication_id}/schedules/{schedule_id}` | `delete_schedule` | yes: `audit_intent`, `log_document_event` |
| 72 | `medications.py:963` | POST | `/medications/{medication_id}/doses` | `log_dose` | yes: `_audit_after_change` via `_audit_after_change->log_document_event` |
| 73 | `medications.py:1118` | GET | `/medications/{medication_id}/doses` | `list_doses` | **no** -> AUDIT-READ-ROUTES T1 (`document.view`, `entity_type=medication_doses`) |
| 74 | `medications.py:1163` | GET | `/medications/{medication_id}/stats` | `get_adherence_stats` | yes: `audit_and_commit`, `log_document_event` |
| 75 | `medications.py:1348` | POST | `/medications/{medication_id}/learn-patterns` | `learn_patterns` | yes: `_audit_after_change` via `_audit_after_change->log_document_event` |
| 76 | `memory.py:95` | POST | `/memory/` | `create_memory_item` | yes: `audit_and_commit`, `log_memory_event` |
| 77 | `memory.py:142` | GET | `/memory/` | `list_memory_items` | yes: `audit_and_commit`, `log_memory_event` |
| 78 | `memory.py:172` | GET | `/memory/{item_id}` | `get_memory_item` | yes: `audit_and_commit`, `log_memory_event` |
| 79 | `memory.py:208` | PUT | `/memory/{item_id}` | `update_memory_item` | yes: `audit_and_commit`, `log_memory_event` |
| 80 | `memory.py:261` | DELETE | `/memory/{item_id}` | `delete_memory_item` | yes: `audit_intent`, `log_memory_event` |
| 81 | `model_settings.py:397` | GET | `/settings/model` | `get_model_settings` | yes: `audit_and_commit` |
| 82 | `model_settings.py:493` | POST | `/settings/model/detect` | `run_hardware_detection` | yes: `_audit_settings_change` via `_audit_settings_change->create_audit_log` |
| 83 | `model_settings.py:538` | POST | `/settings/model/tier` | `set_model_tier` | yes: `_audit_settings_change` via `_audit_settings_change->create_audit_log` |
| 84 | `model_settings.py:600` | GET | `/settings/model/tiers` | `list_tiers` | no; no profile data (owner AUDIT-READ-SCOPE 2026-10-21) (label) |
| 85 | `model_settings.py:649` | GET | `/settings/model/download-progress` | `get_download_progress` | no; labelled exception, owner AUDIT-READ-SCOPE (a) |
| 86 | `model_settings.py:716` | POST | `/settings/model/download` | `start_model_download` | yes: `_audit_settings_change` via `_audit_settings_change->create_audit_log` |
| 87 | `model_settings.py:802` | GET | `/settings/model/external-api` | `get_external_api_settings` | yes: `audit_and_commit` |
| 88 | `model_settings.py:841` | PUT | `/settings/model/external-api` | `save_external_api_settings` | yes: `_audit_settings_change` via `_audit_settings_change->create_audit_log` |
| 89 | `model_settings.py:892` | GET | `/settings/model/provider` | `get_llm_provider` | no; no profile data (owner AUDIT-READ-SCOPE) (label) |
| 90 | `model_settings.py:932` | PUT | `/settings/model/provider` | `set_llm_provider` | **no**; process-wide runtime switch, no profile data -> AUDIT-READ-ROUTES T3 under L0 ruling PROVIDER-AUDIT |
| 91 | `model_settings.py:1087` | GET | `/settings/model/timezone` | `get_timezone` | yes: `audit_and_commit` |
| 92 | `model_settings.py:1108` | PUT | `/settings/model/timezone` | `set_timezone` | yes: `_audit_settings_change` via `_audit_settings_change->create_audit_log` |
| 93 | `model_settings.py:1137` | GET | `/settings/model/voice` | `get_voice_settings` | yes: `audit_and_commit` |
| 94 | `model_settings.py:1161` | PATCH | `/settings/model/voice` | `update_voice_settings` | yes: `_audit_settings_change` via `_audit_settings_change->create_audit_log` |
| 95 | `model_settings.py:1199` | GET | `/settings/model/gamification` | `get_gamification_settings` | yes: `audit_and_commit` |
| 96 | `model_settings.py:1219` | PATCH | `/settings/model/gamification` | `update_gamification_settings` | yes: `audit_and_commit` |
| 97 | `model_settings.py:1249` | GET | `/settings/model/diagnostics` | `get_environment_diagnostics` | no; no profile data (owner AUDIT-READ-SCOPE) (label) |
| 98 | `model_settings.py:1261` | POST | `/settings/model/diagnostics/recheck` | `recheck_environment_diagnostics` | no; no profile data (owner AUDIT-READ-SCOPE) (label) |
| 99 | `model_settings.py:1272` | PATCH | `/settings/model/ocr` | `update_ocr_settings` | yes: `_audit_settings_change` via `_audit_settings_change->create_audit_log` |
| 100 | `model_settings.py:1308` | PATCH | `/settings/model/agent` | `update_agent_settings` | yes: `_audit_settings_change` via `_audit_settings_change->create_audit_log` |
| 101 | `notifications.py:149` | GET | `/notifications/settings/{medication_id}` | `get_notification_settings` | yes: `audit_and_commit`, `log_document_event` |
| 102 | `notifications.py:210` | PATCH | `/notifications/settings/{medication_id}` | `update_notification_settings` | yes: `log_document_event` |
| 103 | `notifications.py:321` | GET | `/notifications/history` | `get_notification_history` | yes: `audit_and_commit`, `log_document_event` |
| 104 | `notifications.py:425` | POST | `/notifications/test` | `send_test_notification` | no; OS test toast with request text, no profile data (label) |
| 105 | `notifications.py:459` | POST | `/notifications/test/{medication_id}` | `send_test_medication_notification` | yes: `audit_and_commit`, `log_document_event` |
| 106 | `notifications.py:546` | GET | `/notifications/scheduler/status` | `get_scheduler_status` | no; process-wide scheduler counts, no profile data (label) |
| 107 | `notifications.py:571` | POST | `/notifications/{reminder_id}/interaction` | `record_reminder_interaction` | yes: `log_document_event` |
| 108 | `observations.py:271` | GET | `/observations/panels/{panel_id}/snapshots` | `get_panel_snapshots` | yes: `audit_and_commit`, `log_observation_event` |
| 109 | `observations.py:350` | GET | `/observations/` | `list_observations` | yes: `audit_and_commit`, `log_observation_event` |
| 110 | `observations.py:423` | GET | `/observations/{observation_id}` | `get_observation` | yes: `audit_and_commit`, `log_observation_event` |
| 111 | `observations.py:458` | POST | `/observations/{observation_id}/verify` | `verify_observation` | yes: `log_observation_event` |
| 112 | `observations.py:608` | GET | `/observations/trends/{analyte}` | `get_analyte_trend` | yes: `audit_and_commit`, `log_observation_event` |
| 113 | `observations.py:840` | GET | `/observations/panels/{panel_id}` | `get_panel` | yes: `audit_and_commit`, `log_observation_event` |
| 114 | `pinboards.py:220` | POST | `/pinboards/` | `create_pinboard` | yes: `audit_and_commit`, `log_pinboard_event` |
| 115 | `pinboards.py:238` | GET | `/pinboards/` | `list_pinboards` | yes: `audit_and_commit`, `log_pinboard_event` |
| 116 | `pinboards.py:253` | PATCH | `/pinboards/{pinboard_id}` | `rename_pinboard` | yes: `audit_and_commit`, `log_pinboard_event` |
| 117 | `pinboards.py:272` | DELETE | `/pinboards/{pinboard_id}` | `delete_pinboard` | yes: `audit_intent`, `log_pinboard_event` |
| 118 | `pinboards.py:295` | POST | `/pinboards/{pinboard_id}/items` | `add_pinboard_item` | yes: `audit_and_commit`, `log_pinboard_event` |
| 119 | `pinboards.py:335` | GET | `/pinboards/{pinboard_id}/items` | `list_pinboard_items` | yes: `audit_and_commit`, `log_pinboard_event` via `_prune_stale_items->audit_intent`, `_prune_stale_items->log_pinboard_event` |
| 120 | `pinboards.py:358` | DELETE | `/pinboards/{pinboard_id}/items/{item_id}` | `remove_pinboard_item` | yes: `audit_and_commit`, `log_pinboard_event` |
| 121 | `pinboards.py:397` | POST | `/pinboards/{pinboard_id}/export` | `export_pinboard_packet` | yes: `audit_and_commit`, `log_pinboard_event` via `_prune_stale_items->audit_intent`, `_prune_stale_items->log_pinboard_event` |
| 122 | `profiles.py:319` | GET | `/profiles/` | `list_profiles` | **no** -> E-2 (Q-AUD-LIST answered (a); `profile.list`) |
| 123 | `profiles.py:333` | POST | `/profiles/` | `create_profile` | yes: `_audit_fk_orphan_cleanup`, `log_profile_event` via `_audit_fk_orphan_cleanup->create_audit_log` |
| 124 | `profiles.py:431` | POST | `/profiles/login` | `login` | yes: `_audit_fk_orphan_cleanup`, `log_profile_event` via `_audit_fk_orphan_cleanup->create_audit_log` |
| 125 | `profiles.py:496` | GET | `/profiles/me` | `get_current_profile` | **no** -> E-2 (OG-1 answered; `profile.view`) |
| 126 | `profiles.py:518` | POST | `/profiles/logout` | `logout` | yes: `log_profile_event` |
| 127 | `profiles.py:558` | POST | `/profiles/test/reset` | `reset_synthetic_test_profile` | **no** -> E-2 (RESET-AUDIT-OWNER: W-11a PR-1 writes `profile.test_reset`) |
| 128 | `profiles.py:665` | POST | `/profiles/{profile_id}/recovery-code` | `issue_recovery_code` | yes: `log_profile_event` |
| 129 | `profiles.py:724` | POST | `/profiles/{profile_id}/recover` | `recover_profile` | yes: `_audit_fk_orphan_cleanup`, `log_profile_event` via `_audit_fk_orphan_cleanup->create_audit_log`, `_fail->log_profile_event` |
| 130 | `profiles.py:850` | DELETE | `/profiles/{profile_id}` | `delete_profile` | yes: `audit_intent`, `create_audit_log` |
| 131 | `profiles.py:1050` | GET | `/profiles/{profile_id}` | `get_profile` | **no** -> E-2 (OG-1 answered; `profile.view`) |
| 132 | `profiles.py:1073` | POST | `/profiles/{profile_id}/lock` | `lock_profile` | yes: `log_profile_event` |
| 133 | `profiles.py:1118` | POST | `/profiles/{profile_id}/unlock` | `unlock_profile` | yes: `_audit_fk_orphan_cleanup`, `log_profile_event` via `_audit_fk_orphan_cleanup->create_audit_log` |
| 134 | `profiles.py:1180` | POST | `/profiles/{profile_id}/change-password` | `change_password` | yes: `log_profile_event` |
| 135 | `search.py:56` | GET | `/search/` | `get_search_results` | yes: `audit_and_commit` |
| 136 | `timeline.py:65` | GET | `/timeline/` | `get_timeline` | yes: `audit_and_commit` |

Command (scratch copy of `origin/main` `0f0cd100`): `python3 -I inventory.py main/src/backend` (136 rows) and `python3 -I reach.py main/src/backend` (23 `NO-AUDIT-REACH` lines), both in the planner scratchpad, not committed.
