/**
 * Accessibility (axe-core) E2E scan, AXE-E2E.
 *
 * One test per route. Fails on any WCAG 2 A/AA violation of impact `critical`
 * or `serious` unless its rule id + route + selector is listed in KNOWN_A11Y.
 * Every entry names the row that removes it. Entries may only be removed;
 * adding one needs an L0 ruling. A listed entry that matches nothing also
 * fails (stale), so the list can only shrink.
 */

import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { openAuthenticatedPage } from './support/auth';

const ROUTES = ['/setup', '/inbox', '/verify', '/trends', '/explain', '/settings'] as const;
type Route = (typeof ROUTES)[number];

interface KnownA11y {
  rule: string;
  selector: string;
  fixBy: 'UI-TOKENS' | 'UI-SHELL';
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

const IMPACTS = new Set(['critical', 'serious']);

/**
 * The single place where axe results are matched against KNOWN_A11Y.
 * Entries match on rule id + route + selector (`node.target.join(' ')`).
 * blocking: critical/serious nodes with no entry. stale: entries with no node.
 */
function classify(
  route: Route,
  violations: AxeViolation[],
  known: Record<Route, KnownA11y[]>
): Classified {
  const entries = known[route];
  const seen = new Set<string>();
  const blocking: Blocking[] = [];
  for (const v of violations) {
    if (!v.impact || !IMPACTS.has(v.impact)) continue;
    for (const node of v.nodes) {
      const selector = node.target.join(' ');
      seen.add(`${v.id}\u0000${selector}`);
      if (!entries.some((e) => e.rule === v.id && e.selector === selector)) {
        blocking.push({ rule: v.id, impact: v.impact, selector, help: v.help });
      }
    }
  }
  const stale = entries.filter((e) => !seen.has(`${e.rule}\u0000${e.selector}`));
  return { blocking, stale };
}

function report(route: Route, { blocking, stale }: Classified): string {
  const lines = blocking.map((b) => `  NEW ${b.rule} (${b.impact}): ${b.selector}  [${b.help}]`);
  lines.push(
    ...stale.map((e) => `  STALE ${e.rule}: ${e.selector}  (fixed by ${e.fixBy}; delete this entry)`)
  );
  return `axe allow-list mismatch on ${route}:\n${lines.join('\n')}`;
}

/**
 * Measured on CI run 40068287285 (E2E Smoke Tests, head fa0a9e5) and nothing
 * else. Keyed by rule + route + selector; never rule-wide or route-wide. The
 * list may only shrink: an entry that matches nothing fails the route test.
 */

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
  // A fade-in still running makes axe measure blended colours (transient
  // color-contrast nodes seen on /setup, run 40068287285 attempt 3).
  await page.waitForFunction(() => document.getAnimations().length === 0, undefined, {
    timeout: 5000,
  });
}

// globals.css collapses CSS animation/transition durations under this media query.
// (reducedMotion is a context option, not a test option, in Playwright 1.58.)
test.use({ contextOptions: { reducedMotion: 'reduce' } });

for (const route of ROUTES) {
  test(`E2E-A11Y: ${route} has no unexpected critical/serious axe violations`, async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, route);
    await waitForMainContent(page, route);
    expect(
      await page.evaluate(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches),
      'reduced motion must be active for the scan'
    ).toBe(true);

    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();

    const result = classify(route, results.violations, KNOWN_A11Y);
    const message = report(route, result);

    expect(result.blocking, message).toEqual([]);
    expect(result.stale, message).toEqual([]);
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
