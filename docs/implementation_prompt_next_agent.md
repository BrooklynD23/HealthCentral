# Implementation Prompt for Next Agent

## Mission (Updated 2026-01-31)

Ship the **MVP end-to-end first** (import → verify → trends → export), then implement the **RAG assistant**.

Sprint cadence: **1 week**.

The execution backlog (tickets + acceptance criteria + E2E matrix) lives in:
- `docs/06_mvp_to_rag_execution_board.md`

---

## Current Status: Sprint 5 Complete

### Completed Sprints

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 1 | Auth + Session Plumbing | ✅ Complete |
| Sprint 2 | Import → Extract → Normalize → Persist | ✅ Complete |
| Sprint 3 | Verification Workbench + Trends Dashboard | ✅ Complete |
| Sprint 4 | Export System End-to-End | ✅ Complete |
| Sprint 5 | RAG Assistant Pipeline | ✅ Complete |
| **Sprint 6** | **LLM Integration + E2E Testing** | ⏳ **NEXT** |

### What Was Done in Sprint 5

1. **Backend Chunking Module** (`src/backend/modules/chunking.py`) - Created:
   - Document text splitting with sentence boundary preservation
   - Configurable chunk size and overlap
   - Character position tracking for provenance
   - Multi-page PDF support

2. **Backend Embeddings Module** (`src/backend/modules/embeddings.py`) - Created:
   - Sentence-transformers integration (all-MiniLM-L6-v2)
   - Hash-based fallback for testing
   - Vector-to-blob storage conversion
   - Cosine similarity search

3. **Backend Glossary Module** (`src/backend/modules/glossary.py`) - Created:
   - 25+ curated medical term definitions
   - Plain-language explanations
   - Related terms linking
   - No medical advice content

4. **Backend Test Intent Module** (`src/backend/modules/test_intent.py`) - Created:
   - 16+ analyte purpose explanations
   - Educational content about test ordering reasons
   - Conservative, factual information

5. **RAGModule Updates** (`src/backend/modules/rag.py`) - Enhanced:
   - `retrieve_context_sync()` method for synchronous retrieval
   - `_search_vectors()` placeholder for vector store integration
   - Ready for LLM integration

6. **Assistant API** (`src/backend/api/assistant.py`) - Wired:
   - `/assistant/glossary/{term}` - Returns curated definitions
   - `/assistant/test-intent/{analyte}` - Returns test purpose info
   - `/assistant/chat` - Returns 501 until LLM configured

7. **Frontend Assistant Service** (`src/frontend/src/services/assistant.ts`) - Created:
   - `useSendMessage()` - Chat mutation hook
   - `useGlossaryLookup()` - Glossary query hook
   - `useTestIntentLookup()` - Test intent query hook
   - Citation formatting utilities

8. **ExplainAssistant Page** (`src/frontend/src/pages/ExplainAssistant.tsx`) - Wired:
   - Real API integration with useSendMessage hook
   - Citation display with source links
   - Verification info display
   - Error handling (501, 401, network)
   - Insufficient context indicators

9. **Tests** - All passing:
   - Backend: 27 RAG pipeline tests in `src/backend/tests/test_rag_pipeline.py`
   - Frontend: 12 tests in `src/frontend/src/__tests__/ExplainAssistant.test.tsx`
   - Total backend tests: 110 passing
   - Total frontend tests: 51 passing

---

### What Was Done in Sprint 4

1. **Backend Export API** (`src/backend/api/export.py`) - Fully wired:
   - `GET /export/csv` - Returns CSV data for authenticated profile
   - `GET /export/json` - Returns JSON data for authenticated profile
   - `POST /export/doctor-summary` - Generates clinician-ready summary
   - `GET /export/doctor-summary/{id}/download` - Downloads generated summary
   - `POST /export/questions` - Generates discussion prompts
   - All endpoints use `ProfileDbSession` for data isolation
   - Audit logging for all export actions

2. **Frontend Export Service** (`src/frontend/src/services/export.ts`) - Created:
   - `useExportCSV()` - Mutation for CSV download
   - `useExportJSON()` - Mutation for JSON download
   - `useGenerateSummary()` - Mutation for summary generation
   - `useDownloadSummary()` - Mutation for summary download
   - `useGenerateQuestions()` - Mutation for questions generation

3. **ExportPage.tsx** - Fully wired to real API:
   - CSV/JSON download buttons
   - Summary generation with key findings display
   - Summary download after generation
   - Section toggles for customization
   - Real document list from API

4. **Tests** - All passing:
   - Backend: 17 tests in `src/backend/tests/test_export_api.py`
   - Frontend: 11 tests in `src/frontend/src/__tests__/ExportPage.test.tsx`
   - Total frontend tests: 39 passing

---

## Sprint 6 Focus: LLM Integration + E2E Testing

### Objective

Complete the RAG assistant by integrating a local LLM and running full end-to-end tests.

### Tickets

#### S6-BE-001: LLM Integration

**Scope:** Integrate local LLM (llama.cpp or similar) for response generation.

**Files to Modify:**
- `src/backend/modules/rag.py` - Implement `generate_response()` with LLM inference
- `src/backend/core/model_runner.py` (NEW) - LLM inference wrapper

**Acceptance:**
- `/assistant/chat` returns grounded responses (no 501)
- Responses include `[cite:N]` citations
- Timeout handling for long responses

#### S6-BE-002: Vector Store Integration

**Scope:** Persist embeddings to profile DB and implement real vector search.

**Files to Modify:**
- `src/backend/modules/rag.py` - Implement `_search_vectors()` with DB lookup
- `src/backend/api/documents.py` - Trigger chunk+embed on import

**Acceptance:**
- Documents are chunked and embedded on import
- Vector search returns relevant chunks by similarity
- Filters (analyte, date) work correctly

#### S6-E2E-001: End-to-End Test Suite

**Scope:** Playwright tests for full user journeys.

**Tests:**
- E2E-RAG-001: No docs → insufficient context
- E2E-RAG-002: With docs → citations in response
- E2E-RAG-003: Prohibited request → safe refusal
- E2E-RAG-004: Glossary + test-intent return 200

---

## Sprint 5 Focus: RAG Assistant (Post-MVP) - COMPLETE

### Objective

Implement the RAG-based assistant for grounded explanations with citations.

### Tickets

#### S5-BE-001: Chunking + Embeddings Pipeline

**Scope:** Create/populate `Chunk` + `Embedding` from documents during import or background job.

**Files to Create/Modify:**
- `src/backend/modules/chunking.py` (NEW) - Document chunking logic
- `src/backend/modules/embeddings.py` (NEW) - Embedding generation
- `src/backend/api/documents.py` - Trigger chunking after import

**Tests FIRST:**
```
src/backend/tests/test_rag_pipeline.py:
├── API-RAG-INDEX-001: test_chunking_creates_chunks()
├── API-RAG-INDEX-002: test_embeddings_created_for_chunks()
└── API-RAG-INDEX-003: test_retrieval_returns_chunks_with_provenance()
```

**Acceptance:**
- Documents are chunked on import
- Embeddings are generated and stored in per-profile DB
- Chunks include provenance (page, snippet)

#### S5-BE-002: Implement RAGModule.retrieve_context()

**Scope:** Implement similarity search over stored embeddings.

**Files to Modify:**
- `src/backend/modules/rag.py` - Implement `retrieve_context()`

**Tests FIRST:**
```
src/backend/tests/test_rag_pipeline.py:
├── API-RAG-RETRIEVE-001: test_similarity_search_returns_top_k()
├── API-RAG-RETRIEVE-002: test_filter_by_analyte()
└── API-RAG-RETRIEVE-003: test_filter_by_date_range()
```

**Acceptance:**
- Top-k retrieval with similarity scores
- Analyte and date filtering work
- Returns provenance with each chunk

#### S5-BE-003: Implement RAGModule.generate_response()

**Scope:** Generate grounded responses with citations.

**Files to Modify:**
- `src/backend/modules/rag.py` - Implement `generate_response()`
- `src/backend/api/assistant.py` - Wire `/assistant/chat` endpoint

**Tests FIRST:**
```
src/backend/tests/test_rag_pipeline.py:
├── API-AST-CHAT-001: test_chat_returns_structured_response()
├── API-AST-CHAT-002: test_response_includes_citations()
└── API-AST-CHAT-003: test_refusal_for_prohibited_topics()
```

**Acceptance:**
- `/assistant/chat` returns structured response
- Response includes `[cite:N]` format citations
- Prohibited medical advice is refused

#### S5-BE-004: Implement Glossary + Test Intent

**Scope:** Local lookups powered by curated tables.

**Files to Modify:**
- `src/backend/api/assistant.py` - Wire glossary and test-intent endpoints

**Tests FIRST:**
```
src/backend/tests/test_rag_pipeline.py:
├── API-AST-GLOSSARY-001: test_glossary_lookup()
└── API-AST-INTENT-001: test_test_intent_lookup()
```

**Acceptance:**
- No `501` responses
- Returns conservative, cited content

#### S5-FE-001: Wire ExplainAssistant

**Scope:** Replace mock chat with real API.

**Files to Modify:**
- `src/frontend/src/services/assistant.ts` (NEW) - Assistant API hooks
- `src/frontend/src/pages/ExplainAssistant.tsx` - Wire to real API

**Tests FIRST:**
```
src/frontend/src/__tests__/ExplainAssistant.test.tsx:
├── FE-AST-001: test_chat_sends_message()
├── FE-AST-002: test_response_displays_citations()
└── FE-AST-003: test_empty_state_handled()
```

**Acceptance:**
- User can ask questions
- Response displays with citations
- Empty/error states handled

---

## Required Reading (in order)

1. `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md` (MVP scope + safety constraints)
2. `docs/06_mvp_to_rag_execution_board.md` (current sprint plan + test matrix)
3. `docs/05_backend_integration_status.md` (endpoint inventory)
4. `src/backend/modules/rag.py` - Review existing RAG module structure
5. `src/backend/api/assistant.py` - Review current 501 stubs to replace
6. `src/backend/models/chunk.py` - Existing Chunk model
7. `src/backend/models/embedding.py` - Existing Embedding model

---

## Current Repo State (Reality Check)

### Backend

- FastAPI backend is fully implemented for MVP
- Per-profile SQLCipher DB isolation is implemented
- **Export API** is fully implemented (Sprint 4)
- **Assistant API** currently returns `501` stubs - Sprint 5 target
- `Chunk`/`Embedding` models already exist but pipeline not populating them

### Frontend

- `ProfileSetup.tsx` - ✅ Uses real API with password auth
- `DocumentInbox.tsx` - ✅ Uses real API hooks
- `VerificationWorkbench.tsx` - ✅ Uses real API hooks
- `TrendsDashboard.tsx` - ✅ Uses real API hooks
- `ExportPage.tsx` - ✅ Uses real API hooks (Sprint 4)
- `ExplainAssistant.tsx` - ⏳ Mock-driven (Sprint 5 target)

### Auth System (Implemented in Sprint 1)

- `authStore.ts` - Zustand store for JWT token management
- `api.ts` - Adds `Authorization: Bearer <token>` header to all requests
- `ProtectedRoute.tsx` - Auth guard component

---

## Developer Commands (Windows)

- Start dev (recommended): `.\dev.ps1` or `.\dev.bat`
- Backend tests: `cd src/backend; pytest -v`
- Frontend tests: `cd src/frontend; npm test`
- Run specific test file: `npm test -- --run src/__tests__/ExplainAssistant.test.tsx`

---

## TDD Workflow Reminder

Follow Red-Green-Refactor strictly:

1. **RED** - Write failing test first
2. **Verify RED** - Run test, confirm it fails for the right reason
3. **GREEN** - Write minimal code to pass
4. **Verify GREEN** - Run test, confirm it passes
5. **REFACTOR** - Clean up while staying green

Never write implementation code before a failing test exists.

---

## Important Pitfalls / Guardrails

- Do not rely on `profile_id` query params for access control. Use the authenticated session.
- Keep all patient data in per-profile DB; master DB is reference/profile metadata only.
- RAG responses must cite sources with `[cite:N]` format.
- Refuse prohibited medical advice (diagnosis, treatment recommendations).
- Test all API calls with mocked responses using URL-based mocking (see TrendsDashboard/ExportPage tests for pattern).

---

## Files Reference for Sprint 5

### Backend
```
src/backend/api/assistant.py          # Wire to RAGModule (replace 501s)
src/backend/modules/rag.py            # Implement retrieve_context() and generate_response()
src/backend/modules/chunking.py       # NEW - Document chunking
src/backend/modules/embeddings.py     # NEW - Embedding generation
src/backend/models/chunk.py           # EXISTING - Chunk model
src/backend/models/embedding.py       # EXISTING - Embedding model
src/backend/tests/test_rag_pipeline.py # NEW - RAG pipeline tests
```

### Frontend
```
src/frontend/src/pages/ExplainAssistant.tsx       # Wire to real API
src/frontend/src/services/assistant.ts            # NEW - Assistant API hooks
src/frontend/src/__tests__/ExplainAssistant.test.tsx # NEW - Assistant tests
```

---

## E2E Cases for Sprint 5

| ID | Area | Scenario | Expected |
|----|------|----------|----------|
| E2E-RAG-001 | Assistant | No docs → chat | Returns "insufficient context" (no hallucinations) |
| E2E-RAG-002 | Assistant | With docs → chat | Response includes `[cite:N]` citations |
| E2E-RAG-003 | Assistant | Prohibited advice prompt | Safe refusal / guarded response |
| E2E-RAG-004 | Assistant | Glossary + test-intent | Endpoints return 200 with conservative content |
