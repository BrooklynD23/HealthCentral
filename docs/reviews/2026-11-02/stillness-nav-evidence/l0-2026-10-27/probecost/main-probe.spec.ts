// L0 measurement (scratch): the same instrumented stillnessProbe as the branch copy, on origin/main's dev server.
// Main has no Safety Rail and (checked by grep) no [data-t0] node in its shell, so `expected` names main's own
// shell nodes. With MAIN_TAG_T0=N, N shell elements on main get a data-t0 attribute in the page before the probe
// (no source change), so the probe visits a node count like the branch's.
import { test, type Page } from '@playwright/test';
import { stillnessProbe } from './e2e/support/gates';
import { installMockApi, seedMockSession } from '/mnt/e/Programming/Github Repo/hc-measure-main/src/frontend/e2e/support/mockApi';

const ROUTES = ['/timeline', '/search', '/medications/med-fixture-1', '/notifications', '/care-tasks'];
const BASE = process.env.MAIN_BASE || 'http://127.0.0.1:3001';
const TAG = Number(process.env.MAIN_TAG_T0 || '0');

async function navigateTo(page: Page, route: string) {
  if (route === '/search') {
    await page.getByRole('banner').getByRole('searchbox').fill('migraine');
    await page.keyboard.press('Enter');
    return;
  }
  if (route === '/medications/med-fixture-1') {
    await page.evaluate(() => {
      window.history.pushState({}, '', '/medications/med-fixture-1');
      window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
    });
    return;
  }
  await page.getByRole('navigation', { name: 'Main navigation' }).locator(`a[href="${route}"]`).click();
}

test.use({ viewport: { width: 1440, height: 900 } });
for (const route of ROUTES) {
  test(`main probe ${route}`, async ({ page }) => {
    await installMockApi(page);
    await seedMockSession(page);
    await page.goto(BASE + '/inbox');
    await page.getByRole('navigation', { name: 'Main navigation' }).waitFor({ state: 'visible', timeout: 15_000 });
    await page.evaluate(() => document.fonts.ready);
    if (TAG > 0) {
      await page.evaluate((n) => {
        const els = Array.from(document.querySelectorAll('aside h1, aside p, nav[aria-label="Main navigation"] a, header button, header input'));
        els.slice(0, n).forEach((el) => el.setAttribute('data-t0', ''));
      }, TAG);
    }
    try {
      await stillnessProbe(page, {
        trigger: () => navigateTo(page, route),
        expected: ['nav[aria-label="Main navigation"]'],
        kind: 'navigation',
        lazyRoute: true,
      });
    } catch (e) {
      console.log(`PROBEFAIL\t${route}\t${String(e).split('\n').slice(0, 4).join(' | ')}`);
    }
  });
}
