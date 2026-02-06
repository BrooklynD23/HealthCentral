# HealthCentral Repository Audit Report (2026-02-01)

Repository audit covering:
- Code quality and consistency
- Security vulnerabilities (OWASP Top 10)
- Test coverage gaps
- Documentation accuracy / outdated docs
- Technical debt (TODOs, incomplete features)
- Performance considerations

> Constraint: No code changes were made during this audit. This report is the only artifact added/updated.

## Snapshot

- Date: 2026-02-01
- Branch: `Security-Revamp-2` (local repo status showed `ahead 8`)

## Executive Summary

- **High risk**:
  - Stored medical documents appear to be written **unencrypted** due to `IngestModule` being initialized without an encryption key in `src/backend/api/documents.py`.
  - Per-profile “SQLCipher” database encryption may be **non-functional** depending on the runtime SQLite build (current code uses `sqlite+aiosqlite` + `PRAGMA key`, which can be a no-op on non-SQLCipher SQLite).
  - Backend may fail to start due to invalid dependency injection usage in `src/backend/api/model_settings.py` (`Depends(RequireAuth())`, `Depends(ProfileDbSession)`).
  - `npm audit` reports **high** severity vulnerabilities in the frontend dependency tree (`react-router`/`react-router-dom` via `@remix-run/router` advisory).
- **Medium risk**:
  - Model downloads from Hugging Face are performed without revision pinning (supply chain integrity risk).
  - JWT signing secret is persisted to disk with unclear permissions on Windows (`data/.jwt_secret`).
  - Backend and frontend dependency hygiene: Python deps are largely unpinned (`>=`), and `pip-audit` flagged `ecdsa` for `CVE-2024-23342`.
  - Missing frontend ESLint configuration blocks intended linting/CI quality gates.
  - Limited FastAPI-route integration tests increases regression risk for auth/session/db wiring.
- **Low risk / hygiene**: encoding artifacts (mojibake), doc version drift, stray/empty root `package-lock.json`, large TODO backlog.

## Audit Checklist

### Code Quality Review
- [x] Consistent style (Python/TS)
- [ ] Docstrings / comments accuracy
- [x] Dead code / unused imports
- [ ] Error handling consistency
- [ ] Logging consistency (incl. PII/PHI concerns)
- [ ] Type annotations (Python + TS)

### Security Audit (OWASP)
- [ ] A01 Broken access control
- [x] A02 Cryptographic failures
- [ ] A03 Injection
- [ ] A04 Insecure design
- [x] A05 Security misconfiguration
- [x] A06 Vulnerable/outdated components
- [x] A07 Identification & authentication failures
- [ ] A08 Software & data integrity failures
- [ ] A09 Security logging & monitoring failures
- [ ] A10 SSRF

### Test Coverage
- [x] Backend unit/integration coverage
- [x] Frontend unit coverage
- [x] E2E coverage and reliability
- [x] Edge cases (malformed PDFs, large files, auth failures)

### Documentation Accuracy
- [x] README accuracy (setup, versions, commands)
- [x] Backend/Frontend docs align with implementation
- [x] Security/privacy docs match current behavior

### Technical Debt
- [x] TODO/FIXME inventory
- [x] Incomplete modules / stubs
- [x] Dependency hygiene

### Performance
- [x] PDF/OCR pipeline performance
- [x] DB query and indexing concerns
- [x] Embeddings/vector-search scalability

## Findings

### Security Vulnerabilities (Initial)

1) **A02 Cryptographic failures: document vault encryption is not actually enabled**
   - `src/backend/api/documents.py` constructs `IngestModule(vault_path)` without passing a profile encryption key.
   - `src/backend/modules/ingest.py` explicitly warns that if no `encryption_key` is provided, documents are stored **UNENCRYPTED**.
   - Impact: imported PDFs/images likely land on disk as plaintext PHI (`data/vaults/<profile_id>/docs/<document_id>.bin`), contradicting “encrypted at rest” claims.

2) **A02 Cryptographic failures: SQLCipher encryption may be a no-op**
   - `src/backend/core/profile_database.py` uses `sqlite+aiosqlite` and executes `PRAGMA key = "x'<hex>'"`.
   - If Python’s SQLite driver is not built with SQLCipher, `PRAGMA key` can be ignored while the verification query (`SELECT count(*) FROM sqlite_master`) still succeeds.
   - Impact: per-profile databases may be plaintext SQLite files despite “SQLCipher-encrypted” intent.

3) **A07 Identification/auth: JWT secret persistence permissions unclear on Windows**
   - `src/backend/core/security.py` persists a JWT secret to `data/.jwt_secret` and attempts `chmod(0o600)` (best-effort; not enforced on Windows).
   - Impact: local token signing secret may be readable by other local users depending on filesystem ACLs.

4) **Frontend token storage increases XSS blast radius (desktop mitigations TBD)**
   - `src/frontend/src/stores/authStore.ts` persists JWT tokens to `localStorage`.
   - Impact: any XSS in the renderer can exfiltrate tokens (less likely in a locked-down desktop shell, but still the standard risk model).

### Automated Scan Results (2026-02-01)

1) **Python dependency vulnerability (pip-audit)**
   - `ecdsa 0.19.1` flagged for `CVE-2024-23342` (no fix versions listed by the tool output).
   - Note: backend `requirements.txt` uses mostly `>=` specifiers; results can vary by environment and should ideally be validated against a lock/pinned set.

2) **Python security lints (bandit)**
   - **Medium**: Hugging Face downloads via `hf_hub_download()` without revision pinning (CWE-494) in:
     - `src/backend/api/model_settings.py`
     - `src/backend/modules/model_selector.py`
     - `src/backend/scripts/model_manager.py`
   - **Low**: `try/except: pass` in `src/backend/modules/hardware_detection.py`
   - **Low**: `random.choice()` flagged in `src/backend/modules/message_generator.py` (likely non-cryptographic usage)

3) **Frontend dependency vulnerabilities (npm audit)**
   - **High**: `react-router` / `react-router-dom` via vulnerable `@remix-run/router` (open redirect → XSS advisory)
   - **Moderate**: `lodash` prototype pollution advisory
   - **Moderate**: `eslint` advisory (dev tooling)

### Documentation Issues (Initial)

1) **README Python version mismatch**
   - README says Python **3.10+** while backend `src/backend/requirements.txt` says **Python 3.11+**.
   - Risk: onboarding friction, inconsistent environments.

2) **Mojibake / encoding artifacts in docs**
   - `README.md` and `docs/implementation_prompt_next_agent.md` display box-drawing characters as `â”œâ”€â”€` in some Windows/PowerShell viewers.
   - Risk: reduces readability; indicates inconsistent encoding assumptions across tooling.

3) **README project structure appears out of date**
   - Root `README.md` lists `src/shared/`, `src/desktop/`, and a `tests/` folder at repo root, but current `src/` only contains `backend/` and `frontend/` and tests live under `src/backend/tests` + `src/frontend/...`.
   - README also references a Tauri desktop shell, but there is no `src-tauri/` directory in the repo.

4) **Architecture/security docs conflict with current implementation**
   - `docs/01_backend_architecture_plan.md` describes loopback HTTP with **per-launch bearer token** and random ephemeral port; current implementation uses long-lived JWT sessions with a persisted signing key and a fixed default port.
   - `docs/03_data_confidentiality_pipeline_plan.md` claims “encrypted document blobs” and “SQLCipher DB” as implemented; current code path stores imported documents unencrypted (see Security finding #1) and SQLCipher enforcement is not guaranteed (see Security finding #2).

5) **Execution/status docs are stale relative to code**
   - `docs/06_mvp_to_rag_execution_board.md` states several components return `501` or are `NotImplementedError` stubs; current code appears to have implemented many of those areas (e.g., RAG module, export endpoints).
   - `docs/05_backend_integration_status.md` lists backend module statuses (e.g., `extract.py` “partial”, `rag.py` “stub”) that no longer match the current codebase.

### TODO / Technical Debt (Initial)

Collected via repo search (not yet triaged):
- `src/backend/modules/ingest.py`: duplicate check TODO
- `src/backend/modules/verify.py`: multiple TODOs (DB query, payload preparation, edit application, date validation)
- `src/backend/modules/verifier_agent.py`: entailment TODO
- Various feature TODOs tracked in `docs/features/TASK_LIST.md`

### Repo Hygiene / Sensitive Artifacts

1) **AI tool configuration and “memory” files are tracked**
   - Tracked paths include `.claude/settings.local.json` and multiple `.serena/memories/*.md` files.
   - These contain machine-specific paths and operational notes; they should be reviewed for sensitive content and likely excluded from version control unless intentionally shipped.

### Code Quality / Correctness Findings

1) **Backend may fail to start: invalid FastAPI dependency usage in `model_settings`**
   - `src/backend/api/model_settings.py` uses `Depends(RequireAuth())` and `Depends(ProfileDbSession)`.
   - `RequireAuth` / `ProfileDbSession` are typed `Annotated[...]` aliases (not callables), so calling/depending on them is likely to raise at import/runtime.
   - Impact: model settings endpoints (and potentially the whole app, since routers are included) may crash on startup.

2) **Lint/format debt is high (backend)**
   - `python -m ruff check src/backend` reports **118 issues** (many unused imports + style problems; many auto-fixable).
   - `python -m black --check src/backend` indicates **55 files would be reformatted**.

3) **Frontend lint script currently fails**
   - `npm run lint` fails because there is **no ESLint configuration file** in `src/frontend/`.
   - Impact: CI/quality gate cannot enforce TS/React code standards as intended.

4) **Verification module appears stubbed/unwired**
   - `src/backend/modules/verify.py` contains multiple `NotImplementedError` paths and TODOs.
   - This conflicts with “verification workbench complete” messaging unless the module is intentionally unused.

5) **Frontend/backend contract drift around `profile_id`**
   - Frontend services include `profile_id` as a query param on multiple endpoints (`src/frontend/src/services/documents.ts`, `src/frontend/src/services/observations.ts`).
   - Backend endpoints derive `profile_id` from the JWT session and do not declare a `profile_id` query param.
   - Impact: confusing contract; potential for UI bugs (e.g., `DocumentInbox.tsx` uses `localStorage.activeProfileId` rather than auth store).

6) **Likely broken UI flows due to ID mismatches**
   - `src/frontend/src/pages/DocumentInbox.tsx` reads `activeProfileId` from `localStorage`, but no other code sets it (repo search only finds this reference). This prevents document list/import from running (`useDocuments` is disabled when `profile_id` is empty).
   - `src/frontend/src/pages/TrendsDashboard.tsx` uses panel id `lipids`, but backend panel definitions use `lipid` (`src/backend/api/observations.py`). This causes `/observations/panels/lipids` to 404.

### Test Coverage Gaps (Heuristic)

1) **Backend tests are mostly module-level, not HTTP/API-level**
   - `src/backend/tests/` tests instantiate modules directly (e.g., `ExportModule`) and do not use `TestClient`/`httpx` to exercise FastAPI routes.
   - Impact: gaps in coverage for auth, request validation, HTTP status codes, and dependency wiring (e.g., profile DB session).

2) **Large surface area with limited targeted coverage**
   - Repo contains ~60 FastAPI route handlers across: profiles, documents, observations, assistant, export, interpretations, medications, notifications, model settings.
   - There are 5 main backend test files; coverage for `medications.py`, `interpretations.py`, `model_settings.py` appears especially thin.

3) **Frontend tests exist but don’t replace backend integration tests**
   - `src/frontend/src/__tests__/` has component tests and `src/frontend/e2e/` has Playwright E2E tests (auth + assistant).
   - Gaps likely remain for document import, verification edits, trends correctness, export download behaviors against a real backend.

### Performance Considerations (Heuristic)

1) **RAG vector search scales poorly**
   - `src/backend/modules/rag.py` fetches **all** chunks+embeddings for a profile and computes similarity in Python.
   - Documented filters (`selected_analytes`, `from_date`, `to_date`) are noted as “not yet implemented” in the async search method docstring.
   - Impact: O(N) per query and increasing latency as the vault grows.

2) **Import path does heavy work inline**
   - `src/backend/api/documents.py` performs extraction, DB writes, and then chunking+embedding creation during import.
   - For large PDFs, this can cause long request times and memory spikes (file is read fully into memory in `src/backend/modules/ingest.py`).

## Recommended Remediation Plan (Prioritized)

### P0 (Fix ASAP)

1) **Enable real encryption at rest**
   - Pass the per-profile encryption key into `IngestModule`.
   - Integrate decrypt/read paths everywhere documents are opened (import, pages, extraction, chunking).
   - Add an explicit runtime check that SQLCipher is actually active (fail closed if not).

2) **Fix backend startup/runtime blockers**
   - Fix `src/backend/api/model_settings.py` dependency injection (`session: RequireAuth`, `profile_db: ProfileDbSession`), and add a minimal import/startup test to catch this class of issue.

3) **Fix broken core UI flows**
   - Remove `activeProfileId` localStorage usage and use the auth store profile id consistently.
   - Align panel IDs between frontend and backend (`lipid` vs `lipids`).

4) **Patch known vulnerable dependencies**
   - Update frontend routing deps to a non-vulnerable `react-router-dom` / `@remix-run/router` version.
   - Triage `pip-audit` result for `ecdsa` (confirm whether `python-jose` brings it in; pin/upgrade accordingly).

### P1 (Near-term)

1) **Establish enforced lint/format configs**
   - Add ESLint config to `src/frontend/` so `npm run lint` is actionable.
   - Add a backend `pyproject.toml` (or equivalent) to standardize `ruff`/`black`/`mypy` configuration.

2) **Add API-level integration tests**
   - Add minimal FastAPI route tests for: auth/login, documents import/list/pages, observations list/verify/trends/panels, export endpoints.
   - Include negative tests (401/403, locked profile DB, invalid UUIDs, unsupported file types, oversized uploads).

3) **Harden model download integrity**
   - Pin HF downloads by revision (commit hash/tag) and validate expected file hashes for GGUF models.

### P2 (Scale/perf)

1) **Vector search scalability**
   - Replace "load everything and score in Python" with a real vector index approach (FAISS, sqlite-vss, or equivalent) and implement analyte/date filters.
   - Remove `asyncio.run()` patterns inside running event loops in `src/backend/modules/rag.py`.

2) **Move heavy import work to background**
   - Offload chunking/embedding generation (and potentially extraction) to background tasks, with progress reporting and retry semantics.
