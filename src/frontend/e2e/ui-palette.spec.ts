/**
 * UI-PALETTE (HC-UIPAL-001 .. 005): the lazy command palette, plus gate G for it.
 *
 * Runs on the dev server with the mock API (no backend): the recipe is
 * PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-palette.spec.ts --project=chromium
 *
 * mockApi.ts answers /observations with [] and has no /search fixture, so this file adds both on top of it (a route
 * registered later wins). G2, G3, G5 and HC-UIPAL-005 are timing gates: they are written here but count as
 * acceptance only on a quiet box (the quiet-box precheck is in the PR).
 */

import { expect, test, type Locator, type Page } from '@playwright/test';
import {
  axeGate,
  consoleAndNetworkGuard,
  maxEventDuration,
  measureCls,
  noHorizontalScroll,
  reducedMotionSnapshot,
  safetyVisible,
  stillnessProbe,
  type AxeViolation,
} from './support/gates';
import { FIXTURE_PROFILE_ID, installMockApi, seedMockSession } from './support/mockApi';
import type { Observation } from '../src/services/types';
import type { SearchResponse } from '../src/services/search';

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };
const RAIL = '[data-safety-rail]';
const DIALOG_NAME = 'Command palette';

function observation(overrides: Partial<Observation>): Observation {
  return {
    id: 'obs',
    profile_id: FIXTURE_PROFILE_ID,
    doc_id: 'doc-1',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 100,
    value_text: null,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 99,
    ref_range_text: null,
    flag: null,
    is_abnormal: null,
    collected_at: '2026-01-10',
    user_verified: false,
    extraction_confidence: null,
    source_page: null,
    source_bbox_json: null,
    ...overrides,
  };
}

const OBSERVATIONS: Observation[] = [
  observation({ id: 'g1', value: 92, collected_at: '2026-01-10' }),
  observation({ id: 'g2', value: 118, collected_at: '2026-04-10', user_verified: true }),
  observation({ id: 'g3', value: 101, collected_at: '2026-02-10' }),
  observation({ id: 'l1', analyte_canonical: 'ldl_cholesterol', analyte_raw: 'LDL Cholesterol', value: 142, collected_at: '2026-04-10' }),
  observation({ id: 'h1', analyte_canonical: 'hdl_cholesterol', analyte_raw: 'HDL Cholesterol', value: 51, collected_at: '2026-04-10' }),
];

const SEARCH_RESPONSE: SearchResponse = {
  count: 1,
  results: [
    {
      type: 'entity',
      id: 'e1',
      doc_id: 'doc-1',
      title: 'Lipid panel: cholesterol',
      snippet: 'recorded',
      date: null,
      verified_status: 'unverified',
      category: null,
      highlight_types: [],
    },
  ],
};

function describeViolation(v: AxeViolation): string {
  const nodes = v.nodes.slice(0, 3).map((node) => node.target.join(' ')).join(', ');
  return `${v.id}:${v.impact} at ${nodes}`;
}

/**
 * /trends fixtures for this spec's observations. mockApi.ts has trend fixtures for glucose, ldl and hba1c, but this
 * spec's lipid observations are ldl_cholesterol and hdl_cholesterol, which it does not know (an unmocked request is a
 * 599 and trips the G7 guard). Each analyte has its own chart title and latest value, so "the chart on screen" can be
 * read off the page. Glucose is answered by mockApi.ts: title "Glucose", latest 101.
 */
const LIPID_TRENDS: Record<string, { title: string; latest: number }> = {
  ldl_cholesterol: { title: 'LDL chart', latest: 143 },
  hdl_cholesterol: { title: 'HDL chart', latest: 52 },
};

async function mockLipidTrends(page: Page): Promise<void> {
  await page.route(/\/api\/v1\/observations\/trends\/[^/?]+\/?(\?.*)?$/, (route) => {
    const analyte = new URL(route.request().url()).pathname.replace(/\/+$/, '').split('/').pop() ?? '';
    const fixture = LIPID_TRENDS[analyte];
    if (route.request().method() !== 'GET' || !fixture) return route.fallback();
    const point = (date: string, value: number) => ({
      date: `${date}T00:00:00`,
      value,
      unit: 'mg/dL',
      is_abnormal: false,
      flag: null,
      user_verified: true,
      doc_id: 'doc-1',
    });
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        analyte_canonical: analyte,
        analyte_display_name: fixture.title,
        unit: 'mg/dL',
        ref_low: null,
        ref_high: null,
        summary: '',
        data_points: [point('2026-01-10', fixture.latest - 5), point('2026-04-10', fixture.latest)],
      }),
    });
  });
}

/** The analytes whose /observations/trends/<analyte> the page has asked for since this call. */
function trendRequests(page: Page): string[] {
  const asked: string[] = [];
  page.on('request', (request) => {
    const match = /\/api\/v1\/observations\/trends\/([^/?]+)/.exec(request.url());
    if (match) asked.push(match[1]);
  });
  return asked;
}

const chartTitle = (page: Page, name: string) => page.locator('h3 span').getByText(name, { exact: true });

/** The chart on screen is this one: its title and its latest value are up. */
async function expectChart(page: Page, title: string, latest: number) {
  await expect(chartTitle(page, title)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(`Latest value: ${latest} mg/dL`)).toBeVisible();
}

/** Opens the app with the mock API, the observations and the search answer the palette reads. */
async function openApp(
  page: Page,
  route = '/inbox',
  observations: Observation[] = OBSERVATIONS,
  prepare?: (page: Page) => Promise<void>
) {
  const mock = await installMockApi(page);
  await page.route(/\/api\/v1\/observations\/?(\?.*)?$/, (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(observations) })
      : route.fallback()
  );
  await page.route(/\/api\/v1\/search\/?(\?.*)?$/, (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SEARCH_RESPONSE) })
      : route.fallback()
  );
  await prepare?.(page);
  await seedMockSession(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  await page.goto(route);
  await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
  await page.evaluate(() => document.fonts.ready);
  return { mock, guard };
}

const trigger = (page: Page) => page.getByRole('banner').getByRole('button', { name: /search/i });
const dialog = (page: Page) => page.getByRole('dialog', { name: DIALOG_NAME });
const input = (page: Page) => dialog(page).getByRole('combobox');

async function openWithKeys(page: Page): Promise<Locator> {
  await page.keyboard.press('Control+K');
  await expect(dialog(page)).toBeVisible({ timeout: 15_000 });
  return input(page);
}

/** Every aria-activedescendant on the page names an element that exists, is an option and is selected. */
async function activeDescendantProblems(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const holders = Array.from(document.querySelectorAll('[aria-activedescendant]'));
    if (holders.length === 0) return ['nothing carries aria-activedescendant'];
    const problems: string[] = [];
    for (const holder of holders) {
      const id = holder.getAttribute('aria-activedescendant') ?? '';
      const target = id ? document.getElementById(id) : null;
      if (!target) problems.push(`#${id} does not exist`);
      else if (target.getAttribute('role') !== 'option') problems.push(`#${id} has role ${target.getAttribute('role')}`);
      else if (target.getAttribute('aria-selected') !== 'true') problems.push(`#${id} is not selected`);
      else if (!target.getClientRects().length) problems.push(`#${id} is not rendered`);
    }
    return problems;
  });
}

test.describe('UI-PALETTE', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP);
  });

  test('HC-UIPAL-001: Ctrl+K and / open the palette, and it has no transition or animation', async ({ page }) => {
    await openApp(page);
    await expect(dialog(page)).toHaveCount(0);

    await page.keyboard.press('Control+K');
    await expect(dialog(page)).toBeVisible({ timeout: 15_000 });
    const motion = await dialog(page).evaluate((root) => {
      return [root, ...Array.from(root.querySelectorAll('*'))]
        .map((el) => {
          const cs = getComputedStyle(el);
          return { el: `${el.tagName.toLowerCase()}.${el.getAttribute('class') ?? ''}`, td: cs.transitionDuration, an: cs.animationName };
        })
        .filter((row) => row.an !== 'none' || row.td.split(',').some((part) => parseFloat(part) !== 0));
    });
    expect(motion, 'no element in the palette has a transition or an animation').toEqual([]);
    const own = await dialog(page).evaluate((root) => ({
      td: getComputedStyle(root).transitionDuration,
      an: getComputedStyle(root).animationName,
    }));
    expect(own).toEqual({ td: '0s', an: 'none' });

    await page.keyboard.press('Control+K');
    await expect(dialog(page)).toHaveCount(0);

    await page.locator('main').click({ position: { x: 5, y: 5 } });
    await page.keyboard.press('/');
    await expect(dialog(page)).toBeVisible();
    await expect(input(page)).toBeFocused();
  });

  test('HC-UIPAL-002 (DF-5): after typing chol every aria-activedescendant resolves to a rendered option', async ({ page }) => {
    await openApp(page);
    const box = await openWithKeys(page);
    await expect.poll(() => activeDescendantProblems(page), { message: 'open' }).toEqual([]);
    let typed = '';
    for (const ch of 'chol') {
      typed += ch;
      await box.pressSequentially(ch);
      await expect.poll(() => activeDescendantProblems(page), { message: typed }).toEqual([]);
    }
    await expect(dialog(page).getByRole('option', { name: /LDL Cholesterol/ })).toBeVisible();
    await expect(dialog(page).getByRole('option', { name: /Glucose/ })).toHaveCount(0);
    await expect(dialog(page).getByRole('option').first()).toHaveAttribute('aria-selected', 'true');

    await box.pressSequentially('x');
    await expect.poll(() => activeDescendantProblems(page), { message: 'cholx' }).toEqual([]);
    await box.fill('');
    await expect.poll(() => activeDescendantProblems(page), { message: 'cleared' }).toEqual([]);
  });

  test('HC-UIPAL-002: the arrow keys, Home and End move the selection and the id follows', async ({ page }) => {
    await openApp(page);
    const box = await openWithKeys(page);
    const options = dialog(page).getByRole('option');
    await expect(options.first()).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('ArrowDown');
    await expect(options.nth(1)).toHaveAttribute('aria-selected', 'true');
    await expect.poll(() => activeDescendantProblems(page)).toEqual([]);
    await page.keyboard.press('End');
    await expect(options.last()).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('Home');
    await expect(options.first()).toHaveAttribute('aria-selected', 'true');
    await expect(box).toBeFocused();
  });

  for (const theme of ['light', 'dark'] as const) {
    test(`HC-UIPAL-003 (G1): the open, filtered palette has no serious or critical axe violation in ${theme}`, async ({ page }) => {
      await openApp(page);
      const box = await openWithKeys(page);
      // Unfiltered first: the long, scrolling list is where scrollable-region-focusable would show.
      await expect(dialog(page).getByRole('option').nth(8)).toBeVisible();
      // The scrim fades in over 200 ms (Modal's SCRIM); axe reads colours under it, so measure once it has settled.
      await page.waitForFunction(() =>
        Array.from(document.querySelectorAll('div.fixed.inset-0')).every((el) => getComputedStyle(el).opacity === '1')
      );
      expect((await axeGate(page, { theme })).blocking.map(describeViolation), `axe in ${theme}, unfiltered`).toEqual([]);
      await box.pressSequentially('chol');
      await expect(dialog(page).getByRole('option', { name: /LDL Cholesterol/ })).toBeVisible();
      const result = await axeGate(page, { theme });
      expect(result.blocking.map(describeViolation), `axe in ${theme}, filtered`).toEqual([]);
    });
  }

  test('HC-UIPAL-004: Escape returns focus to the trigger', async ({ page }) => {
    await openApp(page);
    await trigger(page).click();
    await expect(dialog(page)).toBeVisible({ timeout: 15_000 });
    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);
    await expect(trigger(page)).toBeFocused();

    // Opened with nothing focused (the opener is the page body, not <main>, which takes focus when clicked), focus
    // still ends on the header trigger: the fallback in CommandPalette.
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(true);
    await page.keyboard.press('Control+K');
    await expect(dialog(page)).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);
    await expect(trigger(page)).toBeFocused();
  });

  test('HC-UIPAL-004: Enter on free text goes to /search?q=', async ({ page }) => {
    await openApp(page);
    await trigger(page).click();
    const box = input(page);
    await expect(box).toBeFocused({ timeout: 15_000 });
    await box.pressSequentially('migraine aura');
    // The hit renders only after the 150 ms debounce and the answer; Enter before then proves nothing about the order.
    await expect(dialog(page).getByRole('option', { name: /Lipid panel: cholesterol/ })).toBeVisible();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/search\?q=migraine\+aura$/, { timeout: 15_000 });
    await expect(dialog(page)).toHaveCount(0);
  });

  test('HC-UIPAL-004: Enter on a matching page goes there, not to /search', async ({ page }) => {
    await openApp(page);
    const box = await openWithKeys(page);
    await box.pressSequentially('timeline');
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/timeline$/, { timeout: 15_000 });
  });

  test('HC-UIPAL-004: the record search is debounced 150 ms: typing chol quickly asks once', async ({ page }) => {
    await openApp(page);
    const asked: string[] = [];
    page.on('request', (request) => {
      const url = new URL(request.url());
      if (/\/api\/v1\/search\/?$/.test(url.pathname)) asked.push(url.searchParams.get('q') ?? '');
    });
    const box = await openWithKeys(page);
    await box.pressSequentially('chol', { delay: 10 });
    await expect(dialog(page).getByRole('option', { name: /Lipid panel: cholesterol/ })).toBeVisible();
    expect(asked, 'one request, for the whole word').toEqual(['chol']);
  });

  test('HC-UIPAL-004: a Results row goes to its analyte, and an unverified value or hit is marked', async ({ page }) => {
    await openApp(page, '/inbox', OBSERVATIONS, mockLipidTrends);
    const asked = trendRequests(page);
    const box = await openWithKeys(page);
    await box.pressSequentially('chol');
    const ldl = dialog(page).getByRole('option', { name: /LDL Cholesterol/ });
    await expect(ldl.locator('[data-t0]')).toHaveText('142 mg/dL (unverified)');
    await expect(dialog(page).getByRole('option', { name: /Lipid panel: cholesterol \(unverified\)/ })).toBeVisible();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/trends\?analyte=ldl_cholesterol$/, { timeout: 15_000 });
    // L0 ruling 6586583230: the chart is LDL's, not the first analyte's (glucose).
    await expectChart(page, 'LDL chart', 143);
    await expect(chartTitle(page, 'Glucose')).toHaveCount(0);
    expect(asked, 'no /observations/trends/glucose request, only LDL').toEqual(['ldl_cholesterol']);
  });

  test('HC-UIPAL-004: on /trends a row clicked earlier does not outlast a palette pick (the page is not remounted)', async ({ page }) => {
    await openApp(page, '/trends', OBSERVATIONS, mockLipidTrends);
    await expectChart(page, 'Glucose', 101);
    await page.getByRole('main').getByRole('button', { name: /HDL Cholesterol/ }).click();
    await expectChart(page, 'HDL chart', 52);

    const box = await openWithKeys(page);
    await box.pressSequentially('chol');
    await dialog(page).getByRole('option', { name: /LDL Cholesterol/ }).click();
    await expect(page).toHaveURL(/\/trends\?analyte=ldl_cholesterol$/, { timeout: 15_000 });
    await expectChart(page, 'LDL chart', 143);
    await expect(chartTitle(page, 'HDL chart')).toHaveCount(0);
  });

  test('HC-UIPAL-004: /trends?analyte=nope shows the first analyte, asks for nothing named nope, and logs nothing', async ({ page }) => {
    let asked: string[] = [];
    const { guard } = await openApp(page, '/trends?analyte=nope', OBSERVATIONS, async (p) => {
      await mockLipidTrends(p);
      asked = trendRequests(p);
    });
    await expectChart(page, 'Glucose', 101);
    expect(asked, 'one trend request, for the first analyte').toEqual(['glucose']);
    await expect(page.getByText('No trend data available for this analyte')).toHaveCount(0);
    await expect(page.getByText('Failed to load observations')).toHaveCount(0);
    guard.assertClean();
  });

  test('HC-UIPAL-004: /trends?analyte=ldl_cholesterol is a clean page (G7), its Safety Rail is up (G9), and it asks for LDL only', async ({ page }) => {
    let asked: string[] = [];
    const { guard } = await openApp(page, '/trends?analyte=ldl_cholesterol', OBSERVATIONS, async (p) => {
      await mockLipidTrends(p);
      asked = trendRequests(p);
    });
    await expectChart(page, 'LDL chart', 143);
    expect(await safetyVisible(page)).toEqual({ found: true, inViewport: true, effectiveOpacity: 1 });
    guard.assertClean();
    expect(asked, 'the first and only trend request is LDL, never glucose').toEqual(['ldl_cholesterol']);
  });

  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`G6: /trends?analyte=ldl_cholesterol has no horizontal scroll at ${viewport.width}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openApp(page, '/trends?analyte=ldl_cholesterol', OBSERVATIONS, mockLipidTrends);
      await expectChart(page, 'LDL chart', 143);
      const scroll = await noHorizontalScroll(page);
      expect(scroll.ok, `scrollWidth ${scroll.scrollWidth} > innerWidth ${scroll.innerWidth}`).toBe(true);
    });
  }

  for (const theme of ['light', 'dark'] as const) {
    test(`G1: /trends?analyte=ldl_cholesterol has no serious or critical axe violation in ${theme}`, async ({ page }) => {
      await openApp(page, '/trends?analyte=ldl_cholesterol', OBSERVATIONS, mockLipidTrends);
      await expectChart(page, 'LDL chart', 143);
      // The summary rows fade in one after another; axe reads colours, so measure once they have all settled.
      await page.waitForFunction(() =>
        Array.from(document.querySelectorAll('main button')).every((el) => getComputedStyle(el).opacity === '1')
      );
      expect((await axeGate(page, { theme })).blocking.map(describeViolation), `axe in ${theme}`).toEqual([]);
    });
  }

  test('the input sits at the top edge of the dialog and its focus ring stays inside it', async ({ page }) => {
    await openApp(page);
    await openWithKeys(page);
    const gap = await dialog(page).evaluate((root) => {
      const field = root.querySelector('[role="combobox"]') as HTMLElement;
      return {
        band: field.getBoundingClientRect().top - root.getBoundingClientRect().top,
        ring: getComputedStyle(field).boxShadow,
      };
    });
    expect(gap.band, 'no blank band above the input').toBeLessThanOrEqual(1);
    expect(gap.ring, 'the focus ring is inset (the dialog clips outside paint)').toContain('inset');
  });

  test('HC-UIPAL-005 (G10): the Results latest value is still from the Ctrl+K press (overlay)', async ({ page }) => {
    await openApp(page);
    // Warm the lazy chunk and the observations, as a returning user has them; then close it.
    await openWithKeys(page);
    await expect(dialog(page).getByText('118 mg/dL')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);
    await page.locator('main').click({ position: { x: 5, y: 5 } });

    const report = await stillnessProbe(page, {
      kind: 'overlay',
      trigger: () => page.keyboard.press('Control+K'),
      expected: ['[role="dialog"] [role="option"] [data-t0]', RAIL],
    });
    expect(report.nodes).toBeGreaterThan(0);
    await expect(dialog(page).getByText('118 mg/dL')).toHaveAttribute('data-t0', '');
  });

  test('HC-UIPAL-005 (G10, cold): the first open, with the chunk and the data still to fetch, is still too', async ({ page }) => {
    await openApp(page);
    await page.locator('main').click({ position: { x: 5, y: 5 } });
    const report = await stillnessProbe(page, {
      kind: 'overlay',
      lazyRoute: true,
      trigger: () => page.keyboard.press('Control+K'),
      expected: ['[role="dialog"] [role="option"] [data-t0]', RAIL],
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('the palette chunk is fetched on the first open, not before', async ({ page }) => {
    const chunk: string[] = [];
    page.on('request', (request) => {
      if (/CommandPalette/.test(new URL(request.url()).pathname)) chunk.push(request.url());
    });
    await openApp(page);
    await page.locator('main').click({ position: { x: 5, y: 5 } });
    expect(chunk, 'no CommandPalette request while the app is idle').toEqual([]);
    await openWithKeys(page);
    await expect.poll(() => chunk.length, { message: 'the first open fetches it' }).toBeGreaterThan(0);
  });

  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`a 255-character value keeps the analyte name and the unverified mark inside the list at ${viewport.width}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      const long = observation({
        id: 'long1',
        analyte_canonical: 'long_result',
        analyte_raw: 'Long Result',
        value: null,
        value_text: 'W'.repeat(255),
        unit: null,
        user_verified: false,
      });
      await openApp(page, '/timeline', [long]);
      await openWithKeys(page);
      await input(page).pressSequentially('long result');
      const row = dialog(page).getByRole('option', { name: /Long Result/ });
      await expect(row).toBeVisible();
      const m = await row.evaluate((option) => {
        const list = option.closest('[role="listbox"]') as HTMLElement;
        const listBox = list.getBoundingClientRect();
        const [name, value] = Array.from(option.querySelectorAll('span'));
        const nameBox = name.getBoundingClientRect();
        const valueBox = value.getBoundingClientRect();
        return {
          nameWidth: nameBox.width,
          nameTruncated: name.scrollWidth > name.clientWidth,
          valueRight: valueBox.right,
          valueLeft: valueBox.left,
          listLeft: listBox.left,
          listRight: listBox.right,
          valueText: value.textContent ?? '',
          rowOverflow: option.scrollWidth - option.clientWidth,
          listOverflow: list.scrollWidth - list.clientWidth,
        };
      });
      expect(m.nameWidth, 'the analyte name keeps room').toBeGreaterThanOrEqual(60);
      expect(m.nameTruncated, 'the name "Long Result" is not cut').toBe(false);
      expect(m.valueLeft).toBeGreaterThanOrEqual(m.listLeft);
      expect(m.valueRight, 'the value wraps inside the list').toBeLessThanOrEqual(m.listRight);
      expect(m.rowOverflow).toBeLessThanOrEqual(0);
      expect(m.listOverflow).toBeLessThanOrEqual(0);
      expect(m.valueText.endsWith('(unverified)'), 'the D4 mark is in the same text as the value').toBe(true);
      const scroll = await noHorizontalScroll(page);
      expect(scroll.ok, `scrollWidth ${scroll.scrollWidth} > innerWidth ${scroll.innerWidth}`).toBe(true);
    });
  }

  test('HC-UIPAL-004: below lg Escape returns focus to the phone search link (the header button is hidden)', async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openApp(page, '/timeline');
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(true);
    await openWithKeys(page);
    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);
    await expect(page.getByRole('banner').getByRole('link', { name: 'Search' })).toBeFocused();
  });

  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`G6: no horizontal scroll with the palette open at ${viewport.width}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      // Not /inbox: it overflows by itself until UI-PG-DOCUMENTS (PAGE_OVERFLOW in ui-shell.spec.ts).
      await openApp(page, '/timeline');
      await openWithKeys(page);
      await input(page).pressSequentially('chol');
      const scroll = await noHorizontalScroll(page);
      expect(scroll.ok, `scrollWidth ${scroll.scrollWidth} > innerWidth ${scroll.innerWidth}`).toBe(true);
      const box = await dialog(page).boundingBox();
      expect(box && box.x >= 0 && box.x + box.width <= viewport.width, 'the dialog sits inside the viewport').toBe(true);
    });
  }

  test('G7: no console error, no non-localhost request and no unmocked API call while it is used', async ({ page }) => {
    const { guard } = await openApp(page);
    await trigger(page).click();
    await expect(dialog(page)).toBeVisible({ timeout: 15_000 });
    await input(page).pressSequentially('chol');
    await expect(dialog(page).getByRole('option', { name: /Lipid panel: cholesterol/ })).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);
    guard.assertClean();
  });

  test('G9: the Safety Rail stays visible at opacity 1 while the palette is open', async ({ page }) => {
    await openApp(page);
    await openWithKeys(page);
    await input(page).pressSequentially('chol');
    const rail = await safetyVisible(page);
    expect(rail).toEqual({ found: true, inViewport: true, effectiveOpacity: 1 });
  });

  test('G2 and G3 (quiet box): CLS from load through an open, and the open and a keystroke stay under the event bound', async ({ page }) => {
    const cls = await measureCls(page, async () => {
      await openApp(page);
      await openWithKeys(page);
      await input(page).pressSequentially('chol');
    });
    expect(cls).toBeLessThan(0.1);

    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);
    const inp = await maxEventDuration(page, async () => {
      await page.keyboard.press('Control+K');
      await expect(dialog(page)).toBeVisible();
      await input(page).pressSequentially('lipid');
    });
    expect(inp).toBeLessThan(200);
  });

  test('G5 (quiet box): with reduced motion no element has a transform after the palette opens, after typing and after moving', async ({ page }) => {
    await openApp(page);
    // One snapshot per interaction (the plan's "after each interaction"), each taken 50 ms after its own action.
    const open = await reducedMotionSnapshot(page, async () => {
      await page.keyboard.press('Control+K');
      await expect(dialog(page)).toBeVisible({ timeout: 15_000 });
    });
    const typed = await reducedMotionSnapshot(page, async () => {
      await input(page).pressSequentially('chol');
      await expect(dialog(page).getByRole('option', { name: /LDL Cholesterol/ })).toBeVisible();
    });
    const moved = await reducedMotionSnapshot(page, async () => {
      await page.keyboard.press('ArrowDown');
    });
    // The Dialog centres with a translate property, which is not a transform; anything listed here is motion.
    expect({ open, typed, moved }).toEqual({ open: [], typed: [], moved: [] });
  });
});
