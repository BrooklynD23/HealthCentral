# Security Remediation Follow-Up Plan

## Requirements Restatement

Four follow-up items remain after the main Sprint 06 security remediation:

1. **SEC-006 incomplete**: `validate_startup()` forces `debug=False` in production, but `create_app()` already read `settings.debug` *before* lifespan runs — so `/docs` and `/redoc` are still exposed and `uvicorn.run(reload=True)` still fires.
2. **Upload multipart overhead**: `max_upload_bytes = max_import_file_size_mb * 1024 * 1024` doesn't account for multipart framing, so a file exactly at the 50 MB limit gets rejected.
3. **Docs drift**: `docs/user/troubleshooting.md` and `docs/05_backend_integration_status.md` still reference old `/health` behavior (metrics summary) and show unauthenticated `curl` for metrics.
4. **Nits**: unused `from unittest.mock import patch` at top of `test_security_remediation.py:9`; stale docstring in `test_input_validator.py:161`.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Moving `validate_startup()` before `create_app()` could change error handling | Medium | Keep it in lifespan for JWT check; only move debug override earlier |
| Multipart overhead cushion could allow slightly larger-than-intended uploads | Low | 5% cushion is well within safe range |
| None of these changes affect runtime logic beyond SEC-006 | Low | Straightforward edits |

## Implementation Phases

### Phase 1 — Fix SEC-006 properly (main.py + config.py)

**Problem**: `create_app()` at line 54-55 reads `settings.debug` to decide `docs_url`/`redoc_url`. `validate_startup()` runs later inside `lifespan()`. Similarly `__main__` reads `settings.debug` for `reload=` at line 132.

**Fix**:
1. In `src/backend/core/config.py`, move the production debug guard *out* of `validate_startup()` and into an **eagerly-called** property or post-init hook. Specifically, add it as a `model_post_init` override on the `Settings` class so it fires at construction time (line 179: `settings = Settings()` triggers it). This ensures `settings.debug` is already `False` before `create_app()` reads it.
2. In `src/backend/main.py`, no changes needed — `create_app()` will now see the corrected `debug` value.
3. Update the existing SEC-006 test to verify the behavior fires at construction, not at `validate_startup()` time.

**Files**: `src/backend/core/config.py`, `src/backend/tests/security/test_security_remediation.py`

### Phase 2 — Add multipart overhead cushion (input_validator.py)

**Problem**: `max_upload_bytes = max_import_file_size_mb * 1024 * 1024` is exact. A 50 MB file + multipart boundary framing (~1-4 KB overhead per part) exceeds this.

**Fix**:
1. In `src/backend/security/input_validator.py:41`, add a 5% cushion:
   ```python
   self.max_upload_bytes = int(app_settings.max_import_file_size_mb * 1024 * 1024 * 1.05)
   ```
2. Update the SEC-002 test to account for the cushion.

**Files**: `src/backend/security/input_validator.py`, `src/backend/tests/security/test_security_remediation.py`

### Phase 3 — Fix docs drift (2 doc files)

**File `docs/user/troubleshooting.md`**:
- Line 55: Change `Check /health endpoint for metrics summary` → `Check /health endpoint for status`
- Lines 98-101: Update the curl example to show the new slim response; remove "metrics summary" wording
- Lines 105-106: Add `Authorization: Bearer <token>` to the metrics curl example

**File `docs/05_backend_integration_status.md`**:
- Line 21: Remove "enhanced `/health` with metrics summary" → "lightweight `/health` liveness probe"
- Line 136: Change description from "Health check with optional metrics summary (no auth)" → "Liveness probe (status, mode, version only)"
- Line 137: Add "(auth required)" to metrics description
- Lines 341-344: Mark SEC-001 through SEC-004 as done (they're currently listed as TODO)

**Files**: `docs/user/troubleshooting.md`, `docs/05_backend_integration_status.md`

### Phase 4 — Nit fixes (2 test files)

1. `src/backend/tests/security/test_security_remediation.py:9`: Remove unused `from unittest.mock import patch` top-level import (it's imported locally in the one test that uses it).
2. `src/backend/tests/security/test_input_validator.py:161`: Update docstring from "bypasses body size limit" → "uses a larger upload limit".

**Files**: `src/backend/tests/security/test_security_remediation.py`, `src/backend/tests/security/test_input_validator.py`

## Files to Modify

| File | Phase | Change |
|------|-------|--------|
| `src/backend/core/config.py` | 1 | Move debug guard to `model_post_init` |
| `src/backend/security/input_validator.py` | 2 | Add 5% multipart cushion |
| `docs/user/troubleshooting.md` | 3 | Update /health and metrics references |
| `docs/05_backend_integration_status.md` | 3 | Update endpoint descriptions, mark SEC items done |
| `src/backend/tests/security/test_security_remediation.py` | 1,2,4 | Fix SEC-006 test + remove unused import |
| `src/backend/tests/security/test_input_validator.py` | 4 | Fix stale docstring |

## Estimated Complexity: Low

All changes are small, targeted edits — no new files, no architectural changes. ~30 minutes.
