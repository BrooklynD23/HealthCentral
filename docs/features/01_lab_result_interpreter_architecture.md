# Personal Lab Result Interpreter - Architecture Document

*Version 0.1 | January 2025 | Draft - (PM Approved)

---

## 1. Feature Overview

The Personal Lab Result Interpreter transforms raw lab results into actionable health insights by providing:
- Easy-to-understand explanations of biomarkers
- Personalized health advice based on actual values and trends
- Contextualized information that patient portals lack

### User Stories

**US-1: Upload and Interpret Lab Results**
- User uploads lab PDF through existing document import flow
- System generates plain-language interpretations with citations
- Medical disclaimers prominently displayed 

**US-2: View Personalized Health Advice**
- Recommendations reference actual patient values
- Suggestions are conservative and evidence-based
- All advice includes "consult your doctor" framing

**US-3: Track Context Over Time**
- Trend analysis shows direction of change
- Interpretations consider improving/worsening patterns
- "New abnormal" vs "chronically abnormal" differentiation

**US-4: Understand Biomarker Relationships**
- System identifies related biomarkers (lipid panel, etc.)
- Explanations reference relationships
- Panel-level interpretations when appropriate

---

## 2. Integration with Existing Pipeline

```
Existing Flow:
Import → Extract → Normalize → Verify → [NEW: Interpret] → Visualize → RAG → Export

Integration Points:
1. Trigger: After user verifies observations
2. Input: Verified observations from observations table
3. Output: Interpretations stored in new tables
4. Export: Interpretations included in doctor-ready summaries
```

---

## 3. Data Architecture

### New Tables

**`lab_interpretations`**
```python
class LabInterpretation(Base):
    id: str                        # Primary key
    profile_id: str                # FK to profiles
    observation_id: str            # FK to observations (unique)
    interpretation_text: str       # Plain-language explanation
    severity_level: str            # "normal", "borderline", "abnormal", "critical"
    advice_text: Optional[str]     # Personalized recommendations
    citations_json: str            # JSON array of citations
    context_json: Optional[str]    # Trend, historical context
    model_id: str                  # Model provenance
    confidence_score: float        # 0.0-1.0
    requires_physician_review: bool
    created_at: datetime
```

**`panel_interpretations`**
```python
class PanelInterpretation(Base):
    id: str
    profile_id: str
    panel_name: str                # "lipid", "thyroid", "cbc", "cmp"
    collected_at: datetime
    observation_ids_json: str      # Observations in panel
    summary_text: str              # Holistic interpretation
    overall_status: str
    relationship_insights_json: Optional[str]  # Ratios, patterns
    advice_text: Optional[str]
    citations_json: str
```

**`biomarker_knowledge`**
```python
class BiomarkerKnowledge(Base):
    id: str
    analyte_canonical: str
    description: str               # What it measures
    clinical_significance: str     # Why it's tested
    normal_interpretation: str
    high_interpretation: str
    low_interpretation: str
    ref_range_adult_json: str      # By sex
    common_causes_high_json: Optional[str]
    common_causes_low_json: Optional[str]
    sources_json: str              # Clinical guidelines, etc.
    last_reviewed: datetime
```

**`intervention_mappings`**
```python
class InterventionMapping(Base):
    id: str
    analyte_canonical: str
    condition_type: str            # "high", "low", "ratio_abnormal"
    category: str                  # "diet", "exercise", "lifestyle"
    intervention_text: str
    strength_of_evidence: str      # "strong", "moderate", "limited"
    contraindications_json: Optional[str]
    priority: int
    sources_json: str
```

**`biomarker_relationships`**
```python
class BiomarkerRelationship(Base):
    id: str
    primary_analyte: str
    related_analyte: str
    relationship_type: str         # "ratio", "inverse_correlation", "panel_member"
    description: str
    clinical_significance: str
    ratio_calculation: Optional[str]  # e.g., "total_cholesterol / hdl"
    ratio_target_range_json: Optional[str]
```

---

## 4. AI/ML Pipeline

### Model Selection

The system uses a **hardware-adaptive tiered provider system** that automatically selects the optimal LLM provider and model based on available hardware. The provider layer (`src/backend/core/llm/`) is model-agnostic and supports:

**Providers:**
- `llama_cpp_provider` (default): Embeds llama.cpp; auto-detects chat template from GGUF
- `ollama_provider` (optional): Requires localhost Ollama service

**Hardware Tiers** (auto-detected at startup, overridable by user):
- **Tier 1 (High):** BioMistral-7B | GPU 8GB+ VRAM or 32GB+ RAM | Best medical accuracy
- **Tier 2 (Mid):** Phi-3-mini + Enhanced RAG | GPU 4-6GB VRAM or 16GB RAM | Good with strong KB
- **Tier 3 (Low):** Qwen2.5-0.5B + RAG | CPU-only, 8GB RAM | Basic, KB-heavy
- **Gemma 4 alternates:** gemma4-e2b / gemma4-e4b / gemma4-12b | GPU preferred, CPU viable | Registered/read-visible in model config, but current set/download write APIs accept only `low`, `mid`, and `high`

Provider/model selection is configurable via `GET`/`PUT /api/v1/settings/model/provider` and managed by `modules/model_selector.py` + `modules/hardware_detection.py`.

### Interpretation Pipeline

```
1. Context Assembly
   - Fetch observation details
   - Retrieve historical values
   - Calculate trends
   - Identify related abnormalities

2. Knowledge Retrieval
   - Query biomarker_knowledge for analyte
   - Retrieve intervention_mappings
   - Fetch biomarker_relationships

3. Severity Classification
   - Compare value to reference range
   - Consider degree of deviation
   - Check critical value thresholds

4. Interpretation Generation (LLM)
   - Compose structured prompt
   - Generate with BioMistral
   - Enforce citation requirements

5. Advice Generation
   - Retrieve applicable interventions
   - Filter by safety constraints
   - Prioritize by evidence strength
   - Personalize with specific values

6. Safety Validation
   - Check for prohibited content
   - Verify citation presence
   - Ensure disclaimers included
   - Flag critical values

7. Storage & Audit
   - Save to lab_interpretations
   - Log model version and confidence
   - Audit log entry
```

### Biomarker Grounding

The assistant RAG pipeline grounds biomarker-related responses in **two independent citation layers**:

**Patient's Own Results `[YOUR_RESULTS:N]`:**
- Latest measured value for the biomarker
- Normal reference range (sex-specific if applicable)
- Trend direction over time (improving/stable/worsening)
- Extracted from patient's observation history

**General Reference Knowledge `[REFERENCE:N]`:**
- Auto-seeded at startup via `seed_knowledge_base.py` if empty
- Clinical significance of the biomarker
- Common causes of abnormality
- General management principles
- Sourced from `biomarker_knowledge` table

**Response Structure:**
- "Report Facts" section cites `[YOUR_RESULTS:N]` exclusively (patient's personal data context)
- "General Info" section cites `[REFERENCE:N]` exclusively (reference KB context)
- This separation maintains the education-only framing and ensures no medical advice is provided
- All outputs include disclaimers directing user to healthcare provider

### Safety Guardrails

```python
class InterpretationSafetyGuard:
    PROHIBITED_PATTERNS = [
        r"\b(you have|you are diagnosed with|diagnosis of)\s+\w+",
        r"\btake\s+\d+\s*(mg|mcg|g|ml)",  # Dosing
        r"\b(prescribe|prescription|medication dosage)\b",
        r"\b(definitely|certainly|always means)\b",  # Certainty
        r"\b(emergency|call 911|go to ER)\b",
    ]

    REQUIRED_DISCLAIMERS = [
        "consult",
        "healthcare provider",
        "educational",
    ]
```

---

## 5. API Endpoints

```python
@router.post("/api/v1/interpretations/observations/{observation_id}/interpret-grounded")
async def generate_interpretation(observation_id: str, force_regenerate: bool = False)

@router.get("/api/v1/interpretations/observations/{observation_id}/interpretation")
async def get_interpretation(observation_id: str)

@router.post("/api/v1/interpretations/panels/{panel_name}/interpret")
async def generate_panel_interpretation(panel_name: str, collected_at: datetime)

@router.get("/api/v1/interpretations/recent")
async def get_recent_interpretations(limit: int = 10)

@router.get("/api/v1/interpretations/knowledge/biomarker/{analyte_canonical}")
async def get_biomarker_knowledge(analyte_canonical: str)

@router.post("/api/v1/interpretations/batch")
async def batch_generate_interpretations(observation_ids: list[str])
```

---

## 6. Frontend Components

| Component | Purpose |
|-----------|---------|
| `InterpretedResultCard` | Display observation with interpretation |
| `InterpretedTrendChart` | Recharts with interpretation annotations |
| `PanelInterpretationDashboard` | Holistic panel view |
| `ReferenceRangeComparison` | Visual bar comparison |
| `CitationTooltip` | Expandable citation display |
| `DisclaimerBanner` | Persistent safety disclaimer |
| `AdviceSection` | Collapsible recommendations |

---

## 7. Privacy & Safety

### Local-First Processing
- All interpretation runs on local BioMistral model
- Knowledge base stored locally (SQLite)
- No telemetry or usage tracking
- Network requests blocked at module level

### Disclaimer System

**Feature Activation Disclaimer (one-time):**
```
IMPORTANT MEDICAL DISCLAIMER

The Lab Result Interpreter provides educational information only.

This feature:
✓ Explains what biomarkers measure
✓ Provides general health education
✓ Suggests lifestyle considerations

This feature does NOT:
✗ Diagnose medical conditions
✗ Recommend medications or treatments
✗ Replace professional medical advice
✗ Provide emergency guidance

ALWAYS consult your healthcare provider.
```

### Citation Requirements
- Every factual claim must cite `[KB:source_id]` or `[INT:intervention_id]`
- Validation rejects responses without citations
- UI displays sources with hover tooltips

---

## 8. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Database models and migrations
- Knowledge base seed data (20-30 biomarkers)
- BioMistral model integration
- Basic inference testing

### Phase 2: Core Engine (Week 3-4)
- InterpretModule class
- Safety guardrails
- Recommendation engine
- Unit tests

### Phase 3: API Layer (Week 5)
- REST endpoints
- Pydantic schemas
- Authentication checks
- Rate limiting

### Phase 4: Frontend (Week 6-7)
- UI components
- Page integration
- Accessibility testing

### Phase 5: Panel Interpretations (Week 8)
- Panel detection
- Relationship analysis
- Dashboard display

### Phase 6: Testing & Polish (Week 9-10)
- Adversarial safety testing
- User testing
- Performance optimization

---

## 9. Files to Create

**Backend:**
```
src/backend/
├── models/
│   ├── interpretation.py          # LabInterpretation, PanelInterpretation
│   └── knowledge_base.py          # BiomarkerKnowledge, InterventionMapping
├── modules/
│   ├── interpret.py               # Main interpretation pipeline
│   ├── interpret_safety.py        # Safety guardrails
│   ├── recommend.py               # Recommendation engine
│   └── knowledge_loader.py        # Load medical knowledge base
├── api/
│   ├── interpretations.py         # API routes
│   └── schemas/interpretation.py  # Pydantic schemas
└── scripts/
    └── seed_knowledge_base.py     # Populate initial knowledge
```

**Frontend:**
```
src/frontend/src/
├── components/features/interpreter/
│   ├── InterpretedResultCard.tsx
│   ├── InterpretedTrendChart.tsx
│   ├── PanelInterpretationDashboard.tsx
│   ├── ReferenceRangeComparison.tsx
│   ├── CitationTooltip.tsx
│   ├── DisclaimerBanner.tsx
│   └── AdviceSection.tsx
├── pages/LabInterpreter.tsx
├── services/interpretationService.ts
└── hooks/useInterpretation.ts
```

---

## 10. Knowledge Base Curation

### Priority Biomarkers (Phase 1)

1. **CBC:** Hemoglobin, Hematocrit, RBC, WBC, Platelets, MCV, MCH, MCHC, RDW
2. **CMP:** Glucose, BUN, Creatinine, Sodium, Potassium, Chloride, CO2, Calcium, Albumin, Bilirubin, ALP, AST, ALT
3. **Lipid Panel:** Total Cholesterol, LDL, HDL, Triglycerides
4. **Thyroid:** TSH, Free T4, Free T3
5. **Vitamins:** Vitamin D, B12, Folate
6. **Iron Studies:** Iron, Ferritin, TIBC, Transferrin Saturation
7. **Diabetes:** HbA1c, Fasting Glucose
8. **Inflammation:** CRP, ESR

### Data Sources
- American Heart Association guidelines
- American Diabetes Association guidelines
- Endocrine Society guidelines
- PubMed literature reviews
- Harrison's Principles of Internal Medicine

---

## 11. Resolved Decisions

### Model Selection: Hardware-Adaptive Tiered System ✓

The system auto-detects hardware and selects the appropriate model tier:

| Tier | Hardware | Model | Quality |
|------|----------|-------|---------|
| **Tier 1** (High) | GPU 8GB+ VRAM or 32GB+ RAM | BioMistral-7B | Best medical accuracy |
| **Tier 2** (Mid) | GPU 4-6GB VRAM or 16GB RAM | Phi-3 Mini + Enhanced RAG | Good with strong KB |
| **Tier 3** (Low) | CPU-only, 8GB RAM | Qwen2.5 0.5B + RAG | Basic, KB-heavy |
| **Tier 4** (Minimal) | Limited hardware | Template-based only | All facts from KB |

- Auto-detect at startup with user override option
- Graceful degradation if model fails to load
- User can choose smaller model for speed

### Knowledge Base: Free/Open Source Stack ✓

| Source | License | Content |
|--------|---------|---------|
| LOINC | Free (Regenstrief) | Test codes, canonical names |
| Awesome Biomarkers | Open Source | Reference ranges |
| Open Medical KB | CC BY 4.0 | Disease/observation relationships |
| PubMed Abstracts | Free API | Evidence citations |
| Custom Curation | Internal | Plain-language explanations |

### Platform: Desktop-First with Mobile-Ready Architecture ✓

- Windows desktop MVP (Tauri/Electron)
- API designed to support future mobile clients
- Notification system abstracted for cross-platform
- Android APK planned for future release (v0.3+)

### Notifications: Opt-In Only ✓

- Disabled by default
- User explicitly enables in settings
- Clear explanation of what notifications will do
- Easy to disable at any time

## 12. Remaining Open Decisions

- [ ] Export format for interpretations (PDF, JSON, both?)
- [ ] Interpretation regeneration policy (auto vs manual)
- [ ] Knowledge base update frequency
