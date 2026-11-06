/**
 * UI-ABOUT e2e (plan section UI-ABOUT, §4.2 About row): the public About page at /about, end to end.
 *
 * Two describes, kept apart on purpose:
 *  - "HC-UIABT e2e" is functional and has no timing in it: HC-UIABT-001 (no redirect, no API request, signed out and
 *    signed in), HC-UIABT-003 (the example label), HC-UIABT-004 / G7, G1 (axe, light and dark), G6 (390 and 320), G9,
 *    the profile-menu and "Open Asclexis" link tests, and the space between the two S1 sections.
 *    Run it under normal load:
 *      PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-about.spec.ts --project=chromium --grep-invert QUIET-BOX
 *  - "QUIET-BOX" is G2, G3, G5 and G10 (HC-UIABT-002), which are timing measurements. Run them on a quiet box only
 *    (RUNBOOK 10.1):
 *      PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-about.spec.ts --project=chromium --grep QUIET-BOX
 *    G3 is also run against the production build (`npm run build`, `npx vite preview`, HC_E2E_BASE_URL).
 *
 * G9 reading: /about is outside ProtectedRoute and AppLayout, so it has no shell and no Safety Rail, as /setup has none.
 * The test asserts that the rail is absent and that the page's own safety statement ([data-about-safety]) is in the
 * first viewport at full opacity instead.
 *
 * Nothing here answers an API call: the page must make none. The exceptions install the shared mock because they
 * start or end on a page that does call the API: the two link tests (the shell behind the profile menu, and /setup
 * behind "Open Asclexis") and HC-UIABT-002 (its start page, /setup, fetches its profile list).
 */

import { expect, test, type Page } from '@playwright/test';
import {
  axeGate,
  consoleAndNetworkGuard,
  maxEventDuration,
  measureCls,
  noHorizontalScroll,
  reducedMotionSnapshot,
  safetyVisible,
  setTheme,
  stillnessProbe,
  type Theme,
} from './support/gates';
import { installMockApi, seedMockSession } from './support/mockApi';

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };
const THEMES: Theme[] = ['light', 'dark'];

const EXAMPLE_LABEL = 'Example data, not yours';
/** The plan (§4.2) names three T0 elements: the safety statement, the local-first statement and the "not medical advice" text. The example label is this row's fourth. All sit outside every ShowcaseReveal. */
const T0_SELECTORS = ['[data-about-safety]', '[data-about-not-advice]', '[data-about-local-first]', '[data-about-example-label]'];
const H1 = (page: Page) => page.getByRole('heading', { level: 1 });

/** Records every request the page makes. */
function recordRequests(page: Page): string[] {
  const urls: string[] = [];
  page.on('request', (request) => urls.push(request.url()));
  return urls;
}

const isApi = (url: string) => /\/api\//.test(new URL(url).pathname) || /:8000\b/.test(url);

/**
 * Waits until the page is at rest: network idle, fonts loaded, and every one-shot animation finished (the S1
 * entrance, the ribbon draw, a theme transition). The beam's own loop is infinite and does not count.
 */
async function settle(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  await page.waitForFunction(() =>
    document
      .getAnimations()
      .every((animation) => animation.playState !== 'running' || animation.effect?.getComputedTiming().iterations === Infinity)
  );
}

async function openAbout(page: Page, options: { viewport?: { width: number; height: number }; signedIn?: boolean } = {}) {
  await page.setViewportSize(options.viewport ?? DESKTOP);
  if (options.signedIn) await seedMockSession(page);
  const urls = recordRequests(page);
  const guard = consoleAndNetworkGuard(page);
  await page.goto('/about');
  // On the About page itself: a redirect to /setup shows another h1, and every gate below would measure that page.
  await expect(page).toHaveURL(/\/about$/);
  await expect(H1(page)).toHaveText('About Asclexis');
  await settle(page);
  return { urls, guard };
}

/** Applies a theme, then waits for the colour transitions it starts to end, so axe does not sample a half-faded page. */
async function applyTheme(page: Page, theme: Theme): Promise<void> {
  await setTheme(page, theme);
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await page.waitForFunction(() => document.getAnimations().filter((a) => a instanceof CSSTransition).length === 0);
}

async function axeBlocking(page: Page): Promise<string[]> {
  const axe = await axeGate(page);
  return axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);
}

/** Where a selector sits against the viewport, and its effective opacity. */
async function placement(page: Page, selector: string) {
  return page.evaluate((target) => {
    const el = document.querySelector(target);
    if (!(el instanceof HTMLElement)) return null;
    const rect = el.getBoundingClientRect();
    let opacity = 1;
    for (let node: Element | null = el; node; node = node.parentElement) opacity *= parseFloat(getComputedStyle(node).opacity);
    return {
      top: rect.top,
      bottom: rect.bottom,
      left: rect.left,
      right: rect.right,
      width: rect.width,
      height: rect.height,
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      opacity,
      isT0: el.hasAttribute('data-t0'),
    };
  }, selector);
}

async function expectT0InFirstViewport(page: Page, when: string): Promise<void> {
  for (const selector of T0_SELECTORS) {
    const where = await placement(page, selector);
    expect(where, `${when}: ${selector} exists`).not.toBeNull();
    const w = where!;
    const inside = w.width > 0 && w.height > 0 && w.top >= 0 && w.bottom <= w.innerHeight && w.left >= 0 && w.right <= w.innerWidth;
    expect(inside, `${when}: ${selector} fully in the first viewport ${JSON.stringify(w)}`).toBe(true);
    expect(w.opacity, `${when}: ${selector} effective opacity`).toBeGreaterThanOrEqual(0.99);
    expect(w.isT0, `${when}: ${selector} data-t0`).toBe(true);
  }
}

/** A client-side navigation: the sampler in the page survives it, a page.goto would end it. */
async function spaTo(page: Page, path: string): Promise<void> {
  await page.evaluate((to) => {
    window.history.pushState({}, '', to);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}

// ---------------------------------------------------------------------------------------------------------------
// Functional: no timing.
// ---------------------------------------------------------------------------------------------------------------
test.describe('HC-UIABT e2e', () => {
  test('HC-UIABT-001: /about stays on /about with no profile and makes no API request', async ({ page }) => {
    const { urls } = await openAbout(page);
    await expect(page).toHaveURL(/\/about$/);
    await expect(H1(page)).toHaveCount(1);
    // A /setup redirect would show the welcome heading instead.
    await expect(page.getByRole('heading', { name: 'Welcome to Asclexis' })).toHaveCount(0);
    expect(urls.filter(isApi), 'API requests with no profile').toEqual([]);
  });

  test('HC-UIABT-001: a signed-in visitor stays on /about and triggers no API request either', async ({ page }) => {
    const { urls } = await openAbout(page, { signedIn: true });
    await expect(page).toHaveURL(/\/about$/);
    await expect(H1(page)).toHaveCount(1);
    expect(urls.filter(isApi), 'API requests with a stored session').toEqual([]);
    // No shell: no main navigation for a signed-in visitor either.
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toHaveCount(0);
  });

  test('the profile menu leads to /about and "Open Asclexis" leads on to the shell (signed in)', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await installMockApi(page);
    await seedMockSession(page);
    await page.goto('/');
    const nav = page.getByRole('navigation', { name: 'Main navigation' }).first();
    await expect(nav).toBeVisible();
    await page.getByRole('button', { name: 'Profile and settings' }).click();
    await page.getByRole('link', { name: 'About', exact: true }).click();
    await expect(page).toHaveURL(/\/about$/);
    await expect(H1(page)).toHaveText('About Asclexis');
    await page.getByRole('link', { name: 'Open Asclexis' }).click();
    await expect(page).not.toHaveURL(/\/about/);
    await expect(nav).toBeVisible();
  });

  test('"Open Asclexis" with no profile leads to /setup', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await installMockApi(page);
    await page.goto('/about');
    await expect(H1(page)).toHaveText('About Asclexis');
    await page.getByRole('link', { name: 'Open Asclexis' }).click();
    await expect(page).toHaveURL(/\/setup/);
    await expect(page.getByRole('heading', { name: 'Welcome to Asclexis' })).toBeVisible();
  });

  test('HC-UIABT-003: "Example data, not yours" is real text that names the ribbon region', async ({ page }) => {
    await openAbout(page);
    const label = page.getByText(EXAMPLE_LABEL, { exact: true });
    await expect(label).toHaveCount(1);
    await expect(label).toBeVisible();
    // In the DOM as text: not inside the svg, not aria-hidden.
    expect(await label.evaluate((el) => el.closest('svg') === null && el.closest('[aria-hidden="true"]') === null)).toBe(true);

    const region = page.getByRole('region', { name: EXAMPLE_LABEL });
    await expect(region).toBeVisible();
    await expect(region.getByRole('slider', { name: 'Example analyte: results over time' })).toBeVisible();
    // The label is above the ribbon, in the same region.
    const labelBox = await label.boundingBox();
    const ribbonBox = await region.getByRole('slider').boundingBox();
    expect(labelBox && ribbonBox && labelBox.y + labelBox.height <= ribbonBox.y + 0.5, 'label sits above the ribbon').toBe(true);
  });

  test('the two S1 sections have space between them at 1440, 390 and 320', async ({ page }) => {
    // ShowcaseReveal wraps each child in its own div, so the page's space-y-10 does not reach between them.
    for (const viewport of [DESKTOP, PHONE, SMALL_PHONE]) {
      await openAbout(page, { viewport });
      const gap = await page.evaluate(() => {
        const how = document.querySelector('[data-about-group="how-it-works"]');
        const capstone = document.querySelector('[data-about-group="capstone"]');
        if (!how || !capstone) return null;
        // The heading's top edge, not the section's padding box: the space a reader sees.
        const heading = capstone.querySelector('h2');
        return (heading ?? capstone).getBoundingClientRect().top - how.getBoundingClientRect().bottom;
      });
      expect(gap, `${viewport.width}px: sections exist`).not.toBeNull();
      expect(gap!, `${viewport.width}px: gap between How it works and Capstone project`).toBeGreaterThanOrEqual(32);
    }
  });

  test('the four T0 statements are in the first viewport at 1440 and 390, visible with no hover', async ({ page }) => {
    for (const viewport of [DESKTOP, PHONE]) {
      await openAbout(page, { viewport });
      await expectT0InFirstViewport(page, `${viewport.width}px`);
    }
  });

  test('HC-UIABT-004 and G7: no console error, no outside request, orb canvas mounted after the chunk and fonts load', async ({ page }) => {
    const { guard } = await openAbout(page);
    // The lazy orb chunk really loaded: its canvas is in the DOM, inside the aria-hidden wrapper.
    const canvas = page.locator('canvas');
    await expect(canvas).toHaveCount(1);
    expect(await canvas.evaluate((el) => el.closest('[aria-hidden="true"]') !== null)).toBe(true);
    await page.waitForLoadState('networkidle');
    expect(await page.evaluate(() => document.fonts.status)).toBe('loaded');
    guard.assertClean();
  });

  test('G9: the route has no Safety Rail, so the page\'s own safety statement is in view at full opacity', async ({ page }) => {
    for (const viewport of [DESKTOP, PHONE]) {
      await openAbout(page, { viewport });
      // The rail belongs to the shell, and /about has no shell (as /setup has none).
      expect((await safetyVisible(page)).found, 'no Safety Rail on /about').toBe(false);
      const statement = await safetyVisible(page, '[data-about-safety]');
      expect(
        statement.found && statement.inViewport && statement.effectiveOpacity >= 0.99,
        `G9 own statement ${viewport.width}px ${JSON.stringify(statement)}`
      ).toBe(true);
    }
  });

  for (const theme of THEMES) {
    test(`G1 on /about (${theme}): axe finds no serious or critical violation`, async ({ page }) => {
      await openAbout(page);
      await applyTheme(page, theme);
      expect(await axeBlocking(page), `G1 ${theme}`).toEqual([]);
    });
  }

  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`G6 on /about at ${viewport.width}x${viewport.height}: no horizontal scroll`, async ({ page }) => {
      await openAbout(page, { viewport });
      expect((await noHorizontalScroll(page)).ok, `G6 ${viewport.width}`).toBe(true);
    });
  }
});

// ---------------------------------------------------------------------------------------------------------------
// Timing: G2, G3, G5, G10. Quiet box only.
// ---------------------------------------------------------------------------------------------------------------
test.describe('QUIET-BOX UI-ABOUT timing gates', () => {
  for (const theme of THEMES) {
    test(`QUIET-BOX G2 on /about (${theme})`, async ({ page }) => {
      await page.setViewportSize(DESKTOP);

      // G2: layout shift over the first load (lazy chunk, fonts, orb, S1, the ribbon reveal) and the theme change.
      // No earlier visit: a second load would measure a page whose S1 and ribbon reveal were already played and whose
      // chunks and fonts were already fetched.
      const cls = await measureCls(page, async () => {
        await page.goto('/about');
        await expect(H1(page)).toBeVisible();
        await settle(page);
        await applyTheme(page, theme);
      });
      expect(cls, `G2 ${theme}`).toBeLessThan(0.1);
    });

    test(`QUIET-BOX G3 on /about (${theme})`, async ({ page }) => {
      await openAbout(page);
      await applyTheme(page, theme);

      // G3: the worst Event Timing duration over the page's interactions (the ribbon is the only control but the
      // link), CPU x4. The link is not pressed: it leaves the page.
      const ribbon = page.getByRole('slider', { name: 'Example analyte: results over time' });
      const inp = await maxEventDuration(
        page,
        async () => {
          await ribbon.focus();
          await page.keyboard.press('Home');
          await page.keyboard.press('ArrowRight');
          await page.keyboard.press('End');
          await ribbon.click({ position: { x: 20, y: 40 } });
        },
        { cpuRate: 4 }
      );
      expect(inp, `G3 ${theme}`).toBeLessThan(200);
    });

    test(`QUIET-BOX G5 on /about (${theme})`, async ({ page }, testInfo) => {
      await page.setViewportSize(DESKTOP);
      await page.goto('/about');
      await expect(H1(page)).toBeVisible();
      await settle(page);

      // A first visit under reduced motion. The snapshot runs after the entrance has ended, so G5 sees a transform
      // left behind on S1, the ribbon or the beam; it does not see the entrance itself. That the S1 entrance is
      // opacity-only under reduced motion is HC-UISK-005's job. A press on the ribbon moves its cursor.
      const offenders = await reducedMotionSnapshot(page, async () => {
        // S1 and the ribbon reveal play only on the first visit per session. Without this the reload takes the skip
        // path and the snapshot would not see S1 at all.
        await page.evaluate(() => window.sessionStorage.clear());
        await page.reload();
        await expect(H1(page)).toBeVisible();
        await expect(page.locator('canvas')).toHaveCount(1);
        // The reload resets data-theme to light (index.html), so the theme goes on after it.
        await applyTheme(page, theme);
        const ribbon = page.getByRole('slider', { name: 'Example analyte: results over time' });
        await ribbon.focus();
        await page.keyboard.press('Home');
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('End');
        await ribbon.click({ position: { x: 20, y: 40 } });
      });
      expect(offenders, `G5 ${theme}`).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.dataset.theme), 'G5 theme on the screenshot').toBe(theme);
      const shot = testInfo.outputPath(`about-${theme}-reduced.png`);
      await page.screenshot({ path: shot, fullPage: false });
      testInfo.annotations.push({ type: 'gate-g5-screenshot', description: shot });
    });

    for (const mount of ['warm', 'first-visit'] as const) {
      test(`QUIET-BOX G10 / HC-UIABT-002 stillness on /about through the whole S1 sequence, ${mount} mount (${theme})`, async ({ page }, testInfo) => {
        // The probe's sampler lives in the page, so /about is reached by a client-side navigation from /setup.
        await page.setViewportSize(DESKTOP);
        await installMockApi(page);
        await page.goto('/setup');
        await page.waitForLoadState('networkidle');
        if (mount === 'warm') {
          // Load the lazy chunks (page, orb) by visiting once, then go back, so the probed mount is warm.
          await spaTo(page, '/about');
          await expect(H1(page)).toBeVisible();
          await expect(page.locator('canvas')).toHaveCount(1);
          await spaTo(page, '/setup');
          await expect(page.getByRole('heading', { name: 'About Asclexis' })).toHaveCount(0);
          await page.waitForLoadState('networkidle');
        }
        // first-visit: no warm-up. The page chunk and the orb chunk arrive during the probe (gate G10 names the first
        // visit to a lazy route), so a T0 rect that changes when a chunk lands is seen.
        await applyTheme(page, theme);

        // S1 plays only on the first visit per session. Clear the session so the probed mount is a first visit, and
        // record the S1 groups from the page, so a probe that saw nothing move is not read as a pass.
        await page.evaluate(() => {
          window.sessionStorage.clear();
          const w = window as unknown as {
            __aboutMoves: { running: boolean; groups: Record<string, { minOpacity: number; moved: boolean; samples: number }> };
          };
          w.__aboutMoves = { running: true, groups: {} };
          const tick = () => {
            if (!w.__aboutMoves.running) return;
            document.querySelectorAll('[data-about-group]').forEach((el) => {
              const name = el.getAttribute('data-about-group') ?? '';
              let opacity = 1;
              for (let node: Element | null = el; node; node = node.parentElement) opacity *= parseFloat(getComputedStyle(node).opacity);
              const transform = el.parentElement ? getComputedStyle(el.parentElement).transform : 'none';
              const record = (w.__aboutMoves.groups[name] ??= { minOpacity: 1, moved: false, samples: 0 });
              record.samples += 1;
              record.minOpacity = Math.min(record.minOpacity, opacity);
              if (transform !== 'none' && !/^matrix\(1, 0, 0, 1, 0, 0\)$/.test(transform)) record.moved = true;
            });
            requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        });

        // The groups S1 wraps are 6 or fewer at 60 ms stagger + 480 ms, so the 1000 ms window covers the sequence.
        const report = await stillnessProbe(page, {
          trigger: async () => {
            await spaTo(page, '/about');
            await expect(H1(page)).toBeVisible();
          },
          expected: ['[data-about-not-advice]', '[data-about-local-first]', '[data-about-safety]', '[data-about-example-label]'],
          kind: 'interaction',
          windowMs: 1000,
          lazyRoute: mount === 'first-visit',
        });
        testInfo.annotations.push({ type: 'gate-g10', description: `about ${mount} ${theme}: ${JSON.stringify(report)}` });
        if (mount === 'first-visit') await expect(page.locator('canvas')).toHaveCount(1);

        const moves = await page.evaluate(() => {
          const w = window as unknown as { __aboutMoves: { running: boolean; groups: Record<string, { minOpacity: number; moved: boolean; samples: number }> } };
          w.__aboutMoves.running = false;
          return w.__aboutMoves.groups;
        });
        testInfo.annotations.push({ type: 'gate-g10-s1-groups', description: JSON.stringify(moves) });
        const names = Object.keys(moves);
        expect(names.length, 'S1 groups seen').toBeGreaterThanOrEqual(2);
        for (const name of names) {
          // The probe is only evidence if the S1 groups really moved while it ran.
          expect(moves[name].minOpacity, `S1 group ${name} started hidden`).toBeLessThan(0.99);
          expect(moves[name].moved, `S1 group ${name} rose`).toBe(true);
        }
        expect(report.nodes).toBeGreaterThanOrEqual(T0_SELECTORS.length);
      });
    }
  }
});
