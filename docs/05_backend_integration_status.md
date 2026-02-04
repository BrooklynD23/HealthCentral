# Backend Integration Status

**Last Updated:** 2026-02-04
**Status:** Sprint 6 Complete (Security Revamp + Alembic Migrations)

---

## Overview

This document tracks the implementation status of backend-frontend integration for HealthCentral. The integration follows the architecture defined in `01_backend_architecture_plan.md`.

---

## Implemented Components

### Backend API Endpoints (`src/backend/api/`)

#### Profiles (`profiles.py`)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/profiles/` | POST | ✅ Done | Create profile with encrypted vault |
| `/api/v1/profiles/` | GET | ✅ Done | List all profiles |
| `/api/v1/profiles/{id}` | GET | ✅ Done | Get profile details |
| `/api/v1/profiles/{id}/unlock` | POST | ✅ Done | Unlock profile for access |
| `/api/v1/profiles/{id}/lock` | POST | ✅ Done | Lock profile |

#### Documents (`documents.py`)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/documents/import` | POST | ✅ Done | Import PDF/image documents |
| `/api/v1/documents/` | GET | ✅ Done | List documents with filters |
| `/api/v1/documents/{id}` | GET | ✅ Done | Get document details |
| `/api/v1/documents/{id}/pages` | GET | ✅ Done | Get document pages for provenance |
| `/api/v1/documents/{id}` | DELETE | ✅ Done | Delete document and data |

#### Observations (`observations.py`)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/observations/` | GET | ✅ Done | List observations with filters |
| `/api/v1/observations/{id}` | GET | ✅ Done | Get observation details |
| `/api/v1/observations/{id}/verify` | POST | ✅ Done | Verify/edit observation |
| `/api/v1/observations/trends/{analyte}` | GET | ✅ Done | Get trend data with summary |
| `/api/v1/observations/panels/{panel_id}` | GET | ✅ Done | Get panel data (CBC, CMP, etc.) |

#### Assistant (`assistant.py`) - Sprint 5 Complete
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/assistant/chat` | POST | ⚠️ LLM Required | RAG chat (needs local model setup) |
| `/api/v1/assistant/test-intent/{analyte}` | GET | ✅ Done | Test intent lookup from curated data |
| `/api/v1/assistant/glossary/{term}` | GET | ✅ Done | Glossary lookup from curated data |
| `/api/v1/assistant/verification-status` | GET | ✅ Done | Verification components status |

#### Export (`export.py`) - Sprint 4 Complete
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/export/doctor-summary` | POST | ✅ Done | Generate clinician-ready summary |
| `/api/v1/export/doctor-summary/{summary_id}/download` | GET | ✅ Done | Download generated summary |
| `/api/v1/export/questions` | POST | ✅ Done | Generate discussion questions |
| `/api/v1/export/csv` | GET | ✅ Done | CSV export with filters |
| `/api/v1/export/json` | GET | ✅ Done | JSON export with filters |

#### Interpretations (`interpretations.py`)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/observations/{id}/interpret` | POST | ✅ Done | Generate interpretation |
| `/api/v1/observations/{id}/interpretation` | GET | ✅ Done | Get existing interpretation |
| `/api/v1/panels/{name}/interpret` | POST | ✅ Done | Panel interpretation |
| `/api/v1/interpretations/recent` | GET | ✅ Done | List recent |
| `/api/v1/knowledge/biomarker/{analyte}` | GET | ✅ Done | Knowledge lookup |
| `/api/v1/interpretations/batch` | POST | ✅ Done | Batch generation |

#### Medications (`medications.py`)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/medications/` | POST | ✅ Done | Create medication |
| `/api/v1/medications/` | GET | ✅ Done | List medications |
| `/api/v1/medications/{id}` | GET | ✅ Done | Get medication details |
| `/api/v1/medications/{id}` | PATCH | ✅ Done | Update medication |
| `/api/v1/medications/{id}` | DELETE | ✅ Done | Delete medication |
| `/api/v1/medications/{id}/schedules` | POST/GET | ✅ Done | Manage schedules |
| `/api/v1/medications/{id}/doses` | POST/GET | ✅ Done | Log and list doses |
| `/api/v1/medications/{id}/stats` | GET | ✅ Done | Adherence stats |

#### Notifications (`notifications.py`)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/notifications/settings/{med_id}` | GET/PATCH | ✅ Done | Notification settings |
| `/api/v1/notifications/history` | GET | ✅ Done | Notification history |
| `/api/v1/notifications/test` | POST | ✅ Done | Test notification |
| `/api/v1/notifications/scheduler/status` | GET | ✅ Done | Scheduler status |

#### Model Settings (`model_settings.py`) - Phase 0.3
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/settings/model` | GET | ✅ Done | Get model settings + hardware info |
| `/api/v1/settings/model/detect` | POST | ✅ Done | Run hardware detection |
| `/api/v1/settings/model/tier` | POST | ✅ Done | Set preferred tier |
| `/api/v1/settings/model/tiers` | GET | ✅ Done | List tiers with status |
| `/api/v1/settings/model/download-progress` | GET | ✅ Done | Check download status |
| `/api/v1/settings/model/download` | POST | ✅ Done | Start model download |

---

### Frontend Services (`src/frontend/src/services/`)

#### Created Files
| File | Purpose |
|------|---------|
| `api.ts` | Base API client with fetch wrapper, error handling |
| `types.ts` | TypeScript types matching backend Pydantic models |
| `profiles.ts` | React Query hooks for profile management |
| `documents.ts` | React Query hooks for document management |
| `observations.ts` | React Query hooks for observations and trends |
| `export.ts` | React Query hooks for export functionality |
| `index.ts` | Barrel export for all services |

#### React Query Hooks
- **Profiles:** `useProfiles`, `useProfile`, `useCreateProfile`, `useUnlockProfile`, `useLockProfile`
- **Documents:** `useDocuments`, `useDocument`, `useDocumentPages`, `useImportDocument`, `useDeleteDocument`
- **Observations:** `useObservations`, `useObservation`, `useVerifyObservation`, `useTrend`, `usePanel`, `useAnalyteList`
- **Export:** `useExportCSV`, `useExportJSON`, `useGenerateSummary`, `useDownloadSummary`, `useGenerateQuestions`

---

### Frontend Pages Integration

| Page | Integration Status | Notes |
|------|-------------------|-------|
| `ProfileSetup.tsx` | ✅ Connected | Uses `useCreateProfile()` for real API calls |
| `DocumentInbox.tsx` | ✅ Connected | Uses `useDocuments()`, `useImportDocument()` |
| `VerificationWorkbench.tsx` | ✅ Connected | Uses `useObservations()`, `useVerifyObservation()` |
| `TrendsDashboard.tsx` | ✅ Connected | Uses `useObservations()`, `useTrend()`, `usePanel()` |
| `ExportPage.tsx` | ✅ Connected | Uses `useExportCSV()`, `useExportJSON()`, `useGenerateSummary()` |
| `ExplainAssistant.tsx` | ⏳ Pending | Awaits assistant API implementation (Sprint 5) |

---

## Configuration Updates

### Path Aliases Added
- `@services` alias added to `vite.config.ts` and `tsconfig.json`

### Environment Variables
- `VITE_API_URL` - Backend API base URL (default: `http://localhost:8000/api/v1`)

### PWA Meta Tags (`index.html`)
- Added light/dark theme-color meta tags
- Added Apple PWA meta tags for iOS support
- Added Microsoft tile color for Windows

---

## Database Models

All models are implemented in `src/backend/models/`:

| Model | Table | Database | Status |
|-------|-------|----------|--------|
| `Profile` | `profiles` | Master | ✅ Done |
| `AuditLog` | `audit_logs` | Master | ✅ Done |
| `BiomarkerKnowledge` | `biomarker_knowledge` | Master | ✅ Done |
| `InterventionMapping` | `intervention_mappings` | Master | ✅ Done |
| `BiomarkerRelationship` | `biomarker_relationships` | Master | ✅ Done |
| `Document` | `documents` | Per-Profile | ✅ Done |
| `Observation` | `observations` | Per-Profile | ✅ Done |
| `Chunk` | `chunks` | Per-Profile | ✅ Done |
| `Embedding` | `embeddings` | Per-Profile | ✅ Done |
| `LabInterpretation` | `lab_interpretations` | Per-Profile | ✅ Done |
| `PanelInterpretation` | `panel_interpretations` | Per-Profile | ✅ Done |
| `Medication` | `medications` | Per-Profile | ✅ Done |
| `MedicationSchedule` | `medication_schedules` | Per-Profile | ✅ Done |
| `DoseTaken` | `doses_taken` | Per-Profile | ✅ Done |
| `AdherencePattern` | `adherence_patterns` | Per-Profile | ✅ Done |
| `ReminderLog` | `reminder_logs` | Per-Profile | ✅ Done |
| `UserModelSettings` | `user_model_settings` | Per-Profile | ✅ Done |

---

## Database Migrations (Alembic)

HealthCentral uses Alembic for versioned schema migrations with a dual-environment setup.

### Migration Architecture

| Component | Location | Description |
|-----------|----------|-------------|
| `alembic.ini` | `src/backend/` | Configuration with `[master]` and `[profile]` sections |
| Master env.py | `migrations/master/env.py` | Sync SQLite migrations for master DB |
| Profile env.py | `migrations/profile/env.py` | SQLCipher-aware migrations with PRAGMA key |
| Migration utilities | `core/migrations.py` | Baseline detection + async wrappers |
| CLI tool | `scripts/migrate.py` | Manual migration execution |

### Key Features

1. **Baseline Detection**: Existing DBs without `alembic_version` are stamped (not re-created)
2. **Non-blocking**: All Alembic calls run via `asyncio.to_thread()`
3. **SQLCipher Support**: Profile migrations set `PRAGMA key` before operations
4. **Automatic Execution**:
   - Master migrations run on app startup (`main.py` lifespan)
   - Profile migrations run on vault open (`profile_database.py`)

### Schema Versions

| Database | Current Revision | Tables |
|----------|-----------------|--------|
| Master | `001_initial` | profiles, audit_logs, biomarker_knowledge, intervention_mappings, biomarker_relationships |
| Profile | `001_initial` | documents, observations, chunks, embeddings, lab_interpretations, panel_interpretations, medications, medication_schedules, doses_taken, adherence_patterns, reminder_logs, user_model_settings |

### CLI Commands

```bash
cd src/backend

# Run master migrations
python -m scripts.migrate master

# Check status
python -m scripts.migrate status

# Run profile migrations
python -m scripts.migrate profile --profile-id <uuid> --password <pwd>

# Alembic CLI (for development)
alembic -c alembic.ini -n master current
alembic -c alembic.ini -n master upgrade head
```

---

## Backend Modules

| Module | Status | Notes |
|--------|--------|-------|
| `ingest.py` | ✅ Basic | File import, hashing, storage |
| `extract.py` | ⏳ Partial | Table extraction implemented; text extraction still TODO |
| `normalize.py` | ✅ Basic | Built-in synonym mapping implemented |
| `verify.py` | ⏳ Stub | Verification workflow not yet implemented |
| `analytics.py` | ✅ Basic | Trend calculations implemented (deterministic) |
| `rag.py` | ⏳ Stub | RAG pipeline not yet implemented |
| `export.py` | ✅ Done | CSV/JSON + summary/question generation - API fully wired (Sprint 4) |
| `interpret.py` | ✅ Done | Lab interpretation pipeline with LLM support |
| `interpret_safety.py` | ✅ Done | Safety guardrails for interpretations |
| `recommend.py` | ✅ Done | Evidence-based recommendation engine |
| `knowledge_loader.py` | ✅ Done | Knowledge base access with caching |
| `adherence_patterns.py` | ✅ Done | Medication adherence pattern learning |
| `message_generator.py` | ✅ Done | Notification message generation |
| `notification_scheduler.py` | ✅ Done | Background notification scheduling |
| `platform_notifications.py` | ✅ Done | Cross-platform notification delivery |
| `hardware_detection.py` | ✅ Done | Hardware capability detection (Phase 0.3) |
| `model_selector.py` | ✅ Done | Tiered model selection (Phase 0.3) |

---

## Running the Application

### Backend
```bash
cd src/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd src/frontend
npm install
npm run dev
```

Access:
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

---

## Next Steps

1. **Sprint 5: RAG Assistant (Post-MVP)**
   - Implement chunking + embeddings pipeline
   - Implement `RAGModule.retrieve_context()` with similarity search
   - Implement `RAGModule.generate_response()` with citations
   - Implement glossary + test-intent endpoints
   - Wire `ExplainAssistant.tsx` to real API
2. **Polish & Testing** - Adversarial testing, accessibility audit, performance

---

## Known Issues

1. **vite.config.ts lint warnings** - `@types/node` needs to be installed for Node.js type declarations
2. **theme-color meta tag warning** - Informational only; progressive enhancement works in supported browsers
