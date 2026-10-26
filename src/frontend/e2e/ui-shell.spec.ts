/**
 * UI-SHELL (HC-UISH-002 .. HC-UISH-009), plus the Playwright halves of the
 * checks the L0 rulings moved here: HC-UIOV-007 (stillness of a still overlay),
 * HC-UIFB-006 (a still toast) and HC-UIPC-007 (focus ring 16 ms after Tab).
 * Gate G (G1, G2, G6, G7, G9) runs on every route the shell renders.
 *
 * Runs on the dev server with the mock API (no backend): the recipe is
 * PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-shell.spec.ts --project=chromium
 *
 * Routes: the 14 authenticated routes in App.tsx plus /setup. /recover is
 * checked for the h1 and skip-link rules only.
 */

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import {
  ROUTE_CONTAINER_SELECTOR,
  ROUTE_FALLBACK_SELECTOR,
  WCAG_TAGS,
  consoleAndNetworkGuard,
  measureCls,
  maxEventDuration,
  noHorizontalScroll,
  reducedMotionSnapshot,
  routeOpacitySamples,
  safetyVisible,
  setTheme,
  stillnessProbe,
  type AxeViolation,
} from './support/gates';
import { installMockApi, seedMockSession } from './support/mockApi';

/** The rule, impact and first three nodes of an axe violation, so a failure names the element. */
function describeViolation(v: { id: string; impact?: string | null; nodes: Array<{ target: string[] }> }): string {
  const nodes = v.nodes.slice(0, 3).map((node) => node.target.join(' ')).join(', ');
  return `${v.id}:${v.impact} at ${nodes}`;
}

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };

/** The 14 authenticated routes (App.tsx) in the order the nav lists them. */
const AUTH_ROUTES = [
  '/inbox',
  '/verify',
  '/trends',
  '/timeline',
  '/search',
  '/interpret',
  '/medications',
  '/medications/med-fixture-1',
  '/notifications',
  '/care-tasks',
  '/pinboards',
  '/explain',
  '/export',
  '/settings',
];
/**
 * The 15 routes of HC-UISH-002 and gate G6/G7. /setup is not a shell route: App.tsx:201 renders it outside
 * AppLayout, so it has no banner, navigation or Safety Rail. The shell checks (G1, G9) use AUTH_ROUTES.
 */
const ALL_ROUTES = [...AUTH_ROUTES, '/setup'];

/** Destination names as navConfig.ts writes them (the nav link for each route, when it has one). */
const NAV_LABEL: Record<string, string> = {
  '/inbox': 'Documents',
  '/verify': 'Review values',
  '/trends': 'Results',
  '/timeline': 'Timeline',
  '/interpret': 'Interpret',
  '/medications': 'Medications',
  '/notifications': 'Reminders',
  '/care-tasks': 'Follow-ups',
  '/pinboards': 'Pinboards',
  '/explain': 'Ask',
  '/export': 'Doctor summary',
};

/** Every destination the More sheet must reach (plan §3.1: the four groups). */
const ALL_DESTINATIONS = [
  'Documents',
  'Review values',
  'Timeline',
  'Pinboards',
  'Results',
  'Interpret',
  'Ask',
  'Medications',
  'Reminders',
  'Follow-ups',
  'Doctor summary',
];

/** The Safety Rail and the toggle copy carry data-t0 (plan §2.7). The probe takes CSS selectors. */
const RAIL = '[data-safety-rail]';
const TOGGLE_POPOVER = '[data-safety-toggle-popover]';
const TOGGLE_NOTE = '[data-safety-toggle-note]';

/** The shell's own regions for the G1 scoped axe run. Page content in [data-route-container] is not one of them. */
const SHELL_REGIONS = ['header', 'nav[aria-label="Main navigation"]', 'nav[aria-label="Tab bar"]', RAIL];
const MORE_SHEET = '[role="dialog"]';
const ROUTE_CONTAINER = '[data-route-container]';

/**
 * G1 on the shell's own nodes only (banner, Main navigation, tab bar, More sheet when open, Safety Rail),
 * serious and critical, in one theme. Page content goes to the page rows (PAGE-A11Y), not this gate.
 */
async function shellAxeBlocking(page: Page, theme: 'light' | 'dark'): Promise<AxeViolation[]> {
  await setTheme(page, theme);
  let builder = new AxeBuilder({ page }).withTags(WCAG_TAGS);
  let included = 0;
  for (const selector of [...SHELL_REGIONS, MORE_SHEET]) {
    // axe throws when an include matches nothing, so only regions that are rendered are included.
    if ((await page.locator(selector).count()) > 0) {
      builder = builder.include(selector);
      included += 1;
    }
  }
  // With no include, axe would analyse the whole document, which is page content, so refuse to run.
  if (included === 0) throw new Error('no shell region is rendered on this route; the scoped axe run would scan the page');
  const results = await builder.exclude(ROUTE_CONTAINER).analyze();
  return results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
}

async function openRoute(page: Page, route: string) {
  const mock = await installMockApi(page);
  await seedMockSession(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  await page.goto(route);
  return { mock, guard };
}

/**
 * Waits until the route element has finished its entrance fade. This is the wait settleRoute in ui-gates.spec.ts
 * uses. It is copied, not imported: importing that spec would register its tests in this file too.
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
      { message: 'the route element must finish its entrance fade before the probe starts', timeout: 10_000 }
    )
    .toBeGreaterThanOrEqual(0.99);
}

/** The navigation landmark that is visible at the current width. */
function visibleNav(page: Page) {
  return page.getByRole('navigation', { name: 'Main navigation' });
}

/** Navigates the way a user does: a nav link, the search form, or the profile menu. */
async function navigateTo(page: Page, route: string): Promise<void> {
  if (route === '/search') {
    await page.getByRole('banner').getByRole('searchbox').fill('migraine');
    await page.keyboard.press('Enter');
    return;
  }
  if (route === '/settings') {
    await page.getByRole('button', { name: 'Profile and settings' }).click();
    await page.getByRole('link', { name: 'Settings', exact: true }).click();
    return;
  }
  if (route === '/medications/med-fixture-1') {
    // No nav item leads here; the detail page is reached from a medication row, which the mock does not list.
    await page.evaluate(() => {
      window.history.pushState({}, '', '/medications/med-fixture-1');
      window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
    });
    return;
  }
  await visibleNav(page).getByRole('link', { name: NAV_LABEL[route], exact: true }).click();
}

/** A route is always reached from a different page, so the click is a real route change. */
function startPageFor(route: string): string {
  return route === '/inbox' ? '/verify' : '/inbox';
}

/** Walks the sampler across one navigation and returns the route container's samples. */
async function sampleRouteContainer(page: Page, route: string) {
  // The start page may still be fetching or rendering its data. That work takes the frames the fade needs: on
  // preview the fade's first frame landed 40-50 ms late on /verify, /interpret, /medications and /search. Measure
  // the fade from a settled start page, as HC-UISH-008 and HC-UIFB-006 do. The 240 ms bound is unchanged.
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => {
    const w = window as unknown as {
      __shellSamples?: Array<{ t: number; key: string | null; opacity: number; transform: string }>;
      __shellTimer?: number;
    };
    w.__shellSamples = [];
    w.__shellTimer = window.setInterval(() => {
      const el = document.querySelector<HTMLElement>('[data-route-container]');
      w.__shellSamples?.push({
        t: performance.now(),
        key: el?.getAttribute('data-route-container') ?? null,
        opacity: el ? parseFloat(getComputedStyle(el).opacity) : NaN,
        transform: el ? getComputedStyle(el).transform : '',
      });
    }, 16);
  });
  await navigateTo(page, route);
  await page.waitForTimeout(900);
  return page.evaluate(() => {
    const w = window as unknown as {
      __shellSamples?: Array<{ t: number; key: string | null; opacity: number; transform: string }>;
      __shellTimer?: number;
    };
    window.clearInterval(w.__shellTimer);
    return w.__shellSamples ?? [];
  });
}

/** HC-UISH-003 rules on the route container, sampled every 16 ms after the click. */
function routeFadeFailures(
  samples: Array<{ t: number; key: string | null; opacity: number; transform: string }>,
  route: string,
  reduced: boolean
): string[] {
  const failures: string[] = [];
  const mounted = samples.filter((s) => s.key === route);
  if (mounted.length === 0) {
    return [`the keyed route container for ${route} never mounted`];
  }
  const t0 = mounted[0].t;
  for (const s of mounted) {
    if (s.transform !== 'none') failures.push(`transform ${s.transform} at ${Math.round(s.t - t0)} ms`);
    if (reduced ? s.opacity !== 1 : s.opacity < 0.35) {
      failures.push(`opacity ${s.opacity} at ${Math.round(s.t - t0)} ms`);
    }
  }
  const settled = mounted.find((s) => s.opacity >= 0.999);
  if (!settled) {
    failures.push('opacity never reached 1');
  } else if (settled.t - t0 > 240) {
    failures.push(`opacity reached 1 after ${Math.round(settled.t - t0)} ms (limit 240)`);
  }
  if (settled) {
    const after = mounted.filter((s) => s.t >= settled.t);
    for (const s of after) {
      if (s.opacity < 0.999) failures.push(`opacity fell back to ${s.opacity} at ${Math.round(s.t - t0)} ms`);
    }
  }
  return failures;
}

// ---------------------------------------------------------------------------
// HC-UISH-002: the skip link is the first tab stop, the shell renders no h1, and no route renders more than one.
// ---------------------------------------------------------------------------
/** The shell's chrome: sidebar, top bar, tab bar and Safety Rail. /setup and /recover have none of it. */
const SHELL_CHROME = 'aside, header, nav, [data-safety-rail]';

test.describe('HC-UISH-002 skip link and h1 rules', () => {
  test.use({ viewport: DESKTOP });

  test('HC-UISH-002: the first Tab focuses the skip link', async ({ page }) => {
    await openRoute(page, '/inbox');
    await expect(page.locator('main')).toBeVisible({ timeout: 15_000 });
    await page.keyboard.press('Tab');
    await expect(page.getByRole('link', { name: /skip to (main )?content/i })).toBeFocused();
  });

  for (const route of [...ALL_ROUTES, '/recover']) {
    test(`HC-UISH-002: the shell renders no h1, and ${route} renders at most one`, async ({ page }) => {
      await openRoute(page, route);
      // /recover renders no h1 and no main, so wait for any rendered content rather than for one of those.
      await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });
      // Count after the page has loaded, so a count taken before the page's own h1 mounts cannot pass for the wrong reason.
      await page.waitForLoadState('networkidle');
      const shellH1 = await page.locator(SHELL_CHROME).getByRole('heading', { level: 1 }).count();
      const routeH1 = (await page.getByRole('heading', { level: 1 }).count()) - shellH1;
      expect(shellH1, 'h1 inside the shell chrome').toBe(0);
      expect(routeH1, 'h1 inside the route content').toBeLessThanOrEqual(1);
    });
  }
});

// ---------------------------------------------------------------------------
// HC-UISH-003 (DF-6): the route container fades opacity-only, in 240 ms, then stays still.
// HC-UISH-009: the Safety Rail keeps opacity 1 and a fixed rect through the same click.
// ---------------------------------------------------------------------------
test.describe('HC-UISH-003 route fade and HC-UISH-009 rail stillness', () => {
  test.use({ viewport: DESKTOP });

  for (const route of AUTH_ROUTES) {
    test(`HC-UISH-003: opacity-only route fade on ${route}`, async ({ page }) => {
      await openRoute(page, startPageFor(route));
      await expect(page.locator('[data-route-container]')).toBeVisible({ timeout: 15_000 });
      const samples = await sampleRouteContainer(page, route);
      expect(routeFadeFailures(samples, route, false)).toEqual([]);
    });

    test(`HC-UISH-003: no fade under reduced motion on ${route}`, async ({ page }) => {
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await openRoute(page, startPageFor(route));
      await expect(page.locator('[data-route-container]')).toBeVisible({ timeout: 15_000 });
      const samples = await sampleRouteContainer(page, route);
      expect(routeFadeFailures(samples, route, true)).toEqual([]);
    });
  }

  // /explain is left out of HC-UISH-009 until UI-PG-ASK lands (L0 ruling 2026-10-25). /settings is left out until
  // UI-PG-SETTINGS lands (L0 ruling 2026-10-26T07:12:53Z): a bare 20 ms timer on /inbox -> /settings reads a max gap
  // of 58-72 ms on this branch (median 60, 5 runs) and 48-55 ms on origin/main (median 49, 5 runs), interleaved on
  // preview, and this case fails 3 of 3 on preview with 60-64 ms gaps.
  for (const route of AUTH_ROUTES.filter((candidate) => candidate !== '/explain' && candidate !== '/settings')) {
    test(`HC-UISH-009: the Safety Rail stays still through the navigation to ${route}`, async ({ page }) => {
      await openRoute(page, startPageFor(route));
      await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
      const report = await stillnessProbe(page, {
        trigger: () => navigateTo(page, route),
        expected: [RAIL, TOGGLE_NOTE],
        kind: 'navigation',
        lazyRoute: true,
      });
      expect(report.nodes).toBeGreaterThan(0);
    });
  }
});

// ---------------------------------------------------------------------------
// HC-UISH-004: at phone widths the sidebar is replaced by a five-tab bar.
// ---------------------------------------------------------------------------
test.describe('HC-UISH-004 phone shell', () => {
  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`HC-UISH-004: no sidebar, main at x=0, five tabs of at least 56 px at ${viewport.width}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openRoute(page, '/inbox');
      await expect(page.locator('main')).toBeVisible({ timeout: 15_000 });

      await expect(page.locator('aside:visible')).toHaveCount(0);
      const main = await page.locator('main').boundingBox();
      expect(main?.x).toBe(0);
      expect(main?.width).toBe(viewport.width);

      const tabBar = page.getByRole('navigation', { name: 'Tab bar' });
      const tabs = tabBar.locator('a, button');
      await expect(tabs).toHaveCount(5);
      const names = await tabs.evaluateAll((els) => els.map((el) => el.textContent?.trim() ?? ''));
      expect(names.map((name) => name.replace(/\s+/g, ' '))).toEqual(
        expect.arrayContaining(['Documents', 'Review values', 'Results', 'Ask', 'More'])
      );
      for (let index = 0; index < 5; index += 1) {
        const box = await tabs.nth(index).boundingBox();
        expect(box?.height ?? 0, `tab ${index} height`).toBeGreaterThanOrEqual(56);
      }
    });
  }
});

// ---------------------------------------------------------------------------
// HC-UISH-005 (DF-1): the Safety Rail is opaque and on top, light and dark, 1440 and 390.
// ---------------------------------------------------------------------------
test.describe('HC-UISH-005 Safety Rail is opaque and on top', () => {
  for (const viewport of [DESKTOP, PHONE]) {
    for (const theme of ['light', 'dark'] as const) {
      test(`HC-UISH-005: opaque, unblurred and hit-testable at ${viewport.width}, ${theme}`, async ({ page }) => {
        await page.setViewportSize(viewport);
        await openRoute(page, '/inbox');
        await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
        await setTheme(page, theme);

        const style = await page.locator(RAIL).evaluate((el) => {
          const cs = getComputedStyle(el);
          return { background: cs.backgroundColor, backdrop: cs.backdropFilter, webkit: cs.webkitBackdropFilter };
        });
        // rgb() has three channels; rgba() carries the alpha as the fourth.
        const channels = style.background.match(/rgba?\(([^)]+)\)/)?.[1].split(',').map((part) => part.trim()) ?? [];
        expect(channels.length === 4 ? Number(channels[3]) : 1).toBe(1);
        expect(style.backdrop).toBe('none');
        expect(style.webkit ?? 'none').toBe('none');

        await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
        await page.waitForTimeout(100);
        const hits = await page.locator(RAIL).evaluate((rail) => {
          const rect = rail.getBoundingClientRect();
          const y = rect.top + rect.height / 2;
          return [0.1, 0.3, 0.5, 0.7, 0.9].map((fraction) => {
            const x = rect.left + rect.width * fraction;
            const hit = document.elementFromPoint(x, y);
            return Boolean(hit && (hit === rail || rail.contains(hit)));
          });
        });
        expect(hits).toEqual([true, true, true, true, true]);
      });
    }
  }
});

// ---------------------------------------------------------------------------
// HC-UISH-006: the relabelled toggle is an honest, disabled switch.
// ---------------------------------------------------------------------------
test.describe('HC-UISH-006 relabelled safety toggle', () => {
  test.use({ viewport: DESKTOP });

  test('HC-UISH-006: no "Safety Mode", ON or OFF in the top bar, and the switch is disabled with its note', async ({
    page,
  }) => {
    await openRoute(page, '/inbox');
    const banner = page.getByRole('banner');
    await expect(banner).toBeVisible({ timeout: 15_000 });
    await expect(banner).not.toContainText(/Safety Mode/);
    await expect(banner).not.toContainText(/\bON\b/);
    await expect(banner).not.toContainText(/\bOFF\b/);

    const toggle = page.getByRole('switch', { name: 'Stricter safety mode' });
    // The switch's row and the note carry no standalone ON or OFF (case-sensitive, so "on" in a sentence still reads).
    await expect(toggle.locator('xpath=..')).not.toContainText(/\b(ON|OFF)\b/);
    await expect(page.locator(TOGGLE_NOTE)).not.toContainText(/\b(ON|OFF)\b/);
    await expect(toggle).toHaveAttribute('aria-checked', 'false');
    await expect(toggle).toHaveAttribute('aria-disabled', 'true');
    await expect(toggle).toHaveAccessibleDescription(/standard safety checks always run/i);
  });

  test('HC-UISH-006: clicking the disabled switch changes no DOM state outside its popover', async ({ page }) => {
    await openRoute(page, '/inbox');
    const banner = page.getByRole('banner');
    await expect(banner).toBeVisible({ timeout: 15_000 });
    const before = await banner.evaluate((el) => el.outerHTML);
    await page.getByRole('switch', { name: 'Stricter safety mode' }).click({ force: true });
    await page.waitForTimeout(300);
    expect(await banner.evaluate((el) => el.outerHTML)).toBe(before);
    await expect(page.getByRole('switch', { name: 'Stricter safety mode' })).toHaveAttribute('aria-checked', 'false');
  });
});

// ---------------------------------------------------------------------------
// HC-UISH-007 (DF-3): a visible toast does not sit over the More sheet.
// HC-UISH-008: the More sheet closes on Escape, returns focus, and reaches every destination.
// ---------------------------------------------------------------------------
test.describe('HC-UISH-007 and HC-UISH-008 More sheet', () => {
  test.use({ viewport: PHONE });

  test('HC-UISH-007: with a toast visible, opening More leaves no toast over the sheet', async ({ page }) => {
    await openRoute(page, '/inbox');
    await expect(page.getByRole('navigation', { name: 'Tab bar' })).toBeVisible({ timeout: 15_000 });
    await page.evaluate(async () => {
      const toast = await import('/src/components/ui/toast.tsx');
      toast.notify({ message: 'Document saved' });
    });
    await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);

    await page.getByRole('navigation', { name: 'Tab bar' }).getByRole('button', { name: 'More' }).click();
    const sheet = page.getByRole('dialog');
    await expect(sheet).toBeVisible();
    await expect
      .poll(async () => {
        const sheetBox = await sheet.boundingBox();
        const toasts = await page.locator('[data-sonner-toast]').evaluateAll((els) =>
          els.map((el) => el.getBoundingClientRect())
        );
        if (!sheetBox) return 'no sheet box';
        const hits = toasts.filter(
          (t) =>
            t.left < sheetBox.x + sheetBox.width &&
            t.right > sheetBox.x &&
            t.top < sheetBox.y + sheetBox.height &&
            t.bottom > sheetBox.y
        );
        return hits.length;
      }, { timeout: 2000 })
      .toBe(0);
  });

  test('HC-UISH-008: Escape closes More, focus returns to the More tab, every destination is reachable', async ({
    page,
  }) => {
    await openRoute(page, '/inbox');
    const tabBar = page.getByRole('navigation', { name: 'Tab bar' });
    await expect(tabBar).toBeVisible({ timeout: 15_000 });
    const moreTab = tabBar.getByRole('button', { name: 'More' });
    await moreTab.click();

    const sheet = page.getByRole('dialog');
    await expect(sheet).toBeVisible();
    // The sheet slides in on a transform. A tile measured mid-slide reads 51.99997 px, so wait for the slide to settle.
    await expect
      .poll(() => sheet.evaluate((el) => getComputedStyle(el).transform))
      .toMatch(/^(none|matrix\(1, 0, 0, 1, 0, 0\))$/);
    for (const name of ALL_DESTINATIONS) {
      const tile = sheet.getByRole('link', { name, exact: true });
      await expect(tile, `More sheet tile "${name}"`).toHaveCount(1);
      const box = await tile.boundingBox();
      expect(box?.height ?? 0, `tile "${name}" height`).toBeGreaterThanOrEqual(52);
    }

    await page.keyboard.press('Escape');
    await expect(sheet).toBeHidden();
    await expect(moreTab).toBeFocused();
  });
});

// ---------------------------------------------------------------------------
// HC-UIOV-007 (stillness of a still overlay, from the opening click),
// HC-UIFB-006 (a still toast keeps its text and rect from the trigger),
// HC-UIPC-007 (a focus ring is visible 16 ms after Tab on a Button).
// ---------------------------------------------------------------------------
test.describe('Inherited stillness and focus halves (L0 rulings #363, #364, #365)', () => {
  test('HC-UIOV-007: the still toggle popover holds still from the opening click', async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openRoute(page, '/inbox');
    await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
    const info = page.getByRole('button', { name: /stricter safety mode/i });
    await expect(info).toBeVisible();
    const report = await stillnessProbe(page, {
      trigger: () => info.click(),
      expected: [TOGGLE_POPOVER],
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('HC-UIFB-006: a still toast keeps its text and rect from the trigger', async ({ page }) => {
    // The toast module is imported from a /src path, which only the dev server serves (no such path on a preview or deployed build).
    test.skip(
      !!process.env.HC_E2E_BASE_URL,
      'HC_E2E_BASE_URL is set: the /src/components/ui/toast.tsx import path exists only on the dev server'
    );
    type Notify = (options: { message: string; still: boolean }) => unknown;
    await page.setViewportSize(DESKTOP);
    await openRoute(page, '/inbox');
    await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
    // The inbox renders its list when its data arrives, which takes about 50 ms of React work. Wait for that to
    // finish, so the probe times the toast and not the page's own data render.
    await settleRoute(page);
    await expect(
      page.getByRole('button', { name: 'View document' }).first().or(page.getByText('No documents yet.'))
    ).toBeVisible({ timeout: 15_000 });
    // Import the module before the probe window, so the window does not time module loading.
    await page.evaluate(async () => {
      const toast = await import('/src/components/ui/toast.tsx');
      (window as unknown as { __hcNotify: Notify }).__hcNotify = toast.notify;
    });
    const report = await stillnessProbe(page, {
      trigger: () =>
        page.evaluate(() => {
          (window as unknown as { __hcNotify: Notify }).__hcNotify({ message: 'Glucose 118 mg/dL', still: true });
        }),
      expected: ['[data-sonner-toast] [data-t0]'],
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('HC-UIPC-007: a focus ring is visible 16 ms after Tab on a Button', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openRoute(page, '/inbox');
    await expect(page.getByRole('button', { name: 'Profile and settings' })).toBeVisible({ timeout: 15_000 });
    const target = page.getByRole('button', { name: 'Profile and settings' });
    let reached = false;
    for (let press = 0; press < 80 && !reached; press += 1) {
      await page.keyboard.press('Tab');
      reached = await target.evaluate((el) => el === document.activeElement);
    }
    expect(reached, 'Tab reaches the profile button').toBe(true);
    await page.waitForTimeout(16);
    const shadow = await target.evaluate((el) => getComputedStyle(el).boxShadow);
    expect(shadow).not.toBe('none');
  });
});

// ---------------------------------------------------------------------------
// Gate G6 on every route: no horizontal scroll at 390 and 320. Its own test per route, so a page-owned overflow
// can be marked without touching the other checks.
// ---------------------------------------------------------------------------
/**
 * Routes whose page content is wider than 390 px inside [data-route-container]. origin/main overflows on all four
 * too, and the shell itself does not (UI-SHELL T2). Each mark names the page row that fixes it; the mark fails the
 * run once that row lands, so remove the entry then.
 */
const PAGE_OVERFLOW: Record<string, { selector: string; fixBy: string }> = {
  '/inbox': { selector: 'div.flex.items-center.gap-1', fixBy: 'UI-PG-DOCUMENTS' },
  '/medications/med-fixture-1': { selector: 'div.flex.items-center.gap-2', fixBy: 'UI-PG-MEDS' },
  '/explain': { selector: 'div.w-80.space-y-4', fixBy: 'UI-PG-ASK' },
  '/export': { selector: 'div.flex.items-center.gap-3', fixBy: 'UI-PG-EXPORT' },
};

test.describe('Gate G6 on every route', () => {
  for (const route of ALL_ROUTES) {
    test(`GATE G6 on ${route}: no horizontal scroll at 390 and 320`, async ({ page }) => {
      const overflow = PAGE_OVERFLOW[route];
      if (overflow) test.fail(true, `PAGE-OVERFLOW: ${overflow.selector}, fixBy ${overflow.fixBy}`);
      // Load at 390 px, as a phone does, then measure once the data rows are in the DOM (they arrive after load).
      // The route fade is opacity only, so it does not change scroll width; /setup has no route container to wait on.
      await page.setViewportSize(PHONE);
      await openRoute(page, route);
      await expect(page.locator('h1, main').first()).toBeVisible({ timeout: 15_000 });
      await page.waitForLoadState('networkidle');
      expect((await noHorizontalScroll(page)).ok, 'no horizontal scroll at 390').toBe(true);
      await page.setViewportSize(SMALL_PHONE);
      expect((await noHorizontalScroll(page)).ok, 'no horizontal scroll at 320').toBe(true);
    });
  }
});

// ---------------------------------------------------------------------------
// Gate G on every shell route: G1 (axe on the shell's own nodes, light and dark), G7 (console and network),
// G9 (Safety Rail visible). G6 is its own test above; /setup is outside the shell and keeps only G7.
// ---------------------------------------------------------------------------
test.describe('Gate G on every route', () => {
  for (const route of AUTH_ROUTES) {
    test(`GATE G on ${route}: axe light and dark, guard, Safety Rail visible`, async ({ page }) => {
      await page.setViewportSize(DESKTOP);
      const { guard } = await openRoute(page, route);
      await expect(page.locator('h1, main').first()).toBeVisible({ timeout: 15_000 });

      const light = await shellAxeBlocking(page, 'light');
      expect(light.map(describeViolation), 'light axe serious/critical on the shell').toEqual([]);
      const dark = await shellAxeBlocking(page, 'dark');
      expect(dark.map(describeViolation), 'dark axe serious/critical on the shell').toEqual([]);

      const rail = await safetyVisible(page);
      expect(rail.found, 'Safety Rail rendered').toBe(true);
      expect(rail.inViewport, 'Safety Rail in the viewport').toBe(true);
      expect(rail.effectiveOpacity, 'Safety Rail effective opacity').toBe(1);

      guard.assertClean();
    });
  }

  // /setup renders outside AppLayout (App.tsx:201): it has no shell, so the shell axe (G1) and the Safety Rail
  // check (G9) do not run on it. It keeps the guard (G7) here and G6 above. Its whole-page axe findings are page
  // content, recorded in the PR body under PAGE-A11Y.
  test('GATE G7 on /setup: console and network guard (outside the shell)', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    const { guard } = await openRoute(page, '/setup');
    await expect(page.locator('h1, main').first()).toBeVisible({ timeout: 15_000 });
    guard.assertClean();
  });

  test('GATE G2 and G3 on the shell: CLS on load, INP proxy on a nav click', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    const cls = await measureCls(page, async () => {
      await openRoute(page, '/inbox');
      await expect(page.locator('main')).toBeVisible({ timeout: 15_000 });
    });
    expect(cls).toBeLessThan(0.1);

    const inp = await maxEventDuration(page, () =>
      visibleNav(page).getByRole('link', { name: 'Timeline', exact: true }).click()
    );
    expect(inp).toBeLessThan(200);
  });

  test('GATE G5: reduced motion leaves no transformed element 50 ms after a nav click', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openRoute(page, '/inbox');
    await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
    const offenders = await reducedMotionSnapshot(page, () => navigateTo(page, '/verify'));
    expect(offenders).toEqual([]);
  });

  test('GATE G10 route fade sampling is consistent with HC-UIG-003 (no sample below 0.3)', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openRoute(page, '/inbox');
    await expect(page.locator('[data-route-container]')).toBeVisible({ timeout: 15_000 });
    const samples = await routeOpacitySamples(page, { navigate: () => navigateTo(page, '/verify'), durationMs: 800 });
    expect(samples.filter((s) => s.opacity < 0.3)).toEqual([]);
  });
});
