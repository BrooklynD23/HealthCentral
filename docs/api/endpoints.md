# API Endpoints

**Last Updated:** 2026-03-27
**Owner:** Platform maintainers
**Refresh Trigger:** Mounted backend route added, removed, renamed, or auth requirement changed
**Status:** Source of truth for the live mounted backend API

All routes are mounted under `/api/v1` unless a section explicitly says otherwise.
Auth-required endpoints need `Authorization: Bearer <token>`.
`/health` is mounted at the app root and is intentionally public.

## Profiles

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/profiles/` | No | List available profiles |
| POST | `/profiles/` | No | Create a profile and return a session token |
| POST | `/profiles/login` | No | Log in to a profile |
| GET | `/profiles/me` | Yes | Get the current authenticated profile |
| POST | `/profiles/logout` | Yes | Log out the current session |
| GET | `/profiles/{profile_id}` | Yes | Get profile details |
| POST | `/profiles/{profile_id}/lock` | Yes | Lock a profile and revoke the current session |
| POST | `/profiles/{profile_id}/unlock` | No | Unlock a profile with password and return a session token |
| POST | `/profiles/{profile_id}/change-password` | Yes | Change the profile password |

## Documents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/documents/import` | Yes | Import a PDF/image document |
| GET | `/documents/` | Yes | List documents with optional status/type filters |
| GET | `/documents/{document_id}` | Yes | Get document metadata |
| GET | `/documents/{document_id}/category` | Yes | Get the classified document category |
| GET | `/documents/{document_id}/entities` | Yes | Get extracted document entities |
| GET | `/documents/{document_id}/pages` | Yes | Get page text/provenance data |
| GET | `/documents/{document_id}/pages/{page_number}/image` | Yes | Render a document page as PNG |
| DELETE | `/documents/{document_id}` | Yes | Delete a document and associated data |

## Observations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/observations/` | Yes | List observations with filters |
| GET | `/observations/{observation_id}` | Yes | Get observation details |
| POST | `/observations/{observation_id}/verify` | Yes | Verify or edit an observation |
| GET | `/observations/trends/{analyte}` | Yes | Get analyte trend data |
| GET | `/observations/panels/{panel_id}` | Yes | Get grouped panel data |

## Interpretations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/interpretations/observations/{observation_id}/interpret` | Yes | Generate an observation interpretation |
| GET | `/interpretations/observations/{observation_id}/interpretation` | Yes | Get a stored observation interpretation |
| POST | `/interpretations/panels/{panel_name}/interpret` | Yes | Generate a panel interpretation |
| GET | `/interpretations/recent` | Yes | List recent interpretations |
| GET | `/interpretations/knowledge/biomarker/{analyte_canonical}` | Yes | Get biomarker knowledge content |
| POST | `/interpretations/batch` | Yes | Generate interpretations in batch |

## Assistant

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/assistant/chat` | Yes | Chat with the grounded assistant |
| GET | `/assistant/test-intent/{analyte}` | Yes | Test intent lookup for an analyte |
| GET | `/assistant/glossary/{term}` | Yes | Glossary lookup |
| GET | `/assistant/verification-status` | Yes | Get assistant verification component status |

## Memory

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/memory/` | Yes | Create a memory item |
| GET | `/memory/` | Yes | List memory items |
| GET | `/memory/{item_id}` | Yes | Get a memory item |
| PUT | `/memory/{item_id}` | Yes | Update a memory item |
| DELETE | `/memory/{item_id}` | Yes | Delete a memory item |

## Medications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/medications/` | Yes | Create a medication |
| GET | `/medications/` | Yes | List medications |
| GET | `/medications/{medication_id}` | Yes | Get medication details |
| PATCH | `/medications/{medication_id}` | Yes | Update a medication |
| DELETE | `/medications/{medication_id}` | Yes | Deactivate or hard-delete a medication |
| POST | `/medications/{medication_id}/schedules` | Yes | Create a schedule |
| GET | `/medications/{medication_id}/schedules` | Yes | List schedules |
| PATCH | `/medications/{medication_id}/schedules/{schedule_id}` | Yes | Update a schedule |
| DELETE | `/medications/{medication_id}/schedules/{schedule_id}` | Yes | Delete a schedule |
| POST | `/medications/{medication_id}/doses` | Yes | Log a taken or skipped dose |
| GET | `/medications/{medication_id}/doses` | Yes | List dose history |
| GET | `/medications/{medication_id}/stats` | Yes | Get adherence statistics |
| POST | `/medications/{medication_id}/learn-patterns` | Yes | Run adaptive reminder pattern learning |

## Gamification

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/gamification/badges` | Yes | List badges with earned status |
| GET | `/gamification/streaks` | Yes | Get profile-level streak summary |

## Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/notifications/settings/{medication_id}` | Yes | Get notification settings |
| PATCH | `/notifications/settings/{medication_id}` | Yes | Update notification settings |
| GET | `/notifications/history` | Yes | Get notification history |
| POST | `/notifications/test` | Yes | Send a generic test notification |
| POST | `/notifications/test/{medication_id}` | Yes | Send a medication-specific test notification |
| GET | `/notifications/scheduler/status` | Yes | Get scheduler status |
| POST | `/notifications/{reminder_id}/interaction` | Yes | Record a reminder interaction |

## Export

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/export/doctor-summary` | Yes | Generate a clinician summary |
| GET | `/export/doctor-summary/{summary_id}/download` | Yes | Download a generated summary |
| POST | `/export/questions` | Yes | Generate discussion prompts |
| GET | `/export/csv` | Yes | Export observations as CSV |
| GET | `/export/json` | Yes | Export observations as JSON |

## Model Settings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/settings/model` | Yes | Get model settings and hardware summary |
| POST | `/settings/model/detect` | Yes | Run hardware detection |
| POST | `/settings/model/tier` | Yes | Set preferred model tier |
| GET | `/settings/model/tiers` | Yes | List tier availability |
| GET | `/settings/model/download-progress` | Yes | Get model download progress |
| POST | `/settings/model/download` | Yes | Start a model download |
| GET | `/settings/model/external-api` | Yes | Get external API settings |
| PUT | `/settings/model/external-api` | Yes | Save external API settings |
| GET | `/settings/model/timezone` | Yes | Get the profile timezone |
| PUT | `/settings/model/timezone` | Yes | Set the profile timezone |
| GET | `/settings/model/voice` | Yes | Get voice logging preferences |
| PATCH | `/settings/model/voice` | Yes | Update voice logging preferences |

## Health and Monitoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Public liveness probe |
| GET | `/monitoring/metrics` | Yes | Authenticated metrics dashboard |
