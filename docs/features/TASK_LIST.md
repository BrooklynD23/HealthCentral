# HealthCentral Remaining Work Task List

**Version:** 0.5.0
**Last Updated:** 2026-07-02
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

1. `README.md` (repo entrypoint and audited live feature surface overview)
2. `docs/api/endpoints.md` (exact mounted backend routes; API source of truth)
3. `docs/00_architecture_plans_index.md` (full documentation index — start here for anything not covered by the four entries in this list)
4. `docs/features/TASK_LIST.md` (this active remaining-work tracker)
5. `docs/05_backend_integration_status.md` (**Historical Reference** — Sprint 06 snapshot retained for audit context, not the live tracker)

This exact order (paths + sequence) must also appear in `README.md`'s "Documentation Source of Truth"
and `docs/00_architecture_plans_index.md`'s "Start Here" sections — `scripts/docs_lint.py`'s DOC-010
check enforces the three stay identical.

---

## Current Baseline Snapshot (2026-03-27)

- Sprint 1 (Auth + Session), Sprint 2 (Import/Extract/Normalize/Persist), Sprint 3 (Verification Workbench + Trends Dashboard), and Sprint 4 (Export System + Data Interoperability) all completed pre-2026-02 — this is what "import/extract/verify, trends, export" below refers to. (Merged in from `implementation_plan/README.md`, since removed — its MVP checklist and Sprint Progress table covered the same ground.)
- Completed baseline areas: auth, import/extract/verify, trends, export, assistant, assistant memory, interpretations, medications, notifications, gamification, settings, and document categorization/entity extraction.
- Stabilization sprint (STAB-001 through STAB-007) completed on 2026-02-14.
- Sprint 05 (Frontend Quality & Testing) completed on 2026-02-19: 188 frontend tests, accessibility, responsive layout, visualization interactions, E2E workflows.
- Sprint 06 (Platform Operations & Compliance) completed on 2026-02-21: security middleware (4 classes, 31 tests), monitoring/metrics (23 tests), backup/restore (14 tests), API/user/compliance documentation (14 files).
- Documentation reconciliation refreshed on 2026-03-27: `README.md` and `docs/api/endpoints.md` describe the audited live surface; `docs/05_backend_integration_status.md` is now explicitly historical.
- Remaining work: security remediation from Sprint 06 review, deferred feature backlog, the separate in-progress RAG category-filter wiring noted in the M001 audit (`INGEST-F`), and `MED-CORR-001` (medication correlations endpoint — see below).

---

## Open Items (Not Yet Started)

| Item ID | Scope | Priority | Ticket Detail | Primary File Targets | Status |
|---------|-------|----------|----------------|----------------------|--------|
| `MED-CORR-001` | `GET /medications/{id}/correlations` backend endpoint — currently only a frontend heuristic (`src/frontend/src/utils/correlation.ts`) exists; no backend route. Discovered via a 2026-07 doc-accuracy audit: `docs/plans/roadmap_gap_closure.md` had marked this "✅ COMPLETE" though the endpoint was never built. | P2 | Full ticket (goal, deliverables, acceptance criteria, TDD plan) at `docs/plans/roadmap_gap_closure.md:235` | `src/backend/api/medications.py`, `src/backend/models/`, `src/backend/tests/` (new test module) | [ ] OPEN |
| `RL-REDACT-001` | RL dataset export (`POST /feedback/export`) hardcoded `RedactionEngine(policy_level="standard")` — DOB/addresses/MRNs were not removed from exported DPO/GRPO/SFT training data. **Resolved 2026-07-07 (HC-M05 PR):** export now forces `policy_level="strict"` unconditionally (no configuration knob — an export cannot be made less redacted), and two additive strict-only rules were added to `modules/redaction.py` (owner-approved): context-labeled `mrn` and slash/dash `numeric_date` (ISO-8601 collection timestamps deliberately preserved — they are the longitudinal clinical signal). Regression tests: `test_rl_feedback.py::TestRedactionOnExport` (DOB/address/MRN scrubbed, ISO dates kept — the DOB test is the downgrade tripwire) and `test_redaction.py` policy-matrix rows. **Recorded deferral:** lab-value and medication-name redaction remain out of scope — values are the RL training signal itself, and medication names need a curated dictionary; tracked as a follow-up decision, not silently dropped. | P1 | Resolved in HC-M05 | `src/backend/modules/rl_dataset.py`, `src/backend/modules/redaction.py`, `src/backend/tests/test_rl_feedback.py`, `src/backend/tests/test_redaction.py` | [x] DONE (2026-07-07) |
| `S06-SEC-003` | Streaming request-body size enforcement raises a bare `ValueError` (`src/backend/security/input_validator.py:101-104`) with no global exception handler converting it to a 413 — confirmed still open via 2026-07 re-verification (S06-SEC-001 and S06-SEC-002 in the same review doc were found resolved/mitigated and corrected in place). Oversized streaming requests may 500 instead of cleanly rejecting. | P2 | Full finding + fix options at `docs/compliance/security-review-sprint06.md` (S06-SEC-003 section) | `src/backend/security/input_validator.py`, `src/backend/main.py` (exception handler registration) | [ ] OPEN |
| `DOC-API-001` | `PATCH /settings/model/agent` existed in code with no entry in `docs/api/endpoints.md` — already fixed in this session (added at `docs/api/endpoints.md:166`). Listed here only as a closed-loop record; no further action. | P4 | N/A | `docs/api/endpoints.md` | [x] DONE (2026-07-01) |
| `E2E-MED-001` | `MedicationDetail` page (`/medications/:medicationId`) has zero Playwright e2e coverage — route exists and works, just untested end-to-end. All other pages have at least one covering spec. | P3 | None yet — needs a new or extended spec under `src/frontend/e2e/` | `src/frontend/e2e/` (new spec or extend `ui-full-verification.spec.ts`), `src/frontend/src/pages/MedicationDetail.tsx` | [ ] OPEN |
| `SEC-RECOV-001` | Recovery key for profile encryption — a forgotten password is currently permanent, unrecoverable loss of the profile's entire health record (DEK is sealed by password only, `core/profile_database.py`; no recovery path exists). Generate a one-time recovery code at profile creation that seals a second DEK copy. **GATED (auth/encryption) — design sign-off required before any code.** | P1 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#sec-recov-001--recovery-key-for-profile-encryption) | `src/backend/core/security.py`, `src/backend/core/profile_database.py`, `src/backend/api/profiles.py`, frontend ProfileSetup/unlock | [ ] OPEN |
| `BKUP-UX-001` | User-facing scheduled backup & restore — `scripts/backup.py` (Sprint 06 OPS-002) is a developer CLI no patient will run; device loss currently destroys the whole record. Surface backup/verify/restore in SettingsPage with scheduling via the existing asyncio-scheduler pattern. Restore/key edge cases flagged for review. | P2 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#bkup-ux-001--user-facing-scheduled-backup--restore) | `src/backend/scripts/backup.py`, new backup routes, `src/frontend/src/pages/SettingsPage.tsx` | [ ] OPEN |
| `INGEST-FHIR-001` | FHIR R4 structured import (lab `Observation`/`DiagnosticReport` bundles) — zero structured ingest exists today; everything goes PDF/image → OCR → regex. Portal FHIR exports (Cures Act) give exact values/units/ranges/LOINC codes with no OCR errors. Deterministic stdlib-JSON parsing, no new dependency, imports stay unverified until workbench review. | P2 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#ingest-fhir-001--fhir-r4-structured-import-lab-observations-first) | `src/backend/modules/extract_fhir.py` (new), `modules/ingest.py`, `modules/normalize.py`/`glossary.py` (LOINC map) | [ ] OPEN |
| `NORM-UNIT-001` | Unit normalization/conversion — `normalize.py`'s docstring promises "Unit preservation and conversion" but no conversion exists; TrendsDashboard assumes one unit per analyte, so cross-lab unit mixes (mg/dL vs mmol/L) silently corrupt or fragment trend lines. Table-driven per-analyte conversion at trend-read time; originals never mutated. Step 0: audit actual mixed-unit behavior. **Step-0 audit found the bug is data-corruption grade, not just fragmentation: the trend summary's change-% was computed across incompatible units (94 mg/dL → 5.22 mmol/L read as a ~-94% drop). Implemented 2026-07-03.** | P2 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#norm-unit-001--unit-normalization--conversion-for-cross-lab-comparability) | `src/backend/modules/normalize.py`, `src/backend/api/observations.py`, `src/frontend/src/pages/TrendsDashboard.tsx` | [x] DONE (2026-07-03) |
| `PROF-DEL-001` | Profile deletion & data lifecycle — no `DELETE /profiles/{id}` route exists (every sub-entity is deletable; the profile is immortal), though `core/audit.py`'s event conventions already list `profile.delete`. Ordered crypto-erase sequence (keys first) + export-before-erase. **DECISION FIRST: audit-row retention (retain vs. anonymized tombstone) is a compliance call — scope with user before coding.** | P2 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#prof-del-001--profile-deletion--data-lifecycle-right-to-erase) | `src/backend/api/profiles.py`, `core/profile_database.py`, `modules/export.py`, `docs/compliance/data-privacy.md` | [ ] OPEN |
| `RAG-INJ-001` | Injection-filter retrieved chunks — `rag.py` screened history and memory items through `PROMPT_INJECTION_PATTERNS` but composed document/reference chunk text into prompts unfiltered. **Resolved 2026-07-07 (HC-M05 PR):** `compose_prompt` now routes reference/user-document chunk text through `_sanitize_chunk_text` (neutralize-don't-drop: matching spans replaced with `[UNTRUSTED-INSTRUCTION-REMOVED]`, benign prose and grounding preserved, warning logged); the agent path got the parallel fix — `draft`/`replay` scrub observation `analyte`/`unit` fields via `guardrails/redaction_gate.sanitize_untrusted_field` (same imported pattern list, so surfaces can't drift). Guarded by the HC-M05 eval corpus: 16 injection/phi-bait golden cases + `injection_resistance`/`phi_leakage` CI axes + the `score_injection_compose_case` end-to-end probe in `scripts/agent_eval_gate.py`. | P2 | Resolved in HC-M05 | `src/backend/modules/rag.py`, `src/backend/modules/agent/nodes/draft.py`, `src/backend/modules/agent/guardrails/redaction_gate.py`, `src/backend/modules/agent/eval/scorer.py` | [x] DONE (2026-07-07) |
| `CITE-SRC-001` | Citation click-through to source — `[YOUR_RESULTS:N]` chips in ExplainAssistant become deep links to the source document page/bbox region in the Verification Workbench. Bbox OCR data and per-chunk document provenance already exist; this is additive response-schema fields + frontend routing. Turns citations from labels into checkable evidence. | P3 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#cite-src-001--citation-click-through-to-source-document-region) | `src/backend/api/assistant.py`, `src/frontend/src/pages/ExplainAssistant.tsx`, `VerificationWorkbench.tsx` | [ ] OPEN |
| `AUDIT-PHI-001` | Audit-log PHI minimization — audit rows (free-text `action`, arbitrary `details` JSON) land in the unencrypted master DB, the one place patient-linked data escapes SQLCipher; the 2026-07 GET-route audit expansion increased that volume. Phase A: inventory call sites, allowlist-scrub `details` inside `create_audit_log` (single choke point). Phase B (master-DB encryption) explicitly out of scope/gated. | P2 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#audit-phi-001--audit-log-phi-minimization-in-the-unencrypted-master-db) | `src/backend/core/audit.py`, `api/` call sites, `docs/compliance/hipaa-controls.md` | [ ] OPEN |
| `MODEL-INT-001` | Model-artifact integrity manifest — `download_models.py`/`model_selector.py` have zero checksum handling (and Gemma4 URLs are still `PLACEHOLDER`); a silently swapped model artifact silently invalidates every tuned guardrail threshold and golden eval. Checked-in SHA256 manifest, verify at download and at `llama_cpp` load (hash cached by path+mtime+size). Foundation for the shared model-distribution infra the findings report wants. | P3 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#model-int-001--model-artifact-integrity-manifest-sha256-pin--verify-on-load) | `scripts/download_models.py`, `src/backend/modules/model_selector.py`, `src/backend/core/llm/`, `config/model_manifest.json` (new) | [ ] OPEN |

---

## Active Remaining Items (TDD Structured)

| Item ID | Scope | Phase T1 (Red: define failing check first) | Phase T2 (Green: implement minimal fix) | Phase T3 (Refactor/Verify: stabilize + document) | Primary File Targets | Status |
|---------|-------|---------------------------------------------|------------------------------------------|---------------------------------------------------|----------------------|--------|
| `DOC-003` | Automated documentation drift checks | Added baseline drift checks in `scripts/docs_lint.py` for stale markers and contradictory labels. | Implemented executable local entrypoint: `python3 scripts/docs_lint.py`. | Documented rule set in script header and validated passing baseline run. | `scripts/docs_lint.py` (new), `docs/00_architecture_plans_index.md`, `docs/features/TASK_LIST.md` | [x] DONE |
| `DOC-004` | Canonical doc ownership and update policy | Added `_check_canonical_ownership()` lint rule checking for `Owner:` and `Refresh Trigger:` fields. | Added `**Owner:**` and `**Refresh Trigger:**` to the canonical docs and cross-links across the active doc set. | Added monthly review cadence section to TASK_LIST.md. | `scripts/docs_lint.py`, `docs/00_architecture_plans_index.md`, `docs/05_backend_integration_status.md`, `docs/features/00_features_index.md`, `docs/features/TASK_LIST.md`, `docs/plans/next-agent-documentation-consolidation.md` | [x] DONE |
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

### 2026-07-03 - NORM-UNIT-001 Implemented (cross-lab unit normalization)

First of the shovel-ready architect-review tickets, done TDD-first (branch
`claude/healthcentral-arch-review-qrwht3`).

**Step-0 audit result (the ticket mandated it first):** the bug is worse than
"fragmentation". In `api/observations.py::get_analyte_trend`, the trend summary's
change-percentage was computed from `data_points[0].value` → `[-1].value` with no
unit awareness, so a clinically flat glucose series reported 94 mg/dL then
5.22 mmol/L rendered as "decreased by 94.5%". Data corruption in the flagship view.

**Fix (deliberately conservative):**
- `modules/normalize.py`: added a per-analyte `UNIT_CONVERSIONS` table (established
  clinical factors), `normalize_unit()`, `canonical_unit_for()`, and
  `convert_to_canonical()` returning a `UnitConversion` (or `None` — never guesses a
  factor for an unlisted unit). Scoped to mass/molar-concentration conversions;
  deliberately omits CBC ×10ⁿ count relabels (numerically factor-1.0 cosmetic cases
  with high unit-string parsing ambiguity — not worth the risk in a patient app).
- `api/observations.py`: conversion activates **only** when a tabled analyte's series
  contains ≥2 distinct units AND every unit is convertible; otherwise the exact legacy
  path runs. Guarantees zero change for any single-unit series. Summary %, ref ranges,
  and per-point values all computed in the canonical unit; each converted `TrendPoint`
  carries `original_value`/`original_unit` for provenance. Storage untouched.
- Frontend: `TrendPoint` type + chart tooltip show "Reported: X mmol/L" on converted
  points.

**Verification:** 10 new tests in `tests/test_unit_conversion.py` (pure conversion +
endpoint mixed-unit/single-unit/untabled), all pass. Full backend suite: 680 passed,
10 failed — the 10 confirmed pre-existing/env-only by stash-diff (date & PDF
extraction, model-download, embedding-similarity 0.63<0.7); zero new failures.
Frontend `npx tsc --noEmit` clean; TrendsDashboard vitest 9/9 pass; `from main import app`
boots. Not touched: any CLAUDE.md-gated file.

**Env note:** the committed `.wsl-pytest-venv` has a corrupted `python3` symlink on this
mount (unusable); ran tests in a throwaway local venv instead. The tracked venv was left
untouched.

### 2026-07-02 - Architect Review: Nine New Proposal Tickets Registered

Review-and-propose pass (branch `claude/healthcentral-arch-review-qrwht3`) requested as input to the
next build cycle: independent architecture judgment on what the consolidated findings report
(`docs/plans/2026-07-02-consolidated-findings-report.md`) and this backlog missed entirely — every
item below is additional to that report's Section 4, not a rehash. Each proposal was verified
against the codebase before ticketing (no FHIR handling anywhere in `src/`; no unit-conversion code
despite `normalize.py`'s docstring claim; `backup.py` CLI-only; password-only DEK unsealing with no
recovery path; no profile DELETE route; `rag.py` injection filter covering history/memory but not
retrieved chunks; no model checksum handling).

Nine tickets registered in the Open Items table, full designs + implementation guidance in
`docs/plans/2026-07-02-architect-review-proposal-tickets.md`:

- **Data durability** (highest trust stakes): `SEC-RECOV-001` (recovery key — **gated**, needs
  design sign-off), `BKUP-UX-001` (user-facing backup/restore).
- **User value**: `INGEST-FHIR-001` (structured import, bypasses OCR), `CITE-SRC-001` (citation
  click-through to source region).
- **Correctness**: `NORM-UNIT-001` (cross-lab unit conversion in trends).
- **Privacy/safety hygiene**: `PROF-DEL-001` (**decision first**: audit-row retention),
  `RAG-INJ-001` (review-gated, guardrail-adjacent), `AUDIT-PHI-001` (**decision** on legacy rows;
  phase B gated), `MODEL-INT-001`.

No product code was changed this session — docs only. Next step: user sign-off conversations for
`SEC-RECOV-001` and the `PROF-DEL-001`/`AUDIT-PHI-001` decisions; `NORM-UNIT-001`/`RAG-INJ-001`/
`MODEL-INT-001` are shovel-ready for an implementation agent.

### 2026-07-01 - Multi-Agent Tech Survey, Gap-Closure Round, and Compliance Audit (session summary for next planning pass)

This was a multi-turn session (branch `claude/agent-exploration-tech-research-en1ia3`, PR #8) running parallel Explore/research/implementation agents. Read this before starting the next planning pass — it's a map of what changed and what's still open.

**1. Tech upgrade survey** (`docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md`): 9-area open-source/research survey (faithfulness/entailment, retrieval indexing, PHI redaction, OCR/extraction, agent orchestration, frontend, notifications, auth/encryption, gamification) with per-area candidates, recommendations, and effort estimates. Two corrections baked in: `modules/agent/` is a hand-rolled state machine, **not** LangGraph; `apscheduler` was a dead dependency (real scheduler is a hand-rolled asyncio loop). Section 14 has 5 gap-closure implementation suggestions (test-coverage map, shared model-distribution prerequisite for future NLI/NER work, bcrypt-is-fine correction, Gemma4-placeholder correction, dead-code cleanup).

**2. Implemented from that survey** (safe/no-sign-off items only — Areas 1/3/8 deliberately deferred, they touch CLAUDE.md-protected safety/auth files and need explicit sign-off before any work starts):
- §14.5 cleanup: removed dead `vector_store_type` config + unused `faiss-cpu` dependency.
- Area 6: Recharts 2.10.3 → 3.9.1 (v2 was EOL upstream).
- Area 7: dropped unused `apscheduler`; added additive `DesktopNotifierProvider` (plyer/winsdk retained as fallback).
- Config cleanup: removed dead `multi_pass_verification`/`verification_passes` fields (confirmed never read); kept `use_llm_entailment` as an intentional placeholder for future NLI wiring (Area 1). *(Retroactive sign-off 2026-07-05: user approved the dffe1f9 verifier_agent.py dead-config removal.)*

**3. Real gap found and fixed:** 11 GET routes across `api/documents.py`/`api/observations.py` had zero audit logging (middleware only covers mutating methods; these routes had no handler-level logging either) — violated CLAUDE.md's explicit audit-logging invariant. Fixed with additive `event="view"` logging, try/except-wrapped so a logging failure can't fail a read. A post-review bug (3 list/aggregate routes passing `profile_id` as the audit `entity_id`, producing misleading log rows) was caught and fixed before commit.

**4. Tooling added:** vendored all 14 skills from `github.com/obra/superpowers` (MIT) into `.claude/skills/`, so they work as slash commands in Claude Code web/cloud sessions (repo-committed skills carry over; user-level `~/.claude/skills/` does not). `.gitignore` narrowed from blanket `.claude/` to `.claude/*` + `!.claude/skills/` so they're actually trackable — verified nothing else under `.claude/` is exposed by this change.

**5. Docs consolidation:** `2026-03-04-handoff.md` bannered historical (corrected its own overstated "23/23 tasks" claim to 22/23 — RAG category-filter wiring, `INGEST-F`, is still open). `roadmap_gap_closure.md` deliberately **not** bannered — found a real discrepancy (see MED-CORR-001 below) and got a "Status Update" note instead of a false supersession claim.

**6. New tickets registered this session** (see Open Items table below): `MED-CORR-001` (medication correlations endpoint marked "COMPLETE" but never built). This session's follow-up compliance/gap audit found more — see the new rows added just below.

**7. Compliance audit findings** (`docs/compliance/security-review-sprint06.md`, `audit-checklist.md` corrected in place): `S06-SEC-001` (unauth metrics dashboard) verified **resolved**. `S06-SEC-002` (upload size bypass) verified **partially mitigated** (bounded limit now applied, not unlimited — `modules/ingest.py`'s in-memory read behavior not re-verified this pass). `S06-SEC-003` (ValueError not caught globally on streaming body size limit) confirmed **still open**. `audit-checklist.md`'s 50 unchecked items are correctly unchecked (it's a per-deployment sign-off, not a code-capability inventory) — annotated with which areas have supporting code evidence without checking boxes on its behalf.

**8. Not started, needs a decision before scoping:**
- RL dataset export redaction gap (highest safety stakes of anything found this session — default "standard" policy doesn't redact lab values/dates/medication names/biomarker values on `POST /feedback/export`; only "strict" does, and strict isn't default). See Open Items table.
- HIPAA technical safeguards: MFA, automated key rotation, penetration testing, BAA template — none implemented; these are product/ops decisions as much as engineering ones.
- `F-006` (removing `profile_id` from API response DTOs) — still just a review doc, not started, not approved.
- Areas 1/3/8 from the tech survey (faithfulness/entailment NLI, PHI redaction NER, auth library swaps) — recommendations exist, implementation needs explicit sign-off per CLAUDE.md before any code changes to `faithfulness.py`/`verifier_agent.py`/`redaction.py`/`core/security.py`.

**Next planning pass should start by:** picking one of the "not started" items above (RL export redaction and S06-SEC-003 are the two with genuine safety/security stakes), scoping it as its own ticket the way `MED-CORR-001` was done, and getting explicit sign-off before touching any CLAUDE.md-protected file.

### 2026-03-27 - Live Surface Reconciliation Pass

- Reconciled the canonical doc ownership model with the M001/S01 audit and the mounted router inventory.
- Promoted `README.md` and `docs/api/endpoints.md` as the live surface source of truth for contributors.
- Marked `docs/05_backend_integration_status.md` as a **Historical Reference** for the Sprint 06 snapshot rather than an active live-surface tracker.
- Updated the baseline summary here to explicitly include assistant memory, gamification, model settings sub-surfaces, and document categorization/entity/image routes.
- Verification: `python3 scripts/docs_lint.py` and targeted `rg` drift checks re-run after reconciliation.

### 2026-03-27 - Historical Doc Ownership Reclassification

- Reclassified `docs/05_backend_integration_status.md` under the historical-doc lint bucket instead of the canonical ownership bucket.
- Kept the historical banner, inactive-tracker wording, and stale-marker guard in place so the Sprint 06 snapshot still fails loudly if it drifts.
- Removed the implication that contributors must preserve canonical `Owner` / `Refresh Trigger` metadata on this file.
- Verification: `python3 scripts/docs_lint.py`.

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

- **DOC-004**: Added `Owner` + `Refresh Trigger` fields to the canonical docs. Added lint rule `_check_canonical_ownership()`. Added monthly review cadence section. The Sprint 06 backend snapshot is now treated as historical and no longer participates in that ownership rule.
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

### 2026-07-10 - HC-M12 Entity Source Spans + User Verification (HC-SPAN)

- **Schema**: `DocumentEntity` gained nullable `char_start`, `char_end`, `quote` (verbatim source substring, invariant `text[char_start:char_end] == quote`), `verified_by_user` (null=unreviewed / true=verified / false=rejected), `extraction_version`. Profile migration `010_entity_source_spans` (additive, working downgrade, linear on `009_agent_enabled`).
- **Extractors**: `extract_imaging` / `extract_pathology` / `extract_visit_notes` now attach spans via new `modules/extract_spans.with_span()` (uses regex match spans, whitespace-trimmed; unresolvable span => quote None + confidence capped at 0.5; `extraction_version="rule-v2"`).
- **API**: entity fields persisted in `_classify_and_extract_entities`; `GET /documents/{id}/entities` returns the new fields; new `PATCH /documents/{doc_id}/entities/{entity_id}/verification` with body `{verified: true|false|null}` (auth + profile-DB scoping + master-DB audit logging matching neighboring routes).
- **Frontend**: `EntityDetailView` shows each entity's verbatim quote plus verify/reject controls; rendered in `VerificationWorkbench` for the selected document (including document-review mode with no lab observations). `useSetEntityVerification` / `setEntityVerification` exported through the services barrel.
- **Tests**: backend `tests/test_source_spans.py` (HC-SPAN: extractor span exactness, confidence cap, API round-trip, PATCH state + audit + 404/403, migration 010 upgrade/downgrade); migration-head assertion bumped to 010 in the SQLCipher-fallback test; frontend `EntityVerificationService.test.tsx` (FE-SPAN contract tests).
- **Verification**: backend `pytest` 740 passed / 1 known env-only embedding failure (unchanged); `npx tsc --noEmit` → 0 errors; `npx vitest run` → 109/109 pass; `from main import app` boots.
