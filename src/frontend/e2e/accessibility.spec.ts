/**
 * Accessibility (axe-core) E2E scan, AXE-E2E.
 *
 * One test per route. Fails on any WCAG 2 A/AA violation of impact
 * `critical` or `serious` unless its rule id is listed in KNOWN_A11Y for that
 * route. Every KNOWN_A11Y entry names the bullet that will fix it. Entries may
 * only be removed; adding one needs a queue row.
 */

import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { openAuthenticatedPage } from './support/auth';

const ROUTES = ['/setup', '/inbox', '/verify', '/trends', '/explain', '/settings'] as const;
type Route = (typeof ROUTES)[number];

interface KnownA11y {
  rule: string;
  fixBy: 'FE-A11Y-DIALOGS';
  note: string;
}

const KNOWN_A11Y: Record<Route, KnownA11y[]> = {
  '/setup': [],
  '/inbox': [],
  '/verify': [],
  '/trends': [],
  '/explain': [],
  '/settings': [],
};

// Content that proves the page rendered (not a loading skeleton).
// /explain has no heading, so it waits on the layout's <main> plus network idle.
async function waitForMainContent(page: Page, route: Route): Promise<void> {
  if (route === '/explain') {
    await expect(page.locator('main')).toBeVisible({ timeout: 15000 });
  } else {
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 15000 });
  }
  await page.waitForLoadState('networkidle');
}

for (const route of ROUTES) {
  test(`E2E-A11Y: ${route} has no unexpected critical/serious axe violations`, async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, route);
    await waitForMainContent(page, route);

    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();

    const known = new Set(KNOWN_A11Y[route].map((entry) => entry.rule));
    const blocking = results.violations.filter(
      (v) => (v.impact === 'critical' || v.impact === 'serious') && !known.has(v.id)
    );

    const report = blocking
      .map(
        (v) =>
          `${v.id} (${v.impact}): ${v.help}\n` +
          v.nodes.map((n) => `    ${n.target.join(' ')}`).join('\n')
      )
      .join('\n');

    expect(blocking, `Unexpected axe violations on ${route}:\n${report}`).toEqual([]);
  });
}
