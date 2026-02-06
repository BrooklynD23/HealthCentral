# HealthCentral Complete Repository Audit Report

**Date:** 2026-02-02
**Branch:** `Security-Revamp-2`
**Audited Commit:** `3751c76` (Security Audit Remediation: Fix critical encryption and auth issues)
**Audit Type:** Post-Remediation Verification + Comprehensive Review

---

## Executive Summary

This audit verifies the security remediation performed in commit `3751c76` and provides a comprehensive assessment of the repository's security, code quality, documentation, and architecture.

### Overall Assessment

| Category | Score | Status |
|----------|-------|--------|
| Remediation Verification | 95% | All P0 fixes complete |
| Security | 85% | 0 P0, 5 P1 issues remain |
| Code Quality | 75% | 4 HIGH, 6 MEDIUM, 6 LOW issues |
| Documentation | 90% | README updated, SQLCipher documented |
| Architecture | 80% | Good separation, **no migrations system** |

### Critical Findings

1. **~~P0: SQLCipher Provisioning Not Documented~~** - **RESOLVED (2026-02-03)**
   - Added `sqlcipher3-binary>=0.5.0` to requirements.txt
   - Created `core/sqlcipher_driver.py` helper module
   - Added startup verification in `init_database()`
   - Patched aiosqlite to use sqlcipher3 in `profile_database.py`
   - Added SQLCipher Setup section to README.md
   - Added `DATABASE_ENCRYPTION_REQUIRED` to `.env.example`

2. **P1: No Database Migration System** - No Alembic or equivalent. Schema changes risk data loss.

---

## 1. Remediation Verification Results

### Verified Fixes (Static Analysis)

| Issue | Fix Applied | Verification Status |
|-------|-------------|---------------------|
| FastAPI `Depends()` pattern broken | Changed to `Annotated` type aliases | **PASS** - Type aliases work correctly |
| Document encryption disabled | Encryption key now passed to IngestModule | **PASS** - Code path confirmed |
| Decrypt-on-read missing | Created `document_crypto.py` helper | **PASS** - Helper implemented and integrated |
| SQLCipher verification absent | Added `cipher_version` check | **PASS** - Fail-closed behavior working |
| DocumentInbox localStorage bug | Uses `useAuthStore` now | **PASS** - Uses auth store for profile ID |
| Panel ID mismatch (lipids/lipid) | Changed frontend to `lipid` | **PASS** - Frontend uses correct ID |
| ESLint config missing | Created `eslint.config.js` | **PASS** - Flat config correct |
| HF download revision pinning | Added `revision` param | **PASS** - All 3 locations updated |
| Frontend contract drift | Removed unused `profile_id` params | **PASS** - Services updated |
| Ruff config missing | Created `pyproject.toml` | **PASS** - E712 ignored for SQLAlchemy |

### CRITICAL ISSUE: SQLCipher Provisioning

**Severity:** P0 - CRITICAL

The SQLCipher verification logic is correctly implemented, but **SQLCipher itself is not provisioned** in the default development environment:

```python
# profile_database.py - This check will FAIL on standard sqlite3:
cursor.execute("PRAGMA cipher_version")
cipher_version = cursor.fetchone()  # Returns None without SQLCipher

if not cipher_version or not cipher_version[0]:
    if settings.database_encryption_required:  # Defaults to True!
        raise ProfileDatabaseEncryptionError(...)
```

**Impact:** Login will return HTTP 500 unless:
1. A SQLCipher-enabled SQLite driver is installed (e.g., `sqlcipher3`, `pysqlcipher3`), OR
2. `DATABASE_ENCRYPTION_REQUIRED=false` is set in `.env` for development

**Immediate Actions Required:**
1. Document SQLCipher installation in README (Windows: vcpkg/prebuilt, Linux: apt-get)
2. Add `DATABASE_ENCRYPTION_REQUIRED=false` to `.env.example` with clear warning
3. Consider shipping SQLCipher-enabled binaries for production

### Note: FastAPI DI Pattern Clarification

The pattern `profile_db: ProfileDbSession = None` does **NOT** break FastAPI dependency injection. Verification confirmed:
- All 44 routes with `profile_db` still include `get_profile_db_session` in their dependency graph
- The `Annotated` type alias carries `Depends()` metadata regardless of default value
- Failure mode is HTTP 403 from `get_profile_db_session`, not `AttributeError`
- Tested with FastAPI 0.109.0 and 0.123.5

### Detailed Verification Results

#### 1. FastAPI DI Pattern - **PASS**
All endpoints using `ProfileDbSession` type alias correctly resolve dependencies. The `Annotated[AsyncSession, Depends(get_profile_db_session)]` pattern works regardless of whether a default value is specified.

#### 2. Document Encryption Key Flow - **PASS**
- Line 150: `encryption_key = get_profile_encryption_key(profile_id)`
- Line 156: `ingest = IngestModule(vault_path, encryption_key=encryption_key)`
- Proper error handling if key is None

#### 3. Decrypt-on-Read Infrastructure - **PASS**
`src/backend/core/document_crypto.py` implements:
- `get_profile_encryption_key(profile_id)` - Retrieves key from active session
- `get_decrypted_document(profile_id, document_id)` - Returns `io.BytesIO` for processing

Usage verified in `documents.py`:
- Line 195: Import endpoint uses decrypt helper
- Line 323: Pages endpoint uses decrypt helper
- Line 477: Chunks creation uses decrypt helper

#### 4. SQLCipher Verification - **PASS**
`profile_database.py` lines 253-279:
- Executes `PRAGMA cipher_version` check
- Raises `ProfileDatabaseEncryptionError` if SQLCipher unavailable and `DATABASE_ENCRYPTION_REQUIRED=true`
- Fail-closed behavior prevents silent fallback to unencrypted

#### 5. Ruff Configuration - **PASS**
`pyproject.toml` contains:
- `line-length = 100`, `target-version = "py311"`
- Rules: F (Pyflakes), I (isort), W (pycodestyle)
- E712 ignored for SQLAlchemy compatibility

#### 6. ESLint Configuration - **PASS**
`eslint.config.js` uses ESLint 9 flat config:
- TypeScript-ESLint integration
- React Hooks rules
- `@typescript-eslint/no-explicit-any` set to warn

---

## 2. Security Audit Findings

### P0 Critical Issues: **NONE** (security-specific)

The previous security P0 findings have been remediated. The SQLCipher provisioning issue above is a deployment/documentation issue, not a security vulnerability - the security logic is correctly implemented.

### P1 Important Issues (5 Found)

#### P1-1: Legacy Insecure Functions Still Present
**File:** `src/backend/core/security.py:313-354`

Two deprecated legacy functions return unprotected keys on failure:
- `seal_key_with_dpapi_legacy()` (line 313)
- `unseal_key_with_dpapi_legacy()` (line 336)

**Risk:** Security fallback behavior that should not exist in production.
**Recommendation:** Remove these functions or make them raise exceptions.

---

#### P1-2: JWT Token Invalidation Not Implemented
**File:** `src/backend/api/profiles.py:328`

The logout endpoint does not invalidate JWT tokens - tokens remain valid until expiration (60 minutes).

**Risk:** Stolen tokens cannot be revoked.
**Recommendation:** Implement token blacklist or use shorter token lifetimes with refresh tokens.

---

#### P1-3: No Rate Limiting on Authentication Endpoints
**Files:** `src/backend/api/profiles.py:244` (login), `profiles.py:416` (unlock)

No rate limiting exists on login and unlock endpoints.

**Risk:** Brute-force password attacks possible.
**Recommendation:** Implement rate limiting using `slowapi` or custom middleware.

---

#### P1-4: SQLCipher Key in SQL String
**File:** `src/backend/core/profile_database.py:276`

The encryption key is passed via string interpolation:
```python
cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")
```

**Risk:** Low (key is internally derived), but pattern is fragile.
**Recommendation:** Document why this pattern is necessary for SQLCipher.

---

#### P1-5: Document Decryption Fallback to Plaintext
**File:** `src/backend/modules/ingest.py:193-196`

The `decrypt_document()` function falls back to returning plaintext on decryption failure.

**Risk:** Unencrypted legacy documents accessed without proper warning.
**Recommendation:** Add explicit flag for legacy document handling.

---

### P2 Minor Issues (5 Found)

| ID | Description | File | Recommendation |
|----|-------------|------|----------------|
| P2-1 | Debug mode exposes API docs | `main.py:32-33` | Ensure `DEBUG=false` in production |
| P2-2 | Profile ID logged on auth failure | `auth.py:117-125` | Acceptable for debugging |
| P2-3 | CORS allows all headers | `main.py:40-50` | Explicitly list allowed headers |
| P2-4 | In-memory summary storage | `export.py:38-39` | Move to database for production |
| P2-5 | Dependency versions not strictly pinned | `requirements.txt` | Use exact versions or ranges |

### Security Strengths Identified (14)

1. Protected API endpoints require authentication via `RequireAuth` dependency (login/register intentionally unauthenticated)
2. Profile isolation enforced with `verify_*_access()` helper functions
3. JWT token validation with expiration checking
4. Session expiration handling
5. Password requirements enforce minimum complexity
6. PHI encrypted at rest using AES-GCM with per-document IVs
7. Comprehensive audit logging for sensitive operations
8. Secure key management using DPAPI or PBKDF2 (600,000 iterations)
9. Keys cleared from memory on logout/lock
10. JWT secret persisted with chmod 0o600
11. UUID validation on all ID parameters
12. File upload validation (type and size limits)
13. SQL injection prevention (SQLAlchemy ORM)
14. Path traversal prevention (UUID-based file paths)

---

## 3. Architecture Audit Findings

### Separation of Concerns - **GOOD**

**Backend Structure:**
- `/src/backend/api/` - HTTP endpoint handlers (9 routers)
- `/src/backend/core/` - Cross-cutting concerns (config, database, auth, security)
- `/src/backend/models/` - SQLAlchemy ORM models (14 model files)
- `/src/backend/modules/` - Domain business logic (27 specialized modules)

**Strengths:**
- Clear layer separation: API layer doesn't contain business logic
- Domain logic isolated in modules (e.g., `interpret.py`, `rag.py`)
- Models cleanly separated into master DB and per-profile DB bases

**Violations Found:**
- Module-level caching in `api/assistant.py` (lines 125-142): Global `_rag_module` cache creates hidden dependencies

**Frontend Structure:**
- `/src/frontend/src/components/` - UI components (auth, layout, ui)
- `/src/frontend/src/pages/` - Page-level containers (6 pages)
- `/src/frontend/src/services/` - API service layer (8 service files)
- `/src/frontend/src/stores/` - State management (Zustand)

**Strengths:**
- Components stay presentational
- Services layer cleanly decouples from API (React Query hooks)
- State centralized in Zustand stores

---

### Circular Dependencies - **MINIMAL**

**Patterns Used to Avoid Circular Imports:**
1. `TYPE_CHECKING` guards in `core/auth.py`
2. Lazy imports inside functions in `api/documents.py`

**No circular dependencies detected.** The codebase uses proper import hygiene.

---

### Database Migrations - **CRITICAL GAP**

**Issue:** No Alembic or migration system exists.

**Current Approach:**
```python
# core/database.py (lines 54-80)
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)  # Creates all tables
```

**Problems:**
1. No versioning of schema changes
2. No forward compatibility for existing deployments
3. No rollback capability
4. Data loss risk on schema changes

**Recommendation:** Implement Alembic migrations immediately with baseline migration from current schema.

---

### API Contracts - **PARTIAL ALIGNMENT**

**Strengths:**
- Comprehensive Pydantic models for all requests/responses
- Type hints throughout

**Issues Found:**

1. **Missing Enum Types:**
   - Document status: Backend stores `"pending"`, `"parsed"`, `"verified"` - Frontend accepts arbitrary `string`
   - Observation flags: Backend uses `"L"`, `"H"`, `"C"` - Frontend has no type safety

2. **Panel Definitions Hardcoded in Two Places:**
   - Backend: `observations.py` lines 72-89
   - Frontend: Components hardcode panel names
   - No shared source of truth

3. **Panel Definitions Not Shared:**
   Backend and frontend both define panel configurations independently with no single source of truth.

**Recommendation:** Generate frontend types from Pydantic schema using `pydantic-openapi-schema` or similar.

---

### Error Response Consistency - **INCONSISTENT**

**Status Codes - GOOD:**
- `201 Created` for creation
- `204 No Content` for deletions
- `400/403/404` used consistently

**Error Format - INCONSISTENT:**
- Standard FastAPI `{"detail": "message"}` used in API layer
- Module-level errors in dataclass fields sometimes lost in translation
- Frontend handler falls back to `parsed.message` but backend only uses `detail`

**Recommendation:** Create standard error response wrapper with error codes.

---

### Module Dependencies - **TIGHT COUPLING**

**RAG Module Verification Chain** (`modules/rag.py`):
```python
from .embeddings import EmbeddingsModule
from .claim_extractor import ClaimExtractor
from .source_authority import SourceAuthorityScorer
from .verifier_agent import VerifierAgent
from .faithfulness import FaithfulnessScorer
```
Creates a 5-module dependency cascade. Hard to test in isolation.

**Recommendation:** Create dependency injection container for module initialization.

---

## 4. Code Quality Audit Findings

### HIGH Severity (4 Issues)

#### 4.1 Unused Import: `WeakValueDictionary`
**File:** `src/backend/core/profile_database.py:19`
```python
from weakref import WeakValueDictionary  # UNUSED
```

---

#### 4.2 Async Function Without Await
**File:** `src/backend/modules/ingest.py:201-279`

`import_document()` is marked `async` but contains no `await` expressions.

**Impact:** Synchronous file I/O blocks the event loop.

---

#### 4.3 Bare Exception Handling
**File:** `src/backend/api/assistant.py:250-254`
```python
except Exception as e:
    raise HTTPException(...)
```
**Impact:** Could leak sensitive error details.

---

#### 4.4 Duplicate UUID Validation Code
**Files:** `src/backend/api/documents.py:35-49`, `src/backend/api/observations.py:29-43`

Same `UUID_PATTERN` and `validate_uuid()` function duplicated.

**Recommendation:** Extract to shared utility module.

---

### MEDIUM Severity (6 Issues)

| # | Issue | File | Line |
|---|-------|------|------|
| 1 | Missing type hint on `profile_db` param | `documents.py` | 299-303 |
| 2 | Inconsistent error handling in security module | `security.py` | 76-77 |
| 3 | Missing docstrings on response models | `model_settings.py` | 65-78 |
| 4 | Unused `asyncio` import | `model_settings.py` | 10 |
| 5 | Unused mutation parameter `profileId` | `documents.ts` | 68-69 |
| 6 | Empty catch block | `VerificationWorkbench.tsx` | 83-84 |

### LOW Severity (6 Issues)

| # | Issue | Files |
|---|-------|-------|
| 1 | Deprecated `datetime.utcnow()` usage | Multiple (4 files) |
| 2 | Inline import inside function | `documents.py:202` |
| 3 | Magic numbers in confidence calculation | `extract.py:260-266` |
| 4 | Potential undefined array access | `TrendsDashboard.tsx:91-92` |
| 5 | Inconsistent error type casting | `VerificationWorkbench.tsx:139` |
| 6 | Unused `panelData` fetch | `TrendsDashboard.tsx:77` |

---

## 5. Documentation Audit Findings

### Overall Score: **72%**

### Issues Found

#### P0 Critical (Fix Immediately) - **ALL RESOLVED**

1. **~~README Python Version Mismatch~~** - **RESOLVED (2026-02-03)**
   - README updated to Python 3.11+
   - dev.ps1 updated to require Python 3.11+

2. **~~README Project Structure Outdated~~** - **RESOLVED (2026-02-03)**
   - Removed non-existent `src/shared/`, `src/desktop/`, root `tests/`
   - Updated structure to show `src/backend/tests/` correctly
   - Removed Tauri references, updated to "React + Vite + TypeScript"

#### P1 High Priority

3. **Missing CONTRIBUTING.md** - No contribution guidelines
4. **Missing SECURITY.md** - No security policy or vulnerability reporting
5. **Architecture docs conflict with implementation**
   - `01_backend_architecture_plan.md` describes per-launch bearer token; code uses JWT

#### P2 Medium Priority

6. **Missing SQLCipher installation instructions**
7. **Frontend env vars not in `.env.example`** (`VITE_API_URL`)
8. **No static OpenAPI schema exported**

---

## 6. Recommended Actions

### Immediate (P0) - **ALL COMPLETE** (2026-02-03)

1. ~~**Document SQLCipher provisioning:**~~ **DONE**
   - Added `sqlcipher3-binary>=0.5.0` to requirements.txt
   - Created `core/sqlcipher_driver.py` with fallback to sqlite3
   - Added startup verification in `database.py`
   - Added SQLCipher Setup section to README with install instructions

2. ~~**Update README.md:**~~ **DONE**
   - Changed Python version to 3.11+
   - Updated project structure to match actual directories
   - Added SQLCipher setup section

3. ~~**Update `.env.example`:**~~ **DONE**
   - Added `DATABASE_ENCRYPTION_REQUIRED=true` with warning comment

### Short-term (P1) - This Sprint

4. **Implement Alembic migrations:**
   - Create baseline migration from current schema
   - Add migration verification tests

5. **Security hardening:**
   - Remove legacy `*_dpapi_legacy()` functions
   - Add rate limiting to auth endpoints

6. **Code quality fixes:**
   - Remove unused `WeakValueDictionary` import
   - Extract UUID validation to shared utility

7. **Documentation:**
   - Create `CONTRIBUTING.md`
   - Create `SECURITY.md`

### Medium-term (P2) - Next Sprint

8. **Implement JWT token blacklist**
9. **Add Enum types for fixed-value fields**
10. **Create dependency injection container for modules**
11. **Export static OpenAPI schema**

---

## 7. Summary Statistics

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Remediation | ~~1~~ 0 | 0 | 0 | 0 | 0 |
| Security | 0 | 5 | 5 | 0 | 10 |
| Architecture | 0 | 1 | 3 | 0 | 4 |
| Code Quality | 0 | 4 | 6 | 6 | 16 |
| Documentation | ~~2~~ 0 | 3 | 3 | 0 | 6 |
| **Total** | **0** | **13** | **17** | **6** | **36** |

### Risk Assessment

| Risk | Level | Details |
|------|-------|---------|
| P0 Runtime | ~~HIGH~~ **RESOLVED** | SQLCipher provisioned via sqlcipher3-binary |
| P0 Security | None | All security issues remediated |
| P1 Data Integrity | High | No migration system for schema changes |
| P1 Security | Medium | 5 defense-in-depth improvements needed |
| Documentation Gap | ~~Moderate~~ **Low** | README updated, SQLCipher documented |

---

## 8. Conclusion

The security remediation in commit `3751c76` successfully addressed the critical security issues:
- Document encryption is enabled
- SQLCipher verification with fail-closed behavior
- Decrypt-on-read infrastructure complete
- FastAPI dependency injection patterns work correctly
- Frontend bugs (auth store, panel ID) resolved
- Lint configurations exist

**P0 Items Resolved (2026-02-03):**

All P0 blockers have been addressed:
- **SQLCipher provisioned** via `sqlcipher3-binary` package with aiosqlite patching
- **README updated** with correct Python version (3.11+) and project structure
- **SQLCipher documentation** added to README with installation instructions
- **dev.ps1 updated** to require Python 3.11+

**Remaining P1 issues to address:**
- No database migration system (Alembic) - schema changes risk data loss
- Missing CONTRIBUTING.md and SECURITY.md
- Legacy DPAPI fallback functions should be removed
- Rate limiting needed on auth endpoints

### Verification Checklist for Next Steps

```bash
# 1. For development without SQLCipher, add to .env:
DATABASE_ENCRYPTION_REQUIRED=false

# 2. Verify backend starts:
cd src/backend
python -c "from main import app; print('App startup OK')"
python -m pytest tests/ -v

# 3. Verify frontend:
cd ../frontend
npm run lint
npm run build
npm test
```

---

## 9. Agent Handoff: Fix Implementation Instructions (P0 -> P2 -> Low)

This section is a practical hand-off for the next agent/team that will implement fixes. It is ordered by impact and "unblocks first".

### Working Agreements (Read First)

1. **Keep scope tight:** Fix the item at hand; avoid refactors that aren't required to resolve the stated issue.
2. **Fail-closed in production:** Any security/encryption decision must default to safe behavior for `APP_ENV=production`.
3. **Prefer explicit flags over silent fallbacks:** If we allow plaintext legacy docs or non-SQLCipher SQLite, make it an explicit setting with loud warnings.
4. **Ship verifiable changes:** Each item below includes concrete acceptance criteria; do not mark complete without running the relevant verification steps.

---

### P0 (Critical) - Runtime Unblockers + Documentation Clarity - **ALL COMPLETE**

#### ~~P0-1 - SQLCipher provisioning (real blocker)~~ **RESOLVED 2026-02-03**

**Problem:** `DATABASE_ENCRYPTION_REQUIRED` defaults to `true`, but standard Python SQLite does **not** include SQLCipher. Profile DB open will fail at login/unlock in most dev environments unless SQLCipher is actually provisioned.

**Goal:** Make the "encrypted by default" design *operationally real* (or explicitly dev-only plaintext), with clear docs and predictable behavior.

**Decision required (choose one and document it):**

- **Path A (recommended for immediate dev unblock):** Support **dev-only plaintext profile DB** by setting `DATABASE_ENCRYPTION_REQUIRED=false` (and documenting the security tradeoff).
- **Path B (recommended for security-first releases):** Provide a **SQLCipher-capable runtime** for all supported platforms (Windows/macOS/Linux) and keep `DATABASE_ENCRYPTION_REQUIRED=true`.

**Implementation instructions:**

1. **Documentation / configuration (must-do regardless of A/B):**
   - Update `README.md` with a dedicated "SQLCipher Setup" section:
     - What SQLCipher is, why we need it (encrypted per-profile vault DB).
     - How to run in dev without SQLCipher (only if Path A is supported).
     - How to verify SQLCipher is working (e.g., `PRAGMA cipher_version` returns a value).
   - Update `config/.env.example`:
     - Add `DATABASE_ENCRYPTION_REQUIRED=false` **with a warning comment** ("dev only; set true in production with SQLCipher available").
     - Add `VITE_API_URL=http://localhost:8000/api/v1` (frontend uses `/api/v1` base).
   - Clarify **where `.env` should live**:
     - Backend settings load `env_file=".env"` relative to the backend's working directory (`src/backend` when running locally).
     - Frontend uses Vite's `.env` in `src/frontend` (or `.env.local`).

2. **Path A (dev-only plaintext) specifics:**
   - Ensure README and `.env.example` explicitly describe:
     - Local dev can proceed with plaintext profile DB by setting `DATABASE_ENCRYPTION_REQUIRED=false`.
     - Production must not use this setting.
   - Add a startup log warning when `DATABASE_ENCRYPTION_REQUIRED=false`.
   - Add a CI/test job (or unit test) that asserts the default remains `true` unless explicitly overridden.

3. **Path B (real SQLCipher provisioning) specifics:**
   - Pick one supported provisioning approach and document it:
     - **Ship a SQLCipher-enabled SQLite** (preferred for desktop distribution), or
     - **Use a SQLCipher-capable DB-API driver** compatible with the chosen async stack.
   - Confirm that the SQLAlchemy async engine actually uses SQLCipher:
     - `aiosqlite` normally uses stdlib `sqlite3`; verify/replace as needed.
   - Add an automated runtime check:
     - `PRAGMA cipher_version` must return non-empty.
     - Attempting to open the DB without the key should fail (where feasible to test).

**Acceptance criteria:**
- A fresh dev can follow README to (a) run in plaintext dev mode, or (b) install SQLCipher and run encrypted mode, with no guessing.
- Login/unlock does not 500 due to missing SQLCipher in the documented dev flow.

**Primary files likely to change:**
- `README.md`
- `config/.env.example`
- `src/backend/core/config.py`
- `src/backend/core/profile_database.py`
- (optional) `dev.ps1` if you choose to auto-copy `.env.example` into place

---

#### ~~P0-2 - Fix Python version mismatch across docs/scripts~~ **RESOLVED 2026-02-03**

**Status:** COMPLETE
- README updated to Python 3.11+
- dev.ps1 updated to require Python 3.11+

---

#### ~~P0-3 - README project structure is outdated~~ **RESOLVED 2026-02-03**

**Status:** COMPLETE
- Updated project structure to match actual directories
- Removed non-existent `src/shared/`, `src/desktop/`, root `tests/`
- Removed Tauri references

---

### P1 (High) - Data Integrity + Security Defense-in-Depth

#### P1-1 - Add a migration system (Alembic) for both databases

**Problem:** No migration/versioning system exists; schema changes risk data loss and break existing installs.

**Key complexity:** There are **two logical databases**:
- **Master DB** (global metadata, profiles, audit logs).
- **Per-profile DB** (vault DB opened with profile auth; contains documents/observations/chunks/embeddings/etc).

**Implementation approach (recommended):**
- Create **two Alembic environments** (clear separation):
  - `src/backend/migrations_master/` for master DB.
  - `src/backend/migrations_profile/` for per-profile DB (ProfileDatabaseBase metadata).

**Implementation instructions:**
1. Add Alembic dependency to `src/backend/requirements.txt` (and document it).
2. Create initial/baseline migrations generated from current models:
   - Master baseline from the master metadata.
   - Profile baseline from the profile metadata.
3. Provide a migration runner strategy:
   - Master DB: run on app startup (safe).
   - Profile DB: run on profile DB open (needs key) or via an explicit "migrate all profiles" maintenance command.
4. Add a test that:
   - Creates an empty DB, runs migrations, and asserts tables exist.
   - Runs "upgrade head" idempotently.

**Acceptance criteria:**
- DB schema changes become additive/versioned; no more `create_all()` as the long-term mechanism.
- A developer can run migrations locally, and CI can verify migrations apply cleanly.

---

#### ~~P1-2 - Remove legacy DPAPI fallback functions~~ **RESOLVED 2026-02-03**

**Status:** COMPLETE
- Removed `seal_key_with_dpapi_legacy()` and `unseal_key_with_dpapi_legacy()` from `security.py`
- Confirmed no call sites existed
- All tests pass

---

#### P1-3 - Add rate limiting to auth endpoints

**Problem:** No rate limiting on login/unlock; brute-force risk.

**Implementation instructions:**
- Choose a mechanism (e.g., `slowapi` or custom middleware).
- Apply to:
  - `POST /profiles/login`
  - `POST /profiles/{profile_id}/unlock` (or equivalent)
- Document limits and how to configure them for local dev/testing.

**Acceptance criteria:**
- Repeated failed auth attempts are throttled server-side.

---

#### P1-4 - Make legacy plaintext document handling explicit

**Problem:** `decrypt_document()` falls back to treating bytes as plaintext if decryption fails.

**Implementation instructions:**
- Add an explicit setting (example: `ALLOW_LEGACY_PLAINTEXT_DOCUMENTS=false` by default).
- If enabled, log a warning with enough context to find/migrate legacy docs.
- Consider adding a one-time migration tool to re-encrypt legacy docs.

**Acceptance criteria:**
- No silent plaintext fallback in secure/default mode.

---

#### ~~P1-5 - Add missing project policy documents~~ **RESOLVED 2026-02-03**

**Status:** COMPLETE
- Created `CONTRIBUTING.md` with:
  - Development setup instructions
  - Code style guidelines
  - PR checklist and workflow
  - Project structure overview
- Created `SECURITY.md` with:
  - Vulnerability reporting process
  - Security architecture overview
  - Known limitations transparency

---

#### P1-6 - Align architecture docs with the implemented auth model (JWT)

**Problem:** `docs/01_backend_architecture_plan.md` describes a per-launch bearer token + ephemeral port, but current code uses JWT (and fixed local ports by default).

**Implementation instructions (choose one direction and make docs/code match):**
- **Option A (doc update):** Update architecture docs to describe current JWT auth and token storage approach.
- **Option B (implementation shift):** Implement the per-launch bearer-token model (bigger change; requires app-runner integration and token distribution to frontend).

**Acceptance criteria:**
- Architecture docs do not contradict the running code.

---

### P2 (Medium) - Maintainability, Contracts, and Performance

#### P2-1 - Standardize API error shape

**Problem:** Mixed error handling (`detail` vs ad-hoc fields) complicates frontend parsing and consistency.

**Implementation instructions:**
- Define a standard error response model (e.g., `{ code, message, details }`) and a single translation layer.
- Keep compatibility: continue returning `detail` for FastAPI defaults where needed, but converge endpoints over time.

**Acceptance criteria:**
- Frontend can rely on a consistent error shape for non-2xx responses.

---

#### P2-2 - Fix blocking I/O in `IngestModule.import_document()`

**Problem:** `import_document()` is `async` but performs blocking file I/O, potentially stalling the event loop.

**Implementation instructions (pick one):**
- Make it truly async (use `anyio.to_thread.run_sync` for blocking work, or `aiofiles` for file ops).
- Or make it synchronous and call it from a worker thread/executor at the API layer.

**Acceptance criteria:**
- Large document imports do not block unrelated requests.

---

#### P2-3 - Tighten API contracts (enums + shared types)

**Problem:** Some backend fixed-value fields are "stringly typed" in the frontend, increasing drift risk.

**Implementation instructions:**
- Introduce enums in backend (Pydantic) for:
  - Document status
  - Observation flags
  - Any other fixed-value fields used in UI logic
- Export OpenAPI schema and generate TypeScript types from it (or provide a stable manual types module).

**Acceptance criteria:**
- Frontend cannot compile if it drifts from backend contract for key enums.

---

#### P2-4 - Export a static OpenAPI schema

**Implementation instructions:**
- Add a script (backend) to write OpenAPI JSON to `docs/openapi.json` (or similar).
- Keep it updated via CI or a "make docs" step.

**Acceptance criteria:**
- A static schema file exists and matches the running API for the current commit.

---

#### P2-5 - Implement JWT token invalidation (logout should revoke)

**Problem:** JWTs remain valid until expiry; logout does not revoke a stolen token.

**Implementation instructions:**
- Add a token revocation strategy:
  - Simple: server-side blacklist keyed by `jti` (requires issuing `jti` claims).
  - Better: short-lived access tokens + refresh tokens, with refresh token rotation.
- Store revocations in master DB so restarts don't re-validate revoked tokens.
- Update `POST /profiles/logout` to revoke the current token (and optionally all tokens for the profile).

**Acceptance criteria:**
- After logout, the same token cannot access protected endpoints.

---

#### P2-6 - Reduce assistant/RAG coupling and hidden global state

**Problems:**
- `src/backend/api/assistant.py` caches a global `_rag_module`, hiding state and complicating test isolation.
- The RAG stack has a deep dependency chain, making it harder to test/replace components.

**Implementation instructions:**
- Replace global caching with an explicit factory/container:
  - Initialize modules in app startup (lifespan) or via a lightweight DI container.
  - Keep per-request state out of module singletons (especially anything tied to `profile_db`).
- Add unit tests that can construct RAG components with fakes/mocks.

**Acceptance criteria:**
- RAG module initialization is deterministic, testable, and does not rely on mutable global state.

---

#### P2-7 - Centralize panel definitions to prevent backend/frontend drift

**Problem:** Panel/analyte mappings are hardcoded in multiple places.

**Implementation instructions (pick one):**
- Backend as source of truth: expose `/observations/panels` returning panel definitions; frontend renders from API.
- Shared types: generate types from OpenAPI and ensure the frontend uses backend-provided panel IDs.

**Acceptance criteria:**
- Panel IDs/names/analyte sets cannot silently diverge between backend and frontend.

---

#### P2-8 - Production hardening defaults (CORS, docs exposure)

**Problems:**
- CORS currently allows all headers.
- `/docs` and `/redoc` are exposed when `DEBUG=true` (ensure production defaults are safe).

**Implementation instructions:**
- Restrict CORS headers to the minimal set required by the frontend (keep dev mode flexible if needed).
- Ensure production docs exposure is disabled by default (already keyed to `DEBUG`, but document and enforce safe defaults in `.env.example`).

**Acceptance criteria:**
- Production defaults do not expose interactive docs or overly broad CORS policies.

---

#### P2-9 - Replace in-memory export summary storage (persistence)

**Problem:** Export summaries are stored in an in-memory dict, which is not durable and can leak data if the process model changes.

**Implementation instructions:**
- Persist summaries in the per-profile DB (encrypted) with TTL/cleanup strategy.
- Alternatively, persist to encrypted filesystem with explicit lifecycle rules.

**Acceptance criteria:**
- Export summaries do not disappear on restart and are stored in the intended secure boundary.

---

#### P2-10 - Close out remaining code quality findings (small fixes batch)

**Partially addressed (2026-02-03):**
- Fixed all frontend lint errors (8 issues):
  - `assistant.spec.ts`: Prefixed unused `request` params with `_`
  - `Input.tsx`: Fixed conditional hook call
  - `ExplainAssistant.tsx`: Removed unused `Citation` import, fixed useEffect dependency
  - `ExportPage.tsx`: Removed unused `ChevronRight`, `Printer` imports
  - `TrendsDashboard.tsx`: Prefixed unused `previousValue` with `_`
  - `export.ts`: Removed unused `useQuery` import

**Still TODO:**
- Remove unused `WeakValueDictionary` import in `profile_database.py`
- Fix `assistant.py` exception handling

**Acceptance criteria:**
- Lint/test passes without suppressions; no obvious "footgun" patterns remain in reviewed areas.

---

### Low Priority Backlog (Do After P0-P2)

These are worthwhile, but should not preempt P0/P1/P2 work:
- Replace `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)` consistently.
- Remove unused imports (`WeakValueDictionary`, unused `asyncio` in model settings if still present).
- Extract duplicated UUID validation utilities into a shared module.
- Fix small frontend robustness issues (undefined array access, unused fetches, error casting).

---

### Handoff Verification Checklist (What to run before declaring "done")

Backend:
```bash
cd src/backend
python -c "from main import app; print('App startup OK')"
python -m pytest -v
```

Frontend:
```bash
cd src/frontend
npm run lint
npm run build
npm test
```

---

*Report generated by parallel audit agents on 2026-02-02*
*Agents: Remediation Verification, Security Audit, Code Quality, Documentation, Architecture*
*Peer-reviewed and corrected: FastAPI DI pattern verified working; SQLCipher provisioning identified as real blocker*
