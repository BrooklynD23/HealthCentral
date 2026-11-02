/**
 * UI-PG-CARE e2e (plan section 7.7, "UI-PG-CARE - Follow-ups"): HC-UIFU-001
 * (Done and Ignore are optimistic, with an Undo toast that restores the task
 * and PATCHes the previous status), HC-UIFU-002 (the heading reads "Follow-ups"
 * and the route stays /care-tasks), and Gate G on /care-tasks: G1 axe in light
 * and dark, G2 CLS, G3 INP with CPU x4, G5 reduced motion, G6 phone and small
 * phone widths, G7 console and network, G9 the Safety Rail, and G10 stillness
 * on the navigation to the page and on the Done click.
 *
 * Every /api/v1 request goes to the shared fixtures in support/mockApi.ts. This
 * spec adds its own GET and PATCH for /care-tasks: a later route wins, so these
 * answer the task calls, and a PATCH changes the row the next GET returns, as
 * the backend does. Nothing reaches the backend, and the unmocked list stays
 * empty (checked by the guard).
 *
 * Run on the dev server, then on a `vite preview` build (HC_E2E_BASE_URL):
 *   npx playwright test e2e/ui-care.spec.ts --project=chromium
 * Stillness runs need a quiet box (load < 1.5, no foreign test process).
 */

import { expect, test, type Locator, type Page } from '@playwright/test';
import type { CarePlanTask } from '../src/services/careTasks';
import { installMockApi, seedMockSession } from './support/mockApi';
import {
  axeGate,
  consoleAndNetworkGuard,
  maxEventDuration,
  measureCls,
  noHorizontalScroll,
  reducedMotionSnapshot,
  safetyVisible,
  stillnessProbe,
} from './support/gates';

const DOCUMENT_ID = '3b9a1f20-1111-4a2b-8c3d-0000000c4e01';
const TASK_OPEN = '6f1c2a7e-0b3d-4c5e-9a8f-0000000ca001';
const TASK_REVIEW = '6f1c2a7e-0b3d-4c5e-9a8f-0000000ca002';
const TASK_DONE = '6f1c2a7e-0b3d-4c5e-9a8f-0000000ca003';

const TITLE_OPEN = 'Repeat CBC';
const TITLE_REVIEW = 'Ask about the referral';

/** Three tasks: one in each of needs_review, open and done, each with a due date. */
const FIXTURE_TASKS: CarePlanTask[] = [
  {
    id: TASK_OPEN,
    title: TITLE_OPEN,
    due_date: '2026-11-20',
    due_date_confidence: 0.8,
    status: 'open',
    source_document_id: DOCUMENT_ID,
    source_entity_id: '6f1c2a7e-0b3d-4c5e-9a8f-0000000ce001',
    source_quote: 'Repeat CBC in 4 weeks',
    user_note: null,
    created_at: '2026-10-01T00:00:00',
    updated_at: '2026-10-01T00:00:00',
  },
  {
    id: TASK_REVIEW,
    title: TITLE_REVIEW,
    due_date: '2026-12-05',
    due_date_confidence: 0.4,
    status: 'needs_review',
    source_document_id: DOCUMENT_ID,
    source_entity_id: '6f1c2a7e-0b3d-4c5e-9a8f-0000000ce002',
    source_quote: 'Follow up on the referral',
    user_note: null,
    created_at: '2026-10-02T00:00:00',
    updated_at: '2026-10-02T00:00:00',
  },
  {
    id: TASK_DONE,
    title: 'Book the eye check',
    due_date: '2026-10-30',
    due_date_confidence: 0.9,
    status: 'done',
    source_document_id: DOCUMENT_ID,
    source_entity_id: '6f1c2a7e-0b3d-4c5e-9a8f-0000000ce003',
    source_quote: 'Book an eye check before winter',
    user_note: null,
    created_at: '2026-10-03T00:00:00',
    updated_at: '2026-10-03T00:00:00',
  },
];

/** One card per task. The page marks each card with data-care-task. */
const CARD = '[data-care-task]';
/** The follow-up dates (G10's expected selector): a [data-t0] node inside a card. */
const DATE_SELECTOR = `${CARD} [data-t0]`;
/** The Safety Rail (plan G9; UI-SHELL marks it). */
const SAFETY_RAIL = '[data-safety-rail]';

interface TaskControl {
  /** Every PATCH the page sent, in order. */
  readonly patches: Array<{ id: string; status: string }>;
  /** A task id whose next PATCH the server refuses with a 500. */
  failFor: string | null;
}

/**
 * The care-task API for this spec. GET /care-tasks/ answers the rows as they
 * are now; PATCH /care-tasks/:id changes the row and returns it. Other methods
 * fall through to the shared mock.
 */
async function mockCareTasks(page: Page): Promise<TaskControl> {
  const rows = new Map(FIXTURE_TASKS.map((task) => [task.id, { ...task }]));
  const control: TaskControl = { patches: [], failFor: null };

  await page.route(/\/api\/v1\/care-tasks\/?$/, async (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([...rows.values()]),
    });
  });

  await page.route(/\/api\/v1\/care-tasks\/([^/?]+)$/, async (route, request) => {
    if (request.method() !== 'PATCH') return route.fallback();
    const id = /\/care-tasks\/([^/?]+)$/.exec(new URL(request.url()).pathname)![1];
    const body = request.postDataJSON() as { status?: string };
    control.patches.push({ id, status: body.status ?? '' });
    const row = rows.get(id);
    if (!row) {
      await route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"Task not found"}' });
      return;
    }
    if (control.failFor === id) {
      control.failFor = null;
      await route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"refused"}' });
      return;
    }
    if (body.status) row.status = body.status as CarePlanTask['status'];
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(row) });
  });

  return control;
}

/**
 * Waits until the element's effective opacity is 1 and its box has not moved for
 * six frames, so a route still fading in cannot pass as ready (the provenance
 * spec uses the same wait).
 */
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

/** The card whose title is `title`. */
function cardFor(page: Page, title: string): Locator {
  return page.locator(CARD).filter({ hasText: title });
}

/** The status label on a card (the morphing label; a data attribute holds the status word). */
function statusLabel(page: Page, title: string): Locator {
  return cardFor(page, title).locator('[data-care-status]');
}

/** The button on the "Marked as done." toast. */
function undoButton(page: Page): Locator {
  return page.getByRole('button', { name: 'Undo', exact: true });
}

/** Clicks Done on the Repeat CBC card and waits for the toast that offers Undo. */
async function markDone(page: Page): Promise<void> {
  await cardFor(page, TITLE_OPEN).getByRole('button', { name: 'Done', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Marked as done.' })).toBeVisible();
  await expect(undoButton(page)).toBeVisible();
}

/**
 * Interactions the gates below measure: Done, and Undo on its toast (a toast action, the toast's exit and a
 * reverse PATCH). Ignore and Reopen are not measured on their own: they run through the same changeStatus
 * path as Done and Undo (one optimistic write, one PATCH, the same label morph), and add only a different
 * button on the same card.
 */

/** Opens /care-tasks with the fixtures, and waits until it is ready to interact with. */
async function openCareTasks(page: Page): Promise<void> {
  await page.goto('/care-tasks');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.getByText(TITLE_OPEN, { exact: true })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await waitForEffectiveOpacity(page, 'h1');
}

/** Sets up the shared mock, the session and the care-task API for one test. */
async function setup(page: Page) {
  const mock = await installMockApi(page);
  await seedMockSession(page);
  const control = await mockCareTasks(page);
  return { mock, control };
}

// ---------------------------------------------------------------------------
// HC-UIFU-002: the heading reads "Follow-ups" and the route is unchanged.
// ---------------------------------------------------------------------------
test.describe('HC-UIFU-002 and HC-UIFU-001 end to end', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('HC-UIFU-002: /care-tasks shows one h1 that reads "Follow-ups"', async ({ page }) => {
    // Would not notice: a heading that reads "Care Tasks", or a second h1 on the page (PAGE-H1). The URL check
    // stops the test passing on a redirect to another route.
    // RED today: the h1 reads "Care Tasks", so the named heading is not found.
    await setup(page);
    await page.goto('/care-tasks');
    await expect(page).toHaveURL(/\/care-tasks$/);
    await expect(page.getByRole('heading', { level: 1, name: 'Follow-ups', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1);
  });

  test('HC-UIFU-001: Done shows the status toast; Undo restores the task and PATCHes the previous status', async ({
    page,
  }) => {
    // Would not notice: a Done that shows no toast; an Undo that sends a fixed status; a card that leaves its
    // section when Done is marked (the dates below it would move, G10).
    // RED today: no "Marked as done." toast and no Undo button, so the test fails at the toast.
    const { control } = await setup(page);
    await openCareTasks(page);

    await cardFor(page, TITLE_OPEN).getByRole('button', { name: 'Done', exact: true }).click();

    await expect(page.getByRole('status').filter({ hasText: 'Marked as done.' })).toBeVisible();
    await expect(statusLabel(page, TITLE_OPEN)).toHaveAttribute('data-care-status', 'done');
    await expect(cardFor(page, TITLE_OPEN).locator('xpath=ancestor::section[1]')).toHaveAttribute('aria-label', 'Open');

    await page.getByRole('button', { name: 'Undo', exact: true }).click();

    await expect(statusLabel(page, TITLE_OPEN)).toHaveAttribute('data-care-status', 'open');
    expect(control.patches).toEqual([
      { id: TASK_OPEN, status: 'done' },
      { id: TASK_OPEN, status: 'open' },
    ]);
  });

  test('HC-UIFU-001: Ignore on a task in review shows the toast; Undo PATCHes needs_review back', async ({ page }) => {
    // Would not notice: an Ignore whose Undo restores "open" for a task that was "needs_review".
    // RED today: no "Marked as ignored." toast, so the test fails at the toast.
    const { control } = await setup(page);
    await openCareTasks(page);

    await cardFor(page, TITLE_REVIEW).getByRole('button', { name: 'Ignore', exact: true }).click();

    await expect(page.getByRole('status').filter({ hasText: 'Marked as ignored.' })).toBeVisible();
    await page.getByRole('button', { name: 'Undo', exact: true }).click();

    await expect(statusLabel(page, TITLE_REVIEW)).toHaveAttribute('data-care-status', 'needs_review');
    expect(control.patches).toEqual([
      { id: TASK_REVIEW, status: 'ignored' },
      { id: TASK_REVIEW, status: 'needs_review' },
    ]);
  });
});

// ---------------------------------------------------------------------------
// Gate G on /care-tasks (plan section 6). Each test names its RED state.
// ---------------------------------------------------------------------------
test.describe('Gate G on /care-tasks', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Gate G1 /care-tasks has no serious or critical axe violation in light or dark', async ({ page }) => {
    // Would not notice: a dark-only contrast failure. The native select keeps a white background in dark mode,
    // so its ink fails AA (PAGE-A11Y: color-contrast on #care-task-doc-select).
    // RED today: color-contrast (serious) on #care-task-doc-select in dark. Light passes.
    await setup(page);
    await openCareTasks(page);
    const light = await axeGate(page, { theme: 'light' });
    expect(light.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`), 'light').toEqual([]);
    const dark = await axeGate(page, { theme: 'dark' });
    expect(dark.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`), 'dark').toEqual([]);
  });

  test('Gate G2 /care-tasks: CLS stays under 0.1 over the load, the Done click and Undo', async ({ page }) => {
    // Would not notice: a layout shift when the status label changes, a label row that grows or shrinks, or a
    // card that moves when Undo puts the status back.
    // RED today: the Done button is not labelled from a card, so the sequence fails before the shift is measured.
    await setup(page);
    const cls = await measureCls(page, async () => {
      await page.goto('/care-tasks');
      await expect(page.getByText(TITLE_OPEN, { exact: true })).toBeVisible();
      await markDone(page);
      await undoButton(page).click();
      await expect(statusLabel(page, TITLE_OPEN)).toHaveAttribute('data-care-status', 'open');
    });
    expect(cls).toBeLessThan(0.1);
  });

  test('Gate G3 /care-tasks: the Done click and the Undo click each stay under 200 ms with CPU throttled x4', async ({
    page,
  }) => {
    // Would not notice: a Done that re-renders the whole list on the main thread (an INP over 200 ms at CPU x4), or
    // an Undo that does the same through the toast action.
    // Returns 0 when no event reaches 16 ms, so a dead observer also passes; the bound is the gate's, unchanged.
    // RED today: the Done button of the Repeat CBC card is found only with the new card markup.
    await setup(page);
    await openCareTasks(page);
    const done = await maxEventDuration(page, () =>
      cardFor(page, TITLE_OPEN).getByRole('button', { name: 'Done', exact: true }).click()
    );
    expect(done, 'Done click').toBeLessThan(200);

    await expect(undoButton(page)).toBeVisible();
    const undo = await maxEventDuration(page, () => undoButton(page).click());
    expect(undo, 'Undo click').toBeLessThan(200);
  });

  test('Gate G5 /care-tasks: no element has a transform 50 ms after the Done click or the Undo click under reduced motion', async ({
    page,
  }) => {
    // Would not notice: a morph or a toast that moves with a transform for users who asked for reduced motion (the
    // morph must fade opacity only; the toast must not slide in, and must not slide out when Undo dismisses it).
    // The check is page-wide, so the toast is included.
    // RED today: the card is not marked data-care-task, so the Done click cannot be made on the card.
    await setup(page);
    await openCareTasks(page);
    const afterDone = await reducedMotionSnapshot(page, () =>
      cardFor(page, TITLE_OPEN).getByRole('button', { name: 'Done', exact: true }).click()
    );
    expect(afterDone, 'elements with a non-identity transform 50 ms after Done').toEqual([]);

    await expect(undoButton(page)).toBeVisible();
    const afterUndo = await reducedMotionSnapshot(page, () => undoButton(page).click());
    expect(afterUndo, 'elements with a non-identity transform 50 ms after Undo').toEqual([]);
  });

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 320, height: 640 },
  ]) {
    test(`Gate G6 /care-tasks: no horizontal scroll at ${viewport.width}x${viewport.height}, before and after Done`, async ({
      page,
    }) => {
      // Would not notice: a card whose buttons push the page wider than the phone viewport.
      // RED today: passes on the old page too (it had no wide row); it guards the new card layout and the toast.
      await page.setViewportSize(viewport);
      await setup(page);
      await openCareTasks(page);
      expect((await noHorizontalScroll(page)).ok, 'before Done').toBe(true);
      await cardFor(page, TITLE_OPEN).getByRole('button', { name: 'Done', exact: true }).click();
      await expect(page.getByRole('status').filter({ hasText: 'Marked as done.' })).toBeVisible();
      expect((await noHorizontalScroll(page)).ok, 'after Done').toBe(true);
    });
  }

  test('Gate G7 /care-tasks: no console error, no non-localhost request and no unmocked API call', async ({ page }) => {
    // Would not notice: an unmocked request the page made (it would be answered 599 and logged), or a console error
    // from the optimistic write or the toast.
    // RED today: the Done click finds no card, so the test cannot reach the guard's clean assertion.
    const { mock } = await setup(page);
    const guard = consoleAndNetworkGuard(page, { mock });
    await openCareTasks(page);
    await cardFor(page, TITLE_OPEN).getByRole('button', { name: 'Done', exact: true }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Marked as done.' })).toBeVisible();
    guard.assertClean();
  });

  test('Gate G9 /care-tasks: the Safety Rail is in the viewport at full opacity at first paint, after Done and after Undo', async ({
    page,
  }) => {
    // Would not notice: a rail that fades or moves off-screen when the page changes state.
    // RED today: the rail is in the shell (UI-SHELL, done), so this check passes on the old page too, and it guards
    // the new page. The Done click needs the new card markup, so the second half fails on the old page.
    await setup(page);
    await openCareTasks(page);
    const first = await safetyVisible(page, SAFETY_RAIL);
    expect(first.found, 'safety rail found').toBe(true);
    expect(first.inViewport, 'safety rail in viewport at first paint').toBe(true);
    expect(Math.abs(first.effectiveOpacity - 1)).toBeLessThan(0.01);

    await markDone(page);
    const after = await safetyVisible(page, SAFETY_RAIL);
    expect(after.inViewport, 'safety rail in viewport after Done').toBe(true);
    expect(Math.abs(after.effectiveOpacity - 1)).toBeLessThan(0.01);

    await undoButton(page).click();
    await expect(statusLabel(page, TITLE_OPEN)).toHaveAttribute('data-care-status', 'open');
    const afterUndo = await safetyVisible(page, SAFETY_RAIL);
    expect(afterUndo.inViewport, 'safety rail in viewport after Undo').toBe(true);
    expect(Math.abs(afterUndo.effectiveOpacity - 1)).toBeLessThan(0.01);
  });

  test('Gate G10 /care-tasks: the navigation to the page is still for the follow-up dates (stillnessProbe, navigation)', async ({
    page,
  }) => {
    // Would not notice: a date that counts up, fades in or moves during the page change, or a date that has no
    // data-t0 (the probe fails with zero data-t0 nodes). The probe starts on the Inbox and clicks the nav link, a
    // client-side change. The route is lazy, so the window waits for the network to go idle.
    // RED today: no date carries data-t0, so the probe fails with "zero [data-t0] nodes".
    await setup(page);
    await page.goto('/inbox');
    const nav = page.getByRole('navigation', { name: 'Main navigation' });
    const link = nav.getByRole('link', { name: 'Follow-ups', exact: true });
    await expect(link).toBeVisible();
    await page.evaluate(() => document.fonts.ready);

    const report = await stillnessProbe(page, {
      trigger: () => link.click(),
      expected: [DATE_SELECTOR],
      kind: 'navigation',
      lazyRoute: true,
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('Gate G10 /care-tasks: the Done click is still for the follow-up dates (stillnessProbe, interaction)', async ({
    page,
  }) => {
    // Would not notice: a Done that regroups the card under "Done", so every date below it moves; a date that
    // changes colour or clip-path while its status changes; or a card that re-renders its date with new text.
    // RED today: no date carries data-t0, so the probe fails with "zero [data-t0] nodes".
    await setup(page);
    await openCareTasks(page);
    const done = cardFor(page, TITLE_OPEN).getByRole('button', { name: 'Done', exact: true });
    // Scroll the button into view before the probe starts: a click that scrolls moves every date, and the probe
    // would then measure the scroll, not the change of status.
    await done.scrollIntoViewIfNeeded();
    await waitForEffectiveOpacity(page, 'h1');

    const report = await stillnessProbe(page, {
      trigger: () => done.click(),
      expected: [DATE_SELECTOR],
    });
    expect(report.nodes).toBeGreaterThan(0);
    expect(report.postTriggerSamples).toBeGreaterThan(0);
  });

  test('Gate G10 /care-tasks: the Undo click is still for the follow-up dates (stillnessProbe, interaction)', async ({
    page,
  }) => {
    // Would not notice: an Undo that regroups the card under "Open" again, so every date below it moves; or a date
    // that fades or changes colour when its status goes back. Kind and bound are the Done click's: interaction, 40 ms.
    // RED today: no date carries data-t0, so the probe fails with "zero [data-t0] nodes".
    await setup(page);
    await openCareTasks(page);
    await markDone(page);
    await waitForEffectiveOpacity(page, 'h1');

    const report = await stillnessProbe(page, {
      trigger: () => undoButton(page).click(),
      expected: [DATE_SELECTOR],
    });
    expect(report.nodes).toBeGreaterThan(0);
    expect(report.postTriggerSamples).toBeGreaterThan(0);
    await expect(statusLabel(page, TITLE_OPEN)).toHaveAttribute('data-care-status', 'open');
  });
});
