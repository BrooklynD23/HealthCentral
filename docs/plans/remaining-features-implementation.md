# HealthCentral: Remaining Features Implementation Plan (Revised)

> Historical Reference: this document is not an active tracker. It captures a prior execution plan whose primary checklist items were completed and is retained for history.
> For active remaining work, use [`docs/features/TASK_LIST.md`](../features/TASK_LIST.md).

## Context

The HealthCentral MVP has a solid foundation: auth, document import, text PDF extraction, verification, trends, interpretations, medications, and a RAG assistant skeleton. However, several pipelines have gaps (hardcoded stubs, missing date persistence, unconnected modules) and OCR/export/settings UI are missing entirely. This plan completes the four priority areas to make the app end-to-end functional.

### Audit Corrections Applied
This revision addresses 10 findings from a code audit:
- Date fields (`collected_at`, `collection_date`) extracted but never persisted — blocks date-based RAG filters, trends, and export
- Singleton `ModelRunner`/`RAGModule` incompatible with per-user external API setting — needs request-scoped runner
- `content_hash` index already exists in model + migration — no new migration needed
- Dedup must happen in the API route (has DB context), not `IngestModule` (no DB context)
- `selected_panel` and `include_references` accepted by API but not functional in RAG pipeline
- Export download is text-only throughout the stack (backend, `api.ts`, `export.ts`, tests) — wider changes needed
- No cancel-download backend endpoint — don't promise cancel in Settings UI
- OCR plan must also cover direct image imports (`.png`/`.jpg`), not just scanned PDFs
- TrendsDashboard `_previousValue` issue already resolved — remove from plan
- VerifyModule stubs are dead code; production verification already works in API route

---

## Execution Order (Hard Dependencies)

1. **Phase 1A first** (date persistence), then 2A can proceed.
2. **Fix RAG request-scope architecture** before 2E/2F tests.
3. **Complete 3A** before 3B, then 3C.
4. **Complete backend contracts before frontend wiring** in each phase.

---

## Phase 1: PDF Processing Pipeline (Week 1-2)

### Checklist

- [x] Implement date persistence in `documents.py`
- [x] Replace `_canonicalize_analyte()` with `NormalizeModule` in `documents.py`
- [x] Add dedup check in import route and duplicate cleanup in `documents.py`
- [x] Add scanned/image detection + `pending_ocr` status in `extract.py`, `ingest.py`, `documents.py`
- [x] Add OCR methods for scanned PDFs and images in `extract.py`
- [x] Remove or delete dead VerifyModule stubs in `verify.py`

### 1A. Persist Extracted Dates (CRITICAL — unblocks Phase 2A, trends, export)
**Files:** `src/backend/api/documents.py` (~lines 203-232), `src/backend/modules/extract.py`
- **Problem:** `ExtractedObservation.collected_at` and `ExtractionResult.collection_dates` are populated by the extractor, but `documents.py` never maps them to `Observation.collected_at` or `Document.collection_date` during import.
- Add `collected_at=extracted_obs.collected_at` when constructing each `Observation` (line ~220). Parse the string date to `datetime`.
- After the extraction loop, set `document.collection_date` from `extraction_result.collection_dates[0]` (earliest date) if available.
- This is a ~5-line fix but unblocks date-based RAG filters, proper trend ordering, and export date ranges.

### 1B. Wire NormalizeModule into Import Pipeline
**Files:** `src/backend/api/documents.py` (~line 208), `src/backend/modules/normalize.py`
- Replace inline `_canonicalize_analyte()` with `NormalizeModule().normalize_analyte()` (has 40+ synonym mappings already built)
- One-line change, immediate data quality improvement

### 1C. Content-Hash Deduplication (in API route, not IngestModule)
**Files:** `src/backend/api/documents.py` (~line 171)
- **Correction:** `IngestModule` has no DB session — dedup cannot happen there. The TODO at `ingest.py:260` is misleading.
- After `ingest.import_document()` returns with `content_hash`, query `profile_db` for existing `Document` with matching `content_hash` BEFORE creating the new Document record.
- If duplicate found: clean up the encrypted file just stored by ingest, return 200 with existing document (not 201).
- No new Alembic migration needed — `content_hash` is already indexed in model (`document.py:48`) and migration (`001_initial_schema.py:54`).

### 1D. Scanned PDF Detection + Image Import Handling
**Files:** `src/backend/modules/extract.py`, `src/backend/modules/ingest.py` (~line 143), `src/backend/api/documents.py` (~line 509)
- Add `has_extractable_text()` check to ExtractModule (chars/page < 50 = scanned)
- In `ingest.py:detect_doc_type()`: for PDFs, call this check. Return `lab_pdf_scanned` if sparse text.
- In import route: if `doc_type` is `lab_pdf_scanned` or `lab_image` and OCR is disabled, set `document.status = "pending_ocr"` and skip extraction (instead of silently extracting 0 results or hardcoding "[OCR not yet implemented]").
- Update `documents.py:509` page preview for images to return `status: "pending_ocr"` info instead of hardcoded string.

### 1E. OCR Pipeline (Scanned PDFs + Images)
**Files:** `src/backend/requirements.txt`, `src/backend/modules/extract.py`, `src/backend/core/config.py`
- Uncomment `pillow`, `pytesseract`, `pdf2image` in requirements.txt
- Add `extract_from_scanned_pdf()`: pdf2image → pytesseract per page → feed through existing text parsers
- Add `extract_from_image()`: direct image → pytesseract → text parsing (for `.png`/`.jpg` imports, not just scanned PDFs)
- OCR observations get base confidence 0.4 (vs 0.5 for text) to trigger mandatory verification
- Gated by `ocr_enabled` config flag (default False)
- **Depends on:** 1A-1D complete, `tesseract-ocr` system package

### 1F. VerifyModule Cleanup (Low Priority)
**Files:** `src/backend/modules/verify.py`
- Production verification already works correctly in `api/observations.py:verify_observation` endpoint.
- **Do NOT duplicate existing route logic** into VerifyModule.
- Delete the dead stubs for simplicity.

### Phase 1 Acceptance Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| `API-IMPORT-DATE-001` | Import dated PDF | `Observation.collected_at` is non-null AND `Document.collection_date` is set |
| `API-IMPORT-NORM-001` | Import "Hemoglobin A1c" | Canonical stored as `hba1c` |
| `API-IMPORT-DEDUP-001` | Same file twice | Second call returns 200, same `document.id`, document count unchanged |
| `API-IMPORT-DEDUP-002` | Second-call cleanup | Removes orphaned newly-written `.bin` encrypted file |
| `API-OCR-STATE-001` | Scanned PDF with `ocr_enabled=false` | `status=pending_ocr`, no observations |
| `API-OCR-STATE-002` | Image import with `ocr_enabled=false` | `status=pending_ocr` |
| `API-OCR-EXTRACT-001` | Scanned/image with `ocr_enabled=true` | Observations exist, low confidence baseline (~0.4 start) |

---

## Phase 2: RAG System Completion (Week 2-3)

### Checklist

- [x] Add date/analyte/panel filters to `_search_vectors_async()` in `rag.py`
- [x] Implement reference retrieval path (knowledge base chunks) in `rag.py` + `knowledge_loader.py`
- [x] Remove sync threadpool retrieval path from `rag.py`
- [x] Wire chat history through API and prompt composition in `assistant.py` + `rag.py`
- [x] Add request-scoped external/local runner selection in `external_runner.py`, `assistant.py`, `rag.py`
- [x] Add graceful no-model fallback in `rag.py` + `assistant.py`
- [x] Add one migration for external API user settings

### 2A. Vector Search Filters (Date + Analyte + Panel)
**File:** `src/backend/modules/rag.py` (~lines 330-380)
- **Prereq:** Phase 1A (dates must be persisted for date filters to work)
- `_search_vectors_async()` accepts `selected_analytes`, `from_date`, `to_date` but ignores them
- Add SQLAlchemy WHERE clauses to the existing query at line 348:
  - Date: filter `Document.collection_date` between `from_date` and `to_date`
  - Analyte: join to `Observation` table, filter `Observation.analyte_canonical.in_(selected_analytes)`
- Also wire `selected_panel` parameter: map panel name → list of analytes using existing `PanelInterpretation` or a static panel→analyte mapping, then apply as analyte filter
- No new index migration needed — `Document.collection_date` and `Observation.collected_at` already have `index=True` in models

### 2B. Reference Corpus Retrieval
**Files:** `src/backend/modules/rag.py`, `src/backend/modules/knowledge_loader.py`
- **Problem:** `include_references=True` is accepted by the API and passed to RAG, but retrieval only returns `source_type: "user_document"` chunks. No reference corpus path exists.
- Add a reference retrieval path using `KnowledgeLoader` biomarker data:
  - For each analyte mentioned in user query, fetch relevant knowledge entries
  - Format as reference chunks with `source_type: "reference"` and appropriate authority tier
- This enables the assistant to provide educational context alongside user-specific data

### 2C. Async Refactor for RAG Retrieval
**File:** `src/backend/modules/rag.py` (~lines 293-315)
- `retrieve_context_sync()` uses `ThreadPoolExecutor` hack to call async from sync context
- Refactor to use `await _search_vectors_async()` directly throughout
- Deprecate sync path; all callers are already in async FastAPI routes

### 2D. Conversation History Support
**Files:** `src/backend/modules/rag.py`, `src/backend/api/assistant.py`
- `ChatRequest` already has `history: list[ChatMessage]` field (assistant.py:60)
- `RAGModule.compose_prompt()` doesn't use it → extend to prepend conversation turns
- Add context window management: trim history if exceeding model context size
- Wire `request.history` through from `assistant.py:chat()` to RAG pipeline (currently only `question`, `selected_analytes`, `from_date`, `to_date`, `include_references` are passed at line 189-195)

### 2E. External API Backend (Opt-in) — Request-Scoped Architecture
**New file:** `src/backend/core/external_runner.py`
**Modify:** `src/backend/core/config.py`, `src/backend/core/model_runner.py`, `src/backend/api/assistant.py`, `src/backend/modules/rag.py`

- **Problem:** Current `ModelRunner` and `RAGModule` are global singletons (model_runner.py:290, assistant.py:128). A per-user `use_external_api` setting can't work with a single global runner — user A's preference would affect user B.
- **Solution:** Make runner selection request-scoped:
  1. Create `ExternalModelRunner` class in `external_runner.py` implementing same `generate()`/`generate_async()` interface
  2. Add factory function `get_runner_for_request(profile_settings) -> ModelRunner | ExternalModelRunner` that checks the user's `use_external_api` preference
  3. In `assistant.py:chat()`, resolve the runner per-request using the authenticated user's settings, then pass it to the RAG module: `rag.query(..., model_runner=runner)`
  4. Extend `RAGModule.query()` to accept an optional `model_runner` override instead of always using `self._model_runner`
  5. This keeps the singleton for the default case (local LLM) but allows per-request override for external API users
- Config: `external_api_provider` (None/"openai"/"anthropic"), `external_api_key`, `external_api_model`
- Alembic migration: add `use_external_api: bool = False`, `external_api_provider: str = ""`, `external_api_key_encrypted: str = ""` to `UserModelSettings`
- **Privacy safeguard:** Default off. Frontend must show consent dialog explaining data leaves device.

### 2F. Graceful No-Model Fallback
**Files:** `src/backend/modules/rag.py`, `src/backend/api/assistant.py`
- When no LLM available (local not downloaded, external not configured): return rule-based response using knowledge base + biomarker data instead of 501 error
- Use `knowledge_loader.py` and `glossary.py` to compose informative non-LLM responses
- Flag response as `source: "knowledge_base"` (not LLM-generated)

### Phase 2 Acceptance Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| `API-RAG-FILTER-DATE-001` | Date-constrained query | Returns chunks only from documents within date range |
| `API-RAG-FILTER-ANALYTE-001` | Analyte filter | Excludes unrelated analytes from results |
| `API-RAG-FILTER-PANEL-001` | `selected_panel=lipid` | Maps to lipid analytes and filters correctly |
| `API-RAG-REF-001` | `include_references=true` | Returns at least one citation with `source_type=reference` |
| `API-RAG-HISTORY-001` | Second-turn response | Changes when prior turn included (history applied) |
| `API-RAG-RUNNER-ISOLATION-001` | User A external / User B local | Concurrent requests use correct runner each time |
| `API-RAG-NOMODEL-001` | No model available | Returns 200 knowledge-base response, never 501 |

---

## Phase 3: Export — HTML + PDF Generation (Week 3)

### Checklist

- [x] Add HTML renderer in `export.py`
- [x] Add format-aware download endpoint in `export.py` (text/html/pdf)
- [x] Add PDF rendering with WeasyPrint fallback in `export.py`
- [x] Add `apiGetRaw()` in `api.ts`
- [x] Rewrite summary download flow for content-type aware blobs in `export.ts`
- [x] Add format selector UI + fix `mutateAsync(undefined)` + questions param bug in `ExportPage.tsx` and `export.ts`
- [x] Update tests in `ExportPage.test.tsx`

### 3A. HTML Summary Template
**Files:** `src/backend/modules/export.py`, `src/backend/api/export.py` (~line 279)
- Add `render_html_summary(summary_data: dict) -> str` method to export module
- Inline-CSS HTML template (print/email compatible) with:
  - HealthCentral header with accent color (#2D7D6F)
  - Date range, key findings with color-coded severity flags
  - Organized sections (abnormal results, trends, panels)
  - Questions section for clinician discussion
  - Footer disclaimer ("AI-assisted summary, verify with provider")
- Update download endpoint at `export.py:279`:
  - Accept `format` query parameter (default "text")
  - `format=html` → call `render_html_summary()`, return `Response(content=html, media_type="text/html")` with `Content-Disposition: attachment; filename=*.html`
  - Keep `format=text` as current behavior (backward compatible)

### 3B. PDF Generation via WeasyPrint
**Files:** `src/backend/requirements.txt`, `src/backend/modules/export.py`, `src/backend/api/export.py`
- Add `weasyprint>=60.0` to requirements.txt (needs system `libpango`, `libgdk-pixbuf`)
- Add `render_pdf_summary(summary_data: dict) -> bytes`: call `render_html_summary()` → WeasyPrint → PDF bytes
- Update download endpoint: `format=pdf` → return `Response(content=pdf_bytes, media_type="application/pdf")`
- Graceful fallback: if WeasyPrint not installed → 501 with helpful error message listing required system packages
- **Depends on:** 3A (reuses HTML template)

### 3C. Frontend Export Overhaul
**Files:** `src/frontend/src/services/api.ts`, `src/frontend/src/services/export.ts`, `src/frontend/src/pages/ExportPage.tsx`, `src/frontend/src/__tests__/ExportPage.test.tsx`
- **Problem:** The entire download stack assumes text:
  - `api.ts:67` always calls `response.json()` — no binary support
  - `export.ts:77` `downloadSummary()` calls `apiGet<string>` → JSON parsed
  - `export.ts:155` `useDownloadSummary` creates `text/plain` blob
  - `ExportPage.test.tsx:162` mocks download as string return
- **Changes needed:**
  1. Add `apiGetRaw(endpoint, params)` to `api.ts` that returns the raw `Response` object (not JSON-parsed), allowing caller to check `Content-Type` header and handle accordingly
  2. Rewrite `downloadSummary()` in `export.ts` to use `apiGetRaw()`, pass `format` query param, detect response content-type, create appropriate blob (`text/plain`, `text/html`, or `application/pdf`)
  3. Update `useDownloadSummary` to accept format parameter, use correct file extension (`.txt`/`.html`/`.pdf`)
  4. Add format selector (Text / HTML / PDF) to `ExportPage.tsx` sidebar
  5. Fix `mutateAsync(undefined)` → `mutateAsync()` at ExportPage.tsx:97
  6. Fix `generateQuestions()` in `export.ts:86` — params are built (lines 82-84) but never passed to `apiPost`
  7. Update `ExportPage.test.tsx` to cover new format scenarios

### Phase 3 Acceptance Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| `API-EXPORT-DOWNLOAD-TEXT-001` | Default / `format=text` | Returns `text/plain`, `.txt` file |
| `API-EXPORT-DOWNLOAD-HTML-001` | `format=html` | Returns `text/html`, `.html` file |
| `API-EXPORT-DOWNLOAD-PDF-001` | `format=pdf` with WeasyPrint | Valid PDF header bytes (`%PDF`) |
| `API-EXPORT-DOWNLOAD-PDF-002` | Missing WeasyPrint | Returns 501 with dependency hint message |
| `FE-EXPORT-BLOB-001` | Download uses raw response | Correct file extension by content-type |
| `FE-EXPORT-QUESTIONS-001` | Questions with dates | `from_date`/`to_date` are sent to `/export/questions` |
| `FE-EXPORT-REGRESSION-001` | Existing text download | Path still passes unchanged |

---

## Phase 4: Frontend Integration & Polish (Week 3-4)

### Checklist

- [x] Add settings service in `modelSettings.ts`
- [x] Add settings page in `SettingsPage.tsx`
- [x] Wire route and sidebar nav in `App.tsx`, Sidebar component
- [x] Add external API consent + save flow
- [x] Update assistant UI for model-availability banner, history, filters, verification display in `ExplainAssistant.tsx`
- [x] Run frontend API signature audit/fixes across `src/frontend/src/services/`

### 4A. Fix Pre-existing TypeScript Errors
**Files:** `src/frontend/src/pages/ExportPage.tsx:97`
- ExportPage: `mutateAsync(undefined)` → `mutateAsync()` (or handle as part of 3C)
- TrendsDashboard `_previousValue` issue is already resolved — no action needed

### 4B. Model Settings Page (No Cancel Support)
**New files:** `src/frontend/src/services/modelSettings.ts`, `src/frontend/src/pages/SettingsPage.tsx`
**Modify:** `src/frontend/src/App.tsx` (route), Sidebar/nav component
- Service layer: `useModelSettings()`, `useDetectHardware()`, `useSetTier()`, `useDownloadModel()`, `useDownloadProgress()` hooks
- Settings page with:
  - Hardware info card (RAM, CPU, GPU detection results)
  - Model tier selector (Low/Mid/High) with recommended badge based on hardware
  - Download progress indicator (progress polling, **no cancel button** — backend has no cancel endpoint; note: model_settings.py:493 acknowledges it can't update DB from background task, so progress may be approximate)
  - External API section: provider dropdown (OpenAI/Anthropic), API key input (encrypted storage), model selector, **privacy consent toggle with explicit dialog** explaining data leaves device
  - Current model status display
- Follow existing patterns: CVA variants, Card composition, Radix UI components
- Add `/settings` route and Sidebar nav link (gear icon)
- **Depends on:** Phase 2E (external API config must exist for the toggle to wire to)

### 4C. ExplainAssistant Polish
**File:** `src/frontend/src/pages/ExplainAssistant.tsx`
- Add "model not available" banner with link to Settings page (instead of generic 501 error display)
- Wire conversation history: store messages in component state → include as `history` in `ChatRequest` body
- Add analyte/date/panel filter controls in sidebar (the backend accepts `selected_analytes`, `selected_panel`, `from_date`, `to_date` — frontend doesn't expose them)
- Add verification score display: show faithfulness score badge and source authority indicators on response segments
- **Depends on:** Phase 2D (history), 2F (no-model fallback), 4B (settings link)

### 4D. Frontend API Signature Audit + Fixes
**All service files in:** `src/frontend/src/services/`
- Confirmed matching: documents, observations, interpretations, medications, assistant
- Fix `export.ts:86`: `generateQuestions` builds filter params but never passes them to `apiPost` call
- Ensure all error responses handled gracefully (not just 401)
- Add missing loading/empty states where needed across all pages

### Phase 4 Acceptance Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| `FE-SETTINGS-ROUTE-001` | `/settings` route and nav | Renders without errors |
| `FE-SETTINGS-HARDWARE-001` | Hardware + tier data | Renders from API response |
| `FE-SETTINGS-DOWNLOAD-001` | Progress polling | Displays without cancel action |
| `FE-SETTINGS-CONSENT-001` | External API toggle | Requires explicit consent dialog before saving |
| `FE-AST-HISTORY-001` | Outgoing chat payload | Includes `history` field with prior messages |
| `FE-AST-FILTERS-001` | Outgoing payload | Includes selected analyte/date/panel |
| `FE-AST-MODEL-BANNER-001` | Model unavailable state | Shows banner with settings link |

---

## Sprint Schedule

| Sprint | Tasks | Can Parallelize | Notes |
|--------|-------|-----------------|-------|
| **Week 1** | 1A, 1B, 1C, 1D, 1F, 4A, 4D | Yes (all independent) | 1A is highest priority (unblocks 2A) |
| **Week 2** | 1E, 2A, 2B, 2C, 3A | 2B+2C+3A parallel; 1E after week 1; 2A after 1A | |
| **Week 3** | 2D, 2E, 2F, 3B, 3C | 2D+2E+2F parallel; 3B after 3A; 3C after 3A+3B | |
| **Week 4** | 4B, 4C, integration testing | 4B after 2E; 4C after 2D+2F | |

## Dependency Graph
```
1A (persist dates) ────────> 2A (date filters) ──> 4C (assistant filters)
1B (normalize) ───────────> (standalone)
1C (dedup) ───────────────> (standalone)
1D (scanned detection) ───> 1E (OCR)
1F (verify cleanup) ──────> (standalone, low priority)

2B (reference corpus) ────> (standalone)
2C (async refactor) ──────> (standalone)
2D (conversation history) ─> 4C (assistant polish)
2E (external API) ────────> 4B (settings UI)
2F (no-model fallback) ───> 4C (assistant polish)

3A (HTML template) ───────> 3B (PDF gen) ──> 3C (export FE overhaul)

4A (TS fix) ──────────────> (standalone, or absorbed into 3C)
4D (API audit) ───────────> (standalone, do first)
```

## Release Gates

```bash
cd src/backend && pytest -q
cd src/frontend && npm test
cd src/frontend && npm run build
```

- No 501 on UI-reachable happy paths except explicit optional dependency fallbacks (WeasyPrint missing).

## Alembic Migrations Needed
1. `UserModelSettings.use_external_api: bool = False` + `external_api_provider`, `external_api_key_encrypted` columns (Phase 2E)
- **Note:** `content_hash` index already exists. `collection_date` index already exists on model. No other migrations needed.

## New Dependencies to Add
- `weasyprint>=60.0` in requirements.txt (Phase 3B) — optional, with graceful fallback
- Uncomment `pillow`, `pytesseract`, `pdf2image` (Phase 1E) — gated by config flag
- System packages: `tesseract-ocr` (1E), `libpango1.0-dev libgdk-pixbuf2.0-dev` (3B)

## New Files to Create
- `src/backend/core/external_runner.py` (Phase 2E)
- `src/frontend/src/services/modelSettings.ts` (Phase 4B)
- `src/frontend/src/pages/SettingsPage.tsx` (Phase 4B)
- 1 Alembic migration file (Phase 2E)

## Key Architectural Decisions
1. **Request-scoped runner selection** (not global singleton swap) for external API — preserves privacy for users who didn't opt in
2. **Dedup in API route** (not IngestModule) — that's where the DB session lives
3. **`apiGetRaw()` for binary downloads** — avoids breaking existing `apiGet()` JSON contract
4. **No cancel-download in Settings UI** — backend doesn't support it; showing a fake cancel button would be dishonest
5. **VerifyModule cleanup, not wiring** — production verification already works; adding a wrapper layer adds complexity without value

---

## Post-Commit Audit Addendum (HEAD `dccb5f0`)

This addendum captures remaining implementation work found after reviewing the latest commit.
It **supersedes the completed checkboxes above** for the listed items.

### Open Issues Summary

| ID | Severity | Finding | Evidence |
|----|----------|---------|----------|
| `HC-REM-001` | ~~Critical~~ **RESOLVED** | Settings API route mismatch between frontend and backend | Already correct: FE uses `/settings/model/*` matching BE prefix |
| `HC-REM-002` | ~~Critical~~ **RESOLVED** | External API opt-in not persisted end-to-end | Added GET/PUT `/external-api` endpoints + FE hooks + SettingsPage wiring |
| `HC-REM-003` | ~~Critical~~ **RESOLVED** | External runner lookup uses wrong DB session scope | Changed `get_runner_for_request()` to accept `profile_db`; updated assistant.py call site |
| `HC-REM-004` | ~~High~~ **RESOLVED** | Duplicate import likely returns `201` instead of `200` | Added `responses={200: ...}` to OpenAPI spec; runtime already correct |
| `HC-REM-005` | ~~High~~ **RESOLVED** | `Observation.collected_at` remains mostly null after extraction | Propagated dates from document/page level to each `ExtractedObservation.collected_at` |
| `HC-REM-006` | ~~High~~ **RESOLVED** | FE CSV/JSON export parsing is inconsistent with backend content types | Previously resolved with `apiGetRaw()` |
| `HC-REM-007` | ~~Medium~~ **RESOLVED** | `selected_panel` filter accepted by API but not sent from UI | Added panel selector `<select>` in ExplainAssistant + included in chat request |
| `HC-REM-008` | ~~Medium~~ **RESOLVED** | RAG singleton still holds mutable request state (`set_profile_db`) | Removed `set_profile_db()`; `profile_db` now passed as parameter through `query()` → `retrieve_context()` → `_search_vectors_async()` |
| `HC-REM-009` | ~~Low~~ **RESOLVED** | Download progress UX and persistence are incomplete | Added `_write_download_status()` helper using PerProfileDatabaseManager; FE polling derives from progress data statuses |

---

## TDD Implementation Plan for Remaining Issues

### Working Agreement for Agents

For every issue below:
1. Add failing tests first.
2. Run only targeted test files while implementing.
3. Implement minimal code to pass.
4. Refactor without changing behavior.
5. Re-run targeted tests, then full backend/frontend suites.

Use these commands during implementation:

```bash
# backend (targeted)
cd src/backend && pytest -q <test_file>::<test_name>

# frontend (targeted)
cd src/frontend && npm test -- <test_file>
```

---

### `HC-REM-001` Settings API Route Mismatch

**Goal:** frontend model settings service uses backend path contract.

**Write failing tests first**
1. Add `FE-SETTINGS-API-001` in `src/frontend/src/__tests__/api.test.ts`:
   - Assert model settings calls hit `/api/v1/settings/model` paths (not `/model-settings`).
2. Add/extend settings page integration test `FE-SETTINGS-API-002` in new file `src/frontend/src/__tests__/SettingsPage.test.tsx`:
   - Mock successful responses on `/settings/model`, `/settings/model/tiers`, `/settings/model/download-progress`.
   - Expect page to render without request failures.

**Implementation steps**
1. Update `src/frontend/src/services/modelSettings.ts` endpoint paths to `/settings/model...`.
2. Verify exports in `src/frontend/src/services/index.ts` still compile.
3. Ensure no remaining `/model-settings` references in frontend.

**Expected green results**
1. All settings API tests pass with correct URL expectations.
2. Settings page renders from real backend route contract.

---

### `HC-REM-002` External API Opt-In Persistence (Backend + Frontend)

**Goal:** user can explicitly save and load external provider settings with consent.

**Write failing tests first**
1. Add `API-MODEL-EXTERNAL-001` in new file `src/backend/tests/test_model_settings_api.py`:
   - `PUT /api/v1/settings/model/external-api` persists `use_external_api`, provider, model, encrypted key.
2. Add `API-MODEL-EXTERNAL-002`:
   - Enabling external API without consent/ack flag returns `400`.
3. Add `API-MODEL-EXTERNAL-003`:
   - `GET /api/v1/settings/model/external-api` returns masked/safe shape (`api_key_configured=true`) and never plaintext key.
4. Add `FE-SETTINGS-EXTERNAL-001` in `src/frontend/src/__tests__/SettingsPage.test.tsx`:
   - After consent dialog confirmation and save action, frontend sends payload to external settings endpoint.

**Implementation steps**
1. Add request/response models and endpoints in `src/backend/api/model_settings.py`:
   - `GET /external-api`
   - `PUT /external-api`
2. Store external key encrypted-at-rest (or with existing project crypto abstraction); never return raw key.
3. Extend `src/frontend/src/services/modelSettings.ts` with hooks:
   - `useExternalApiSettings()`
   - `useSaveExternalApiSettings()`
4. Wire save/load into `src/frontend/src/pages/SettingsPage.tsx`:
   - Load initial values.
   - Save only after consent.
   - Show success/error feedback.

**Expected green results**
1. Backend API tests prove persistence and privacy-safe responses.
2. Frontend test proves consent-gated save behavior.
3. External settings survive page reload and are user-specific.

---

### `HC-REM-003` Runner Lookup Must Use Profile DB Scope

**Goal:** per-user external runner selection reads profile-scoped settings from the correct DB.

**Write failing tests first**
1. Add `API-RAG-RUNNER-SCOPE-001` in `src/backend/tests/test_rag_pipeline.py`:
   - Runner lookup reads `UserModelSettings` from profile DB session.
2. Add `API-RAG-RUNNER-SCOPE-002`:
   - Two users with different settings resolve different runners in concurrent requests.

**Implementation steps**
1. Change `get_runner_for_request(...)` in `src/backend/core/external_runner.py` to accept profile DB session explicitly.
2. Update `src/backend/api/assistant.py` to pass `profile_db` (not master `db`) for runner lookup.
3. Keep `master_db` usage only where master tables/knowledge are required.

**Expected green results**
1. Runner selection is correctly user-scoped.
2. No cross-user preference leakage in concurrent chat requests.

---

### `HC-REM-004` Duplicate Import Must Return HTTP 200

**Goal:** duplicate upload returns `200 OK`; fresh upload remains `201 Created`.

**Write failing tests first**
1. Add `API-IMPORT-DEDUP-HTTP-001` in new file `src/backend/tests/test_documents_api.py`:
   - First upload returns `201`.
   - Second upload of same file returns `200`.
2. Add `API-IMPORT-DEDUP-HTTP-002`:
   - Second response document ID equals first response document ID.

**Implementation steps**
1. Update `src/backend/api/documents.py` duplicate branch to explicitly set response status to `200` (e.g., `JSONResponse` or response override).
2. Keep non-duplicate path behavior unchanged (`201`).

**Expected green results**
1. Dedup status semantics match API contract.
2. Existing import behavior for new files remains unchanged.

---

### `HC-REM-005` Populate `ExtractedObservation.collected_at` Reliably

**Goal:** extracted observations carry collection datetime for trends/export/date filtering.

**Write failing tests first**
1. Add `API-EXTRACT-DATE-OBS-001` in `src/backend/tests/test_extraction_pipeline.py`:
   - Given report text with a collection date and multiple analyte lines, each extracted observation has `collected_at`.
2. Add `API-IMPORT-DATE-OBS-002` in `src/backend/tests/test_documents_api.py`:
   - After import, stored observations have non-null `collected_at`.
3. Add `API-TRENDS-DATE-003` in `src/backend/tests/test_rag_pipeline.py` or observations API tests:
   - Date filters include/exclude observations correctly using populated dates.

**Implementation steps**
1. In `src/backend/modules/extract.py`, propagate page/document date to each `ExtractedObservation.collected_at`.
2. Keep document-level `collection_dates` behavior intact.
3. Ensure parser supports all expected date formats already accepted by `_parse_date_string` in `documents.py`.

**Expected green results**
1. Observation rows have usable dates by default.
2. Trend sorting and date-range filters behave deterministically.

---

### `HC-REM-006` CSV/JSON Export Client Content Handling

**Goal:** frontend handles CSV/text and JSON downloads according to backend `Content-Type`.

**Write failing tests first**
1. Add `FE-EXPORT-CSV-CONTENT-001` in `src/frontend/src/__tests__/ExportPage.test.tsx`:
   - CSV export does not attempt JSON parse and triggers file download.
2. Add `FE-EXPORT-JSON-CONTENT-002`:
   - JSON export downloads valid JSON content and extension.
3. Add `FE-API-TEXT-001` in `src/frontend/src/__tests__/api.test.ts`:
   - New helper for text/raw handling returns plain text without JSON parse errors.

**Implementation steps**
1. Add a text/raw-safe API utility in `src/frontend/src/services/api.ts` (`apiGetText` or extend raw helper usage).
2. Update `src/frontend/src/services/export.ts` for CSV/JSON exports to use content-appropriate response handling.
3. Keep summary format download (`text/html/pdf`) behavior unchanged.

**Expected green results**
1. CSV exports succeed with `text/csv`.
2. JSON exports remain valid.
3. No runtime `response.json()` parse errors for CSV routes.

---

### `HC-REM-007` Send `selected_panel` From Explain Assistant UI

**Goal:** panel filter is user-selectable and included in chat request payload.

**Write failing tests first**
1. Add `FE-AST-PANEL-001` in `src/frontend/src/__tests__/ExplainAssistant.test.tsx`:
   - Selecting panel and sending question includes `selected_panel` in request body.
2. Add `FE-AST-PANEL-002`:
   - Clearing panel removes `selected_panel` from payload.

**Implementation steps**
1. Add panel selector control in `src/frontend/src/pages/ExplainAssistant.tsx`.
2. Track selected panel state and include it in `sendMessage.mutateAsync(...)`.
3. Ensure analyte/date filters still work together with panel selection.

**Expected green results**
1. Chat requests include panel context when selected.
2. Backend panel-to-analyte logic is now reachable from UI.

---

### `HC-REM-008` Remove Mutable `set_profile_db` from Singleton RAG

**Goal:** eliminate shared mutable request state in singleton `RAGModule`.

**Write failing tests first**
1. Add `API-RAG-ISOLATION-001` in `src/backend/tests/test_rag_pipeline.py`:
   - Two concurrent requests with different profile DB sessions never cross-read data.
2. Add `API-RAG-ISOLATION-002`:
   - `query(...)`/`retrieve_context(...)` require explicit `profile_db` parameter; no implicit module state.

**Implementation steps**
1. Refactor `src/backend/modules/rag.py`:
   - Remove `self._profile_db` and `set_profile_db()`.
   - Pass `profile_db` through `query()` -> `retrieve_context()` -> `_search_vectors_async()`.
2. Update `src/backend/api/assistant.py` call site to pass `profile_db` directly.
3. Remove now-obsolete tests/usages of `set_profile_db`.

**Expected green results**
1. No mutable DB pointer stored in singleton.
2. Concurrent chat requests are request-isolated by construction.

---

### `HC-REM-009` Model Download Progress Reliability

**Goal:** show accurate progress states and poll until terminal status.

**Write failing tests first**
1. Add `API-MODEL-DL-PROGRESS-001` in `src/backend/tests/test_model_settings_api.py`:
   - Start download -> status transitions to `pending`/`downloading`.
2. Add `API-MODEL-DL-PROGRESS-002`:
   - On completion/failure, persisted status updates to `completed`/`failed`.
3. Add `FE-SETTINGS-DL-PROGRESS-001` in `src/frontend/src/__tests__/SettingsPage.test.tsx`:
   - UI polling continues while any tier status is `pending` or `downloading`, not only while mutation is pending.

**Implementation steps**
1. In `src/backend/api/model_settings.py`, ensure background task writes terminal progress state to DB.
2. In `src/frontend/src/pages/SettingsPage.tsx`, derive polling enablement from progress statuses, not only mutation state.
3. Keep explicit UX note that progress may be approximate if backend cannot provide byte-level updates.

**Expected green results**
1. Progress survives past initial request lifecycle.
2. UI updates from pending to terminal states without manual refresh.

---

## Recommended Implementation Order for Remaining Work

1. `HC-REM-001`, `HC-REM-004`, `HC-REM-006` (quick contract fixes, unblock FE/BE integration).
2. `HC-REM-002`, `HC-REM-003`, `HC-REM-008` (architecture/privacy correctness).
3. `HC-REM-005`, `HC-REM-007` (feature completeness and filter reachability).
4. `HC-REM-009` (progress fidelity polish).

## Final Verification Gate for This Addendum

```bash
cd src/backend && pytest -q
cd src/frontend && npm test
cd src/frontend && npm run build
```

Pass condition: all tests introduced above are green, and no regressions in existing suites.
