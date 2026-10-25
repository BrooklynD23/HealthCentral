/**
 * UI-PROVENANCE e2e (plan section 7.6): HC-UIPV-001 (popover opens on click and
 * Enter, not hover; Escape closes and returns focus), HC-UIPV-002 (a tap opens it
 * in a hasTouch context), HC-UIPV-006 (popover part: stillnessProbe from the
 * opening click), and Gate G on the three routes that show the citation popover
 * or PageImageOverlay: /interpret, /inbox and /verify.
 *
 * Every /api/v1 request is answered by the spec-local mock below, typed from
 * src/services/types.ts. Any other request is recorded as unmocked, answered
 * with 599, and fails the guard. Run without the backend, as e2e/README.md
 * recipe 2 describes:
 *   PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-provenance.spec.ts --project=chromium
 */

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Locator, type Page, type Route } from '@playwright/test';
import type {
  Document,
  InterpretationResponse,
  Observation,
  TrendData,
} from '../src/services/types';
import {
  axeGate,
  consoleAndNetworkGuard,
  maxEventDuration,
  measureCls,
  noHorizontalScroll,
  reducedMotionSnapshot,
  setTheme,
  stillnessProbe,
  type Theme,
  WCAG_TAGS,
} from './support/gates';

const PROFILE_ID = '8d2f4a10-6c1e-4b7a-9f00-0000000e2e01';
const DOCUMENT_ID = '3b9a1f20-1111-4a2b-8c3d-000000000001';
const OBSERVATION_ID = '6f1c2c4e-8a1b-4c3d-9e0f-123456789abc';

const observation: Observation = {
  id: OBSERVATION_ID,
  profile_id: PROFILE_ID,
  doc_id: DOCUMENT_ID,
  analyte_canonical: 'glucose',
  analyte_raw: 'Glucose',
  value: 96,
  value_text: null,
  unit: 'mg/dL',
  ref_low: 70,
  ref_high: 99,
  ref_range_text: '70-99 mg/dL',
  flag: null,
  is_abnormal: false,
  collected_at: '2026-04-10T00:00:00',
  user_verified: false,
  extraction_confidence: 0.92,
  source_page: 3,
  // The backend stores [x0,y0,x1,y1] (api/documents.py:661), the form parseBbox reads (VerificationWorkbench.tsx).
  source_bbox_json: '[10,20,200,40]',
};

/** A second value on page 1, so /verify can switch the page image to another page. */
const OTHER_OBSERVATION_ID = '6f1c2c4e-8a1b-4c3d-9e0f-00000000a1c1';
const otherObservation: Observation = {
  ...observation,
  id: OTHER_OBSERVATION_ID,
  analyte_canonical: 'hemoglobin_a1c',
  analyte_raw: 'Hemoglobin A1c',
  value: 5.4,
  unit: '%',
  ref_low: 4.0,
  ref_high: 5.6,
  ref_range_text: '4.0-5.6 %',
  source_page: 1,
};

const documentFixture: Document = {
  id: DOCUMENT_ID,
  profile_id: PROFILE_ID,
  doc_type: 'lab_report',
  source: 'provenance-report.pdf',
  status: 'needs_review',
  page_count: 3,
  collection_date: '2026-04-10',
  imported_at: '2026-04-11T09:00:00',
  parsed_at: '2026-04-11T09:01:00',
  verified_at: null,
  extraction_confidence: 0.92,
};

const interpretation: InterpretationResponse = {
  id: '9c0e7a55-2222-4d3e-8f4a-000000000002',
  observation_id: OBSERVATION_ID,
  interpretation_text: 'Your fasting glucose is within the reference range for this test.',
  severity_level: 'normal',
  advice_text: null,
  citations: [
    {
      type: 'knowledge_base',
      id: 'kb-glucose-1',
      text: 'Fasting glucose between 70 and 99 mg/dL is within the usual reference range.',
    },
  ],
  context: null,
  model_id: 'mock-model',
  model_tier: 'local',
  confidence_score: 0.9,
  requires_physician_review: false,
  physician_review_reason: null,
  viewed_at: null,
  created_at: '2026-04-10T12:00:00',
};

const trend: TrendData = {
  analyte_canonical: 'glucose',
  analyte_display_name: 'Glucose',
  unit: 'mg/dL',
  ref_low: 70,
  ref_high: 99,
  data_points: [],
  summary: '',
};

const externalApiSettings = {
  use_external_api: false,
  provider: 'none',
  model: '',
  api_key_configured: false,
  redaction_break_glass: false,
};

/**
 * A 400x100 PNG for every page. The bbox [10,20,200,40] sits inside it, so the highlight lands on the
 * page. A 1x1 image would scale the bbox to thousands of px and push it off-screen (recurring-failures #1).
 */
const PAGE_PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAZAAAABkCAIAAAAnqfEgAAABDUlEQVR42u3UQREAAAzCMPyrRQI6tksk9NEU4IhIABgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYwF8DXxGNujLHPvkAAAAASUVORK5CYII=';
const PAGE_PNG = Buffer.from(PAGE_PNG_BASE64, 'base64');

/** Answers every /api/v1 request from the fixtures above; records the rest. */
async function mockApi(page: Page): Promise<string[]> {
  const unmocked: string[] = [];
  await page.route(/\/api\/v1\//, async (route: Route, request) => {
    const url = new URL(request.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '').replace(/\/+$/, '') || '/';
    const label = `${request.method()} /api/v1${path}${url.search}`;
    const json = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (request.method() === 'GET') {
      // /verify lists the rows that need verification; the other routes read the single observation.
      if (path === '/observations') {
        return json(url.searchParams.get('needs_verification') === 'true' ? [observation, otherObservation] : [observation]);
      }
      if (path === '/observations/trends/glucose') return json(trend);
      if (path === `/interpretations/observations/${OBSERVATION_ID}/interpretation`) {
        return json(interpretation);
      }
      if (path === '/settings/model/external-api') return json(externalApiSettings);
      if (path === '/documents') return json([documentFixture]);
      if (path === '/documents/highlights/summary') return json([]);
      if (path === '/pinboards') return json([]);
      if (path === `/documents/${DOCUMENT_ID}/entities`) return json([]);
      if (path === `/documents/${DOCUMENT_ID}/pages`) {
        return json([
          { page_number: 1, text: '', has_tables: false },
          { page_number: 3, text: '', has_tables: false },
        ]);
      }
      if (/^\/documents\/[^/]+\/pages\/\d+\/image$/.test(path)) {
        return route.fulfill({ status: 200, contentType: 'image/png', body: PAGE_PNG });
      }
    }
    unmocked.push(label);
    return json({ detail: 'not mocked by ui-provenance.spec.ts' }, 599);
  });
  return unmocked;
}

/** A session the auth store accepts, so ProtectedRoute lets the page through. */
async function seedSession(page: Page): Promise<void> {
  await page.addInitScript(
    ({ profileId, expiresAt }) => {
      try {
        window.localStorage.setItem(
          'healthcentral-auth',
          JSON.stringify({
            state: {
              token: 'ui-provenance-e2e-token',
              profileId,
              profileName: 'Provenance E2E',
              expiresAt,
              isAuthenticated: true,
            },
            version: 0,
          })
        );
      } catch {
        // Storage blocked: the page shows the sign-in route, and the test fails there.
      }
    },
    { profileId: PROFILE_ID, expiresAt: Date.now() + 60 * 60 * 1000 }
  );
}

/**
 * Waits until the element's effective opacity is 1 and its box has not moved for
 * six frames. Playwright's visibility check accepts opacity 0, so a route that is
 * still fading in would otherwise look ready.
 */
async function waitForSettled(page: Page, selector: string): Promise<void> {
  await page.waitForFunction(
    (sel) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      let opacity = 1;
      for (let node: Element | null = el; node; node = node.parentElement) {
        opacity *= Number(getComputedStyle(node).opacity);
      }
      const rect = el.getBoundingClientRect();
      const w = window as unknown as { __hcSettle?: { x: number; y: number; frames: number } };
      const prev = w.__hcSettle;
      const stable = prev !== undefined && Math.abs(prev.x - rect.x) < 0.01 && Math.abs(prev.y - rect.y) < 0.01;
      const frames = stable ? prev.frames + 1 : 0;
      w.__hcSettle = { x: rect.x, y: rect.y, frames };
      return opacity >= 0.99 && frames >= 6;
    },
    selector,
    { polling: 'raf', timeout: 10_000 }
  );
}

const CHIP = '[aria-label^="Citation 1:"]';
const POPOVER = '[role="dialog"][aria-label="Citation 1"]';
const VIEW_DOCUMENT = 'button[aria-label="View document"]';
const PREVIEW_IMAGE = 'img[alt="Page 1 of document"][src^="blob:"]';
const SOURCE_IMAGE = 'img[alt="Page 3 of document"][src^="blob:"]';
const PAGE_ONE_IMAGE = 'img[alt="Page 1 of document"][src^="blob:"]';
/** The PageImageOverlay root (a data hook on its Card; PageImageOverlay.tsx). */
const PAGE_IMAGE_OVERLAY = '[data-page-image-overlay]';
/** The TraceMark inside the bbox highlight. /verify must show it, so a missing mark fails the own-node match. */
const PAGE_IMAGE_TRACE_MARK = '[data-page-image-overlay] [data-trace-mark]';
/** The identity transform, as gates.ts's G5 helper spells it (kept spec-local: gates.ts is not in this row). */
const IDENTITY_TRANSFORM_SOURCE =
  '^(none|matrix\\(\\s*1,\\s*0,\\s*0,\\s*1,\\s*0,\\s*0\\s*\\)|matrix3d\\(\\s*1,\\s*0,\\s*0,\\s*0,\\s*0,\\s*1,\\s*0,\\s*0,\\s*0,\\s*0,\\s*1,\\s*0,\\s*0,\\s*0,\\s*0,\\s*1\\s*\\))$';

interface GateRoute {
  path: string;
  /** Opens the route and waits until it is ready for the gate's interaction. */
  ready: (page: Page) => Promise<void>;
  /** The gate's interaction: the popover, or the document preview with its page image. */
  interact: (page: Page) => Promise<void>;
  /**
   * This row's own nodes after the interaction. G1, G5 and G6 are judged on these
   * only; the rest of the page is recorded, never asserted.
   */
  own: string[];
  /** The own nodes that already exist before the interaction (empty when none do). */
  ownBefore: string[];
}

/** Records one Gate G line: an annotation for the PR body and a console line. */
function recordLine(line: string): void {
  test.info().annotations.push({ type: 'gate-g-record', description: line });
  console.log(line);
}

/** Visible nodes matching a selector. A scoped check on zero nodes proves nothing (recurring-failures #1). */
async function visibleMatchCount(page: Page, selector: string): Promise<number> {
  return page.locator(selector).evaluateAll(
    (els) =>
      els.filter((el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
      }).length
  );
}

/** Non-vacuity guard: every own selector must match at least one visible node, or the check fails. */
async function assertOwnMatched(page: Page, selectors: string[], phase: string): Promise<void> {
  for (const selector of selectors) {
    expect(
      await visibleMatchCount(page, selector),
      `${phase}: own selector matches no visible node: ${selector}`
    ).toBeGreaterThan(0);
  }
}

/** G1 scoped: serious or critical axe violations inside each own node, in one theme. */
async function ownAxeBlocking(page: Page, selectors: string[], theme: Theme): Promise<string[]> {
  await setTheme(page, theme);
  const found: string[] = [];
  for (const selector of selectors) {
    const result = await new AxeBuilder({ page }).withTags(WCAG_TAGS).include(selector).analyze();
    for (const violation of result.violations) {
      if (violation.impact !== 'serious' && violation.impact !== 'critical') continue;
      for (const node of violation.nodes) {
        found.push(`${violation.id} ${node.target.join(' ')} (own ${selector})`);
      }
    }
  }
  return found;
}

/**
 * Record only: the page-wide axe result for one theme. Each serious or critical node is
 * named OWN when it sits inside a row-owned selector, and OUTSIDE otherwise.
 */
async function recordPageWideAxe(page: Page, own: string[], theme: Theme, path: string): Promise<void> {
  const full = await axeGate(page, { theme });
  for (const violation of full.blocking) {
    for (const node of violation.nodes) {
      const target = node.target.join(' ');
      const inOwn = await page.evaluate(
        ({ selector, selectors }) => {
          try {
            const el = document.querySelector(selector);
            return el !== null && selectors.some((s) => el.closest(s) !== null);
          } catch {
            return false;
          }
        },
        { selector: target, selectors: own }
      );
      recordLine(`G1 ${path} ${theme} ${violation.id} ${inOwn ? 'OWN' : 'OUTSIDE'} ${target}`);
    }
  }
}

/** G5 scoped: each own node and its descendants must have the identity transform. */
async function ownTransformOffenders(page: Page, selectors: string[]): Promise<string[]> {
  return page.evaluate(
    ({ sels, identitySource }) => {
      const identity = new RegExp(identitySource);
      const offenders: string[] = [];
      for (const selector of sels) {
        for (const root of Array.from(document.querySelectorAll(selector))) {
          for (const el of [root, ...Array.from(root.querySelectorAll('*'))]) {
            const transform = getComputedStyle(el).transform;
            if (!identity.test(transform)) {
              offenders.push(`${selector}: ${el.tagName.toLowerCase()} transform=${transform}`);
            }
          }
        }
      }
      return offenders;
    },
    { sels: selectors, identitySource: IDENTITY_TRANSFORM_SOURCE }
  );
}

/** G6 scoped: each visible own node inside the viewport, and not scrolling itself sideways. */
async function ownBoxProblems(page: Page, selectors: string[]): Promise<string[]> {
  const measured = await page.evaluate((sels) => {
    const rows: { selector: string; left: number; right: number; scrollWidth: number; clientWidth: number; innerWidth: number }[] = [];
    for (const selector of sels) {
      for (const el of Array.from(document.querySelectorAll(selector))) {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;
        rows.push({
          selector,
          left: rect.left,
          right: rect.right,
          scrollWidth: el.scrollWidth,
          clientWidth: el.clientWidth,
          innerWidth: window.innerWidth,
        });
      }
    }
    return rows;
  }, selectors);
  const problems: string[] = [];
  for (const r of measured) {
    if (r.left < 0) problems.push(`${r.selector}: left ${r.left.toFixed(1)} < 0`);
    if (r.right > r.innerWidth) problems.push(`${r.selector}: right ${r.right.toFixed(1)} > innerWidth ${r.innerWidth}`);
    if (r.scrollWidth > r.clientWidth) {
      problems.push(`${r.selector}: scrollWidth ${r.scrollWidth} > clientWidth ${r.clientWidth}`);
    }
  }
  return problems;
}

/**
 * Record only (G6 at 390 and 320 in this row): the own-node box problems for one phase, with the
 * visible match count per selector, so an empty problem list cannot pass by matching nothing.
 */
async function recordOwnBoxes(page: Page, label: string, selectors: string[]): Promise<string[]> {
  const problems = await ownBoxProblems(page, selectors);
  const matched = await Promise.all(selectors.map((selector) => visibleMatchCount(page, selector)));
  recordLine(`${label} matched ${matched.join('/')}, problems ${problems.length ? problems.join('; ') : 'none'}`);
  return problems;
}

const GATE_ROUTES: GateRoute[] = [
  {
    path: '/interpret',
    ready: async (page) => {
      await page.goto('/interpret');
      await expect(page.locator(CHIP)).toBeVisible();
      await waitForSettled(page, CHIP);
    },
    interact: async (page) => {
      await page.locator(CHIP).click();
      await expect(page.locator(POPOVER)).toBeVisible();
    },
    own: [CHIP, POPOVER],
    ownBefore: [CHIP],
  },
  {
    path: '/inbox',
    ready: async (page) => {
      await page.goto('/inbox');
      await expect(page.locator(VIEW_DOCUMENT)).toBeAttached();
      // On a fine pointer the row actions are opacity 0 until the row is hovered.
      await page.locator(VIEW_DOCUMENT).hover();
      await waitForSettled(page, VIEW_DOCUMENT);
    },
    interact: async (page) => {
      await page.locator(VIEW_DOCUMENT).click();
      await expect(page.locator(PREVIEW_IMAGE)).toBeVisible();
      // toBeVisible accepts opacity 0, and the image is opacity 0 until onLoad. The card's note also appears
      // only after onLoad (PageImageOverlay.tsx), so wait for the loaded, settled image before the own-node checks.
      await waitForSettled(page, PREVIEW_IMAGE);
    },
    // The preview mounts PageImageOverlay (bbox null). No row-owned node exists before the click.
    own: [PAGE_IMAGE_OVERLAY],
    ownBefore: [],
  },
  {
    path: '/verify',
    ready: async (page) => {
      // ?doc= selects the document's first observation, which mounts PageImageOverlay.
      await page.goto(`/verify?doc=${DOCUMENT_ID}`);
      await expect(page.locator(SOURCE_IMAGE)).toBeVisible();
      await waitForSettled(page, SOURCE_IMAGE);
    },
    interact: async (page) => {
      // Another page: PageImageOverlay refetches for page 1, its highlight unmounts and remounts,
      // and a fresh TraceMark mounts after reduced motion is emulated. Re-selecting the same row would not.
      await page.getByText('Hemoglobin A1c', { exact: true }).first().click();
      // toBeVisible accepts opacity 0, and the image is opacity 0 until onLoad. The highlight and its TraceMark
      // mount only after onLoad (PageImageOverlay.tsx), so wait for the settled page-1 image, then for its mark.
      await waitForSettled(page, PAGE_ONE_IMAGE);
      await expect(page.locator(PAGE_IMAGE_TRACE_MARK)).toBeVisible();
    },
    own: [PAGE_IMAGE_OVERLAY, PAGE_IMAGE_TRACE_MARK],
    ownBefore: [PAGE_IMAGE_OVERLAY, PAGE_IMAGE_TRACE_MARK],
  },
];

// ---------------------------------------------------------------------------
// HC-UIPV-001: click and Enter open the popover; Escape closes it and returns focus.
// ---------------------------------------------------------------------------
test('HC-UIPV-001 hover does not open the popover; click opens it; Enter opens it; Escape closes it and returns focus', async ({
  page,
}) => {
  await mockApi(page);
  await seedSession(page);
  await page.goto('/interpret');
  await expect(page.locator(CHIP)).toBeVisible();
  await waitForSettled(page, CHIP);
  const chip = page.locator(CHIP);
  const popover = page.locator(POPOVER);

  await chip.hover();
  await expect(popover).toHaveCount(0);
  await expect(page.getByRole('tooltip')).toHaveCount(0);

  await chip.click();
  await expect(popover).toBeVisible();
  await expect(popover).toContainText(interpretation.citations[0].text);
  await page.keyboard.press('Escape');
  await expect(popover).toHaveCount(0);
  await expect(chip).toBeFocused();

  await chip.focus();
  await page.keyboard.press('Enter');
  await expect(popover).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(popover).toHaveCount(0);
  await expect(chip).toBeFocused();
});

// ---------------------------------------------------------------------------
// HC-UIPV-002: a tap opens the popover in a touch context; the hit area is 44 px.
// ---------------------------------------------------------------------------
test.describe('HC-UIPV-002 touch', () => {
  test.use({ hasTouch: true, viewport: { width: 390, height: 844 } });

  test('HC-UIPV-002 a tap opens the citation popover, and the trigger is at least 44 by 44 px', async ({
    page,
  }) => {
    await mockApi(page);
    await seedSession(page);
    await page.goto('/interpret');
    await expect(page.locator(CHIP)).toBeVisible();
    await waitForSettled(page, CHIP);
    const chip: Locator = page.locator(CHIP);
    const box = await chip.boundingBox();
    expect(box, 'citation trigger has a layout box').not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(44);

    await chip.tap();
    await expect(page.locator(POPOVER)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// HC-UIPV-006 (popover part): stillnessProbe from the opening click on /interpret.
// ---------------------------------------------------------------------------
test('HC-UIPV-006 the citation popover is still from its opening click (stillnessProbe)', async ({
  page,
}) => {
  await mockApi(page);
  await seedSession(page);
  await page.goto('/interpret');
  await expect(page.locator(CHIP)).toBeVisible();
  await waitForSettled(page, CHIP);
  const chip = page.locator(CHIP);

  // Scroll the trigger into view before the probe starts. A click on an off-screen
  // trigger makes Playwright scroll the page, and that scroll moves every T0 node:
  // the probe would then measure the scroll, not the popover.
  await chip.scrollIntoViewIfNeeded();
  await waitForSettled(page, CHIP);

  const report = await stillnessProbe(page, {
    trigger: () => chip.click(),
    expected: [`${CHIP} [data-t0]`, `${POPOVER} [data-t0]`],
  });
  expect(report.postTriggerSamples).toBeGreaterThan(0);
  await expect(page.locator(POPOVER)).toBeVisible();
});

// ---------------------------------------------------------------------------
// Gate G on /interpret, /inbox and /verify.
// G1 axe light and dark, G5 reduced motion and G6 viewport fit are judged on this row's
// own nodes only (GATE_ROUTES[].own). The page-wide results are recorded, never asserted,
// and each outside node is named in the annotations for its owning row.
// G2 CLS over load and the interaction; G3 INP with CPU x4 for the interaction;
// G7 console and network.
// ---------------------------------------------------------------------------
for (const route of GATE_ROUTES) {
  test(`Gate G1 ${route.path} own nodes have no serious or critical violation in light or dark`, async ({ page }) => {
    await mockApi(page);
    await seedSession(page);
    await route.ready(page);
    // Before the interaction only the own nodes that already exist are scanned.
    await assertOwnMatched(page, route.ownBefore, 'before the interaction');
    const beforeLight = await ownAxeBlocking(page, route.ownBefore, 'light');
    const beforeDark = await ownAxeBlocking(page, route.ownBefore, 'dark');

    // The popover and the document preview exist only after the interaction. On /verify the page-3 highlight
    // is already up before it (ownBefore), and the interaction moves it to page 1.
    await route.interact(page);
    await assertOwnMatched(page, route.own, 'after the interaction');
    const afterLight = await ownAxeBlocking(page, route.own, 'light');
    const afterDark = await ownAxeBlocking(page, route.own, 'dark');

    // Record only: the full page, each node named OWN or OUTSIDE for the owning row.
    await recordPageWideAxe(page, route.own, 'light', route.path);
    await recordPageWideAxe(page, route.own, 'dark', route.path);

    expect(beforeLight, 'light theme, before the interaction').toEqual([]);
    expect(beforeDark, 'dark theme, before the interaction').toEqual([]);
    expect(afterLight, 'light theme, after the interaction').toEqual([]);
    expect(afterDark, 'dark theme, after the interaction').toEqual([]);
  });

  test(`Gate G2 ${route.path} CLS stays under 0.1 over load and the interaction`, async ({ page }) => {
    const cls = await measureCls(page, async () => {
      await mockApi(page);
      await seedSession(page);
      await route.ready(page);
      await route.interact(page);
    });
    expect(cls).toBeLessThan(0.1);
  });

  test(`Gate G3 ${route.path} the interaction stays under 200 ms with CPU throttled x4`, async ({ page }) => {
    await mockApi(page);
    await seedSession(page);
    await route.ready(page);
    const slowest = await maxEventDuration(page, () => route.interact(page));
    expect(slowest).toBeLessThan(200);
  });

  test(`Gate G5 ${route.path} own nodes and their descendants keep the identity transform under reduced motion`, async ({
    page,
  }) => {
    await mockApi(page);
    await seedSession(page);
    await route.ready(page);
    // Record only: every page-wide offender. The popper wrapper is outside the own set (GATES-POPPER-TRANSFORM).
    const pageWide = await reducedMotionSnapshot(page, () => route.interact(page));
    for (const offender of pageWide) recordLine(`G5 ${route.path} page-wide ${offender}`);
    // Read 50 ms after the interaction, on the own nodes and their descendants only.
    await assertOwnMatched(page, route.own, 'after the interaction');
    expect(await ownTransformOffenders(page, route.own)).toEqual([]);
  });

  // L0 ruling (2026-10-25 21:54:33Z, restated 21:56:34Z): G6 asserts at 1440 and 1024 here; 390 and 320 are record only, moved to UI-PG-REVIEW (/verify) and UI-PG-RESULTS (/interpret).
  for (const viewport of [
    { width: 1440, height: 900, asserted: true },
    { width: 1024, height: 768, asserted: true },
    { width: 390, height: 844, asserted: false },
    { width: 320, height: 640, asserted: false },
  ]) {
    const size = `${viewport.width}x${viewport.height}`;
    test(`Gate G6 ${route.path} own nodes stay inside the viewport at ${size}${viewport.asserted ? '' : ' (record only)'}`, async ({
      page,
    }) => {
      await page.setViewportSize(viewport);
      await mockApi(page);
      await seedSession(page);
      await route.ready(page);
      const pageBefore = await noHorizontalScroll(page);
      recordLine(`G6 ${route.path} ${size} page-wide before: scrollWidth ${pageBefore.scrollWidth}, innerWidth ${pageBefore.innerWidth}`);
      if (viewport.asserted) await assertOwnMatched(page, route.ownBefore, 'before the interaction');
      const beforeProblems = await recordOwnBoxes(page, `G6 ${route.path} ${size} own before`, route.ownBefore);

      await route.interact(page);
      const pageAfter = await noHorizontalScroll(page);
      recordLine(`G6 ${route.path} ${size} page-wide after: scrollWidth ${pageAfter.scrollWidth}, innerWidth ${pageAfter.innerWidth}`);
      if (viewport.asserted) await assertOwnMatched(page, route.own, 'after the interaction');
      const afterProblems = await recordOwnBoxes(page, `G6 ${route.path} ${size} own after`, route.own);

      if (!viewport.asserted) return;
      expect(beforeProblems, 'own nodes before the interaction').toEqual([]);
      expect(afterProblems, 'own nodes after the interaction').toEqual([]);
    });
  }

  test(`Gate G7 ${route.path} logs no console error and makes no non-localhost or unmocked request`, async ({ page }) => {
    const unmocked = await mockApi(page);
    await seedSession(page);
    const guard = consoleAndNetworkGuard(page, { mock: { unmocked } });
    await route.ready(page);
    await route.interact(page);
    guard.assertClean();
  });
}
