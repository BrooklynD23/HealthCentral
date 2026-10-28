# Follow-ups 2026-10-28 — plans for VITEST-TZ-PIN, G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE and AUDIT-GUARD-ATTR-DYNAMIC

**Last Updated:** 2026-10-28 (#392 review round 2 on `b1ee5794` (#370 merged): UIG006-PASS3-FLAKE ready, pass-3 re-cited; the VITEST-TZ-PIN sweep runs on a native Linux clone or a CI matrix; HC-UIG-009 reads `__seq` at trigger and after; fail-fixture (m) under decision (a); the Node fetch promise is awaited); 2026-10-28 (#392 Opus review round 1, REVISE: VITEST-TZ-PIN zone sweep before the pin, `VITEST_TZ` override, `/mnt` run required; UIG006 mutant m4, a Node-side fetch, decision (a) to L0; quiet-box lock and `hold_slots.sh` on both Playwright rows; scratch worktree (recurring-failures #13); failure-rate rule; HC-UIPV-007 method; HC-UIPV-006 A/B facts; property-skip rule and HC-AUD-ORD-033 mixed case); 2026-10-28 (Opus planner on `9d0dc2a`: four follow-up bullets planned as rows; GATES-PASS3-ELAPSED folded into UIG006-PASS3-FLAKE; HC-UIPV-006 noted as pending L0 evidence, no row)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). No row below needs an owner gate; each names the point where it stops and goes to L0 instead.
**Base measured:** `origin/main` @ `9d0dc2a` (2026-10-28, after #391), refreshed for the e2e and frontend rows on `b1ee5794` (#370, UI-SHELL, merged): of the files cited here #370 changed only `e2e/ui-gates.spec.ts` (re-cited below) and two grid tokens in `VerificationWorkbench.tsx` (`:731-736` unchanged). Every `file:line` below was re-read by the planner on those commits. Product code was read only.
**Refresh Trigger:** a merge of STILLNESS-NAV-LATE, B-3 (#264) or RSI1-DONATE PR-2 (#239); a second HC-UIPV-006 failure; any edit before these rows are built to `src/frontend/vitest.config.ts`, `src/frontend/e2e/ui-provenance.spec.ts`, `src/frontend/e2e/ui-gates.spec.ts`, `src/frontend/e2e/support/gates.ts`, `src/frontend/src/components/PageImageOverlay.tsx`, `src/backend/tests/support/callgraph.py` or `src/backend/tests/test_audit_order_guard.py`.

Queue rows: [queue.md, "Planned 2026-10-28, follow-ups"](2026-10-15-build-program/queue.md#planned-2026-10-28-follow-ups). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`, `e2e/` = `src/frontend/e2e/`.

**Rules that hold for every row here.**
- Two rows (G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE) fix test-harness races. The fix makes the test wait for the right condition. No row relaxes a bound, adds a retry, or marks a test flaky, fixme, skip or fail. No row changes a constant in `e2e/support/gates.ts`.
- **CI's `retries: 2` hides a failure.** A retried pass is listed as `flaky` and the job still exits 0. So "CI E2E green" here also means the job log summary lists none of the row's tests as flaky.
- **Quiet box for every Playwright measurement** (G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE), as STILLNESS-NAV-LATE does: L0 holds `/tmp/claude-1000/quiet-box.lock` for the run; each Playwright command runs under `/tmp/claude-1000/hold_slots.sh`; `uptime` (1-minute load below 1.5) and `pgrep -fa "playwright|vitest|pytest"` (empty) are pasted first. These rows run alone: never beside pytest, vitest, another Playwright run or a model-host row.
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
