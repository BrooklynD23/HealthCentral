# Plans for DOC-EXC-LOGGING, CPU-DEFAULT-PIN, SRE-002-WEAK, SAFETY-MODE-DUPROW, A11Y-LABEL-MINORS, DOC-OVERCLAIM-2 and HANDOFF-ARCHIVE-6

**Last Updated:** 2026-11-07 (Opus planner on `9ab89972`, docs batch BATCH-1107C: five code/test rows plus two docs rows, all for runtime `codex` under the owner's chat direction QUIET-PARALLEL-1107; IMPORT-FAILED-REASON and DOCS-VISIT-EXC-LOG folded into one DOC-EXC-LOGGING row — both are raw-exception handling in `be/api/documents.py`)
**Owner:** repository owner
**Status:** PLANNED (Opus planner). Docs only. All owner gates answered 2026-11-07: **SAFETY-MODE-DUPROW-SEMANTICS = option 1** (any-ON authoritative; PATCH writes every row). DOC-OVERCLAIM-2 carries the standing owner answer "Plan a fix row (Recommended)" (`owner-decisions-2026-09-27.md:403`); HANDOFF-ARCHIVE-6 carries "Move, keep quotes (Recommended)" (`:402`).
**Base measured:** `origin/main` @ `9ab89972` (2026-11-07, #534 merged). Every `file:line` below was re-read on this docs worktree at `da1a5836` — `9ab89972` plus docs-only commits; `git diff --name-only 9ab89972..HEAD` lists no `src/` file, so product and test code is exactly main. No probe was run this round: DOC-EXC-LOGGING, SAFETY-MODE-DUPROW and A11Y-LABEL-MINORS have real RED on main by direct reading (the build pastes the runs); CPU-DEFAULT-PIN and SRE-002-WEAK are honestly GREEN on main and name the mutation-RED the build must paste.
**Refresh Trigger:** a merge that edits `src/backend/api/documents.py`, `src/backend/api/assistant.py`, `src/backend/tests/test_safety_mode_setting.py`, `src/backend/tests/test_cpu_default_model.py`, `src/frontend/src/services/profiles.ts`, `src/frontend/src/pages/ProfileSetup.tsx`, `src/frontend/src/__tests__/ProfileSetup.test.tsx`, `src/frontend/src/__tests__/a11y-crit-labels.test.tsx`, `src/frontend/src/pages/settings/AssistantPrivacySection.tsx`, `src/frontend/src/components/MemoryManager.tsx`, `src/backend/models/model_settings.py`, `src/backend/models/audit.py`, the five DOC-OVERCLAIM-2 docs, `docs/plans/2026-10-1[78c]*-session-handoff.md`, `docs/plans/2026-10-20c-session-handoff.md` or `docs/plans/2026-10-21-session-handoff.md`; an owner answer to SAFETY-MODE-DUPROW-SEMANTICS; #535, #537 or #538 leaving the open-PR list; parked #264, #316 or #239 leaving draft; any BATCH-1107A or BATCH-1107B row landing.

Queue rows: [queue.md, "Planned 2026-11-01, harness speedup"](2026-10-15-build-program/queue.md#planned-2026-11-01-harness-speedup) (the seven rows append at the end of that table; promoted from candidate bullets `IMPORT-FAILED-REASON` :549, `DOCS-VISIT-EXC-LOG` :558, `DOC-OVERCLAIM-2` :156, `HANDOFF-ARCHIVE-6` :157, `CPU-DEFAULT-PIN` :617, `SRE-002-WEAK` :618, `SAFETY-MODE-DUPROW` :619, `A11Y-LABEL-MINORS` :620). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md) (§10.1 planner checklist, §10.2 Codex CLI), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue (`fe/` = `src/frontend/src`, `be/` = `src/backend`).

**Rules that hold for every row here.**
- **Runtime `codex`** (owner chat 2026-11-07, QUIET-PARALLEL-1107). Codex implements; the review is a Claude Code Opus session (RUNBOOK §1 rule 2), with the lens each row names. The two docs rows are `noslot` (DOCS kind), same runtime.
- No row lowers a threshold, relaxes a guard or weakens an assertion to pass. A test named as "must change" changes only as written; any other RED test stops the build for L0 with its ids.
- Route tests go through `tests/support/routes.py::route_client` — never a direct handler call for anything asserting auth, path scoping or status codes (recurring-failures #1).
- Backend pytest always runs as: `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest <files> -p no:cacheprovider -q`. **Collected-count baseline: 4661** (measured on `origin/main` `9ab89972` under pyslot, queue Last Updated 2026-11-07). Each build reports its measured count and delta.
- Frontend acceptance: `cd src/frontend && npx vitest run <files>` then `npx tsc --noEmit`.
- `git diff --name-only origin/main...HEAD` must print exactly the row's file list.
- **Open PRs checked 2026-11-07** (`gh pr diff <n> --name-only`, carried from the BATCH-1107A/1107B plan headers): #538 SAFETY-MODE-VERIFIED-FE (`fe/pages/ResultsPage.tsx`, `fe/components/results/RangeRibbon.tsx`, `SafetyModeToggle.tsx` note text, `fe/__tests__/safety-mode-toggle.test.tsx`, `safety-mode-verified.test.tsx`, `e2e/safety-mode.spec.ts` — frontend only); #537 C-GC1 (`be/api/export.py`, `be/api/pinboards.py`, `be/api/profiles.py`, profile migration `019_export_artifacts`, `be/models/export_artifact.py`, `be/models/__init__.py`, `be/tests/support/migrations.py`, `be/tests/test_audit_order_guard.py`, `test_denial_audit.py`, `test_export_redaction.py`, `test_visit_prep_packet.py`, `test_export_artifact_persistence.py`, `test_fk_migration_017.py`); #535 UI-PG-SECURITY (`e2e/support/gates.ts`, `e2e/ui-gates-sampler.spec.ts`, `e2e/ui-security.spec.ts`, `BackupCard`/`DangerZone`/`RecoveryCodeCard`/`SecuritySection` tsx, `ui-security.test.tsx`, `BackupRestoreFlow.test.tsx`); #316 (draft: `README.md`, `dev.ps1`, `dev.sh`, `test_dev_sh_prereqs.py`); #264 B-3 (parked draft, floats per contracts §b rule 2: `api/interpretations.py`, `api/assistant.py`, `modules/rag.py`, `test_audit_order_guard.py`, `test_safe_interp_grounded.py`); #239 RSI1-DONATE PR-2 (blocked draft: `config/.env.example`, `fe/pages/SettingsPage.tsx`, `test_audit_order_guard.py`). Ready BATCH-1107A rows hold: `fe/services/documents.ts`, `fe/pages/DocumentInbox.tsx`, `fe/pages/VerificationWorkbench.tsx`, `fe/pages/settings/AdvancedSection.tsx`, `be/api/model_settings.py`, `be/modules/interpret.py`, `be/api/interpretations.py`, `be/tests/test_value_range_compare.py`, `be/modules/environment_diagnostics.py`, `config/.env.example`, `dev.sh` (+ new test files). BATCH-1107B rows hold: `fe/__tests__/api.test.ts`, `fe/__tests__/ExplainAssistant.test.tsx`, `be/tests/test_ocr_bbox.py`, `be/tests/test_extraction_pipeline.py`, `be/tests/test_pyslot_lock_guard.py`, `be/modules/extract.py`, `be/modules/import_structured.py`, `be/tests/test_extract_properties.py`, `be/tests/test_structured_import.py`, `be/api/observations.py`, `fe/services/observations.ts`, `fe/services/medications.ts`, `fe/services/timeline.ts`, `scripts/pyslot.sh`.
- **RED honesty.** Real RED on main exists for DOC-EXC-LOGGING, SAFETY-MODE-DUPROW and the new A11Y assertions. CPU-DEFAULT-PIN and SRE-002-WEAK are test-strengthening rows — production code is already right — so each names a mutation-RED paste. DOC-OVERCLAIM-2 and HANDOFF-ARCHIVE-6 are docs/git-mv rows: no tests.

---

## DOC-EXC-LOGGING (folds IMPORT-FAILED-REASON + DOCS-VISIT-EXC-LOG)

**Source:** queue.md :549 ("a password-protected or non-PDF `.pdf` returns 201 `extraction_failed` with no reason; also that `except` logs `{e}`") and :558 ("`be/api/documents.py:988` logs `{e}` on the LLM-assist entity pass failure; same RUNNER-EXC-INTERP shape"). The cited lines moved to :717 and :1013. Kind: PRODUCT (backend; privacy/logging + API surface). Lens: security — raw exception strings can carry paths, tokens and document text.

**Facts (re-read on `9ab89972`).**
- `be/api/documents.py` has **four** raw-exception log sites: `:703-704` `f"Chunking failed … {chunk_error}"`, `:716-717` `f"Extraction failed for document {document.id}: {e}"`, `:1002-1006` `f"Entity extraction failed for {doc_id} (category={result.category}): {e}"`, `:1009-1013` `f"LLM-assist entity pass failed for {doc_id}: {e}"`.
- The `:716-726` handler also stores `document.status = "extraction_failed"`, clears `parsed_at`/`verified_at`, commits, and returns `{observations_extracted: 0, needs_verification: True, extracted_text: None}` — no reason reaches the 201 response. `DocumentResponse` (`:230-264`) and `DocumentImportResponse` (`:284-295`) have no reason field; the import route (`:563-573`) and reprocess route (`:1274-1279`) return the latter. Grep: no `failure_reason`/`extraction_error` anywhere in `src/`.
- Safe precedent in the same file: the delete path logs `type(exc).__name__`, never `str(exc)` (`:1932-1937`).
- `test_embedding_fail_closed_paths.py:694-702` (HC-EMB-009c) asserts `"Chunking failed"` appears in caplog and no path leaks — the "Chunking failed" prefix must survive.
- Frontend treats `extraction_failed` as a status badge only (`fe/pages/DocumentInbox.tsx:618`, `fe/pages/VerificationWorkbench.tsx:39,145-146,861`); those files are excluded and stay untouched — the new field is additive and optional, no frontend change.

**Build.**
1. At `:704`, `:717`, `:1005`, `:1013` replace the exception-message interpolation with `type(e).__name__`/`type(chunk_error).__name__`, keeping every message prefix verbatim ("Chunking failed", "Extraction failed", "Entity extraction failed", "LLM-assist entity pass failed"). Never `str(exc)` — parser/DB errors can embed paths, secrets and document text.
2. The `:716-726` handler adds `"extraction_error": type(e).__name__` to its return dict; the success path carries no such key (or `None`).
3. `DocumentImportResponse` gains `extraction_error: Optional[str] = None`; the import route (`:563-573`) and reprocess route (`:1274-1279`) populate it from the outcome dict. `DocumentResponse` and the `Document` model are unchanged — the reason is transient on the 201 response; the persisted signal stays `status = "extraction_failed"` (no profile migration; `019_export_artifacts` is #537's slug).
4. Nothing else in the file moves. No `str(e)` remains at these four sites.

**Files:** `be/api/documents.py` (the four log sites, the handler's return, `DocumentImportResponse`, the two route returns), `be/tests/test_document_extraction_failure.py` (new, HC-EXL-001…005). Nothing else.

**Tests (RED first).**
- **HC-EXL-001 (the reported defect + the log redaction, through the route).** `route_client(documents_router, "/documents")` on an in-memory profile DB; monkeypatch the extract step to raise `RuntimeError("secret-token-xyz path /tmp/phi-file")`. POST import → 201; body `document.status == "extraction_failed"`, `extraction_error == "RuntimeError"`, `"secret-token-xyz"` absent from the response JSON **and** from caplog (which does contain "Extraction failed"). RED on main: no field; `{e}` lands the secret in caplog.
- **HC-EXL-002.** `_classify_and_extract_entities` with `llm_assist=True`, `llm_assist_visit_entities` raising `RuntimeError("sk-live-key")`: caplog has "LLM-assist entity pass failed" and `RuntimeError` and not the key text. RED on main.
- **HC-EXL-003.** A category extractor raising `RuntimeError("path /tmp/x")`: "Entity extraction failed" logged with the type name, not the message.
- **HC-EXL-004 (pin, GREEN on main):** a chunking failure (absent embedding model, HC-EMB-009c's shape) still logs a line starting "Chunking failed" and now carries the exception type name.
- **HC-EXL-005 (pin, GREEN on main):** a successful import/reprocess has `extraction_error` null.
- **Would not notice:** which exception class fires for a real locked PDF (the reason is the type name, honestly coarse — no invented mapping); the persisted column (none added).

**Tests that must stay unedited:** `test_embedding_fail_closed_paths.py` (HC-EMB-009c; the "Chunking failed" prefix survives by construction), `test_document_import_classification.py` (all of it, incl. the `:340-454` non-fatal suite — mock-level, unaffected), `test_documents_api.py`, `test_ocr_bbox.py`, `test_visit_note_extraction.py`, `test_runner_exc_interp_logs.py`, `test_extraction_pipeline.py` (BATCH-1107B holds it anyway).

**Acceptance.**
- `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_document_extraction_failure.py tests/test_embedding_fail_closed_paths.py tests/test_document_import_classification.py tests/test_documents_api.py -p no:cacheprovider -q`, with RED then GREEN per new id.
- The full backend suite (RUNBOOK §6 step 2) and the collected count with its delta against 4661.
- `git diff --name-only origin/main...HEAD` prints the two files.

**Never beside:** another PR on `be/api/documents.py` (none open on 2026-11-07). Disjoint from #535/#537/#538, parked #264 (does not hold it), #316, #239 and every BATCH-1107A/1107B file. The excluded frontend files (`fe/services/documents.ts`, `fe/pages/DocumentInbox.tsx`, `fe/pages/VerificationWorkbench.tsx`) are not touched.

**Estimate:** 1.5 h. **Runtime:** `codex` (+ Claude Code Opus review, security lens).

---

## CPU-DEFAULT-PIN

**Source:** queue.md :617 (found 2026-10-23, #315 review MINOR; optional): "an extra HC-CPU-002 assert, `(16.0, 100.0, 8.0) == "gemma4-12b"`". Kind: TEST. Lens: —.

**Facts (re-read on `9ab89972`).** `be/tests/test_cpu_default_model.py:27-28` (HC-CPU-002) pins only `(24.0, 100.0, 16.0) == "high"`. `hardware_detection.py:51-57` adds a capped VRAM boost at `gpu_vram_gb >= GPU_VRAM_BUMP_MIN_GB` (8.0, `:43`); `:352-359` skips `gemma4-12b` when the boost does not apply. With `(16.0, 100.0, 8.0)`: boost applies (over = 0), effective RAM 16 → `high` needs 32, `gemma4-12b` needs 16 → returns `"gemma4-12b"`. The tuple pins the exact VRAM threshold and the 16 GB RAM floor at once; HC-CPU-001 already pins the CPU-only ceiling.

**Honest note — GREEN on `main`.** The implementation already answers `gemma4-12b`; RED is impossible. Mutation-RED (build pastes it): change `:352` `>=` to `>` (or `GPU_VRAM_BUMP_MIN_GB` to `9.0`) → the boost no longer applies at exactly 8.0 → returns `"mid"` → the new assert fails. Revert.

**Files:** `be/tests/test_cpu_default_model.py` (`:28` gains `assert get_recommended_tier_from_hardware(16.0, 100.0, 8.0) == "gemma4-12b"`). Nothing else; `hardware_detection.py` is not edited.

**Tests that must stay unedited:** `test_hardware_detection.py` (same helper called at `:39-52`), `test_llm_provider_layer.py` (`TIER_REQUIREMENTS`/`TIER_ORDER` at `:680-715`), `test_tier_capabilities.py`, `test_model_settings_api.py`, `test_settings_detect_nonblocking.py`, `test_audit_read_settings.py`, `test_audit_order_guard.py`.

**Acceptance.**
- The pyslot pytest command on `tests/test_cpu_default_model.py tests/test_hardware_detection.py tests/test_llm_provider_layer.py`, with the mutation-RED paste and the GREEN run.
- Full suite + count delta (adding an assertion, not a test — expect +0 collected).

**Never beside:** nothing open on the file; disjoint from every BATCH-1107A/1107B row.

**Estimate:** 0.5 h. **Runtime:** `codex` (+ Claude Code Opus review).

---

## SRE-002-WEAK

**Source:** queue.md :618 (#312 PR body): "HC-SRE-002 passes without `gcTime: 0` because `clear()` empties the cache; only HC-SRE-003 guards the edit." Kind: TEST. Lens: security (secret retention, RCC-2).

**Facts (re-read on `9ab89972`).** HC-SRE-002 (`fe/__tests__/ProfileSetup.test.tsx:364-392`) types the password, unlocks, then asserts `cachedMutationsContaining(queryClient, PASSWORD) === 0`. The success handler (`fe/pages/ProfileSetup.tsx:207-219`) runs `login.reset()` (`:214`) then `queryClient.clear()` (`:217`), which empties the whole mutation cache — the postcondition passes even if `gcTime: 0` (`fe/services/profiles.ts:158`) were deleted. On the failure path (`:221`) there is no `clear()`, which is why only HC-SRE-003 (`:394-415`) actually guards the flag. React Query `^5.17.0`: `reset()` detaches the observer; the Mutation object lives in the MutationCache until GC — `gcTime: 0` destroys it on the next tick, the 5-minute default does not. Helpers: `fe/__tests__/support/secretRetention.ts:23-44`.

**Fix.** Keep HC-SRE-002's flow and postcondition (positive control `pw.seen` + post-flow zero stays valid), and add one `it` in the same describe, **HC-SRE-002b**, that pins `gcTime: 0` without `queryClient.clear()`: with the spec's own `QueryClient`, `renderHook(() => useLogin(), { wrapper })` (wrapper = the existing `QueryClientProvider`), `await result.current.mutateAsync({ profile_id: PROFILE.id, password: PASSWORD })` (apiPost mocked as in 002), `result.current.reset()`, then `await waitFor(() => expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0))`. No `clear()` on this path — only `gcTime: 0` can collect the detached mutation. New imports: `renderHook` (already a testing-library import site), `useLogin` from `@/services`.

**Honest note — GREEN on `main`.** Production is correct; the gap is the test's blindness. Mutation-RED (build pastes it): delete `gcTime: 0` (`profiles.ts:158`) → the settled-but-detached mutation lingers under the 5-minute default → HC-SRE-002b fails while HC-SRE-002 still passes, proving the old hole. Revert. (`login.reset()` removal is already covered by the existing postcondition — the mounted observer's mutation stays cached.)

**Files:** `fe/__tests__/ProfileSetup.test.tsx` only. `profiles.ts` and `ProfileSetup.tsx` are not edited.

**Tests that must stay unedited:** every other spec that renders `ProfileSetup` — `ui-auth.test.tsx` (~17 renders), `onboarding-lands-overview.test.tsx`, `ui-results.test.tsx`, `ui-routes.test.tsx` (stub), `ui-motion.test.tsx` — plus `ProfileMenuLock.test.tsx`, `RecoverProfile.test.tsx`, `RecoveryCodeCard.test.tsx`, `BackupRestoreFlow.test.tsx` (#535's), `DangerZone.test.tsx`, `__tests__/support/secretRetention.ts`, e2e `session-reentry.spec.ts`, `session-lock-now.spec.ts`, `auth.spec.ts`, `ui-tokens.spec.ts` (HC-UITK-006 CLS on `/setup`), `ui-shell.spec.ts` (G7 on `/setup`).

**Acceptance.**
- `cd src/frontend && npx vitest run src/__tests__/ProfileSetup.test.tsx src/__tests__/ui-auth.test.tsx src/__tests__/onboarding-lands-overview.test.tsx src/__tests__/ui-results.test.tsx`, then `npx tsc --noEmit`. The mutation-RED paste and the GREEN run.
- `git diff --name-only origin/main...HEAD` prints the one file.
- No quiet box: no rendering change.

**Never beside:** #535 (`BackupRestoreFlow.test.tsx` — named unedited, not touched). Disjoint from #537, #538, both ready batches, and #316/#239.

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review, security lens).

---

## SAFETY-MODE-DUPROW

**Source:** queue.md :619 (#349 review): "`is_strict_safety_mode` returns true if ANY `user_model_settings` row has the flag, while GET/PATCH `/assistant/safety-mode` read and write one row." Kind: PRODUCT (backend; safety semantics). Lens: medical safety. **Owner gate: SAFETY-MODE-DUPROW-SEMANTICS — do not build until answered.**

**Facts (re-read on `9ab89972`).**
- `be/api/assistant.py:700-713`: `is_strict_safety_mode` = `EXISTS` over **all** rows with `strict_safety_mode` true; the docstring (`:703-708`) documents fail-closed any-ON, no `profile_id` filter (the vault is per-profile), duplicate rows possible. Imported by `api/interpretations.py` (`:494, :566, :788, :879, :981, :1055`) and used at `assistant.py:1237, :1606` — signature stays `(profile_db) -> bool`.
- GET `/assistant/safety-mode` (`:716-735`) and PATCH (`:738-781`) both go through `_get_user_model_settings` (`:788-798`), which is `scalar_one_or_none()` on `profile_id == session.profile_id`. Two failure shapes, both worse than the bullet's "shows OFF while enforcing ON": **(a)** two rows for the same profile → `MultipleResultsFound` → GET and PATCH 500; **(b)** a stray row under a *different* `profile_id` in the same vault → enforcement ON, route row OFF (display/enforcement disagree).
- `be/models/model_settings.py:38-42`: `profile_id` indexed, **not unique**. `be/api/model_settings.py:341-349` `_get_user_settings` has the same `scalar_one_or_none()` dup-row hazard — **excluded file** (OCR-COPY-ENGINE holds it); noted for the owner, out of scope here.
- `test_safety_mode_setting.py` runs GET/PATCH through `route_client` (in-memory vault fixture `:41-69`); its HC-SMS-002 tail (`:116-128`) seeds `race-off` + `race-on` and pins `is_strict_safety_mode is True` — the any-ON contract. `test_safety_mode_strict.py:198-207` and `test_safety_mode_verified.py:~:225` PATCH through HTTP helpers.

### Owner question: SAFETY-MODE-DUPROW-SEMANTICS — **answered 2026-11-07: option 1** (any-ON authoritative; PATCH writes every row)

> A profile vault can hold two `user_model_settings` rows (`profile_id` is indexed, not unique). `is_strict_safety_mode()` treats ANY row with the flag as ON — but GET/PATCH `/assistant/safety-mode` read and write one row via `scalar_one_or_none()`: two rows for the same profile 500 both routes today, and a stray row under another `profile_id` makes enforcement ON while the UI reads OFF. What should the routes do?

1. **Any-ON is authoritative; PATCH writes every row (Recommended).** GET answers `is_strict_safety_mode()`'s value; PATCH sets `strict_safety_mode` on every row in the vault (inserting one when none exist, as today). Display and enforcement can never disagree; the documented fail-closed contract (HC-SMS-002) is preserved. A stray ON row is only switched off by an explicit OFF write. No schema change, no deletion.
2. **Dedupe to one canonical row on read/write.** The route collapses duplicates into one surviving row (the newest `updated_at`, or any ON row — fail closed) and deletes the rest. Cleaner end-state but introduces row deletion inside a settings route, and other readers (`api/model_settings.py`, out of this row's scope) keep the same hazard until dedup runs.
3. **One canonical row wins; strays ignored.** Read/write the newest row only; `is_strict_safety_mode` would need changing to match — weakens the fail-closed contract the docstring and HC-SMS-002 record. Not recommended.

**Recommended: 1** — smallest, keeps enforcement fail-closed, no deletions, no migration.

**Build (owner answered option 1 — any-ON authoritative; PATCH writes every row).**
- `is_strict_safety_mode` unchanged.
- GET answers `await is_strict_safety_mode(profile_db)` (the EXISTS value), not the one-row helper's flag.
- PATCH: `UPDATE user_model_settings SET strict_safety_mode = :v` for every row in the vault (`profile_id` rows and strays alike — the EXISTS predicate is unfiltered); when no row exists keep the existing insert path (`:747-754`). One `safety_mode_updated` audit row as today (`:760-771`), unchanged details.
- `_get_user_model_settings` callers other than GET/PATCH are untouched; if none remain in this file after the edit, leave the helper for its other users (`memory-settings` etc. — verify at build).
- Docstring `:703-708` gains one line: the routes converge on the same any-ON rule.

**Files:** `be/api/assistant.py` (GET `:723`, PATCH `:746-759`, docstring `:703-708`), `be/tests/test_safety_mode_setting.py` (new HC-SMS-008 cases, **and one edit to an existing assertion: the shared-vault tail of `test_hc_sms_004_profile_isolation`, see L0 ruling R1 below**). No model, no migration.

**L0 ruling R1 (2026-11-10; L0's, not the owner's; BATCH-1110A correction to this plan).** The plan omitted an edit that the owner answer forces. In `test_hc_sms_004_profile_isolation` (`be/tests/test_safety_mode_setting.py`, around `:180`), the tail that seeds a second profile's ON row into the shared vault asserts that profile B's GET reads `{"strict_safety_mode": False}`. Under the owner's any-ON answer (SAFETY-MODE-DUPROW-SEMANTICS, option 1) the GET answers `is_strict_safety_mode()`, which is true while any row in the vault is ON, so that assertion cannot stay. The licensed edit is exactly this: B's GET becomes `{"strict_safety_mode": True}` and the same tail gains `assert await assistant_api.is_strict_safety_mode(vault) is True`. HC-SMS-008c asserts the same thing from the other direction. No other existing assertion in the file changes. The edit is owner-visible at merge: the PR body says that a stray ON row under another `profile_id` now shows ON in the UI because enforcement is ON. Source: the sub-orchestrator's diff review (SUBORCH-2026-11-09) found it on the built branch; the Haiku red/green run showed HC-SMS-004 failing on `main` as the edited assertion.

**Tests (RED first; all through `route_client`).**
- **HC-SMS-008a:** seed `race-off` + `race-on` under `PROFILE_A` (the HC-SMS-002 tail's shape) → GET returns **200** `{"strict_safety_mode": true}`. RED on main (500 `MultipleResultsFound`).
- **HC-SMS-008b:** same two rows → PATCH `{"strict_safety_mode": false}` → 200; every row reads false; `is_strict_safety_mode` False; then PATCH true → every row true. RED on main (500).
- **HC-SMS-008c:** a stray ON row under `profile_id="other"` in the same vault → GET true (matches enforcement); PATCH false flips the stray too.
- **Would not notice:** `api/model_settings.py`'s duplicate hazard (out of scope); ordering among equal `updated_at` rows (option 1 makes ordering irrelevant).

**Tests that must stay unedited** (the one edit above, to the HC-SMS-004 shared-vault tail, is the only exception in `test_safety_mode_setting.py`): `test_safety_mode_strict.py`, `test_safety_mode_verified.py`, `test_rag_timeout_answer.py`, `test_gc5_nli_flag.py`, `test_chat_sessions.py`, `tests/agent/test_s5_cutover_cache.py`, `test_runner_exception_chain_logs.py`, `test_legacy_abstain.py`, `test_model_settings_api.py`, `test_audit_order_guard.py` (#537 holds it anyway), `test_fk_migration_017.py`.

**Acceptance.**
- The pyslot pytest command on `tests/test_safety_mode_setting.py tests/test_safety_mode_strict.py tests/test_safety_mode_verified.py tests/test_rag_timeout_answer.py`, with RED then GREEN for HC-SMS-008a-c; the full suite and count delta.
- `git diff --name-only origin/main...HEAD` prints the two files.

**Never beside:** parked #264 holds `be/api/assistant.py` — it floats and rebases (contracts §b rule 2); flag the shared file to L0 anyway. #538 is frontend-only (disjoint). BATCH-1107A PANEL-WITHHELD-FIRSTGEN touches `be/api/interpretations.py` (calls `is_strict_safety_mode`, unedited — signature and semantics hold). Any other PR on `be/api/assistant.py` or `test_safety_mode_setting.py`.

**Estimate:** 1.5 h. **Runtime:** `codex` (+ Claude Code Opus review, medical-safety lens).

---

## A11Y-LABEL-MINORS

**Source:** queue.md :620 (#348 round-2 minors): "HC-A11YCL-003 uses a loose `/provider/i` query; the API Key and Model labels in `SettingsPage.tsx` and the Category label in `MemoryManager.tsx` have no `htmlFor`." The `SettingsPage.tsx` labels moved to `fe/pages/settings/AssistantPrivacySection.tsx` in the UI-PG-SETTINGS split. Kind: PRODUCT (frontend; accessibility). Lens: —.

**Facts (re-read on `9ab89972`).**
- `fe/__tests__/a11y-crit-labels.test.tsx:154-161`: `screen.getByLabelText(/provider/i)` then `tagName === 'SELECT'`. The regex matches any accessible name containing "provider" — a label bound to an INPUT would still satisfy the tag check only via the tag assertion; a different "provider"-named select would pass outright.
- `AssistantPrivacySection.tsx`: the Provider label **is** bound (`:97` `htmlFor="external-provider-select"` → `:99` id). The **API Key** label (`:110`) and input (`:111-117`) are unbound; the **Model** label (`:120`) and input (`:121-127`) are unbound.
- `MemoryManager.tsx` add/edit form: Key (`:166-167`), Value (`:177-178`) and **Category** (`:188-189`) labels are all unbound. The candidate names Category; the same defect sits beside it — include Key and Value so the form ships no unbound label (L0 may trim to Category-only).
- `ui-settings.test.tsx:1626` already queries the exact `findByLabelText('Provider')` — tightening 003 changes no other spec's behavior. `ui-settings.spec.ts:412-419` already axe-scans the external-API fields (`#external-provider-select` wait at `:417` — the id stays). `a11y-crit-labels.test.tsx:84` mocks `MemoryManager` to null for the SettingsPage path — the new MemoryManager assertion renders the real component directly (import it unmocked and stub `@/services/memory` hooks).

**Build.**
1. `AssistantPrivacySection.tsx`: `id="external-api-key"` on the API-Key input + `htmlFor` on its label; `id="external-api-model"` + `htmlFor` likewise (the `external-provider-select` naming convention).
2. `MemoryManager.tsx`: `id="memory-category"` + `htmlFor` on the Category select; same for `memory-key`/`memory-value` (flagged inclusion above).
3. `a11y-crit-labels.test.tsx`: HC-A11YCL-003 becomes `getByLabelText('Provider', { selector: 'select' })` (exact accessible name; the tag assertion stays). New **HC-A11YCL-004**: on `assistant-privacy` with `use_external_api: true`, `getByLabelText('API Key', { selector: 'input' })` is a password input and `getByLabelText('Model', { selector: 'input' })` is a text input. New **HC-A11YCL-005**: render the real `<MemoryManager />` (stub `useMemoryItems`/`useCreateMemoryItem`/`useUpdateMemoryItem`/`useDeleteMemoryItem` from `@/services/memory`), open the add form, `getByLabelText('Category', { selector: 'select' })` (and 'Key'/'Value' inputs if included).

**RED honesty.** HC-A11YCL-004/005 are real RED on main (unbound labels). HC-A11YCL-003's tightening is mutation-RED — production is already bound: repoint the provider label's `htmlFor` to the API-key input (a "provider"-named label now bound to an INPUT) → the loose `/provider/i` + SELECT check passes only if the select itself were named — actually it fails the tightened query while the old regex still finds *a* provider-named element; the build pastes whichever mutation cleanly separates the two queries (e.g., duplicate the label text onto a second control). Paste it, then revert.

**Files:** `fe/pages/settings/AssistantPrivacySection.tsx` (`:110-127` ids/htmlFor), `fe/components/MemoryManager.tsx` (`:166-200` ids/htmlFor), `fe/__tests__/a11y-crit-labels.test.tsx` (`:154-161` tighten + HC-A11YCL-004/005 + a MemoryManager hook stub). **Not** `fe/pages/SettingsPage.tsx` (host only) and **not** `fe/pages/settings/AdvancedSection.tsx` (OCR-COPY-ENGINE's).

**Tests that must stay unedited:** `ui-settings.test.tsx` (its `'Provider'` query at `:1626` and `sk-...`/`gpt-4o` placeholders at `:1627-1628` work under the new ids — no edit), `Gamification.test.tsx`, `ui-routes.test.tsx`, every e2e spec — `ui-settings.spec.ts` (incl. `#external-provider-select` `:417`), `settings-smoke.spec.ts`, and #535's `ui-security.spec.ts`/`ui-gates-sampler.spec.ts`/`e2e/support/gates.ts` (never touched).

**Acceptance.**
- `cd src/frontend && npx vitest run src/__tests__/a11y-crit-labels.test.tsx src/__tests__/ui-settings.test.tsx src/__tests__/Gamification.test.tsx`, then `npx tsc --noEmit`. RED then GREEN for HC-A11YCL-004/005; the HC-A11YCL-003 mutation-RED paste.
- `git diff --name-only origin/main...HEAD` prints the three files.
- **Quiet box (L0), final head:** every spec whose gate sees the changed components — from `grep -ln "external-provider-select\|assistant-privacy\|sk-\.\.\.\|MemoryManager" src/frontend/e2e/*.spec.ts` on `9ab89972`: `ui-settings.spec.ts` (its assistant-privacy axe pass at `:412-419` now scans bound fields) and `settings-smoke.spec.ts` (E2E-SET-003 opens the section). Re-run the grep on the final head.

**Never beside:** #535 until it merges — files are disjoint but `ui-settings.spec.ts` quiet acceptance is shared, and one quiet batch cannot tell whose change moved a Settings node (same rule OCR-COPY-ENGINE carries). Also never beside the OCR-COPY-ENGINE row itself (different file, same Settings surface) or #239 leaving draft (`SettingsPage.tsx` — this row does not edit it). Disjoint from #538.

**Estimate:** 1.5 h. **Runtime:** `codex` (+ Claude Code Opus review).

---

## DOC-OVERCLAIM-2

**Source:** queue.md :156; owner prompt 42, answered "Plan a fix row (Recommended)" (`owner-decisions-2026-09-27.md:403`): re-read each cited line against main and write a one-docs-PR row rewording each claim to what the code does; the `models/audit.py` change is comment-only; the owner reviews before merge. Kind: DOCS (no slot).

**Per-line read on `9ab89972`** (the L1-C line list is stale; these are the current texts):
- `data-privacy.md:33` — "| Audit logs | Master DB (not encrypted). No log file is written | Indefinite |". True of the app: the per-event `logger.info` (`core/audit.py:258-265`) sits below the WARN root and writes to stderr; `log_file_path` only has its parent dir created (`core/database.py:110-111`), no FileHandler exists. Caveat worth sharpening to match `:35`'s style: dev launchers tee stderr (`dev.sh` → `logs/dev-backend.log`). Proposed: keep the row, qualify as "application logger only (the process's stderr), at INFO below the default WARN level — the app writes no log file".
- `data-privacy.md:46` — "| Backups | Same as source | SQLite backup API preserves encryption |". Accurate for the database files (`scripts/backup.py:181-232`, `:460-462`; locked vaults use `VACUUM INTO` keeping the cipher); scope it: the bundle's `manifest.json` is plaintext metadata and sealed keys stay sealed.
- `data-privacy.md:61` — "| Backups | 30 days | … `0` means never prune. Deleted with the profile. |" — verified (`backup_schedule.py:61` default 30; `api/backup.py:107-111,:131-135` "0 means never prune" verbatim; profile deletion sweeps backups). Keep.
- `hipaa-controls.md:50-51` — "emits application-log entries for mutating requests" / "application logger for security middleware entries" — verified (`audit_middleware.py:38-40` mutating methods only).
- `hipaa-controls.md:83-88` — **overclaims twice**: calls the trail "append-only" while `:52` declares "Not append-only", and says profile deletion is "the only path that removes them" while `:52` says a whole-install restore replaces the master DB. Reword to: rewriting history is a worse property than the exposure it removes; "removed by profile deletion, or by restoring a whole-install backup that does not contain them".
- `docs/compliance/README.md:14-18` — same two overclaims; same rewording.
- `src/backend/models/audit.py:4` — "HIPAA-compliant audit trail" → "Audit trail modelled on the HIPAA technical safeguards" (posture, per `README.md:22-25`); `:25` "for HIPAA compliance" → "for security review". Comment-only.
- `docs/capstone-report/implementation-program.md:510` — the DOC-OVERCLAIM-2 tracker row itself; update its status text in the same PR (own-row edit, contracts §b rule 4).

**Files:** `docs/compliance/data-privacy.md`, `docs/compliance/hipaa-controls.md`, `docs/compliance/README.md`, `src/backend/models/audit.py` (docstring only), `docs/capstone-report/implementation-program.md`; regenerated `docs/INDEX.md` + `docs/_link_graph.json` (SLOT-RULE-2a).

**Acceptance:** every named line either reworded to measured behavior or recorded "verified, kept"; `python3 scripts/docs_lint.py` clean and `generate_docs_index.py --check` fresh; the owner sees the PR before merge (standing gate from the answer).

**Never beside:** nothing open on the five files (the stale `data-privacy.md` order "F-6 → WEAR-14" names no open row).

**Estimate:** 1 h, `noslot`. **Runtime:** `codex` (+ Claude Code Opus review).

---

## HANDOFF-ARCHIVE-6

**Source:** queue.md :157; owner prompt 42, answered "Move, keep quotes (Recommended)" (`owner-decisions-2026-09-27.md:402`): `git mv` the six superseded handoffs + 2026-10-21c to `docs/archive/plans/`, repoint links in `queue.md` and lane E; quoted paths keep their old text. Kind: DOCS (no slot).

**Facts (re-read on `9ab89972`).** The move is **partly done**: `docs/archive/plans/` already holds `2026-10-17`, `-19`, `-20`, `-20b`, `-21b` and `-21c`. Still in `docs/plans/`: `2026-10-18-session-handoff.md`, `2026-10-20c-session-handoff.md`, `2026-10-21-session-handoff.md` — this row completes the set (all seven named handoffs end archived).

**Build.**
1. `git mv` the three files into `docs/archive/plans/`.
2. Repoint live links (in `docs/plans/2026-10-15-build-program/` sources, `../archive/plans/…`): `queue.md:51`, `:361`, `:381` (→ `2026-10-20c`), `queue.md:423` (→ `2026-10-21`), `queue.md:1013` (→ `2026-10-18`), `lane-E-privacy-gates-ci.md:928` (→ `2026-10-20c`). `lane-E-privacy-gates-ci.md:1035`'s citation paths `docs/plans/2026-10-20-session-handoff.md:53` and `2026-10-20c-session-handoff.md:43` repoint to `docs/archive/plans/…` (the 2026-10-20 one is already stale); the quoted sentences stay verbatim.
3. Inside the moved files, relative links deepen one level: `../../CLAUDE.md`/`../../AGENT.md` → `../../../…`; `2026-10-15-build-program/RUNBOOK.md` → `../../plans/2026-10-15-build-program/RUNBOOK.md`; `2026-10-21`'s `2026-10-24-session-handoff.md` and `docs/reviews/2026-10-21/b3-codex-plan-review.md` links → `../../plans/…` / `../../reviews/…`; `2026-10-20c`'s `archive/plans/2026-10-20b-…` and `2026-10-21`'s `archive/plans/2026-10-21b-…` become sibling `2026-10-…` links; `20c`↔`21` sibling links need no change. Recorded `/goal` blocks and the `sed -n '66,85p' docs/plans/…` instruction stay verbatim (session record).
4. Back-links inside already-archived handoffs: `2026-10-17` and `2026-10-19` → `2026-10-18` (sibling), `2026-10-20b` → `2026-10-20c` (sibling), `2026-10-21b:9` and `:74` → `2026-10-21` (sibling).
5. Keep verbatim: `owner-decisions-2026-09-27.md` quoted paths, `docs/agentic/rsi-runs/2026-10-21-laptop/summary.json:27`.
6. Regenerate `docs/INDEX.md` and `docs/_link_graph.json` (`python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`; generated, never hand-merged — contracts §b rule 3, §d SLOT-RULE-2a).

**Files:** the three `git mv`s; edits to `queue.md`, `lane-E-privacy-gates-ci.md`, the three moved files, `docs/archive/plans/2026-10-{17,19,20b,21b}-session-handoff.md`; regenerated index files. No other handoff moves.

**Acceptance:** `python3 scripts/docs_lint.py` clean; `generate_docs_index.py --check` fresh; `grep -rn "docs/plans/2026-10-\(18\|20c\|21\)-session-handoff" docs/ --include='*.md'` returns only the verbatim-keep set (session-record `/goal`/`sed` text).

**Never beside:** another docs PR on `queue.md` or `lane-E-privacy-gates-ci.md` (own lines only — BATCH-1107A/1107B queue rows land in the same file); a PR moving or renaming other handoffs.

**Estimate:** 1 h, `noslot`. **Runtime:** `codex` (+ Claude Code Opus review).

---

## Owner questions drafted

- **SAFETY-MODE-DUPROW-SEMANTICS** — **answered 2026-11-07: option 1** (any-ON authoritative; PATCH writes every row). Recorded in owner-decisions at the BATCH-1107C docs batch.
- **DOC-OVERCLAIM-2** — no new question; the standing answer (:403) requires the docs PR to be owner-reviewed before merge.
- **HANDOFF-ARCHIVE-6** — no new question; destination `docs/archive/plans/` is fixed by the queue bullet and the existing archive.
