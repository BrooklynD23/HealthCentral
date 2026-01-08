# HealthCentral New Features Index

This folder contains architecture plans and PRDs for new features added to HealthCentral.

## Feature Documents

| Document | Feature | Resource Level | Status |
|----------|---------|----------------|--------|
| `01_lab_result_interpreter_architecture.md` | Personal Lab Result Interpreter | Moderate (GPU) | Planning |
| `02_medication_adherence_coach_architecture.md` | Adaptive Medication Adherence Coach | Light (CPU) | Planning |
| `03_features_prd.md` | Combined PRD for both features | N/A | Planning |
| `TASK_LIST.md` | **Implementation Task Tracker** | N/A | **Active** |

## Feature Overview

### Personal Lab Result Interpreter (Moderate)
Transforms raw lab results into actionable health insights with:
- Easy-to-understand explanations of biomarkers
- Personalized health advice based on specific values and trends
- Contextualized information beyond what patient portals provide
- Medical knowledge base with citations

**Resource Requirements:** Single-GPU model for medical NLP + data visualization

### Adaptive Medication Adherence Coach (Light)
Intelligent medication reminder system that adapts to real-world behavior:
- Learns when user ACTUALLY takes medications (not rigid schedules)
- Sends supportive nudges and tips
- Adapts timing tolerance (7am vs 9:37am is fine)
- Pattern recognition for optimal reminder timing

**Resource Requirements:** CPU-only, basic scheduling logic, small on-device models

## Integration Points

Both features integrate with the existing HealthCentral architecture:
- Extend existing profile-based encryption
- Reuse RAG assistant and embedding infrastructure
- Leverage existing local LLM (llama.cpp)
- Share audit logging and safety guardrails

### Cross-Feature Synergy
- Lab Result Interpreter can reference medication adherence patterns
- Medication Coach can correlate adherence with lab result trends
- Shared medical knowledge base for citations
