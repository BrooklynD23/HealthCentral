# Sprint 04 - Data Interoperability Design

**Sprint ID:** HC-S04-DATA
**Date:** 2026-02-15
**Status:** Approved

## Overview

Six work packages across three domains: Export (PDF with charts, Excel, FHIR R4), Search (hybrid FTS5 + semantic backend, search UI), Import (multi-source external parsers). All follow existing patterns: per-profile DB isolation, `RequireAuth` + `ProfileDbSession`, React Query hooks, audit logging.

## Design Decisions

### DD-1: Semantic search uses SQL+cosine, not FAISS

Current vector search (`rag.py:301`) loads embeddings from SQL and computes cosine similarity in Python. Config references FAISS (`config.py:73`) but no index lifecycle exists. Building per-profile FAISS index creation, refresh on import/delete, and recovery on unlock is out of scope.

**Decision:** v1 reuses the existing SQL+cosine pattern. FAISS deferred to v2 if corpus size warrants it.

### DD-2: External imports create synthetic Document records

`Observation.doc_id` is `NOT NULL` with a foreign key to `documents.id` (`observation.py:45`). Current ingestion is document-first (`documents.py:141`).

**Decision:** Each external import creates a synthetic `Document` with `doc_type="external_import"` and `source` set to the parser name (e.g., `"apple_health"`). Parsers return observations + metadata; the endpoint wraps them in a Document for provenance.

### DD-3: External import route is `/documents/import/external`

Routes are grouped by domain (`api/__init__.py:31`). Import lives under `/documents/import`.

**Decision:** New endpoint is `POST /documents/import/external` on the existing `documents_router`. No new router.

### DD-4: Minimal FHIR Patient, LOINC via BiomarkerKnowledge

`Profile` has only `display_name` + auth fields (`profile.py:46`). No DOB/sex/contact. LOINC codes live in `BiomarkerKnowledge.loinc_codes_json` (`knowledge_base.py:50`).

**Decision:** Ship minimal FHIR Patient with `name` only. Mark absent fields with FHIR `data-absent-reason`. Look up LOINC via `BiomarkerKnowledge` join on `analyte_canonical`. No Profile schema changes.

### DD-5: FTS5 indexes both observations and chunks

Most free text is in `chunks.text`, not observations. Indexing only observations misses document content.

**Decision:** Two FTS5 virtual tables:
- `observations_fts` on `(analyte_canonical, analyte_raw, value_text, notes)`
- `chunks_fts` on `(text)`

Results merge with type tagging. RRF combines obs FTS, chunk FTS, and embedding similarity.

### DD-6: PDF charts extend existing summary flow

Frontend uses `generateSummary()` -> `downloadSummary(id, format)` pattern (`export.ts:88`). A parallel PDF route risks duplicated logic.

**Decision:** No new endpoint. Extend `render_pdf_summary()` to accept `include_charts=True`. Add `include_charts` query param to `GET /doctor-summary/{id}/download?format=pdf`. Charts embedded via matplotlib -> base64 `<img>` in existing HTML->PDF pipeline.

### DD-7: Dependencies pinned

**Decision:** Add to `requirements.txt`:
```
matplotlib>=3.8.0
openpyxl>=3.1.0
defusedxml>=0.7.0
```
matplotlib uses `Agg` backend (no display).

### DD-8: Importer security extends existing guardrails

`ingest.py:92` has `validate_file()` with size/extension checks. `config.py:77` has `max_import_file_size_mb`.

**Decision:** External importers reuse `config.max_import_file_size_mb`. Additional:
- XML: `defusedxml.ElementTree` (prevents XXE, billion-laughs)
- CSV: Row limit 100,000, column limit 50
- HL7 v2: Segment limit 10,000, field length limit 10KB
- All parsers: Per-row error collection, hard-fail above 10% error rate
- Extension whitelist: `.xml`, `.csv`, `.json`, `.hl7`

### DD-9: Audit events mapped per endpoint

| Endpoint | Audit Event | Helper |
|---|---|---|
| `GET .../download?format=pdf&include_charts` | `export.create` type=`pdf_with_charts` | `log_export_event()` |
| `GET /export/excel` | `export.create` type=`excel` | `log_export_event()` |
| `GET /export/fhir` | `export.create` type=`fhir_r4` | `log_export_event()` |
| `GET /search` | `search.query` | new `log_search_event()` |
| `POST /documents/import/external` | `document.import` type=`external_{source}` | `log_document_event()` |

---

## DATA-001: PDF Export with Charts

### Architecture

Extend `ExportModule` in `src/backend/modules/export.py`:
- New method: `generate_chart_image(analyte: str, data_points: list[dict]) -> bytes`
  - Uses matplotlib with `Agg` backend
  - Line plot with reference range shading (green band)
  - Abnormal points highlighted in red
  - Returns PNG bytes
- New method: `render_pdf_with_charts(summary_data: dict, chart_images: dict[str, bytes]) -> bytes`
  - Embeds chart PNGs as base64 `<img>` tags in existing HTML template
  - Renders via WeasyPrint

### API Changes

Extend existing `GET /export/doctor-summary/{summary_id}/download`:
- New query param: `include_charts: bool = False`
- When `True` and `format=pdf`: generates charts for trending analytes, embeds in PDF
- When `True` and `format=html`: same chart embedding in HTML output

### Frontend Changes

Extend `downloadSummary()` in `export.ts` to pass `include_charts` param.

---

## DATA-002: Excel Export with Formatting

### Architecture

New method in `ExportModule`:
- `export_excel(observations: list[dict], trends: list[dict], medications: list[dict]) -> bytes`
  - Returns openpyxl `Workbook` saved to `BytesIO`
  - Sheets: Summary, Labs, Medications, Trends
  - Conditional formatting: `PatternFill(fgColor="FFC7CE")` for abnormal, `PatternFill(fgColor="FFEB9C")` for borderline
  - Frozen header row, auto-column widths
  - Data validation on flag column

### API

New endpoint: `GET /export/excel`
- Same auth/filter params as existing `GET /export/csv`
- Returns `StreamingResponse` with `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Audit: `log_export_event(type="excel")`

### Frontend

New hook: `useExportExcel()` in `export.ts`. Button added to ExportPage.

---

## DATA-003: HL7 FHIR R4 Export

### Architecture

New file: `src/backend/models/fhir_resources.py`

Pydantic models (not SQLAlchemy - these are serialization-only):
- `FHIRPatient` - minimal: `resourceType`, `id`, `name`, `_absent` extensions
- `FHIRObservation` - `resourceType`, `id`, `status`, `code` (with LOINC from BiomarkerKnowledge), `valueQuantity`, `referenceRange`, `effectiveDateTime`, `subject`
- `FHIRBundle` - `resourceType="Bundle"`, `type="collection"`, `entry[]`

LOINC lookup: Query `BiomarkerKnowledge` by `analyte_canonical`, parse `loinc_codes_json`. Fall back to display text if no LOINC match.

### API

New endpoint: `GET /export/fhir`
- Same auth/filter params as CSV/JSON endpoints
- Requires `master_db` for BiomarkerKnowledge LOINC lookup
- Returns `application/fhir+json` with FHIR Bundle
- Audit: `log_export_event(type="fhir_r4")`

### Frontend

New hook: `useExportFHIR()` in `export.ts`. Button added to ExportPage.

---

## DATA-004: Hybrid Search Backend

### Architecture

New files:
- `src/backend/modules/search.py` - SearchModule class
- `src/backend/api/search.py` - Search endpoints
- `src/backend/migrations/profile/versions/003_add_fts5_indexes.py` - FTS5 migration

**SearchModule** methods:
- `search_fulltext(query, profile_db, filters) -> list[FTSResult]` - FTS5 queries on both virtual tables
- `search_semantic(query, profile_db, embedder, top_k) -> list[SemanticResult]` - Reuses `_search_vectors_async` pattern
- `search_hybrid(query, profile_db, embedder, filters) -> list[HybridResult]` - Combines via RRF
- `get_suggestions(prefix, profile_db) -> list[str]` - Autocomplete from observations

**FTS5 Migration** (`003_add_fts5_indexes.py`):
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
USING fts5(analyte_canonical, analyte_raw, value_text, notes, content=observations, content_rowid=rowid);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
USING fts5(text, content=chunks, content_rowid=rowid);
```
Plus triggers for insert/update/delete sync.

**RRF (Reciprocal Rank Fusion):**
```
score(doc) = sum(1 / (k + rank_i)) for each ranking list i
k = 60 (standard constant)
```

### API

New router: `src/backend/api/search.py`, mounted at `/search` in `api/__init__.py`.

Endpoints:
- `GET /search?q=...&mode=hybrid|text|semantic&limit=20&offset=0&from_date=...&to_date=...&analyte=...&abnormal_only=false`
  - Returns `SearchResponse` with `results[]`, `total_count`, `query`, `mode`
  - Each result: `type` (observation|chunk), `id`, `title`, `snippet`, `highlight`, `score`, `explanation`
- `GET /search/suggestions?prefix=...&limit=10`
  - Returns `list[str]` of analyte name suggestions

Audit: new `log_search_event()` in `audit.py`.

### Frontend Service

New file: `src/frontend/src/services/search.ts`
- `useSearch(query, filters)` - React Query hook with debounce
- `useSearchSuggestions(prefix)` - Autocomplete hook

---

## DATA-005: Advanced Search UI

### Architecture

New files:
- `src/frontend/src/pages/SearchPage.tsx`
- `src/frontend/src/components/SearchResults.tsx`

New route: `/search` in `App.tsx`

**SearchPage** layout:
- Search bar with 300ms debounce, mode selector (hybrid/text/semantic)
- Faceted filter sidebar: date range picker, panel checkboxes (from BiomarkerKnowledge categories), abnormal toggle
- Results area with `SearchResults` component
- Pagination (limit/offset)
- Empty state, loading skeleton, error handling

**SearchResults** component:
- Result cards with: type icon (lab/document), title, value+unit (for observations), date, highlight snippet, relevance score badge
- Explanation tooltip showing ranking contributions
- Click-through to source (observation -> trends, chunk -> document viewer)

---

## DATA-006: External Source Importers

### Architecture

New package: `src/backend/modules/importers/`
- `__init__.py` - Registry and base class
- `base.py` - `BaseImporter` ABC
- `apple_health.py` - Apple Health XML parser
- `google_fit.py` - Google Fit JSON parser
- `generic_csv.py` - Generic CSV with column mapping
- `quest.py` - Quest Diagnostics CSV
- `labcorp.py` - LabCorp CSV
- `hl7v2.py` - HL7 v2 pipe-delimited parser

**BaseImporter** interface:
```python
class BaseImporter(ABC):
    source_name: str
    supported_extensions: list[str]

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> ImportResult

class ImportResult:
    observations: list[ImportedObservation]
    source_metadata: dict  # For synthetic Document
    errors: list[ImportError]  # Per-row errors
    warnings: list[str]

class ImportedObservation:
    analyte_raw: str
    value: float | None
    value_text: str | None
    unit: str | None
    collected_at: datetime | None
    ref_low: float | None
    ref_high: float | None
    flag: str | None
```

**Security** (per DD-8):
- All XML via `defusedxml`
- Row/segment limits per parser
- File size via `config.max_import_file_size_mb`
- Hard-fail above 10% error rate

### API

New endpoint on existing `documents_router`:
`POST /documents/import/external`
- Params: `file: UploadFile`, `source_type: str` (enum of supported sources)
- Creates synthetic `Document` record with `doc_type="external_import"`
- Inserts parsed observations with `doc_id` FK
- Returns `ExternalImportResponse` with observation count, error count, document_id
- Audit: `log_document_event(event="import", details={"source": source_type, "type": "external"})`

### Frontend

New hook: `useImportExternal()` in `documents.ts`. Import source selector added to DocumentInbox.

---

## New Dependencies

```
matplotlib>=3.8.0      # DATA-001: Chart generation
openpyxl>=3.1.0        # DATA-002: Excel export
defusedxml>=0.7.0      # DATA-006: Safe XML parsing
```

## New Files Summary

### Backend
- `src/backend/models/fhir_resources.py` (new)
- `src/backend/modules/search.py` (new)
- `src/backend/modules/importers/__init__.py` (new)
- `src/backend/modules/importers/base.py` (new)
- `src/backend/modules/importers/apple_health.py` (new)
- `src/backend/modules/importers/google_fit.py` (new)
- `src/backend/modules/importers/generic_csv.py` (new)
- `src/backend/modules/importers/quest.py` (new)
- `src/backend/modules/importers/labcorp.py` (new)
- `src/backend/modules/importers/hl7v2.py` (new)
- `src/backend/api/search.py` (new)
- `src/backend/migrations/profile/versions/003_add_fts5_indexes.py` (new)

### Backend Tests
- `src/backend/tests/test_export_pdf.py` (new)
- `src/backend/tests/test_export_excel.py` (new)
- `src/backend/tests/test_export_fhir.py` (new)
- `src/backend/tests/test_search_api.py` (new)
- `src/backend/tests/test_search_ranking.py` (new)
- `src/backend/tests/test_import_health_apps.py` (new)
- `src/backend/tests/test_import_lab_providers.py` (new)

### Backend Modified
- `src/backend/modules/export.py` (extend with charts, excel, FHIR)
- `src/backend/api/export.py` (add excel, FHIR endpoints; extend download with include_charts)
- `src/backend/api/documents.py` (add /import/external endpoint)
- `src/backend/api/__init__.py` (register search router)
- `src/backend/core/audit.py` (add log_search_event)
- `src/backend/requirements.txt` (add matplotlib, openpyxl, defusedxml)

### Frontend
- `src/frontend/src/pages/SearchPage.tsx` (new)
- `src/frontend/src/components/SearchResults.tsx` (new)
- `src/frontend/src/services/search.ts` (new)

### Frontend Tests
- `src/frontend/src/__tests__/SearchPage.test.tsx` (new)
- `src/frontend/src/__tests__/SearchResults.test.tsx` (new)

### Frontend Modified
- `src/frontend/src/App.tsx` (add /search route)
- `src/frontend/src/services/export.ts` (add excel, FHIR hooks; extend download with include_charts)
- `src/frontend/src/services/documents.ts` (add useImportExternal hook)
- `src/frontend/src/pages/index.ts` (export SearchPage)
- `src/frontend/src/pages/ExportPage.tsx` (add Excel, FHIR buttons)
- `src/frontend/src/pages/DocumentInbox.tsx` (add external import source selector)
