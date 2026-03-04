# PRD: Voice Logging, Gamification v1, INGEST-EPIC-001

**Date:** 2026-03-04
**Status:** Approved — ready for implementation planning
**Context:** Core app complete (auth, import, OCR, verification, trends, export, medications, assistant, memory). These three items are the remaining product decisions and the next major epic.

---

## Table of Contents

1. [Voice Logging (MED-VOICE-001)](#1-voice-logging-med-voice-001)
2. [Gamification v1 — Streaks + Badges (GAM-001)](#2-gamification-v1--streaks--badges-gam-001)
3. [INGEST-EPIC-001 — Imaging, Pathology & Visit Notes](#3-ingest-epic-001--imaging-pathology--visit-notes)

---

## 1. Voice Logging (MED-VOICE-001)

### Scope

Browser-based voice-to-text dose note capture with mobile-ready API contract.

### Decisions

| # | Decision | Answer |
|---|----------|--------|
| 1 | Platform | Web v1 via browser Web Speech API; API contract supports future mobile native STT |
| 2 | Audio storage | None — HealthCentral stores only the confirmed text transcript. Speech recognition may be processed by the browser's speech service (e.g., Google for Chrome) |
| 3 | Consent | Per-profile server toggle (off by default) + first-use explanatory modal before browser mic prompt |
| 4 | Transcript storage | Reuse `DoseTaken.notes` field, prefixed with `[Voice]` |
| 5 | Voice scope | Transcript/notes only — user manually controls taken/skipped, which medication |
| 6 | Settings persistence | Per-profile (server-stored on `UserModelSettings` table, syncs across devices) |
| 7 | Browser support | Runtime feature-detect `SpeechRecognition` / `webkitSpeechRecognition`; mic icon hidden on unsupported browsers |

### Infrastructure Prerequisite

Update `src/backend/security/security_headers.py` Permissions-Policy from `microphone=()` to `microphone=(self)`. Camera and geolocation remain blocked.

### Profile Preferences (Backend Shape)

Add two columns to `UserModelSettings` (existing per-profile table in profile DB):

```sql
ALTER TABLE user_model_settings ADD COLUMN voice_logging_enabled BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE user_model_settings ADD COLUMN voice_modal_seen BOOLEAN NOT NULL DEFAULT 0;
```

API endpoints for frontend read/write:
- `GET /settings/voice` → `{ voice_logging_enabled: bool, voice_modal_seen: bool }`
- `PATCH /settings/voice` → `{ voice_logging_enabled?: bool, voice_modal_seen?: bool }`

### User Flow

1. User enables "Voice Logging" in Settings → `PATCH /settings/voice { voice_logging_enabled: true }`
2. First use: modal explains privacy posture ("We don't store audio; we store only the text you confirm. Speech recognition may be processed by your browser's speech service.") → user acknowledges → `PATCH /settings/voice { voice_modal_seen: true }` → then browser mic permission prompt fires
3. Mic icon appears on dose logging screens (only when `voice_logging_enabled && voice_modal_seen && SpeechRecognition available`)
4. Tap dose → tap mic → browser listens → transcript displayed → user edits/confirms → dose logged
5. `DoseTaken` record saved: `log_method='voice'`, `notes='[Voice] <transcript>'`, `taken_at=now`

### Transcript / Notes Behavior

- If user has no prior notes: `notes = '[Voice] <transcript>'`
- If user already typed notes: append `'\n[Voice] <transcript>'` to existing notes
- Empty transcript blocks the "Confirm" button (user must speak or cancel)
- No double-prefixing: if notes already starts with `[Voice]`, append without prefix

### Failure Modes

| Scenario | UX |
|----------|-----|
| Mic permission denied | Toast: "Microphone access denied. You can enable it in browser settings." Manual logging remains available |
| Unsupported browser | Mic icon not rendered. No degradation to manual flow |
| No speech detected (5s timeout) | Toast: "No speech detected. Try again or type manually." |
| Network error during recognition | Toast: "Speech recognition unavailable. Try again or type manually." |
| Cancel/stop mid-recording | Discard partial transcript, return to dose modal |
| Max listen duration | 30s cap; auto-stop and show partial transcript for confirmation |

### Accessibility

- Keyboard-operable mic toggle (Enter/Space to start/stop)
- `aria-live="polite"` region for transcript updates
- Screen reader announcements for recording state changes ("Recording started", "Recording stopped")
- Focus management: focus returns to confirm button after transcript appears

### Deliverables

- **Backend:** Alembic migration for `voice_logging_enabled` + `voice_modal_seen` on `UserModelSettings`; update Permissions-Policy header; voice settings API endpoints
- **Frontend:** Settings toggle, first-use modal (sequenced before mic prompt), mic button component with SpeechRecognition feature-detect, transcript confirm step, notes append logic
- **Tests:** Frontend (mock SpeechRecognition API), backend (dose with `log_method='voice'`, settings CRUD)
- **Docs:** Update `docs/api/endpoints.md` to match actual dose logging payload (`log_method`, `was_skipped`, `notes`)

### Out of Scope v1

- Mobile native STT (future — API contract ready)
- Audio file upload/storage
- Offline voice recognition
- NLP command parsing (extracting time, dosage, medication from speech)
- Multi-language STT

### Acceptance Criteria

- [ ] Voice logging works end-to-end: mic → transcript → confirmed dose with `log_method="voice"` and `[Voice]`-prefixed notes
- [ ] Settings toggle persists per-profile; first-use modal appears once before mic prompt
- [ ] Unsupported/denied-permission paths fail gracefully; manual logging always available
- [ ] Permissions-Policy updated to allow microphone
- [ ] API docs (`endpoints.md`) updated to match real request/response schema

---

## 2. Gamification v1 — Streaks + Badges (GAM-001)

### Scope

Medication adherence streak tracking with 8 achievement badges.

### Decisions

| # | Decision | Answer |
|---|----------|--------|
| 1 | Approach | Streaks + badges (not points/leaderboard) |
| 2 | Badge count | Extended set of 8 |
| 3 | Streak computation | Derived from existing `DoseTaken` records, using `taken_at` in profile timezone |
| 4 | Timezone | Per-profile stored IANA timezone (default `'UTC'`), added to `UserModelSettings` |
| 5 | Ended medications | Streak computed as-of `min(today_local, medication.ended_at)` |
| 6 | Badge toast | Dose log response includes `newly_earned_badges` array |
| 7 | Existing endpoints | `GET /medications/{id}/stats` remains canonical for medication-level streaks |
| 8 | Perfect Week | Requires dose logging UI to send `schedule_id` (scope addition) |

### Badge Definitions

| Badge | Criteria | Trigger |
|-------|----------|---------|
| First Log | 1 dose logged | On first `DoseTaken` insert |
| 3-Day Streak | 3 consecutive days with at least 1 dose | Streak counter reaches 3 |
| Week Warrior | 7 consecutive days | Streak counter reaches 7 |
| Two-Week Titan | 14 consecutive days | Streak counter reaches 14 |
| Month Master | 30 consecutive days | Streak counter reaches 30 |
| Perfect Week | All scheduled doses within ±60 min for 7 consecutive days | Weekly schedule-linked check |
| Multi-Med Master | 7-day streak on 2+ medications simultaneously | Cross-medication streak check |
| Comeback Kid | Resume logging after 3+ calendar day gap | Detect gap then new log |

### Edge Cases

- **Missed day:** Streak resets to 0; Comeback Kid eligible after 3+ day gap
- **Schedule change:** Streak continues if new schedule is met on the day of change
- **Medication ended:** Streak computed as-of `min(today_in_profile_tz, medication.ended_at)`. Logging after end date rejected (medication inactive). Badges already earned are permanent
- **Backdated logs:** Use `taken_at` (not `created_at`) converted to profile timezone for streak grouping

### Timezone Handling

Add to `UserModelSettings`:

```sql
ALTER TABLE user_model_settings ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC';
```

- IANA timezone string (e.g., `'America/New_York'`)
- User sets in Settings page; defaults to `'UTC'` until set
- All streak/badge computations group `DoseTaken.taken_at` by calendar date in this timezone
- API: `GET /settings/timezone` and `PATCH /settings/timezone`

### Schema

New tables in profile DB:

```sql
CREATE TABLE badge_definition (
    id TEXT PRIMARY KEY,           -- e.g., 'first-log', 'week-warrior'
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL,             -- icon identifier: 'spark', 'flame', 'trophy', 'star', 'shield', 'rocket', 'medal', 'heart'
    criteria_type TEXT NOT NULL,    -- 'streak', 'count', 'pattern', 'gap'
    criteria_json TEXT NOT NULL,    -- e.g., {"streak_days": 7} or {"gap_days": 3, "action": "resume"}
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE earned_badge (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    badge_id TEXT NOT NULL REFERENCES badge_definition(id),
    medication_id TEXT NOT NULL DEFAULT '',  -- '' for global badges (avoids SQLite NULL uniqueness bug)
    earned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, badge_id, medication_id)
);
```

**Note:** `medication_id=''` (empty string) for global badges (First Log, Multi-Med Master, Comeback Kid) to ensure the UNIQUE constraint works correctly in SQLite/SQLCipher (multiple NULLs are allowed, but empty strings are unique).

### Dose Logging UI Change (Perfect Week Prerequisite)

Update `DoseLoggingModal` to auto-match each dose to the nearest active `MedicationSchedule`:

1. On modal open, fetch active schedules for the medication
2. Find the schedule entry closest to `taken_at` (within same calendar day in profile TZ)
3. Send `schedule_id` as query parameter on `POST /medications/{med_id}/doses`
4. Backend computes `variance_minutes` from schedule time
5. If no schedule matches (PRN medication), `schedule_id` omitted, `variance_minutes=NULL`

**Perfect Week criteria:** For 7 consecutive calendar days, every scheduled dose has a corresponding `DoseTaken` with `|variance_minutes| <= 60`. Days with only PRN medications are excluded from the check.

### API Changes

**Dose log response (updated):**

```json
POST /medications/{med_id}/doses
Response: {
  "dose": {
    "id": "...",
    "medication_id": "...",
    "taken_at": "2026-03-04T08:00:00Z",
    "log_method": "manual",
    "notes": null,
    "variance_minutes": 5
  },
  "newly_earned_badges": [
    {
      "badge_id": "week-warrior",
      "name": "Week Warrior",
      "description": "7 consecutive days of adherence",
      "icon": "flame",
      "medication_id": "med-123",
      "earned_at": "2026-03-04T08:00:01Z"
    }
  ]
}
```

**Badge listing:**

```json
GET /gamification/badges
Response: {
  "badges": [
    {
      "id": "first-log",
      "name": "First Log",
      "description": "Log your first dose",
      "icon": "spark",
      "criteria_type": "count",
      "earned": true,
      "earned_at": "2026-02-15T10:00:00Z",
      "medication_id": ""
    },
    {
      "id": "week-warrior",
      "name": "Week Warrior",
      "description": "7 consecutive days of adherence",
      "icon": "flame",
      "criteria_type": "streak",
      "earned": false,
      "earned_at": null,
      "medication_id": null
    }
  ]
}
```

**Existing endpoint preserved:** `GET /medications/{id}/stats` continues to return `current_streak` and `longest_streak` as-is. The new `/gamification/badges` endpoint is additive for cross-medication badge listing.

### Streak Computation Algorithm

```python
def compute_streak(doses: list[DoseTaken], profile_tz: str, as_of_date: date) -> int:
    """Count consecutive days with at least one dose, backward from as_of_date."""
    dose_dates = {dose.taken_at.astimezone(tz).date() for dose in doses}
    streak = 0
    current = as_of_date
    while current in dose_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak

# For ended medications:
# as_of_date = min(today_in_tz, medication.ended_at.date())
# For active medications:
# as_of_date = today_in_tz
```

### Surfaces

- **Medication detail card:** Current streak count + flame icon (existing `stats` endpoint)
- **Dashboard:** "Achievements" widget showing earned badges (full color) and unearned (greyed, with lock icon)
- **Toast notification:** Framer Motion slide-in on badge earn (triggered from dose response `newly_earned_badges`)
- **Settings > Achievements:** Full badge grid with descriptions and earned dates

### Deliverables

- **Backend:** Alembic migration for `badge_definition` + `earned_badge` tables + `timezone` column; streak computation module; badge evaluation logic (runs inline on dose log); seed 8 badge definitions; `GET /gamification/badges` endpoint; updated dose response schema
- **Frontend:** DoseLoggingModal schedule matching; streak display component; badges grid; toast notification on earn; timezone picker in Settings
- **Tests:** Streak computation edge cases (gaps, ended meds, timezone boundaries); badge evaluation for each of the 8 badges; dose response with `newly_earned_badges`; SQLite uniqueness constraint for global badges

### Out of Scope v1

Points, leaderboards, badge sharing, custom badges, badge revocation, schedule history tracking

### Acceptance Criteria

- [ ] Streak counter displays correctly on medication card, resets on missed days
- [ ] Ended medication streaks frozen at `min(today, ended_at)`
- [ ] All 8 badges earnable with correct criteria evaluation
- [ ] Global badges use `medication_id=''` (no duplicate earned_badge rows)
- [ ] Toast notification fires on badge earn via dose response
- [ ] Badges persist across sessions (server-stored in profile DB)
- [ ] DoseLoggingModal sends `schedule_id` for scheduled medications
- [ ] Perfect Week correctly evaluates `variance_minutes` within ±60
- [ ] Timezone stored per-profile; streak/badge computation uses profile timezone

---

## 3. INGEST-EPIC-001 — Imaging, Pathology & Visit Notes

### Scope

Extend document ingestion to classify and extract structured entities from imaging reports, pathology reports, and visit notes.

### Decisions

| # | Decision | Answer |
|---|----------|--------|
| 1 | Classification timing | Synchronous at import (user sees category immediately after OCR) |
| 2 | Multi-category docs | Single primary category per document (user can manually re-classify) |
| 3 | HL7/FHIR import | Not in v1 (OCR-only) |
| 4 | Confidence threshold | 0.7 (entities below shown with "low confidence" badge, user can correct) |
| 5 | ICD lookup | Not in v1 (store raw diagnosis text; ICD mapping is future enhancement) |
| 6 | Phasing | Schema + Imaging first, then Pathology, Visit Notes, Frontend, RAG |

### Sub-Tickets with Dependencies

```
INGEST-A ──┬── INGEST-B (Imaging)     ──┬── INGEST-E (Frontend)
           ├── INGEST-C (Pathology)    ──┤
           └── INGEST-D (Visit Notes)  ──┘── INGEST-F (RAG)
```

| Ticket | Scope | Depends on | Parallelizable with | Effort |
|--------|-------|------------|---------------------|--------|
| **INGEST-A** | Schema migration + rule-based category classifier | None | — | 1 sprint |
| **INGEST-B** | Imaging entity extractor + tests | INGEST-A | INGEST-C, INGEST-D | 1 sprint |
| **INGEST-C** | Pathology entity extractor + tests | INGEST-A | INGEST-B, INGEST-D | 1 sprint |
| **INGEST-D** | Visit notes entity extractor + tests | INGEST-A | INGEST-B, INGEST-C | 1 sprint |
| **INGEST-E** | Frontend display components | INGEST-B, C, D | INGEST-F | 1 sprint |
| **INGEST-F** | RAG integration + category-aware retrieval | INGEST-B, C, D | INGEST-E | 1 sprint |

**Parallelization:** B, C, D are independent after A. E and F are independent after B+C+D. Minimum critical path: 3 sprints (A → B/C/D parallel → E/F parallel).

### Entity Types by Category

**Imaging:**

| Entity | Example |
|--------|---------|
| modality | MRI, CT, X-ray, Ultrasound |
| body_region | lumbar spine, chest, abdomen |
| finding | disc herniation at L4-L5, consolidation |
| impression | No acute abnormality |
| laterality | left, right, bilateral |
| contrast_used | with contrast, without contrast |
| ordering_provider | Dr. Smith |
| report_date | 2026-01-15 |

**Pathology:**

| Entity | Example |
|--------|---------|
| specimen_type | biopsy, excision, cytology |
| specimen_site | left breast, colon |
| diagnosis | Basal cell carcinoma, well-differentiated |
| grade | Grade 1, well-differentiated |
| stage | T1N0M0 |
| margins | negative, positive at deep margin |
| special_stains | Ki-67: 15% |
| pathologist | Dr. Jones |
| report_date | 2026-02-01 |

**Visit Notes:**

| Entity | Example |
|--------|---------|
| visit_type | progress note, discharge summary, consult |
| chief_complaint | chest pain, follow-up hypertension |
| assessment | HTN well-controlled |
| plan | continue lisinopril, recheck in 3 months |
| diagnoses | Hypertension, Type 2 Diabetes |
| provider | Dr. Williams |
| visit_date | 2026-02-20 |
| vitals | BP 120/80, HR 72, Temp 98.6 |

### Schema (Profile DB)

```sql
CREATE TABLE document_category (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(id),
    category TEXT NOT NULL,           -- 'imaging', 'pathology', 'visit_notes', 'lab'
    confidence REAL NOT NULL,
    classified_by TEXT NOT NULL,       -- 'rule', 'llm', 'manual'
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_entity (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(id),
    category TEXT NOT NULL,
    entity_type TEXT NOT NULL,         -- 'finding', 'diagnosis', 'modality', etc.
    entity_value TEXT NOT NULL,
    confidence REAL NOT NULL,
    source_page INTEGER,
    source_bbox_json TEXT,            -- OCR bounding box for highlighting
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_doc_category_doc_id ON document_category(doc_id);
CREATE INDEX idx_doc_entity_doc_id ON document_entity(doc_id);
CREATE INDEX idx_doc_entity_type ON document_entity(entity_type);
```

### Category Classifier (INGEST-A)

Rule-based first pass using regex keyword matching:

| Category | Keywords (examples) | Confidence |
|----------|-------------------|------------|
| imaging | MRI, CT scan, X-ray, ultrasound, radiograph, FINDINGS, IMPRESSION | 1.0 strong match, 0.8 partial |
| pathology | biopsy, specimen, histologic, cytology, surgical pathology, DIAGNOSIS, margins | 1.0 strong match, 0.8 partial |
| visit_notes | chief complaint, assessment, plan, progress note, discharge summary, vital signs | 1.0 strong match, 0.8 partial |
| unknown | No keywords above 0.7 threshold | — |

Fallback: `category='unknown'` if no match above 0.7. User can manually re-classify via frontend.

### Extraction Pipeline

```
Document → OCR (existing) → Category Classification → Category-Specific Extractor → Entities → DB
                                                        ├── extract_imaging.py
                                                        ├── extract_pathology.py
                                                        └── extract_visit_notes.py
```

Each extractor:
1. Receives OCR text + page metadata
2. Applies category-specific regex patterns to extract entity types
3. Assigns confidence score per entity (1.0 for exact pattern, 0.7-0.9 for partial)
4. Returns list of `DocumentEntity` objects
5. Entities with confidence < 0.7 still stored but flagged as low-confidence in UI

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Regex misses non-standard report formats | Medium | Confidence scores + manual correction UI + LLM fallback in future |
| Multi-category documents misclassified | Medium | Single primary + manual re-classify UI |
| Pathology diagnoses are sensitive PHI | High | Same SQLCipher encryption pipeline; no new exposure surface |
| Large OCR text slows classification | Low | Classification runs on first 2 pages only; full extraction on all pages |

### Out of Scope v1

HL7/FHIR structured data import, ICD code lookup/mapping, LLM-based classification, multi-category per document, entity relationship mapping, SNOMED/LOINC coding

### Acceptance Criteria

**INGEST-A:**
- [ ] `document_category` and `document_entity` tables created via Alembic migration
- [ ] Category classifier correctly identifies imaging/pathology/visit_notes on 10+ sample documents
- [ ] Unknown category assigned when no keywords match above 0.7

**INGEST-B:**
- [ ] Imaging extractor extracts all 8 entity types from 5+ sample imaging reports
- [ ] Extracted entities have confidence >= 0.7

**INGEST-C:**
- [ ] Pathology extractor extracts all 8 entity types from 5+ sample pathology reports
- [ ] Extracted entities have confidence >= 0.7

**INGEST-D:**
- [ ] Visit notes extractor extracts all 8 entity types from 5+ sample visit notes
- [ ] Extracted entities have confidence >= 0.7

**INGEST-E:**
- [ ] Category badge visible on document cards in document list
- [ ] Entity detail view renders per category with appropriate layout
- [ ] Low-confidence entities visually distinguished (e.g., dashed border, warning icon)
- [ ] Manual re-classification UI updates category and re-runs extraction

**INGEST-F:**
- [ ] Assistant queries can filter by document category
- [ ] Entity-boosted search: queries mentioning extracted entities rank relevant documents higher
- [ ] Category filter available in RAG retrieval pipeline

---

## Implementation Priority

| Priority | Feature | Prerequisites | Estimated Effort |
|----------|---------|---------------|------------------|
| 1 | Gamification v1 (GAM-001) | Dose logging UI schedule matching | ~1.5 sprints |
| 2 | Voice Logging (MED-VOICE-001) | Permissions-Policy update | ~1 sprint |
| 3 | INGEST-EPIC-001 | None (independent) | ~3 sprints (with parallelization) |

**Shared prerequisite:** Both Voice Logging and Gamification add columns to `UserModelSettings`, so their migrations should be coordinated (or combined into a single migration if shipped in the same sprint).

---

## References

- `docs/plans/roadmap_gap_closure.md` — Original decision tickets (PRD-DEC-VOICE-001, PRD-DEC-GAM-001)
- `docs/plans/ingest-imaging-pathology-spec.md` — Detailed INGEST-EPIC-001 specification
- `docs/features/02_medication_adherence_coach_architecture.md` — Existing streak templates and voice logging architecture
- `docs/features/03_features_prd.md` — Product requirements document
- `src/backend/security/security_headers.py:21` — Permissions-Policy header (mic blocked)
- `src/backend/models/model_settings.py` — UserModelSettings table (preferences target)
- `src/backend/api/medications.py:113` — Current dose logging API
- `src/frontend/src/components/medication-coach/DoseLoggingModal.tsx:33` — Current dose logging UI
