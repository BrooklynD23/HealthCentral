# Follow-ups 2026-10-28 — plans for VITEST-TZ-PIN, G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE and AUDIT-GUARD-ATTR-DYNAMIC

**Last Updated:** 2026-10-28 (Opus planner on `9d0dc2a`: four follow-up bullets planned as rows; GATES-PASS3-ELAPSED folded into UIG006-PASS3-FLAKE; HC-UIPV-006 noted as pending L0 evidence, no row)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). No row below needs an owner gate; each names the point where it stops and goes to L0 instead.
**Base measured:** `origin/main` @ `9d0dc2a` (2026-10-28, after #391). Every `file:line` below was re-read by the planner on that commit. Product code was read only.
**Refresh Trigger:** a merge of UI-SHELL (#370), STILLNESS-NAV-LATE, B-3 (#264) or RSI1-DONATE PR-2 (#239); L0's HC-UIPV-006 A/B result; any edit before these rows are built to `src/frontend/vitest.config.ts`, `src/frontend/e2e/ui-provenance.spec.ts`, `src/frontend/e2e/ui-gates.spec.ts`, `src/frontend/e2e/support/gates.ts`, `src/frontend/src/components/PageImageOverlay.tsx`, `src/backend/tests/support/callgraph.py` or `src/backend/tests/test_audit_order_guard.py`.

Queue rows: [queue.md, "Planned 2026-10-28, follow-ups"](2026-10-15-build-program/queue.md#planned-2026-10-28-follow-ups). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`, `e2e/` = `src/frontend/e2e/`.

**Rules that hold for every row here.**
- Two rows (G1-VERIFY-TRACE-RACE, UIG006-PASS3-FLAKE) fix test-harness races. The fix makes the test wait for the right condition. No row relaxes a bound, adds a retry, or marks a test flaky, fixme, skip or fail. No row changes a constant in `e2e/support/gates.ts`.
- **CI's `retries: 2` hides a failure.** A retried pass is listed as `flaky` and the job still exits 0. So "CI E2E green" here also means the job log summary lists none of the row's tests as flaky.
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

So the describe's switch works on CI (Linux, `forks`) and on native Windows (`forks`), and silently does nothing on a WSL `/mnt` checkout (`threads`). There, line 202 sees the host offset (480 in Los Angeles), and the sanity check fails as it was written to.

**Pin, or fix the test? Pin.** The test checks product behaviour that depends on the time zone by design. `AchievementsWidget.tsx:54` shows `parseUtc(badge.earned_at).toLocaleDateString(...)`: it reads a naive `earned_at` as UTC and shows the patient's local date. To tell "read as UTC" from "read as local", the test needs a zone that is not UTC. It already says which one (America/New_York) and checks that it got it (line 202). Nothing in the product should be zone-independent here, so a pin hides no product bug. What is broken is how the test sets the zone, and the smallest correct fix is to set it where every pool inherits it: in the config, on the main process, before the pool starts.

**What the pin changes elsewhere.** Today CI runs every vitest file in the runner's zone (UTC on GitHub's Linux runners). After the pin, all 62 files under `fe/__tests__/` run in America/New_York everywhere. A test that passes only in UTC would then fail. That would be a real zone dependence, which the pin exposes rather than hides. The row stops and reports it to L0. It does not fix that test.

**Files:**
- `src/frontend/vitest.config.ts`: at module top, `process.env.TZ = 'America/New_York';` with a one-line comment: Node ignores a `TZ` write inside a worker thread, so the zone is set here, before the pool starts (VITEST-TZ-PIN). No other change.
- `fe/__tests__/vitest-tz-pin.test.ts` (new, HC-VTZ-001).
- `Gamification.test.tsx` is **not** edited. Its `beforeAll`/`afterAll` become a no-op, but they still record the zone the test needs, and UI-PG-MEDS and UI-PG-SETTINGS own that file.

**RED test.**
- **HC-VTZ-001** `the vitest process runs in the pinned zone`: `Intl.DateTimeFormat().resolvedOptions().timeZone` is `'America/New_York'`, and `new Date('2026-03-05T12:00:00Z').getTimezoneOffset()` is 300. RED on main in both pools: CI (UTC, `forks`) gives `UTC`/0, and the WSL checkout (Los Angeles, `threads`) gives `America/Los_Angeles`/480. Paste both RED outputs, or the CI one plus the local one.

**Acceptance (outputs pasted):**
1. HC-VTZ-001 RED then GREEN.
2. On the WSL `/mnt` checkout (`threads`), host zone America/Los_Angeles: `npx vitest run src/__tests__/Gamification.test.tsx src/__tests__/vitest-tz-pin.test.ts` passes 20 of 20 runs (a shell loop; paste the pass count). Before the pin it fails at `:202`.
3. Full `npx vitest run` passes on the WSL checkout with the host zone, again with `TZ=UTC` in the shell environment and again with `TZ=Asia/Kolkata` (the pin overrides all three), and on CI (`forks`, UTC host). Any other file that fails under the pin is a stop: report it to L0 with the failing assertion, and do not edit it.
4. `npx tsc --noEmit` clean.

**Depends on:** none. **Never beside:** another `src/frontend/vitest.config.ts` PR. It shares no file with UI-PG-MEDS or UI-PG-SETTINGS (both own `Gamification.test.tsx`). **Gate:** none. **Ask-first files:** none. **Est:** 0.5 h. **Runtime:** any. **MVP:** P2 (a local test ergonomics fix; no screen changes).

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
- Run `npx playwright test e2e/ui-provenance.spec.ts --project=chromium --workers=1 --retries=0 --repeat-each=60 -g "G1 /verify"`, once as is and once with CDP CPU throttling ×4 (`Emulation.setCPUThrottlingRate`) applied in the scratch copy. Paste the pass and fail counts and the recorded fields of every failing run. Check `uptime` and `pgrep -fa "playwright|vitest|pytest"` first; never beside another Playwright run or a model-host row.
- **Decision rule:**
  - (a) A failing run shows `src` equal to the pre-click value (or a `blob:` URL already revoked) when `interact` returned: the hypothesis holds; do Task 2.
  - (b) Failures show something else: stop, paste the fields, and ask for an `L0 ruling:`. Do not change the test by guess.
  - (c) 0 failures in 120 runs: do Task 2 anyway. HC-UIPV-007 is RED on its own, and the src check is the condition the test claims to wait for. The PR states that the CI failure was not reproduced.

**Task 2 (the fix; `e2e/ui-provenance.spec.ts` only).**
- `waitForSettled` resets its frame count at the start of each call: `__hcSettle` is cleared, or the state is keyed by selector and call. It then needs six fresh frames, as its docstring says. Every caller gets stricter, never looser.
- The `/verify` `interact` waits for the right image: before the click it reads the current `<img>`'s `src`. After the click it waits (`expect.poll` or `waitForFunction`) until `img[alt="Page 1 of document"]` has a `blob:` src **different from** the pre-click src, with `complete === true` and `naturalWidth > 0`. Then it calls `waitForSettled(page, PAGE_ONE_IMAGE)`, then `expect(PAGE_IMAGE_TRACE_MARK).toBeVisible()` as today.
- No other change. `assertOwnMatched` stays a one-shot count: turning it into a polling assertion would hide exactly this kind of race. `GATE_ROUTES[].own` and `ownBefore` stay as they are, and nothing in `e2e/support/gates.ts` changes. The G2, G3, G5 and G6 `/verify` tests use the same `interact` and get the same wait.

**RED test.**
- **HC-UIPV-007** `waitForSettled needs six fresh frames on every call` (in `ui-provenance.spec.ts`, using `page.setContent`): settle element A, replace it with element B at the same rect, then call `waitForSettled` on B and count `requestAnimationFrame` callbacks from the call to its return. It must be at least 6. RED on main: the call returns after about 1 frame. Paste the frame count before and after.

**Acceptance (outputs pasted):**
1. Task 1 counts and fields, and the decision taken (a, b or c).
2. HC-UIPV-007 RED then GREEN.
3. After Task 2, with the same commands and load as Task 1: `G1 /verify` passes 60 of 60 unthrottled and 60 of 60 at CPU ×4, `--retries=0`. Under (a), the Task 1 failure count is the RED for this.
4. The whole `e2e/ui-provenance.spec.ts` passes with `--retries=0` (HC-UIPV-001…007 and Gate G on all three routes). CI E2E green, and the job log summary lists no `ui-provenance.spec.ts` test as flaky.
5. `git diff --stat` touches `e2e/ui-provenance.spec.ts` only.

**Depends on:** none. **Never beside:** another `e2e/ui-provenance.spec.ts` PR, including any row L0 opens after its HC-UIPV-006 A/B (see the section note in the queue). Never beside another Playwright run on the box while Task 1 or the acceptance runs. **Gate:** none. **Ask-first files:** none (no product file changes). **Est:** 3 h. **Runtime:** claude. **MVP:** P2 (CI retries hide it; it blocks no demo path).

**Out of scope, for L0.** The one-frame stale render in `PageImageOverlay` (page 3's image under a "Page 1" label, with the new row's highlight) is a product glitch that Task 1 may confirm. If it does, the PR names it as a new follow-up bullet. A product fix would be a `key` on the overlay or resetting state during render, in the UI-PG-REVIEW area. This row does not fix it.

---

## UIG006-PASS3-FLAKE — reproduce the pass-3 miss, then make the fixture's fetch start when its scenario says

**Source:** bullet UIG006-PASS3-FLAKE (found 2026-10-28, #390 review): HC-UIG-006 pass 3 once reported `elapsedMs` 741 < 2000. **Folded in:** bullet GATES-PASS3-ELAPSED (found 2026-10-25, #374): the same test once reported `elapsedMs` 1657 < 2000, unexplained, "needs a reproduction before a row". This row is that reproduction first.

**What the test does.** Fixture pass-3 (`e2e/ui-gates.spec.ts:586-595`): `__start` runs `setTimeout(() => fetch('/gates/slow'), 50)`. The route answers after 1200 ms (`serveFixture`, `:46-62`). `runPassFixture` (`:612-628`) asserts `elapsedMs >= 2000`. In `stillnessProbe` (`e2e/support/gates.ts:815-879`) with `lazyRoute`, `trackRequests` starts before the trigger, and `lastEventAt` starts at tracker creation (`:786`). After the trigger, the probe waits until nothing is in flight and `NETWORK_IDLE_MS` (500) has passed since the last request event (`:830-839`). It then runs the 800 ms window. `elapsedMs` is wall time from just before the trigger to the end of the window (`:828`, `:843`).

**Two readings, and what each implies.**
- **1657 ms (GATES-PASS3-ELAPSED) fits the bullet's diagnosis.** The page's 50 ms timer fired late, more than about 450 ms after the tracker started, as it can under CPU contention. The quiet period then ended before the request event, and the window closed at roughly 850 + 800 ms, before the fetch's 1200 ms. On that run the probe behaved as written: it saw 500 ms of quiet after the trigger. The fixture's scenario ("a fetch that starts after the trigger returns", meaning a few ms after) did not happen.
- **741 ms cannot come from main's code.** The loop ends only when `Date.now() >= windowStart + 800`, and `windowStart >= triggeredWall`. Both readings use the same clock, so `elapsedMs = Date.now() - triggeredWall >= 800` on every path. A 741 reading must come from a different `gates.ts`. #390's review was mutation-testing that file ("an unmutated interaction path" in its PR body), so a mutant is the likely source, but that is not shown. Task 1 must not treat 741 as a reproduction target.

**Task 1 (measure; no committed change).** In a scratch copy of the spec and fixture:
- Record in-page `performance.now()` at `__start` and at the `fetch` call. On the Node side, record `Date.now()` at the trigger, at the `/gates/slow` `request` and `requestfinished` events, at the return of the idle wait, and `elapsedMs`. (The idle-wait time needs a scratch copy of `gates.ts` that logs it. Never commit that copy.)
- Run `npx playwright test e2e/ui-gates.spec.ts --project=chromium --retries=0 --repeat-each=40 -g "pass-3"`, once on a quiet box with `--workers=1`, and once under load: `--workers=4`, plus 4 busy-loop `node -e` processes started by the row and listed with `pgrep`. Paste counts and the fields of every failing run. Never run beside a model-host row, pytest or another row's Playwright run: the load is the row's own, and it is stopped and shown stopped afterwards.
- **Decision rule:**
  - (a) Every failing run has the in-page fetch call more than 400 ms after `__start` (timer starvation): do Task 2.
  - (b) A failing run has the fetch call on time but the Node `request` event more than 400 ms after it (event delivery lag), or any run gives `elapsedMs < 800`: stop and ask for an `L0 ruling:`. That would be a probe matter in `gates.ts` logic, and the probe's idle rule is the G10 gate's definition for real lazy routes.
  - (c) 0 failures in 80 runs: stop and report. No fix without a reproduction (the GATES-PASS3-ELAPSED rule).

**Task 2 (the fix; `e2e/ui-gates.spec.ts` only).**
- Pass-3's `__start` starts the fetch from a microtask it queues (`Promise.resolve().then(() => fetch('/gates/slow'))`) instead of a 50 ms timer. The fetch still begins after `__start` returns, as the fixture's title says. Its start no longer depends on a page timer firing on time under load.
- The fixture records `window.__fetchStartedAt` and `window.__startReturnedAt`. The test asserts `__fetchStartedAt >= __startReturnedAt`, so the scenario is checked on every run: "after the trigger returns" is asserted, not assumed. This is **HC-UIG-009**.
- `expect(report.elapsedMs).toBeGreaterThanOrEqual(2000)`, `slowFetchMs: 1200` and every constant in `gates.ts` stay as they are.
- **Mutation check (the fixture must still catch a broken probe).** With the new fixture, each of these three scratch mutants of `stillnessProbe` must make pass-3 fail; paste each failure: (m1) the lazy wait replaced by `page.waitForLoadState('networkidle')`; (m2) the `inFlight.size === 0` term removed; (m3) `windowStart` left at `triggeredWall` (the window not restarted after the idle wait). Mutants are never committed.

**RED tests.**
- The Task 1 failure count under load (decision (a)) is the RED for the fix. Rerun at the same load after Task 2: 0 failures in 40.
- **HC-UIG-009** `pass-3's fetch starts after the trigger returns`: RED first against a scratch fixture whose `__start` calls `fetch` synchronously (the assertion must be able to fail), then GREEN with the microtask fixture.

**Acceptance (outputs pasted):**
1. Task 1 counts, fields and decision.
2. After Task 2, pass-3 passes 40 of 40 at the Task 1 load and 40 of 40 quiet, `--retries=0`, with each run's `elapsedMs` logged and at least 2000.
3. HC-UIG-009 RED then GREEN. Mutants m1, m2 and m3 each fail pass-3.
4. The whole `e2e/ui-gates.spec.ts` passes (HC-UIG-001…009) with `--retries=0`. CI E2E green, and the job log summary lists no `ui-gates.spec.ts` test as flaky.
5. `git diff --stat` touches `e2e/ui-gates.spec.ts` only. `git diff origin/main -- e2e/support/gates.ts` is empty.

**Depends on:** UI-SHELL (#370), which edits `e2e/ui-gates.spec.ts` and is active again (resumed 2026-10-28). This row starts after #370 merges, or L0 rules otherwise. **Never beside:** another `e2e/ui-gates.spec.ts` or `e2e/support/gates.ts` PR (STILLNESS-NAV-LATE Task 2 if its ruling names either file), and never beside a model-host row or another Playwright run while Task 1 or the acceptance runs. **Gate:** none. **Ask-first files:** none. **Est:** 3 h. **Runtime:** claude. **MVP:** P1. A pass-3 miss is a stillness self-test listed as flaky, which fails STILLNESS-NAV-LATE's acceptance ("no stillness test listed as flaky").

---

## AUDIT-GUARD-ATTR-DYNAMIC — the audit-order guard flags a bound method passed as a value

**Source:** bullet AUDIT-GUARD-ATTR-DYNAMIC (found 2026-10-27, L0 ruling on #385, comment 6442124521). In `be/tests/support/callgraph.py`, `Graph.dynamic_sites` (`:99-133`) flags a def passed as an argument only when the argument is a bare name (`work`) or `self.<def>` / `cls.<def>` (`:116-132`). A bound attribute of any other object, such as `asyncio.to_thread(selector.detect_hardware_tier)` in `get_model_settings` (`be/api/model_settings.py:398`) and `list_tiers` (`:598`), is neither followed by `reachable` nor flagged. So the edge disappears silently from HC-AUD-ORD-030 (`be/tests/test_audit_order_guard.py:257-261`). That is why `list_tiers` went stale on #385 with no dynamic key reported.

**Measured by the planner** (scratch script `/tmp/claude-1000/agad/measure.py`, Python 3.12, on `9d0dc2a`; it subclasses nothing in the repo and edits no file):
- Today `_DYN` has 23 sites, all named (0 unlisted).
- Widening the argument rule to "any `<expr>.<attr>` whose `attr` names a def" adds **26** sites. 23 of them pass an attribute whose every same-named def is a `@property` (`settings.app_data_path` ×17, `self._settings.models_path` ×2, `item.key`/`data.key` ×3, `scheduler.last_pass_skipped_locked` ×1). Those are values, not callables.
- Excluding names whose every def is a property leaves **3** new sites:
  - `api/model_settings.py::get_model_settings::asyncio.to_thread(detect_hardware_tier)`
  - `api/model_settings.py::list_tiers::asyncio.to_thread(detect_hardware_tier)`
  - `modules/document_classifier.py::classify_document::max(get)` (`key=scores.get`, a dict method that shares a name with codebase defs)
- `ModelSelector.detect_hardware_tier` reaches 139 defs. The commits among them are `backup_scheduler.run_due_backups`, `NotificationScheduler._send_notification` and `PatternLearner.relearn_unmarked_windows`, the same three name collisions #385's PR body recorded ("Without those edges, 39 defs and no commit").

**Files:**
- `be/tests/support/callgraph.py` (`dynamic_sites` argument loop only): also take `ast.Attribute` arguments whose base is not `self`/`cls`, `ref = v.attr`, under the same conditions as today (`ref in self.by_name`, not a param or local, not the callee's own name). Skip a `ref` when **every** def of that name has a `property` or `cached_property` decorator (or a `.setter`/`.getter`). The key format stays `relpath::qualname::<unparse(func)>(<ref>)`. Update the comment at `:116-119` to match. No change to `reachable`, `commits`, or any other method.
- `be/tests/test_audit_order_guard.py`: three new `NAMED_DYNAMIC_EXCLUSIONS` keys (the three sites above), each with a **measured** reason in the style of the `_diagnostics_list_response` entries (`:162-174`). Before writing a reason, paste the site's reachable set and say which `.commit()` it reaches and through which name collision. `list_tiers` does **not** come back into `CLASSIFICATION`. The edge is now flagged, not followed, so `_COMMITTING` is unchanged. Plus the new break-it tests below.
- `docs/agentic/recurring-failures.md` (#9 audit paragraph, one sentence) only if the PR judges this an instance of #9, as AUDIT-GUARD-TEST did.

**RED tests** (in `be/tests/test_audit_order_guard.py`, using the `_overlay` synthetic tree like `:299-309`):
- **HC-AUD-ORD-032** `break_it_bound_method_passed_as_argument`: `modules/zz_helper.py` defines `class S: def work(self): ...`. The handler runs `s = S(); await asyncio.to_thread(s.work)`. Expect `dyn - set(NAMED_DYNAMIC_EXCLUSIONS) == {"api/zz.py::zz::asyncio.to_thread(work)"}`. RED on main (empty set).
- **HC-AUD-ORD-033** `property_value_passed_as_argument_is_not_dynamic`: a class with `@property def path(self)` and a handler calling `Path(cfg.path)`. Expect no new dynamic site. GREEN on main and GREEN after; it pins the property exclusion so a later widening cannot turn 23 values into noise.
- On the real tree, `test_hc_aud_ord_030_dynamic_calls_are_named` goes RED with the new rule (3 unlisted sites; paste them), then GREEN once the three keys are added.

**Stop rule.** If any newly flagged site reaches a `.commit()` on a profile-data path other than through a name collision, stop and tell L0. That would be an audit gap in a real route, not a classification task. The same applies if the property-free count differs from 3 on the branch's base.

**Acceptance (outputs pasted):**
1. HC-AUD-ORD-032 RED then GREEN; HC-AUD-ORD-033 GREEN; the real-tree RED list (3 sites) and then GREEN.
2. For each new key, the reachable-set output and the commit sites it names.
3. `scripts/pyslot.sh` run of `tests/test_audit_order_guard.py tests/test_audit_order.py tests/test_audit_phi_minimization.py`, all pass. Then the full backend suite through `pyslot.sh`, with no new failures against the baseline (5 environmental failures allowed only without the embedding bundle). Report the collected count and its delta (+2 expected; the PR does not edit the slot lines).
4. `cd src/backend && python -c "from main import app"`.
5. `git diff --stat` touches only the files listed above.

**Depends on:** none. **Never beside:** another `be/tests/test_audit_order_guard.py` or `be/tests/support/callgraph.py` PR. B-3 (#264) and RSI1-DONATE PR-2 (#239) also edit `test_audit_order_guard.py`, but both are parked drafts and hold no files (contracts §b rule 2), so they rebase onto this row. **Gate:** none. The row only adds detection, and each new named exclusion carries its measured reason for review. #385's L0 ruling is the precedent for this shape of key. **Ask-first files:** none (`test_audit_order_guard.py` is a guard; this row strengthens it and removes no entry). **Est:** 1.5 h. **Runtime:** any. **MVP:** P2.

---

## Not planned: HC-UIPV-006 popover stillness flake (pending L0 evidence)

HC-UIPV-006 (`e2e/ui-provenance.spec.ts:513`, the citation popover's `stillnessProbe`, an interaction probe with a 40 ms gap bound) failed once in CI on #370 run 40649511595 with a 41 ms gap. L0 is running an A/B of it on the #370 branch against main. **No row is planned until that evidence is in.** Whatever row follows must not run beside G1-VERIFY-TRACE-RACE (same spec file), and it falls under the same rules: no bound change, no retry, no flaky mark, no change to `gates.ts` constants.
