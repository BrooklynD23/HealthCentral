# Product Requirements Document (PRD)
## HealthCentral Feature Expansion v0.2

*Version 0.2 | January 2025 | Windows (primary)*

**Last Updated:** 2026-02-12

---

## 1. Executive Summary

This PRD extends HealthCentral's local-first medical results companion with two new features:

1. **Personal Lab Result Interpreter** (Moderate) - AI-powered explanations and personalized advice for lab results
2. **Adaptive Medication Adherence Coach** (Light) - Intelligent reminder system that adapts to user behavior

Both features maintain HealthCentral's core principles:
- Local-first, privacy-first operation
- Conservative, grounded outputs with citations
- No diagnosis or treatment recommendations
- Windows desktop primary platform

---

## 2. Background and Problem

### User Pain Points Addressed

**Lab Result Interpretation:**
- Patient portals show numbers without actionable guidance
- Users struggle to decipher blood test reports
- No context for what values mean or what to do next
- Health anxiety increases with unclear results

**Medication Adherence:**
- Existing reminder apps are rigid about timing
- Users penalized for taking meds at 9:37am instead of 9:00am
- Lack of adaptive, supportive reminders
- No correlation between adherence and health outcomes

### Market Validation

Reddit users have expressed:
> "I wish there was an app to upload my blood test and get recommendations to improve my health"

> "I wish there was an app that could adapt if a dose was at 7am or 9:37am"

---

## 3. Goals, Non-Goals, and Principles

### Goals

**Lab Result Interpreter:**
- Provide plain-language explanations of biomarkers
- Generate personalized health advice with citations
- Show trends and context for results
- Integrate with existing document pipeline

**Medication Adherence Coach:**
- Learn user's actual medication-taking patterns
- Adapt reminder timing to behavior
- Provide supportive, non-judgmental nudges
- Track streaks and adherence statistics

### Non-Goals

- Diagnose diseases or medical conditions
- Recommend medications or dosages
- Provide emergency medical advice
- Replace healthcare provider judgment
- Sync data to cloud services (MVP)

### Principles

- **Local-first:** All processing on-device by default
- **Grounded outputs:** Every claim cites sources
- **Conservative behavior:** Prefer refusal over speculation
- **Supportive tone:** Encourage, don't judge or alarm
- **User control:** All data under user control

---

## 4. Target Users

### Primary Persona: Health-Conscious Patient
- Receives frequent lab tests (chronic conditions, preventive care)
- Takes multiple medications daily
- Wants to understand their health data
- Values privacy and local control

### Secondary Persona: Medication Manager
- Takes 3+ medications with different schedules
- Struggles with rigid reminder apps
- Needs adaptive, flexible reminders
- Values encouragement over guilt

---

## 5. Feature Specifications

### 5.1 Personal Lab Result Interpreter

#### Core Capabilities

1. **Interpretation Generation**
   - Parse verified lab observations
   - Generate plain-language explanations
   - Include severity classification (normal/borderline/abnormal/critical)
   - Cite medical knowledge base sources

2. **Personalized Advice**
   - Evidence-based lifestyle recommendations
   - Prioritized by evidence strength
   - Personalized with actual values
   - Conservative framing ("may help" not "will fix")

3. **Trend Context**
   - Compare current to historical values
   - Show improving/worsening/stable trends
   - Highlight "new abnormal" vs "chronic abnormal"

4. **Panel Interpretation**
   - Group related biomarkers (lipid, thyroid, CBC)
   - Analyze biomarker relationships (ratios, correlations)
   - Generate holistic panel summaries

#### Safety Guardrails

- Never diagnose conditions
- Never recommend medications or dosages
- Always require citations
- Include disclaimers on all outputs
- Flag critical values for physician review

#### Resource Requirements

- **Model:** Hardware-adaptive tiered system auto-selects provider and model based on available hardware. The current write APIs accept Low (Qwen2.5-0.5B), Mid (Phi-3-mini), and High (BioMistral-7B). Gemma 4 variants are registered/read-visible alternates in model config, but current set/download schemas do not accept them as selectable tiers. See `modules/model_selector.py` + `modules/hardware_detection.py`.
- **Providers:** `llama_cpp_provider` (default, embeds llama.cpp with auto-detected GGUF chat template) or `ollama_provider` (localhost optional).
- **Storage:** ~500MB-1GB for medical knowledge base; auto-seeded at startup if empty.
- **Compute:** GPU recommended for Tier 1; CPU fallback available for lower tiers.

### 5.2 Adaptive Medication Adherence Coach

#### Core Capabilities

1. **Medication Management**
   - Add medications with name, dosage, frequency
   - Create flexible schedules (morning, evening, custom)
   - Track active/inactive medications

2. **Adaptive Scheduling**
   - Learn user's actual dose-taking times
   - Calculate adaptive time windows (e.g., 7:15am-9:30am)
   - Detect weekday vs weekend patterns
   - Identify frequently missed days

3. **Smart Reminders**
   - Priority levels: initial, gentle nudge, important alert
   - Message tones: supportive, friendly, concerned
   - Randomized encouraging messages
   - Streak celebrations

4. **Adherence Tracking**
   - Log doses (manual, notification tap, voice)
   - Track variance from scheduled time
   - Record skip reasons
   - Calculate adherence statistics

5. **Pattern Recognition**
   - Time window patterns (average, std dev)
   - Weekday vs weekend differences
   - Missed dose patterns (e.g., always forgets Tuesdays)
   - Streak tracking

6. **Lab Correlation (Integration)**
   - Link adherence to lab result changes
   - Show messages like "Your HbA1c improved since consistent adherence"
   - Surface relevant medication context for lab interpretation

#### Safety Guardrails

- Never suggest medications
- Never recommend dosage changes
- Never diagnose conditions
- Clear disclaimers: reminder tool only
- No emergency medical advice

#### Resource Requirements

- **Model:** Optional LLM for message personalization (uses existing small model)
- **Compute:** CPU-only viable, no GPU required
- **Storage:** Minimal (schedules, adherence events)

---

## 6. Data Model Extensions

### Lab Interpreter Tables

| Table | Purpose |
|-------|---------|
| `lab_interpretations` | Per-observation interpretation with citations |
| `panel_interpretations` | Holistic panel interpretations |
| `biomarker_knowledge` | Medical knowledge base (reference info) |
| `intervention_mappings` | Evidence-based lifestyle interventions |
| `biomarker_relationships` | Relationships between biomarkers |

### Medication Coach Tables

| Table | Purpose |
|-------|---------|
| `medications` | User's medication list |
| `medication_schedules` | Dose schedules per medication |
| `doses_taken` | Record of doses taken/skipped |
| `adherence_patterns` | Learned behavioral patterns |
| `reminder_logs` | History of reminders sent |

---

## 7. API Endpoints

### Lab Interpreter API

```
POST   /api/v1/interpretations/observations/{id}/interpret-grounded   Generate interpretation
GET    /api/v1/interpretations/observations/{id}/interpretation       Get existing interpretation
POST   /api/v1/interpretations/panels/{name}/interpret                Generate panel interpretation
GET    /api/v1/interpretations/recent                                 List recent interpretations
GET    /api/v1/interpretations/knowledge/biomarker/{analyte}          Get knowledge base entry
POST   /api/v1/interpretations/batch                                  Batch generate interpretations
```

### Medication Coach API

```
POST   /api/v1/medications                         Create medication
GET    /api/v1/medications                         List medications
GET    /api/v1/medications/{id}                    Get medication details
POST   /api/v1/medications/{id}/schedules          Create schedule
GET    /api/v1/medications/{id}/schedules          List schedules
POST   /api/v1/medications/{id}/doses              Log dose
GET    /api/v1/medications/{id}/doses              List doses
GET    /api/v1/medications/{id}/stats              Get adherence stats
POST   /api/v1/medications/{id}/learn-patterns     Trigger pattern learning
GET    /api/v1/medications/{id}/correlations       Get lab correlations
```

---

## 8. UI/UX Requirements

### Lab Interpreter UI

1. **InterpretedResultCard** - Displays lab result with interpretation
2. **InterpretedTrendChart** - Trend visualization with annotations
3. **PanelInterpretationDashboard** - Panel overview with relationships
4. **ReferenceRangeComparison** - Visual comparison to reference range
5. **CitationTooltip** - Accessible citation display
6. **DisclaimerBanner** - Persistent safety disclaimers

### Medication Coach UI

1. **Medication List View** - Cards with next dose and quick log
2. **Add Medication Flow** - Step-by-step medication entry
3. **Dose Logging Modal** - Quick logging with options
4. **Adherence Dashboard** - Calendar heatmap, streaks, charts
5. **Notification Settings** - Preferences, quiet hours, urgency

### Accessibility Requirements (WCAG 2.2 AA)

- All components keyboard accessible
- Screen reader compatible
- Color not sole indicator (icons + patterns)
- Respect `prefers-reduced-motion`
- Text remains usable at 200% zoom

---

## 9. Implementation Phases

### Phase 0: Foundation (Week 1-2)
- Database models and migrations
- Knowledge base seed data (20-30 biomarkers)
- Medical knowledge corpus curation
- BioMistral model integration

### Phase 1: Core Interpretation (Week 3-4)
- Interpretation pipeline
- Safety guardrails
- Recommendation engine
- API endpoints

### Phase 2: Medication Management (Week 5-6)
- Medication CRUD
- Schedule management
- Dose logging
- Pattern learning algorithms

### Phase 3: Smart Notifications (Week 7-8)
- Notification scheduler
- Platform-specific providers
- Message generator
- Reminder priority system

### Phase 4: Frontend Integration (Week 9-10)
- Interpreter UI components
- Medication coach UI
- Dashboard integration
- Adherence visualization

### Phase 5: Polish & Testing (Week 11-12)
- Adversarial safety testing
- User testing
- Accessibility audit
- Performance optimization

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Medical accuracy | High | Citation requirements, curated knowledge base, conservative refusal |
| User over-reliance | High | Prominent disclaimers, "consult your doctor" framing |
| Model hallucinations | High | Safety validator, template fallbacks |
| Notification fatigue | Medium | Adaptive scheduling, user-controlled preferences |
| Pattern learning inaccuracy | Medium | Minimum sample requirements, confidence thresholds |
| Battery drain (mobile) | Medium | OS scheduling APIs, batch notifications |

---

## 11. Success Metrics

### Lab Interpreter
- Interpretation generation success rate > 95%
- Citation coverage = 100%
- Safety violation rate = 0%
- User satisfaction score > 4.0/5.0

### Medication Coach
- Dose logging completion rate > 80%
- Notification interaction rate > 50%
- Pattern learning accuracy > 70%
- 7-day adherence improvement > 10%

---

## 12. Resolved Decisions

### PM Decisions (January 2025)

| Decision | Resolution |
|----------|------------|
| **Model Selection** | Hardware-adaptive tiered system: BioMistral (GPU) → Phi-3 + RAG (mid) → Qwen 0.5B (low) → Templates (minimal) |
| **Knowledge Base** | Free/open source stack: LOINC + Awesome Biomarkers + Open Medical KB + PubMed + Custom curation |
| **Notifications** | Opt-in only, disabled by default, user explicitly enables |
| **Mobile Scope** | Desktop MVP with mobile-ready architecture; Android APK in v0.3+ |
| **Platform** | Windows desktop first (Tauri), scalable to mobile |

### Remaining Open Questions

1. **Export Format:** PDF, JSON, or both for interpretations?
2. **Gamification Level:** Basic streaks vs full badges/achievements system?
3. **Lab Correlation UI:** How prominently to feature medication-lab correlations?
4. **Voice Logging:** Include in v0.2 or defer to v0.3?

---

## 13. References

- Existing PRD: `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md`
- Lab Interpreter Architecture: `docs/features/01_lab_result_interpreter_architecture.md`
- Medication Coach Architecture: `docs/features/02_medication_adherence_coach_architecture.md`
- Backend Architecture: `docs/01_backend_architecture_plan.md`
- Frontend Accessibility: `docs/02_frontend_accessibility_plan.md`
