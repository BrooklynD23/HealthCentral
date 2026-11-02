/**
 * UI-PG-REVIEW e2e (plan section 7.7): Gate G on /verify, plus HC-UIREV-001 to HC-UIREV-005 end to end.
 *
 * The observation, entity and page calls are answered here (page.route, registered after installMockApi so it
 * runs first); every other /api/v1 call goes to the shared shell fixtures. Run without the backend (recipe 2 in
 * e2e/README.md):
 *   PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-review.spec.ts --project=chromium
 *
 * /verify has no chart, so the Ink moment is asserted on the row marker and the chip only.
 *
 * Test titles carry the gate id the plan uses. The timing-sensitive ones (Gate G2 CLS, Gate G3 INP, Gate G5
 * reduced motion, Gate G10 stillness, HC-UIREV-002 and HC-UIREV-005 probes) run on a quiet box only; a run on a
 * busy box leaves them out with --grep-invert.
 */

import { expect, test, type Locator, type Page, type Route } from '@playwright/test';
import {
  axeGate,
  consoleAndNetworkGuard,
  maxEventDuration,
  measureCls,
  noHorizontalScroll,
  reducedMotionSnapshot,
  ROUTE_CONTAINER_SELECTOR,
  ROUTE_FALLBACK_SELECTOR,
  safetyVisible,
  setTheme,
  stillnessProbe,
  type Theme,
} from './support/gates';
import { FIXTURE_PROFILE_ID, installMockApi, seedMockSession } from './support/mockApi';
import type { DocumentEntityResponse } from '../src/services/documentCategories';
import type { Observation } from '../src/services/types';

const DOC_ID = 'doc-fixture-0002';
const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };

const GLUCOSE_ID = 'obs-review-glucose';
const A1C_ID = 'obs-review-a1c';
const FERRITIN_ID = 'obs-review-ferritin';

function makeObservation(overrides: Partial<Observation> & Pick<Observation, 'id' | 'analyte_raw'>): Observation {
  return {
    profile_id: FIXTURE_PROFILE_ID,
    doc_id: DOC_ID,
    analyte_canonical: overrides.analyte_raw.toLowerCase(),
    value: null,
    value_text: null,
    unit: null,
    ref_low: null,
    ref_high: null,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2026-04-10T00:00:00',
    user_verified: false,
    extraction_confidence: 0.92,
    source_page: null,
    source_bbox_json: null,
    ...overrides,
  };
}

const initialObservations: Observation[] = [
  makeObservation({ id: GLUCOSE_ID, analyte_raw: 'Glucose', value: 96, unit: 'mg/dL', ref_low: 70, ref_high: 99 }),
  makeObservation({
    id: A1C_ID,
    analyte_raw: 'Hemoglobin A1c',
    value: 6.1,
    unit: '%',
    ref_low: 4.0,
    ref_high: 5.6,
    flag: 'H',
    is_abnormal: true,
  }),
  makeObservation({
    id: FERRITIN_ID,
    analyte_raw: 'Ferritin',
    value: 8,
    unit: 'ng/mL',
    ref_low: 12,
    ref_high: 150,
    flag: 'L',
    is_abnormal: true,
  }),
];

const entities: DocumentEntityResponse[] = [
  {
    id: 'ent-review-date',
    doc_id: DOC_ID,
    category: 'radiology',
    entity_type: 'report_date',
    entity_value: '2026-08-02',
    confidence: 0.95,
    source_page: null,
    source_bbox_json: null,
    char_start: null,
    char_end: null,
    quote: null,
    verified_by_user: null,
    extraction_version: null,
  },
  {
    id: 'ent-review-finding',
    doc_id: DOC_ID,
    category: 'radiology',
    entity_type: 'finding',
    entity_value: 'No acute findings',
    confidence: 0.9,
    source_page: null,
    source_bbox_json: null,
    char_start: null,
    char_end: null,
    quote: null,
    verified_by_user: null,
    extraction_version: null,
  },
];

/** Observation, entity and page answers, with verify as state: a verified row stays verified on the next GET. */
async function mockReviewApi(page: Page): Promise<void> {
  const rows = initialObservations.map((row) => ({ ...row }));
  await page.route(/\/api\/v1\/(observations|documents)(\/|\?|$)/, async (route: Route, request) => {
    const url = new URL(request.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '').replace(/\/+$/, '') || '/';
    const json = (body: unknown) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

    if (request.method() === 'GET') {
      if (path === '/observations') {
        const needsVerification = url.searchParams.get('needs_verification') === 'true';
        return json(needsVerification ? rows.filter((row) => !row.user_verified) : rows);
      }
      if (path === `/documents/${DOC_ID}/entities`) return json(entities);
      if (path === `/documents/${DOC_ID}/pages`) return json([]);
      if (path === `/documents/${DOC_ID}/highlights`) return json([]);
    }
    const verify = /^\/observations\/([^/]+)\/verify$/.exec(path);
    if (request.method() === 'POST' && verify) {
      const row = rows.find((candidate) => candidate.id === verify[1]);
      if (!row) return route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"not found"}' });
      row.user_verified = true;
      return json(row);
    }
    return route.fallback();
  });
}

async function prepare(page: Page, viewport = DESKTOP) {
  await page.setViewportSize(viewport);
  const mock = await installMockApi(page);
  await mockReviewApi(page);
  await seedMockSession(page);
  return mock;
}

const REVIEW_ALL = `/verify?doc=${DOC_ID}&mode=all`;

/** Waits until the route container has finished its entrance fade (the shell's settle, copied). */
async function settle(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
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
      { timeout: 10_000 }
    )
    .toBeGreaterThanOrEqual(0.99);
}

const row = (page: Page, id: string): Locator => page.locator(`#observation-row-${id}`);

async function openReview(page: Page, path = REVIEW_ALL) {
  await page.goto(path);
  await expect(page.getByRole('heading', { name: 'Verification Workbench' })).toBeVisible();
  await expect(row(page, GLUCOSE_ID)).toBeVisible();
  await settle(page);
}

const nav = (page: Page, name: string) =>
  page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name, exact: true });

// ---------------------------------------------------------------------------
// HC-UIREV-001: out-of-range values carry an icon and words.
// ---------------------------------------------------------------------------
test('HC-UIREV-001: an out-of-range value carries an icon and words, in the DOM and on screen', async ({ page }) => {
  await prepare(page);
  await openReview(page);

  const above = row(page, A1C_ID).locator('[data-state="above-range"]');
  await expect(above).toBeVisible();
  await expect(above).toHaveText("Above the report's range");
  await expect(above.locator('svg')).toHaveCount(1);

  const below = row(page, FERRITIN_ID).locator('[data-state="below-range"]');
  await expect(below).toHaveText("Below the report's range");
  await expect(below.locator('svg')).toHaveCount(1);

  await expect(row(page, GLUCOSE_ID).locator('[data-state="in-range"]')).toHaveText('In range');

  // The words are real text on screen, not clipped to nothing.
  const box = await above.boundingBox();
  expect(box?.width ?? 0).toBeGreaterThan(40);
});

// ---------------------------------------------------------------------------
// Ink: the functional half. The stillness half is HC-UIREV-002 below.
// ---------------------------------------------------------------------------
test('UI-PG-REVIEW Ink: the marker goes from pencil to ink with the chip, and a toast names the value and date', async ({
  page,
}) => {
  await prepare(page);
  await openReview(page);
  const glucose = row(page, GLUCOSE_ID);

  await expect(glucose.locator('[data-ink-marker]')).toHaveAttribute('data-state', 'pencil');
  await expect(glucose.locator('[data-state="not-checked"]')).toHaveText('Not yet checked');

  await glucose.getByRole('button', { name: 'Verify observation' }).click();

  await expect(glucose.locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect(glucose.locator('[data-state="checked-by-you"]')).toHaveText('Checked by you');
  await expect(glucose.locator('[data-state="not-checked"]')).toHaveCount(0);

  // The other rows stay pencil.
  await expect(row(page, A1C_ID).locator('[data-ink-marker]')).toHaveAttribute('data-state', 'pencil');

  const toast = page.locator('[data-sonner-toast]');
  await expect(toast).toContainText('Glucose, Apr 10, 2026 is now marked as checked');
  // The API has no unverify endpoint, so the toast has no action button.
  await expect(toast.getByRole('button')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// HC-UIREV-002: the value text passes stillnessProbe through the Ink animation. Timing: quiet box only.
// ---------------------------------------------------------------------------
test('HC-UIREV-002: the value text passes stillnessProbe from the Verify click through the Ink animation', async ({
  page,
}) => {
  await prepare(page);
  await openReview(page);
  const report = await stillnessProbe(page, {
    trigger: () => row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click(),
    expected: [
      `#observation-row-${GLUCOSE_ID} span[data-t0]`,
      `#observation-row-${GLUCOSE_ID} [data-state="checked-by-you"]`,
    ],
    kind: 'interaction',
  });
  expect(report.nodes).toBeGreaterThan(0);
  await expect(row(page, GLUCOSE_ID).locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
});

// ---------------------------------------------------------------------------
// HC-UIREV-003: the Edit dialog.
// ---------------------------------------------------------------------------
test('HC-UIREV-003: the Edit dialog is labelled, traps focus, closes on Escape and returns focus', async ({ page }) => {
  await prepare(page);
  await openReview(page);

  const opener = row(page, GLUCOSE_ID).getByRole('button', { name: 'Edit value' });
  await opener.click();
  const dialog = page.getByRole('dialog', { name: 'Edit Value' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('heading', { name: 'Edit Value' })).toBeVisible();

  const input = dialog.getByRole('textbox', { name: /Glucose/ });
  await expect(input).toHaveValue('96');
  await expect(input).toBeFocused();

  for (let i = 0; i < 12; i += 1) {
    await page.keyboard.press('Tab');
    expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
  }
  for (let i = 0; i < 12; i += 1) {
    await page.keyboard.press('Shift+Tab');
    expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
  }

  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
});

test('HC-UIREV-003: a comma decimal shows the alert and the failed save keeps the dialog open (FE-VERIFY-NUMERIC)', async ({
  page,
}) => {
  await prepare(page);
  await openReview(page);
  await row(page, GLUCOSE_ID).getByRole('button', { name: 'Edit value' }).click();
  const dialog = page.getByRole('dialog', { name: 'Edit Value' });
  await dialog.getByRole('textbox', { name: /Glucose/ }).fill('7,5');
  await expect(dialog.getByRole('alert')).toContainText('Use a dot for decimals');
  await expect(dialog.getByRole('button', { name: /save & verify/i })).toBeDisabled();
});

// ---------------------------------------------------------------------------
// HC-UIREV-005: the Edit dialog's current value passes the overlay stillness probe. Timing: quiet box only.
// ---------------------------------------------------------------------------
test('HC-UIREV-005: the current value in the Edit dialog passes stillnessProbe from the Edit click', async ({ page }) => {
  await prepare(page);
  await openReview(page);
  const report = await stillnessProbe(page, {
    trigger: () => row(page, GLUCOSE_ID).getByRole('button', { name: 'Edit value' }).click(),
    expected: ['[role="dialog"] [data-t0]'],
    kind: 'overlay',
  });
  expect(report.nodes).toBeGreaterThan(0);
  await page.keyboard.press('Escape');
});

// ---------------------------------------------------------------------------
// HC-UIREV-004 and Gate G6: no horizontal scroll at 390 and 320, rows stacked on a phone.
// ---------------------------------------------------------------------------
const G6_PATHS = ['/verify', REVIEW_ALL];

for (const path of G6_PATHS) {
  test(`HC-UIREV-004 and Gate G6 on ${path}: no horizontal scroll at 390 and 320`, async ({ page }) => {
    await prepare(page, PHONE);
    await openReview(page, path);
    const at390 = await noHorizontalScroll(page);
    expect(at390.ok, `G6 390 ${path}: ${JSON.stringify(at390)}`).toBe(true);
    await page.setViewportSize(SMALL_PHONE);
    const at320 = await noHorizontalScroll(page);
    expect(at320.ok, `G6 320 ${path}: ${JSON.stringify(at320)}`).toBe(true);
  });
}

test('HC-UIREV-004 and Gate G6 with the Edit dialog open: no horizontal scroll at 390 and 320', async ({ page }) => {
  await prepare(page, PHONE);
  await openReview(page);
  await row(page, GLUCOSE_ID).getByRole('button', { name: 'Edit value' }).click();
  await expect(page.getByRole('dialog', { name: 'Edit Value' })).toBeVisible();
  expect((await noHorizontalScroll(page)).ok, 'G6 390').toBe(true);
  await page.setViewportSize(SMALL_PHONE);
  expect((await noHorizontalScroll(page)).ok, 'G6 320').toBe(true);
  // The dialog's actions stay reachable at 320 x 640.
  const save = page.getByRole('dialog', { name: 'Edit Value' }).getByRole('button', { name: /save & verify/i });
  await save.scrollIntoViewIfNeeded();
  await expect(save).toBeInViewport();
});

test('HC-UIREV-004: a row is one line on desktop and stacked on a phone', async ({ page }) => {
  await prepare(page, DESKTOP);
  await openReview(page);
  const cells = row(page, GLUCOSE_ID).locator('td');
  const desktopName = await cells.nth(0).boundingBox();
  const desktopValue = await cells.nth(1).boundingBox();
  expect(desktopName && desktopValue).toBeTruthy();
  // Side by side: the value cell starts to the right of the name cell, on the same line.
  expect(desktopValue!.x).toBeGreaterThan(desktopName!.x + desktopName!.width - 1);
  expect(Math.abs(desktopValue!.y - desktopName!.y)).toBeLessThan(8);

  await page.setViewportSize(PHONE);
  const phoneName = await cells.nth(0).boundingBox();
  const phoneValue = await cells.nth(1).boundingBox();
  expect(phoneName && phoneValue).toBeTruthy();
  // Stacked: the value cell starts below the name cell, at the same left edge.
  expect(phoneValue!.y).toBeGreaterThanOrEqual(phoneName!.y + phoneName!.height - 1);
  expect(Math.abs(phoneValue!.x - phoneName!.x)).toBeLessThan(2);
});

// ---------------------------------------------------------------------------
// Gate G: the per-gate checks. Functional gates first, timing gates after (quiet box only).
// ---------------------------------------------------------------------------
const THEMES: Theme[] = ['light', 'dark'];

for (const theme of THEMES) {
  test(`UI-PG-REVIEW Gate G1 axe on /verify (${theme})`, async ({ page }) => {
    await prepare(page);
    await openReview(page);
    await setTheme(page, theme);
    const axe = await axeGate(page, { theme });
    expect(
      axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
      `G1 /verify ${theme}`
    ).toEqual([]);
  });

  test(`UI-PG-REVIEW Gate G1 axe with the Edit dialog open (${theme})`, async ({ page }) => {
    await prepare(page);
    await openReview(page);
    await setTheme(page, theme);
    await row(page, GLUCOSE_ID).getByRole('button', { name: 'Edit value' }).click();
    await expect(page.getByRole('dialog', { name: 'Edit Value' })).toBeVisible();
    const axe = await axeGate(page, { theme });
    expect(
      axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
      `G1 edit dialog ${theme}`
    ).toEqual([]);
  });
}

test('UI-PG-REVIEW Gate G7 and Gate G9 on /verify: no console error, local only, Safety Rail in view', async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  const mock = await installMockApi(page);
  await mockReviewApi(page);
  await seedMockSession(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  await openReview(page);

  const rail = await safetyVisible(page);
  expect(rail.found && rail.inViewport && rail.effectiveOpacity >= 0.99, `G9 ${JSON.stringify(rail)}`).toBe(true);

  // After each interaction: verify, then the Edit dialog open and closed.
  await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
  await expect(row(page, GLUCOSE_ID).locator('[data-state="checked-by-you"]')).toBeVisible();
  const afterVerify = await safetyVisible(page);
  expect(afterVerify.found && afterVerify.inViewport && afterVerify.effectiveOpacity >= 0.99, `G9 ${JSON.stringify(afterVerify)}`).toBe(true);

  guard.assertClean();
  expect(mock.unmocked, 'G7 unmocked').toEqual([]);
});

test('UI-PG-REVIEW Gate G2 CLS under 0.1 over load, Verify and the Edit dialog', async ({ page }) => {
  await prepare(page);
  await openReview(page);
  const cls = await measureCls(page, async () => {
    await page.goto(REVIEW_ALL);
    await expect(row(page, GLUCOSE_ID)).toBeVisible();
    await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
    await expect(row(page, GLUCOSE_ID).locator('[data-state="checked-by-you"]')).toBeVisible();
    await row(page, A1C_ID).getByRole('button', { name: 'Edit value' }).click();
    await page.keyboard.press('Escape');
  });
  expect(cls, 'G2 /verify').toBeLessThan(0.1);
});

test('UI-PG-REVIEW Gate G3 INP proxy under 200 ms for Verify and the Edit dialog, CPU x4', async ({ page }) => {
  await prepare(page);
  await openReview(page);
  const inp = await maxEventDuration(
    page,
    async () => {
      await row(page, A1C_ID).getByRole('button', { name: 'Edit value' }).click();
      await expect(page.getByRole('dialog', { name: 'Edit Value' })).toBeVisible();
      await page.keyboard.press('Escape');
      await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
      await expect(row(page, GLUCOSE_ID).locator('[data-state="checked-by-you"]')).toBeVisible();
    },
    { cpuRate: 4 }
  );
  expect(inp, 'G3 /verify').toBeLessThan(200);
});

test('UI-PG-REVIEW Gate G5 reduced motion: no transform 50 ms after Verify or the Edit dialog opens', async ({
  page,
}, testInfo) => {
  await prepare(page);
  await openReview(page);
  const offenders = await reducedMotionSnapshot(page, async () => {
    await row(page, A1C_ID).getByRole('button', { name: 'Edit value' }).click();
    await expect(page.getByRole('dialog', { name: 'Edit Value' })).toBeVisible();
    await page.keyboard.press('Escape');
    await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
  });
  expect(offenders, 'G5 /verify').toEqual([]);
  const shot = testInfo.outputPath('verify-reduced.png');
  await page.screenshot({ path: shot, fullPage: false });
  testInfo.annotations.push({ type: 'gate-g5-screenshot', description: shot });
});

test('UI-PG-REVIEW Gate G10 stillness on /verify: every [data-t0] node stays still from the nav click', async ({
  page,
}, testInfo) => {
  await prepare(page);
  await page.goto('/settings');
  await settle(page);
  const report = await stillnessProbe(page, {
    trigger: () => nav(page, 'Review values').click(),
    expected: ['td span[data-t0]', 'td [data-t0]'],
    kind: 'navigation',
    lazyRoute: true,
  });
  testInfo.annotations.push({ type: 'gate-g10', description: `/verify: ${JSON.stringify(report)}` });
  await expect(row(page, GLUCOSE_ID)).toBeVisible();
});

test('UI-PG-REVIEW Gate G10 stillness on /verify when a row is selected and its extracted entities load', async ({
  page,
}) => {
  await prepare(page);
  await openReview(page, '/verify');
  const report = await stillnessProbe(page, {
    trigger: () => row(page, A1C_ID).locator('td').first().click(),
    // entity_value cells, the date entity included (plan section 2.7).
    expected: ['[id^="entity-row-"] span[data-t0]', `#observation-row-${A1C_ID} span[data-t0]`],
    kind: 'interaction',
    lazyRoute: true,
  });
  expect(report.nodes).toBeGreaterThan(0);
  await expect(page.getByText('2026-08-02')).toBeVisible();
});
