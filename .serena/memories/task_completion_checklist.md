# Task Completion Checklist

## Before Committing Changes

### Code Quality
- [ ] Run Python formatter: `black .` (from src/backend)
- [ ] Run Python linter: `ruff .`
- [ ] Run type checker: `mypy .`
- [ ] Run tests: `pytest` (ensure no failures)

### Security Review
- [ ] No sensitive data in logs or error messages
- [ ] No hardcoded secrets or API keys
- [ ] Input validation on all user-provided data
- [ ] UUID format validation for ID parameters
- [ ] No path traversal vulnerabilities

### Documentation
- [ ] Docstrings for new functions/classes
- [ ] Update relevant docs/ files if architecture changes
- [ ] Comment complex logic

### Testing
- [ ] Unit tests for new business logic
- [ ] Integration tests for new API endpoints
- [ ] Manual testing of affected features

## After Feature Implementation

### Database Changes
- [ ] Create migration if schema changes (Alembic - TODO: setup required)
- [ ] Test with fresh database

### API Changes
- [ ] Update API documentation
- [ ] Test with frontend integration
- [ ] Verify error responses

### Audit Log
- [ ] Ensure security-relevant actions are logged
- [ ] Use `create_audit_log()` helper (should be centralized)

## Known Issues to Address
1. ✅ FIXED: `models/` directory created with all SQLAlchemy models
2. ✅ FIXED: Document encryption implemented (AES-GCM in ingest.py)
3. ✅ FIXED: DPAPI fallback now fails securely with KeySealingError
4. ⏳ TODO: No authentication/authorization on API endpoints (Phase 2)
5. ✅ FIXED: JWT secret persisted to data/.jwt_secret
6. ✅ FIXED: Centralized audit logging in core/audit.py
7. ✅ FIXED: UUID validation on all API parameters (path traversal protection)
8. ✅ FIXED: Error messages sanitized (no internal path leakage)
