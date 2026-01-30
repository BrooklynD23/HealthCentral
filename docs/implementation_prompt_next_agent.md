# Implementation Prompt for Next Agent

## Mission
Continue implementing HealthCentral's v0.2 features based on current documentation and task status. Focus on completing Phase 0.3 (BioMistral Model Integration), Phase 3 (Smart Notifications), or Phase 4 (Frontend Integration).

## Current Project State
- **Phase 0.1-0.2**: ✅ COMPLETE (Database models, seed data)
- **Phase 0.3**: ⏳ PENDING (BioMistral Model Integration)
- **Phase 1**: ✅ COMPLETE (Core Lab Interpretation Engine - Backend)
- **Phase 2**: ✅ COMPLETE (Core Medication Management - Backend)
- **Phase 3**: ⏳ PENDING (Smart Notifications)
- **Phase 4**: ⏳ PENDING (Frontend Integration)
- **Phase 5**: ⏳ NOT STARTED (Polish & Testing)

## What Was Completed (2026-01-29)

### Phase 1: Lab Interpretation Engine ✅
- ✅ `modules/interpret.py` - InterpretModule orchestrator with template-based generation
- ✅ `modules/interpret_safety.py` - Safety guardrails (prohibited patterns, disclaimers, critical values)
- ✅ `modules/recommend.py` - Evidence-based recommendation engine with citations
- ✅ `modules/knowledge_loader.py` - Knowledge base access with caching
- ✅ `api/interpretations.py` - All API endpoints implemented:
  - POST /interpretations/observations/{id}/interpret
  - GET /interpretations/observations/{id}/interpretation
  - POST /interpretations/panels/{name}/interpret
  - GET /interpretations/recent
  - GET /interpretations/knowledge/biomarker/{analyte}
  - POST /interpretations/batch

### Phase 2: Medication Management ✅
- ✅ `api/medications.py` - Full CRUD with schedules, doses, stats
- ✅ `modules/adherence_patterns.py` - Pattern learning engine:
  - Time window learning (mean ± 1.5 std dev)
  - Weekday vs weekend detection
  - Missed day pattern detection
  - Streak calculation
  - Adaptive window updates

## Required Reading (Priority Order)

### 1. Current Implementation Status
- `docs/features/TASK_LIST.md` - **CRITICAL** - Active task tracker with detailed phase breakdown
- `docs/05_backend_integration_status.md` - Backend API implementation status

### 2. Feature Architecture & Requirements
- `docs/features/01_lab_result_interpreter_architecture.md` - Lab interpreter technical specs
- `docs/features/02_medication_adherence_coach_architecture.md` - Medication coach technical specs
- `docs/features/03_features_prd.md` - Combined PRD for both features

### 3. Core Project Documentation
- `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md` - Original MVP requirements
- `docs/01_backend_architecture_plan.md` - Backend architecture patterns
- `docs/03_data_confidentiality_pipeline_plan.md` - Security requirements

## Implementation Priority

### Option A: BioMistral Model Integration (Phase 0.3)
**Start here to enhance interpretation quality with LLM**

1. **Model Setup**
   - Add BioMistral-7B GGUF download/setup script (~4GB)
   - Create hardware detection for tiered model selection
   - Integrate with existing llama.cpp module in `modules/llama_inference.py`

2. **Tiered Fallback System**
   - Tier 1 (High): GPU 8GB+ → BioMistral-7B
   - Tier 2 (Mid): GPU 4-6GB or 16GB RAM → Phi-3 Mini + RAG
   - Tier 3 (Low): CPU-only, 8GB RAM → Qwen2.5 0.5B + RAG
   - Tier 4 (Minimal): Template-based only (already implemented)

3. **Update InterpretModule**
   - Add LLM-based interpretation generation
   - Implement model selection based on hardware detection
   - Add fallback chain when model loading fails

### Option B: Smart Notifications (Phase 3)
**Start here if prioritizing medication reminder features**

1. **Notification Scheduler** (`modules/notification_scheduler.py`)
   - Background service with minute-by-minute checking
   - Priority calculation (initial → nudge → alert)
   - Integration with adaptive windows from pattern learning

2. **Message Generator** (`modules/message_generator.py`)
   - Template selection by priority and tone
   - Streak celebration messages (3, 7, 14, 30 days)
   - Optional LLM personalization

3. **Platform Notifications** (`modules/platform_notifications.py`)
   - Abstract notification interface
   - Windows ToastNotificationManager implementation
   - Fallback plyer notifications for cross-platform

### Option C: Frontend Integration (Phase 4)
**Start here if backend is sufficient and UI is needed**

1. **Lab Interpreter UI** (`src/frontend/src/components/features/interpreter/`)
   - InterpretedResultCard.tsx
   - InterpretedTrendChart.tsx (Recharts with annotations)
   - PanelInterpretationDashboard.tsx
   - ReferenceRangeComparison.tsx
   - CitationTooltip.tsx, DisclaimerBanner.tsx, AdviceSection.tsx
   - Create `pages/LabInterpreter.tsx`
   - Create `services/interpretationService.ts` and `hooks/useInterpretation.ts`

2. **Medication Coach UI** (`src/frontend/src/components/features/adherence/`)
   - MedicationCard.tsx
   - DoseLoggingModal.tsx
   - AdherenceDashboard.tsx (calendar heatmap)
   - StreakDisplay.tsx
   - NotificationSettings.tsx
   - Create `pages/MedicationCoach.tsx`
   - Create `services/medicationService.ts` and `hooks/useAdherence.ts`

3. **Navigation Integration**
   - Add Lab Interpreter to main navigation
   - Add Medication Coach to main navigation
   - Link lab results to interpretations
   - Link medication adherence to lab trends

## Technical Constraints & Requirements

### Security & Privacy
- All data must remain local-first
- Continue using existing profile-based encryption
- Implement audit logging for all feature operations
- Follow existing safety guardrails patterns

### Integration Requirements
- Extend existing FastAPI backend structure
- Use existing SQLAlchemy models (already created)
- Integrate with existing llama.cpp module for local inference
- Follow existing API patterns and error handling

### Existing Backend Patterns
- API routers: See `api/observations.py`, `api/medications.py` for patterns
- Modules: See `modules/interpret.py`, `modules/adherence_patterns.py` for patterns
- Auth: Use `RequireAuth` and `ProfileDbSession` for protected endpoints
- Audit: Use `log_document_event()` for audit logging

## Task Management Requirements

### Update Task Tracking
You MUST maintain and update the task tracking file:
- **File**: `docs/features/TASK_LIST.md`
- **Format**: Keep existing table structure
- **Updates**: Mark tasks as [x] DONE when completed, update notes with dates
- **New Tasks**: Add any discovered tasks to appropriate phases

### Session Notes
Add session notes at the bottom of `TASK_LIST.md`:
```markdown
### YYYY-MM-DD - Your Session Focus
- What you implemented
- Any issues encountered
- Next session recommendations
```

## Quality Gates

Before marking any phase complete, ensure:
- [ ] All unit tests passing
- [ ] No security warnings from safety review
- [ ] No regressions in existing functionality
- [ ] Code formatted (black, ruff)
- [ ] Type hints complete (mypy)
- [ ] Documentation updated

## Cross-Feature Integration Planning

While implementing, consider these integration points:
- Lab results should show "Related Medications"
- Medication details should show "Lab Correlations"
- Shared medical knowledge base between features
- Unified safety disclaimers and messaging

## Decision Points

Document any decisions in the task list:
- Export format preferences (PDF, JSON, both)
- Gamification level (basic streaks vs full badges)
- Lab correlation prominence (subtle vs dashboard section)
- Voice logging timing (v0.2 or v0.3)

## Next Steps

1. **Choose your focus**:
   - Phase 0.3 (BioMistral) for better interpretation quality
   - Phase 3 (Notifications) for medication reminder functionality
   - Phase 4 (Frontend) for user-facing UI
2. **Read the relevant architecture documents** listed above
3. **Review current task status** in `TASK_LIST.md`
4. **Begin implementation** following the phase breakdown
5. **Update task tracking** as you complete items
6. **Add session notes** documenting your progress

## Files to Reference for Patterns

- Existing API structure: `src/backend/api/` (especially `interpretations.py`, `medications.py`)
- Existing modules: `src/backend/modules/` (especially `interpret.py`, `adherence_patterns.py`)
- Existing models: `src/backend/models/`
- Database patterns: `src/backend/core/`
- Frontend structure: `src/frontend/src/`

**DO NOT skip reading the current task status and architecture docs before starting implementation.**
