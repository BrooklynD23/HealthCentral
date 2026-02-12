# HealthCentral Remaining Work Task List

**Version:** 0.3.0
**Last Updated:** 2026-02-12
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

1. `docs/current_gap_audit_2026-02-09.md` (closure log for HC-T001 to HC-T006)
2. `docs/05_backend_integration_status.md` (current API/UI integration baseline)
3. `docs/features/TASK_LIST.md` (this active remaining-work tracker)
4. `docs/plans/next-agent-documentation-consolidation.md` (hands-off execution plan)

---

## Current Baseline Snapshot (2026-02-12)

- Completed baseline areas: auth, import/extract/verify, trends, export, assistant, interpretations, medications, notifications, settings.
- Major drift cleanup completed: doc indexes aligned, historical banners added to superseded plan files, stale assistant/OCR status wording corrected.
- Remaining work now centers on consolidation guardrails and hardening.

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

---

## Recommended Execution Order

1. `DOC-003`
2. `DOC-004`
3. `DOC-005`
4. `TEST-001`
5. `TEST-002`
6. `UX-001`
7. `A11Y-001`
8. `DOC-006`

---

## Monthly Review Cadence

On the first of each month, review all canonical docs for freshness:

1. Check each doc's `**Last Updated:**` field — if stale (>60 days), flag for update or archival.
2. Verify `**Owner:**` is still the correct responsible party.
3. Confirm `**Refresh Trigger:**` conditions haven't occurred without a doc update.
4. Run `python3 scripts/docs_lint.py` to catch any drift.
5. Update this section's "Last cadence review" date below.

**Last cadence review:** 2026-02-12

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
