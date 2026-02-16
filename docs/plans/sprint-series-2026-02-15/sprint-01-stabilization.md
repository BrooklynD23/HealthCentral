# Sprint 01 - Stabilization

**Sprint ID:** HC-S01-STAB
**Priority:** Immediate
**Source Items:** STAB-001 through STAB-007

## Architecture Scope

- Backend extraction pipeline (`documents.py` -> `extract.py`) must degrade gracefully when OCR is unavailable.
- Startup configuration (`config.py` + `main.py`) must fail fast for production-critical misconfiguration.
- Assistant fallback path (`assistant.py` + `rag.py`) must use deterministic domain-specific exception signaling.
- Delivery guardrails must include CI-driven smoke E2E coverage and governance docs consistency.

## Work Packages

### STAB-001 OCR Graceful Degradation

- Backend files:
  - `src/backend/modules/extract.py`
  - `src/backend/api/documents.py`
  - `src/backend/core/config.py`
- Frontend files:
  - `src/frontend/src/pages/DocumentInbox.tsx`
- Implementation:
  - Replace OCR dependency RuntimeError paths with `ExtractionResult(ocr_unavailable=True)`.
  - Add OCR availability precheck before extraction request execution.
  - Render explicit "OCR Required" badge for `pending_ocr` documents.
- Acceptance checks:
  - Missing OCR dependency no longer returns 500 for import endpoints.
  - Frontend visually distinguishes OCR-pending documents.

### STAB-002 Extraction Silent-Failure Logging

- Backend files:
  - `src/backend/modules/extract.py`
- Implementation:
  - Add module logger.
  - Replace `pass` in parsing exceptions with contextual warning logs.
  - Preserve data semantics: unparseable value remains `None`.
- Acceptance checks:
  - No bare `pass` left in ValueError extraction parse handlers.
  - Logs include analyte/raw value/page context.

### STAB-003 Config Startup Validation

- Backend files:
  - `src/backend/core/config.py`
  - `src/backend/main.py`
  - `src/backend/tests/test_config_validation.py`
- Implementation:
  - Add `validate_startup()` on settings object.
  - Add standalone `is_ocr_available()` helper.
  - Enforce production hard-fail for missing JWT secret.
  - Maintain non-production startup behavior with actionable warnings.
- Acceptance checks:
  - 9 config-validation tests pass.
  - Production boot fails without JWT secret.

### STAB-004 CORS Allow-Headers Hardening

- Backend files:
  - `src/backend/main.py`
- Implementation:
  - Replace wildcard headers with explicit list:
    - `Authorization`
    - `Content-Type`
    - `Accept`
    - `X-Requested-With`
- Acceptance checks:
  - No `allow_headers=["*"]` usage in backend app boot path.

### STAB-005 Assistant Fallback Determinism

- Backend files:
  - `src/backend/modules/rag.py`
  - `src/backend/api/assistant.py`
- Implementation:
  - Add `ModelUnavailableError` exception type.
  - Replace model-unavailable `NotImplementedError` raises.
  - Catch `ModelUnavailableError` in assistant API and return stable fallback response.
- Acceptance checks:
  - No model-unavailable `NotImplementedError` remains.
  - Assistant endpoint returns fallback response contract consistently.

### STAB-006 E2E Smoke Suite and CI Job

- Frontend and CI files:
  - `src/frontend/e2e/document-import.spec.ts`
  - `src/frontend/e2e/settings-smoke.spec.ts`
  - `src/frontend/playwright.config.ts`
  - `.github/workflows/ci.yml`
  - `src/frontend/e2e/assistant.spec.ts`
- Implementation:
  - Add two smoke specs (5 + 4 tests).
  - Configure Playwright with dual `webServer` entries for frontend and backend.
  - Add `e2e-tests` CI job.
  - Update E2E-RAG-002 wording to no-model fallback behavior.
- Acceptance checks:
  - E2E job runs in CI and is gated by backend/frontend test jobs.

### STAB-007 Governance Reconciliation

- Documentation files:
  - `docs/features/TASK_LIST.md`
  - `docs/00_architecture_plans_index.md`
- Implementation:
  - Add stabilization sprint entries with explicit Red/Green/Refactor details.
  - Align architecture index pointers to active trackers.
- Acceptance checks:
  - `python3 scripts/docs_lint.py` passes.

## Handoff Notes

If any STAB item is already implemented in code, the implementation agent should treat this sprint as a verification and regression-proofing pass rather than a net-new build.
