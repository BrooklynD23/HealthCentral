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
/** A value read from page 3 with a bounding box: selecting it mounts PageImageOverlay and its TraceMark. */
const SOURCED_ID = 'obs-review-creatinine';

/** A 400 x 100 PNG (the one ui-provenance.spec.ts serves), so the overlay has a real image to scale the box onto. */
const PAGE_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAZAAAABkCAIAAAAnqfEgAAABDUlEQVR42u3UQREAAAzCMPyrRQI6tksk9NEU4IhIABgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYwF8DXxGNujLHPvkAAAAASUVORK5CYII=',
  'base64'
);

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
  makeObservation({
    id: SOURCED_ID,
    analyte_raw: 'Creatinine',
    value: 0.9,
    unit: 'mg/dL',
    ref_low: 0.6,
    ref_high: 1.3,
    source_page: 3,
    // [x0,y0,x1,y1] in image pixels, the form parseBbox reads.
    source_bbox_json: '[10,20,200,40]',
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
  // Long values, one already checked: the one-third column is where a chip appearing once pushed the page wide.
  {
    id: 'ent-review-checked',
    doc_id: DOC_ID,
    category: 'radiology',
    entity_type: 'finding',
    entity_value: 'Mild degenerative change of the lumbar spine at L4-L5 with no acute fracture or malalignment',
    confidence: 0.92,
    source_page: null,
    source_bbox_json: null,
    char_start: null,
    char_end: null,
    quote: null,
    verified_by_user: true,
    extraction_version: null,
  },
  {
    id: 'ent-review-long',
    doc_id: DOC_ID,
    category: 'radiology',
    entity_type: 'finding',
    entity_value: 'Small stable nodule in the right lower lobe measuring 4 mm, unchanged from the prior examination',
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

/** GET /documents/:id, for the Source Trace sheet's file name. */
const DOCUMENT_BODY = {
  id: DOC_ID,
  profile_id: FIXTURE_PROFILE_ID,
  doc_type: 'lab_report',
  source: 'metabolic-panel-august.pdf',
  status: 'needs_review',
  page_count: 3,
  collection_date: '2026-04-10',
  imported_at: '2026-04-11T09:00:00',
  parsed_at: '2026-04-11T09:01:00',
  verified_at: null,
  extraction_confidence: 0.92,
};

/**
 * Page 3, where the Creatinine row was read. One line holds both the analyte and the value, so the sheet can
 * highlight it. The long line has neither, so it is plain context that must still stay inside the sheet (DF-2).
 */
const LONG_CONTEXT_LINE =
  'Reference intervals are for adults and depend on the method, the age, the sex and the hydration of the person tested; interpret with previous results';
const PAGES_BODY = [
  {
    page_number: 3,
    text: ['Chemistry panel', LONG_CONTEXT_LINE, 'Creatinine 0.9 mg/dL (0.6-1.3)', 'Sodium 140 mmol/L'].join('\n'),
    has_tables: false,
  },
];

/**
 * What POST /observations/:id/verify does, copied from src/backend/api/observations.py (`_NORMAL_FLAGS` at :82 and the
 * recalculation after `observation.version += 1`): the numbers are recalculated only when value, ref_low or ref_high
 * really changed AND the row has a range (#479, VERIFY-EDIT-NO-RANGE), or when the row has no flag or a normal word.
 * A plain Verify keeps any other printed flag, and so does an edit of a row with no range.
 * This is a mock, not the backend; HC-VKF on main pins the real behaviour.
 */
const NORMAL_FLAGS = new Set(['NORMAL', 'N', 'WNL', 'NO', 'FALSE', '0']);
function verifyLikeApi(current: Observation, edit: Partial<Observation> = {}): Observation {
  const next: Observation = { ...current };
  for (const field of ['value', 'ref_low', 'ref_high'] as const) {
    const sent = edit[field];
    if (sent !== undefined && sent !== null) next[field] = sent;
  }
  if (edit.value_text !== undefined) next.value_text = edit.value_text;
  next.user_verified = true;
  const numbersChanged = (['value', 'ref_low', 'ref_high'] as const).some((field) => next[field] !== current[field]);
  const keepsFlag = current.flag !== null && !NORMAL_FLAGS.has(current.flag.trim().toUpperCase());
  const hasRange = next.ref_low !== null || next.ref_high !== null;
  if (((numbersChanged && hasRange) || !keepsFlag) && next.value !== null) {
    if (next.ref_low !== null && next.value < next.ref_low) Object.assign(next, { is_abnormal: true, flag: 'L' });
    else if (next.ref_high !== null && next.value > next.ref_high) Object.assign(next, { is_abnormal: true, flag: 'H' });
    else Object.assign(next, { is_abnormal: false, flag: null });
  }
  return next;
}

interface ReviewMockOptions {
  /** The rows the API starts with. Default: the shared fixture. */
  rows?: Observation[];
}

/** What a test can steer or read from the mock. */
interface ReviewMock {
  /** "METHOD /path" of every call the review mock answered, in order. */
  readonly requests: string[];
  /** While true, POST /observations/:id/verify answers 500. */
  failVerify: boolean;
  /** From now on GET /documents (the list) waits for release(), like a slow server. */
  hold(): void;
  release(): void;
  /**
   * From now on GET /observations waits for releaseObservations() and reads the rows only then, like a refetch that was
   * sent early and answers late. Release it to let it answer; later GETs are not held.
   */
  holdObservations(): void;
  releaseObservations(): void;
  /** From now on POST /observations/:id/verify commits at once and answers only at releaseVerify() (one POST). */
  holdVerify(): void;
  releaseVerify(): void;
}

/** Observation, entity and page answers, with verify as state: a verified row stays verified on the next GET. */
async function mockReviewApi(page: Page, options: ReviewMockOptions = {}): Promise<ReviewMock> {
  const rows = (options.rows ?? initialObservations).map((row) => ({ ...row }));
  const entityRows = entities.map((entity) => ({ ...entity }));
  let gate: Promise<void> | null = null;
  let open: () => void = () => undefined;
  let observationsGate: Promise<void> | null = null;
  let openObservations: () => void = () => undefined;
  let verifyGate: Promise<void> | null = null;
  let openVerify: () => void = () => undefined;
  const mock: ReviewMock = {
    requests: [],
    failVerify: false,
    hold() {
      gate = new Promise<void>((resolve) => {
        open = resolve;
      });
    },
    release() {
      open();
      gate = null;
    },
    holdObservations() {
      observationsGate = new Promise<void>((resolve) => {
        openObservations = resolve;
      });
    },
    releaseObservations() {
      openObservations();
      observationsGate = null;
    },
    holdVerify() {
      verifyGate = new Promise<void>((resolve) => {
        openVerify = resolve;
      });
    },
    releaseVerify() {
      openVerify();
      verifyGate = null;
    },
  };
  await page.route(/\/api\/v1\/(observations|documents)(\/|\?|$)/, async (route: Route, request) => {
    const url = new URL(request.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '').replace(/\/+$/, '') || '/';
    const json = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (request.method() === 'GET') {
      if (path === '/documents' && gate) {
        await gate;
        return route.fallback();
      }
      if (path === '/observations') {
        mock.requests.push(`GET ${path}`);
        const heldGet = observationsGate;
        if (heldGet) await heldGet;
        const needsVerification = url.searchParams.get('needs_verification') === 'true';
        return json(needsVerification ? rows.filter((row) => !row.user_verified) : rows);
      }
      if (path === `/documents/${DOC_ID}`) {
        mock.requests.push(`GET ${path}`);
        return json(DOCUMENT_BODY);
      }
      if (path === `/documents/${DOC_ID}/entities`) return json(entityRows);
      if (path === `/documents/${DOC_ID}/pages`) {
        mock.requests.push(`GET ${path}`);
        return json(PAGES_BODY);
      }
      if (/^\/documents\/[^/]+\/pages\/\d+\/image$/.test(path)) {
        return route.fulfill({ status: 200, contentType: 'image/png', body: PAGE_PNG });
      }
      if (path === `/documents/${DOC_ID}/highlights`) return json([]);
    }
    const verify = /^\/observations\/([^/]+)\/verify$/.exec(path);
    if (request.method() === 'POST' && verify) {
      mock.requests.push(`POST ${path}`);
      if (mock.failVerify) return json({ detail: 'the server could not save this' }, 500);
      const index = rows.findIndex((candidate) => candidate.id === verify[1]);
      if (index === -1) return json({ detail: 'not found' }, 404);
      rows[index] = verifyLikeApi(rows[index], (request.postDataJSON() ?? {}) as Partial<Observation>);
      const saved = rows[index];
      // The server has committed; the answer waits when a test holds it, so a refetch can land in between.
      const heldPost = verifyGate;
      if (heldPost) {
        verifyGate = null;
        await heldPost;
      }
      return json(saved);
    }
    const entityVerification = /^\/documents\/[^/]+\/entities\/([^/]+)\/verification$/.exec(path);
    if (request.method() === 'PATCH' && entityVerification) {
      const entity = entityRows.find((candidate) => candidate.id === entityVerification[1]);
      if (!entity) return json({ detail: 'not found' }, 404);
      entity.verified_by_user = (request.postDataJSON() as { verified: boolean | null }).verified;
      return json(entity);
    }
    return route.fallback();
  });
  return mock;
}

async function prepare(page: Page, viewport = DESKTOP, options: ReviewMockOptions = {}) {
  await page.setViewportSize(viewport);
  const mock = await installMockApi(page);
  const review = await mockReviewApi(page, options);
  await seedMockSession(page);
  return Object.assign(mock, { review });
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

/** The computed clip-path of a row's ink layer: shut while pencil, open once ink (the 360 ms reveal has ended). */
const inkClip = (target: Locator): Promise<string> =>
  target.locator('[data-ink-layer]').evaluate((el) => getComputedStyle(el).clipPath);
const INK_SHUT = /circle\(0(%|px)/;
const INK_OPEN = /circle\(75%/;

async function openReview(page: Page, path = REVIEW_ALL, readyId = GLUCOSE_ID) {
  await page.goto(path);
  await expect(page.getByRole('heading', { name: 'Verification Workbench' })).toBeVisible();
  await expect(row(page, readyId)).toBeVisible();
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

  // L0 ruling on review round 3: no reassurance chip. A value inside its range carries no range words at all.
  await expect(row(page, GLUCOSE_ID).locator('[data-state$="-range"]')).toHaveCount(0);
  await expect(row(page, GLUCOSE_ID)).not.toContainText(/in range/i);

  // The words are real text on screen, not clipped to nothing.
  const box = await above.boundingBox();
  expect(box?.width ?? 0).toBeGreaterThan(40);
});

// ---------------------------------------------------------------------------
// L0 ruling on review round 3, finding 1: Verify keeps the flag the report printed, so the words, the tint and
// the position of the value are the same before and after. The mock answers like observations.py (see
// verifyLikeApi), so a row the report flagged keeps its flag across Verify.
// ---------------------------------------------------------------------------
const FLAG_ROWS: Observation[] = [
  makeObservation({
    id: 'obs-f-crit',
    analyte_raw: 'Potassium',
    value: 4.2,
    unit: 'mmol/L',
    ref_low: 3.5,
    ref_high: 5.1,
    flag: 'CRITICAL',
    is_abnormal: true,
  }),
  makeObservation({ id: 'obs-f-high', analyte_raw: 'Troponin', value: 0.08, unit: 'ng/mL', flag: 'H', is_abnormal: true }),
  makeObservation({
    id: 'obs-f-paren',
    analyte_raw: 'Sodium',
    value: 150,
    unit: 'mmol/L',
    ref_low: 135,
    ref_high: 145,
    flag: '(H)',
    is_abnormal: true,
  }),
  makeObservation({ id: 'obs-f-none', analyte_raw: 'LDL cholesterol', value: 130, unit: 'mg/dL', ref_high: 100 }),
  makeObservation({
    id: 'obs-f-nin',
    analyte_raw: 'Chloride',
    value: 102,
    unit: 'mmol/L',
    ref_low: 98,
    ref_high: 107,
    flag: 'N',
  }),
  makeObservation({
    id: 'obs-f-nhigh',
    analyte_raw: 'Triglycerides',
    value: 180,
    unit: 'mg/dL',
    ref_high: 150,
    flag: 'N',
  }),
  // Reference rows: the colour a plain value and an above-range value really get (no flag, in range / flag H).
  initialObservations[0],
  initialObservations[1],
];

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}
interface ValueSnapshot {
  words: string | null;
  color: string;
  rect: Box;
  /** Every T0 node in the rows after this one, in document coordinates. */
  below: Box[];
}

/** The range words, the computed colour and the document-space box of a row's value, and the T0 nodes below it. */
async function snapshotValue(page: Page, id: string): Promise<ValueSnapshot> {
  return row(page, id).evaluate((tr) => {
    const box = (el: Element): Box => {
      const r = el.getBoundingClientRect();
      return { x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height };
    };
    const value = tr.querySelectorAll('td')[1].querySelector('span[data-t0]') as HTMLElement;
    const chip = tr.querySelector('[data-state$="-range"]');
    const below: Box[] = [];
    for (let next = tr.nextElementSibling; next; next = next.nextElementSibling) {
      for (const node of Array.from(next.querySelectorAll('[data-t0]'))) below.push(box(node));
    }
    return {
      words: chip?.textContent?.trim() ?? null,
      color: getComputedStyle(value).color,
      rect: box(value),
      below,
    };
  });
}

function expectSameBox(after: Box, before: Box, label: string) {
  for (const key of ['x', 'y', 'w', 'h'] as const) {
    expect(Math.abs(after[key] - before[key]), `${label} ${key}: ${before[key]} -> ${after[key]}`).toBeLessThanOrEqual(0.5);
  }
}

const ABOVE_WORDS = "Above the report's range";
const FLAG_CASES = [
  { id: 'obs-f-crit', name: '(a) CRITICAL 4.2 inside 3.5-5.1', words: null, tint: 'ink' },
  { id: 'obs-f-high', name: '(b) H with no numeric range', words: ABOVE_WORDS, tint: 'attention' },
  { id: 'obs-f-paren', name: '(c) "(H)"', words: ABOVE_WORDS, tint: 'attention' },
  { id: 'obs-f-none', name: '(d) no flag, 130 over ref_high 100', words: ABOVE_WORDS, tint: 'attention' },
  { id: 'obs-f-nin', name: '(e) flag N, inside the range', words: null, tint: 'ink' },
  { id: 'obs-f-nhigh', name: '(f) flag N, 180 over 150', words: ABOVE_WORDS, tint: 'attention' },
] as const;

for (const flagCase of FLAG_CASES) {
  test(`HC-UIREV-001 Verify keeps what the report printed: ${flagCase.name}`, async ({ page }) => {
    await prepare(page, DESKTOP, { rows: FLAG_ROWS });
    await openReview(page, '/verify', 'obs-f-crit');
    const ink = (await snapshotValue(page, GLUCOSE_ID)).color;
    const attention = (await snapshotValue(page, A1C_ID)).color;
    expect(ink, 'the two reference tints differ').not.toBe(attention);

    const before = await snapshotValue(page, flagCase.id);
    expect(before.words, `${flagCase.name} words before`).toBe(flagCase.words);
    expect(before.color, `${flagCase.name} tint before`).toBe(flagCase.tint === 'ink' ? ink : attention);
    expect(await page.evaluate(() => window.scrollY)).toBe(0);

    await row(page, flagCase.id).getByRole('button', { name: 'Verify observation' }).click();
    await expect(row(page, flagCase.id).locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
    await page.waitForLoadState('networkidle');

    const after = await snapshotValue(page, flagCase.id);
    expect(after.words, `${flagCase.name} words after`).toBe(before.words);
    expect(after.color, `${flagCase.name} tint after`).toBe(before.color);
    expectSameBox(after.rect, before.rect, `${flagCase.name} value`);
    expect(after.below.length, 'rows below').toBe(before.below.length);
    after.below.forEach((box, index) => expectSameBox(box, before.below[index], `${flagCase.name} below[${index}]`));
  });
}

// ---------------------------------------------------------------------------
// L0 ruling on review round 3, finding 3: the last unverified value verified. The row stays as ink (HC-UIREV-002
// needs it on screen), the end-of-queue state shows above the list, and Mark All Verified is disabled.
// ---------------------------------------------------------------------------
test('UI-PG-REVIEW Ink on the default /verify: verifying the last row shows the end of the queue above the held row', async ({
  page,
}) => {
  await prepare(page, DESKTOP, { rows: [initialObservations[0]] });
  await openReview(page, '/verify');
  const markAll = page.getByRole('button', { name: 'Mark All Verified' });
  await expect(markAll).toBeEnabled();
  await expect(page.getByText('All observations verified')).toHaveCount(0);
  const top = () => row(page, GLUCOSE_ID).evaluate((el) => el.getBoundingClientRect().y + window.scrollY);
  const topBefore = await top();

  await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
  await expect(page.getByText('All observations verified')).toBeVisible();
  await page.waitForLoadState('networkidle');

  await expect(row(page, GLUCOSE_ID).locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect(markAll).toBeDisabled();
  const done = await page.getByText('All observations verified').boundingBox();
  const held = await row(page, GLUCOSE_ID).boundingBox();
  expect(done!.y, 'the end of the queue sits above the held row').toBeLessThan(held!.y);
  // Recorded, not asserted: the list moves down by the height of this block (candidate bullet for L0).
  console.log(`UI-PG-REVIEW last row: the held row moved ${Math.round((await top()) - topBefore)} px when the end of the queue mounted`);
});

// ---------------------------------------------------------------------------
// L0 ruling on review round 3, finding 4: the page does not move when /documents answers late. The "Reviewing:
// <file>" line is reserved in document review mode. Layout only (no clock), so it runs on any box.
// ---------------------------------------------------------------------------
for (const width of [1024, 1280, 1440]) {
  test(`HC-UIREV-004: the grid does not move when the document list answers late, at ${width}`, async ({ page }) => {
    const mock = await prepare(page, { width, height: 900 });
    mock.review.hold();
    await page.goto(REVIEW_ALL);
    await expect(row(page, GLUCOSE_ID)).toBeVisible();
    await expect(page.getByText(/^Reviewing:/)).toHaveCount(0);
    const gridTop = () =>
      page.locator('.grid.grid-cols-1').first().evaluate((el) => el.getBoundingClientRect().y + window.scrollY);
    const rowTop = () => row(page, GLUCOSE_ID).evaluate((el) => el.getBoundingClientRect().y + window.scrollY);
    const before = { grid: await gridTop(), row: await rowTop() };

    mock.review.release();
    await expect(page.getByText(/^Reviewing:/)).toBeVisible();
    await page.waitForLoadState('networkidle');
    const after = { grid: await gridTop(), row: await rowTop() };
    expect(after, `grid and first row, before and after /documents answers (${width})`).toEqual(before);
  });
}

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
  expect(await inkClip(glucose), 'the ink layer is shut while pencil').toMatch(INK_SHUT);

  await glucose.getByRole('button', { name: 'Verify observation' }).click();

  await expect(glucose.locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect(glucose.locator('[data-state="checked-by-you"]')).toHaveText('Checked by you');
  await expect(glucose.locator('[data-state="not-checked"]')).toHaveCount(0);
  // The reveal itself: the computed clip-path ends open (the vitest suite cannot see a CSS engine).
  await expect.poll(() => inkClip(glucose), { message: 'the ink layer opens' }).toMatch(INK_OPEN);
  // Finding 7: the Verify button left with the commit, so focus moves to the row's Edit button, and the page did not scroll.
  await expect(glucose.getByRole('button', { name: 'Edit value' })).toBeFocused();
  expect(await page.evaluate(() => window.scrollY)).toBe(0);

  // The other rows stay pencil.
  await expect(row(page, A1C_ID).locator('[data-ink-marker]')).toHaveAttribute('data-state', 'pencil');

  const toast = page.locator('[data-sonner-toast]');
  await expect(toast).toContainText('Glucose, Apr 10, 2026 is now marked as checked');
  // The API has no unverify endpoint, so the toast has no action button.
  await expect(toast.getByRole('button')).toHaveCount(0);
});

// The default /verify asks for needs_verification=true, so the API drops a row once it is verified. The row
// stays on screen as ink for the rest of the visit (the mock above filters the way the API does).
test('UI-PG-REVIEW Ink on the default /verify: a verified row stays in place as ink, with the chip and the toast', async ({
  page,
}) => {
  await prepare(page);
  await openReview(page, '/verify');
  const order = () => page.locator('tr[id^="observation-row-"]').evaluateAll((trs) => trs.map((tr) => tr.id));
  const before = await order();
  const glucose = row(page, GLUCOSE_ID);

  const refetched = page.waitForResponse(
    (response) => response.url().includes('/observations') && response.request().method() === 'GET' && response.url().includes('needs_verification')
  );
  await glucose.getByRole('button', { name: 'Verify observation' }).click();
  await refetched;
  await page.waitForLoadState('networkidle');

  await expect(glucose.locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect(glucose.locator('[data-state="checked-by-you"]')).toHaveText('Checked by you');
  await expect.poll(() => inkClip(glucose), { message: 'the ink layer opens on the default list too' }).toMatch(INK_OPEN);
  expect(await order()).toEqual(before);
  await expect(page.locator('[data-sonner-toast]')).toContainText('Glucose, Apr 10, 2026 is now marked as checked');
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

// The hold only acts on the default list, where the API drops a verified row, so the probe runs there too (finding 12).
test('HC-UIREV-002: the value text passes stillnessProbe through the Ink animation on the default /verify', async ({
  page,
}) => {
  await prepare(page);
  await openReview(page, '/verify');
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
  await expect.poll(() => inkClip(row(page, GLUCOSE_ID))).toMatch(INK_OPEN);
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

test('HC-UIREV-003: a comma decimal shows the alert, and a failed save keeps the dialog open (FE-VERIFY-NUMERIC)', async ({
  page,
}) => {
  const mock = await prepare(page);
  await openReview(page);
  await row(page, GLUCOSE_ID).getByRole('button', { name: 'Edit value' }).click();
  const dialog = page.getByRole('dialog', { name: 'Edit Value' });
  const input = dialog.getByRole('textbox', { name: /Glucose/ });
  await input.fill('7,5');
  await expect(dialog.getByRole('alert')).toContainText('Use a dot for decimals');
  await expect(dialog.getByRole('button', { name: /save & verify/i })).toBeDisabled();

  // The failed save (a 500 from the server): the dialog stays open, says so, and nothing is marked as checked.
  mock.review.failVerify = true;
  await input.fill('99');
  await dialog.getByRole('button', { name: /save & verify/i }).click();
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('alert')).toBeVisible();
  expect(mock.review.requests).toContain(`POST /observations/${GLUCOSE_ID}/verify`);
  await expect(row(page, GLUCOSE_ID).locator('[data-state="checked-by-you"]')).toHaveCount(0);
  await expect(page.locator('[data-sonner-toast]')).toHaveCount(0);

  // And it can be retried: the next save goes through and closes the dialog.
  mock.review.failVerify = false;
  await dialog.getByRole('button', { name: /save & verify/i }).click();
  await expect(dialog).toHaveCount(0);
  await expect(row(page, GLUCOSE_ID).locator('[data-state="checked-by-you"]')).toBeVisible();
});

// A failed Verify from the row (finding 9): a still error toast, and the row stays unchecked.
test('UI-PG-REVIEW a failed Verify shows an error toast and the row stays unchecked', async ({ page }) => {
  const mock = await prepare(page);
  await openReview(page);
  mock.review.failVerify = true;
  await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
  await expect(page.locator('[data-sonner-toast]')).toContainText('Could not mark Glucose as checked. Try again.');
  await expect(row(page, GLUCOSE_ID).locator('[data-state="not-checked"]')).toHaveText('Not yet checked');
  await expect(row(page, GLUCOSE_ID).locator('[data-ink-marker]')).toHaveAttribute('data-state', 'pencil');
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

// L0 ruling (ui-provenance.spec.ts, 2026-10-25): G6 at 390 and 320 for /verify is asserted here, with a selected row
// whose source preview shows PageImageOverlay and its TraceMark. Each size is its own load: PageImageOverlay measures
// the image once, on load, so a resize after load is not a layout this page owns.
for (const viewport of [PHONE, SMALL_PHONE]) {
  const size = `${viewport.width}x${viewport.height}`;
  test(`HC-UIREV-004 and Gate G6 at ${size} with a selected row: the page image and its mark stay inside the viewport`, async ({
    page,
  }) => {
    await prepare(page, viewport);
    await openReview(page, '/verify');
    await row(page, SOURCED_ID).locator('td').first().click();

    const overlay = page.locator('[data-page-image-overlay]');
    const image = overlay.locator('img');
    await expect(image).toBeVisible();
    // The image fades in only after onLoad, and the mark mounts only after that.
    await expect.poll(() => image.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
    const mark = overlay.locator('[data-trace-mark]');
    await expect(mark).toBeVisible();
    await page.waitForLoadState('networkidle');

    const scroll = await noHorizontalScroll(page);
    expect(scroll.ok, `G6 ${size}: ${JSON.stringify(scroll)}`).toBe(true);
    for (const [name, locator] of [
      ['overlay card', overlay],
      ['page image', image],
      ['trace mark', mark],
    ] as const) {
      const box = await locator.boundingBox();
      expect(box, `${name} has a box`).not.toBeNull();
      expect(box!.x, `${name} left edge at ${size}`).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width, `${name} right edge at ${size}`).toBeLessThanOrEqual(viewport.width);
    }
  });
}

// The header row is hidden below sm, so the value cell names itself there and not on desktop.
test('HC-UIREV-004: the value cell says "Value" on a phone only', async ({ page }) => {
  await prepare(page, PHONE);
  await openReview(page);
  const label = row(page, GLUCOSE_ID).locator('td').nth(1).getByText('Value', { exact: true });
  await expect(label).toBeVisible();
  await page.setViewportSize(DESKTOP);
  await expect(label).toBeHidden();
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
// HC-UIREV-006 (plan delta, followups plan): "Show source" on a row opens the Source Trace sheet for that row.
// ---------------------------------------------------------------------------
const showSource = (page: Page, id: string): Locator => row(page, id).getByRole('button', { name: 'Show source' });
const SHEET = '[role="dialog"]';

test('HC-UIREV-006: Show source opens the Source Trace sheet for that row and leaves the selection alone', async ({
  page,
}) => {
  const mock = await prepare(page);
  const imageRequests: string[] = [];
  page.on('request', (request) => {
    if (/\/pages\/\d+\/image/.test(request.url())) imageRequests.push(request.url());
  });
  await openReview(page, '/verify');
  expect(mock.review.requests, 'no GET /documents/<id> before the sheet opens').not.toContain(`GET /documents/${DOC_ID}`);

  await showSource(page, SOURCED_ID).click();
  const sheet = page.getByRole('dialog', { name: 'Source for Creatinine' });
  await expect(sheet).toBeVisible();
  await expect(sheet.getByText('metabolic-panel-august.pdf')).toBeVisible();
  await expect(sheet.getByText('Page 3')).toBeVisible();
  await expect(sheet.locator('li', { hasText: 'Matching line:' })).toContainText('Creatinine 0.9 mg/dL (0.6-1.3)');
  expect(mock.review.requests).toContain(`GET /documents/${DOC_ID}`);

  // Clicks on the trigger and inside the sheet bubble through the React tree to the row; neither may select it.
  await sheet.getByRole('heading', { name: 'Source for Creatinine' }).click();
  await sheet.getByText('Excerpt', { exact: true }).click();
  await expect(row(page, SOURCED_ID)).not.toHaveClass(/bg-accent-subtle/);
  await expect(page.locator('[data-page-image-overlay]')).toHaveCount(0);
  expect(imageRequests, 'no page image was requested').toEqual([]);

  await page.keyboard.press('Escape');
  await expect(sheet).toHaveCount(0);
  await expect(showSource(page, SOURCED_ID)).toBeFocused();

  // A second row opens its own sheet.
  await showSource(page, GLUCOSE_ID).click();
  await expect(page.getByRole('dialog', { name: 'Source for Glucose' })).toBeVisible();
  await expect(page.getByRole('dialog', { name: 'Source for Creatinine' })).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(row(page, GLUCOSE_ID)).not.toHaveClass(/bg-accent-subtle/);
  expect(imageRequests).toEqual([]);
});

test('HC-UIREV-006: the button is a 44 px target and the row stays one line on desktop', async ({ page }) => {
  await prepare(page, DESKTOP);
  await openReview(page, '/verify');
  const button = showSource(page, GLUCOSE_ID);
  const box = await button.boundingBox();
  expect(box!.height, 'Show source target height').toBeGreaterThanOrEqual(44);
  const cells = row(page, GLUCOSE_ID).locator('td');
  const name = await cells.nth(0).boundingBox();
  const value = await cells.nth(1).boundingBox();
  expect(value!.x).toBeGreaterThan(name!.x + name!.width - 1);
  expect(Math.abs(value!.y - name!.y)).toBeLessThan(8);
});

// DF-2 / HC-UIPV-004 (queue.md:627 assigns it to this row): no source line scrolls sideways, at 1440 and 390.
for (const viewport of [DESKTOP, PHONE]) {
  test(`HC-UIREV-006 and DF-2 (HC-UIPV-004): every source line fits its box at ${viewport.width}`, async ({ page }) => {
    await prepare(page, viewport);
    await openReview(page, '/verify');
    await showSource(page, SOURCED_ID).click();
    const sheet = page.getByRole('dialog', { name: 'Source for Creatinine' });
    await expect(sheet.locator('li', { hasText: 'Matching line:' })).toBeVisible();
    const lines = await sheet.locator('ol li').evaluateAll((items) =>
      items.map((li) => {
        const text = li.querySelector('[data-t0]') as HTMLElement;
        return {
          text: (text?.textContent ?? '').slice(0, 40),
          li: [li.scrollWidth, li.clientWidth],
          span: [text?.scrollWidth ?? 0, text?.clientWidth ?? 0],
        };
      })
    );
    expect(lines.length, 'the excerpt shows its lines').toBeGreaterThanOrEqual(4);
    for (const line of lines) {
      expect(line.li[0], `li scrollWidth ${JSON.stringify(line)}`).toBeLessThanOrEqual(line.li[1]);
      expect(line.span[0], `span scrollWidth ${JSON.stringify(line)}`).toBeLessThanOrEqual(line.span[1]);
    }
  });
}

test('HC-UIREV-006 and Gate G6 with the Source Trace sheet open: no horizontal scroll at 390 and 320', async ({ page }) => {
  await prepare(page, PHONE);
  await openReview(page, '/verify');
  await showSource(page, SOURCED_ID).click();
  await expect(page.getByRole('dialog', { name: 'Source for Creatinine' })).toBeVisible();
  await expect(page.locator(`${SHEET} li`, { hasText: 'Matching line:' })).toBeVisible();
  const at390 = await noHorizontalScroll(page);
  expect(at390.ok, `G6 390 with the sheet: ${JSON.stringify(at390)}`).toBe(true);
  await page.setViewportSize(SMALL_PHONE);
  const at320 = await noHorizontalScroll(page);
  expect(at320.ok, `G6 320 with the sheet: ${JSON.stringify(at320)}`).toBe(true);
});

// Timing: quiet box only. The title carries "HC-UIREV-006 stillness" so the quiet-box line selects it.
test('HC-UIREV-006 stillness: the Source Trace sheet passes stillnessProbe from the Show source click', async ({ page }) => {
  await prepare(page);
  await openReview(page, '/verify');
  const trigger = showSource(page, SOURCED_ID);
  // Scroll first, so the click does not scroll the page under the probe.
  await trigger.scrollIntoViewIfNeeded();
  await settle(page);
  const report = await stillnessProbe(page, {
    trigger: () => trigger.click(),
    expected: [`${SHEET} dd[data-t0]`, `${SHEET} ol [data-t0]`],
    kind: 'overlay',
  });
  expect(report.postTriggerSamples).toBeGreaterThan(0);
  await expect(page.getByRole('dialog', { name: 'Source for Creatinine' })).toBeVisible();
});

// ---------------------------------------------------------------------------
// L0 rulings 6602430522 and 6603062959: "It matches, mark as checked" inside the Source Trace sheet on the default
// /verify. The sheet verifies through its own mutation; without the hold the refetch drops the row and the sheet.
// ---------------------------------------------------------------------------
const MARK_CHECKED = 'It matches, mark as checked';
const SHEET_CHECKED = 'You have marked this value as checked.';
const CHECKED_TOAST = 'Creatinine, Apr 10, 2026 is now marked as checked';
const rowOrder = (page: Page) => page.locator('tr[id^="observation-row-"]').evaluateAll((trs) => trs.map((tr) => tr.id));

/** Opens the sheet for the Creatinine row (it has a source excerpt) and waits until "It matches" is enabled. */
async function openCreatinineSheet(page: Page) {
  await showSource(page, SOURCED_ID).click();
  const sheet = page.getByRole('dialog', { name: 'Source for Creatinine' });
  await expect(sheet.locator('li', { hasText: 'Matching line:' })).toBeVisible();
  const mark = sheet.getByRole('button', { name: MARK_CHECKED });
  await expect(mark).toBeEnabled();
  return { sheet, mark };
}

test('UI-PG-REVIEW Ink on the default /verify: It matches in the Source Trace sheet holds the row as ink, and focus returns to Show source', async ({
  page,
}) => {
  await prepare(page);
  await openReview(page, '/verify');
  const before = await rowOrder(page);
  const creatinine = row(page, SOURCED_ID);
  const { sheet, mark } = await openCreatinineSheet(page);

  await mark.click();
  await expect(creatinine.locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect(creatinine.locator('[data-state="checked-by-you"]')).toHaveText('Checked by you');
  // The refetch (needs_verification) has answered without this row; the sheet must still be there, saying so.
  await page.waitForLoadState('networkidle');
  await expect(sheet.getByText(SHEET_CHECKED)).toBeVisible();
  await expect(creatinine.locator('span[data-t0].font-mono')).toHaveText('0.9');
  await expect.poll(() => inkClip(creatinine), { message: 'the ink layer opens' }).toMatch(INK_OPEN);
  await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);
  await expect(page.locator('[data-sonner-toast]')).toContainText(CHECKED_TOAST);

  await page.keyboard.press('Escape');
  await expect(sheet).toHaveCount(0);
  await expect(showSource(page, SOURCED_ID)).toBeFocused();
  expect(await rowOrder(page)).toEqual(before);
  await expect(creatinine.locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);
});

// Order (b) in a real browser: a refetch already in flight answers without the row before the POST answers. jsdom's
// focus and Radix are not Chromium's, so the order runs here too. The refetch is started without a product edit: the
// clock moves 6 minutes (the app's staleTime is 5) without firing a timer, then a visibilitychange makes TanStack
// refetch the now-stale observations on focus. The GET and the POST are held by the mock.
test('UI-PG-REVIEW Ink on the default /verify: a refetch in flight when It matches is clicked answers first, and the row is still held', async ({
  page,
}) => {
  await page.clock.install();
  const mock = await prepare(page);
  await openReview(page, '/verify');
  const before = await rowOrder(page);
  const { mark } = await openCreatinineSheet(page);
  const gets = () => mock.review.requests.filter((request) => request === 'GET /observations').length;
  const posts = () => mock.review.requests.filter((request) => request.startsWith('POST ')).length;

  mock.review.holdObservations();
  const getsBefore = gets();
  await page.clock.setSystemTime(new Date(Date.now() + 6 * 60 * 1000));
  await page.evaluate(() => window.dispatchEvent(new Event('visibilitychange')));
  await expect.poll(gets, { message: 'the focus refetch is in flight' }).toBeGreaterThan(getsBefore);

  mock.review.holdVerify();
  await mark.click();
  await expect.poll(posts, { message: 'the POST was sent' }).toBe(1);

  // The server has committed. The older GET answers: the row is gone from the list and the sheet with it.
  mock.review.releaseObservations();
  await expect(row(page, SOURCED_ID)).toHaveCount(0);
  await expect(page.getByRole('dialog')).toHaveCount(0);

  // Only now does the POST answer.
  mock.review.releaseVerify();
  const creatinine = row(page, SOURCED_ID);
  await expect(creatinine.locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect(creatinine.locator('[data-state="checked-by-you"]')).toHaveText('Checked by you');
  await page.waitForLoadState('networkidle');
  await expect(creatinine.locator('span[data-t0].font-mono')).toHaveText('0.9');
  expect(await rowOrder(page), 'the held row comes back in its place').toEqual(before);
  await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);
  await expect(page.locator('[data-sonner-toast]')).toContainText(CHECKED_TOAST);
  await expect(showSource(page, SOURCED_ID), 'focus is not lost to the body').toBeFocused();
  // The page is not left locked behind a removed sheet: another sheet opens and closes.
  expect(await page.evaluate(() => document.body.style.pointerEvents)).not.toBe('none');
  await showSource(page, GLUCOSE_ID).click();
  await expect(page.getByRole('dialog', { name: 'Source for Glucose' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

// Timing: quiet box only. The title carries HC-UIREV-002 so the quiet-box line for that gate selects it.
test('HC-UIREV-002: the value text passes stillnessProbe from the It matches click in the Source Trace sheet', async ({
  page,
}) => {
  await prepare(page);
  await openReview(page, '/verify');
  const { mark } = await openCreatinineSheet(page);
  // In view before the probe starts, so the click does not scroll inside its window.
  await mark.scrollIntoViewIfNeeded();
  await settle(page);
  const report = await stillnessProbe(page, {
    trigger: () => mark.click(),
    expected: [
      `#observation-row-${SOURCED_ID} span[data-t0]`,
      `#observation-row-${SOURCED_ID} [data-state="checked-by-you"]`,
    ],
    kind: 'interaction',
  });
  expect(report.nodes).toBeGreaterThan(0);
  await expect(row(page, SOURCED_ID).locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect(page.getByRole('dialog', { name: 'Source for Creatinine' }).getByText(SHEET_CHECKED)).toBeVisible();
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

  test(`UI-PG-REVIEW Gate G1 axe with the Source Trace sheet open (${theme})`, async ({ page }) => {
    await prepare(page);
    await openReview(page, '/verify');
    await setTheme(page, theme);
    await showSource(page, SOURCED_ID).click();
    await expect(page.getByRole('dialog', { name: 'Source for Creatinine' })).toBeVisible();
    await expect(page.locator(`${SHEET} li`, { hasText: 'Matching line:' })).toBeVisible();
    const axe = await axeGate(page, { theme });
    expect(
      axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
      `G1 source sheet ${theme}`
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

  // The Edit dialog open and closed (Escape returns focus to its button).
  await row(page, A1C_ID).getByRole('button', { name: 'Edit value' }).click();
  await expect(page.getByRole('dialog', { name: 'Edit Value' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  const afterDialog = await safetyVisible(page);
  expect(afterDialog.found && afterDialog.inViewport && afterDialog.effectiveOpacity >= 0.99, `G9 ${JSON.stringify(afterDialog)}`).toBe(true);

  // HC-UIREV-006: the Source Trace sheet open (its GETs run) and closed.
  await showSource(page, SOURCED_ID).click();
  await expect(page.getByRole('dialog', { name: 'Source for Creatinine' })).toBeVisible();
  await expect(page.locator(`${SHEET} li`, { hasText: 'Matching line:' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  const afterSheet = await safetyVisible(page);
  expect(afterSheet.found && afterSheet.inViewport && afterSheet.effectiveOpacity >= 0.99, `G9 ${JSON.stringify(afterSheet)}`).toBe(true);

  guard.assertClean();
  expect(mock.unmocked, 'G7 unmocked').toEqual([]);
});

test('UI-PG-REVIEW Gate G2 CLS under 0.1 over load (a late /documents), Verify, the Edit dialog and the Source Trace sheet', async ({
  page,
}) => {
  const mock = await prepare(page);
  await openReview(page);
  // From here GET /documents (the list) waits until the rows are on screen, like a slow server: the "Reviewing:
  // <file>" line used to mount then and drop the grid (L0 ruling on review round 3, finding 4).
  mock.review.hold();
  const cls = await measureCls(page, async () => {
    await page.goto(REVIEW_ALL);
    await expect(row(page, GLUCOSE_ID)).toBeVisible();
    mock.review.release();
    await expect(page.getByText(/^Reviewing:/)).toBeVisible();
    await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
    await expect(row(page, GLUCOSE_ID).locator('[data-state="checked-by-you"]')).toBeVisible();
    await row(page, A1C_ID).getByRole('button', { name: 'Edit value' }).click();
    await page.keyboard.press('Escape');
    await showSource(page, SOURCED_ID).click();
    await expect(page.locator(`${SHEET} li`, { hasText: 'Matching line:' })).toBeVisible();
    await page.getByRole('dialog', { name: 'Source for Creatinine' }).getByRole('button', { name: MARK_CHECKED }).click();
    await expect(page.getByText(SHEET_CHECKED)).toBeVisible();
    await page.keyboard.press('Escape');
  });
  console.log(`UI-PG-REVIEW G2 CLS /verify: ${cls}`);
  expect(cls, 'G2 /verify').toBeLessThan(0.1);
});

test('UI-PG-REVIEW Gate G3 INP proxy under 200 ms for Verify, the Edit dialog and the Source Trace sheet, CPU x4', async ({ page }) => {
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
      await showSource(page, SOURCED_ID).click();
      await expect(page.getByRole('dialog', { name: 'Source for Creatinine' })).toBeVisible();
      await page.keyboard.press('Escape');
    },
    { cpuRate: 4 }
  );
  console.log(`UI-PG-REVIEW G3 INP proxy /verify (CPU x4): ${inp} ms`);
  expect(inp, 'G3 /verify').toBeLessThan(200);
});

test('UI-PG-REVIEW Gate G5 reduced motion: no transform 50 ms after the Edit dialog opens, after Verify, with the Source Trace sheet open or after It matches', async ({
  page,
}, testInfo) => {
  await prepare(page);
  await openReview(page);

  // Snapshot 1: the Edit dialog open (its screenshot is taken while it is still open).
  const dialogOffenders = await reducedMotionSnapshot(page, async () => {
    await row(page, A1C_ID).getByRole('button', { name: 'Edit value' }).click();
    await expect(page.getByRole('dialog', { name: 'Edit Value' })).toBeVisible();
  });
  expect(dialogOffenders, 'G5 /verify, Edit dialog open').toEqual([]);
  const dialogShot = testInfo.outputPath('verify-dialog-reduced.png');
  await page.screenshot({ path: dialogShot, fullPage: false });
  testInfo.annotations.push({ type: 'gate-g5-screenshot', description: dialogShot });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);

  // Snapshot 2: after Verify.
  const offenders = await reducedMotionSnapshot(page, async () => {
    await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
  });
  expect(offenders, 'G5 /verify, after Verify').toEqual([]);
  const shot = testInfo.outputPath('verify-reduced.png');
  await page.screenshot({ path: shot, fullPage: false });
  testInfo.annotations.push({ type: 'gate-g5-screenshot', description: shot });

  // Snapshot 3: the Source Trace sheet open (its screenshot is taken while it is still open).
  const sheetOffenders = await reducedMotionSnapshot(page, async () => {
    await showSource(page, SOURCED_ID).click();
    await expect(page.locator(`${SHEET} li`, { hasText: 'Matching line:' })).toBeVisible();
  });
  expect(sheetOffenders, 'G5 /verify, Source Trace sheet open').toEqual([]);
  const sheetShot = testInfo.outputPath('verify-sheet-reduced.png');
  await page.screenshot({ path: sheetShot, fullPage: false });
  testInfo.annotations.push({ type: 'gate-g5-screenshot', description: sheetShot });

  // Snapshot 4: after It matches, with the sheet still open and saying so.
  const checkedOffenders = await reducedMotionSnapshot(page, async () => {
    await page.getByRole('dialog', { name: 'Source for Creatinine' }).getByRole('button', { name: MARK_CHECKED }).click();
    await expect(page.getByText(SHEET_CHECKED)).toBeVisible();
  });
  expect(checkedOffenders, 'G5 /verify, after It matches in the sheet').toEqual([]);
  const checkedShot = testInfo.outputPath('verify-sheet-checked-reduced.png');
  await page.screenshot({ path: checkedShot, fullPage: false });
  testInfo.annotations.push({ type: 'gate-g5-screenshot', description: checkedShot });
});

/**
 * Headless Chromium starts a CSS animation at the first frame after it mounts, and an idle page can make that frame late
 * (seen once in the dialog case: every spinner read the identity at 50 ms and a rotation 300 ms later). Two frames put the
 * start before the 50 ms the gate waits, so a spinning svg is seen as the rotation it is.
 */
async function twoFrames(page: Page): Promise<void> {
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}

// Review round 1 (major): the unheld G5 snapshot passes only because the mock answers inside 50 ms. A real server is
// slower, and then the Verify button of every unverified row shows its spinner (the mutation's pending flag is shared),
// and under reduced motion a rotating svg has a non-identity transform. The pending spinners breathe instead.
// Blind spot: it reads the transform only. It does not see that the pulse is visible, nor a spinner elsewhere on the page.
test('UI-PG-REVIEW Gate G5 reduced motion: no transform 50 ms after Verify while the server is still answering', async ({
  page,
}) => {
  const mock = await prepare(page);
  await openReview(page);
  mock.review.holdVerify();
  const offenders = await reducedMotionSnapshot(page, async () => {
    await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
    await expect.poll(() => mock.review.requests.filter((request) => request.startsWith('POST ')).length).toBe(1);
    await twoFrames(page);
  });
  // The spinner is on screen, so the snapshot saw the pending state and not a finished one.
  await expect(page.locator('button[aria-label="Verify observation"] svg.lucide-loader2').first()).toBeAttached();
  mock.review.releaseVerify();
  expect(offenders, 'G5 /verify, Verify pending').toEqual([]);
});

test('UI-PG-REVIEW Gate G5 reduced motion: no transform 50 ms after Save & Verify while the server is still answering', async ({
  page,
}) => {
  const mock = await prepare(page);
  await openReview(page);
  await row(page, A1C_ID).getByRole('button', { name: 'Edit value' }).click();
  const dialog = page.getByRole('dialog', { name: 'Edit Value' });
  await expect(dialog).toBeVisible();
  mock.review.holdVerify();
  const offenders = await reducedMotionSnapshot(page, async () => {
    await dialog.getByRole('button', { name: /save & verify/i }).click();
    await expect.poll(() => mock.review.requests.filter((request) => request.startsWith('POST ')).length).toBe(1);
    await twoFrames(page);
  });
  await expect(dialog.locator('svg.lucide-loader2')).toBeAttached();
  mock.review.releaseVerify();
  expect(offenders, 'G5 /verify, Save & Verify pending').toEqual([]);
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

// ---------------------------------------------------------------------------
// L0 ruling on review round 3, finding 5: an entity in the one-third column. Checking it must not widen the page
// or move any entity value, at the desktop widths where the nowrap cells once overflowed.
// ---------------------------------------------------------------------------
for (const width of [1024, 1280, 1440]) {
  test(`HC-UIREV-004: checking an entity keeps the page inside the viewport and every value still, at ${width}`, async ({
    page,
  }) => {
    await prepare(page, { width, height: 900 });
    await openReview(page);
    // The value nodes only: the "Checked by you" chip is a T0 node too, and it is not there before the click.
    const values = page.locator('[id^="entity-row-"] td span[data-t0]:not([data-state])');
    await expect(values).toHaveCount(4);
    const measure = () =>
      values.evaluateAll((nodes) =>
        nodes.map((node) => {
          const r = node.getBoundingClientRect();
          return { x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height };
        })
      );
    const scrollBefore = await noHorizontalScroll(page);
    expect(scrollBefore.ok, `${width} before: ${JSON.stringify(scrollBefore)}`).toBe(true);
    const before = await measure();

    const target = page.locator('#entity-row-ent-review-long');
    await target.getByRole('button', { name: 'Verify Finding' }).click();
    await expect(target.locator('[data-state="checked-by-you"]')).toBeVisible();
    await page.waitForLoadState('networkidle');

    const scrollAfter = await noHorizontalScroll(page);
    expect(scrollAfter.ok, `${width} after: ${JSON.stringify(scrollAfter)}`).toBe(true);
    const after = await measure();
    expect(after.length).toBe(before.length);
    after.forEach((box, index) => expectSameBox(box, before[index], `entity value ${index} at ${width}`));
  });
}

// Timing: quiet box only. The title carries HC-UIREV-002 so the quiet-box line for that gate selects it.
test('HC-UIREV-002: an entity value passes stillnessProbe from the entity Verify click', async ({ page }) => {
  await prepare(page);
  await openReview(page);
  const verifyEntity = page.locator('#entity-row-ent-review-long').getByRole('button', { name: 'Verify Finding' });
  // The button is below the fold at 1440 x 900 (y 1430). Playwright's click() would scroll the page 825 px inside the
  // probe's window, and the probe would charge that scroll to the product (measured: window.scrollY is 825 at the
  // pointerdown, before any click handler runs). Scroll first; the probe still fails on any scroll the product does.
  await verifyEntity.scrollIntoViewIfNeeded();
  await settle(page);
  const report = await stillnessProbe(page, {
    trigger: () => verifyEntity.click(),
    expected: ['[id^="entity-row-"] span[data-t0]', '#entity-row-ent-review-long [data-state="checked-by-you"]'],
    kind: 'interaction',
  });
  expect(report.nodes).toBeGreaterThan(0);
  await expect(page.locator('#entity-row-ent-review-long [data-ink-marker]')).toHaveAttribute('data-state', 'ink');
});

// ---------------------------------------------------------------------------
// Finding 8: a Verify keeps the selected row and its Source Preview (ruling 6604622632).
// ---------------------------------------------------------------------------
const pagesRequests = (requests: readonly string[]): number =>
  requests.filter((request) => request === `GET /documents/${DOC_ID}/pages`).length;
const selectRow = (page: Page, id: string, name: string) => row(page, id).locator('span.font-medium', { hasText: name }).click();

// Functional (no timing threshold). Written red first: on f7e03ea7 the effect re-ran handleRowSelect on every
// observations change, so a Verify fetched /pages again, swapped the preview for a spinner and selected the first row.
// Blind spot: it samples with a MutationObserver and a frame loop, so a spinner that lives and dies inside one task
// with no frame and no mutation record cannot happen (React commits are mutations); it watches the one document.
test('UI-PG-REVIEW finding 8: a Verify on a row that is not the first keeps the selection, the Source Preview node and the /pages count', async ({
  page,
}) => {
  const mock = await prepare(page);
  await openReview(page);
  await selectRow(page, SOURCED_ID, 'Creatinine');
  await expect(row(page, SOURCED_ID)).toHaveClass(/bg-accent-subtle/);
  const image = page.locator('[data-page-image-overlay] img');
  await expect(image).toBeVisible();
  await expect(page.locator('p.font-mono', { hasText: 'Creatinine 0.9 mg/dL' })).toBeVisible();
  await settle(page);

  const pagesBefore = pagesRequests(mock.review.requests);
  const getsBefore = mock.review.requests.filter((request) => request === 'GET /observations').length;
  expect(pagesBefore, 'the first load and the click each fetched the pages').toBe(2);

  // Tag the live nodes and watch every mutation and every frame from here until the end of the Verify.
  await page.evaluate(() => {
    const SPINNER = 'svg.animate-spin.w-8.h-8';
    const w = window as unknown as { __f8: Record<string, unknown> };
    const img = document.querySelector('[data-page-image-overlay] img');
    // The page text itself, not its box: the loading, loaded and empty boxes are all one div, which React reuses.
    const preview = document.querySelector('p.font-mono');
    const probe = { img, preview, spinnerSeen: 0, detached: 0, stop: false };
    w.__f8 = probe;
    new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => {
          if (node instanceof Element && (node.matches(SPINNER) || node.querySelector(SPINNER))) probe.spinnerSeen += 1;
        });
        mutation.removedNodes.forEach((node) => {
          if (node === img || node === preview || (node instanceof Element && (node.contains(img) || node.contains(preview)))) {
            probe.detached += 1;
          }
        });
      }
    }).observe(document.body, { subtree: true, childList: true });
    const frame = () => {
      if (document.querySelector(SPINNER)) probe.spinnerSeen += 1;
      if (!probe.stop) requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  });

  await row(page, SOURCED_ID).getByRole('button', { name: 'Verify observation' }).click();
  await expect(row(page, SOURCED_ID).locator('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
  await expect.poll(() => mock.review.requests.filter((request) => request === 'GET /observations').length).toBeGreaterThan(getsBefore);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(300);

  const seen = await page.evaluate(() => {
    const probe = (window as unknown as { __f8: { img: Element; preview: Element; spinnerSeen: number; detached: number; stop: boolean } }).__f8;
    probe.stop = true;
    return {
      spinnerSeen: probe.spinnerSeen,
      detached: probe.detached,
      sameImage: document.querySelector('[data-page-image-overlay] img') === probe.img && probe.img.isConnected,
      samePreview: document.querySelector('p.font-mono') === probe.preview && probe.preview.isConnected,
    };
  });
  expect.soft(pagesRequests(mock.review.requests), 'no new GET /pages').toBe(pagesBefore);
  expect.soft(seen.spinnerSeen, 'the Source Preview spinner never showed').toBe(0);
  expect.soft(seen.detached, 'the preview and the image were never removed from the page').toBe(0);
  expect.soft(seen.sameImage, 'the page image is the same element').toBe(true);
  expect.soft(seen.samePreview, 'the preview page text is the same element').toBe(true);
  await expect.soft(row(page, SOURCED_ID), 'the selection stayed on the verified row').toHaveClass(/bg-accent-subtle/);
  await expect.soft(row(page, GLUCOSE_ID), 'the first row was not selected').not.toHaveClass(/bg-accent-subtle/);
});

// PIN, green before and after the fix (it guards against a fix that stops re-selecting): a click on a row on another
// page still selects it and loads its page. Blind spot: the mock serves PAGES_BODY for the one document, so a
// second document is not covered here.
test('UI-PG-REVIEW finding 8: selecting a row on another page still loads it, and selecting back drops it', async ({ page }) => {
  const mock = await prepare(page);
  const imageRequests: string[] = [];
  page.on('request', (request) => {
    if (/\/pages\/\d+\/image/.test(request.url())) imageRequests.push(new URL(request.url()).pathname);
  });
  await openReview(page);
  await expect(row(page, GLUCOSE_ID)).toHaveClass(/bg-accent-subtle/);
  await expect(page.locator('[data-page-image-overlay]')).toHaveCount(0);

  await selectRow(page, SOURCED_ID, 'Creatinine');
  await expect(row(page, SOURCED_ID)).toHaveClass(/bg-accent-subtle/);
  await expect(page.locator('[data-page-image-overlay] img')).toBeVisible();
  expect(imageRequests.some((path) => path.endsWith(`/documents/${DOC_ID}/pages/3/image`))).toBe(true);
  expect(pagesRequests(mock.review.requests)).toBe(2);

  await selectRow(page, GLUCOSE_ID, 'Glucose');
  await expect(row(page, GLUCOSE_ID)).toHaveClass(/bg-accent-subtle/);
  await expect(page.locator('[data-page-image-overlay]')).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// The still toast's mount state (ruling 6604622632): `still` promises "enters with no motion", and sonner's base rule
// starts every toast at opacity 0 and translateY(100%) until data-mounted turns true.
// ---------------------------------------------------------------------------
/** What the probe reads from a toast li at one instant. */
interface ToastSample {
  when: string;
  mounted: string | null;
  front: string | null;
  opacity: number;
  ty: number;
  transform: string;
  rect: { left: number; top: number; width: number; height: number };
}

/** Starts recording every sonner toast li: synchronously on insertion, on each data-mounted change and for 20 frames. */
async function recordToasts(page: Page): Promise<void> {
  await page.evaluate(() => {
    const samples: unknown[] = [];
    (window as unknown as { __toastSamples: unknown[] }).__toastSamples = samples;
    const read = (li: Element, when: string, index: number) => {
      const style = getComputedStyle(li);
      const box = li.getBoundingClientRect();
      samples.push({
        when,
        index,
        mounted: li.getAttribute('data-mounted'),
        front: li.getAttribute('data-front'),
        opacity: parseFloat(style.opacity),
        ty: new DOMMatrix(style.transform === 'none' ? undefined : style.transform).f,
        transform: style.transform,
        rect: { left: box.left, top: box.top, width: box.width, height: box.height },
      });
    };
    const all = () => Array.from(document.querySelectorAll('[data-sonner-toast]'));
    new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) return;
          const lis = node.matches('[data-sonner-toast]') ? [node] : Array.from(node.querySelectorAll('[data-sonner-toast]'));
          for (const li of lis) {
            read(li, 'insert', all().indexOf(li));
            let frames = 0;
            const frame = () => {
              read(li, 'frame', all().indexOf(li));
              if (++frames < 20) requestAnimationFrame(frame);
            };
            requestAnimationFrame(frame);
          }
        });
        if (mutation.type === 'attributes' && mutation.target instanceof Element && mutation.target.matches('[data-sonner-toast]')) {
          read(mutation.target, 'attribute', all().indexOf(mutation.target));
        }
      }
    }).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['data-mounted'] });
  });
}

const toastSamples = (page: Page): Promise<ToastSample[]> =>
  page.evaluate(() => (window as unknown as { __toastSamples: ToastSample[] }).__toastSamples.slice());

// Written red first. On f7e03ea7 the first sample of a still toast was opacity 0 and 100 % below its place.
// Blind spot: it uses the Verify toast, which is still; a plain toast starts the same way and is not asserted here
// (ui-toast.spec.ts HC-TOAST-001 owns that). It reads computed style and rect, so a repaint-only change is not seen.
test('UI-PG-REVIEW still toast: across its mount frame the toast has full opacity and does not move', async ({ page }) => {
  await prepare(page);
  await openReview(page);
  await recordToasts(page);
  await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
  await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);
  await expect.poll(async () => (await toastSamples(page)).length, { message: 'the probe sampled frames' }).toBeGreaterThan(20);

  const samples = await toastSamples(page);
  const first = samples.find((sample) => sample.when === 'insert');
  expect(first, 'the probe saw the insertion synchronously').toBeDefined();
  expect(
    samples.filter((sample) => sample.mounted === 'false').length,
    'the probe saw data-mounted="false" on at least one sample, or this test passes vacuously'
  ).toBeGreaterThan(0);
  expect(first!.mounted, 'the insertion sample is the mount state').toBe('false');

  for (const sample of samples) {
    expect.soft(sample.opacity, `opacity at ${sample.when} (mounted=${sample.mounted})`).toBe(1);
    expect.soft(sample.ty, `translateY at ${sample.when} (mounted=${sample.mounted}), transform ${sample.transform}`).toBe(0);
    expect.soft(sample.rect, `rect at ${sample.when} (mounted=${sample.mounted}) against the insertion rect`).toEqual(first!.rect);
  }
});

// PIN, named as one: green on f7e03ea7 and green after the fix. Two still toasts stack as they do today: the older one
// is not the front, sits at its stack offset, and no inline --y was set (stacking reads --y from sonner's own rules).
// Blind spot: two toasts only; the expanded (hovered) stack is not covered.
test('UI-PG-REVIEW still toast: two still toasts stack, the older one at its offset with no inline --y', async ({ page }) => {
  await prepare(page);
  await openReview(page);
  await row(page, GLUCOSE_ID).getByRole('button', { name: 'Verify observation' }).click();
  await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);
  await row(page, A1C_ID).getByRole('button', { name: 'Verify observation' }).click();
  await expect(page.locator('[data-sonner-toast]')).toHaveCount(2);
  // Both are past their mount frame before the stack is read.
  await expect(page.locator('[data-sonner-toast][data-mounted="true"]')).toHaveCount(2);

  const stack = await page.evaluate(() =>
    Array.from(document.querySelectorAll<HTMLElement>('[data-sonner-toast]')).map((li) => ({
      text: li.textContent,
      front: li.getAttribute('data-front'),
      inlineY: li.style.getPropertyValue('--y'),
      ty: new DOMMatrix(getComputedStyle(li).transform === 'none' ? undefined : getComputedStyle(li).transform).f,
      scale: new DOMMatrix(getComputedStyle(li).transform === 'none' ? undefined : getComputedStyle(li).transform).d,
    }))
  );
  const older = stack.find((toast) => toast.text?.includes('Glucose'))!;
  const newer = stack.find((toast) => toast.text?.includes('Hemoglobin'))!;
  expect(older, 'the Glucose toast is still on screen').toBeDefined();
  expect(newer, 'the A1c toast is on screen').toBeDefined();
  expect(older.front).toBe('false');
  expect(newer.front).toBe('true');
  expect(older.inlineY, 'no inline --y on the older toast').toBe('');
  expect(newer.inlineY, 'no inline --y on the front toast').toBe('');
  expect(newer.ty, 'the front toast sits at its place').toBe(0);
  expect(older.ty, 'the older toast sits at its stack offset, off the front toast').not.toBe(0);
  // sonner's stack scale is --toasts-before * 0.05 + 1 (dist/styles.css:298-299): one toast in front gives 1.05.
  expect(Math.abs(older.scale), 'the older toast has sonner\'s stack scale (1.05 for one toast in front)').toBeCloseTo(1.05, 2);
});
