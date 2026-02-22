# Integration Guide

## Quick Start

### 1. Start the Server

```bash
cd src/backend
python main.py
```

The API runs at `http://localhost:8000`.

### 2. Create a Profile

```bash
curl -X POST http://localhost:8000/api/v1/profiles/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "password": "test123"}'
```

### 3. Login

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/profiles/login \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "<profile_id>", "password": "test123"}' \
  | jq -r '.access_token')
```

### 4. Import a Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@lab-results.pdf"
```

### 5. View Observations

```bash
curl http://localhost:8000/api/v1/observations/ \
  -H "Authorization: Bearer $TOKEN"
```

## Common Patterns

### Pagination

List endpoints support query parameters for filtering. Check each endpoint's
documentation for available filters.

### Error Handling

Always check the HTTP status code. Error responses include a `detail` field:

```python
response = requests.get(url, headers=headers)
if response.status_code == 401:
    # Token expired — re-login
    token = login(profile_id, password)
elif response.status_code == 429:
    # Rate limited — wait and retry
    retry_after = int(response.headers.get("Retry-After", 60))
    time.sleep(retry_after)
elif response.status_code >= 400:
    error = response.json().get("detail", "Unknown error")
    raise Exception(f"API error {response.status_code}: {error}")
```

### Token Refresh

Tokens expire after the auto-lock timeout (default 15 minutes of inactivity).
Re-login to get a fresh token:

```python
def ensure_authenticated(profile_id, password, headers):
    response = requests.get(f"{BASE}/profiles/me", headers=headers)
    if response.status_code == 401:
        token = login(profile_id, password)
        headers["Authorization"] = f"Bearer {token}"
    return headers
```

### Import Workflow

The typical document workflow:

1. **Import**: `POST /documents/import` with file
2. **Review**: `GET /observations/` to see extracted values
3. **Verify**: `POST /observations/{id}/verify` to confirm accuracy
4. **Interpret**: `POST /interpretations/observations/{id}/interpret`
5. **Export**: `POST /export/doctor-summary` for clinician report

### Correlation IDs

Include `X-Correlation-ID` in requests to trace operations across logs:

```bash
curl http://localhost:8000/api/v1/observations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Correlation-ID: $(uuidgen)"
```

The same ID appears in the response header and server logs.
