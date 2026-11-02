# Follow-ups 2026-10-28 — plans for VITEST-TZ-PIN, G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE and AUDIT-GUARD-ATTR-DYNAMIC

**Last Updated:** 2026-10-29 (Opus planner on `41fa3824`: TOAST-SHELL added (the shared Toaster's centring transform fails G5 on `/care-tasks`, found by UI-PG-CARE #400; bullet TOAST-PHONE-CHROME absorbed); no owner gate); 2026-10-28 (Opus planner on `434179a9`: DARK-PRIMITIVE-CONTRAST added (dark primary Button and Input fail G1; sources #365 (BUTTON-DARK-CONTRAST, deferred to UI-DARK-FLIP), #400 and #398; supersedes the #365 deferral); no owner gate; #404 review round 1: history, sources, the corrected cause, mapping rules, settle wait, and every page row now depends on it); 2026-10-28 (#392 review round 2 on `b1ee5794` (#370 merged): UIG006-PASS3-FLAKE ready, pass-3 re-cited; the VITEST-TZ-PIN sweep runs on a native Linux clone or a CI matrix; HC-UIG-009 reads `__seq` at trigger and after; fail-fixture (m) under decision (a); the Node fetch promise is awaited); 2026-10-28 (#392 Opus review round 1, REVISE: VITEST-TZ-PIN zone sweep before the pin, `VITEST_TZ` override, `/mnt` run required; UIG006 mutant m4, a Node-side fetch, decision (a) to L0; quiet-box lock and `hold_slots.sh` on both Playwright rows; scratch worktree (recurring-failures #13); failure-rate rule; HC-UIPV-007 method; HC-UIPV-006 A/B facts; property-skip rule and HC-AUD-ORD-033 mixed case); 2026-10-28 (Opus planner on `9d0dc2a`: four follow-up bullets planned as rows; GATES-PASS3-ELAPSED folded into UIG006-PASS3-FLAKE; HC-UIPV-006 noted as pending L0 evidence, no row)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). No row below needs an owner gate; each names the point where it stops and goes to L0 instead.
**Base measured:** `origin/main` @ `9d0dc2a` (2026-10-28, after #391), refreshed for the e2e and frontend rows on `b1ee5794` (#370, UI-SHELL, merged): of the files cited here #370 changed only `e2e/ui-gates.spec.ts` (re-cited below) and two grid tokens in `VerificationWorkbench.tsx` (`:731-736` unchanged). Every `file:line` below was re-read by the planner on those commits. Product code was read only.
**Refresh Trigger:** a merge of STILLNESS-NAV-LATE, B-3 (#264) or RSI1-DONATE PR-2 (#239); a second HC-UIPV-006 failure; any edit before these rows are built to `src/frontend/vitest.config.ts`, `src/frontend/e2e/ui-provenance.spec.ts`, `src/frontend/e2e/ui-gates.spec.ts`, `src/frontend/e2e/support/gates.ts`, `src/frontend/src/components/PageImageOverlay.tsx`, `src/backend/tests/support/callgraph.py` or `src/backend/tests/test_audit_order_guard.py`.

Queue rows: [queue.md, "Planned 2026-10-28, follow-ups"](2026-10-15-build-program/queue.md#planned-2026-10-28-follow-ups). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`, `e2e/` = `src/frontend/e2e/`.

**Rules that hold for every row here.**
- Two rows (G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE) fix test-harness races. The fix makes the test wait for the right condition. No row relaxes a bound, adds a retry, or marks a test flaky, fixme, skip or fail. No row changes a constant in `e2e/support/gates.ts`.
- **CI's `retries: 2` hides a failure.** A retried pass is listed as `flaky` and the job still exits 0. So "CI E2E green" here also means the job log summary lists none of the row's tests as flaky.
- **Quiet box for every Playwright measurement** (G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE), as STILLNESS-NAV-LATE does: L0 holds `/tmp/claude-1000/quiet-box.lock` for the run; each Playwright command runs under `/tmp/claude-1000/hold_slots.sh`; `uptime` (1-minute load below 1.5) and the quiet-box `pgrep` and `ss` checks (RUNBOOK §10.1; empty) are pasted first. These rows run alone: never beside pytest, vitest, another Playwright run or a model-host row.
- **Scratch copies and mutants run in a separate scratch worktree**, never in the row's own worktree (recurring-failures #13: an agent returned while its own background mutation run was still editing the worktree). Location: `<repo-parent>/hc-<id>-scratch`, made with `git worktree add --detach <repo-parent>/hc-<id>-scratch <row branch HEAD>`, removed with `git worktree remove --force` once every scratch run has finished and its output is pasted. `git -C <row worktree> status` must be clean of scratch files before the PR leaves draft.
- **"0 failures after" needs a measured failure rate before.** Let p = failures / runs in the row's RED measurement. The after-fix run count at the same setting is N = max(40, ceil(3 / p)) (the rule of three: 0 failures in N bounds the rate below 3/N at about 95 %). If p is below 1 % (N above 300), stop and report to L0 instead of claiming a fix.
- **MVP priority** uses the scale in the [MVP plan](2026-10-22-mvp-rows-plan.md): P0 = a false safety, privacy or lab-value claim on screen; P1 = visible on the demo path, or blocks a P0/P1 row's acceptance; P2 = after the demo is fine.

---

## VITEST-TZ-PIN — pin the vitest time zone in the config, because a worker thread cannot change it

**Source:** bullet VITEST-TZ-PIN (found 2026-10-25, #364). `fe/__tests__/Gamification.test.tsx:202` fails when the host time zone is America/Los_Angeles and passes 20 of 20 with `TZ=America/New_York`.

**Root cause (measured by the planner).** The `AchievementsWidget` describe block (`Gamification.test.tsx:188-191`) sets `process.env.TZ = 'America/New_York'` in `beforeAll`. Line 202 then checks that the switch worked: `new Date('2026-03-05T12:00:00Z').getTimezoneOffset()` must be 300. `src/frontend/vitest.config.ts:8,20` picks `pool: 'threads'` whenever the working directory starts with `/mnt/` (the WSL checkout), and `'forks'` otherwise. Node applies a runtime `process.env.TZ` write only on the main thread. In a `worker_threads` worker the write changes the variable but not the time zone. Planner check on this box (Node v26.2.0, host `TZ=America/Los_Angeles`), script `/tmp/claude-1000/tzw.js` and `tzm.js`:

```
worker before 480
worker after 480        # process.env.TZ = 'America/New_York' inside the worker: no effect
main 300                # the same write on the main thread works
worker inherits 300     # and a worker started afterwards inherits it
```

So the describe's switch works on CI (Linux, `forks`) and, unmeasured, should work on native Windows (`forks`); it silently does nothing on a WSL `/mnt` checkout (`threads`). There, line 202 sees the host offset (480 in Los Angeles), and the sanity check fails as it was written to.

**Pin, or fix the test? Pin.** The test checks product behaviour that depends on the time zone by design. `fe/components/medication-coach/AchievementsWidget.tsx:54` shows `parseUtc(badge.earned_at).toLocaleDateString(...)`: it reads a naive `earned_at` as UTC and shows the patient's local date. To tell "read as UTC" from "read as local", the test needs a zone that is not UTC. It already says which one (America/New_York) and checks that it got it (line 202). Nothing in the product should be zone-independent here, so a pin hides no product bug. What is broken is how the test sets the zone, and the smallest correct fix is to set it where every pool inherits it: in the config, on the main process, before the pool starts.

**What the pin changes elsewhere.** Today CI runs every vitest file in the runner's zone (UTC on GitHub's Linux runners). After the pin, all 60 test files under `fe/` (on `b1ee5794`) run in one zone everywhere, and the suite loses whatever zone diversity hosts gave it. Product code does mix zones: `fe/services/export.ts:249` and `:263` name the export file with `new Date().toISOString().split('T')[0]`, a UTC date, while the badge date is local. So the row first measures, before the pin, which files depend on the zone (Task 1). Any zone-dependent file is a stop for L0, not something the pin may paper over. The pin also reads an override, `VITEST_TZ`, so a later zone sweep needs no config edit.

**Task 1 (measure, before any change).** **Where:** not on `/mnt`. `vitest.config.ts:8,20` switches to `threads` there because `forks` stalls under WSL on `/mnt` (`docs/agentic/orchestration.md:45`). The sweep runs either on a native Linux clone outside `/mnt` (`git clone <origin> ~/hc-vtz-sweep && cd ~/hc-vtz-sweep && git checkout <row base> && cd src/frontend && npm ci`; removed afterwards), or as a one-off CI matrix over the four zones on a `seed/vitest-tz-pin` branch (no PR; deleted after; the CI-seed pattern E-3 Task 8 used). **A hang is a stop, not a skip:** paste where it hung and ask for an `L0 ruling:`. Run the full suite in the `forks` pool, where a host `TZ` takes effect, once per zone, from `src/frontend`: `TZ=<zone> npx vitest run --pool=forks` for UTC, America/New_York, America/Los_Angeles and Asia/Kolkata. Paste per zone the files and tests passed and failed. Expected: all four zones pass, since `Gamification.test.tsx` sets its own zone and that switch works in `forks`. **Any file that passes in one zone and fails in another is a stop:** paste the failing assertion and ask for an `L0 ruling:`. The pin lands only after a clean sweep.

**Files:**
- `src/frontend/vitest.config.ts`: at module top, `process.env.TZ = process.env.VITEST_TZ ?? 'America/New_York';` with a one-line comment: Node ignores a `TZ` write inside a worker thread, so the zone is set here, before the pool starts (VITEST-TZ-PIN). No other change.
- `fe/__tests__/vitest-tz-pin.test.ts` (new, HC-VTZ-001).
- `Gamification.test.tsx` is **not** edited. Its `beforeAll`/`afterAll` become a no-op, but they still record the zone the test needs, and UI-PG-MEDS and UI-PG-SETTINGS own that file.

**RED test.**
- **HC-VTZ-001** `the vitest process runs in the pinned zone`: `Intl.DateTimeFormat().resolvedOptions().timeZone` equals `process.env.VITEST_TZ ?? 'America/New_York'`, and, when no `VITEST_TZ` is set, `new Date('2026-03-05T12:00:00Z').getTimezoneOffset()` is 300. RED on main in both pools: CI (UTC, `forks`) gives `UTC`/0, and the WSL checkout (Los Angeles, `threads`) gives `America/Los_Angeles`/480. Paste both RED outputs, or the CI one plus the local one.

**Acceptance (outputs pasted):**
1. HC-VTZ-001 RED then GREEN.
2. Task 1's four-zone sweep, pasted per zone with where it ran (native clone path or CI run id), clean before the pin.
3. **The `/mnt` (`threads`) run is required**, because it is the only place the bug shows. The implementer runs it in the row's own worktree under `/mnt/e/...` (the pool there is `threads`), with host zone America/Los_Angeles: `npx vitest run src/__tests__/Gamification.test.tsx src/__tests__/vitest-tz-pin.test.ts` fails at `Gamification.test.tsx:202` before the pin and passes 20 of 20 after (a shell loop; paste the count). Then the full `npx vitest run` there. The build-item runner's "frontend vitest stalls under WSL on /mnt/c: record it as skipped" rule (`.claude/workflows/build-item.js:273`) does **not** apply to this row: if the runner skips it, the implementer or L0 runs these commands by hand and pastes them, and the PR does not leave draft without them.
4. Full `npx vitest run` green on CI (`forks`, UTC host, pin in force).
5. `npx tsc --noEmit` clean.

**Depends on:** none. **Never beside:** another `src/frontend/vitest.config.ts` PR. It shares no file with UI-PG-MEDS or UI-PG-SETTINGS (both own `Gamification.test.tsx`). **Gate:** none. **Ask-first files:** none. **Est:** 1 h (the zone sweep is four full runs). **Runtime:** claude (needs the WSL `/mnt` checkout). **MVP:** P2 (a local test ergonomics fix; no screen changes).

---

## G1-VERIFY-TRACE-RACE — the /verify interaction must wait for the new page image, not the old one under a new label

**Source:** bullet G1-VERIFY-TRACE-RACE (found 2026-10-28, #390 CI run 40643774878). `e2e/ui-provenance.spec.ts:546` "Gate G1 /verify own nodes have no serious or critical violation in light or dark" failed once and passed on retry. The planner re-read the job log (job 122669877096). The failure is at `ui-provenance.spec.ts:558`, the after-interaction `assertOwnMatched`: `own selector matches no visible node: [data-page-image-overlay] [data-trace-mark]` (`Received: 0`). CI uploads no `test-results/` for E2E, so there is no trace or error-context to read.

**What the test does** (`ui-provenance.spec.ts:429-449`). `ready` opens `/verify?doc=…`, waits for the page-3 image (`SOURCE_IMAGE`) and settles it with `waitForSettled`. `interact` clicks the "Hemoglobin A1c" row (page 1), runs `waitForSettled(page, PAGE_ONE_IMAGE)` with `PAGE_ONE_IMAGE = 'img[alt="Page 1 of document"][src^="blob:"]'`, then `expect(PAGE_IMAGE_TRACE_MARK).toBeVisible()`. The G1 test then runs `assertOwnMatched` (`:281-288`), a one-shot count with no retry.

**Planner's hypothesis (from code reading; Task 1 must confirm or refute it).** Two harness defects add up, and together they explain a mark that was visible and then gone:
1. **`waitForSettled` carries frames from the previous call** (`ui-provenance.spec.ts:211-231`). Its state lives in `window.__hcSettle` and is never reset. `ready` leaves `frames >= 6` for the page-3 `<img>`. `PageImageOverlay` keeps the same `<img>` element (`VerificationWorkbench.tsx:731-736` renders the same component at the same place, with no `key`), and both pages are the same 400 × 100 PNG (`ui-provenance.spec.ts:132-138`). So the first poll after the click sees an unmoved rect and returns on its first frame, without the six fresh frames the helper's docstring promises.
2. **For a moment the old image matches the new selector.** On the row click, `PageImageOverlay` (`fe/components/PageImageOverlay.tsx`, effect `:42-69`) first re-renders with `pageNumber=1` while its state still holds page 3's `imageLoaded = true` and the old `blob:` src. The `alt` is already "Page 1 of document", and the highlight with its `TraceMark` is still mounted (`:148-162`). The effect that resets that state runs after the commit. Its `setState` calls are default-priority updates (React 18.3.1), so the browser can paint a frame between them. In that frame `PAGE_ONE_IMAGE` matches the page-3 image at full opacity, and the old mark is visible. Then the reset unmounts the mark until the page-1 blob loads. If `toBeVisible` lands in the stale frame and `assertOwnMatched` lands after the reset, the test fails exactly as CI reported.

The stale frame is a one-frame product glitch: the page-3 image under a "Page 1" label. This row does not change it (see Out of scope).

**Task 1 (measure; no committed change).** In a scratch copy of the spec:
- Before the click, record the page-3 `<img>`'s `src`. At the moment `interact` returns, and again just before `assertOwnMatched`, record: the `<img>`'s `alt`, `src`, whether `src` equals the pre-click value, `complete`, `naturalWidth`, and the mark count.
- In the scratch worktree (rules above), run `/tmp/claude-1000/hold_slots.sh npx playwright test e2e/ui-provenance.spec.ts --project=chromium --workers=1 --retries=0 --repeat-each=60 -g "G1 /verify"`, once as is and once with CDP CPU throttling ×4 (`Emulation.setCPUThrottlingRate`) applied in the scratch copy. Quiet box first (lock, `uptime`, `pgrep`). Paste the pass and fail counts and the recorded fields of every failing run.
- **Decision rule:**
  - (a) A failing run shows `src` equal to the pre-click value (or a `blob:` URL already revoked) when `interact` returned: the hypothesis holds; do Task 2.
  - (b) Failures show something else: stop, paste the fields, and ask for an `L0 ruling:`. Do not change the test by guess.
  - (c) 0 failures in 120 runs: do Task 2 anyway. HC-UIPV-007 is RED on its own, and the src check is the condition the test claims to wait for. The PR states that the CI failure was not reproduced, and acceptance 3 then has no failure rate to scale by (it stays at 60 + 60).

**Task 2 (the fix; `e2e/ui-provenance.spec.ts` only).**
- `waitForSettled` resets its frame count at the start of each call: `__hcSettle` is cleared, or the state is keyed by selector and call. It then needs six fresh frames, as its docstring says. Today a poll that finds no element (`:215`, `if (!el) return false;`) returns without touching `__hcSettle`, so frames counted before the element vanished survive its absence. The fix also clears the state on that path, so the six frames are consecutive frames on a present element. Every caller gets stricter, never looser.
- The `/verify` `interact` waits for the right image: before the click it reads the current `<img>`'s `src`. After the click it waits (`expect.poll` or `waitForFunction`) until `img[alt="Page 1 of document"]` has a `blob:` src **different from** the pre-click src, with `complete === true` and `naturalWidth > 0`. Then it calls `waitForSettled(page, PAGE_ONE_IMAGE)`, then `expect(PAGE_IMAGE_TRACE_MARK).toBeVisible()` as today.
- No other change. `assertOwnMatched` stays a one-shot count: turning it into a polling assertion would hide exactly this kind of race. `GATE_ROUTES[].own` and `ownBefore` stay as they are, and nothing in `e2e/support/gates.ts` changes. The G2, G3, G5, G6 and G7 (`:636-641`) `/verify` tests use the same `interact` and get the same wait. HC-UIPV-006's setup also calls `waitForSettled` (`:520`, `:527`), so the stricter helper changes when its probe starts (see acceptance 5).

**RED test.**
- **HC-UIPV-007** `waitForSettled needs six fresh frames on every call` (in `ui-provenance.spec.ts`, using `page.setContent`): settle element A, replace it with element B at the same rect. **Frame counting:** immediately before the call, `page.evaluate` starts an in-page counter, `window.__rafCount = 0` plus a self-rescheduling `requestAnimationFrame` callback that increments it; immediately after `waitForSettled` returns, `page.evaluate` reads `__rafCount` and stops the loop. The test asserts the count is at least 6. A second case removes B for a few frames mid-wait and re-adds it, and asserts at least 6 frames after the re-add (the `:215` path). RED on main: the first case returns after about 1 frame. **Verified over repeats:** run it with `--repeat-each=20 --retries=0`; RED on all 20 before the fix, GREEN on all 20 after; paste the min and max count of each set.

**Acceptance (outputs pasted):**
1. Task 1 counts and fields, and the decision taken (a, b or c).
2. HC-UIPV-007 RED then GREEN.
3. After Task 2, with the same commands and setting as Task 1: `G1 /verify` passes N of N unthrottled and N of N at CPU ×4, `--retries=0`, with N from the failure-rate rule above (at least 60 each). Under (a), the Task 1 failure count is the RED for this.
4. The whole `e2e/ui-provenance.spec.ts` passes with `--retries=0` (HC-UIPV-001…007 and Gate G on all three routes). CI E2E green, and the job log summary lists no `ui-provenance.spec.ts` test as flaky.
5. HC-UIPV-006 gap figures before and after: `--repeat-each=20 --retries=0 -g "HC-UIPV-006"` on main and on the branch, quiet box, pasting pass count and each run's `maxGapMs` (min, median, max). A worse pass count on the branch is a stop for L0.
6. `git diff --stat` touches `e2e/ui-provenance.spec.ts` only.

**Depends on:** none. **Never beside:** another `e2e/ui-provenance.spec.ts` PR, including any HC-UIPV-006 row if one is ever opened. Runs alone on a quiet box (rules above): never beside pytest, vitest, another Playwright run or a model-host row while Task 1 or the acceptance runs. **Gate:** none. **Ask-first files:** none (no product file changes). **Est:** 3 h. **Runtime:** claude. **MVP:** P2 (CI retries hide it; it blocks no demo path).

**Out of scope, for L0.** The one-frame stale render in `PageImageOverlay` (page 3's image under a "Page 1" label, with the new row's highlight) is a product glitch that Task 1 may confirm. If it does, the PR names it as a new follow-up bullet. A product fix would be a `key` on the overlay or resetting state during render, in the UI-PG-REVIEW area. This row does not fix it.

---

## UIG006-PASS3-FLAKE — reproduce the pass-3 miss, then make the fixture's fetch start when its scenario says

**Source:** bullet UIG006-PASS3-FLAKE (found 2026-10-28, #390 review): HC-UIG-006 pass 3 once reported `elapsedMs` 741 < 2000. **Folded in:** bullet GATES-PASS3-ELAPSED (found 2026-10-25, #374): the same test once reported `elapsedMs` 1657 < 2000, unexplained, "needs a reproduction before a row". This row is that reproduction first.

**What the test does** (on `b1ee5794`). Fixture pass-3 (`e2e/ui-gates.spec.ts:583-592`): `__start` runs `setTimeout(() => fetch('/gates/slow'), 50)` (`:589`). The route answers after 1200 ms (`serveFixture`, `:46-62`). `runPassFixture` (`:612`) asserts `elapsedMs >= 2000` (`:625`). Fail-fixture (m) (`:482-492`) uses the same 50 ms page-timer pattern (`:486`) to start its lazy fetch. In `stillnessProbe` (`e2e/support/gates.ts:815-879`) with `lazyRoute`, `trackRequests` starts before the trigger, and `lastEventAt` starts at tracker creation (`:786`). After the trigger, the probe waits until nothing is in flight and `NETWORK_IDLE_MS` (500) has passed since the last request event (`:830-839`). It then runs the 800 ms window. `elapsedMs` is wall time from just before the trigger to the end of the window (`:828`, `:843`).

**Two readings, and what each implies.**
- **1657 ms (GATES-PASS3-ELAPSED) fits the bullet's diagnosis.** The page's 50 ms timer fired late, more than about 450 ms after the tracker started, as it can under CPU contention. The quiet period then ended before the request event, and the window closed at roughly 850 + 800 ms, before the fetch's 1200 ms. On that run the probe behaved as written: it saw 500 ms of quiet after the trigger. The fixture's scenario ("a fetch that starts after the trigger returns", meaning a few ms after) did not happen.
- **741 ms cannot come from main's code, barring a wall-clock step.** `Date.now()` is wall-clock time, not monotonic, so an NTP step during the run is the one way main could produce it. The loop ends only when `Date.now() >= windowStart + 800`, and `windowStart >= triggeredWall`. Both readings use the same clock, so `elapsedMs = Date.now() - triggeredWall >= 800` on every path while the clock moves forward. Otherwise a 741 reading must come from a different `gates.ts`. #390's review was mutation-testing that file ("an unmutated interaction path" in its PR body), so a mutant is the likely source, but that is not shown. Task 1 must not treat 741 as a reproduction target.

**Task 1 (measure; no committed change).** In the scratch worktree (rules above), in a scratch copy of the spec and fixture:
- Record in-page `performance.now()` at `__start` and at the `fetch` call. On the Node side, record `Date.now()` at the trigger, at the `/gates/slow` `request` and `requestfinished` events, at the return of the idle wait, and `elapsedMs`. (The idle-wait time needs a scratch copy of `gates.ts` that logs it. Never commit that copy.)
- Run `/tmp/claude-1000/hold_slots.sh npx playwright test e2e/ui-gates.spec.ts --project=chromium --retries=0 --repeat-each=40 -g "pass-3"`, once quiet with `--workers=1`, and once under load: `--workers=4`, plus 4 busy-loop `node -e` processes started by the row and listed with `pgrep`. Quiet box first (lock, `uptime`, `pgrep`); the load is the row's own, and it is stopped and shown stopped afterwards. Paste counts and the fields of every failing run.
- **Decision rule:**
  - (a) Every failing run has the in-page fetch call more than 400 ms after `__start` (timer starvation): stop and ask for an `L0 ruling:`. This may be a limit of the probe (a request that starts after its 500 ms quiet period is not waited for, in the app as in the fixture), not a fixture bug. The ruling covers **both** fixtures that start their fetch from a 50 ms page timer: pass-3 (`:589`) and fail-fixture (m) (`:486`), which can pass for the wrong reason the same way (its transform never lands inside a window that closed early). Task 2 below is the planner's candidate for L0 to accept, change or reject, for pass-3 and, if the ruling says so, for (m).
  - (b) A failing run has the fetch call on time but the Node `request` event more than 400 ms after it (event delivery lag), or any run gives `elapsedMs < 800`: stop and ask for an `L0 ruling:`. That would be a probe matter in `gates.ts` logic, and the probe's idle rule is the G10 gate's definition for real lazy routes.
  - (c) 0 failures in 80 runs: stop and report. No fix without a reproduction (the GATES-PASS3-ELAPSED rule).

**Task 2 (only under an `L0 ruling:`; `e2e/ui-gates.spec.ts` only). Planner's candidate:**
- **The fetch still starts after the trigger has resolved in Node.** A page microtask is rejected: it starts the fetch before Node sees the trigger resolve, so the request is already in flight at the probe's first idle check, and mutant m4 below survives. Candidate: `__start` only arms the fixture; the test's trigger awaits `__start`, then schedules, without awaiting inside the trigger, a Node-side `setTimeout(() => page.evaluate(() => window.__fetchSlow()), 50)`. The promise of that `page.evaluate` is kept (e.g. the `setTimeout` callback resolves a stored promise) and **awaited before the test ends**, after the probe returns, so a rejected or still-pending evaluate fails the test instead of leaking past it. The fetch then starts after the trigger has resolved, from a Node timer rather than a page timer. Whether a Node timer is steadier under the Task 1 load is measured, not assumed: the same Task 1 timings, logged for the new fixture.
- **HC-UIG-009** `pass-3's fetch starts after the trigger resolves`: ordering is checked with a sequence, not with `>=` on `performance.now()`. Node keeps an array: it pushes `trigger-resolved` when `__start`'s evaluate resolves and `fetch-sent` just before it calls `__fetchSlow`; the page pushes `fetch-called` in `__fetchSlow` into `window.__seq`. `__start`'s evaluate returns a copy of `window.__seq`, and the test asserts it is `[]` when the trigger resolves. After the probe (and the awaited fetch evaluate), the test asserts Node's array is `['trigger-resolved', 'fetch-sent']` and `window.__seq` is `['fetch-called']`.
- `expect(report.elapsedMs).toBeGreaterThanOrEqual(2000)`, `slowFetchMs: 1200` and every constant in `gates.ts` stay as they are.
- **Mutation check (the fixture must still catch a broken probe).** With the new fixture, each of these four scratch mutants of `stillnessProbe`, run in the scratch worktree, must make pass-3 fail; paste each failure: (m1) the lazy wait replaced by `page.waitForLoadState('networkidle')`; (m2) the `inFlight.size === 0` term removed; (m3) `windowStart` left at `triggeredWall` (the window not restarted after the idle wait); (m4) the `Date.now() - network.lastEventAt >= NETWORK_IDLE_MS` term removed (`gates.ts:835`). **A fixture that lets any of m1-m4 survive is rejected.** Mutants are never committed.

**RED tests.**
- The Task 1 failure count under load is the RED for the fix. Rerun at the same load after Task 2: 0 failures in N, with N from the failure-rate rule above.
- **HC-UIG-009**: RED first against a scratch fixture whose `__start` calls `__fetchSlow` itself (so `__seq` is `['fetch-called']`, not `[]`, when the trigger resolves; the assertion must be able to fail), then GREEN with the candidate fixture.

**Acceptance (outputs pasted):**
1. Task 1 counts, fields and decision.
2. The `L0 ruling:` that licensed Task 2, quoted.
3. After Task 2, pass-3 passes N of N at the Task 1 load and 40 of 40 quiet, `--retries=0`, with each run's `elapsedMs` logged and at least 2000.
4. HC-UIG-009 RED then GREEN. Mutants m1, m2, m3 and m4 each fail pass-3.
5. The whole `e2e/ui-gates.spec.ts` passes (HC-UIG-001…009) with `--retries=0`. CI E2E green, and the job log summary lists no `ui-gates.spec.ts` test as flaky.
6. `git diff --stat` touches `e2e/ui-gates.spec.ts` only. `git diff origin/main -- e2e/support/gates.ts` is empty.

**Depends on:** UI-SHELL (done, #370 `b1ee5794`). **Never beside:** another `e2e/ui-gates.spec.ts` or `e2e/support/gates.ts` PR (STILLNESS-NAV-LATE Task 2 if its ruling names either file), and runs alone on a quiet box (rules above) while Task 1 or the acceptance runs. **Gate:** none (Task 2 waits on an `L0 ruling:`, not an owner gate). **Ask-first files:** none. **Est:** 3 h. **Runtime:** claude. **MVP:** P1. A pass-3 miss is a stillness self-test listed as flaky, which fails STILLNESS-NAV-LATE's acceptance ("no stillness test listed as flaky").

---

## AUDIT-GUARD-ATTR-DYNAMIC — the audit-order guard flags a bound method passed as a value

**Source:** bullet AUDIT-GUARD-ATTR-DYNAMIC (found 2026-10-27, L0 ruling on #385, comment 6442124521). In `be/tests/support/callgraph.py`, `Graph.dynamic_sites` (`:99-133`) flags a def passed as an argument only when the argument is a bare name (`work`) or `self.<def>` / `cls.<def>` (`:116-132`). A bound attribute of any other object, such as `asyncio.to_thread(selector.detect_hardware_tier)` in `get_model_settings` (`be/api/model_settings.py:398`) and `list_tiers` (`:598`), is neither followed by `reachable` nor flagged. So the edge disappears silently from HC-AUD-ORD-030 (`be/tests/test_audit_order_guard.py:257-261`). That is why `list_tiers` went stale on #385 with no dynamic key reported.

**Measured by the planner** (scratch script `/tmp/claude-1000/agad/measure.py`, Python 3.12, on `9d0dc2a`; it subclasses nothing in the repo and edits no file):
- Today `_DYN` has 23 sites, all named (0 unlisted).
- Widening the argument rule to "any `<expr>.<attr>` whose `attr` names a def" adds **26** sites. 23 of them pass an attribute whose every same-named def is a `@property` (`settings.app_data_path` ×17, `self._settings.models_path` ×2, `item.key`/`data.key` ×3, `scheduler.last_pass_skipped_locked` ×1). Those are values, not callables.
- Excluding names whose every def is a property leaves **3** new sites (the property test used: a decorator that is `ast.Name` `property`/`cached_property`, or an `ast.Attribute` ending in `cached_property`/`setter`/`getter`/`deleter`):
  - `api/model_settings.py::get_model_settings::asyncio.to_thread(detect_hardware_tier)`
  - `api/model_settings.py::list_tiers::asyncio.to_thread(detect_hardware_tier)`
  - `modules/document_classifier.py::classify_document::max(get)` (`key=scores.get`, a dict method). The only def named `get` in the graph is `modules/agent/tools/registry.py::get`, whose reach is 1 def and no commit; the key's reason says so.
- `ModelSelector.detect_hardware_tier` reaches 139 defs. The commits among them are `backup_scheduler.run_due_backups`, `NotificationScheduler._send_notification` and `PatternLearner.relearn_unmarked_windows`, the same three name collisions #385's PR body recorded ("Without those edges, 39 defs and no commit").
- **An existing gap, not this row's:** `reachable` follows calls only, so a property getter's body is never reached through an attribute read. Measured today: 27 property defs (same decorator test), and none of their reachable sets commits (scratch `/tmp/claude-1000/agad/prop.py`). The plan records it; a property that starts to commit would be a new bullet.

**Files:**
- `be/tests/support/callgraph.py` (`dynamic_sites` argument loop only): also take `ast.Attribute` arguments whose base is not `self`/`cls`, `ref = v.attr`, under the same conditions as today (`ref in self.by_name`, not a param or local, not the callee's own name). Skip a `ref` when **every** def of that name is a property: a decorator that is `ast.Name` `property` or `cached_property`, or `ast.Attribute` `functools.cached_property`, or `<x>.setter`, `<x>.getter`, `<x>.deleter`. If one def of the name is a property and another is a plain method, the site is still flagged. The key format stays `relpath::qualname::<unparse(func)>(<ref>)`. Update the comment at `:116-119` to match. No change to `reachable`, `commits`, or any other method.
- `be/tests/test_audit_order_guard.py`: three new `NAMED_DYNAMIC_EXCLUSIONS` keys (the three sites above), each with a **measured** reason in the style of the `_diagnostics_list_response` entries (`:162-174`). Before writing a reason, paste the site's reachable set and say which `.commit()` it reaches and through which name collision. `list_tiers` does **not** come back into `CLASSIFICATION`. The edge is now flagged, not followed, so `_COMMITTING` is unchanged. Plus the new break-it tests below.
- `docs/agentic/recurring-failures.md` (#9 audit paragraph, one sentence) only if the PR judges this an instance of #9, as AUDIT-GUARD-TEST did.

**RED tests** (in `be/tests/test_audit_order_guard.py`, using the `_overlay` synthetic tree like `:299-309`):
- **HC-AUD-ORD-032** `break_it_bound_method_passed_as_argument`: `modules/zz_helper.py` defines `class S: def work(self): ...`. The handler runs `s = S(); await asyncio.to_thread(s.work)`. Expect `dyn - set(NAMED_DYNAMIC_EXCLUSIONS) == {"api/zz.py::zz::asyncio.to_thread(work)"}`. RED on main (empty set).
- **HC-AUD-ORD-033** `property_value_passed_as_argument_is_not_dynamic`: (1) a class with `@property def path(self)` and a handler calling `Path(cfg.path)`: no new dynamic site; the same with `@functools.cached_property` and with a `@path.setter` pair. (2) **Mixed case:** a second class with a plain method `def path(self)`; then `Path(cfg.path)` **is** flagged. Case (1) is GREEN on main and after; case (2) is RED on main and GREEN after. It pins the property exclusion so a later widening cannot turn 23 values into noise, and pins that the exclusion needs every def to be a property.
- On the real tree, `test_hc_aud_ord_030_dynamic_calls_are_named` goes RED with the new rule (3 unlisted sites; paste them), then GREEN once the three keys are added.

**Stop rule.** If any newly flagged site reaches a `.commit()` on a profile-data path other than through a name collision, stop and tell L0. That would be an audit gap in a real route, not a classification task. The same applies if the property-free count differs from 3 on the branch's base.

**Acceptance (outputs pasted):**
1. HC-AUD-ORD-032 RED then GREEN; HC-AUD-ORD-033 case (1) GREEN throughout and case (2) RED then GREEN; the real-tree RED list (3 sites) and then GREEN.
2. For each new key, the reachable-set output and the commit sites it names.
3. `scripts/pyslot.sh` run of `tests/test_audit_order_guard.py tests/test_audit_order.py tests/test_audit_phi_minimization.py`, all pass. Then the full backend suite through `pyslot.sh`, with no new failures against the baseline (5 environmental failures allowed only without the embedding bundle). Report the collected count and its delta (+2 expected; the PR does not edit the slot lines).
4. `cd src/backend && python -c "from main import app"`.
5. `git diff --stat` touches only the files listed above.

**Depends on:** none. **Never beside:** another `be/tests/test_audit_order_guard.py` or `be/tests/support/callgraph.py` PR. B-3 (#264) and RSI1-DONATE PR-2 (#239) also edit `test_audit_order_guard.py`, but both are parked drafts and hold no files (contracts §b rule 2), so they rebase onto this row. **Gate:** none. The row only adds detection, and each new named exclusion carries its measured reason for review. #385's L0 ruling is the precedent for this shape of key. **Ask-first files:** none (`test_audit_order_guard.py` is a guard; this row strengthens it and removes no entry). **Est:** 1.5 h. **Runtime:** any. **MVP:** P2.

---

## Not planned: HC-UIPV-006 popover stillness (one CI event, not reproduced)

HC-UIPV-006 (`e2e/ui-provenance.spec.ts:513`, the citation popover's `stillnessProbe`, an interaction probe with a 40 ms gap bound) failed once in CI on #370 run 40649511595 with a 41 ms gap. L0's A/B is done: HC-UIPV-006 ×20 passed 20 of 20 on #370 `479938d8` and 20 of 20 on main `9d0dc2a` (quiet box), and CI re-run attempt 2 on #370 was clean. **No row:** one 41 ms CI event, not reproduced. A second failure re-opens it, under the same rules (no bound change, no retry, no flaky mark, no change to `gates.ts` constants), and never beside G1-VERIFY-TRACE-RACE (same spec file). G1-VERIFY-TRACE-RACE's acceptance 5 reports HC-UIPV-006 gap figures before and after its change.

---

## DARK-PRIMITIVE-CONTRAST — the primary Button and the Input field fail dark-theme contrast

**Sources:** #365 (UI-PRIM-CONTROLS), #400 (UI-PG-CARE) and #398 (UI-PG-MEDS).
- **2026-10-25, #365.** UI-PRIM-CONTROLS' Gate G found the defect on `/setup` in dark: "Button.tsx primary text-white fails dark contrast on /setup; not applied". L0 named the follow-up BUTTON-DARK-CONTRAST and deferred it. The L0 ruling, verbatim: "The in-row dark-contrast failure (Button primary `text-white` on /setup in DARK) is deferred: the app is light-only until UI-DARK-FLIP (owner UI-DARK-MODE), whose gate HC-UIDRK-* covers it. L0 logs follow-up BUTTON-DARK-CONTRAST on UI-DARK-FLIP." The queue bullet BUTTON-DARK-CONTRAST records it.
- **2026-10-28, #400 and #398.** UI-PG-CARE stopped on the same failure, a serious `color-contrast` on the primary Button in Gate G1 dark. UI-PG-MEDS stopped on all four of its routes ("blocked: tell L0"). Its stop names a second primitive, `ui/Input.tsx`.

**This row supersedes the #365 deferral.** The deferral sent the fix to UI-DARK-FLIP, which is wave 9. The wave-5 page rows' Gate G already requires G1 in light **and dark** (frontend-revamp plan §6 G1), so they hit the failure first and cannot pass. The row keeps the bullet's ID history: it was first planned as BUTTON-DARK-CONTRAST, was widened to the Input field after #398, and is renamed **DARK-PRIMITIVE-CONTRAST**. No other row uses either name. The order mistake is logged as bullet DEFER-ORDER-CHECK in the queue.

**Base measured:** `origin/main` @ `434179a9`. The planner re-read every `file:line` below on that commit and read product code only.

**Cause (code reading, ratios computed with the WCAG 2.x sRGB formula the HC-UITK-001 helper uses).**
- `fe/components/ui/Button.tsx:26`, primary variant: `bg-accent text-white`. In dark, `--accent` is `#6fc6b3` (`fe/styles/globals.css:207`) and `--accent-hover` is `#86d1c0` (`:208`). Plan §2.2 already defines `--on-accent` for this pair: `#ffffff` light (`globals.css:165`), `#0b1d19` dark (`:211`), "on-accent on accent / accent-hover (primary button)". The danger variant next to it (`Button.tsx:33`) uses `text-[var(--on-status)]`, as §2.2 asks. The primary variant was never moved onto `--on-accent`.
- `fe/components/ui/Input.tsx:36`: `bg-white` with `text-ink` and `placeholder:text-ink-tertiary` (`:37`). In dark the text tokens turn light but the field stays white. Plan §2.2 gives cards and elevated surfaces `--surface-1`, which is `#ffffff` light (`globals.css:153`) and `#1c1c19` dark (`:199`), through the existing utility `bg-surface-elevated` (`@theme`, `globals.css:34`).

| Pair | Theme | Today | After the fix | Needs |
|---|---|---|---|---|
| primary text on `--accent` | dark | white on `#6fc6b3`: **2.02** | `--on-accent` `#0b1d19`: **8.64** | 4.5 |
| primary text on `--accent-hover` | dark | white on `#86d1c0`: **1.77** | `#0b1d19`: **9.88** | 4.5 |
| primary text on `--accent` / `--accent-hover` | light | white on `#1d6b5e` / `#185a4f`: 6.33 / 8.03 | unchanged (`--on-accent` is `#ffffff`): 6.33 / 8.03 | 4.5 |
| Input value text (`--ink-1`) on the field | dark | `#eeece6` on `#ffffff`: **1.18** | on `--surface-1` `#1c1c19`: **14.46** | 4.5 |
| Input placeholder (`--ink-3`) on the field | dark | `#a29e95` on `#ffffff`: **2.67** | on `#1c1c19`: **6.39** | 4.5 |
| Input border (`--line-strong`) on the field | dark | `#77736b` on `#ffffff`: 4.72 | on `#1c1c19`: 3.62 | 3 (1.4.11) |
| Input value / placeholder on the field | light | `#1c1b19` / `#68645d` on `#ffffff`: 17.21 / 5.88 | unchanged (`--surface-1` is `#ffffff`): 17.21 / 5.88 | 4.5 |

Light mode does not fail and does not change. Every replacement token has the same light value as the literal it replaces, so the computed light colours are byte-identical.

**Earlier gates did catch it, once, and it was deferred.** UI-PRIM-CONTROLS' Gate G found it on `/setup` in dark (#365). L0 deferred it to UI-DARK-FLIP (wave 9) without checking that the wave-5 page rows, whose Gate G requires dark G1, run first. That ordering is the cause of the two stops. Since #365, nothing on `main` has asserted page-wide axe in dark, so nothing else could catch it. `KNOWN_A11Y` (`accessibility.spec.ts:88-95`) is empty on every route, so no entry hides it.
1. `e2e/accessibility.spec.ts` and `e2e/ui-tokens.spec.ts:62` run G1 light only. UI-TOKENS' acceptance says "G1 light; dark contrast is covered by HC-UITK-001 until each page row runs G1 dark".
2. HC-UITK-001 (`fe/__tests__/ui-tokens.test.ts:120-121`) proves that the token pair `--on-accent` on `--accent` reaches 8.64 in dark. Nothing checks that `Button` uses that pair.
3. `e2e/ui-shell.spec.ts:112-127` (`shellAxeBlocking`) runs dark axe on the shell regions only. It calls `.exclude('[data-route-container]')`.
4. `e2e/ui-provenance.spec.ts:290-304` (`ownAxeBlocking`) asserts dark on the row's own nodes only: the chip, the popover and the page-image overlay. Its page-wide dark result, `recordPageWideAxe` (`:310-331`, called at `:563-564`), is record only.
5. No `UI-PG-*` page row has merged. UI-PG-MEDS and UI-PG-CARE are the first rows since #365 whose gate asserts page-wide G1 dark. 44 `<Button>` elements in 27 non-test files use the primary variant (43 by default, 1 explicit), and there are 22 `<Input>` elements, so every later page row would hit the same failures.

**Other `bg-accent text-white` and `bg-white` sites: not this row.** Page code with the same pairing, at origin/main lines: `fe/components/MemoryManager.tsx:139,152`, `fe/pages/ExplainAssistant.tsx:544,621,725`, `ExportPage.tsx:705`, `DocumentInbox.tsx:226`, `LabInterpreter.tsx:216`, `ProfileSetup.tsx:487`, `TrendsDashboard.tsx:330`. These sit in files that page rows own. Each page row's own G1 dark will flag them, and UI-DARK-FLIP's HC-UIDRK-001 source scan (no allowlist) flags every `text-white` and `bg-white` left over. The primitives `ui/Select.tsx:22` and `ui/Textarea.tsx:35` have the same `bg-white` field, but no page renders either one on origin/main (0 JSX uses). They are left to HC-UIDRK-001 and are not widened in here. `ui/Checkbox.tsx:18` and `ui/Switch.tsx:32` hold no text.

**Owner gate: none.** The fix adds no colour value. It uses two tokens that already exist:
- Frontend-revamp plan §2.2 defines "Text on accent `--on-accent` `#FFFFFF` / `#0B1D19`" (`2026-10-23-frontend-revamp-plan.md:90`) and computes "on-accent on accent / accent-hover (primary button) 6.33 / 8.03 light, 8.64 / 9.88 dark" (`:108`).
- `--surface-1` is the §2.2 "Card / elevated" token (`:85`).

Both were merged into `globals.css` under the UI-TOKENS queue row (#356, `335e5f9`). The owner's UI-DARK-MODE answer is **"Follow OS setting"**: "Ship dark mode on, following the operating system, once every page is migrated." This row is part of that migration. The owner made no separate choice of dark colours, and this row claims none. Light is unchanged, so TW4-VISUAL's computed-style asserts keep their values. The planner rejected a darker dark-mode accent fill with white text: it would add a token and change the dark brand colour, which is a new visual decision and would need an owner question first. This row does not draft or ask that question.

**Files:**
- `fe/components/ui/Button.tsx:26`: `text-white` → `text-[var(--on-accent)]` in the primary variant only. That is the same form as danger's `text-[var(--on-status)]`. Nothing else changes.
- `fe/components/ui/Input.tsx:36`: `bg-white` → `bg-surface-elevated`. Nothing else changes.
- `fe/__tests__/ui-tokens.test.ts` (extended, because it already has `TOKENS`, `resolveToken` and `contrastRatio`): the mapping helper and HC-DPC-001 and HC-DPC-002.
- `e2e/ui-dark-primitives.spec.ts` (new): HC-DPC-003. It is a new file so the row shares no spec with a page row.

`globals.css` is **not** edited: every token needed already exists.

**RED tests (HC-DPC-001 … 003; `HC-DPC` is unused on origin/main).**

**Class-to-colour mapping (HC-DPC-001 and 002).** One helper in `ui-tokens.test.ts` reuses `TOKENS`, `resolveToken` and `contrastRatio` (`:47-87`).
- It splits the class string on whitespace. A class counts only if, after stripping its state prefix, it is a **colour** utility for `bg-`, `text-` or `border-`. The state prefix is none (rest), `hover:` or `placeholder:`.
- **Mapping:**
  - Named utilities go through the `--color-<name>` entry of the `@theme` block (`globals.css:27`) to the raw token, for example `bg-accent` → `--color-accent` → `--accent`.
  - Bracketed `text-[var(--x)]`, `bg-[var(--x)]` and `border-[var(--x)]` map to `--x`.
  - `white` maps to `#ffffff`, and `black` to `#000000`.
- **Excluded as non-colour:** size and layout utilities (`text-sm`, `text-base`, `text-xs`, `text-left`, `border`, `border-2` and so on), recognised by a closed list of size and alignment suffixes.
- **Ignored, with the reason written in a test comment:**
  - `ring-*` and `ring-offset-*`: the focus ring is checked as a non-text pair by HC-UITK-001.
  - Every `focus-visible:` class: focus only adds the ring and a border colour, and the text and fill are unchanged.
  - Every `disabled:` class: WCAG 1.4.3 exempts inactive controls, and axe skips them.
  - `active:` (scale only) and `shadow-*`.
- **Fails closed:** any other colour-looking class (`bg-…`, `text-…` or `border-…` with an unknown name, a hex such as `[#…]`, an opacity suffix such as `/80`, or `dark:`) **throws** "unmapped colour class <cls>". A missing rest foreground or rest background also throws, so a variant that loses its fill cannot pass by having nothing to compare.
- **Pairs:**
  - rest text on rest bg;
  - `hover:` text (or rest text) on `hover:` bg (or rest bg);
  - `placeholder:` text on rest bg;
  - rest border on rest bg, 3:1 (WCAG 1.4.11).

Text pairs need ≥ 4.5 in both themes.

- **HC-DPC-001** (vitest, `ui-tokens.test.ts`), `primary Button text reaches 4.5:1 on its fill, light and dark, at rest and on hover`. Input: `buttonVariants({ variant: 'primary' })`. The test also asserts that `buttonVariants({})` (the default) equals `buttonVariants({ variant: 'primary' })`. RED on main: dark 2.02 at rest and 1.77 on hover.
- **HC-DPC-002** (vitest, `ui-tokens.test.ts`; the file is `.ts`, so it renders with `render(createElement(Input, { label: 'x' }))` from `react` and `@testing-library/react`, with vitest's `jsdom` environment from `vitest.config.ts:17`), `Input value and placeholder reach 4.5:1 on the field, and its border 3:1, light and dark`. Input: the rendered `<input>`'s `className`. Pairs: `text-ink` and `placeholder:text-ink-tertiary` on the field bg, and `border-[var(--line-strong)]` on the field bg. The `error` branch adds `border-status-critical` and must also map. RED on main: dark 1.18 (value) and 2.67 (placeholder).
- **HC-DPC-003** (Playwright, `e2e/ui-dark-primitives.spec.ts`), `the unlock form's Input and default Button pass axe and computed contrast in dark`.
  - Setup: `installMockApi(page)` and `page.goto('/setup')`. `/profiles` returns fixtures, so the unlock form renders, as HC-UIG-005 relies on (`e2e/ui-gates.spec.ts:259-261`).
  - Targets: `page.getByLabel('Unlock password')`, filled with `x`, and `page.getByRole('button', { name: 'Unlock', exact: true })` (`ProfileSetup.tsx:355-375`). `exact` keeps the role query from also matching any other button whose name contains "Unlock".
  - Settle: after each `setTheme(page, theme)`, wait until no animation or CSS transition is running, with `page.waitForFunction(() => document.getAnimations().length === 0)` and then one `requestAnimationFrame`. Only after that does it read `getComputedStyle` or run axe. Button transitions `background-color` and `color` over `--dur-hover` (150 ms, `Button.tsx:16`), and Input uses `transition-colors duration-200` (`Input.tsx:38`). Without the wait, a read taken mid-transition could see a blend of the light and dark colours and pass on main.
  - Checks, in dark:
    - (a) axe with `WCAG_TAGS`, `.include()` on the two targets, has 0 serious or critical violations.
    - (b) In the page, the WCAG ratio of `getComputedStyle(el).color` to `backgroundColor` is ≥ 4.5 for each target. This catches the case where axe reports `incomplete` instead of a violation.
  - Then light: the settle wait again, then (a) and (b) in light.
  - RED on main in dark; light passes. If the unlock form does not render under the mock, stop and ask for an `L0 ruling:`. Do not switch routes silently.

**Acceptance (outputs pasted):**
1. HC-DPC-001, 002 and 003 RED on the base, then GREEN. Paste the measured ratios from both runs.
2. `npx vitest run src/__tests__/ui-tokens.test.ts src/__tests__/ui-controls.test.tsx` green. HC-UITK-001 … 003 and HC-UIPC-* are unchanged and pass.
3. **Every route's G1 dark still passes.** On a quiet box (lock, `hold_slots.sh`, `uptime` and the quiet-box `pgrep` and `ss` checks (RUNBOOK §10.1) pasted first), run `npx playwright test e2e/ui-dark-primitives.spec.ts e2e/ui-shell.spec.ts e2e/ui-provenance.spec.ts e2e/ui-tokens.spec.ts e2e/accessibility.spec.ts e2e/tailwind4-styles.spec.ts e2e/ui-gates.spec.ts` and paste the summary. It must be all green: the shell's dark G1 on every route, provenance Gate G1 light and dark on `/interpret`, `/inbox` and `/verify`, the light G1 routes, and TW4's computed-style asserts with unchanged values.
4. ui-provenance's record-only page-wide dark G1 annotations (`G1 <path> dark …`) for the base and for the head, pasted. The head adds no line, and no remaining `color-contrast` line names a primary `<button>` or an `<input>` rendered by `ui/Input`.
5. Full `npx vitest run` green on CI, and the CI E2E job green with none of the above listed as `flaky`. `npx tsc --noEmit` and `npm run lint` clean.
6. `git diff --stat` touches only the four files listed above.

**Depends on:** none. **Never beside:** an open PR that edits `fe/components/ui/Button.tsx`, `fe/components/ui/Input.tsx`, `fe/styles/globals.css` or `fe/__tests__/ui-tokens.test.ts`. On 2026-10-28 the planner checked #393 and #397–#403 with `gh pr diff N --name-only`, and none of them touches these files. The Playwright acceptance follows the quiet-box rule above, so it never runs beside another Playwright run. **Unblocks:** every page row that renders a primary Button or an Input. Each now lists this row in `depends_on`:
- UI-PG-CARE (#400) and UI-PG-MEDS (#398), which rebase onto its merge and re-run their dark G1.
- UI-PG-EXPORT (`ExportPage.tsx:267`), which was `ready` and is now blocked on this row.
- UI-PG-RESULTS (`TrendsDashboard.tsx:611`, `LabInterpreter.tsx:176`), UI-PG-DOCUMENTS (`DocumentInbox.tsx:172`), UI-PG-REVIEW (`VerificationWorkbench.tsx:419`), UI-PG-ASK (`ExplainAssistant.tsx:743`), UI-PG-RECORDS (`SearchPage.tsx:110` Input and `:117` Button, `PinboardsPage.tsx:100`), UI-PG-SETTINGS (`SettingsPage.tsx:916`, `MemoryManager.tsx:119`) and UI-PG-AUTH (`ProfileSetup.tsx:355` Input and `:368` Button).

Lines are the first primary Button or Input on `434179a9`. **Gate:** none. **Ask-first files:** none. **Est:** 1.5 h. **Runtime:** claude (Playwright). **MVP:** P1, because it blocks the acceptance of every page row, P1 page rows included.

---

## TOAST-SHELL — the shared Toaster centres itself with a transform (fails G5) and sits over the phone tab bar and Safety Rail

**Planned:** 2026-10-29 by the Opus planner on `origin/main` @ `41fa3824` (after #405). Revised the same day after the #409 Opus review (REVISE) and the L0 calls recorded below. Queue: ["Planned 2026-10-29, toast"](2026-10-15-build-program/queue.md#planned-2026-10-29-toast).

**Name.** The brief and the PR title call the row TOAST-G5. It was planned as **TOAST-SHELL** because it absorbs bullet TOAST-PHONE-CHROME. Both fixes are rules on the same element (`ol[data-sonner-toaster]`) in the same block of `globals.css`. TOAST-G5 is not a separate row and no other row uses either name.

**Sources.**
- **UI-PG-CARE (#400) stop, 2026-10-29.** #400's head is `0f8f2271`. CI run 40834430710 (E2E Smoke Tests) ran "Gate G5 /care-tasks: no element has a transform 50 ms after the Done click under reduced motion" (`e2e/ui-care.spec.ts:297`). It failed on all three attempts with one offender, `ol transform=matrix(1, 0, 0, 1, -178, 0)`. The L1 stop names `components/ui/toast.tsx` and says the fix needs an edit to `ui/*` or `globals.css`, which the row's brief forbids.
- **Bullet TOAST-PHONE-CHROME** (#370 final review, inferred, not measured): on phones a toast likely covers the tab bar and part of the Safety Rail.

**Diagnosis (code reading on `41fa3824`; sonner 2.0.8 `dist/styles.css`, which sonner injects at runtime).**
- **The offender is sonner's toaster list.** It is not a toast, and it is not `CareTasksPage.tsx`.
  - sonner's rule `[data-sonner-toaster][data-x-position='center'] { left: 50%; transform: translateX(-50%); }` (`styles.css:68-71`) centres the list. `-178` px is half of its `--width` (`TOAST_WIDTH = 356`, `index.mjs:472`).
  - Our `AppToaster` is `position="bottom-center"` (`fe/components/ui/toast.tsx:61`).
  - Under `(max-width: 600px)` sonner already sets `transform: none` on the list (`styles.css:460-464`). So only viewports wider than 600 px fail.
- **A single toast passes.**
  - sonner's `@media (prefers-reduced-motion)` rule (`styles.css:708-714`) removes the toasts' transitions.
  - A mounted front toast sits at `translateY(0)`, which is the identity.
  - The list's own `transition: transform 400ms ease` is outside that rule. It never runs, because the list's transform never changes.
- **Why other rows did not fail.**
  - sonner renders the `ol` only while a toast is showing (`index.mjs:1150-1153`: `if (!filteredToasts.length) return null`). G5 can see it only when the gate's interaction itself raises a toast.
  - No route's G5 interaction on `origin/main` raises one. UI-SHELL's G5 (`e2e/ui-shell.spec.ts:1041-1046`) is a nav click. ui-provenance's G5 (`e2e/ui-provenance.spec.ts:590-602`) opens a citation popover.
  - UI-PG-MEDS (#398) calls `notify()` from BadgeToast. Its G5 interactions only open and close the dose dialog, which raises no toast.
  - UI-PG-CARE is the first row whose G5 interaction (Done) shows a toast.
  - The cause is position, not the 50 ms timing. The transform is static and lasts for the toast's whole life.
- **Is G5 meant to include toasts? Yes, from the plan text.**
  - Frontend-revamp plan §6, G5: "with `reducedMotion: 'reduce'`, no element has a non-identity computed transform 50 ms after each interaction" (`2026-10-23-frontend-revamp-plan.md:340`). The helper scans `body *` (`e2e/support/gates.ts:211-228`).
  - Nothing in §6 limits G5 to the route container or to T0 content. G10 is the check scoped to `[data-t0]` nodes and the route container.
  - M11 (`:177`) says the reduced-motion toast is "sonner reduced (opacity)", so it is meant to carry no transform.
  - So the plan text gives no ground for excluding the toaster region from G5, and this row fixes the toast.
  - The provenance spec scopes its G5 to its own nodes. That was an L0 ruling for the Radix popper (bullet GATES-POPPER-TRANSFORM), not plan text, and it is not extended here.
- **A stacked or dismissed toast also fails (predicted).**
  - With a second toast, the back toast becomes `[data-expanded=false][data-front=false]`. sonner gives it `--y: translateY(…) scale(…)`.
  - A dismissed toast becomes `[data-removed=true]`. It keeps a `translateY` until it unmounts about 200 ms later.
  - sonner's reduced-motion rule removes transitions only, so both transforms are present 50 ms after the interaction.
  - HC-TOAST-003 is therefore predicted **RED on the base** for (a) and (b), and rule 3 is the expected outcome. Task 1 still measures it, and the rule is added only on that measurement.
- **Phone chrome (TOAST-PHONE-CHROME).** This is inferred from the classes; Task 1 measures it.
  - sonner places the list at `bottom: var(--mobile-offset-bottom)` (16 px) up to 600 px, and at `var(--offset-bottom)` (24 px) above that. `--z-toast` is 40 (`globals.css:179`).
  - Below `lg` (1024 px), the tab bar is `fixed bottom-0 z-40` (`MobileTabBar.tsx:20`). The Safety Rail is fixed just above it at `z-30` (`SafetyRail.tsx:19`).
  - From `lg` up, the rail is `sticky bottom-0` (`:20`), so the 24 px offset also overlaps the rail on desktop.
  - `AppLayout.tsx:29-53` already measures that chrome into `--shell-bottom-h`: the tab bar plus the rail below `lg`, the rail alone at `lg`.

**Fix: one CSS block in `globals.css`, outside any layer.**
- The block sits next to the reduced-motion block, outside any `@layer`.
- sonner appends its `<style>` to the end of `<head>` at runtime, after the built `globals.css`. A rule of equal specificity would therefore lose.
- Each selector is prefixed with `:root`, which gives (0,3,0) against sonner's (0,2,0), whatever order the stylesheets load in.

1. **Centring without a transform.** Above sonner's phone breakpoint, inside `@media not all and (max-width: 600px)` (the exact complement of sonner's query):
   `:root [data-sonner-toaster][data-x-position='center'] { left: 0; right: 0; margin-inline: auto; transform: none; }`
   The list keeps `position: fixed` and `width: var(--width)`, so the auto margins centre it. **For rule 1 only, the layout is unchanged** and only the mechanism differs.
2. **Bottom offset above the shell chrome.**
   - Base rule, no media query: `:root [data-sonner-toaster][data-y-position='bottom'] { bottom: calc(var(--shell-bottom-h, 0px) + var(--offset-bottom)); }`.
   - Then, **after it in source order**, `@media (max-width: 600px) { :root [data-sonner-toaster][data-y-position='bottom'] { bottom: calc(var(--shell-bottom-h, 0px) + var(--mobile-offset-bottom)); } }`. Both rules have the same specificity, so the later mobile rule wins on phones. The other way round, the base rule would override the mobile one.
   - sonner's `offset` and `mobileOffset` props keep working, because the rule adds the shell height to them instead of replacing them. `toast.tsx` is not edited.
   - **Rule 2 does change the layout.** It lifts the toast by the shell chrome at every width. That is the tab bar plus the rail below `lg` (about 57 + 43 px on phones), and the rail height on desktop (`lg:sticky`, about 41 px). On desktop the toast now sits above the rail's "Educational only, not medical advice. Your records stay on this device." line instead of over it.
3. **Reduced-motion stack rule (expected, gated on Task 1).** Add it only if Task 1 measures an offender in HC-TOAST-003 (a) or (b), as predicted. Inside `@media (prefers-reduced-motion: reduce)`:
   `:root [data-sonner-toast][data-expanded='false'][data-front='false'], :root [data-sonner-toast][data-removed='true'] { transform: none; }`
   - A collapsed back toast then sits in the front toast's box: sonner gives it `bottom: 0`, the same width and `height: var(--front-toast-height)`, with a lower `z-index`. The opaque front toast (`--normal-bg: var(--surface-1)`) covers it.
   - A removed toast already has opacity 0.
   - **Still toasts.** A non-still back toast's content is already opacity 0 (sonner's `[data-front=false][data-styled=true]>*`). A **still** back toast keeps its text at opacity 1 (`STILL_CONTENT = 'opacity-100! transition-none!'`, `toast.tsx:21-24`), so its text is hidden only because the front toast covers it.
   - HC-TOAST-003 (c) checks that nothing of a still back toast shows. If (c) fails because the text is taller than the front toast's box, stop and go to L0. Do not add `visibility` or `opacity` rules to still toasts. They are T0 nodes and fall under M0.
   - Under reduced motion, the only visible loss is the peeking edge of the collapsed stack, which M11 permits ("opacity").

**Known limits (recorded, not fixed).** In each case a G5 interaction that hits the limit stops and goes to L0.
- **Expanded stack.** When the pointer or focus is over the toaster with two or more toasts, sonner sets `[data-expanded=true]` and spreads the toasts with `translateY` offsets. Without the offsets they would overlap, so rule 3 does not touch them.
- **Swipe.** While a toast is being swiped, `[data-sonner-toast][data-swiping=true]` sets `transform: var(--y) translateY(var(--swipe-amount-y)) translateX(var(--swipe-amount-x))` with `transition: none` (sonner `styles.css`). The transform follows the user's pointer, so it is direct manipulation and not an animation, and it is left alone.

**Rejected.**
- **A `still` toast variant.** The offender is the list, not the toast, so a per-toast prop cannot remove it.
- **Inline `style` on `<Toaster>`.** It cannot be scoped to a media query, so `left: 0; right: 0` would override sonner's phone offsets.
- **The CSS `translate` property in place of `transform`.** G5 reads `transform`, so this would hide the same offset from the gate. That is a gate dodge.
- **`position="bottom-right"`.** A placement change that nobody asked for.
- **Scoping G5 to exclude the toaster.** The §6 text does not support it (see above). No `gates.ts` change of any kind.

**Files (narrowest set).**
- `fe/styles/globals.css`: the one unlayered block above. It holds rules 1 and 2, and rule 3 if Task 1 measures as predicted, with a comment citing G5, M11 and TOAST-PHONE-CHROME. Nothing else in the file changes.
- `e2e/ui-toast.spec.ts` (new): HC-TOAST-001 … 004. It is a new file, so the row shares no spec with `ui-shell.spec.ts`. UI-PG-MEDS (#398), UI-PALETTE, UI-PG-EXPORT and POPOVER-OPEN-COST also edit that spec.

Not edited: `fe/components/ui/toast.tsx`, `AppLayout.tsx`, `e2e/support/gates.ts`, `e2e/ui-shell.spec.ts`, `fe/__tests__/ui-feedback.test.tsx`.

**Toast triggers (L0 call on the #409 review: no skip on preview).**
- **Dev server** (`HC_E2E_BASE_URL` unset, which is what CI runs, `playwright.config.ts:31`):
  - The real toast. Load `/inbox` with `installMockApi` and wait for the Safety Rail. Then, in `page.evaluate`, import `/src/components/ui/toast.tsx` and call `notify()`, as HC-UISH-007 does (`e2e/ui-shell.spec.ts:792-795`).
  - Dismiss with only what `toast.tsx` exports: `notify`, `AppToaster` and `OVERLAY_OPEN_EVENT`. Either dispatch `document.dispatchEvent(new Event(OVERLAY_OPEN_EVENT))`, or call `notify({ message, action: { label: 'Close', onClick: () => {} } })` and fire that action with `element.click()` inside `page.evaluate`. Never use a Playwright pointer click on the toaster: the pointer would expand the stack.
  - The spec **never imports `sonner`** in `page.evaluate`. A second copy of sonner's store would not be the one the app's Toaster renders.
- **`vite preview`** (`HC_E2E_BASE_URL` set). The `/src/...` path does not exist there, and the Source Trace verify toast cannot be reached on main (bullet SOURCE-TRACE-UNWIRED, #407). So the spec uses a **fixture check**:
  - Open the same authenticated route (`/inbox` under `installMockApi`). `AppLayout` mounts `AppToaster` there, so sonner's runtime `<style>` is in `<head>`. Assert that it is: a `<style>` containing `[data-sonner-toaster]`.
  - Inject `<ol data-sonner-toaster data-x-position="center" data-y-position="bottom" style="--width: 356px; --gap: 14px; --front-toast-height: 56px; --offset-bottom: 24px; --mobile-offset-bottom: 16px; --mobile-offset-left: 16px; --mobile-offset-right: 16px">` into `<body>`.
  - For HC-TOAST-003 it holds `li[data-sonner-toast]` children that copy sonner's runtime attributes and variables (`index.mjs:715-737`; `GAP = 14`, `:474`):
    - attributes: `data-y-position="bottom"`, `data-x-position="center"`, `data-mounted="true"`, `data-styled="true"`, `data-front`, `data-expanded="false"`, `data-removed`, `data-swiping="false"`, `data-swipe-out="false"`;
    - inline style: `--index: 1; --toasts-before: 1; --z-index: 1; --offset: 0px; --initial-height: 56px`.
  - **Why the copy matters (#409 round 2, recurring-failures #1).** A bare `li` has no `--gap` or `--toasts-before`, so sonner's `--y` is invalid at computed-value time and the transform falls back to `none` on main. The fixture could not go RED.
  - Read computed styles through the real cascade: sonner's stylesheet plus the built `globals.css`.
  - Each test below states what its fixture asserts. The fixture is used only when `HC_E2E_BASE_URL` is set. Dev runs keep the real `notify()` trigger.

**RED tests (HC-TOAST-001 … 004; `HC-TOAST` is unused on `origin/main`).** Transforms are read 50 ms after the trigger with reduced motion emulated, as G5 does. Centring uses `document.documentElement.clientWidth`, which excludes a scrollbar, unlike `innerWidth`.
- **HC-TOAST-001 (RED).** Two separate cases, each the **only** toast on the page: (i) one plain `notify()` toast, (ii) one `notify({ still: true })` toast. Each runs at 1280×800 and 1440×900.
  - Dev: `reducedMotionSnapshot(page, trigger)` page-wide returns `[]`. The list is centred: `|ol.left + ol.width / 2 - documentElement.clientWidth / 2| <= 1`. The centring check stops a fix that drops the transform and leaves the list off-centre.
  - Preview fixture: the injected `ol` has computed `transform: none` and passes the same centring check.
  - RED on base: `ol transform=matrix(1, 0, 0, 1, -178, 0)`.
  - If the base shows a page-wide offender outside `[data-sonner-toaster]` on `/inbox`, stop and report it. Do not switch routes silently.
- **HC-TOAST-002 (RED).** Viewports 390×844, 820×1180 and 1440×900.
  - Dev: one settled toast. The rect of each `[data-sonner-toast]` does not intersect the rect of `nav[aria-label="Tab bar"]` (where visible) or of `[data-safety-rail]`, and lies inside `[0, documentElement.clientWidth]` horizontally.
  - Preview fixture: the injected `ol` has computed `bottom` equal to `--shell-bottom-h` (read from `documentElement`) plus 16 px at 390, or plus 24 px at 820 and 1440, within ±0.5 px.
  - RED on base at 390 and 820 is expected: the 16 or 24 px offset sits inside the tab bar's 57 px. The 1440 base result is measured in Task 1 and pasted. It is expected RED as well, because the toast sits over the sticky rail.
- **HC-TOAST-003 (predicted RED for (a) and (b)).** At 1280×800 under reduced motion.
  - (a) A second toast while a first is showing: every element in the `[data-sonner-toaster]` subtree has the identity transform 50 ms later.
  - (b) Dismiss the front toast so that the pointer never enters the toaster: `document.dispatchEvent(new Event(OVERLAY_OPEN_EVENT))`, or the action button's `element.click()` inside `page.evaluate`. Never use a Playwright pointer click, because a real pointer over the toaster sets `data-expanded=true`, which is the expanded-stack stop point. Then the same check, 50 ms later.
  - (c) A **still** toast followed by a plain toast, so the still one is the back toast. Nothing of the still back toast shows. `document.elementFromPoint` at the centre and the four inset corners (2 px in) of its `[data-t0]` text rect returns a node inside the front toast, and that text rect lies inside the front toast's rect.
  - Preview fixture, with the attributes and variables above:
    - (a) a back toast, `data-front="false" data-removed="false"`;
    - (b) a removed back toast, `data-front="false" data-removed="true"`;
    - (b′) a removed front toast, `data-front="true" data-removed="true"`.
    - Each must compute `transform: none` on the head.
    - On main the expected values are a `translateY(-14px)` plus `scale` matrix for (a) and a `translateY` matrix for (b) and (b′). The fixture's base run must show them.
    - (c) needs real stacking, so on preview it becomes the fixture assertion that the back `li` (a) computes `transform: none` and `bottom: 0px`.
  - If Task 1 shows (a) and (b) green on the base, contrary to the prediction, the test stays as a guard, rule 3 is not added, and the PR says so.
- **HC-TOAST-004 (both sides of the breakpoint).** Dev uses a real toast; preview uses the fixture.
  - At 390×844 and at **600**×800, sonner's own phone layout is unchanged: the list computes `transform: none`, `left: 16px` and `right: 16px`. This is a guard, green on the base.
  - At **601**×800, rule 1 applies: `transform: none` and centred (the HC-TOAST-001 check). This is RED on the base, where the list computes `translateX(-50%)`.
  - Together these pin both sides of `not all and (max-width: 600px)`.

**Tasks.**
- **Task 1, measure.** Run in a scratch worktree on a quiet box.
  - On the base, run HC-TOAST-001 … 004 on dev and preview, and paste every offender, rect and computed value at each viewport.
  - Run #400's `e2e/ui-care.spec.ts` G5 test, from head `0f8f2271`, against a scratch merge of this row's head, to confirm the `ol` offender goes away. This is record only: #400's files stay #400's.
- **Task 2, fix.** Add rules 1 and 2, and rule 3 per Task 1. Re-run.

**Acceptance (outputs pasted).**
1. **The new tests.** Offender lists, rects and computed values are pasted for both runs, on dev and preview.
   - HC-TOAST-001 and 002 go from RED on the base to GREEN on the head.
   - HC-TOAST-003 is RED → GREEN, as predicted, or a guard that is green on both, as Task 1 decided.
   - **The preview fixture of HC-TOAST-003 must be shown RED on `origin/main`**, with each fixture `li`'s computed transform pasted. If it cannot be shown RED, the preview case is labelled a guard in the spec and the PR, and the dev case carries the RED.
   - HC-TOAST-004 at 601 px goes RED → GREEN. At 390 and 600 px it is green on both.
2. **The quiet-box rule for every Playwright run**, as in the rules at the top of this file. L0 holds `/tmp/claude-1000/quiet-box.lock`. Each Playwright command runs under `/tmp/claude-1000/hold_slots.sh`. Paste `uptime` (1-minute load below 1.5) and the quiet-box `pgrep` and `ss` checks (RUNBOOK §10.1; empty) first. Never run beside pytest, vitest, another Playwright run or a model-host row.
3. **Baseline, then delta.**
   - On the dev server, `npx playwright test e2e/ui-toast.spec.ts e2e/ui-shell.spec.ts e2e/ui-provenance.spec.ts e2e/ui-gates.spec.ts e2e/tailwind4-styles.spec.ts` is all green on the head. That covers every existing G5, HC-UISH-005 (rail opaque and hit-testable), HC-UISH-007 (no toast over the More sheet) and HC-UIFB-006's Playwright half.
   - On `vite preview` (`HC_E2E_BASE_URL`), **first run the same specs (minus the new one) on `origin/main` as a baseline**. Record each pre-existing failure and skip by name. Known ones: HC-UISH-007 imports the dev-only `/src/components/ui/toast.tsx` and so fails on preview on main (#398 adds a preview guard to it, which is not on main yet). HC-UIFB-006 is skipped on preview (`e2e/ui-shell.spec.ts:912-915`).
   - Then run them on the head. The row is judged on the **delta**: no new failure or skip, and ui-toast green. Paste both summaries.
4. **Vitest.** `npx vitest run src/__tests__/ui-feedback.test.tsx src/__tests__/ui-shell.test.tsx` is green, with HC-UIFB-001 … 006 unchanged. Then run the full `npx vitest run` and report the count and delta.
5. **CI.** CI E2E is green with **none** of the above in the `flaky` list. CI's `retries: 2` hides a retried failure.
6. **#400 after this merges.** UI-PG-CARE (#400) rebases and its Gate G5 on `/care-tasks` passes on dev, preview and CI. That is #400's own acceptance, listed here as the reason this row exists. G5 is then green on every route whose gate interaction shows a toast, because the list rules apply on every route: `AppLayout.tsx:104` mounts the only `AppToaster`.
7. **Build and diff.** `npx tsc --noEmit`, `npm run build` and `npm run lint` are clean. `git diff --stat` touches only `fe/styles/globals.css` and `e2e/ui-toast.spec.ts`.

**Stop and go to L0** if any of these happens:
- the base shows a G5 offender outside the toaster on the test route;
- the preview fixture cannot find sonner's stylesheet on the route;
- HC-TOAST-003 (c) shows a still back toast;
- a G5 interaction hits the expanded-stack or swipe limit;
- a fix would need `toast.tsx`, `gates.ts` or a bound change.

**Order, depends on, never beside.**
- **Depends on:** none. UI-PRIM-FEEDBACK (#364) and UI-SHELL (#370) are merged.
- **Never beside** an open PR that edits `fe/styles/globals.css`, `fe/components/ui/toast.tsx` or `e2e/ui-toast.spec.ts`. On 2026-10-29 the planner checked every open PR with `gh pr diff N --name-only`:
  - #393 and #399 hold no files.
  - #398 edits `e2e/ui-shell.spec.ts` and medication files, but none of these three.
  - #400 edits `CareTasksPage.tsx`, `ui-care.test.tsx` and `ui-care.spec.ts`.
  - #401 holds no files.
  - #407 is docs only.
- **Order with POPOVER-OPEN-COST** (L0 call on the #409 review). When #393 resumes, it adds a top-level `@property --removed-body-scroll-bar-size` rule to `globals.css` (planned in #407). **TOAST-SHELL builds first**, because it unblocks UI-PG-CARE. POPOVER-OPEN-COST rebases after it. The hunks do not overlap: the `@property` rule sits at top level, and this block sits next to the reduced-motion block.
- **Docs order:** #407 merges before this plan (#409). This branch then merges `origin/main` and resolves `queue.md`.
- The Playwright runs follow the quiet-box rule.
- **Unblocks:** UI-PG-CARE (`depends_on += TOAST-SHELL`). UI-PG-MEDS is not blocked: its G5 interactions raise no toast.

**Gate, owner, model, sizing.**
- **Gate:** none. **Ask-first files:** none. **Owner gate:** none. No new token or colour, and the toast stays bottom-centre. Rule 2's lift above the rail follows TOAST-PHONE-CHROME's candidate fix.
- **Implementer:** Sonnet 5.5. Haiku 5.5 at effort `medium` runs the test scripts only and never edits. Opus reviews. This follows owner-decisions row MODEL-ROUTING-SONNET (2026-10-29, PR #408), which supersedes MODEL-ROUTING-HAIKU. #408 merged as `f85adcb3`, so the routing is settled.
- **Est:** 2.5 h. **Runtime:** claude (Playwright, quiet box).
- **MVP:** P1. The row blocks UI-PG-CARE's acceptance, and on phones a toast covers the Safety Rail's "Educational only, not medical advice" line, which is on the demo path.
