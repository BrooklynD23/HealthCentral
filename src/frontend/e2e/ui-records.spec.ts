/**
 * UI-PG-RECORDS e2e (plan section 7.7, "UI-PG-RECORDS"): HC-UIPIN-001 (a timeline card names its analytes),
 * HC-UIPIN-002 (pinboard rename and delete use dialogs), HC-UIPIN-003 (the search page shows the query it searched),
 * the M3 enter of the add-to-pinboard menu, and Gate G on /timeline, /search and /pinboards.
 *
 * Two describes of Gate G, kept apart on purpose:
 *  - "Gate G on the records routes" is functional and has no timing in it: G1 (axe, light and dark, including the open
 *    dialogs and the open pin menu), G6 (390 and 320), G7, G9. Run it under normal load:
 *      TMPDIR=/dev/shm npx playwright test e2e/ui-records.spec.ts --project=chromium --grep-invert QUIET-BOX
 *  - "QUIET-BOX" is G2, G3, G5 and G10, which are timing measurements. Run them on a quiet box only (RUNBOOK 10.1);
 *    G3 is also run against the production build (`vite preview`, HC_E2E_BASE_URL). The runnable lines are in the PR body.
 *
 * Every /api/v1 request goes to the shared fixtures in support/mockApi.ts (installMockApi). This spec adds its own
 * routes for /timeline, /observations, /search and /pinboards on top of them: a later page.route wins, and a method it
 * does not answer falls through. The one real-backend case (HC-UIPIN-001, last describe) seeds through the backend's own
 * write routes, because a mock cannot notice an id mismatch between /timeline and /observations.
 */

import { expect, test, type Locator, type Page, type Route } from '@playwright/test';
import type { Pinboard, PinboardItem } from '../src/services/pinboards';
import type { SearchResponse, SearchResult } from '../src/services/search';
import type { TimelineEvent, TimelineResponse } from '../src/services/timeline';
import type { Observation } from '../src/services/types';
import { E2E_API_URL, ensureE2EProfile, openAuthenticatedPage } from './support/auth';
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

// ---------------------------------------------------------------------------------------------------------------
// Fixtures, typed from the services' own types
// ---------------------------------------------------------------------------------------------------------------
const OBS_GLUCOSE = '0b5e0001-1111-4a2b-8c3d-000000000001';
const OBS_LDL = '0b5e0002-1111-4a2b-8c3d-000000000002';
const OBS_A1C = '0b5e0003-1111-4a2b-8c3d-000000000003';
const OBS_LONG = '0b5e0004-1111-4a2b-8c3d-000000000004';
const OBS_UNKNOWN = '0b5e00ff-1111-4a2b-8c3d-0000000000ff';
const DOC_ID = '3b9a1f20-1111-4a2b-8c3d-0000000c4e01';

const LONG_ANALYTE = 'ALongUnbrokenAnalyteNameThatHasNoSpacesAtAllAndKeepsGoingPastTheEdgeOfAnyPhoneScreen0123456789';
const LONG_BOARD = 'AVeryLongPinboardNameWithNoSpacesAtAllThatKeepsGoingPastTheEdgeOfAPhoneScreen_0123456789_0123456789';
const LONG_QUERY = 'glucose'.padEnd(120, 'x');
const UUID_ITEM = '6f1c2a7e-0b3d-4c5e-9a8f-1d2e3f4a5b6c-6f1c2a7e0b3d4c5e9a8f1d2e3f4a5b6c';

function observation(id: string, raw: string, canonical: string): Observation {
  return {
    id,
    profile_id: FIXTURE_PROFILE_ID,
    doc_id: DOC_ID,
    analyte_canonical: canonical,
    analyte_raw: raw,
    value: 95,
    value_text: null,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 99,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2026-03-14T00:00:00',
    user_verified: true,
    extraction_confidence: 0.92,
    source_page: 1,
    source_bbox_json: null,
  };
}

const OBSERVATIONS: Observation[] = [
  observation(OBS_GLUCOSE, 'Glucose', 'glucose'),
  observation(OBS_LDL, 'LDL', 'ldl_cholesterol'),
  observation(OBS_A1C, 'HbA1c', 'hemoglobin_a1c'),
  observation(OBS_LONG, LONG_ANALYTE, 'long_analyte'),
];

function labEvent(over: Partial<TimelineEvent> & Pick<TimelineEvent, 'event_id' | 'title' | 'related_ids'>): TimelineEvent {
  return {
    event_type: 'lab_results',
    event_date: '2026-03-14',
    event_date_source: 'recorded_date',
    doc_id: DOC_ID,
    verification_status: 'verified',
    ...over,
  };
}

const TITLE_TWO = 'Lab results (2 analytes)';
const TITLE_ONE = 'Lab results (1 analyte)';
const TITLE_LONG = 'Lab results (1 analyte) with a long name';

const TIMELINE: TimelineResponse = {
  events: [
    labEvent({ event_id: 'lab:a', title: TITLE_TWO, related_ids: [OBS_GLUCOSE, OBS_LDL, OBS_UNKNOWN] }),
    labEvent({
      event_id: 'lab:b',
      title: TITLE_ONE,
      related_ids: [OBS_A1C],
      event_date: '2026-02-01',
      verification_status: 'unverified',
    }),
    labEvent({ event_id: 'lab:c', title: TITLE_LONG, related_ids: [OBS_LONG], event_date: '2026-01-20' }),
    {
      event_id: 'doc:d',
      event_type: 'imaging',
      event_date: '2026-01-05',
      event_date_source: 'document_date',
      title: 'Chest X-ray',
      doc_id: DOC_ID,
      related_ids: [],
      verification_status: 'n/a',
    },
  ],
  undated: [],
};

function result(over: Partial<SearchResult> & Pick<SearchResult, 'id' | 'title'>): SearchResult {
  return {
    type: 'entity',
    doc_id: DOC_ID,
    snippet: `The record says ${over.title.toLowerCase()} was noted.`,
    date: '2026-03-14',
    verified_status: 'unverified',
    category: 'lab',
    highlight_types: [],
    ...over,
  };
}

function searchFor(q: string): SearchResponse {
  if (q === 'nothing') return { results: [], count: 0 };
  const results: SearchResult[] = q.startsWith('glucose')
    ? [
        result({ id: 'e-1', title: 'Glucose 118 mg/dL' }),
        result({ id: 'd-1', title: 'Lab report, March', type: 'document', verified_status: 'verified', snippet: 'Fasting panel' }),
        result({
          id: 'o-1',
          title: 'Glucose',
          type: 'observation',
          snippet: `Value ${LONG_ANALYTE} ${LONG_ANALYTE}`,
        }),
      ]
    : [result({ id: 'e-9', title: `Match for ${q}` })];
  return { results, count: results.length };
}

const BOARD_A = '5a7e0001-1111-4a2b-8c3d-0000000000a1';
const BOARD_B = '5a7e0002-1111-4a2b-8c3d-0000000000b2';

function boardsFixture(): Pinboard[] {
  return [
    { id: BOARD_A, name: 'Visit prep', created_at: '2026-03-01T00:00:00', updated_at: '2026-03-01T00:00:00' },
    { id: BOARD_B, name: LONG_BOARD, created_at: '2026-03-02T00:00:00', updated_at: '2026-03-02T00:00:00' },
  ];
}

const ITEMS: Record<string, PinboardItem[]> = {
  [BOARD_A]: [
    { id: 'it-1', pinboard_id: BOARD_A, item_type: 'observation', item_id: UUID_ITEM, created_at: '2026-03-03T00:00:00' },
    { id: 'it-2', pinboard_id: BOARD_A, item_type: 'document', item_id: DOC_ID, created_at: '2026-03-03T00:00:01' },
  ],
  [BOARD_B]: [],
};

interface RecordsControl {
  boards: Pinboard[];
  patches: Array<{ id: string; name: string }>;
  deletes: string[];
  searches: string[];
  /** The next PATCH / DELETE is refused with a 500. */
  failNextPatch: boolean;
  failNextDelete: boolean;
  /** While set, GET /observations/ waits for it (or answers 500 when `observationsFail`). */
  observationsGate: Promise<void> | null;
  observationsFail: boolean;
}

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

/**
 * The records API for this spec. Registered after installMockApi, so it answers first; any method it does not
 * handle falls through to the shared mock.
 */
async function mockRecords(page: Page): Promise<RecordsControl> {
  const control: RecordsControl = {
    boards: boardsFixture(),
    patches: [],
    deletes: [],
    searches: [],
    failNextPatch: false,
    failNextDelete: false,
    observationsGate: null,
    observationsFail: false,
  };

  await page.route(/\/api\/v1\/timeline\/?(\?.*)?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    return json(route, TIMELINE);
  });

  await page.route(/\/api\/v1\/observations\/?(\?.*)?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    if (control.observationsGate) await control.observationsGate;
    if (control.observationsFail) return json(route, { detail: 'refused' }, 500);
    return json(route, OBSERVATIONS);
  });

  await page.route(/\/api\/v1\/search\/?(\?.*)?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    const q = new URL(request.url()).searchParams.get('q') ?? '';
    control.searches.push(q);
    return json(route, searchFor(q));
  });

  await page.route(/\/api\/v1\/pinboards\/?(\?.*)?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    return json(route, control.boards);
  });

  await page.route(/\/api\/v1\/pinboards\/([^/?]+)\/items\/?(\?.*)?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    const id = /\/pinboards\/([^/?]+)\/items/.exec(new URL(request.url()).pathname)![1];
    return json(route, ITEMS[id] ?? []);
  });

  await page.route(/\/api\/v1\/pinboards\/([^/?]+)\/?(\?.*)?$/, async (route, request) => {
    const id = /\/pinboards\/([^/?]+)/.exec(new URL(request.url()).pathname)![1];
    const board = control.boards.find((b) => b.id === id);
    if (request.method() === 'PATCH') {
      const body = request.postDataJSON() as { name: string };
      control.patches.push({ id, name: body.name });
      if (control.failNextPatch) {
        control.failNextPatch = false;
        return json(route, { detail: 'refused' }, 500);
      }
      if (!board) return json(route, { detail: 'Not found' }, 404);
      board.name = body.name;
      return json(route, board);
    }
    if (request.method() === 'DELETE') {
      control.deletes.push(id);
      if (control.failNextDelete) {
        control.failNextDelete = false;
        return json(route, { detail: 'refused' }, 500);
      }
      control.boards = control.boards.filter((b) => b.id !== id);
      return route.fulfill({ status: 204 });
    }
    return route.fallback();
  });

  return control;
}

// ---------------------------------------------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------------------------------------------
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

/** The shared mock, the session and the records API. Call before the first navigation. */
async function setup(page: Page, viewport = DESKTOP) {
  await page.setViewportSize(viewport);
  const mock = await installMockApi(page);
  await seedMockSession(page);
  const control = await mockRecords(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  return { mock, control, guard };
}

/** window.prompt and window.confirm throw: a page that still calls them fails its own flow and the console guard. */
async function stubNativeDialogs(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.prompt = () => {
      throw new Error('window.prompt must not be called');
    };
    window.confirm = () => {
      throw new Error('window.confirm must not be called');
    };
  });
}

async function openTimeline(page: Page): Promise<void> {
  await page.goto('/timeline');
  await expect(page.getByRole('heading', { name: 'Timeline', level: 1 })).toBeVisible();
  await expect(page.getByText(TITLE_TWO, { exact: true })).toBeVisible();
  await settle(page);
}

async function openSearch(page: Page, query = 'glucose'): Promise<void> {
  await page.goto(query ? `/search?q=${encodeURIComponent(query)}` : '/search');
  await expect(page.getByRole('heading', { name: 'Search records', level: 1 })).toBeVisible();
  if (query === 'glucose') await expect(page.getByRole('heading', { name: 'Glucose 118 mg/dL' })).toBeVisible();
  await settle(page);
}

async function openPinboards(page: Page): Promise<void> {
  await page.goto('/pinboards');
  await expect(page.getByRole('heading', { name: 'Pinboards', level: 1 })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Rename', exact: true })).toBeVisible();
  await expect(page.locator('[data-pinboard-item-id]').first()).toBeVisible();
  await settle(page);
}

const cardOf = (page: Page, title: string): Locator => page.locator('li').filter({ hasText: title }).first();
const renameDialog = (page: Page) => page.getByRole('dialog', { name: 'Rename pinboard' });
const deleteDialog = (page: Page) => page.getByRole('alertdialog');
const renameButton = (page: Page) => page.getByRole('button', { name: 'Rename', exact: true });
const deleteButton = (page: Page) => page.getByRole('button', { name: 'Delete pinboard', exact: true });
const pinButton = (page: Page, title = TITLE_TWO) => page.getByRole('button', { name: `Add ${title} to pinboard` });

async function applyTheme(page: Page, theme: Theme): Promise<void> {
  await setTheme(page, theme);
  // Two frames so the style change has started its transitions before they are counted.
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await page.waitForFunction(() => document.getAnimations().filter((a) => a instanceof CSSTransition).length === 0);
}

async function axeBlocking(page: Page): Promise<string[]> {
  const axe = await axeGate(page);
  return axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);
}

/**
 * Waits until the element's effective opacity (its own times every ancestor's) is 1, so an axe scan never reads a
 * half-faded surface: an EmptyState's action rises in an S1 group, and a dialog fades in.
 */
async function opaque(locator: Locator): Promise<void> {
  await expect
    .poll(
      () =>
        locator.evaluate((el) => {
          let opacity = 1;
          for (let node: Element | null = el; node; node = node.parentElement) {
            opacity *= parseFloat(getComputedStyle(node).opacity);
          }
          return opacity;
        }),
      { timeout: 5_000 }
    )
    .toBeGreaterThanOrEqual(0.99);
}

async function expectRail(page: Page, when: string): Promise<void> {
  const rail = await safetyVisible(page);
  expect(rail.found, `${when}: rail found`).toBe(true);
  expect(rail.inViewport, `${when}: rail in viewport`).toBe(true);
  expect(Math.abs(rail.effectiveOpacity - 1), `${when}: rail opacity`).toBeLessThan(0.01);
}

/** Opens the pin menu on the first lab card and waits for the board names. */
async function openPinMenu(page: Page): Promise<Locator> {
  await pinButton(page).click();
  const menu = page.getByRole('menu');
  await expect(menu.getByRole('menuitem', { name: 'Visit prep' })).toBeVisible();
  await opaque(menu);
  return menu;
}

// ---------------------------------------------------------------------------------------------------------------
// HC-UIPIN-001: a timeline card names its analytes.
// ---------------------------------------------------------------------------------------------------------------
test.describe('HC-UIPIN-001 timeline analytes', () => {
  test.use({ viewport: DESKTOP });

  test('HC-UIPIN-001: each lab card names its analytes under the backend title; the title text is unchanged', async ({ page }) => {
    // Would not notice: names under the wrong card, a duplicate or an id printed for an id with no observation, a
    // changed backend title (TW4-TIMELINE reads "Lab results (" and the real card would lose it).
    // RED today: no card names an analyte ("1 analyte" is all it says).
    await setup(page);
    await openTimeline(page);

    for (const [title, names] of [
      [TITLE_TWO, 'Glucose, LDL'],
      [TITLE_ONE, 'HbA1c'],
      [TITLE_LONG, LONG_ANALYTE],
    ] as const) {
      const card = cardOf(page, title);
      await expect(card.locator('[data-timeline-analytes]')).toHaveText(names);
      // The names sit below the title, in the same text column.
      const titleBox = await card.getByText(title, { exact: true }).boundingBox();
      const namesBox = await card.locator('[data-timeline-analytes]').boundingBox();
      expect(namesBox!.y, `${title}: names under the title`).toBeGreaterThan(titleBox!.y);
    }
    await expect(cardOf(page, 'Chest X-ray').locator('[data-timeline-analytes]')).toHaveCount(0);
    await expect(page.getByText(OBS_UNKNOWN)).toHaveCount(0);
    await expect(page.locator('[data-timeline-date]').first()).toHaveAttribute('data-t0');
    await expect(page.locator('[data-timeline-analytes]').first()).toHaveAttribute('data-t0');
    await expect(page.locator('[data-timeline-verification]').first()).toHaveAttribute('data-t0');
  });

  test('HC-UIPIN-001: the first card that paints already has its names (no card is added to, and none moves)', async ({ page }) => {
    // Would not notice: cards that paint at once and gain a line when the observations arrive, so every later card
    // moves (G2, G10). The observations are held 600 ms after the timeline has answered. A MutationObserver records
    // how many name lines exist at the first moment any card exists.
    // RED today: the first card paints with no names.
    const { control } = await setup(page);
    let release!: () => void;
    control.observationsGate = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.addInitScript(() => {
      const w = window as unknown as { __firstCard?: { cards: number; names: number } };
      new MutationObserver(() => {
        if (w.__firstCard) return;
        const cards = document.querySelectorAll('[data-timeline-date]').length;
        if (cards > 0) w.__firstCard = { cards, names: document.querySelectorAll('[data-timeline-analytes]').length };
      }).observe(document, { childList: true, subtree: true });
    });
    await page.goto('/timeline');
    await expect(page.getByRole('heading', { name: 'Timeline', level: 1 })).toBeVisible();
    await page.waitForTimeout(600);
    await expect(page.locator('[data-timeline-date]')).toHaveCount(0);
    release();
    await expect(page.getByText(TITLE_TWO, { exact: true })).toBeVisible();
    const first = await page.evaluate(() => (window as unknown as { __firstCard?: { cards: number; names: number } }).__firstCard);
    expect(first?.cards, 'every card paints in one step').toBe(4);
    expect(first?.names, 'with its names').toBe(3);
  });

  test('HC-UIPIN-001: when the observations fail, the cards still show, with the backend title and no names', async ({ page }) => {
    // Would not notice: a timeline hidden, or an error shown, because a second query failed. The app retries a failed
    // query once after one second, so the cards appear then.
    // RED today: passes the "cards show" half only; the page never asks for the observations.
    const { control } = await setup(page);
    control.observationsFail = true;
    const asked: string[] = [];
    page.on('request', (request) => {
      if (/\/api\/v1\/observations\/?(\?|$)/.test(request.url())) asked.push(request.url());
    });
    await page.goto('/timeline');
    await expect(page.getByText(TITLE_TWO, { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('[data-timeline-analytes]')).toHaveCount(0);
    await expect(page.getByRole('alert')).toHaveCount(0);
    expect(asked.length, 'the observations were asked for').toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------------------------------------------
// HC-UIPIN-003: the search page shows the query it searched.
// ---------------------------------------------------------------------------------------------------------------
test.describe('HC-UIPIN-003 search', () => {
  test.use({ viewport: DESKTOP });

  test('HC-UIPIN-003: the echo shows the searched query, not the draft; Enter replaces it and the results', async ({ page }) => {
    // Would not notice: an echo read from the input, or one that does not follow a second search.
    // RED today: no echo.
    const { control } = await setup(page);
    await openSearch(page);
    const echo = page.locator('[data-search-query]');
    await expect(echo).toHaveText('Searched for “glucose”');

    const box = page.getByRole('searchbox', { name: 'Search health records' });
    await box.fill('glucose draft not sent');
    await expect(echo).toHaveText('Searched for “glucose”');
    await box.press('Enter');
    await expect(echo).toHaveText('Searched for “glucose draft not sent”');
    await expect(page.getByRole('heading', { name: 'Glucose 118 mg/dL' })).toBeVisible();
    expect(control.searches.at(-1)).toBe('glucose draft not sent');
  });

  test('HC-UIPIN-003: zero results and a refused search both keep the echo; Try again recovers', async ({ page }) => {
    // Would not notice: an echo in the results branch only; a Try again that does not ask again.
    // RED today: no echo, no Try again.
    await setup(page);
    await openSearch(page, 'nothing');
    await expect(page.locator('[data-search-query]')).toHaveText('Searched for “nothing”');
    await expect(page.getByRole('heading', { name: 'No matching records' })).toBeVisible();

    let refuse = true;
    await page.route(/\/api\/v1\/search\/?(\?.*)?$/, (route, request) => {
      if (request.method() === 'GET' && refuse) return json(route, { detail: 'refused' }, 500);
      return route.fallback();
    });
    await page.getByRole('searchbox', { name: 'Search health records' }).fill('glucose');
    await page.getByRole('searchbox', { name: 'Search health records' }).press('Enter');
    const alert = page.getByRole('alert');
    await expect(alert).toContainText('Could not search records', { timeout: 15_000 });
    await expect(page.locator('[data-search-query]')).toHaveText('Searched for “glucose”');
    refuse = false;
    await page.getByRole('button', { name: 'Try again' }).click();
    await expect(page.getByRole('heading', { name: 'Glucose 118 mg/dL' })).toBeVisible();
  });

  test('HC-UIPIN-003: a result is one whole-card link: a click on the snippet follows it; hover and focus show', async ({ page }) => {
    // Would not notice: a stretched link that does not stretch (a click on the snippet does nothing), a hover that
    // changes nothing, a focused link with no visible ring, or a card that moves (Card variant="interactive").
    // RED today: only the link text is clickable and the card has no hover or focus style.
    await setup(page);
    await openSearch(page);
    const card = page.locator('[data-search-result]').first();
    const snippet = card.locator('[data-search-snippet]');

    const restBg = await card.evaluate((el) => getComputedStyle(el).backgroundColor);
    const restRect = await card.boundingBox();
    await card.hover();
    await expect
      .poll(() => card.evaluate((el) => getComputedStyle(el).backgroundColor), { message: 'hover changes the background' })
      .not.toBe(restBg);
    const hoverRect = await card.boundingBox();
    expect(hoverRect, 'a hover moves nothing').toEqual(restRect);

    const link = card.getByRole('link', { name: 'Review extraction' });
    await link.focus();
    await expect
      .poll(() => card.evaluate((el) => getComputedStyle(el).boxShadow), { message: 'focus shows a ring on the card' })
      .not.toBe('none');

    // A real pointer click at the snippet's centre: Playwright's own click() refuses a target that another element
    // (here, the stretched link) covers, which is the point.
    const at = (await snippet.boundingBox())!;
    await page.mouse.click(at.x + at.width / 2, at.y + at.height / 2);
    await expect(page).toHaveURL(/\/verify$/);
  });

  test('HC-UIPIN-003: the input follows the URL when it changes on the same page (the palette on /search)', async ({ page }) => {
    // Would not notice: the box keeping its first text after the palette sends /search?q=...; the next Enter would
    // search the old query. The palette is driven for real: open it on /search, type free text, Enter.
    // RED today: the box keeps "glucose".
    await setup(page);
    await openSearch(page);
    await page.getByRole('banner').getByRole('button', { name: /search/i }).click();
    const palette = page.getByRole('dialog').getByRole('combobox');
    await palette.pressSequentially('cholesterol check');
    await palette.press('Enter');
    await expect(page).toHaveURL(/\/search\?q=cholesterol\+check$/);
    await expect(page.getByRole('searchbox', { name: 'Search health records' })).toHaveValue('cholesterol check');
    await expect(page.locator('[data-search-query]')).toHaveText('Searched for “cholesterol check”');
  });

  test('HC-UIPIN-003: the empty search focuses the box; "Clear search and filters" clears the query and the filters', async ({ page }) => {
    // Would not notice: an action that leaves a filter set, or one that leaves focus on <body>.
    // RED today: neither empty state has an action.
    await setup(page);
    await openSearch(page, '');
    await page.getByRole('button', { name: 'Start a search' }).click();
    await expect(page.getByRole('searchbox', { name: 'Search health records' })).toBeFocused();

    await openSearch(page, 'nothing');
    await page.getByLabel('Provider').fill('Dr Who');
    await page.getByLabel('Category').selectOption('lab');
    await page.getByRole('button', { name: 'Clear search and filters' }).click();
    await expect(page).toHaveURL(/\/search$/);
    await expect(page.getByLabel('Provider')).toHaveValue('');
    await expect(page.getByLabel('Category')).toHaveValue('');
    await expect(page.getByRole('searchbox', { name: 'Search health records' })).toBeFocused();
  });
});

// ---------------------------------------------------------------------------------------------------------------
// HC-UIPIN-002: pinboard rename and delete use dialogs.
// ---------------------------------------------------------------------------------------------------------------
test.describe('HC-UIPIN-002 pinboards', () => {
  test.use({ viewport: DESKTOP });

  test('HC-UIPIN-002: Rename and Delete complete through the dialogs, with window.prompt and window.confirm throwing', async ({ page }) => {
    // Would not notice: a dialog that sends the old or an untrimmed name, a Cancel or Escape that sends something,
    // a focus dropped on <body>. The PATCH and the DELETE are read at the mock, with the real Radix dialogs.
    // RED today: window.prompt throws on the first Rename click and nothing is sent.
    const { control, guard } = await setup(page);
    await stubNativeDialogs(page);
    await openPinboards(page);

    // Cancel and Escape send nothing and give focus back.
    await renameButton(page).click();
    const dialog = renameDialog(page);
    await expect(dialog.getByLabel('Pinboard name')).toHaveValue('Visit prep');
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await expect(dialog).toHaveCount(0);
    await expect(renameButton(page)).toBeFocused();
    await renameButton(page).click();
    await expect(dialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(renameButton(page)).toBeFocused();
    expect(control.patches).toEqual([]);

    // Rename completes, with the name trimmed.
    await renameButton(page).click();
    await dialog.getByLabel('Pinboard name').fill('  Cardiology visit  ');
    await dialog.getByRole('button', { name: 'Save' }).click();
    await expect(dialog).toHaveCount(0);
    expect(control.patches).toEqual([{ id: BOARD_A, name: 'Cardiology visit' }]);
    await expect(page.getByRole('heading', { name: 'Cardiology visit' })).toBeVisible();

    // Delete: Cancel sends nothing, Delete sends one DELETE for the board that was open.
    await deleteButton(page).click();
    await expect(deleteDialog(page)).toContainText('Cardiology visit');
    await expect(deleteDialog(page).getByRole('button', { name: 'Cancel' })).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(deleteDialog(page)).toHaveCount(0);
    await expect(deleteButton(page)).toBeFocused();
    expect(control.deletes).toEqual([]);
    await deleteButton(page).click();
    await deleteDialog(page).getByRole('button', { name: 'Delete', exact: true }).click();
    await expect(deleteDialog(page)).toHaveCount(0);
    expect(control.deletes).toEqual([BOARD_A]);
    await expect(page.getByRole('button', { name: 'Cardiology visit' })).toHaveCount(0);
    await expect(deleteButton(page)).toBeFocused();
    guard.assertClean();
  });

  test('HC-UIPIN-002: a refused rename and a refused delete keep their dialogs open with an alert, and the retry completes', async ({ page }) => {
    // Would not notice: a dialog that closes on a refused request, so the patient's change is lost without a word.
    // RED today: window.prompt throws and nothing is sent.
    const { control } = await setup(page);
    await stubNativeDialogs(page);
    await openPinboards(page);

    control.failNextPatch = true;
    await renameButton(page).click();
    await renameDialog(page).getByLabel('Pinboard name').fill('Second try');
    await renameDialog(page).getByRole('button', { name: 'Save' }).click();
    await expect(renameDialog(page).getByRole('alert')).toContainText('Could not rename');
    await expect(renameDialog(page).getByLabel('Pinboard name')).toHaveValue('Second try');
    await renameDialog(page).getByRole('button', { name: 'Save' }).click();
    await expect(renameDialog(page)).toHaveCount(0);
    expect(control.patches.map((p) => p.name)).toEqual(['Second try', 'Second try']);

    control.failNextDelete = true;
    await deleteButton(page).click();
    await deleteDialog(page).getByRole('button', { name: 'Delete', exact: true }).click();
    await expect(deleteDialog(page).getByRole('alert')).toContainText('Could not delete');
    expect(control.boards.map((b) => b.id)).toContain(BOARD_A);
    await deleteDialog(page).getByRole('button', { name: 'Delete', exact: true }).click();
    await expect(deleteDialog(page)).toHaveCount(0);
    expect(control.deletes).toEqual([BOARD_A, BOARD_A]);
  });

  test('HC-UIPIN-002: pinned items carry data-t0 on label and id; a UUID item and a long board name stay inside the page at 320', async ({ page }) => {
    // Would not notice: an unbroken id or board name that pushes the page wider than the phone (G6).
    // RED today: no data-t0 on the items, and the long name has no wrap class.
    await setup(page, SMALL_PHONE);
    await openPinboards(page);
    await expect(page.locator('[data-pinboard-item-label]').first()).toHaveAttribute('data-t0');
    await expect(page.locator('[data-pinboard-item-id]').first()).toHaveText(UUID_ITEM);
    await expect(page.locator('[data-pinboard-item-id]').first()).toHaveAttribute('data-t0');
    await page.getByRole('button', { name: LONG_BOARD }).click();
    await expect(page.getByRole('heading', { name: LONG_BOARD })).toBeVisible();
    expect((await noHorizontalScroll(page)).ok, 'long board selected').toBe(true);
    await page.getByRole('button', { name: 'Visit prep' }).click();
    await expect(page.locator('[data-pinboard-item-id]').first()).toBeVisible();
    expect((await noHorizontalScroll(page)).ok, 'UUID item').toBe(true);
  });
});

// ---------------------------------------------------------------------------------------------------------------
// M3: the add-to-pinboard menu enters with opacity and scale from the Radix origin.
// ---------------------------------------------------------------------------------------------------------------
test.describe('M3 add-to-pinboard menu enter', () => {
  test.use({ viewport: DESKTOP });

  /** Samples the open menu's computed opacity and scale once per frame, from the frame it exists, while `open` runs. */
  async function sampleEnter(page: Page, open: () => Promise<void>) {
    const sampled = page.evaluate(
      () =>
        new Promise<Array<{ t: number; opacity: number; scale: string }>>((resolve) => {
          const out: Array<{ t: number; opacity: number; scale: string }> = [];
          const observer = new MutationObserver(() => {
            const menu = document.querySelector('[role="menu"]');
            if (!menu) return;
            observer.disconnect();
            const t0 = performance.now();
            const tick = () => {
              const style = getComputedStyle(menu);
              out.push({ t: performance.now() - t0, opacity: parseFloat(style.opacity), scale: style.scale });
              if (performance.now() - t0 < 400) requestAnimationFrame(tick);
              else resolve(out);
            };
            tick();
          });
          observer.observe(document.body, { childList: true, subtree: true });
        })
    );
    await open();
    return sampled;
  }

  test('M3: the menu fades in and scales from .96 over about 180 ms from the Radix origin, with no transition-all', async ({ page }) => {
    // Would not notice: a `starting:` rule that Tailwind did not generate or the browser ignores (the menu would
    // appear at opacity 1 on its first frame), a duration other than 180 ms, a transform origin of the centre.
    // RED today: the menu has no transition; its first frame is already opacity 1.
    await setup(page);
    await openTimeline(page);
    const samples = await sampleEnter(page, () => pinButton(page).click());
    expect(samples.length).toBeGreaterThan(3);
    expect(samples[0].opacity, 'first frame starts transparent').toBeLessThan(0.9);
    expect(parseFloat(samples[0].scale), 'first frame starts below full scale').toBeLessThan(1);
    expect(samples.at(-1)!.opacity, 'ends opaque').toBe(1);
    expect(samples.at(-1)!.scale === 'none' || parseFloat(samples.at(-1)!.scale) === 1, 'ends at full scale').toBe(true);

    const menu = page.getByRole('menu');
    const style = await menu.evaluate((el) => {
      const s = getComputedStyle(el);
      return {
        property: s.transitionProperty,
        duration: s.transitionDuration,
        origin: s.transformOrigin,
        classes: Array.from(document.querySelectorAll('*')).flatMap((n) => (n.getAttribute('class') ?? '').split(/\s+/)),
      };
    });
    expect(style.property).toBe('opacity, scale');
    expect(style.duration).toBe('0.18s');
    expect(style.classes.filter((c) => /(^|:)transition-all$/.test(c))).toEqual([]);
  });

  test('M3: under reduced motion the menu fades and never scales', async ({ page }) => {
    // Would not notice: a scale that survives the reduced-motion preference.
    // RED today: no fade at all.
    await setup(page);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openTimeline(page);
    const samples = await sampleEnter(page, () => pinButton(page).click());
    expect(samples[0].opacity, 'still fades').toBeLessThan(0.9);
    for (const s of samples) expect(s.scale === 'none' || parseFloat(s.scale) === 1, `scale ${s.scale} at ${s.t}`).toBe(true);
  });
});

// ---------------------------------------------------------------------------------------------------------------
// Gate G, functional: G1, G6, G7, G9.
// ---------------------------------------------------------------------------------------------------------------
test.describe('Gate G on the records routes', () => {
  for (const theme of THEMES) {
    test(`G1 axe on /timeline, with the pin menu open (${theme})`, async ({ page }) => {
      // Would not notice: a white native select or a divider that fails in dark, or a menu scanned half-faded.
      // RED today: the event-type select is bg-white with ink text (color-contrast in dark).
      await setup(page);
      await openTimeline(page);
      await applyTheme(page, theme);
      expect(await axeBlocking(page), `G1 timeline ${theme}`).toEqual([]);
      await openPinMenu(page);
      expect(await axeBlocking(page), `G1 pin menu ${theme}`).toEqual([]);
      await page.keyboard.press('Escape');
    });

    test(`G1 axe on /search: results, zero results, and the empty page (${theme})`, async ({ page }) => {
      // RED today: both native selects are bg-white with ink text (color-contrast in dark).
      await setup(page);
      await openSearch(page);
      await applyTheme(page, theme);
      expect(await axeBlocking(page), `G1 results ${theme}`).toEqual([]);
      await page.getByRole('searchbox', { name: 'Search health records' }).fill('nothing');
      await page.keyboard.press('Enter');
      await expect(page.getByRole('heading', { name: 'No matching records' })).toBeVisible();
      // The empty state enters as an S1 group (480 ms): scan it once it has settled.
      await opaque(page.getByRole('button', { name: 'Clear search and filters' }));
      expect(await axeBlocking(page), `G1 zero results ${theme}`).toEqual([]);
      await page.getByRole('button', { name: 'Clear search and filters' }).click();
      await expect(page.getByRole('heading', { name: 'Search your records' })).toBeVisible();
      await opaque(page.getByRole('button', { name: 'Start a search' }));
      expect(await axeBlocking(page), `G1 empty ${theme}`).toEqual([]);
    });

    test(`G1 axe on /pinboards: page, Rename open with an error, Delete open (${theme})`, async ({ page }) => {
      // RED today: window.prompt throws, and the list divider is black/5.
      const { control } = await setup(page);
      await openPinboards(page);
      await applyTheme(page, theme);
      expect(await axeBlocking(page), `G1 pinboards ${theme}`).toEqual([]);

      control.failNextPatch = true;
      await renameButton(page).click();
      const dialog = renameDialog(page);
      await expect(dialog).toBeVisible();
      await opaque(dialog);
      expect(await axeBlocking(page), `G1 rename ${theme}`).toEqual([]);
      await dialog.getByLabel('Pinboard name').fill('Another name');
      await dialog.getByRole('button', { name: 'Save' }).click();
      await expect(dialog.getByRole('alert')).toBeVisible();
      expect(await axeBlocking(page), `G1 rename error ${theme}`).toEqual([]);
      await page.keyboard.press('Escape');
      await expect(dialog).toHaveCount(0);

      await deleteButton(page).click();
      await expect(deleteDialog(page)).toBeVisible();
      await opaque(deleteDialog(page));
      expect(await axeBlocking(page), `G1 delete ${theme}`).toEqual([]);
    });
  }

  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`G6 at ${viewport.width}x${viewport.height}: no horizontal scroll on /timeline, /search and /pinboards, with dialogs open`, async ({ page }) => {
      // Would not notice: an unbroken analyte, query, snippet, board name or id wider than the phone.
      await setup(page, viewport);
      await openTimeline(page);
      await expect(page.locator('[data-timeline-analytes]').filter({ hasText: LONG_ANALYTE })).toBeVisible();
      expect((await noHorizontalScroll(page)).ok, `timeline ${viewport.width}`).toBe(true);

      await page.goto(`/search?q=${LONG_QUERY}`);
      await expect(page.locator('[data-search-query]')).toContainText(LONG_QUERY);
      await expect(page.locator('[data-search-result]').first()).toBeVisible();
      expect((await noHorizontalScroll(page)).ok, `search ${viewport.width}`).toBe(true);

      await openPinboards(page);
      await page.getByRole('button', { name: LONG_BOARD }).click();
      await expect(page.getByRole('heading', { name: LONG_BOARD })).toBeVisible();
      expect((await noHorizontalScroll(page)).ok, `pinboards ${viewport.width}`).toBe(true);
      await renameButton(page).click();
      await expect(renameDialog(page)).toBeVisible();
      const fitsRename = await renameDialog(page).evaluate((el) => el.scrollWidth <= el.clientWidth);
      expect(fitsRename, `rename dialog ${viewport.width}`).toBe(true);
      await page.keyboard.press('Escape');
      await expect(renameDialog(page)).toHaveCount(0);
      await deleteButton(page).click();
      await expect(deleteDialog(page)).toContainText(LONG_BOARD);
      const fitsDelete = await deleteDialog(page).evaluate((el) => el.scrollWidth <= el.clientWidth);
      expect(fitsDelete, `delete dialog ${viewport.width}`).toBe(true);
      expect((await noHorizontalScroll(page)).ok, `delete dialog open ${viewport.width}`).toBe(true);
    });
  }

  test('G7 and G9: no console error, no outside request, no unmocked call; the Safety Rail is visible after each interaction', async ({ page }) => {
    // Would not notice: a console error from a dialog, an unmocked call from a new query, a rail that fades or moves.
    const { guard, mock, control } = await setup(page);
    await stubNativeDialogs(page);
    await openTimeline(page);
    await expectRail(page, 'timeline first paint');
    await openPinMenu(page);
    await expectRail(page, 'pin menu open');
    await page.keyboard.press('Escape');

    await openSearch(page);
    await expectRail(page, 'search first paint');
    await page.getByRole('searchbox', { name: 'Search health records' }).fill('nothing');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { name: 'No matching records' })).toBeVisible();
    await expectRail(page, 'after a search');

    await openPinboards(page);
    await expectRail(page, 'pinboards first paint');
    await renameButton(page).click();
    await expectRail(page, 'rename open');
    await page.keyboard.press('Escape');
    await deleteButton(page).click();
    await expectRail(page, 'delete open');
    await page.keyboard.press('Escape');
    await expectRail(page, 'dialogs closed');

    guard.assertClean();
    expect(mock.unmocked, 'G7 unmocked').toEqual([]);
    expect(control.patches).toEqual([]);
    expect(control.deletes).toEqual([]);
  });
});

// ---------------------------------------------------------------------------------------------------------------
// Timing: G2, G3, G5, G10. Quiet box only.
// ---------------------------------------------------------------------------------------------------------------
test.describe('QUIET-BOX UI-PG-RECORDS timing gates', () => {
  test.use({ viewport: DESKTOP });

  /** The T0 selectors the plan lists for each route (section 2.7). */
  const TIMELINE_T0 = ['[data-timeline-date]', '[data-timeline-analytes]', '[data-timeline-verification]'];
  const SEARCH_T0 = ['[data-search-title]', '[data-search-snippet]', '[data-search-date]', '[data-search-verification]'];
  const PINBOARD_T0 = ['[data-pinboard-item-label]', '[data-pinboard-item-id]'];

  for (const theme of THEMES) {
    test(`QUIET-BOX G2 on the records routes (${theme})`, async ({ page }) => {
      // The observations are held 700 ms, so the cards' arrival lands outside the 500 ms hadRecentInput window.
      const { control } = await setup(page);
      let release!: () => void;
      control.observationsGate = new Promise<void>((resolve) => {
        release = resolve;
      });
      const cls = await measureCls(page, async () => {
        await page.goto('/timeline');
        await expect(page.getByRole('heading', { name: 'Timeline', level: 1 })).toBeVisible();
        setTimeout(release, 700);
        await expect(page.getByText(TITLE_TWO, { exact: true })).toBeVisible();
        await settle(page);
        await applyTheme(page, theme);
        await openPinMenu(page);
        await page.keyboard.press('Escape');

        await page.goto('/search?q=glucose');
        await expect(page.getByRole('heading', { name: 'Glucose 118 mg/dL' })).toBeVisible();
        await page.getByRole('searchbox', { name: 'Search health records' }).fill('nothing');
        await page.keyboard.press('Enter');
        await expect(page.getByRole('heading', { name: 'No matching records' })).toBeVisible();

        await page.goto('/pinboards');
        await expect(renameButton(page)).toBeVisible();
        await renameButton(page).click();
        await expect(renameDialog(page)).toBeVisible();
        await page.keyboard.press('Escape');
        await deleteButton(page).click();
        await expect(deleteDialog(page)).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(deleteDialog(page)).toHaveCount(0);
      });
      expect(cls, `G2 ${theme}`).toBeLessThan(0.1);
    });

    test(`QUIET-BOX G3 on the records routes (${theme})`, async ({ page }) => {
      await setup(page);
      await openTimeline(page);
      await applyTheme(page, theme);
      const timeline = await maxEventDuration(
        page,
        async () => {
          await page.getByLabel('Event type').selectOption('lab_results');
          await openPinMenu(page);
          await page.keyboard.press('Escape');
        },
        { cpuRate: 4 }
      );
      expect(timeline, `G3 timeline ${theme}`).toBeLessThan(200);

      await openSearch(page);
      await applyTheme(page, theme);
      const search = await maxEventDuration(
        page,
        async () => {
          await page.getByRole('searchbox', { name: 'Search health records' }).fill('nothing');
          await page.keyboard.press('Enter');
          await expect(page.getByRole('heading', { name: 'No matching records' })).toBeVisible();
        },
        { cpuRate: 4 }
      );
      expect(search, `G3 search ${theme}`).toBeLessThan(200);

      await openPinboards(page);
      await applyTheme(page, theme);
      const pinboards = await maxEventDuration(
        page,
        async () => {
          await page.getByRole('button', { name: LONG_BOARD }).click();
          await renameButton(page).click();
          await expect(renameDialog(page)).toBeVisible();
          await renameDialog(page).getByRole('button', { name: 'Cancel' }).click();
          await expect(renameDialog(page)).toHaveCount(0);
          await deleteButton(page).click();
          await expect(deleteDialog(page)).toBeVisible();
          await deleteDialog(page).getByRole('button', { name: 'Cancel' }).click();
          await expect(deleteDialog(page)).toHaveCount(0);
        },
        { cpuRate: 4 }
      );
      expect(pinboards, `G3 pinboards ${theme}`).toBeLessThan(200);
    });

    test(`QUIET-BOX G5 on the records routes (${theme})`, async ({ page }, testInfo) => {
      await setup(page);
      await openTimeline(page);
      await applyTheme(page, theme);
      const pin = await reducedMotionSnapshot(page, () => pinButton(page).click());
      expect(pin, `G5 pin menu ${theme}`).toEqual([]);
      await page.screenshot({ path: testInfo.outputPath(`timeline-${theme}-reduced.png`), fullPage: false });
      await page.keyboard.press('Escape');

      await openSearch(page);
      await applyTheme(page, theme);
      const search = await reducedMotionSnapshot(page, async () => {
        await page.getByRole('searchbox', { name: 'Search health records' }).fill('nothing');
        await page.keyboard.press('Enter');
      });
      expect(search, `G5 search ${theme}`).toEqual([]);
      await page.screenshot({ path: testInfo.outputPath(`search-${theme}-reduced.png`), fullPage: false });

      await openPinboards(page);
      await applyTheme(page, theme);
      const rename = await reducedMotionSnapshot(page, () => renameButton(page).click());
      expect(rename, `G5 rename ${theme}`).toEqual([]);
      await page.screenshot({ path: testInfo.outputPath(`pinboards-${theme}-reduced.png`), fullPage: false });
      await page.keyboard.press('Escape');
      const remove = await reducedMotionSnapshot(page, () => deleteButton(page).click());
      expect(remove, `G5 delete ${theme}`).toEqual([]);
    });

    test(`QUIET-BOX G10 stillness on the records routes (${theme})`, async ({ page }, testInfo) => {
      await setup(page);
      const nav = (name: string) =>
        page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name, exact: true });
      await page.goto('/inbox');
      await settle(page);
      await applyTheme(page, theme);

      // Navigation to /timeline: the dates, the analyte names and the verification words stay through the route fade.
      const timelineNav = await stillnessProbe(page, {
        trigger: () => nav('Timeline').click(),
        expected: TIMELINE_T0.map((s) => `${ROUTE_CONTAINER_SELECTOR} ${s}`),
        kind: 'navigation',
        lazyRoute: true,
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `timeline navigation ${theme}: ${JSON.stringify(timelineNav)}` });
      await settle(page);

      // Navigation to /search?q=: /search has no link in the desktop navigation (the header button opens the palette,
      // whose own exit would be a second overlay), so the router is driven the way the browser's Back button is.
      const searchNav = await stillnessProbe(page, {
        trigger: () =>
          page.evaluate(() => {
            window.history.pushState({}, '', '/search?q=glucose');
            window.dispatchEvent(new PopStateEvent('popstate'));
          }),
        expected: SEARCH_T0.map((s) => `${ROUTE_CONTAINER_SELECTOR} ${s}`),
        kind: 'navigation',
        lazyRoute: true,
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `search navigation ${theme}: ${JSON.stringify(searchNav)}` });
      await settle(page);

      // The search submit: results appear from the empty page. Their text and rects stay from their first sample.
      await openSearch(page, '');
      await page.getByRole('searchbox', { name: 'Search health records' }).fill('glucose');
      const submit = await stillnessProbe(page, {
        trigger: () => page.keyboard.press('Enter'),
        expected: SEARCH_T0.map((s) => `${ROUTE_CONTAINER_SELECTOR} ${s}`),
        kind: 'interaction',
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `search submit ${theme}: ${JSON.stringify(submit)}` });

      // Navigation to /pinboards: the pinned label and id.
      await page.goto('/inbox');
      await settle(page);
      const pinboardsNav = await stillnessProbe(page, {
        trigger: () => nav('Pinboards').click(),
        expected: PINBOARD_T0.map((s) => `${ROUTE_CONTAINER_SELECTOR} ${s}`),
        kind: 'navigation',
        lazyRoute: true,
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `pinboards navigation ${theme}: ${JSON.stringify(pinboardsNav)}` });
      await settle(page);

      // Rename and Delete open: the page behind them (the pinned label and id) does not move or change.
      const renameOpen = await stillnessProbe(page, {
        trigger: async () => {
          await renameButton(page).click();
          await expect(renameDialog(page)).toBeVisible();
        },
        expected: PINBOARD_T0,
        kind: 'overlay',
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `rename open ${theme}: ${JSON.stringify(renameOpen)}` });
      await page.keyboard.press('Escape');
      await expect(renameDialog(page)).toHaveCount(0);
      const deleteOpen = await stillnessProbe(page, {
        trigger: async () => {
          await deleteButton(page).click();
          await expect(deleteDialog(page)).toBeVisible();
        },
        expected: PINBOARD_T0,
        kind: 'overlay',
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `delete open ${theme}: ${JSON.stringify(deleteOpen)}` });
      expect(deleteOpen.nodes).toBeGreaterThan(0);
    });
  }
});

// ---------------------------------------------------------------------------------------------------------------
// HC-UIPIN-001 against the real backend: the ids on /timeline and /observations are the same ids.
// ---------------------------------------------------------------------------------------------------------------
test.describe('HC-UIPIN-001 real backend', () => {
  test.use({ viewport: DESKTOP });

  test('HC-UIPIN-001: a card names the analytes of the observations its related ids point to', async ({ page, request }) => {
    // Would not notice (in the mocked cases above): a mismatch between the ids /timeline returns and the ids
    // /observations returns, so every real card would stay unnamed. A fresh CSV is imported through the write route;
    // the expected names are read from the API by id (order of the sorted related ids, each name once), not typed in.
    // RED today: the card says only "Lab results (2 analytes)".
    const auth = await ensureE2EProfile(request);
    const headers = { Authorization: `Bearer ${auth.access_token}` };
    const stamp = Date.now() % 100_000;
    const csv =
      'Date,Analyte,Value,Unit,Reference Low,Reference High,Flag\n' +
      `2017-05-06,Glucose,${(90 + stamp / 100_000).toFixed(5)},mg/dL,70,99,\n` +
      `2017-05-06,Hemoglobin A1c,5.${String(stamp).padStart(5, '0')},%,4.0,5.6,\n`;
    const imported = await request.post(`${E2E_API_URL}/documents/import`, {
      headers,
      multipart: { file: { name: `uipin-001-${stamp}.csv`, mimeType: 'text/csv', buffer: Buffer.from(csv) } },
    });
    expect(imported.ok(), `import: ${imported.status()} ${await imported.text()}`).toBeTruthy();
    const docId = ((await imported.json()) as { document: { id: string } }).document.id;

    const timelineResponse = await request.get(`${E2E_API_URL}/timeline/`, { headers });
    expect(timelineResponse.ok()).toBeTruthy();
    const event = ((await timelineResponse.json()) as TimelineResponse).events.find(
      (e) => e.event_type === 'lab_results' && e.doc_id === docId
    );
    expect(event, 'the imported document has a lab event').toBeTruthy();
    const observationsResponse = await request.get(`${E2E_API_URL}/observations/`, { headers });
    expect(observationsResponse.ok()).toBeTruthy();
    const byId = new Map(((await observationsResponse.json()) as Observation[]).map((o) => [o.id, o]));
    const expected: string[] = [];
    for (const id of event!.related_ids) {
      const row = byId.get(id);
      expect(row, `related id ${id} is an observation`).toBeTruthy();
      const name = row!.analyte_raw || row!.analyte_canonical;
      if (!expected.includes(name)) expected.push(name);
    }
    expect(expected.length, 'two analytes were seeded').toBeGreaterThanOrEqual(2);

    await openAuthenticatedPage(page, request, '/timeline');
    // Found by the date and the backend title only, so the old page finds the card too and fails on the names.
    const card = page
      .locator('li')
      .filter({ hasText: '2017-05-06' })
      .filter({ hasText: /Lab results \(/ })
      .first();
    await expect(card).toBeVisible({ timeout: 15_000 });
    await expect(card.locator('[data-timeline-analytes]')).toHaveText(expected.join(', '));
  });
});
