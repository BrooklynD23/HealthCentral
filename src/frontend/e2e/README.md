# Frontend e2e harness

Playwright specs for the frontend. The gate helpers in `support/gates.ts` implement the acceptance checks in the frontend revamp plan, section 6 (G1-G10). The fixtures in `support/mockApi.ts` answer the page's API calls. `ui-gates.spec.ts` proves each helper can fail (HC-UIG-001 to 006).

## Running

From `src/frontend`:

```bash
npx playwright test e2e/ui-gates.spec.ts --project=chromium
```

Environment variables:

| Variable | Use |
|---|---|
| `HC_E2E_BACKEND_PYTHON` | Python with the backend requirements, for `support/start-backend.mjs` (the config always starts the backend). |
| `HC_E2E_CHROMIUM_PATH` | Browser binary when the bundled Chromium revision is not installed. |
| `HC_E2E_BASE_URL` | Overrides `use.baseURL` (default `http://127.0.0.1:3000`), for example a `vite preview` run. The config still starts `npm run dev` on port 3000 for its `webServer`, so run preview on the same origin or accept that the dev server also starts. |

## Mock API or the real backend

Use the mock (`installMockApi`) for layout, motion, accessibility, and stillness checks. Those tests care about what the page renders, not what the server decides.

Use the real backend through HTTP (`support/start-backend.mjs`, with the helpers in `support/auth.ts`) for anything that asserts **auth, sessions, or status codes**: login, lock and unlock, token expiry, 401/403 handling, and any response code. A mock returns the status the test wrote, so it cannot show that the backend returns it. Route tests in the backend go through `tests/support/routes.py::route_client` for the same reason.

`ui-gates.spec.ts` makes no `/api/v1` request that reaches the backend. Every such request is answered by `installMockApi`, and the precondition test (`HC-UIG-002 pre`) fails on any request the mock did not answer. Two things still run the backend: the config's `webServer` starts it, and `support/global-setup.ts` waits for `/health` and creates the e2e profile before any test. The spec does not depend on that data.

## Helpers

| Helper | Gate | Use it when | Returns (or throws) |
|---|---|---|---|
| `axeGate(page, { theme? })` | G1 | Checking a route for WCAG 2.0-2.2 A and AA violations. Run it for light, and for dark once `UI-DARK-FLIP` lands. | `{ violations, ruleIds, blocking }`. `blocking` is serious or critical. Assert on `ruleIds` or `blocking`. |
| `setTheme(page, theme)` | G1 | Applying dark before an axe or screenshot run. The product stays light until `UI-DARK-FLIP`, so dark results only mean something after the flip. | Sets `color-scheme`, `data-theme` and the `dark` class. |
| `noHorizontalScroll(page)` | G6 | After setting a viewport of 390×844 or 320×640, checking the page does not scroll sideways. | `{ scrollWidth, innerWidth, ok }`. |
| `measureCls(page, action)` | G2 | Measuring layout shift over a load plus interactions. Call it before the navigation that loads the page. | The CLS total, or NaN when no observer ran. |
| `maxEventDuration(page, action, { cpuRate? })` | G3 | Measuring the slowest input response (INP proxy) with the CPU throttled (default ×4). Chromium only. | Milliseconds. 0 means no event reached the 16 ms threshold. |
| `reducedMotionSnapshot(page, action)` | G5 | Checking that nothing is still transformed 50 ms after an interaction with reduced motion on. | Offending elements. An empty array passes. |
| `routeOpacitySamples(page, { navigate, durationMs?, intervalMs? })` | DF-6, HC-UISH-003 | Checking the route fade after a click in the nav. Samples every 40 ms by default. | `[{ t, opacity, source }]`. See **The route element** below. |
| `consoleAndNetworkGuard(page, { mock? })` | G7 | Failing a page that logs an error, requests a non-localhost origin, or reaches an unmocked API. Create it before the navigation. Pass the `installMockApi` result as `mock`. | `{ report(), assertClean() }`. `assertClean` throws, listing every problem. |
| `safetyVisible(page, selector?)` | G9 (from UI-SHELL) | Checking the Safety Rail is in the viewport at effective opacity 1, at first paint and after each interaction. Default selector `[data-safety-rail]`. | `{ found, inViewport, effectiveOpacity }`. |
| `stillnessProbe(page, { trigger, expected, kind?, lazyRoute?, windowMs? })` | G10 | Checking that `[data-t0]` content stays still through an interaction or a navigation. | Resolves with `{ samples, nodes, routeKey }` when still. Throws `StillnessError` with one line per failure. |

### stillnessProbe

- `trigger` runs after the first sample, so the probe sees the start of any animation it starts.
- `expected` lists the route's `data-t0` selectors (plan §2.7). Each must match a `[data-t0]` node. The probe also fails on zero nodes.
- `kind: 'navigation'` turns on the route-fade rules: the container is keyed by pathname, it must have no transform, it must reach opacity 1 within 240 ms, and each node's effective opacity must equal the container's during that window. `kind: 'interaction'` (the default) requires effective opacity 1 throughout, with no fade window.
- `lazyRoute: true` extends the window until network idle, then 800 ms more. Use it on the first visit to a lazy route.
- Failure messages name the property: `computed transform changed`, `getBoundingClientRect changed`, `computed color changed`, `computed clip-path changed`, `textContent changed`, `effective opacity 0.35 (must be 1)`, `route container transform`, `route container did not reach opacity 1 within 240 ms`, `found zero [data-t0] nodes`, `expected selector "…" matched no [data-t0] node`.

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

`HC-UIG-002` and `HC-UIG-003` are `test.fail()`. Each one asserts on the specific defect (an axe rule id, a sample below 0.3), so an unrelated error cannot make it pass. Each has a green precondition test beside it that proves the page rendered and the sampler worked. When the owning row lands, the test starts to pass; Playwright reports that as an unexpected pass, and the row removes the `test.fail()` wrapper.

Do not weaken a helper or an assertion to make a test pass. Fix the product, or stop and ask.
