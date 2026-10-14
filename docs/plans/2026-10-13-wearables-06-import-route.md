# WEAR-06 — Import Route, Persistence, Audit, Size Cap — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0, WEAR-01/02/04/05 merged, and owner gates D4 + D6 signed)
**Base measured:** `origin/main` @ 8234990
**Refresh trigger:** WEAR-01, 02, 04 or 05 merge (re-read their real function names, Task 0); any edit to `security/input_validator.py`, `core/audit.py`, `core/config.py` or `main.py` lifespan; owner answers D4 or D6.
**Program:** [00-program](2026-10-13-wearables-00-program.md) (A1, A2, A5b, A9, A10, A12, A13; R4, R6)
**Depends on:** WEAR-01 (flag + routers), WEAR-02 (models, `validate_summary`, audit vocabulary), WEAR-04 (Apple parser), WEAR-05 (aggregate).
**Owner decisions it builds:** D1 (b) no raw ZIP kept; D4 (a) per-prefix cap, placeholder 500 MB; D6 (b) app-owned temp file.
**Size target:** ~380 lines of non-test diff, one L1 PR.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, with superpowers:subagent-driven-development. Domain skill: `asclexis-backend`.

## 1. Scope

**Does:**
- `POST /api/v1/wearables/imports`: the client sends the Apple Health ZIP as the raw request body (`Content-Type: application/zip`). No multipart.
- Stream the body to `app_data_path/tmp/wearables-<uuid>.zip` in chunks, hashing SHA-256 while writing. Delete the file in `finally`.
- Refuse a duplicate `content_hash` for this profile (409 with the existing import id). Parse, aggregate, validate, write the import + daily rows + review stubs in one transaction.
- Audit with counts plus the opaque `import_id` and `vendor` enum (program M2). Add the per-prefix size limit in `security/input_validator.py` (OWNER GATE D4). Add the startup sweep of stale temp files.

**Does NOT:**
- Read, list, review or delete imports (WEAR-07). Detect Garmin (WEAR-12). Touch the frontend (WEAR-07b/10).
- Store the ZIP anywhere permanent (D1 b). Write wearable rows into `observations` (A3).
- Edit `modules/redaction.py`, `core/auth.py`, `core/security.py` or any encryption code.

## 2. Evidence

| Fact | path:line @8234990 |
|---|---|
| Import prefixes are one shared tuple | `src/backend/security/input_validator.py:18-21` |
| Shared upload limit = `max_import_file_size_mb` x 1.05 | `security/input_validator.py:41` |
| Limit chosen per request; non-import = 10 MB | `security/input_validator.py:69-71` (`max_request_body_bytes` default `:38`) |
| Content-Length over limit → 413; missing → counting `receive` | `security/input_validator.py:78-96` |
| Counting `receive` raises `_BodyTooLargeError`, caught around the app call → 413 | `security/input_validator.py:122-132`, `:106-110` |
| Middleware registered in the real app | `src/backend/main.py:19`, `:136` |
| Lifespan; fail-soft startup blocks (backup scheduler); `yield` | `main.py:30-31`, `:67-74`, `:87` |
| `max_import_file_size_mb: int = 50`; `app_data_path` property | `src/backend/core/config.py:121`, `:165` |
| `audit_and_commit` (fail-closed) | `core/audit.py:474` |
| `ALLOWED_ACTIONS`, `STRING_DETAIL_KEYS`, `ALLOWED_DETAIL_KEYS`, scrubber | `core/audit.py:36`, `:69`, `:89`, `:118` |
| `log_document_event` never persists filename | `core/audit.py:305-317` |
| `ProfileDbSession`; `get_profile_db_session` | `core/auth.py:341`, `:315` |
| Routers mounted statically; export mounted here | `src/backend/api/__init__.py:45`, `:55` |
| `route_client(router, prefix, profile_id, master_db, raise_server_exceptions)`, bare `FastAPI()` | `src/backend/tests/support/routes.py:26-40` |
| Profile DB override pattern on a `route_client` | `tests/test_audit_order.py:163-173` |
| Poisoned-details audit test to mirror (HC-AUD-001) | `tests/test_audit_phi_minimization.py:58-62` |
| `wearables_enabled`, `status_router`, gated `router`, models, `validate_summary`, parser and aggregate names | INFERRED from WEAR-01/02/04/05 briefs; none exists on this tree (`ls modules/wearables api/wearables.py` → missing). Task 0 re-reads them. |

## 3. Files to touch

| Path | new/edit | Why | ~Lines |
|---|---|---|---|
| `src/backend/api/wearables.py` | edit | add `POST /imports` to the gated router | +110 |
| `src/backend/modules/wearables/upload.py` | new | `stream_body_to_temp()`, `sweep_stale_uploads()` | +55 |
| `src/backend/security/input_validator.py` | edit | per-prefix limit (OWNER GATE D4) | +16 / -2 |
| `src/backend/core/config.py` | edit | `wearables_max_import_mb: int = 500` after `:121` | +2 |
| `src/backend/main.py` | edit | fail-soft sweep call before `yield` (`:87`) | +8 |
| `src/backend/core/audit.py` | edit only if WEAR-02 left no wearable log function | `log_wearable_event` (security-reviewer) | +0..20 |
| `tests/test_wearables_import_route.py`, `tests/test_wearables_import_limits.py` | new | tests below | +330 |

Non-test diff stays near 200 lines; tests carry the rest.

## 4. Ask-first / owner-gated files touched

| File | Gate | Note |
|---|---|---|
| `src/backend/security/input_validator.py` | **OWNER GATE D4** (program §7 treats it as ask-first) | Owner signs the diff in section 5 before Task 3. |
| `core/audit.py` | not ask-first; security-reviewer pass required (program A12) | Only if Task 0 finds no wearable log function. |

No file on the CLAUDE.md ask-first list is touched.

## 5. Exact intended `security/input_validator.py` diff (D4 option a)

Goal: wearables get their own cap, active only when `wearables_enabled`, for exactly `POST /api/v1/wearables/imports`. Every other path keeps today's limit.

```diff
 IMPORT_PATH_PREFIXES = (
     "/api/v1/documents/import",
     "/api/v1/documents/upload",
 )
+
+# Wearables upload: exact POST path, own cap, only while the flag is on (D4).
+WEARABLE_IMPORT_PATH = "/api/v1/wearables/imports"
@@ class InputValidationMiddleware
+    def _limit_for(self, method: str, path: str) -> int:
+        if path.rstrip("/") == WEARABLE_IMPORT_PATH and method == "POST":
+            if app_settings.wearables_enabled:
+                return int(app_settings.wearables_max_import_mb * 1024 * 1024 * 1.05)
+            return self.max_request_body_bytes  # flag off: default 10 MB, then 404
+        if any(path.startswith(prefix) for prefix in IMPORT_PATH_PREFIXES):
+            return self.max_upload_bytes
+        return self.max_request_body_bytes
@@ __call__ (replaces lines 69-71)
-        is_import = any(path.startswith(prefix) for prefix in IMPORT_PATH_PREFIXES)
-        effective_limit = self.max_upload_bytes if is_import else self.max_request_body_bytes
+        effective_limit = self._limit_for(method, path)
```

Why this shape:
- The flag and the cap are read per request, so a test that patches `settings` takes effect (the constructor at `:41` reads once).
- Exact path + POST only: `PUT /wearables/imports/{id}/review` and `DELETE` keep the 10 MB default. A `startswith` match would give them a 525 MB body allowance.
- Existing document prefixes behave exactly as before (`:41`, `:70-71`).

## 6. Data contract used (WEAR-02)

- Reads/writes `wearable_imports`, `wearable_daily_metrics`, `wearable_metric_reviews` exactly as WEAR-02 defines them. This plan adds no column.
- Import row: `source_vendor="apple"`, `schema_version="wdm-1"`, `content_hash` = streaming SHA-256 of the body, `filename` from header `X-Wearable-Filename` (optional, path separators stripped, capped 255, shown in the app only), counts from the parser/aggregate result, `first/last_local_date` from the rows.
- One `wearable_metric_reviews` stub per metric that has rows: `patient_reviewed_at=NULL`, `include_in_packet=False`. WEAR-07 depends on this.
- Response `201`: `{import_id, source_vendor, rows_written, records_read, records_skipped, skipped: {reason: count}, days_covered, first_local_date, last_local_date}`.
- Status map: 404 flag off; 415 wrong content-type; 400 empty body or parse refusal; 409 duplicate (`{"detail": ..., "import_id": ...}`); 413 over cap; 422 contract errors.
- Audit event `wearable.import`, action from WEAR-02's reserved list, `details` limited to `import_id, vendor, rows_written, records_read, records_skipped, days_covered`.

## 7. TDD test list

IDs `HC-WRB-6NN`. Files: `R` = `tests/test_wearables_import_route.py` (via `route_client`, profile DB override as in `tests/test_audit_order.py:173`), `L` = `tests/test_wearables_import_limits.py` (`TestClient(main.app)`, program A13). Synthetic exports come from WEAR-04's test helper. Covers research HC-WRB-004, 005, 008 (partly), 014.

| ID | File | Assertion | RED reason |
|---|---|---|---|
| HC-WRB-601 | R | flag off → `POST` 404; tmp dir has zero `wearables-*` files | route absent |
| HC-WRB-602 | R | happy path: 201; profile DB holds 1 import, N metric rows whose `(metric, local_date, value)` equal the fixture dict, 1 review stub per metric (NULL reviewed, `include_in_packet` False) | route absent |
| HC-WRB-603 | R | after 201 the tmp dir is empty | no temp handling |
| HC-WRB-604 | R | hostile ZIP (path traversal member; and a header-lying bomb) → 400, tmp dir empty, zero rows | route absent |
| HC-WRB-605 | R | bomb parse peak memory `tracemalloc` < 64 MB, status 400 (research 005) | route absent |
| HC-WRB-606 | R | same bytes twice → second is 409 whose `import_id` equals the first; import row count still 1 (research 004) | no dedup |
| HC-WRB-607 | R | monkeypatch aggregate to emit an unknown unit → 422; zero rows in all 3 tables | no validation call |
| HC-WRB-608 | R | `Content-Type: multipart/form-data` → 415; empty body → 400 | route absent |
| HC-WRB-609 | R | `wearables_max_import_mb=1`, 2 MB body, no middleware → 413 from the route's own byte counter; tmp dir empty | no counter |
| HC-WRB-610 | R | profile A imports; a session for profile B sees zero imports/metrics/reviews by direct query; B importing the same bytes gets 201 (hash is per profile) (research 008) | route absent |
| HC-WRB-611 | R | audit row written through a real master DB: `details` keys ⊆ the reserved count keys + `import_id`/`vendor`; filename, `source_name`, a metric value and the word "Watch" absent from `details_json` (mirror `tests/test_audit_phi_minimization.py:58-62`; research 014) | no audit call |
| HC-WRB-612 | R | audit commit raises → 500 and zero rows in the profile DB (profile rows flushed, not committed, until audit succeeds) | wrong order |
| HC-WRB-613 | L | `main.app`, flag on, cap 1 MB, `Content-Length` 2 MB → 413 | no per-prefix cap |
| HC-WRB-614 | L | `main.app`, flag on, chunked body (generator, no Content-Length) over cap → 413 | counting path unused |
| HC-WRB-615 | L | `main.app`, flag on, cap 100 MB, `Content-Length` 20 MB → NOT 413 (reaches the handler: 401/415) | cap still 10 MB |
| HC-WRB-616 | L | `main.app`, flag off, `Content-Length` 11 MB → 413; 1 KB body with auth overridden → 404 | cap leaks when off |
| HC-WRB-617 | L | flag on: `PUT /api/v1/wearables/imports/x/review` with 11 MB → 413; `POST /api/v1/documents/import` limit unchanged (51 MB → 413) | `startswith` too wide |
| HC-WRB-618 | L | `sweep_stale_uploads(tmp)` deletes `wearables-*.zip`, leaves other files and subdirs | no sweep |
| HC-WRB-619 | L | `main.lifespan` calls the sweep (patch `init_database`, migrations, sweep recorder; fail-soft if sweep raises) | not wired |
| HC-WRB-620 | R | two same-profile uploads of the same synthetic export fired concurrently (two threads released by one `threading.Barrier`, each with its own `route_client` request): status codes are exactly `{201, 409}`, never 500; profile DB holds one import | second request 500 (`IntegrityError` unhandled) |

Collected count = start + 20. Update the CLAUDE.md and AGENT.md count slots in the same commit (SLOT-RULE).

## 8. Tasks

### Task 0 — gates and re-reads
- [ ] `git fetch origin && git merge-base --is-ancestor <WEAR-01,02,04,05 merge commits> origin/main` — all four. STOP if not.
- [ ] Owner decisions D4 (a) and D6 (b) signed in `owner-decisions-2026-09-27.md` (or its successor). STOP if not. Section 5 diff signed.
- [ ] `ls docs/plans/2026-10-13-wearables-06-import-route.md` present.
- [ ] Read the real names: gated router, parser entry point and its refusal exception, aggregate entry point, `validate_summary`, wearable log function, reserved audit actions and keys. Replace every INFERRED name in this plan's commit message, not by guessing.
- [ ] `git diff --stat` empty on `modules/redaction.py`, `core/auth.py`, `core/security.py`.

### Task 1 — RED
- [ ] Write both test files (section 7). Use the WEAR-04 synthetic-export helper; do not commit binary fixtures.
- [ ] Run: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_import_route.py tests/test_wearables_import_limits.py -p no:cacheprovider -q`
- [ ] Paste the failure output. Expected: every test fails (404/AttributeError/ImportError), none errors at collection for a reason other than the missing symbols.

### Task 2 — GREEN: upload helper and route
- [ ] `modules/wearables/upload.py`: `async stream_body_to_temp(request, tmp_dir, max_bytes) -> (path, sha256_hex, size)`. Loop `request.stream()`, write, update hash, raise `HTTPException(413)` past `max_bytes`. Create `tmp_dir` with `mkdir(parents=True, exist_ok=True)`.
- [ ] `api/wearables.py`: `POST /imports` reads content-type (415), calls the helper, checks empty (400), checks `content_hash` for `profile_id` (409); on `IntegrityError` from the unique `(profile_id, content_hash)` at flush, rolls back, re-reads the existing import and returns the same 409 (Codex plans ADV-5; test HC-WRB-620 fires two same-profile uploads concurrently and expects one 201 and one 409, never 500), runs parser + aggregate in `asyncio.to_thread` (CPU work must not block the loop), calls `validate_summary` (422), builds ORM rows, `profile_db.add_all` + `flush`, then `audit_and_commit(master_db, ...)`, then `profile_db.commit()`. `try/finally` unlinks the temp file. Roll back the profile session on any exception.
- [ ] Add `wearables_max_import_mb: int = 500` to `core/config.py`.
- [ ] Run the route file; HC-WRB-601..612 green.

### Task 3 — GREEN: size cap (OWNER GATE D4)
- [ ] Apply the section 5 diff exactly. Run `tests/test_wearables_import_limits.py` 613-617; then `python -m pytest tests -k "input_validat or security" -p no:cacheprovider -q` to prove the existing middleware tests are untouched.

### Task 4 — GREEN: startup sweep
- [ ] Add `sweep_stale_uploads(tmp_dir)` and call it in `main.py` lifespan before `yield`, in a `try/except Exception: logger.warning(...)` block like `main.py:67-74`. Smallest option chosen: lifespan, not first-route-call, because a lazy sweep needs module state and would not run if the user never imports again. A lifespan sweep runs before any request, so no in-flight upload can be deleted.
- [ ] Run 618-619.

### Task 5 — verify and refactor
- [ ] Full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`. Expected: collected = start + 19; `test_api_rag_index_002b` may fail on embeddings (environmental, CLAUDE.md section 4).
- [ ] Update count slots in CLAUDE.md and AGENT.md. `python3 scripts/docs_lint.py --link-graph`.
- [ ] security-reviewer on the diff (`input_validator.py`, temp-file handling, audit).

## 9. Mutation / break checks (temporary, never committed)

1. Replace the exact-path check in `_limit_for` with `path.startswith(...)` → HC-WRB-617 red. Revert; `git diff` empty.
2. Delete the `finally` unlink → HC-WRB-603/604/609 red.
3. Move `profile_db.commit()` before `audit_and_commit` → HC-WRB-612 red.
4. Drop the `content_hash` lookup → HC-WRB-606 red. Remove the `wearables_enabled` branch in `_limit_for` → HC-WRB-616 red.

## 10. Acceptance criteria (each seen, not asserted)

- RED output pasted (Task 1), then GREEN output for the two files showing 19 passed.
- Full-suite output with collected count = start + 20.
- `git diff --stat origin/main...HEAD` lists only the files in section 3.
- Break checks 1-4 each show the named test failing.
- Owner-signed D4 diff present in the PR description verbatim.

## 11. Rollback

Revert the PR. No migration is added here, so the schema is unchanged. Imported rows from a rolled-back build stay in the profile DB, unreachable (route gone); WEAR-07's delete removes them if the module returns. `app_data_path/tmp/wearables-*` leftovers are harmless plaintext until the next start with the sweep; delete by hand on rollback.

## 12. What these tests cannot see (recurring-failures.md)

- **#10 never started:** `route_client` cannot see a missing mount or the middleware; HC-WRB-613..619 go through `main.app`. A live socket upload of a real 500 MB file is not covered (OW-W2).
- **#1 could not have failed:** isolation is asserted on rows and values, not file names. B's session and A's session share one test DB here, so physical per-profile DB separation is not proven by 610; it is proven by the `profile_id` filter plus A's existing per-profile DB design.
- **#9 invariant at one site:** "temp file always removed" is proven for success, parse refusal and over-cap. A process kill mid-upload is only covered by the sweep (618/619), not by a killed process.
- **#2 next bug one layer over:** audit succeeds, then the profile commit fails → an audit row with no rows. Accepted, logged as a residual; the reverse (rows without audit) is prevented.
- Real Apple exports differ from fixtures (R1, OM-1). The memory ceiling is measured on a synthetic bomb only.

## 13. Owner / model-machine items

OW-W0 (OM-1 notes size the 500 MB placeholder), OW-W2 (200 MB perf smoke), OW-W5 (D4 diff + D6 answers). No model-machine item.
