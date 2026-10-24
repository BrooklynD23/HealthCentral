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
  selector: string;
  fixBy: 'UI-TOKENS' | 'A11Y-CRIT-LABELS';
  note: string;
}

interface AxeNode {
  target: unknown[];
}
interface AxeViolation {
  id: string;
  impact?: string | null;
  help: string;
  nodes: AxeNode[];
}
interface Blocking {
  rule: string;
  impact: string;
  selector: string;
  help: string;
}
interface Classified {
  blocking: Blocking[];
  stale: KnownA11y[];
}

// STUB (RED): real matching lands in the next commit.
function classify(
  _route: Route,
  _violations: AxeViolation[],
  _known: Record<Route, KnownA11y[]>
): Classified {
  return { blocking: [], stale: [] };
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

const EMPTY_KNOWN: Record<Route, KnownA11y[]> = {
  '/setup': [],
  '/inbox': [],
  '/verify': [],
  '/trends': [],
  '/explain': [],
  '/settings': [],
};

test.describe('E2E-A11Y self-tests: allow-list matching', () => {
  const entry = (rule: string, selector: string): KnownA11y => ({
    rule,
    selector,
    fixBy: 'UI-TOKENS',
    note: 'synthetic',
  });
  const violation = (id: string, impact: string, selectors: string[][]): AxeViolation => ({
    id,
    impact,
    help: `help for ${id}`,
    nodes: selectors.map((target) => ({ target })),
  });

  test('E2E-A11Y-SELF-001: listed rule+route+selector passes, unlisted selector of a listed rule blocks', () => {
    const known = { ...EMPTY_KNOWN, '/inbox': [entry('color-contrast', '.a')] };
    const { blocking, stale } = classify(
      '/inbox',
      [violation('color-contrast', 'serious', [['.a'], ['.b']])],
      known
    );
    expect(blocking.map((b) => b.selector)).toEqual(['.b']);
    expect(stale).toEqual([]);
  });

  test('E2E-A11Y-SELF-002: a listed rule on an unlisted route blocks', () => {
    const known = { ...EMPTY_KNOWN, '/inbox': [entry('color-contrast', '.a')] };
    const { blocking } = classify(
      '/verify',
      [violation('color-contrast', 'serious', [['.a']])],
      known
    );
    expect(blocking.map((b) => b.selector)).toEqual(['.a']);
  });

  test('E2E-A11Y-SELF-003: an entry matching nothing is stale', () => {
    const known = {
      ...EMPTY_KNOWN,
      '/inbox': [entry('color-contrast', '.a'), entry('color-contrast', '.gone')],
    };
    const { blocking, stale } = classify(
      '/inbox',
      [violation('color-contrast', 'serious', [['.a']])],
      known
    );
    expect(blocking).toEqual([]);
    expect(stale.map((e) => e.selector)).toEqual(['.gone']);
  });

  test('E2E-A11Y-SELF-004: minor/moderate impact is ignored; multi-part targets join with a space', () => {
    const known = { ...EMPTY_KNOWN, '/inbox': [entry('label', 'iframe input')] };
    const { blocking, stale } = classify(
      '/inbox',
      [
        violation('label', 'critical', [['iframe', 'input']]),
        violation('region', 'moderate', [['.x']]),
      ],
      known
    );
    expect(blocking).toEqual([]);
    expect(stale).toEqual([]);
  });

  test('E2E-A11Y-SELF-005: a real axe scan of a page with an unnamed <select> is blocking', async ({
    page,
  }) => {
    await page.setContent('<!doctype html><html lang="en"><body><main><select><option>a</option></select></main></body></html>');
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    const { blocking } = classify('/settings', results.violations, EMPTY_KNOWN);
    expect(blocking.map((b) => b.rule)).toContain('select-name');
  });
});
