/**
 * UI-PG-ASK e2e (plan "UI-PG-ASK"): HC-UIASK-001 to 005 on the real layout, and Gate G on /explain.
 *
 *  - HC-UIASK-001  sending scrolls only the message list; window.scrollY is unchanged
 *  - HC-UIASK-002  the disclaimer under the composer is in the viewport at 390 and 1440 without scrolling
 *  - HC-UIASK-003  axe: scrollable-region-focusable, label and button-name pass
 *  - HC-UIASK-004  no canvas and no ThinkingOrb (a pin: green before the change)
 *  - HC-UIASK-005  a new answer's values and citations pass stillnessProbe from the first sample after they render
 *
 * The chat and feedback calls are answered here (page.route, registered after installMockApi so it runs first);
 * every other /api/v1 call goes to the shared shell fixtures. Run without the backend (recipe 2 in e2e/README.md):
 *   PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 TMPDIR=/dev/shm npx playwright test e2e/ui-ask.spec.ts --project=chromium
 *
 * The stillness probes and the G2, G3 and G5 measurements are timing measurements. Run them on a quiet box only.
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
import { installMockApi, seedMockSession } from './support/mockApi';

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };

const verification = {
  enabled: true,
  total_claims: 2,
  verified_claims: 2,
  failed_claims: 0,
  faithfulness_score: 0.95,
  authority_score: 0.85,
  summary: 'All claims verified',
  issues: [],
};

/** An answer with an observation-backed citation (it has a deep link) and a reference one (it has none). */
function chatAnswer(n: number) {
  return {
    segments: [
      {
        segment_type: 'report_facts',
        content: `Your LDL cholesterol is 142 mg/dL [cite:1] (answer ${n}). It is above the 100 mg/dL reference limit.`,
        citations: [
          {
            source_type: 'user_observation',
            doc_id: 'doc-fixture-0001',
            doc_title: 'Lab report, March',
            page: 2,
            text_snippet: 'LDL Cholesterol 142 mg/dL (reference below 100)',
            observation_id: 'obs-fixture-0001',
          },
        ],
      },
      {
        segment_type: 'general_info',
        content: 'LDL carries cholesterol to the arteries [cite:2].',
        citations: [
          {
            source_type: 'reference',
            doc_id: null,
            doc_title: 'Medical Reference',
            page: null,
            text_snippet: 'LDL is the main carrier of cholesterol in the blood.',
          },
        ],
      },
    ],
    full_response: `Your LDL cholesterol is 142 mg/dL [cite:1] (answer ${n}). It is above the 100 mg/dL reference limit. LDL carries cholesterol to the arteries [cite:2].`,
    insufficient_context: false,
    insufficient_reasons: [],
    verification,
    is_valid: true,
    validation_errors: [],
    session_id: 'session-ask-1',
    turn_id: `turn-ask-${n}`,
  };
}

interface AskMock {
  /** Chat questions answered so far. */
  readonly answered: () => number;
  /** Holds every chat answer until `release()` is called. */
  hold(): void;
  release(): void;
  /** From now on the chat call fails with a 500, so the page shows its error reply. */
  failChat(): void;
}

/** Chat and feedback answers. Anything else falls through to installMockApi's shell fixtures. */
async function mockAskApi(page: Page): Promise<AskMock> {
  let count = 0;
  let failing = false;
  let gate: Promise<void> | null = null;
  let open: () => void = () => {};
  await page.route(/\/api\/v1\/(assistant\/chat|feedback\/turns\/[^/]+)\/?$/, async (route: Route, request) => {
    if (request.method() !== 'POST') return route.fallback();
    const path = new URL(request.url()).pathname;
    const json = (body: unknown) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    if (path.includes('/feedback/turns/')) {
      return json({
        turn_id: path.split('/').filter(Boolean).pop(),
        rating: -1,
        correction_text: null,
        feedback_tags: null,
        created_at: '2026-11-02T10:00:00',
        updated_at: '2026-11-02T10:00:00',
      });
    }
    if (gate) await gate;
    if (failing) {
      return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'fixture failure' }) });
    }
    count += 1;
    return json(chatAnswer(count));
  });
  return {
    answered: () => count,
    hold() {
      gate = new Promise<void>((resolve) => (open = resolve));
    },
    release() {
      gate = null;
      open();
    },
    failChat() {
      failing = true;
    },
  };
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

async function openAsk(page: Page, viewport = DESKTOP) {
  await page.setViewportSize(viewport);
  const mock = await installMockApi(page);
  const ask = await mockAskApi(page);
  await seedMockSession(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  await page.goto('/explain');
  await expect(page.getByPlaceholder('Ask about your results...')).toBeVisible();
  await settle(page);
  return { mock, ask, guard };
}

/** Types a question, sends it and waits for the answer to land. */
async function ask(page: Page, question: string, expectedAnswers: number): Promise<void> {
  await page.getByPlaceholder('Ask about your results...').fill(question);
  await page.getByRole('button', { name: 'Send question' }).click();
  await expect(page.locator('[data-testid="chat-message"][data-role="assistant"]')).toHaveCount(expectedAnswers);
}

/** Sends enough questions that the message list overflows its box. */
async function fillConversation(page: Page, answers = 6): Promise<void> {
  for (let n = 1; n <= answers; n += 1) await ask(page, `Question number ${n} about my cholesterol`, n);
}

const MESSAGE_LIST = (page: Page) => page.getByRole('log', { name: 'Conversation' });

// HC-UIASK-001: sending scrolls only the message list.
for (const [name, viewport] of [
  ['1440', DESKTOP],
  ['390', PHONE],
] as const) {
  test(`HC-UIASK-001: sending scrolls only the message list, not the window (${name})`, async ({ page }) => {
    await openAsk(page, viewport);
    // Make the window scrollable and park it part way down, so a window scroll has room to show. A page that already
    // fits the viewport could not fail this test (the blind spot): the spacer removes that excuse.
    await page.evaluate(() => {
      const spacer = document.createElement('div');
      spacer.id = 'hc-uiask-spacer';
      spacer.style.height = '2400px';
      document.body.appendChild(spacer);
      // The page sets scroll-behavior: smooth on the root; an instant scroll parks it at once.
      window.scrollTo({ top: 120, behavior: 'instant' });
    });
    const parked = await page.evaluate(() => window.scrollY);
    expect(parked, 'the window is parked below the top').toBeGreaterThan(0);

    for (let n = 1; n <= 6; n += 1) {
      await ask(page, `Question number ${n} about my cholesterol`, n);
      // A smooth scrollIntoView takes about half a second to move the window, so wait it out.
      await page.waitForTimeout(700);
      expect(await page.evaluate(() => window.scrollY), `window.scrollY after send ${n}`).toBe(parked);
    }

    // The list itself did scroll: it overflows and sits at its end.
    const list = MESSAGE_LIST(page);
    await expect(list).toBeVisible();
    const box = await list.evaluate((el) => ({ top: el.scrollTop, client: el.clientHeight, height: el.scrollHeight }));
    expect(box.height, 'the list overflows its box').toBeGreaterThan(box.client);
    expect(box.top + box.client, 'the list is scrolled to its end').toBeGreaterThanOrEqual(box.height - 2);
  });
}

// HC-UIASK-002: the disclaimer under the composer is in the viewport without scrolling.
for (const [name, viewport] of [
  ['1440', DESKTOP],
  ['390', PHONE],
] as const) {
  test(`HC-UIASK-002: the disclaimer under the composer is in the viewport without scrolling (${name})`, async ({ page }) => {
    await openAsk(page, viewport);
    const disclaimer = page.getByText(/does not provide medical advice/i);
    const composer = page.getByRole('textbox', { name: 'Your question' });
    await expect(disclaimer).toBeVisible();

    const measured = await page.evaluate(() => {
      const rect = (el: Element | null) => (el ? el.getBoundingClientRect() : null);
      const text = Array.from(document.querySelectorAll('p')).find((p) => /does not provide medical advice/i.test(p.textContent ?? ''));
      const input = document.querySelector('input[aria-label="Your question"]');
      const rail = document.querySelector('[data-safety-rail]');
      return {
        scrollY: window.scrollY,
        innerHeight: window.innerHeight,
        disclaimer: rect(text ?? null),
        composer: rect(input),
        railTop: rect(rail)?.top ?? window.innerHeight,
      };
    });
    expect(measured.disclaimer, 'the disclaimer exists').not.toBeNull();
    expect(measured.composer, 'the composer exists').not.toBeNull();
    const d = measured.disclaimer!;
    const c = measured.composer!;
    expect(d.top, 'the disclaimer is below the composer').toBeGreaterThanOrEqual(c.bottom - 0.5);
    expect(d.top, 'the disclaimer starts inside the viewport').toBeGreaterThanOrEqual(0);
    // Not under the Safety Rail or the tab bar either: its bottom is above the rail's top.
    expect(d.bottom, 'the disclaimer ends above the Safety Rail').toBeLessThanOrEqual(Math.min(measured.innerHeight, measured.railTop) + 0.5);
    await expect(composer).toBeInViewport({ ratio: 1 });
    // And the page did not move to get there: the load itself scrolled it when the list scrolled the window.
    expect(measured.scrollY, 'no scroll happened').toBe(0);
  });
}

// HC-UIASK-003: axe on the three rules, with the page in the state that shows them.
for (const [name, viewport] of [
  ['1440', DESKTOP],
  ['390', PHONE],
] as const) {
  test(`HC-UIASK-003: axe scrollable-region-focusable, label and button-name pass (${name})`, async ({ page }) => {
    await openAsk(page, viewport);
    await fillConversation(page);

    // The list must overflow, or scrollable-region-focusable has nothing to check (a vacuous pass).
    const overflows = await page.evaluate(() => {
      const list = document.querySelector('[role="log"]') ?? document.querySelector('[data-testid="chat-message"]')?.parentElement;
      return list ? list.scrollHeight > list.clientHeight : false;
    });
    expect(overflows, 'the message list overflows its box').toBe(true);

    const wanted = ['scrollable-region-focusable', 'label', 'button-name'];
    const violationsOf = async () =>
      (await axeGate(page)).violations
        .filter((v) => wanted.includes(v.id))
        .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);

    // Step 1: a conversation long enough to scroll.
    expect(await violationsOf(), 'axe violations among the three rules, conversation').toEqual([]);

    // Step 2: thumbs-down opens the tag picker and the correction box: the controls that had no name.
    await page.getByRole('button', { name: 'Not helpful' }).first().click();
    await expect(page.locator('textarea')).toBeVisible();
    expect(await violationsOf(), 'axe violations among the three rules, feedback box open').toEqual([]);
  });
}

// The region the axe rule is about: a list whose replies are errors holds no focusable content (an error reply has no
// feedback buttons and no citations), so only tabindex="0" on the list lets a keyboard user scroll it.
for (const [name, viewport] of [
  ['1440', DESKTOP],
  ['390', PHONE],
] as const) {
  test(`HC-UIASK-003: a message list with no focusable content is itself focusable (${name})`, async ({ page }) => {
    const { ask: chat } = await openAsk(page, viewport);
    chat.failChat();
    await fillConversation(page, 6);

    const overflows = await page.evaluate(() => {
      const list = document.querySelector('[role="log"]') ?? document.querySelector('[data-testid="chat-message"]')?.parentElement;
      return list ? list.scrollHeight > list.clientHeight : false;
    });
    expect(overflows, 'the message list overflows its box').toBe(true);
    expect(await page.locator('[data-testid="chat-message"] button').count(), 'the list holds no button').toBe(0);

    const axe = await axeGate(page);
    expect(
      axe.violations.filter((v) => v.id === 'scrollable-region-focusable').map((v) => v.nodes.map((n) => n.target.join(' ')).join(', ')),
      'scrollable-region-focusable'
    ).toEqual([]);
  });
}

// HC-UIASK-004: a pin for the tier rule. Ask is not a showcase surface.
test('HC-UIASK-004: no canvas and no orb on the page, idle, pending or answered', async ({ page }) => {
  const { ask: chat } = await openAsk(page);
  await expect(page.locator('canvas')).toHaveCount(0);

  chat.hold();
  await page.getByPlaceholder('Ask about your results...').fill('Question while pending');
  await page.getByRole('button', { name: 'Send question' }).click();
  await expect(page.getByText('Question while pending')).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(0);
  chat.release();

  await expect(page.locator('[data-testid="chat-message"][data-role="assistant"]')).toHaveCount(1);
  await expect(page.locator('canvas')).toHaveCount(0);
});

test('UI-PG-ASK: the pending state reads "Reading your verified results…" and nothing else moves', async ({ page }) => {
  const { ask: chat } = await openAsk(page);
  chat.hold();
  await page.getByPlaceholder('Ask about your results...').fill('Question while pending');
  await page.getByRole('button', { name: 'Send question' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Reading your verified results' })).toBeVisible();
  await expect(page.getByText(/searching documents|generating response/i)).toHaveCount(0);
  chat.release();
  await expect(page.getByRole('status').filter({ hasText: 'Reading your verified results' })).toHaveCount(0);
});

// HC-UIASK-005 (G10): the answer's values and citations, from the first sample after they render.
test('HC-UIASK-005: a new answer and its citations pass the stillness probe', async ({ page }) => {
  await openAsk(page);
  await page.getByPlaceholder('Ask about your results...').fill('What is my LDL?');

  const report = await stillnessProbe(page, {
    trigger: () => page.getByRole('button', { name: 'Send question' }).click(),
    expected: [
      '[data-testid="chat-message"][data-role="assistant"] div[data-t0]',
      '[data-testid="chat-message"][data-role="assistant"] button[data-t0]',
      '[data-testid="ask-disclaimer"][data-t0]',
    ],
    kind: 'interaction',
  });
  expect(report.nodes).toBeGreaterThan(0);
  await expect(page.locator('[data-testid="chat-message"][data-role="assistant"]')).toHaveCount(1);
});

test('HC-UIASK-005: a citation popover is still when it opens', async ({ page }) => {
  await openAsk(page);
  await ask(page, 'What is my LDL?', 1);
  const report = await stillnessProbe(page, {
    trigger: () => page.getByRole('button', { name: /^\[1\] Lab report, March/ }).click(),
    expected: ['[role="dialog"] [data-t0]'],
    kind: 'overlay',
  });
  expect(report.nodes).toBeGreaterThan(0);
  await expect(page.getByRole('dialog', { name: /Source 1/ })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog', { name: /Source 1/ })).toHaveCount(0);
});

// The two e2e sides of the citation popover: it opens the quote, and its link opens the Review values page.
test('UI-PG-ASK: a citation chip opens its quote, and Show in source document goes to /verify', async ({ page }) => {
  await openAsk(page);
  await ask(page, 'What is my LDL?', 1);
  await page.getByRole('button', { name: /^\[1\] Lab report, March/ }).click();
  const dialog = page.getByRole('dialog', { name: /Source 1/ });
  await expect(dialog).toContainText('LDL Cholesterol 142 mg/dL');
  await dialog.getByRole('button', { name: 'Show in source document' }).click();
  await expect(page).toHaveURL(/\/verify\?observation=obs-fixture-0001&doc=doc-fixture-0001&page=2$/);
});

// Gate G on /explain. G1, G6, G7 and G9 are not timing measurements; G2, G3, G5 and G10 are (quiet box only).
const THEMES: Theme[] = ['light', 'dark'];

for (const theme of THEMES) {
  test(`UI-PG-ASK GATE G1, G7, G9 on /explain (${theme})`, async ({ page }) => {
    const { mock, guard } = await openAsk(page);

    // G9: the Safety Rail is in view at full opacity at first paint and after the conversation.
    const rail = await safetyVisible(page);
    expect(rail.found && rail.inViewport && rail.effectiveOpacity >= 0.99, `G9 first paint ${JSON.stringify(rail)}`).toBe(true);

    // G1: axe, no serious or critical violations, empty state and then with a conversation and the feedback box open.
    await setTheme(page, theme);
    const empty = await axeGate(page, { theme });
    expect(
      empty.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
      `G1 empty ${theme}`
    ).toEqual([]);

    await fillConversation(page, 3);
    await page.getByRole('button', { name: 'Not helpful' }).first().click();
    await expect(page.locator('textarea')).toBeVisible();
    const full = await axeGate(page, { theme });
    expect(
      full.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
      `G1 conversation ${theme}`
    ).toEqual([]);

    const after = await safetyVisible(page);
    expect(after.found && after.inViewport && after.effectiveOpacity >= 0.99, `G9 after ${JSON.stringify(after)}`).toBe(true);

    // G7: no console error, no non-localhost request, no unmocked API call.
    guard.assertClean();
    expect(mock.unmocked, 'G7 unmocked').toEqual([]);
  });
}

test('UI-PG-ASK GATE G6 on /explain: no horizontal scroll at 390 and 320', async ({ page }) => {
  await openAsk(page, PHONE);
  expect((await noHorizontalScroll(page)).ok, 'G6 390 empty').toBe(true);
  await fillConversation(page, 3);
  expect((await noHorizontalScroll(page)).ok, 'G6 390 conversation').toBe(true);
  await page.setViewportSize(SMALL_PHONE);
  expect((await noHorizontalScroll(page)).ok, 'G6 320 conversation').toBe(true);
});

test('UI-PG-ASK GATE G2, G3, G5 on /explain (quiet box only)', async ({ page }) => {
  await openAsk(page);

  // G2: layout shift over the load and a send.
  const cls = await measureCls(page, async () => {
    await page.goto('/explain');
    await expect(page.getByPlaceholder('Ask about your results...')).toBeVisible();
    await settle(page);
    await ask(page, 'What is my LDL?', 1);
  });
  expect(cls, 'G2 /explain').toBeLessThan(0.1);

  // G3: the worst Event Timing duration of a send, with CPU throttled x4.
  await settle(page);
  const inp = await maxEventDuration(page, () => ask(page, 'Is my LDL high?', 2), { cpuRate: 4 });
  expect(inp, 'G3 /explain').toBeLessThan(200);

  // G5: reduced motion, no element with a transform 50 ms after a send.
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const offenders = await reducedMotionSnapshot(page, () => ask(page, 'And my HDL?', 3));
  expect(offenders, 'G5 /explain').toEqual([]);
});

test('UI-PG-ASK GATE G10 on the navigation to /explain (quiet box only)', async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await installMockApi(page);
  await mockAskApi(page);
  await seedMockSession(page);
  await page.goto('/settings');
  await settle(page);
  const report = await stillnessProbe(page, {
    trigger: () => nav(page, 'Ask').click(),
    expected: ['[data-testid="ask-disclaimer"][data-t0]'],
    kind: 'navigation',
    lazyRoute: true,
  });
  expect(report.nodes).toBeGreaterThan(0);
});
