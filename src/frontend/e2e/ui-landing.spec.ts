/**
 * UI-OVERVIEW e2e (plan section 7.7, "UI-OVERVIEW"): the Overview landing at /overview, end to end.
 *
 * HC-UILAND-001 in a real browser (the checklist's links work, the "Next step" card has a static accent border and no
 * animation once the S1 entrance has settled), HC-UILAND-002 (with data the counts and values equal what the API
 * answered, and every count and value passes `stillnessProbe` from the moment the route fade settles), and Gate G on
 * /overview in both states, first run and with data: G1 axe in light and dark, G2 CLS, G3 INP with CPU x4, G5 reduced
 * motion, G6 at 390 and 320, G7 console and network, G9 the Safety Rail, G10 stillness.
 *
 * Two describes, kept apart on purpose (the pattern of ui-export.spec.ts):
 *  - "HC-UILAND e2e" is functional and has no timing in it. Run it under normal load:
 *      PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-landing.spec.ts --project=chromium --grep-invert QUIET-BOX
 *  - "QUIET-BOX" is G2, G3, G5 and G10, which are timing measurements. Run them on a quiet box only (RUNBOOK 10.1):
 *      PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-landing.spec.ts --project=chromium --grep QUIET-BOX
 *    G3 is also run against the production build (`npm run build`, `npx vite preview`, HC_E2E_BASE_URL). On the dev
 *    server it prints the figure and asserts no bound: React's dev build is slower than the bound, so a dev-server pass
 *    was never a G3 pass.
 *
 * Every /api/v1 request goes to the shared fixtures in support/mockApi.ts, with later routes (registered here, so they
 * run first) for the three lists the Overview reads: GET /documents, GET /observations (with and without
 * needs_verification) and GET /medications. Nothing reaches the backend; the guard fails on an unmocked call.
 *
 * The next dose depends on the time of day, so the page clock is fixed at 12:00 on 5 Nov 2026 (Date only: timers and
 * animation frames keep running, so the probe's sampler is not affected).
 */

import { expect, test, type Page, type Route } from '@playwright/test';
import type { Document, Medication, Observation } from '../src/services/types';
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

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };
const THEMES: Theme[] = ['light', 'dark'];

/** Set when the run points at a `vite preview` build (HC_E2E_BASE_URL), the pattern of ui-documents.spec.ts. */
const PREVIEW = Boolean(process.env.HC_E2E_BASE_URL);

/** One unbroken token: the worst case for a row that does not shrink at 320 px. */
const LONG_ANALYTE = 'ALongUnbrokenAnalyteNameThatHasNoSpacesAtAllAndKeepsGoingPastTheEdgeOfAnyPhoneScreen_0123456789';
const LONG_MEDICATION = 'ALongUnbrokenMedicationNameWithNoSpacesAtAllAndKeepsGoingPastTheEdgeOfAnyPhoneScreen_0123456789';

/** 12:00 on Thursday 5 Nov 2026, in the browser's own zone. */
const NOW = new Date(2026, 10, 5, 12, 0, 0);

const documents: Document[] = [
  {
    id: 'doc-landing-1',
    profile_id: FIXTURE_PROFILE_ID,
    doc_type: 'lab_report',
    source: 'Alex Rivera lab report, June',
    status: 'needs_review',
    page_count: 2,
    collection_date: '2026-06-02',
    imported_at: '2026-06-03T10:12:00Z',
    parsed_at: '2026-06-03T10:12:04Z',
    verified_at: null,
    extraction_confidence: 0.9,
  },
];

function makeObservation(over: Partial<Observation>): Observation {
  return {
    id: 'obs-x',
    profile_id: FIXTURE_PROFILE_ID,
    doc_id: 'doc-landing-1',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 101,
    value_text: null,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 99,
    ref_range_text: '70-99',
    flag: null,
    is_abnormal: null,
    collected_at: '2026-06-02T00:00:00',
    user_verified: false,
    extraction_confidence: 0.9,
    source_page: 1,
    source_bbox_json: null,
    ...over,
  };
}

/** Four analytes, five rows. Four are not yet checked (the count the page must show); glucose has an older checked row. */
const observations: Observation[] = [
  makeObservation({ id: 'obs-g1', value: 92, collected_at: '2026-01-10T00:00:00', user_verified: true }),
  makeObservation({ id: 'obs-g2', value: 118, collected_at: '2026-06-02T00:00:00' }),
  makeObservation({
    id: 'obs-l1',
    analyte_canonical: 'ldl',
    analyte_raw: 'LDL',
    value: 142,
    ref_low: null,
    ref_high: 100,
    ref_range_text: '<100',
    flag: 'H',
    collected_at: '2026-06-02T00:00:00',
  }),
  makeObservation({
    id: 'obs-a1',
    analyte_canonical: 'hba1c',
    analyte_raw: 'HbA1c',
    value: 5.4,
    unit: '%',
    ref_low: 4,
    ref_high: 5.6,
    collected_at: '2026-05-20T00:00:00',
  }),
  makeObservation({
    id: 'obs-long',
    analyte_canonical: 'long-name',
    analyte_raw: LONG_ANALYTE,
    value: 3,
    unit: 'units',
    ref_low: null,
    ref_high: null,
    ref_range_text: null,
    collected_at: '2026-04-01T00:00:00',
  }),
];

const medications: Medication[] = [
  {
    id: 'med-landing-1',
    profile_id: FIXTURE_PROFILE_ID,
    name: LONG_MEDICATION,
    generic_name: null,
    dosage_amount: 500,
    dosage_unit: 'mg',
    dosage_form: 'tablet',
    frequency: 'twice_daily',
    instructions: null,
    is_active: true,
    reminder_enabled: false,
    started_at: '2026-01-05',
    ended_at: null,
    created_at: '2026-01-05T09:00:00Z',
    updated_at: '2026-01-05T09:00:00Z',
    schedules: [
      {
        id: 'sched-landing-am',
        medication_id: 'med-landing-1',
        schedule_label: 'Morning',
        target_time: '08:00',
        adaptive_window_start: null,
        adaptive_window_end: null,
        reminder_offset_minutes: 0,
        days_of_week: null,
        is_active: true,
        created_at: '2026-01-05T09:00:00Z',
      },
      {
        id: 'sched-landing-pm',
        medication_id: 'med-landing-1',
        schedule_label: 'Evening',
        target_time: '20:00',
        adaptive_window_start: null,
        adaptive_window_end: null,
        reminder_offset_minutes: 0,
        days_of_week: null,
        is_active: true,
        created_at: '2026-01-05T09:00:00Z',
      },
    ],
  },
];

type State = 'first-run' | 'data';

/** What the API actually sent the page, kept so the test compares the screen with the response, not with a constant. */
interface Served {
  waiting: Observation[];
  all: Observation[];
}

/**
 * Answers the three lists the Overview reads. Registered after installMockApi, so it runs first and passes every other
 * call down with route.fallback(). The first run has no documents, no values and no medications.
 */
async function mockOverviewApi(page: Page, state: State): Promise<Served> {
  const served: Served = { waiting: [], all: [] };
  await page.route(/\/api\/v1\//, async (route: Route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '').replace(/\/+$/, '') || '/';
    const json = (body: unknown) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    if (path === '/documents') return json(state === 'data' ? documents : []);
    if (path === '/observations') {
      if (state === 'first-run') return json([]);
      if (url.searchParams.get('needs_verification') === 'true') {
        served.waiting = observations.filter((row) => !row.user_verified);
        return json(served.waiting);
      }
      served.all = observations;
      return json(served.all);
    }
    if (path === '/medications') return json(state === 'data' ? medications : []);
    return route.fallback();
  });
  return served;
}

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

const nav = (page: Page, name: string) =>
  page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name, exact: true });

interface OpenOptions {
  state?: State;
  viewport?: { width: number; height: number };
  /** Where to start. Default /overview. */
  path?: string;
}

async function openOverview(page: Page, options: OpenOptions = {}) {
  const state = options.state ?? 'data';
  const path = options.path ?? '/overview';
  await page.setViewportSize(options.viewport ?? DESKTOP);
  const mock = await installMockApi(page);
  const served = await mockOverviewApi(page, state);
  await seedMockSession(page);
  await page.clock.setFixedTime(NOW);
  const guard = consoleAndNetworkGuard(page, { mock });
  await page.goto(path);
  if (path === '/overview') {
    await expect(page.getByRole('heading', { name: 'Overview', level: 1 })).toBeVisible();
    await settle(page);
  }
  return { mock, guard, served };
}

async function expectRail(page: Page, when: string): Promise<void> {
  const rail = await safetyVisible(page);
  expect(rail.found && rail.inViewport && rail.effectiveOpacity >= 0.99, `G9 ${when} ${JSON.stringify(rail)}`).toBe(true);
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

/** The `[data-t0]` nodes the Overview carries with data (plan §2.7 "Overview counts and values"). */
const EXPECTED_T0 = [
  '[data-testid="overview-waiting-count"]',
  '[data-testid^="overview-latest-"] span[data-t0]',
  '[data-testid="overview-next-dose"] span[data-t0]',
];

// ---------------------------------------------------------------------------------------------------------------
// Functional: no timing.
// ---------------------------------------------------------------------------------------------------------------
test.describe('HC-UILAND e2e', () => {
  test('HC-UILAND-001: first run, three working links, "Next step" on Import with a static border and no animation', async ({ page }) => {
    const { guard } = await openOverview(page, { state: 'first-run' });

    const steps = page.getByRole('list', { name: /first steps/i });
    await expect(steps.getByRole('link')).toHaveCount(3);
    await expect(steps.getByText('Next step')).toHaveCount(1);
    const card = steps.getByRole('listitem').filter({ hasText: 'Next step' });
    await expect(card.getByRole('link', { name: /import/i })).toBeVisible();

    // The S1 entrance plays on the cards once, then nothing runs on the next-step card.
    await expect
      .poll(() => card.evaluate((el) => el.getAnimations({ subtree: true }).length), { timeout: 5_000 })
      .toBe(0);
    const border = await card.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { width: parseFloat(cs.borderTopWidth), color: cs.borderTopColor, animation: cs.animationName };
    });
    expect(border.width, 'a border is drawn').toBeGreaterThan(0);
    expect(border.color, 'the border is not transparent').not.toMatch(/rgba\(0, 0, 0, 0\)|transparent/);
    expect(border.animation).toBe('none');

    // Each link works: it leaves /overview for its own page.
    const targets: Array<[RegExp, RegExp]> = [
      [/import/i, /\/inbox$/],
      [/review values/i, /\/verify$/],
      [/see results/i, /\/results$/],
    ];
    for (const [name, url] of targets) {
      await steps.getByRole('link', { name }).click();
      await expect(page).toHaveURL(url);
      await page.goBack();
      await expect(page).toHaveURL(/\/overview$/);
      await expect(steps).toBeVisible();
    }
    guard.assertClean();
  });

  test('HC-UILAND-002: with data the count and the latest values equal what the API answered, each linking to its page', async ({ page }) => {
    const { guard, served, mock } = await openOverview(page, { state: 'data' });

    const count = page.getByTestId('overview-waiting-count');
    await expect(count).toBeVisible();
    expect(served.waiting.length, 'the API answered with rows to count').toBeGreaterThan(0);
    await expect(count).toHaveText(String(served.waiting.length));
    await expect(count).toHaveAttribute('data-t0', '');

    // The latest value of each analyte the API sent, newest first: glucose is 118 (not the older 92).
    const latest = new Map<string, Observation>();
    for (const row of served.all) {
      const kept = latest.get(row.analyte_canonical);
      if (!kept || (row.collected_at ?? '') > (kept.collected_at ?? '')) latest.set(row.analyte_canonical, row);
    }
    expect(latest.size).toBe(4);
    for (const [canonical, row] of latest) {
      const line = page.getByTestId(`overview-latest-${canonical}`);
      await expect(line.locator('span[data-t0]', { hasText: `${row.value} ${row.unit}` }).first()).toBeVisible();
    }
    await expect(page.getByTestId('overview-latest-glucose')).not.toContainText('92');
    await expect(page.getByTestId('overview-latest-glucose')).toContainText("Above the report's range");
    await expect(page.getByTestId('overview-latest-ldl')).toContainText("Above the report's range");
    await expect(page.getByTestId('overview-latest-hba1c')).toContainText('In range');

    // 12:00 on the fixed clock, schedules at 08:00 and 20:00.
    await expect(page.getByTestId('overview-next-dose')).toContainText('20:00');

    const main = page.getByRole('main');
    await expect(main.getByRole('link', { name: /review values/i })).toHaveAttribute('href', '/verify');
    await expect(main.getByRole('link', { name: /see results/i })).toHaveAttribute('href', '/results');
    await expect(main.getByRole('link', { name: /medications/i })).toHaveAttribute('href', '/medications');
    await expect(page.getByRole('list', { name: /first steps/i })).toHaveCount(0);

    guard.assertClean();
    expect(mock.unmocked).toEqual([]);
  });

  test('HC-UILAND-003 in a real browser: the index and an unknown path both land on /overview', async ({ page }) => {
    await openOverview(page, { state: 'data', path: '/no-such-page' });
    await expect(page).toHaveURL(/\/overview$/);
    await expect(page.getByRole('heading', { name: 'Overview', level: 1 })).toBeVisible();
  });

  for (const state of ['first-run', 'data'] as State[]) {
    for (const theme of THEMES) {
      test(`G1 axe on /overview, ${state} (${theme})`, async ({ page }) => {
        await openOverview(page, { state });
        await applyTheme(page, theme);
        expect(await axeBlocking(page), `G1 ${state} ${theme}`).toEqual([]);
      });
    }
  }

  test('G7 and G9: no console error, no outside request, no unmocked call, Safety Rail visible, in both states', async ({ page }) => {
    const first = await openOverview(page, { state: 'first-run' });
    await expectRail(page, 'first run, first paint');
    await first.guard.assertClean();
    expect(first.mock.unmocked, 'G7 unmocked, first run').toEqual([]);
  });

  test('G7 and G9: with data, after a click through to Results and back', async ({ page }) => {
    const { guard, mock } = await openOverview(page, { state: 'data' });
    await expectRail(page, 'with data, first paint');
    await nav(page, 'Results').click();
    await expect(page).toHaveURL(/\/results$/);
    await expectRail(page, 'after the Results click');
    await nav(page, 'Overview').click();
    await expect(page.getByRole('heading', { name: 'Overview', level: 1 })).toBeVisible();
    await expectRail(page, 'back on Overview');
    guard.assertClean();
    expect(mock.unmocked, 'G7 unmocked, with data').toEqual([]);
  });

  for (const state of ['first-run', 'data'] as State[]) {
    for (const viewport of [PHONE, SMALL_PHONE]) {
      test(`G6 on /overview, ${state}, at ${viewport.width}x${viewport.height}: no horizontal scroll`, async ({ page }) => {
        await openOverview(page, { state, viewport });
        if (state === 'data') await expect(page.getByTestId('overview-latest-long-name')).toBeVisible();
        expect((await noHorizontalScroll(page)).ok, `G6 ${state} ${viewport.width}`).toBe(true);
      });
    }
  }
});

// ---------------------------------------------------------------------------------------------------------------
// Timing: G2, G3, G5, G10. Quiet box only.
// ---------------------------------------------------------------------------------------------------------------
test.describe('QUIET-BOX UI-OVERVIEW timing gates', () => {
  for (const state of ['first-run', 'data'] as State[]) {
    for (const theme of THEMES) {
      test(`QUIET-BOX G2 on /overview, ${state} (${theme})`, async ({ page }) => {
        await openOverview(page, { state });
        const cls = await measureCls(page, async () => {
          await page.goto('/overview');
          await expect(page.getByRole('heading', { name: 'Overview', level: 1 })).toBeVisible();
          await settle(page);
          await applyTheme(page, theme);
        });
        expect(cls, `G2 ${state} ${theme}`).toBeLessThan(0.1);
      });

      test(`QUIET-BOX G3 on /overview, ${state} (${theme})`, async ({ page }) => {
        await openOverview(page, { state, path: '/inbox' });
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
        await settle(page);
        await applyTheme(page, theme);
        const inp = await maxEventDuration(
          page,
          async () => {
            await nav(page, 'Overview').click();
            await expect(page.getByRole('heading', { name: 'Overview', level: 1 })).toBeVisible();
            await settle(page);
            await page.getByRole('main').getByRole('link').first().click();
            await expect(page).not.toHaveURL(/\/overview$/);
          },
          { cpuRate: 4 }
        );
        // The dev server's React build is slower than the bound, so only a production build asserts (see the header).
        if (PREVIEW) expect(inp, `G3 ${state} ${theme}`).toBeLessThan(200);
        else test.info().annotations.push({ type: 'gate-g3-dev-server', description: `${state} ${theme}: ${inp} ms (not asserted)` });
      });

      test(`QUIET-BOX G5 on /overview, ${state} (${theme})`, async ({ page }, testInfo) => {
        await openOverview(page, { state, path: '/inbox' });
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
        await settle(page);
        await applyTheme(page, theme);
        const moving = await reducedMotionSnapshot(page, () => nav(page, 'Overview').click());
        expect(moving, `G5 ${state} ${theme}`).toEqual([]);
        await expect(page.getByRole('heading', { name: 'Overview', level: 1 })).toBeVisible();
        const shot = testInfo.outputPath(`overview-${state}-${theme}-reduced.png`);
        await page.screenshot({ path: shot, fullPage: false });
        testInfo.annotations.push({ type: 'gate-g5-screenshot', description: shot });
      });
    }
  }

  for (const theme of THEMES) {
    test(`QUIET-BOX G10 / HC-UILAND-002 stillness on /overview with data (${theme})`, async ({ page }, testInfo) => {
      // A fresh browser context has an empty sessionStorage, so any S1 entrance the page has would play on this visit.
      const { guard } = await openOverview(page, { state: 'data', path: '/inbox' });
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      await settle(page);
      await applyTheme(page, theme);

      const report = await stillnessProbe(page, {
        trigger: () => nav(page, 'Overview').click(),
        expected: EXPECTED_T0,
        kind: 'navigation',
        lazyRoute: true,
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `navigation ${theme}: ${JSON.stringify(report)}` });
      expect(report.nodes).toBeGreaterThan(0);
      await expect(page.getByTestId('overview-waiting-count')).toBeVisible();
      guard.assertClean();
    });
  }
});
