/**
 * UI-PG-RESULTS (HC-UIRES-001 .. 009, plus gate G on /results and /interpret).
 *
 * Runs on the dev server with the mock API (no backend), as ui-palette.spec.ts does:
 *   PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-results.spec.ts --project=chromium
 *
 * mockApi.ts answers /observations with [] and has an empty CBC panel, so this file adds its own observations, trends,
 * panels and interpretation on top of it (a route registered later wins). Tests whose title carries QUIET-BOX are timing
 * gates (G2, G3, G5, G10): they are written to run, but count as acceptance only on a quiet box.
 *
 * Ids: 001 redirects, 002 the CBC tab, 003 first paint and stillness, 004 DF-4 (the drawn plot on a phone), 005 the
 * closed table of controls, 006 PNG and SVG download, 007 Reported and Read confidence, 008 the tabs, 009 widths
 * between a phone and lg, 010 the break-glass warning in a real browser, 011 an explanation belongs to the result it
 * was made for, 024 no analyte name in browser storage and the reveal replays after a reload (the mock API has no
 * lock endpoint, so the Lock now step is in the unit test HC-UIRES-024).
 *
 * Canonical names in the fixtures are the ones NormalizeModule stores (white_blood_cells, hdl_cholesterol, ...), and
 * the panel fixtures list the analytes a panel should hold for them (see the PANEL_DEFINITIONS note in the PR).
 */

import { expect, test, type Page, type Route } from '@playwright/test';
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
  type AxeViolation,
} from './support/gates';
import { FIXTURE_PROFILE_ID, installMockApi, seedMockSession } from './support/mockApi';
import type { Observation, TrendPoint } from '../src/services/types';

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };
const RAIL = '[data-safety-rail]';
const TAB_BAR = '[aria-label="Tab bar"]';
const SLIDER = 'svg[role="slider"]';
const DISCLAIMER = '[role="note"]';

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

// Glucose first (the default chart). Vitamin D is in none of the four panels.
const OBSERVATIONS: Observation[] = [
  observation({ id: 'g1', value: 92, collected_at: '2026-01-10' }),
  observation({ id: 'g2', value: 118, collected_at: '2026-04-10', user_verified: true }),
  observation({ id: 'hgb', analyte_canonical: 'hemoglobin', analyte_raw: 'Hemoglobin', value: 14.2, unit: 'g/dL', ref_low: 12, ref_high: 17.5, collected_at: '2026-04-10' }),
  observation({ id: 'wbc', analyte_canonical: 'white_blood_cells', analyte_raw: 'WBC Count', value: 7.5, unit: 'K/uL', ref_low: 4.5, ref_high: 11, collected_at: '2026-04-10' }),
  observation({ id: 'hdl', analyte_canonical: 'hdl_cholesterol', analyte_raw: 'HDL Cholesterol', value: 51, ref_low: null, ref_high: null, collected_at: '2026-04-10' }),
  observation({ id: 'ldl', analyte_canonical: 'ldl_cholesterol', analyte_raw: 'LDL Cholesterol', value: 142, ref_low: null, ref_high: null, collected_at: '2026-04-10' }),
  observation({ id: 'vitd', analyte_canonical: 'vitamin_d', analyte_raw: 'Vitamin D', value: 31, unit: 'ng/mL', ref_low: 30, ref_high: 100, collected_at: '2026-04-10' }),
];
const ANALYTE_ROWS = ['Glucose', 'Hemoglobin', 'WBC Count', 'HDL Cholesterol', 'LDL Cholesterol', 'Vitamin D'];

function point(date: string, value: number, unit: string, extra: Partial<TrendPoint> = {}): TrendPoint {
  return { date: `${date}T00:00:00`, value, unit, is_abnormal: false, flag: null, doc_id: 'doc-1', extraction_confidence: null, user_verified: true, ...extra };
}

/** Per analyte: its chart title and the series. Glucose is the seeded UI-review series (92, 104, 118, 101 against 70-99). */
const TRENDS: Record<string, { title: string; unit: string; low: number | null; high: number | null; points: TrendPoint[] }> = {
  glucose: {
    title: 'Glucose',
    unit: 'mg/dL',
    low: 70,
    high: 99,
    points: [
      point('2026-01-10', 92, 'mg/dL', { extraction_confidence: 0.92 }),
      point('2026-02-10', 104, 'mg/dL', { flag: 'H', is_abnormal: true, user_verified: false, extraction_confidence: 0.55 }),
      point('2026-03-10', 118, 'mg/dL', { flag: 'H', is_abnormal: true, original_value: 6.5, original_unit: 'mmol/L', extraction_confidence: 0.3 }),
      point('2026-04-10', 101, 'mg/dL', { flag: 'H', is_abnormal: true, user_verified: false }),
    ],
  },
  hemoglobin: { title: 'Hemoglobin', unit: 'g/dL', low: 12, high: 17.5, points: [point('2026-01-10', 13.5, 'g/dL'), point('2026-04-10', 14.2, 'g/dL')] },
  white_blood_cells: { title: 'WBC chart', unit: 'K/uL', low: 4.5, high: 11, points: [point('2026-01-10', 7.1, 'K/uL'), point('2026-04-10', 7.5, 'K/uL')] },
  hdl_cholesterol: { title: 'HDL chart', unit: 'mg/dL', low: null, high: null, points: [point('2026-01-10', 49, 'mg/dL'), point('2026-04-10', 51, 'mg/dL')] },
  ldl_cholesterol: { title: 'LDL chart', unit: 'mg/dL', low: null, high: null, points: [point('2026-01-10', 140, 'mg/dL'), point('2026-04-10', 142, 'mg/dL')] },
  vitamin_d: { title: 'Vitamin D chart', unit: 'ng/mL', low: 30, high: 100, points: [point('2026-01-10', 28, 'ng/mL'), point('2026-04-10', 31, 'ng/mL')] },
};

const PANEL_MEMBERS: Record<string, string[]> = {
  cbc: ['hgb', 'wbc'],
  cmp: ['g1'],
  lipid: ['hdl', 'ldl'],
  thyroid: [],
};

const STORED_INTERPRETATION = {
  id: 'interp-1',
  observation_id: 'g1',
  interpretation_text: 'Your glucose is a little above the range used on the report.',
  severity_level: 'mild',
  advice_text: 'Ask whether a repeat test makes sense.',
  citations: [{ type: 'knowledge_base', id: 'kb-glucose', text: 'Fasting glucose is compared with the range printed on the report.' }],
  context: null,
  model_id: 'template-v1',
  model_tier: 'template',
  confidence_score: 0.9,
  requires_physician_review: false,
  physician_review_reason: null,
  viewed_at: null,
  created_at: '2026-04-11T00:00:00Z',
};

const PANEL_INTERPRETATION = {
  id: 'panel-1',
  panel_name: 'cbc',
  collected_at: '2026-04-10T00:00:00',
  observation_ids: ['hgb', 'wbc'],
  summary_text: 'Your blood count panel reads as expected on the report.',
  overall_status: 'normal',
  relationship_insights: null,
  advice_text: null,
  citations: [],
  confidence_score: 0.9,
  requires_physician_review: false,
  created_at: '2026-04-11T00:00:00Z',
};

const GROUNDED = {
  interpretation: STORED_INTERPRETATION,
  grounded_segments: [],
  full_response: '**FACTS**\nGlucose was 101 mg/dL on the latest report.',
  insufficient_context: false,
  insufficient_reasons: [],
  verification: { enabled: true, total_claims: 1, verified_claims: 1, failed_claims: 0, faithfulness_score: 1, authority_score: 1, summary: '', issues: [] },
  is_valid: true,
  validation_errors: [],
};

const BREAK_GLASS = { use_external_api: true, provider: 'openai', model: 'gpt-x', api_key_configured: true, redaction_break_glass: true };

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

interface OpenOptions {
  /** Hold the /observations answer until the caller releases it (first paint with the data still to come). */
  holdObservations?: boolean;
  /** Answer GET /interpretations/... with the stored card (default) or leave it out (a 404 logs a console error). */
  interpretation?: 'stored' | 'none';
  observations?: Observation[];
  /** Answer the trend of an analyte from here instead of TRENDS (a different display name, say). */
  trends?: typeof TRENDS;
  /** Answer GET /settings/model/external-api with this (default: the mock's, break-glass off). */
  externalApi?: Record<string, unknown>;
}

/** Opens the app on `route` with the mock API plus this spec's observations, trends, panels and interpretation. */
async function openApp(page: Page, route = '/results', options: OpenOptions = {}) {
  const mock = await installMockApi(page);
  let release: () => void = () => undefined;
  const gate = options.holdObservations ? new Promise<void>((resolve) => (release = resolve)) : Promise.resolve();
  const asked: string[] = [];
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path.includes('/api/v1/')) asked.push(`${request.method()} ${path}`);
  });
  await page.route(/\/api\/v1\/observations\/?(\?.*)?$/, async (r) => {
    if (r.request().method() !== 'GET') return r.fallback();
    await gate;
    return json(r, options.observations ?? OBSERVATIONS);
  });
  await page.route(/\/api\/v1\/observations\/trends\/[^/?]+\/?(\?.*)?$/, (r) => {
    const analyte = new URL(r.request().url()).pathname.replace(/\/+$/, '').split('/').pop() ?? '';
    const fixture = (options.trends ?? TRENDS)[analyte];
    if (r.request().method() !== 'GET' || !fixture) return r.fallback();
    return json(r, {
      analyte_canonical: analyte,
      analyte_display_name: fixture.title,
      unit: fixture.unit,
      ref_low: fixture.low,
      ref_high: fixture.high,
      summary: '',
      data_points: fixture.points,
    });
  });
  await page.route(/\/api\/v1\/observations\/panels\/[^/?]+\/?(\?.*)?$/, (r) => {
    const panel = new URL(r.request().url()).pathname.replace(/\/+$/, '').split('/').pop() ?? '';
    if (r.request().method() !== 'GET' || !(panel in PANEL_MEMBERS)) return r.fallback();
    return json(r, {
      panel_id: panel,
      panel_name: panel.toUpperCase(),
      collection_date: '2026-04-10T00:00:00',
      observations: (options.observations ?? OBSERVATIONS).filter((o) => PANEL_MEMBERS[panel].includes(o.id)),
    });
  });
  await page.route(/\/api\/v1\/interpretations\/panels\/[^/]+\/interpret\/?(\?.*)?$/, (r) =>
    r.request().method() === 'POST' ? json(r, PANEL_INTERPRETATION) : r.fallback()
  );
  await page.route(/\/api\/v1\/interpretations\/observations\/[^/]+\/interpret-grounded\/?(\?.*)?$/, (r) =>
    r.request().method() === 'POST' ? json(r, GROUNDED) : r.fallback()
  );
  if (options.externalApi) {
    await page.route(/\/api\/v1\/settings\/model\/external-api\/?(\?.*)?$/, (r) =>
      r.request().method() === 'GET' ? json(r, options.externalApi) : r.fallback()
    );
  }
  if (options.interpretation !== 'none') {
    await page.route(/\/api\/v1\/interpretations\/observations\/[^/]+\/interpretation\/?(\?.*)?$/, (r) =>
      r.request().method() === 'GET' ? json(r, STORED_INTERPRETATION) : r.fallback()
    );
  }
  await seedMockSession(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  await page.goto(route);
  if (!options.holdObservations) {
    await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
    await page.evaluate(() => document.fonts.ready);
  }
  return { mock, guard, asked, release };
}

const main = (page: Page) => page.getByRole('main');
const list = (page: Page) => page.getByRole('region', { name: /lab results/i });
const listButtons = (page: Page) => list(page).getByRole('button');
const chartTitle = (page: Page) => page.locator('h3 span').first();
const slider = (page: Page) => page.locator(SLIDER);
async function chartUp(page: Page, title = 'Glucose') {
  await expect(chartTitle(page)).toHaveText(title, { timeout: 15_000 });
  await expect(slider(page)).toBeVisible();
}
/** The probe starts from a settled page: fonts loaded and the route fade finished (a probe started mid-fade reads 0.99). */
async function settled(page: Page) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => {
    const container = document.querySelector('[data-route-container]');
    return container !== null && getComputedStyle(container).opacity === '1';
  });
}
const analyteNames = async (page: Page) =>
  (await listButtons(page).allInnerTexts()).map((text) => text.split('\n')[0].replace(/\s+\d.*$/, '').trim());

function describeViolation(v: AxeViolation): string {
  const nodes = v.nodes.slice(0, 3).map((node) => node.target.join(' ')).join(', ');
  return `${v.id}:${v.impact} at ${nodes}`;
}

// ---------------------------------------------------------------------------
// HC-UIRES-001: redirects
// ---------------------------------------------------------------------------

test.describe('HC-UIRES-001 redirects', () => {
  test('/trends?analyte=ldl_cholesterol lands on /results?analyte=ldl_cholesterol and shows LDL', async ({ page }) => {
    await openApp(page, '/trends?analyte=ldl_cholesterol');
    await expect(page).toHaveURL(/\/results\?analyte=ldl_cholesterol$/, { timeout: 15_000 });
    await chartUp(page, 'LDL chart');
  });

  test('/trends lands on /results', async ({ page }) => {
    await openApp(page, '/trends');
    await expect(page).toHaveURL(/\/results$/, { timeout: 15_000 });
    await chartUp(page);
  });

  test('/interpret lands on exactly /results with router state { explain: true }, and the interpretation is up', async ({ page }) => {
    await openApp(page, '/interpret');
    await expect(page).toHaveURL(/\/results$/, { timeout: 15_000 });
    expect(new URL(page.url()).search).toBe('');
    expect(await page.evaluate(() => (history.state as { usr?: unknown } | null)?.usr)).toEqual({ explain: true });
    await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible({ timeout: 15_000 });
  });

  test('/interpret?analyte=ldl_cholesterol keeps the query and opens Explain (router state), on LDL', async ({ page }) => {
    await openApp(page, '/interpret?analyte=ldl_cholesterol');
    await expect(page).toHaveURL(/\/results\?analyte=ldl_cholesterol$/, { timeout: 15_000 });
    expect(await page.evaluate(() => (history.state as { usr?: unknown } | null)?.usr)).toEqual({ explain: true });
    await chartUp(page, 'LDL chart');
    await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible({ timeout: 15_000 });
  });

  for (const redirect of ['/trends', '/interpret']) {
    test(`a redirect replaces the history entry: Back from /results (via ${redirect}) lands on /inbox, and the length did not grow`, async ({ page }) => {
      await openApp(page, '/inbox');
      const lengthBefore = await page.evaluate(() => history.length);
      // A client-side navigation to the old path, as a link to it would make: pushes one entry, which the redirect replaces.
      await page.evaluate((to) => {
        history.pushState({}, '', to);
        window.dispatchEvent(new PopStateEvent('popstate'));
      }, redirect);
      await expect(page).toHaveURL(/\/results$/, { timeout: 15_000 });
      expect(await page.evaluate(() => history.length), 'one entry for the redirect, not two').toBe(lengthBefore + 1);
      await page.goBack();
      // With push instead of replace the entry behind /results is the old path, which redirects straight back to /results.
      await expect(page).toHaveURL(/\/inbox$/);
    });
  }
});

// ---------------------------------------------------------------------------
// HC-UIRES-002 and 008: the tabs
// ---------------------------------------------------------------------------

test.describe('HC-UIRES-002 / 008 tabs', () => {
  test('HC-UIRES-002: the CBC tab lists only CBC analytes, fetches the CBC panel, and the chart is a CBC analyte', async ({ page }) => {
    const { asked } = await openApp(page);
    await chartUp(page);
    expect(await analyteNames(page)).toEqual(ANALYTE_ROWS);
    expect(asked.filter((entry) => entry.includes('/observations/panels/')), 'All makes no panel request').toEqual([]);
    await page.getByRole('tab', { name: /^CBC/ }).click();
    await expect(page.getByRole('tab', { name: /^CBC/ })).toHaveAttribute('aria-selected', 'true');
    await expect.poll(() => analyteNames(page)).toEqual(['Hemoglobin', 'WBC Count']);
    expect(asked).toContain('GET /api/v1/observations/panels/cbc');
    await chartUp(page, 'Hemoglobin');
  });

  test('HC-UIRES-008: an empty panel shows a message, never the unfiltered list; All brings the list back', async ({ page }) => {
    await openApp(page);
    await chartUp(page);
    await page.getByRole('tab', { name: /^Thyroid/ }).click();
    await expect(main(page).getByText(/no results from this panel/i)).toBeVisible();
    await expect(listButtons(page)).toHaveCount(0);
    await page.getByRole('tab', { name: 'All' }).click();
    await expect(listButtons(page)).toHaveCount(ANALYTE_ROWS.length);
  });

  test('HC-UIRES-008: a named ?analyte= resets to All, and an analyte outside the four panels is reachable', async ({ page }) => {
    await openApp(page);
    await chartUp(page);
    await page.getByRole('tab', { name: /^Lipids/ }).click();
    await expect.poll(() => analyteNames(page)).toEqual(['HDL Cholesterol', 'LDL Cholesterol']);
    await page.goto('/results?analyte=vitamin_d');
    await chartUp(page, 'Vitamin D chart');
    await expect(page.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true');
    await expect(list(page).getByRole('button', { name: /Vitamin D/ })).toBeVisible();
  });

  test('HC-UIRES-008: Interpret <panel> Panel shows only with a panel tab selected', async ({ page }) => {
    await openApp(page);
    await chartUp(page);
    await expect(page.getByRole('button', { name: /^Interpret .* Panel$/ })).toHaveCount(0);
    await page.getByRole('tab', { name: /^CMP/ }).click();
    await expect(page.getByRole('button', { name: 'Interpret CMP Panel' })).toBeVisible();
    await page.getByRole('tab', { name: 'All' }).click();
    await expect(page.getByRole('button', { name: /^Interpret .* Panel$/ })).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-003: first paint, and stillness
// ---------------------------------------------------------------------------

test.describe('HC-UIRES-003 first paint', () => {
  test('the disclaimer and the Safety Rail are up before the data arrives, and every value is up once it has', async ({ page }) => {
    const { release } = await openApp(page, '/results', { holdObservations: true });
    await expect(page.getByRole('heading', { level: 1, name: 'Results' })).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(DISCLAIMER)).toBeVisible();
    await expect(page.locator(DISCLAIMER)).toContainText('not medical advice');
    expect(await safetyVisible(page)).toEqual({ found: true, inViewport: true, effectiveOpacity: 1 });
    await expect(listButtons(page)).toHaveCount(0);
    release();
    await chartUp(page);
    await expect(listButtons(page)).toHaveCount(ANALYTE_ROWS.length);
    await expect(page.locator(DISCLAIMER).first()).toBeVisible();
    // Every value on the page is plain text in the DOM: the list values, the latest value, the ribbon's readout and table.
    await expect(list(page).getByText('92 mg/dL')).toBeVisible();
    await expect(page.getByText('Latest value: 101 mg/dL (unverified)')).toBeVisible();
    await expect(page.locator('[data-readout]')).toContainText('101 mg/dL');
    expect(await page.locator('table td[data-t0]').count()).toBeGreaterThan(0);
  });

  test('QUIET-BOX G10: Results is still from the nav click: disclaimer, list values, ribbon text and the rail', async ({ page }) => {
    await openApp(page, '/inbox');
    await page.getByRole('navigation').getByRole('link', { name: 'Results' }).first().click();
    await chartUp(page);
    await page.goto('/inbox');
    await expect(page.locator(RAIL)).toBeVisible();
    await settled(page);
    const report = await stillnessProbe(page, {
      kind: 'navigation',
      lazyRoute: true,
      trigger: async () => {
        await page.getByRole('navigation').getByRole('link', { name: 'Results' }).first().click();
      },
      expected: [`${DISCLAIMER}[data-t0]`, '[role="region"] [data-t0]', '[data-readout]', 'table td[data-t0]', RAIL],
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('QUIET-BOX G10: a tab click, an analyte click and Explain this result are each still from the click', async ({ page }) => {
    await openApp(page);
    await chartUp(page);
    await settled(page);
    const tab = await stillnessProbe(page, {
      trigger: () => page.getByRole('tab', { name: /^Lipids/ }).click(),
      expected: ['[data-readout]', RAIL],
    });
    expect(tab.nodes).toBeGreaterThan(0);
    await page.getByRole('tab', { name: 'All' }).click();
    await chartUp(page);
    await settled(page);
    const row = await stillnessProbe(page, {
      trigger: () => list(page).getByRole('button', { name: /Hemoglobin/ }).click(),
      expected: ['[data-readout]', RAIL],
    });
    expect(row.nodes).toBeGreaterThan(0);
    await chartUp(page, 'Hemoglobin');
    // Scroll the trigger into view first: Playwright would scroll for the click, and that scroll moves every T0 node,
    // so the probe would measure the scroll, not the card (ui-provenance.spec.ts does the same).
    const explainButton = page.getByRole('button', { name: /explain this result/i });
    await explainButton.scrollIntoViewIfNeeded();
    await page.waitForTimeout(150);
    const explain = await stillnessProbe(page, {
      trigger: () => explainButton.click(),
      expected: [`${DISCLAIMER}[data-t0]`, '[data-readout]', RAIL],
    });
    expect(explain.nodes).toBeGreaterThan(0);
    await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-004 (DF-4): the drawn plot on a phone
// ---------------------------------------------------------------------------

interface Drawn {
  limit: number;
  visibleTop: number;
  visibleBottom: number;
  visible: number;
  drawn: number;
  svgHeight: number;
}

/**
 * The drawn band and marks, not the svg element: a svg whose CSS height is forced letterboxes its viewBox, and the
 * element's rect would pass while the plot stayed small. getBoundingClientRect of each [data-band] and [data-marker]
 * is where the browser really put it. The limit is the higher of the tab bar's and the Safety Rail's top edge.
 */
async function drawnPlot(page: Page): Promise<Drawn> {
  return page.evaluate(
    ({ slider, tabBar, rail }) => {
      const svg = document.querySelector(slider) as SVGSVGElement;
      const shapes = Array.from(svg.querySelectorAll('[data-band], [data-marker]')).map((el) => el.getBoundingClientRect());
      const top = Math.min(...shapes.map((r) => r.top));
      const bottom = Math.max(...shapes.map((r) => r.bottom));
      const tabTop = (document.querySelector(tabBar) as HTMLElement | null)?.getBoundingClientRect().top ?? window.innerHeight;
      const railTop = (document.querySelector(rail) as HTMLElement | null)?.getBoundingClientRect().top ?? window.innerHeight;
      const limit = Math.min(tabTop, railTop, window.innerHeight);
      const visibleTop = Math.max(top, 0);
      const visibleBottom = Math.min(bottom, limit);
      return {
        limit,
        visibleTop,
        visibleBottom,
        visible: Math.max(0, visibleBottom - visibleTop),
        drawn: bottom - top,
        svgHeight: svg.getBoundingClientRect().height,
      };
    },
    { slider: SLIDER, tabBar: TAB_BAR, rail: RAIL }
  );
}

test.describe('HC-UIRES-004 (DF-4)', () => {
  test('at 390 x 844, first paint, at least 200 px of the drawn band and marks are above the tab bar and the Safety Rail', async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openApp(page);
    await chartUp(page);
    const drawn = await drawnPlot(page);
    console.log(`DF-4 glucose ${JSON.stringify(drawn)}`);
    expect(
      drawn.visible,
      `visible plot ${drawn.visible.toFixed(1)} px (drawn ${drawn.drawn.toFixed(1)} px from ${drawn.visibleTop.toFixed(1)} to ${drawn.visibleBottom.toFixed(1)}, limit ${drawn.limit.toFixed(1)}, svg ${drawn.svgHeight.toFixed(1)} px)`
    ).toBeGreaterThanOrEqual(200);
    expect(await page.evaluate(() => window.scrollY), 'measured at first paint, unscrolled').toBe(0);
  });

  // The page was first measured on a short title and dated chips. These are the real shapes a patient has: the display
  // name the backend gives BUN, and a first chip with the third "undated" line.
  test('the same holds with the longest real display name, "BUN (Blood Urea Nitrogen)", as the chart title', async ({ page }) => {
    await page.setViewportSize(PHONE);
    const title = 'BUN (Blood Urea Nitrogen)';
    await openApp(page, '/results', { trends: { ...TRENDS, glucose: { ...TRENDS.glucose, title } } });
    await chartUp(page, title);
    const drawn = await drawnPlot(page);
    console.log(`DF-4 long title ${JSON.stringify(drawn)}`);
    expect(drawn.visible, `visible plot ${drawn.visible.toFixed(1)} px (${JSON.stringify(drawn)})`).toBeGreaterThanOrEqual(200);
  });

  test('the same holds when the first chip is undated (the chip grows a third line)', async ({ page }) => {
    await page.setViewportSize(PHONE);
    const undated = OBSERVATIONS.map((o, i) => (i === 0 ? { ...o, collected_at: null } : o));
    await openApp(page, '/results', { observations: undated });
    await chartUp(page);
    await expect(list(page).getByText('undated')).toBeVisible();
    const drawn = await drawnPlot(page);
    console.log(`DF-4 undated first chip ${JSON.stringify(drawn)}`);
    expect(drawn.visible, `visible plot ${drawn.visible.toFixed(1)} px (${JSON.stringify(drawn)})`).toBeGreaterThanOrEqual(200);
  });

  test('the same holds with the long title, an undated first chip and unverified badges together', async ({ page }) => {
    await page.setViewportSize(PHONE);
    const title = 'BUN (Blood Urea Nitrogen)';
    const undated = OBSERVATIONS.map((o, i) => (i === 0 ? { ...o, collected_at: null } : o));
    await openApp(page, '/results', { observations: undated, trends: { ...TRENDS, glucose: { ...TRENDS.glucose, title } } });
    await chartUp(page, title);
    const drawn = await drawnPlot(page);
    console.log(`DF-4 worst case ${JSON.stringify(drawn)}`);
    expect(drawn.visible, `visible plot ${drawn.visible.toFixed(1)} px (${JSON.stringify(drawn)})`).toBeGreaterThanOrEqual(200);
  });

  test('the same holds on another chart with a band (hemoglobin, opened by ?analyte=)', async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openApp(page, '/results?analyte=hemoglobin');
    await chartUp(page, 'Hemoglobin');
    const drawn = await drawnPlot(page);
    console.log(`DF-4 hemoglobin ${JSON.stringify(drawn)}`);
    expect(drawn.visible, `visible plot ${drawn.visible.toFixed(1)} px (${JSON.stringify(drawn)})`).toBeGreaterThanOrEqual(200);
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-005: the closed table of controls
// ---------------------------------------------------------------------------

interface Control {
  label: string;
  match: RegExp;
}

async function controlNames(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    Array.from(
      document.querySelectorAll<HTMLElement>('main button, main [role="tab"], main [role="slider"], main a[href], main input, main select, main [tabindex="0"]')
    ).map((el) => {
      const label = el.getAttribute('aria-label');
      if (label !== null) return label.trim();
      const by = el.getAttribute('aria-labelledby');
      return ((by ? document.getElementById(by)?.textContent : el.textContent) ?? '').trim();
    })
  );
}

async function expectControlSet(page: Page, table: Control[]) {
  const names = await controlNames(page);
  const unmatched = names.filter((name) => table.filter((row) => row.match.test(name)).length !== 1);
  const missing = table.filter((row) => !names.some((name) => row.match.test(name))).map((row) => row.label);
  expect({ unmatched, missing, count: names.length }).toEqual({ unmatched: [], missing: [], count: table.length });
}

const TAB_ROWS: Control[] = [
  { label: 'All', match: /^All$/ },
  { label: 'CBC', match: /^CBC\d*$/ },
  { label: 'CMP', match: /^CMP\d*$/ },
  { label: 'Lipids', match: /^Lipids\d*$/ },
  { label: 'Thyroid', match: /^Thyroid\d*$/ },
];
const ANALYTE_TABLE_ROWS: Control[] = ANALYTE_ROWS.map((name) => ({ label: name, match: new RegExp(`^${name}\\s*\\d`) }));
const COMMON_ROWS: Control[] = [
  { label: 'Lab results scroller', match: /^Lab results$/ },
  { label: 'Download chart as PNG', match: /^Download chart as PNG$/ },
  { label: 'Download chart as SVG', match: /^Download chart as SVG$/ },
  { label: 'Open Explain', match: /^Open Explain$/ },
  { label: 'Ribbon slider', match: /results over time$/ },
];

test.describe('HC-UIRES-005 closed table of controls', () => {
  for (const viewport of [DESKTOP, PHONE]) {
    test(`at ${viewport.width}: the page has exactly the controls in the table, in each of its three states`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openApp(page, '/results', { interpretation: 'none' });
      await chartUp(page);
      await expectControlSet(page, [...TAB_ROWS, ...ANALYTE_TABLE_ROWS, ...COMMON_ROWS, { label: 'Explain this result', match: /^Explain this result$/ }]);

      await page.getByRole('tab', { name: /^CBC/ }).click();
      await expect(page.getByRole('button', { name: 'Interpret CBC Panel' })).toBeVisible();
      await expect(listButtons(page)).toHaveCount(2);
      // The controls are counted once the chart is up: while the trend loads there is no slider yet.
      await chartUp(page, 'Hemoglobin');
      await expectControlSet(page, [
        ...TAB_ROWS,
        ANALYTE_TABLE_ROWS[1],
        ANALYTE_TABLE_ROWS[2],
        ...COMMON_ROWS,
        { label: 'Explain this result', match: /^Explain this result$/ },
        { label: 'Interpret CBC Panel', match: /^Interpret CBC Panel$/ },
      ]);

      await page.getByRole('tab', { name: 'All' }).click();
      await expect(listButtons(page)).toHaveCount(ANALYTE_ROWS.length);
      await chartUp(page);
      await page.getByRole('button', { name: /explain this result/i }).click();
      await expect(page.getByText('No interpretation yet')).toBeVisible();
      await expectControlSet(page, [...TAB_ROWS, ...ANALYTE_TABLE_ROWS, ...COMMON_ROWS, { label: 'Generate Interpretation', match: /^Generate Interpretation$/ }]);

      // The fourth state: a panel with nothing in it. Nothing is selected, so there is no chart to download and nothing
      // to explain; the exports are there but off, and the page does not say "choose a result" with none to choose.
      await page.getByRole('tab', { name: /^Thyroid/ }).click();
      await expect(main(page).getByText(/no results from this panel/i)).toBeVisible();
      await expect(slider(page)).toHaveCount(0);
      await expectControlSet(page, [
        ...TAB_ROWS,
        { label: 'Lab results scroller', match: /^Lab results$/ },
        { label: 'Download chart as PNG', match: /^Download chart as PNG$/ },
        { label: 'Download chart as SVG', match: /^Download chart as SVG$/ },
        { label: 'Open Explain', match: /^Open Explain$/ },
        { label: 'Interpret THYROID Panel', match: /^Interpret THYROID Panel$/ },
      ]);
      await expect(page.getByRole('button', { name: 'Download chart as PNG' })).toBeDisabled();
      await expect(page.getByRole('button', { name: 'Download chart as SVG' })).toBeDisabled();
      await expect(page.getByRole('button', { name: /explain this result/i })).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Generate Interpretation' })).toHaveCount(0);
      await expect(main(page).getByText(/choose a result/i)).toHaveCount(0);
    });
  }

  test('each control does what its name says (desktop)', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openApp(page, '/results', { interpretation: 'none' });
    await chartUp(page);

    for (const [label, count] of [['CBC', 2], ['CMP', 1], ['Lipids', 2], ['Thyroid', 0]] as const) {
      await page.getByRole('tab', { name: new RegExp(`^${label}`) }).click();
      await expect(page.getByRole('tab', { name: new RegExp(`^${label}`) })).toHaveAttribute('aria-selected', 'true');
      await expect(listButtons(page)).toHaveCount(count);
    }
    await page.getByRole('tab', { name: 'All' }).click();
    await expect(listButtons(page)).toHaveCount(ANALYTE_ROWS.length);

    for (const [name, title] of [['Hemoglobin', 'Hemoglobin'], ['WBC Count', 'WBC chart'], ['Vitamin D', 'Vitamin D chart'], ['Glucose', 'Glucose']] as const) {
      await list(page).getByRole('button', { name: new RegExp(`^${name}`) }).click();
      await expect(chartTitle(page)).toHaveText(title);
    }

    const before = Number(await slider(page).getAttribute('aria-valuenow'));
    await slider(page).focus();
    await page.keyboard.press('ArrowLeft');
    await expect(slider(page)).toHaveAttribute('aria-valuenow', String(before - 1));
    await list(page).focus();
    await expect(list(page)).toBeFocused();

    const [png] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download chart as PNG' }).click()]);
    expect(png.suggestedFilename()).toBe('glucose-trend.png');
    const [svg] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download chart as SVG' }).click()]);
    expect(svg.suggestedFilename()).toBe('glucose-trend.svg');

    await page.getByRole('button', { name: /explain this result/i }).click();
    await expect(page.getByText('No interpretation yet')).toBeVisible();
    const generate = page.getByRole('button', { name: 'Generate Interpretation' });
    await expect(generate).toBeEnabled();

    await page.getByRole('button', { name: 'Open Explain' }).click();
    await expect(page).toHaveURL(/\/explain$/, { timeout: 15_000 });
  });

  test('the old dead controls (Last 12 Months, Filters, View Sources) are gone', async ({ page }) => {
    await openApp(page);
    await chartUp(page);
    for (const name of [/last 12 months/i, /^filters$/i, /view sources/i]) {
      await expect(main(page).getByRole('button', { name })).toHaveCount(0);
    }
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-006: PNG and SVG download, in a real browser
// ---------------------------------------------------------------------------

function pngSize(bytes: Buffer): { width: number; height: number } {
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
}

test.describe('HC-UIRES-006 export', () => {
  for (const viewport of [DESKTOP, PHONE]) {
    test(`at ${viewport.width}: PNG is a PNG of the ribbon, SVG holds the slider markup and no var(--)`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openApp(page);
      await chartUp(page);
      const viewBox = (await slider(page).getAttribute('viewBox')) ?? '';
      const [, , vbW, vbH] = viewBox.split(' ').map(Number);

      const [pngDownload] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download chart as PNG' }).click()]);
      expect(pngDownload.suggestedFilename()).toBe('glucose-trend.png');
      const pngPath = await pngDownload.path();
      const fs = await import('node:fs');
      const png = fs.readFileSync(pngPath);
      expect([...png.subarray(0, 8)]).toEqual([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
      const size = pngSize(png);
      expect(size.width / size.height, 'the PNG has the ribbon svg shape').toBeCloseTo(vbW / vbH, 1);

      const [svgDownload] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download chart as SVG' }).click()]);
      expect(svgDownload.suggestedFilename()).toBe('glucose-trend.svg');
      const svg = fs.readFileSync(await svgDownload.path(), 'utf8');
      expect(svg).toContain('role="slider"');
      expect(svg).toContain(`viewBox="0 0 ${vbW} ${vbH}"`);
      expect(svg).toContain(`height="${vbH}"`);
      expect(svg).not.toContain('var(--');
      expect(svg).not.toContain('currentColor');
    });
  }
});

// ---------------------------------------------------------------------------
// HC-UIRES-007: Reported and Read confidence, in the real DOM
// ---------------------------------------------------------------------------

test.describe('HC-UIRES-007 Reported and Read confidence', () => {
  test('a non-latest point shows them in the readout, and every row of the table carries its own', async ({ page }) => {
    await openApp(page);
    await chartUp(page);
    await slider(page).focus();
    await page.keyboard.press('ArrowLeft');
    await expect(page.locator('[data-readout]')).toContainText('Mar 10, 2026: 118 mg/dL · Reported: 6.5 mmol/L · Read confidence: Low');
    await page.keyboard.press('Home');
    await expect(page.locator('[data-readout]')).toContainText('Read confidence: High');
    await expect(page.locator('[data-readout]')).not.toContainText('Reported');
    const cells = await page.locator('table tbody tr td:nth-child(2)').allInnerTexts();
    expect(cells).toEqual([
      '92 mg/dL · Read confidence: High',
      '104 mg/dL · Read confidence: Medium',
      '118 mg/dL · Reported: 6.5 mmol/L · Read confidence: Low',
      '101 mg/dL',
    ]);
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-009: widths between a phone and lg
// ---------------------------------------------------------------------------

test.describe('HC-UIRES-009 widths', () => {
  for (const width of [768, 1023]) {
    test(`at ${width}: no horizontal scroll, and the tall phone ribbon does not balloon`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await openApp(page);
      await chartUp(page);
      expect((await noHorizontalScroll(page)).ok).toBe(true);
      const box = await slider(page).boundingBox();
      expect(box!.width, 'the ribbon is capped').toBeLessThanOrEqual(520);
      expect(box!.height, 'and so is its height').toBeLessThanOrEqual(540);
    });
  }

  test('at lg and above the ribbon is the default 320 x 160', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openApp(page);
    await chartUp(page);
    await expect(slider(page)).toHaveAttribute('viewBox', '0 0 320 160');
  });

  test('crossing lg redraws at the other height', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openApp(page);
    await chartUp(page);
    await page.setViewportSize(PHONE);
    await expect.poll(async () => Number(((await slider(page).getAttribute('viewBox')) ?? '').split(' ')[3])).toBeGreaterThan(160);
  });
});

// ---------------------------------------------------------------------------
// The ribbon in a real browser (inherited from UI-RIBBON, #362)
// ---------------------------------------------------------------------------

test.describe('the ribbon in the page (real browser)', () => {
  test('a pointer press moves the cursor to the nearest point, and no transform is left when the glide ends', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openApp(page);
    await chartUp(page);
    const box = (await slider(page).boundingBox())!;
    const before = await page.locator('[data-cursor]').getAttribute('x1');
    await page.mouse.click(box.x + box.width * 0.05, box.y + box.height / 2);
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '0');
    const after = await page.locator('[data-cursor]').getAttribute('x1');
    expect(after).not.toBe(before);
    await page.waitForTimeout(400);
    expect(await page.locator('[data-cursor]').evaluate((el) => getComputedStyle(el).transform)).toBe('none');
  });

  test('the first visit draws the line with a clip-path animation (Web Animations), and does not replay on a second visit in the session', async ({ page }) => {
    await page.addInitScript(() => {
      const w = window as unknown as { __clip: number };
      w.__clip = 0;
      const animate = Element.prototype.animate;
      Element.prototype.animate = function patched(this: Element, keyframes: Keyframe[] | PropertyIndexedKeyframes | null, options?: number | KeyframeAnimationOptions) {
        if (Array.isArray(keyframes) && keyframes.some((frame) => 'clipPath' in frame)) w.__clip += 1;
        return animate.call(this, keyframes, options);
      };
    });
    // The dev build runs effects twice (StrictMode), so the count is compared between steps, not against a number.
    const clips = () => page.evaluate(() => (window as unknown as { __clip: number }).__clip);
    await openApp(page);
    await chartUp(page);
    const afterGlucose = await clips();
    expect(afterGlucose, 'the first visit to glucose draws the line with a clip-path animation').toBeGreaterThan(0);
    await page.getByRole('tab', { name: /^CBC/ }).click();
    await chartUp(page, 'Hemoglobin');
    const afterHemoglobin = await clips();
    expect(afterHemoglobin, 'a different analyte reveals on its own first visit').toBeGreaterThan(afterGlucose);
    await page.getByRole('tab', { name: 'All' }).click();
    await list(page).getByRole('button', { name: /Glucose/ }).click();
    await chartUp(page);
    expect(await clips(), 'glucose does not reveal twice in one session').toBe(afterHemoglobin);
  });

  test('HC-UIRES-024: after two reveals no storage key or value names the analytes, and a reload reveals again (nothing persists the state)', async ({ page }) => {
    await page.addInitScript(() => {
      const w = window as unknown as { __clip: number };
      w.__clip = 0;
      const animate = Element.prototype.animate;
      Element.prototype.animate = function patched(this: Element, keyframes: Keyframe[] | PropertyIndexedKeyframes | null, options?: number | KeyframeAnimationOptions) {
        if (Array.isArray(keyframes) && keyframes.some((frame) => 'clipPath' in frame)) w.__clip += 1;
        return animate.call(this, keyframes, options);
      };
    });
    const clips = () => page.evaluate(() => (window as unknown as { __clip: number }).__clip);
    // Every key and value of both storages, lower-cased.
    const stored = () =>
      page.evaluate(() => {
        const texts: string[] = [];
        for (const area of [window.sessionStorage, window.localStorage]) {
          for (let i = 0; i < area.length; i += 1) {
            const key = area.key(i) as string;
            texts.push(key, area.getItem(key) ?? '');
          }
        }
        return texts.map((text) => text.toLowerCase());
      });
    const names = ['glucose', 'hemoglobin'];
    await openApp(page);
    await chartUp(page);
    const afterGlucose = await clips();
    expect(afterGlucose, 'glucose revealed').toBeGreaterThan(0);
    await page.getByRole('tab', { name: /^CBC/ }).click();
    await chartUp(page, 'Hemoglobin');
    expect(await clips(), 'hemoglobin revealed').toBeGreaterThan(afterGlucose);

    const texts = await stored();
    expect(texts.length, 'the probe reads the seeded session, so it is not looking at an empty list').toBeGreaterThan(0);
    for (const name of names) {
      expect(texts.filter((text) => text.includes(name)), `no storage key or value contains "${name}"`).toEqual([]);
    }

    // The cost L0 accepted: the state lives in memory, so a reload draws the line again.
    await page.reload();
    await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
    await chartUp(page);
    expect(await clips(), 'after a reload glucose reveals again').toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Gate G on /results (light and dark) and /interpret
// ---------------------------------------------------------------------------

test.describe('gate G', () => {
  for (const theme of ['light', 'dark'] as const) {
    test(`G1: /results has no serious or critical axe violation in ${theme}`, async ({ page }) => {
      await openApp(page);
      await chartUp(page);
      await page.getByRole('button', { name: /explain this result/i }).click();
      await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible();
      await setTheme(page, theme);
      await page.waitForFunction(() =>
        document.getAnimations().every((a) => a.playState === 'finished' || a.effect?.getComputedTiming().iterations === Infinity)
      );
      const { blocking } = await axeGate(page);
      expect(blocking.map(describeViolation), `axe in ${theme}`).toEqual([]);
    });
  }

  for (const route of ['/results', '/interpret']) {
    for (const viewport of [PHONE, SMALL_PHONE]) {
      test(`G6: ${route} has no horizontal scroll at ${viewport.width}`, async ({ page }) => {
        await page.setViewportSize(viewport);
        await openApp(page, route);
        await chartUp(page);
        if (route === '/interpret') await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible();
        const scroll = await noHorizontalScroll(page);
        expect(scroll.ok, `scrollWidth ${scroll.scrollWidth}, innerWidth ${scroll.innerWidth}`).toBe(true);
      });
    }
  }

  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`G1: /interpret has no serious or critical axe violation at ${viewport.width}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openApp(page, '/interpret');
      await chartUp(page);
      await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible();
      const { blocking } = await axeGate(page);
      expect(blocking.map(describeViolation)).toEqual([]);
    });
  }

  test('G7 and G9: /results is a clean page and its Safety Rail is up, before and after Explain', async ({ page }) => {
    const { guard } = await openApp(page);
    await chartUp(page);
    expect(await safetyVisible(page)).toEqual({ found: true, inViewport: true, effectiveOpacity: 1 });
    await page.getByRole('button', { name: /explain this result/i }).click();
    await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible();
    expect(await safetyVisible(page)).toEqual({ found: true, inViewport: true, effectiveOpacity: 1 });
    guard.assertClean();
  });

  test('G7 and G9: /interpret (through the redirect) is a clean page with its Safety Rail up', async ({ page }) => {
    const { guard } = await openApp(page, '/interpret');
    await chartUp(page);
    await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible();
    expect(await safetyVisible(page)).toEqual({ found: true, inViewport: true, effectiveOpacity: 1 });
    guard.assertClean();
  });

  test('the disclaimer is visible without hover or a click, on the loading, loaded and Explain states', async ({ page }) => {
    const { release } = await openApp(page, '/results', { holdObservations: true });
    await expect(page.locator(DISCLAIMER).first()).toBeVisible({ timeout: 15_000 });
    release();
    await chartUp(page);
    await expect(page.locator(DISCLAIMER).first()).toBeVisible();
    await page.getByRole('button', { name: /explain this result/i }).click();
    await expect(page.locator(DISCLAIMER)).toHaveCount(2);
  });

  test('QUIET-BOX G2: layout shift over load, a tab, an analyte, Interpret panel and Explain stays under 0.1', async ({ page }) => {
    await page.setViewportSize(PHONE);
    const total = await measureCls(page, async () => {
      await openApp(page);
      await chartUp(page);
      await page.getByRole('tab', { name: /^CBC/ }).click();
      await chartUp(page, 'Hemoglobin');
      await page.getByRole('button', { name: 'Interpret CBC Panel' }).click();
      await expect(page.getByText('Your blood count panel reads as expected on the report.')).toBeVisible();
      await page.getByRole('tab', { name: 'All' }).click();
      await page.getByRole('button', { name: /explain this result/i }).click();
      await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible();
      await page.getByRole('button', { name: 'Regenerate' }).click();
      await expect(page.getByText('Grounded explanation')).toBeVisible();
    });
    expect(total).toBeLessThan(0.1);
  });

  test('QUIET-BOX G3: the slowest event on this page stays under 200 ms with the CPU slowed x4', async ({ page }) => {
    await openApp(page);
    await chartUp(page);
    const slowest = await maxEventDuration(page, async () => {
      await page.getByRole('tab', { name: /^CBC/ }).click();
      await chartUp(page, 'Hemoglobin');
      await page.getByRole('button', { name: 'Interpret CBC Panel' }).click();
      await expect(page.getByText('Your blood count panel reads as expected on the report.')).toBeVisible();
      await page.getByRole('tab', { name: 'All' }).click();
      await list(page).getByRole('button', { name: /WBC Count/ }).click();
      await chartUp(page, 'WBC chart');
      await page.getByRole('button', { name: /explain this result/i }).click();
      await page.getByRole('button', { name: 'Regenerate' }).click();
      await expect(page.getByText('Grounded explanation')).toBeVisible();
    });
    expect(slowest).toBeLessThan(200);
  });

  for (const theme of ['light', 'dark'] as const) {
    for (const viewport of [PHONE, DESKTOP]) {
      test(`QUIET-BOX G5: reduced motion leaves no transform after each interaction (${theme}, ${viewport.width})`, async ({ page }, testInfo) => {
        await page.setViewportSize(viewport);
        await openApp(page);
        await chartUp(page);
        await setTheme(page, theme);
        // One snapshot per interaction (the gate's "50 ms after each interaction"), each taken after its own action.
        const afterTab = await reducedMotionSnapshot(page, async () => {
          await page.getByRole('tab', { name: /^CBC/ }).click();
          await chartUp(page, 'Hemoglobin');
        });
        const afterPanel = await reducedMotionSnapshot(page, async () => {
          await page.getByRole('button', { name: 'Interpret CBC Panel' }).click();
          await expect(page.getByText('Your blood count panel reads as expected on the report.')).toBeVisible();
        });
        const afterAll = await reducedMotionSnapshot(page, async () => {
          await page.getByRole('tab', { name: 'All' }).click();
          await chartUp(page);
        });
        const afterRow = await reducedMotionSnapshot(page, async () => {
          await list(page).getByRole('button', { name: /Hemoglobin/ }).click();
          await chartUp(page, 'Hemoglobin');
        });
        const afterExplain = await reducedMotionSnapshot(page, async () => {
          await page.getByRole('button', { name: /explain this result/i }).click();
          await expect(page.getByText('Your glucose is a little above the range used on the report.')).toBeVisible();
        });
        const afterRegenerate = await reducedMotionSnapshot(page, async () => {
          await page.getByRole('button', { name: 'Regenerate' }).click();
          await expect(page.getByText('Grounded explanation')).toBeVisible();
        });
        expect({ afterTab, afterPanel, afterAll, afterRow, afterExplain, afterRegenerate }).toEqual({
          afterTab: [],
          afterPanel: [],
          afterAll: [],
          afterRow: [],
          afterExplain: [],
          afterRegenerate: [],
        });
        const screenshot = testInfo.outputPath(`results-${theme}-reduced-${viewport.width}.png`);
        await page.screenshot({ path: screenshot, fullPage: false });
        testInfo.annotations.push({ type: 'gate-g5-screenshot', description: screenshot });
      });
    }
  }
});

// ---------------------------------------------------------------------------
// HC-UIRES-010: the break-glass warning on /results, in a real browser
// ---------------------------------------------------------------------------

test.describe('HC-UIRES-010 break-glass warning', () => {
  const ALERT = '[role="alert"]';

  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`at ${viewport.width}: the alert is in the first viewport above the chart, nothing scrolls sideways, and the DF-4 effect is recorded`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      await openApp(page, '/results', { externalApi: BREAK_GLASS });
      await chartUp(page);
      const alert = page.locator(ALERT).filter({ hasText: /privacy protection override is on/i });
      await expect(alert).toBeVisible();
      const box = (await alert.boundingBox())!;
      const sliderBox = (await slider(page).boundingBox())!;
      expect(box.y, 'in the first viewport').toBeLessThan(viewport.height);
      expect(box.y + box.height, 'above the chart').toBeLessThanOrEqual(sliderBox.y);
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width, 'inside the viewport width').toBeLessThanOrEqual(viewport.width);
      const scroll = await noHorizontalScroll(page);
      expect(scroll.ok, `scrollWidth ${scroll.scrollWidth}, innerWidth ${scroll.innerWidth}`).toBe(true);
      // Recorded, not asserted against the 200 px: the warning is a D12 / BG-WARN-INTERP guarantee and does not get narrower.
      const drawn = await drawnPlot(page);
      console.log(`DF-4 break-glass on, ${viewport.width} wide ${JSON.stringify(drawn)}`);
      testInfo.annotations.push({ type: 'df4-break-glass-visible-plot-px', description: drawn.visible.toFixed(1) });
    });
  }

  for (const theme of ['light', 'dark'] as const) {
    test(`G1: /results with the warning on has no serious or critical axe violation in ${theme}`, async ({ page }) => {
      await openApp(page, '/results', { externalApi: BREAK_GLASS });
      await chartUp(page);
      await expect(page.locator(ALERT).filter({ hasText: /privacy protection override is on/i })).toBeVisible();
      await setTheme(page, theme);
      await page.waitForFunction(() =>
        document.getAnimations().every((a) => a.playState === 'finished' || a.effect?.getComputedTiming().iterations === Infinity)
      );
      const { blocking } = await axeGate(page);
      expect(blocking.map(describeViolation), `axe in ${theme}`).toEqual([]);
    });
  }
});
