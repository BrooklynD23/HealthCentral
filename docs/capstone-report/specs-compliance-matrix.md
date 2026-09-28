# Asclexis — Specs & Compliance Matrix

**Last Updated:** 2026-09-27
**Evidence basis:** main @ `40f590e`, re-checked 2026-09-27. The rules behind each row are in [architecture-engineering-contract.md](architecture-engineering-contract.md) and the architecture in [architecture-overview.md](architecture-overview.md).

Each row maps one requirement to:

- its **authoritative source**;
- the **implementation** and **tests**;
- the **gate** that would catch a violation;
- the **current status**, with evidence;
- any **owner gate**.

A document statement, owner preference, proposal, code comment, or legal conclusion is **never** counted as an implemented control. Controls that are unenforced or only partial are shown as gaps.

**Status values** (one never implies another):

| Status | Meaning |
|---|---|
| `enforced` | Implemented, tested, and an automated gate fails on violation. |
| `tested` | Implemented and exercised by tests, but no dedicated gate beyond the test suite. |
| `implemented` | Code exists and is wired; no test found. |
| `partial` | True for part of the scope; the gap is named. |
| `gap` | Not implemented or not enforced. |
| `contradicted` | Code disagrees with the authoritative source. |
| `owner-gated` | Needs an owner decision that is not on record. |
| `unknown` | Could not be determined. |

"Direct-call" means route tests call the handler as a function, so FastAPI `Depends(...)` never runs (recurring-failures #1).

**Scorecard** (counted by script over §1–§10 on 2026-09-27; each row counted once, by its Status cell): **62 requirement rows**: 4 enforced · 18 tested · 4 implemented · 16 partial · 13 gap · 3 contradicted · 2 owner-gated · 2 unknown. Recounted after the contracts review moved LOCAL-04 and GATE-08 to partial. Plus 8 deferred owner-gated items in §11. Only 4 of 62 rows are `enforced` (an automated gate fails on violation). That, more than any single gap, is the matrix's main finding.

---

## 1. Local-first and network boundary

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| LOCAL-01 | No network calls in product code paths | `CLAUDE.md:59`; PRD `:7` | Only `httpx` users are `core/llm/ollama_provider.py` and `core/external_runner.py`; no `requests`/`aiohttp`/`socket` | agent loop only: `tests/agent/test_s4_phi_gate.py::test_s4_2_offline_loop_completes` | none (no import ban) | **partial** (see LOCAL-03/04) | — |
| LOCAL-02 | Ollama is localhost-only | `CLAUDE.md:59`; `AGENT.md` Configuration | `_assert_localhost` at `core/llm/ollama_provider.py:34-54`, called at `:73` and `api/model_settings.py:799-808`; the factory pins `127.0.0.1:11434` (`core/llm/factory.py:51`) | `tests/test_llm_provider_layer.py::TestOllamaProvider::test_refuses_non_local_url`, `::test_accepts_localhost` (direct-call) | pytest only | **tested**. The comment at `core/config.py:109` claims startup rejection, but `validate_startup` has no such check | — |
| LOCAL-03 | Model fetches happen only through user-triggered downloads | `00-original-goal.md` ("only sanctioned network call is model download") | `SentenceTransformer(name)` at `modules/embeddings.py:56`, with no offline flag | none | none | **gap**: implicit HF fetch on first embedding use | Owner: accept or pin offline (C-LOCAL-2) |
| LOCAL-04 | The opt-in external LLM is off by default and redacted | `skills/asclexis-guardrails` (PHI gate before opt-in external call); `CLAUDE.md:60` | `use_external_api` default False (`models/model_settings.py:78-81`); strict redaction (`core/external_runner.py:166-236`) | `tests/test_redaction.py::TestExternalRunnerIntegration`; `tests/test_config_validation.py` | pytest only | **partial**: two bypasses. Outside production, `redaction_enabled=False` skips redaction (`core/external_runner.py:201`); in production, break-glass bypasses the block (`:172`). `CLAUDE.md:60` is unconditional | **owner-gated**: accept the bypasses, or remove them |
| LOCAL-05 | Local mode binds 127.0.0.1 with a localhost-only CORS list | `docs/compliance/data-privacy.md:53` | `dev.ps1:719` (`--host 127.0.0.1`); `src/backend/main.py:164-171` for `python main.py` only; CORS `main.py:101-103` | none found | none | **implemented** | — |

## 2. Profile isolation

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| ISO-01 | Profile data only via `ProfileDbSession`, never master `get_db()` | `CLAUDE.md:58` | `core/auth.py:313-339`; master session touches only master models (2026-09-27 scan) | HTTP: `tests/test_backup_routes.py` (HC-BKUP-033…042); others direct-call | pytest only | **tested** | — |
| ISO-02 | Cross-profile access is refused over HTTP | `CLAUDE.md` §4 ("Route tests go through HTTP") | `require_profile_access` (`core/auth.py:251-289`), used 5× in `api/profiles.py` | no HTTP test for the `api/profiles.py` guards | none | **gap** (test coverage) | — |
| ISO-03 | Profile id comes from the JWT, not the client | `CLAUDE.md:58` | `core/auth.py:191`; the frontend never sends it (`services/observations.ts:15`) | indirect | none | **implemented** | — |
| ISO-04 | Backups are profile-scoped; restore touches only this profile | `AGENT.md` flow 4 | `api/backup.py`, `scripts/backup.py` | `tests/test_backup_routes.py` (HTTP) | pytest only | **tested** | — |

## 3. Encryption and key lifecycle

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| KEY-01 | Each vault is SQLCipher-encrypted and fails closed | `CLAUDE.md:58`; `docs/compliance/data-privacy.md:7-15` | `core/profile_database.py:315-356`; `database_encryption_required=True` (`core/config.py:40`) | `tests/test_bootstrap_check.py` (source assert) | CI installs SQLCipher; `scripts/check_sqlcipher.py` is not run in CI | **partial** | — |
| KEY-02 | On-disk ciphertext is proven by tests | (implied by KEY-01) | — | the suite sets `DATABASE_ENCRYPTION_REQUIRED=false` (`tests/conftest.py:57`); only e2e runs encrypted | none | **gap** | — |
| KEY-03 | DEK is sealed, plus a password-sealed recovery copy (SEC-RECOV-001) | `AGENT.md` flow 5 | `core/security.py:184-186,323`; `api/profiles.py:546-589,648-763` | `tests/security/test_key_sealing_baseline.py`; `tests/test_profile_recovery.py` (direct-call) | pytest only | **tested** (backend). The signed-in issuance UI is only on branch A | — |
| KEY-04 | Delete is an ordered crypto-erase | `AGENT.md` flow 5; `data-privacy.md:141` | `api/profiles.py:781-923` | `tests/test_profile_deletion.py` HC-PDEL-001…018 (direct-call) | pytest only | **tested** | — |
| KEY-05 | DEK rotation | `docs/compliance/hipaa-controls.md:169` ("Manual via password change") | none; `change_password` re-seals the same DEK (plan 08 evidence) | — | — | **gap**. The doc overstates it: a password change is a re-seal, not a rotation | **owner-gated** (plan 08 brief 2) |
| KEY-06 | MFA / step-up re-auth | `hipaa-controls.md:168` ("Planned for server mode") | none | — | — | **owner-gated** | plan 08 brief 1 |
| KEY-07 | Documents are encrypted at rest | `00-original-goal.md` ("AES-GCM documents") | `core/security.py:443-466` (AESGCM); `modules/ingest.py:190` | ingest tests | pytest only | **tested** | — |

## 4. Human verification and medical safety

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| SAFE-01 | Extracted and imported data lands unverified | PRD `:24,50,69` | `api/documents.py:655,757`; verify handlers `:1249-1278`, `api/observations.py:458-488` | document/observation tests | pytest only | **tested** | — |
| SAFE-02 | Downstream consumers use verified data | `docs/architecture/pipelines.md:53-56`; PRD `:50` | Verified-only: agent tools, FHIR, visit-prep, pinboards, medications. **Not** verified-only: trends (`api/observations.py:529-535`), legacy RAG (`modules/rag.py:322-328`), CSV/JSON/doctor summary (`api/export.py:130-150`) | agent golden `abstain-unverified-*`; `test_hc_fhir_031` | `agent-evals` (agent path only) | **partial** | **owner-gated**: which surfaces may show unverified rows, and how they are labelled |
| SAFE-03 | Every answer sentence is grounded and cited (agent path) | `CLAUDE.md:62` | `modules/agent/guardrails/groundedness.py`, `guard.py`; draft is deterministic (`nodes/draft.py`) | 74 golden cases; `tests/agent/test_s3_guardrails.py`, `test_s6_evals.py` | **CI `agent-evals`**: groundedness / citation / abstention / injection == 1.0, advice / PHI leakage == 0 | **enforced** | — |
| SAFE-04 | Legacy RAG path is validated and gated | `CLAUDE.md:62`; `AGENT.md` flow 2 | `validate_response` (`modules/rag.py:793`), `[cite:N]` (`:819`), faithfulness < 0.6 sets `is_valid=False` (`:861-870`) **but the answer is still served** (`api/assistant.py:772-811`); `verify_all_claims` (`:1002`). Runs whenever the agent raises (`api/assistant.py:743-755`) | `tests/test_biomarker_assistant.py` and others | **no CI eval gate** for this path | **partial**: low-faithfulness answers reach the patient, flagged only in the payload | — (program G-B5; raised priority) |
| SAFE-05 | No diagnosis or dosing (prohibited patterns) | `CLAUDE.md:62`; ask-first `CLAUDE.md:8` | `modules/interpret_safety.py:49`, reused at `modules/rag.py:176` | `tests/test_interpret_safety_adversarial.py`, `tests/test_phase4_ai_safety.py` | pytest + `agent-evals` `advice_leakage == 0` | **enforced** | changes to the file are owner-gated |
| SAFE-06 | Patient-facing trust scores are computed, not constant | `CLAUDE.md:62` ("grounded") | main: hard-coded `faithfulness_score=1.0` (`api/assistant.py:608-617`) | none | none | **contradicted** on main; fix `cc202d9` on branch B | merge approved (§21 Q3, agent-recorded) |
| SAFE-07 | Safety and eval thresholds are never lowered to pass | `CLAUDE.md:24` | eval bars in `scripts/agent_eval_gate.py`; 0.6 in `rag.py:862`; 0.7 in `tests/test_rag_pipeline.py:270` (environment-dependent, not safety) | — | review only | **implemented** (convention) | — |
| SAFE-08 | One citation-marker vocabulary | `CLAUDE.md:62` (`[REFERENCE:N]`/`[YOUR_RESULTS:N]`) | the legacy validator uses `[cite:N]`; the prompt instructs both (`modules/rag.py:120-132`) | — | none | **partial** (doc/code mismatch) | owner: prompt is adjacent to ask-first files |
| SAFE-09 | The no-LLM fallback stays functional | `AGENT.md` flow 2 | `api/assistant.py:847,1224` | fallback tests (legacy path) | pytest only | **tested** | — |

## 5. Redaction and export

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| PRIV-01 | RL export is strict-redacted, no knob, explicit confirmation | `CLAUDE.md:60`; `AGENT.md` flow 3 | `api/feedback.py:306,384`; `modules/rl_dataset.py:105-215` | `tests/test_rl_feedback.py` | pytest only | **tested** | — |
| PRIV-02 | FHIR export is redacted | `CLAUDE.md:60` | `modules/fhir_export.py:50-65` | `tests/test_fhir_export.py` (HC-FHIR-080…082) | pytest only | **tested** | — |
| PRIV-03 | Visit-prep and pinboard exports are redacted | `CLAUDE.md:60` | `modules/export.py:533,637-642`; `api/pinboards.py:382` | `tests/test_visit_prep_packet.py` (HC-PKT-008, -016) | pytest only | **tested** | — |
| PRIV-04 | Every non-backup export is redacted | `data-privacy.md:173-174`; `CLAUDE.md:60` | **CSV, JSON and doctor summary** (text/html/pdf) do not call redaction (`modules/export.py:82,223,267,290,358`) | none | none | **contradicted** | **owner-gated**: are patient-directed exports "leaving"? Until decided, `data-privacy.md:173-174` is false |
| PRIV-05 | Backups are deliberately unredacted | `data-privacy.md:173-178` | `api/backup.py:10-15` | backup tests | pytest only | **tested** (documented exception) | — |
| PRIV-06 | No PHI in logs or audit rows | `hipaa-controls.md:47-53` | UUID-only audit helpers (`core/audit.py`) | `tests/test_audit_phi_minimization.py` (HC-AUD-001…010b) | pytest only | **partial**: plan 02 reports `medication_name` at INFO in `modules/notification_scheduler.py` (≈:517-520, REPORTED). The module is currently unwired | — |
| PRIV-07 | Derived verbatim text is cleared when its source document is deleted | backlog plan §14 d1 (branch A) | fix `45ac889` on branch A only | HC-CAREQ-001…003 (branch A) | — | **gap** on main; fix unmerged | owner-approved (branch record) |
| PRIV-08 | Export artifacts survive a restart | audit §11 P1-3 | module-level dicts in `api/export.py` (REPORTED) | — | — | **unknown** (not re-checked) | — |

## 6. Inference boundary

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| LLM-01 | Live local inference goes through `ModelRunner` (the opt-in cloud `ExternalModelRunner`, `core/external_runner.py:95`, does not; owner-gated deviation) | `CLAUDE.md:25` | `modules/rag.py:1267-1291` → `core/model_runner.py:85-90` → `core/llm/factory.py` | provider-layer tests | pytest only | **tested** | — |
| LLM-02 | No `llama_cpp` import in feature code | `CLAUDE.md:25` | **dormant violation** at `modules/model_selector.py:438`, reachable only via `interpret_with_model` (`modules/interpret.py:877`, 0 callers) | none | none | **partial** | owner: delete, or route through ModelRunner |
| LLM-03 | The boundary is checked automatically | (proposed, C-LLM-2) | none; `pyproject.toml` ruff selects F, I, W and ruff is not run in CI | — | none | **gap** | — |

## 7. Audit data

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| AUD-01 | Document and observation routes are audited | `CLAUDE.md:61` | documents 13/13, observations 6/6 routes call `core/audit.py` helpers (text scan) | `tests/test_observations_audit.py` (HTTP) | pytest only | **tested** | — |
| AUD-02 | Profile routes are audited | `CLAUDE.md:61` | 9/13. Missing: `GET /` (`api/profiles.py:241`), `GET /me` (`:416`), `POST /test/reset` (`:477`), `GET /{profile_id}` (`:943`) | — | none | **partial** | — |
| AUD-03 | Audit retention policy | audit §21 Q6; plan 08 brief 4 | none (retention is unbounded) | — | — | **owner-gated** (HIPAA status conditional; legal review) | yes |
| AUD-04 | Audit data is protected at rest | `hipaa-controls.md:47-53` | master DB is **unencrypted** (`core/config.py:180-184`); audit helpers also log each row at INFO (`core/audit.py:254-261`); plan 08's "`logs/asclexis.log`" file sink is **UNVERIFIED** because no product code configures a file handler | — | — | **partial** (rows are minimized; the stores are plaintext) | part of plan 08 brief 4 |

## 8. Timestamps, Python target, migrations, schema integrity

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| TIME-01 | Timestamps come only from `core.time.utcnow` (naive UTC) | `CLAUDE.md:57` | helper at `core/time.py:9-11`; **101 product lines / 109 references / 30 files** still call `datetime.utcnow` | `test_hc_recov_025` (one module) | none | **gap** (systemic) | — (plan 05) |
| TIME-02 | Python 3.11+ target; no 3.12-only syntax | `CLAUDE.md:57` | ruff/black `target-version = "py311"`; no `requires-python` | best-effort AST parse (2026-09-27 agent scan: 0 failures) | CI pins 3.11 in every Python job | **tested** (by CI interpreter) | — |
| MIG-01 | Dual Alembic chains, linear | `CLAUDE.md:63` | master 2 revisions (head `002_backup_schedules`); profile 12 (head `012_pinboards`) | parent checks only (`test_pinboards.py`, `test_rl_feedback.py`) | none | **implemented** (currently linear) | — |
| MIG-02 | One head per chain is asserted | (proposed, C-MIG-2) | — | — | — | **gap** | — |
| MIG-03 | Declared FK actions are enforced | `TASK_LIST.md` SQL-FK-001; `recurring-failures.md:144` | `PRAGMA foreign_keys` set nowhere (comment `api/profiles.py:914`) | — | — | **gap** | owner-approved sequence and blast radius (branch record `fe31e78`); delete semantics need explicit approval at P6 (D5) |
| MIG-04 | Test reset wipes every profile table | `api/profiles.py:477-531` docstring | deletes 16 models; omits ChatSession, ChatTurn, CarePlanTask, Pinboard, PinboardItem, ResponseFeedback and the FTS `search_records*` tables; production 404; name-prefix 403 | none (only caller: `src/frontend/e2e/support/auth.ts:51`) | none | **partial** | — (plan 07) |

## 9. Product claims

| ID | Requirement | Source | Implementation | Tests | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|---|
| PROD-01 | Import → extract → verify → trends | PRD `:49,69` | §5 of the overview | pytest + e2e `document-workflow.spec.ts` | CI backend + e2e | **tested** | — |
| PROD-02 | Medication reminders fire | features index | engine built; `start_notification_scheduler` has no caller | unit tests only | — | **gap** (not wired) | owner answer "wire it up" (§21 Q1, agent-recorded) |
| PROD-03 | Desktop app | `docs/features/` HC-M08 | none | — | — | **gap** | owner: "Both" (§21 Q4); spike first |
| PROD-04 | Recovery-code issuance UI for existing profiles | SEC-RECOV-001 | branch A `692fdf3` only | branch A e2e `recovery-code.spec.ts` | — | **partial** (backend yes, UI unmerged) | merge approved (§21 Q3, agent-recorded) |
| PROD-05 | Medication correlations served by the endpoint | MED-CORR-001 | branch A `692fdf3` only | branch A vitest | — | **partial** | merge approved (§21 Q3, agent-recorded) |

## 10. Engineering gates and harness

| ID | Requirement | Source | Implementation | Gate | Status | Owner gate |
|---|---|---|---|---|---|---|
| GATE-01 | Docs lint and index freshness | `AGENT.md`; `scripts/docs_lint.py` | 13 numbered rules, 14 check functions | CI `docs-lint` | **enforced**. Locally on 2026-09-27: `docs_lint.py` passed; `generate_docs_index.py --check` → stale (owner's uncommitted `docs/INDEX.md` + untracked package) | — |
| GATE-02 | Backend suite; measured baseline | `CLAUDE.md` §4; `AGENT.md` DoD | `scripts/run-backend-tests.sh` | CI `backend-tests` | **tested**: 1245 collected at `40f590e` (2026-09-27); pass count not run this pass | — |
| GATE-03 | Frontend type-check and unit tests | `AGENT.md` DoD | `tsc --noEmit`, `vitest run` | CI `frontend-tests` | **partial**: no `npm run build`, no eslint in CI; the 155-test figure is unverified | — |
| GATE-04 | Security scan fails closed | `recurring-failures.md` #1 | main: `scripts/security_gate.py:49-51,76-78` return `[]` on missing or malformed reports; scanners run `|| true` (`ci.yml:92,95`) | CI `security-scan` | **gap** (fails open); fix `934a842` on branch B | merge approved (§21 Q3, agent-recorded) |
| GATE-05 | Agent behavioural eval gate | `skills/asclexis-evals` | `scripts/agent_eval_gate.py`, 74 cases | CI `agent-evals` | **tested** (agent path only; see SAFE-04) | — |
| GATE-06 | E2E critical flows | `AGENT.md` | Playwright chromium; needs `HC_E2E_CHROMIUM_PATH` locally (`recurring-failures.md` #4) | CI `e2e-tests` | **partial**: 25-test figure unverified; not run this pass | — |
| GATE-07 | Lint, type and coverage gates | audit §13 | ruff/black/mypy/eslint configured, not run in CI; no coverage threshold | none | **gap** | — |
| GATE-08 | Staging uses explicit pathspecs | `recurring-failures.md` #5 | plan 04 `git add -A` and plan 02 `git add docs/` corrected 2026-09-27. Directory adds remain in plans 03 and 05, behind a required status check | review | **partial** | — |
| GATE-09 | Agent/hook harness claims match committed artifacts | `docs/agentic/harness.md:25-28` | `.claude/agents/` absent; `.gitignore:44` blocks it; no repo hooks | none on main (`harness_drift_check.py` on branch B, not CI-wired) | **contradicted** | **owner-gated** (plan 03, §21 Q2 "Not sure") |
| GATE-10 | Feature ledger is linted | `feature_list.json` | `scripts/feature_list_lint.py` | CI `docs-lint` | **enforced** | — |
| GATE-11 | Merge-required checks | — | branch protection is not in the repo | — | **unknown** | — |

## 11. Deferred, owner-gated items (prepare only)

| ID | Item | Recorded owner position | Evidence status | Packet |
|---|---|---|---|---|
| GATED-01 | MFA / step-up re-auth | "Still want them — keep gated" (§21 Q6, agent-recorded) | not implemented | plan 08 brief 1 |
| GATED-02 | DEK rotation | same | not implemented; doc overstates (KEY-05) | plan 08 brief 2 |
| GATED-03 | Penetration-test scope | same; `hipaa-controls.md:171` "Scheduled for post-launch" | not scheduled | plan 08 brief 3 |
| GATED-04 | Audit retention | same | unbounded (AUD-03); HIPAA status conditional (legal) | plan 08 brief 4 |
| GATED-05 | HC-M11 NLI faithfulness | **approved for build behind a default-off flag** (branch A §14 d2, `fe31e78`); production behaviour change not approved | `consistency_score` placeholder 1.0 (audit REPORTED) | plan 08 brief 5 (must cite the branch record) |
| GATED-06 | `.claude/agents/` + hooks (A vs B) | "Not sure" (§21 Q2) | absent at every level | plan 03 |
| GATED-07 | Serena memories: delete, regenerate, or freshness gate | none | 7 files frozen since 2026-01-07 (plan 04 evidence) | plan 04 Task 12 |
| GATED-08 | Export-redaction and verified-only scope | none | PRIV-04, SAFE-02 | new: program P0-D |

## Unrun checks and blockers

| Check | Blocker |
|---|---|
| Backend **pass** counts | Not run this pass (planning only). Collection was measured with Windows Python 3.13.7 (`/mnt/c/Python313/python.exe`); CI is 3.11. |
| Vitest / Playwright counts | Not run. `vitest run` stalls under WSL on `/mnt/c` (project memory note); Playwright needs `HC_E2E_CHROMIUM_PATH`. |
| HHS HIPAA pages | HTTP 403 to this session's fetcher on 2026-09-27. |
| Branch-protection settings | Not in the repo; `gh` API not queried. |

Back to index: [README.md](README.md)
