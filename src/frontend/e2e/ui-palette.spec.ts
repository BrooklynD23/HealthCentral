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
  observation({ id: 'g2', value: 118, collected_at: '2026-04-10' }),
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

/** Opens the app with the mock API, the observations and the search answer the palette reads. */
async function openApp(page: Page, route = '/inbox') {
  const mock = await installMockApi(page);
  await page.route(/\/api\/v1\/observations\/?(\?.*)?$/, (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(OBSERVATIONS) })
      : route.fallback()
  );
  await page.route(/\/api\/v1\/search\/?(\?.*)?$/, (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SEARCH_RESPONSE) })
      : route.fallback()
  );
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
      await box.pressSequentially('chol');
      await expect(dialog(page).getByRole('option', { name: /LDL Cholesterol/ })).toBeVisible();
      const result = await axeGate(page, { theme });
      expect(result.blocking.map(describeViolation), `axe in ${theme}`).toEqual([]);
    });
  }

  test('HC-UIPAL-004: Escape returns focus to the trigger', async ({ page }) => {
    await openApp(page);
    await trigger(page).click();
    await expect(dialog(page)).toBeVisible({ timeout: 15_000 });
    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);
    await expect(trigger(page)).toBeFocused();

    // Opened from the page body, focus still ends on the header trigger.
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

  test('G5 (quiet box): with reduced motion no element has a transform while the palette is open', async ({ page }) => {
    await openApp(page);
    const offenders = await reducedMotionSnapshot(page, async () => {
      await page.keyboard.press('Control+K');
      await expect(dialog(page)).toBeVisible({ timeout: 15_000 });
    });
    // The Dialog centres with a translate property, which is not a transform; anything listed here is motion.
    expect(offenders).toEqual([]);
  });
});
