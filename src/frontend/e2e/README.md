# Frontend e2e harness

Playwright specs for the frontend. The gate helpers in `support/gates.ts` implement the acceptance checks in the frontend revamp plan, section 6 (G1-G10). The fixtures in `support/mockApi.ts` answer the page's API calls. `ui-gates.spec.ts` proves each helper can fail (HC-UIG-001 to 006).

## Running

Run these from `src/frontend`. Each one was run as written on the UI-GATES branch, and each passed all 30 tests in `ui-gates.spec.ts` (the two `test.fail()` marks count as passes).

**1. With the backend (the config's default).** The config starts `e2e/support/start-backend.mjs` on port 8000 and `npm run dev` on port 3000. Set `HC_E2E_BACKEND_PYTHON` to a path to a Python that has the backend requirements. The path is resolved from `src/frontend`, so a checkout with `src/backend/.venv` can use `../backend/.venv/bin/python`.

```bash
HC_E2E_BACKEND_PYTHON=<python with the backend requirements> npx playwright test e2e/ui-gates.spec.ts --project=chromium
```

**2. Without the backend.** `PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1` is the config's switch for this: it starts only the dev server and `global-setup.ts` returns before it waits for `/health`. The variable is named for the assistant proof, so reusing it here is a side effect. A dedicated variable would change `playwright.config.ts` and `global-setup.ts`, which this row does not own.

```bash
PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-gates.spec.ts --project=chromium
```

**3. Against a production build (`vite preview`).** G3 is measured on a production build (plan §6). Preview serves `dist/`, and `HC_E2E_BASE_URL` points the specs at it. The config still starts the dev server on port 3000, which the specs do not use.

```bash
npm run build
npx vite preview --host 127.0.0.1 --port 4173 --strictPort &
HC_E2E_BASE_URL=http://127.0.0.1:4173 PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-gates.spec.ts --project=chromium
```

Stop the preview server afterwards.

Environment variables:

| Variable | Use |
|---|---|
| `HC_E2E_BACKEND_PYTHON` | Python with the backend requirements, for `support/start-backend.mjs`. Without a usable one, the backend webServer exits with "no candidate Python can import FastAPI/Uvicorn". |
| `PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1` | Starts only the dev server and skips the backend wait and the e2e profile setup (recipe 2). |
| `HC_E2E_BASE_URL` | Overrides `use.baseURL` (default `http://127.0.0.1:3000`), for example a `vite preview` run (recipe 3). |
| `HC_E2E_CHROMIUM_PATH` | Browser binary when the bundled Chromium revision is not installed. |

## Mock API or the real backend

Use the mock (`installMockApi`) for layout, motion, accessibility, and stillness checks. Those tests care about what the page renders, not what the server decides.

Use the real backend through HTTP (`support/start-backend.mjs`, with the helpers in `support/auth.ts`) for anything that asserts **auth, sessions, or status codes**: login, lock and unlock, token expiry, 401/403 handling, and any response code. A mock returns the status the test wrote, so it cannot show that the backend returns it. Route tests in the backend go through `tests/support/routes.py::route_client` for the same reason.

`ui-gates.spec.ts` makes no `/api/v1` request that reaches the backend. Every such request is answered by `installMockApi`. An unanswered request is recorded, answered with 599, and fails the precondition test (`HC-UIG-002 pre`) and the guard. With the backend running (recipe 1), `global-setup.ts` still waits for `/health` and creates the e2e profile before any test. The spec does not use that data, and recipe 2 shows it passes without the backend.

## Helpers

| Helper | Gate | Use it when | Returns (or throws) |
|---|---|---|---|
| `axeGate(page, { theme? })` | G1 | Checking a route for WCAG 2.0-2.2 A and AA violations. Run it for light, and for dark once `UI-DARK-FLIP` lands. | `{ violations, ruleIds, blocking }`. `blocking` is serious or critical. Assert on `ruleIds` or `blocking`. |
| `setTheme(page, theme)` | G1 | Applying dark before an axe or screenshot run. The product stays light until `UI-DARK-FLIP`, so dark results only mean something after the flip. | Sets `color-scheme`, `data-theme` and the `dark` class. |
| `noHorizontalScroll(page)` | G6 | After setting a viewport of 390×844 or 320×640, checking the page does not scroll sideways. | `{ scrollWidth, innerWidth, ok }`. |
| `measureCls(page, action)` | G2 | Measuring layout shift over a load plus interactions. Call it before the navigation that loads the page. | The CLS total, or NaN when no observer ran. |
| `maxEventDuration(page, action, { cpuRate? })` | G3 | Measuring the slowest input response (INP proxy) with the CPU throttled (default ×4). Chromium only. Only events that start after the call count. | Milliseconds. 0 means no event reached the 16 ms threshold, which a fast click and a dead observer both give. Pair it with a click known to be slow (HC-UIG-005). |
| `reducedMotionSnapshot(page, action)` | G5 | Checking that nothing is still transformed 50 ms after an interaction with reduced motion on. | Offending elements. An empty array passes. |
| `routeOpacitySamples(page, { navigate, durationMs?, intervalMs? })` | DF-6, HC-UISH-003 | Checking the route fade after a click in the nav. Samples every 40 ms by default. | `[{ t, opacity, source }]`. See **The route element** below. |
| `consoleAndNetworkGuard(page, { mock? })` | G7 | Failing a page that logs an error, requests a non-localhost origin, or reaches an unmocked API. Create it before the navigation. Pass the `installMockApi` result as `mock`. | `{ report(), assertClean() }`. `assertClean` throws, listing every problem. |
| `safetyVisible(page, selector?)` | G9 (from UI-SHELL) | Checking the Safety Rail is in the viewport at effective opacity 1, at first paint and after each interaction. Default selector `[data-safety-rail]`. | `{ found, inViewport, effectiveOpacity }`. |
| `stillnessProbe(page, { trigger, expected, kind?, lazyRoute?, windowMs? })` | G10 | Checking that `[data-t0]` content stays still through an interaction or a navigation. | Resolves with `{ samples, postTriggerSamples, maxGapMs, elapsedMs, nodes, routeKey }` when still. Throws `StillnessError` with one line per failure. |
| `checkSampling(sampleTimes, triggeredAt, windowMs, lastError)` | G10 | Checking sample times without a page: the sampling rule the probe applies. Used by its own test. | `{ failures, maxGapMs, postTriggerSamples }`. |

### stillnessProbe

- `trigger` runs after the first sample, so the probe sees the start of any animation it starts.
- `expected` lists the route's `data-t0` selectors (plan §2.7). Each must match a `[data-t0]` node. The probe also fails on zero nodes.
- `kind: 'navigation'` turns on the route-fade rules. The container is keyed by pathname, it must have no transform, and it must reach opacity 1 within 240 ms. During that window a `[data-t0]` node inside the container must match the container's opacity. A node outside it, such as the Safety Rail, must stay at 1, because only the container fades (plan §2 T0 row, HC-UISH-009). Plan G10's "each T0 node" is read as "each T0 node inside the container", since the same plan keeps the Safety Rail outside it at opacity 1. `kind: 'interaction'` (the default) requires effective opacity 1 throughout, with no fade window.
- `lazyRoute: true` is for a trigger that starts a fetch. The window starts only when no request is in flight and none has started or finished for 500 ms, counted from the trigger (the same quiet period as Playwright's `networkidle`). Then the probe runs 800 ms more. It does not use `waitForLoadState('networkidle')`, which returns at once on a page that was already idle. HC-UIG-006 (m) is a fetch that starts after the trigger; the old wait missed it.
- Sampling runs inside the page, every 20 ms, on the page's clock (`performance.now()`, in whole milliseconds). A CDP call from Node would queue behind the trigger's own calls, so the gap between samples would depend on what ran earlier in the run. The probe fails when a gap at or after the trigger is over 40 ms, or when the window has fewer than 800 / 40 = 20 samples after the trigger. The report's `maxGapMs` and `postTriggerSamples` show the measured values. `HC-UIG-006 pass-2 passes in a fresh browser context` runs a navigation in a new context, so a cold run is part of the suite.
- A full page load ends the in-page sampler, and the probe then fails with `lost its sampler`. Use the probe for interactions and client-side (SPA) navigations.
- Failure messages name the property: `computed transform changed`, `getBoundingClientRect changed`, `computed color changed`, `computed clip-path changed`, `textContent changed`, `effective opacity 0.35 (must be 1)`, `effective opacity 0.60 must be 1 … outside the route container`, `route container transform`, `route container opacity changed after settling`, `route container did not reach opacity 1 within 240 ms`, `found zero [data-t0] nodes`, `expected selector "…" matched no [data-t0] node`, `sampling gap of N ms`, `only N sample(s) after the trigger`, `timed out waiting for the lazy route to go network idle`, `lost its sampler`.

### maxEventDuration

Event Timing reports an event only when it takes at least 16 ms, and the duration is rounded. Entries that start before the call are ignored, so an earlier slow click does not leak into the next measurement. Under the default ×4 throttle, a 120 ms busy handler reports about 120 ms.

### consoleAndNetworkGuard

Console errors are recorded as they arrive. Requests are checked on the `request` event, so a request that is aborted still counts. `localhost`, `127.0.0.1` and `[::1]` are local. `data:` and `blob:` are not network requests.

### mockApi

`installMockApi(page)` answers `GET /profiles`, `/documents`, `/documents/highlights/summary`, `/pinboards` and `/observations/trends/{glucose|ldl|hba1c}`. Each fixture is typed from `src/services/types.ts`. Any other `/api/v1` request is recorded in `unmocked` and answered with 599. `seedMockSession(page)` writes the zustand auth state so `ProtectedRoute` lets the page through.

The seeded values are glucose 92/104/118/101 against 70-99 mg/dL, LDL 142 and HbA1c 6.1. Every trend point sets `user_verified` (contract I-13). The person in every fixture is `Alex Rivera`. Do not use a real person's name in a fixture.

## Contracts the product must meet

| Attribute | Who adds it | Used by |
|---|---|---|
| `data-t0` on every element in plan §2.7 | the row named there | `stillnessProbe` |
| `data-route-container="<pathname>"` on the route element | UI-SHELL (the outlet that holds the page) | `routeOpacitySamples`, `stillnessProbe` with `kind: 'navigation'` |
| `data-safety-rail` on the Safety Rail | UI-SHELL | `safetyVisible` |

### The route element

No row has added `data-route-container` yet. Until one does, `routeOpacitySamples` reads `main > div`, which is the PageTransition `motion.div` that `AppLayout` renders directly inside `<main>`. That element goes 1 → 0 on exit and 0 → 1 on enter, so it is the one that carries the defect. `main` itself never animates, so sampling it would read 1 and hide the defect. Once a row adds `data-route-container`, the helper reads that element first.

## Test-fail policy

`HC-UIG-002` and `HC-UIG-003` are `test.fail()`. Playwright passes a `test.fail()` on any failure, so the defect assertion alone cannot show the reason. Two things do. The green `pre` test beside each one proves the page rendered and the sampler recorded. The line each test prints (`HC-UIG-002 axe rule ids on /inbox: [...]`, `HC-UIG-003 samples below 0.3 (...)`) names the rule id or the samples that failed. The `HC-UIG-002 pre` test also calls `axeGate` and asserts that it returned a list of rule ids. If axe itself throws, the `test.fail()` would pass for the wrong reason, so the `pre` test fails first.

To see the assertion behind a `test.fail()`, copy the spec to a scratch file under `e2e/`, replace `test.fail(` with `test(`, and run it with `-g 'expected until'`. Delete the copy afterwards. When the owning row lands, the test starts to pass. Playwright reports that as an unexpected pass, and the row removes the `test.fail()` wrapper.

Do not weaken a helper or an assertion to make a test pass. Fix the product, or stop and ask.
