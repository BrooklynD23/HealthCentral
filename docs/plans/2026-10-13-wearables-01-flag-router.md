# WEAR-01 — Feature Flag, Status Route and Router Skeleton — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0 and the gates in Task 0)
**Base measured:** `origin/main` @ `8234990`. Every `file:line` below was re-read on the plan worktree (`a985390`, docs-only on top of that base) on 2026-10-13.
**Refresh trigger:** any edit to `core/config.py`, `api/__init__.py`, `tests/support/routes.py`, `security/input_validator.py`; WEAR-06 starts (it adds the first gated route and the real-prefix 404 test); a second `/wearables` router appears.
**Program:** [00-program](2026-10-13-wearables-00-program.md) §3 (flag), A13 (real-app tests)
**Depends on:** program M0 only. No other WEAR package.
**Owner decisions it depends on:** none. Builds the flag default (`False`) that every later package assumes.
**Size target:** S, about 150 lines of diff (about 40 product, 110 test).

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, then superpowers:subagent-driven-development. Domain skill for backend work: `asclexis-backend`. Steps use `- [ ]` checkboxes.

**Goal:** `WEARABLES_ENABLED=false` (default) means every `/api/v1/wearables/*` route except `GET /status` answers 404. `GET /api/v1/wearables/status` always answers `{"enabled": <bool>}` to a logged-in profile. No feature code ships.

## 1. Scope

**This plan does:**
- Add `wearables_enabled: bool = False` to `Settings`.
- Add `api/wearables.py` with two routers on the same prefix: `status_router` (ungated, `GET /status`) and `router` (gated by `require_wearables_enabled`, no routes yet).
- Mount both in `api/__init__.py` at `/wearables`.
- Test the flag, the status route, the gate and the real mount.

**This plan does NOT license:**
- Any wearable table, parser, import route or audit key (WEAR-02, 04, 06).
- Any frontend change. The nav entry, page and `useWearablesStatus` hook are WEAR-10.
- Any edit to `security/input_validator.py` (owner gate D4, WEAR-06).
- Any ask-first file (section 4).
- A route inside the gated router. A placeholder route would be a feature nobody asked for (see Q1 in the report).

## 2. Evidence

| Fact | Path:line @8234990 |
|---|---|
| Existing default-False flags sit together; `wearables_enabled` goes after `allow_legacy_plaintext_documents` | `src/backend/core/config.py:123,125,126` |
| `max_import_file_size_mb: int = 50` and `supported_doc_types` are the neighbours | `src/backend/core/config.py:121,122` |
| Settings read env case-insensitively, `.env` file, unknown keys ignored, so `WEARABLES_ENABLED=true` just works | `src/backend/core/config.py:18-23` |
| `settings = Settings()` is a module global; code that reads `settings.x` at call time sees a `monkeypatch.setattr` | `src/backend/core/config.py:276` |
| Routers are mounted one per line with prefix and tags; last static mount is backup | `src/backend/api/__init__.py:48-64` |
| `api_router` is mounted at `/api/v1` | `src/backend/main.py:169` |
| `app = create_app()` is a module global | `src/backend/main.py:104,179` |
| `RequireAuth = Annotated[Session, Depends(require_auth)]`; unauthenticated raises 401 | `src/backend/core/auth.py:217-248,296` |
| Precedent for a single-flag read route that requires auth | `src/backend/api/assistant.py:481-486` (`GET /memory-settings`, takes `RequireAuth`) |
| `route_client(router, prefix, profile_id, master_db, raise_server_exceptions)` mounts a bare `FastAPI()` and overrides `require_auth` and `get_db` only | `src/backend/tests/support/routes.py:27-59` |
| Bare app cannot see a missing mount in `api/__init__.py` | `src/backend/tests/support/routes.py:39-40` (`app = FastAPI()`, `app.include_router(router, prefix=prefix)`) |
| Only `test_db_rename_migration.py` imports `main` in a test; no test builds a `TestClient` on `main.app` | `src/backend/tests/test_db_rename_migration.py:315` |
| Tests flip settings with `monkeypatch.setattr(settings, "<name>", value)` | `src/backend/tests/test_care_tasks.py:801` |
| Upload rejection for `.zip` today: extension check against `supported_extensions` | `src/backend/modules/ingest.py:93-106` |
| `POST /documents/import` returns 400 on `ValueError` from ingest; needs a profile encryption key | `src/backend/api/documents.py:402-450` |
| Baseline collected count on this tree | `CLAUDE.md:30` (1487), `AGENT.md:76` |

INFERRED: a `TestClient(main.app)` built without `with` skips the lifespan, so no startup work touches the real data dir. Task 2 confirms it by running the test and checking no file appears under `app_data_path`.

## 3. Files to touch

| Path | New/edit | Why | Approx lines |
|---|---|---|---|
| `src/backend/core/config.py` | edit | `wearables_enabled: bool = False` after line 126 | +2 |
| `src/backend/api/wearables.py` | new | two routers, dependency, status route | +40 |
| `src/backend/api/__init__.py` | edit | import and mount both routers; docstring line | +5 |
| `src/backend/tests/test_wearables_flag.py` | new | HC-WRB-101..110 | +120 |
| `CLAUDE.md`, `AGENT.md` | edit | collected-count slots (SLOT-RULE) | +2 |

## 4. Ask-first files touched

None. `core/config.py` and `api/__init__.py` are ordinary files. `security/input_validator.py` is untouched (D4 belongs to WEAR-06).

## 5. Data contract

No database change. API surface only.

| Route (full path) | Gate | Auth | Response |
|---|---|---|---|
| `GET /api/v1/wearables/status` | none | `RequireAuth` | `200 {"enabled": bool}` |
| any other `/api/v1/wearables/*` | `require_wearables_enabled` | by that route | flag off: `404 {"detail": "Not Found"}` |

Decisions:
- **Two routers, one prefix.** A router-level dependency also gates every route in that router, `/status` included (program §3, Fable F8). So `/status` lives on `status_router` with no dependency.
- **`/status` requires auth.** Every other `/api/v1` route needs a session, and the frontend asks after login. An open route would tell an unauthenticated caller which optional modules are installed for no benefit. The 401 path is tested.
- **404 body is the framework's own `"Not Found"`.** The dependency raises `HTTPException(404, detail="Not Found")`, the same text FastAPI sends for an unmounted path, so flag-off does not reveal that the module exists.
- **The dependency reads `settings.wearables_enabled` at call time**, never a copy taken at import. That is what lets tests flip it and what lets the owner restart with the env var.
- Dependency signature: `def require_wearables_enabled() -> None`.

## 6. TDD test list

Test IDs `HC-WRB-1NN`. File: `src/backend/tests/test_wearables_flag.py`. Route tests go through HTTP.

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-101 | `Settings(_env_file=None).wearables_enabled is False` with `WEARABLES_ENABLED` removed from env | attribute does not exist (`AttributeError`) |
| HC-WRB-102 | `WEARABLES_ENABLED=true` in env gives `True` | same |
| HC-WRB-103 | `route_client(status_router, "/wearables")` flag off: `GET /wearables/status` is 200 and body equals `{"enabled": False}` | `ImportError: api.wearables` |
| HC-WRB-104 | same, flag on: body equals `{"enabled": True}` | same |
| HC-WRB-105 | probe app built with `APIRouter(dependencies=router.dependencies)` plus one test-local `GET /probe`: flag off gives 404 with body `{"detail": "Not Found"}`; flag on gives 200. Uses the real router's dependency list, so removing the dependency from `router` breaks it | same |
| HC-WRB-106 | `any(d.dependency is require_wearables_enabled for d in router.dependencies)` and `not status_router.dependencies` | same |
| HC-WRB-107 | `TestClient(main.app)` with `require_auth` overridden: `GET /api/v1/wearables/status` is 200 for flag off and for flag on. Proves the status mount at the real prefix (program A13, recurring-failures #10) | route not mounted: 404 |
| HC-WRB-108 | `TestClient(main.app)` with no override: `GET /api/v1/wearables/status` is 401 | route not mounted: 404 instead of 401 |
| HC-WRB-109 | AST of `api/__init__.py` contains two `include_router` calls with `prefix="/wearables"` whose first arguments are `wearables_router` and `wearables_status_router`. Weak guard for the empty gated router, whose mount no HTTP call can see yet | calls absent |
| HC-WRB-110 | Characterization (research HC-WRB-007, reworded): `POST /api/v1/documents/import` through `route_client(documents_router, "/documents")` with `export.zip` returns 400 and detail contains `Unsupported file type`. Needs `api.documents.get_profile_encryption_key` patched and `get_profile_db_session` overridden. **Passes before the change by design**: it pins that WEAR-01 did not widen `supported_doc_types` | not RED; proves no regression |

Covers research HC-WRB-007 (HC-WRB-103/105 for "wearables route 404 when off", HC-WRB-110 for the documents path). Research HC-WRB-015 (count rises by exactly the new tests) is checked in Task 4.

Test hygiene: every flag flip uses `monkeypatch.setattr(settings, "wearables_enabled", ...)` where `settings` is `core.config.settings`. `main.app.dependency_overrides` is cleared in a `try/finally`.

## 7. Tasks

### Task 0 — gates

- [ ] 0.1 `git fetch origin && git merge-base --is-ancestor 8234990 origin/main` exits 0.
- [ ] 0.2 Program M0 is met: the owner has approved the plan set. Plan file `docs/plans/2026-10-13-wearables-01-flag-router.md` is on the branch.
- [ ] 0.3 `git grep -n "wearables" src/backend` shows no existing flag or router (expected: empty). If not empty, STOP and re-plan.
- [ ] 0.4 Branch `feat/wear-01-flag-router` from `origin/main`.
- [ ] 0.5 Record the start count: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1`. Expect 1487 (`CLAUDE.md:30`). Call it N.

### Task 1 — RED

- [ ] 1.1 Write `tests/test_wearables_flag.py` with HC-WRB-101..110.
- [ ] 1.2 Run: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_flag.py -p no:cacheprovider -q`
- [ ] 1.3 Expected: collection error `ModuleNotFoundError: api.wearables` for the file, or per-test failures if imports are done inside tests. Paste the first failure into the PR. HC-WRB-110 is the one test that passes; say so.

### Task 2 — GREEN

- [ ] 2.1 `core/config.py`: add `wearables_enabled: bool = False` directly after `allow_legacy_plaintext_documents` (`:126`).
- [ ] 2.2 `api/wearables.py` (key shape):

```python
status_router = APIRouter()
router = APIRouter(dependencies=[Depends(require_wearables_enabled)])

def require_wearables_enabled() -> None:
    if not settings.wearables_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not Found")

@status_router.get("/status")
async def wearables_status(session: RequireAuth) -> dict[str, bool]:
    return {"enabled": settings.wearables_enabled}
```

- [ ] 2.3 `api/__init__.py`: import both routers and add two `include_router(..., prefix="/wearables", tags=["wearables"])` lines after the backup mount (`:64`). Add `- wearables: ...` to the module docstring list.
- [ ] 2.4 Re-run the file command. Expect 10 passed. Check no new file under the configured `app_data_path` (INFERRED lifespan skip).
- [ ] 2.5 No `# type: ignore`, no new dependency. `status_router` and `router` stay in one 40-line file.

### Task 3 — refactor and neighbours

- [ ] 3.1 Run the neighbours that touch the router list or settings: `python -m pytest tests/test_documents_api.py tests/test_audit_phi_minimization.py -p no:cacheprovider -q`.
- [ ] 3.2 `python -m ruff check src/backend/api/wearables.py` and the repo's type check if configured. Report the output.

### Task 4 — full suite and count slots

- [ ] 4.1 `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest tests/ -p no:cacheprovider -q`
- [ ] 4.2 Expect only `test_api_rag_index_002b` to fail without an embedding model (`CLAUDE.md:30-33`). Anything else is yours.
- [ ] 4.3 Collected = N + 10 = 1497 if no one else has moved the count. Update the count in `CLAUDE.md:30` and `AGENT.md:76` in the same commit. If `origin/main` has moved N, use N + 10.
- [ ] 4.4 Read `docs/agentic/recurring-failures.md` before claiming done; add a new entry if you hit a new mode.

## 8. Mutation and break checks

Each break is temporary. After reverting run `git diff --stat` and confirm only the intended files differ.

| # | Break | Expected red |
|---|---|---|
| B1 | Delete `dependencies=[Depends(require_wearables_enabled)]` from `router` | HC-WRB-105 and HC-WRB-106 fail |
| B2 | Move `/status` onto `router` | HC-WRB-103 fails (404 when off) and HC-WRB-106 fails |
| B3 | Comment out the `status_router` mount in `api/__init__.py` | HC-WRB-107, 108, 109 fail |
| B4 | Cache the flag at import: `ENABLED = settings.wearables_enabled` and read `ENABLED` | HC-WRB-104 and HC-WRB-105 (flag-on half) fail |

## 9. Acceptance criteria

- `pytest tests/test_wearables_flag.py` prints `10 passed`; the output is pasted in the PR.
- Full suite: only the known embedding failure; collected count equals N + 10; slots updated.
- B1-B4 each seen red, then reverted, `git diff --stat` clean of the break.
- `git diff --stat origin/main` lists exactly the files in section 3.
- Manual check by running the app: `GET /api/v1/wearables/status` with a session token gives `{"enabled":false}`; with `WEARABLES_ENABLED=true` gives `{"enabled":true}`. Paste the two responses. No frontend change visible.

## 10. Rollback

Revert the PR. There is no migration, no data and no persisted setting. Removing the env var alone also restores the off state.

## 11. What these tests cannot see

- **Recurring-failures #1 (green suite that could not fail).** `route_client` mounts a bare app, so HC-WRB-103/105 cannot see a missing mount. HC-WRB-107/108 on `main.app` cover `/status`. The **gated** router has no route yet, so no HTTP call can prove it is mounted, or that flag-off 404 holds at the real prefix; HC-WRB-109 is a source-text check, not behaviour. WEAR-06 must add the real-prefix flag-off 404 on `main.app` as soon as `POST /wearables/imports` exists.
- **Recurring-failures #10 (built but never started).** The flag exists and `/status` answers, but nothing consumes it until WEAR-10. A dead flag is expected here; do not read "tests green" as "feature reachable".
- **Recurring-failures #4 (environment-dependent counts).** The count is N + 10 relative to the tree you start from, not an absolute.
- The body-size and multipart-before-dependency order (program §3) is not exercised: there is no upload route yet.
- HC-WRB-110 depends on patching the encryption-key lookup; if that helper is renamed the test fails for the wrong reason.

## 12. Owner and model-machine items

None. (OW-W0..W6 in program §10 belong to later packages.)
