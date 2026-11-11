# Plans for FHIR-DOSAGE-FORM, VKF-RANGE-EDIT-PIN, CRIT-LOG-ROUNDED, LOG-DOSE-BADGE-FAILURE, TOAST-TIMER-TEARDOWN, PROGRESS-CLIPPATH, IMPORT-SCANNED-MINORS (+ alternate BREAK-GLASS-320)

**Last Updated:** 2026-11-08 (Opus planner on `9ab89972`, docs batch BATCH-1108A: seven candidate rows planned for runtime `codex` under the owner's chat direction QUIET-PARALLEL-1107, plus one drafted alternate; TOAST-TIMER-TEARDOWN folds SONNER-TEARDOWN-FLAKE — the same `ReferenceError: window is not defined` from a sonner timer after jsdom teardown, two recorded CI instances)
**Owner:** repository owner
**Status:** PLANNED (Opus planner). Docs only. No new owner gates for the seven; the alternate BREAK-GLASS-320 carries a drafted question (BREAK-GLASS-320-PIN) and is not promoted until a primary row dies or the owner answers.
**Base measured:** `origin/main` @ `9ab89972` (2026-11-07, #534 merged). Every `file:line` below was re-read on the docs worktree at `da1a5836` — `9ab89972` plus docs-only commits; `git diff --name-only 9ab89972..HEAD` lists no `src/` file, so product and test code is exactly main. Sonner internals were read on the vendored copy `node_modules/sonner/dist/index.mjs` in the `hc-scratch-meds-main` worktree (same version, `sonner@2.0.8` per `fe/package.json:41`); the build worktree's `node_modules` must be re-read there to confirm the same offsets.
**Refresh Trigger:** a merge that edits `src/backend/modules/fhir_export.py`, `src/backend/tests/test_fhir_export.py`, `src/backend/tests/test_verify_keeps_flag.py`, `src/backend/api/observations.py`, `src/backend/tests/test_interpret_safety_log_scrub.py`, `src/backend/modules/interpret_safety.py`, `src/backend/api/medications.py`, `src/backend/tests/test_medications_routes_http.py`, `src/backend/api/documents.py`, `src/backend/tests/test_documents_api.py`, `src/backend/tests/test_extraction_pipeline.py`, `src/backend/tests/support/minimal_pdf.py`, `src/frontend/src/__tests__/setup.ts`, `src/frontend/src/__tests__/DocumentInbox.test.tsx`, `src/frontend/src/__tests__/ui-feedback.test.tsx`, `src/frontend/src/components/ui/Progress.tsx`, `src/frontend/src/pages/DocumentInbox.tsx`, `src/frontend/src/pages/ExplainAssistant.tsx` or `src/frontend/e2e/ui-ask.spec.ts`; an owner answer to BREAK-GLASS-320-PIN; #535, #537 or #538 leaving the open-PR list; parked #264, #316 or #239 leaving draft; any BATCH-1107A/1107B/1107C row landing.

Queue rows: [queue.md, "Planned 2026-11-01, harness speedup"](2026-10-15-build-program/queue.md#planned-2026-11-01-harness-speedup) (the seven rows append at the end of that table before its `**Done:**` line; promoted from the candidate bullets `IMPORT-SCANNED-MINORS` :621, `PROGRESS-CLIPPATH` :638, `CRIT-LOG-ROUNDED` :659, `LOG-DOSE-BADGE-FAILURE` :666, `SONNER-TEARDOWN-FLAKE` :669 (folded), `FHIR-DOSAGE-FORM` :686, `VKF-RANGE-EDIT-PIN` :687 and `TOAST-TIMER-TEARDOWN` :748; `BREAK-GLASS-320` :698 stays a bullet while alternate). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md) (§10.1 planner checklist, §10.2 Codex CLI), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue (`fe/` = `src/frontend/src`, `be/` = `src/backend`).

**Rules that hold for every row here.**
- **Runtime `codex`** (owner chat 2026-11-07, QUIET-PARALLEL-1107). Codex implements; the review is a Claude Code Opus session (RUNBOOK §1 rule 2), with the lens each row names.
- No row lowers a threshold, relaxes a guard or weakens an assertion to pass. A test named as "must change" changes only as written; any other RED test stops the build for L0 with its ids.
- Route tests go through `tests/support/routes.py::route_client` — never a direct handler call for anything asserting auth, path scoping or status codes (recurring-failures §1).
- Backend pytest always runs as: `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest <files> -p no:cacheprovider -q`. **Collected-count baseline: 4661** (measured on `origin/main` `9ab89972` under pyslot). Each build reports its measured count and delta.
- Frontend acceptance: `cd src/frontend && npx vitest run <files>` then `npx tsc --noEmit`. `node_modules` exists in the build worktrees.
- `git diff --name-only origin/main...HEAD` must print exactly the row's file list.
- **Open PRs checked 2026-11-07** (`gh pr diff <n> --name-only`, carried from the BATCH-1107A/1107B/1107C plan headers; re-check before launch): #538 SAFETY-MODE-VERIFIED-FE (frontend only: `fe/pages/ResultsPage.tsx`, `RangeRibbon.tsx`, `SafetyModeToggle.tsx` note, `fe/__tests__/safety-mode-toggle.test.tsx`, `safety-mode-verified.test.tsx`, `e2e/safety-mode.spec.ts`); #537 C-GC1 (`be/api/export.py`, `be/api/pinboards.py`, `be/api/profiles.py`, profile migration `019`, `be/models/export_artifact.py`, `be/models/__init__.py`, `be/tests/support/migrations.py`, `be/tests/test_audit_order_guard.py`, `test_denial_audit.py`, `test_export_redaction.py`, `test_visit_prep_packet.py`, `test_export_artifact_persistence.py`, **`be/tests/test_fhir_export.py`**, `test_fk_migration_017.py`, and licensed hunks in **`be/tests/test_verify_keeps_flag.py`** — export-store seed/patch lines only); #535 UI-PG-SECURITY (security-section files + `ui-security.test.tsx` + e2e); #316 (draft: `dev.ps1`, `dev.sh`, `README.md`, `test_dev_sh_prereqs.py`); #264 (parked: `api/interpretations.py`, `api/assistant.py`, `modules/rag.py`, `test_audit_order_guard.py`, `test_safe_interp_grounded.py`); #239 (`config/.env.example`, `fe/pages/SettingsPage.tsx`, `test_audit_order_guard.py`). Ready BATCH-1107A rows hold: `fe/services/documents.ts`, `fe/pages/DocumentInbox.tsx`, `fe/pages/VerificationWorkbench.tsx`, `fe/pages/settings/AdvancedSection.tsx`, `be/api/model_settings.py`, `be/modules/interpret.py`, `be/api/interpretations.py`, `be/tests/test_value_range_compare.py`, `be/modules/environment_diagnostics.py`, `config/.env.example`, `dev.sh` (+ new test files). BATCH-1107B rows hold: `fe/__tests__/api.test.ts`, `fe/__tests__/ExplainAssistant.test.tsx`, `be/tests/test_ocr_bbox.py`, **`be/tests/test_extraction_pipeline.py`** (TEST-PLACEHOLDERS and RANGE-ORDER both), `be/tests/test_pyslot_lock_guard.py`, `be/modules/extract.py`, `be/modules/import_structured.py`, `be/api/observations.py`, `fe/services/{observations,medications,timeline}.ts`. BATCH-1107C rows hold: **`be/api/documents.py`**, `be/tests/test_document_extraction_failure.py`, `be/tests/test_cpu_default_model.py`, `fe/__tests__/ProfileSetup.test.tsx`, `be/api/assistant.py`, `be/tests/test_safety_mode_setting.py`, `fe/pages/settings/AssistantPrivacySection.tsx`, `fe/components/MemoryManager.tsx`, `fe/__tests__/a11y-crit-labels.test.tsx`, docs files (`be/models/audit.py` docstring), archived handoffs.
- **RED honesty.** FHIR-DOSAGE-FORM, LOG-DOSE-BADGE-FAILURE (expected — measured first), PROGRESS-CLIPPATH and IMPORT-SCANNED-MINORS (HC-ISP-005/harness absence and the `[2,3,4]` join) have real RED on main. VKF-RANGE-EDIT-PIN and CRIT-LOG-ROUNDED are honest-GREEN test-strengthening rows — each names the mutation-RED the build must paste. TOAST-TIMER-TEARDOWN's queue-empty pin goes real RED without the fix; the teardown crash itself is a CI-recorded race (two instances), not reproducible on demand.

---

## FHIR-DOSAGE-FORM

**Source:** queue.md :686 (found 2026-11-02, #463 ruling 6595064037; measured `call 555-123-4567` by #463 review round 2): "`dosage_form` reaches the FHIR dosage text unredacted (`modules/fhir_export.py:169`, `:175`, `build_medication_statement`). Same class as #463's flag fix under the hard invariant 'redaction before anything leaves'." Kind: PRODUCT (backend; safety/privacy — the export choke point). Lens: security.

**Facts (re-read on `9ab89972`).**
- `be/modules/fhir_export.py` module docstring `:14-20` is the invariant: every free-text string sourced from user or document narrative — "(display name, entity values, quotes, task titles, medication names/instructions, dosage units, document metadata titles, observation analyte names/units, observation flags)" — passes through `RedactionEngine(policy_level="strict")` before entering the bundle; "Structured fields (ISO-8601 dates, numeric values, coded enums like status/frequency) are left as-is."
- `build_medication_statement` `:155-182`: `name` redacted `:160`, `generic_name` `:162`, `dosage_unit` `redact(med.get("dosage_unit"))` `:168` — but `dosage_form` at `:169` is `med.get("dosage_form")` **raw**, and `:174-175` appends `str(form)` into `dosage[].text`.
- `dosage_form` is genuinely free text: `MedicationCreate.dosage_form` is `Optional[str] = Field(None, max_length=50)` (`api/medications.py:96`); no pattern. `frequency`, by contrast, is pattern-locked to a seven-word enum (`api/medications.py:97`, `:111`) — a coded enum the docstring already covers; it is **not** in scope and stays unredacted.
- `redact` is the file-local `_Redactor` (`:49-66`): `engine.redact(text)` per string, `redacted_count` tallied; falsy inputs pass through (`:62-63`), so `redact(med.get("dosage_form"))` is a drop-in.
- `be/tests/test_fhir_export.py` `TestRedaction` (`:373-434`) is the destination: `test_hc_fhir_082` (`:403-434`) already pins analyte/unit/dosage-unit redaction through `build_fhir_bundle` + `json.dumps(result["bundle"])` — the new test is the same shape.

**Fix.** `:169` becomes `redact(med.get("dosage_form"))`; the docstring's field list at `:15-16` gains "dosage forms" (accuracy — the invariant already covers free-text fields by description, the list was incomplete). Nothing else moves; `frequency` stays raw (coded enum).

**Files:** `be/modules/fhir_export.py` (`:169`, docstring `:15-16`), `be/tests/test_fhir_export.py` (`TestRedaction`, one added test). Nothing else. `modules/redaction.py` is **called only, never edited** (ask-first honored).

**Tests (RED first — real defect, no mutation needed).**
- **HC-FHIR-083** `test_hc_fhir_083_dosage_form_is_redacted` (new, appended in `TestRedaction` after `test_hc_fhir_082`): `_med(id="med-1", dosage_form="call 555-123-4567")` → `build_fhir_bundle("Jane Doe", [], [med], [], [], [])` → `assert "555-123-4567" not in json.dumps(result["bundle"])`, `assert "555-123-4567" not in stmt["dosage"][0]["text"]` on the MedicationStatement, `assert result["redaction_count"] > 0`. RED on main (the raw string lands in `dosage.text`).
- **Pin (already green, untouched):** HC-FHIR-020 (`:191-204`) asserts `"tablet" in dosage text` — strict redaction leaves "tablet" alone, so ordinary coded forms survive unchanged.
- **Would not notice:** `frequency` content (enum-locked upstream); `dosage_amount` (numeric).

**Tests that must stay unedited:** `test_verify_keeps_flag.py` (HC-VKF-015/016 exercise the same export path), `test_export_redaction.py`, `test_export_store_purge.py`, `test_export_artifact_persistence.py`, `test_visit_prep_packet.py`, `test_denial_audit.py`, `test_audit_order_guard.py` (all #537-held), `test_documents_api.py`, `test_backup*.py`, e2e `ui-export.spec.ts`.

**Acceptance.**
- The pyslot pytest command on `tests/test_fhir_export.py tests/test_verify_keeps_flag.py`, RED then GREEN for HC-FHIR-083; full suite + collected count delta (expect +1).
- `git diff --name-only origin/main...HEAD` prints the two files.

**Never beside:** **#537 C-GC1** — it holds `be/tests/test_fhir_export.py` (row files, `gh pr diff 537 --name-only` 2026-11-07). Serialize after #537 merges, or rebase — flagged, not substituted. Disjoint from #535, #538, parked #264, #316, #239, and every BATCH-1107A/1107B/1107C file (`be/api/export.py` is #537's caller-side file — untouched here).

**Estimate:** 0.5 h. **Runtime:** `codex` (+ Claude Code Opus review, security lens).

---

## VKF-RANGE-EDIT-PIN

**Source:** queue.md :687 (#463 ruling 6595064037): "nothing pins a range edit on a row with no value (`test_verify_keeps_flag.py`); head is correct (200, `Positive` kept), but a mutant moving the value guard survives." Kind: TEST. Lens: medical-record integrity. **One added test.**

**Facts (re-read on `9ab89972`).**
- The guard chain in `verify_observation` (`api/observations.py:549-559`): `numbers_changed` `:549-552` over `("value","ref_low","ref_high")`; `keeps_flag` `:553-556` (non-normal word); `has_range` `:557` (either bound non-null **after** the edit); `recalculate = (numbers_changed and has_range) or not keeps_flag` `:558`; the recalc block only runs `if recalculate and observation.value is not None` `:559-568`.
- Existing coverage exercises `value=None` only through *plain Verify* (HC-VKF-008's `nv_id` case, `:222-227`: `flag=None`, no edits). Every edit-path test (017-024) seeds `value != None`. So `recalculate=True` + `value=None` + a **stored non-normal flag** is unexercised: a mutant dropping `and observation.value is not None` from `:559` (`None < 12.0` TypeError → 500), or adding an `else:` branch that clears the flag, survives the whole suite.
- `_verify_and_load` (`:80-91`) posts through `route_client`, asserts 200, re-reads the stored row — the shape the new test reuses.

**Test (one added; appended at file end).**
- **HC-VKF-026** `test_hc_vkf_026_range_edit_on_a_row_with_no_value_keeps_the_flag`: seed `flag="Positive", is_abnormal=True, value=None, ref_low=None, ref_high=None`; POST `{"ref_low": 12.0, "ref_high": 16.0}` → `(obs.ref_low, obs.ref_high) == (12.0, 16.0)` (the edit applied), `obs.value is None`, `(obs.flag, obs.is_abnormal) == ("Positive", True)`.
- The file docstring (`:10-14`) gains half a line naming 026's case.

**Honest note — GREEN on `main`.** The route is already right; RED is impossible. Mutation-RED (build pastes it): delete `and observation.value is not None` from `api/observations.py:559` → `None < 12.0` → `TypeError` → the route 500s → HC-VKF-026 fails at the 200 assert. Equivalent second paste: an `else: observation.flag = None; observation.is_abnormal = False` on the `if recalculate and …` — flag erased. Revert after pasting.

**Files:** `be/tests/test_verify_keeps_flag.py` only. `api/observations.py` is never edited (VERIFY-NONFINITE, BATCH-1107B, holds it anyway).

**Tests that must stay unedited:** every existing HC-VKF id, `test_verify_nonfinite.py` (1107B's), `test_panel_canonical_names.py`, `test_value_range_compare.py`, `test_no_range_wording.py`, `test_fhir_export.py` (#537's), `test_observations_audit.py`, `test_audit_order_guard.py` (#537's).

**Acceptance.** The pyslot pytest command on `tests/test_verify_keeps_flag.py`; the mutation-RED paste + revert, then GREEN; full suite + count delta (+1 collected).

**Never beside:** **#537 C-GC1** — its licensed hunks live in `test_verify_keeps_flag.py` (export-store seed lines only, per L0 ruling 6712823856 item 3). Serialize after #537 or rebase — flagged, not substituted. Compatible with VERIFY-NONFINITE's eventual head: `{"ref_low":12,"ref_high":16}` is finite and ordered, so the 200/kept-flag contract survives its new validation; if VERIFY-NONFINITE lands first, re-run the probe on its head.

**Estimate:** 0.5 h. **Runtime:** `codex` (+ Claude Code Opus review, medical-integrity lens).

---

## CRIT-LOG-ROUNDED

**Source:** queue.md :659 (found 2026-10-31, #436 review, shown to the owner in CRIT-LOG-DIFF): "HC-CLS-001/002 would not catch a rounded value or one passed via `extra=`". Kind: TEST. Lens: security/privacy (log redaction).

**Facts (re-read on `9ab89972`).**
- `modules/interpret_safety.py:209-212` and `:220-223` log `logger.warning("Critical value detected: %s below/above critical threshold", analyte_canonical)` — parameterized, analyte only. Production code is correct today (the scrub shipped in #436).
- `test_interpret_safety_log_scrub.py` (78 lines): `test_hc_cls_001`/`-002` use non-round values (`1.937`/`2.513`, `7.193`/`6.487`), assert the needles absent from `r.getMessage()` and `str(r.args)` (`_assert_values_absent`, `:19-26`), and pin `physician_review_reason`.
- **The named blind spot is real:** (a) a mutant logging `round(value,1)` → `"1.9"` or `int(value)` → `"1"` evades the exact-repr needles — `getMessage()` would contain digits but not `"1.937"`; (b) a mutant passing `extra={"value": value}` lands the value in record **attributes**, never in `getMessage()`/`args` — unchecked today.
- Python 3.11 `logging.LogRecord` standard attributes are fixed (name, msg, args, levelname, levelno, pathname, filename, module, exc_info, exc_text, stack_info, lineno, funcName, created, msecs, relativeCreated, thread, threadName, processName, process, taskName) — anything else on `vars(r)` is an `extra=` payload.

**Build (test file only).**
1. Add module-level `_STANDARD_LOG_RECORD_ATTRS` frozenset (the list above) and a helper `_assert_critical_record_clean(record, analyte, direction)`: `record.getMessage()` equals the exact expected sentence (any injected numeric fails); `record.args == (analyte,)` (any added arg — rounded float, threshold — fails); `set(vars(record)) - _STANDARD_LOG_RECORD_ATTRS == set()` (any `extra=` fails).
2. **HC-CLS-004** `test_hc_cls_004_critical_low_record_is_analyte_only`: same call as 001 (potassium, `1.937`, `critical_low=2.513`); find the one WARNING hit; run the clean-record helper; keep the 001-style `physician_review_reason` pin.
3. **HC-CLS-005** `test_hc_cls_005_critical_high_record_is_analyte_only`: mirror for the high path (`7.193`, `critical_high=6.487`).

**Honest note — GREEN on `main`.** The production calls are clean. Mutation-RED pastes (build must run both, then revert): (a) change `:210` to `logger.warning("Critical value detected: %s below critical threshold (%.1f)", analyte_canonical, value)` → `args` carries `1.9`-ish → both new tests fail; (b) add `extra={"value": value, "threshold": c_low}` to `:209-212` → the attrs check fails. Paste, observe RED, revert — `interpret_safety.py` is **ask-first**; the committed diff never touches it (mutation is temporary by definition).

**Files:** `be/tests/test_interpret_safety_log_scrub.py` only.

**Tests that must stay unedited:** `interpret_safety.py` itself (called only), `test_interpret_safety_enforce.py`, `test_interpret_safety_names.py`, `test_no_range_wording.py`, `test_value_range_compare.py`, `test_kb_canonical_names.py`, `test_audit_order_guard.py` (#537's).

**Acceptance.** The pyslot pytest command on `tests/test_interpret_safety_log_scrub.py`; both mutation pastes observed RED then reverted, then GREEN; full suite + count delta (+2).

**Never beside:** nothing open on the file; disjoint from every open PR and all three ready batches.

**Estimate:** 0.5 h. **Runtime:** `codex` (+ Claude Code Opus review, security/privacy lens).

---

## LOG-DOSE-BADGE-FAILURE

**Source:** queue.md :666 (found 2026-11-02, #454; **unmeasured**): "`api/medications.py:1114-1116`, the badge-failure path. The dose is stored, and `DoseResponse.from_model` may 500 after the rollback." Kind: PRODUCT (backend) — **measurement first: the new test exercises the path; the fix is licensed only if it REDs.** Lens: —.

**Facts (re-read on `9ab89972`).**
- `api/medications.py`: dose row built `:1043-1056`, `add`+`commit`+`refresh` `:1058-1060`, `dose_id = dose_record.id` bound at `:1062` (comment: "the badge-failure rollback below expires dose_record"). Badge block `:1064-1121`; `except Exception` → `await profile_db.rollback()` `:1123` + warning log `:1124`. Audit `_audit_after_change(... dose_id ...)` `:1127-1129`. Response `DoseResponse.from_model(dose_record)` `:1136`.
- `DoseResponse.from_model` (`:248-264`) reads 13 instrumented attributes. `Session.rollback()` expires them; attribute access inside an async session then attempts a lazy load → `MissingGreenlet` → the route 500s (the expected measurement), unless the engine keeps them. `expire_on_commit=False` does **not** cover rollback.
- `test_medications_dose_logging.py` calls the handler directly on a `_FakeProfileDb` whose `rollback()` is a counter (`:63-64`) — it cannot see expiry. `test_medications_routes_http.py` `test_hc_audcmed_003_log_dose_badge_failure_still_audits_dose_id` (`:859-877`) monkeypatches `med_api.evaluate_badges_after_dose` to raise, uses `_acm_wire` (`raise_server_exceptions=False`, `:765`), **discards the response** (`:872`) and asserts only the audit call — status and body unpinned.

**Build (measurement first).**
1. Append **HC-AUDCMED-004** `test_hc_audcmed_004_log_dose_badge_failure_returns_the_dose` to `test_medications_routes_http.py`, reusing `_acm_seed`/`_acm_master`/`_acm_wire`/`_acm_send` and the same `evaluate_badges_after_dose` monkeypatch; keep the returned `resp`. Assert `resp.status_code == 201`, `resp.json()["dose"]["id"] == calls[0]["document_id"]`, `resp.json()["newly_earned_badges"] == []`, and the dose row persists (column-select, `_acm_vault_change_present` shape).
2. **If it REDs on main** (expected: 500 from expired `dose_record`): the licensed minimal fix is to bind the response eagerly — at `:1062` beside `dose_id`, add `dose_response = DoseResponse.from_model(dose_record)` (fields are frozen at insert; the comment gains "and the response"), and `:1135-1138` returns `DoseLogResponse(dose=dose_response, newly_earned_badges=newly_earned_badges)`. Alternative if the build prefers: `await profile_db.refresh(dose_record)` after the rollback — one extra read; either is inside the two lines' scope. Audit order, dose persistence and the `newly_earned_badges=[]` semantics do not change.
3. **If it passes on main** (GREEN): ship the test as a pin; no production edit; the PR body records the measurement.

**Files:** `be/tests/test_medications_routes_http.py` (always); `be/api/medications.py` (`:1062` + `:1136`, RED branch only).

**Tests that must stay unedited:** `test_medications_dose_logging.py` (the fake-DB direct-call suite — its contract is the response model, not session expiry), `test_medications_schedules*.py`, `test_badge_evaluation*.py`, `test_gamification*.py`, `test_audit_order_guard.py` (#537's), HC-AUDCMED-001…003.

**Acceptance.** The pyslot pytest command on `tests/test_medications_routes_http.py tests/test_medications_dose_logging.py`; HC-AUDCMED-004's measured outcome stated in the PR body (RED-then-fix or GREEN-pin); full suite + count delta (+1). Mutation-RED if GREEN: `profile_db.expire(dose_record)` after the rollback → 500 → the pin catches it — paste only if the row ships pin-only.

**Never beside:** nothing open on either file; disjoint from #535/#537/#538, parked #264, and all three ready batches (TIMELINE-VERIFY-INVALIDATE holds `fe/services/medications.ts` — the frontend service, not this route).

**Estimate:** 1.5 h (measurement + conditional fix). **Runtime:** `codex` (+ Claude Code Opus review).

---

## TOAST-TIMER-TEARDOWN (folds SONNER-TEARDOWN-FLAKE)

**Source:** queue.md :748 (found 2026-11-06, #507 CI at `a4ebe8bf`): a vitest "Unhandled error", `ReferenceError: window is not defined`, thrown from a sonner timer after jsdom teardown, originating in `ui-provenance.test.tsx`; "the fix would be to clear or flush the toast timers at test teardown; not ruled, and which file owns it is not established." Same failure at :669 (SONNER-TEARDOWN-FLAKE, #465 CI run 41495977227, `sonner/dist/index.mjs:635`, same file, passed on rerun) — **one row folds both bullets.** Kind: TEST (harness hygiene). Lens: —.

**Facts (re-read on `9ab89972`; sonner internals read on `node_modules/sonner/dist/index.mjs`, version 2.0.8 per `fe/package.json:41`).**
- `vitest.config.ts:18-21` setup files: `setupLocalStorage.ts` then `src/__tests__/setup.ts`; environment `jsdom`, `globals: true` (RTL auto-cleanup registered per test file).
- `src/__tests__/setup.ts:61-72` afterEach: `vi.clearAllMocks()`, auth-store reset, `localStorage.clear()` — no sonner cleanup anywhere global.
- Per-file `toast.dismiss()` exists in `ui-feedback.test.tsx:68`, `ui-care.test.tsx:155`, `safety-mode-toggle.test.tsx:121`, `safety-mode-citations.test.tsx:483`, `Gamification.test.tsx:122` — and **`ui-provenance.test.tsx` has none** (`:118-121` afterEach: unstub + `cleanup()` only) while rendering the real `AppToaster` (`:22`) and asserting on real sonner toasts (`:431`,`:450-464`) — the exact gap the CI error named. Per-file coverage has already proven leaky; the single choke point is `setup.ts`.
- **Timer sites in sonner 2.0.8 (`dist/index.mjs`):** `:662-665` — the per-toast auto-dismiss `setTimeout` (`remainingTime`, default 4 s), cleared on unmount by the effect return `:672` — safe; **`:634-636` — `setTimeout(() => removeToast(toast), TIME_BEFORE_UNMOUNT)` (200 ms, `:478`), a bare timer inside `deleteToast` armed by every dismissal cascade — the exact site the CI error names — and NOT cleared on unmount**; `:943-947`,`:951-972` and `:1032` — bare `setTimeout`s in the store subscribers wrapping `ReactDOM.flushSync(setToasts…)`; `:1023` — `requestAnimationFrame` marking `delete: true`. Any of these firing after `window` is deleted → `ReferenceError: window is not defined` via react-dom's event-priority read — matching both CI instances.
- The subscriber timers only arm on publish while a `Toaster` is mounted; the `:634` timer survives RTL `cleanup()` whenever a dismissal was in flight within its last 200 ms. So the teardown contract is: **no toast left queued at each test's end** (dismiss) **plus a wait that outlives 200 ms at file end** (drain).

**Build.**
1. `setup.ts`: `import { afterAll, afterEach, beforeAll, vi } from 'vitest'` (`:7` gains `afterAll`).
2. In the existing `afterEach` (`:61-72`), append:
   ```ts
   // TOAST-TIMER-TEARDOWN: leave no toast queued — a still-live toast keeps
   // sonner's timers armed past jsdom teardown (see afterAll below).
   const { toast } = await vi.importActual<typeof import('sonner')>('sonner');
   toast.dismiss();
   ```
   (`vi.importActual` — the file already uses that pattern at `:65` — so files that mock `sonner` still hit the real store, which they never populated: a no-op.)
3. Append the teardown hook:
   ```ts
   // TOAST-TIMER-TEARDOWN (SONNER-TEARDOWN-FLAKE): sonner arms a bare
   // 200 ms setTimeout(removeToast) inside deleteToast (dist/index.mjs:634-636,
   // the site the CI errors name) plus 0-tick flushSync timers in its
   // subscribers (:943,:951,:1032); none is cancelled on unmount. Dismiss the
   // queue, then outwait the unmount timer so whichever survives fires while
   // `window` still exists — else vitest reports "Unhandled error:
   // ReferenceError: window is not defined" with every test green.
   afterAll(async () => {
     const { toast } = await vi.importActual<typeof import('sonner')>('sonner');
     toast.dismiss();
     if (toast.getHistory().length === 0) return;
     await new Promise((resolve) => setTimeout(resolve, 250));
   });
   ```
   The `getHistory()` gate (`index.mjs:439`) skips the 250 ms in files that never raised a toast — per-file cost ≈0 in the common case, one 250 ms wait in the rest.
4. New spec `fe/__tests__/toast-teardown.test.tsx` — **the ordered pair is the thing under test; name the coupling as intentional:**
   - `it('HC-TTD-001a: a toast left live in the DOM stays in sonner's queue across the boundary', …)` — render `<AppToaster/>`, `act(() => notify({ message: 'Teardown probe' }))`, await `[data-sonner-toast]`; assert `toast.getToasts().length > 0`; deliberately leave it.
   - `it('HC-TTD-001b: the shared teardown dismisses it — getToasts() is empty', …)` — `expect(toast.getToasts()).toHaveLength(0)` — **RED without the fix** (the un-dismissed toast lingers in the module store), GREEN with it.
   - `it('HC-TTD-002: the still-toast path is dismissed too', …)` — same pair through `notify({ still: true, message: 'Value 14.2' })` (covers the other arming shape; may be folded into 001 by parametrize).

**RED honesty.** HC-TTD-001b is real RED on the un-patched setup (queue non-empty). The crash itself is a teardown race — two CI instances recorded; not re-runnable on demand. Mutation-RED for the drain half: remove the `afterAll` → a spec that leaves a dismissing toast at file end is the covered vector; the build pastes the `index.mjs:634-636` read in the PR body as the mechanism evidence (L0 may ask for a deliberately-armed `setTimeout` reproducer pasted from a scratch spec).

**Files:** `fe/__tests__/setup.ts`, `fe/__tests__/toast-teardown.test.tsx` (new). Per-file `toast.dismiss()` calls elsewhere **stay** (harmless; this row does not churn them).

**Tests that must stay unedited:** `ui-provenance.test.tsx` (the origin file — the fix is in the shared harness, not the file), `ui-feedback.test.tsx`, `ui-care.test.tsx`, `safety-mode-toggle.test.tsx`, `safety-mode-citations.test.tsx`, `Gamification.test.tsx`, `ui-toast.spec.ts`, `vitest.config.ts`, every other spec.

**Acceptance.** `cd src/frontend && npx vitest run src/__tests__/toast-teardown.test.tsx src/__tests__/ui-provenance.test.tsx src/__tests__/ui-feedback.test.tsx src/__tests__/Gamification.test.tsx src/__tests__/safety-mode-toggle.test.tsx`, then `npx tsc --noEmit`; HC-TTD-001b RED on the un-patched setup, GREEN after; full vitest run reports zero unhandled errors.

**Never beside:** nothing open on `fe/__tests__/setup.ts`; the new spec file is new. Disjoint from #535/#537/#538 and all ready batches (TIMELINE-VERIFY-INVALIDATE's new spec has a different name — verify `timeline-verify-invalidate.test.tsx` vs `toast-teardown.test.tsx` at launch).

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review).

---

## PROGRESS-CLIPPATH

**Source:** queue.md :638 (found 2026-10-25, #364 L0 ruling): "Progress fill uses `scaleX`, which G5 reads as a transform under reduced motion; move the fill to `clip-path` (not a G5 allowlist) before UI-SHELL runs G5." UI-SHELL has merged (#370); the row stands for every later page row whose G5 samples a route that mounts `Progress` (e.g., `AdvancedSection.tsx`'s download progress). Kind: PRODUCT (frontend; a11y-motion). Lens: —.

**Facts (re-read on `9ab89972`).**
- `fe/components/ui/Progress.tsx` (34 lines): fill `div` at `:28-31` — `className="absolute inset-0 origin-left bg-accent transition-transform duration-[240ms] ease-[var(--ease-out)] motion-reduce:transition-none"`, `style={{ transform: `scaleX(${fraction})` }}`; docstring `:11-14` ("scaleX over 240 ms").
- **Why G5 sees it:** `reducedMotionSnapshot` (`e2e/support/gates.ts:213-230`) scans **every `body *`** under `reducedMotion: 'reduce'` for a non-identity computed `transform`. `scaleX(0.4)` → `matrix(0.4,0,0,1,0,0)` — non-identity **at rest**, not only during the 240 ms transition: any Progress on screen during a G5 snapshot fails the whole check, with no allowlist hook. `clip-path` is not sampled by G5 (and the G10 `analyse()` clip-path compare at `gates.ts:653` only covers `[data-t0]` nodes — the fill has none).
- clip-path is the house pattern already: `SourceTrace.tsx:62-63` (`inset(0 100% 0 0)` → `inset(0 0% 0 0)`), `RangeRibbon.tsx:374`, `EntityDetailView.tsx:99`.
- `ui-feedback.test.tsx` HC-UIFB-005 (`:445-470`): `it('moves the fill with transform: scaleX and sets no width')` pins `fill.style.transform === 'scaleX(0.4)'`, no width, `transition-transform`, no `transition-all` — the spec that must change (named).
- Other `Progress` usage: `AdvancedSection.tsx` download rows (service type `DownloadProgress`); `ui-feedback.test.tsx` is the only spec importing the component (`:25`,`:448`,`:460`).

**Build.**
1. `Progress.tsx` fill: `style={{ clipPath: `inset(0 ${(1 - fraction) * 100}% 0 0)` }}`; classes `absolute inset-0 bg-accent transition-[clip-path] duration-[240ms] ease-[var(--ease-out)] motion-reduce:transition-none` (drop `origin-left`, drop `transition-transform`). Docstring `:11-14` rewords "clip-path over 240 ms … Reduced motion makes the step instant."
2. `ui-feedback.test.tsx` HC-UIFB-005 — retitle the describe to `'Progress reveals with clip-path, never transform or width'`; the ARIA `it` is unchanged; the second `it` becomes: `expect(fill.style.clipPath).toContain('60%')` (jsdom/cssstyle normalisation is not pinned char-for-char), `expect(fill.style.transform).toBe('')`, `expect(fill.style.width).toBe('')`, `expect(fill.className).not.toMatch(/(^|\s)w-/)`, `expect(fill.className).toMatch(/transition-\[clip-path\]/)`, `expect(fill.className).not.toMatch(/transition-transform|transition-all/)`, `expect(fill.className).toMatch(/motion-reduce:transition-none/)`.

**RED honesty.** Real RED on main — the rewritten case fails against `scaleX` before the component change, then GREEN after. No mutation-RED needed; the change is itself the defect's fix.

**Files:** `fe/components/ui/Progress.tsx`, `fe/__tests__/ui-feedback.test.tsx`. Nothing else (`AdvancedSection.tsx`, globals.css, gates.ts untouched).

**Tests that must stay unedited:** every other spec; `e2e/support/gates.ts` (the gate is the contract — not edited); `ui-settings.spec.ts`, `ui-gates-sampler.spec.ts` (#535's).

**Acceptance.** `npx vitest run src/__tests__/ui-feedback.test.tsx`, then `npx tsc --noEmit`. **Quiet box (L0), final head:** G5 sites whose pages can mount a Progress — `ui-settings.spec.ts` (Advanced-section download progress is fixture-driven; grep `Progress|download-progress` in `e2e/*.spec.ts` on the final head and run whichever match).

**Never beside:** nothing open on either file; disjoint from #535/#537/#538 and all three ready batches.

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review).

---

## IMPORT-SCANNED-MINORS

**Source:** queue.md :621 (found 2026-10-24, #347 review): the five MINOR findings — the planner could not re-fetch `gh pr view 347 --comments` (no exec in the planning sandbox); each finding below was re-verified line-by-line on `9ab89972` (line numbers moved from the bullet's citations; flagged where they differ). Kind: TEST + one comment. Lens: —.

**Findings (each verified on `9ab89972`).**
1. **`be/api/documents.py:293-294` comment.** `DocumentImportResponse.pages_without_text` is null on three paths, not the one the comment names: `_run_extraction_pipeline` returns `None` (`:585-586` non-lab types → `:1237-1240` `.get()` → None), the pre-extraction `pending_ocr` early return (`:601-605` — the dict has no key), and the extraction-failure catch (`:722-726` — no key). The OCR-unavailable `pending_ocr` return (`:632-637`) DOES carry it — so `status == "pending_ocr"` does not imply null. **Fix:** widen the `:293-294` comment: "Null when the pipeline did not run, on the pre-extraction `pending_ocr` early return, or when extraction failed." No field or return changes.
2. **No route test for the reprocess wiring.** `POST /{document_id}/reprocess` runs `_run_extraction_pipeline` (`:1231-1240`) and returns `pages_without_text` (`:1274-1279`); `test_HC_FK_020` (`:1394`) exercises reprocess but stubs `ExtractModule` out. **Fix:** append `test_hc_isp_005_reprocess_response_names_the_page_without_text` after `test_hc_isp_002` (`:1390`): the same real-extraction harness (`_PdfIngest` stub + `get_decrypted_document` + `_no_classify` monkeypatches, `:1327-1384`), POST `/documents/import` then `POST /documents/{doc_id}/reprocess`, assert `200` and `body["pages_without_text"] == [2]`. Extract the monkeypatch scaffolding into a module-level `_stub_pdf_import(monkeypatch, tmp_path) -> dict[str,bytes]` so the two tests share it (same de-dup spirit as finding 4; not a third copy).
3. **The three-or-more-page join is untested.** `pagesWithoutTextNotice` (`fe/pages/DocumentInbox.tsx:44-50`, bullet said :42 — moved) does `head = pages.slice(0,-1).join(', ')` + `and ${last}`; HC-ISP-004 (`DocumentInbox.test.tsx:341-367`) covers `[2]`, `[2,3]`, `[]` only. **Fix:** extend the same `it` with a fourth `.mockResolvedValueOnce(importResponse('scan-three','three-scan.pdf',[2,3,4]))` + upload + `findByText('Pages 2, 3 and 4 have no readable text, so their values were not read. Check the original report.')`.
4. **`_text_then_image_pdf` is copied twice** — `test_documents_api.py:1276-1313` (body `import io as _io`) and `test_extraction_pipeline.py:965-1002` (body `import io`), each used once (`:1383`, `:1019`). **Fix:** move it to `tests/support/minimal_pdf.py` as exported `text_then_image_pdf(text_lines) -> bytes` (the file already imports `io` `:9`); both test files `from tests.support.minimal_pdf import text_then_image_pdf` and delete the local defs. Their local `import io` stays — `test_hc_isp_001` (`:1019`) and `test_hc_isp_003` (`:1035`) still need `io.BytesIO`.
5. **Redundant `import io as _io`** at `test_documents_api.py:1278` — the file imports `io` at `:9`. Goes away with the helper move (finding 4); if the move lands separately, the line becomes `io.BytesIO` — either way it does not survive.

**RED honesty.** HC-ISP-005 (reprocess coverage absent → new test) and the `[2,3,4]` join case are real additions — the join case is honest-GREEN on main (the join already produces the right string: `head="2, 3"`, `last=4`) — mutation-RED paste: change `:48` join separator to `'; '` or drop `and ${last}` → "Pages 2; 3 and 4" → RED. HC-ISP-005 is GREEN-expected on main (the wiring exists — it pins it); its mutation-RED: delete `pages_without_text=pages_without_text` from `:1278` → `pages_without_text` null → RED. The comment + de-dup moves are hygiene.

**Files:** `be/api/documents.py` (comment `:293-294` only), `be/tests/test_documents_api.py` (delete `:1276-1313`, imports, `_stub_pdf_import`, `test_hc_isp_005`), `be/tests/test_extraction_pipeline.py` (delete `:965-1002`, import), `be/tests/support/minimal_pdf.py` (`text_then_image_pdf`), `fe/__tests__/DocumentInbox.test.tsx` (the one `it`).

**Tests that must stay unedited:** `test_ocr_rapid.py` (route harness at `:385-438` mirrors the same shape — no change), `test_document_extraction_failure.py` (DOC-EXC-LOGGING's new file), `test_document_import_classification.py`, `test_embedding_fail_closed_paths.py`, `test_visit_note_extraction.py`, `fe/pages/DocumentInbox.tsx` (OCR-COPY-ENGINE's, untouched — the notice text is read, not edited), every e2e spec.

**Acceptance.**
- The pyslot pytest command on `tests/test_documents_api.py tests/test_extraction_pipeline.py tests/test_ocr_rapid.py`; HC-ISP-005 GREEN, both mutation pastes observed.
- `cd src/frontend && npx vitest run src/__tests__/DocumentInbox.test.tsx`, `npx tsc --noEmit`.
- Full backend suite + count delta (+1 collected for HC-ISP-005).
- `git diff --name-only origin/main...HEAD` prints the five files.

**Never beside:** **DOC-EXC-LOGGING** (BATCH-1107C; holds `be/api/documents.py` and re-runs `test_documents_api.py`), **TEST-PLACEHOLDERS** and **RANGE-ORDER** (BATCH-1107B; both hold `be/tests/test_extraction_pipeline.py`) — this row lands **after** those three merge or rebases onto them. Flagged hard, not substituted: the findings' files are fixed by the bullet. Disjoint from #535/#537/#538, #264, #316, #239, OCR-COPY-ENGINE (its `DocumentInbox.tsx` is untouched — only the test file is edited here) and DELETED-DOC-NAMES-TIMELINE.

**Estimate:** 1.5 h. **Runtime:** `codex` (+ Claude Code Opus review).

---

## ALTERNATE — BREAK-GLASS-320 (not promoted unless a primary row dies/conflicts or the owner answers)

**Source:** queue.md :698 (found 2026-11-03, #453 body): "at 320x640 on `/explain` the break-glass warning leaves the screen when the patient scrolls to the disclaimer. D12 and W6-Q3 are met as written (shown at first paint, `role="alert"`); the on-screen keyboard was not measured." Kind: PRODUCT (frontend; privacy-surface display). Lens: UX/privacy. **Owner gate: BREAK-GLASS-320-PIN — do not build until answered** (the spec is met as written; pinning is an enhancement beyond the ruling).

**Facts (re-read on `9ab89972`).**
- `ExplainAssistant.tsx:885-889`: the warning wrapper is `mx-4 mt-4 shrink-0` — normal flow at the card's top, outside the scrollable `role="log"` list (`:891-901`). The card's `min-h-min` (`:846-852`, comment `:840-845`) grows it past a short viewport so **the window scrolls** to reach the disclaimer (`data-testid="ask-disclaimer"`, `:1043`) — and the warning scrolls off the top with it. The comment at `:892-895` claims it "stays pinned" — pinned only means "outside the list".
- `ExternalApiBreakGlassWarning.tsx:35-47`: `role="alert"`, `data-t0`, fixed D12 text; `Card` (`Card.tsx:7`) sets no overflow — `position: sticky` against the window scrollport is viable.
- `e2e/ui-ask.spec.ts`: `openAsk(page, viewport, {breakGlass: true})` (`:220-277`); `cardLayout` (`:441-498`) already measures `breakGlass.found`/`inList` and scrolls composer+disclaimer into view (`:469-476`) — it captures the warning **after** `window.scrollTo({top:0})` at `:480`, so `:532`'s `toBeInViewport` only proves first paint. `SMALL_PHONE` 320×640 states exist at `:509-510`.

**Build (option 1 only — under the owner answer).**
1. `ExplainAssistant.tsx:886` wrapper gains `sticky top-[var(--shell-top-h,4rem)] z-10` (+ optional `bg-surface-elevated` so the 16 px side rails cover scrolled-under content — cosmetic detail left to the implementer, both are inside the licence).
2. `ui-ask.spec.ts` `cardLayout` `breakGlass` measurement gains `inViewAfterDisclaimerScroll`: capture `bg.getBoundingClientRect()` immediately after `disclaimerReach` (before the `:480` reset), flag `rect.top >= headerBottom - 0.5 && rect.bottom <= limit + 0.5`; the `if (state.options.breakGlass)` branch (`:528-533`) asserts it. **Real RED on main** — the warning's rect is above the header bound when the disclaimer is scrolled into view.
3. Warning placement/text/role — **unchanged** (D12/W6-Q3 preserved verbatim).

**Files (option 1):** `fe/pages/ExplainAssistant.tsx` (`:886`), `e2e/ui-ask.spec.ts` (`:441-498`, `:528-533`). **Option 2** ("leave as-is — spec met, close as measured"): docs-only flip, no code.

**Tests that must stay unedited:** `ExplainAssistant.test.tsx` (FE-401-MOCKS's), `ExternalApiBreakGlassWarning.test.tsx`, `ui-settings.test.tsx`, `ResultsPage.test.tsx`, `ui-results.test.tsx`, every other e2e spec.

**Acceptance.** `npx vitest run src/__tests__/ExplainAssistant.test.tsx` + `npx tsc --noEmit`; quiet-box `ui-ask.spec.ts` by L0 (the assertion is a rect probe, not a timing gate — deterministic).

**Never beside:** nothing open on either file (`fe/pages/ExplainAssistant.tsx` vs FE-401-MOCKS's `fe/__tests__/ExplainAssistant.test.tsx` — disjoint). #535/#537/#538 disjoint.

**Owner question drafted: BREAK-GLASS-320-PIN**
> At 320×640 on `/explain`, the break-glass warning scrolls off the screen when the patient scrolls down to the disclaimer. D12 and W6-Q3 are met as written (it shows at first paint, `role="alert"`). The page comment already says it "stays pinned". What should it do on small screens?
1. **Pin it — `position: sticky` under the shell header (Recommended).** One wrapper change at `ExplainAssistant.tsx:886` plus an e2e rect assertion; realises the comment's stated intent; no text, role or D12 rule changes.
2. **Leave it — the spec is met.** Record the measurement, close the bullet; no code change.

**Estimate:** 1 h (option 1). **Runtime:** `codex` (+ Claude Code Opus review, UX/privacy lens).

---

## Owner questions drafted

- **BREAK-GLASS-320-PIN** — drafted above; **asked only if the alternate is promoted** (one of the seven dies or conflicts). Question + two options verbatim above.
- **FHIR-DOSAGE-FORM** — no gate: the docstring invariant mandates redaction of free-text narrative; `modules/redaction.py` is called only. Merge review uses the security lens.
- **LOG-DOSE-BADGE-FAILURE** — no gate: the measurement decides the branch; both branches (pin-only vs the two-line bind) are inside safety norms.
- All others — no product decisions.
