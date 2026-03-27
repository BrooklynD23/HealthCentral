# Phase 2 Handoff: INGEST-EPIC-001 Pipeline Wiring

## Context

Repository: `/mnt/c/Users/DangT/Documents/GitHub/HealthCentral`

### What's Done (Phase 1 — committed as `f91a057`)
- GAM-001 + MED-VOICE-001 frontend fully wired: BadgeToast in MedicationCoach, AchievementsWidget, voice toggle in SettingsPage
- Backend: badge eval, streaks, dose→badge response, model settings upsert — 21 tests pass
- Frontend: `tsc --noEmit` clean, zero errors

### Source of Truth
- **PRD:** `docs/plans/2026-03-04-prd-voice-gamification-ingest-design.md`
- **Implementation plan:** `docs/plans/2026-03-04-gam-voice-ingest-implementation.md` (Tasks 16-23 cover INGEST-EPIC-001)
- **Handoff doc:** `docs/plans/2026-03-04-handoff.md` (stale — claims 23/23 complete, not authoritative)

### What Exists But Isn't Wired (from prior commit `27f66e7`)
These files exist and their **unit tests pass (23 classifier + 3 stub tests = 26 total)**:

| File | Status |
|------|--------|
| `src/backend/migrations/profile/versions/004_document_categories_entities.py` | Written, not applied (no live DB needed) |
| `src/backend/models/document_category.py` | `DocumentCategory` + `DocumentEntity` models exist |
| `src/backend/modules/document_classifier.py` | `classify_document()` — rule-based, works, 6 tests pass |
| `src/backend/modules/extract_imaging.py` | `extract_imaging_entities()` — regex-based, tests pass |
| `src/backend/modules/extract_pathology.py` | `extract_pathology_entities()` — regex-based, tests pass |
| `src/backend/modules/extract_visit_notes.py` | `extract_visit_note_entities()` — regex-based, tests pass |
| `src/frontend/src/components/documents/CategoryBadge.tsx` | Component exists |
| `src/frontend/src/components/documents/EntityDetailView.tsx` | Component exists |
| `src/frontend/src/services/documentCategories.ts` | `useDocumentCategory()` + `useDocumentEntities()` hooks exist, call `GET /documents/{id}/category` + `GET /documents/{id}/entities` |

### What's NOT Done — Your Work

**The classifier and extractors exist but are NOT wired into the import pipeline, and the backend API endpoints the frontend hooks call do NOT exist.**

---

## Working Style: ecc-build-fix

- Diagnose first
- Run the narrowest failing build/test command for the current change
- Fix one issue at a time
- Rerun after each fix
- Stop if a fix introduces cascading failures
- Do not overwrite unrelated user changes in the dirty worktree

## Verification Environment

- **Backend pytest:** Use `/tmp/hc-pytest-venv/bin/python -m pytest` (NOT the Windows venv)
- **Frontend TS:** `cd src/frontend && npx tsc --noEmit`
- **Existing passing backend tests (must remain green):**
  ```bash
  /tmp/hc-pytest-venv/bin/python -m pytest \
    src/backend/tests/test_badge_evaluator.py \
    src/backend/tests/test_gamification_api.py \
    src/backend/tests/test_gamification_models.py \
    src/backend/tests/test_model_settings_api.py \
    src/backend/tests/test_medications_dose_logging.py \
    src/backend/tests/test_document_classifier.py \
    src/backend/tests/test_extract_imaging.py \
    src/backend/tests/test_extract_pathology.py \
    src/backend/tests/test_extract_visit_notes.py \
    -q
  ```
  Expected: 44 passed

---

## Phase 2 Tasks (implement in order)

### Task A: Wire classifier + extractors into document import pipeline

**File:** `src/backend/api/documents.py`

**Where to wire:** After extraction/chunking completes (~line 369, after `await profile_db.commit()` and before the chunking try block, OR after chunking), add:

1. Get the OCR/extracted text. The extraction pipeline already has the text — look for how `extraction_result` is used. The raw text may need to be retrieved from the decrypted document or from extraction_result metadata.
2. Call `classify_document(text)` from `modules.document_classifier`
3. If category != "unknown", persist a `DocumentCategory` record via `profile_db`
4. Based on category, call the appropriate extractor:
   - `"imaging"` → `extract_imaging_entities()` from `modules.extract_imaging`
   - `"pathology"` → `extract_pathology_entities()` from `modules.extract_pathology`
   - `"visit_notes"` → `extract_visit_note_entities()` from `modules.extract_visit_notes`
5. Persist each extracted entity as a `DocumentEntity` record

**Important:** The existing import flow handles lab documents. Classification should run for ALL document types, not just labs. The extractors return lists of dicts with keys: `entity_type`, `entity_value`, `confidence`, `source_page` (optional).

**Ref:** Implementation plan Task 21, lines 2354-2402.

### Task B: Add backend API endpoints for category + entities

**File:** `src/backend/api/documents.py`

Add two new GET endpoints:

```
GET /documents/{doc_id}/category → DocumentCategoryResponse
GET /documents/{doc_id}/entities → list[DocumentEntityResponse]
```

These must query `DocumentCategory` and `DocumentEntity` from `profile_db`. The frontend hooks in `src/frontend/src/services/documentCategories.ts` already call these exact paths.

**Response shapes** (match what the frontend expects):
```python
# GET /documents/{id}/category
{
  "doc_id": str,
  "category": str,
  "confidence": float,
  "classified_by": str
}

# GET /documents/{id}/entities
[
  {
    "id": str,
    "doc_id": str,
    "category": str,
    "entity_type": str,
    "entity_value": str,
    "confidence": float,
    "source_page": int | null
  }
]
```

Check the frontend types in `src/frontend/src/services/documentCategories.ts` to confirm exact field names.

### Task C: Replace stub integration tests with real pipeline/API tests

**Files:**
- `src/backend/tests/test_document_import_classification.py` — currently only tests `classify_document()` in isolation (same as unit tests). Replace with tests that verify the classification + entity persistence happens during import.
- `src/backend/tests/test_rag_category_filter.py` — currently only tests `classify_document()` returns valid categories. Keep or augment if Phase 3 is deferred.

Write tests that:
1. Mock the import pipeline enough to test that `classify_document` is called
2. Verify `DocumentCategory` and `DocumentEntity` records are created
3. Test the new `GET /documents/{id}/category` and `GET /documents/{id}/entities` endpoints return correct data

### Task D: Frontend integration verification

- Verify `CategoryBadge` and `EntityDetailView` are imported/rendered somewhere in the document views
- Check if `src/frontend/src/services/documentCategories.ts` exports are in the services barrel (`src/frontend/src/services/index.ts`)
- Run `tsc --noEmit` to confirm clean

---

## Phase 3 Decision: Category-Aware RAG Retrieval

**Implementation plan Task 23** calls for adding category filtering to `src/backend/modules/rag.py`.

**Decision needed:** If this is too invasive for this turn, explicitly:
1. Add a `# TODO(INGEST-F): Add category filter parameter` comment in `rag.py`
2. Mark it as deferred in the handoff doc
3. Do NOT leave stub tests that claim it's implemented

---

## Phase 4: Docs Cleanup (LAST)

Only after code is settled:
1. Update `docs/plans/2026-03-04-handoff.md` to reflect actual completion status
2. Update `docs/api/endpoints.md` to document new category/entity endpoints
3. Update `docs/05_backend_integration_status.md` if needed

---

## Deliverables

Before finishing, document all changes and prepare for commit:
1. List every file changed/created
2. Report exact test commands and results
3. Report `tsc --noEmit` result
4. Update `docs/plans/2026-03-04-handoff.md` with real status
5. Do NOT commit — leave staged for user review
