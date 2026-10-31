/**
 * UI-GATES acceptance harness self-tests (HC-UIG-001 .. HC-UIG-006, HC-UIG-008).
 *
 * Every test here proves that a gate helper from e2e/support/gates.ts can
 * fail, or passes on the page it is given. HC-UIG-002 (/inbox colour contrast)
 * and HC-UIG-003 (the route fade) are plain tests: their assertions must pass
 * on this branch. The green "pre" test beside each one is the guard: it shows
 * the page rendered and the sampler recorded. The console output prints the
 * axe rule id or the opacity sample that failed.
 *
 * Every /api/v1 request in these tests is answered by e2e/support/mockApi.ts,
 * and any other API request fails the precondition tests. Fixture pages are
 * served from http://localhost/gates/* through page.route, so they make no
 * network request. The config may still start the backend webServer and
 * globalSetup; see e2e/README.md for the run that starts neither.
 */

import { expect, test, type Page } from '@playwright/test';
import {
  ROUTE_CONTAINER_SELECTOR,
  ROUTE_FALLBACK_SELECTOR,
  STILLNESS_NAV_MAX_GAP_MS,
  axeGate,
  checkSampling,
  consoleAndNetworkGuard,
  maxEventDuration,
  noHorizontalScroll,
  routeOpacitySamples,
  stillnessProbe,
  type StillnessOptions,
} from './support/gates';
import { installMockApi, seedMockSession } from './support/mockApi';

const FIXTURE_ORIGIN = 'http://localhost';
const FIXTURE_PATH = '/gates/fixture';

/**
 * Serves one HTML fixture from a fulfilled route (no network) and opens it.
 * `slowFetchMs` answers GET /gates/slow only after that delay (lazy route
 * fixtures). Playwright matches the newest route first, so that route is
 * registered after the page route.
 */
async function serveFixture(page: Page, html: string, options: { slowFetchMs?: number } = {}): Promise<void> {
  await page.route(`${FIXTURE_ORIGIN}/gates/**`, (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: html })
  );
  if (options.slowFetchMs !== undefined) {
    const delay = options.slowFetchMs;
    await page.route(`${FIXTURE_ORIGIN}/gates/slow`, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, delay));
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
  }
  await page.goto(`${FIXTURE_ORIGIN}${FIXTURE_PATH}`);
  // Idle before the probe starts, as an SPA route change is after the app has loaded.
  // stillnessProbe's lazyRoute wait then returns at once, which is what the lazy fixtures test.
  await page.waitForLoadState('networkidle');
}

function fixtureHtml(body: string, script: string): string {
  return [
    '<!doctype html><html lang="en"><head><meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    '<style>body{margin:0;font:16px/1.4 sans-serif}</style>',
    `</head><body>${body}<script>${script}</script></body></html>`,
  ].join('');
}

/**
 * Navigation fixtures: a same-document route change (pushState) that swaps the
 * keyed route container. __swap(inner) returns the new container.
 */
const NAV_SWAP_SCRIPT = `
  window.__swap = function (inner) {
    history.pushState({}, '', '/gates/next');
    document.getElementById('route').remove();
    var m = document.createElement('main');
    m.id = 'route';
    m.setAttribute('data-route-container', '/gates/next');
    m.innerHTML = inner;
    document.body.appendChild(m);
    return m;
  };
`;

const NAV_BODY = '<main id="route" data-route-container="/gates/fixture"><p data-t0>Route A</p></main>';

const startFixture = (page: Page): StillnessOptions['trigger'] => () =>
  page.evaluate(() => (window as unknown as { __start: () => void }).__start());

/** Opens /inbox with the mock API, the seeded session, and returns the guard. */
async function openInbox(page: Page) {
  const mock = await installMockApi(page);
  await seedMockSession(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  await page.goto('/inbox');
  await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
  return { mock, guard };
}

// ---------------------------------------------------------------------------
// HC-UIG-001: noHorizontalScroll can fail (GREEN self-test).
// ---------------------------------------------------------------------------
test('HC-UIG-001 noHorizontalScroll fails a 600 px block at 390 and passes a fitting one', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });

  await page.setContent(
    '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>' +
      '<body style="margin:0"><div style="width:600px;height:40px;background:#ccc">wide</div></body></html>'
  );
  const wide = await noHorizontalScroll(page);
  console.log(`HC-UIG-001 600px block at 390: ${JSON.stringify(wide)}`);
  expect(wide.ok, `600 px block must fail the gate, got ${JSON.stringify(wide)}`).toBe(false);

  await page.setContent(
    '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>' +
      '<body style="margin:0"><div style="width:300px;height:40px;background:#ccc">fits</div></body></html>'
  );
  const fit = await noHorizontalScroll(page);
  console.log(`HC-UIG-001 300px block at 390: ${JSON.stringify(fit)}`);
  expect(fit.ok, `fitting block must pass the gate, got ${JSON.stringify(fit)}`).toBe(true);
});

// ---------------------------------------------------------------------------
// HC-UIG-002: axeGate on /inbox reports no color-contrast (plain test; no longer expected to fail).
// ---------------------------------------------------------------------------
test('HC-UIG-002 pre: /inbox renders under the mock API, and axe returns rule ids', async ({ page }) => {
  const { mock, guard } = await openInbox(page);
  await page.waitForLoadState('networkidle');

  console.log(`HC-UIG-002 pre served=${mock.served.length} unmocked=${JSON.stringify(mock.unmocked)}`);
  expect(mock.served.length, 'the mock must answer the inbox API calls').toBeGreaterThan(0);
  expect(mock.unmocked, 'no /api/v1 call may reach the backend').toEqual([]);
  expect(() => guard.assertClean(), 'console and network must be clean on /inbox').not.toThrow();

  // The guard for the HC-UIG-002 axe test below: axe must return rule ids on /inbox.
  const result = await axeGate(page);
  console.log(`HC-UIG-002 pre axe rule ids: ${JSON.stringify(result.ruleIds)}`);
  expect(Array.isArray(result.ruleIds), 'axeGate must return a list of rule ids').toBe(true);
});

test(
  'HC-UIG-002 axeGate on /inbox reports no color-contrast',
  async ({ page }) => {
    await installMockApi(page);
    await seedMockSession(page);
    await page.goto('/inbox');
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();

    // Axe reads colour mid-fade if it runs during the route's entrance fade (flaky otherwise).
    await settleRoute(page);
    const result = await axeGate(page);
    console.log(
      `HC-UIG-002 axe rule ids on /inbox: ${JSON.stringify(result.ruleIds)} ` +
        `blocking=${JSON.stringify(result.blocking.map((v) => `${v.id}:${v.impact}`))}`
    );
    expect(result.ruleIds, 'axe rule ids reported on /inbox').not.toContain('color-contrast');
  }
);

// ---------------------------------------------------------------------------
// HC-UIG-003: routeOpacitySamples records a sample < 0.3 (UI-SHELL: the route fade is opacity-only, M7).
// ---------------------------------------------------------------------------
/**
 * Waits until the route element has finished its entrance fade. On /inbox the
 * PageTransition fades in on load; a sample taken during that fade is load-in,
 * not the nav-click defect that HC-UIG-003 measures.
 */
async function settleRoute(page: Page): Promise<void> {
  await expect
    .poll(
      () =>
        page.evaluate(
          ({ container, fallback }) => {
            const el = document.querySelector(container) ?? document.querySelector(fallback);
            return el ? parseFloat(getComputedStyle(el).opacity) : NaN;
          },
          { container: ROUTE_CONTAINER_SELECTOR, fallback: ROUTE_FALLBACK_SELECTOR }
        ),
      { message: 'the route element must finish its entrance fade before the nav click', timeout: 10_000 }
    )
    .toBeGreaterThanOrEqual(0.99);
}

const navigateToVerify = (page: Page) => async () => {
  await page
    .getByRole('navigation', { name: 'Main navigation' })
    .getByRole('link', { name: 'Review values' })
    .click();
};

test('HC-UIG-003 pre: a nav click samples the route container and ends at opacity 1', async ({
  page,
}) => {
  await openInbox(page);
  await settleRoute(page);

  const samples = await routeOpacitySamples(page, { navigate: navigateToVerify(page), durationMs: 800 });
  console.log(
    `HC-UIG-003 pre samples (${samples.length}): ${JSON.stringify(samples.map((s) => [s.t, s.opacity]))}`
  );
  expect(samples.length, 'sampler must record samples').toBeGreaterThan(10);
  expect(
    samples.filter((s) => !Number.isFinite(s.opacity)),
    'every sample must read a finite route container opacity'
  ).toEqual([]);
  expect(samples[samples.length - 1]?.opacity, 'route container must settle at 1').toBe(1);
});

test(
  'HC-UIG-003 route container opacity after a nav click never drops below 0.3',
  async ({ page }) => {
    await openInbox(page);
    await settleRoute(page);

    const samples = await routeOpacitySamples(page, { navigate: navigateToVerify(page), durationMs: 800 });
    const low = samples.filter((s) => s.opacity < 0.3);
    console.log(
      `HC-UIG-003 samples below 0.3 (${low.length} of ${samples.length}): ${JSON.stringify(low.map((s) => [s.t, s.opacity]))}`
    );
    expect(low, 'route container opacity samples below 0.3 after a nav click').toEqual([]);
  }
);

// ---------------------------------------------------------------------------
// HC-UIG-004: consoleAndNetworkGuard fails a non-localhost request (GREEN self-test).
// ---------------------------------------------------------------------------
test('HC-UIG-004 consoleAndNetworkGuard fails a page that requests https://example.com', async ({
  page,
}) => {
  await page.route('https://example.com/**', (route) => route.abort());
  await page.route('http://localhost/pixel.png', (route) =>
    route.fulfill({ status: 200, contentType: 'image/png', body: '' })
  );
  const guard = consoleAndNetworkGuard(page);

  const requested = page.waitForRequest('https://example.com/**');
  await page.setContent(
    '<!doctype html><img src="http://localhost/pixel.png" alt=""><img src="https://example.com/pixel.png" alt="">'
  );
  await requested;

  const report = guard.report();
  console.log(`HC-UIG-004 guard report: ${JSON.stringify(report)}`);
  expect(report.externalRequests, 'only the non-localhost request is external').toEqual([
    'https://example.com/pixel.png',
  ]);
  expect(() => guard.assertClean(), 'guard must fail the page').toThrow(/example\.com/);
});

// ---------------------------------------------------------------------------
// HC-UIG-005: maxEventDuration returns a finite number under CPU x4 (GREEN self-test).
// ---------------------------------------------------------------------------
test('HC-UIG-005 maxEventDuration returns a finite number for a click on /setup under CPU x4', async ({
  page,
}) => {
  await installMockApi(page);
  await page.goto('/setup');
  const setupButton = page.getByRole('button', { name: 'Create a new profile' });
  await expect(setupButton).toBeVisible();

  const ms = await maxEventDuration(page, async () => {
    await setupButton.click();
  });
  console.log(`HC-UIG-005 max event duration on /setup click at CPU x4: ${ms} ms`);
  expect(Number.isFinite(ms), `expected a finite duration, got ${ms}`).toBe(true);
});

test('HC-UIG-005 maxEventDuration reports a 120 ms busy click as >= 100 ms and ignores earlier events', async ({
  page,
}) => {
  // A dead observer returns 0 for the /setup click, so the test above cannot
  // fail on its own. This one needs a known slow click to be seen.
  await page.setContent(
    fixtureHtml(
      '<button id="busy" type="button">Busy</button><button id="quick" type="button">Quick</button>',
      "document.getElementById('busy').addEventListener('click', function () { var end = performance.now() + 120; while (performance.now() < end) {} });"
    )
  );
  // Before the measurement: this slow event must not be counted.
  await page.click('#busy');
  await page.waitForTimeout(200);

  const quick = await maxEventDuration(page, async () => {
    await page.click('#quick');
  });
  const busy = await maxEventDuration(page, async () => {
    await page.click('#busy');
  });
  console.log(`HC-UIG-005 busy click: ${busy} ms; quick click after an earlier busy click: ${quick} ms`);
  expect(busy, `a 120 ms click must be reported as >= 100 ms, got ${busy}`).toBeGreaterThanOrEqual(100);
  expect(quick, `the earlier 120 ms click must not be counted, got ${quick}`).toBeLessThan(100);
});

// ---------------------------------------------------------------------------
// HC-UIG-006: stillnessProbe self-tests (GREEN). Each failing fixture must be
// rejected with a message that names the property that moved.
// ---------------------------------------------------------------------------
const FAIL_FIXTURES: Array<{
  id: string;
  title: string;
  html: string;
  kind: 'interaction' | 'navigation';
  expected: string[];
  reason: RegExp;
  /** Passed to serveFixture: answers GET /gates/slow after this many ms. */
  slowFetchMs?: number;
  /** Passed to stillnessProbe. */
  lazyRoute?: boolean;
  /** The first capture of `pattern` in the rejection must be at least `min`. */
  minimum?: { pattern: RegExp; min: number };
}> = [
  {
    id: '(a)',
    title: 'child of a container that fades from .35',
    html: fixtureHtml(
      '<div id="box"><p data-t0 id="t">Glucose 104 mg/dL</p></div>',
      "window.__start = function () { document.getElementById('box').animate([{opacity:.35},{opacity:1}], {duration:300, fill:'both'}); };"
    ),
    kind: 'interaction',
    expected: ['[data-t0]'],
    reason: /effective opacity/,
  },
  {
    id: '(b)',
    title: 'inside a parent that translates 6 px',
    html: fixtureHtml(
      '<div id="parent"><p data-t0 id="t">Glucose 104 mg/dL</p></div>',
      "window.__start = function () { document.getElementById('parent').animate([{transform:'translateX(0px)'},{transform:'translateX(6px)'}], {duration:300, fill:'forwards'}); };"
    ),
    kind: 'interaction',
    expected: ['[data-t0]'],
    reason: /getBoundingClientRect changed/,
  },
  {
    id: '(c)',
    title: 'popover that scales in from .96 (overlay rule)',
    html: fixtureHtml(
      '<div data-t0 id="pop" style="width:220px;height:60px;background:#eee">Glucose 104 mg/dL</div>',
      "window.__start = function () { document.getElementById('pop').animate([{transform:'scale(0.96)'},{transform:'scale(1)'}], {duration:200}); };"
    ),
    kind: 'interaction',
    expected: ['[data-t0]'],
    reason: /computed transform changed/,
  },
  {
    id: '(d)',
    title: 'zero [data-t0] nodes while expected is non-empty',
    html: fixtureHtml('<p id="x">Glucose 104 mg/dL</p>', 'window.__start = function () {};'),
    kind: 'interaction',
    expected: ['[data-t0]'],
    reason: /found zero \[data-t0\] nodes/,
  },
  {
    id: '(e)',
    title: 'one expected selector that matches nothing',
    html: fixtureHtml(
      '<p data-t0 class="present">Glucose 104 mg/dL</p>',
      'window.__start = function () {};'
    ),
    kind: 'interaction',
    expected: ['.present', '.missing-selector'],
    reason: /"\.missing-selector" matched no \[data-t0\] node/,
  },
  {
    id: '(f)',
    title: 'navigation whose route container translates during the fade',
    html: fixtureHtml(
      NAV_BODY,
      `${NAV_SWAP_SCRIPT}
       window.__start = function () {
         var m = window.__swap('<p data-t0 id="t">Route B</p>');
         m.animate([{opacity:.35, transform:'translateY(6px)'},{opacity:1, transform:'translateY(0px)'}], {duration:200, fill:'both'});
       };`
    ),
    kind: 'navigation',
    expected: ['[data-t0]'],
    reason: /route container transform/,
  },
  {
    id: '(g)',
    title: 'route fade that takes longer than 240 ms',
    html: fixtureHtml(
      NAV_BODY,
      `${NAV_SWAP_SCRIPT}
       window.__start = function () {
         var m = window.__swap('<p data-t0 id="t">Route B</p>');
         m.animate([{opacity:.35},{opacity:1}], {duration:400, fill:'both'});
       };`
    ),
    kind: 'navigation',
    expected: ['[data-t0]'],
    reason: /did not reach opacity 1 within 240 ms/,
  },
  {
    id: '(h)',
    title: 'a [data-t0] node that re-fades after the route fade settled',
    html: fixtureHtml(
      NAV_BODY,
      `${NAV_SWAP_SCRIPT}
       window.__start = function () {
         var m = window.__swap('<p data-t0 id="t">Route B</p>');
         m.animate([{opacity:.35},{opacity:1}], {duration:200, fill:'both'});
         m.querySelector('[data-t0]').animate([{opacity:1},{opacity:.5},{opacity:1}], {duration:400, delay:450});
       };`
    ),
    kind: 'navigation',
    expected: ['[data-t0]'],
    reason: /effective opacity 0\.\d+ \(must be 1\)/,
  },
  {
    id: '(h2)',
    title: 'the route container re-fades inside the 240 ms window, after it had settled',
    html: fixtureHtml(
      NAV_BODY,
      `${NAV_SWAP_SCRIPT}
       window.__start = function () {
         var m = window.__swap('<p data-t0 id="t">Route B</p>');
         m.animate([{opacity:.35},{opacity:1}], {duration:120, fill:'both'});
         m.animate([{opacity:1},{opacity:.5},{opacity:1}], {duration:120, delay:150});
       };`
    ),
    kind: 'navigation',
    expected: ['[data-t0]'],
    reason: /route container opacity changed after settling/,
  },
  {
    id: '(i)',
    title: 'count-up at fixed width (tabular-nums)',
    html: fixtureHtml(
      '<p data-t0 id="n" style="display:inline-block;width:6ch;text-align:right;font-variant-numeric:tabular-nums">000</p>',
      `window.__start = function () {
         var el = document.getElementById('n'); var n = 0;
         var id = setInterval(function () { n += 5; el.textContent = String(n).padStart(3, '0'); if (n >= 100) clearInterval(id); }, 40);
       };`
    ),
    kind: 'interaction',
    expected: ['[data-t0]'],
    reason: /textContent changed/,
  },
  {
    id: '(j)',
    title: 'colour pulse on a [data-t0] node',
    html: fixtureHtml(
      '<p data-t0 id="p" style="color:rgb(0,0,0)">Glucose 104 mg/dL</p>',
      "window.__start = function () { document.getElementById('p').animate([{color:'rgb(0, 0, 0)'},{color:'rgb(255, 0, 0)'},{color:'rgb(0, 0, 0)'}], {duration:300}); };"
    ),
    kind: 'interaction',
    expected: ['[data-t0]'],
    reason: /computed color changed/,
  },
  {
    id: '(k)',
    title: 'clip-path reveal of a [data-t0] node',
    html: fixtureHtml(
      '<p data-t0 id="p">LDL 142 mg/dL</p>',
      "window.__start = function () { document.getElementById('p').animate([{clipPath:'inset(0 100% 0 0)'},{clipPath:'inset(0 0 0 0)'}], {duration:300}); };"
    ),
    kind: 'interaction',
    expected: ['[data-t0]'],
    reason: /computed clip-path changed/,
  },
  {
    id: '(l)',
    title: 'nested 150 ms translate of a [data-t0] node inside the route-fade window',
    html: fixtureHtml(
      NAV_BODY,
      `${NAV_SWAP_SCRIPT}
       window.__start = function () {
         var m = window.__swap('<p data-t0 id="t">Route B</p>');
         m.animate([{opacity:.35},{opacity:1}], {duration:200, fill:'both'});
         m.querySelector('[data-t0]').animate([{transform:'translateY(8px)'},{transform:'translateY(0px)'}], {duration:150});
       };`
    ),
    kind: 'navigation',
    expected: ['[data-t0]'],
    reason: /computed transform changed/,
  },
  {
    id: '(m)',
    title: 'lazy route: a fetch that starts after the trigger returns, then a [data-t0] transform after the 800 ms window',
    html: fixtureHtml(
      '<p data-t0 id="t">Glucose 104 mg/dL</p>',
      "window.__start = function () { setTimeout(function () { fetch('/gates/slow').then(function () { document.getElementById('t').animate([{transform:'translateX(0px)'},{transform:'translateX(6px)'}], {duration:300, fill:'forwards'}); }); }, 50); };"
    ),
    kind: 'interaction',
    expected: ['[data-t0]'],
    lazyRoute: true,
    slowFetchMs: 1200,
    reason: /computed transform changed/,
    minimum: { pattern: / at (\d+) ms/, min: 1000 },
  },
  {
    id: '(n)',
    title: 'the main thread blocks 150 ms during the trigger, so the sampler has a gap',
    html: fixtureHtml(
      '<p data-t0 id="t">Glucose 104 mg/dL</p>',
      'window.__start = function () { var end = performance.now() + 150; while (performance.now() < end) {} };'
    ),
    kind: 'interaction',
    expected: ['[data-t0]'],
    reason: /sampling gap of \d+ ms/,
    minimum: { pattern: /sampling gap of (\d+) ms/, min: 100 },
  },
  {
    id: '(o)',
    title: 'a Safety Rail outside the route container fades with its wrapper during the route swap',
    html: fixtureHtml(
      '<div id="shell"><aside data-t0 data-safety-rail id="rail">Safety Rail</aside></div>' + NAV_BODY,
      `${NAV_SWAP_SCRIPT}
       window.__start = function () {
         var m = window.__swap('<p data-t0 id="t">Route B</p>');
         m.animate([{opacity:.35},{opacity:1}], {duration:200, fill:'both'});
         document.getElementById('shell').animate([{opacity:.6},{opacity:1}], {duration:200, fill:'both'});
       };`
    ),
    kind: 'navigation',
    expected: ['[data-safety-rail]'],
    reason: /effective opacity 0\.\d+ must be 1 on \[data-t0\] aside "Safety Rail".*outside the route container/,
  },
];

for (const fixture of FAIL_FIXTURES) {
  test(`HC-UIG-006 ${fixture.id} stillnessProbe fails: ${fixture.title}`, async ({ page }) => {
    await serveFixture(page, fixture.html, { slowFetchMs: fixture.slowFetchMs });
    const error = await stillnessProbe(page, {
      trigger: startFixture(page),
      expected: fixture.expected,
      kind: fixture.kind,
      lazyRoute: fixture.lazyRoute,
    }).then(
      () => null,
      (caught: unknown) => caught
    );
    console.log(`HC-UIG-006 ${fixture.id} rejected with: ${String(error)}`);
    expect(error, 'the probe must reject this fixture').not.toBeNull();
    expect(String(error), 'the rejection must name the property that moved').toMatch(fixture.reason);
    if (fixture.minimum) {
      const captured = Number(fixture.minimum.pattern.exec(String(error))?.[1]);
      expect(captured, `the rejection must come at or after ${fixture.minimum.min}`).toBeGreaterThanOrEqual(
        fixture.minimum.min
      );
    }
  });
}

interface PassFixture {
  id: string;
  title: string;
  html: string;
  kind: 'interaction' | 'navigation';
  slowFetchMs?: number;
  lazyRoute?: boolean;
  /** Defaults to ['[data-t0]']. */
  expected?: string[];
}

const PASS_FIXTURES: PassFixture[] = [
  {
    id: 'pass-1',
    title: 'still [data-t0] node beside an infinitely animated non-T0 sibling',
    html: fixtureHtml(
      '<section><p data-t0 id="still">Glucose 92 mg/dL</p><div id="sib" style="width:40px;height:40px;background:#ccc"></div></section>',
      `document.getElementById('sib').animate([{transform:'translateX(0px)'},{transform:'translateX(20px)'}], {duration:500, iterations: Infinity, direction:'alternate'});
       window.__start = function () {};`
    ),
    kind: 'interaction',
  },
  {
    id: 'pass-2',
    title: 'navigation with a 200 ms opacity-only route fade, then stillness',
    html: fixtureHtml(
      NAV_BODY,
      `${NAV_SWAP_SCRIPT}
       window.__start = function () {
         var m = window.__swap('<p data-t0 id="t">Route B 92 mg/dL</p>');
         m.animate([{opacity:.35},{opacity:1}], {duration:200, fill:'both'});
       };`
    ),
    kind: 'navigation',
  },
  {
    id: 'pass-3',
    title: 'lazy route: a fetch that starts after the trigger returns and takes 1200 ms, then stillness',
    html: fixtureHtml(
      '<p data-t0 id="t">Glucose 92 mg/dL</p>',
      "window.__start = function () { setTimeout(function () { fetch('/gates/slow'); }, 50); };"
    ),
    kind: 'interaction',
    slowFetchMs: 1200,
    lazyRoute: true,
  },
  {
    id: 'pass-4',
    title: 'navigation whose Safety Rail sits outside a route container that fades (HC-UISH-009)',
    html: fixtureHtml(
      '<aside data-t0 data-safety-rail id="rail">Safety Rail: not medical advice</aside>' + NAV_BODY,
      `${NAV_SWAP_SCRIPT}
       window.__start = function () {
         var m = window.__swap('<p data-t0 id="t">Route B 92 mg/dL</p>');
         m.animate([{opacity:.35},{opacity:1}], {duration:200, fill:'both'});
       };`
    ),
    kind: 'navigation',
    expected: ['[data-safety-rail]'],
  },
];

/** Runs one PASS fixture through the probe and returns its report. */
async function runPassFixture(page: Page, fixture: PassFixture) {
  await serveFixture(page, fixture.html, { slowFetchMs: fixture.slowFetchMs });
  const report = await stillnessProbe(page, {
    trigger: startFixture(page),
    expected: fixture.expected ?? ['[data-t0]'],
    kind: fixture.kind,
    lazyRoute: fixture.lazyRoute,
  });
  console.log(`HC-UIG-006 ${fixture.id} report: ${JSON.stringify(report)}`);
  expect(report.samples, 'probe must take samples').toBeGreaterThan(3);
  expect(report.nodes, 'probe must see the [data-t0] node').toBeGreaterThan(0);
  if (fixture.lazyRoute) {
    // The 1200 ms fetch ends at ~1200 ms, network idle is 500 ms of quiet, then 800 ms more.
    expect(report.elapsedMs, 'the lazy window must run past the fetch, then 800 ms more').toBeGreaterThanOrEqual(2000);
  }
  return report;
}

for (const fixture of PASS_FIXTURES) {
  test(`HC-UIG-006 ${fixture.id} stillnessProbe passes: ${fixture.title}`, async ({ page }) => {
    await runPassFixture(page, fixture);
  });
}

// The sampler's gap check must not depend on what ran before it. A new browser context
// starts with a cold page and no earlier probe in it. Review round 2 measured a 40 ms
// gap limit failing on a cold run of pass-2 when the sampler queued behind CDP calls.
test('HC-UIG-006 pass-2 passes in a fresh browser context (cold sampler, no earlier probe)', async ({ browser }) => {
  const fixture = PASS_FIXTURES.find((candidate) => candidate.id === 'pass-2');
  if (!fixture) throw new Error('pass-2 fixture is missing');
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    const report = await runPassFixture(page, fixture);
    expect(report.maxGapMs, 'no sampling gap may exceed 40 ms on a cold context').toBeLessThanOrEqual(40);
  } finally {
    await context.close();
  }
});

test('HC-UIG-006 sampling check rejects too few samples and a gap over 40 ms, and passes a 20 ms cadence', () => {
  const cadence = (from: number, to: number, step: number): number[] => {
    const times: number[] = [];
    for (let t = from; t <= to; t += step) times.push(t);
    return times;
  };

  const steady = checkSampling(cadence(-100, 800, 20), 0, 800, null);
  console.log(`HC-UIG-006 sampling steady: ${JSON.stringify(steady)}`);
  expect(steady.failures, 'a 20 ms cadence must pass').toEqual([]);

  const sparse = checkSampling(cadence(-100, 200, 20), 0, 800, null);
  console.log(`HC-UIG-006 sampling sparse: ${JSON.stringify(sparse)}`);
  expect(sparse.failures.join('\n'), 'too few post-trigger samples must be named').toMatch(
    /only 11 sample\(s\) after the trigger/
  );

  const gapped = checkSampling([...cadence(-100, 0, 20), 180, ...cadence(200, 800, 20)], 0, 800, null);
  console.log(`HC-UIG-006 sampling gapped: ${JSON.stringify(gapped)}`);
  expect(gapped.maxGapMs, 'the 180 ms gap must be measured').toBe(180);
  expect(gapped.failures.join('\n'), 'the gap must be named').toMatch(/sampling gap of 180 ms/);
});

test('HC-UIG-008 sampling check bounds a page change at 70 ms, keeps 40 ms elsewhere, and keeps the 40 ms minimum', () => {
  const cadence = (from: number, to: number, step: number): number[] => {
    const times: number[] = [];
    for (let t = from; t <= to; t += step) times.push(t);
    return times;
  };
  // A 20 ms cadence with one gap of `gap` ms from the trigger at 0 ms.
  const withGap = (gap: number): number[] => [...cadence(-100, 0, 20), gap, ...cadence(gap + 20, 800, 20)];

  const nav70 = checkSampling(withGap(70), 0, 800, null, STILLNESS_NAV_MAX_GAP_MS);
  console.log(`HC-UIG-008 navigation 70 ms: ${JSON.stringify(nav70)}`);
  expect(nav70.failures, 'a 70 ms page-change gap must pass the 70 ms bound').toEqual([]);
  expect(nav70.maxGapMs, 'the 70 ms gap must be measured').toBe(70);

  const nav71 = checkSampling(withGap(71), 0, 800, null, STILLNESS_NAV_MAX_GAP_MS);
  console.log(`HC-UIG-008 navigation 71 ms: ${JSON.stringify(nav71)}`);
  expect(nav71.failures.join('\n'), 'a 71 ms page-change gap must fail and name the 70 ms bound').toMatch(
    /sampling gap of 71 ms \(must be <= 70 ms for a page change, owner STILLNESS-NAV-70; G10 samples every 16-40 ms\)/
  );

  const interaction41 = checkSampling(withGap(41), 0, 800, null);
  console.log(`HC-UIG-008 interaction 41 ms: ${JSON.stringify(interaction41)}`);
  expect(interaction41.failures.join('\n'), 'an interaction keeps the 40 ms bound: 41 ms must fail').toMatch(
    /sampling gap of 41 ms \(must be <= 40 ms/
  );

  const interaction40 = checkSampling(withGap(40), 0, 800, null);
  expect(interaction40.failures, 'a 40 ms gap must pass the default bound').toEqual([]);

  // 70 ms samples over 800 ms give 12 post-trigger samples; the minimum (800 / 40 = 20) still applies.
  const sparseNav = checkSampling(cadence(-70, 800, 70), 0, 800, null, STILLNESS_NAV_MAX_GAP_MS);
  console.log(`HC-UIG-008 navigation sparse: ${JSON.stringify(sparseNav)}`);
  expect(sparseNav.failures.join('\n'), 'too few samples must still fail on the 40 ms minimum').toMatch(
    /only 12 sample\(s\) after the trigger; the 800 ms window needs at least 20 at one per 40 ms/
  );
  expect(sparseNav.failures.join('\n'), 'a 70 ms gap is within the page-change bound').not.toMatch(/sampling gap/);
});
