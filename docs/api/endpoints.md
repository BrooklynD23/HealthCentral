# API Endpoints

All endpoints are prefixed with `/api/v1`. Auth-required endpoints need a
`Authorization: Bearer <token>` header unless noted otherwise.

## Profiles

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/profiles/` | No | List all profiles |
| POST | `/profiles/` | No | Create new profile |
| POST | `/profiles/login` | No | Login to profile |
| GET | `/profiles/me` | Yes | Get current profile |
| POST | `/profiles/logout` | Yes | Logout and close vault |
| GET | `/profiles/{profile_id}` | Yes | Get profile details |
| POST | `/profiles/{profile_id}/lock` | Yes | Lock profile |
| POST | `/profiles/{profile_id}/unlock` | No | Unlock profile with password |
| POST | `/profiles/{profile_id}/change-password` | Yes | Change password |

### POST /profiles/

```json
{
    "name": "string (required)",
    "password": "string (required)"
}
```

### POST /profiles/login

```json
{
    "profile_id": "string (required)",
    "password": "string (required)"
}
```

## Documents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/documents/import` | Yes | Import PDF/image, extract observations |
| GET | `/documents/` | Yes | List documents |
| GET | `/documents/{document_id}` | Yes | Get document details |
| GET | `/documents/{document_id}/pages` | Yes | Get document pages |
| DELETE | `/documents/{document_id}` | Yes | Delete document |

### POST /documents/import

Accepts `multipart/form-data` with a file field. Supported types: PDF, PNG, JPG, JPEG.

```bash
curl -X POST http://localhost:8000/api/v1/documents/import \
  -H "Authorization: Bearer <token>" \
  -F "file=@lab-results.pdf"
```

## Observations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/observations/` | Yes | List observations with filters |
| GET | `/observations/{observation_id}` | Yes | Get observation details |
| POST | `/observations/{observation_id}/verify` | Yes | Verify/edit observation |
| GET | `/observations/trends/{analyte}` | Yes | Get trend data for analyte |
| GET | `/observations/panels/{panel_id}` | Yes | Get lab panel data |

### GET /observations/

Query parameters:
- `analyte`: Filter by analyte name
- `date_from`, `date_to`: Date range filter (ISO 8601)
- `abnormal`: Filter abnormal results only (`true`/`false`)
- `verified`: Filter by verification status (`true`/`false`)

### Panels

Available panel IDs: `cbc`, `cmp`, `lipid`, `thyroid`

## Interpretations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/interpretations/observations/{observation_id}/interpret` | Yes | Generate interpretation |
| GET | `/interpretations/observations/{observation_id}/interpretation` | Yes | Get existing interpretation |
| POST | `/interpretations/panels/{panel_name}/interpret` | Yes | Holistic panel interpretation |
| GET | `/interpretations/recent` | Yes | Recent interpretations |
| GET | `/interpretations/knowledge/biomarker/{analyte}` | Yes | Biomarker knowledge |
| POST | `/interpretations/batch` | Yes | Batch interpretation |

## Medications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/medications/` | Yes | Create medication |
| GET | `/medications/` | Yes | List medications |
| GET | `/medications/{medication_id}` | Yes | Get medication |
| PATCH | `/medications/{medication_id}` | Yes | Update medication |
| DELETE | `/medications/{medication_id}` | Yes | Deactivate medication |
| POST | `/medications/{medication_id}/schedules` | Yes | Create schedule |
| GET | `/medications/{medication_id}/schedules` | Yes | List schedules |
| PATCH | `/medications/{medication_id}/schedules/{schedule_id}` | Yes | Update schedule |
| DELETE | `/medications/{medication_id}/schedules/{schedule_id}` | Yes | Delete schedule |
| POST | `/medications/{medication_id}/doses` | Yes | Log dose |
| GET | `/medications/{medication_id}/doses` | Yes | List dose records |
| GET | `/medications/{medication_id}/stats` | Yes | Adherence statistics |
| POST | `/medications/{medication_id}/learn-patterns` | Yes | Trigger pattern learning |

### POST /medications/

```json
{
    "name": "string (required)",
    "dosage": "string",
    "frequency": "string",
    "notes": "string"
}
```

### POST /medications/{medication_id}/doses

**Query Parameters:** `schedule_id` (optional) — auto-matched schedule ID

**Request:**
```json
{
    "taken_at": "ISO 8601 datetime (required)",
    "log_method": "manual | voice",
    "dosage_amount": "number",
    "dosage_unit": "string",
    "notes": "string",
    "was_skipped": "boolean (default false)",
    "skip_reason": "string (when was_skipped=true)"
}
```

**Response:**
```json
{
    "dose": {
        "id": "string",
        "medication_id": "string",
        "schedule_id": "string | null",
        "taken_at": "ISO 8601 datetime",
        "log_method": "string",
        "dosage_amount": "number | null",
        "dosage_unit": "string | null",
        "variance_minutes": "number | null",
        "notes": "string | null",
        "was_skipped": "boolean",
        "skip_reason": "string | null",
        "logged_at": "ISO 8601 datetime"
    },
    "newly_earned_badges": [
        {
            "badge_id": "string",
            "name": "string",
            "description": "string",
            "icon": "string",
            "medication_id": "string | null",
            "earned_at": "ISO 8601 datetime"
        }
    ]
}
```

## Gamification

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/gamification/badges` | Yes | List all badges with earned status |

## Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/notifications/settings/{medication_id}` | Yes | Get notification settings |
| PATCH | `/notifications/settings/{medication_id}` | Yes | Update notification settings |
| GET | `/notifications/history` | Yes | Notification history |
| POST | `/notifications/test` | Yes | Send test notification |
| POST | `/notifications/test/{medication_id}` | Yes | Test medication notification |
| GET | `/notifications/scheduler/status` | Yes | Scheduler status |
| POST | `/notifications/{reminder_id}/interaction` | Yes | Record reminder interaction |

## Assistant (RAG Chat)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/assistant/chat` | Yes | Chat with grounded AI assistant |
| GET | `/assistant/test-intent/{analyte}` | Yes | Test intent explanation |
| GET | `/assistant/glossary/{term}` | Yes | Glossary lookup |
| GET | `/assistant/verification-status` | Yes | Verification system status |

### POST /assistant/chat

```json
{
    "message": "string (required)",
    "conversation_id": "string (optional)"
}
```

## Export

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/export/doctor-summary` | Yes | Generate clinician summary |
| GET | `/export/doctor-summary/{summary_id}/download` | Yes | Download summary |
| POST | `/export/questions` | Yes | Generate discussion prompts |
| GET | `/export/csv` | Yes | Export observations as CSV |
| GET | `/export/json` | Yes | Export observations as JSON |

## Model Settings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/settings/model/` | Yes | Get model settings |
| POST | `/settings/model/detect` | Yes | Run hardware detection |
| POST | `/settings/model/tier` | Yes | Set model tier |
| GET | `/settings/model/tiers` | Yes | List available tiers |
| GET | `/settings/model/download-progress` | Yes | Download progress |
| POST | `/settings/model/download` | Yes | Start model download |
| GET | `/settings/model/external-api` | Yes | Get external API settings |
| PUT | `/settings/model/external-api` | Yes | Save external API settings |

## Health & Monitoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Liveness probe (status, mode, version) |
| GET | `/api/v1/monitoring/metrics` | Yes | Full metrics dashboard (Bearer token required) |
