# UIDOC-006A-FLAKE Task 1: diagnosis (no fix)

**Result.** The 42-50 ms sampling gap in HC-UIDOC-006 (a) comes from product work, not from the sampler. The cause is the
import-complete React commit in `DocumentInbox`. That one task runs 17-23 ms at CPU x1 and 39-62 ms at CPU x2, and about
45 % of it is the page's **first `Date.prototype.toLocaleDateString()`** (`DocumentInbox.tsx:575` on `e8a64c60`): that call
loads ICU date data and costs 7-13 ms at x1 and 17-31 ms at x2. The list starts empty, so this row is the first date the
page ever formats. That is why (a) misses and the list-with-rows cases do not. An A/B that warms the formatter while the
page is idle (the existing `ResultsPage.tsx` `warmExplainClick` pattern) takes the quiet-box rate from **9/20 to 0/20**.
At CPU x2 the same warm-up only brings it from **20/20 to 11/20**. The leftover miss there is the rest of the dev-mode React
commit plus the frame after it.

- Owner answer UIDOC-006A-FIX option (a) applies: the long task is product code. The sampler's own ticks inside the gaps
  measure 0.3-1.5 ms at x1 and up to 3.2 ms at x2 in the traces, so option (b) is not indicated.
- Base measured: worktree `/mnt/e/Programming/Github Repo/hc-uidoc-006a-diag`, detached at `371350a1` (origin/main at
  start, the #542 merge). It has a real `npm ci` (358 packages; `node_modules` is a real directory). During the run origin/main
  moved to `e8a64c60` (#571, #588, #589 and others). Re-checked: between the two commits, `startSampler`/`checkSampling`/
  `stillnessProbe` and the bodies of the measured tests are unchanged (#571 edits only `reducedMotionSnapshot`, G5).
  #588 adds a remove-error card to `DocumentInbox.tsx`, which is not on the import path. Line numbers below are on
  `e8a64c60`.
- Bounds: none moved. `STILLNESS_MAX_GAP_MS = 40` (`gates.ts:28`), `kind: 'interaction'`, `--retries=0`.

## How it was run

- Quiet box: `quiet-box.lock`, then each line through `/tmp/claude-1000/quiet_run_b22.sh --max-wait 7200` (the pytest
  slots are held; the run waits for load < 1.5, no foreign playwright/vite/pytest/uvicorn, and free ports
  3000/4173/5173/8000). Settings: `HC_E2E_BACKEND_PYTHON=~/venvs/asclexis-311/bin/python`, `TMPDIR=/dev/shm`,
  dev server (as in the CI E2E smoke job), `--workers=1 --retries=0`. Driver: `uidoc006a-diag/tools/run_diag.sh`.
- Probe: the planner's `probe-append.ts`, copied to `uidoc006a-diag/tools/probe-append.ts` with one added line that
  calls `performance.mark` per phase so the marks show in the trace. It was appended to the worktree's
  `ui-documents.spec.ts` only. There is also a file-level `beforeEach`/`afterEach` block (`tools/diag-hooks.ts`, appended to
  ui-documents, ui-export and ui-ask). It does not change any test body or bound. It applies CDP
  `Emulation.setCPUThrottlingRate` (`HC_PROBE_CPU`) and re-applies it on every load. An init-script setter archives every
  `window.__hcStill` sampler state, and the hook records longtask and long-animation-frame entries. With
  `HC_DIAG_TRACE=1` it records a Chromium trace (devtools.timeline plus the V8 sampling profiler). With `HC_DIAG_WARM=1`
  (A/B only) it warms the ICU date and time formatters on `load`. Nothing was committed. The three spec files were
  restored afterwards.
- Attribution: `tools/gap_attrib.py` maps `performance.now()` to trace time through a `hc-align` mark. It lists the
  main-thread tasks in each run's largest gap, with time-weighted CPU-profile self time per source line.
  `tools/commit_breakdown.py` breaks down the hot task. `tools/gap_budget.py` sorts gap time into sampler tick, product JS,
  frame and input. The served (Vite-transformed) sources used to map profile lines are in `uidoc006a-diag/served/`.

## Evidence

Miss rates. A miss is a `sampling gap of N ms (must be <= 40 ms …)` failure. Gap columns are min/median/max of the
largest post-trigger gap in each run (`logs/miss-table.txt`).

| Test | Condition | Misses | Gap ms min/med/max | Notes |
|---|---|---|---|---|
| HC-UIDOC-006 (a) `ui-documents:1260` | quiet, x1 | **9/20** | 22/40/45 | 9/9 misses have the import-complete commit (tracked nodes 3 → 8) inside the gap, which starts +20-23 ms after the trigger |
| UIDOC006A-PROBE (planner probe) | quiet, x1 | 3/20 | 21/29.5/52 | 3/3 misses: the 3 → 8 commit is inside the gap |
| HC-UIDOC-006 (a) | x2 | **20/20** | 41/55/68 | LoAF: the long script is `TimerHandler:setTimeout` @tanstack_react-query (notify, then a React SyncLane render), 35-45 ms |
| UIDOC006A-PROBE | x2 | 20/20 | 49/54/59 | same |
| HC-UIDOC-006 (a) | x4 | 20/20 | 92/125.5/145 | same task, 92-101 ms |
| HC-UIDOC-006 (a) **+ ICU warm (A/B)** | quiet, x1 | **0/20** | 22/25.5/35 | |
| HC-UIDOC-006 (a) **+ ICU warm (A/B)** | x2 | **11/20** | 35/43.5/61 | 9 misses still at the 3 → 8 commit; 2 at import start (`MessagePort.onmessage` 40-47 ms, nodes 3 → 3, the ThinkingOrb mount) |
| HC-UIASK-005 `ui-ask:716` | quiet, x1 | 1/20 | 22/29.5/41 | |
| HC-UIASK-005 | x2 / x4 | 20/20 / 20/20 | 41/53.5/65 · 87/103/117 | |
| HC-UIASK-005 + ICU warm (A/B) | x1 / x2 | 0/20 / 20/20 | 21/27.5/40 · 51/55.5/70 | |
| /export (light + dark) `ui-export:431` (CI's :430) | quiet, x1 | 1/20 | from the log | plus 1 other failure: "only 5 sample(s) after the trigger" on the Full Preview overlay probe (not this class) |
| /export with Questions (light + dark) `:473` (CI's :472) | quiet, x1 | 0/20 | ≤ 40 | |
| /export :431 / :473 | x2 | 12/20 · 18/20 | 27-53 · 37-55 | |
| /export :431 / :473 | x4 | 0/20 + 20 nav-probe failures · 20/20 | nav-probe gaps such as 85-93 (70 bound) · 63-101 | at x4 :431 fails earlier, on the navigation probe |

CI for comparison (the plan's table): 42-50 ms, a single gap line. That matches the quiet-box x1 range for (a) (41-45).

Attribution of the largest gap, from traces (`logs/commit-breakdown.txt`, `logs/gap-budget.txt`, `logs/attrib-*.txt`):

| Test | Main-thread task in the gap | ms at x1 | ms at x2 | Part of it | Whose |
|---|---|---|---|---|---|
| 006 (a) | import success: TanStack `notifyManager` setTimeout(0), then React SyncLane render and commit of `DocumentInbox` (row, handoff card, scanned warning, ThinkingOrb unmount) | **17.3-23.4** (11 traces) | **39.0-61.6** (10 traces) | the first `toLocaleDateString()` at `DocumentInbox.tsx:575`: **7.2-12.7** at x1, **17.0-29.8** at x2; the rest is react-dom dev and libraries (6.6-8.9 / 13.9-25.4) and DocumentInbox render (~1-4) | product |
| 006 (a) | the next rendering task (UpdateLayoutTree, Layout of 101/281 dirty objects, Paint, framer-motion rAF) | 7.4-10.9 | 14-18 | | product (browser rendering of the new nodes) |
| 006 (a) | sampler ticks (`startSampler` `snapshot`) inside the gap | 0.3-1.5 (one tick of 4.6 ms right after the commit: the first forced style read of the new nodes) | 0.3-3.2 | | harness |
| 006 (a), traced only | ThinkingOrb mount, first canvas `ctx.setTransform` (`thinking-orbs` `frame`) at import start | 26-581 | 66-3408 | | product library. **Under tracing only**: untraced runs show it in 0/40 cold runs at x1/x2 by LoAF, and in 2/20 warm runs at x2 (40-47 ms) |
| HC-UIASK-005 | Send click: discrete event, then React render of the user bubble | 15.5-22.1 | 50.2-61.0 | the first `toLocaleTimeString([], {hour, minute})` at `ExplainAssistant.tsx:721`: 5.0-8.7 at x1, 13.2-16.4 at x2; the rest is react-dom dev (26.9-37.2 at x2) | product |
| /export Generate | Playwright click (pointerout/pointerdown/click, hit test `elementsFromPoint`) followed by the pending-state commit of `ExportPage` | ~4-6 and 6.6-9.2 | ~14-17 and 19.5-23.0 | no single hot line; react-dom dev commit (setValueForProperty, restoreSelection), Radix Checkbox and lucide icons | input (Playwright) + product, spread across the commit |

Phase of each miss. The planner probe's mark-based phases (`filesSet`, `reading`, `handoff`, `done`) do not locate the
miss. Each mark is taken after an `expect()` resolves, and its polling lags the DOM: the `handoff` mark lands at +131-146
ms while the 3 → 8 commit lands at about +60-75 ms. Every probe miss is therefore labelled `after-filesSet` or
`after-reading`. The reliable phase is the tracked-node count at the two ends of the gap: **3 → 8 = the import-complete
commit (handoff card + scanned warning + new row)**. That holds in all 12 quiet-box misses (12/12 confirmed 3 → 8). All 40 cold x2 misses end with the 8 nodes present
(19 of them have a recorded start of 3; for the other 21 the start count was not kept).

## Recommended change (option (a), Task 2)

**Warm the ICU date formatter while `/inbox` is idle**, so the import-complete commit does not pay for the first
`toLocaleDateString()`. Prior art is `ResultsPage.tsx:103-122` (`warmExplainClick`, CDP trace in PR #476: "the first
toLocaleDateString of a page loads the browser's ICU date data (9-15 ms)") and `ResultsPage.tsx:291`
(`useEffect(warmExplainClick, [])`).

- **Licence:** `src/frontend/src/pages/DocumentInbox.tsx`. Add one effect beside the existing one at `:84`. In an idle
  callback (`requestIdleCallback`, with a `setTimeout` fallback, both cleared on unmount) it runs
  `void new Date(0).toLocaleDateString()`. The row still formats `new Date(doc.imported_at).toLocaleDateString()` at
  `:575` in its first commit, so the output is unchanged and only the cost moves out of the trigger task. Plus the new test
  in `e2e/ui-documents.spec.ts` (after `:1260`). Nothing in `gates.ts`. Do not import `thinking-orbs` (HC-UISK-004,
  `:18-19`). #542 has merged, so the plan's wait condition is met.
- **Measured effect (A/B, same warm-up injected by init script):** quiet x1 9/20 → 0/20, largest gap median 40 → 25.5 ms.
  x2 20/20 → 11/20, median 55 → 43.5 ms.
- **Open for L0: the planned acceptance HC-UIDOC-006 (a2), "the probe body at `HC_PROBE_CPU=2` passing 20/20", would stay
  RED with this change alone** (measured 11/20 misses). At x2 the commit without ICU is still about 22-26 ms of React dev
  render and commit (react-dom 14-20 ms; no single product line over 4 ms), followed by an 8-18 ms frame, and in 2/20 the
  ThinkingOrb's first canvas draw at import start (40-47 ms). Two ways forward:
  1. Accept (a2) at x1 (20/20 measured with the warm-up). CI's 42-50 ms matches this box at x1.
  2. License more product work for x2: split the import-complete commit, or make the ThinkingOrb's first frame cheaper.
     Neither has a single hotspot like the ICU call, so this would need its own diagnosis.
  The 40 ms bound stays in both. Choosing between them is L0's call; this diagnosis does not pick one.

## Siblings (same class, other files: outside the 006 (a) licence)

- **HC-UIASK-005 (UIASK-005-FLAKE):** the same ICU class. The first `toLocaleTimeString([], {hour, minute})` at
  `ExplainAssistant.tsx:721` sits inside the Send-click render. The same warm-up (with the same options) takes x1 from 1/20
  to 0/20, but x2 stays 20/20 (median 55.5 ms; the rest is react-dom dev work in the click task). Its own row would license
  `ExplainAssistant.tsx`.
- **/export :430/:472 (UIEXPORT-430-FLAKE):** no ICU and no single product hotspot. The gap is Playwright's click
  dispatch (hit test) followed by the pending-state commit of `ExportPage`, both spread across many components. Quiet box
  x1: 1/20 (:431) and 0/20 (:473). There is no option (a) target to name. A known-flake note (option (c)), or a separate
  diagnosis if L0 wants one.

## What this would not notice / skipped

- The traced runs inflate the ThinkingOrb canvas init by a factor of 10-100, and they slow everything else too. Trace
  ms are attribution, not rates. The rates come from the untraced lines only.
- The /export quiet-box line was recorded before a dump-name collision was fixed, so its per-test numbers come from the
  `DIAG` console lines in `logs/q1-export.log`, not from the JSON dumps. /export at x1 has no traces of a miss: the 12
  traced x1 runs all passed.
- Production build (`vite preview`) not measured. CI's smoke job runs the dev server, so the dev server was the target.
- A CI-runner-only long task that CDP throttling does not reproduce would not show here. The CI gap values (42-50) do match
  quiet-box x1.
- The ICU warm-up A/B was injected by an init script. The real change runs from a React effect, so its timing relative to
  the trigger will be close but not identical. Task 2 must re-measure.

## Files

- Driver, hooks, probe copy, parsers: `~/hc-quiet-logs/staging-1111a/uidoc006a-diag/tools/`
- Raw Playwright logs (one per line: `q1-*` quiet, `c2-*`/`c4-*` throttled, `t1-*`/`t2-*` traced, `w1-*`/`w2-*` ICU-warm
  A/B, `smoke`), plus the parser outputs: `~/hc-quiet-logs/staging-1111a/uidoc006a-diag/logs/`
- Per-run JSON dumps (sampler gaps, LoAF and longtask entries, marks): `~/hc-quiet-logs/staging-1111a/uidoc006a-diag/dumps/`
- Traces (gzip, 70 files): `~/hc-quiet-logs/staging-1111a/uidoc006a-diag/traces/`
- Served Vite sources used to map profile lines: `~/hc-quiet-logs/staging-1111a/uidoc006a-diag/served/`
- Servers: Playwright's webServer started and stopped them per line. Two short `vite` servers on :5199 (to fetch the
  transformed sources) were started and killed by this task. No PORT-LEAK in any log, and `ss -ltn` showed nothing on
  3000/4173/5173/8000/5199 at the end.
