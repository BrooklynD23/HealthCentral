# Plans for DELETED-DOC-NAMES-TIMELINE, PANEL-WITHHELD-FIRSTGEN and OCR-COPY-ENGINE

**Last Updated:** 2026-11-10 (BATCH-1110B: row 3 of the OCR-COPY-TEXT table shortened by owner answer OCR-HEIGHT-SHORTEN); 2026-11-07 (Opus planner on `9ab89972`, docs batch BATCH-1107A: the three rows that said "needs planning detail before a build-item starts", planned for runtime `codex` under the owner's chat direction QUIET-PARALLEL-1107)
**Owner:** repository owner
**Status:** PLANNED (Opus planner). Docs only. **Owner answers recorded 2026-11-07** ([owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)): **PANEL-WITHHELD-WORDING** — asked by L0 with a differently-framed option set ("Count only (Recommended)" / "Named" / "Response flag + UI badge"), answered "Count only"; confirmed against this plan's drafted option 1 (fail closed) in a follow-up: **"Keep Count only"**. **OCR-COPY-TEXT** — "Approve proposed copy (Recommended)" on L0's shown strings, then **"Approved strings + table fills gaps (Recommended)"**: the owner-approved strings below (marked †) plus this table's remaining rows. **OCR-BLOCKER-CODE** — "Keep code, change label (Recommended)". **OCR-DEVPS1-SCOPE** — "Leave it; note for later (Recommended)". The build sections below are updated for those answers.
**Base measured:** `origin/main` @ `9ab89972` (2026-11-07, #534 merged). Every `file:line` below was re-read on that commit. Product code was read only. One backend probe ran on a scratch copy (`git archive` of `9ab89972` in `/dev/shm`, outside any worktree, under `scripts/pyslot.sh`); its output is pasted under PANEL-WITHHELD-FIRSTGEN.
**Refresh Trigger:** a merge that edits `src/frontend/src/services/documents.ts`, `src/frontend/src/pages/TimelinePage.tsx`, `src/backend/modules/interpret.py` (`interpret_panel`), `src/backend/api/interpretations.py` (panel route), `src/frontend/src/pages/settings/AdvancedSection.tsx`, `src/backend/modules/environment_diagnostics.py`, `dev.sh` or `config/.env.example`; an owner answer to PANEL-WITHHELD-WORDING or OCR-COPY-TEXT; #316 or #239 leaving draft.

Queue rows: [queue.md, "Planned 2026-11-01, harness speedup"](2026-10-15-build-program/queue.md#planned-2026-11-01-harness-speedup) (the three rows sit at the end of that table). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md) (§10.1 planner checklist, §10.2 Codex CLI), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue.

**Rules that hold for every row here.**
- **Runtime `codex`** (owner chat 2026-11-07, QUIET-PARALLEL-1107: "Pass /codex to continue building them out too"). Codex implements; the review is a Claude Code Opus session (RUNBOOK §1 rule 2), with the lens each row names. Codex has no network in its sandbox (§10.2), so Playwright quiet-box acceptance is L0's.
- No row lowers a threshold, relaxes a guard or weakens an assertion to pass. A test named as "must change" changes only as written; any other RED test stops the build for L0 with its ids.
- Route tests go through `tests/support/routes.py::route_client`.
- **Open PRs checked 2026-11-07** (`gh pr diff <n> --name-only`): #538 SAFETY-MODE-VERIFIED-FE (claim, empty diff; its row names `fe/pages/ResultsPage.tsx`, `fe/components/results/RangeRibbon.tsx`, `e2e/safety-mode.spec.ts` and its tests); #537 C-GC1 (`api/export.py`, `api/pinboards.py`, `api/profiles.py`, `models/__init__.py`, `models/export_artifact.py`, profile migration `019_export_artifacts.py`, `tests/support/migrations.py`, `tests/test_audit_order_guard.py`, `test_denial_audit.py`, `test_export_artifact_persistence.py`, `test_export_redaction.py`, `test_visit_prep_packet.py`); #535 UI-PG-SECURITY (`e2e/support/gates.ts`, `e2e/ui-gates-sampler.spec.ts`, `e2e/ui-security.spec.ts`, `BackupRestoreFlow.test.tsx`, `ui-security.test.tsx`, `components/settings/BackupCard.tsx`, `DangerZone.tsx`, `RecoveryCodeCard.tsx`, `pages/settings/SecuritySection.tsx`); #316 (draft: `README.md`, `dev.ps1`, `dev.sh`, `test_dev_sh_prereqs.py`); #264 B-3 (parked draft: `api/interpretations.py`, `api/assistant.py`, `modules/rag.py`, `tests/test_audit_order_guard.py`, `tests/test_safe_interp_grounded.py` and others); #239 RSI1-DONATE PR-2 (blocked draft: `config/.env.example`, `pages/SettingsPage.tsx`, `tests/test_audit_order_guard.py` and others). STILLNESS-NAV-LATE has no open PR: its Task 3 merged as #514, and what is left is L0's quiet-box measurement on `main`.
- **RED runs.** The backend probe for PANEL-WITHHELD-FIRSTGEN ran (below). The two frontend rows' RED runs were **not** run by the planner: neither the main checkout nor this worktree has `src/frontend/node_modules`, and an install on `/mnt/e` is not cheap (RUNBOOK §10.1 checklist item 3). Each build pastes its RED output.

---

## DELETED-DOC-NAMES-TIMELINE

**Source:** #487 (UI-PG-RECORDS, merged `5cd5959d`) body, "For L0" item 3, measured by its security lens: "a deleted document's analyte names stay on `/timeline` for up to 5 minutes. `services/` is off limits here. Fix: `useDeleteDocument` and import invalidate `['timeline']` and `['observations']`; reprocess and verify invalidate `['timeline']`." L0 ruling 6651066872 (2026-11-04) item 2 asks for this row. Kind: PRODUCT (frontend; query invalidation). Lens: security (deleted data on screen).

**Facts (re-read on `9ab89972`).**
- The query client keeps every query for 5 minutes: `staleTime: 1000 * 60 * 5` (`fe/App.tsx:94`). `useTimeline` keys on `['timeline', filters]` (`fe/services/timeline.ts:58-62`). `TimelinePage` is its only caller (`fe/pages/TimelinePage.tsx:195`).
- **Half of the stated fix is already on `main`.** UI-OVERVIEW (#507, merged `961e36bc`; commit `ee5dbeec`, after #487) added `['observations']` to import and delete. On `9ab89972` all four mutations invalidate `[QUERY_KEY]` (`'documents'`) and `['observations']`, and **none** invalidates `['timeline']`:

  | Hook | Line | `onSuccess` | invalidates |
  |---|---|---|---|
  | `useImportDocument` | `:104` | `:110-113` | `documents`, `observations` |
  | `useDeleteDocument` | `:117` | `:122-125` | `documents`, `observations` |
  | `useReprocessDocument` | `:129` | `:134-137` | `documents`, `observations` |
  | `useVerifyDocument` | `:141` | `:146-149` | `documents`, `observations` |

- What a patient sees on `main` now (by reading, not run): after a delete, the cached timeline still holds the deleted document's lab card for up to 5 minutes. The observations are refetched, so the card's ids no longer match. `needsRefresh` needs the observations to be older than the timeline (`TimelinePage.tsx:232-233`), and here they are newer, so nothing refreshes. The card then shows with its backend title ("Lab results (N analytes)") and no names. #487 measured the names staying because `['observations']` was not invalidated then. **The defect that is left is the card itself.**
- `TimelinePage.tsx:223` ("an import does not invalidate them") and `ui-records.test.tsx:449` ("which useImportDocument does not invalidate") have been stale since #507. This row does not edit them (see "Not in this row").

**Fix.** One line in each of the four `onSuccess` blocks: `queryClient.invalidateQueries({ queryKey: ['timeline'] });`, beside the two that are there. Prefix matching covers every filtered key (`['timeline', {event_type: 'lab_results'}]`). A literal key, like `['observations']` beside it: no shared constant, no import from `timeline.ts`.

**Files:** `fe/services/documents.ts` (the four `onSuccess` blocks above, one added line each; nothing else), `fe/__tests__/deleted-doc-names-timeline.test.tsx` (new, HC-DDNT-001…005). Nothing else.

**Tests (RED first).**
- **HC-DDNT-001 (the reported defect, through the page).** Client as the app has it (`staleTime: 300_000`, `retry: false`). The timeline answers one lab card for `doc-1` (`related_ids` `o-1`, `o-2`), and the observations name them Glucose and LDL. Mount `TimelinePage` and wait for the names, then unmount. The server now answers the timeline and the observations with nothing. Run `useDeleteDocument().mutateAsync('doc-1')` (`renderHook`, same client), then mount `TimelinePage` again. **No timer advances.** Assert that the card title and both names are absent and that `/timeline/` was asked for a second time. Also cache `['timeline', {event_type: 'lab_results'}]` before the delete and assert `isInvalidated` on it. RED on `main`: the card is still there (by reading; the build pastes the run).
- **HC-DDNT-002 / 003 / 004.** A mounted `useTimeline()` observer (as `TimelineService.test.tsx` mounts one). After `useImportDocument` (`apiUpload` mocked), `useReprocessDocument` and `useVerifyDocument` each succeed, `/timeline/` is fetched again. RED on `main`.
- **HC-DDNT-005 (pin, GREEN on `main`).** Each of the four still invalidates `['documents']` and `['observations']`, so the new line replaces neither.
- **Would not notice:** a failed mutation (`onError`), which invalidates nothing before or after this change and is not tested. Other pages that cache document-derived data (Overview counts are already covered by HC-UILAND-002; Results, search and pinboards are not in this row).

**Tests that must stay unedited** (each still passes, by reading): `ui-landing.test.tsx` HC-UILAND-002 (real hooks; invalidating an absent `['timeline']` query changes nothing), `ui-records.test.tsx` (the HC-UIPIN-001 cases call `removeQueries({ queryKey: ['timeline'] })` themselves), `DocumentInbox.test.tsx` (mocks the hooks, `:34-36`), `VerificationWorkbench.test.tsx`, `TimelineService.test.tsx`, `e2e/ui-records.spec.ts`, `e2e/ui-documents.spec.ts`. No e2e assertion changes. The inbox and `/verify` do not mount the timeline, so the added invalidation causes no fetch on those pages and no G10 change.

**Acceptance.**
- `cd src/frontend && npx vitest run src/__tests__/deleted-doc-names-timeline.test.tsx src/__tests__/ui-landing.test.tsx src/__tests__/ui-records.test.tsx src/__tests__/TimelineService.test.tsx src/__tests__/DocumentInbox.test.tsx src/__tests__/VerificationWorkbench.test.tsx`, with RED then GREEN pasted for HC-DDNT-001…004.
- `npx tsc --noEmit`.
- `git diff --name-only --no-renames origin/main...HEAD | python3 scripts/change_scope.py` (expect `backend=false`, `frontend=true`); CI Frontend Tests and E2E green.
- `git diff --name-only origin/main...HEAD` prints the two files.
- No quiet box: no rendering changes.

**Never beside:** another PR on `fe/services/documents.ts` or `fe/pages/TimelinePage.tsx`. It is file-disjoint from #535, #537 and #538.

**Not in this row:** the two stale comments above. They are a comment-only follow-up that L0 may fold into any later `TimelinePage.tsx` row (mode 8, stale guidance). Invalidation for observation edits and deletes (`services/observations.ts:94-96`).

**Estimate:** 1 h. **Runtime:** `codex` (+ Claude Code Opus review, security lens).

---

## PANEL-WITHHELD-FIRSTGEN

**Source:** L0 ruling 6656962109 on #492 (VALUE-RANGE-COMPARE, merged `0b7e3587`), "Still report only: a first-generation member with **no** saved card, withheld and dropped, as on main (HC-VRC-027). L0 opens a row for it." Kind: PRODUCT (backend; medical wording). Lens: medical safety. **Owner question: PANEL-WITHHELD-WORDING** (below; the answer decides the build).

**Facts (re-read on `9ab89972`).**
- `interpret_panel` (`be/modules/interpret.py:413-617`) fetches each member's card through `interpret_observation` (`:489-493`). A member the safety check withholds is kept in `withheld_members` only when the read replaces a saved panel or the member had a saved card (`:496-505`). Otherwise the member falls through. It has no `interpretation`, so it adds nothing to `observation_summaries` (`:506-525`). Its id is still written into `observation_ids_json` (`:488`, `:588`).
- The summary counts only the summarised members: `f"{normal_count} of {len(observation_summaries)} values are within normal range."` (`:1531-1532`). `overall_status` counts `abnormal_count` over the summarised members only (`:546-554`).
- The route writes `interpretation.withheld` rows only for `result.withheld_members` (`be/api/interpretations.py:929-930`), so a dropped member writes **no** withheld row.
- A withheld card saves nothing (`interpret.py:335-347`, "Nothing is saved, deleted or committed before this return").
- The comment pin is `test_value_range_compare.py:2484-2486` ("Report only, as on main (HC-VRC-027): a first-generation member with NO saved card, withheld, is dropped and the panel is created"). HC-VRC-027 itself (`:1936-`) tests single cards. **No test asserts the drop** (`_withhold_for` is used only in HC-VRC-030 and 031, `:2527-2800`).

**Planner probe (scratch copy of `9ab89972`, one test appended to a copy of `test_value_range_compare.py` that reuses its fixtures):** cmp panel of two verified members, glucose 300 (range 70-100) and sodium 140; no saved panel and no saved card; glucose withheld with `_withhold_for("glucose")`; then `_read_panel` twice.

    PROBE status 201
    PROBE overall_status normal
    PROBE summary 'Your Comprehensive Metabolic Panel results:\n\n1 of 1 values are within normal range.\n\nThis summary is for educational purposes only. Please consult your healthcare provider for personalized interpretation.'
    PROBE glucose cards 0
    PROBE sodium cards 1
    PROBE audit [('interpretation.panel_generate', None)]
    PROBE read2 201 normal True
    E       assert 201 == 500
    WARNING  modules.interpret:interpret.py:339 Withholding interpretation for observation a63105e1-…: safety checks failed: ['prohibited_dosing_recommendation', 'prohibited_medication_advice']
    1 failed, 1048 deselected, 1 warning in 2.19s

So a two-member panel with a glucose of 300 reads "1 of 1 values are within normal range." and `normal`. It writes no withheld row, it is **saved** (read 2 returns the same row, `True`), and it keeps reading normal. The final assert is option A's RED shape (expects 500).

**Ask-first check (CLAUDE.md §1).** None of the options edits `be/modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py` or any auth file. The withhold decision (`safety_result.passed`, `interpret.py:337-347`) and `_apply_critical_check` stay as they are. `be/modules/interpret.py` is not on the §1 list, but L0 treats it as ask-first (rows VALUE-RANGE-COMPARE and KEPT-FLAG-DISAGREES). The owner's answer to PANEL-WITHHELD-WORDING is the licence for the lines its option names, and for nothing else in that file. If a build finds it needs `interpret_safety.py`, it stops: that is an ask-first edit, and no option here licenses it.

### Owner question: PANEL-WITHHELD-WORDING — **answered 2026-11-07: "Keep Count only"**

L0 first asked the question with a different option set; the owner answered "Count only (Recommended)": "One result in this panel could not be checked and is not counted in this summary. Please review it with your healthcare provider." L0 then showed the drafted option 1 (fail closed, the HC-VRC-031 rule) in a follow-up, and the owner kept Count only. The drafted options stay below as the record; the build is the **Count-only build** section after them.

> When one result in a lab panel cannot be explained (the safety check withholds its card) and it never had a saved card, the panel today leaves it out and can read "normal": a panel with a glucose of 300 says "1 of 1 values are within normal range." What should the panel do?

1. **Fail the panel closed, as for a result that had a card (Recommended).** The panel read answers the existing escalation message (`ESCALATE_TEMPLATE`, "This is a question for your doctor or pharmacist. …"; on the Results page the panel card shows today's "Failed to load interpretation"). It saves no panel and writes one `interpretation.withheld` audit row per withheld result. Cards for the other results that are made on the way stay (they are true). This is the rule HC-VRC-031 already applies when the result had a saved card (L0 ruling 6656962109 item 3). There is no new wording. Cost: while that result keeps being withheld, the panel summary cannot be shown at all.
2. **Show the panel, name the gap, never "normal".** The panel is saved, and the withheld result is named and counted: the count line uses every member ("1 of 2 values are within normal range."). A new line follows the items needing attention: "1 result in this panel has no summary here: GLUCOSE. Open it on its own to see why." `overall_status` is a new value, `incomplete`. The saved panel counts as stale while a member it lists has no card, so it is rebuilt once that result has one. New patient-facing wording (the owner approves the exact sentence) and a new status value, which the panel card shows as a plain badge (`PanelInterpretationDashboard.tsx` `statusVariant` falls back to `default`).
3. **Keep today's behaviour (report only).** No code change. The drop stays a known limit, recorded in `test_value_range_compare.py:2484-2486` and here.

**Why 1 is recommended:** it is the smallest change: one condition, no new copy and no route edit. It gives the panel route one rule for a withheld member, whatever that member's history. It keeps the row off `api/interpretations.py` and `tests/test_audit_order_guard.py`, which #264 and #537 hold. It is the conservative choice for a health app (CLAUDE.md §1): a panel that cannot account for a result says nothing rather than "normal".

### Count-only build (the owner's answer)

The panel is still created and saved, the dropped member stays out of `observation_summaries` and keeps its id in `observation_ids`, and the summary discloses the gap **by count, never by name**: the withheld member's analyte never appears. `overall_status` still counts the checked members only; the notice is the disclosure. `requires_physician_review` is `True` when any dropped member's own check had set it (`interpret.py:330-333` sets it before the withhold), so a critical flag is not lost with the card.

**Files:** `be/modules/interpret.py`, in `interpret_panel` and `_generate_panel_summary` only; `be/api/interpretations.py`, the withheld-audit loop at `:929-930` only; `be/tests/test_value_range_compare.py` (the places named below only).

1. `interpret_panel` (`:487-537`): on the withheld fall-through (the member that today silently drops — `stale_panel is None` and `obs.id not in saved_card_ids`), collect `obs.id` in a new `withheld_dropped_ids` list (a field on the result object beside `withheld_members`, or a parallel return — whichever touches fewer signatures). The member still adds nothing to `observation_summaries`; its id still lands in `observation_ids_json` as it does at `:488`/`:588`. Keep each dropped member's `requires_physician_review` bit: `result.requires_physician_review` is `True` if any summarised **or** dropped member set it.
2. `_generate_panel_summary` (`:1495-1541`): gains the count (a parameter or the same result field). Emit the existing `"N of M values are within normal range."` sentence only when `observation_summaries` is non-empty — an all-withheld panel must not print "0 of 0". When the count is non-zero, append, verbatim:
   - count 1: `"One result in this panel could not be checked and is not counted in this summary. Please review it with your healthcare provider."`
   - count N>1: `"N results in this panel could not be checked and are not counted in this summary. Please review them with your healthcare provider."` (the digit; L0's mechanical plural of the approved sentence — the owner sees it in the pre-merge diff).
3. `be/api/interpretations.py` `:929-930`: the loop also writes one `interpretation.withheld` row per id in the dropped list — same row shape as today, `entity_id` the observation id, **no analyte name or value** in details (ruling 6656962109 item 2's convention). Same audit action, so `test_audit_order_guard.py` needs no change and stays unedited. (The file is held only by parked #264, which rebases under contracts §b rule 2; #537 does not hold it.)

**Tests (HC-VRC-033, RED first on `main`; appended after HC-VRC-032, reusing `rdbs`, `_withhold_for`, `_read_panel`, `_fire`, `_assert_closed`, `_audit_pairs`, `_rows_of`, `_no_phi`, `_WriteSpy`; the module docstring gains an HC-VRC-033 line after `:41`, and the `:2484-2486` comment is corrected to the new contract):**
- **(a)** The probe's state: 201; `summary_text` contains the singular notice verbatim and `"1 of 1 values are within normal range."`; `"GLUCOSE"` (case-insensitive) absent from `summary_text`; the glucose id still in `observation_ids`; `overall_status` `normal`; `_audit_pairs` contains one `("interpretation.withheld", <glucose id>)` row with no analyte or value in details; the sodium card exists; `_no_phi`. RED on `main` (the probe answered 201 with no notice and no withheld row).
- **(b)** A second read serves the same saved panel (the notice persists; no second `panel_generate` write).
- **(c)** `force=True` rebuilds: 201 with the notice again, and one more withheld row.
- **(d)** Both members withheld: 201; the plural notice with the digit; **no** `"0 of 0"` counts sentence; two withheld rows.
- **(e)** A withheld member whose check had set `requires_physician_review`: the response field is `true`.
- **(f) (pin, GREEN on `main`):** no member withheld, so the response shape is exactly today's and the notice is absent.
- **Would not notice:** a withheld member on the batch route (HC-VRC-032 covers it), and the frontend's rendering (the notice rides `summary_text`, unchanged structurally).

**Tests that must stay unedited (any RED among them stops the build for L0; it would mean a fixture whose real template card is withheld):** every HC-VRC-001…032 assertion (HC-VRC-027's `201` and `"GLUCOSE" not in summary_text` survive: the notice names no analyte); `test_kb_canonical_names.py` (HC-KCN-003 calls `interpret_panel`, `:475`, `:529`, `:558`); `test_panel_canonical_names.py`; `test_safe_interp_grounded.py`; `test_safety_mode_verified.py`; `test_utc_sweep_http.py`; `test_interpret_withhold_msg.py`; `test_interpret_safety_enforce.py`; `test_audit_order_guard.py`.

**Acceptance.**
- `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_value_range_compare.py tests/test_kb_canonical_names.py tests/test_panel_canonical_names.py tests/test_safe_interp_grounded.py tests/test_safety_mode_verified.py tests/test_utc_sweep_http.py tests/test_interpret_withhold_msg.py tests/test_interpret_safety_enforce.py tests/test_audit_order_guard.py -p no:cacheprovider -q`, with RED then GREEN for HC-VRC-033 (a)-(e).
- The full backend suite (RUNBOOK §6 step 2) and the collected count with its delta.
- `git diff --name-only origin/main...HEAD` prints the three files.
- **Merge-only gate (medical wording):** the owner sees the exact `summary_text` diff — the singular and plural sentences as generated — before merge (the convention of SAFETY-MODE-NOTE-WORDING).

**Never beside:** another PR on `be/modules/interpret.py` or `be/tests/test_value_range_compare.py` (none open on 2026-11-07). `be/api/interpretations.py` is held only by parked #264 (contracts §b rule 2: it rebases). If the build would need `be/tests/test_audit_order_guard.py`, it stops (#537 holds it): the withheld rows reuse the existing action, so it must not. No frontend file is touched, so it is disjoint from #538 (`ResultsPage.tsx`).

**Estimate:** 2 h. **Runtime:** `codex` (+ Claude Code Opus review, medical-safety lens).

---

> **Delta 2026-11-10 (BATCH-1110A; owner answers relayed by L0): PANEL-WITHHELD-WORDING (residual) and PANEL-ALL-WITHHELD-STATUS.**
> - The two sentences at `be/modules/interpret.py:1567-1578` are approved as built ("Text OK; all-withheld not normal (Recommended)").
> - New fix, in the same row before merge: a panel where **every** member is withheld never shows `overall_status` "normal". The first answer was "no status"; the second answer (PANEL-ALL-WITHHELD-STATUS, 2026-11-10) chose **"incomplete" (Recommended)**: an all-withheld panel gets `overall_status` "incomplete" (no migration, no API change; the frontend shows the default badge). This supersedes "no status".
> - Test (d) below changes: HC-VRC-033(d) was report-only (it recorded that an all-withheld panel still read "normal"); it now asserts `overall_status == "incomplete"` and not "normal". The built branch has this at `6d00b325` (HC-VRC-033(d) RED then GREEN, 1120 passed, ruff clean).
> - The earlier line in this plan, "`overall_status` `normal`" for case (a) and "`overall_status` still counts the checked members only", stays true for panels with at least one checked member.

## OCR-COPY-ENGINE

**Source:** #498 (RAPIDOCR-BUNDLE, merged `8b59d35a`, "read scans with bundled RapidOCR once the patient opts in") review round 1 finding 6 (comment 6656935102). "Task 6 makes `pending_ocr` the first thing a new patient sees after importing a scan, and it says to install software they do not need." Kind: PRODUCT (frontend and backend copy, launcher text). **Owner question: OCR-COPY-TEXT** (merge-only; the build uses the Recommended strings).

**Facts (re-read on `9ab89972`).** RapidOCR is read first and Tesseract is the fallback (`modules/extract.py:227-247`). The blocker code `tesseract_missing` means neither engine is available (`core/config.py:337-358`, engine test `:350-353`). The code is an API value pinned by tests (`test_config_validation.py:170`, `test_ocr_rapid.py:775`, `:788`, `:790`), so **it stays**; only its UI label changes. The row's `SettingsPage.tsx` lines moved to `fe/pages/settings/AdvancedSection.tsx` (UI-PG-SETTINGS split the page). The OCR switch sits **above** the status box (`AdvancedSection.tsx:543-550` before `:551`), so the label "Turn on document OCR below" is wrong as well.

### Owner question: OCR-COPY-TEXT — **answered 2026-11-07: "Approved strings + table fills gaps"**

The owner approved the copy twice: "Approve proposed copy (Recommended)" on the strings L0 showed (rows marked † below use that approved wording verbatim), then "Approved strings + table fills gaps (Recommended)" when shown that this table existed alongside — so every un-† row below stands as drafted. Two related answers: **OCR-BLOCKER-CODE** "Keep code, change label (Recommended)" (the `tesseract_missing` API value stays; only its label changes) and **OCR-DEVPS1-SCOPE** "Leave it; note for later (Recommended)" (`dev.ps1` untouched; candidate OCR-DEVPS1-INSTALLS). The owner sees the exact patient-visible diff before merge.

> RapidOCR now ships inside the app, so text that tells patients to install Tesseract is wrong. Approve these replacements?

1. **Approve the strings and the two display rules below as written (Recommended).**
2. **Approve the strings only.** The two display rules stay as today: the badge keeps "Blocked" for the normal off state, and the diagnostics row for a missing Tesseract stays a red error while its text says Tesseract is optional.
3. **Change the wording.** The owner gives the text, and the build uses it verbatim.

| # | Where (at `9ab89972`) | Today | Proposed |
|---|---|---|---|
| 1 † | `fe/pages/DocumentInbox.tsx:555` (`title` of the "OCR Required" badge; the badge text stays) | "OCR processing is required. In Settings, enable document OCR and install Tesseract (or your admin must set OCR_ENABLED)." | "This scan needs text recognition before its values can be read. In Settings, turn on document OCR under Document import (the reader is built in; your server must allow OCR with OCR_ENABLED)." |
| 2 † | `fe/pages/VerificationWorkbench.tsx:144` (`documentAttentionHint`, `pending_ocr`; shown at `:759`, `:883`) | "OCR is required or unavailable. In Settings, turn on document OCR under Document import and ensure Tesseract is installed. Your server must allow OCR (OCR_ENABLED). Or use a clearer scan." | "This scan needs text recognition. In Settings, turn on document OCR under Document import — the OCR reader is built into the app. Your server must allow OCR (OCR_ENABLED). Or use a clearer scan." |
| 3 † | `AdvancedSection.tsx:59` (`OCR_BLOCKER_LABELS.tesseract_missing`) | "Install Tesseract OCR and add it to PATH." | "The built-in OCR reader could not start. Re-run the backend setup (dev.ps1 / dev.sh)." (shortened by owner answer OCR-HEIGHT-SHORTEN, 2026-11-10) |
| 4 | `AdvancedSection.tsx:60` (`user_disabled`) | "Turn on document OCR below for this profile." | "Turn on document OCR above for this profile." |
| 5 † | `AdvancedSection.tsx:540-541` | "Extract text from scanned PDFs and lab images using Tesseract. Your preference applies to this profile; the server must also allow OCR (OCR_ENABLED)." | "Read text from scanned PDFs and lab images with the built-in reader. Your preference applies to this profile; the server must also allow OCR (OCR_ENABLED)." |
| 6 † | `AdvancedSection.tsx:560` | "OCR is active for this profile (Tesseract + server allow)." | "OCR is active for this profile (built-in reader + server allow)." |
| 7 | `AdvancedSection.tsx:562` (display rule) | "OCR is blocked" (attention style) for every off state | When every blocker is `user_disabled`: "OCR is off for this profile" in the neutral style. Otherwise unchanged. |
| 8 | `AdvancedSection.tsx:622-623` (display rule; `StatusCard` "OCR (profile)") | "Blocked" (attention) whenever OCR is not effective | When every blocker is `user_disabled`: "Off" (`default` variant). Otherwise "Blocked", unchanged. An empty blocker list keeps "Blocked". |
| 9 † | `be/api/model_settings.py:1270` (OpenAPI description of `PATCH /api/v1/settings/model/ocr`) | "Per-profile toggle for scanned PDF and image OCR (subject to server config and Tesseract)." | "Per-profile toggle for scanned PDF and image OCR (subject to server config and an OCR engine)." |
| 10 | `be/modules/environment_diagnostics.py:35-72` (Tesseract component; display rule for its status) | label "Tesseract OCR"; when it is missing: `error`, "Not on PATH — required for OCR of scans and images.", three install commands | label "Tesseract OCR (fallback)". Missing, engine present (the same test as `config.py:350-353`): `ok`, "Not installed. Not needed: the bundled OCR reader handles scans and images; Tesseract is only a fallback.", no fix actions. Missing, engine absent: `error`, "Not on PATH, and the built-in OCR reader did not load. One of the two is needed to read scans and images.", the three commands unchanged. Found: unchanged. The `id` stays `tesseract`. |
| 11 | `environment_diagnostics.py:126` (Poppler detail; beyond the row's list, included under the approved option 1) | "Not on PATH — scanned PDF → image conversion may fail on some systems." | "Not on PATH. Only the Tesseract fallback needs it; the bundled OCR reader renders PDF pages itself." (status `warn` unchanged) |
| 12 † | `config/.env.example:117-118` | "# OCR enabled (Phase 1+). On Windows, dev.ps1 installs Tesseract/Poppler when" / "# possible and sets this from PATH detection. Set HC_SKIP_OCR_SETUP=1 to skip." | "# OCR enabled (Phase 1+). The bundled OCR reader is detected automatically; dev.ps1/dev.sh" / "# set this flag. Tesseract on PATH is an optional fallback (on Windows dev.ps1 can install it" / "# and Poppler). Set HC_SKIP_OCR_SETUP=1 to skip." |
| 13 | `dev.sh:163` (`warn`) | "Tesseract not found. For scanned PDFs: sudo apt install tesseract-ocr  (macOS: brew install tesseract)" | `status` "Tesseract not found (optional fallback; the bundled OCR reader is used first). To add it: sudo apt install tesseract-ocr  (macOS: brew install tesseract)" |
| 14 | `dev.sh:165` (`warn`) | "pdftoppm not found - scanned PDF OCR may fail. Install: sudo apt install poppler-utils  (macOS: brew install poppler)" | `status` "pdftoppm not found (optional: only the Tesseract fallback needs it). Install: sudo apt install poppler-utils  (macOS: brew install poppler)" |

Rows 5 and 6 are no longer than the text they replace. HC-UISET-005 holds Advanced at 1800 px or less at 1440, and a clean copy measured 1796 px (recurring-failures §5, WORKTREE-ENV-HEIGHT), so these two rows must add no line. The e2e fixture has `ocr_blockers: []` (`e2e/support/mockApi.ts:231`), so rows 3, 4, 7 and 8 do not change what HC-UISET-005 measures.

**Files:** `fe/pages/DocumentInbox.tsx` (`:555` `title` only), `fe/pages/VerificationWorkbench.tsx` (`:144` only), `fe/pages/settings/AdvancedSection.tsx` (`:59-60`, `:540-541`, `:560-562`, `:622-623` only), `be/api/model_settings.py` (`:1270` only), `be/modules/environment_diagnostics.py` (`:35-72`; `:126` included under the approved option 1; the engine test reuses `core.config` helpers, which are called and not edited), `config/.env.example` (`:117-118`), `dev.sh` (`:163`, `:165` only; **not** the OCR sync block `:186-199`, which `test_ocr_rapid.py` runs), `fe/__tests__/ocr-copy-engine.test.tsx` (new, HC-OCE-001…004), `be/tests/test_ocr_copy_engine.py` (new, HC-OCE-005…008), slots.

**Tests (RED first; every string asserted verbatim, from the answered option).**
- **HC-OCE-001:** a `pending_ocr` document in the inbox (rendered as `DocumentInbox.test.tsx` renders it). The badge `title` equals row 1 and contains no "Tesseract".
- **HC-OCE-002:** `/verify` with a `pending_ocr` document (as `VerificationWorkbench.test.tsx:395-420`). The hint equals row 2.
- **HC-OCE-003:** Advanced expanded. Inside the "Document import (OCR)" card only (`within`; the diagnostics list still names Tesseract), there is no `/Tesseract/`, and rows 4-6 are on screen. The switch precedes the status box in document order, which proves "above".
- **HC-OCE-004:** blockers `['user_disabled']` show "Off" and "OCR is off for this profile", with no "Blocked". `['disabled_by_admin', 'user_disabled']` and `['tesseract_missing']` show "Blocked", and the second also shows row 3.
- **HC-OCE-005:** `build_environment_diagnostics()` with `shutil.which` returning None for `tesseract` gives the two engine states and the strings of row 10 (`ok` with no fix actions; `error` with the three commands). Found is unchanged and `id == "tesseract"`.
- **HC-OCE-006:** `app.openapi()` description of `PATCH /api/v1/settings/model/ocr` equals row 9.
- **HC-OCE-007:** `dev.sh` step 3b (the block at `:157-166`, extracted the way `test_ocr_rapid.py` `_block` extracts its block) runs under bash with stubbed `status`, `ok` and `warn` and with no `tesseract` or `pdftoppm` on PATH. It prints rows 13-14 through `status` and no `warn:` line. This is a real-repo reader by design (it reads `dev.sh` from the repo root).
- **HC-OCE-008:** `config/.env.example` holds row 12's lines and no "sets this from PATH detection".
- **Would not notice:** `dev.ps1` (not in this row), and the Settings deep link (no test opens it from the inbox).

**Tests that must stay unedited:** `test_config_validation.py` (the `validate_startup` warning still names Tesseract, `config.py:233-237`; the `tesseract_missing` code), `test_ocr_rapid.py` (all HC-OCR-*, including `_run_dev_sh_ocr_sync` over `dev.sh:186-199`), `test_model_settings_api.py:331-336` (the `tesseract` and `ocr_python` ids), `test_settings_detect_nonblocking.py`, `test_audit_read_settings.py`, `ModelSettingsService.test.tsx:152`, `ui-settings.test.tsx` (HC-UISET-002 still finds `/Tesseract/` after expanding, through its diagnostics fixture label at `:149`; if it goes red, stop), `DocumentInbox.test.tsx`, `VerificationWorkbench.test.tsx`, `e2e/ui-settings.spec.ts` (its fixtures `:77-81` stay), `e2e/document-import.spec.ts` E2E-DOC-005 (the badge text "OCR Required" is unchanged), `e2e/ui-full-verification.spec.ts:104`.

**Acceptance.**
- `cd src/frontend && npx vitest run src/__tests__/ocr-copy-engine.test.tsx src/__tests__/ui-settings.test.tsx src/__tests__/DocumentInbox.test.tsx src/__tests__/VerificationWorkbench.test.tsx src/__tests__/ModelSettingsService.test.tsx` and `npx tsc --noEmit`.
- `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_ocr_copy_engine.py tests/test_ocr_rapid.py tests/test_config_validation.py tests/test_model_settings_api.py tests/test_settings_detect_nonblocking.py -p no:cacheprovider -q`, with RED then GREEN per new id; then the full suite and the count delta.
- **Quiet box (L0), on the final head:** every spec whose gate sees a changed component (rule from BATCH-1107A, RUNBOOK §10.1 quiet box). From `grep -ln "pending_ocr\|section=advanced\|Show advanced settings\|OCR (profile)\|Document import (OCR)" src/frontend/e2e/*.spec.ts` on `9ab89972`, these are `ui-settings.spec.ts` (all of it: HC-UISET-005 height, G10 "Show advanced settings", G10 tab switch `:583`), `settings-smoke.spec.ts`, `ui-routes-verification.spec.ts` and `document-import.spec.ts`. Rerun the grep on the final head.

**Never beside:** #535 (UI-PG-SECURITY) until it merges. The files are disjoint, but both need `ui-settings.spec.ts` quiet acceptance, and one quiet batch could not tell whose change moved a Settings node. Also #316 leaving draft (`dev.sh`; its hunks at `:119` and `:154` are near `:163`; the second lander rebases) and #239 leaving draft (`config/.env.example`, its hunk at `:91`). It is disjoint from #537 and #538.

**Not in this row:** `dev.ps1` makes the same claims at `:532`, `:540` and `:555`, and #316 holds that file. The `ocr_python` diagnostic (`environment_diagnostics.py:74-106`) still calls `pytesseract` and `pdf2image` required, which is behaviour, not copy. Both are follow-ups for L0, not rows here.

**Estimate:** 2.5 h. **Runtime:** `codex` (+ Claude Code Opus review).

> **Delta 2026-11-10 (BATCH-1110A): OCR-COPY-MERGE and an L0 licence amendment.**
> - Owner answer OCR-COPY-MERGE "Merge as built (Recommended)" (2026-11-10): the 14 strings as built from OCR-COPY-TEXT merge; the string diff still goes in the PR body.
> - **L0 ruling (2026-11-09; L0's, not the owner's) on HC-UISET-002:** the row's licence is amended to include ONE assertion edit in `src/frontend/src/__tests__/ui-settings.test.tsx`: `screen.getAllByText(/Tesseract/)` becomes `await screen.findAllByText(/Tesseract/)`. It waits for the same diagnostics label and is not weakened. Owner-visible at merge.

