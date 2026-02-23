# Ingest Spec: Imaging, Pathology & Visit Notes (INGEST-EPIC-001)

> Status: **SPEC ONLY — no code changes**
> Author: Sprint 06 backlog
> Date: 2026-02-23

---

## 1. Motivation

HealthCentral currently ingests **lab panels** (blood work, metabolic panels, lipid panels, etc.). Users also receive:

- **Imaging reports** (X-ray, MRI, CT, ultrasound)
- **Pathology reports** (biopsy, cytology, surgical pathology)
- **Visit / encounter notes** (progress notes, discharge summaries)

Supporting these categories lets users track a more complete health picture in one place.

---

## 2. Supported Categories

| Category | Examples | Primary Entities |
|----------|----------|-----------------|
| **imaging** | X-ray, MRI, CT, US | Findings, impressions, modality, body region |
| **pathology** | Biopsy, cytology, surgical path | Diagnosis, specimen type, grade/stage, margins |
| **visit_notes** | Progress note, discharge summary, consult | Chief complaint, assessment, plan, diagnoses (ICD) |

---

## 3. Entity Types per Category

### 3.1 Imaging

| Entity | Type | Example |
|--------|------|---------|
| `modality` | enum | MRI, CT, X-RAY, US, PET |
| `body_region` | string | "chest", "lumbar spine" |
| `finding` | string | "No acute osseous abnormality" |
| `impression` | string | "Normal chest X-ray" |
| `laterality` | enum | LEFT, RIGHT, BILATERAL, N/A |
| `contrast_used` | bool | true/false |
| `ordering_provider` | string | "Dr. Smith" |
| `report_date` | date | 2026-01-15 |

### 3.2 Pathology

| Entity | Type | Example |
|--------|------|---------|
| `specimen_type` | string | "skin punch biopsy" |
| `specimen_site` | string | "left forearm" |
| `diagnosis` | string | "Basal cell carcinoma" |
| `grade` | string | "Well-differentiated" |
| `stage` | string | "T1N0M0" (if applicable) |
| `margins` | enum | NEGATIVE, POSITIVE, CLOSE, INDETERMINATE |
| `special_stains` | list[string] | ["PAS", "Ki-67"] |
| `pathologist` | string | "Dr. Jones" |
| `report_date` | date | 2026-02-01 |

### 3.3 Visit Notes

| Entity | Type | Example |
|--------|------|---------|
| `visit_type` | enum | PROGRESS, DISCHARGE, CONSULT, ANNUAL |
| `chief_complaint` | string | "Follow-up for hypertension" |
| `assessment` | string | "HTN well-controlled on current regimen" |
| `plan` | list[string] | ["Continue lisinopril 10mg", "Recheck in 3mo"] |
| `diagnoses_icd` | list[string] | ["I10", "E11.9"] |
| `provider` | string | "Dr. Williams" |
| `visit_date` | date | 2026-02-10 |
| `vitals` | object | { bp: "120/80", hr: 72, temp: 98.6 } |

---

## 4. Schema Proposal

### 4.1 New Tables (additive only — no migration to existing tables)

```sql
-- Category-level metadata per document
CREATE TABLE document_category (
    id          TEXT PRIMARY KEY,
    doc_id      TEXT NOT NULL REFERENCES documents(id),
    category    TEXT NOT NULL,  -- 'imaging', 'pathology', 'visit_notes'
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doc_id)
);

-- Flexible key-value entity storage
CREATE TABLE document_entity (
    id          TEXT PRIMARY KEY,
    doc_id      TEXT NOT NULL REFERENCES documents(id),
    category    TEXT NOT NULL,
    entity_type TEXT NOT NULL,  -- e.g. 'finding', 'diagnosis', 'chief_complaint'
    entity_value TEXT NOT NULL,
    confidence  REAL,           -- extraction confidence 0.0-1.0
    source_page INTEGER,
    source_bbox_json TEXT,      -- reuse OCR-BOX-001 bbox format
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_entity_doc (doc_id),
    INDEX idx_entity_type (entity_type)
);
```

### 4.2 Why Key-Value Instead of Typed Columns

- **Additive**: New entity types require no migration
- **Flexible**: Visit notes and imaging have very different schemas
- **Queryable**: `WHERE entity_type = 'diagnosis'` is efficient with index
- **Trade-off**: Loses column-level type safety; mitigated by Pydantic validation on ingest

### 4.3 Alembic Migration Plan

1. Single migration file: `add_document_category_and_entity_tables`
2. `upgrade()`: CREATE TABLE x2, CREATE INDEX x2
3. `downgrade()`: DROP TABLE x2
4. **No changes to existing `observations`, `documents`, or `chunks` tables**
5. Existing lab panel ingestion pipeline is unaffected

---

## 5. Detection Strategy

### 5.1 Category Classification

Before entity extraction, classify the document into a category:

```
Input: OCR text (first 500 chars) + filename
Output: { category: "imaging" | "pathology" | "visit_notes" | "lab_panel" | "unknown" }
```

**Rule-based first pass** (regex on keywords):
- **Imaging**: "IMPRESSION", "FINDINGS", "MODALITY", "RADIOLOGY", X-RAY/MRI/CT/US mentions
- **Pathology**: "SPECIMEN", "DIAGNOSIS", "GROSS DESCRIPTION", "MICROSCOPIC", "MARGINS"
- **Visit notes**: "CHIEF COMPLAINT", "ASSESSMENT", "PLAN", "SUBJECTIVE", "OBJECTIVE"
- **Lab panel**: Existing detection (analyte names, reference ranges, units)

**Fallback**: If rule-based is ambiguous, use LLM classification (when available).

### 5.2 Entity Extraction Pipeline

```
Document → OCR → Category Classification → Category-specific Extractor → Entities → DB
```

Each category gets a dedicated extractor module:
- `extract_imaging.py` — regex + structured patterns for radiology reports
- `extract_pathology.py` — regex + structured patterns for pathology reports
- `extract_visit_notes.py` — SOAP note parser, ICD code detection

Extractors follow the same pattern as `extract.py` (the existing lab panel extractor):
- Accept raw text + page metadata
- Return frozen dataclass results
- Include confidence scores and provenance (page, bbox)
- Never mutate input

---

## 6. Frontend Display (Future)

| Category | Display Component | Notes |
|----------|------------------|-------|
| imaging | `ImagingReport` card | Findings list, impression highlight, body region tag |
| pathology | `PathologyReport` card | Diagnosis badge, margins indicator, specimen details |
| visit_notes | `VisitSummary` card | SOAP sections, diagnosis chips, vitals grid |

All categories reuse:
- `PageImageOverlay` (OCR-BOX-001) for bbox citation highlights
- Verification badge for confidence indicators (UX-CONF-001)
- Export integration (existing CSV/PDF export pipeline)

---

## 7. API Endpoints (Future)

```
GET  /documents/{id}/category      → document category + metadata
GET  /documents/{id}/entities      → all extracted entities
GET  /documents/{id}/entities?type=finding  → filtered by entity type
POST /documents/{id}/reclassify    → manually override category
```

All endpoints follow existing auth pattern (`RequireAuth` + `ProfileDbSession`).

---

## 8. RAG Integration (Future)

- Entity text is chunked and embedded like existing observations
- Category-aware retrieval: user can filter by document type
- Memory store (ASSIST-MEM-003) can record category preferences (e.g., "always show imaging first")

---

## 9. Open Questions

| # | Question | Options | Decision |
|---|----------|---------|----------|
| 1 | Should category classification be mandatory at import time, or deferred? | (a) Mandatory — blocks import until classified (b) Deferred — classify async, allow "unknown" | **TBD** — Lean toward (b) for UX |
| 2 | How to handle multi-category documents (e.g., discharge summary with labs)? | (a) Primary category only (b) Multi-label with primary | **TBD** — Lean toward (b) |
| 3 | Should we support structured data import (HL7 FHIR, CDA) in addition to OCR? | (a) OCR only (b) OCR + FHIR/CDA parser | **TBD** — Phase 2 consideration |
| 4 | Entity extraction confidence threshold for display? | (a) Show all with confidence badge (b) Hide below 0.5 | **TBD** — Lean toward (a) with visual cue |
| 5 | ICD code lookup for visit notes — bundle a local DB or call external API? | (a) Local SQLite lookup table (b) External API | **TBD** — (a) preferred for privacy |

---

## 10. Implementation Phases (Proposed)

| Phase | Scope | Dependencies |
|-------|-------|-------------|
| **A** | Schema migration + category classification | None |
| **B** | Imaging entity extractor + tests | Phase A |
| **C** | Pathology entity extractor + tests | Phase A |
| **D** | Visit notes entity extractor + tests | Phase A |
| **E** | Frontend display components | Phases B-D |
| **F** | RAG integration + category-aware retrieval | Phases B-D |

Phases B, C, D are independent and can be parallelised.

---

## 11. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Regex extraction misses non-standard report formats | Medium | Confidence scores + manual review flag |
| Large pathology reports exceed context window | Low | Chunk by section (gross, micro, diagnosis) |
| ICD code lookup table becomes stale | Low | Versioned SQLite bundle, periodic updates |
| Multi-category documents confuse classification | Medium | Primary + secondary labels, user override |
| Privacy: pathology diagnoses are highly sensitive | High | Same encryption (SQLCipher) + redaction pipeline (PRIV-RED-001) |
