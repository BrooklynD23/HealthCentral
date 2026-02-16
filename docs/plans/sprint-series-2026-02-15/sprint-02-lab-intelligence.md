# Sprint 02 - Lab Intelligence Advanced Features

**Sprint ID:** HC-S02-LAB
**Priority:** High
**Source Area:** Personal Lab Result Interpreter - Advanced Features

## Architecture Scope

- Core interpretation logic lives in `src/backend/modules/interpret.py`.
- Trend context logic lives in `src/backend/modules/analytics.py`.
- Recommendation refinement lives in `src/backend/modules/recommend.py` and `src/backend/modules/intervention_mappings.py`.
- UI delivery requires new interpretation-focused components under `src/frontend/src/components/`.

## Work Packages

### LAB-001 Severity Classification System

- Backend files:
  - `src/backend/modules/interpret.py`
- Frontend files:
  - `src/frontend/src/components/InterpretedResultCard.tsx` (new)
- Required behavior:
  - Classify results as `normal`, `borderline`, `abnormal`, `critical`.
  - Flag critical values for physician review workflow.
  - Return severity metadata from interpretation payload.
  - Render severity badges, iconography, and color coding in UI.
- Test targets:
  - `src/backend/tests/test_interpret.py` (extend)
  - `src/frontend/src/__tests__/InterpretedResultCard.test.tsx` (new)

### LAB-002 Trend Context Analysis

- Backend files:
  - `src/backend/modules/analytics.py`
- Frontend files:
  - `src/frontend/src/components/InterpretedTrendChart.tsx` (new)
- Required behavior:
  - Determine trend direction: improving, worsening, stable.
  - Detect "new abnormal" vs "chronic abnormal" using historical windows.
  - Return trend annotations and interpretation-ready trend messaging.
  - Render chart annotations with explanatory labels.
- Test targets:
  - `src/backend/tests/test_analytics.py` (extend)
  - `src/frontend/src/__tests__/InterpretedTrendChart.test.tsx` (new)

### LAB-003 Panel Interpretation with Biomarker Relationships

- Backend files:
  - `src/backend/modules/interpret.py`
- Frontend files:
  - `src/frontend/src/components/PanelInterpretationDashboard.tsx` (new)
- Required behavior:
  - Support cross-biomarker calculations (ratios and basic correlations).
  - Produce panel-level summary narratives.
  - Attach relationship insights to interpretation payloads.
  - Display panel summaries with per-relationship evidence snippets.
- Test targets:
  - `src/backend/tests/test_panel_interpretation.py` (new)
  - `src/frontend/src/__tests__/PanelInterpretationDashboard.test.tsx` (new)

### LAB-004 Personalized Evidence-Based Advice

- Backend files:
  - `src/backend/modules/recommend.py`
  - `src/backend/modules/intervention_mappings.py` (new)
- Required behavior:
  - Rank recommendations by evidence strength.
  - Personalize interventions by user profile/preferences.
  - Enforce conservative health language ("may help" framing).
  - Include recommendation rationale metadata for UI display.
- Test targets:
  - `src/backend/tests/test_recommend.py` (extend)
  - `src/backend/tests/test_intervention_mappings.py` (new)

## Dependency Notes

- LAB-001 and LAB-002 can execute in parallel once common result DTO contract is agreed.
- LAB-003 depends on biomarker normalization utilities established in LAB-001.
- LAB-004 depends on stable output structures from LAB-001 and LAB-003.

## Definition of Done

- All four work packages ship with unit tests and UI render coverage.
- Interpretation APIs expose explicit metadata for severity, trend, and recommendation confidence.
- New components are wired to existing interpretation screens without regressions.
