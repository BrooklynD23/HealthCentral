# Rows 1114 plan: SQLC-LOGIN-ERROR-MAP and TREND-POINT-RANGE

Planner: Opus, 2026-11-14, read-only investigation on origin/main `c60be508`.
Owner instruction (BUILD-1114, verbatim, last line of `~/hc-quiet-logs/plans-1112/owner-answers-1112b.md`):
"Start both and the housekeeping batch. Also ensure that main origin is updated with everything we do not updated yet on local. We will have a senior architect review it on their machine"
MVP presentation ~2026-11-19; product freeze ~2026-11-17.

Origins (both were queue candidate bullets, not rows):
- SQLC-LOGIN-ERROR-MAP: queue.md candidate bullet (2026-11-13 plan, follow-up of SQLCIPHER-WHEEL; `~/hc-quiet-logs/plans-1113/sqlcipher-wheel-plan.md`).
- TREND-POINT-RANGE: queue.md candidate bullet (found 2026-10-25, #362 L0 ruling; measured by BATCH-1111G probe `test_probe_trend_point_carries_own_range` FAILED `assert None == 12.0`, `~/hc-quiet-logs/staging-1111g/probes/`).

File-disjoint: yes. SQLC touches `src/backend/core/auth.py` + one new backend test + `ProfileSetup.test.tsx`; TREND touches `api/observations.py`, `services/types.ts`, `RangeRibbon.tsx`, `ResultsPage.tsx` + tests. No shared file. No open PR (#614, #264, #239) touches any of them; no unfinished queue row lists them. Both can build in parallel.

Licence gate note: `scripts/pr_licence_gate.py` reads the queue and owner-decisions from origin/main. Neither build PR can pass the gate until BATCH-1114B (PR #666, head `9e3b0897`: both rows, owner rows BUILD-1114 for SQLC with `auth.py` and BUILD-1114-TPR for the trend row) is merged. Builders open drafts; the gate is re-run after BATCH-1114B merges.

---

## Row 1: SQLC-LOGIN-ERROR-MAP

### Finding (the candidate bullet named the wrong file)
The candidate says `api/profiles.py` does not catch `ProfileDatabaseEncryptionError`. The real catch is one level down:
- `core/vault_conversion.py` raises `ProfileDatabaseEncryptionError` with one of seven fixed, path-free messages (`FIXED_MESSAGE`, `MSG_UNVERIFIED`, `MSG_RECOVER`, `MSG_PENDING`, `MSG_HELD`, `MSG_BUSY`, `MSG_REPLACE_LOST`, lines 38-60). It already logs step + exception class only.
- `core/profile_database.py:297-301` calls it before the pool lock; the exception propagates unwrapped.
- `core/auth.py:363-403` `open_profile_database_on_login` has `except Exception` → `HTTPException(500, "Failed to open profile database")`. That is the 500 the owner would see. It is the single choke point for all four callers in `api/profiles.py` (create :447, login :523, recover :928, unlock :1283).
- Frontend `pages/ProfileSetup.tsx:239-256` (`handleUnlock`): 401 → "Incorrect password", 429 → wait message, anything else → `err.message` (the `detail`). So the UI already shows whatever `detail` the backend sends. No frontend product change is needed; a vitest pins it.
- `ProfileDatabaseEncryptionError` is also raised by `profile_database.py:366` ("SQLCipher is not available but encryption is required. ... set DATABASE_ENCRYPTION_REQUIRED=false") and `:387` ("Invalid SQLCipher key format"). Those texts must NOT reach the UI (the first one tells a user how to turn encryption off).

### Fix (conservative)
In `core/auth.py` only, add one `except ProfileDatabaseEncryptionError as e:` branch before `except Exception`:
- If `str(e)` is one of the seven `core.vault_conversion` message constants (imported by name, compared by exact equality): `HTTPException(503, detail=str(e))`.
- Otherwise: `HTTPException(503, detail="Encrypted storage could not be opened for this profile. Your data was not changed.")` (fixed text; the raw message goes to the log only).
- Log: `logger.error("Profile vault could not be opened for %s (%s)", profile_id, type(e).__name__)`. No message text, path or key in the new log line (vault_conversion already logs the step).
- Nothing else changes: no retry, no plaintext fallback, no change to conversion, encryption, key handling, or the 401/429 paths. `KeySealingError` and `FileNotFoundError` branches untouched.
- Status 503 (Service Unavailable): the server cannot serve this profile right now; not a client error, not a crash. One status for all cases keeps the branch to a few lines.

Not in scope (recorded as risks): `login` commits `is_locked=False` and the "login" audit row before the vault opens (`api/profiles.py:506-520`), so a failed open leaves a "login" audit row with no session. Pre-existing; a later row may move it.

### Files cell
`src/backend/core/auth.py`, `src/backend/tests/test_sqlc_login_error_map.py`, `src/frontend/src/__tests__/ProfileSetup.test.tsx`

Ask-first cell: `src/backend/core/auth.py` (owner BUILD-1114; Opus security review before the owner merges)

### Test plan (test first)
Backend `src/backend/tests/test_sqlc_login_error_map.py`, HC-SLEM-NNN, all through HTTP with `tests/support/routes.py::route_client(profiles_api.router, "/profiles")` and a real file-backed master DB (`tests/support/master_db.py::make_master_db`, seed like `tests/test_profile_name_unique.py::_seed`). Patch `core.auth.get_profile_db_manager` to return a stub whose `open_profile_database` raises the given error (do NOT patch `open_profile_database_on_login`; the code under test is inside it).
- HC-SLEM-001 (parametrized over all seven vault_conversion constants): POST `/profiles/login` with the right password → 503, `detail` equals the constant exactly.
- HC-SLEM-002: `ProfileDatabaseEncryptionError("SQLCipher is not available but database encryption is required. ... DATABASE_ENCRYPTION_REQUIRED=false ...")` → 503 with the fixed generic text; response body does not contain `DATABASE_ENCRYPTION_REQUIRED`, `SQLCipher`, or `false`.
- HC-SLEM-003: an unknown `ProfileDatabaseEncryptionError("vault at C:\\[redacted]\\vault.db key=ABCD")` → 503 generic; body contains neither `C:\\` nor `ABCD` (non-leak).
- HC-SLEM-004: `RuntimeError("boom")` still → 500 "Failed to open profile database" (unchanged path).
- HC-SLEM-005: wrong password still → 401 "Invalid credentials", and the stub's open is never called.
- HC-SLEM-006: POST `/profiles/{id}/unlock` with a conversion error → 503 same detail (second caller through the same choke point).
- HC-SLEM-007 (log): with `caplog`, the new error line has the profile id and `ProfileDatabaseEncryptionError` and not the message text.
RED: 001-003, 006 fail on main (500). Mutation check: revert the new branch → 001-003, 006 fail; drop the allowlist (pass `str(e)` always) → 002-003 fail.

Frontend `src/frontend/src/__tests__/ProfileSetup.test.tsx`: add one case: login mock rejects with `new ApiError(503, 'Service Unavailable', <MSG_HELD text>)` → the unlock dialog shows that text, not "Incorrect password", and the password field is cleared. (Expected GREEN on main: it pins existing behaviour so a later refactor cannot hide the message.)

### Est h
2

### Risks
- Exact string equality against the constants: if vault_conversion rewords a message, it falls to the generic text (safe direction). HC-SLEM-001 imports the constants, so it follows.
- 503 may be read by some HTTP clients as retryable; the app's react-query `retry: 1` applies to queries, not to `useLogin` (a mutation), so no automatic re-login.
- Touches `core/auth.py` (ask-first, FAIL level in the licence gate): needs the BUILD-1114 owner-decisions row naming `SQLC-LOGIN-ERROR-MAP` and `auth.py` on one line (added by BATCH-1114B).

### Owner acceptance on Windows
1. `dev.bat`, sign in to a real profile with the right password: works as before. Wrong password: "Incorrect password" as before.
2. In the backend venv: `cd src\backend` then `python -m pytest tests\test_sqlc_login_error_map.py -q` → all pass.
3. Optional, throwaway profile only (never a real one): create profile "Plain Test", stop the app, replace `data\vaults\<id>\vault.db` with a plain SQLite file (`python -c "import sqlite3; sqlite3.connect(r'data\vaults\<id>\vault.db').execute('create table t(x)')"`), start `dev.bat`, sign in to "Plain Test": the dialog shows a plain sentence starting "Could not convert this profile to encrypted storage..." (or another fixed sentence), not "Failed to open profile database"; the backend console shows no 500 traceback for that request. Delete "Plain Test" afterwards.

---

## Row 2: TREND-POINT-RANGE

### Finding
- `api/observations.py:215-234` `TrendPoint` has no bounds. `get_analyte_trend` (`:729-860`) builds one series band: the latest emitted observation with both bounds (`ref_source_both`), else the latest low and latest high from possibly different reports (`:842-856`).
- `components/results/RangeRibbon.tsx` judges every point against that series band (`buildLayout` `:216`, `sideOf` `:163`) and says so in its words ("Within the range used for this chart", table header "Against this chart's range", `:69-83`, `:622`). So a January point with its own range 12-16 is judged against March's 13.5-17.5.
- `pages/ResultsPage.tsx:303-305` badge uses `bandOfValue(latest.value, trend.ref_low, trend.ref_high)`.
- Existing tests whose fixtures carry no per-point bounds: `__tests__/ui-range-ribbon.test.tsx`, `__tests__/kept-flag-disagrees.test.tsx`, `__tests__/ui-results.test.tsx`. With optional per-point fields and a fallback, they stay green unchanged.
- `modules/agent/tools/compute_trend.py` has its own `TrendPoint` (chat path); not touched.

### Change (presentational; no new medical wording)
Backend `api/observations.py`:
- `TrendPoint` gains `ref_low: Optional[float] = None`, `ref_high: Optional[float] = None`: this point's own report bounds, in the point's unit.
- In the loop at `:826`: when the point is emitted unconverted, the row's raw `obs.ref_low/ref_high`. When `normalize_units` is on, each bound converted with `convert_to_canonical(analyte_key, bound, obs.unit)`; a bound that does not convert is `None` (never a bound in another unit; unlike the series `_resolve_ref_bound` fallback). Series `ref_low/ref_high` and every other field unchanged.

Frontend:
- `services/types.ts`: `TrendPoint` gains optional `ref_low?: number | null; ref_high?: number | null`.
- `RangeRibbon.tsx`: per point, if the point has its own bound (either finite), `side` is computed against the point's own pair with the existing `sideOf` (flag rules unchanged) and its words say "this report's range" ("Above this report's range", "Below this report's range", "Within this report's range", conflict "The report's flag and its own range disagree"); otherwise the series band and today's words, unchanged. The out-of-range triangle follows the per-point side. Table header: "Against this chart's range" when no visible point has its own range (today's text, so old tests hold), else "Against each report's range". When two or more visible points carry different own ranges, one caption line under the chart: "Reports gave different ranges. Each result is compared with its own report's range; the shaded band is the range this chart uses." The drawn band stays the series band (option a; see open question). Update the header comment (`:7-8`) that says TrendPoint carries no range. `serializeRangeRibbonSvg` follows the drawing as today.
- `ResultsPage.tsx:303-305`: the latest badge uses the latest point's own pair when it has one, else the series pair (one expression; the badge then agrees with the ribbon's readout for the latest point).
- Wording is descriptive only (above/below/within a printed range); no "normal", no advice, no clinical claim. `modules/interpret_safety.py` and `modules/interpret.py` untouched.

### Files cell
`src/backend/api/observations.py`, `src/backend/tests/test_trend_point_range.py`, `src/frontend/src/services/types.ts`, `src/frontend/src/components/results/RangeRibbon.tsx`, `src/frontend/src/pages/ResultsPage.tsx`, `src/frontend/src/__tests__/trend-point-range.test.tsx`, `src/frontend/src/__tests__/ui-results.test.tsx`

Ask-first cell: none

### Test plan (test first)
Backend `src/backend/tests/test_trend_point_range.py`, HC-TPR-NNN, through HTTP: `route_client(observations_router, "/observations", profile_db=<async_sessionmaker>)` (prior art: `tests/test_kept_flag_disagrees.py` and the 1111G probe `~/hc-quiet-logs/staging-1111g/probes/test_zz_probe_1111g_verify.py::test_probe_trend_point_carries_own_range`).
- HC-TPR-001: hemoglobin, two reports 2026-01-05 (12-16, value 15.5) and 2026-03-05 (13.5-17.5, value 14.0) → point0 `ref_low==12.0, ref_high==16.0`, point1 13.5/17.5; series `ref_low/ref_high` still 13.5/17.5 (unchanged).
- HC-TPR-002: a report with no range → that point's bounds `None`; series unaffected.
- HC-TPR-003: one bound only (ref_high only) → point has `ref_low None`, `ref_high` set.
- HC-TPR-004: unit normalization: one report in g/L (120-160, value 150) and one in g/dL → the g/L point's bounds are 12.0/16.0 (canonical g/dL, `modules/normalize.py:48`), its `original_unit` g/L as today.
RED: 001, 003, 004 fail on main (no field). Mutation: emit the series pair on every point → 001 fails.

Frontend `src/frontend/src/__tests__/trend-point-range.test.tsx` (vitest):
- Two points with own ranges 12-16 and 13.5-17.5, values 15.5 and 14.0, series 13.5-17.5: row 1 reads "Within this report's range" (against the series it would also be within; use value 13.0 at point 1 to discriminate: own 12-16 → within, series 13.5-17.5 → below). Header "Against each report's range". Caption present.
- A point with no own range on a series with a band → today's words ("…the range used for this chart").
- Flag H on a point within its own range → conflict words, no triangle.
- No own ranges anywhere → header "Against this chart's range", no caption (today's output).
`src/frontend/src/__tests__/ui-results.test.tsx`: one case: latest point own range 12-16, value 15.5, series band 16-20 → badge is "Normal Range" (own range), not "Outside Range". Badge texts as the page prints them today; check the file for the exact strings.

### Est h
4

### Risks
- Visual: the shaded band (series) and a point's words (own range) can disagree for older points. The caption says so; option (b) below removes it at higher cost.
- The badge change alters which badge shows for the latest value when its own range differs from the series pair. In the common case (latest report has both bounds) the series pair IS the latest point's pair, so nothing changes.
- Doctor summary/export: the ribbon export follows the drawing; no backend export reads `TrendPoint`.
- Medical wording: only "above/below/within this report's range" and one caption; reviewer (Opus, plus Fable advisor per owner 11-11 for UI rows) checks no clinical claim.

### Owner acceptance on Windows
1. `dev.bat`, a profile with two uploaded lab reports for the same analyte whose printed ranges differ (e.g. the demo hemoglobin pair). Results → that analyte's chart:
   - The table header reads "Against each report's range"; each row says Within/Above/Below "this report's range" matching the range printed on that row's own report.
   - The caption "Reports gave different ranges..." shows under the chart.
   - The badge for the latest value matches the latest report's own printed range.
2. An analyte with a single report: the chart reads exactly as before (header "Against this chart's range").
3. No new text gives advice or says "normal" beyond the existing badge.

---

## Open questions for the owner (non-blocking; defaults stand if unanswered)
1. TREND-POINT-RANGE band: (a) keep one shaded band (the range this chart uses) and compare each point with its own report's range in words, with a caption (Recommended, smaller, freeze-safe); (b) draw a stepped band that changes at each report. Default (a).
2. SQLC-LOGIN-ERROR-MAP audit: (a) log line only, no new audit row (Recommended; vault_conversion already logs the failing step, and a new master audit event type is a wider change); (b) add a `profile.vault_open_failed` audit row (needs `db` passed into `open_profile_database_on_login`, touching `api/profiles.py`). Default (a).

---

## Builder brief: SQLC-LOGIN-ERROR-MAP (Sonnet, effort high)

You are implementing queue row SQLC-LOGIN-ERROR-MAP in Asclexis. Read `CLAUDE.md`, `AGENT.md`, and `docs/agentic/recurring-failures.md` first. This touches `src/backend/core/auth.py`, an ask-first auth/encryption file: the owner asked for this row (owner-decisions BUILD-1114, 2026-11-14). Change nothing in it beyond what is below. Never weaken encryption, never retry with plaintext, never put a path, key or raw exception text in an HTTP response.

Setup:
```
cd "/mnt/e/Programming/Github Repo/HealthCentral" && git fetch origin
git worktree add ~/wt/hc-sqlc-login-error-map -b fix/sqlc-login-error-map origin/main
cd ~/wt/hc-sqlc-login-error-map
```
Never edit `/mnt/e/Programming/Github Repo/HealthCentral` itself.

Files you may touch (exactly): `src/backend/core/auth.py`, `src/backend/tests/test_sqlc_login_error_map.py` (new), `src/frontend/src/__tests__/ProfileSetup.test.tsx`.

Context: `core/vault_conversion.py:38-60` defines seven fixed user-safe messages (`FIXED_MESSAGE`, `MSG_UNVERIFIED`, `MSG_RECOVER`, `MSG_PENDING`, `MSG_HELD`, `MSG_BUSY`, `MSG_REPLACE_LOST`) raised as `core.profile_database.ProfileDatabaseEncryptionError`. `core/auth.py:363-403` `open_profile_database_on_login` turns every non-KeySealing, non-FileNotFound exception into 500 "Failed to open profile database". `ProfileDatabaseEncryptionError` is also raised by `core/profile_database.py:366` and `:387` with texts that must not reach a user.

Steps (test first):
1. Write `src/backend/tests/test_sqlc_login_error_map.py` with HC-SLEM-001..007 exactly as in "Row 1 → Test plan" of `~/hc-quiet-logs/plans-1114/rows-1114-plan.md`. Use `tests/support/routes.py::route_client(profiles_api.router, "/profiles")`, `tests/support/master_db.py::make_master_db` and a `_seed` like `tests/test_profile_name_unique.py` (real `hash_password`). Override the master DB the way that file does (`use_master` / `master_db=`); read it. Monkeypatch `core.auth.get_profile_db_manager` to a stub whose async `open_profile_database(profile_id, password)` raises the parametrized error. Reset `profiles_api.auth_rate_limiter` for `login:testclient` in the fixture.
2. Run it; record the RED output (001-003, 006 fail with 500).
3. In `core/auth.py`: import `ProfileDatabaseEncryptionError` (from `.profile_database`, check how auth.py already imports from it) and the seven constants from `.vault_conversion`; build a module-level `frozenset` of them. Add, before `except Exception`, an `except ProfileDatabaseEncryptionError as e:` branch: log `logger.error("Profile vault could not be opened for %s (%s)", profile_id, type(e).__name__)`; raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e) if str(e) in <set> else "Encrypted storage could not be opened for this profile. Your data was not changed.")` with `from None`. Update the docstring's Raises section. Nothing else.
4. GREEN. Mutation checks (revert after each, report results): remove the new branch → which tests fail; replace the allowlist with `detail=str(e)` → HC-SLEM-002/003 must fail.
5. Add the frontend case to `ProfileSetup.test.tsx` (503 + MSG_HELD text → dialog shows the text, not "Incorrect password", password cleared). Follow the file's existing login-mock pattern.

Verification (paste the real output in the PR body):
```
cd src/backend && bash ../../scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_sqlc_login_error_map.py tests/test_vault_conversion.py tests/test_profile_name_unique.py tests/test_profile_recovery.py tests/test_notification_scheduler_wiring.py -q -p no:cacheprovider
cd src/backend && bash ../../scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest -q -p no:cacheprovider --co | tail -1   # collected count; report delta vs 5114
cd src/frontend && npx vitest run src/__tests__/ProfileSetup.test.tsx && npx tsc --noEmit
python3 scripts/pr_licence_gate.py --title "fix(auth): map a failed vault conversion at login to a clear 503 (SQLC-LOGIN-ERROR-MAP)" --base origin/main --head HEAD --ref origin/main
```
The licence gate reads the queue from origin/main; until BATCH-1114B merges it will FAIL with no-queue-id/outside-licence/ask-first. Report that output as-is; do not work around it.
No Playwright. Commit (`fix(auth): ...`, end with `Co-Authored-By: Claude Sonnet 5.5 <[redacted]>`), push, open a DRAFT PR titled `fix(auth): map a failed vault conversion at login to a clear 503 (SQLC-LOGIN-ERROR-MAP)`, body: what changed, RED and GREEN output, mutation results, collected count + delta, gate output, the Windows acceptance steps from the plan, and "Needs: Opus security review, then owner merge". Do not merge, do not mark ready.

## Builder brief: TREND-POINT-RANGE (Sonnet, effort high)

You are implementing queue row TREND-POINT-RANGE in Asclexis. Read `CLAUDE.md`, `AGENT.md`, and `docs/agentic/recurring-failures.md` first. This is presentational: a trend point carries its own report's reference range and the chart words say which range a point is compared with. Do not touch `modules/interpret_safety.py`, `modules/interpret.py`, or `modules/agent/`. Add no wording that gives advice or calls a value "normal" (the existing badge text is not yours to change).

Setup:
```
cd "/mnt/e/Programming/Github Repo/HealthCentral" && git fetch origin
git worktree add ~/wt/hc-trend-point-range -b feat/trend-point-range origin/main
cd ~/wt/hc-trend-point-range && (cd src/frontend && npm ci)
```
Never edit `/mnt/e/Programming/Github Repo/HealthCentral` itself.

Files you may touch (exactly): `src/backend/api/observations.py`, `src/backend/tests/test_trend_point_range.py` (new), `src/frontend/src/services/types.ts`, `src/frontend/src/components/results/RangeRibbon.tsx`, `src/frontend/src/pages/ResultsPage.tsx`, `src/frontend/src/__tests__/trend-point-range.test.tsx` (new), `src/frontend/src/__tests__/ui-results.test.tsx`.

Spec: "Row 2 → Change" and "Row 2 → Test plan" in `~/hc-quiet-logs/plans-1114/rows-1114-plan.md`. Summary:
- Backend `TrendPoint` gains `ref_low`/`ref_high` (Optional[float], default None) = the row's own bounds; under unit normalization each bound is converted with `convert_to_canonical(analyte_key, bound, obs.unit)` and a bound that does not convert is None. Series fields unchanged.
- `types.ts` optional `ref_low?`/`ref_high?: number | null`.
- `RangeRibbon.tsx`: per point, own pair if either own bound is finite, else the series pair; words "…this report's range" for own, today's words for series; triangle follows the side; header "Against each report's range" only when some visible point has its own range, else unchanged; caption "Reports gave different ranges. Each result is compared with its own report's range; the shaded band is the range this chart uses." when two or more visible points have differing own ranges; band drawing unchanged; fix the header comment at `:7-8`.
- `ResultsPage.tsx:303-305`: the badge uses the latest point's own pair when it has one, else the series pair.

Steps (test first):
1. Backend test HC-TPR-001..004 through HTTP: `route_client(observations_router, "/observations", profile_db=...)`; copy the seeding pattern from `tests/test_kept_flag_disagrees.py` and `~/hc-quiet-logs/staging-1111g/probes/test_zz_probe_1111g_verify.py::test_probe_trend_point_carries_own_range`. RED, then implement, GREEN. Mutation: emit the series pair on every point → HC-TPR-001 must fail; report it.
2. Frontend vitest `trend-point-range.test.tsx` (cases in the plan) and the `ui-results.test.tsx` badge case: RED first, then implement, GREEN. Read the existing `ui-range-ribbon.test.tsx` and `kept-flag-disagrees.test.tsx` and keep them passing unchanged (do not edit them; if one fails, your fallback is wrong).

Verification (paste the real output in the PR body):
```
cd src/backend && bash ../../scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_trend_point_range.py tests/test_kept_flag_disagrees.py tests/test_unit_conversion.py tests/test_verified_only_consumers.py tests/test_audit_view_analyte.py tests/test_utc_sweep_http.py -q -p no:cacheprovider
cd src/backend && bash ../../scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest -q -p no:cacheprovider --co | tail -1   # collected count; report delta vs 5114
cd src/frontend && npx vitest run src/__tests__/trend-point-range.test.tsx src/__tests__/ui-range-ribbon.test.tsx src/__tests__/kept-flag-disagrees.test.tsx src/__tests__/ui-results.test.tsx src/__tests__/safety-mode-verified.test.tsx && npx tsc --noEmit && npx vitest run
python3 scripts/pr_licence_gate.py --title "feat(results): each trend point is compared with its own report's range (TREND-POINT-RANGE)" --base origin/main --head HEAD --ref origin/main
```
The licence gate reads the queue from origin/main; until BATCH-1114B merges it will FAIL with no-queue-id/outside-licence. Report that output as-is.
No Playwright from this agent (CI E2E covers it; if L0 wants a local Playwright run, one named agent does it later). Commit (`feat(results): ...`, end with `Co-Authored-By: Claude Sonnet 5.5 <[redacted]>`), push, open a DRAFT PR titled `feat(results): each trend point is compared with its own report's range (TREND-POINT-RANGE)`, body: what changed, RED and GREEN output, mutation result, collected count + delta, gate output, the Windows acceptance steps from the plan, and "Needs: Opus review (wording + Fable advisor per owner 11-11), owner Windows check". Do not merge, do not mark ready.
