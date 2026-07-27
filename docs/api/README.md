# HealthCentral API Documentation

**Last Updated:** 2026-07-27

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints except profile listing, creation, login, and profile recovery
require a Bearer token. See [authentication.md](authentication.md) for the full
auth flow.

Profile recovery (`POST /profiles/{id}/recover`) is necessarily unauthenticated
— the caller has lost the only other credential — and is rate-limited
separately and more strictly than login.

```
Authorization: Bearer <jwt_token>
```

## API Versioning

The API is versioned via URL prefix (`/api/v1`). Breaking changes will increment
the version number.

## Documentation Index

| Document | Description |
|----------|-------------|
| [Authentication](authentication.md) | Login flow, tokens, rate limiting, recovery |
| [Endpoints](endpoints.md) | Full endpoint catalog with schemas — the API source of truth |
| [Error Codes](error-codes.md) | HTTP status codes and error format |
| [Integration Guide](integration-guide.md) | Quick start and common patterns |

## Router Groups

Eighteen routers are mounted under `/api/v1`. See
[endpoints.md](endpoints.md) for the exact route inventory and
[the request-lifecycle diagram](../architecture/backend.md#request-lifecycle)
for what every request passes through before it reaches one.

| Group | Prefix | Notes |
|---|---|---|
| Profiles | `/profiles` | Create, login, unlock, change password, recovery code, recover, **delete** |
| Documents | `/documents` | Import (incl. CSV/FHIR), pages, entities, highlights, verify, reprocess |
| Observations | `/observations` | List, trends, panels, verify |
| Interpretations | `/interpretations` | Generate, regenerate, feedback |
| Medications | `/medications` | CRUD, schedules, doses, **correlations** |
| Med reconciliation | `/med-reconciliation` | Suggestions only — never mutates the tracker |
| Care tasks | `/care-tasks` | Candidates, accept, update |
| Timeline | `/timeline` | Derived chronological read-model |
| Search | `/search` | Cross-record search |
| Pinboards | `/pinboards` | Collections + packet export |
| Assistant | `/assistant` | Chat, sessions, glossary, memory settings |
| Memory | `/memory` | Assistant memory items |
| Export | `/export` | Doctor summary, visit prep, FHIR R4, questions, CSV/JSON |
| Feedback | `/feedback` | Ratings, stats, RL dataset export (strict redaction) |
| Model settings | `/settings/model` | Provider, tier, downloads, timezone, voice |
| Gamification | `/gamification` | Badges, settings |
| Notifications | `/notifications` | Reminder settings |
| Monitoring | `/monitoring` | Metrics (auth-protected); `/health` is public and unprefixed |

**Every route touching documents, observations or profile data writes an audit
row**, and those rows are allowlist-scrubbed before they are stored — see
[PHI minimization](../compliance/hipaa-controls.md).

## Interactive Documentation

When running in debug mode, interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
