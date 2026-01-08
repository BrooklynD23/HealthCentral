# HealthCentral Feature Implementation Task List

**Version:** 0.2.0 | **Last Updated:** 2026-01-07 | **Branch:** Security-Revamp-2

---

## Quick Start for Session Pickup

```bash
# Load this context at session start:
# 1. Read this file: docs/features/TASK_LIST.md
# 2. Activate Serena: mcp__serena__activate_project("HealthCentral")
# 3. Read memory: mcp__serena__read_memory("feature_implementation_progress")
# 4. Check current phase status below
```

---

## Overview

This task list tracks implementation of two new features:
1. **Personal Lab Result Interpreter** (Moderate - GPU recommended)
2. **Adaptive Medication Adherence Coach** (Light - CPU only)

### Implementation Order
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

---

## Phase 0: Foundation (Backend Infrastructure)

### 0.1 Database Models & Migrations
| Task | Status | Notes |
|------|--------|-------|
| Create `models/knowledge_base.py` (BiomarkerKnowledge, InterventionMapping, BiomarkerRelationship) | [x] DONE | 2026-01-07 |
| Create `models/interpretation.py` (LabInterpretation, PanelInterpretation) | [x] DONE | 2026-01-07 |
| Create `models/medication.py` (Medication, MedicationSchedule, DoseTaken, AdherencePattern, ReminderLog) | [x] DONE | 2026-01-07 |
| Update `models/__init__.py` with all exports | [x] DONE | 2026-01-07 |
| Update database initialization (core/database.py, core/profile_database.py) | [x] DONE | 2026-01-07 |
| Fix circular imports in core/auth.py and core/audit.py | [x] DONE | 2026-01-07 |
| Test migrations with fresh database | [x] DONE | Tables created successfully |

### 0.2 Knowledge Base Seed Data
| Task | Status | Notes |
|------|--------|-------|
| Create `scripts/seed_knowledge_base.py` | [x] DONE | 2026-01-07 |
| Seed priority biomarkers (12 biomarkers: lipid, diabetes, CBC, thyroid, kidney, vitamin) | [x] DONE | Lipid panel, HbA1c, glucose, hemoglobin, WBC, platelets, TSH, creatinine, Vitamin D |
| Add intervention mappings (9 lifestyle recommendations) | [x] DONE | Diet, exercise, lifestyle, supplement interventions |
| Add biomarker relationships (7 relationships: ratios, correlations, panels) | [x] DONE | TC/HDL ratio, LDL/HDL ratio, TSH-T4 inverse, panel memberships |

### 0.3 BioMistral Model Integration (Lab Interpreter)
| Task | Status | Notes |
|------|--------|-------|
| Add BioMistral-7B GGUF download/setup script | [ ] TODO | ~4GB download |
| Create hardware detection for tiered model selection | [ ] TODO | GPU → Phi-3 → Qwen → Templates |
| Integrate with existing llama.cpp module | [ ] TODO | |
| Test inference pipeline | [ ] TODO | |

---

## Phase 1: Core Lab Interpretation Engine

### 1.1 Interpretation Pipeline
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/interpret.py` (InterpretModule) | [ ] TODO | Main orchestrator |
| Create `modules/interpret_safety.py` (safety guardrails) | [ ] TODO | Prohibited patterns, required disclaimers |
| Create `modules/recommend.py` (recommendation engine) | [ ] TODO | Evidence-based advice |
| Create `modules/knowledge_loader.py` | [ ] TODO | Query knowledge base |

### 1.2 Safety Guardrails
| Task | Status | Notes |
|------|--------|-------|
| Implement PROHIBITED_PATTERNS regex checking | [ ] TODO | No diagnoses, no dosing |
| Implement REQUIRED_DISCLAIMERS validation | [ ] TODO | Must cite, must disclaim |
| Add critical value flagging | [ ] TODO | Auto-flag for physician review |
| Test adversarial inputs | [ ] TODO | Security testing |

### 1.3 API Endpoints
| Task | Status | Notes |
|------|--------|-------|
| Create `api/interpretations.py` router | [ ] TODO | |
| POST /observations/{id}/interpret | [ ] TODO | Generate interpretation |
| GET /observations/{id}/interpretation | [ ] TODO | Get existing |
| POST /panels/{name}/interpret | [ ] TODO | Panel interpretation |
| GET /interpretations/recent | [ ] TODO | List recent |
| GET /knowledge/biomarker/{analyte} | [ ] TODO | Knowledge lookup |
| POST /interpretations/batch | [ ] TODO | Batch generation |
| Create `api/schemas/interpretation.py` | [ ] TODO | Pydantic schemas |

---

## Phase 2: Core Medication Management

### 2.1 Medication CRUD
| Task | Status | Notes |
|------|--------|-------|
| Create `api/medications.py` router | [ ] TODO | |
| POST /{profile}/medications | [ ] TODO | Create medication |
| GET /{profile}/medications | [ ] TODO | List medications |
| GET /{profile}/medications/{id} | [ ] TODO | Get medication |
| PATCH /{profile}/medications/{id} | [ ] TODO | Update medication |
| DELETE /{profile}/medications/{id} | [ ] TODO | Soft delete |

### 2.2 Schedule Management
| Task | Status | Notes |
|------|--------|-------|
| POST /{profile}/medications/{id}/schedules | [ ] TODO | Create schedule |
| GET /{profile}/medications/{id}/schedules | [ ] TODO | List schedules |
| PATCH /{profile}/medications/{id}/schedules/{sid} | [ ] TODO | Update |
| DELETE /{profile}/medications/{id}/schedules/{sid} | [ ] TODO | Remove |

### 2.3 Dose Logging
| Task | Status | Notes |
|------|--------|-------|
| POST /{profile}/medications/{id}/doses | [ ] TODO | Log dose |
| GET /{profile}/medications/{id}/doses | [ ] TODO | List doses |
| GET /{profile}/medications/{id}/stats | [ ] TODO | Adherence stats |

### 2.4 Pattern Learning
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/adherence_patterns.py` | [ ] TODO | PatternLearner class |
| Implement time window learning algorithm | [ ] TODO | Mean ± 1.5 std dev |
| Implement weekday vs weekend detection | [ ] TODO | |
| Implement missed day pattern detection | [ ] TODO | |
| POST /{profile}/medications/{id}/learn-patterns | [ ] TODO | Trigger learning |

---

## Phase 3: Smart Notifications

### 3.1 Notification Scheduler
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/notification_scheduler.py` | [ ] TODO | Background service |
| Implement minute-by-minute checking loop | [ ] TODO | |
| Implement priority calculation | [ ] TODO | initial → nudge → alert |
| Integrate with schedule adaptive windows | [ ] TODO | |

### 3.2 Message Generator
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/message_generator.py` | [ ] TODO | |
| Implement template selection | [ ] TODO | By priority + tone |
| Add streak celebration messages | [ ] TODO | 3, 7, 14, 30 day |
| Optional: LLM personalization | [ ] TODO | Use existing small model |

### 3.3 Platform Notifications
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/platform_notifications.py` | [ ] TODO | Abstract interface |
| Implement Windows ToastNotificationManager | [ ] TODO | Primary platform |
| Add fallback plyer notifications | [ ] TODO | Cross-platform |
| Test notification delivery | [ ] TODO | |

---

## Phase 4: Frontend Integration

### 4.1 Lab Interpreter UI
| Task | Status | Notes |
|------|--------|-------|
| Create `components/features/interpreter/` directory | [ ] TODO | |
| InterpretedResultCard.tsx | [ ] TODO | Show interpretation |
| InterpretedTrendChart.tsx | [ ] TODO | Recharts with annotations |
| PanelInterpretationDashboard.tsx | [ ] TODO | Panel overview |
| ReferenceRangeComparison.tsx | [ ] TODO | Visual bar |
| CitationTooltip.tsx | [ ] TODO | Expandable citations |
| DisclaimerBanner.tsx | [ ] TODO | Safety disclaimer |
| AdviceSection.tsx | [ ] TODO | Recommendations |
| Create `pages/LabInterpreter.tsx` | [ ] TODO | Main page |
| Create `services/interpretationService.ts` | [ ] TODO | API client |
| Create `hooks/useInterpretation.ts` | [ ] TODO | Data fetching |

### 4.2 Medication Coach UI
| Task | Status | Notes |
|------|--------|-------|
| Create `components/features/adherence/` directory | [ ] TODO | |
| MedicationCard.tsx | [ ] TODO | List item |
| DoseLoggingModal.tsx | [ ] TODO | Quick logging |
| AdherenceDashboard.tsx | [ ] TODO | Calendar heatmap |
| StreakDisplay.tsx | [ ] TODO | Streak visualization |
| NotificationSettings.tsx | [ ] TODO | Preferences |
| Create `pages/MedicationCoach.tsx` | [ ] TODO | Main page |
| Create `services/medicationService.ts` | [ ] TODO | API client |
| Create `hooks/useAdherence.ts` | [ ] TODO | Data fetching |

### 4.3 Integration & Navigation
| Task | Status | Notes |
|------|--------|-------|
| Add Lab Interpreter to main navigation | [ ] TODO | |
| Add Medication Coach to main navigation | [ ] TODO | |
| Link lab results to interpretations | [ ] TODO | Cross-feature |
| Link medication adherence to lab trends | [ ] TODO | Correlation UI |

---

## Phase 5: Polish & Testing

### 5.1 Safety Testing
| Task | Status | Notes |
|------|--------|-------|
| Adversarial prompt testing (Lab Interpreter) | [ ] TODO | Try to bypass guardrails |
| Verify all interpretations have citations | [ ] TODO | 100% coverage required |
| Verify all interpretations have disclaimers | [ ] TODO | |
| Test critical value flagging | [ ] TODO | |

### 5.2 Accessibility Audit (WCAG 2.2 AA)
| Task | Status | Notes |
|------|--------|-------|
| Keyboard navigation all components | [ ] TODO | |
| Screen reader compatibility | [ ] TODO | |
| Color contrast verification | [ ] TODO | |
| prefers-reduced-motion support | [ ] TODO | |
| 200% zoom usability | [ ] TODO | |

### 5.3 Performance Optimization
| Task | Status | Notes |
|------|--------|-------|
| Model loading time optimization | [ ] TODO | Lazy load |
| Interpretation caching | [ ] TODO | Don't regenerate |
| Notification battery optimization | [ ] TODO | Efficient scheduling |
| Frontend bundle size check | [ ] TODO | |

### 5.4 Documentation
| Task | Status | Notes |
|------|--------|-------|
| Update API documentation | [ ] TODO | |
| User guide for Lab Interpreter | [ ] TODO | |
| User guide for Medication Coach | [ ] TODO | |
| Update CLAUDE.md with new patterns | [ ] TODO | |

---

## Dependencies to Add

### Python (requirements.txt)
```txt
# Already have: FastAPI, SQLAlchemy, llama-cpp-python

# New for Medication Coach
plyer>=2.1.0          # Cross-platform notifications
winsdk>=1.0.0b10      # Windows notification center (optional)
apscheduler>=3.10.0   # Background task scheduling
```

### Frontend (package.json)
```json
{
  "dependencies": {
    // May need: recharts for charts (check if already present)
  }
}
```

---

## Open Decisions (Requires PM Input)

| Decision | Options | Current Thinking |
|----------|---------|------------------|
| Export format for interpretations | PDF, JSON, both | Both (JSON for dev, PDF for sharing) |
| Gamification level | Basic streaks vs full badges | Start with basic streaks |
| Lab correlation prominence | Subtle hint vs dashboard section | Dashboard section |
| Voice logging | v0.2 or v0.3 | Defer to v0.3 |

---

## Session Notes

### 2026-01-07 - Initial Setup
- Created this task list from PRD and architecture documents
- Project state: Security Revamp phases 1-4 complete
- Ready to begin Phase 0: Foundation

### 2026-01-07 - Phase 0 Complete
- Created all database models (knowledge_base.py, interpretation.py, medication.py)
- Fixed circular imports in core/auth.py and core/audit.py (deferred imports)
- Created seed script with 12 biomarkers, 9 interventions, 7 relationships
- Tested database initialization - all tables created successfully
- Models exported in `__init__.py`, database init files updated

### Next Session Pickup
1. Start with Phase 0.3: BioMistral Model Integration OR
2. Start with Phase 1.1: Interpretation Pipeline
3. Consider adding more biomarkers to seed data as needed

---

## Cross-Feature Integration Points

```
Lab Interpreter ←→ Medication Coach

1. Lab results page shows "Related Medications"
   - If user takes Metformin, show near HbA1c results

2. Medication detail shows "Lab Correlations"
   - "Your HbA1c improved since consistent adherence"

3. Shared medical knowledge base
   - Biomarker knowledge used by both features

4. Unified safety disclaimers
   - Consistent "consult your doctor" messaging
```

---

## Quality Gates

Before marking any phase complete:
- [ ] All unit tests passing
- [ ] No security warnings from safety review
- [ ] No regressions in existing functionality
- [ ] Code formatted (black, ruff)
- [ ] Type hints complete (mypy)
- [ ] Documentation updated
