// L0 measurement (scratch, not committed): the "bare timer" of PR #370 rulings 2026-10-25/26.
// A 20 ms setInterval in the page records the max gap between ticks, from the trigger through 1500 ms after it.
// Start page, wait and trigger mirror HC-UISH-009 (ui-shell.spec.ts startPageFor / navigateTo, desktop 1440x900).
// Each case is a fresh browser context (cold page), like each HC-UISH-009 test.
import { test, type Page } from '@playwright/test';
import * as branchMock from '/mnt/e/Programming/Github Repo/hc-ui-shell/src/frontend/e2e/support/mockApi';
import * as mainMock from '/mnt/e/Programming/Github Repo/hc-measure-main/src/frontend/e2e/support/mockApi';

type Case = { tree: string; base: string; route: string; run: number };
const PLAN: Case[] = JSON.parse(process.env.MEAS_PLAN || '[]');

function startPageFor(route: string): string {
  return route === '/inbox' ? '/verify' : '/inbox';
}

// Same element as navigateTo on the branch; on main the nav labels differ, so the link is found by href.
async function navigateTo(page: Page, route: string): Promise<void> {
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

for (const c of PLAN) {
  test(`${c.run} ${c.tree} ${c.route}`, async ({ page }) => {
    const mock = c.tree === 'main-dev' ? mainMock : branchMock;
    await mock.installMockApi(page);
    await mock.seedMockSession(page);
    await page.goto(c.base + startPageFor(c.route));
    await page.getByRole('navigation', { name: 'Main navigation' }).waitFor({ state: 'visible', timeout: 15_000 });
    if (c.tree !== 'main-dev') await page.locator('[data-safety-rail]').waitFor({ state: 'visible', timeout: 15_000 });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => {
      const w = window as any;
      w.__ticks = [];
      w.__lt = [];
      w.__obs = new PerformanceObserver((list) => { for (const e of list.getEntries()) w.__lt.push(Math.round(e.duration)); });
      w.__obs.observe({ type: 'longtask', buffered: false });
      w.__timer = setInterval(() => w.__ticks.push(performance.now()), 20);
    });
    await page.waitForTimeout(100);
    const t0 = await page.evaluate(() => performance.now());
    await navigateTo(page, c.route);
    await page.waitForTimeout(1500);
    const r = await page.evaluate((trig) => {
      const w = window as any;
      clearInterval(w.__timer);
      w.__obs.disconnect();
      const t: number[] = w.__ticks;
      let max = 0;
      for (let i = 1; i < t.length; i++) if (t[i] >= trig) max = Math.max(max, t[i] - t[i - 1]);
      return { maxGap: Math.round(max), n: t.filter((x) => x >= trig).length, lt: w.__lt, path: location.pathname };
    }, t0);
    console.log(`MEAS\t${c.tree}\t${c.route}\t${c.run}\t${r.maxGap}\tticks=${r.n}\tlongtasks=${JSON.stringify(r.lt)}\tpath=${r.path}`);
  });
}
