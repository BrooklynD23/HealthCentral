/**
 * UI-PG-DOCUMENTS e2e (plan section 7.7, "UI-PG-DOCUMENTS"): HC-UIDOC-001 (row actions are visible with the mouse
 * away and reachable by Tab), HC-UIDOC-002 (at most two tag chips, no raw identifier), HC-UIDOC-003 (the beam card
 * and the orb while an import is in flight, static under reduced motion), HC-UIDOC-004 (an alert stays outside the
 * beam), HC-UIDOC-005 (delete through the AlertDialog, with the real Radix focus and pointer-events checks),
 * HC-UIDOC-006 (stillnessProbe across an import into an empty list with a scanned-page warning, across a failed
 * import, across the start of an import, plain navigation onto /inbox and the preview Sheet; on the events the patient
 * caused, into a list that has rows, rows jump once: see "one instant jump" below), and Gate G on
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
 *   npx playwright test e2e/ui-documents.spec.ts --project=chromium --grep-invert 'GATE G(2|3|5|10)|HC-UIDOC-006|INBOX-DATA-RENDER'
 * The quiet box runs the timing set on the dev server, then on a `vite preview` build (HC_E2E_BASE_URL):
 *   npx playwright test e2e/ui-documents.spec.ts --project=chromium --grep 'GATE G(2|3|5|10)|HC-UIDOC-006|INBOX-DATA-RENDER'
 *
 * GATE G3 on /inbox asserts only on a production build (HC_E2E_BASE_URL set, PREVIEW below). On the dev server it
 * prints the three figures and asserts no bound, because React's dev build puts a View click at 216 ms on CI. So CI
 * (dev server) no longer enforces G3 on /inbox; the quiet-box run on `vite preview` does. A dev-server pass was never
 * a G3 pass.
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
  RECT_TOLERANCE_PX,
  STILLNESS_MAX_GAP_MS,
  STILLNESS_WINDOW_MS,
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
const AGAIN_NAME = 'second-cbc-report.pdf';

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

/** Set when the run points at a `vite preview` build (HC_E2E_BASE_URL), the pattern of ui-toast.spec.ts. */
const PREVIEW = Boolean(process.env.HC_E2E_BASE_URL);

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
  /** The next GET /documents waits until the returned function is called (the page shows its loading state). */
  holdList(): () => void;
  /** The next DELETE waits until the returned function is called; the row goes when it does. */
  holdDelete(): () => void;
  answer: ImportAnswer;
  /** Every GET /documents waits this long before it answers (the refetch after an import or a delete). Default 0. */
  listDelayMs: number;
  /** Every GET /documents answers 500 (the refetch fails). */
  listFails: boolean;
  /** The next GET /documents/highlights/summary waits until the returned function is called. */
  holdSummary(): () => void;
  /** Every GET /documents/highlights/summary the page sent. */
  summaryRequests: number;
  /** Every GET /documents/highlights/summary answers 500. */
  summaryFails: boolean;
  /** Wall-clock ms when the last GET /documents was fulfilled. */
  lastListFulfilledAt: number;
}

/**
 * The documents API for this spec. GET /documents answers the rows as they are now, newest first (the backend
 * orders by imported_at descending, api/documents.py:1093), so an import puts its row at the top.
 */
async function mockDocuments(page: Page, rows: Document[]): Promise<DocsControl> {
  let gate: Promise<void> | null = null;
  let listGate: Promise<void> | null = null;
  let summaryGate: Promise<void> | null = null;
  let deleteGate: Promise<void> | null = null;
  const control: DocsControl = {
    rows: [...rows],
    deletes: [],
    imports: 0,
    answer: {},
    listDelayMs: 0,
    listFails: false,
    summaryRequests: 0,
    summaryFails: false,
    lastListFulfilledAt: 0,
    holdSummary() {
      let release!: () => void;
      summaryGate = new Promise<void>((resolve) => {
        release = () => {
          resolve();
        };
      });
      return release;
    },
    hold() {
      let release!: () => void;
      gate = new Promise<void>((resolve) => {
        release = () => {
          resolve();
        };
      });
      return release;
    },
    holdList() {
      let release!: () => void;
      listGate = new Promise<void>((resolve) => {
        release = () => {
          resolve();
        };
      });
      return release;
    },
    holdDelete() {
      let release!: () => void;
      deleteGate = new Promise<void>((resolve) => {
        release = () => {
          resolve();
        };
      });
      return release;
    },
  };

  await page.route(/\/api\/v1\/documents\/?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    if (listGate) await listGate;
    listGate = null;
    if (control.listDelayMs > 0) await new Promise((resolve) => setTimeout(resolve, control.listDelayMs));
    if (control.listFails) {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'list failed' }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(control.rows) });
    control.lastListFulfilledAt = Date.now();
  });

  await page.route(/\/api\/v1\/documents\/highlights\/summary\/?(\?.*)?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    control.summaryRequests += 1;
    if (summaryGate) await summaryGate;
    summaryGate = null;
    if (control.summaryFails) {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'summary failed' }) });
      return;
    }
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
    // Every import gets its own id, so a second import, or a retry after a failed one, is a different document from
    // the first. A mock that answered every import with one document hid the three-position jump a second import
    // made (the first is doc-new-0004, the second doc-new-0005). The first import keeps NEW_NAME whatever file was
    // sent (the long-name tests send a name that is already a fixture row); a later one takes the uploaded name.
    const uploaded = /filename="([^"]+)"/.exec(request.postData() ?? '')?.[1] ?? NEW_NAME;
    const document = makeDoc({
      id: `doc-new-${String(3 + control.imports).padStart(4, '0')}`,
      source: control.imports === 1 ? NEW_NAME : uploaded,
      doc_type: 'lab_pdf',
      status: 'parsed',
      extraction_confidence: 0.62,
      imported_at: `2026-11-02T08:${String(control.imports).padStart(2, '0')}:00Z`,
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
    const held = deleteGate;
    deleteGate = null;
    if (held) await held;
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
  // Not getByRole('heading'): it skips content an open AlertDialog hides from the accessibility tree, so a row that
  // is still in the DOM would read as gone (toHaveCount(0)) while the dialog is up.
  return page.locator(ROW).filter({ has: page.locator('h4').getByText(name, { exact: true }) });
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

// ---------------------------------------------------------------------------
// HC-UIDOC-006: one instant jump (owner INBOX-ROW-JUMP, L0 ruling on PR #464).
//
// On an event the patient caused or was waiting on (an import completed or failed, an alert or a warning dismissed,
// Remove), a row may move once, in one step, with no slide and no fade. stillnessProbe allows no displacement at all
// and is not relaxed; plain navigation onto /inbox, the start of an import and opening the preview Sheet keep using it.
// This helper is the assertion for the events: it samples every row at animation-frame rate across the event and
// requires each row to hold at most two positions, before and after, with no sample in between.
// ---------------------------------------------------------------------------

/** Every GET /documents the event triggers answers this late (what a real server costs). The instant mock hides a split commit. */
const LIST_HOLD_MS = 300;
/** A row's opacity is read as the product of its own and every ancestor's. */
const OPACITY_EPSILON = 0.01;

interface FrameItem {
  rect: [number, number, number, number];
  opacity: number;
}
interface Frame {
  /** performance.now() in the page */
  t: number;
  items: Record<string, FrameItem>;
}
interface FrameRun {
  frames: Frame[];
  /** Frames sampled before the trigger started. */
  preCount: number;
}

/**
 * Pure. One message per failure. It fails closed: too few samples after the trigger, a gap between two samples over
 * STILLNESS_MAX_GAP_MS (a slide could hide inside it and read as a jump), or an event that changed nothing it tracks
 * (it measured nothing) is a failure, not a pass.
 */
function jumpFailures(run: FrameRun, options: { windowMs?: number } = {}): string[] {
  const { frames, preCount } = run;
  const windowMs = options.windowMs ?? STILLNESS_WINDOW_MS;
  const failures: string[] = [];

  const minimumAfter = Math.floor(windowMs / STILLNESS_MAX_GAP_MS);
  if (preCount < 2) failures.push(`only ${preCount} sample(s) before the event; a "before" position needs at least 2`);
  if (frames.length - preCount < minimumAfter) {
    failures.push(
      `only ${frames.length - preCount} sample(s) after the event; a ${windowMs} ms window needs at least ${minimumAfter} at one per ${STILLNESS_MAX_GAP_MS} ms`
    );
  }
  let maxGap = 0;
  for (let i = 1; i < frames.length; i++) maxGap = Math.max(maxGap, frames[i].t - frames[i - 1].t);
  if (maxGap > STILLNESS_MAX_GAP_MS) {
    failures.push(
      `a ${maxGap.toFixed(1)} ms gap between two samples is over ${STILLNESS_MAX_GAP_MS} ms: a slide could hide in it and read as a jump`
    );
  }
  if (frames.length === 0) return failures;

  const names = Array.from(new Set(frames.flatMap((frame) => Object.keys(frame.items))));
  const origin = frames[0].t;
  let changed = false;
  for (const name of names) {
    let anchor: FrameItem['rect'] | null = null;
    const positions: string[] = [];
    let seenAt = -1;
    let lostAt = -1;
    let badOpacity = '';
    let returned = '';
    for (let i = 0; i < frames.length; i++) {
      const item = frames[i].items[name];
      if (!item) {
        if (seenAt >= 0 && lostAt < 0) lostAt = i;
        continue;
      }
      if (seenAt < 0) seenAt = i;
      if (lostAt >= 0 && !returned) {
        // Gone and back is two moves, or a spinner where the list was: not a before and an after.
        returned = `left the screen at ${(frames[lostAt].t - origin).toFixed(0)} ms and came back at ${(frames[i].t - origin).toFixed(0)} ms`;
      }
      const at = `${(frames[i].t - origin).toFixed(0)} ms`;
      if (!badOpacity && Math.abs(item.opacity - 1) > OPACITY_EPSILON) {
        badOpacity = `effective opacity ${item.opacity.toFixed(2)} at ${at}`;
      }
      // Drift is measured from the position the item last held, not from the previous sample, so a slow slide of
      // 0.3 px a frame adds up to a change instead of passing under the tolerance each frame.
      if (!anchor || item.rect.some((value, index) => Math.abs(value - anchor![index]) > RECT_TOLERANCE_PX)) {
        anchor = item.rect;
        positions.push(`[${item.rect.map((value) => Math.round(value * 10) / 10)}] at ${at}`);
      }
    }
    if (badOpacity) failures.push(`${name}: ${badOpacity} (must be 1 on every sample: no fade)`);
    if (returned) failures.push(`${name}: ${returned}`);
    // An item that was on screen when the event began holds a position before and one after. One that appears
    // during the event appears where it will stay.
    const allowed = seenAt === 0 ? 2 : 1;
    if (positions.length > allowed) {
      failures.push(`${name}: held ${positions.length} positions (at most ${allowed}): ${positions.join(' -> ')}`);
    }
    if (positions.length > 1 || seenAt > 0 || lostAt >= 0) changed = true;
  }
  if (!changed) failures.push('nothing the sampler tracks changed during the event, so it measured nothing');
  if (Object.keys(frames[frames.length - 1].items).length === 0) failures.push('no row or event element on screen at the end');
  return failures;
}

/**
 * Samples every inbox row (named by its title) and the event elements once per animation frame, runs the trigger, keeps
 * sampling for STILLNESS_WINDOW_MS more, and returns the frames. The wait is the sampling window, read off the page's
 * own clock.
 */
async function sampleFrames(page: Page, trigger: () => Promise<void>): Promise<FrameRun> {
  const tracked = { alert: ERROR_ALERT, handoff: HANDOFF, scanned: SCANNED_WARNING };
  await page.evaluate(
    ({ row, extra }) => {
      const state = { running: true, frames: [] as unknown[] };
      (window as unknown as { __hcFrames?: typeof state }).__hcFrames = state;
      const read = (el: Element) => {
        const box = el.getBoundingClientRect();
        let opacity = 1;
        for (let node: Element | null = el; node; node = node.parentElement) {
          opacity *= parseFloat(getComputedStyle(node).opacity);
        }
        return { rect: [box.x, box.y, box.width, box.height], opacity };
      };
      const frame = () => {
        if (!state.running) return;
        const items: Record<string, unknown> = {};
        document.querySelectorAll(row).forEach((el) => {
          items[`row ${el.querySelector('h4')?.textContent ?? '?'}`] = read(el);
        });
        for (const [name, selector] of Object.entries(extra)) {
          const el = document.querySelector(selector);
          if (el) items[name] = read(el);
        }
        state.frames.push({ t: performance.now(), items });
        requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    },
    { row: ROW, extra: tracked }
  );
  await page.waitForFunction(() => ((window as unknown as { __hcFrames: { frames: unknown[] } }).__hcFrames.frames.length >= 3), undefined, {
    polling: 'raf',
  });
  const preCount = await page.evaluate(() => (window as unknown as { __hcFrames: { frames: unknown[] } }).__hcFrames.frames.length);
  await trigger();
  const until = await page.evaluate((windowMs) => performance.now() + windowMs, STILLNESS_WINDOW_MS);
  await page.waitForFunction((end) => performance.now() >= end, until, { polling: 'raf' });
  const frames = await page.evaluate(() => {
    const state = (window as unknown as { __hcFrames?: { running: boolean; frames: unknown[] } }).__hcFrames;
    if (!state) return null;
    state.running = false;
    return state.frames as Frame[];
  });
  if (frames === null) throw new Error('the frame sampler is gone: the document was replaced during the event');
  return { frames, preCount };
}

/** Runs the event and asserts one instant jump (see jumpFailures). Prints the figures so the log carries them. */
async function expectOneJump(page: Page, label: string, trigger: () => Promise<void>): Promise<void> {
  const run = await sampleFrames(page, trigger);
  const gaps = run.frames.slice(1).map((frame, index) => frame.t - run.frames[index].t);
  console.log(
    `HC-UIDOC-006 ${label}: ${run.frames.length} frames (${run.preCount} before), max gap ${Math.max(...gaps).toFixed(1)} ms`
  );
  expect(jumpFailures(run), label).toEqual([]);
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

/**
 * Counts the pixels of a screenshot of `locator` that sit within 3 px of its edge and are within 48 (RGB distance) of
 * the accent token. The screenshot is decoded on a blank second page, so the page under test is not touched.
 * Reads the pixels: a ring that is in the DOM but painted under an opaque card counts 0.
 */
async function accentPixelsOnEdge(page: Page, locator: Locator): Promise<number> {
  const accent = await page.evaluate(() => {
    const probe = document.createElement('span');
    probe.style.color = 'var(--accent)';
    document.body.append(probe);
    const colour = getComputedStyle(probe).color;
    probe.remove();
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = colour;
    ctx.fillRect(0, 0, 1, 1);
    return Array.from(ctx.getImageData(0, 0, 1, 1).data).slice(0, 3);
  });
  const png = (await locator.screenshot()).toString('base64');
  const decoder = await page.context().newPage();
  try {
    return await decoder.evaluate(
      async ({ b64, target }) => {
        const image = new Image();
        image.src = `data:image/png;base64,${b64}`;
        await image.decode();
        const canvas = document.createElement('canvas');
        canvas.width = image.width;
        canvas.height = image.height;
        const ctx = canvas.getContext('2d')!;
        ctx.drawImage(image, 0, 0);
        const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
        let count = 0;
        for (let y = 0; y < canvas.height; y++) {
          for (let x = 0; x < canvas.width; x++) {
            const onEdge = x < 3 || y < 3 || x >= canvas.width - 3 || y >= canvas.height - 3;
            if (!onEdge) continue;
            const i = (y * canvas.width + x) * 4;
            const distance = Math.hypot(data[i] - target[0], data[i + 1] - target[1], data[i + 2] - target[2]);
            if (data[i + 3] > 200 && distance <= 48) count += 1;
          }
        }
        return count;
      },
      { b64: png, target: accent }
    );
  } finally {
    await decoder.close();
  }
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

  for (const mode of ['no-preference', 'reduce'] as const) {
    test(`HC-UIDOC-003: with reducedMotion=${mode} the ring is painted above the card: accent pixels sit on the card edge`, async ({
      page,
    }) => {
      // Would not notice: a ring that is the wrong shade of accent (the tolerance is 48 in RGB distance; only fully opaque pixels count, so the test waits for the 240 ms fade-in), or one that
      // paints on one edge only (the count is over all four). It does see a ring that sits in the DOM but under the
      // opaque card, which every DOM and computed-style check misses. Measured before the fix: 0 pixels in both modes.
      // RED today: the ring has no z-index, so the card (position: relative, later in paint order) covers it.
      const { docs } = await setup(page);
      await page.emulateMedia({ reducedMotion: mode });
      await openInbox(page);
      const release = await startHeldImport(page, docs);
      // The ring fades in over 240 ms; a screenshot taken halfway reads blended colours.
      await page.waitForFunction(() => {
        const ring = document.querySelector('.beam-border[data-active="true"] > span');
        return ring !== null && getComputedStyle(ring).opacity === '1';
      });
      const accentPixels = await accentPixelsOnEdge(page, page.locator(BEAM));
      expect(accentPixels, 'accent-coloured pixels within 3 px of the card edge').toBeGreaterThan(100);
      release();
      await expect(page.locator(BEAM)).toHaveCount(0);
    });
  }

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

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 390, height: 844 },
    { width: 320, height: 640 },
  ]) {
    test(`HC-UIDOC-009: closing the preview Sheet with Escape puts focus back on View document of that row, at ${viewport.width}x${viewport.height}`, async ({
      page,
    }) => {
      // Would not notice: focus on <body> (the next Tab lands on "Skip to content"). The focused element is read and
      // must be the exact button that opened the Sheet, on the second row so a "first button" default would fail.
      await page.setViewportSize(viewport);
      await setup(page);
      await openInbox(page);
      const view = rowByName(page, SECOND_NAME).getByRole('button', { name: 'View document' });
      await view.focus();
      await page.keyboard.press('Enter');
      const sheet = page.getByRole('dialog', { name: 'Document preview' });
      await expect(sheet).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(sheet).toBeHidden();
      await expect(view).toBeFocused();
      expect(await page.evaluate(() => document.activeElement?.tagName)).toBe('BUTTON');
    });
  }

  test('HC-UIDOC-009: closing the preview Sheet that the last-import card opened puts focus back on its Preview button', async ({
    page,
  }) => {
    await setup(page);
    await openInbox(page);
    await fileInput(page).setInputFiles(NEW_FILE);
    await expect(page.locator(HANDOFF)).toBeVisible();
    const preview = page.getByRole('button', { name: 'Preview', exact: true });
    await preview.focus();
    await page.keyboard.press('Enter');
    const sheet = page.getByRole('dialog', { name: 'Document preview' });
    await expect(sheet).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(sheet).toBeHidden();
    await expect(preview).toBeFocused();
  });

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 390, height: 844 },
    { width: 320, height: 640 },
  ]) {
    test(`HC-UIDOC-010: the delete dialog shows the whole document name inside itself, at ${viewport.width}x${viewport.height}`, async ({
      page,
    }) => {
      // Would not notice: a name cut off inside a dialog that scrolls sideways. A fixed overlay does not widen the
      // document, so G6 cannot see it; the text range of the name is measured against the dialog box instead. The
      // delete cannot be undone, so the person must be able to read which document goes.
      await page.setViewportSize(viewport);
      await setup(page);
      await openInbox(page);
      await rowByName(page, LONG_NAME).getByRole('button', { name: 'More options' }).click();
      await page.getByRole('menuitem', { name: /delete/i }).click();
      const dialog = page.getByRole('alertdialog');
      await expect(dialog).toContainText(LONG_NAME);
      const measured = await dialog.evaluate((el, name) => {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        let node: Node | null;
        let range: Range | null = null;
        while ((node = walker.nextNode())) {
          const at = node.textContent?.indexOf(name) ?? -1;
          if (at >= 0) {
            range = document.createRange();
            range.setStart(node, at);
            range.setEnd(node, at + name.length);
            break;
          }
        }
        const box = el.getBoundingClientRect();
        const text = range ? Array.from(range.getClientRects()) : [];
        return {
          found: range !== null,
          dialogLeft: box.left,
          dialogRight: box.right,
          textLeft: Math.min(...text.map((r) => r.left)),
          textRight: Math.max(...text.map((r) => r.right)),
          scrollWidth: el.scrollWidth,
          clientWidth: el.clientWidth,
        };
      }, LONG_NAME);
      expect(measured.found, 'the name is in one text node of the dialog').toBe(true);
      expect(measured.textLeft).toBeGreaterThanOrEqual(measured.dialogLeft - 0.5);
      expect(measured.textRight).toBeLessThanOrEqual(measured.dialogRight + 0.5);
      expect(measured.scrollWidth, 'the dialog does not scroll sideways').toBe(measured.clientWidth);
    });
  }

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

  test('GATE G1 /inbox has no serious or critical axe violation in light or dark: the list, the open row menu, an import in flight, the delete dialog, the empty library', async ({
    page,
  }) => {
    // Would not notice: a violation that only the delete dialog, the processing state or the empty library has, so
    // five states are scanned. The theme is applied after load by the harness.
    // RED today: not known; the old page passes axe (HC-UIG-002). The new states are the new surface.
    const { docs } = await setup(page);
    await openInbox(page);
    for (const theme of ['light', 'dark'] as const) {
      expect(blockingIds(await axeSettled(page, theme)), `list, ${theme}`).toEqual([]);
    }
    // The open row menu is a surface of its own (bg-white was #fff under dark text, contrast 1.18).
    await setTheme(page, 'light');
    await rowByName(page, THIRD_NAME).getByRole('button', { name: 'More options' }).click();
    await expect(page.getByRole('menu')).toBeVisible();
    for (const theme of ['light', 'dark'] as const) {
      expect(blockingIds(await axeSettled(page, theme)), `open row menu, ${theme}`).toEqual([]);
    }
    await page.keyboard.press('Escape');
    await expect(page.getByRole('menu')).toBeHidden();
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

    // The empty library (EmptyState with its action) is a fifth surface.
    docs.rows = [];
    await openInbox(page, { empty: true });
    await expect(page.getByRole('button', { name: 'Choose a file' })).toBeVisible();
    for (const theme of ['light', 'dark'] as const) {
      expect(blockingIds(await axeSettled(page, theme)), `empty library, ${theme}`).toEqual([]);
    }
  });

  test('GATE G1 /inbox: the open Add to pinboard menu has no serious or critical axe violation in light or dark', async ({
    page,
  }) => {
    // Would not notice: a violation in the menu's contents with pinboards to list: the mock lists none, so the menu
    // holds its one disabled "Create a pinboard first" item. The row menu is scanned by the test above.
    // RED today: a modal DropdownMenu sets aria-hidden on the page while its trigger keeps focus (aria-hidden-focus),
    // the same failure the row menu had; the menu surface is bg-white with a black/8 border.
    await setup(page);
    await openInbox(page);
    await setTheme(page, 'light');
    await rowByName(page, THIRD_NAME).getByRole('button', { name: 'Add to pinboard' }).click();
    await expect(page.getByRole('menu')).toBeVisible();
    await expect(page.getByRole('menuitem', { name: 'Create a pinboard first' })).toBeVisible();
    for (const theme of ['light', 'dark'] as const) {
      expect(blockingIds(await axeSettled(page, theme)), `open pin menu, ${theme}`).toEqual([]);
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
    // The bound counts only on a production build (vite preview, HC_E2E_BASE_URL set): the dev server carries React's
    // dev cost (CI measured View 216, 248 and Delete 200 on this head). On the dev server this test prints the three
    // figures and asserts nothing about them, so CI no longer enforces G3 on /inbox, and the quiet-box run on vite
    // preview does. A dev-server pass is not a G3 pass. It still clicks, and still checks the dialog closes.
    await setup(page);
    await openInbox(page);
    const row = rowByName(page, THIRD_NAME);
    const view = await maxEventDuration(page, () => row.getByRole('button', { name: 'View document' }).click());
    if (PREVIEW) expect(view, 'View document click').toBeLessThan(200);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();

    const menu = await maxEventDuration(page, () => row.getByRole('button', { name: 'More options' }).click());
    if (PREVIEW) expect(menu, 'More options click').toBeLessThan(200);
    const del = await maxEventDuration(page, () => page.getByRole('menuitem', { name: /delete/i }).click());
    if (PREVIEW) expect(del, 'Delete click').toBeLessThan(200);
    console.log(
      `GATE G3 /inbox (${PREVIEW ? 'production build, bound 200 ms' : 'dev server, no bound asserted'}): View ${view} ms, More options ${menu} ms, Delete ${del} ms`
    );
  });

  test('GATE G5 /inbox: no element has a transform 50 ms after View document, Delete or an import starts, under reduced motion', async ({
    page,
  }) => {
    // Would not notice: a transform on the Sheet or the dialog on a path the sequence skips. The check is page-wide.
    // It covers View document, Delete, an import starting, the loading state (held list) and the empty library.
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

    // The loading state: the list request is held, so the spinner is on screen when the transforms are read.
    const releaseList = docs.holdList();
    const afterLoading = await reducedMotionSnapshot(page, async () => {
      await page.goto('/inbox');
      await expect(page.getByText('Loading documents...')).toBeVisible();
    });
    expect(afterLoading, 'the loading state').toEqual([]);
    releaseList();
    await expect(page.locator(ROW).first()).toBeVisible();

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
    // Each picture is attached and also written under the test's output directory, with g5 in its name and a
    // 'gate-g5-screenshot' annotation (as ui-palette.spec.ts does), so `find <output> -name '*.png' -path '*g5*'` collects them.
    const keep = async (name: string, take: (path: string) => Promise<Buffer>) => {
      const path = testInfo.outputPath(`g5-${name}.png`);
      await testInfo.attach(name, { body: await take(path), contentType: 'image/png' });
      testInfo.annotations.push({ type: 'gate-g5-screenshot', description: path });
    };
    await keep('empty-state-reduced-motion', (path) => page.screenshot({ path, fullPage: true }));

    const release = await startHeldImport(page, docs);
    await expect(page.locator(`${BEAM} canvas`)).toBeAttached();
    await keep('s2-s3-beam-and-orb-reduced-motion', (path) => page.locator(BEAM).screenshot({ path }));
    await keep('inbox-importing-reduced-motion', (path) => page.screenshot({ path, fullPage: true }));
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
      // It also reads the first row's top before and during the import: a wrapped status line that makes the running
      // block taller than the idle block moves the page at the start of the import without moving scrollWidth.
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
      const firstRowTop = () =>
        page.locator(ROW).first().evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
      const topBefore = await firstRowTop();
      // The 127-character name has no space: the status line "Reading <name>" has to wrap inside the card.
      const release = await startHeldImport(page, docs, { ...NEW_FILE, name: LONG_NAME });
      expect((await noHorizontalScroll(page)).ok, 'during the import with the long name').toBe(true);
      expect(await firstRowTop(), 'the first row has not moved since the import started').toBeCloseTo(topBefore, 0);
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

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 320, height: 640 },
  ]) {
    test(`GATE G6 /inbox: a 255-character file name does not move the first row or widen the page when an import starts, at ${viewport.width}x${viewport.height}`, async ({
      page,
    }) => {
      // Would not notice: a name that moves the page only after the import ends (the rows move for the new row, which
      // HC-UIDOC-006 (g) covers). The longest name a file system allows is 255 characters; the status line is clamped,
      // so the running block must not be taller than the idle block.
      // RED today: 255 characters move the first row by 80 px at 390 and 100 px at 320 (measured in review).
      await page.setViewportSize(viewport);
      const { docs } = await setup(page);
      await openInbox(page);
      const firstRowTop = () =>
        page.locator(ROW).first().evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
      const before = await firstRowTop();
      const name = `${'x'.repeat(251)}.pdf`;
      const release = await startHeldImport(page, docs, { ...NEW_FILE, name });
      expect((await noHorizontalScroll(page)).ok, 'during the import').toBe(true);
      expect(await firstRowTop(), 'the first row has not moved since the import started').toBeCloseTo(before, 0);
      release();
      await expect(page.locator(HANDOFF)).toBeVisible();
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
    // empty, so the displacement of existing rows is measured separately, by the jump cases further down (an
    // import that completes, and an import that fails, both into a list that has rows).
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
    // the alert is inserted above the drop zone, and a row below it would move. That is the
    // failed-import jump case further down, which starts with rows.
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

  // The events below are the ones the owner allows one instant jump on (INBOX-ROW-JUMP). Each holds the list refetch
  // for LIST_HOLD_MS, because the instant mock answers in the same frame and hides a card that commits before its row.
  // The summary does not refetch: the import and the delete invalidate ['documents'], the summary is ['highlights'].
  // Would not notice, for all of them: (1) a motion shorter than one frame, which no sampler at frame rate can see;
  // (2) a gap the sampler could not fill: such a run fails closed, so a loaded box fails the run instead of passing
  // it, which is why these are timing gates; (3) scroll: rects are read relative to the viewport, a focus() that
  // scrolls the page (the scroller is the window, not <main>) moves every row at once, and that single move reads as
  // the one allowed jump. The list here is three rows in 900 px, so no event scrolls; a long list is not covered
  // (HC-UIDOC-013 reads the focus position at 320x640, not the rows); (4) a duplicate warning or a handoff card
  // that moves while a row stays put is read only through the T0 hooks (alert, handoff, scanned): the duplicate
  // warning has no hook, so it is covered through the rows it pushes, not on its own; (5) rows that were never on
  // screen: only the three fixture rows and the one new row are tracked.

  /** A held import into the three-row list: the beam card is up, the request waits for the returned release. */
  async function inboxWithHeldImport(page: Page, answer: ImportAnswer = {}) {
    const { docs } = await setup(page);
    docs.answer = answer;
    await openInbox(page);
    docs.listDelayMs = LIST_HOLD_MS;
    const release = await startHeldImport(page, docs);
    return { docs, release };
  }

  const DUPLICATE: ImportAnswer = {
    duplicate_warning: { match_type: 'content_hash', document_id: 'doc-third-0003', title: THIRD_NAME },
  };

  async function openDeleteDialog(page: Page, name: string): Promise<void> {
    await rowByName(page, name).getByRole('button', { name: 'More options' }).click();
    await page.getByRole('menuitem', { name: /delete/i }).click();
    await expect(page.getByRole('alertdialog')).toBeVisible();
  }

  test('HC-UIDOC-006 (d): the start of an import into a list with rows moves nothing (stillnessProbe, interaction)', async ({
    page,
  }) => {
    // Would not notice: a displacement that happens when the import ends (the jump tests below own that), or one on a
    // row the probe cannot read: it reads the rows' dates, status words and confidence words.
    const { docs } = await setup(page);
    await openInbox(page);
    const release = docs.hold();
    try {
      const report = await stillnessProbe(page, {
        kind: 'interaction',
        expected: EXPECTED,
        trigger: async () => {
          await fileInput(page).setInputFiles(NEW_FILE);
          await expect(page.getByText(`Reading ${NEW_NAME}`)).toBeVisible();
        },
      });
      expect(report.nodes).toBeGreaterThan(0);
    } finally {
      release();
    }
    await expect(page.locator(HANDOFF)).toBeVisible();
  });

  test('HC-UIDOC-006 (e): plain navigation onto /inbox moves nothing (stillnessProbe, navigation)', async ({ page }) => {
    // Would not notice: a late arrival that the instant mock never produces (the next test holds the highlights). The
    // start page is /verify, so the click is a real route change.
    await setup(page);
    await page.goto('/verify');
    await expect(page.locator(SAFETY_RAIL)).toBeVisible({ timeout: 15_000 });
    const report = await stillnessProbe(page, {
      kind: 'navigation',
      lazyRoute: true,
      expected: EXPECTED,
      trigger: () => page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Documents', exact: true }).click(),
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('HC-UIDOC-006 (f): highlights that arrive after the rows do not move the rows on a plain navigation (stillnessProbe, navigation)', async ({
    page,
  }) => {
    // The documents answer at once and the highlight summary 300 ms later. A row that rendered without its chips and
    // then grew would push every row below it. Would not notice: a stale summary that is cached for five minutes
    // (App.tsx staleTime) and refetches in the background. isLoading is false on a background refetch, so the rows are
    // not held for it, and chips could still be inserted; this test navigates with no cached summary, so it does not
    // cover that case.
    const { docs } = await setup(page);
    await page.goto('/verify');
    await expect(page.locator(SAFETY_RAIL)).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');
    const release = docs.holdSummary();
    try {
      const report = await stillnessProbe(page, {
        kind: 'navigation',
        expected: EXPECTED,
        trigger: async () => {
          await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Documents', exact: true }).click();
          await expect.poll(() => docs.summaryRequests).toBeGreaterThan(0);
          // The summary is late by this much; the list has answered long before.
          await page.evaluate((ms) => new Promise((resolve) => setTimeout(resolve, ms)), LIST_HOLD_MS);
          release();
          await expect(page.locator(ROW).first()).toBeVisible();
        },
      });
      expect(report.nodes).toBeGreaterThan(0);
    } finally {
      release();
    }
  });

  test('HC-UIDOC-006 (g): an import that completes into a list with rows jumps once: the handoff card and the new row come together', async ({
    page,
  }) => {
    const { release } = await inboxWithHeldImport(page);
    await expectOneJump(page, 'import completed', async () => {
      release();
      await expect(page.locator(HANDOFF)).toBeVisible();
      await expect(rowByName(page, NEW_NAME)).toBeVisible();
    });
  });

  test('HC-UIDOC-006 (h): an import with a duplicate warning jumps once: the card, the warning and the new row come together', async ({
    page,
  }) => {
    const { release } = await inboxWithHeldImport(page, DUPLICATE);
    await expectOneJump(page, 'import completed with a duplicate warning', async () => {
      release();
      await expect(page.getByText('Possible duplicate upload')).toBeVisible();
      await expect(page.locator(HANDOFF)).toBeVisible();
      await expect(rowByName(page, NEW_NAME)).toBeVisible();
    });
  });

  test('HC-UIDOC-006 (i): a failed import jumps once: the alert pushes the rows down in one step', async ({ page }) => {
    const { release } = await inboxWithHeldImport(page, { fail: { status: 400, detail: 'Unsupported file type' } });
    await expectOneJump(page, 'import failed', async () => {
      release();
      await expect(page.getByRole('alert')).toContainText('Unsupported file type');
    });
  });

  test('HC-UIDOC-006 (j): dismissing the import-failed alert jumps once', async ({ page }) => {
    const { release } = await inboxWithHeldImport(page, { fail: { status: 400, detail: 'Unsupported file type' } });
    release();
    await expect(page.getByRole('alert')).toContainText('Unsupported file type');
    await waitForEffectiveOpacity(page, ROW);
    await expectOneJump(page, 'alert dismissed', async () => {
      await page.getByRole('button', { name: `Dismiss import error for ${NEW_NAME}` }).click();
      await expect(page.getByRole('alert')).toBeHidden();
    });
  });

  test('HC-UIDOC-006 (k): dismissing the duplicate warning jumps once', async ({ page }) => {
    const { release } = await inboxWithHeldImport(page, DUPLICATE);
    release();
    await expect(page.getByText('Possible duplicate upload')).toBeVisible();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await waitForEffectiveOpacity(page, ROW);
    await expectOneJump(page, 'duplicate warning dismissed', async () => {
      await page.getByRole('button', { name: `Dismiss duplicate warning for ${THIRD_NAME}` }).click();
      await expect(page.getByText('Possible duplicate upload')).toBeHidden();
    });
  });

  test('HC-UIDOC-006 (l): Remove on a row with no card jumps once: the rows below close up in one step', async ({ page }) => {
    const { docs } = await setup(page);
    await openInbox(page);
    docs.listDelayMs = LIST_HOLD_MS;
    await openDeleteDialog(page, SECOND_NAME);
    await waitForEffectiveOpacity(page, ROW);
    await expectOneJump(page, 'Remove', async () => {
      await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
      await expect(rowByName(page, SECOND_NAME)).toHaveCount(0);
    });
    expect(docs.deletes).toEqual(['doc-second-0002']);
  });

  test('HC-UIDOC-006 (m): Remove on the row the handoff card is for jumps once: the card leaves with its row', async ({ page }) => {
    const { docs, release } = await inboxWithHeldImport(page);
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await waitForEffectiveOpacity(page, ROW);
    await openDeleteDialog(page, NEW_NAME);
    await expectOneJump(page, 'Remove of the imported document', async () => {
      await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
      await expect(rowByName(page, NEW_NAME)).toHaveCount(0);
      await expect(page.locator(HANDOFF)).toHaveCount(0);
    });
    expect(docs.deletes).toEqual(['doc-new-0004']);
  });

  test('HC-UIDOC-006 (n): Remove on a row with a duplicate warning jumps once: the card and the warning leave with it', async ({
    page,
  }) => {
    const { release } = await inboxWithHeldImport(page, DUPLICATE);
    release();
    await expect(page.getByText('Possible duplicate upload')).toBeVisible();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await waitForEffectiveOpacity(page, ROW);
    await openDeleteDialog(page, NEW_NAME);
    await expectOneJump(page, 'Remove of a duplicate-warned import', async () => {
      await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
      await expect(rowByName(page, NEW_NAME)).toHaveCount(0);
      await expect(page.getByText('Possible duplicate upload')).toHaveCount(0);
    });
  });

  test('HC-UIDOC-006 (o): a second import in one visit jumps once: the new card replaces the old in the frame the new row arrives', async ({
    page,
  }) => {
    // Would not notice: what (g) cannot see, a card that is replaced when the import resolves instead of when the
    // list answers. (g) runs a first import, where there is no card to replace; here the old card leaves a frame
    // early, the rows below it move up, and the new card and row move them down again: three positions.
    // The mock gives each import its own id and name.
    const { docs, release } = await inboxWithHeldImport(page);
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await waitForEffectiveOpacity(page, ROW);
    const again = { ...NEW_FILE, name: AGAIN_NAME };
    const releaseSecond = await startHeldImport(page, docs, again);
    await expectOneJump(page, 'second import', async () => {
      releaseSecond();
      await expect(page.getByText(`Document imported: ${AGAIN_NAME}`)).toBeVisible();
      await expect(rowByName(page, AGAIN_NAME)).toBeVisible();
    });
    expect(docs.imports).toBe(2);
    await expect(page.getByText(`Document imported: ${NEW_NAME}`)).toHaveCount(0);
  });

  test('HC-UIDOC-006 (p): a retry after a failed import jumps once: the alert leaves in the frame the new card and row arrive', async ({
    page,
  }) => {
    // Would not notice: the same as (o), for the alert. The alert used to leave when the retry resolved, a frame before
    // the row, so the rows moved up by the alert and down by the card and the row.
    const { docs, release } = await inboxWithHeldImport(page, { fail: { status: 400, detail: 'Unsupported file type' } });
    release();
    await expect(page.getByRole('alert')).toContainText('Unsupported file type');
    await waitForEffectiveOpacity(page, ROW);
    docs.answer = {};
    const releaseRetry = await startHeldImport(page, docs);
    await expectOneJump(page, 'retry after a failed import', async () => {
      releaseRetry();
      await expect(page.locator(HANDOFF)).toBeVisible();
      await expect(rowByName(page, NEW_NAME)).toBeVisible();
      await expect(page.getByRole('alert')).toHaveCount(0);
    });
    expect(docs.imports).toBe(2);
  });

  /**
   * Two imports, then Remove on the newer one: the card and the row leave together, and every later list refresh
   * (the next Remove, the next import) must not bring the older import's card back. Returns when the list is settled.
   */
  async function twoImportsThenRemoveSecond(page: Page) {
    const { docs, release } = await inboxWithHeldImport(page);
    release();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await expect(page.getByText(`Document imported: ${NEW_NAME}`)).toBeVisible();
    await waitForEffectiveOpacity(page, ROW);
    const again = { ...NEW_FILE, name: AGAIN_NAME };
    const releaseSecond = await startHeldImport(page, docs, again);
    releaseSecond();
    await expect(rowByName(page, AGAIN_NAME)).toBeVisible();
    await expect(page.getByText(`Document imported: ${AGAIN_NAME}`)).toBeVisible();
    await openDeleteDialog(page, AGAIN_NAME);
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect(rowByName(page, AGAIN_NAME)).toHaveCount(0);
    await expect(page.getByText('Document imported:')).toHaveCount(0);
    await waitForEffectiveOpacity(page, ROW);
    return docs;
  }

  /** A failed import, a retry that comes through, then Remove on the retried row. Returns when the list is settled. */
  async function retryThenRemove(page: Page) {
    const { docs, release } = await inboxWithHeldImport(page, { fail: { status: 400, detail: 'Unsupported file type' } });
    release();
    await expect(page.getByRole('alert')).toContainText('Unsupported file type');
    await waitForEffectiveOpacity(page, ROW);
    docs.answer = {};
    const releaseRetry = await startHeldImport(page, docs);
    releaseRetry();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await expect(page.getByText(/Import failed:/)).toHaveCount(0);
    await openDeleteDialog(page, NEW_NAME);
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect(rowByName(page, NEW_NAME)).toHaveCount(0);
    await expect(page.getByText(/Import failed:/)).toHaveCount(0);
    await waitForEffectiveOpacity(page, ROW);
    return docs;
  }

  test('HC-UIDOC-006 (q): two imports, Remove the newer, then Remove an old row: the older import card does not come back', async ({
    page,
  }) => {
    // Would not notice: a stale card that shows for less than one animation frame (the sampler reads at frame rate);
    // a stale card that is on screen for the whole refresh is read, as a third row position. The closing check
    // reads only the settled page. Scroll is not covered (see the block header).
    await twoImportsThenRemoveSecond(page);
    await openDeleteDialog(page, SECOND_NAME);
    await expectOneJump(page, 'Remove an old row after Remove of an import', async () => {
      await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
      await expect(rowByName(page, SECOND_NAME)).toHaveCount(0);
    });
    await expect(page.getByText('Document imported:')).toHaveCount(0);
  });

  test('HC-UIDOC-006 (r): two imports, Remove the newer, then a third import: its card arrives with its row, the older card does not', async ({
    page,
  }) => {
    // Would not notice: the same limits as (q). The list answers 300 ms late, so a first-import card that shows while
    // the list is still fetching holds a position of its own for about 300 ms, and is read.
    const docs = await twoImportsThenRemoveSecond(page);
    const third = { ...NEW_FILE, name: 'third-cbc-report.pdf' };
    const release = await startHeldImport(page, docs, third);
    await expectOneJump(page, 'import after Remove of an import', async () => {
      release();
      await expect(page.getByText(`Document imported: ${third.name}`)).toBeVisible();
      await expect(rowByName(page, third.name)).toBeVisible();
    });
    await expect(page.getByText(`Document imported: ${NEW_NAME}`)).toHaveCount(0);
  });

  test('HC-UIDOC-006 (s): a failed import, a retry, Remove the retried row, then Remove an old row: the failure alert does not come back', async ({
    page,
  }) => {
    // Would not notice: the same limits as (q). The alert would be role=alert for a file the retry did import, so
    // one that returns says something false as well as moving the rows.
    await retryThenRemove(page);
    await openDeleteDialog(page, SECOND_NAME);
    await expectOneJump(page, 'Remove an old row after Remove of a retried import', async () => {
      await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
      await expect(rowByName(page, SECOND_NAME)).toHaveCount(0);
    });
    await expect(page.getByText(/Import failed:/)).toHaveCount(0);
  });

  test('HC-UIDOC-006 (t): a failed import, a retry, Remove the retried row, then a new import: the failure alert does not come back', async ({
    page,
  }) => {
    // Would not notice: the same limits as (s).
    const docs = await retryThenRemove(page);
    const third = { ...NEW_FILE, name: 'third-cbc-report.pdf' };
    const release = await startHeldImport(page, docs, third);
    await expectOneJump(page, 'import after Remove of a retried import', async () => {
      release();
      await expect(rowByName(page, third.name)).toBeVisible();
      await expect(page.getByText(`Document imported: ${third.name}`)).toBeVisible();
    });
    await expect(page.getByText(/Import failed:/)).toHaveCount(0);
  });

  // HC-UIDOC-014..017: the import result waits for the list refresh, but not for ever. After 3 s (a constant in
  // DocumentInbox.tsx) the card, the notices, the warning and the alert show without the new row, and the row arrives
  // when the list answers: a second step, each step one instant jump (L0 ruling on PR #464, comment 6606938809).

  test('HC-UIDOC-014: a list refresh that never answers still shows the card, the scanned-page notice and the duplicate warning, without the new row', async ({
    page,
  }) => {
    // Would not notice: the exact tick (3000 ms; this waits up to 8 s and prints the time it took), or a timer that fires
    // early: the first check runs the moment the import has resolved. The list is held for the whole test.
    // RED at fb6e7ef2: none of them ever showed (reviewer: card, link, scanned notice and warning all null at 2 s).
    const { docs, release } = await inboxWithHeldImport(page, { ...DUPLICATE, pages_without_text: [2] });
    docs.holdList();
    release();
    await expect(page.getByText(`Reading ${NEW_NAME}`)).toBeHidden();
    const resolvedAt = Date.now();
    await expect(page.locator(HANDOFF)).toBeHidden();
    await expect(page.locator(HANDOFF)).toBeVisible({ timeout: 8_000 });
    console.log(`HC-UIDOC-014: the card showed ${Date.now() - resolvedAt} ms after the import resolved (list never answered)`);
    await expect(page.locator(SCANNED_WARNING)).toBeVisible();
    await expect(page.getByText('Possible duplicate upload')).toBeVisible();
    await expect(rowByName(page, NEW_NAME)).toHaveCount(0);
  });

  test('HC-UIDOC-006 (u) HC-UIDOC-014: a refresh that has not settled after 3 s shows the card in one step, and the row arrives in a second one', async ({
    page,
  }) => {
    // Would not notice: the same limits as (g). Two windows, each read by jumpFailures unchanged: rows hold two
    // positions in each (before and after the step), the card appears once, and nothing is half-faded. The wait for the
    // card is inside the first window, so the window is about 3 s plus STILLNESS_WINDOW_MS.
    const { docs, release } = await inboxWithHeldImport(page);
    const releaseList = docs.holdList();
    await expectOneJump(page, 'card at the timer', async () => {
      release();
      await expect(page.locator(HANDOFF)).toBeVisible({ timeout: 8_000 });
    });
    await expect(rowByName(page, NEW_NAME)).toHaveCount(0);
    await expectOneJump(page, 'row after the timer', async () => {
      releaseList();
      await expect(rowByName(page, NEW_NAME)).toBeVisible();
    });
    await expect(page.locator(HANDOFF)).toBeVisible();
  });

  test('HC-UIDOC-006 (v) HC-UIDOC-014: with an ordinary list answer the 3 s timer changes nothing: rows hold two positions across the import and past the timer', async ({
    page,
  }) => {
    // Would not notice: a timer that fires early, in the first 300 ms: the card would then show before its row and the
    // rows would hold three positions, which is what this reads. The window runs 3.5 s after the import, past the timer.
    const { release } = await inboxWithHeldImport(page);
    await expectOneJump(page, 'import completed, then the timer fires', async () => {
      release();
      await expect(page.locator(HANDOFF)).toBeVisible();
      await expect(rowByName(page, NEW_NAME)).toBeVisible();
      await page.waitForTimeout(3_500);
    });
  });

  test('HC-UIDOC-016: a failed import, then a retry whose refresh never answers: the alert leaves and the card shows at the timer', async ({
    page,
  }) => {
    // Would not notice: the swap happening in one frame (HC-UIDOC-006 (p) reads that for an ordinary list).
    // RED at fb6e7ef2: the alert stayed for ever.
    const { docs, release } = await inboxWithHeldImport(page, { fail: { status: 400, detail: 'Unsupported file type' } });
    release();
    await expect(page.getByRole('alert')).toContainText('Unsupported file type');
    docs.answer = {};
    const releaseRetry = await startHeldImport(page, docs);
    docs.holdList();
    releaseRetry();
    await expect(page.getByText(`Reading ${NEW_NAME}`)).toBeHidden();
    await expect(page.getByRole('alert')).toHaveCount(1);
    await expect(page.locator(HANDOFF)).toBeVisible({ timeout: 8_000 });
    await expect(page.getByRole('alert')).toHaveCount(0);
  });

  test('HC-UIDOC-017: Remove of an import before its timer fires: the card and the alert do not come back when it fires or on a later refresh', async ({
    page,
  }) => {
    // Would not notice: a card that returns for less than a frame (HC-UIDOC-006 (q) to (t) sample at frame rate; this
    // reads the settled page 3.5 s after the Remove). Recurring failure 17's chain, with the timer in it.
    const { docs, release } = await inboxWithHeldImport(page);
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await openDeleteDialog(page, NEW_NAME);
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect(rowByName(page, NEW_NAME)).toHaveCount(0);
    await expect(page.locator(HANDOFF)).toHaveCount(0);
    await page.waitForTimeout(3_500);
    await expect(page.locator(HANDOFF)).toHaveCount(0);
    await expect(page.getByText(`Document imported: ${NEW_NAME}`)).toHaveCount(0);
    await openDeleteDialog(page, SECOND_NAME);
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect(rowByName(page, SECOND_NAME)).toHaveCount(0);
    await expect(page.getByText(`Document imported: ${NEW_NAME}`)).toHaveCount(0);
    expect(docs.deletes).toEqual(['doc-new-0004', 'doc-second-0002']);
  });

  test('HC-UIDOC-018: a second Remove while the first is in flight: the card and the link for the first removed document do not stay', async ({
    page,
  }) => {
    // Would not notice: the order the two DELETEs settle in (the first is released first), or a card that goes for less
    // than a frame (HC-UIDOC-006 (m) samples the ordinary Remove). It reads the settled page.
    // RED at fb6e7ef2: the card and "N values ready to review" stayed for the document the first Remove deleted.
    const { docs, release } = await inboxWithHeldImport(page);
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await openDeleteDialog(page, NEW_NAME);
    const releaseFirst = docs.holdDelete();
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect.poll(() => docs.deletes.length).toBe(1);
    await openDeleteDialog(page, SECOND_NAME);
    const releaseSecond = docs.holdDelete();
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect.poll(() => docs.deletes.length).toBe(2);
    releaseFirst();
    releaseSecond();
    await expect(rowByName(page, NEW_NAME)).toHaveCount(0);
    await expect(rowByName(page, SECOND_NAME)).toHaveCount(0);
    await expect(page.getByText(`Document imported: ${NEW_NAME}`)).toHaveCount(0);
    await expect(page.locator(HANDOFF)).toHaveCount(0);
    expect(docs.deletes).toEqual(['doc-new-0004', 'doc-second-0002']);
  });

  test('HC-UIDOC-013: after Remove of the only row, keyboard focus on Import Document is inside the viewport at 320x640', async ({
    page,
  }) => {
    // Would not notice: a focus that is on screen for a frame and scrolls away again (it polls until the smooth scroll
    // the focus starts has ended, then reads once). Not a timing gate: the position is read after the scroll, not
    // during it. The page is made tall by an import into an empty library with a scanned-page notice and a duplicate
    // warning, then scrolled to the bottom, so the Import Document button at the top is above the viewport.
    // RED before this round: Remove focused the button with preventScroll, so it stayed above the viewport (top -321
    // at scrollY 542, measured in review).
    await page.setViewportSize({ width: 320, height: 640 });
    const { docs } = await setup(page, []);
    docs.answer = { ...DUPLICATE, pages_without_text: [1, 2, 3] };
    await openInbox(page, { empty: true });
    await fileInput(page).setInputFiles(NEW_FILE);
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await expect(page.getByText('Possible duplicate upload')).toBeVisible();
    await page.evaluate(() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' }));
    await waitForEffectiveOpacity(page, ROW);
    const importButton = page.getByRole('button', { name: /import document/i });
    const before = await importButton.evaluate((el) => el.getBoundingClientRect().bottom);
    expect(before, 'the button starts above the viewport').toBeLessThan(0);
    await openDeleteDialog(page, NEW_NAME);
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect(rowByName(page, NEW_NAME)).toHaveCount(0);
    await expect(importButton).toBeFocused();
    await expect
      .poll(
        () =>
          importButton.evaluate((el) => {
            const box = el.getBoundingClientRect();
            return box.top >= 0 && box.bottom <= window.innerHeight;
          }),
        { timeout: 5_000, message: 'Import Document has focus and is inside the viewport' }
      )
      .toBe(true);
  });

  test('HC-UIDOC-012: a failing highlight summary still shows the rows, and the delay App.tsx retry: 1 adds is printed', async ({
    page,
  }) => {
    // Would not notice: the delay on a slow or flaky network. The retry waits one second (react-query's first retry
    // delay), and the rows wait with it, because they wait for the summary (the late-highlights fix). The figure is
    // printed for L0; the rows must be there within 15 s, with no chip.
    const { docs } = await setup(page);
    const timeToRows = async () => {
      const startedAt = Date.now();
      await page.goto('/inbox');
      await expect(page.locator(ROW).first()).toBeVisible({ timeout: 15_000 });
      return Date.now() - startedAt;
    };
    const ok = await timeToRows();
    docs.summaryFails = true;
    docs.summaryRequests = 0;
    const failing = await timeToRows();
    console.log(`HC-UIDOC-012 rows visible ${ok} ms after goto with the summary answering, ${failing} ms with it failing (${docs.summaryRequests} summary requests)`);
    expect(docs.summaryRequests, 'one request and one retry').toBe(2);
    await expect(page.locator(ROW)).toHaveCount(3);
    await expect(page.getByText('Abnormal lab')).toHaveCount(0);
  });

  test('HC-UIDOC-011: when the list refresh after an import fails, the patient still sees the import result', async ({ page }) => {
    // Would not notice: a result that shows too early (HC-UIDOC-006 (g) owns the timing). Here the refetch answers 500,
    // and App.tsx retry: 1 holds the page one second before it gives up, so the card comes after that delay.
    const { docs, release } = await inboxWithHeldImport(page, DUPLICATE);
    docs.listFails = true;
    release();
    await expect(page.locator(HANDOFF)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Possible duplicate upload')).toBeVisible();
    await expect(page.getByText('Failed to load documents')).toBeVisible();
  });

  test('HC-UIDOC-011: when the list refresh after a Remove fails, a card for the removed document does not stay', async ({ page }) => {
    // Would not notice: a card that hides on a refetch that never ends. The refetch here fails, and the card goes
    // when it does.
    const { docs, release } = await inboxWithHeldImport(page);
    release();
    await expect(page.locator(HANDOFF)).toBeVisible();
    await expect(rowByName(page, NEW_NAME)).toBeVisible();
    await openDeleteDialog(page, NEW_NAME);
    docs.listFails = true;
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click();
    await expect.poll(() => docs.deletes).toEqual(['doc-new-0004']);
    await expect(page.getByText('Failed to load documents')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(HANDOFF)).toHaveCount(0);
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

    const fulfilledAt = docs.lastListFulfilledAt || startedAt;
    // The longest run of busy samples inside the window. '(program)' is native browser work that is not script: it is
    // counted as idle in the first figure and as busy in the second, and both are printed (round 3 read 14.8-22.4 ms
    // against 22.7-31.2 ms on the same profiles). Neither is asserted.
    const longestRun = (idleNames: string[]) => {
      const idleIds = new Set(profile.nodes.filter((n) => idleNames.includes(n.callFrame.functionName)).map((n) => n.id));
      let t = 0;
      let longest = 0;
      let run = 0;
      (profile.samples ?? []).forEach((id, i) => {
        const delta = ((profile.timeDeltas ?? [])[i] ?? 0) / 1000;
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
      return longest;
    };
    const programIdle = longestRun(['(idle)', '(program)']);
    const programBusy = longestRun(['(idle)']);
    const line =
      `INBOX-DATA-RENDER longest busy run between documents response and first row: ${programIdle.toFixed(1)} ms with (program) counted as idle, ` +
      `${programBusy.toFixed(1)} ms with (program) counted as busy (window ${(visibleAt - fulfilledAt).toFixed(0)} ms)`;
    console.log(line);
    await testInfo.attach('inbox-data-render', { body: line, contentType: 'text/plain' });
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-006: the jump assertion itself, on synthetic samples (no browser, no timing).
// ---------------------------------------------------------------------------
test.describe('HC-UIDOC-006 jumpFailures (pure)', () => {
  /** Rows by name: one y per frame, or null while the row is not on screen. Frames are `gap` ms apart. */
  function run(
    rows: Record<string, Array<number | null>>,
    options: { gap?: number; pre?: number; opacity?: (name: string, frame: number) => number } = {}
  ): FrameRun {
    const gap = options.gap ?? 16;
    const length = Math.max(...Object.values(rows).map((ys) => ys.length));
    const frames: Frame[] = [];
    for (let i = 0; i < length; i++) {
      const items: Frame['items'] = {};
      for (const [name, ys] of Object.entries(rows)) {
        const y = ys[i];
        if (y !== null && y !== undefined) items[name] = { rect: [0, y, 100, 50], opacity: options.opacity?.(name, i) ?? 1 };
      }
      frames.push({ t: 1000 + i * gap, items });
    }
    return { frames, preCount: options.pre ?? 3 };
  }
  const still = (y: number, n: number) => Array<number>(n).fill(y);

  test('HC-UIDOC-006: one step from a position to another passes', () => {
    // Would not notice: a step that is a slide faster than the sample rate (a 16 ms slide is one sample).
    expect(jumpFailures(run({ 'row a': [...still(100, 5), ...still(300, 35)] }))).toEqual([]);
  });

  test('HC-UIDOC-006: a slide between the two positions fails', () => {
    const slide = [...still(100, 5), 140, 180, 220, 260, ...still(300, 35)];
    expect(jumpFailures(run({ 'row a': slide })).join('\n')).toMatch(/row a: held 6 positions/);
  });

  test('HC-UIDOC-006: one sample between the two positions fails', () => {
    expect(jumpFailures(run({ 'row a': [...still(100, 5), 200, ...still(300, 35)] })).join('\n')).toMatch(/held 3 positions/);
  });

  test('HC-UIDOC-006: a slide sampled too sparsely to see it fails closed, not as a jump', () => {
    // 64 ms apart the slide has no sample inside it and reads as a clean jump. The gap is what fails it.
    const failures = jumpFailures(run({ 'row a': [...still(100, 5), ...still(300, 35)] }, { gap: 64 }));
    expect(failures.join('\n')).toMatch(/64\.0 ms gap between two samples is over 40 ms/);
  });

  test('HC-UIDOC-006: too few samples after the event fails closed', () => {
    expect(jumpFailures(run({ 'row a': [...still(100, 5), ...still(300, 10)] })).join('\n')).toMatch(/only 12 sample\(s\) after the event/);
  });

  test('HC-UIDOC-006: too few samples before the event fails closed', () => {
    expect(jumpFailures(run({ 'row a': [...still(100, 5), ...still(300, 35)] }, { pre: 1 })).join('\n')).toMatch(/only 1 sample\(s\) before/);
  });

  test('HC-UIDOC-006: a fade of one frame fails', () => {
    const failures = jumpFailures(
      run({ 'row a': [...still(100, 5), ...still(300, 35)] }, { opacity: (_name, frame) => (frame === 7 ? 0.6 : 1) })
    );
    expect(failures.join('\n')).toMatch(/row a: effective opacity 0\.60 at 112 ms/);
  });

  test('HC-UIDOC-006: a row that moves and comes back fails (two moves are not before and after)', () => {
    const there = [...still(100, 5), ...still(300, 10), ...still(100, 25)];
    expect(jumpFailures(run({ 'row a': there })).join('\n')).toMatch(/held 3 positions/);
  });

  test('HC-UIDOC-006: a drift of 0.3 px a frame adds up and fails', () => {
    const drift = Array.from({ length: 40 }, (_, i) => 100 + 0.3 * i);
    expect(jumpFailures(run({ 'row a': drift })).join('\n')).toMatch(/row a: held \d+ positions/);
  });

  test('HC-UIDOC-006: an event that changes nothing the sampler tracks fails (it measured nothing)', () => {
    expect(jumpFailures(run({ 'row a': still(100, 40) })).join('\n')).toMatch(/measured nothing/);
  });

  test('HC-UIDOC-006: a row that appears with the jump holds one position; one that then moves fails', () => {
    const stays = { 'row a': [...still(100, 5), ...still(300, 35)], 'row new': [...Array<null>(5).fill(null), ...still(100, 35)] };
    expect(jumpFailures(run(stays))).toEqual([]);
    const moves = { ...stays, 'row new': [...Array<null>(5).fill(null), ...still(100, 10), ...still(150, 25)] };
    expect(jumpFailures(run(moves)).join('\n')).toMatch(/row new: held 2 positions \(at most 1\)/);
  });

  test('HC-UIDOC-006: a row that vanishes during the event and comes back fails', () => {
    // Would not notice: a row that is hidden for less than one sample (a motion shorter than a frame). Found in review:
    // a list that swaps to a spinner during the refetch used to pass, because the row came back at its old position.
    const rows = { 'row a': [...still(100, 10), ...Array<null>(5).fill(null), ...still(100, 25)], 'row b': [...still(50, 5), ...still(90, 35)] };
    expect(jumpFailures(run(rows)).join('\n')).toMatch(/row a: left the screen at \d+ ms and came back at \d+ ms/);
  });

  test('HC-UIDOC-006: a row that leaves with the jump holds one position and passes', () => {
    const rows = { 'row a': [...still(100, 5), ...still(300, 35)], 'row gone': [...still(200, 5), ...Array<null>(35).fill(null)] };
    expect(jumpFailures(run(rows))).toEqual([]);
  });
});
