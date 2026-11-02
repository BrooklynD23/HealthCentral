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

/** The record behind the first citation, as GET /observations/ returns it. */
function observationRow(verified: boolean) {
  return {
    id: 'obs-fixture-0001',
    profile_id: 'profile-fixture',
    doc_id: 'doc-fixture-0001',
    analyte_canonical: 'ldl_cholesterol',
    analyte_raw: 'LDL Cholesterol',
    value: 142,
    value_text: null,
    unit: 'mg/dL',
    ref_low: null,
    ref_high: 100,
    ref_range_text: null,
    flag: 'H',
    is_abnormal: true,
    collected_at: '2026-03-14',
    user_verified: verified,
    extraction_confidence: 0.92,
    source_page: 2,
    source_bbox_json: null,
  };
}

/** What the first citation's text_snippet carries. `quote` is a sentence; `agent` is what the default agent path sends. */
type SnippetShape = { kind: 'quote' } | { kind: 'agent' } | { kind: 'text'; text: string };

/** An answer with an observation-backed citation (it has a deep link) and a reference one (it has none). */
function chatAnswer(n: number, snippet: SnippetShape = { kind: 'quote' }) {
  const firstSnippet =
    snippet.kind === 'agent'
      ? 'obs-fixture-0001'
      : snippet.kind === 'text'
        ? snippet.text
        : 'LDL Cholesterol 142 mg/dL (reference below 100)';
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
            text_snippet: firstSnippet,
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
  /** From now on the chat call fails (500 unless given), so the page shows its error reply. 501 is "no model". */
  failChat(status?: number): void;
  /** From now on the first citation's text_snippet has this shape. */
  snippet(shape: SnippetShape): void;
}

/** Chat and feedback answers. Anything else falls through to installMockApi's shell fixtures. */
async function mockAskApi(page: Page): Promise<AskMock> {
  let count = 0;
  let failing = 0;
  let shape: SnippetShape = { kind: 'quote' };
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
      return route.fulfill({ status: failing, contentType: 'application/json', body: JSON.stringify({ detail: 'fixture failure' }) });
    }
    count += 1;
    return json(chatAnswer(count, shape));
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
    failChat(status = 500) {
      failing = status;
    },
    snippet(next) {
      shape = next;
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

interface OpenOptions {
  /** The record behind citation 1. 'unverified' also shows the page's "Some values are still unverified" banner. */
  observation?: 'verified' | 'unverified' | 'none';
  /** The privacy override is on: the page pins its break-glass warning (W-6 Q3, D12). */
  breakGlass?: boolean;
}

async function openAsk(page: Page, viewport = DESKTOP, options: OpenOptions = {}) {
  await page.setViewportSize(viewport);
  const mock = await installMockApi(page);
  const ask = await mockAskApi(page);
  const { observation = 'verified', breakGlass = false } = options;
  await page.route(/\/api\/v1\/observations\/?(\?.*)?$/, (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    const rows = observation === 'none' ? [] : [observationRow(observation === 'verified')];
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(rows) });
  });
  if (breakGlass) {
    await page.route(/\/api\/v1\/settings\/model\/external-api\/?$/, (route, request) => {
      if (request.method() !== 'GET') return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          use_external_api: true,
          provider: 'openai',
          model: 'gpt-fixture',
          api_key_configured: true,
          redaction_break_glass: true,
        }),
      });
    });
  }
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

// HC-UIASK-002 in the states that take height from the chat card: banners, a phone, a small phone. Nothing in the card
// may be clipped. Where the viewport is too short to show everything at once the card grows and the window scrolls, so
// the composer and the disclaimer are reachable and the message list keeps a usable height.
const LIST_MIN_PX = 120;

interface CardLayout {
  listHeight: number;
  clipped: string[];
  reach: { composerOk: boolean; disclaimerOk: boolean; composerBottom: number; disclaimerBottom: number; limit: number };
  breakGlass: { found: boolean; inList: boolean; top: number; bottom: number; cardTop: number };
}

async function cardLayout(page: Page): Promise<CardLayout> {
  return page.evaluate(() => {
    const list = document.querySelector('[role="log"]') as HTMLElement;
    const input = document.querySelector('input[aria-label="Your question"]') as HTMLElement;
    const text = Array.from(document.querySelectorAll('p')).find((p) => /does not provide medical advice/i.test(p.textContent ?? ''));
    const disclaimer = (text ?? null) as HTMLElement | null;
    const clippedBy = (el: HTMLElement | null): string[] => {
      const found: string[] = [];
      if (!el) return ['missing'];
      const box = el.getBoundingClientRect();
      for (let a = el.parentElement; a && a !== document.documentElement; a = a.parentElement) {
        const cs = getComputedStyle(a);
        if (cs.overflowY === 'visible' && cs.overflowX === 'visible') continue;
        const r = a.getBoundingClientRect();
        if (box.top < r.top - 1 || box.bottom > r.bottom + 1) {
          found.push(`${a.tagName.toLowerCase()}.${String(a.className).split(' ').slice(0, 2).join('.')} clips ${(box.bottom - r.bottom).toFixed(0)}px`);
        }
      }
      return found;
    };
    const clipped = [...clippedBy(input).map((c) => `composer ${c}`), ...clippedBy(disclaimer).map((c) => `disclaimer ${c}`)];

    // Reach it: scroll the window to its end, then both must sit above the Safety Rail / tab bar.
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' });
    const rail = document.querySelector('[data-safety-rail]');
    const limit = Math.min(window.innerHeight, rail ? rail.getBoundingClientRect().top : window.innerHeight);
    const bottomOf = (el: HTMLElement | null) => (el ? el.getBoundingClientRect().bottom : Infinity);
    const topOf = (el: HTMLElement | null) => (el ? el.getBoundingClientRect().top : -Infinity);
    const bg = Array.from(document.querySelectorAll('[role="alert"], [role="status"]')).find((n) =>
      /privacy protection override|Could not confirm this installation/i.test(n.textContent ?? '')
    ) as HTMLElement | undefined;
    const card = list.parentElement as HTMLElement;
    window.scrollTo({ top: 0, behavior: 'instant' });
    return {
      listHeight: list.clientHeight,
      clipped,
      reach: {
        composerOk: topOf(input) >= 0 && bottomOf(input) <= limit + 0.5,
        disclaimerOk: topOf(disclaimer) >= 0 && bottomOf(disclaimer) <= limit + 0.5,
        composerBottom: bottomOf(input),
        disclaimerBottom: bottomOf(disclaimer),
        limit,
      },
      breakGlass: {
        found: Boolean(bg),
        inList: bg ? list.contains(bg) : false,
        top: bg ? bg.getBoundingClientRect().top : 0,
        bottom: bg ? bg.getBoundingClientRect().bottom : 0,
        cardTop: card.getBoundingClientRect().top,
      },
    };
  });
}

const STATES: Array<{
  name: string;
  viewport: { width: number; height: number };
  options: OpenOptions;
  noModel: boolean;
}> = [
  { name: '390x844 unverified values and no model', viewport: PHONE, options: { observation: 'unverified' }, noModel: true },
  { name: '390x844 unverified values and break-glass', viewport: PHONE, options: { observation: 'unverified', breakGlass: true }, noModel: false },
  { name: '390x844 every banner at once', viewport: PHONE, options: { observation: 'unverified', breakGlass: true }, noModel: true },
  { name: '320x640 no banners', viewport: SMALL_PHONE, options: {}, noModel: false },
  { name: '320x640 every banner at once', viewport: SMALL_PHONE, options: { observation: 'unverified', breakGlass: true }, noModel: true },
  { name: '1440x900 every banner at once', viewport: DESKTOP, options: { observation: 'unverified', breakGlass: true }, noModel: true },
];

for (const state of STATES) {
  test(`HC-UIASK-002: nothing in the card is clipped and the list stays usable (${state.name})`, async ({ page }) => {
    const { ask: chat } = await openAsk(page, state.viewport, state.options);
    if (state.noModel) {
      chat.failChat(501);
      await page.getByPlaceholder('Ask about your results...').fill('Is a model set up?');
      await page.getByRole('button', { name: 'Send question' }).click();
      await expect(page.getByText('No AI model configured')).toBeVisible();
    }
    const layout = await cardLayout(page);
    expect(layout.clipped, 'composer or disclaimer clipped by an overflow ancestor').toEqual([]);
    expect(layout.listHeight, 'the message list keeps a usable height').toBeGreaterThanOrEqual(LIST_MIN_PX);
    expect(layout.reach.composerOk, `composer reachable ${JSON.stringify(layout.reach)}`).toBe(true);
    expect(layout.reach.disclaimerOk, `disclaimer reachable ${JSON.stringify(layout.reach)}`).toBe(true);
    if (state.options.breakGlass) {
      // D12: the privacy warning stays pinned in the card, outside the list that scrolls, and in view at the top.
      expect(layout.breakGlass.found, 'the break-glass warning is on the page').toBe(true);
      expect(layout.breakGlass.inList, 'the break-glass warning is not inside the scrolling list').toBe(false);
      await expect(page.getByRole('alert').filter({ hasText: 'Privacy protection override is on' })).toBeInViewport();
    }
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
      '[data-testid="chat-message"][data-role="assistant"] button [data-t0]',
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
    trigger: () => page.getByRole('button', { name: /^Citation 1:/ }).click(),
    expected: ['[role="dialog"] [data-t0]'],
    kind: 'overlay',
  });
  expect(report.nodes).toBeGreaterThan(0);
  await expect(page.getByRole('dialog', { name: 'Citation 1' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog', { name: 'Citation 1' })).toHaveCount(0);
});

// The e2e sides of the citation popover: it opens the quote, and "Open source" opens the Source Trace sheet.
test('UI-PG-ASK: a citation chip opens its quote, and Open source opens the Source Trace sheet', async ({ page }) => {
  await openAsk(page);
  await ask(page, 'What is my LDL?', 1);
  await page.getByRole('button', { name: /^Citation 1:/ }).click();
  const dialog = page.getByRole('dialog', { name: 'Citation 1' });
  await expect(dialog).toContainText('LDL Cholesterol 142 mg/dL');
  await expect(dialog).toContainText('Page 2');
  await dialog.getByRole('button', { name: 'Open source' }).click();
  await expect(page.getByRole('dialog', { name: 'Source for LDL Cholesterol' })).toBeVisible();
  await expect(page.getByRole('dialog', { name: 'Source for LDL Cholesterol' })).toContainText('142 mg/dL');
});

// The default agent path sends row ids where the legacy path sends quotes (recurring failures #1).
test('UI-PG-ASK: an agent-shaped citation shows the record, never its row id', async ({ page }) => {
  const { ask: chat } = await openAsk(page);
  chat.snippet({ kind: 'agent' });
  await ask(page, 'What is my LDL?', 1);
  await page.getByRole('button', { name: /^Citation 1:/ }).click();
  const dialog = page.getByRole('dialog', { name: 'Citation 1' });
  await expect(dialog).toContainText('LDL Cholesterol: 142 mg/dL');
  await expect(dialog.getByRole('button', { name: 'Open source' })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('obs-fixture-0001');
});

// HC-UIPV-004 (DF-2) runs here too (queue SHOWCASE-PROVENANCE-MOVES): every line of the popover wraps.
for (const [name, viewport] of [
  ['1440', DESKTOP],
  ['390', PHONE],
] as const) {
  test(`HC-UIPV-004: a long unbroken quote wraps inside the citation popover (${name})`, async ({ page }) => {
    const { ask: chat } = await openAsk(page, viewport);
    chat.snippet({ kind: 'text', text: 'LDL'.repeat(61) + 'END' });
    await ask(page, 'What is my LDL?', 1);
    await page.getByRole('button', { name: /^Citation 1:/ }).click();
    const dialog = page.getByRole('dialog', { name: 'Citation 1' });
    await expect(dialog).toContainText('LDLLDL');

    const overflow = await dialog.evaluate((root) => {
      const vw = document.documentElement.clientWidth;
      const rect = root.getBoundingClientRect();
      const wide = [root, ...Array.from(root.querySelectorAll('*'))]
        .filter((el) => el.scrollWidth > el.clientWidth + 1)
        .map((el) => `${el.tagName.toLowerCase()} ${el.scrollWidth}>${el.clientWidth}`);
      return { wide, left: rect.left, right: rect.right, vw };
    });
    expect(overflow.wide, 'every element in the popover wraps (scrollWidth <= clientWidth)').toEqual([]);
    expect(overflow.left, 'the popover starts inside the screen').toBeGreaterThanOrEqual(0);
    expect(overflow.right, 'the popover ends inside the screen').toBeLessThanOrEqual(overflow.vw + 0.5);
    expect((await noHorizontalScroll(page)).ok, 'no horizontal page scroll').toBe(true);
  });
}

// M6 has to finish: vitest sees only the first frame, and toBeVisible passes at opacity .35.
test('UI-PG-ASK: the patient\u2019s own message finishes M6 at full opacity and no transform', async ({ page }) => {
  await openAsk(page);
  await page.getByPlaceholder('Ask about your results...').fill('A question of my own');
  await page.getByRole('button', { name: 'Send question' }).click();
  const own = page.locator('[data-testid="chat-message"][data-role="user"]').last();
  await expect(own).toContainText('A question of my own');
  await expect
    .poll(() => own.evaluate((el) => ({ opacity: getComputedStyle(el).opacity, transform: getComputedStyle(el).transform })), {
      timeout: 3000,
    })
    .toEqual({ opacity: '1', transform: 'none' });
});

// G10 read for a list that is already full: the new answer is still from its first frame. The list scrolling itself
// moves the OLDER answers, which stillnessProbe would count; this samples the new answer only (the probe's scoping of
// nodes moved by the list's own scroll is an open L0 question).
test('HC-UIASK-005: in a full list the new answer is still from its first frame', async ({ page }) => {
  await openAsk(page);
  await fillConversation(page, 6);
  await page.evaluate(() => {
    const w = window as unknown as { __askSamples: string[]; __askStop: () => void };
    w.__askSamples = [];
    const count = () => document.querySelectorAll('[data-testid="chat-message"][data-role="assistant"]').length;
    const before = count();
    let raf = 0;
    const sample = () => {
      const messages = document.querySelectorAll('[data-testid="chat-message"][data-role="assistant"]');
      const fresh = messages.length > before ? messages[messages.length - 1] : null;
      if (fresh) {
        w.__askSamples.push(
          Array.from(fresh.querySelectorAll('[data-t0]'))
            .map((el) => {
              const r = el.getBoundingClientRect();
              return `${el.tagName}|${[r.x, r.y, r.width, r.height].map((v) => v.toFixed(1)).join(',')}|${getComputedStyle(el).transform}|${el.textContent}`;
            })
            .join('\n')
        );
      }
      raf = requestAnimationFrame(sample);
    };
    raf = requestAnimationFrame(sample);
    w.__askStop = () => cancelAnimationFrame(raf);
  });
  await ask(page, 'And one more question about my LDL?', 7);
  await page.waitForTimeout(900);
  const samples = await page.evaluate(() => {
    const w = window as unknown as { __askSamples: string[]; __askStop: () => void };
    w.__askStop();
    return w.__askSamples;
  });
  expect(samples.length, 'the new answer was sampled').toBeGreaterThan(5);
  expect(new Set(samples).size, 'the new answer\u2019s T0 nodes are identical in every sample').toBe(1);
  expect(samples[0]).toContain('(answer 7)');
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
