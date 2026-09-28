# Asclexis — Architecture & Engineering Contract

**Last Updated:** 2026-09-28
**Authority:** [`CLAUDE.md`](../../CLAUDE.md) and [`AGENT.md`](../../AGENT.md) override this file. It restates their invariants as testable contracts. A rule is `BINDING` only when CLAUDE.md or AGENT.md states it. Rules drawn from other repo documents (compliance docs, API README) or inferred by this pass are `PROPOSED`, with the source cited. *(Corrected 2026-09-27 after the contracts review: an earlier draft labelled six such rules BINDING and narrowed two CLAUDE.md invariants; see the follow-up §Validation.)*

This contract turns the repo's invariants into rules a reviewer can check. Current compliance for each rule is tracked in [specs-compliance-matrix.md](specs-compliance-matrix.md). The system being governed is described in [architecture-overview.md](architecture-overview.md).

## How to read a contract

| Field | Meaning |
|---|---|
| **Class** | `BINDING`: an existing repo invariant, where a violation is a broken build or broken trust. `PROPOSED`: an engineering decision recommended by this pass, not yet adopted. `OWNER-GATED`: needs a product/owner decision that is not on record, or is on record only for part of the scope. A partial approval is cited inline, with its source. |
| **Rule** | MUST / MUST NOT, worded so that a command or test can falsify it. |
| **Enforced at** | The code, test, or CI job that would catch a violation *today*. "none" means convention only. |
| **Verify** | The command or evidence a reviewer runs. Grep commands run from the repo root. Pytest runs from `src/backend` using an interpreter that has the backend dependencies (see C-GATE-1). |
| **On violation** | What the engineer does. For every BINDING contract the rule is the same: **stop and ask; never weaken the guard to proceed** (CLAUDE.md §3). |
| **Owner** | Who decides when the rule itself is in question. |
| **Planned by** | The 2026-09-27 plan(s) that would change the status (IDs as in the matrix legend). A plan changes nothing until it merges. |

"Status today" is a summary. The matrix row it cites holds the evidence.

---

## 1. Privacy and local-first

**C-LOCAL-1 · BINDING.**
- **Rule:** Product code MUST NOT make network calls (`CLAUDE.md:59`). Ollama MUST stay localhost-only.
- **Known exceptions, not approved by this contract:**
  - user-triggered model downloads, the product's stated "only sanctioned network call";
  - the opt-in external runner (documented in `skills/asclexis-guardrails`; owner-gated, see C-LLM-1 and C-REDACT-2);
  - the implicit embedding download (C-LOCAL-2).

  A new outbound destination needs owner approval.
- **Enforced at:**
  - `core/llm/ollama_provider.py:34-54` (`_assert_localhost`, called at `:73`) and `api/model_settings.py:799-808`.
  - `tests/agent/test_s4_phi_gate.py::test_s4_2_offline_loop_completes` blocks AF_INET for the agent loop only.
  - No lint bans network imports.
- **Verify:**
  - `grep -rnE "import (requests|httpx|aiohttp|socket|urllib\.request|huggingface_hub|sentence_transformers)|from (requests|httpx|aiohttp|huggingface_hub|sentence_transformers)" src/backend --include=*.py | grep -v /tests/`. Every hit must be in `core/llm/ollama_provider.py`, `core/external_runner.py`, the model-download code (`api/model_settings.py`, `modules/model_selector.py`, `scripts/model_manager.py`), `modules/embeddings.py`, or the import-availability probe in `modules/environment_diagnostics.py:268`. That is 7 files at main on 2026-09-27, 8 after P1 (B's `src/backend/scripts/download_models.py` adds `huggingface_hub`, `:53`).
  - `pytest tests/test_llm_provider_layer.py -k "local"` covers the Ollama allow-list only (2 tests).
- **Status today:** partial. `modules/embeddings.py:56` fetches from Hugging Face implicitly. Observed 2026-09-27 17:05 PDT during a local full-suite run (11 files, 91,578,415 B), and relied on by CI (`ci.yml:30-48` has no model step) (matrix LOCAL-03, LOCAL-06).
- **On violation:** stop; remove the call or route it through an approved path.
- **Owner:** Project owner.
- **Planned by:** W-8, W-6.

**C-LOCAL-2 · PROPOSED** (owner-approved D8 + D8-delivery, `owner-decisions-2026-09-27.md:21,26`; not yet in CLAUDE.md).
- **Rule:** The embedding model MUST load from a local path or cache and MUST NOT download implicitly at query time. Downloads happen only through the user-triggered model manager. Interim delivery (D8-delivery): the model is fetched once by `src/backend/scripts/download_models.py` into a local models dir; runtime loads that path with HF offline and fails closed if it is absent.
- **Enforced at:** none.
- **Verify:** a test that sets `HF_HUB_OFFLINE=1` and asserts `EmbeddingModule` fails closed or loads from the local path (planned: W-8 HC-EMB-001/002, with sockets blocked and an empty `HF_HOME`).
- **On violation:** —.
- **Owner:** Owner decides whether implicit first-use download is acceptable.
- **Planned by:** W-8.

**C-LOCAL-3 · PROPOSED** (source: `docs/compliance/data-privacy.md:53`).
- **Rule:** In `local` mode the backend MUST bind `127.0.0.1`, and CORS MUST list only the localhost frontend origins.
- **Enforced at:** the launcher (`dev.ps1:719` passes `--host 127.0.0.1`); `src/backend/main.py:164-171` applies only to `python main.py`; CORS at `main.py:101-103`. No test found.
- **Verify:** `grep -n "127.0.0.1" src/backend/main.py dev.ps1`.
- **On violation:** stop.
- **Owner:** Project owner.

## 2. Profile isolation

**C-ISO-1 · BINDING.**
- **Rule:** Profile-scoped rows MUST be read and written only through `ProfileDbSession` (`core/auth.py:339`). The master `get_db()` MUST NOT touch profile tables. The profile id MUST come from the JWT `sub` (`core/auth.py:191`), never from a request parameter, for data access.
- **Enforced at:** code structure. HTTP-level tests exist for backup routes (`tests/test_backup_routes.py`); most other route tests call handlers directly.
- **Verify:** every `db`/`get_db` use in `src/backend/api/` touches only `Profile`, `AuditLog`, `BackupSchedule` or the knowledge-base models; route tests for new code use `tests/support/routes.py::route_client`.
- **Status today:** tested (mostly direct-call). HTTP coverage of `require_profile_access` on `api/profiles.py` routes is missing (matrix ISO-02).
- **On violation:** stop; fix the query, never the test.
- **Owner:** Project owner.

**C-ISO-2 · BINDING.**
- **Rule:** Any test asserting auth, path scoping, or status codes MUST go through HTTP (`route_client`), not a direct handler call.
- **Enforced at:** review only.
- **Verify:** `grep -ln "route_client" src/backend/tests` must include each new route test.
- **Status today:** review only. Known direct-call status assertions: `test_profile_deletion.py` HC-PDEL-001…018; HC-PKT-014/015 (`tests/test_visit_prep_packet.py:403-432`); HC-FHIR-103/104 (W-11b F-6). `api/profiles.py` guards have no HTTP test (matrix ISO-02).
- **On violation:** rewrite the test through HTTP and break the code on purpose to see it go red (recurring-failures #1).
- **Owner:** Engineering.
- **Planned by:** W-11a (profiles); W-11b keeps F-6 as direct-call (documented).

## 3. Encryption and key lifecycle

**C-KEY-1 · BINDING (ask-first).**
- **Rule:** Each profile vault MUST be SQLCipher-encrypted with a per-profile DEK. The DEK MUST be stored only sealed (DPAPI or password), plus one password-sealed recovery copy. Plaintext DEK material MUST NOT be written to disk or logs.
- **Enforced at:**
  - `core/profile_database.py:315-356` sets `PRAGMA key` and fails closed on the cipher check.
  - `core/security.py:323` (sealing) and `api/profiles.py:546-589` (recovery copy).
  - `database_encryption_required=True` default (`core/config.py:40`).
- **Verify:** `pytest tests/security/test_key_sealing_baseline.py tests/test_profile_recovery.py`.
- **Status today:** partial: tested, but the backend suite sets `DATABASE_ENCRYPTION_REQUIRED=false` (`tests/conftest.py:57`), so no pytest proves on-disk ciphertext (matrix KEY-02). **Native Windows dev vaults are unencrypted:** `sqlcipher3-binary` has no cp313 `win_amd64` wheel (`pip download … --only-binary=:all:` → "No matching distribution"), so `dev.ps1:471-500` installs without it and `:586-593` flips `DATABASE_ENCRYPTION_REQUIRED=false`; `dev.ps1:578` writes `=false` in the fallback `.env` even when SQLCipher is present (matrix KEY-08).
- **On violation:** stop; CLAUDE.md requires asking before any auth or encryption change.
- **Owner:** Project owner.
- **Planned by:** W-11a (KEY-02 test); the Windows posture is unowned → owner item (G-C4 packaging must ship SQLCipher).

**C-KEY-2 · BINDING (ask-first).**
- **Rule:** Profile deletion MUST crypto-erase in this order:
  1. re-auth + confirmation phrase;
  2. close the vault;
  3. unlink every sealed key (the commit point);
  4. sweep the vault;
  5. sweep the managed backups;
  6. in one master transaction, purge audit rows and write an anonymized tombstone.

  It MUST NOT rely on FK cascades.
- **Enforced at:** `api/profiles.py:781-923`; `tests/test_profile_deletion.py` HC-PDEL-001…018 (direct-call).
- **Verify:** `pytest tests/test_profile_deletion.py`; re-walk the whole create → backup → delete flow (recurring-failures #2).
- **On violation:** stop.
- **Owner:** Project owner.

**C-KEY-3 · OWNER-GATED.**
- **Rule:** DEK rotation (a password change today re-seals the same DEK) and MFA / step-up re-auth.
- **Enforced at:** —.
- **Verify:** —.
- **On violation:** —.
- **Owner:** Owner (plan 08 briefs 1–2).

## 4. Human verification

**C-VERIFY-1 · BINDING.**
- **Rule:** Extraction and structured import MUST create observations with `user_verified=False`. Only an explicit user verify action may set it `True`.
- **Enforced at:** `api/documents.py:655,757,1249-1278`; `api/observations.py:458-488`.
- **Verify:** `grep -rnE "user_verified\s*=\s*True" src/backend/api src/backend/modules` → exactly `api/documents.py:1274` and `api/observations.py:458` (checked 2026-09-27).
- **On violation:** stop.
- **Owner:** Project owner.

**C-VERIFY-2 · PROPOSED** (owner decision D4, 2026-09-27; becomes a repo rule when W-10 amends `data-privacy.md`).
- **Rule:** Which consumers MUST read verified rows only.
  - Today: the agent tools, FHIR, visit-prep, pinboards and medications do.
  - Today: the trends endpoint, legacy RAG and CSV/JSON/doctor summary do not.
  - `docs/architecture/pipelines.md:53-56` claims all do.
  - D4: legacy RAG MUST cite verified observations only; trends MAY show unverified points only when visibly labelled. Exports carrying unverified rows (CSV/JSON/doctor summary, `api/export.py:130-150`) are **not decided** (owner item, D4-EXPORTS).
- **Enforced at:** agent path: `agent-evals` golden `abstain-unverified-*`. Others: none.
- **Verify:** `grep -n "user_verified" src/backend/api/observations.py src/backend/modules/rag.py src/backend/api/export.py`.
- **On violation:** —.
- **Owner:** Owner decides; then the losing side (code or doc) is corrected.
- **Planned by:** W-3, W-10, P04 N1.

## 5. Assistant citations and medical safety

**C-SAFE-1 · BINDING (ask-first files).**
- **Rule:** Outputs MUST be educational. They MUST NOT diagnose or give dosing/treatment advice. `interpret_safety` prohibited patterns MUST keep passing. `interpret_safety.py`, `faithfulness.py`, `verifier_agent.py` and `redaction.py` MUST NOT change without owner approval.
- **Enforced at:**
  - `modules/interpret_safety.py:49`.
  - `tests/test_interpret_safety_adversarial.py`, `tests/test_phase4_ai_safety.py`.
  - CI `agent-evals` (`advice_leakage == 0`).
- **Verify:** `pytest tests/test_interpret_safety_adversarial.py tests/test_phase4_ai_safety.py tests/agent/test_s3_guardrails.py`; `<interp> scripts/agent_eval_gate.py` (interpreter with backend deps; see C-GATE-1). It prints `Agent eval gate: PASS` but did not exit within 420 s on Win Py 3.13.7 (2026-09-27, `rc=124`; matrix GATE-14, unfixed and unowned; Linux/3.11 UNMEASURED). Until GATE-14 is fixed, read the PASS line and the bars, not the exit code.
- **On violation:** stop.
- **Owner:** Project owner.

**C-SAFE-2 · BINDING.**
- **Rule:** Every factual answer sentence MUST map to a citable source (the user's verified data or the reference KB). Memory and session history MUST NOT be citable. When grounding fails, the system MUST abstain or escalate rather than answer.
- **Enforced at:**
  - Agent path: `guardrails/groundedness.py`, `guardrails/guard.py`; CI bars groundedness / citation / abstention == 1.0 over 74 cases.
  - Legacy path: `validate_response` (`modules/rag.py:793-872`, `[cite:N]` at `:819`) sets `is_valid=False` (`:869`) on any of 5 triggers (`:826`, `:833`, `:838`, `:858`, `:863`); faithfulness < 0.6 (`:862`) is one of them. **None blocks:** `api/assistant.py:772-811` still serves the segments. Only `pages/LabInterpreter.tsx` reads `is_valid`. There is no CI eval gate, and this path runs whenever the agent raises (`api/assistant.py:743-755`).
- **Verify:** `<interp> scripts/agent_eval_gate.py` (interpreter with backend deps; see C-GATE-1). It prints `Agent eval gate: PASS` but did not exit within 420 s on Win Py 3.13.7 (2026-09-27, `rc=124`; matrix GATE-14, unfixed and unowned; Linux/3.11 UNMEASURED). Until GATE-14 is fixed, read the PASS line and the bars, not the exit code.
- **Status today:** partial. The agent path is enforced (SAFE-03). The legacy path serves low-faithfulness answers to the patient with no abstention (SAFE-04, raised in priority).
- **On violation:** stop.
- **Owner:** Project owner.
- **Planned by:** W-4 (G-B5 decided).

**C-SAFE-3 · PROPOSED** (derived from `CLAUDE.md:62` "grounded"; not stated there).
- **Rule:** Trust indicators shown to the patient (faithfulness/verification scores) MUST be computed, never constants.
- **Enforced at:** none on main (`api/assistant.py:608-617` hard-codes 1.0). Fix on branch B `cc202d9`.
- **Verify:** after the merge, `grep -n "faithfulness_score=1.0" src/backend/api/assistant.py` should return nothing.
- **On violation:** treat as a trust defect; merge the fix (program P1).
- **Owner:** Engineering; already approved to merge (§21 Q3).

**C-SAFE-4 · BINDING.**
- **Rule:** Safety and eval thresholds MUST NOT be lowered to make a test pass. This covers the eval-gate bars, the 0.6 faithfulness threshold, and the 0.7 embedding-similarity assertion in `test_api_rag_index_002b` (an environment-dependent test, not a safety test).
- **Enforced at:** review.
- **Verify:** `git diff` shows no threshold change without an owner-approval reference.
- **On violation:** revert.
- **Owner:** Project owner.

**C-SAFE-5 · PROPOSED** (decided D11: docs match code).
- **Rule:** One citation-marker vocabulary across docs, prompt and validator.
  - Today `CLAUDE.md` and the docs name `[YOUR_RESULTS:N]`/`[REFERENCE:N]`.
  - The legacy validator accepts `[cite:N]`.
  - The legacy prompt instructs both (`modules/rag.py:123-140`; contradictory lines `:128`, `:133`, `:134`).
- **Enforced at:** none.
- **Verify:** —.
- **On violation:** —.
- **Owner:** Owner. The prompt lives beside ask-first modules, so ask first. D11 decided; `CLAUDE.md:62` changes only if W-10 Q1 (GOV-D11) is signed.
- **Planned by:** W-5, W-10, P04 N8.

## 6. Redaction before anything leaves

**C-REDACT-1 · BINDING (ask-first).**
- **Rule:** Any path that writes user text to exportable files or external runners MUST pass through `modules/redaction.py` first (`CLAUDE.md:60`, verbatim scope). RL export MUST force `policy_level="strict"` with no configuration knob. Backups are the single documented exception.
- **Enforced at:** `modules/rl_dataset.py:105-215`, `modules/fhir_export.py:50-65`, `modules/export.py:533,637-642`. Tests: `tests/test_rl_feedback.py`, `tests/test_fhir_export.py`, `tests/test_visit_prep_packet.py`.
- **Verify:** `grep -n "RedactionEngine" src/backend/modules/export.py src/backend/modules/fhir_export.py src/backend/modules/rl_dataset.py`.
- **Status today:** **contradicted** for the doctor summary (`api/export.py:379,482`; text built inline `:551-604`; `modules/export.py:82,290,358`) and `/export/questions` (`api/export.py:607`). CSV/JSON (`modules/export.py:223,267`) become owner-approved named exceptions (D3) once W-10 amends `CLAUDE.md:60` and `data-privacy.md:173-174`; until then `data-privacy.md:173-174` (every non-backup export is redacted) is false (matrix PRIV-04).
- **On violation:** stop. D3 is decided (2026-09-27): redact the doctor summary; CSV/JSON are named exceptions once W-10 lands. Until then, CSV/JSON/doctor summary violate `CLAUDE.md:60` as written.
- **Owner:** Project owner.
- **Planned by:** W-2, W-10.

**C-REDACT-2 · BINDING.**
- **Rule:** The external runner MUST apply strict redaction before any network call, unconditionally (`CLAUDE.md:60`).
- **Known exceptions in code (OWNER-GATED, not approved here):**
  - outside production, `redaction_enabled=False` skips redaction (`core/external_runner.py:201`);
  - in production, break-glass bypasses the block (`:172`).
- **Enforced at:** `core/external_runner.py:166-236`; `tests/test_redaction.py::TestExternalRunnerIntegration`; `tests/test_config_validation.py`.
- **Verify:** `pytest tests/test_redaction.py -k ExternalRunner`.
- **Status today:** partial. Default `redaction_enabled=True` (`core/config.py:135`), but the bypasses at `core/external_runner.py:201` (dev) and `:172` (production break-glass) exist, main = B. The payload is the whole composed prompt (`modules/rag.py:1256-1268`), not only the question (`data-privacy.md:196-197` @main is false; matrix LOCAL-04, LOCAL-07).
- **On violation:** stop.
- **Owner:** Project owner. D12 decided: unconditional strict; break-glass only with audit + UI warning.
- **Planned by:** W-6, W-10.

**C-REDACT-3 · PROPOSED** (source: `docs/compliance/hipaa-controls.md:53`).
- **Rule:** Logs and audit rows MUST NOT contain PHI (medication names, values, document text); use UUIDs.
- **Enforced at:** `tests/test_audit_phi_minimization.py` (HC-AUD-001…010b); none for SQLAlchemy loggers (HC-AUD-007 caplogs `core.audit` only).
- **Verify:** `pytest tests/test_audit_phi_minimization.py`.
- **Status today:** **violated in the default dev config.** Both engines set `echo=settings.debug` (`core/database.py:46`, `core/profile_database.py:308`) with `debug=True` (`core/config.py:28`) and no `hide_parameters`, so bound PHI goes to stderr (S-01 probe; matrix PRIV-06, PRIV-09). `medication_name` at INFO (`modules/notification_scheduler.py:517-520`, VERIFIED) and `display_name` at INFO (`api/profiles.py:328`) are masked only by root WARN.
- **On violation:** stop.
- **Owner:** Project owner.
- **Planned by:** S-1 (SQL-ECHO), audit plan 02.

## 7. Inference boundary

**C-LLM-1 · BINDING.**
- **Rule:** All LLM calls MUST go through the `ModelRunner` facade (`CLAUDE.md:25`). Feature code MUST NOT import `llama_cpp` or call Ollama directly. New providers are added inside `core/llm/`, never as a layer on top of it.
- **Enforced at:** none automated.
- **Verify:** `grep -rnE "import llama_cpp|from llama_cpp" src/backend --include=*.py | grep -v /tests/` should return only `core/llm/llama_cpp_provider.py:36`.
- **Status today:** two deviations.
  1. **Dormant:** `modules/model_selector.py:438` @main (`:456` after P1), reachable only via `interpret_with_model` (0 callers) (matrix LLM-02).
  2. **Live, opt-in:** `ExternalModelRunner` (`core/external_runner.py:95`, `httpx` at `:263,296`) is a standalone runner that `api/assistant.py` and `api/interpretations.py` pass into `rag.query`. It does not go through `ModelRunner`. It is an owner-approved exception (D12), pending W-10's CLAUDE.md amendment.
- **On violation:** stop; never extend the dormant path.
- **Owner:** Engineering.
- **Planned by:** W-7, W-6, W-10.

**C-LLM-2 · PROPOSED.**
- **Rule:** An automated boundary check (a pytest scanning imports, or a ruff banned-API rule run in CI) MUST fail on a new `llama_cpp`/`ollama`/HTTP-client import outside `core/llm/` (plus `core/external_runner.py` only if the owner accepts that deviation).
- **Enforced at:** none (after W-7: HC-LLMB in `backend-tests`, `llama_cpp` only; that is a suite test, so matrix LLM-02 → `tested`, not `enforced`).
- **Verify:** break it on purpose and watch CI go red.
- **On violation:** —.
- **Owner:** Engineering; owner decides what to do with the dormant path (delete vs route through ModelRunner).
- **Planned by:** W-7, W-11a (ruff).

**C-LLM-3 · BINDING.**
- **Rule:** The no-LLM fallback MUST keep answering (knowledge fallback) when no model is available.
- **Enforced at:** `api/assistant.py:847,1224`.
- **Verify:** a test that forces `ModelUnavailableError` on the legacy path.
- **Status today:** fallback covers the legacy path only; the agent path needs no model.
- **On violation:** stop.
- **Owner:** Project owner.

## 8. Timestamps

**C-TIME-1 · BINDING.**
- **Rule:** New and changed code MUST use `core.time.utcnow` (naive UTC: `datetime.now(UTC).replace(tzinfo=None)`, `core/time.py:9-11`). It MUST NOT introduce aware datetimes into naive SQLite `DateTime` columns. It MUST NOT use Python 3.12+-only syntax or APIs (target 3.11; CI pins 3.11).
- **Enforced at:** `tests/test_profile_recovery.py::test_hc_recov_025_recovery_uses_the_project_time_helper` (one module only).
- **Verify:** `grep -rn "datetime.utcnow" src/backend --include=*.py | grep -v /tests/ | wc -l` → 101 today; must not rise.
- **Status today:** 101 lines / 109 references in 30 product files (matrix TIME-01). Plus **12 aware-datetime lines in 8 files** (`git grep -nE '(dt_)?timezone\.utc' 40f590e -- 'src/backend/*.py' ':!src/backend/tests' ':!src/backend/core/time.py'`): 9 `datetime.now(…utc)` calls in 7 files (`core/auth.py:73,144`; `core/security.py:136`; `core/token_revocation.py:51`; `api/export.py:949,1005`; `api/model_settings.py:332`; alias `dt_timezone.utc` at `api/gamification.py:148`, `modules/badge_evaluator.py:84`) and 3 aware conversions (`core/auth.py:207`, `api/medications.py:84`, `modules/badge_evaluator.py:54`). One is persisted into a naive column: `modules/badge_evaluator.py:84` → `earned_at` (`:101`, `:157-163`) → `EarnedBadge.earned_at` `DateTime` (`models/gamification.py:64-68`), a C-TIME-1 violation (by reading, not by test; matrix TIME-03). `Session.is_expired` (`core/auth.py:73`) must keep comparing aware-to-aware: swapping in `core.time.utcnow` there would raise TypeError against `expires_at` (`core/auth.py:144,207`).
- **On violation:** replace with `core.time.utcnow`.
- **Owner:** Engineering. The aware sites in `core/auth.py` and `core/security.py` are auth code, so ask first.

**C-TIME-2 · PROPOSED.**
- **Rule:** A CI lint (plan 05 Task 5) MUST fail on any `datetime.utcnow` outside allow-listed test literals.
- **Enforced at:** —.
- **Verify:** —.
- **On violation:** —.
- **Owner:** Engineering.

## 9. Migrations and schema

**C-MIG-1 · BINDING.**
- **Rule:**
  - A new master table gets a revision in `migrations/master/`.
  - A new profile table gets a revision in `migrations/profile/`.
  - Each chain stays linear (a single `down_revision`, a single head).
  - Model and DDL must agree.
- **Enforced at:** convention; `test_pinboards.py` / `test_rl_feedback.py` check the parents of single revisions only.
- **Verify:** `for c in master profile; do grep -h "^down_revision" src/backend/migrations/$c/versions/*.py | sort | uniq -d; done` → empty (checked 2026-09-27); heads are master `002_backup_schedules`, profile `012_pinboards` (2026-09-27).
- **On violation:** stop.
- **Owner:** Engineering.

**C-MIG-2 · PROPOSED.**
- **Rule:** A test MUST assert exactly one head per chain.
- **Enforced at:** —.
- **Verify:** —.
- **On violation:** —.
- **Owner:** Engineering.

**C-MIG-3 · OWNER-GATED for delete semantics** (the pragma listener sits in `core/profile_database.py` beside the SQLCipher key hook, so ask first). The owner approved the blast radius on 2026-09-08 (agent-recorded, branch-only). Delete-effect approval is inferred, so it is required explicitly at program P6 (D5).
- **Rule:** `PRAGMA foreign_keys=ON` MUST be set once per new physical DBAPI connection on the master engine and the profile engine, after profile migration 013 realigns P14/P15 → CASCADE and P16/P17 → SET NULL. Migration engines and `scripts/backup.py` raw `sqlite3` connections MUST stay pragma-OFF. A constraint MUST NOT be relaxed to get a green suite.
- **Enforced at:** — (plan 06).
- **Verify:** plan 06 tests on ≥2 distinct connections per engine.
- **On violation:** stop.
- **Owner:** Owner record `docs/plans/2026-09-08-backlog-closure-plan.md` §14 decision 3 (branch A, `fe31e78`).

## 10. API and frontend integration

**C-API-1 · BINDING (barrel and `/api/v1` layout: AGENT.md "Stack & layout") + PROPOSED (the 401/403 rule, from `services/api.ts:65-71` only).**
- **Rule:**
  - All product routes mount under `/api/v1` (health at `/health`).
  - The frontend calls through `src/frontend/src/services/api.ts`, with the Bearer token from the Zustand store.
  - A 401 clears auth; a 403 does not.
  - Services export through `services/index.ts`.
- **Enforced at:** `src/backend/main.py:150-155`, `api/__init__.py:39-58`, `services/api.ts:13-70`; CI `tsc --noEmit` + `vitest run`.
- **Verify:** `cd src/frontend && npx tsc --noEmit && npx vitest run` (run on Windows; WSL stalls).
- **On violation:** fix.
- **Owner:** Engineering.

**C-API-2 · PROPOSED** (source: `docs/api/README.md:35`; `docs/00_architecture_plans_index.md` canonical order).
- **Rule:** `docs/api/endpoints.md` is the route source of truth and MUST list every mounted route.
- **Enforced at:** none automated.
- **Verify:** manual diff against the `include_router` list.
- **On violation:** docs fix.
- **Owner:** Engineering.

**C-API-3 · PROPOSED.**
- **Rule:** `npm run build` and eslint run in CI.
- **Enforced at:** — (audit §18).
- **Verify:** —.
- **On violation:** —.
- **Owner:** Engineering.

## 11. Background scheduling

**C-SCHED-1 · BINDING for the backup scheduler (AGENT.md flow 4); PROPOSED as the general rule for every lifespan job.**
- **Rule:** A lifespan job MUST be fail-soft at startup and stopped at shutdown. It MUST NOT open a locked vault. It MUST record `skipped_locked` honestly instead of reporting success.
- **Enforced at:** `src/backend/main.py:69-81`; `modules/backup_scheduler.py` (`skipped_locked`).
- **Verify:** backup scheduler tests; run the lifespan and inspect status.
- **On violation:** stop.
- **Owner:** Engineering.

**C-SCHED-2 · OWNER-GATED.** "Wire it up" is on record (§21 Q1, agent-recorded), but the scope and the `core/auth.py` hooks are not approved (D6).
- **Rule:** The notification scheduler MUST follow C-SCHED-1:
  - session-scoped registration at vault open/close;
  - no reminder content, medication names or schedules in the master DB or logs;
  - naive-UTC comparisons (C-TIME-1).
- **Enforced at:** — (plan 02).
- **Verify:** plan 02 HC-NSW tests.
- **On violation:** stop.
- **Owner:** Owner re-confirms scope (session-scoped only; quiet hours unenforced) at P2 sign-off.

## 12. Audit data

**C-AUDIT-1 · BINDING.**
- **Rule:** Every route that touches documents, observations or profile data MUST write an audit row via `core/audit.py` (`create_audit_log` `:198` and its wrappers), without PHI.
- **Enforced at:** `tests/test_observations_audit.py` (HTTP), `tests/test_audit_phi_minimization.py`.
- **Verify:** for each new route, a test asserts that the audit row exists.
- **Status today:** documents 13/13 and observations 6/6. Profiles 9/13: missing on `GET /` (`api/profiles.py:241`), `GET /me` (`:416`), `POST /test/reset` (`:477`), `GET /{profile_id}` (`:943`) (matrix AUD-02). **Interpretations 0/7** (`api/interpretations.py:323,383,508,565,615,640,673`; 6 read or write observation-derived data, W-7 F-3; matrix AUD-06).
- **On violation:** add the audit call.
- **Owner:** Engineering.
- **Planned by:** W-11a (profiles); interpretations are **unowned** → W-7 if AUD-INTERP (W-7 OG-3) is signed, else W-11a.

**C-AUDIT-2 · OWNER-GATED.** D10 frames it (HIPAA-aligned design posture, not legal status).
- **Rule:** An audit-retention window or cap for `audit_logs` (plus any log sink the owner configures). No product code configures a log sink, and INFO audit echoes are dropped after startup (root WARN via `alembic.ini:45-47`), so the `logs/asclexis.log` claim (`data-privacy.md:33`) is false, not UNVERIFIED (matrix AUD-05). HIPAA applicability is conditional on the operator and contracts and must not be asserted.
- **Enforced at:** —.
- **Verify:** —.
- **On violation:** —.
- **Owner:** Owner / legal (plan 08 brief 4).
- **Planned by:** P08 (brief 4); W-11b O-C3-4 for sink visibility.

## 13. Verification gates (the meta-contract)

**C-GATE-1 · BINDING.**
- **Rule:**
  - A verification claim MUST carry the command and its actual output.
  - A test count MUST be the *collected* count measured on the tree the claim is about, with interpreter and environment named.
  - A number MUST NOT be carried forward from another ref or date.
  - A pass-count sentence changes only with a pass count measured in a named environment. It is never derived.
- **Enforced at:** AGENT.md Definition of Done; review.
- **Verify:**
  - Baseline 2026-09-27: `1245 tests collected` at `40f590e`.
  - Measured 2026-09-27 (Win Py 3.13.7, scratch archives): main 1245 · A 1248 · B 1288 · A+B merge-tree 1291. B `AGENT.md:76` (1269) is stale.
  - Working command in this WSL checkout: `cd src/backend && /mnt/c/Python313/python.exe -B -m pytest tests/ --collect-only -q -p no:cacheprovider`.
  - `python` is absent, and `/home/danny/venvs/healthcentral-backend` lacks SQLAlchemy. CI uses 3.11.
- **On violation:** retract the number.
- **Owner:** Engineering.

**C-GATE-2 · BINDING.**
- **Rule:** A CI gate MUST fail closed. A scanner crash or a missing report MUST NOT pass.
- **Enforced at:** on main, `scripts/security_gate.py:49-51,76-78` fails **open**; fixed on branch B `934a842` (HC-SECGATE-001…007).
- **Verify:** after the merge, feed the gate a missing or malformed report and observe a non-zero exit.
- **On violation:** block the merge.
- **Owner:** Engineering; merge is owner-approved.

**C-GATE-3 · BINDING.**
- **Rule:** Staging MUST use explicit task-owned pathspecs, and `git diff --cached --name-only` must be reviewed before each commit. `git add -A` and `git add .` are not allowed. A directory pathspec is allowed only when `git status --short <dir>` shows task-owned changes and nothing else. Commit-level gates run in a clean worktree when anything else is editing the tree.
- **Enforced at:** review (recurring-failures #5).
- **Verify:** `grep -nE 'git add (-A|\.)( |$|`)' audit/2026-09-25/plans/*.md | grep -vE '^[^:]+:[0-9]+:>'` → none. Then list directory adds with `grep -nE 'git add [^ ]+/( |$|`)' audit/2026-09-25/plans/*.md`, and each needs the status check. Plans 03 and 05 carry such adds; their banners require the check (added 2026-09-27).
- **On violation:** unstage; never `git reset` to clean up shared work.
- **Owner:** Engineering.

**C-GATE-4 · BINDING.**
- **Rule:** Docs changes MUST pass `python3 scripts/docs_lint.py`. New docs MUST be reachable (DOC-011). `docs/INDEX.md` regeneration MUST NOT overwrite uncommitted owner edits.
- **Enforced at:** CI `docs-lint`.
- **Verify:** `python3 scripts/docs_lint.py`; `python3 scripts/generate_docs_index.py --check`.
- **On violation:** fix the links or the index, with the owner's consent for `docs/INDEX.md`.
- **Owner:** Engineering.

---

## Proposals and owner gates, reconciled

When two sources disagree, the rule is: code is evidence of current behaviour, and a dated owner record outranks an agent plan.

| Topic | Conflicting sources | Decision in this pass | Rationale | Depends on | Approval authority |
|---|---|---|---|---|---|
| FK enforcement approval | Review F-02 says unapproved; plan 06 says approved | **Sequence and blast radius approved; delete semantics owner-gated** (explicit D5 stop) | `backlog-closure-plan.md` §14 d3 (branch A, `fe31e78`). The pre-decision question asked only about tolerating orphan-write failures; approval of CASCADE / SET NULL is inferred | P1 merge brings the record to main | Owner |
| `.claude/agents/` | Research 02 said ADOPT the five agents; plan 03 recommends B (fix docs) | **D1 decided 2026-09-27: A, all 5 agents** (hooks not licensed) | `owner-decisions-2026-09-27.md:17-18` (replaces §21 Q2 "Not sure") | W-1 plan; P1-DRIFT | Owner |
| Serena memories | Plan 04 recommended DELETE; audit says decide; research 02 proposes a freshness gate | **Blocked; owner chooses** | deletion of tracked files is not authorized | — | Owner |
| HC-M11 | Plan 08 treats it as gated; branch A §14 d2 records it approved | **Approved for build behind a default-off flag only**; production behaviour change is gated | scoped approval text | P1 merge | Owner |
| Export redaction scope | `data-privacy.md:173` says all non-backup exports; code redacts only 3 of 5 | **Owner-gated**; the doc claim is flagged false until decided | patient-directed vs third-party exports | — | Owner |
| Verified-only consumers | `pipelines.md` says the verified set; code serves unverified to trends and RAG | **Owner-gated** | product/UX decision with safety impact | — | Owner |
| HIPAA status | Plan 08 said "not a covered entity" | **Conditional; legal review** | depends on operator and contracts | — | Owner / legal |
| External runner vs ModelRunner | `CLAUDE.md:25` says all LLM calls; `core/external_runner.py` is a separate opt-in runner | **Owner-gated deviation**, recorded rather than approved | cloud path documented in `skills/asclexis-guardrails` | — | Owner |
| Laya adoption | Research 01 said it runs on "all tiers" | **Test candidate only** | vendor-reported numbers | local eval | Owner |

Back to index: [README.md](README.md)
