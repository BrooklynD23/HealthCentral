/**
 * UI-TOKENS end-to-end checks (HC-UITK-004 .. 006).
 *
 * - HC-UITK-004: axe `color-contrast` is zero on the six scanned routes, light
 *   theme. The routes run against the real backend, as in accessibility.spec.ts,
 *   because /verify, /explain and /settings render their contrast-bearing data
 *   only from real responses; the mock API answers four endpoints and nothing else.
 * - HC-UITK-005: the focus ring stays a box-shadow in the accent token, the
 *   nav link keeps no outline (TW4-FOCUS and TW4-INBOX, pinned here), and a
 *   shimmer loader keeps breathing under reduced motion (plan §2.6 M12).
 * - HC-UITK-006: cold-load CLS on /setup is at most 0.02 (measured with the
 *   mock API, which answers the page's only profile request).
 */
import { expect, test, type Page } from '@playwright/test';
import { axeGate, measureCls } from './support/gates';
import { installMockApi } from './support/mockApi';
import { openAuthenticatedPage } from './support/auth';

const CONTRAST_ROUTES = ['/setup', '/inbox', '/verify', '/trends', '/explain', '/settings'] as const;
/** The plan's CLS budget for a cold load of /setup (G2). */
const CLS_BUDGET = 0.02;
/**
 * L0 ruling 1 (PR #356, 2026-10-24): the TopBar safety-mode "ON" badge (`.px-1\.5`)
 * fails contrast at 4.44:1 and is reassigned from UI-TOKENS to UI-SHELL §3.6, which
 * replaces the TopBar. The badge renders in the TopBar on these five routes only.
 */
const TOPBAR_BADGE_ROUTES: ReadonlySet<string> = new Set(['/inbox', '/verify', '/trends', '/explain', '/settings']);
/**
 * Axe names the badge by one of these selectors, and the one it picks depends on the run: `.px-1\.5` on
 * four routes, `.text-\[10px\]` on /trends (same element). Only a node with one of these selectors can be
 * excluded, and each excluded node must still be the badge: a bare span with its ON/OFF text.
 */
const TOPBAR_BADGE_SELECTORS: ReadonlySet<string> = new Set(['.px-1\\.5', '.text-\\[10px\\]']);
const TOPBAR_BADGE_HTML = /^<span\b[^>]*\bpx-1\.5\b[^>]*>(ON|OFF)<\/span>$/;

/** Waits until no finite animation runs. Infinite loaders (spinners, pulses) are ignored. */
async function settleFiniteAnimations(page: Page): Promise<void> {
  await page.waitForFunction(
    () =>
      document.getAnimations().every((animation) => {
        const iterations = animation.effect?.getComputedTiming().iterations;
        return iterations === Infinity || animation.playState !== 'running';
      }),
    undefined,
    { timeout: 5000 }
  );
}

// The contrast scan runs with reduced motion, as accessibility.spec.ts does.
test.describe('UI-TOKENS contrast on scanned routes', () => {
  test.use({ contextOptions: { reducedMotion: 'reduce' } });

  for (const route of CONTRAST_ROUTES) {
    test(`HC-UITK-004: ${route} has no color-contrast violation in the light theme`, async ({
      page,
      request,
    }) => {
      await openAuthenticatedPage(page, request, route);
      await page.waitForLoadState('networkidle');
      await settleFiniteAnimations(page);

      const result = await axeGate(page, { theme: 'light' });
      const allNodes = result.violations
        .filter((violation) => violation.id === 'color-contrast')
        .flatMap((violation) =>
          violation.nodes.map((node) => ({ selector: node.target.join(' '), html: node.html }))
        );
      console.log(
        `HC-UITK-004 ${route} color-contrast nodes (unfiltered): ${JSON.stringify(allNodes.map((node) => node.selector))}`
      );
      // Only the TopBar badge is excluded, and only on the TopBar routes (L0 ruling 1).
      // Every node with a badge selector must be that badge, so a different element with one of these
      // selectors fails here rather than being excluded.
      const badge = TOPBAR_BADGE_ROUTES.has(route)
        ? allNodes.filter((node) => TOPBAR_BADGE_SELECTORS.has(node.selector))
        : [];
      for (const node of badge) {
        expect(node.html, `excluded ${node.selector} node on ${route} is the TopBar badge`).toMatch(
          TOPBAR_BADGE_HTML
        );
      }
      const nodes = allNodes.filter((node) => !badge.includes(node)).map((node) => node.selector);
      console.log(`HC-UITK-004 ${route} color-contrast nodes (filtered): ${JSON.stringify(nodes)}`);
      expect(nodes, `color-contrast nodes on ${route}`).toEqual([]);
    });
  }
});

test('HC-UITK-005: the focus ring is a box-shadow in the accent token (TW4-FOCUS)', async ({ page }) => {
  await page.goto('/recover');
  const input = page.locator('#recover-code');
  await expect(input).toBeVisible({ timeout: 15000 });
  for (let i = 0; i < 40 && !(await input.evaluate((el) => el === document.activeElement)); i++) {
    await page.keyboard.press('Tab');
  }
  await expect(input).toBeFocused();
  const shadow = await input.evaluate((el) => getComputedStyle(el).boxShadow);
  expect(shadow).not.toBe('none');
  // The accent token as the browser computes it, so the pin holds whatever the accent is.
  const accent = await page.evaluate(() => {
    const probe = document.createElement('span');
    probe.style.color = 'var(--color-accent)';
    document.body.appendChild(probe);
    const computed = getComputedStyle(probe).color;
    probe.remove();
    return computed;
  });
  expect(shadow, 'focus ring uses the accent token').toContain(accent);
});

test('HC-UITK-005: the focused nav link has no outline; its ring is the global box-shadow (TW4-INBOX)', async ({
  page,
  request,
}) => {
  await openAuthenticatedPage(page, request, '/inbox');
  const nav = page.getByRole('navigation', { name: /main navigation/i }).getByRole('link').first();
  await expect(nav).toBeVisible({ timeout: 15000 });
  for (let i = 0; i < 40 && !(await nav.evaluate((el) => el === document.activeElement)); i++) {
    await page.keyboard.press('Tab');
  }
  await expect(nav).toBeFocused();
  const outline = await nav.evaluate((el) => {
    const style = getComputedStyle(el);
    return { outlineStyle: style.outlineStyle, outlineColor: style.outlineColor };
  });
  expect(outline.outlineStyle === 'none' || outline.outlineColor === 'rgba(0, 0, 0, 0)').toBeTruthy();
  await nav.blur();
});

// Plan §2.6 M12: loaders keep breathing under reduced motion. The fallback names pulseSoft, and Tailwind 4
// emits a @theme keyframes block only when a utility uses it, so pulseSoft must sit outside @theme.
test.describe('HC-UITK-005: reduced motion keeps the loaders breathing (M12)', () => {
  test.use({ contextOptions: { reducedMotion: 'reduce' } });

  test('HC-UITK-005: a shimmer loader and the typing dots still run pulseSoft, infinitely, under reduced motion', async ({
    page,
  }) => {
    await page.goto('/recover');
    await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
    const running = await page.evaluate(() => {
      const probeAnimations = (tag: string, className: string) => {
        const probe = document.createElement(tag);
        probe.className = className;
        document.body.appendChild(probe);
        const animations = probe.getAnimations().map((animation) => ({
          name: (animation as CSSAnimation).animationName,
          infinite: animation.effect?.getComputedTiming().iterations === Infinity,
        }));
        probe.remove();
        return animations;
      };
      return {
        shimmer: probeAnimations('div', 'animate-shimmer'),
        // The typing dots in ExplainAssistant.tsx are spans with animate-bounce (plan §2.6 M12, G5).
        typingDots: probeAnimations('span', 'animate-bounce'),
      };
    });
    expect(running.shimmer, 'the reduced-motion shimmer runs pulseSoft as a loop').toEqual([
      { name: 'pulseSoft', infinite: true },
    ]);
    expect(running.typingDots, 'the reduced-motion typing dots run pulseSoft as a loop, not bounce').toEqual([
      { name: 'pulseSoft', infinite: true },
    ]);
  });
});

// HC-UITK-006 is a pin, not a check of the fallback font metrics: CLS is 0 on origin/main without the
// @font-face overrides too, so a wrong override cannot turn this red.
test('HC-UITK-006: cold-load CLS on /setup is at most 0.02', async ({ page }) => {
  const mock = await installMockApi(page);
  const cls = await measureCls(page, async () => {
    await page.goto('/setup');
    await page.waitForLoadState('networkidle');
  });
  console.log(`HC-UITK-006 cold-load CLS on /setup: ${cls} (unmocked: ${JSON.stringify(mock.unmocked)})`);
  expect(mock.unmocked, 'the setup page must not reach an unmocked API').toEqual([]);
  expect(cls, 'CLS on a cold load of /setup').toBeLessThanOrEqual(CLS_BUDGET);
});
