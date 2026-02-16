# Backend Integration Status

**Last Updated:** 2026-02-16
**Owner:** Backend Lead
**Refresh Trigger:** API endpoint added, changed, or removed
**Status:** Current integration baseline (post-stabilization sprint, active backend/frontend contracts)

---

## Overview

This document tracks the implementation status of backend-frontend integration for HealthCentral. The integration follows the architecture defined in `01_backend_architecture_plan.md`.

---

## Stabilization Updates (2026-02-14)

The STAB-001 through STAB-007 sprint hardening work is implemented:

- OCR extraction now degrades gracefully with `ocr_unavailable` signals instead of raising runtime crashes.
- Document import uses runtime OCR capability checks and marks scanned/image docs as `pending_ocr` when unavailable.
- Extraction parser no longer silently swallows parse failures; warning logs now capture parse-context metadata.
- Startup config validation is enforced via `settings.validate_startup()` with production JWT-secret hard-fail behavior.
- CORS `allow_headers` is explicit (`Authorization`, `Content-Type`, `Accept`, `X-Requested-With`) instead of wildcard.
- Assistant no-model path now uses explicit `ModelUnavailableError` and deterministic knowledge-base fallback responses.
- E2E smoke coverage expanded with `document-import.spec.ts` and `settings-smoke.spec.ts`; CI now includes an `e2e-tests` job.

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

#### Assistant (`assistant.py`) - Current
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/assistant/chat` | POST | ✅ Done | RAG chat with local/external model path and no-model knowledge-base fallback |
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
| `/api/v1/export/excel` | GET | ✅ Done | Excel export (summary/labs/trends workbook) |
| `/api/v1/export/fhir` | GET | ✅ Done | FHIR R4 Bundle JSON export |

#### Search (`search.py`) - Sprint 4 Backend
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/search` | GET | ✅ Done | Hybrid/full-text/semantic search with pagination |
| `/api/v1/search/suggestions` | GET | ✅ Done | Prefix suggestions for analyte names |

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
| `search.ts` | React Query hooks for hybrid search and suggestions |
| `index.ts` | Barrel export for all services |

#### React Query Hooks
- **Profiles:** `useProfiles`, `useProfile`, `useCreateProfile`, `useUnlockProfile`, `useLockProfile`
- **Documents:** `useDocuments`, `useDocument`, `useDocumentPages`, `useImportDocument`, `useDeleteDocument`
- **Observations:** `useObservations`, `useObservation`, `useVerifyObservation`, `useTrend`, `usePanel`, `useAnalyteList`
- **Export:** `useExportCSV`, `useExportJSON`, `useGenerateSummary`, `useDownloadSummary`, `useGenerateQuestions`
- **Search:** `useSearch`, `useSearchSuggestions`

---

### Frontend Pages Integration

| Page | Integration Status | Notes |
|------|-------------------|-------|
| `ProfileSetup.tsx` | ✅ Connected | Uses `useCreateProfile()` for real API calls |
| `DocumentInbox.tsx` | ✅ Connected | Uses `useDocuments()`, `useImportDocument()`, and renders `OCR Required` for `pending_ocr` docs |
| `VerificationWorkbench.tsx` | ✅ Connected | Uses `useObservations()`, `useVerifyObservation()` |
| `TrendsDashboard.tsx` | ✅ Connected | Uses `useObservations()`, `useTrend()`, `usePanel()` |
| `MedicationCoach.tsx` | ✅ Connected | Uses medication CRUD, schedules, dose logging, and adherence stats hooks |
| `MedicationDetail.tsx` | ✅ Connected | Uses medication detail + schedule + dose history + pattern learning hooks |
| `NotificationSettings.tsx` | ✅ Connected | Uses notification settings/history/scheduler APIs with local-time quiet-hours controls |
| `ExportPage.tsx` | ✅ Connected | Uses `useExportCSV()`, `useExportJSON()`, `useGenerateSummary()` |
| `SearchPage.tsx` | ✅ Connected | Uses `useSearch()` with mode/date/abnormal filters and pagination |
| `SettingsPage.tsx` | ✅ Connected | Uses model settings and external API hooks |
| `ExplainAssistant.tsx` | ✅ Connected | Wired to `/assistant/chat` with citation + verification rendering |

---

## Configuration Updates

### Path Aliases Added
- `@services` alias added to `vite.config.ts` and `tsconfig.json`

### Environment Variables
- `VITE_API_URL` - Backend API base URL (default: `http://localhost:8000/api/v1`)

### Startup Validation + OCR Runtime Checks
- `settings.validate_startup()` runs during FastAPI lifespan startup.
- `is_ocr_available()` gates OCR work based on config flag + runtime `tesseract` availability.
- Production mode now requires non-empty `jwt_secret` at startup.

### CORS Hardening
- `allow_headers` now uses explicit allow-list values in `main.py` (no wildcard).

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
| `extract.py` | ✅ Hardened | Table/text extraction + OCR paths with graceful OCR-unavailable fallback and parse-failure warning logs |
| `normalize.py` | ✅ Basic | Built-in synonym mapping implemented |
| `verify.py` | Legacy / non-owning | Verification logic is enforced in API route (`api/observations.py`); module stubs are non-critical |
| `analytics.py` | ✅ Basic | Trend calculations implemented (deterministic) |
| `rag.py` | ✅ Done (model-dependent) | Retrieval + generation + citation validation + safety checks; explicit `ModelUnavailableError` path with assistant fallback handling |
| `export.py` | ✅ Done | CSV/JSON + summary/question generation - API fully wired (Sprint 4), with HTML output escaping and spreadsheet formula-injection hardening |
| `search.py` | ✅ Done | Hybrid search (FTS + semantic + RRF), snippet sanitization, and pagination contract support |
| `importers/` | ✅ Done (core parsers) | Apple Health, Google Fit, Generic CSV, Quest, LabCorp, HL7v2 parser package; external connector OAuth scaffolding now enforces redirect allowlist validation |
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

1. **Regression safety**
   - Keep E2E smoke suite green in CI and expand deterministic fixtures as workflows evolve.
   - Continue adversarial safety test expansion for RAG and interpretation guardrails.
2. **Deferred backlog**
   - Sprint 4 polish for search history/saved searches, export template customization, and importer OAuth connectors is implemented.
   - Continue follow-up hardening and productionization for OAuth callback/state exchange flow.
   - Continue docs consolidation so canonical trackers stay synchronized with implemented behavior.

### Recent Security Hardening (2026-02-16)

- Summary HTML/PDF template rendering now escapes untrusted branding and summary content before interpolation.
- CSV/XLSX export sanitization now guards formula-like payloads even when prefixed by whitespace/control characters.
- OAuth scaffold start endpoint validates `redirect_uri` against `settings.oauth_redirect_allowlist` and records state metadata for callback verification scaffolding.
- Search history/saved searches are session-scoped by default in the frontend, with explicit user opt-in to persist on device.

---

## Backend Test Setup

### Running Tests

```bash
# Linux/WSL (from repo root)
bash scripts/run-backend-tests.sh

# Windows PowerShell (from repo root)
.\scripts\run-backend-tests.ps1

# Run specific test file
bash scripts/run-backend-tests.sh tests/test_bootstrap_check.py -q
```

### Test Environment

- `TEST_MODE=1` is set automatically by `conftest.py` and the runner scripts.
- `DATABASE_ENCRYPTION_REQUIRED=false` is set **only** in `conftest.py` for environments without SQLCipher.
- The production default (`database_encryption_required: bool = True`) must remain unchanged in `core/config.py`.
- `test_bootstrap_check.py` verifies all three invariants on every test run.

### Prerequisites

- Python 3.11+ with `pip install -r requirements.txt` (includes pytest)
- SQLCipher optional — tests run without it via the conftest override

---

## Known Issues

1. **vite.config.ts lint warnings** - `@types/node` needs to be installed for Node.js type declarations
2. **theme-color meta tag warning** - Informational only; progressive enhancement works in supported browsers
3. **Date persistence tracking note** - Date persistence (`Observation.collected_at`, `Document.collection_date`) is now implemented, but date parsing/timezone normalization still requires ongoing regression checks for filter consistency.
