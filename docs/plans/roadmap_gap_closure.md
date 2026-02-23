# Gap Closure Roadmap (Security + PRD Completion)

**Last Updated:** 2026-02-23  
**Owner:** PM (prioritization) + Senior Dev (technical approval)  
**Status:** Phases 1-3 COMPLETE; Phases 4-6 in progress
**Refresh Trigger:** Scope/priority change, PRD decision, or ticket completion  
**Primary Tracker (after approval):** GitHub Issues + Milestones (sync back to `docs/features/TASK_LIST.md` as needed)

## Purpose

Turn the Gap Analysis report into a **reviewable, copy/paste-ready ticket pack** that an implementation agent can execute with:

- Test Driven Development (Red → Green → Refactor/Verify)
- GitHub CI as a hard merge gate
- Production-ready deployment discipline (staging smoke, rollback notes, docs updated)

## Inputs / Sources of Truth

- Root follow-ups: `PLAN.md` (SEC-006, multipart cushion, docs drift, test nits)
- Sprint 06 security review: `docs/compliance/security-review-sprint06.md` (SEC-007, SEC-008)
- PRDs:
  - v0.2 features PRD: `docs/features/03_features_prd.md`
  - v0.1 PRD: `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md`
- Current integration baseline: `docs/05_backend_integration_status.md`

## Deployment + CI Gates (applies to every ticket)

- **CI must pass**: `docs-lint`, `backend-tests`, `frontend-tests`, `e2e-tests` (see `.github/workflows/ci.yml`).
- **Security regressions**: no new unauthenticated sensitive endpoints; rate limiting and body-size enforcement remain effective.
- **Staging smoke** (when applicable): run at least one happy-path flow for the changed area.
- **Rollback note**: every ticket that changes DB schema, auth, or middleware includes a rollback plan.

## Sprint / Phase Outline (recommended)

1. **Phase 1 (P0 Stabilization):** SEC-006 + upload cushion + docs drift + test nits
2. **Phase 2 (P1 Security/CI):** SEC-007 + SEC-008
3. **Phase 3 (P2 Product API):** `GET /medications/{id}/correlations` (+ optional frontend adoption)
4. **Phase 4 (PRD Decisions):** voice dose logging scope + gamification/badges decision (then implementation)
5. **Phase 5 (Privacy + Provenance):** redaction pipeline + OCR bounding-box citations
6. **Phase 6 (Backlog/Expansion):** imaging/pathology/visit notes ingestion + assistant memory store + chart image export

> Note: Phases 4–6 are intentionally split into “decision/spec” then “implementation” tickets to avoid ambiguous build work.

---

# Ticket Pack (Copy/Paste Into GitHub Issues)

Each ticket below is formatted to be pasted directly into a GitHub Issue body.

## Phase 1 — P0 Stabilization ✅ COMPLETE

### SEC-006 — Enforce production `debug=False` before app creation

**Priority:** P0 (ship this sprint)  
**Suggested Labels:** `security`, `backend`, `config`, `pydantic`  
**Primary Context:** `PLAN.md` item #1

**Problem**
`src/backend/main.py:create_app()` reads `settings.debug` before `settings.validate_startup()` runs (lifespan), so production can still expose `/docs` + enable reload behavior.

**Expected Deliverables**
- Backend: production debug guard runs at `Settings()` construction time (e.g., `model_post_init`) so `settings.debug` is already safe before `create_app()` executes.
- Tests: regression tests proving `/docs` is disabled when `app_env=production` even before lifespan validation.
- Docs: short note in `docs/05_backend_integration_status.md` clarifying docs exposure policy (dev-only) if not already explicit.

**Key Files / Entry Points**
- `src/backend/core/config.py` (`Settings`, `settings = Settings()`)
- `src/backend/main.py` (`create_app()`, `uvicorn.run(... reload=settings.debug)`)
- Existing tests: `src/backend/tests/security/test_security_remediation.py`, `src/backend/tests/test_config_validation.py`

**Acceptance Criteria**
- [ ] When `app_env="production"` and `debug=True`, `Settings()` results in `debug == False` **without** needing `validate_startup()` to be called.
- [ ] In production-mode tests, `create_app()` sets `docs_url=None` and `redoc_url=None`.
- [ ] CI passes (`backend-tests`).

**TDD Plan**
- **Red:** add a test that instantiates `Settings(app_env="production", debug=True, jwt_secret="x")` and asserts `debug` is forced false immediately.
- **Green:** implement eager enforcement (`model_post_init` or equivalent).
- **Refactor/Verify:** ensure `validate_startup()` still returns warnings consistently and does not become the only enforcement point.

**Verify**
- `bash scripts/run-backend-tests.sh -q`

**Rollback Plan**
- Revert to prior behavior (lifespan-only) if the eager hook causes unintended config side effects; keep the new test to prevent regressions once re-fixed.

---

### UPL-001 — Multipart overhead cushion (5%) for 50MB uploads

**Priority:** P0  
**Suggested Labels:** `backend`, `uploads`, `middleware`  
**Primary Context:** `PLAN.md` item #2

**Problem**
`InputValidationMiddleware` uses an exact byte limit derived from `max_import_file_size_mb`. Multipart framing overhead can cause a “50 MB file” to be rejected.

**Expected Deliverables**
- Backend: import/upload endpoints get an **effective** limit with a small overhead cushion (5%).
- Tests: upload/body-size tests that fail pre-fix and pass post-fix for near-limit multipart bodies.
- Docs: add a one-line note documenting the effective limit behavior (optional; only if API docs mention the exact byte cap).

**Key Files**
- `src/backend/security/input_validator.py` (`max_upload_bytes`)
- Tests: `src/backend/tests/security/test_security_remediation.py`

**Acceptance Criteria**
- [ ] A multipart request with a nominal 50MB file does not fail due to framing overhead.
- [ ] Requests materially above the intended cap still fail with `413`.
- [ ] CI passes (`backend-tests`).

**TDD Plan**
- **Red:** add/adjust a test that constructs a body just over the current exact cap and expects success with the cushion.
- **Green:** apply `* 1.05` (or equivalent) to upload limit.
- **Refactor/Verify:** ensure non-import endpoints keep the stricter `max_request_body_bytes` limit.

**Verify**
- `bash scripts/run-backend-tests.sh -q`

---

### DOC-DRIFT-001 — Update docs for `/health` (liveness) and metrics auth

**Priority:** P0  
**Suggested Labels:** `docs`, `backend`, `monitoring`  
**Primary Context:** `PLAN.md` item #3

**Expected Deliverables**
- Docs: update both files to match the shipped behavior:
  - `docs/user/troubleshooting.md`
  - `docs/05_backend_integration_status.md`
- Remove any unauthenticated metrics `curl` examples; replace with auth-required examples.
- Update “Next Steps” / TODO sections so they do not reference already-completed SEC items.

**Acceptance Criteria**
- [ ] No docs claim `/health` returns metrics summaries.
- [ ] Metrics endpoint examples include auth.
- [ ] `python3 scripts/docs_lint.py` passes.

**Verify**
- `python3 scripts/docs_lint.py`

---

### TEST-NIT-001 — Clean up security test nits (unused import + stale docstring)

**Priority:** P0  
**Suggested Labels:** `tests`, `maintenance`  
**Primary Context:** `PLAN.md` item #4

**Expected Deliverables**
- Tests: remove unused imports and update misleading docstrings:
  - `src/backend/tests/security/test_security_remediation.py` (unused `patch` import)
  - `src/backend/tests/security/test_input_validator.py` (stale docstring wording, if still present)

**Acceptance Criteria**
- [ ] No unused imports in touched test files.
- [ ] CI passes (`backend-tests`).

**Verify**
- `bash scripts/run-backend-tests.sh -q`

---

## Phase 2 — P1 Security/CI Follow-ups ✅ COMPLETE

### SEC-007 — Proxy-aware client IP handling for rate limiting (safe-by-default)

**Priority:** P1  
**Suggested Labels:** `security`, `backend`, `ops`, `rate-limiting`  
**Primary Context:** `docs/compliance/security-review-sprint06.md` finding SEC-007

**Problem**
Rate limiting is keyed on `scope["client"]` which may be wrong behind reverse proxies. Blindly trusting `X-Forwarded-For` is also unsafe unless proxy trust is configured.

**Expected Deliverables**
- Backend: configurable “trusted proxy” behavior (disabled by default) to derive client IP from forwarded headers only when safe.
- Docs: a deployment note explaining how to configure proxy trust and what happens when not configured.
- Tests: middleware tests proving:
  - default mode uses `scope["client"]`
  - trusted-proxy mode uses forwarded headers only when request originates from a trusted proxy source

**Key Files**
- `src/backend/security/rate_limit_middleware.py` (client key computation)
- `src/backend/core/config.py` (add proxy-trust settings surface)
- `docs/05_backend_integration_status.md` (deployment notes)

**Acceptance Criteria**
- [ ] Default behavior unchanged for local/dev.
- [ ] When proxy-trust is enabled and configured, rate limiting keys on real client IP.
- [ ] Spoof attempts (untrusted source sending `X-Forwarded-For`) do not change the key.

**TDD Plan**
- **Red:** add middleware unit tests covering trusted/untrusted forwarded header scenarios.
- **Green:** implement config + parsing logic.
- **Refactor/Verify:** document deployment steps; ensure no performance regressions in middleware path.

**Verify**
- `bash scripts/run-backend-tests.sh -q`

---

### SEC-008 — Make CI security scan blocking on High/Critical (policy + implementation)

**Priority:** P1  
**Suggested Labels:** `security`, `ci`, `tooling`  
**Primary Context:** `docs/compliance/security-review-sprint06.md` finding SEC-008; `.github/workflows/ci.yml`

**Expected Deliverables**
- CI: security scan job becomes **required** and fails builds on agreed thresholds (minimum: high/critical).
- Artifacts: still upload `bandit` + `pip-audit` reports to CI artifacts on both pass/fail.
- Policy: lightweight “waiver” process documented (expiry + owner) for exceptional cases.

**Implementation Notes (context engineering)**
- Current CI is non-blocking (`continue-on-error: true`) and also uses `|| true`, effectively never failing.
- If tool CLIs cannot filter by severity cleanly, add a small gating script (e.g., `scripts/security_gate.py`) to parse JSON reports and exit non-zero when threshold is exceeded.

**Acceptance Criteria**
- [ ] A known-high/critical finding causes the CI job to fail.
- [ ] Reports are always uploaded as artifacts for visibility.
- [ ] Branch protection can mark the job as required without “always green” false positives.

**Verify**
- Update workflow on a branch; confirm check behavior in PR (expected: job fails when findings exist).

---

## Phase 3 — Product API Completion ✅ COMPLETE

### MED-CORR-001 — Implement `GET /medications/{id}/correlations`

**Priority:** P2  
**Suggested Labels:** `backend`, `api`, `medications`, `prd`  
**Primary Context:** v0.2 features PRD gap (“Lab-medication correlation API endpoint”)

**Goal**
Provide a backend correlation endpoint so clients can fetch a consistent “medication ↔ lab observations” view (not just frontend-only heuristics).

**Expected Deliverables**
- Backend:
  - New route: `GET /api/v1/medications/{id}/correlations`
  - Response schema (documented) including:
    - medication metadata (id/name/period)
    - observations in medication active period (filterable)
    - optional summary statistics (count, abnormal count, per-analyte min/max/avg)
- OpenAPI docs updated (where this repo documents endpoints).
- Tests: integration tests for authz + correctness with seeded meds/observations.
- Frontend (optional, gated): add a service method and a feature flag to adopt the endpoint without breaking existing overlay logic.

**Key Context (existing frontend reference)**
- Frontend heuristic utility: `src/frontend/src/utils/correlation.ts`
- Frontend types: `src/frontend/src/services/types.ts` (“CorrelationContext”, “MedicationOverlayPeriod”)

**Key Backend Files**
- `src/backend/api/medications.py` (add endpoint)
- `src/backend/models/` (Medication, Observation, Document)
- Test location: `src/backend/tests/` (add a focused test module)

**Acceptance Criteria**
- [ ] Endpoint returns only data for the authenticated profile (authz enforced).
- [ ] Observations returned are within `[started_at, ended_at]` (or no end when ongoing).
- [ ] Supports query params for basic filtering (at minimum: `analyte_canonical`, date range, limit).
- [ ] CI passes (`backend-tests`).

**TDD Plan**
- **Red:** write an integration test that seeds a medication + 3 observations (before/during/after) and asserts only “during” is returned.
- **Green:** implement query + response model.
- **Refactor/Verify:** align response shape with frontend needs; update docs.

**Verify**
- `bash scripts/run-backend-tests.sh -q`

---

## Phase 4 — PRD Decisions (must be approved before build)

### PRD-DEC-VOICE-001 — Decide scope for “Voice dose logging”

**Priority:** Decision  
**Suggested Labels:** `pm`, `prd`, `privacy`, `ux`  
**Blockers:** platform decision

**Open Questions**
- Supported clients: web only, mobile only, or both?
- Implementation strategy: browser Web Speech API vs upload audio + local STT vs cloud STT (privacy implications).
- Consent + data handling: are audio clips stored? retained? encrypted? deletable?

**Expected Deliverables**
- One-page spec: user stories + non-goals + explicit platform support.
- Privacy note: what data leaves device (ideally none) and retention policy.
- UX flow: “tap mic → confirm transcription → log dose” (error states included).
- Engineering plan: chosen approach + test strategy.

**Acceptance Criteria**
- [ ] PM + Senior Dev sign-off on a single approach and its privacy posture.

---

### PRD-DEC-GAM-001 — Decide “streaks-only” vs “badges” (gamification)

**Priority:** Decision  
**Suggested Labels:** `pm`, `prd`, `ux`  
**Blockers:** product decision

**Expected Deliverables**
- Decision record: streak milestones only OR badge system (with examples).
- If badges: define rules, display surfaces, and whether achievements are stored or computed.
- Anti-abuse and edge cases: missed days, medication ended, schedule changes.

**Acceptance Criteria**
- [ ] PM + Senior Dev choose a minimal v1 that is testable and won’t require later data backfills.

---

## Phase 4B — Blocked Implementation Tickets (do not start until decisions approved)

### MED-VOICE-001 — Voice dose logging (implementation)

**Priority:** Blocked (by `PRD-DEC-VOICE-001`)  
**Suggested Labels:** `frontend`, `backend`, `medications`, `ux`, `privacy`

**Goal**
Let users log a medication dose via voice input (then confirm) and persist it as a normal dose record with `log_method="voice"`.

**Expected Deliverables**
- Frontend:
  - Voice capture + transcription flow per the approved approach.
  - “Confirm transcript” step before logging.
  - Accessible UI (keyboard, aria-live for listening state).
- Backend:
  - Ensure dose logging endpoint accepts `log_method="voice"` (already allowed by schema) and stores transcript in an explicit field or `notes` (decision-dependent).
  - Add server-side validation so voice logs cannot bypass normal authz and dose constraints.
- Tests:
  - Frontend tests for the voice-log flow (mock transcription results).
  - Backend tests confirming `log_method="voice"` persists and appears in dose history.
- Docs:
  - Update user docs with supported browsers/devices and privacy posture.

**Key Files**
- Backend: `src/backend/api/medications.py` (dose logging endpoints + models)
- Frontend: medication logging UI (likely `src/frontend/src/pages/MedicationDetail.tsx` and services under `src/frontend/src/services/medications.ts`)

**Acceptance Criteria**
- [ ] A voice dose log creates a `DoseTaken` entry with `log_method="voice"`.
- [ ] User can edit/cancel before submitting.
- [ ] Works with the approved platform(s) and fails gracefully otherwise.
- [ ] CI passes (`frontend-tests`, `backend-tests`).

---

### GAM-001 — Gamification (streak milestones or badges) (implementation)

**Priority:** Blocked (by `PRD-DEC-GAM-001`)  
**Suggested Labels:** `frontend`, `backend`, `ux`, `prd`

**Goal**
Implement the approved v1 gamification approach with deterministic rules and tests (no “magic” client-only behavior).

**Expected Deliverables**
- Backend:
  - If “streak milestones”: compute milestones from existing streak data (no new DB required), expose via an endpoint.
  - If “badges”: implement badge rules + storage/computation approach as decided (may require a migration).
- Frontend:
  - Display streak milestones/badges in the agreed surfaces (e.g., medication detail, dashboard).
  - Empty states and “earned” states.
- Tests:
  - Rule tests for milestones/badges (edge cases: schedule changes, medication ended, skipped days).
  - UI tests for rendering earned/unearned states.
- Docs:
  - Update PRD status and add a short user explanation (“what counts as a streak/badge”).

**Key Context**
- Existing streak computation lives in `src/backend/modules/adherence_patterns.py` (`StreakData`).

**Acceptance Criteria**
- [ ] Rules are documented, tested, and consistent across devices.
- [ ] Feature does not require backfills unless explicitly approved.
- [ ] CI passes (`frontend-tests`, `backend-tests`).

---

## Phase 5 — Privacy + Provenance (production-grade)

### PRIV-RED-001 — Redaction pipeline for external API prompts (opt-in cloud LLM)

**Priority:** P2/P1 (depending on external API adoption)  
**Suggested Labels:** `security`, `privacy`, `backend`, `ai`  
**Primary Context:** v0.1 PRD Phase 4 gap (redaction missing); external API runner exists in `src/backend/core/external_runner.py`

**Goal**
Before sending any prompt to external providers, apply deterministic redaction to reduce PHI/PII leakage, and record what was redacted (without storing the raw secrets).

**Expected Deliverables**
- Backend:
  - New redaction module with a policy-driven API (input text → redacted text + metadata).
  - Integration point: external provider calls (ideally in `ExternalModelRunner.generate_async()` or a single upstream boundary).
  - Config toggles: enable/disable redaction; choose policy level.
- Tests:
  - Unit tests for redaction rules (names/dates/emails/phones/addresses as MVP).
  - Integration test confirming outbound payload is redacted when enabled.
- Docs:
  - Operator-facing note: what redaction does/doesn’t guarantee.
  - User-facing consent copy updated if needed.

**Acceptance Criteria**
- [ ] Redaction runs for any external API request when enabled.
- [ ] Redaction metadata is available for debugging/audit without persisting plaintext secrets.
- [ ] CI passes (`backend-tests`).

**Verify**
- `bash scripts/run-backend-tests.sh -q`

---

### OCR-BOX-001 — OCR bounding-box citations in verification UI

**Priority:** P3  
**Suggested Labels:** `frontend`, `backend`, `ocr`, `ux`  
**Primary Context:** v0.1 PRD gap (“bounding-box citations”)

**Goal**
When a user selects an extracted observation, show a visual provenance highlight (bounding box) on the source page.

**Expected Deliverables**
- Backend:
  - Persist bounding box data for OCR-derived text (minimum viable: per extracted observation, store `{page, x, y, w, h}` in page-relative coordinates).
  - New API surface to retrieve bounding boxes for a document (and/or for a specific observation).
  - (If needed) a page-image endpoint to render PDF pages to PNG for UI overlays.
- Frontend:
  - Update Verification UI to render page image and draw highlight rectangles.
  - Graceful fallback: if no boxes available, keep text-only provenance.
- Tests:
  - Backend unit/integration tests for bbox storage/retrieval schema.
  - Frontend component tests for overlay rendering (happy path + fallback).

**Key Context**
- Current provenance endpoint is text-only: `GET /api/v1/documents/{id}/pages` in `src/backend/api/documents.py`.
- Current UI “Source Preview” renders text (no page image): `src/frontend/src/pages/VerificationWorkbench.tsx`.

**Acceptance Criteria**
- [ ] Selecting an OCR-derived observation highlights the source region on the page image.
- [ ] Non-OCR documents still work (text-only or image-only as appropriate).
- [ ] CI passes (`backend-tests`, `frontend-tests`).

---

### UX-CONF-001 — Confidence scoring surfaced consistently (audit + close gap)

**Priority:** P3  
**Suggested Labels:** `frontend`, `ux`, `verification`, `prd-gap`

**Problem**
The PRD calls for “confidence scoring per extracted field.” Verify whether the current UI surfaces confidence in the intended places; if already satisfied, close the gap by documenting it.

**Expected Deliverables**
- Audit note: where confidence is currently shown (or missing) across Verification, Trends, and Export flows.
- If missing: add UI display (and tests) in the agreed surface(s).
- Docs: update `docs/05_backend_integration_status.md` (or PRD status notes) to reflect actual behavior.

**Key Context**
- Observation includes `extraction_confidence`; Verification UI currently renders a confidence badge in `src/frontend/src/pages/VerificationWorkbench.tsx`.

**Acceptance Criteria**
- [ ] PM/Senior Dev agree the requirement is satisfied OR approve the minimal UI change.
- [ ] If changed, CI passes (`frontend-tests`).

---

## Phase 6 — Backlog / Expansion (larger epics; split into sub-tickets)

### INGEST-EPIC-001 — Imaging reports + pathology + visit notes ingestion (Epic)

**Priority:** P3 (future sprint)  
**Suggested Labels:** `backend`, `ingestion`, `prd`, `epic`

**Expected Deliverables (Epic-level)**
- Spec: supported document categories, formats, and “definition of extracted entities” for each.
- Data model updates: schema changes and migrations (backward compatible).
- Ingestion pipeline: detection, extraction, verification UX updates, and indexing for search/RAG.
- Test suite: golden-file fixtures for each new doc category.
- Docs: update `docs/05_backend_integration_status.md` with supported formats and limitations.

**Recommended Sub-Tickets**
1. `INGEST-IMG-001` — Spec + schema proposal + migration plan
2. `INGEST-IMG-002` — MVP ingestion for one new category (pick one: imaging OR visit notes)
3. `INGEST-IMG-003` — Expand coverage + hardening + monitoring

**Acceptance Criteria (Epic exit)**
- [ ] At least one new doc category is ingested end-to-end with verification UI support.
- [ ] Observability exists (logs/metrics) for extraction failures and coverage.

---

### ASSIST-MEM-EPIC-001 — Persistent local assistant memory store (reviewable) (Epic)

**Priority:** P3  
**Suggested Labels:** `backend`, `frontend`, `assistant`, `privacy`, `epic`

**Expected Deliverables (Epic-level)**
- Backend: encrypted, per-profile memory store with CRUD.
- Frontend: UI to view/edit/delete memory items (user reviewable).
- Assistant integration: optional use of approved memory items in prompts (local + external, respecting consent).
- Tests: CRUD + authz tests + “memory not used unless enabled” tests.
- Docs: user-facing explanation of what is stored and how to clear it.

**Recommended Sub-Tickets**
1. `ASSIST-MEM-001` — Schema + CRUD API + tests
2. `ASSIST-MEM-002` — UI for review/edit/delete + tests
3. `ASSIST-MEM-003` — Prompt integration + guardrails + tests

---

### EXPORT-CHART-001 — Chart image export for clinician visits

**Priority:** P3  
**Suggested Labels:** `frontend`, `export`, `ux`

**Expected Deliverables**
- Frontend: “Download chart as PNG/SVG” action from Trends view (or export page).
- Compatibility: deterministic output size + includes labels/units/date range.
- Tests: UI unit test for export action wiring; manual QA checklist for at least Chromium.
- Docs: add a short “How to export charts” note in user docs.

**Key Context**
- Trends chart uses `recharts` (SVG) in `src/frontend/src/pages/TrendsDashboard.tsx`.

**Acceptance Criteria**
- [ ] User can export the current analyte chart as an image without screenshots.
- [ ] Output includes analyte name, units, and date range.
- [ ] CI passes (`frontend-tests`).
