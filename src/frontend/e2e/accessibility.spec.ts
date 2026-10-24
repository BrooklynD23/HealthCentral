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
function known(rule: string, fixBy: KnownA11y['fixBy'], note: string, selectors: string[]): KnownA11y[] {
  return selectors.map((selector) => ({ rule, selector, fixBy, note }));
}

const KNOWN_A11Y: Record<Route, KnownA11y[]> = {
  '/setup': [
    ...known("color-contrast", "UI-TOKENS", "serious: contrast below WCAG AA; removed by UI-TOKENS", [
      ".text-xs",
    ]),
  ],
  '/inbox': [
    ...known("color-contrast", "UI-TOKENS", "serious: contrast below WCAG AA; removed by UI-TOKENS", [
      ".text-accent > span",
      ".bg-status-verified-subtle > span:nth-child(2)",
      ".px-1\\.5",
    ]),
  ],
  '/verify': [
    ...known("color-contrast", "UI-TOKENS", "serious: contrast below WCAG AA; removed by UI-TOKENS", [
      ".text-accent > span",
      ".bg-status-verified-subtle > span:nth-child(2)",
      ".px-1\\.5",
    ]),
  ],
  '/trends': [
    ...known("color-contrast", "UI-TOKENS", "serious: contrast below WCAG AA; removed by UI-TOKENS", [
      ".text-accent > span",
      ".bg-status-verified-subtle > span:nth-child(2)",
      ".px-1\\.5",
    ]),
  ],
  '/explain': [
    ...known("color-contrast", "UI-TOKENS", "serious: contrast below WCAG AA; removed by UI-TOKENS", [
      "a[aria-current=\"page\"] > span",
      ".bg-status-verified-subtle > span:nth-child(2)",
      ".px-1\\.5",
      ".truncate",
      ".gap-1",
      "div:nth-child(1) > .gap-2.items-center.flex > .text-ink-tertiary",
      ".text-center.py-2.text-ink-tertiary",
    ]),
    ...known("label", "A11Y-CRIT-LABELS", "critical: date input has no accessible name; removed by A11Y-CRIT-LABELS", [
      "input[type=\"date\"]:nth-child(1)",
      "input[type=\"date\"]:nth-child(3)",
    ]),
  ],
  '/settings': [
    ...known("color-contrast", "UI-TOKENS", "serious: contrast below WCAG AA; removed by UI-TOKENS", [
      ".z-10.relative:nth-child(3)",
      ".border-status-verified\\/20 > span:nth-child(2)",
      ".px-1\\.5",
      ".border-accent\\/20.bg-accent-subtle[role=\"switch\"] > .text-accent",
      ".space-y-3.p-6 > .border-accent\\/20.bg-accent-subtle.w-full > .text-accent",
      ".space-y-1 > p",
      ".list-disc > li:nth-child(1)",
      ".list-disc > li:nth-child(2)",
      ".py-2\\.5.justify-between.px-3:nth-child(2) > .min-w-0 > .truncate.text-ink-tertiary.text-xs",
      ".bg-status-attention-subtle.text-status-attention.capitalize",
      ".py-2\\.5.justify-between.px-3:nth-child(3) > .min-w-0 > .truncate.text-ink-tertiary.text-xs",
      ".py-2\\.5.justify-between.px-3:nth-child(3) > .shrink-0.gap-2.flex > .bg-status-verified-subtle.text-status-verified.capitalize",
      ".py-2\\.5.justify-between.px-3:nth-child(4) > .min-w-0 > .truncate.text-ink-tertiary.text-xs",
      ".py-2\\.5.justify-between.px-3:nth-child(4) > .shrink-0.gap-2.flex > .bg-status-caution-subtle.text-status-caution.capitalize",
      ".py-2\\.5.justify-between.px-3:nth-child(5) > .min-w-0 > .truncate.text-ink-tertiary.text-xs",
      ".py-2\\.5.justify-between.px-3:nth-child(5) > .shrink-0.gap-2.flex > .bg-status-verified-subtle.text-status-verified.capitalize",
      ".py-2\\.5.justify-between.px-3:nth-child(6) > .min-w-0 > .truncate.text-ink-tertiary.text-xs",
      ".py-2\\.5.justify-between.px-3:nth-child(6) > .shrink-0.gap-2.flex > .bg-status-caution-subtle.text-status-caution.capitalize",
      ".py-2\\.5.justify-between.px-3:nth-child(7) > .min-w-0 > .truncate.text-ink-tertiary.text-xs",
      ".py-2\\.5.justify-between.px-3:nth-child(7) > .shrink-0.gap-2.flex > .bg-status-verified-subtle.text-status-verified.capitalize",
      ".py-2\\.5.justify-between.px-3:nth-child(8) > .min-w-0 > .truncate.text-ink-tertiary.text-xs",
      ".py-2\\.5.justify-between.px-3:nth-child(8) > .shrink-0.gap-2.flex > .bg-status-caution-subtle.text-status-caution.capitalize",
      ".p-4.border-black\\/2.bg-surface-muted:nth-child(1) > .mb-1.uppercase.tracking-wider",
      ".p-4.border-black\\/2.bg-surface-muted:nth-child(2) > .mb-1.uppercase.tracking-wider",
      ".truncate.text-ink-tertiary.text-\\[10px\\]",
      ".p-4.border-black\\/2.bg-surface-muted:nth-child(3) > .mb-1.uppercase.tracking-wider",
      ".p-4.border-black\\/2.bg-surface-muted:nth-child(4) > .mb-1.uppercase.tracking-wider",
      ".mb-1.uppercase.text-accent",
      ".text-lg.text-accent.capitalize",
      "div[data-testid=\"tier-row-high\"] > .gap-2.flex.items-center > .opacity-50.gap-1\\.5.px-2\\.5",
      "div[data-testid=\"tier-row-gemma4-12b\"] > .gap-3.flex.items-center > div:nth-child(2) > .mt-2.flex-wrap.gap-1\\.5 > .bg-status-info-subtle.text-status-info.gap-1",
      "div[data-testid=\"tier-row-gemma4-12b\"] > .gap-3.flex.items-center > div:nth-child(2) > .mt-2.flex-wrap.gap-1\\.5 > .bg-status-verified-subtle.text-status-verified.gap-1",
      "div[data-testid=\"tier-row-gemma4-12b\"] > .gap-2.flex.items-center > .opacity-50.gap-1\\.5.px-2\\.5",
      "div[data-testid=\"tier-row-mid\"] > .gap-2.flex.items-center > .opacity-50.gap-1\\.5.px-2\\.5",
      ".text-\\[9px\\]",
      "div[data-testid=\"tier-row-gemma4-e4b\"] > .gap-3.flex.items-center > div:nth-child(2) > .mt-2.flex-wrap.gap-1\\.5 > .bg-status-info-subtle.text-status-info.gap-1",
      "div[data-testid=\"tier-row-gemma4-e4b\"] > .gap-3.flex.items-center > div:nth-child(2) > .mt-2.flex-wrap.gap-1\\.5 > .bg-status-verified-subtle.text-status-verified.gap-1",
      "div[data-testid=\"tier-row-gemma4-e2b\"] > .gap-3.flex.items-center > div:nth-child(2) > .mt-2.flex-wrap.gap-1\\.5 > .bg-status-info-subtle.text-status-info.gap-1",
      "div[data-testid=\"tier-row-gemma4-e2b\"] > .gap-3.flex.items-center > div:nth-child(2) > .mt-2.flex-wrap.gap-1\\.5 > .bg-status-verified-subtle.text-status-verified.gap-1",
      ".gap-2.flex.items-center > .bg-status-verified-subtle.text-status-verified.gap-1",
      ".border-black\\/2.py-2\\.5.justify-between:nth-child(1) > .bg-status-verified-subtle.text-status-verified.capitalize",
      ".bg-status-attention-subtle.text-status-attention.font-bold",
      ".leading-relaxed.text-ink-tertiary.text-xs",
      ".leading-relaxed.text-center.text-ink-tertiary",
      ".space-y-4.pt-0.p-6 > .text-ink-tertiary.text-xs",
      ".text-base.tracking-tight > .bg-status-verified-subtle.text-status-verified.gap-1\\.5",
      "p[data-testid=\"recovery-code-replace-warning\"]",
      ".text-status-attention.text-xl.tracking-tight",
    ]),
    ...known("select-name", "A11Y-CRIT-LABELS", "critical: select has no accessible name; removed by A11Y-CRIT-LABELS", [
      "select",
    ]),
  ],
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
