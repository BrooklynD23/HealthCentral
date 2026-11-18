# Plans for FE-401-MOCKS, TEST-PLACEHOLDERS, PYSLOT-LOCK-GUARD, RANGE-ORDER, VERIFY-NONFINITE and TIMELINE-VERIFY-INVALIDATE

**Last Updated:** 2026-11-07 (Opus planner on `9ab89972`, docs batch BATCH-1107B: six candidate rows that said "needs planning detail", planned for runtime `codex` under the owner's chat direction QUIET-PARALLEL-1107)
**Owner:** repository owner
**Status:** PLANNED (Opus planner). Docs only. All owner gates answered 2026-11-07: RANGE-ORDER-STORE = option 1 (swap bounds, keep printed text); RANGE-ORDER-STORE-VERIFY = reject 400 for a patient-typed inverted pair, folded into VERIFY-NONFINITE's `api/observations.py` scope (keeps RANGE-ORDER modules-only and disjoint from VERIFY-NONFINITE).
**Base measured:** `origin/main` @ `9ab89972` (2026-11-07, #534 merged). Every `file:line` below was re-read on this docs worktree at `da1a5836`, which is `9ab89972` plus docs-only commits `fd9ed99d` and `da1a5836` (`git diff --name-only 9ab89972..HEAD` lists no `src/` file — product and test code is exactly main). Two read-only probes ran against the worktree's own `src/backend` (`~/venvs/asclexis-311/bin/python`, import + parse only, nothing written); their output is pasted under RANGE-ORDER and VERIFY-NONFINITE.
**Refresh Trigger:** a merge that edits `src/frontend/src/__tests__/api.test.ts`, `src/frontend/src/__tests__/ExplainAssistant.test.tsx`, `src/backend/tests/test_ocr_bbox.py`, `src/backend/tests/test_extraction_pipeline.py`, `scripts/pyslot.sh`, `src/backend/modules/extract.py`, `src/backend/modules/import_structured.py`, `src/backend/tests/test_extract_properties.py`, `src/backend/tests/test_structured_import.py`, `src/backend/api/observations.py`, `src/frontend/src/services/observations.ts`, `src/frontend/src/services/medications.ts` or `src/frontend/src/services/timeline.ts`; an owner answer to RANGE-ORDER-STORE; #535, #537 or #538 leaving the open-PR list; any of the three ready BATCH-1107A rows landing.

Queue rows: [queue.md, "Planned 2026-11-01, harness speedup"](2026-10-15-build-program/queue.md#planned-2026-11-01-harness-speedup) (the six rows sit at the end of that table; promoted from the candidate-pool bullets `RANGE-ORDER` :555, `TEST-PLACEHOLDERS` :563, `VERIFY-NONFINITE` :690, `PYSLOT-LOCK-GUARD` :723, `FE-401-MOCKS` :743, `TIMELINE-VERIFY-INVALIDATE` :769 on the #539 head, folded into the status cells on promotion). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md) (§10.1 planner checklist, §10.2 Codex CLI), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue (`fe/` = `src/frontend/src`, `be/` = `src/backend`).

**Rules that hold for every row here.**
- **Runtime `codex`** (owner chat 2026-11-07, QUIET-PARALLEL-1107). Codex implements; the review is a Claude Code Opus session (RUNBOOK §1 rule 2), with the lens each row names.
- No row lowers a threshold, relaxes a guard or weakens an assertion to pass. A test named as "must change" changes only as written; any other RED test stops the build for L0 with its ids.
- Route tests go through `tests/support/routes.py::route_client` — never a direct handler call for anything asserting auth, path scoping or status codes (recurring-failures §1).
- Backend pytest always runs as: `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest <files> -p no:cacheprovider -q`. **Collected-count baseline: 4661** (measured on `origin/main` `9ab89972` under pyslot, queue Last Updated 2026-11-07). Each build reports its measured count and delta.
- Frontend acceptance: `cd src/frontend && npx vitest run <files>` then `npx tsc --noEmit`. `node_modules` exists in the build worktrees.
- `git diff --name-only origin/main...HEAD` must print exactly the row's file list.
- **Open PRs checked 2026-11-07** (`gh pr diff <n> --name-only`): #538 SAFETY-MODE-VERIFIED-FE (`fe/pages/ResultsPage.tsx`, `fe/components/results/RangeRibbon.tsx`, `fe/components/results/SafetyModeToggle.tsx` note text, `fe/__tests__/safety-mode-toggle.test.tsx`, `safety-mode-verified.test.tsx`, `e2e/safety-mode.spec.ts`); #537 C-GC1 (`be/api/export.py`, `be/api/pinboards.py`, `be/api/profiles.py`, profile migration `019`, `be/models/export_artifact.py`, `be/models/__init__.py`, `be/tests/support/migrations.py`, `be/tests/test_audit_order_guard.py`, `test_denial_audit.py`, `test_export_redaction.py`, `test_visit_prep_packet.py`, `test_export_artifact_persistence.py`, `test_fk_migration_017.py`); #535 UI-PG-SECURITY (`e2e/support/gates.ts`, `e2e/ui-gates-sampler.spec.ts`, `e2e/ui-security.spec.ts`, `BackupCard`/`DangerZone`/`RecoveryCodeCard`/`SecuritySection` tsx, `ui-security.test.tsx`, `BackupRestoreFlow.test.tsx`). Plus the three ready BATCH-1107A rows ([plan](2026-11-07-three-rows-plan.md)): DELETED-DOC-NAMES-TIMELINE (`fe/services/documents.ts` + `fe/__tests__/deleted-doc-names-timeline.test.tsx`), PANEL-WITHHELD-FIRSTGEN (`be/modules/interpret.py` + `be/api/interpretations.py` + `be/tests/test_value_range_compare.py`), OCR-COPY-ENGINE (`fe/pages/DocumentInbox.tsx`, `fe/pages/VerificationWorkbench.tsx`, `fe/pages/settings/AdvancedSection.tsx`, `be/api/model_settings.py`, `be/modules/environment_diagnostics.py`, `config/.env.example`, `dev.sh`, `fe/__tests__/ocr-copy-engine.test.tsx`, `be/tests/test_ocr_copy_engine.py`).
- **RED runs.** The two read-only probes below already ran on the worktree. Every other RED output is pasted by the build; where a row is honestly GREEN on main (the production code is already right), the section says so and names the mutation-RED the build must paste instead.

---

## FE-401-MOCKS

**Source:** queue.md `:743` (found 2026-11-06, after SESSION-REENTRY Task 2 merged as #505 `a821078d`, head `2d430b13` — in the base): "two frontend tests still mock the missing-profile-connection error as 403, which the backend no longer sends". Kind: TEST (mock accuracy; no production change). Lens: —.

**Facts (re-read on `9ab89972`).**
- `be/core/auth.py:305-311`: a missing profile connection raises `HTTP_401_UNAUTHORIZED`, detail `"Profile database not available. Please log in again."`. Before `2d430b13` (SESSION-REENTRY Task 2, owner answer SESSION-AUTH-DIFF "Change to 401") this was a 403 — the two mocks date from then. The backend still sends real 403s elsewhere: `Access denied to this profile` (`be/core/auth.py:286`, audited denial) and the synthetic-reset guard (`be/api/profiles.py:589`).
- Every `403` under `src/frontend` (grep, `*.ts`/`*.tsx`, and `e2e/`):
  - `fe/__tests__/api.test.ts:246-265` — `it('should handle 403 for locked profile database')`: mocks `status: 403` (`:255`) with the locked-db detail and asserts `rejects.toMatchObject({ status: 403, ... })` (`:262`). **This test asserts 403-specific behavior** — mock and assertion move together.
  - `fe/__tests__/ExplainAssistant.test.tsx:391-399` — `it('HC-FEE-001: a real 403 ApiError shows the session-expired message')`: mocks `new api.ApiError(403, 'Forbidden', 'Profile database not available. Please log in again.')` (`:393`).
  - `fe/__tests__/ui-documents.test.tsx:1356` — parametrized `[403, 'Access denied']` on the generic list-failure card. **Legitimate, stays**: it pins the generic-403 UI contract, not the locked-profile case, and 403 remains a real backend status.
  - Product code (all stays): `fe/services/api.ts:63-71` (`handleAuthError`: 401 clears auth + redirects; "403 is kept - profile database locked, but token may still be valid" — still true for genuine denials), `fe/pages/ExplainAssistant.tsx:632` (`error.status === 401 || error.status === 403` → session-expired copy), `fe/pages/DocumentInbox.tsx:381-395` (401/403-specific copy).
  - `e2e/`: comments only (`session-lock-now.spec.ts:9,67`, `ui-auth.spec.ts:986`); no 403 mocks.
- `handleAuthError(401)` (`fe/services/api.ts:65-69`) calls `clearAuth()` then `redirectToSessionRecovery()` → `window.location.replace(origin + '/setup')` unless already on `/setup` (`:56-60`). The file already has `stubLocationReplace()` (`api.test.ts:17-29`) for the MVP-REAUTH-401 block.
- `backup.ts:188-190` comment "every subsequent call 403s" is stale since `2d430b13` (that path is now a 401). A comment; **not in this row**.

**Fix.** Two test edits, nothing else.

1. `fe/__tests__/api.test.ts` `:246-265` — retitle to `should handle 401 for locked profile database`; mock `status: 401, statusText: 'Unauthorized'` with the same detail body; wrap with `stubLocationReplace()`; assert `rejects.toMatchObject({ status: 401, message: expect.stringContaining('Profile database not available') })`, `useAuthStore` token `null` and `isAuthenticated` `false`, and `loc.replace` called once with `http://localhost:3000/setup`. Add one companion `it` (pin, name it `HC-FEM-002` in the same `FE-AUTH-006` describe): a fetch `403` with detail `"Access denied to this profile"` rejects `{ status: 403 }`, the token survives and `replace` is not called — the surviving half of `handleAuthError`'s contract, which the retitled test vacates.
2. `fe/__tests__/ExplainAssistant.test.tsx` `:391-399` — HC-FEE-001 retitled `a real 401 ApiError shows the session-expired message`; mock `new api.ApiError(401, 'Unauthorized', 'Profile database not available. Please log in again.')`; the `/session has expired/` assertion is unchanged (`ExplainAssistant.tsx:632` handles `401 || 403`). Add `HC-FEE-001b` (pin): a real `ApiError(403, 'Forbidden', 'Access denied to this profile')` shows the same session-expired message — keeps the 403 half of `:632` exercised after the mock moves to 401.

**Honest note — GREEN on `main`.** Nothing goes RED: the production code is already correct; only the mocks lag the backend. The build must instead paste a **mutation-RED**: (a) drop `error.status === 401 ||` from `ExplainAssistant.tsx:632` → HC-FEE-001 fails; (b) make `handleAuthError` treat 401 like 403 (comment out the `status === 401` branch, `api.ts:66-69`) → the updated `api.test.ts` case fails (session kept). Then revert.

**Files:** `fe/__tests__/api.test.ts` (`:246-265` + the added `it`), `fe/__tests__/ExplainAssistant.test.tsx` (`:391-399` + the added `it`). Nothing else.

**Tests that must stay unedited:** `ui-documents.test.tsx` (including the `[403, 'Access denied']` case at `:1356`), every other test in the two edited files, `MedicationCorrelations.test.tsx`, `TimelineService.test.tsx`, all e2e specs.

**Acceptance.**
- `cd src/frontend && npx vitest run src/__tests__/api.test.ts src/__tests__/ExplainAssistant.test.tsx src/__tests__/ui-documents.test.tsx`, then `npx tsc --noEmit`. Both mutation-RED pastes and the GREEN run.
- `git diff --name-only origin/main...HEAD` prints the two files.
- No quiet box: no rendering change.

**Never beside:** nothing open — both files are disjoint from #535, #537, #538 and all three ready BATCH-1107A rows.

**Not in this row:** the stale `backup.ts:189` comment; whether a genuine 403 "Access denied" should show session-expired copy in `ExplainAssistant.tsx:632` (current behavior, pinned by HC-FEE-001b — a product question for L0, not this row).

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review).

---

## TEST-PLACEHOLDERS

**Source:** queue.md `:563` (review-round candidate): "`tests/test_ocr_bbox.py:141-145` (`assert True`), `tests/test_extraction_pipeline.py:112-122` (`pass`)". Kind: TEST (fill placeholders with real assertions). Lens: —.

**Facts (re-read on `9ab89972`).**
- `be/tests/test_ocr_bbox.py:142-145` — `TestPageImageEndpoint.test_page_number_must_be_positive` is `assert True  # Placeholder; full integration test requires TestClient + fixtures`. The code it names: `GET /documents/{document_id}/pages/{page_number}/image` (`be/api/documents.py:1743`), which validates `document_id` (`:1756`), fetches the document (`:1758-1765`), checks access (`:1767`), then rejects `page_number < 1` with 400 `"Page number must be >= 1"` (`:1769-1773`) — before render, before the audit write (`:1830-1838`). A non-integer `page_number` is a FastAPI path-param coercion failure → 422. **Already correct on `main`.**
- `be/tests/test_extraction_pipeline.py:113-121` — `test_api_import_003_document_status_set_to_parsed` is `pass  # Integration test will cover this`. The code it names: `_run_extraction_pipeline` (`be/api/documents.py:577`) sets `document.status = "parsed"` + `parsed_at = utcnow()` + `verified_at = None` (`:688-690`) after observations are persisted. For `doc_type="lab_pdf"` it calls `extract_module.extract_from_pdf` (`:610-613`), then `observation_range_status` per row and `_compute_needs_verification` (`:687`, `:928-940`). **Already correct on `main`.** Route-level proof also already exists: `test_hc_isp_002` asserts `body["document"]["status"] == "parsed"` over HTTP (`test_documents_api.py:1386-1388`) — the placeholder's "requires TestClient + fixtures" comment is stale.

**Honest note — GREEN on `main`.** Both fills assert behavior that exists today. RED-then-GREEN is not possible; the build pastes a **mutation-RED** for each: (a) flip `documents.py:1769` to `page_number < 0` → the page-number test fails (a 0 page reaches the render path, not 400); (b) change `documents.py:688` to `status = "imported"` → the import-status test fails. Then revert.

**Fill 1 — `test_page_number_must_be_positive`** (status codes → HTTP per the route rule; the file's direct-call style at `:208`/`:266` is legacy, not precedent to extend). Mount `route_client(documents_router, "/documents")`; seed one `Document` (id a valid UUID, `profile_id="profile-a"`, `path_hash`/`content_hash` 64-char strings, `doc_type="lab_pdf"`, `status="parsed"`, `imported_at` set) in an in-memory profile DB (`create_async_engine("sqlite+aiosqlite://")` + `ProfileDatabaseBase.metadata.create_all` — the `entity_profile_db` pattern of `test_documents_api.py:549-561`, recreated as a small local fixture); override `get_profile_db_session` as `test_verify_keeps_flag.py::_get` does. GET `…/pages/0/image` → **400** with the `"Page number must be >= 1"` detail; `…/pages/-1/image` → 400; `…/pages/abc/image` → **422** (coercion, free pin); the AsyncMock master DB records **no commit** on the rejected calls (audit lands after render only — the fail-closed pin `test_ocr_bbox.py:268` already asserts for 404).

**Fill 2 — `test_api_import_003_document_status_set_to_parsed`** (a module-internal async function, not a route — the HTTP rule does not apply; the status under test is the `documents.status` column). `monkeypatch` `documents_api.ExtractModule` to a stub whose `extract_from_pdf` returns `ExtractionResult(document_id=document.id, observations=[<one real ExtractedObservation with Provenance>]`, `extracted_text="t")`; `get_decrypted_document` → `io.BytesIO(b"%PDF")`; `_create_chunks_and_embeddings` → `AsyncMock(return_value=0)` — the `_EmptyExtract`/`FK_020` mock set (`test_documents_api.py:1407-1414`). `profile_db` is an `AsyncMock` whose `execute` returns a result with `scalar_one_or_none() -> None` (the `UserModelSettings` read at `:585-588`; `user_ocr_preference_enabled(None)` → `False`, `compute_ocr_effective(False)` → `(False, blockers)` — fine for `lab_pdf`, the OCR branch at `:592` is not taken). `document` is a real `Document` (`doc_type="lab_pdf"`, `status="imported"`). Assert: `document.status == "parsed"`, `document.parsed_at is not None`, `document.verified_at is None`, `out["observations_extracted"] == 1`, and `out["needs_verification"]` equals `_compute_needs_verification` on the stubbed observations.

**Files:** `be/tests/test_ocr_bbox.py` (`:142-145` body fill + the local fixture it needs), `be/tests/test_extraction_pipeline.py` (`:113-121` body fill + its imports/mocks). Nothing else.

**Tests that must stay unedited:** `test_documents_api.py` (`test_hc_isp_002` already proves the route-level status); the rest of `test_ocr_bbox.py` (including the two direct-call page tests — do not "upgrade" them); the rest of `test_extraction_pipeline.py`.

**Acceptance.**
- `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_ocr_bbox.py tests/test_extraction_pipeline.py tests/test_documents_api.py -p no:cacheprovider -q`, with both mutation-RED pastes and the GREEN run.
- The full backend suite (RUNBOOK §6 step 2) and the collected count with its delta against 4661.
- `git diff --name-only origin/main...HEAD` prints the two files.

**Never beside:** nothing open. Same file (`test_extraction_pipeline.py`) as RANGE-ORDER's HC-EXF-007 additions if both build in one batch — disjoint hunks; the second lander rebases (contracts §b rule 2).

**Not in this row:** the commented-out assertions at `test_extraction_pipeline.py:361-362`, `:372`, `:386` ("After implementation:" blocks) — same disease, not named by the candidate; a follow-up for L0. `test_page_image_uses_in_process_cache`/`test_page_image_out_of_range_does_not_audit`'s direct-call style (working; migration to `route_client` is a separate hygiene row).

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review).

---

## PYSLOT-LOCK-GUARD

**Source:** queue.md `:723` (found 2026-11-04): "#490 (`431fbf52`, in `git log`) added `-o` to the `flock` call at `scripts/pyslot.sh:9`, but no committed check guards it; the row's acceptance was a pasted two-line test, so a later edit that drops `-o` fails nothing." PYSLOT-LOCK-LEAK itself is done (queue.md `:956`, #490 merged `431fbf52`, 2026-11-04). Kind: TEST (committed guard for a merged fix). Lens: harness.

**Facts (re-read on `9ab89972`).** `scripts/pyslot.sh:9` is `flock -o -n -E 75 "/tmp/claude-1000/hc-pytest.$i.lock" "$@"` — `-o` is util-linux `--close`: a child the command leaves behind stops holding the slot fd (the #490 leak: a vite server held slot 2 for ~4 h). Non-75 exits pass through (`rc=$?; [ "$rc" -ne 75 ] && exit "$rc"`, `:10-11`); a full busy pass waits `sleep 5` (`:13`). `git ls-files --eol scripts/pyslot.sh` → `i/lf w/lf` — **LF endings must be preserved** (the script is not edited anyway). The batch's recorded acceptance (`/tmp/claude-1000/pyslot-lock-leak-accept.sh`, section A — the "two-line test" the row names):

    PYSLOTS=1 "$S" bash -c "sleep 20 >/dev/null 2>&1 & exit 0"; echo script=$?
    flock -n -E 75 "$L" true; echo probe=$?          # RED: probe=75 (leak); GREEN: probe=0

Its §B/§C/§D record the other pins: `pyslot.sh true`→0, `false`→1; a busy slot waits and retries on 75; the lock IS held while the command runs (`during=75`, `after=0`).

**Fix.** `scripts/pyslot.sh` is **not edited** — the guard is a new committed test file. `be/tests/test_pyslot_lock_guard.py` (new, HC-PSG-001…005). Every functional case copies the real script into `tmp_path` and rewrites its `/tmp/claude-1000` path to the scratch dir — the batch's own approach ("a scratch copy of the script on `d1f05349` with its lock path moved") — so the box's real pytest slots are never touched and the real script is never mutated. `REPO_ROOT` resolution follows `test_ocr_rapid.py:951` (`_DEV_SH = REPO_ROOT / "dev.sh"`); platform gating follows `:1004`: `pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None or shutil.which("flock") is None, reason="needs bash+flock")` on the functional cases.

- **HC-PSG-001 (static pin).** The script's `flock` invocation, tokenized, includes standalone `-o`, `-n` and `-E 75`. (Tokens, not a literal substring — flag order may change; the guard is on the flags' presence.) RED the day `-o` is dropped.
- **HC-PSG-002 (self-proving pair).** Two scratch copies: `good` verbatim (lock path moved) and `bad`, which the test itself de-`-o`s (assert the edit applied). For each: `PYSLOTS=1 <copy> bash -c 'sleep 30 & echo $! > child.pid; exit 0'` → `script=0`, then `flock -n -E 75 <lock> true` → `good` probe **0**, `bad` probe **75**. The `bad` half is the built-in RED proof that the guard sees the regression — no separate mutation run needed. Teardown kills `child.pid`.
- **HC-PSG-003 (anti-vacuous).** `PYSLOTS=1 good sleep 4` in background; probe during → **75** (a "fix" that dropped locking entirely would pass HC-PSG-002 vacuously), after → 0.
- **HC-PSG-004 (passthrough + retry).** `scratch true` → 0; `scratch false` → 1. Hold the scratch lock (`flock "$L" sleep 2 &`), then `PYSLOTS=1 scratch bash -c 'exit 3'` → first pass 75, retry, `rc=3`. The scratch copy may shorten `sleep 5`→`sleep 1` — stated plainly in the test: the retry *interval* is not the pinned property; the 75-loop mechanism is.
- **HC-PSG-005 (LF pin).** `scripts/pyslot.sh` bytes contain no `\r` — a CRLF conversion fails this anywhere, no bash needed.

**Files:** `be/tests/test_pyslot_lock_guard.py` (new). **Nothing else** — `pyslot.sh` is untouched.

**Tests that must stay unedited:** none overlap; the file is new.

**Acceptance.**
- `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_pyslot_lock_guard.py -p no:cacheprovider -q` — HC-PSG-002 prints its `bad`-copy 75 as the RED proof in the run output/log.
- The full backend suite and the collected count with its delta against 4661 (+5 → 4666 expected).
- `git diff --name-only origin/main...HEAD` prints the one file.
- `git ls-files --eol scripts/pyslot.sh` still `i/lf w/lf` (untouched, but checked).

**Never beside:** nothing open — no PR touches `scripts/pyslot.sh` or owns this test name.

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review).

---

## RANGE-ORDER

**Source:** queue.md `:555` (review round 1 of HYPOTHESIS-EXTRACT, #327 `fe9581f`): "`_parse_text_line('Glucose 105 mg/dL 99-70', 1)` stores `ref_low=99, ref_high=70` (also the colon form); a reversed range should be swapped or rejected, never stored inverted. Its property test was dropped from HYPOTHESIS-EXTRACT until this lands" — `test_extract_properties.py:3-4` records the drop ("They do not assert ref_low <= ref_high (RANGE-ORDER is a known open bug)"). Kind: PRODUCT (backend; stored lab data). Lens: medical safety. **Owner question: RANGE-ORDER-STORE** — answered 2026-11-07 (below; option 1 + reject 400 on /verify).

**Facts (re-read on `9ab89972`, probe pasted).**

    'Glucose 105 mg/dL 99-70'   -> (99.0, 70.0, 105.0, "'99-70'")   # column form
    'Glucose: 105 mg/dL (99-70)' -> (99.0, 70.0, 105.0, "'99-70'")  # colon form
    'Glucose 105 mg/dL (99-70)' -> (99.0, 70.0, 105.0, "'99-70'")   # alt form
    table ['Glucose','105','mg/dL','99-70'] -> [(99.0, 70.0, "'99-70'")]

- All `ExtractedObservation` producers invert alike: `_parse_text_line` reads `ref_low`/`ref_high` groups (`extract.py:785-786`) into floats (`:822-837`) and stores them at `:855-856`; `_parse_table_row` reads `RANGE_PATTERN` group(1)→`ref_low`, group(2)→`ref_high` (`:630-634` → `:665-666`). Verified: no module outside `extract.py` constructs `ExtractedObservation`; `extract_imaging`/`extract_pathology`/`extract_visit_notes` never set range fields.
- Structured imports admit the same inversion: `parse_lab_csv` `ref_low`/`ref_high` columns verbatim (`import_structured.py:188-189` via `_parse_float`, `:62-71`); `parse_fhir_bundle` `referenceRange[0].low/high` verbatim (`:247-263` → `:281-282`).
- Why it is a bug: `observation_range_status` (`api/observations.py:87-122`) checks low first (`value < ref_low` → "below", else `value > ref_high` → "above"). With `ref_low > ref_high` no value can be inside — every value lands out and `status_is_abnormal` stores `is_abnormal=True` (persistence: `api/documents.py:657-668` for the text path, `:771-782` for structured). The probe's glucose-105 against "99-70" stores *abnormal*.
- `ref_range_text` keeps the printed order by construction (`extract.py:857-858` rebuilds from the raw strings; the table path stores the raw cell `:667`) — "99-70" survives verbatim in the stored row; the provenance snippet keeps the raw line. The inversion is always auditable.
- Reader pins for inverted input exist and **stay**: HC-VRC-001 `:319` (`(85.0, HI, LO, "below")`) and HC-VRC-015 `:1121` — legacy stored rows and patient-typed bounds can still be inverted; the readers' low-first contract is unchanged by any option.

### Owner question: RANGE-ORDER-STORE — **answered 2026-11-07: option 1 (swap; keep printed text)**. Sub-question (b) answered **reject 400**, and by the same answer it rides VERIFY-NONFINITE's `api/observations.py` file — RANGE-ORDER stays modules-only.

> A lab report that prints a reference range backwards ("Glucose 105 mg/dL 99-70") is stored as `ref_low=99, ref_high=70`. Low is checked before high, so a value can never be inside an inverted range: every such value is stored **abnormal** (105 against "99-70" reads "above"). What should extraction and structured import do with an inverted range?

1. **Swap the bounds; keep the printed text (Recommended).** Store `ref_low=70, ref_high=99`; `ref_range_text` keeps "99-70" verbatim and the provenance snippet keeps the raw line, so the swap is auditable against what was printed. The value then range-compares correctly (105 → "above" for a *true* reason only when the lab meant a bound; under the honest reading of "99-70" as a misordered "70-99", 105 → "above" abnormal — same flag, right reason). Every such observation already lands in the review queue (`user_verified=False`), so the patient confirms the corrected range on /verify — the flag-for-review marker is the queue itself. Same rule for CSV `ref low`/`ref high` columns and FHIR `referenceRange`, which admit the same inversion.
2. **Drop the inverted range.** Keep value, unit and flag; store `ref_low=None, ref_high=None`; `ref_range_text` keeps "99-70". Invents nothing — but a probably-real range is lost, and the value cannot be range-compared (stays `keep`/stored-flag) until the patient re-enters bounds on /verify.
3. **Keep today's storage (report only).** The inverted pair stays; every such value reads abnormal. Recorded as a known limit.

**Why 1 is recommended:** a lab reference interval is low→high by definition, so "99-70" is certainly a misordered print, not a real interval — the swap recovers the printed fact rather than discarding it (2 loses it) or keeping a guaranteed-wrong comparison (3). The raw text is preserved, so nothing is invented silently; and `test_extract_properties.py:3-4` already names the swap target (`ref_low <= ref_high`). The conservative-looking option (2) discards clinical data the patient saw on the report.

**Sub-question (b) — answered 2026-11-07: reject 400.** The patient can type an inverted pair on /verify (`ObservationVerify.ref_low > ref_high`, `api/observations.py:516-522` stores verbatim). The patient typed it; say so rather than silently reorder. Implemented in VERIFY-NONFINITE (`api/observations.py` is already its file; the two rejects sit in the same check block after the access check).

### Build (owner answered option 1 — swap; keep printed text)

- `be/modules/extract.py`: `ExtractedObservation` gains `__post_init__` (after `:53`): `if self.ref_low is not None and self.ref_high is not None and self.ref_low > self.ref_high:` swap them, with a comment naming RANGE-ORDER and that `ref_range_text`/`provenance` keep the printed order. One site covers `_parse_text_line` (all three line forms, and the OCR path via `_extract_from_text`) and `_parse_table_row` — every producer.
- `be/modules/import_structured.py`: a 4-line `_ordered_bounds` (or the same rule inline) applied where the dict's bounds are computed — CSV `:183-194` (compute `ref_low`/`ref_high` locals before the dict, then order), FHIR `:281-282` (`r0` low/high). `ref_range_text`/`r0["text"]` untouched.

**Files:** `be/modules/extract.py` (`__post_init__` only), `be/modules/import_structured.py` (the two sites only), `be/tests/test_extraction_pipeline.py` (HC-EXF-007*, appended to `TestExtractFormats`), `be/tests/test_extract_properties.py` (HC-PROP-005 + docstring `:3-4` updated to record the close), `be/tests/test_structured_import.py` (HC-FIMP-047, HC-FIMP-048 appended). **Not** `be/api/observations.py` — the patient-typed reject-400 rides VERIFY-NONFINITE's file by the owner's answer (keeps this row modules-only). **Not** `test_value_range_compare.py` — held by PANEL-WITHHELD-FIRSTGEN.

**Tests (RED first — every new case is RED on `main`, probe-confirmed).**
- **HC-EXF-007a/b/c:** `_extract_from_text` on the column, colon and alt forms of `"…99-70"` → `(ref_low, ref_high) == (70.0, 99.0)`, `ref_range_text == "99-70"`; plus `_extract_from_table` on a `99-70` cell → same.
- **HC-EXF-007d (pins, GREEN on `main`):** one-bound ranges unchanged (`"TSH 2.10 mIU/L <4.5"` → `(None, 4.5)`); equal bounds `"80-80"` → `(80.0, 80.0)` untouched; the `"(Normal: 99-70)"` form ordered likewise.
- **HC-FIMP-047 / HC-FIMP-048:** CSV `ref low`=99, `ref high`=70 → stored ordered; FHIR `referenceRange` `{low:{value:99}, high:{value:70}, text:"99-70"}` → ordered, `ref_range_text` preserved.
- **HC-PROP-005:** Hypothesis over the existing `_lab_lines` strategy (`test_extract_properties.py:44-52`, which emits `lo>hi` roughly half the time): for every parsed observation, `not (o.ref_low is not None and o.ref_high is not None and o.ref_low > o.ref_high)` — RED on `main` (the strategy finds inverted lines immediately); the assertion shape holds under either option.
- **Would not notice:** a reprocess of an old document (re-extracts fresh — ordering applies then); already-stored inverted rows in a vault (no migration — say so; they read abnormal as today, the readers' pins keep holding).

**Tests that must stay unedited (any RED among them stops the build for L0):** `test_value_range_compare.py` (all of HC-VRC-001…033 — the inverted-reader pins at `:319`, `:1121` *must* keep passing: readers still see inverted bounds from legacy rows and user input), `test_verify_keeps_flag.py`, `test_documents_api.py` — i.e. all other tests in the three touched test files.

**Acceptance.**
- `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_extraction_pipeline.py tests/test_extract_properties.py tests/test_structured_import.py tests/test_value_range_compare.py tests/test_verify_keeps_flag.py tests/test_documents_api.py -p no:cacheprovider -q`, with RED then GREEN per new id.
- The full backend suite and the collected count with its delta against 4661.
- `git diff --name-only origin/main...HEAD` prints the five files (+2 if the (b) answer lands here).
- **Merge-only gate (stored lab data):** the owner sees the exact `extract.py`/`import_structured.py` diff implementing the answered option before merge.

**Never beside:** TEST-PLACEHOLDERS (same `test_extraction_pipeline.py`, disjoint hunks — second lander rebases); PANEL-WITHHELD-FIRSTGEN (holds `test_value_range_compare.py` — this row does not need it; if the build finds it does, it stops); never beside another `modules/extract.py` or `modules/import_structured.py` PR — none open on 2026-11-07. Disjoint from #535, #537, #538.

**Estimate:** 1.5 h after the answer. **Runtime:** `codex` (+ Claude Code Opus review, medical-safety lens).

---

## VERIFY-NONFINITE

**Source:** queue.md `:690` (found 2026-11-02, PR #463, L0 security review; candidate): "`{"value": NaN}` is accepted by `ObservationVerify` (`api/observations.py:155`): measured HTTP 200 on a `CRITICAL` row at 18 against 12-16, stored `value=None, flag=None, is_abnormal=False`. It needs a crafted authenticated request. Same on main by the diff. Likely fix: reject non-finite numbers." Kind: SAFETY (fail-closed input rejection). Lens: security.

**Facts (re-read on `9ab89972`, probe pasted).**

    >>> json.loads('{"value": NaN, "ref_high": Infinity}')  # Python json accepts the JS constants
    >>> ObservationVerify(**body)  ->  accepted: nan inf
    >>> math.isfinite(v.value), math.isfinite(v.ref_high)  ->  False False

- `ObservationVerify` (`api/observations.py:203-211`): `value`, `ref_low`, `ref_high` are `Optional[float]` — pydantic v2 accepts NaN/±inf by default; Python's `json.loads` emits them for the `NaN`/`Infinity`/`-Infinity` literals a crafted body can carry.
- `POST /observations/{observation_id}/verify` (`api/observations.py:457-604`): access check at `:488`, then edits apply verbatim (`:504-522`), then the flag recalculation at `:559-568` — `observation.value < ref_low` with a NaN is always False, so it falls to the `else`: `is_abnormal=False, flag=None`. That is exactly the measured outcome: a `CRITICAL` flag erased by a non-finite edit. SQLite then stores the NaN as NULL (`value=None` measured). `math` is not yet imported by the file.
- **No existing test or fixture relies on non-finite acceptance** — grep `NaN|nan|inf|isfinite` over `test_verify_keeps_flag.py`, `test_observations_audit.py`, `test_observation_panel_snapshots.py`, `test_value_range_compare.py`: nothing.

**Fix (fail closed, 400; two rejects in one check block).** In `verify_observation`, immediately after `verify_observation_access(observation, session)` (`:488`) and before the `original_value_json` write (`:490`):
1. For each of `verify_data.value`, `verify_data.ref_low`, `verify_data.ref_high` — when not `None` and not `math.isfinite(...)` → `HTTPException(status.HTTP_400_BAD_REQUEST, "<field> must be a finite number")` (exact detail text is the merge-only gate below).
2. When both `verify_data.ref_low` and `verify_data.ref_high` are not `None` and `ref_low > ref_high` → `HTTPException(status.HTTP_400_BAD_REQUEST, "ref_low must not exceed ref_high")` (exact detail text is the same merge-only gate). **Owner answer RANGE-ORDER-STORE-VERIFY (2026-11-07): the patient typed the pair — reject, never silently reorder.** This is the /verify half of RANGE-ORDER, placed here so `api/observations.py` has one PR (this row's).
Placement: after the access check — a 404/403 on someone else's row stays first; the input is rejected before any write, flush or audit. A schema-level `Field(allow_inf_nan=False)` would return **422**, not the specified 400 — so the check is the handler's, not pydantic's (say so in the commit message).

**Files:** `be/api/observations.py` (`import math` + the check block only), `be/tests/test_verify_nonfinite.py` (new, HC-VNF-001…006). Nothing else.

**Tests (RED first — every reject case is RED on `main`, which answers 200).** HC-VNF-006 is the owner-answered RANGE-ORDER-STORE-VERIFY half. Harness copied from `test_verify_keeps_flag.py:37-77`: `profile_db` fixture (`sqlite+aiosqlite` in-memory, `ProfileDatabaseBase.metadata.create_all`), `_seed_obs` for a `CRITICAL`-flagged row at 18 against 12-16, `_get` over `route_client(obs_api.router, "/observations", ...)`, `json=` bodies carrying `float("nan")`/`float("inf")`/`float("-inf")` (Python's `json.dumps` emits the `NaN`/`Infinity`/`-Infinity` literals — the wire shape the queue measured).
- **HC-VNF-001:** `{"value": NaN}` → 400; the stored row is **unchanged** when re-read from the profile DB (`value=18`, `flag="CRITICAL"`, `is_abnormal=True`, `user_verified` still False) — the reject happens before the original-values write, so audit fields are absent too.
- **HC-VNF-002:** `{"value": Infinity}` and `{"value": -Infinity}` → 400 each.
- **HC-VNF-003:** `{"ref_low": NaN}` and `{"ref_high": -Infinity}` → 400 each.
- **HC-VNF-004 (pin, GREEN on `main`):** finite edits still verify — `{"value": 18.5, "ref_low": 12.0, "ref_high": 16.0}` → 200 with recalculated flag as today; `{"value": 0.0}` and `{"value": -1.0}` → 200 (zero and negatives are real lab values).
- **HC-VNF-005 (pin, GREEN on `main`):** `{}` → 200, `user_verified` flips True (absent fields skip the check).
- **HC-VNF-006 (RANGE-ORDER-STORE-VERIFY):** `{"ref_low": 99.0, "ref_high": 70.0}` → 400; the stored row's bounds unchanged. `{"ref_low": 70.0, "ref_high": 99.0}` → 200 (a normal pair still verifies — pin). One bound alone (`{"ref_low": 99.0}`) → 200 — the check needs both (the other bound may already be stored). **RED on `main`** for the 400 half.
- **Would not notice:** a non-finite that arrives by `lab_csv` import — `_parse_float` (`import_structured.py:62-71`) accepts `float("nan")`/`float("inf")` from a cell — a same-class gap at a different door (extracted rows are `user_verified=False`, so the vault holds NULL-abnormal not a false flag; **noted, not in this row**).

**Tests that must stay unedited:** `test_verify_keeps_flag.py` (all 001-025 pins), `test_observations_audit.py`, `test_observation_panel_snapshots.py`, `test_value_range_compare.py`, `test_documents_api.py` — any RED among them stops the build for L0.

**Acceptance.**
- `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_verify_nonfinite.py tests/test_verify_keeps_flag.py tests/test_observations_audit.py tests/test_observation_panel_snapshots.py -p no:cacheprovider -q`, with RED then GREEN for HC-VNF-001…003 and the 400 half of HC-VNF-006.
- The full backend suite and the collected count with its delta against 4661.
- `git diff --name-only origin/main...HEAD` prints the two files.
- **Merge-only gate (new patient-visible error text):** the owner sees the exact 400 `detail` strings in the diff before merge (the SAFETY-MODE-NOTE-WORDING convention).

**Never beside:** nothing open holds `be/api/observations.py` (#537 holds `api/export.py`, `api/pinboards.py`, `api/profiles.py` — disjoint; #535/#538 frontend-only). The /verify reject-400 already lives here by owner answer, so no second PR ever touches the file.

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review, security lens).

---

> **Delta 2026-11-10 (BATCH-1110A): VERIFY-NONFINITE.**
> - **Owner answer VERIFY-NONFINITE-400 "Approve as written (Recommended)" (2026-11-10, relayed by L0):** the two 400 `detail` strings are approved verbatim, "<field> must be a finite number" and "ref_low must not exceed ref_high". The merge-only gate in Acceptance is therefore answered; the PR body still shows the strings.
> - **Plan correction (httpx 0.28):** the tests above send `json=` bodies carrying `float("nan")`. With httpx 0.28 that raises on the client ("Out of range float values are not JSON compliant") before any request is made, so a `json=` test of the non-finite cases can never reach the route and cannot fail. The first built version had exactly that defect (a test that could not fail). Send the body as raw text instead, for example `content='{"value": NaN}'` with `headers={"Content-Type": "application/json"}`, and keep one finite `json=` case as the control. Recorded as an instance in `recurring-failures.md`.

## TIMELINE-VERIFY-INVALIDATE

**Source:** queue.md `:769` (found 2026-11-07 by the BATCH-1107A planner beside DELETED-DOC-NAMES-TIMELINE; deliberately not folded into that row — ruling 6651066872 scoped it to the document hooks). Kind: PRODUCT (frontend; query invalidation). Lens: accuracy of displayed clinical status (a stale "Needs verification" badge and stale medication events on screen).

**Facts (re-read on `9ab89972`).**
- The query client caches every query for 5 minutes (`staleTime: 1000 * 60 * 5`, `fe/App.tsx:94`). `useTimeline` keys on `['timeline', filters]` (`fe/services/timeline.ts:58-62`); `TimelinePage` is its only caller.
- `useVerifyObservation` (`fe/services/observations.ts:93-97`): `onSuccess` invalidates `[QUERY_KEY]` (`'observations'`) and `['documents']` — **not** `['timeline']`. A lab card's `verification_status` is built from `o.user_verified` (`be/modules/timeline.py:116-117`, `_verification_from_flags`), so the card's badge (`TimelinePage.tsx:115-117`; labels "Verified"/"Needs verification" at `:63-64`, rendered `:170`) stays stale for up to 5 minutes after a verify.
- The `Medication` table is read on **every** timeline fetch (`be/modules/timeline.py:196-228`): one `medication_start` event per row, `medication_stop` when `ended_at` is set; `medication_start`/`medication_stop` are `TimelineEventType`s (`fe/services/timeline.ts:15-16`). Three `fe/services/medications.ts` mutations change that content and never invalidate `['timeline']`:
  - `useCreateMedication` `:172-177` (`:175` invalidates `[QUERY_KEY]` only) — adds a `medication_start` event.
  - `useUpdateMedication` `:183-195` (`:192-193` invalidate `[QUERY_KEY, medicationId]` and `[QUERY_KEY]`) — `MedicationUpdate` carries `ended_at` and `is_active` (`be/api/medications.py:114-115`, applied `:645-648`): creates/removes a `medication_stop` event, and a rename changes the event title.
  - `useDeleteMedication` `:201-212` (`:210`) — `hard_delete` removes the row → both events gone (`be/api/medications.py:702-708`); the default soft delete sets `is_active=False` (`:717`). `_medication_events` has no `is_active` filter, so a deactivated med's events still display — the existing backend contract; the invalidation keeps the view honest either way (whether deactivation should hide events is a backend product question — **not in this row**).
- The one-line fix is the pattern DELETED-DOC-NAMES-TIMELINE applies to `documents.ts`: `queryClient.invalidateQueries({ queryKey: ['timeline'] });` — prefix matching covers every filtered key (`['timeline', {event_type: 'medication_start'}]`); a literal key like the `['observations']`/`['documents']` literals beside it: no shared constant, no import from `timeline.ts`.

**Files:** `fe/services/observations.ts` (the `useVerifyObservation` `onSuccess` `:93-97`, one added line), `fe/services/medications.ts` (one added line in each of the three `onSuccess` blocks `:174-176`, `:191-194`, `:209-211`), `fe/__tests__/timeline-verify-invalidate.test.tsx` (new, HC-TVI-001…005). Nothing else.

**Tests (RED first).** New file `timeline-verify-invalidate.test.tsx`; `vi.mock('@/services/api', () => ({ apiGet: vi.fn(), apiPost: vi.fn(), apiPatch: vi.fn(), apiDelete: vi.fn() }))` covers both services files. A mounted `useTimeline()` observer (the `TimelineProbe` mount, `TimelineService.test.tsx:31-34`) shares the `QueryClient` (`staleTime: 300_000`, `retry: false`) with the mutation under test.
- **HC-TVI-001:** `useVerifyObservation().mutateAsync({ observationId: 'o-1', data: {} })` (`renderHook`, `apiPost` resolved) → `/timeline/` fetched a second time. **RED on `main`.**
- **HC-TVI-002 / 003 / 004:** `useCreateMedication` (`apiPost` resolved), `useUpdateMedication` (`apiPatch`, args `{medicationId, data}`), `useDeleteMedication` (`apiDelete`, args `{medicationId}`) each → `/timeline/` fetched again. **RED on `main`.**
- **HC-TVI-005 (pins, GREEN on `main`):** `useVerifyObservation` still invalidates `['observations']` and `['documents']` (the new line replaces neither); the three medication mutations still invalidate their existing keys (`['medications']`, `['medications', medicationId]`); a cached `['timeline', {event_type: 'medication_start'}]` query shows `isInvalidated` after `useDeleteMedication` (prefix match).
- **Would not notice:** schedule and dose mutations (`useCreateSchedule`/`useUpdateSchedule`/`useDeleteSchedule` `:223-280`, `useLogDose` `:283-311`, `useLearnPatterns` `:334-350`) — no dose/schedule `TimelineEventType` exists, so nothing to invalidate; failed mutations (`onError`).

**Tests that must stay unedited** (each still passes, by reading): `TimelineService.test.tsx`, `ui-records.test.tsx` (its `removeQueries({ queryKey: ['timeline'] })` calls are its own), `MedicationCorrelations.test.tsx`, `VerificationWorkbench.test.tsx`, `deleted-doc-names-timeline.test.tsx` (the BATCH-1107A row's new file — this row's file is named differently so the two cannot collide), all e2e specs. No e2e assertion changes.

**Acceptance.**
- `cd src/frontend && npx vitest run src/__tests__/timeline-verify-invalidate.test.tsx src/__tests__/TimelineService.test.tsx src/__tests__/ui-records.test.tsx src/__tests__/MedicationCorrelations.test.tsx src/__tests__/VerificationWorkbench.test.tsx`, with RED then GREEN pasted for HC-TVI-001…004.
- `npx tsc --noEmit`.
- `git diff --name-only origin/main...HEAD` prints the three files.
- No quiet box: no rendering changes.

**Never beside:** DELETED-DOC-NAMES-TIMELINE (its ready row holds `fe/services/documents.ts` + `fe/__tests__/deleted-doc-names-timeline.test.tsx` — file-disjoint; both add `['timeline']` lines in different files). Disjoint from #535, #537, #538 and the other two ready rows.

**Not in this row:** whether `_medication_events` should filter `is_active=False` (backend product question — today a deactivated med keeps its start/stop events); `['timeline']` invalidation for observation *edit/delete* paths if any exist beyond verify (`services/observations.ts` has none); the two stale `TimelinePage.tsx`/`ui-records.test.tsx` comments the DELETED-DOC-NAMES-TIMELINE plan already names as a comment-only follow-up (TIMELINE-STALE-COMMENTS).

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review).
