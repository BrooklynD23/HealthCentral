# HealthCentral Sprint Phase Plan - 2026-02-13

**Last Updated:** 2026-02-14  
**Owner:** Project Lead  
**Refresh Trigger:** Ticket status change, scope change, or dependency change  
**Status:** Historical planning reference (superseded by 2026-02-14 stabilization execution)

> Historical Reference: this planning draft is retained for sprint history.
> Implemented stabilization outcomes are tracked in `docs/features/TASK_LIST.md`.

## Purpose

This document captures the detailed ticket findings for the next sprint phase (dated 2026-02-13) and includes an audit of sprint structure with implementation recommendations.

## Scope Snapshot

- `Major` tickets: 3
- `Minor` tickets: 5
- `Feature` requests: 3
- Total estimated effort: 34 to 51 engineering days (see audit section)

## Major Tickets

### MAJOR-001: OCR Integration Missing System Dependencies

- Priority: Major
- Estimated Effort: 3 to 5 days
- Primary Files:
  - `src/backend/modules/extract.py` (lines 448-452, 514-518)
  - `src/backend/core/config.py` (add OCR config section)
  - `src/backend/requirements.txt` (lines 30-35)
  - `docs/05_backend_integration_status.md` (update OCR status)

Description:
OCR methods `extract_from_scanned_pdf()` and `extract_from_image()` exist in `extract.py`, but raise `RuntimeError` when dependencies are missing. Dependency packages are listed in `requirements.txt`, but system-level validation is missing.

Reasoning:
- Impact: Users cannot process scanned PDFs without manual system package installation.
- Risk: `RuntimeError` can crash the import pipeline rather than degrade gracefully.
- User Experience: No clear guidance when OCR is unavailable.
- Code Quality: Graceful fallback is preferable to application crashes.

Detailed Tasks:
1. System Dependency Validation (`src/backend/core/config.py`)
   - Add `ocr_enabled: bool = False` config flag.
   - Add `validate_ocr_dependencies()` function.
   - Check for `tesseract` system binary on startup.
   - Log warnings when OCR dependencies are missing.
2. Graceful Error Handling (`src/backend/modules/extract.py`)
   - Replace `RuntimeError` with warning logs and empty results.
   - Add `is_ocr_available()` helper.
   - Return `ExtractionResult` with `ocr_unavailable: True`.
   - Apply confidence penalty for OCR-unavailable documents.
3. Frontend Integration (`src/frontend/src/pages/DocumentInbox.tsx`)
   - Add OCR status indicator.
   - Show user-helpful message when OCR is unavailable.
   - Provide setup instructions link.
4. Documentation Updates (`docs/05_backend_integration_status.md`)
   - Update OCR implementation status.
   - Add system dependency installation guide.
   - Document configuration options.

### MAJOR-002: Local LLM Model Management Gap

- Priority: Major
- Estimated Effort: 4 to 6 days
- Primary Files:
  - `src/backend/modules/rag.py` (lines 496-500, 872-876)
  - `src/backend/api/assistant.py` (lines 257-259)
  - `src/backend/modules/model_selector.py` (extend functionality)
  - `src/frontend/src/pages/SettingsPage.tsx` (add model management)
  - `src/frontend/src/services/modelSettings.ts` (add management hooks)

Description:
RAG assistant currently throws `NotImplementedError` when no local LLM model is available, forcing manual GGUF download/setup. There is a knowledge-base fallback path, but users get minimal setup guidance. Existing model detection logic in `model_selector.py` is not fully integrated into assistant workflow.

Reasoning:
- Critical Feature: Assistant is core MVP functionality.
- User Friction: Manual model setup is technical and error-prone.
- Existing Infrastructure: Hardware/model detection already exists but is under-connected.
- Competitive Gap: Comparable products provide guided model management.

Detailed Tasks:
1. Model Download Integration (`src/backend/modules/model_selector.py`)
   - Add `download_default_model()` method.
   - Integrate with `hardware_detection.py`.
   - Add progress tracking and resume support.
   - Validate model integrity after download.
2. Assistant Error Handling (`src/backend/modules/rag.py`)
   - Replace `NotImplementedError` with structured error responses.
   - Add model availability status endpoint.
   - Implement progressive loading with status updates.
   - Add setup guidance in user-facing error messages.
3. Frontend Model Management (`src/frontend/src/pages/SettingsPage.tsx`)
   - Add model download progress UI.
   - Show available models and disk usage.
   - Add deletion and model management controls.
   - Display setup status and system requirements.
4. API Extensions (`src/backend/api/model_settings.py`)
   - Add `/model/download` endpoint with progress tracking.
   - Add `/model/available` endpoint for model catalog.
   - Add `/model/setup-guide` endpoint for setup guidance.

### MAJOR-003: Missing E2E Test Coverage

- Priority: Major
- Estimated Effort: 5 to 7 days
- Primary Files:
  - `src/frontend/e2e/` (add test files)
  - `src/frontend/playwright.config.ts` (extend configuration)
  - `scripts/run-e2e-tests.sh` (create test runner)
  - `src/backend/tests/fixtures/` (add test data)

Description:
Unit/component tests exist, but E2E coverage is currently limited to two specs (`auth.spec.ts`, `assistant.spec.ts`). Core workflows are not validated end-to-end.

Reasoning:
- Risk: Integration regressions can ship undetected.
- Quality: E2E tests catch cross-layer issues unit tests miss.
- CI/CD: Regression testing coverage is incomplete.
- User Journey: Core workflows require full-path validation.

Detailed Tasks:
1. Core Workflow Tests (`src/frontend/e2e/document-workflow.spec.ts`)
   - Test document import pipeline end-to-end.
   - Test observation verification workflow.
   - Test trends visualization with real data.
   - Test export functionality (CSV/JSON/summary).
2. OCR Workflow Tests (`src/frontend/e2e/ocr-workflow.spec.ts`)
   - Test scanned PDF import (conditional on OCR availability).
   - Test image import behavior.
   - Test graceful OCR error handling.
   - Test confidence scoring for OCR results.
3. Model Management Tests (`src/frontend/e2e/model-management.spec.ts`)
   - Test model download/setup path.
   - Test assistant interaction with local model.
   - Test fallback behavior with unavailable model.
   - Test model switching and management.
4. Test Infrastructure (`scripts/run-e2e-tests.sh`)
   - Create cross-platform E2E runner.
   - Add test data setup and cleanup.
   - Add conditional test execution by system capability.
   - Integrate into existing CI/CD workflow.

## Minor Tickets

### MINOR-001: Incomplete Error Handling in Extraction

- Priority: Minor
- Estimated Effort: 1 to 2 days
- Primary Files:
  - `src/backend/modules/extract.py` (lines 267-269, 281-284, 408-411)
  - `src/backend/tests/test_extraction_pipeline.py` (add error case tests)

Description:
Table extraction uses `pass` when `ValueError` occurs during float parsing. Parsing failures are silently ignored without logs or metrics.

Reasoning:
- Data Quality: Silent failures can hide data loss.
- Debugging: No visibility into parse failures.
- Metrics: No extraction success/failure tracking.
- Maintainability: Harder troubleshooting during regressions.

Detailed Tasks:
1. Error Logging (`src/backend/modules/extract.py`)
   - Replace `pass` with `logger.warning()` calls.
   - Add structured context (line number, value, document).
   - Add extraction metrics collection.
   - Add error categorization (`parse_error`, `format_error`, etc.).
2. Confidence Scoring (`src/backend/modules/extract.py`)
   - Adjust confidence based on parsing failures.
   - Include parse-failure count in confidence calculation.
   - Add minimum confidence thresholds for auto-verification.
3. Test Coverage (`src/backend/tests/test_extraction_pipeline.py`)
   - Add malformed table-data tests.
   - Add parsing error scenario tests.
   - Add confidence scoring edge-case tests.

### MINOR-002: Missing Test Coverage for Glossary Module

- Priority: Minor
- Estimated Effort: 1 to 2 days
- Primary Files:
  - `src/backend/tests/test_glossary.py` (new)
  - `src/backend/modules/glossary.py` (test helpers as needed)

Description:
`glossary.py` is used by assistant APIs but has no unit test coverage.

Reasoning:
- Core Functionality: Glossary directly affects assistant responses.
- Data Quality: Definitions and related-term behavior need regression safety.
- Performance: Lookup behavior should be validated for larger data.
- Regression: Prevent accidental glossary/data format breakage.

Detailed Tasks:
1. Unit Tests (`src/backend/tests/test_glossary.py`)
   - Test term lookup behavior.
   - Test case-insensitive search.
   - Test related terms retrieval.
   - Test definition validation/formatting.
2. Edge Cases (`src/backend/tests/test_glossary.py`)
   - Missing term handling.
   - Malformed input handling.
   - Duplicate term handling.
   - Special character handling.
3. Performance Tests (`src/backend/tests/test_glossary.py`)
   - Lookup performance for large glossary sets.
   - Memory usage behavior.
   - Concurrent access patterns.

### MINOR-003: Frontend Type Safety Gaps

- Priority: Minor
- Estimated Effort: 2 to 3 days
- Primary Files:
  - `src/frontend/src/services/types.ts` (extend definitions)
  - `src/frontend/src/__tests__/types.test.ts` (type validation tests)

Description:
Some API responses and optional fields are not fully typed, especially around error payloads.

Reasoning:
- Type Safety: Catch errors at compile time.
- Developer Experience: Better IDE inference/autocomplete.
- Maintenance: Safer refactors.
- Runtime Safety: Reduced null/undefined runtime failures.

Detailed Tasks:
1. Complete Type Definitions (`src/frontend/src/services/types.ts`)
   - Add missing API response types.
   - Add error response interfaces.
   - Add optional field typing for all models.
   - Add request/response validation types.
2. Error Type Safety (`src/frontend/src/services/types.ts`)
   - Add structured error response types.
   - Add HTTP error code mapping.
   - Add validation error types.
   - Add network error types.
3. Type Validation Tests (`src/frontend/src/__tests__/types.test.ts`)
   - Add type guard tests.
   - Add runtime type validation.
   - Add mock data type-compliance tests.

### MINOR-004: Configuration Validation Missing

- Priority: Minor
- Estimated Effort: 1 to 2 days
- Primary Files:
  - `src/backend/core/config.py` (validation methods)
  - `src/backend/tests/test_config_validation.py` (new)

Description:
Configuration values are loaded without complete validation, increasing runtime-failure risk from invalid/missing settings.

Reasoning:
- Startup Reliability: Fail fast with clear errors.
- Deployment Safety: Prevent invalid production config.
- Debugging: Faster issue diagnosis.
- Documentation: Validation acts as living config contract.

Detailed Tasks:
1. Validation Methods (`src/backend/core/config.py`)
   - Add `validate_database_config()`.
   - Add `validate_model_paths()`.
   - Add `validate_ocr_config()`.
   - Add `validate_external_apis()`.
2. Startup Validation (`src/backend/main.py`)
   - Add startup config validation.
   - Provide fix-oriented error messages.
   - Add configuration health-check endpoint.
3. Test Coverage (`src/backend/tests/test_config_validation.py`)
   - Valid configuration scenarios.
   - Invalid configuration handling.
   - Missing configuration defaults.
   - Edge-case coverage.

### MINOR-005: Accessibility Improvements Needed

- Priority: Minor
- Estimated Effort: 2 to 3 days
- Primary Files:
  - `src/frontend/src/pages/VerificationWorkbench.tsx`
  - `src/frontend/src/pages/TrendsDashboard.tsx`
  - `src/frontend/src/pages/MedicationDetail.tsx`
  - `src/frontend/src/__tests__/Accessibility.test.tsx` (extend)

Description:
Baseline accessibility exists, but some forms still need complete ARIA labeling and stronger keyboard-navigation behavior.

Reasoning:
- Inclusivity: Better usability for users with disabilities.
- Compliance: Improve standards alignment.
- User Experience: Keyboard improvements benefit all users.
- Quality: Close out accessibility debt.

Detailed Tasks:
1. Form Accessibility
   - Add missing ARIA labels.
   - Add validation announcements.
   - Add field descriptions/help text.
   - Improve error-message association.
2. Keyboard Navigation
   - Ensure full keyboard operability.
   - Improve tab-order management.
   - Add modal focus trapping.
   - Add keyboard shortcuts for common actions.
3. Screen Reader Support
   - Add live regions for dynamic updates.
   - Ensure proper heading hierarchy.
   - Add landmark roles.
   - Ensure table header semantics.
4. Accessibility Testing (`src/frontend/src/__tests__/Accessibility.test.tsx`)
   - Add automated accessibility tests.
   - Test keyboard flow behavior.
   - Test screen-reader compatibility.
   - Add color contrast validation.

## Feature Requests

### FEATURE-001: Advanced Export Formats

- Priority: Feature
- Estimated Effort: 5 to 7 days
- Primary Files:
  - `src/backend/modules/export.py`
  - `src/backend/api/export.py`
  - `src/frontend/src/pages/ExportPage.tsx`
  - `src/backend/tests/test_export_api.py`

Description:
Current export supports CSV/JSON and doctor summary. Additional formats (PDF, Excel, HL7 FHIR) are requested for broader use cases.

Reasoning:
- User Needs: Different stakeholders require different formats.
- Interoperability: FHIR enables healthcare-system exchange.
- Professional Use: Excel/PDF support analysis and sharing.
- Product Competitiveness: Multi-format export is expected.

Detailed Tasks:
1. PDF Export (`src/backend/modules/export.py`)
   - Use `weasyprint` for PDF generation.
   - Include charts/visualizations.
   - Support report templates.
   - Add styling/branding options.
2. Excel Export (`src/backend/modules/export.py`)
   - Add `openpyxl` support.
   - Multi-sheet workbook output.
   - Add charts/formatting.
   - Add formulas and data validation.
3. HL7 FHIR Export (`src/backend/modules/export.py`)
   - Map observations to FHIR resources.
   - Export patient data in FHIR format.
   - Add integration support for external systems.
   - Validate FHIR compliance.

### FEATURE-002: Enhanced Search Functionality

- Priority: Feature
- Estimated Effort: 4 to 6 days
- Primary Files:
  - `src/backend/modules/search.py` (new)
  - `src/backend/api/search.py` (new)
  - `src/frontend/src/pages/SearchPage.tsx` (new)
  - `src/frontend/src/components/SearchResults.tsx` (new)

Description:
Current search behavior is limited. Requested capabilities include full-text, semantic search, and saved-search workflows.

Reasoning:
- User Experience: Better discovery for user data.
- Data Utilization: Leverage existing embeddings for semantic retrieval.
- Productivity: Saved searches and filter controls.
- Product Expectations: Modern search behavior.

Detailed Tasks:
1. Full-Text Search (`src/backend/modules/search.py`)
   - Add document indexing.
   - Add result highlighting.
   - Add ranking/relevance behavior.
   - Add pagination.
2. Semantic Search (`src/backend/modules/search.py`)
   - Reuse embeddings for similarity search.
   - Implement hybrid search (text + semantic).
   - Add search-result explanation text.
   - Optimize query performance.
3. Search UI (`src/frontend/src/pages/SearchPage.tsx`)
   - Build advanced search interface.
   - Add filters/facets.
   - Add saved searches.
   - Add recent/search-history behavior.

### FEATURE-003: Data Import from Other Sources

- Priority: Feature
- Estimated Effort: 6 to 8 days
- Primary Files:
  - `src/backend/modules/import.py` (extend)
  - `src/backend/api/import.py` (extend)
  - `src/frontend/src/pages/ImportPage.tsx` (extend)
  - `src/backend/tests/test_import_apis.py` (new)

Description:
Current import supports PDFs/images. Requested expansion includes health-app/lab-provider/patient-portal imports.

Reasoning:
- Data Aggregation: Consolidate health data sources.
- Convenience: Reduce manual entry.
- Integration: Connect to widely used platforms.
- Market Demand: Multi-source import is common.

Detailed Tasks:
1. Health App Imports (`src/backend/modules/import.py`)
   - Add Apple Health CSV parser.
   - Add Google Fit JSON parser.
   - Add generic CSV mapping flow.
   - Add validation and error handling.
2. Lab Provider Imports (`src/backend/modules/import.py`)
   - Add Quest parser.
   - Add LabCorp parser.
   - Add HL7 v2 lab-data import support.
   - Add provider-specific format handling.
3. Patient Portal Imports (`src/backend/modules/import.py`)
   - Add generic portal import path.
   - Add portal adapters where possible.
   - Add OAuth integration for healthcare APIs.
   - Add import scheduling/automation.

## Sprint Structure Audit and Recommendations (2026-02-14)

### 1. Capacity and Scope Audit

- Current proposed scope totals approximately 34 to 51 engineering days:
  - Major: 12 to 18 days.
  - Minor: 7 to 12 days.
  - Features: 15 to 21 days.
- Recommendation: treat all feature requests as post-stabilization backlog unless sprint capacity is significantly larger than one small team over two weeks.

### 2. Dependency and Critical-Path Audit

Recommended execution order:
1. `MAJOR-001` OCR dependency validation and graceful fallback.
2. `MINOR-004` configuration validation (supports OCR + model setup reliability).
3. `MAJOR-002` model management and assistant no-model behavior.
4. `MINOR-001` extraction logging/confidence hardening.
5. `MAJOR-003` E2E implementation (after backend/frontend contracts stabilize).
6. Remaining minor tickets.
7. Feature requests.

Critical dependencies:
- `MAJOR-003` OCR tests depend on `MAJOR-001`.
- `MAJOR-003` model-management tests depend on `MAJOR-002`.
- `FEATURE-001` PDF/Excel/FHIR should not proceed before baseline export contract tests are stable.

### 3. Ticket Quality Audit

Strengths:
- Tickets include concrete file targets.
- Most include user-impact rationale.
- Major items focus on reliability gaps and user-critical flows.

Gaps to close:
- Acceptance criteria are implied but not consistently explicit per ticket.
- Some tickets combine infra, API, and UI work in one estimate; split by deliverable for better tracking.
- Feature tickets are broad epics; each should be split into smaller implementation stories.

### 4. Suggested Refinements by Priority

High-priority refinements:
1. Add explicit "Definition of Done" checklists for each ticket (API behavior, UI behavior, tests, docs).
2. Add risk labels (`runtime`, `migration`, `data-quality`, `UX`, `perf`) per ticket.
3. Add rollout strategy using feature flags for OCR and model-management changes.
4. Add observability tasks to each major ticket (metrics + structured logs + error codes).

Medium-priority refinements:
1. Split each feature request into:
   - Backend contract story.
   - Frontend integration story.
   - Test/QA story.
   - Documentation story.
2. Add explicit non-functional targets:
   - E2E suite runtime budget.
   - Model download retry/backoff policy.
   - OCR fallback response-time target.

### 5. Suggested Sprint Packaging

If this is a single upcoming sprint, recommend shipping only:
- `MAJOR-001`
- `MAJOR-002`
- `MAJOR-003` (scoped to core workflow tests first)
- `MINOR-001`
- `MINOR-004`

Defer to next sprint:
- `MINOR-002`, `MINOR-003`, `MINOR-005`
- `FEATURE-001`, `FEATURE-002`, `FEATURE-003`

### 6. Suggested Additional Cross-Ticket Tasks

1. Add a sprint-level integration checklist in CI:
   - Import + verify + trends + export flow.
   - Assistant fallback/no-model flow.
   - OCR disabled-mode behavior.
2. Add user-visible runbooks:
   - OCR setup troubleshooting.
   - Local model setup and recovery.
3. Add release readiness gate:
   - No unresolved P0/P1 bugs.
   - E2E smoke suite green.
   - Updated API docs and user docs.

## Notes

This plan captures the provided ticket set verbatim in structure and intent, then adds a practical sequencing and scope audit to improve delivery reliability for the 2026-02-13 sprint phase.
