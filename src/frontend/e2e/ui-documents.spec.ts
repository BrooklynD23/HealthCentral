/**
 * UI-PG-DOCUMENTS e2e (plan section 7.7, "UI-PG-DOCUMENTS"): HC-UIDOC-001 (row actions are visible with the mouse
 * away and reachable by Tab), HC-UIDOC-002 (at most two tag chips, no raw identifier), HC-UIDOC-003 (the beam card
 * and the orb while an import is in flight, static under reduced motion), HC-UIDOC-004 (an alert stays outside the
 * beam), HC-UIDOC-005 (delete through the AlertDialog, with the real Radix focus and pointer-events checks),
 * HC-UIDOC-006 (stillnessProbe across an import into an empty list with a scanned-page warning, across a failed
 * import, and across the preview Sheet; an import into a non-empty list is an expected failure, see the test), and
 * Gate G on
 * /inbox: G1 axe in light and dark, G2 CLS, G3 INP with CPU x4, G5 reduced motion, G6 phone and small phone widths,
 * G7 console and network, G9 the Safety Rail, G10 stillness.
 *
 * Every /api/v1 request goes to the shared fixtures in support/mockApi.ts. This spec adds later routes for the
 * documents API: a later route wins, so these answer GET /documents, GET /documents/highlights/summary, the page
 * image, POST /documents/import (which a test can hold open) and DELETE /documents/:id. Nothing reaches the backend,
 * and the unmocked list stays empty (checked by the guard).
 *
 * Timing gates (G2, G3, G5, G10, HC-UIDOC-006, INBOX-DATA-RENDER) need a quiet box (load < 1.5, no foreign test
 * process). The build lane runs everything else:
 *   npx playwright test e2e/ui-documents.spec.ts --project=chromium --grep-invert 'GATE G(2|3|5|10)|HC-UIDOC-006'
 * The quiet box runs the timing set on the dev server, then on a `vite preview` build (HC_E2E_BASE_URL):
 *   npx playwright test e2e/ui-documents.spec.ts --project=chromium --grep 'GATE G(2|3|5|10)|HC-UIDOC-006|INBOX-DATA-RENDER'
 */

import { expect, test, type Locator, type Page } from '@playwright/test';
import type { Document, DocumentImportResponse } from '../src/services/types';
import type { DocumentHighlightSummary } from '../src/services/highlights';
import { FIXTURE_PROFILE_ID, installMockApi, seedMockSession } from './support/mockApi';
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
  StillnessError,
} from './support/gates';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/** A long name with no space: the worst case for a row that does not shrink. */
const LONG_NAME =
  'Alex_Rivera_comprehensive_metabolic_panel_with_lipid_profile_and_thyroid_screen_regional_laboratory_final_report_2026-10-30.pdf';
const SECOND_NAME = 'Alex Rivera lipid panel, August';
const THIRD_NAME = 'Alex Rivera lab report, March';
const NEW_NAME = 'new-cbc-report.pdf';

function makeDoc(over: Partial<Document>): Document {
  return {
    id: 'doc-x',
    profile_id: FIXTURE_PROFILE_ID,
    doc_type: 'lab_pdf',
    source: 'x.pdf',
    status: 'parsed',
    page_count: 2,
    collection_date: '2026-08-02',
    imported_at: '2026-08-03T07:41:00Z',
    parsed_at: '2026-08-03T07:41:03Z',
    verified_at: null,
    extraction_confidence: 0.9,
    ...over,
  };
}

/** Three rows: long name + 5 tag types + low confidence + raw type; unknown confidence; verified and high. */
function stressRows(): Document[] {
  return [
    makeDoc({
      id: 'doc-long-0001',
      source: LONG_NAME,
      doc_type: 'lab_csv',
      status: 'parsed',
      extraction_confidence: 0.31,
      imported_at: '2026-10-30T09:00:00Z',
    }),
    makeDoc({
      id: 'doc-second-0002',
      source: SECOND_NAME,
      doc_type: 'lab_pdf',
      status: 'pending',
      extraction_confidence: null,
      imported_at: '2026-08-03T07:41:00Z',
    }),
    makeDoc({
      id: 'doc-third-0003',
      source: THIRD_NAME,
      doc_type: 'lab_report',
      status: 'verified',
      extraction_confidence: 0.94,
      imported_at: '2026-03-15T10:12:00Z',
    }),
  ];
}

const HIGHLIGHTS: DocumentHighlightSummary[] = [
  {
    doc_id: 'doc-long-0001',
    counts: {
      abnormal_value: 2,
      medication_started: 1,
      follow_up_needed: 1,
      low_confidence_extraction: 1,
      needs_verification: 3,
    },
  },
];

/** A 400x100 PNG, the same one the provenance spec serves for every page. */
const PAGE_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAZAAAABkCAIAAAAnqfEgAAABDUlEQVR42u3UQREAAAzCMPyrRQI6tksk9NEU4IhIABgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYgGEBGBaAYQGGBWBYgGEBGBaAYQGGBWBYAIYFGBaAYQEYFmBYAIYFYFiAYQEYFoBhAYYFYFgAhgUYFoBhARgWYFgAhgVgWIBhARgWgGEBhgVgWIBhARgWgGEBhgVgWACGBRgWgGEBGBZgWACGBWBYwF8DXxGNujLHPvkAAAAASUVORK5CYII=',
  'base64'
);

const NEW_FILE = { name: NEW_NAME, mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 fixture') };

/** What the import answers with. Defaults to a clean import of 4 values at 0.62 confidence. */
interface ImportAnswer {
  observations_extracted?: number;
  pages_without_text?: number[];
  duplicate_warning?: DocumentImportResponse['duplicate_warning'];
  /** A non-2xx answer: the page must show the alert. */
  fail?: { status: number; detail: string };
}

interface DocsControl {
  rows: Document[];
  /** Every DELETE the page sent, as the document id. */
  readonly deletes: string[];
  /** Every POST /documents/import the page sent. */
  imports: number;
  /** The next import waits until the returned function is called. */
  hold(): () => void;
  answer: ImportAnswer;
  /** Wall-clock ms when the last GET /documents was fulfilled. */
  lastListFulfilledAt: number;
}

/**
 * The documents API for this spec. GET /documents answers the rows as they are now, newest first (the backend
 * orders by imported_at descending, api/documents.py:1093), so an import puts its row at the top.
 */
async function mockDocuments(page: Page, rows: Document[]): Promise<DocsControl> {
  let gate: Promise<void> | null = null;
  const control: DocsControl = {
    rows: [...rows],
    deletes: [],
    imports: 0,
    answer: {},
    lastListFulfilledAt: 0,
    hold() {
      let release!: () => void;
      gate = new Promise<void>((resolve) => {
        release = () => {
          resolve();
        };
      });
      return release;
    },
  };

  await page.route(/\/api\/v1\/documents\/?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(control.rows) });
    control.lastListFulfilledAt = Date.now();
  });

  await page.route(/\/api\/v1\/documents\/highlights\/summary\/?(\?.*)?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(HIGHLIGHTS) });
  });

  await page.route(/\/api\/v1\/documents\/[^/]+\/pages\/\d+\/image$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'image/png', body: PAGE_PNG });
  });

  await page.route(/\/api\/v1\/documents\/import\/?$/, async (route, request) => {
    if (request.method() !== 'POST') return route.fallback();
    control.imports += 1;
    if (gate) await gate;
    gate = null;
    if (control.answer.fail) {
      await route.fulfill({
        status: control.answer.fail.status,
        contentType: 'application/json',
        body: JSON.stringify({ detail: control.answer.fail.detail }),
      });
      return;
    }
    const document = makeDoc({
      id: 'doc-new-0004',
      source: NEW_NAME,
      doc_type: 'lab_pdf',
      status: 'parsed',
      extraction_confidence: 0.62,
      imported_at: '2026-11-02T08:00:00Z',
    });
    control.rows.unshift(document);
    const body: DocumentImportResponse = {
      document,
      observations_extracted: control.answer.observations_extracted ?? 4,
      needs_verification: true,
      duplicate_warning: control.answer.duplicate_warning ?? null,
      import_summary: null,
      pages_without_text: control.answer.pages_without_text ?? [],
    };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });

  await page.route(/\/api\/v1\/documents\/([^/?]+)$/, async (route, request) => {
    if (request.method() !== 'DELETE') return route.fallback();
    const id = /\/documents\/([^/?]+)$/.exec(new URL(request.url()).pathname)![1];
    control.deletes.push(id);
    control.rows = control.rows.filter((row) => row.id !== id);
    await route.fulfill({ status: 204, body: '' });
  });

  return control;
}

async function setup(page: Page, rows: Document[] = stressRows()) {
  const mock = await installMockApi(page);
  await seedMockSession(page);
  const docs = await mockDocuments(page, rows);
  return { mock, docs };
}

// ---------------------------------------------------------------------------
// Selectors and helpers
// ---------------------------------------------------------------------------

const ROW = '[data-inbox-row]';
const DATE = '[data-inbox-date]';
const STATUS = '[data-inbox-status]';
const CONFIDENCE = '[data-confidence-words]';
const HANDOFF = '[data-inbox-handoff]';
const ERROR_ALERT = '[data-inbox-error]';
const SCANNED_WARNING = '[data-inbox-scanned]';
const BEAM = '.beam-border[data-active="true"]';
const SAFETY_RAIL = '[data-safety-rail]';
/** The T0 marks the §2.7 table lists for /inbox. */
const EXPECTED = [DATE, STATUS, CONFIDENCE];

function rowByName(page: Page, name: string): Locator {
  return page.locator(ROW).filter({ has: page.getByRole('heading', { name, exact: true }) });
}

function fileInput(page: Page): Locator {
  return page.locator('input[type="file"]');
}

/** Waits until the element's effective opacity is 1 and its box has not moved for six frames. */
async function waitForEffectiveOpacity(page: Page, selector: string): Promise<void> {
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

/** Opens /inbox and waits until the list (or the empty state) is ready to interact with. */
async function openInbox(page: Page, options: { empty?: boolean } = {}): Promise<void> {
  await page.goto('/inbox');
  if (options.empty) {
    await expect(page.getByText(/no documents yet/i)).toBeVisible();
  } else {
    await expect(page.locator(ROW).first()).toBeVisible();
  }
  await page.evaluate(() => document.fonts.ready);
  await waitForEffectiveOpacity(page, 'h1');
}

/** Starts an import with the request held, and waits until the beam card is on screen. Returns the release. */
async function startHeldImport(page: Page, docs: DocsControl, file: typeof NEW_FILE = NEW_FILE): Promise<() => void> {
  const release = docs.hold();
  await fileInput(page).setInputFiles(file);
  await expect(page.locator(BEAM)).toBeVisible();
  await expect(page.getByText(`Reading ${file.name}`)).toBeVisible();
  return release;
}

/** The effective opacity of an element: its own times every ancestor's. */
async function effectiveOpacity(locator: Locator): Promise<number> {
  return locator.evaluate((el) => {
    let value = 1;
    for (let node: Element | null = el; node; node = node.parentElement) {
      value *= parseFloat(getComputedStyle(node).opacity);
    }
    return value;
  });
}

/**
 * Applies the theme, waits for the 200 ms colour transitions the flip starts (Badge and Card have
 * transition-colors), then runs axe. Without the wait axe reads colours halfway between light and dark, and
 * reports a contrast failure that no user can see.
 */
async function axeSettled(page: Page, theme: 'light' | 'dark') {
  await setTheme(page, theme);
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== 'running' || a.effect?.getTiming().iterations === Infinity));
  return axeGate(page);
}

function blockingIds(result: Awaited<ReturnType<typeof axeGate>>): string[] {
  return result.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);
}

// ---------------------------------------------------------------------------
// HC-UIDOC-001 .. 005 end to end
// ---------------------------------------------------------------------------
test.describe('HC-UIDOC end to end', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('HC-UIDOC-001: with the mouse away the row actions have opacity 1, and Tab reaches them', async ({ page }) => {
    // Would not notice: an opacity applied by a stylesheet rule on an ancestor (the effective opacity covers every
    // ancestor), or a button that is visible but skipped by Tab (the loop checks the focused element's label).
    // RED today: on a fine pointer the actions container is opacity 0 until the row is hovered.
    await setup(page);
    await openInbox(page);
    await page.mouse.move(2, 2);
    const view = rowByName(page, THIRD_NAME).getByRole('button', { name: 'View document' });
    expect(await effectiveOpacity(view)).toBeGreaterThanOrEqual(0.99);
    const more = rowByName(page, THIRD_NAME).getByRole('button', { name: 'More options' });
    expect(await effectiveOpacity(more)).toBeGreaterThanOrEqual(0.99);

    await page.locator('h1').click();
    let reached = '';
    for (let i = 0; i < 60 && reached !== 'View document'; i++) {
      await page.keyboard.press('Tab');
      reached = await page.evaluate(() => {
        const el = document.activeElement;
        const row = el?.closest('[data-inbox-row]');
        return row && row.textContent?.includes('lab report, March') ? (el?.getAttribute('aria-label') ?? '') : '';
      });
    }
    expect(reached).toBe('View document');
  });

  test('HC-UIDOC-002: a row with five tag types shows at most 2 chips and "+3", and no raw identifier anywhere', async ({
    page,
  }) => {
    // Would not notice: a chip hidden by CSS (they are counted in the DOM), or an identifier in a tooltip. The
    // brief's reading: the status word and the confidence words are not tag chips.
    // RED today: four tag chips and "+1", and `lab_csv` printed twice.
    await setup(page);
    await openInbox(page);
    const row = rowByName(page, LONG_NAME);
    const labels = ['Abnormal lab', 'Medication started', 'Follow-up needed', 'Low confidence', 'Needs verification'];
    const shown = await row.locator('span').evaluateAll(
      (nodes, names) =>
        nodes.filter((n) => n.children.length === 0 && names.includes((n.textContent ?? '').replace(/ ×\d+$/, '').trim()))
          .length,
      labels
    );
    expect(shown).toBe(2);
    await expect(row.getByText('+3', { exact: true })).toHaveCount(1);

    const text = await page.locator('main').innerText();
    for (const raw of ['lab_csv', 'lab_pdf', 'lab_report', 'lab_image', 'fhir_bundle']) {
      expect(text, `raw identifier ${raw} in the page text`).not.toContain(raw);
    }
    await expect(row.getByText('Lab Spreadsheet', { exact: true })).toHaveCount(1);
  });

  test('HC-UIDOC-003: while an import is in flight the beam card shows "Reading <name>" and an orb; it ends with the request', async ({
    page,
  }) => {
    // Would not notice: a beam that stays after the request ends (the last assertion). The request is really held.
    // RED today: no beam card, no status text.
    const { docs } = await setup(page);
    await openInbox(page);
    const release = await startHeldImport(page, docs);
    await expect(page.locator(BEAM).getByRole('status')).toHaveText(`Reading ${NEW_NAME}`);
    await expect(page.locator(`${BEAM} canvas`)).toBeAttached();
    release();
    await expect(page.locator(BEAM)).toHaveCount(0);
  });

  test('HC-UIDOC-003: under reduced motion the border is a static frame and the text stays', async ({ page }) => {
    // Would not notice: a frame whose colour is wrong (HC-UISK-001 reads the stylesheet). The computed animation of
    // the frame and of every descendant of the card must be none.
    // RED today: no beam card.
    const { docs } = await setup(page);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openInbox(page);
    const release = await startHeldImport(page, docs);
    const card = page.locator(BEAM);
    await expect(card).toHaveAttribute('data-motion', 'reduced');
    await expect(card.locator('.beam-border__beam')).toHaveCount(0);
    await expect(card.locator('.beam-border__frame')).toHaveCount(1);
    const animated = await card.evaluate((el) =>
      [el, ...Array.from(el.querySelectorAll('*'))]
        .filter((n) => {
          const cs = getComputedStyle(n);
          return cs.animationName !== 'none' && cs.animationPlayState === 'running';
        })
        .map((n) => n.tagName.toLowerCase())
    );
    expect(animated).toEqual([]);
    await expect(page.getByText(`Reading ${NEW_NAME}`)).toBeVisible();
    release();
  });

  test('HC-UIDOC-004: the import-failed alert stays outside the beam card and does not animate while another import runs', async ({
    page,
  }) => {
    // Would not notice: a stylesheet rule that animates [role=alert]; the computed animation name is read.
    const { docs } = await setup(page);
    await openInbox(page);
    docs.answer = { fail: { status: 400, detail: 'Unsupported file type' } };
    await fileInput(page).setInputFiles({ ...NEW_FILE, name: 'bad.pdf' });
    const alert = page.getByRole('alert');
    await expect(alert).toContainText('Unsupported file type');
    docs.answer = {};
    const release = await startHeldImport(page, docs);
    await expect(alert).toBeVisible();
    expect(await alert.evaluate((el) => el.closest('.beam-border') === null)).toBe(true);
    expect(await alert.evaluate((el) => getComputedStyle(el).animationName)).toBe('none');
    release();
  });

  test('HC-UIDOC-005: Delete asks through an AlertDialog; Cancel sends nothing, a click still works, focus returns; Remove sends one DELETE', async ({
    page,
  }) => {
    // Would not notice: a body left with pointer-events none (checked as a style AND by a real click on another row),
    // or focus lost to <body> (the focused element is read). Radix can leave pointer-events: none on body when a
    // dialog opens from a DropdownMenu; this is the first consumer of that pairing.
    const { docs } = await setup(page);
    await openInbox(page);
    const row = rowByName(page, THIRD_NAME);
    const more = row.getByRole('button', { name: 'More options' });

    await more.click();
    await page.getByRole('menuitem', { name: /delete/i }).click();
    const dialog = page.getByRole('alertdialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(`Remove "${THIRD_NAME}" from your library? This cannot be undone.`);
    await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused();
    expect(docs.deletes).toEqual([]);

    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await expect(dialog).toBeHidden();
    expect(docs.deletes).toEqual([]);
    expect(await page.evaluate(() => document.body.style.pointerEvents)).not.toBe('none');
    await expect(more).toBeFocused();

    // A real click on another row still lands.
    await rowByName(page, SECOND_NAME).getByRole('button', { name: 'View document' }).click();
    const sheet = page.getByRole('dialog', { name: 'Document preview' });
    await expect(sheet).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(sheet).toBeHidden();

    await more.click();
    await page.getByRole('menuitem', { name: /delete/i }).click();
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect(page.getByRole('alertdialog')).toBeHidden();
    await expect.poll(() => docs.deletes).toEqual(['doc-third-0003']);
    await expect(rowByName(page, THIRD_NAME)).toHaveCount(0);
    expect(await page.evaluate(() => document.body.style.pointerEvents)).not.toBe('none');
    // Asserted straight after Remove, before any other menu opens: the removed row was the last one, so focus is
    // on the previous row's More options button.
    await expect(rowByName(page, SECOND_NAME).getByRole('button', { name: 'More options' })).toBeFocused();
    // The page is still live: the menu of a remaining row opens.
    await rowByName(page, SECOND_NAME).getByRole('button', { name: 'More options' }).click();
    await expect(page.getByRole('menuitem', { name: /review extracted values/i })).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('thinking-orbs is requested when an orb mounts on /inbox, and not on /inbox idle or on another route', async ({
    page,
  }) => {
    // Would not notice: a static import of the library from a shared file (it would load on every route; the
    // /results visit catches that). Dev server module name is thinking-orbs; a production chunk is named index.es-*
    // (ui-budget.test.ts), so both are matched.
    const asked: string[] = [];
    page.on('request', (request) => {
      if (/thinking-orbs|\/index\.es-/.test(request.url())) asked.push(request.url());
    });
    const { docs } = await setup(page);
    await openInbox(page);
    await page.waitForTimeout(500);
    expect(asked, 'requested on an idle /inbox').toEqual([]);

    await page.goto('/results');
    await expect(page.locator('main')).toBeVisible();
    await page.waitForTimeout(500);
    expect(asked, 'requested on /results').toEqual([]);

    await openInbox(page);
    const release = await startHeldImport(page, docs);
    await expect.poll(() => asked.length).toBeGreaterThan(0);
    release();
  });
});

// ---------------------------------------------------------------------------
// Gate G on /inbox (plan section 6)
// ---------------------------------------------------------------------------
test.describe('Gate G on /inbox', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('GATE G1 /inbox has no serious or critical axe violation in light or dark: the list, an import in flight, the delete dialog, the empty library', async ({
    page,
  }) => {
    // Would not notice: a violation that only the delete dialog, the processing state or the empty library has, so
    // four states are scanned. The theme is applied after load by the harness.
    // RED today: not known; the old page passes axe (HC-UIG-002). The new states are the new surface.
    const { docs } = await setup(page);
    await openInbox(page);
    for (const theme of ['light', 'dark'] as const) {
      expect(blockingIds(await axeSettled(page, theme)), `list, ${theme}`).toEqual([]);
    }
    await setTheme(page, 'light');
    const release = await startHeldImport(page, docs);
    for (const theme of ['light', 'dark'] as const) {
      expect(blockingIds(await axeSettled(page, theme)), `import in flight, ${theme}`).toEqual([]);
    }
    release();
    await expect(page.locator(BEAM)).toHaveCount(0);
    await setTheme(page, 'light');
    await rowByName(page, THIRD_NAME).getByRole('button', { name: 'More options' }).click();
    await page.getByRole('menuitem', { name: /delete/i }).click();
    await expect(page.getByRole('alertdialog')).toBeVisible();
    for (const theme of ['light', 'dark'] as const) {
      expect(blockingIds(await axeSettled(page, theme)), `delete dialog, ${theme}`).toEqual([]);
    }

    // The empty library (EmptyState with its action) is a fourth surface.
    docs.rows = [];
    await openInbox(page, { empty: true });
    await expect(page.getByRole('button', { name: 'Choose a file' })).toBeVisible();
    for (const theme of ['light', 'dark'] as const) {
      expect(blockingIds(await axeSettled(page, theme)), `empty library, ${theme}`).toEqual([]);
    }
  });

  test('GATE G2 /inbox: CLS stays under 0.1 over the load, an import, the preview Sheet and a delete', async ({ page }) => {
    // Would not notice: a layout shift in a state the sequence skips. The sequence covers the card, the handoff,
    // the new row, the Sheet and the row removal.
    const { docs } = await setup(page);
    const cls = await measureCls(page, async () => {
      await page.goto('/inbox');
      await expect(page.locator(ROW).first()).toBeVisible();
      const release = await startHeldImport(page, docs);
      release();
      await expect(page.locator(HANDOFF)).toBeVisible();
      await expect(rowByName(page, NEW_NAME)).toBeVisible();
      await rowByName(page, NEW_NAME).getByRole('button', { name: 'View document' }).click();
      await expect(page.getByRole('dialog', { name: 'Document preview' })).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).toBeHidden();
      await rowByName(page, THIRD_NAME).getByRole('button', { name: 'More options' }).click();
      await page.getByRole('menuitem', { name: /delete/i }).click();
      await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
      await expect(rowByName(page, THIRD_NAME)).toHaveCount(0);
    });
    expect(cls).toBeLessThan(0.1);
  });

  test('GATE G3 /inbox: View document, More options and Delete each stay under 200 ms with CPU throttled x4', async ({
    page,
  }) => {
    // Would not notice: an interaction the list does not have (the import is a file chooser event, not a click).
    // Returns 0 when no event reaches 16 ms, so a dead observer also passes; the bound is the gate's, unchanged.
    // Count only on a production build (vite preview); the dev server carries React's dev cost.
    await setup(page);
    await openInbox(page);
    const row = rowByName(page, THIRD_NAME);
    const view = await maxEventDuration(page, () => row.getByRole('button', { name: 'View document' }).click());
    expect(view, 'View document click').toBeLessThan(200);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();

    const menu = await maxEventDuration(page, () => row.getByRole('button', { name: 'More options' }).click());
    expect(menu, 'More options click').toBeLessThan(200);
    const del = await maxEventDuration(page, () => page.getByRole('menuitem', { name: /delete/i }).click());
    expect(del, 'Delete click').toBeLessThan(200);
  });

  test('GATE G5 /inbox: no element has a transform 50 ms after View document, Delete or an import starts, under reduced motion', async ({
    page,
  }) => {
    // Would not notice: a transform on the Sheet or the dialog on a path the sequence skips. The check is page-wide.
    // It covers View document, Delete, an import starting, and the empty library.
    const { docs } = await setup(page);
    await openInbox(page);
    const row = rowByName(page, THIRD_NAME);
    const afterView = await reducedMotionSnapshot(page, () => row.getByRole('button', { name: 'View document' }).click());
    expect(afterView, 'after View document').toEqual([]);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();

    await row.getByRole('button', { name: 'More options' }).click();
    const afterDelete = await reducedMotionSnapshot(page, () => page.getByRole('menuitem', { name: /delete/i }).click());
    expect(afterDelete, 'after Delete').toEqual([]);
    await page.getByRole('alertdialog').getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByRole('alertdialog')).toBeHidden();

    let release: () => void = () => {};
    const afterImport = await reducedMotionSnapshot(page, async () => {
      release = await startHeldImport(page, docs);
    });
    expect(afterImport, 'after an import starts').toEqual([]);
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();

    // The empty library: the EmptyState mounts with the page, so the load is the action.
    docs.rows = [];
    const afterEmpty = await reducedMotionSnapshot(page, async () => {
      await page.goto('/inbox');
      await expect(page.getByRole('button', { name: 'Choose a file' })).toBeVisible();
    });
    expect(afterEmpty, 'the empty library').toEqual([]);
  });

  test('GATE G5 /inbox: per-recipe reduced-motion screenshots for S2, S3 and the empty state (attached)', async ({
    page,
  }, testInfo) => {
    // Would not notice: a recipe that looks wrong. The test cannot judge a picture; it makes sure each is taken from
    // the right state (the beam card is active, the orb canvas is attached, the empty state has its action) and
    // attaches it for the PR.
    const { docs } = await setup(page, []);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openInbox(page, { empty: true });
    await expect(page.getByRole('button', { name: 'Choose a file' })).toBeVisible();
    await testInfo.attach('empty-state-reduced-motion', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    });

    const release = await startHeldImport(page, docs);
    await expect(page.locator(`${BEAM} canvas`)).toBeAttached();
    await testInfo.attach('s2-s3-beam-and-orb-reduced-motion', {
      body: await page.locator(BEAM).screenshot(),
      contentType: 'image/png',
    });
    await testInfo.attach('inbox-importing-reduced-motion', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    });
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();
  });

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 320, height: 640 },
  ]) {
    test(`GATE G6 /inbox: no horizontal scroll at ${viewport.width}x${viewport.height}, with a long name, five tags and low confidence, before, during and after an import and after a failure`, async ({
      page,
    }) => {
      // Would not notice: an overflow that appears only in a state the sequence skips. The known offenders are the
      // actions div and, during an import, the status line of the orb (813 px wide with this name before it was
      // given [overflow-wrap:anywhere]); every row's actions are also checked against the viewport edge, because a
      // clipped overflow would not move scrollWidth.
      // RED today: the actions div pushes the page wider than 390 px.
      await page.setViewportSize(viewport);
      const { docs } = await setup(page);
      docs.answer = {
        pages_without_text: [2, 3],
        duplicate_warning: { match_type: 'content_hash', document_id: 'old', title: 'a-very-long-prior-document-name.pdf' },
      };
      // The empty library first: EmptyState and its action must fit the width too.
      const rowsBefore = docs.rows;
      docs.rows = [];
      await openInbox(page, { empty: true });
      expect((await noHorizontalScroll(page)).ok, 'empty library: scrollWidth').toBe(true);
      const choose = await page.getByRole('button', { name: 'Choose a file' }).boundingBox();
      expect(choose!.x + choose!.width, 'empty library: action inside the viewport').toBeLessThanOrEqual(viewport.width);
      docs.rows = rowsBefore;
      await openInbox(page);
      const checkRows = async (label: string) => {
        expect((await noHorizontalScroll(page)).ok, `${label}: scrollWidth`).toBe(true);
        const past = await page.locator(ROW).evaluateAll((rows) =>
          rows.flatMap((row) =>
            Array.from(row.querySelectorAll('button')).filter((b) => b.getBoundingClientRect().right > window.innerWidth + 0.5)
              .map((b) => b.getAttribute('aria-label') ?? b.textContent ?? 'button')
          )
        );
        expect(past, `${label}: buttons past the right edge`).toEqual([]);
      };
      await checkRows('before');
      // The 127-character name has no space: the status line "Reading <name>" has to wrap inside the card.
      const release = await startHeldImport(page, docs, { ...NEW_FILE, name: LONG_NAME });
      expect((await noHorizontalScroll(page)).ok, 'during the import with the long name').toBe(true);
      release();
      await expect(page.locator(HANDOFF)).toBeVisible();
      await expect(page.getByText(/possible duplicate upload/i)).toBeVisible();
      await expect(page.getByText(/have no readable text/)).toBeVisible();
      await checkRows('after the import');

      docs.answer = { fail: { status: 400, detail: 'Unsupported file type for this long file name.pdf' } };
      await fileInput(page).setInputFiles({ ...NEW_FILE, name: LONG_NAME });
      await expect(page.getByRole('alert')).toBeVisible();
      await checkRows('after a failure');
    });
  }

  test('GATE G7 /inbox: no console error, no non-localhost request and no unmocked API call, across import, preview, delete', async ({
    page,
  }) => {
    // Would not notice: an unmocked request the page made (answered 599 and logged), or a console error from the
    // Sheet, the dialog or the lazy orb chunk.
    const { mock, docs } = await setup(page);
    const guard = consoleAndNetworkGuard(page, { mock });
    await openInbox(page);
    const release = await startHeldImport(page, docs);
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();
    await rowByName(page, NEW_NAME).getByRole('button', { name: 'View document' }).click();
    await expect(page.getByRole('dialog', { name: 'Document preview' })).toBeVisible();
    await expect(page.locator('[data-page-image-overlay], img[alt="Page 1 of document"]').first()).toBeVisible();
    await page.keyboard.press('Escape');
    await rowByName(page, THIRD_NAME).getByRole('button', { name: 'More options' }).click();
    await page.getByRole('menuitem', { name: /delete/i }).click();
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect(rowByName(page, THIRD_NAME)).toHaveCount(0);
    guard.assertClean();
  });

  test('GATE G9 /inbox: the Safety Rail is in the viewport at full opacity at first paint, during an import and after it', async ({
    page,
  }) => {
    // Would not notice: a rail that fades or leaves the viewport when the beam card or the Sheet appears.
    const { docs } = await setup(page);
    await openInbox(page);
    const first = await safetyVisible(page, SAFETY_RAIL);
    expect(first.found, 'safety rail found').toBe(true);
    expect(first.inViewport, 'in viewport at first paint').toBe(true);
    expect(Math.abs(first.effectiveOpacity - 1)).toBeLessThan(0.01);

    const release = await startHeldImport(page, docs);
    const during = await safetyVisible(page, SAFETY_RAIL);
    expect(during.inViewport, 'in viewport during the import').toBe(true);
    expect(Math.abs(during.effectiveOpacity - 1)).toBeLessThan(0.01);
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();
    const after = await safetyVisible(page, SAFETY_RAIL);
    expect(after.inViewport, 'in viewport after the import').toBe(true);
    expect(Math.abs(after.effectiveOpacity - 1)).toBeLessThan(0.01);
  });
});

// ---------------------------------------------------------------------------
// G10 and HC-UIDOC-006: stillness
// ---------------------------------------------------------------------------
test.describe('Gate G10 and HC-UIDOC-006 on /inbox', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('HC-UIDOC-006 (a): an import into an empty list is still for the dates, status words, confidence words, the scanned-page warning and the handoff (stillnessProbe, interaction)', async ({
    page,
  }) => {
    // Would not notice: a new row that fades or slides in (M0 is the rule), a handoff that counts up, or a card that
    // shifts a row after it appeared. Rows that were already on screen cannot exist in this state: the list starts
    // empty, so the case in (b) below is measured separately.
    // The import reports two pages without text, so the scanned-page warning (section 2.7) is expected too.
    // RED today: no node carries data-t0 (the probe fails with "zero [data-t0] nodes").
    const { docs } = await setup(page, []);
    docs.answer = { pages_without_text: [2, 3] };
    await openInbox(page, { empty: true });
    const release = docs.hold();
    const report = await stillnessProbe(page, {
      kind: 'interaction',
      expected: [...EXPECTED, HANDOFF, SCANNED_WARNING],
      trigger: async () => {
        await fileInput(page).setInputFiles(NEW_FILE);
        await expect(page.getByText(`Reading ${NEW_NAME}`)).toBeVisible();
        release();
        await expect(page.locator(HANDOFF)).toBeVisible();
        await expect(page.locator(SCANNED_WARNING)).toBeVisible();
        await expect(page.locator(ROW)).toHaveCount(1);
      },
    });
    expect(report.nodes).toBeGreaterThan(0);
    expect(report.postTriggerSamples).toBeGreaterThan(0);
  });

  test('HC-UIDOC-006 (c): a failed import is still for the import-failed alert (stillnessProbe, interaction)', async ({
    page,
  }) => {
    // Would not notice: an alert that fades in or slides (M0 is the rule), or one that loses its data-t0 (the probe
    // fails when the expected selector matches nothing). The list starts empty so that no row sits below the alert:
    // the alert is inserted above the page body, and a row there would move, which case (a) already covers.
    // RED today: the alert carries no data-t0.
    const { docs } = await setup(page, []);
    docs.answer = { fail: { status: 400, detail: 'Unsupported file type' } };
    await openInbox(page, { empty: true });
    const report = await stillnessProbe(page, {
      kind: 'interaction',
      expected: [ERROR_ALERT],
      trigger: async () => {
        await fileInput(page).setInputFiles({ ...NEW_FILE, name: 'bad.pdf' });
        await expect(page.getByRole('alert')).toContainText('Unsupported file type');
      },
    });
    expect(report.nodes).toBeGreaterThan(0);
    expect(report.postTriggerSamples).toBeGreaterThan(0);
  });

  test('HC-UIDOC-006 (b): opening the preview Sheet is still for the dates, status words and confidence words (stillnessProbe, overlay)', async ({
    page,
  }) => {
    // Would not notice: a page behind the Sheet that shifts when the scroll lock changes the scrollbar (rects are
    // compared to 0.5 px), or a Sheet whose content moves (`still`). The scrim may fade: it is not a T0 ancestor.
    // RED today: no data-t0, and the hand-made overlay is not a Sheet.
    await setup(page);
    await openInbox(page);
    const view = rowByName(page, THIRD_NAME).getByRole('button', { name: 'View document' });
    await view.scrollIntoViewIfNeeded();
    const report = await stillnessProbe(page, {
      kind: 'overlay',
      expected: EXPECTED,
      trigger: async () => {
        await view.click();
        await expect(page.getByRole('dialog', { name: 'Document preview' })).toBeVisible();
      },
    });
    expect(report.nodes).toBeGreaterThan(0);
    expect(report.postTriggerSamples).toBeGreaterThan(0);
  });

  test('GATE G10 /inbox: opening the delete AlertDialog is still for the page behind it (stillnessProbe, overlay)', async ({
    page,
  }) => {
    // Would not notice: a dialog that makes the rows behind it move or change colour. The menu is opened before the
    // probe, so the trigger is the menu item that opens the dialog.
    await setup(page);
    await openInbox(page);
    await rowByName(page, THIRD_NAME).getByRole('button', { name: 'More options' }).click();
    const item = page.getByRole('menuitem', { name: /delete/i });
    await expect(item).toBeVisible();
    const report = await stillnessProbe(page, {
      kind: 'overlay',
      expected: EXPECTED,
      trigger: async () => {
        await item.click();
        await expect(page.getByRole('alertdialog')).toBeVisible();
      },
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('GATE G10 /inbox: an import into a NON-EMPTY list is still for the rows already on screen (stillnessProbe, interaction) - EXPECTED TO FAIL until L0 or the owner rules', async ({
    page,
  }, testInfo) => {
    // test.fail, as PAGE_OVERFLOW does in ui-shell.spec.ts: the probe is the real one, not loosened and not
    // special-cased, and the test passes only while the probe FAILS. The list is newest first
    // (api/documents.py:1093), so when the import completes the handoff card and the new row appear above the rows
    // already on screen and push every one of them down (84.4 px in CI). stillnessProbe allows no displacement.
    // The running state does not add to it any more: it lives in the drop zone's slot, so the start of the import
    // moves nothing. Which of the two has to give (a probe exemption for a row inserted above, or a list that
    // does not insert at the top) is an L0 or owner ruling. When it is ruled, delete the test.fail line: this
    // test then asserts the probe passes.
    // Would not notice: a probe failure of another kind (a timeout, a missing selector). The failure text is
    // attached so that L0 can read which one it was.
    test.fail(true, 'HC-UIDOC-006 with rows on screen: a newest-first list displaces the rows on completion; needs an L0 or owner ruling');
    const { docs } = await setup(page);
    await openInbox(page);
    const release = docs.hold();
    try {
      await stillnessProbe(page, {
        kind: 'interaction',
        expected: [...EXPECTED, HANDOFF],
        trigger: async () => {
          await fileInput(page).setInputFiles(NEW_FILE);
          await expect(page.getByText(`Reading ${NEW_NAME}`)).toBeVisible();
          release();
          await expect(page.locator(HANDOFF)).toBeVisible();
          await expect(rowByName(page, NEW_NAME)).toBeVisible();
        },
      });
    } catch (error) {
      release();
      const text = error instanceof StillnessError ? `FAIL ${error.message}` : `ERROR ${String(error)}`;
      await testInfo.attach('g10-non-empty-import', { body: text, contentType: 'text/plain' });
      throw error;
    }
  });

  test('INBOX-DATA-RENDER: the longest task between the documents response and the first row, recorded (no assertion)', async ({
    page,
  }, testInfo) => {
    // Recorded, not asserted, and no product instrumentation: the CDP CPU profiler runs from before the load. The
    // longest run of busy samples between the moment the documents response was fulfilled and the moment the first
    // row is visible is printed. The queue bullet opens a separate row only if `vite preview` still shows over 40 ms.
    // The wall clock is the profile's start time plus its cumulative sample deltas.
    const { docs } = await setup(page);
    const session = await page.context().newCDPSession(page);
    await session.send('Profiler.enable');
    await session.send('Profiler.setSamplingInterval', { interval: 200 });
    await page.goto('/inbox', { waitUntil: 'commit' });
    const startedAt = Date.now();
    await session.send('Profiler.start');
    await expect(page.locator(ROW).first()).toBeVisible();
    const visibleAt = Date.now();
    const { profile } = await session.send('Profiler.stop');

    const idleIds = new Set(
      profile.nodes.filter((n) => ['(idle)', '(program)'].includes(n.callFrame.functionName)).map((n) => n.id)
    );
    const fulfilledAt = docs.lastListFulfilledAt || startedAt;
    let t = 0;
    let longest = 0;
    let run = 0;
    profile.samples.forEach((id, i) => {
      const delta = (profile.timeDeltas[i] ?? 0) / 1000;
      t += delta;
      const wall = startedAt + t;
      const busy = !idleIds.has(id);
      if (busy && wall >= fulfilledAt && wall <= visibleAt) {
        run += delta;
        longest = Math.max(longest, run);
      } else {
        run = 0;
      }
    });
    const line = `INBOX-DATA-RENDER longest busy run between documents response and first row: ${longest.toFixed(1)} ms (window ${(visibleAt - fulfilledAt).toFixed(0)} ms)`;
    console.log(line);
    await testInfo.attach('inbox-data-render', { body: line, contentType: 'text/plain' });
  });
});
