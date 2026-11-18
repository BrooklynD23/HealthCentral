/**
 * UI-GATES sampler timing self-tests (HC-UIG-007).
 *
 * The stillness sampler stamps each sample when it reads the page. A page that
 * blocks inside one of the sampler's own reads (here a wrapped
 * getBoundingClientRect, which every tick calls once per [data-t0] node) must
 * show that block as a sampling gap. A 30 ms block stays within the 40 ms bound.
 * A 60 ms block must be rejected, and the message must name the gap.
 * On a navigation (kind 'navigation') the bound is 70 ms: a 55 ms block passes
 * and a 90 ms block is rejected.
 * On an overlay open (kind 'overlay') the bound is also 70 ms: a 55 ms block passes,
 * a 75 ms block is rejected with the overlay text, and an interaction keeps 40 ms.
 *
 * HC-UIG-011 (UI-PG-SECURITY, ruling G10-HIDDEN-TABPANEL): a [data-t0] node inside a Tabs content panel that
 * carries `hidden` is gone, not moved (the Settings page keeps the Security panel mounted and hides it on a tab
 * switch). Only that case is excused. A node hidden by display:none on a plain ancestor, a node in a visible
 * panel that collapses, and a node that leaves a panel and comes back moved still fail.
 *
 * The fixtures are served from fulfilled routes (no network), as in
 * ui-gates.spec.ts. This file keeps its own copy of the small fixture helpers
 * because that spec must stay unchanged.
 */

import { expect, test, type Page } from '@playwright/test';
import { stillnessProbe, type StillnessOptions } from './support/gates';

const FIXTURE_ORIGIN = 'http://localhost';
const FIXTURE_PATH = '/gates/sampler';
const BODY = '<p data-t0 id="t">Glucose 104 mg/dL</p>';

async function serveFixture(page: Page, html: string): Promise<void> {
  await page.route(`${FIXTURE_ORIGIN}/gates/**`, (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: html })
  );
  await page.goto(`${FIXTURE_ORIGIN}${FIXTURE_PATH}`);
  // Idle before the probe starts, as the other fixtures do.
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

const startFixture = (page: Page): StillnessOptions['trigger'] => () =>
  page.evaluate(() => (window as unknown as { __start: () => void }).__start());

/**
 * Wraps getBoundingClientRect so that the first call after __start busy-waits `ms`.
 * The wait happens once, after the trigger, and nothing else on the page runs long.
 */
function blockOnceAfterStart(ms: number): string {
  return `
    (function () {
      var armed = false;
      var spent = false;
      var original = Element.prototype.getBoundingClientRect;
      Element.prototype.getBoundingClientRect = function () {
        if (armed && !spent) {
          spent = true;
          var end = performance.now() + ${ms};
          while (performance.now() < end) {}
        }
        return original.call(this);
      };
      window.__start = function () { armed = true; };
    })();
  `;
}

test('HC-UIG-007 (a) a 30 ms block inside one sampler read is not a sampling gap', async ({ page }) => {
  await serveFixture(page, fixtureHtml(BODY, blockOnceAfterStart(30)));
  const report = await stillnessProbe(page, {
    trigger: startFixture(page),
    expected: ['[data-t0]'],
  });
  console.log(`HC-UIG-007 (a) report: ${JSON.stringify(report)}`);
  expect(report.maxGapMs, 'the 30 ms block must not show as a gap above 40 ms').toBeLessThanOrEqual(40);
  expect(report.maxGapMs, 'the 30 ms block must land in the window and show a gap of at least 25 ms').toBeGreaterThanOrEqual(25);
});

test('HC-UIG-007 (b) a 60 ms block inside one sampler read is a sampling gap above 40 ms', async ({ page }) => {
  await serveFixture(page, fixtureHtml(BODY, blockOnceAfterStart(60)));
  const error = await stillnessProbe(page, {
    trigger: startFixture(page),
    expected: ['[data-t0]'],
  }).then(
    () => null,
    (caught: unknown) => caught
  );
  console.log(`HC-UIG-007 (b) rejected with: ${String(error)}`);
  expect(error, 'the probe must reject a 60 ms block').not.toBeNull();
  expect(String(error), 'the rejection must name a sampling gap').toMatch(/sampling gap of \d+ ms/);
  const gap = Number(/sampling gap of (\d+) ms/.exec(String(error))?.[1]);
  expect(gap, 'the named gap must be above 40 ms').toBeGreaterThan(40);
});

// A navigation: the route container swaps and fades in over 200 ms (the pass-2
// fixture's approach), and the first sampler read after the trigger blocks `ms`.
const NAV_BODY = '<main id="route" data-route-container="/gates/fixture"><p data-t0>Route A</p></main>';
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

function navBlockOnceAfterStart(ms: number): string {
  return `
    ${blockOnceAfterStart(ms)}
    ${NAV_SWAP_SCRIPT}
    (function () {
      var arm = window.__start;
      window.__start = function () {
        var m = window.__swap('<p data-t0 id="t">Route B</p>');
        m.animate([{opacity:.35},{opacity:1}], {duration:200, fill:'both'});
        arm();
      };
    })();
  `;
}

test('HC-UIG-007 (c) a ~55 ms block inside one sampler read during a navigation passes the 70 ms bound', async ({
  page,
}) => {
  await serveFixture(page, fixtureHtml(NAV_BODY, navBlockOnceAfterStart(55)));
  const report = await stillnessProbe(page, {
    kind: 'navigation',
    trigger: startFixture(page),
    expected: ['[data-t0]'],
  });
  console.log(`HC-UIG-007 (c) report: ${JSON.stringify(report)}`);
  expect(report.maxGapMs, 'the 55 ms block must land in the window and show as a gap above 40 ms').toBeGreaterThan(40);
  expect(report.maxGapMs, 'a page change may show a sampling gap of up to 70 ms').toBeLessThanOrEqual(70);
});

test('HC-UIG-007 (d) a ~90 ms block during a navigation is a sampling gap above 70 ms', async ({ page }) => {
  await serveFixture(page, fixtureHtml(NAV_BODY, navBlockOnceAfterStart(90)));
  const error = await stillnessProbe(page, {
    kind: 'navigation',
    trigger: startFixture(page),
    expected: ['[data-t0]'],
  }).then(
    () => null,
    (caught: unknown) => caught
  );
  console.log(`HC-UIG-007 (d) rejected with: ${String(error)}`);
  expect(error, 'the probe must reject a 90 ms block during a navigation').not.toBeNull();
  expect(String(error), 'the rejection must name a sampling gap').toMatch(/sampling gap of \d+ ms/);
  const gap = Number(/sampling gap of (\d+) ms/.exec(String(error))?.[1]);
  expect(gap, 'the named gap must be above 70 ms').toBeGreaterThan(70);
  expect(String(error), 'the navigation bound of 70 ms must be the one named').toMatch(
    /must be <= 70 ms for a page change/
  );
});

test('HC-UIG-007 (e) a ~55 ms block inside one sampler read during an overlay open passes the 70 ms bound', async ({
  page,
}) => {
  await serveFixture(page, fixtureHtml(BODY, blockOnceAfterStart(55)));
  const report = await stillnessProbe(page, {
    kind: 'overlay',
    trigger: startFixture(page),
    expected: ['[data-t0]'],
  });
  console.log(`HC-UIG-007 (e) report: ${JSON.stringify(report)}`);
  expect(report.maxGapMs, 'the 55 ms block must land in the window and show as a gap above 40 ms').toBeGreaterThan(40);
  expect(report.maxGapMs, 'an overlay open may show a sampling gap of up to 70 ms').toBeLessThanOrEqual(70);
});

test('HC-UIG-007 (f) the same ~55 ms block with no kind (an interaction) still fails the 40 ms bound', async ({
  page,
}) => {
  await serveFixture(page, fixtureHtml(BODY, blockOnceAfterStart(55)));
  const error = await stillnessProbe(page, {
    trigger: startFixture(page),
    expected: ['[data-t0]'],
  }).then(
    () => null,
    (caught: unknown) => caught
  );
  console.log(`HC-UIG-007 (f) rejected with: ${String(error)}`);
  expect(error, 'the probe must reject a 55 ms block on an interaction').not.toBeNull();
  expect(String(error), 'the rejection must name a sampling gap').toMatch(/sampling gap of \d+ ms/);
  const gap = Number(/sampling gap of (\d+) ms/.exec(String(error))?.[1]);
  expect(gap, 'the named gap must be above 40 ms').toBeGreaterThan(40);
  expect(String(error), 'the interaction bound of 40 ms must be the one named').toMatch(/must be <= 40 ms/);
});

test('HC-UIG-007 (g) a ~75 ms block during an overlay open is a sampling gap above 70 ms', async ({ page }) => {
  await serveFixture(page, fixtureHtml(BODY, blockOnceAfterStart(75)));
  const error = await stillnessProbe(page, {
    kind: 'overlay',
    trigger: startFixture(page),
    expected: ['[data-t0]'],
  }).then(
    () => null,
    (caught: unknown) => caught
  );
  console.log(`HC-UIG-007 (g) rejected with: ${String(error)}`);
  expect(error, 'the probe must reject a 75 ms block during an overlay open').not.toBeNull();
  expect(String(error), 'the rejection must name a sampling gap').toMatch(/sampling gap of \d+ ms/);
  const gap = Number(/sampling gap of (\d+) ms/.exec(String(error))?.[1]);
  expect(gap, 'the named gap must be above 70 ms').toBeGreaterThan(70);
  expect(String(error), 'the overlay bound of 70 ms must be the one named').toMatch(
    /must be <= 70 ms for an overlay open/
  );
});

// ---------------------------------------------------------------------------
// HC-UIG-011: a hidden Tabs content panel (G10-HIDDEN-TABPANEL, #535 ruling 6714563477).
//
// The panel markup is the Radix TabsContent DOM that /settings renders, captured from the running page
// (@radix-ui/react-tabs 1.2.1, SettingsPage.tsx passing hidden={!active}). Desktop and phone differ only in
// the role and the label:
//   desktop  <div data-state="active" data-orientation="horizontal" role="tabpanel"
//                 aria-labelledby="radix-:rn:-trigger-security" id="radix-:rn:-content-security"
//                 tabindex="-1" class="mt-4 rounded-xl ..." style="animation-duration: 0s;">
//   phone    <div data-state="active" data-orientation="horizontal" role="region"
//                 id="radix-:rn:-content-security" tabindex="-1" class="rounded-xl ... mt-6"
//                 aria-label="Profile &amp; security" style="animation-duration: 0s;">
//   after a tab switch the Security panel keeps its id and gains: data-state="inactive" hidden="" style="".
// The probe matches on [data-orientation][id*="-content-"][data-state] and then reads `hidden`.
// ---------------------------------------------------------------------------

type Layout = 'desktop' | 'phone';
const LAYOUTS: Layout[] = ['desktop', 'phone'];
const PANEL_FOCUS = 'rounded-xl focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2';

function tabsPanel(layout: Layout, value: string, label: string, inner: string, hidden = false): string {
  const state = hidden ? 'inactive' : 'active';
  const attrs =
    layout === 'desktop'
      ? `role="tabpanel" aria-labelledby="radix-:r1:-trigger-${value}"`
      : `role="region" aria-label="${label}"`;
  const cls = layout === 'desktop' ? `mt-4 ${PANEL_FOCUS}` : `${PANEL_FOCUS} mt-6`;
  return (
    `<div data-state="${state}" data-orientation="horizontal" ${attrs} id="radix-:r1:-content-${value}" ` +
    `tabindex="-1" class="${cls}"${hidden ? ' hidden' : ' style="animation-duration: 0s;"'}>${inner}</div>`
  );
}

// What SettingsPage does on a switch: the old panel gets data-state="inactive" and hidden, and the new panel
// mounts (an unmounted panel is not in the DOM at all).
const TABS_SCRIPT = `
  window.__hide = function (panel) {
    panel.setAttribute('data-state', 'inactive');
    panel.hidden = true;
    panel.style.animationDuration = '';
  };
  window.__show = function (panel) {
    panel.setAttribute('data-state', 'active');
    panel.hidden = false;
  };
`;

const HELD = '<p data-t0 id="held" style="margin:0;height:40px">Recovery code held</p>';
const ALERT = '<p data-t0 id="alert" style="margin:0">Assistant alert</p>';

const probeFixture = (page: Page, expected: string[]) =>
  stillnessProbe(page, { trigger: startFixture(page), expected }).then(
    (report) => ({ report, error: null as unknown }),
    (error: unknown) => ({ report: null, error })
  );

for (const layout of LAYOUTS) {
  test(`HC-UIG-011 (a) ${layout}: a node in a Tabs panel that gets hidden after the trigger passes`, async ({ page }) => {
    const script = `${TABS_SCRIPT}
      window.__start = function () {
        window.__hide(document.getElementById('radix-:r1:-content-security'));
        var next = document.createElement('div');
        next.innerHTML = ${JSON.stringify(tabsPanel(layout, 'assistant-privacy', 'Assistant &amp; privacy', ALERT))};
        document.body.appendChild(next.firstChild);
      };`;
    await page.setViewportSize(layout === 'phone' ? { width: 390, height: 844 } : { width: 1440, height: 900 });
    await serveFixture(page, fixtureHtml(tabsPanel(layout, 'security', 'Profile &amp; security', HELD), script));
    const { report, error } = await probeFixture(page, ['#alert']);
    console.log(`HC-UIG-011 (a) ${layout}: ${error ? `rejected with ${String(error)}` : JSON.stringify(report)}`);
    expect(error, 'a node in a hidden Tabs panel is gone, not moved').toBeNull();
    expect(report?.nodes, 'only the visible panel node is left in the last sample').toBe(1);
  });

  test(`HC-UIG-011 (c) ${layout}: a node in a visible Tabs panel that collapses to 0 height still fails`, async ({ page }) => {
    const script = `${TABS_SCRIPT}
      window.__start = function () {
        var held = document.getElementById('held');
        held.style.height = '0px';
        held.style.overflow = 'hidden';
      };`;
    await page.setViewportSize(layout === 'phone' ? { width: 390, height: 844 } : { width: 1440, height: 900 });
    await serveFixture(page, fixtureHtml(tabsPanel(layout, 'security', 'Profile &amp; security', HELD), script));
    const { error } = await probeFixture(page, ['#held']);
    console.log(`HC-UIG-011 (c) ${layout}: rejected with ${String(error)}`);
    expect(error, 'a collapse in a visible panel must be rejected').not.toBeNull();
    expect(String(error)).toMatch(/getBoundingClientRect changed on \[data-t0\] p "Recovery code held"/);
  });

  test(`HC-UIG-011 (d) ${layout}: a node hidden with its panel for part of the window and back moved still fails`, async ({
    page,
  }) => {
    const script = `${TABS_SCRIPT}
      window.__start = function () {
        var panel = document.getElementById('radix-:r1:-content-security');
        window.__hide(panel);
        setTimeout(function () {
          window.__show(panel);
          document.getElementById('held').style.marginTop = '24px';
        }, 250);
      };`;
    await page.setViewportSize(layout === 'phone' ? { width: 390, height: 844 } : { width: 1440, height: 900 });
    await serveFixture(page, fixtureHtml(tabsPanel(layout, 'security', 'Profile &amp; security', HELD), script));
    const { error } = await probeFixture(page, ['#held']);
    console.log(`HC-UIG-011 (d) ${layout}: rejected with ${String(error)}`);
    expect(error, 'a node that returns moved is not excused by the time it was hidden').not.toBeNull();
    // The failure is the move on return ([0,0,w,40] -> [0,24,w,40]), not the hidden samples before it.
    expect(String(error)).toMatch(/getBoundingClientRect changed on \[data-t0\] p "Recovery code held": \[0,0,\d+,40\] -> \[0,24,\d+,40\]/);
  });
}

test('HC-UIG-011 (b) a node hidden by display:none on a plain ancestor (not a Tabs panel) still fails', async ({ page }) => {
  const script = `
    window.__start = function () { document.getElementById('plain').style.display = 'none'; };`;
  const body = `<div id="plain" class="mt-4">${HELD}</div>`;
  await serveFixture(page, fixtureHtml(body, script));
  const { error } = await probeFixture(page, ['#held']);
  console.log(`HC-UIG-011 (b) display:none: rejected with ${String(error)}`);
  expect(error, 'display:none on a plain div is not a hidden Tabs panel').not.toBeNull();
  expect(String(error)).toMatch(/getBoundingClientRect changed on \[data-t0\] p "Recovery code held": .*\[0,0,0,0\]/);
});

test('HC-UIG-011 (b2) a node under a plain ancestor with the hidden attribute still fails', async ({ page }) => {
  const script = `
    window.__start = function () { document.getElementById('plain').hidden = true; };`;
  const body = `<div id="plain" class="mt-4">${HELD}</div>`;
  await serveFixture(page, fixtureHtml(body, script));
  const { error } = await probeFixture(page, ['#held']);
  console.log(`HC-UIG-011 (b2) hidden attribute: rejected with ${String(error)}`);
  expect(error, '[hidden] on a plain div is not a hidden Tabs panel').not.toBeNull();
  expect(String(error)).toMatch(/getBoundingClientRect changed on \[data-t0\] p "Recovery code held": .*\[0,0,0,0\]/);
});
