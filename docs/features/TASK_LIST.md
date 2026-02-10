# HealthCentral Feature Implementation Task List

**Version:** 0.2.0 | **Last Updated:** 2026-01-29 | **Branch:** Security-Revamp-2

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

### Phase Status Snapshot (2026-02-09)
- [x] Phase 0: Foundation
- [x] Phase 1: Core Lab Interpretation Engine
- [x] Phase 2: Core Medication Management
- [x] Phase 3: Smart Notifications
- [ ] Phase 4: Frontend Integration hardening
- [ ] Phase 5: Polish & Testing

---

## Phase 0: Foundation (Backend Infrastructure) [x] DONE

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
| Create UserModelSettings model | [x] DONE | 2026-01-30 Per-profile DB storage |
| Create docs/model_tiers/ documentation | [x] DONE | 2026-01-30 README + tier docs |
| Create modules/hardware_detection.py | [x] DONE | 2026-01-30 RAM/CPU-based tier detection |
| Create modules/model_selector.py | [x] DONE | 2026-01-30 With async wrapper |
| Create scripts/detect_hardware.py CLI | [x] DONE | 2026-01-30 Hardware info display |
| Create scripts/model_manager.py CLI | [x] DONE | 2026-01-30 HF Hub integration |
| Update modules/interpret.py for tiered inference | [x] DONE | 2026-01-30 Citation validation, LLM methods |
| Create api/model_settings.py endpoints | [x] DONE | 2026-01-30 6 endpoints |
| Update requirements.txt | [x] DONE | 2026-01-30 +huggingface-hub, psutil, py-cpuinfo |
| Update config.py with model tier settings | [x] DONE | 2026-01-30 default_model_tier, auto_detect |
| Update module/model exports | [x] DONE | 2026-01-30 __init__.py files |

---

## Phase 1: Core Lab Interpretation Engine [x] DONE

### 1.1 Interpretation Pipeline
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/interpret.py` (InterpretModule) | [x] DONE | 2026-01-29 Main orchestrator with template-based generation |
| Create `modules/interpret_safety.py` (safety guardrails) | [x] DONE | 2026-01-29 Prohibited patterns, required disclaimers |
| Create `modules/recommend.py` (recommendation engine) | [x] DONE | 2026-01-29 Evidence-based advice with citations |
| Create `modules/knowledge_loader.py` | [x] DONE | 2026-01-29 Query knowledge base with caching |

### 1.2 Safety Guardrails
| Task | Status | Notes |
|------|--------|-------|
| Implement PROHIBITED_PATTERNS regex checking | [x] DONE | 2026-01-29 No diagnoses, no dosing, no emergency advice |
| Implement REQUIRED_DISCLAIMERS validation | [x] DONE | 2026-01-29 Must cite, must disclaim |
| Add critical value flagging | [x] DONE | 2026-01-29 Auto-flag for physician review |
| Test adversarial inputs | [ ] TODO | Security testing |

### 1.3 API Endpoints
| Task | Status | Notes |
|------|--------|-------|
| Create `api/interpretations.py` router | [x] DONE | 2026-01-29 Full CRUD + batch |
| POST /observations/{id}/interpret | [x] DONE | 2026-01-29 Generate interpretation |
| GET /observations/{id}/interpretation | [x] DONE | 2026-01-29 Get existing |
| POST /panels/{name}/interpret | [x] DONE | 2026-01-29 Panel interpretation |
| GET /interpretations/recent | [x] DONE | 2026-01-29 List recent |
| GET /knowledge/biomarker/{analyte} | [x] DONE | 2026-01-29 Knowledge lookup |
| POST /interpretations/batch | [x] DONE | 2026-01-29 Batch generation |
| Create `api/schemas/interpretation.py` | [x] DONE | 2026-01-29 Pydantic schemas (in interpretations.py) |

---

## Phase 2: Core Medication Management [x] DONE

### 2.1 Medication CRUD
| Task | Status | Notes |
|------|--------|-------|
| Create `api/medications.py` router | [x] DONE | 2026-01-29 Full CRUD with schedules, doses, stats |
| POST /medications | [x] DONE | 2026-01-29 Create medication |
| GET /medications | [x] DONE | 2026-01-29 List medications (active_only filter) |
| GET /medications/{id} | [x] DONE | 2026-01-29 Get medication with schedules |
| PATCH /medications/{id} | [x] DONE | 2026-01-29 Update medication |
| DELETE /medications/{id} | [x] DONE | 2026-01-29 Soft delete (hard_delete option) |

### 2.2 Schedule Management
| Task | Status | Notes |
|------|--------|-------|
| POST /medications/{id}/schedules | [x] DONE | 2026-01-29 Create schedule |
| GET /medications/{id}/schedules | [x] DONE | 2026-01-29 List schedules |
| PATCH /medications/{id}/schedules/{sid} | [x] DONE | 2026-01-29 Update |
| DELETE /medications/{id}/schedules/{sid} | [x] DONE | 2026-01-29 Remove |

### 2.3 Dose Logging
| Task | Status | Notes |
|------|--------|-------|
| POST /medications/{id}/doses | [x] DONE | 2026-01-29 Log dose (taken or skipped) |
| GET /medications/{id}/doses | [x] DONE | 2026-01-29 List doses with date filters |
| GET /medications/{id}/stats | [x] DONE | 2026-01-29 Adherence stats, streaks |

### 2.4 Pattern Learning
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/adherence_patterns.py` | [x] DONE | 2026-01-29 PatternLearner class |
| Implement time window learning algorithm | [x] DONE | 2026-01-29 Mean ± 1.5 std dev with outlier removal |
| Implement weekday vs weekend detection | [x] DONE | 2026-01-29 Detects significant differences |
| Implement missed day pattern detection | [x] DONE | 2026-01-29 Identifies problem days |
| POST /medications/{id}/learn-patterns | [x] DONE | 2026-01-29 Trigger learning, updates adaptive windows |

---

## Phase 3: Smart Notifications [x] DONE

### 3.1 Notification Scheduler
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/notification_scheduler.py` | [x] DONE | 2026-01-29 Background scheduler with profile registration |
| Implement minute-by-minute checking loop | [x] DONE | 2026-01-29 Async loop with configurable interval |
| Implement priority calculation | [x] DONE | 2026-01-29 INITIAL → GENTLE_NUDGE → IMPORTANT_ALERT |
| Integrate with schedule adaptive windows | [x] DONE | 2026-01-29 Uses learned windows from pattern learning |

### 3.2 Message Generator
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/message_generator.py` | [x] DONE | 2026-01-29 Template-based message generation |
| Implement template selection | [x] DONE | 2026-01-29 By priority + tone + time of day |
| Add streak celebration messages | [x] DONE | 2026-01-29 3, 7, 14, 30, 60, 90, 365 day milestones |
| Optional: LLM personalization | [ ] TODO | Defer to v0.3 |

### 3.3 Platform Notifications
| Task | Status | Notes |
|------|--------|-------|
| Create `modules/platform_notifications.py` | [x] DONE | 2026-01-29 Abstract provider interface |
| Implement Windows ToastNotificationManager | [x] DONE | 2026-01-29 With winsdk integration |
| Add fallback plyer notifications | [x] DONE | 2026-01-29 Cross-platform fallback |
| Test notification delivery | [x] DONE | 2026-01-29 MockProvider for testing |

### 3.4 Notification API Endpoints
| Task | Status | Notes |
|------|--------|-------|
| Create `api/notifications.py` router | [x] DONE | 2026-01-29 Full notification management |
| GET/PATCH /settings/{medication_id} | [x] DONE | 2026-01-29 Per-medication notification settings |
| GET /history | [x] DONE | 2026-01-29 Notification history with stats |
| POST /test | [x] DONE | 2026-01-29 Send test notification |
| POST /test/{medication_id} | [x] DONE | 2026-01-29 Test with real medication context |
| GET /scheduler/status | [x] DONE | 2026-01-29 Scheduler status monitoring |
| POST /{reminder_id}/interaction | [x] DONE | 2026-01-29 Record user interactions |

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

### 2026-01-29 - Phase 1 & Phase 2 Backend Complete
- **Phase 1.1**: Created interpretation pipeline modules:
  - `modules/interpret.py` - Main InterpretModule orchestrator with template-based generation
  - `modules/interpret_safety.py` - Safety guardrails (prohibited patterns, disclaimers, critical values)
  - `modules/recommend.py` - Evidence-based recommendation engine with citations
  - `modules/knowledge_loader.py` - Knowledge base access with caching
- **Phase 1.2**: Implemented safety guardrails:
  - Prohibited patterns: diagnostic language, dosing, medication advice, emergency advice
  - Required disclaimers validation
  - Critical value flagging with auto-physician-review
- **Phase 1.3**: Created `api/interpretations.py` with all endpoints:
  - POST/GET observation interpretations
  - Panel interpretations with relationship insights
  - Batch processing, knowledge lookup
- **Phase 2.1-2.4**: Created `api/medications.py` with full CRUD:
  - Medications, schedules, dose logging, adherence stats
  - `modules/adherence_patterns.py` - Pattern learning (time window, weekday/weekend, missed days)
- Updated `modules/__init__.py` and `api/__init__.py` to export new modules
- All files pass Python syntax validation

### 2026-01-29 - Phase 3 Smart Notifications Complete
- **Phase 3.1**: Created `modules/notification_scheduler.py`:
  - NotificationScheduler with start/stop/pause/resume lifecycle
  - Profile session registration for multi-profile support
  - Minute-by-minute checking loop with configurable interval
  - Priority escalation: INITIAL → GENTLE_NUDGE → IMPORTANT_ALERT
  - Integration with adaptive windows from pattern learning
  - Rate limiting (max notifications per hour)
- **Phase 3.2**: Created `modules/message_generator.py`:
  - Template-based message generation by priority and time of day
  - Streak celebration messages at milestones (3, 7, 14, 30, 60, 90, 365 days)
  - Missed recovery messages with encouraging tone
  - Quiet hours summary messages
- **Phase 3.3**: Created `modules/platform_notifications.py`:
  - Abstract NotificationProvider interface
  - WindowsToastProvider with winsdk integration
  - PlyerProvider for cross-platform fallback
  - MockProvider for testing
  - NotificationService with provider fallback chain
- **Phase 3.4**: Created `api/notifications.py`:
  - GET/PATCH notification settings per medication
  - GET notification history with statistics
  - POST test notifications (generic and medication-specific)
  - GET scheduler status monitoring
  - POST reminder interaction recording
- Updated `api/__init__.py` and `modules/__init__.py` with exports
- Updated `requirements.txt` with apscheduler, plyer dependencies
- Created comprehensive tests in `tests/test_phase3_notifications.py`
- All files pass Python syntax validation

### 2026-01-30 - Phase 0.3 Tiered Hardware Model System Complete
- **Foundation**: Created UserModelSettings model in per-profile database
- **Hardware Detection**: Created `modules/hardware_detection.py`:
  - HardwareProfile dataclass with RAM/CPU/disk/GPU detection
  - Tier requirements: low (8GB), mid (16GB), high (32GB) RAM
  - Can run tier validation and recommendations
- **Model Selection**: Created `modules/model_selector.py`:
  - TIER_MODEL_CONFIG for Qwen2.5-0.5B, Phi-3-mini, BioMistral-7B
  - Async-safe inference with asyncio.to_thread()
  - Fallback chain: high → mid → low → template
  - User preference persistence in database
- **CLI Tools**: Created CLI scripts in scripts/:
  - `detect_hardware.py` - Show hardware info and tier recommendation
  - `model_manager.py` - detect, list, download, switch, cleanup commands
- **Interpretation Integration**: Updated `modules/interpret.py`:
  - Added model_selector to InterpretModule
  - Added _llm_interpretation() with citation-enforcing prompt
  - Added _validate_llm_citations() for [KB:*], [INT:*] patterns
  - Added interpret_with_model() as preferred entry point
- **API Endpoints**: Created `api/model_settings.py`:
  - GET /settings/model - Current settings + hardware info
  - POST /settings/model/detect - Run hardware detection
  - POST /settings/model/tier - Set preferred tier
  - GET /settings/model/tiers - List all tiers with status
  - GET /settings/model/download-progress - Check download status
  - POST /settings/model/download - Start model download
- **Documentation**: Created docs/model_tiers/:
  - README.md - Overview of tier system
  - tier1_low.md - Qwen2.5 0.5B details
  - tier2_mid.md - Phi-3-mini details
  - tier3_high.md - BioMistral-7B details
- **Dependencies**: Added huggingface-hub, psutil, py-cpuinfo to requirements.txt
- **Config**: Added default_model_tier, auto_detect_hardware, model_download_timeout

### Next Session Pickup
1. Phase 4: Frontend Integration (React components for Lab Interpreter and Medication Coach)
2. Phase 5: Polish & Testing (adversarial testing, accessibility audit, performance)
3. Run full test suite with `pip install -r requirements.txt` first
4. Consider integrating scheduler startup with FastAPI lifespan events
5. Test hardware detection and model downloading on actual hardware

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
