# Authentication

## Overview

HealthCentral uses JWT bearer tokens for authentication. Each profile has a
password-protected vault; logging in returns a token for subsequent requests.

## Login Flow

### 1. List Profiles

```bash
curl http://localhost:8000/api/v1/profiles/
```

Returns available profiles (no auth required).

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/profiles/login \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "abc-123", "password": "your-password"}'
```

Response:
```json
{
    "access_token": "eyJhbGciOiJIUzI...",
    "token_type": "bearer",
    "profile_id": "abc-123",
    "profile_name": "John Doe"
}
```

### 3. Use Token

Include the token in all subsequent requests:

```bash
curl http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI..."
```

### 4. Logout

```bash
curl -X POST http://localhost:8000/api/v1/profiles/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI..."
```

Logout revokes the token and closes the profile database connection.

## Token Details

| Property | Value |
|----------|-------|
| Algorithm | HS256 |
| Expiry | Configurable (default: 15 minutes auto-lock) |
| Revocation | Supported via logout |

## Rate Limiting

Authentication endpoints are protected by rate limiting:

| Setting | Default |
|---------|---------|
| Max attempts per window | 10 |
| Window duration | 60 seconds |
| Lockout behavior | 429 Too Many Requests with Retry-After header |

All API endpoints have a general rate limit:

| Setting | Default |
|---------|---------|
| Max requests per window | 100 |
| Window duration | 60 seconds |

Rate limit headers on every response:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when window resets
- `Retry-After`: Seconds to wait (only on 429 responses)

## Creating a Profile

```bash
curl -X POST http://localhost:8000/api/v1/profiles/ \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "password": "secure-password"}'
```

No auth required. Creates an encrypted vault for the profile.
