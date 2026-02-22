# HealthCentral Remaining Work Task List

**Version:** 0.4.0
**Last Updated:** 2026-02-21
**Owner:** Project Lead
**Refresh Trigger:** Task completed or new task identified
**Scope:** Active remaining work only (implementation baseline already shipped)

---

## Purpose

This file is the canonical tracker for remaining implementation tasks.
It replaces legacy mixed-status lists and focuses on:

1. Documentation consolidation and drift prevention.
2. Test reliability hardening.
3. Residual product polish work.

---

## Canonical Doc Order

1. `docs/05_backend_integration_status.md` (current API/UI integration baseline)
2. `docs/features/TASK_LIST.md` (this active remaining-work tracker)

---

## Current Baseline Snapshot (2026-02-21)

- Completed baseline areas: auth, import/extract/verify, trends, export, assistant, interpretations, medications, notifications, settings.
- Stabilization sprint (STAB-001 through STAB-007) completed on 2026-02-14.
- Sprint 05 (Frontend Quality & Testing) completed on 2026-02-19: 188 frontend tests, accessibility, responsive layout, visualization interactions, E2E workflows.
- Sprint 06 (Platform Operations & Compliance) completed on 2026-02-21: security middleware (4 classes, 31 tests), monitoring/metrics (23 tests), backup/restore (14 tests), API/user/compliance documentation (14 files).
- Documentation consolidation completed on 2026-02-21: all canonical docs updated, historical docs marked, security report relocated.
- Remaining work: security remediation from Sprint 06 review, deferred feature backlog.

---

## Active Remaining Items (TDD Structured)

| Item ID | Scope | Phase T1 (Red: define failing check first) | Phase T2 (Green: implement minimal fix) | Phase T3 (Refactor/Verify: stabilize + document) | Primary File Targets | Status |
|---------|-------|---------------------------------------------|------------------------------------------|---------------------------------------------------|----------------------|--------|
| `DOC-003` | Automated documentation drift checks | Added baseline drift checks in `scripts/docs_lint.py` for stale markers and contradictory labels. | Implemented executable local entrypoint: `python3 scripts/docs_lint.py`. | Documented rule set in script header and validated passing baseline run. | `scripts/docs_lint.py` (new), `docs/00_architecture_plans_index.md`, `docs/features/TASK_LIST.md` | [x] DONE |
| `DOC-004` | Canonical doc ownership and update policy | Added `_check_canonical_ownership()` lint rule checking for `Owner:` and `Refresh Trigger:` fields. | Added `**Owner:**` and `**Refresh Trigger:**` to all 5 canonical docs. Added cross-links. | Added monthly review cadence section to TASK_LIST.md. | `scripts/docs_lint.py`, `docs/00_architecture_plans_index.md`, `docs/05_backend_integration_status.md`, `docs/features/00_features_index.md`, `docs/features/TASK_LIST.md`, `docs/plans/next-agent-documentation-consolidation.md` | [x] DONE |
| `DOC-005` | Redundant/outdated document handling | Added `_check_historical_inactive_language()` lint rule checking top 15 lines for inactive-tracker phrases. | Updated `remaining-features-implementation.md` banner with "not an active tracker" language. Verified existing banners in other historical docs. | Confirmed all historical docs have pointers to TASK_LIST.md. | `scripts/docs_lint.py`, `docs/plans/remaining-features-implementation.md` | [x] DONE |
| `TEST-001` | Backend test execution reliability | Created `test_bootstrap_check.py` with 3 assertions: pytest importable, TEST_MODE set, production encryption default unchanged. | Updated `conftest.py` with TEST_MODE=1 and DATABASE_ENCRYPTION_REQUIRED=false (test-only). Created `scripts/run-backend-tests.sh` and `.ps1`. | Documented backend test setup in `docs/05_backend_integration_status.md`. | `src/backend/tests/test_bootstrap_check.py`, `src/backend/tests/conftest.py`, `scripts/run-backend-tests.sh`, `scripts/run-backend-tests.ps1`, `docs/05_backend_integration_status.md` | [x] DONE |
| `TEST-002` | Frontend test runner stability | Triaged baseline: 72/72 tests passing. Identified Zustand store leak as isolation risk. | Added store reset in `setup.ts` afterEach. Added `pool: 'forks'` and `testTimeout: 10000` to vitest.config.ts. | Verified 72/72 pass deterministically. Documented stable test command in `src/frontend/README.md`. | `src/frontend/src/__tests__/setup.ts`, `src/frontend/vitest.config.ts`, `src/frontend/README.md` | [x] DONE |
| `UX-001` | Lab/medication correlation polish | Defined `MedicationOverlayPeriod` and `CorrelationContext` types. Created `correlation.ts` utility with `findActiveMedications()`. Wrote 5 contract tests. | Created `MedicationOverlay` component. Wired into TrendsDashboard (medication overlay below chart) and MedicationDetail (Related Lab Results card). | Added 2 overlay tests to TrendsDashboard.test.tsx. Verified 0 TS errors, all tests pass. | `src/frontend/src/services/types.ts`, `src/frontend/src/utils/correlation.ts`, `src/frontend/src/components/MedicationOverlay.tsx`, `src/frontend/src/pages/TrendsDashboard.tsx`, `src/frontend/src/pages/MedicationDetail.tsx`, `src/frontend/src/__tests__/CorrelationContract.test.ts` | [x] DONE |
| `A11Y-001` | Accessibility completion audit | Created `Accessibility.test.tsx` with 7 tests: tablist/tab roles, aria-selected, loading aria-live, form labels, button accessible names. | Added `role="tablist"/"tab"` + `aria-selected` to TrendsDashboard. Added `role="status"` + `aria-live="polite"` to all loading states. Added `aria-pressed` to ExportPage toggles. | Documented audit results in `docs/02_frontend_accessibility_plan.md`. | `src/frontend/src/__tests__/Accessibility.test.tsx`, `src/frontend/src/pages/TrendsDashboard.tsx`, `src/frontend/src/pages/MedicationDetail.tsx`, `src/frontend/src/pages/VerificationWorkbench.tsx`, `src/frontend/src/pages/ExportPage.tsx`, `docs/02_frontend_accessibility_plan.md` | [x] DONE |
| `DOC-006` | API and user-facing docs completion | Added `_check_required_doc_sections()` lint rule with curated REQUIRED_SECTIONS dict. | Added "API Overview" section with endpoint group table to README.md. Fixed broken `implementation_plan/` link. Added `**Last Updated:**` to PRD. | Cross-linked README API Overview to backend integration status. Verified lint passes. | `scripts/docs_lint.py`, `README.md`, `docs/features/03_features_prd.md` | [x] DONE |

The items above represent v0.3.0 hardening (completed 2026-02-12). The stabilization sprint below addresses production-readiness gaps identified 2026-02-14.

Reference plan: `docs/plans/sprint-phase-2026-02-13-implementation-plan.md`

---

## Sprint 2026-02-14: Stabilization Items (Completed)

| Item ID | Scope | Phase T1 (Red: define failing check first) | Phase T2 (Green: implement minimal fix) | Phase T3 (Refactor/Verify: stabilize + document) | Primary File Targets | Status |
|---------|-------|---------------------------------------------|------------------------------------------|---------------------------------------------------|----------------------|--------|
| `STAB-001` | OCR graceful degradation | Importing scanned PDF with OCR unavailable must return 200 with `pending_ocr`, not 500 RuntimeError. | Replaced RuntimeError in `extract_from_scanned_pdf()` and `extract_from_image()` with graceful `ExtractionResult(ocr_unavailable=True)`. Updated `documents.py` precheck to use `is_ocr_available()`. Added "OCR Required" badge in `DocumentInbox.tsx`. | Verified no RuntimeError can propagate from OCR extraction methods. Frontend shows distinct badge for `pending_ocr` documents. | `src/backend/modules/extract.py`, `src/backend/api/documents.py`, `src/frontend/src/pages/DocumentInbox.tsx`, `src/backend/core/config.py` | [x] DONE |
| `STAB-002` | Extraction silent-failure logging | `grep "except.*ValueError" extract.py` must show no bare `pass` blocks. | Added `import logging` and `logger = logging.getLogger(__name__)` to `extract.py`. Replaced all `pass` in except blocks with `logger.warning()` calls including `analyte`, `page_num`, and raw value context. | Functional behavior unchanged (parsed value stays None). Warning logs emitted for debugging. | `src/backend/modules/extract.py` | [x] DONE |
| `STAB-003` | Config startup validation | `validate_startup()` must raise RuntimeError if `app_env == "production"` and `jwt_secret` is empty. `is_ocr_available()` must return False when tesseract not installed. | Added `validate_startup()` method to Settings class and `is_ocr_available()` standalone function in `config.py`. Called validation in `main.py` lifespan. Created `test_config_validation.py` with 9 test cases. | App starts normally in dev mode with no tesseract (warning only). Production hard-fails without JWT secret. | `src/backend/core/config.py`, `src/backend/main.py`, `src/backend/tests/test_config_validation.py` | [x] DONE |
| `STAB-004` | CORS allow_headers hardening | `grep 'allow_headers' main.py` must not contain `"*"`. | Replaced `allow_headers=["*"]` with explicit `["Authorization", "Content-Type", "Accept", "X-Requested-With"]` in `main.py`. | Verified frontend `api.ts` only sends Authorization and Content-Type headers. | `src/backend/main.py` | [x] DONE |
| `STAB-005` | Assistant fallback determinism | No `NotImplementedError` used for model-unavailable signaling. `assistant.py` must catch `ModelUnavailableError` specifically. | Defined `ModelUnavailableError(Exception)` in `rag.py`. Replaced both `NotImplementedError` raises with `ModelUnavailableError`. Updated `assistant.py` catch clause. | `/api/v1/assistant/chat` with no model returns 200 knowledge-based fallback (not 500/501). Same fallback behavior, explicit exception type. | `src/backend/modules/rag.py`, `src/backend/api/assistant.py` | [x] DONE |
| `STAB-006` | E2E smoke suite + CI job | 2 new E2E spec files with 9 combined tests. Playwright config starts both backend and frontend. CI has `e2e-tests` job gated on both `frontend-tests` and `backend-tests`. | Created `document-import.spec.ts` (5 tests) and `settings-smoke.spec.ts` (4 tests). Updated `playwright.config.ts` with dual webServer array. Added `e2e-tests` job to `ci.yml`. Renamed E2E-RAG-002 from "501 error" to "no-model fallback". | All existing E2E tests still valid. No test requires real LLM model. CI pipeline has 4 jobs. | `src/frontend/e2e/document-import.spec.ts`, `src/frontend/e2e/settings-smoke.spec.ts`, `src/frontend/playwright.config.ts`, `.github/workflows/ci.yml`, `src/frontend/e2e/assistant.spec.ts` | [x] DONE |
| `STAB-007` | Governance reconciliation | TASK_LIST.md must have STAB-001 through STAB-007 as active rows with Red/Green/Refactor columns. v0.3.0 items preserved with clear scope label. | Added stabilization sprint section to TASK_LIST.md with TDD-structured rows. Updated architecture index. | `python3 scripts/docs_lint.py` passes. No doc claims "all complete" while active items exist. | `docs/features/TASK_LIST.md`, `docs/00_architecture_plans_index.md` | [x] DONE |

---

## Recommended Execution Order

### v0.3.0 (completed)
1. `DOC-003`
2. `DOC-004`
3. `DOC-005`
4. `TEST-001`
5. `TEST-002`
6. `UX-001`
7. `A11Y-001`
8. `DOC-006`

### Stabilization Sprint (2026-02-14)
1. `STAB-004` + `STAB-002` (parallel)
2. `STAB-003`
3. `STAB-001` + `STAB-005` (parallel)
4. `STAB-006`
5. `STAB-007`

---

## Monthly Review Cadence

On the first of each month, review all canonical docs for freshness:

1. Check each doc's `**Last Updated:**` field — if stale (>60 days), flag for update or archival.
2. Verify `**Owner:**` is still the correct responsible party.
3. Confirm `**Refresh Trigger:**` conditions haven't occurred without a doc update.
4. Run `python3 scripts/docs_lint.py` to catch any drift.
5. Update this section's "Last cadence review" date below.

**Last cadence review:** 2026-02-21

---

## Definition of Done For This Tracker

- Every active item has a Red/Green/Refactor phase explicitly logged.
- No canonical docs conflict on current implementation status.
- Historical docs are clearly marked and linked back to active tracker.
- Test commands for backend/frontend execute deterministically in the documented environment.

---

## Session Notes

### 2026-02-12 - Documentation Drift Consolidation Pass

- Updated canonical documentation index and feature index to current-state language.
- Corrected backend integration status drift (`assistant/chat` fallback behavior, OCR wording).
- Marked superseded plan files as historical references.
- Replaced this task list with remaining-work-only phased tracker.

### 2026-02-12 - DOC-003 Baseline Lint Implemented

- Added `scripts/docs_lint.py` with deterministic documentation drift rules.
- Rules include canonical `Last Updated` checks, historical banner checks, stale marker checks, and TDD phase coverage checks for active task rows.
- Verified with `python3 scripts/docs_lint.py` (pass).

### 2026-02-12 - Hardening Plan v2 Complete (DOC-004 through DOC-006, TEST-001/002, UX-001, A11Y-001)

- **DOC-004**: Added `Owner` + `Refresh Trigger` fields to all 5 canonical docs. Added lint rule `_check_canonical_ownership()`. Added monthly review cadence section.
- **DOC-005**: Added inactive-tracker language lint rule `_check_historical_inactive_language()`. Updated `remaining-features-implementation.md` banner.
- **TEST-001**: Created `test_bootstrap_check.py` (3 assertions), updated `conftest.py` with test-only env vars, created `run-backend-tests.sh` and `.ps1`.
- **TEST-002**: Added Zustand store reset in `setup.ts` afterEach. Added `pool: 'forks'` + `testTimeout: 10000` to vitest.config.ts. 86/86 tests pass deterministically.
- **UX-001**: Built frontend-only medication-observation correlation: types, `correlation.ts` utility, `MedicationOverlay` component, wired into TrendsDashboard and MedicationDetail with Related Lab Results card. 5 contract tests + 2 overlay tests.
- **A11Y-001**: Added ARIA roles (`tablist`/`tab`/`aria-selected`), `aria-live` loading announcements, `aria-pressed` on toggles. 7 accessibility tests. Documented audit results in accessibility plan.
- **DOC-006**: Added `_check_required_doc_sections()` lint rule. Added API Overview table to README.md. Fixed broken link. Added `Last Updated` to PRD.
- **CI Gates**: Created `.github/workflows/ci.yml` with 3 jobs: docs-lint, backend-tests, frontend-tests.
- **Verification**: `python3 scripts/docs_lint.py` → pass. `npx tsc --noEmit` → 0 errors. `npx vitest run` → 86/86 pass.

### 2026-02-21 - Sprint 06 + Documentation Consolidation

- **Sprint 06 implementation** on `sprint/06-platform-compliance` (6 commits, 39 new files, 68 tests, 4163 lines):
  - OPS-003: Security middleware (InputValidation, RateLimit, SecurityHeaders, SecurityAudit) + CI security-scan job.
  - OPS-001: Monitoring (MetricsCollector, CorrelationId, Timing, enhanced /health).
  - OPS-002: Backup utility (sqlite3.backup API, SHA-256 verify, restore with .bak safety, prune).
  - OPS-004/005/006: API docs, user docs, compliance docs (14 files total).
- **Documentation consolidation**:
  - Moved `next-agent-documentation-consolidation.md` from canonical to historical (all work packages done).
  - Added `sprint-phase-2026-02-13-implementation-plan.md` to historical list in docs_lint.py.
  - Relocated `security_best_practices_report.md` from repo root to `docs/compliance/security-review-sprint06.md`.
  - Marked `sprint-06-handoff-prompt.md` as historical.
  - Updated architecture index, backend integration status, features index, TASK_LIST, README with Sprint 06 completions.
  - Updated `implementation_plan/README.md` sprint progress table.
- **Verification**: `python3 scripts/docs_lint.py` → pass. `npx tsc --noEmit` → 0 errors. `npm run lint` → clean.

### 2026-02-14 - Stabilization Sprint (STAB-001 through STAB-007)

- **STAB-004**: Replaced `allow_headers=["*"]` with explicit header list in `main.py`.
- **STAB-002**: Added `logging.getLogger(__name__)` to `extract.py`. Replaced all silent `pass` blocks in except handlers with `logger.warning()` calls.
- **STAB-003**: Added `validate_startup()` method and `is_ocr_available()` function to `config.py`. Called in `main.py` lifespan. Created `test_config_validation.py` with 9 tests.
- **STAB-001**: Replaced `RuntimeError` in OCR extraction methods with graceful `ExtractionResult(ocr_unavailable=True)`. Updated `documents.py` to use `is_ocr_available()`. Added "OCR Required" badge to `DocumentInbox.tsx`.
- **STAB-005**: Defined `ModelUnavailableError` in `rag.py`. Replaced `NotImplementedError` at both raise sites. Updated `assistant.py` catch clause.
- **STAB-006**: Created `document-import.spec.ts` (5 tests) and `settings-smoke.spec.ts` (4 tests). Updated `playwright.config.ts` with dual webServer. Added `e2e-tests` CI job. Renamed E2E-RAG-002.
- **STAB-007**: Added stabilization sprint section to TASK_LIST.md with TDD-structured rows. Updated architecture index.
- **CI Gates (updated)**: CI now has 4 jobs: docs-lint, backend-tests, frontend-tests, and e2e-tests.
