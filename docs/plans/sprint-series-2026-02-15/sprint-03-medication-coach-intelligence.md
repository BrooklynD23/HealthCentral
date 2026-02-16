# Sprint 03 - Adaptive Medication Coach Intelligence

**Sprint ID:** HC-S03-MED
**Priority:** High
**Source Area:** Adaptive Medication Adherence Coach - Advanced Features

## Architecture Scope

- Behavior analytics and scheduling logic: `src/backend/modules/adherence_patterns.py`.
- Reminder content and dispatch logic: `src/backend/modules/message_generator.py`, `src/backend/modules/notification_scheduler.py`.
- UI workflows: `src/frontend/src/pages/MedicationCoach.tsx`, `src/frontend/src/components/AdherenceDashboard.tsx` (new).
- Lab-medication correlation context: `src/frontend/src/utils/correlation.ts`, `src/frontend/src/components/MedicationOverlay.tsx`.

## Work Packages

### MED-001 Adaptive Scheduling Algorithm

- Backend files:
  - `src/backend/modules/adherence_patterns.py`
- Frontend files:
  - `src/frontend/src/pages/MedicationCoach.tsx`
- Required behavior:
  - Learn user dose timing windows with variance tracking.
  - Split behavior by weekday/weekend patterns.
  - Compute adaptive reminder windows from user history.
  - Feed optimized schedule suggestions to coach UI.
- Test targets:
  - `src/backend/tests/test_adherence_patterns.py` (extend)
  - `src/frontend/src/__tests__/MedicationCoach.test.tsx` (extend)

### MED-002 Smart Reminder System

- Backend files:
  - `src/backend/modules/message_generator.py`
  - `src/backend/modules/notification_scheduler.py`
- Required behavior:
  - Multi-level reminder priority (initial, nudge, important alert).
  - Tone control per context (supportive, friendly, concerned).
  - Encouragement pool randomization with deterministic test mode.
  - Streak celebration triggers and templates.
- Test targets:
  - `src/backend/tests/test_message_generator.py` (extend)
  - `src/backend/tests/test_notification_scheduler.py` (extend)

### MED-003 Pattern Recognition and Analytics

- Backend files:
  - `src/backend/modules/adherence_patterns.py`
- Frontend files:
  - `src/frontend/src/components/AdherenceDashboard.tsx` (new)
- Required behavior:
  - Detect missed-dose patterns and late-dose clusters.
  - Compute streaks and aggregate adherence metrics.
  - Expose analytics API contract for dashboard widgets.
  - Visualize trends and streak health in dashboard.
- Test targets:
  - `src/backend/tests/test_adherence_analytics.py` (new)
  - `src/frontend/src/__tests__/AdherenceDashboard.test.tsx` (new)

### MED-004 Lab-Medication Correlation Integration

- Frontend files:
  - `src/frontend/src/utils/correlation.ts`
  - `src/frontend/src/components/MedicationOverlay.tsx`
- Required behavior:
  - Add correlation strength and confidence output for lab-med relationships.
  - Surface context messages on trend and medication views.
  - Add timeline overlays that align adherence events with lab value changes.
- Test targets:
  - `src/frontend/src/__tests__/CorrelationContract.test.ts` (extend)
  - `src/frontend/src/__tests__/MedicationOverlay.test.tsx` (extend)

## Dependency Notes

- MED-001 should land before MED-002 so reminder timing has adaptive inputs.
- MED-003 depends on event-normalization utilities created in MED-001.
- MED-004 can run in parallel with MED-003 if correlation DTOs remain backward-compatible.

## Definition of Done

- Medication coach behavior adapts based on user adherence history.
- Reminder messages are prioritized and tone-aware.
- Dashboard and overlays expose understandable adherence insights tied to labs.
