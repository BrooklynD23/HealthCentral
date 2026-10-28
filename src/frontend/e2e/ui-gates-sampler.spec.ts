/**
 * UI-GATES sampler timing self-tests (HC-UIG-007).
 *
 * The stillness sampler stamps each sample when it reads the page. A page that
 * blocks inside one of the sampler's own reads (here a wrapped
 * getBoundingClientRect, which every tick calls once per [data-t0] node) must
 * show that block as a sampling gap. A 30 ms block stays within the 40 ms bound.
 * A 60 ms block must be rejected, and the message must name the gap.
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
