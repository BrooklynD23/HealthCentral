# HealthCentral API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints except profile listing, creation, and login require a Bearer token.
See [authentication.md](authentication.md) for the full auth flow.

```
Authorization: Bearer <jwt_token>
```

## API Versioning

The API is versioned via URL prefix (`/api/v1`). Breaking changes will increment
the version number.

## Documentation Index

| Document | Description |
|----------|-------------|
| [Authentication](authentication.md) | Login flow, tokens, rate limiting |
| [Endpoints](endpoints.md) | Full endpoint catalog with schemas |
| [Error Codes](error-codes.md) | HTTP status codes and error format |
| [Integration Guide](integration-guide.md) | Quick start and common patterns |

## Interactive Documentation

When running in debug mode, interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
