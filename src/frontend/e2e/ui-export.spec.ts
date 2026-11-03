/**
 * UI-PG-EXPORT e2e (plan section 7.7): the doctor-summary page at /export, end to end.
 *
 * Two describes, kept apart on purpose:
 *  - "HC-UIEXP e2e" is functional and has no timing in it: HC-UIEXP-001 in a real browser, G1 (axe, light and dark,
 *    including the open Sheet), G6 (390 and 320, empty and generated), G7, G9. Run it under normal load:
 *      PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-export.spec.ts --project=chromium --grep-invert QUIET-BOX
 *  - "QUIET-BOX" is G2, G3, G5 and G10, which are timing measurements. Run them on a quiet box only (RUNBOOK 10.1):
 *      PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-export.spec.ts --project=chromium --grep QUIET-BOX
 *    G3 is also run against the production build (`npm run build`, `npx vite preview`, HC_E2E_BASE_URL).
 *
 * The export calls are answered here (page.route, registered after installMockApi so it runs first); every other
 * /api/v1 call goes to the shared shell fixtures. Do not add these to e2e/support/mockApi.ts.
 */

import { expect, test, type Page, type Route } from '@playwright/test';
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

/** One long unbroken token and a long sentence: both must wrap or truncate inside the card at 320 px. */
const LONG_FINDING =
  'Hemoglobin A1c: 6.5% (H) with a note that reads ' +
  'ALongUnbrokenResultNameThatHasNoSpacesAtAllAndKeepsGoingPastTheEdgeOfAnyPhoneScreen_0123456789_0123456789';
const LONG_DOCUMENT_NAME =
  'Quest Diagnostics Reference Laboratory Comprehensive Metabolic Panel With Lipid Reflex And Extended Hematology Final ' +
  'ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ';

const documents = [
  {
    id: 'doc-export-1',
    profile_id: FIXTURE_PROFILE_ID,
    doc_type: 'lab_report',
    source: LONG_DOCUMENT_NAME,
    status: 'verified',
    page_count: 2,
    collection_date: '2026-03-14',
    imported_at: '2026-03-15T10:12:00Z',
    parsed_at: '2026-03-15T10:12:04Z',
    verified_at: '2026-03-16T18:02:00Z',
    extraction_confidence: 0.94,
  },
  {
    id: 'doc-export-2',
    profile_id: FIXTURE_PROFILE_ID,
    doc_type: 'lab_report',
    source: 'Lipid panel, August',
    status: 'parsed',
    page_count: 1,
    collection_date: '2026-08-02',
    imported_at: '2026-08-03T07:41:00Z',
    parsed_at: '2026-08-03T07:41:03Z',
    verified_at: null,
    extraction_confidence: 0.71,
  },
];

const summary = {
  summary_id: 'summary-export-1',
  profile_id: FIXTURE_PROFILE_ID,
  generated_at: '2026-04-10T12:00:00Z',
  format: 'text',
  key_findings: [LONG_FINDING, 'Glucose: 95.0 mg/dL (normal)'],
  abnormal_count: 2,
  date_range: 'Mar 14, 2026 to Aug 2, 2026',
};

const questions = [
  {
    category: 'abnormal',
    question:
      'My hemoglobin A1c was outside the reference range on the March report. What might that indicate, and when should I repeat it?',
    context: 'Value: 6.5 %, flagged as H',
    related_analytes: ['hemoglobin_a1c'],
  },
];

/**
 * The documents list and the export calls. `summaryDelayMs` holds the summary response back so a spinner is on
 * screen when G5 samples it. Anything else falls through to installMockApi's shell fixtures.
 */
async function mockExportApi(page: Page, options: { summaryDelayMs?: number } = {}): Promise<void> {
  await page.route(/\/api\/v1\/(documents|export)(\/|\?|$)/, async (route: Route, request) => {
    const path = new URL(request.url()).pathname.replace(/^.*\/api\/v1/, '').replace(/\/+$/, '') || '/';
    const json = (body: unknown) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    const method = request.method();
    if (method === 'GET' && path === '/documents') return json(documents);
    if (method === 'GET' && path === '/export/csv') {
      return route.fulfill({ status: 200, contentType: 'text/csv', body: 'Date,Analyte,Value\n2026-03-14,glucose,95\n' });
    }
    if (method === 'GET' && path === '/export/json') return json([{ analyte_canonical: 'glucose', value: 95 }]);
    if (method === 'GET' && path.startsWith('/export/doctor-summary/')) {
      return route.fulfill({ status: 200, contentType: 'text/plain', body: 'HEALTH SUMMARY REPORT\n' });
    }
    if (method === 'GET' && path.startsWith('/export/visit-prep/')) {
      return route.fulfill({ status: 200, contentType: 'text/markdown', body: '# Visit prep\n' });
    }
    if (method === 'GET' && path.startsWith('/export/fhir/')) {
      return route.fulfill({ status: 200, contentType: 'application/fhir+json', body: '{"resourceType":"Bundle"}' });
    }
    if (method === 'POST' && path === '/export/doctor-summary') {
      if (options.summaryDelayMs) await new Promise((resolve) => setTimeout(resolve, options.summaryDelayMs));
      return json(summary);
    }
    if (method === 'POST' && path === '/export/questions') return json(questions);
    if (method === 'POST' && path === '/export/visit-prep') {
      return json({
        packet_id: 'packet-export-1',
        profile_id: FIXTURE_PROFILE_ID,
        generated_at: '2026-04-10T12:00:00Z',
        section_titles: ['Current medications', 'Questions for your provider'],
        markdown: '# Visit prep',
        redaction_count: 2,
      });
    }
    if (method === 'POST' && path === '/export/fhir') {
      return json({
        export_id: 'fhir-export-1',
        profile_id: FIXTURE_PROFILE_ID,
        generated_at: '2026-04-10T12:00:00Z',
        resource_counts: { Observation: 3 },
        redaction_count: 1,
      });
    }
    return route.fallback();
  });
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

async function openExport(page: Page, options: { summaryDelayMs?: number; viewport?: { width: number; height: number } } = {}) {
  await page.setViewportSize(options.viewport ?? DESKTOP);
  const mock = await installMockApi(page);
  await mockExportApi(page, options);
  await seedMockSession(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  await page.goto('/export');
  await expect(page.getByRole('heading', { name: 'Export Summary', level: 1 })).toBeVisible();
  await settle(page);
  return { mock, guard };
}

async function generate(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Generate Summary' }).click();
  await expect(page.getByRole('button', { name: 'Download Summary' })).toBeVisible();
}

const previewDialog = (page: Page) => page.getByRole('dialog', { name: 'Full summary preview' });

async function openPreview(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Full Preview' }).click();
  await expect(previewDialog(page)).toBeVisible();
}

async function expectRail(page: Page, when: string): Promise<void> {
  const rail = await safetyVisible(page);
  expect(rail.found && rail.inViewport && rail.effectiveOpacity >= 0.99, `G9 ${when} ${JSON.stringify(rail)}`).toBe(true);
}

/**
 * Applies a theme, then waits for the colour transitions it starts (transition-colors, 200 ms) to end, so axe and the
 * screenshots do not sample a half-faded page.
 */
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

// ---------------------------------------------------------------------------------------------------------------
// Functional: no timing.
// ---------------------------------------------------------------------------------------------------------------
test.describe('HC-UIEXP e2e', () => {
  test('HC-UIEXP-001: Full Preview opens a sheet with the summary, Escape closes it, focus returns', async ({ page }) => {
    const { guard } = await openExport(page);
    const full = page.getByRole('button', { name: 'Full Preview' });
    await expect(full).toBeDisabled();

    await generate(page);
    await expect(full).toBeEnabled();
    await full.click();

    const dialog = previewDialog(page);
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('Health Summary Report')).toBeVisible();
    await expect(dialog.getByText(summary.date_range)).toBeVisible();
    await expect(dialog.getByText('2 abnormal')).toBeVisible();
    await expect(dialog.getByText('Glucose: 95.0 mg/dL (normal)')).toBeVisible();
    await expect(dialog.getByText(/Redaction level: strict\./)).toBeVisible();
    // Still (M0): no opacity or transform on the sheet once it is open.
    const style = await dialog.evaluate((el) => ({ opacity: getComputedStyle(el).opacity, transform: getComputedStyle(el).transform }));
    expect(style).toEqual({ opacity: '1', transform: 'none' });

    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(full).toBeFocused();
    guard.assertClean();
  });

  test('HC-UIEXP-002 and 004 in a real browser: Checkbox rows, no native input, redaction text before a summary', async ({ page }) => {
    await openExport(page);
    await expect(page.locator('input[type="checkbox"]:not([aria-hidden="true"])')).toHaveCount(0);
    await expect(page.getByRole('checkbox')).toHaveCount(13);

    const questionsRow = page.getByRole('checkbox', { name: 'Questions for Clinician' });
    await expect(questionsRow).not.toBeChecked();
    await page.getByText('Questions for Clinician').click();
    await expect(questionsRow).toBeChecked();
    await expect(page.getByRole('checkbox', { name: 'Questions for your provider' })).toBeChecked();

    const note = page.getByText(/^Redaction level: strict\./);
    await expect(note).toBeVisible();
    await expect(note).toHaveAttribute('data-t0');
    await expect(page.getByText(/CSV and JSON downloads are your own full copy and are not redacted\./)).toBeVisible();
  });

  test('the export flows still reach the API: summary, packet and bundle, with consent first', async ({ page }) => {
    const { guard, mock } = await openExport(page);
    const bodies: string[] = [];
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/export/')) {
        bodies.push(`${new URL(request.url()).pathname.replace(/^.*\/api\/v1/, '')} ${request.postData() ?? ''}`);
      }
    });

    await page.getByRole('checkbox', { name: 'Trend Analysis' }).click();
    await page.getByRole('checkbox', { name: 'Questions for Clinician' }).click();
    await generate(page);
    await expect(page.getByText(questions[0].question)).toBeVisible();

    await expect(page.getByRole('button', { name: 'Generate Packet' })).toBeDisabled();
    await page.getByRole('checkbox', { name: /I understand/ }).first().click();
    await page.getByRole('button', { name: 'Generate Packet' }).click();
    await expect(page.getByText('Packet ready')).toBeVisible();

    await expect(page.getByRole('button', { name: 'Generate Bundle' })).toBeDisabled();
    await page.getByRole('checkbox', { name: /I understand/ }).nth(1).click();
    await page.getByRole('button', { name: 'Generate Bundle' }).click();
    await expect(page.getByText('Bundle ready')).toBeVisible();

    expect(bodies).toEqual([
      '/export/doctor-summary {"include_trends":false,"include_questions":true,"format":"text"}',
      '/export/questions ',
      '/export/visit-prep {"include_medications":true,"include_labs":true,"include_visits":true,"include_tasks":true,"include_questions":true,"confirm":true}',
      '/export/fhir {"confirm":true}',
    ]);
    guard.assertClean();
    expect(mock.unmocked).toEqual([]);
  });

  for (const theme of THEMES) {
    test(`G1 axe on /export: empty, text typed in the reason box, generated, sheet open (${theme})`, async ({ page }) => {
      await openExport(page);
      await applyTheme(page, theme);

      expect(await axeBlocking(page), `G1 empty ${theme}`).toEqual([]);

      // Typed text takes the textarea's text colour; an empty box only shows the placeholder.
      await page.getByLabel('Reason for visit (optional)').fill('Persistent headaches for two weeks');
      expect(await axeBlocking(page), `G1 reason typed ${theme}`).toEqual([]);

      await generate(page);
      expect(await axeBlocking(page), `G1 generated ${theme}`).toEqual([]);

      await openPreview(page);
      expect(await axeBlocking(page), `G1 sheet open ${theme}`).toEqual([]);
    });
  }

  test('G7 and G9: no console error, no outside request, no unmocked call, Safety Rail visible after each interaction', async ({ page }) => {
    const { guard, mock } = await openExport(page);
    await expectRail(page, 'first paint');

    await page.getByRole('checkbox', { name: 'Flagged Values' }).click();
    await expectRail(page, 'after a section toggle');
    await generate(page);
    await expectRail(page, 'after Generate Summary');
    await openPreview(page);
    await expectRail(page, 'with the sheet open');
    await page.keyboard.press('Escape');
    await expect(previewDialog(page)).toHaveCount(0);
    await expectRail(page, 'after the sheet closed');
    await page.getByRole('button', { name: 'Download Summary' }).click();
    await page.getByRole('button', { name: 'Download CSV' }).click();
    await page.getByRole('button', { name: 'Download JSON' }).click();
    await expect(page.getByRole('button', { name: 'Download CSV' })).toBeEnabled();
    await expectRail(page, 'after the downloads');

    guard.assertClean();
    expect(mock.unmocked, 'G7 unmocked').toEqual([]);
  });

  for (const viewport of [PHONE, SMALL_PHONE]) {
    test(`G6 on /export at ${viewport.width}x${viewport.height}: no horizontal scroll, empty and generated`, async ({ page }) => {
      await openExport(page, { viewport });
      // Documents arrive after load; wait for the long name to be in the DOM before measuring.
      await expect(page.getByRole('checkbox', { name: /Quest Diagnostics Reference Laboratory/ })).toBeVisible();
      expect((await noHorizontalScroll(page)).ok, `G6 empty ${viewport.width}`).toBe(true);

      await page.getByRole('checkbox', { name: 'Questions for Clinician' }).click();
      await generate(page);
      await expect(page.getByText('Glucose: 95.0 mg/dL (normal)')).toBeVisible();
      await expect(page.getByText(questions[0].question)).toBeVisible();
      expect((await noHorizontalScroll(page)).ok, `G6 generated ${viewport.width}`).toBe(true);

      await page.getByRole('checkbox', { name: /I understand/ }).first().click();
      await page.getByRole('button', { name: 'Generate Packet' }).click();
      await expect(page.getByText('Packet ready')).toBeVisible();
      expect((await noHorizontalScroll(page)).ok, `G6 packet ${viewport.width}`).toBe(true);

      await openPreview(page);
      const dialogFits = await previewDialog(page).evaluate((el) => el.scrollWidth <= el.clientWidth);
      expect(dialogFits, `G6 sheet ${viewport.width}`).toBe(true);
      expect((await noHorizontalScroll(page)).ok, `G6 sheet open ${viewport.width}`).toBe(true);
    });
  }
});

// ---------------------------------------------------------------------------------------------------------------
// Timing: G2, G3, G5, G10. Quiet box only.
// ---------------------------------------------------------------------------------------------------------------
test.describe('QUIET-BOX UI-PG-EXPORT timing gates', () => {
  for (const theme of THEMES) {
    test(`QUIET-BOX G2 on /export (${theme})`, async ({ page }) => {
      // The summary response is held back 700 ms so its shift lands outside the 500 ms hadRecentInput window after
      // the click; with an instant mock the browser would discount it and G2 could not see it.
      await page.setViewportSize(DESKTOP);
      await installMockApi(page);
      await mockExportApi(page, { summaryDelayMs: 700 });
      await seedMockSession(page);
      await page.goto('/export');
      await expect(page.getByRole('heading', { name: 'Export Summary', level: 1 })).toBeVisible();
      await settle(page);

      // G2: layout shift over the load and the page's interactions, in the theme under test.
      const cls = await measureCls(page, async () => {
        await page.goto('/export');
        await expect(page.getByRole('heading', { name: 'Export Summary', level: 1 })).toBeVisible();
        await settle(page);
        await applyTheme(page, theme);
        await page.getByRole('checkbox', { name: 'Questions for Clinician' }).click();
        await generate(page);
        await openPreview(page);
        await page.keyboard.press('Escape');
        await expect(previewDialog(page)).toHaveCount(0);
      });
      expect(cls, `G2 ${theme}`).toBeLessThan(0.1);
    });

    test(`QUIET-BOX G3 on /export (${theme})`, async ({ page }) => {
      await openExport(page);
      await applyTheme(page, theme);

      // G3: the worst Event Timing duration over the page's interactions, CPU x4.
      const inp = await maxEventDuration(
        page,
        async () => {
          await page.getByRole('checkbox', { name: 'Questions for Clinician' }).click();
          await generate(page);
          await openPreview(page);
          await page.keyboard.press('Escape');
          await expect(previewDialog(page)).toHaveCount(0);
        },
        { cpuRate: 4 }
      );
      expect(inp, `G3 ${theme}`).toBeLessThan(200);
    });

    test(`QUIET-BOX G5 on /export (${theme})`, async ({ page }, testInfo) => {
      // The response is held back so the spinners are on screen when the snapshot samples, 50 ms after the click.
      await openExport(page, { summaryDelayMs: 600 });
      await applyTheme(page, theme);

      const spinning = await reducedMotionSnapshot(page, () => page.getByRole('button', { name: 'Generate Summary' }).click());
      expect(spinning, `G5 while generating ${theme}`).toEqual([]);
      await expect(page.getByRole('button', { name: 'Download Summary' })).toBeVisible();

      const opening = await reducedMotionSnapshot(page, () => page.getByRole('button', { name: 'Full Preview' }).click());
      expect(opening, `G5 sheet open ${theme}`).toEqual([]);
      const shot = testInfo.outputPath(`export-${theme}-reduced.png`);
      await page.screenshot({ path: shot, fullPage: false });
      testInfo.annotations.push({ type: 'gate-g5-screenshot', description: shot });
    });

    test(`QUIET-BOX G10 stillness on /export (${theme})`, async ({ page }, testInfo) => {
      await page.setViewportSize(DESKTOP);
      await installMockApi(page);
      await mockExportApi(page);
      await seedMockSession(page);
      const guard = consoleAndNetworkGuard(page);
      await page.goto('/settings');
      await settle(page);
      await applyTheme(page, theme);

      // Navigation to /export: the redaction note is T0 and must stay still through the route fade.
      const navReport = await stillnessProbe(page, {
        trigger: () => nav(page, 'Doctor summary').click(),
        expected: [`${ROUTE_CONTAINER_SELECTOR} p[data-t0]`],
        kind: 'navigation',
        lazyRoute: true,
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `navigation ${theme}: ${JSON.stringify(navReport)}` });
      await expect(page.getByRole('heading', { name: 'Export Summary', level: 1 })).toBeVisible();
      await settle(page);

      // Generate Summary: the preview values appear and must not animate.
      const generateReport = await stillnessProbe(page, {
        trigger: () => page.getByRole('button', { name: 'Generate Summary' }).click(),
        expected: ['strong[data-t0]', 'ul[data-t0]', 'footer[data-t0]'],
        kind: 'interaction',
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `generate ${theme}: ${JSON.stringify(generateReport)}` });
      await expect(page.getByRole('button', { name: 'Download Summary' })).toBeVisible();

      // Full Preview open: the sheet's values are T0 (M0).
      const sheetReport = await stillnessProbe(page, {
        trigger: () => page.getByRole('button', { name: 'Full Preview' }).click(),
        expected: ['[role="dialog"] strong[data-t0]', '[role="dialog"] ul[data-t0]', '[role="dialog"] footer[data-t0]'],
        kind: 'overlay',
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `sheet ${theme}: ${JSON.stringify(sheetReport)}` });
      expect(sheetReport.nodes).toBeGreaterThan(0);
      await page.keyboard.press('Escape');
      guard.assertClean();
    });
  }
});
