# Follow-ups 2026-10-30 — plans for SOURCE-TRACE-WIRE, SHELL-NAVREF-DEAD and UIG002-TITLE; NAV70-CI-MISS, FOREIGN-CHROMIUM-ON-BOX and GH-READY-REFUSED

**Last Updated:** 2026-10-30 (Opus planner on `144b5d48`: six follow-up bullets from the 2026-10-29 handoff (PR #412, `docs/plans/2026-10-29-session-handoff.md`) §3 item 6 classified; three code rows planned, one folded into STILLNESS-NAV-LATE with an owner question drafted, two harness notes written into the RUNBOOK and recurring-failures in the same PR)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). No row below needs a new owner gate. The two drafted owner questions at the end are not asked; L0 has each one reviewed before AskUserQuestion.
**Base measured:** `origin/main` @ `144b5d48` (2026-10-29, #411 merged). Every `file:line` below was re-read by the planner on that commit. Product code was read only. CI evidence was read with `gh run view` and the job logs (`gh api repos/{owner}/{repo}/actions/jobs/<id>/logs`) on 2026-10-30.
**Refresh Trigger:** a merge of STILLNESS-NAV-LATE, G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE or UI-PG-RESULTS; any edit before these rows are built to `src/frontend/src/components/lab-interpreter/InterpretedResultCard.tsx`, `src/frontend/src/pages/LabInterpreter.tsx`, `src/frontend/src/components/results/SourceTrace.tsx`, `src/frontend/e2e/ui-provenance.spec.ts`, `src/frontend/src/components/layout/Sidebar.tsx`, `src/frontend/e2e/ui-gates.spec.ts` or `src/frontend/e2e/README.md`; a fifth HC-UISH-009 CI miss.

Queue rows: [queue.md, "Planned 2026-10-30, planner"](2026-10-15-build-program/queue.md#planned-2026-10-30-planner). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`, `e2e/` = `src/frontend/e2e/`.

**Rules that hold for every row here.**
- No row relaxes a bound, adds a retry, or marks a test flaky, fixme, skip or fail. No row changes a constant in `e2e/support/gates.ts`.
- None of the three code rows runs a stillness timing measurement, so the quiet-box rule does not apply to them: functional e2e and vitest run under normal load (L0 ruling on #402; 2026-10-29 handoff §4). They still never run beside the rows named in their "never beside" lists, because those rows edit the same files.
- **In-flight drafts checked 2026-10-30** with `gh pr diff <n> --name-only`: #398 (UI-PG-MEDS) touches `e2e/ui-shell.spec.ts`, `e2e/ui-meds.spec.ts`, `e2e/tailwind4-styles.spec.ts` and medication files; #400 (UI-PG-CARE) touches `e2e/ui-care.spec.ts` and `CareTasksPage.tsx`; #410 (TOAST-SHELL) touches `e2e/ui-toast.spec.ts` and `fe/styles/globals.css`; #393, #399 and #401 hold only their claim commit (no file yet; their queue rows name `e2e/ui-shell.spec.ts`, `TopBar.tsx`, `AppLayout.tsx` and `SearchPage.test.tsx`). None of them touches a file a row here edits.

---

## SOURCE-TRACE-WIRE — give the Source Trace sheet a real caller on the interpreted result

**Source:** bullet SOURCE-TRACE-UNWIRED (found 2026-10-29, #407 review), the instance already recorded under [recurring-failures](../agentic/recurring-failures.md) #10. Kind: **PRODUCT (frontend)**. MVP **P1** (provenance on the demo path).

**Facts (re-read on `144b5d48`).**
- `fe/components/results/SourceTrace.tsx:117` exports the sheet. Its only caller is `fe/components/lab-interpreter/CitationTooltip.tsx:99`, which renders the sheet and the "Open source" button only when it gets a `source` prop (`:82`, `:98`).
- Neither call site passes one: `fe/components/lab-interpreter/InterpretedResultCard.tsx:122-126` and `PanelInterpretationDashboard.tsx:110-114`. The bullet is confirmed.
- **The bullet's implied fix is the wrong one.** No interpretation citation is the user's own value. `be/modules/interpret.py:685-711` (`_generate_citations`) emits only `knowledge_base`, `source` (a reference title) and `intervention` citations, and the panel path emits `relationship` citations (`:421-426`). The `Citation` type is `{type, id, text}` (`fe/services/types.ts:247-251`). So a citation on `/interpret` has no observation to trace, and `CitationTooltip` is right to show the quote only (its own comment, `CitationTooltip.tsx:12-15`: "a knowledge-base reference has no page, and the popover never invents one").
- The plan's other entry to the sheet is the one to wire: frontend-revamp plan §4.1 (`2026-10-23-frontend-revamp-plan.md:278`), Source Trace opens from **"Show source" on any value**, or from "Open source" in a citation popover.
- `/interpret` already has the value: `fe/pages/LabInterpreter.tsx:72` (`effectiveObservation`) feeds `InterpretedResultCard` at `:247-256`, passing only its name, value, unit and range.
- The data the sheet reads exists. `Observation` has `doc_id`, `source_page` and `source_bbox_json` (`fe/services/types.ts`, `source_page` at `:173`). `useDocument` (`fe/services/documents.ts:88`) returns the document, whose `source` is the file name (`types.ts:111`). `useDocumentPages` (`:96`) returns each page's `text` (`be/api/documents.py:399-403`, route `:1617`). Both hooks are `enabled: !!documentId`, so passing `undefined` makes no request.
- The `/interpret` e2e mock in `e2e/ui-provenance.spec.ts` already has the observation (`:40-60`, `doc_id`, `source_page: 3`), the document (`:77-89`, `source: 'provenance-report.pdf'`) and a pages route (`:164-168`, but page 3's `text` is `''`). It does not answer `GET /documents/<id>` (only `/documents`, `/entities`, `/pages` and the page image, `:160-172`).
- The assistant path (`/explain`) is a different case: `be/api/assistant.py:1808` emits `user_observation` citations with `doc_id`. Wiring "Open source" there belongs to UI-PG-ASK ("citation chips use the popover from UI-PROVENANCE") and is not planned here.

**Design.**
- `InterpretedResultCard` gets one optional prop, `observation?: Observation`. When `observation?.doc_id` is set, the card shows a "Show source" text button next to the citation chips. Without it the card renders exactly as today, so its existing tests (HC-IRC-001…009) are unchanged.
- The button opens `SourceTrace`. The document and page fetches start only when the sheet first opens: a small `ObservationSourceTrace` exported from `SourceTrace.tsx` calls `useDocument(open ? doc_id : undefined)` and `useDocumentPages(open ? doc_id : undefined)` and passes `sourceFile = document?.source ?? null`. So `/interpret`'s first paint makes no new request, and Gate G7's request lists for `/interpret` do not change.
- Excerpt, with a strict match rule, because the sheet says "This is what your report states." and a wrong highlighted line would be a false provenance claim. A pure `excerptFromPage(text, observation)` in `SourceTrace.tsx`:
  - splits the `source_page` page's text into lines;
  - a line matches when it contains `analyte_raw` (case-insensitive) **and** the value as a whole token (`String(value)`, or `value_text` when `value` is null);
  - exactly one matching line → that line plus up to 2 lines either side, and `matchIndex` points at it;
  - zero or several matching lines, no `source_page`, or no page with that number → no excerpt (`[]`, `null`). The sheet then shows its existing "Excerpt not available." (`SourceTrace.tsx:221`). Nothing is guessed.
- `LabInterpreter.tsx:247` passes `observation={effectiveObservation ?? undefined}`. That is the only page edit.
- `PanelInterpretationDashboard` and `CitationTooltip` are not changed: no panel citation has an observation.
- Focus: closing the sheet returns focus to "Show source". Use the sheet's `trigger` if `Sheet` restores focus with it, or the same effect `CitationTooltip.tsx:30-37` uses.

**Tasks (test-first).**
1. **RED (vitest), new `fe/__tests__/source-trace-wire.test.tsx`.** HTTP is stubbed at `fetch`, not by mocking `@/services/documents`, so a wrong URL fails the test.
   - HC-STW-001: with an `observation` that has a `doc_id`, `InterpretedResultCard` shows a "Show source" button; with no `observation`, or `doc_id: null`, it shows none. RED: no button today.
   - HC-STW-002: no request to `/documents/<id>` or `/documents/<id>/pages` is made before the click. After the click, a dialog named "Source for Glucose" shows the file name from `GET /documents/<id>`, "Page 3", and the matching line marked "Matching line:".
   - HC-STW-003: `excerptFromPage` table: one match (±2 lines, `matchIndex`); no match; two matches (none); the analyte without the value (none); `value: null` with `value_text`; `source_page: null`. The `value` check is a whole token: "196" does not match 96.
   - HC-STW-004: Escape closes the sheet and focus returns to "Show source".
2. **GREEN.** The prop, `ObservationSourceTrace`, `excerptFromPage` and the `LabInterpreter.tsx` line, as designed. Run the four ids, then `InterpretedResultCard.test.tsx`, `ui-provenance.test.tsx`, `LabInterpreter.test.tsx`.
3. **RED then GREEN (e2e), `e2e/ui-provenance.spec.ts`.**
   - Mock: answer `GET /documents/${DOCUMENT_ID}` with `documentFixture`, and give page 3 the text `'Comprehensive Metabolic Panel\nGlucose 96 mg/dL 70-99\nSodium 140 mmol/L 136-145'`. No other mock entry changes.
   - New HC-STW-005: on `/interpret`, click "Show source". The dialog shows `provenance-report.pdf`, `Page 3`, the Glucose line as the matching line, and "This is what your report states."; `mock.unmocked` is empty. Run it once on the base without the product change and paste the RED (no "Show source" button), then GREEN.
4. **Checks.** `npx tsc --noEmit`, `npm run lint`, `npm run build:check` (the `/interpret` chunk already contains `SourceTrace` through `CitationTooltip`, so the budget should not move; paste the line), the whole `ui-provenance.spec.ts` on dev, then CI E2E green with no test listed as flaky.

**Acceptance:** HC-STW-001…005 green, with the RED of each pasted; HC-IRC-001…009 and every `ui-provenance.spec.ts` test unchanged and green; `grep -rn "SourceTrace\b" src/frontend/src --include=*.tsx | grep -v __tests__` lists a page-reachable caller besides `CitationTooltip`. Est 2.5 h.

**Files:** `fe/components/lab-interpreter/InterpretedResultCard.tsx` (prop and button only), `fe/components/results/SourceTrace.tsx` (add `ObservationSourceTrace` and `excerptFromPage`; the sheet itself unchanged), `fe/pages/LabInterpreter.tsx` (`:247` one prop), `fe/__tests__/source-trace-wire.test.tsx` (new, HC-STW-001…004), `e2e/ui-provenance.spec.ts` (mock: one route and page 3's text; new HC-STW-005).

**depends_on:** — (UI-PROVENANCE #367 merged). **Never beside:** G1-VERIFY-TRACE-RACE (also edits `e2e/ui-provenance.spec.ts`; it is ready and goes first in the handoff order, so this row builds after it merges and re-reads the mock lines); UI-PG-RESULTS (edits `InterpretedResultCard.tsx` and deletes `LabInterpreter.tsx`). If UI-PG-RESULTS merges first, Task 0 stops and L0 re-points the `LabInterpreter.tsx` edit to `ResultsPage.tsx`. **Stops:** if the sheet would need a new backend field, or if `excerptFromPage` cannot match the mock line under the rule, stop and tell L0; do not loosen the rule.

**Delta to UI-PG-RESULTS and UI-PG-REVIEW (frontend-revamp plan).** UI-PG-RESULTS keeps HC-STW-001…005 green and carries the `observation` prop into `ResultsPage.tsx` when it folds `LabInterpreter.tsx` in. UI-PG-REVIEW's file list already says "'Show source' opens Source Trace" (`2026-10-23-frontend-revamp-plan.md:704`) but has no check for it; it adds HC-UIREV-006: on `/verify`, "Show source" on a row opens the sheet for that row (e2e), reusing `ObservationSourceTrace`. A one-line pointer is added to both sections.

---

## SHELL-NAVREF-DEAD — remove the unread `navRef` from the sidebar

**Source:** bullet SHELL-NAVREF-DEAD (found 2026-10-28, #370 final review MINOR 1). Kind: **PRODUCT (frontend)**, dead code. MVP **P2**.

**Facts.** `fe/components/layout/Sidebar.tsx:19` declares `const navRef = useRef<HTMLElement>(null);` and `:63` attaches `ref={navRef}` to the `<nav>`. `grep -rn navRef src/frontend` finds only those two lines. `useRef` stays imported for `activeRef`, `placedRef` and `keyboardRef` (`:20-22`). The e2e gates find the nav by `nav[aria-label="Main navigation"]`, not by the ref.

**Design and tasks.** Delete `:19` and the ` ref={navRef}` attribute on `:63`. Nothing else. No new test: a test cannot fail on an unread ref. The pinning checks are `src/__tests__/ui-shell.test.tsx` (it renders `Sidebar` and reads its source, `:9-11`, `:105-108`), `npx tsc --noEmit` and `npm run lint`.

**Acceptance:** `grep -rn navRef src/frontend/src` prints nothing; `npx vitest run src/__tests__/ui-shell.test.tsx`, `npx tsc --noEmit` and `npm run lint` green (paste each); CI green. Est 0.25 h.

**Files:** `fe/components/layout/Sidebar.tsx` only. **depends_on:** —. **Never beside:** another open PR that edits `Sidebar.tsx` (none on 2026-10-30).

---

## UIG002-TITLE — HC-UIG-002's title says what it asserts

**Source:** bullet UIG002-TITLE (found 2026-10-28, #370 final review MINOR 3). Kind: **PRODUCT (e2e harness)**, wording only. MVP **P2**.

**Facts.**
- `e2e/ui-gates.spec.ts:145` titles the test `'HC-UIG-002 axeGate on /inbox reports color-contrast'`, but `:158` asserts `not.toContain('color-contrast')`. The section comment at `:127` already says "reports no color-contrast (plain test; no longer expected to fail)", and the file header (`:5-6`) says HC-UIG-002 and HC-UIG-003 are plain tests. The bullet is confirmed.
- The same stale claim is in `e2e/README.md:103` ("`HC-UIG-002` and `HC-UIG-003` are `test.fail()`"). `grep -rn "test\.fail(" src/frontend/e2e` finds no `test.fail(` in `ui-gates.spec.ts`; the only live one is `ui-shell.spec.ts:978` (PAGE_OVERFLOW). The marks were removed by UI-SHELL (`f7b2dbac`, "HC-UIG-002 no longer expected to fail").
- Nothing filters on the old title: no `-g` with it in `.github/workflows/` or `scripts/`. `2026-10-23-frontend-revamp-plan.md:417` quotes it in the original UI-GATES plan table, a historical record, and is left as is.

**Design and tasks.**
1. Rename `:145` to `'HC-UIG-002 axeGate on /inbox reports no color-contrast'`. The body is unchanged.
2. `e2e/README.md:103`: say that no `ui-gates.spec.ts` test is `test.fail()` now (HC-UIG-002 and HC-UIG-003 became plain tests with UI-TOKENS and UI-SHELL), and that the rest of the paragraph applies to any later `test.fail()` mark, such as the PAGE_OVERFLOW entries in `ui-shell.spec.ts`. `:105` stays.
3. Check: `npx playwright test e2e/ui-gates.spec.ts -g "HC-UIG-002"` lists the new title and `2 passed` (the `pre` test and this one). This is a functional run: normal load is fine, and no stillness test runs.

**Acceptance:** the grep `grep -n "reports color-contrast'" src/frontend/e2e/ui-gates.spec.ts` prints nothing; the Playwright output above, pasted; CI green. Est 0.25 h.

**Files:** `e2e/ui-gates.spec.ts` (`:145` only), `e2e/README.md` (`:103` only). **depends_on:** —. **Never beside:** UIG006-PASS3-FLAKE (`ui-gates.spec.ts`; ready, first in the handoff's quiet-box order) or a STILLNESS-NAV-LATE Task 2 whose L0 ruling names `ui-gates.spec.ts`. The hunks are disjoint (`:145` against `:583-625`), but the file rule holds: build after UIG006-PASS3-FLAKE merges, or before it is claimed.

---

## NAV70-CI-MISS — folded into STILLNESS-NAV-LATE as CI evidence and an after-merge count

**Source:** bullet NAV70-CI-MISS (found 2026-10-28) and the 2026-10-29 handoff (PR #412) §3 item 6. Kind: **MEASURE**, folded into [STILLNESS-NAV-LATE](2026-10-23-frontend-revamp-plan.md#stillness-nav-late--find-and-fix-why-page-changes-run-late-under-the-stillness-probe). No new code row. Owner question drafted below, asked only if STILLNESS-NAV-LATE ends with no fix. The 70 ms bound (owner STILLNESS-NAV-70) is not lowered or relaxed by anything here.

**Facts (CI, measured 2026-10-30).** Every `ci.yml` run created from 2026-10-28T15:40Z to 2026-10-30T17:50Z: 88 runs. Every attempt of each was read (`gh run view <id> --attempt <n> --json jobs`). 91 E2E Smoke Tests attempts: 79 ran (67 success, 12 failure), 12 skipped. Each failed job log was read for its failing tests.

| Run, attempt | Branch (PR) | Failing HC-UISH-009 case | Gap |
|---|---|---|---|
| 40729283791, 1 | `test/vitest-tz-pin-config-pin` (#396) | `ui-shell.spec.ts:318`, navigation to `/search` | 72 ms |
| 40729283791, 2 | same | same | 77 ms |
| 40845146715, 1 | **`main`**, push of `760655c7` (#409 merge) | same | 71 ms |
| 40920267687, 1 | `docs/post-merge-batch-1029` (#411) | same | 71 ms |

- HC-UISH-009 missed the 70 ms bound in **4 of 79** E2E attempts that ran (p = 4/79 ≈ 0.051), in 3 runs. Each miss was on `/search`, and each was the only failure in its job. One turned `main` red; that run was not re-run, and the next `main` run (40924151888) passed.
- The bullet and the handoff count 2 runs (3 misses). The `main` run above was not in either count.
- The describe pins `retries: 0` (`e2e/ui-shell.spec.ts:293`; the CI default is `retries: 2`, `playwright.config.ts:55`). CI runs the dev server (`playwright.config.ts:31`), not `vite preview`.
- Not this item: the other 8 failed attempts were all on PR branches, and each failed on what that branch changes: the new `ui-toast`, `ui-care` and `ui-meds` specs, and HC-UISH-003 on `/notifications` (only on #398's branch, runs 40761322738, 40738292021 and 40738248438; #398 edits `/notifications`, so it belongs to UI-PG-MEDS). In every job, the 90-91 ms "sampling gap" lines are HC-UIG-007 (d), which is a self-test expected to reject.
- Box measurements (STILLNESS-NAV-LATE's table, `2026-10-23-frontend-revamp-plan.md:1142-1151`) saw navigation gaps of 41-59 ms on dev. CI's misses sit at 71-77 ms, so the CI runner adds a pause the quiet box did not show.

**What is added to STILLNESS-NAV-LATE (a delta pointer is added to its plan section).**
1. Task 1's report includes the table above. For each CI miss, it states whether the gap is explained by the cause Task 1 finds.
2. **After-merge count.** One green CI run cannot show that a 5 % miss is gone. Under the 2026-10-28 rule ("0 failures after needs a measured failure rate before", [2026-10-28-followups-plan.md](2026-10-28-followups-plan.md) rules), N = max(40, ceil(3 × 79 / 4)) = **60 E2E attempts**. After STILLNESS-NAV-LATE merges, L0 counts HC-UISH-009 misses over the next 60 E2E attempts on any branch. Zero misses closes NAV70-CI-MISS. One miss reopens it as the owner question below.
3. Until then, the handoff practice stands: when HC-UISH-009 is the **only** failure in an E2E attempt, L0 re-runs the job once and appends the run id, branch and gap to this table, in the next post-merge batch. A second miss on the same PR head stops that PR and goes to L0. The re-run does not count as a pass for the row's measure, and no test is marked flaky.

---

## FOREIGN-CHROMIUM-ON-BOX — one quiet-box precheck in the RUNBOOK (done in this PR)

**Source:** bullet FOREIGN-CHROMIUM-ON-BOX (found 2026-10-29, #410) and the 2026-10-29 handoff (PR #412) §4 ("Extend the quiet-box precheck to `rustc|cargo|rust-lld|chrom` and foreign pytest"). Kind: **DOCS/harness**. No code row.

**Facts.**
- #410 comment 6494099295 (2026-10-29T10:22Z): another repo's session (Stellaris-Adaptive-AI-Engine) drove its own Chromium (`shoot.mjs`) during a quiet-box run, and the precheck pattern `pgrep -fa "playwright|vitest|pytest"` did not match it. Comment 6509780858 shows the wider check #410 then used: `pgrep -fa "playwright|vitest|pytest|chrome|chromium|cargo|rust-lld|vite"` empty, and no listener on 3000/4173/5173/8000.
- The narrow pattern is copied into five places: `2026-10-23-frontend-revamp-plan.md:1035` and `:1186`, `2026-10-28-followups-plan.md:14`, `:273` and `:421`, plus queue.md's STILLNESS-NAV-LATE row and its 2026-10-28 follow-ups intro. No RUNBOOK section names a precheck.
- **New, measured by the planner on 2026-10-30:** run from an agent's Bash tool, `pgrep -fa "<pattern>"` always matches the agent's own wrapping `bash -c` command line, because that command line contains the pattern. So "must print nothing" can never hold as written. Each agent has had to judge by eye which lines are its own. The bracket form avoids the self-match: `pgrep -fa '[p]laywright|…'` does not match its own command line. Run that way here, it printed only a foreign pytest from another worktree (`hc-plan-ise`), and the wrapping shell did not appear.

**Change (in this PR).**
- RUNBOOK §10.1 gets one "Quiet box" bullet. It gives the one precheck: `uptime` (1-minute load below 1.5), `pgrep -fa '[p]laywright|[v]ite|[p]ytest|[c]hrom|[c]argo|[r]ustc|[r]ust-lld'` empty, and `ss -ltn` with no listener on 3000, 4173, 5173 or 8000. It also says the rule is for stillness timing runs only, that a foreign process is never killed (ask the owner to pause it), and that this supersedes the narrow pattern quoted in older plans.
- The five plan copies and the two queue copies point to it instead of quoting the narrow pattern. The FOREIGN-CHROMIUM-ON-BOX bullet keeps its quote, because it is the record.
- recurring-failures #5 gets the instance: a precheck that could not see the contaminant, and could never print nothing.
- `hold_slots.sh` and `wait_quiet.sh` live in `/tmp/claude-1000` and are not in the repo, so they are not edited here. L0 updates its copies to the same pattern when it next recreates them (2026-10-29 handoff §4).

---

## GH-READY-REFUSED — say who runs `gh pr ready` when an agent is refused (done in this PR)

**Source:** bullet GH-READY-REFUSED (found 2026-10-28, #396/#397/#402) and the 2026-10-29 handoff (PR #412) §4 ("`gh pr ready` is often refused for build-item agents. L0 runs it."). Kind: **DOCS/harness**. Owner question drafted (optional).

**Facts.** RUNBOOK §6 (`RUNBOOK.md:160`) and table row 7 (`:40`) tell the item runtime to run `gh pr ready <n>`, and `.claude/workflows/build-item.js:360` tells the verify agent the same. The repo's `.claude/settings.json` has no `permissions` block (only `hooks`), so the refusal comes from the session's permission classifier, not from a repo rule. The refusals are recorded in the build-item session logs and the handoff, not in PR comments: no comment on #396, #397 or #402 mentions them. Ready-marking is the last step after the slot is released, so a refusal stops nothing but the ready flag.

**Change (in this PR).** RUNBOOK §6, after `:160`: if the permission system refuses `gh pr ready`, do not retry it and do not reach the same state another way (`gh api`, GraphQL `markPullRequestReadyForReview`). Finish the PR body, say "ready: L0" in the final report, and L0 runs `gh pr ready`. `build-item.js` is not edited (no workflow-script edits in this PR). L0 already follows this practice.

---

## Drafted owner questions (not asked; L0 has each reviewed first)

**OQ-NAV70 (ask only if STILLNESS-NAV-LATE ends with no fix, or the after-merge count sees a miss).**
> "Page-change stillness check in CI. Even with your 70 ms limit, one check, the Safety Rail staying still while the app moves to the Search page, misses by 1-7 ms in about 1 CI run in 20: 4 of 79 runs from Oct 28 to Oct 30, gaps of 71-77 ms, one of them on `main`. The diagnosis row found no cause it could fix. The limit stays 70 ms in every option. What should happen when this is a PR's only failure?"
> - **"Re-run once and log it"**: L0 re-runs the job once and records each miss. A second miss on the same commit stops the PR. (Today's practice.)
> - **"Measure the CI runner"**: a new measurement row times the same navigation with a bare 20 ms timer on CI, to tell runner pauses from app work. Re-run once meanwhile.
> - **"Hold merges"**: no PR merges with a red E2E job until a fix lands, even if the miss is not the PR's fault.

**OQ-GH-READY (optional; it only saves L0 a step).**
> "Build-item agents are often refused when they run `gh pr ready` to mark a finished PR ready for review, so L0 runs it by hand. Do you want to allow that one command for agents in your Claude Code permission settings? It marks a draft ready for review. It does not merge anything."
> - **"Allow it"**: you add the allow rule yourself; agents never edit permission settings.
> - **"Keep L0 doing it"**: no change.

---

## Not planned (seen while measuring; for L0)

- HC-UISH-007 ("with a toast visible, opening More leaves no toast over the sheet", `ui-shell.spec.ts:789`) passed only on a retry, and so was listed as flaky, in `main` run 40845146715 and in #398's run 40820611795. It is the toast-over-sheet case that TOAST-SHELL (#410) works on. It is recorded here only. If it is flaky again after #410 merges, it becomes a bullet.
- UI-PG-RESULTS and UI-PG-REVIEW still show "blocked: … wave 4 rows", but every wave-4 row (UI-RIBBON #362, UI-PROVENANCE #367, UI-SHOWCASE-KIT #368) is done. The post-merge batch can refresh their status.
