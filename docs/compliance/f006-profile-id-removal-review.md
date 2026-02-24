# F-006 Review: Remove `profile_id` from API responses (Data Minimization)

## Summary

Several API responses include `profile_id` even though the backend already derives the active profile from the JWT/session context. Removing `profile_id` from response DTOs reduces unnecessary identifier exposure to the browser and any client-side logs/telemetry.

This is an **API contract change** and should be reviewed/approved before implementation.

## Current behavior (contract)

Response DTOs that currently include `profile_id`:

- Memory:
  - Backend: `src/backend/api/memory.py:59` (`MemoryItemResponse.profile_id`)
  - Frontend type: `src/frontend/src/services/types.ts:418` (`MemoryItem.profile_id`)
- Documents:
  - Backend: `src/backend/api/documents.py:143` (`DocumentResponse.profile_id`)
  - Frontend type: `src/frontend/src/services/types.ts:38` (`Document.profile_id`)
  - Note: `DocumentImportResponse` embeds `DocumentResponse`.
- Observations:
  - Backend: `src/backend/api/observations.py:92` (`ObservationResponse.profile_id`)
  - Frontend type: `src/frontend/src/services/types.ts:64` (`Observation.profile_id`)

## Proposed change

- Remove `profile_id` from the above response DTOs and from the mirrored frontend TS interfaces.
- Keep `profile_id` server-side for access control, querying, and audit logs.
- The frontend continues to use the auth store’s `profileId` (already required for request-scoped operations).

## Expected effects

### Breaking changes

- Any frontend/backend consumer that reads `resource.profile_id` from API responses will break at runtime (field missing).
- TypeScript compilation will fail until types and fixtures are updated.

### Likely impact in this repo

Initial repo scan suggests most UI code already sources `profileId` from auth state and only uses `profile_id` in **filters / request context**, not as a displayed field. Most work is expected to be:

- Type updates in `src/frontend/src/services/types.ts`
- Updating mocked response objects in frontend tests that include `profile_id`

### Benefits

- Reduces the amount of identifier data returned to the browser.
- Reduces accidental leakage via client-side logging, error reports, or extensions.

## Migration / rollout options

1) **Hard cut (simplest):** remove fields and update UI/tests in the same PR.
   - Pros: clean contract, minimal code complexity.
   - Cons: breaks any external clients pinned to old contract.

2) **Versioned API:** introduce `v2` endpoints without `profile_id`, keep `v1` stable.
   - Pros: safer for external clients.
   - Cons: more code paths and maintenance.

3) **Temporary compatibility flag:** keep `profile_id` behind an explicit opt-in (e.g., query param).
   - Pros: transitional.
   - Cons: more complexity and easy to accidentally keep “on forever”.

## Implementation checklist (if approved)

Backend:

- Update response models and `from_model()` methods:
  - `src/backend/api/memory.py:59`
  - `src/backend/api/documents.py:143`
  - `src/backend/api/observations.py:92`
- Update backend tests expecting `profile_id` in responses (if any).

Frontend:

- Remove `profile_id` from interfaces in `src/frontend/src/services/types.ts`.
- Update any mocked API payloads in `src/frontend/src/__tests__/` that currently include `profile_id`.
- Confirm no UI logic depends on response `profile_id` (prefer auth store `profileId`).

Validation:

- Backend: run `pytest src/backend/tests/`
- Frontend: run `vitest` (or CI equivalent)

## Rollback plan

- Reintroduce `profile_id` into the response DTOs and frontend interfaces if any downstream client requires it.
- Prefer a versioned approach if external clients are expected.

