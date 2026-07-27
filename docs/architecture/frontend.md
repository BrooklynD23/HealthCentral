# Frontend Architecture

**Last Updated:** 2026-07-27
**Owner:** Project Lead
**Refresh Trigger:** A page, service module, or state store is added or removed

Part of the [architecture diagram set](README.md).

---

## Pages and the flows they serve

```mermaid
flowchart TD
    SETUP["ProfileSetup<br/>/setup"] --> RECOVER["RecoverProfile<br/>/recover"]
    SETUP --> APP

    subgraph APP["AppLayout (authenticated)"]
        direction TB

        subgraph capture["Capture & confirm"]
            INBOX["DocumentInbox"]
            VERIFY["VerificationWorkbench"]
        end

        subgraph understand["Understand"]
            TRENDS["TrendsDashboard"]
            TIMELINE["TimelinePage"]
            INTERP["LabInterpreter"]
            EXPLAIN["ExplainAssistant"]
        end

        subgraph act["Act"]
            MEDS["MedicationCoach"]
            MEDDET["MedicationDetail"]
            TASKS["CareTasksPage"]
            NOTIF["NotificationSettings"]
        end

        subgraph organise["Organise & share"]
            SEARCH["SearchPage"]
            PINS["PinboardsPage"]
            EXPORT["ExportPage"]
        end

        SETTINGS["SettingsPage<br/>+ DangerZone"]
    end

    INBOX --> VERIFY --> TRENDS
    VERIFY --> TIMELINE
    MEDS --> MEDDET
    TIMELINE & TRENDS --> EXPLAIN
    organise --> EXPORT
```

## Data flow

```mermaid
flowchart LR
    PAGE["Page component"] --> HOOK["React Query hook<br/>services/*.ts"]
    HOOK --> BARREL["services/index.ts<br/><i>barrel — the single import surface</i>"]
    HOOK --> CLIENT["services/api.ts<br/>apiGet · apiPost · apiPatch · apiDelete"]
    CLIENT --> BACKEND["FastAPI /api/v1"]

    PAGE --> STORE["Zustand authStore<br/>token · profileId · expiry"]
    STORE --> CLIENT

    HOOK --> CACHE["React Query cache<br/>staleTime 5 min"]

    style BARREL fill:#1b5e20,stroke:#66bb6a,color:#fff
```

Two conventions worth stating because they are easy to erode:

- **Everything is exported through `services/index.ts`.** Pages import from the
  barrel, not from individual service files, so the API surface stays visible
  in one place. (Medication hooks are the exception and are imported directly.)
- **Server state lives in React Query; only session state lives in Zustand.**
  The auth store holds the token, profile id and expiry — nothing that the
  server owns.

## Component families

```mermaid
flowchart TD
    UI["components/ui/<br/>Button · Card · Input · Badge · Skeleton · Motion · EmptyState"]

    UI --> LAYOUT["layout/<br/>AppLayout · Sidebar · TopBar"]
    UI --> AUTHC["auth/<br/>ProtectedRoute"]
    UI --> PROFILE["profile/<br/>RecoveryCodeCard"]
    UI --> SET["settings/<br/>DangerZone"]
    UI --> LABS["lab-interpreter/<br/>InterpretedResultCard · CitationTooltip · DisclaimerBanner · ..."]
    UI --> MEDC["medication-coach/<br/>MedicationForm · AdherenceDashboard · StreakDisplay · ..."]
    UI --> DOCS["documents/<br/>HighlightChips · EntityDetailView · ExtractionConfidenceBadge"]
    UI --> PINC["pinboards/<br/>AddToPinboardButton"]
```

Accessibility is a requirement rather than a polish pass: WCAG 2.2 AA, 44 px
targets, keyboard navigation, screen-reader labels, 200 % zoom, and reduced
motion honoured through `useReducedMotion`.
