/**
 * UI-GATES acceptance harness self-tests (HC-UIG-001 .. HC-UIG-006).
 *
 * Every test here proves that a gate helper from e2e/support/gates.ts can
 * fail, or reports the expected defect. Tests marked test.fail() are the
 * known defects of /inbox and the route fade; they are expected to fail until
 * UI-TOKENS and UI-SHELL land, and each one asserts on the specific reason
 * (an axe rule id, a recorded sample below 0.3) so an unrelated error cannot
 * pass it.
 *
 * No backend is needed by these tests: every /api/v1 request is answered by
 * e2e/support/mockApi.ts, and any other API request fails the precondition
 * tests. Fixture pages are served from http://localhost/gates/* through
 * page.route, so they make no network request. (The config's globalSetup and
 * backend webServer still run; see e2e/README.md.)
 */

import { expect, test, type Page } from '@playwright/test';
import {
  axeGate,
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

/** Serves one HTML fixture from a fulfilled route (no network) and opens it. */
async function serveFixture(page: Page, html: string): Promise<void> {
  await page.route(`${FIXTURE_ORIGIN}/gates/**`, (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: html })
  );
  await page.goto(`${FIXTURE_ORIGIN}${FIXTURE_PATH}`);
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
// HC-UIG-002: axeGate on /inbox reports color-contrast (test.fail until UI-TOKENS).
// ---------------------------------------------------------------------------
test('HC-UIG-002 pre: /inbox renders under the mock API with no unmocked call', async ({ page }) => {
  const { mock, guard } = await openInbox(page);
  await page.waitForLoadState('networkidle');

  console.log(`HC-UIG-002 pre served=${mock.served.length} unmocked=${JSON.stringify(mock.unmocked)}`);
  expect(mock.served.length, 'the mock must answer the inbox API calls').toBeGreaterThan(0);
  expect(mock.unmocked, 'no /api/v1 call may reach the backend').toEqual([]);
  expect(() => guard.assertClean(), 'console and network must be clean on /inbox').not.toThrow();
});

test.fail(
  'HC-UIG-002 axeGate on /inbox reports color-contrast (expected until UI-TOKENS)',
  async ({ page }) => {
    await installMockApi(page);
    await seedMockSession(page);
    await page.goto('/inbox');
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();

    const result = await axeGate(page);
    console.log(
      `HC-UIG-002 axe rule ids on /inbox: ${JSON.stringify(result.ruleIds)} ` +
        `blocking=${JSON.stringify(result.blocking.map((v) => `${v.id}:${v.impact}`))}`
    );
    expect(result.ruleIds, 'axe rule ids reported on /inbox').not.toContain('color-contrast');
  }
);

// ---------------------------------------------------------------------------
// HC-UIG-003: routeOpacitySamples records a sample < 0.3 (test.fail until UI-SHELL).
// ---------------------------------------------------------------------------
const navigateToVerify = (page: Page) => async () => {
  await page
    .getByRole('navigation', { name: 'Main navigation' })
    .getByRole('link', { name: 'Verify' })
    .click();
};

test('HC-UIG-003 pre: a nav click samples the route container and ends at opacity 1', async ({
  page,
}) => {
  await openInbox(page);

  const samples = await routeOpacitySamples(page, { navigate: navigateToVerify(page), durationMs: 800 });
  console.log(
    `HC-UIG-003 pre samples (${samples.length}): ${JSON.stringify(samples.map((s) => [s.t, s.opacity]))}`
  );
  expect(samples.length, 'sampler must record samples').toBeGreaterThan(10);
  expect(
    samples.filter((s) => !Number.isFinite(s.opacity)),
    'every sample must read a finite route container opacity'
  ).toEqual([]);
  expect(samples.at(-1)?.opacity, 'route container must settle at 1').toBe(1);
});

test.fail(
  'HC-UIG-003 route container opacity after a nav click never drops below 0.3 (expected until UI-SHELL)',
  async ({ page }) => {
    await openInbox(page);

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
    route.fulfill({ status: 200, contentType: 'image/png', body: Buffer.alloc(0) })
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
];

for (const fixture of FAIL_FIXTURES) {
  test(`HC-UIG-006 ${fixture.id} stillnessProbe fails: ${fixture.title}`, async ({ page }) => {
    await serveFixture(page, fixture.html);
    const probe = stillnessProbe(page, {
      trigger: startFixture(page),
      expected: fixture.expected,
      kind: fixture.kind,
    });
    await expect(probe, `probe must reject with a message naming the moved property`).rejects.toThrow(
      fixture.reason
    );
  });
}

const PASS_FIXTURES: Array<{ id: string; title: string; html: string; kind: 'interaction' | 'navigation' }> = [
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
];

for (const fixture of PASS_FIXTURES) {
  test(`HC-UIG-006 ${fixture.id} stillnessProbe passes: ${fixture.title}`, async ({ page }) => {
    await serveFixture(page, fixture.html);
    const report = await stillnessProbe(page, {
      trigger: startFixture(page),
      expected: ['[data-t0]'],
      kind: fixture.kind,
    });
    console.log(`HC-UIG-006 ${fixture.id} report: ${JSON.stringify(report)}`);
    expect(report.samples, 'probe must take samples').toBeGreaterThan(3);
    expect(report.nodes, 'probe must see the [data-t0] node').toBeGreaterThan(0);
  });
}
