# Implementation Prompt for Next Agent

## Mission (Updated 2026-02-01)

**All 6 sprints are complete!** The full MVP flow is working:
- Import → Extract → Normalize → Persist
- Verification Workbench
- Trends Dashboard
- Export System
- RAG Assistant with Local LLM

**Next Task: Full Repository Audit**

---

## Quick Start for Next Agent

1. **Mission**: Perform a comprehensive audit of the entire repository
2. **Goals**:
   - Review code quality and consistency across backend and frontend
   - Identify technical debt, TODOs, and incomplete implementations
   - Verify test coverage and identify gaps
   - Check for security vulnerabilities (OWASP Top 10)
   - Validate documentation accuracy
   - Ensure all endpoints are properly tested
   - Review error handling and edge cases

---

## Current Status: Sprint 6 Complete

### Completed Sprints

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 1 | Auth + Session Plumbing | ✅ Complete |
| Sprint 2 | Import → Extract → Normalize → Persist | ✅ Complete |
| Sprint 3 | Verification Workbench + Trends Dashboard | ✅ Complete |
| Sprint 4 | Export System End-to-End | ✅ Complete |
| Sprint 5 | RAG Assistant Pipeline | ✅ Complete |
| Sprint 6 | LLM Integration + E2E Testing | ✅ Complete |

### Test Results (as of Sprint 6)

- **Backend RAG Pipeline**: 40/40 tests passing
- All core functionality implemented and tested

---

## Repository Structure

```
HealthCentral/
├── src/
│   ├── backend/                    # FastAPI backend
│   │   ├── api/                    # API endpoints
│   │   │   ├── assistant.py        # RAG chat, glossary, test-intent
│   │   │   ├── documents.py        # Document import/management
│   │   │   ├── export.py           # CSV/JSON/summary export
│   │   │   ├── observations.py     # Observation CRUD
│   │   │   └── profiles.py         # Profile management
│   │   ├── core/                   # Core infrastructure
│   │   │   ├── auth.py             # JWT authentication
│   │   │   ├── config.py           # Settings management
│   │   │   ├── database.py         # Database connections
│   │   │   ├── model_runner.py     # LLM inference (Sprint 6)
│   │   │   └── profile_database.py # Per-profile SQLCipher
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── chunk.py            # RAG chunks
│   │   │   ├── document.py         # Document metadata
│   │   │   ├── embedding.py        # Vector embeddings
│   │   │   └── observation.py      # Lab observations
│   │   ├── modules/                # Business logic
│   │   │   ├── chunking.py         # Document chunking
│   │   │   ├── embeddings.py       # Embedding generation
│   │   │   ├── extract.py          # PDF extraction
│   │   │   ├── glossary.py         # Medical term definitions
│   │   │   ├── model_selector.py   # Tiered model management
│   │   │   ├── rag.py              # RAG pipeline
│   │   │   └── test_intent.py      # Test purpose explanations
│   │   └── tests/                  # Backend tests
│   │       ├── test_rag_pipeline.py # 40 tests
│   │       └── ...
│   └── frontend/                   # React frontend
│       ├── src/
│       │   ├── pages/              # Page components
│       │   │   ├── DocumentInbox.tsx
│       │   │   ├── ExplainAssistant.tsx
│       │   │   ├── ExportPage.tsx
│       │   │   ├── ProfileSetup.tsx
│       │   │   ├── TrendsDashboard.tsx
│       │   │   └── VerificationWorkbench.tsx
│       │   ├── services/           # API hooks
│       │   │   ├── api.ts          # Base API client
│       │   │   ├── assistant.ts    # Assistant API
│       │   │   └── export.ts       # Export API
│       │   └── stores/             # Zustand stores
│       │       └── authStore.ts    # Auth state
│       └── e2e/                    # Playwright E2E tests
│           ├── auth.spec.ts
│           └── assistant.spec.ts
├── scripts/
│   └── download_models.py          # Model download utility
├── docs/                           # Documentation
│   ├── implementation_prompt_next_agent.md (this file)
│   ├── 06_mvp_to_rag_execution_board.md
│   └── Local_First_Medical_Results_Companion_PRD_v0_1.md
└── models/                         # LLM models (gitignored)
```

---

## Audit Checklist

### 1. Code Quality Review

- [ ] Check for consistent code style (backend: Python, frontend: TypeScript)
- [ ] Review function/method documentation
- [ ] Identify unused imports and dead code
- [ ] Check for proper error handling patterns
- [ ] Review logging consistency
- [ ] Verify type annotations (Python) and TypeScript types

### 2. Security Audit

- [ ] Review authentication flow (JWT handling)
- [ ] Check for SQL injection vulnerabilities
- [ ] Verify input validation on all endpoints
- [ ] Review file upload handling (path traversal, file type validation)
- [ ] Check for sensitive data exposure in logs/errors
- [ ] Verify profile data isolation (per-profile encrypted databases)
- [ ] Review CORS configuration

### 3. Test Coverage

- [ ] Identify untested endpoints
- [ ] Check for missing edge case tests
- [ ] Review E2E test coverage
- [ ] Verify test mocking patterns are consistent
- [ ] Check for flaky tests

### 4. Documentation Accuracy

- [ ] Verify README is up to date
- [ ] Check API documentation matches implementation
- [ ] Review inline code comments
- [ ] Verify setup instructions work

### 5. Technical Debt

- [ ] Find and catalog all TODO comments
- [ ] Identify incomplete features (stub implementations)
- [ ] Review database migration status
- [ ] Check for deprecated dependencies

### 6. Performance Considerations

- [ ] Review database query efficiency
- [ ] Check for N+1 query patterns
- [ ] Review embedding/vector search performance
- [ ] Verify async operations are properly handled

---

## Key Files to Review

### Backend Critical Files

1. `src/backend/core/auth.py` - Authentication logic
2. `src/backend/core/profile_database.py` - Per-profile encryption
3. `src/backend/api/documents.py` - File handling security
4. `src/backend/modules/rag.py` - RAG pipeline (most complex)
5. `src/backend/modules/model_selector.py` - Model management

### Frontend Critical Files

1. `src/frontend/src/stores/authStore.ts` - Token management
2. `src/frontend/src/services/api.ts` - API client
3. `src/frontend/src/pages/ExplainAssistant.tsx` - RAG UI

---

## Developer Commands

```bash
# Backend tests
cd src/backend
pytest -v                           # All tests
pytest tests/test_rag_pipeline.py   # RAG tests only

# Frontend tests
cd src/frontend
npm test                            # Unit tests
npm run e2e                         # Playwright E2E

# Download LLM model
python scripts/download_models.py --tier low

# Start development servers
.\dev.ps1   # Windows PowerShell
```

---

## Known Issues / Areas of Concern

1. **Model Download**: Auto-download feature added but not extensively tested
2. **Vector Search**: Currently loads all embeddings into memory (fine for small datasets, may need FAISS for scale)
3. **Date/Analyte Filters**: Vector search filters not yet implemented (placeholders exist)
4. **E2E Tests**: Some tests skip due to needing authenticated API access

---

## What Was Done in Sprint 6

1. **Local LLM Integration** (`src/backend/core/model_runner.py`)
   - ModelRunner class using llama-cpp-python
   - Lazy model loading, async inference with timeout
   - Auto-download capability via ModelSelector

2. **Vector Search** (`src/backend/modules/rag.py`)
   - Real cosine similarity search over stored embeddings
   - Profile database integration

3. **Document Import Enhancement** (`src/backend/api/documents.py`)
   - Automatic chunking and embedding on import

4. **Model Download Script** (`scripts/download_models.py`)
   - CLI tool for downloading tiered models from Hugging Face

5. **E2E Tests** (`src/frontend/e2e/assistant.spec.ts`)
   - Assistant feature E2E tests

---

## Contacts / Resources

- PRD: `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md`
- Execution Board: `docs/06_mvp_to_rag_execution_board.md`
- Backend Status: `docs/05_backend_integration_status.md`
