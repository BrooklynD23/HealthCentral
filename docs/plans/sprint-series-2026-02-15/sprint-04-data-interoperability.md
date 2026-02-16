# Sprint 04 - Data Interoperability (Export, Search, Import)

**Sprint ID:** HC-S04-DATA
**Priority:** Medium
**Source Areas:** Advanced Export Formats, Enhanced Search Functionality, Data Import from External Sources

## Architecture Scope

- Export service and API: `src/backend/modules/export.py`, `src/backend/api/export.py`.
- Search stack (new): `src/backend/modules/search.py`, `src/backend/api/search.py`.
- Search UI (new): `src/frontend/src/pages/SearchPage.tsx`, `src/frontend/src/components/SearchResults.tsx`.
- Import stack (new/extended): `src/backend/modules/importers/` and integration in `src/backend/api/documents.py`.
- FHIR model layer (new): `src/backend/models/fhir_resources.py`.

## Work Packages

### DATA-001 PDF Export with Charts

- Files:
  - `src/backend/modules/export.py`
  - `src/backend/api/export.py`
- Required behavior:
  - Generate styled PDF report outputs with embedded chart images.
  - Support template-level branding and section toggles.
  - Preserve summary and observation-level metadata.
- Test targets:
  - `src/backend/tests/test_export_pdf.py` (new)

### DATA-002 Excel Export with Formatting

- Files:
  - `src/backend/modules/export.py`
  - `src/backend/requirements.txt` (add `openpyxl`)
- Required behavior:
  - Multi-sheet workbooks (summary, labs, medications, trends).
  - Conditional formatting for abnormal values.
  - Built-in formulas and validation cells where needed.
- Test targets:
  - `src/backend/tests/test_export_excel.py` (new)

### DATA-003 HL7 FHIR Export

- Files:
  - `src/backend/modules/export.py`
  - `src/backend/models/fhir_resources.py` (new)
- Required behavior:
  - Observation and patient resource mapping.
  - FHIR JSON export for downstream integrations.
  - Compliance validation hooks.
- Test targets:
  - `src/backend/tests/test_export_fhir.py` (new)

### DATA-004 Full-Text and Semantic Search Backend

- Files:
  - `src/backend/modules/search.py` (new)
  - `src/backend/api/search.py` (new)
- Required behavior:
  - Full-text indexing with highlight snippets.
  - Semantic similarity using existing embeddings.
  - Hybrid ranking and paginated results.
  - Explanations for ranking contributions.
- Test targets:
  - `src/backend/tests/test_search_api.py` (new)
  - `src/backend/tests/test_search_ranking.py` (new)

### DATA-005 Advanced Search UI

- Files:
  - `src/frontend/src/pages/SearchPage.tsx` (new)
  - `src/frontend/src/components/SearchResults.tsx` (new)
- Required behavior:
  - Faceted filters, history, and saved search behavior.
  - Result explanation rendering for hybrid search.
  - Pagination and empty-state handling.
- Test targets:
  - `src/frontend/src/__tests__/SearchPage.test.tsx` (new)
  - `src/frontend/src/__tests__/SearchResults.test.tsx` (new)

### DATA-006 External Source Importers

- Files:
  - `src/backend/modules/importers/` (new package)
- Required behavior:
  - Apple Health XML export parsing, Google Fit JSON, generic CSV mappings.
  - Provider parsers for Quest, LabCorp, and HL7 v2.
  - Import validation and structured error reporting.
  - Pluggable portal connectors (with OAuth scaffolding).
- Test targets:
  - `src/backend/tests/test_import_health_apps.py` (new)
  - `src/backend/tests/test_import_lab_providers.py` (new)

## Dependency Notes

- DATA-001/002/003 can execute in parallel as separate export pathways.
- DATA-004 should complete backend contract before DATA-005 UI integration.
- DATA-006 should share data normalization contracts with export modules to avoid duplicate schema code.

## Definition of Done

- Export formats include PDF, Excel, and FHIR with test coverage.
- Search supports full-text plus semantic hybrid retrieval end-to-end.
- Import module supports at least one happy-path fixture for each source family.
