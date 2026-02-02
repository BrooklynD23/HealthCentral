# Next Agent: Complete Repository Audit

## Context

You are taking over the HealthCentral project on branch `Security-Revamp-2`. A security audit and remediation was just completed (commit `3751c76`). Your task is to perform a **complete repository audit** to verify all fixes and identify any remaining issues.

## Previous Work Summary

The following security and quality issues were identified and remediated:

| Issue | Fix Applied | Needs Verification |
|-------|-------------|-------------------|
| FastAPI `Depends()` pattern broken | Changed to `Annotated` type aliases | Import test passed |
| Document encryption disabled | Encryption key now passed to IngestModule | Needs runtime test |
| Decrypt-on-read missing | Created `document_crypto.py` helper | Needs E2E test |
| SQLCipher verification absent | Added `cipher_version` check | Needs runtime test |
| DocumentInbox localStorage bug | Uses `useAuthStore` now | Needs UI test |
| Panel ID mismatch (lipids/lipid) | Changed frontend to `lipid` | Needs API test |
| ESLint config missing | Created `eslint.config.js` | Run `npm run lint` |
| HF download revision pinning | Added `revision` param | Code review only |
| Frontend contract drift | Removed unused `profile_id` params | Needs API test |
| Ruff config missing | Created `pyproject.toml` | Run `ruff check` |

## Your Audit Responsibilities

### 1. Verify Remediation Completeness

**Backend Verification:**
```bash
# 1. Python import test
cd src/backend
python -c "from main import app; print('App startup OK')"

# 2. SQLCipher detection test
python -c "
from core.profile_database import ProfileDatabaseEncryptionError
from core.config import settings
print(f'Encryption required: {settings.database_encryption_required}')
"

# 3. Ruff lint check
ruff check .
black --check .
```

**Frontend Verification:**
```bash
# 1. Install new ESLint deps
cd src/frontend
npm install

# 2. Run lint
npm run lint

# 3. Build test
npm run build
```

**Integration Tests:**
- Document import → encryption → decrypt-on-read roundtrip
- Panel endpoint `/observations/panels/lipid` returns data
- Auth flow with profile database connection

### 2. Comprehensive Security Audit

Scan the entire codebase for:

**Authentication/Authorization:**
- [ ] All API endpoints require authentication
- [ ] Profile isolation enforced (no cross-profile data access)
- [ ] JWT tokens properly validated
- [ ] Session expiration handled

**Data Protection:**
- [ ] PHI encrypted at rest (documents + profile DBs)
- [ ] No plaintext secrets in code or config
- [ ] Audit logging for sensitive operations
- [ ] Secure key management (DPAPI/password-derived)

**Input Validation:**
- [ ] UUID validation on all ID parameters
- [ ] File upload validation (type, size)
- [ ] SQL injection prevention (parameterized queries)
- [ ] Path traversal prevention

**Dependencies:**
- [ ] `npm audit` - check for vulnerable packages
- [ ] `pip-audit` or `safety check` - Python dependencies
- [ ] Outdated dependencies that need updating

### 3. Code Quality Audit

**Backend:**
- [ ] No unused imports or variables
- [ ] Consistent error handling patterns
- [ ] Proper async/await usage
- [ ] Type hints complete
- [ ] Docstrings present

**Frontend:**
- [ ] No React hooks violations
- [ ] Proper TypeScript types (no `any` abuse)
- [ ] Consistent component patterns
- [ ] State management properly scoped

### 4. Architecture Review

- [ ] Separation of concerns maintained
- [ ] No circular dependencies
- [ ] Database migrations up to date
- [ ] API contracts documented
- [ ] Error responses consistent

### 5. Documentation Completeness

- [ ] README accurate and up-to-date
- [ ] API documentation current
- [ ] Setup instructions work
- [ ] Environment variables documented

## Files Changed in Latest Commit

Review these files specifically:

```
src/backend/api/documents.py          # Encryption + decrypt helpers
src/backend/api/model_settings.py     # DI fix + revision pinning
src/backend/core/config.py            # New config option
src/backend/core/profile_database.py  # SQLCipher verification
src/backend/core/document_crypto.py   # NEW - decrypt helper
src/backend/modules/extract.py        # BytesIO support
src/backend/modules/model_selector.py # Revision pinning
src/backend/scripts/model_manager.py  # Revision pinning
src/backend/pyproject.toml            # NEW - ruff config
src/frontend/eslint.config.js         # NEW - ESLint config
src/frontend/package.json             # ESLint deps
src/frontend/src/pages/DocumentInbox.tsx
src/frontend/src/pages/TrendsDashboard.tsx
src/frontend/src/services/documents.ts
src/frontend/src/services/observations.ts
```

## Expected Deliverables

1. **Audit Report** (`docs/full_audit_report_YYYY-MM-DD.md`):
   - Verification results for each remediation item
   - New issues discovered (if any)
   - Risk assessment (P0/P1/P2)
   - Recommended actions

2. **Fix any P0 issues** found during audit

3. **Update documentation** with audit findings

## Key Files to Reference

- `docs/repo_audit_report_2026-02-01.md` - Original audit findings
- `docs/remediation_plan_audit_2026-02-02.md` - Remediation plan + status

## Start Here

```bash
# 1. Check current state
git log --oneline -5
git status

# 2. Run backend tests
cd src/backend
python -m pytest tests/ -v

# 3. Run frontend tests
cd src/frontend
npm test

# 4. Begin systematic audit
```

Good luck with the audit!
