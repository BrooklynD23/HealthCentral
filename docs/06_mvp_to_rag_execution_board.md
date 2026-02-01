# HealthCentral MVP → RAG Execution Board (1-Week Sprints)

**Last updated:** 2026-01-31  
**Sprint length:** 1 week  
**Priority:** MVP first, then RAG  

This board is a repo-aligned, test-first execution plan. It is meant to be used as a “ticket backlog” (GitHub Issues style) with explicit acceptance criteria and a complete E2E test matrix.

---

## 0) Guiding Principles (for scale)

- **Local-first + privacy-first:** no patient data leaves the device by default.
- **Session-gated access:** all per-profile data access is authorized via the active session (JWT Bearer token).
- **Per-profile isolation:** patient data lives in the per-profile SQLCipher DB; master DB contains reference + profile metadata.
- **No medical advice:** conservative refusals > speculation; every factual claim about user data must be grounded/cited.
- **Design for growth:** pagination, background jobs, and stable contracts from day 1.

---

## 1) Current Repo Reality (as of 2026-01-31)

### 1.1 Backend (FastAPI)

- Auth is Bearer-token based (`src/backend/core/auth.py`); endpoints depend on `RequireAuth`.
- Per-profile SQLCipher DB sessions are opened on profile create/login/unlock (`src/backend/core/profile_database.py`).
- **Assistant** endpoints exist but are effectively blocked by `RAGModule.generate_response()` raising `NotImplementedError` (`src/backend/modules/rag.py`).
- **Export** API endpoints exist but return `501` (`src/backend/api/export.py`); there is an `ExportModule` implementation (`src/backend/modules/export.py`) that should be used instead of creating a new export service.
- ✅ **PDF extraction**: table extraction AND `_extract_from_text()` are implemented (Sprint 2).
- ✅ Document import triggers extraction pipeline and persists observations (Sprint 2).
- `Chunk`/`Embedding` models already exist in the per-profile DB (`src/backend/models/chunk.py`, `src/backend/models/embedding.py`) but there is no pipeline populating them yet.

### 1.2 Frontend (Vite/React)

**Sprint 1-3 Complete:**
- ✅ API client sends `Authorization: Bearer <token>` header (`src/frontend/src/services/api.ts`).
- ✅ Auth state managed via Zustand store (`src/frontend/src/stores/authStore.ts`).
- ✅ Profile creation UI includes `password` field (`src/frontend/src/pages/ProfileSetup.tsx`).
- ✅ `DocumentInbox` wired to services.
- ✅ `VerificationWorkbench` wired to observations API (Sprint 3).
- ✅ `TrendsDashboard` wired to trends/panel APIs (Sprint 3).
- ⏳ `ExportPage` still mock-driven (Sprint 4 target).
- ⏳ `ExplainAssistant` still mock-driven (Sprint 5 target).

---

## 2) Quality Gates (Definition of Done)

### 2.1 Sprint-level DoD

- Backend unit + API integration tests pass: `cd src/backend && pytest -v`.
- Frontend unit/component tests pass: `cd src/frontend && npm test`.
- E2E smoke suite passes on Windows: `npm run e2e` (Playwright) or equivalent scripted runner.
- No `501` responses on any UI-reachable endpoint for that sprint’s scope.
- Error states are user-friendly (no unhandled promise rejections; no blank screens).

### 2.2 Release-level DoD (MVP)

E2E workflows (happy path + key negatives):
1) Create profile (with password) → unlock session → land in inbox  
2) Import PDF → observations created → document status updated  
3) Verify/edit observation → audit/version updated → needs-verification list updates  
4) Trends dashboard → real data time series + empty state  
5) Export CSV/JSON + generate summary + download summary  

---

## 3) Test ID Scheme (traceable to tickets)

- `API-*` = backend integration tests (FastAPI + DB)
- `FE-*` = frontend unit/component tests (Vitest + Testing Library)
- `E2E-*` = end-to-end tests (Playwright driving real UI against real backend)

Example: `S1-FE-002` references `FE-AUTH-003` and `E2E-AUTH-001`.

---

## 4) Sprint Plan (1 week each)

### Sprint 1 — Auth + Session Plumbing (unblocks everything)

**Outcome:** Frontend can create/unlock/login and call protected APIs with `Authorization: Bearer <token>`.

#### Tickets

- **S1-FE-001 — Fix ProfileCreate contract**
  - **Problem:** backend requires `password`; frontend omits it.
  - **Scope:** update types, UI, and hooks usage to send password and handle TokenResponse.
  - **Acceptance:**
    - Create profile succeeds with password, stores `access_token`, and routes to inbox.
    - Wrong password on login/unlock shows a clear error.
  - **Tests:** `FE-AUTH-001`, `E2E-AUTH-001`, `E2E-AUTH-002`.

- **S1-FE-002 — Add Authorization header support to API client**
  - **Scope:** API client attaches Bearer token; add a single token source of truth (e.g., `authStore`).
  - **Acceptance:**
    - Any protected call succeeds once token is present.
    - Missing/expired token routes to unlock/login screen.
  - **Tests:** `FE-AUTH-002`, `E2E-AUTH-003`, `E2E-AUTH-004`.

- **S1-FE-003 — Session/lock UX**
  - **Scope:** handle 401 vs 403 (“not authenticated” vs “profile db not connected”) distinctly.
  - **Acceptance:**
    - 401 → prompt login
    - 403 “Profile database not available…” → prompt unlock
  - **Tests:** `E2E-AUTH-005`.

- **S1-E2E-001 — E2E harness setup (Playwright)**
  - **Scope:** add Playwright tests + a Windows-friendly runner script that starts backend+frontend, waits for readiness, runs E2E, then tears down.
  - **Acceptance:**
    - `E2E-AUTH-001` runs green on a clean checkout after install.
  - **Tests:** all `E2E-AUTH-*`.

#### E2E cases (Sprint 1)

- **E2E-AUTH-001:** create profile (password) → token stored → inbox loads documents endpoint (no 401/403)
- **E2E-AUTH-002:** create profile missing password → validation prevents submit
- **E2E-AUTH-003:** token missing → protected page redirects to login/unlock
- **E2E-AUTH-004:** invalid token → 401 → login screen
- **E2E-AUTH-005:** locked profile (no profile DB connection) → 403 → unlock screen

---

### Sprint 2 — Import → Extract → Normalize → Persist Observations (MVP foundation)

**Outcome:** importing a PDF creates `Observation` rows, sets document status, and returns correct counts.

#### Tickets

- **S2-BE-001 — Import triggers extraction pipeline**
  - **Scope:** wire `/documents/import` to extraction + normalization + observation creation; set `Document.status = "parsed"` on success.
  - **Acceptance:** `observations_extracted` reflects persisted observations; `needs_verification` computed from confidence/flags.
  - **Tests:** `API-IMPORT-001`, `E2E-IMPORT-001`.

- **S2-BE-002 — Implement `_extract_from_text()`**
  - **Scope:** robust regex-based extraction for narrative PDFs; capture provenance snippet + page.
  - **Acceptance:** text-only fixture yields non-zero observations with reasonable confidence.
  - **Tests:** `API-EXTRACT-001` (unit), `API-IMPORT-002`.

- **S2-BE-003 — Fixtures**
  - **Scope:** add `tests/fixtures/` PDFs: `sample_table.pdf`, `sample_text.pdf`, `sample_mixed.pdf` + expected outputs.
  - **Acceptance:** deterministic tests on Windows.
  - **Tests:** used by extraction/import tests.

#### E2E cases (Sprint 2)

- **E2E-IMPORT-001:** import table PDF → observations list shows rows
- **E2E-IMPORT-002:** import text PDF → observations created
- **E2E-IMPORT-003:** duplicate import → handled deterministically (no silent double-write)
- **E2E-IMPORT-004:** unsupported file type → 400 + friendly UI message

---

### Sprint 3 — Verification Workbench + Trends Dashboard (real data)

**Outcome:** verify/edit flow works and trends show real time series.

#### Tickets

- **S3-FE-001 — Wire VerificationWorkbench to observations API**
  - **Scope:** replace mock data with `useObservations({ needs_verification: true })` and `useVerifyObservation()`.
  - **Acceptance:** verifying a row updates list and marks observation verified.
  - **Tests:** `FE-VERIFY-001`, `E2E-VERIFY-001`.

- **S3-FE-002 — Source preview integration**
  - **Scope:** preview provenance using document pages endpoint.
  - **Acceptance:** selecting a row shows page text including snippet highlight (basic).
  - **Tests:** `FE-VERIFY-002`, `E2E-VERIFY-002`.

- **S3-FE-003 — Wire TrendsDashboard**
  - **Scope:** replace mock chart data with `/observations/trends/{analyte}`; analyte list sourced from API.
  - **Acceptance:** chart renders for analytes with values; empty states handled.
  - **Tests:** `FE-TRENDS-001`, `E2E-TRENDS-001`.

#### E2E cases (Sprint 3)

- **E2E-VERIFY-001:** verify an observation → disappears from “needs verification”
- **E2E-VERIFY-002:** edit numeric value and verify → trend reflects update
- **E2E-TRENDS-001:** view analyte trend after import
- **E2E-TRENDS-002:** empty profile (no observations) → empty state

---

### Sprint 4 — Export System End-to-End (CSV/JSON + doctor summary + questions)

**Outcome:** export endpoints implemented and `ExportPage` is wired.

#### Tickets

- **S4-BE-001 — Implement export endpoints using `ExportModule`**
  - **Scope:** implement `/export/csv`, `/export/json`, `/export/questions`, `/export/doctor-summary`, `/export/doctor-summary/{id}/download`.
  - **Acceptance:** no `501`; outputs contain only authenticated profile data.
  - **Tests:** `API-EXPORT-001..004`, `E2E-EXPORT-001`.

- **S4-FE-001 — Wire ExportPage**
  - **Scope:** call export endpoints and support download UX.
  - **Acceptance:** user can download CSV/JSON and generate+download summary.
  - **Tests:** `FE-EXPORT-001`, `E2E-EXPORT-001`.

#### E2E cases (Sprint 4)

- **E2E-EXPORT-001:** download CSV/JSON after import+verify
- **E2E-EXPORT-002:** generate summary → download → file not empty
- **E2E-EXPORT-003:** export with analyte/date filters

---

### Sprint 5 — Assistant (RAG) (post-MVP)

**Outcome:** `/assistant/chat` works with citations + verification metadata; glossary/test-intent endpoints work.

#### Tickets

- **S5-BE-001 — Chunking + embeddings pipeline**
  - **Scope:** create/populate `Chunk` + `Embedding` from documents during import or background job; store in per-profile DB.
  - **Acceptance:** retrieval can return chunks for a profile with provenance.
  - **Tests:** `API-RAG-INDEX-001`, `E2E-RAG-001` (setup).

- **S5-BE-002 — Implement `RAGModule.retrieve_context()`**
  - **Scope:** implement similarity search over stored embeddings (FAISS or SQLite-based approach), with analyte/date filters.
  - **Acceptance:** deterministic top-k retrieval on fixtures.
  - **Tests:** `API-RAG-RETRIEVE-001..`.

- **S5-BE-003 — Implement `RAGModule.generate_response()`**
  - **Scope:** use existing `ModelSelector.run_inference()`; enforce `[cite:N]` formatting; handle timeouts.
  - **Acceptance:** `/assistant/chat` returns structured sections and passes validation for citations.
  - **Tests:** `API-AST-CHAT-001`, `E2E-RAG-002`.

- **S5-BE-004 — Implement glossary + test-intent**
  - **Scope:** local lookups powered by curated tables or bundled JSON; return stable definitions.
  - **Acceptance:** no `501`; results are conservative and cite sources where applicable.
  - **Tests:** `API-AST-GLOSSARY-001`, `API-AST-INTENT-001`.

- **S5-FE-001 — Wire ExplainAssistant**
  - **Scope:** replace mock chat with `/assistant/chat`; display citations + verification info.
  - **Tests:** `FE-AST-001`, `E2E-RAG-003`.

#### E2E cases (Sprint 5)

- **E2E-RAG-001:** ask question with no docs → “insufficient context”
- **E2E-RAG-002:** ask question with docs → response contains citations
- **E2E-RAG-003:** prohibited advice request → refusal/safe response
- **E2E-RAG-004:** glossary lookup and test intent endpoints return 200

---

## 5) API Contract Notes (stability + scale)

- **Avoid `profile_id` query params for patient data access control.** Use the session’s `profile_id` server-side.
- **Pagination:** add `limit`, `cursor` (or `offset`) to list endpoints early to prevent UI regressions with large datasets.
- **Idempotency:** document import should be idempotent by `content_hash` + profile.
- **Async jobs:** extraction/embedding should be designed to move to background jobs without breaking contracts:
  - return `Document.status = pending|parsed|error`
  - add “processing status” endpoints if needed

---

## 6) E2E Test Matrix (minimum set)

This matrix is intentionally redundant across layers; it is used to ensure “no surprises” in end-to-end demos and future CI.

| ID | Area | Scenario | Expected |
|----|------|----------|----------|
| E2E-AUTH-001 | Auth | Create profile (with password) | Token stored; inbox loads without 401/403 |
| E2E-AUTH-002 | Auth | Missing password on create | UI blocks submit or shows validation error |
| E2E-AUTH-003 | Auth | Token missing | Protected route redirects to login/unlock |
| E2E-AUTH-004 | Auth | Invalid/expired token | 401 handled; user prompted to login |
| E2E-AUTH-005 | Auth | Locked profile with valid token | 403 handled; user prompted to unlock |
| E2E-AUTH-006 | Auth | Multi-profile isolation | Profile A token cannot access Profile B data |
| E2E-IMPORT-001 | Import | Import table PDF | Observations persisted; document status becomes `parsed` |
| E2E-IMPORT-002 | Import | Import text PDF | Observations persisted (non-zero) |
| E2E-IMPORT-003 | Import | Duplicate import | Deterministic behavior (no silent duplication) |
| E2E-IMPORT-004 | Import | Unsupported file type | 400 + user-friendly error |
| E2E-IMPORT-005 | Import | Corrupted PDF | 400/500 handled; document marked `error` (no crash) |
| E2E-VERIFY-001 | Verify | View needs-verification list | Rows load from API (no mock) |
| E2E-VERIFY-002 | Verify | Edit numeric + verify | Value persists; version increments; row marked verified |
| E2E-VERIFY-003 | Verify | Invalid numeric input | UI shows validation error; request not sent |
| E2E-VERIFY-004 | Verify | Invalid date input | UI shows validation error; request not sent |
| E2E-VERIFY-005 | Verify | Verify without edits | Row marked verified; audit log created |
| E2E-TRENDS-001 | Trends | Trend chart shows series | Real points render; units + ref range display |
| E2E-TRENDS-002 | Trends | Empty state | No observations → clear empty state |
| E2E-TRENDS-003 | Trends | Date filters | Series respects filter range |
| E2E-EXPORT-001 | Export | Download CSV | File downloads; contains expected headers + rows |
| E2E-EXPORT-002 | Export | Download JSON | JSON parses; contains expected fields |
| E2E-EXPORT-003 | Export | Export empty profile | CSV/JSON returns empty dataset without error |
| E2E-EXPORT-004 | Export | Generate summary + download | Summary created; download is non-empty |
| E2E-EXPORT-005 | Export | Generate questions | Returns discussion prompts (no medical advice) |
| E2E-RAG-001 | Assistant | No docs → chat | Returns “insufficient context” (no hallucinations) |
| E2E-RAG-002 | Assistant | With docs → chat | Response includes `[cite:N]` citations and verification metadata |
| E2E-RAG-003 | Assistant | Prohibited advice prompt | Safe refusal / guarded response (no diagnosis/treatment) |
| E2E-RAG-004 | Assistant | Glossary + test-intent | Endpoints return 200 with conservative content |
