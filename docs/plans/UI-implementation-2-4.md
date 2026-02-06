# HealthCentral Implementation Plan

## Status Corrections

Based on codebase exploration, several items from the original summary are **already implemented**:

| Feature | Status | Evidence |
|---------|--------|----------|
| Rate limiting | **DONE** | `src/backend/core/rate_limiter.py` - Sliding-window, per-IP |
| Token revocation | **DONE** | `src/backend/core/token_revocation.py` - JWT revocation on logout/lock |
| Alembic migrations | **DONE** | Commit `c1d6cf9` - Dual-environment support |
| Document encryption | **DONE** | `src/backend/core/security.py` - AES-256-GCM |

## Actual Remaining Work

### Priority 1: Frontend UI (Backend Ready)
- Lab Interpreter UI components (7 components)
- Medication Coach UI components (6 components)

### Priority 2: Security Gaps
- CORS headers too permissive (`allow_headers=["*"]`)
- Legacy plaintext fallback not strictly enforced

### Priority 3: RAG Enhancement
- Document chunking pipeline
- Vector embeddings (FAISS/sqlite-vss)
- Enhanced retrieval

### Priority 4: Other Features
- OCR Support (P2)
- Imaging Report Handling (P1)

---

## Phase 4A: Lab Interpreter Foundation (Week 1)

**Objective**: Core UI components for single lab result interpretation

### Deliverables

**1. Service Layer** - `src/frontend/src/services/interpretations.ts`
```typescript
// Types
InterpretationResponse, PanelInterpretationResponse,
BiomarkerKnowledge, CitationResponse

// API Functions
generateInterpretation(observationId, forceRegenerate?)
getInterpretation(observationId)
generatePanelInterpretation(panelName, collectedAt, forceRegenerate?)
getBiomarkerKnowledge(analyteCanonical)
batchGenerateInterpretations(observationIds, forceRegenerate?)

// React Query Hooks
useInterpretation(observationId)
useGenerateInterpretation()
usePanelInterpretation(panelName, collectedAt)
useBiomarkerKnowledge(analyte)
```

**2. Core Components** - `src/frontend/src/components/lab-interpreter/`

| Component | Purpose |
|-----------|---------|
| `InterpretedResultCard.tsx` | AI interpretation with severity badge, text, citations |
| `CitationTooltip.tsx` | Popover showing source details (Radix Tooltip) |
| `DisclaimerBanner.tsx` | Medical disclaimer with caution styling |
| `AdviceSection.tsx` | Lifestyle and follow-up recommendations |
| `ReferenceRangeComparison.tsx` | Visual bar comparing value to normal range |

**3. Integration**
- Add "Get Interpretation" button to TrendsDashboard analyte detail
- Show interpretation in expandable panel

### Critical Files
- Pattern: `src/frontend/src/services/observations.ts`
- Backend: `src/backend/api/interpretations.py`

### Verification
- [ ] InterpretedResultCard renders with citations
- [ ] CitationTooltip shows on hover/focus
- [ ] DisclaimerBanner always visible
- [ ] Unit tests pass

---

## Phase 4B: Lab Interpreter Advanced (Week 2)

**Objective**: Panel interpretation dashboard and trend overlays

### Deliverables

**1. Panel Components** - `src/frontend/src/components/lab-interpreter/`

| Component | Purpose |
|-----------|---------|
| `PanelInterpretationDashboard.tsx` | Holistic view for CBC/CMP/Lipid/Thyroid |
| `InterpretedTrendChart.tsx` | LineChart with interpretation annotations |

**2. Lab Interpreter Page** - `src/frontend/src/pages/LabInterpreter.tsx`
- Panel tabs (CBC, CMP, Lipid, Thyroid)
- Panel summary with relationship insights
- Individual biomarker deep-dive on click

**3. Navigation Update**
- `src/frontend/src/components/layout/Sidebar.tsx` - Add "Interpret" link
- `src/frontend/src/App.tsx` - Add route
- `src/frontend/src/pages/index.ts` - Export

### Critical Files
- Pattern: `src/frontend/src/pages/TrendsDashboard.tsx` (tabs, charts)

### Verification
- [ ] Panel dashboard shows 4 tabs
- [ ] Panel interpretation generates and displays
- [ ] Trend chart shows annotations
- [ ] E2E test passes

---

## Phase 4C: Medication Coach Foundation (Week 3)

**Objective**: Core medication management UI

### Deliverables

**1. Service Layer** - `src/frontend/src/services/medications.ts`
```typescript
// Types
Medication, MedicationSchedule, DoseTaken, AdherenceStats

// API Functions
createMedication, getMedications, getMedication, updateMedication, deleteMedication
createSchedule, getSchedules, updateSchedule, deleteSchedule
logDose, getDoses, getAdherenceStats, learnPatterns

// React Query Hooks
useMedications(activeOnly?)
useMedication(id)
useCreateMedication()
useUpdateMedication()
useLogDose()
useAdherenceStats(medicationId)
```

**2. Core Components** - `src/frontend/src/components/medication-coach/`

| Component | Purpose |
|-----------|---------|
| `MedicationCard.tsx` | Name, dosage, frequency, next dose, adherence |
| `MedicationForm.tsx` | Add/edit medication form |
| `DoseLoggingModal.tsx` | Log taken/skipped with reason selector |

**3. Medication Coach Page** - `src/frontend/src/pages/MedicationCoach.tsx`
- List of active medications
- "Add Medication" button
- Quick-log dose on each card
- Empty state

**4. Navigation Update**
- Add "Meds" to Sidebar
- Add route in App.tsx

### Critical Files
- Backend: `src/backend/api/medications.py`

### Verification
- [ ] Medication list loads
- [ ] Create medication works
- [ ] Log dose works
- [ ] Empty state displays

---

## Phase 4D: Medication Coach Adherence (Week 4)

**Objective**: Adherence tracking, streaks, schedule management

### Deliverables

**1. Adherence Components** - `src/frontend/src/components/medication-coach/`

| Component | Purpose |
|-----------|---------|
| `AdherenceDashboard.tsx` | Stats, streaks, 7/30-day rates |
| `StreakDisplay.tsx` | Visual streak with flame icon |
| `ScheduleEditor.tsx` | Configure reminder times |

**2. Detail Page** - `src/frontend/src/pages/MedicationDetail.tsx`
- Medication info header
- Schedule list with CRUD
- Dose history with filters
- Adherence stats panel
- Pattern learning trigger

### Verification
- [ ] Adherence stats correct
- [ ] Streak calculation matches backend
- [ ] Schedule CRUD works
- [ ] Pattern learning displays

---

## Phase 5: Security Hardening (Week 3-4, Parallel)

**Objective**: Fix identified security gaps

### Deliverables

**1. CORS Restriction** - `src/backend/main.py`
```python
# Replace allow_headers=["*"] with:
allow_headers=["Content-Type", "Authorization", "X-Request-ID"]
```

**2. Encryption Enforcement**
- Audit `src/backend/modules/ingest.py` for plaintext fallback
- Add strict validation in document handlers

**3. Security Headers**
- Add CSP, X-Frame-Options, X-Content-Type-Options

### Verification
- [ ] CORS blocks unexpected headers
- [ ] Documents always encrypted
- [ ] Security headers in responses

---

## Phase 6: RAG Enhancement (Week 4-5, Parallel)

**Objective**: Improve assistant retrieval with vector search

### Deliverables

**1. Document Chunking** - `src/backend/modules/chunking.py`
- Semantic chunking by document structure
- Chunk metadata (doc_id, page, section)
- Integration with ingest pipeline

**2. Vector Storage** - `src/backend/core/vector_store.py`
- FAISS or sqlite-vss integration
- Embedding generation (sentence-transformers)
- Similarity search API

**3. Enhanced Retrieval** - `src/backend/modules/retrieval.py`
- Hybrid keyword + vector search
- Reranking step
- Update assistant API

### Verification
- [ ] Documents chunked on ingest
- [ ] Embeddings stored
- [ ] Assistant returns better results

---

## Phase 7: Testing & Accessibility (Week 5)

**Objective**: Comprehensive testing and WCAG 2.2 AA compliance

### Deliverables

**1. Unit Tests**
- All Phase 4 components
- Service layer with mocked API

**2. E2E Tests** - `src/frontend/e2e/`
- `lab-interpreter.spec.ts`
- `medication-coach.spec.ts`

**3. Accessibility**
- WCAG 2.2 AA audit
- Keyboard navigation
- Screen reader testing
- Color contrast validation

### Verification
- [ ] 80%+ coverage for new components
- [ ] E2E tests pass
- [ ] axe-core reports no critical issues

---

## Phase 8: Polish & P2 Features (Week 6)

**Objective**: OCR, imaging reports, final polish

### Deliverables

**1. OCR Support** - `src/backend/modules/ocr.py`
- Tesseract integration
- Scanned PDF detection
- OCR text extraction

**2. Imaging Reports**
- Imaging document type
- Radiology report parsing
- Display in inbox

**3. UI Polish**
- Loading animations
- Error boundaries
- Performance (lazy loading)

---

## Schedule Summary

| Week | Phase | Focus |
|------|-------|-------|
| 1 | 4A | Lab Interpreter Foundation |
| 2 | 4B | Lab Interpreter Advanced |
| 3 | 4C + 5 | Medication Coach + Security |
| 4 | 4D + 6 | Adherence + RAG Enhancement |
| 5 | 7 | Testing & Accessibility |
| 6 | 8 | Polish & P2 Features |

## Dependency Graph

```
4A -> 4B -> 4C -> 4D -> 7 -> 8
         |
5 (Security) runs parallel with 4C-4D
6 (RAG) runs parallel with 4A-4D
```

---

## Key Patterns to Follow

### Frontend Component Pattern
```typescript
// Use CVA for variants
const cardVariants = cva("base-classes", {
  variants: { severity: { high: "...", normal: "..." } }
});

// Use Card composition
<Card>
  <CardHeader><CardTitle>...</CardTitle></CardHeader>
  <CardContent>...</CardContent>
</Card>
```

### Service Hook Pattern
```typescript
export function useInterpretation(observationId: string) {
  return useQuery({
    queryKey: ['interpretations', observationId],
    queryFn: () => getInterpretation(observationId),
    enabled: !!observationId,
  });
}
```

### Page Layout Pattern
```typescript
<div className="space-y-6">
  <div className="flex items-center justify-between">
    <h1 className="font-display text-2xl">Title</h1>
    <Button>Action</Button>
  </div>
  <div className="grid grid-cols-3 gap-6">
    <Card className="col-span-2">Main</Card>
    <Card>Sidebar</Card>
  </div>
</div>
```
