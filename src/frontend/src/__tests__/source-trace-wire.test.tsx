/**
 * SOURCE-TRACE-WIRE vitest halves: HC-STW-001 ("Show source" on the interpreted
 * result card), HC-STW-002 (no request before the click; the sheet shows the file,
 * the page and the matching line after it), HC-STW-003 (excerptFromPage table),
 * HC-STW-004 (Escape closes the sheet and focus returns to "Show source").
 * HC-STW-005 (the same path in a browser) is Playwright, in e2e/ui-provenance.spec.ts.
 * HC-STW-006 to 008 (review round 1, finding 2): "It matches, mark as checked" is enabled
 * only while an excerpt is on screen and both GETs have resolved; the reason is visible
 * when it is not; HC-STW-009 (the same on /interpret) is Playwright.
 * HC-STW-014 (each "not available" sentence follows its own GET; loading says so) and HC-STW-015
 * (the sheet's min-h-[85dvh] and scrollbar-gutter classes): the round 3 escalation, ruling 6591279713.
 *
 * Plan: docs/plans/2026-10-30-followups-plan.md, "SOURCE-TRACE-WIRE".
 *
 * HTTP is stubbed at `fetch`, never by mocking '@/services/documents', so a wrong URL
 * fails the test (recurring-failures #1): an unknown URL is answered with 500.
 *
 * excerptFromPage is imported at run time, so a missing export fails only the ids that
 * need it and the RED run names each id (the ui-provenance.test.tsx pattern).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { InterpretedResultCard } from '@/components/lab-interpreter/InterpretedResultCard';
import type { DocumentPage, InterpretationResponse, Observation } from '@/services/types';

/** Loads a module at run time (variable specifier, so a missing export fails one test). */
async function load<T>(specifier: string): Promise<T> {
  return (await import(/* @vite-ignore */ specifier)) as T;
}

const DOC_ID = 'doc-1';
const OBSERVATION_ID = '6f1c2c4e-8a1b-4c3d-9e0f-123456789abc';

const observation: Observation = {
  id: OBSERVATION_ID,
  profile_id: 'profile-1',
  doc_id: DOC_ID,
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
  source_bbox_json: '[10,20,200,40]',
};

const interpretation: InterpretationResponse = {
  id: 'interp-1',
  observation_id: OBSERVATION_ID,
  interpretation_text: 'Your fasting glucose is within the reference range for this test.',
  severity_level: 'normal',
  advice_text: null,
  citations: [
    { type: 'knowledge_base', id: 'kb-glucose-1', text: 'Fasting glucose between 70 and 99 mg/dL is usual.' },
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

const MATCH_LINE = 'Glucose 96 mg/dL 70-99';
const PAGE_THREE_TEXT = ['Comprehensive Metabolic Panel', MATCH_LINE, 'Sodium 140 mmol/L 136-145'].join('\n');

const documentBody = {
  id: DOC_ID,
  profile_id: 'profile-1',
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

function pagesBody(page3Text: string): DocumentPage[] {
  return [
    { page_number: 1, text: 'Cover page', has_tables: false },
    { page_number: 3, text: page3Text, has_tables: false },
  ];
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function pathOf(input: RequestInfo | URL): string {
  return new URL(String(input), 'http://localhost').pathname.replace(/^.*\/api\/v1/, '');
}

type FetchMock = ReturnType<typeof stubFetch>;

/** Answers the two document routes; any other URL is a 500, so a wrong URL fails the test. */
function stubFetch(page3Text: string = PAGE_THREE_TEXT) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const path = pathOf(input);
    if (path === `/documents/${DOC_ID}`) return jsonResponse(documentBody);
    if (path === `/documents/${DOC_ID}/pages`) return jsonResponse(pagesBody(page3Text));
    return jsonResponse({ detail: `not stubbed: ${path}` }, 500);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function requestsTo(fetchMock: FetchMock, suffix: string): string[] {
  return fetchMock.mock.calls.map(([input]) => pathOf(input)).filter((path) => path.endsWith(suffix));
}

function renderCard(props: Partial<React.ComponentProps<typeof InterpretedResultCard>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <InterpretedResultCard
          interpretation={interpretation}
          analyteName="Glucose"
          value={96}
          unit="mg/dL"
          refLow={70}
          refHigh={99}
          {...props}
        />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

const SHOW_SOURCE = { name: 'Show source' };

beforeEach(() => {
  stubFetch();
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('HC-STW-001 the interpreted result card offers "Show source" only for a value with a document', () => {
  it('HC-STW-001 shows a "Show source" button when the observation has a doc_id', () => {
    renderCard({ observation });
    expect(screen.getByRole('button', SHOW_SOURCE)).not.toBeNull();
  });

  it('HC-STW-001 shows it next to the citation chips, and also when the interpretation has no citations', () => {
    const { unmount } = renderCard({ observation });
    const chip = screen.getByRole('button', { name: /^Citation 1: / });
    expect(screen.getByRole('button', SHOW_SOURCE).parentElement).toBe(chip.parentElement);
    // The row holds the button as well as up to 6 chips, so it wraps rather than shrinking the 44 px chips.
    expect(chip.parentElement?.className).toContain('flex-wrap');
    unmount();

    renderCard({ observation, interpretation: { ...interpretation, citations: [] } });
    expect(screen.queryByRole('button', { name: /^Citation 1: / })).toBeNull();
    expect(screen.getByRole('button', SHOW_SOURCE)).not.toBeNull();
  });

  it('HC-STW-001 shows none without an observation, or with a null doc_id', () => {
    const { unmount } = renderCard();
    expect(screen.queryByRole('button', SHOW_SOURCE)).toBeNull();
    unmount();

    // Observation.doc_id is typed string; a stored row can still carry null.
    renderCard({ observation: { ...observation, doc_id: null as unknown as string } });
    expect(screen.queryByRole('button', SHOW_SOURCE)).toBeNull();
  });

  it('HC-STW-001 leaves the interpretation text, advice, badges and citations identical with and without the observation', () => {
    const rich: InterpretationResponse = {
      ...interpretation,
      severity_level: 'moderate',
      advice_text: 'Ask your clinician about a repeat test.',
      requires_physician_review: true,
      physician_review_reason: 'Please review this result with your clinician.',
    };
    const { container, unmount } = renderCard({ interpretation: rich });
    const without = container.textContent;
    const withoutButtons = screen.getAllByRole('button').map((b) => b.textContent);
    unmount();

    const { container: container2 } = renderCard({ interpretation: rich, observation });
    const withObservation = container2.textContent;
    const withButtons = screen.getAllByRole('button').map((b) => b.textContent);

    // The only addition is the button's own label.
    expect(withObservation?.replace('Show source', '')).toBe(without);
    expect(withButtons.filter((label) => label !== 'Show source')).toEqual(withoutButtons);
    // The interpretation paragraph itself, read on its own.
    expect(screen.getByText(rich.interpretation_text).textContent).toBe(rich.interpretation_text);
  });
});

describe('HC-STW-002 the document is fetched only after the click, and the sheet shows the file, the page and the line', () => {
  it('HC-STW-002 makes no document request on first paint', async () => {
    const fetchMock = stubFetch();
    renderCard({ observation });
    // Let any query that was going to start, start.
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(screen.getByRole('button', SHOW_SOURCE)).not.toBeNull();
    expect(requestsTo(fetchMock, `/documents/${DOC_ID}`)).toEqual([]);
    expect(requestsTo(fetchMock, `/documents/${DOC_ID}/pages`)).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('HC-STW-002 after the click, the dialog shows the file name, Page 3 and the matching line, with GET requests only', async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch();
    renderCard({ observation });

    await user.click(screen.getByRole('button', SHOW_SOURCE));
    const dialog = await screen.findByRole('dialog', { name: 'Source for Glucose' });

    expect(await within(dialog).findByText('provenance-report.pdf')).not.toBeNull();
    expect(within(dialog).getByText('Page 3')).not.toBeNull();
    const matchRow = await within(dialog).findByText(MATCH_LINE);
    expect(matchRow.closest('li')?.textContent).toContain('Matching line:');
    expect(within(dialog).getByText('Comprehensive Metabolic Panel').closest('li')?.textContent).not.toContain(
      'Matching line:'
    );
    expect(within(dialog).getByText('This is what your report states.')).not.toBeNull();

    expect(requestsTo(fetchMock, `/documents/${DOC_ID}`)).toHaveLength(1);
    expect(requestsTo(fetchMock, `/documents/${DOC_ID}/pages`)).toHaveLength(1);
    // Read-only: opening the sheet must not send a verify POST or any other write.
    const nonGet = fetchMock.mock.calls.filter(([, init]) => (init?.method ?? 'GET') !== 'GET');
    expect(nonGet).toEqual([]);
    // Nothing else was requested: every call was one of the two document routes.
    expect(fetchMock.mock.calls.map(([input]) => pathOf(input)).sort()).toEqual([
      `/documents/${DOC_ID}`,
      `/documents/${DOC_ID}/pages`,
    ]);
  });

  it('HC-STW-002 says "Excerpt not available." and still shows the file and page when no single line matches', async () => {
    const user = userEvent.setup();
    stubFetch('Comprehensive Metabolic Panel\nSodium 140 mmol/L 136-145');
    renderCard({ observation });

    await user.click(screen.getByRole('button', SHOW_SOURCE));
    const dialog = await screen.findByRole('dialog', { name: 'Source for Glucose' });

    expect(await within(dialog).findByText('provenance-report.pdf')).not.toBeNull();
    expect(within(dialog).getByText('Page 3')).not.toBeNull();
    expect(await within(dialog).findByText('Excerpt not available.')).not.toBeNull();
    expect(within(dialog).queryByText(/Matching line:/)).toBeNull();
  });

  // The file name comes from GET /documents/<id> and the excerpt from GET /documents/<id>/pages, so each
  // failure removes only its own half: a failed document GET leaves the excerpt, a failed pages GET leaves the file.
  it.each([
    ['the document GET fails with 500', 500, 200, 'Source file not available', true],
    ['the pages GET fails with 404', 200, 404, 'provenance-report.pdf', false],
    ['both GETs fail', 404, 500, 'Source file not available', false],
  ])(
    'HC-STW-002 the sheet stays open and highlights nothing it cannot find when %s',
    async (_label, documentStatus, pagesStatus, fileText, excerptShown) => {
      const user = userEvent.setup();
      const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
        const path = pathOf(input);
        if (path === `/documents/${DOC_ID}`) {
          return jsonResponse(documentStatus === 200 ? documentBody : { detail: 'failed' }, documentStatus);
        }
        if (path === `/documents/${DOC_ID}/pages`) {
          return jsonResponse(pagesStatus === 200 ? pagesBody(PAGE_THREE_TEXT) : { detail: 'failed' }, pagesStatus);
        }
        return jsonResponse({ detail: `not stubbed: ${path}` }, 500);
      });
      vi.stubGlobal('fetch', fetchMock);
      renderCard({ observation });

      await user.click(screen.getByRole('button', SHOW_SOURCE));
      const dialog = await screen.findByRole('dialog', { name: 'Source for Glucose' });

      // Both requests were answered before the settled sheet is read.
      await waitFor(() => {
        expect(requestsTo(fetchMock, `/documents/${DOC_ID}`)).toHaveLength(1);
        expect(requestsTo(fetchMock, `/documents/${DOC_ID}/pages`)).toHaveLength(1);
      });
      expect(await within(dialog).findByText(fileText)).not.toBeNull();
      expect(within(dialog).getByText('Page 3')).not.toBeNull();
      if (excerptShown) {
        expect((await within(dialog).findByText(MATCH_LINE)).closest('li')?.textContent).toContain('Matching line:');
        expect(within(dialog).queryByText('Excerpt not available.')).toBeNull();
      } else {
        expect(await within(dialog).findByText('Excerpt not available.')).not.toBeNull();
        expect(within(dialog).queryByText(/Matching line:/)).toBeNull();
        expect(within(dialog).queryByText(MATCH_LINE)).toBeNull();
      }
      // Still open once the failures have settled.
      expect(screen.getByRole('dialog', { name: 'Source for Glucose' })).toBe(dialog);
    }
  );
});

describe('HC-STW-003 excerptFromPage matches one whole-token line or nothing', () => {
  type Excerpt = { excerptLines: string[]; matchIndex: number | null };
  type ExcerptFn = (pages: readonly DocumentPage[] | undefined, observation: Observation) => Excerpt;

  const NONE: Excerpt = { excerptLines: [], matchIndex: null };

  async function excerpt(text: string, overrides: Partial<Observation> = {}): Promise<Excerpt> {
    const { excerptFromPage } = await load<{ excerptFromPage: ExcerptFn }>('@/components/results/SourceTrace');
    return excerptFromPage(pagesBody(text), { ...observation, ...overrides });
  }

  it('HC-STW-003 one match gives that line and up to 2 lines either side, with matchIndex into the excerpt', async () => {
    const lines = ['l0', 'l1', 'l2', 'l3', MATCH_LINE, 'l5', 'l6', 'l7', 'l8'];
    expect(await excerpt(lines.join('\n'))).toEqual({
      excerptLines: ['l2', 'l3', MATCH_LINE, 'l5', 'l6'],
      matchIndex: 2,
    });
  });

  it('HC-STW-003 splits on CRLF as well as LF', async () => {
    expect(await excerpt(['Panel', MATCH_LINE, 'Sodium 140'].join('\r\n'))).toEqual({
      excerptLines: ['Panel', MATCH_LINE, 'Sodium 140'],
      matchIndex: 1,
    });
  });

  it('HC-STW-003 a match on the first line clips the window and gives matchIndex 0', async () => {
    expect(await excerpt([MATCH_LINE, 'a', 'b', 'c'].join('\n'))).toEqual({
      excerptLines: [MATCH_LINE, 'a', 'b'],
      matchIndex: 0,
    });
  });

  it('HC-STW-003 a match on the last line clips the window at the bottom', async () => {
    expect(await excerpt(['a', 'b', 'c', MATCH_LINE].join('\n'))).toEqual({
      excerptLines: ['b', 'c', MATCH_LINE],
      matchIndex: 2,
    });
  });

  it('HC-STW-003 the analyte is matched case-insensitively', async () => {
    expect(await excerpt('GLUCOSE 96 mg/dL 70-99')).toEqual({
      excerptLines: ['GLUCOSE 96 mg/dL 70-99'],
      matchIndex: 0,
    });
  });

  it('HC-STW-003 no matching line gives none', async () => {
    expect(await excerpt('Panel\nSodium 140 mmol/L 136-145')).toEqual(NONE);
  });

  it('HC-STW-003 two matching lines give none: nothing is guessed', async () => {
    expect(await excerpt(`${MATCH_LINE}\nPanel\nfasting ${MATCH_LINE}`)).toEqual(NONE);
  });

  it('HC-STW-003 the analyte without the value gives none', async () => {
    expect(await excerpt('Glucose 101 mg/dL 70-99')).toEqual(NONE);
  });

  it('HC-STW-003 the value without the analyte gives none', async () => {
    expect(await excerpt('Sodium 96 mmol/L')).toEqual(NONE);
  });

  it('HC-STW-003 the value is a whole token: 196, 96.5 and -96 do not match 96', async () => {
    expect(await excerpt('Glucose 196 mg/dL')).toEqual(NONE);
    expect(await excerpt('Glucose 96.5 mg/dL')).toEqual(NONE);
    expect(await excerpt('Glucose -96 mg/dL')).toEqual(NONE);
  });

  it('HC-STW-003 the reference-range column is not the value: 70-99 matches neither 99 nor 70', async () => {
    expect(await excerpt('Glucose 101 mg/dL 70-99', { value: 99 })).toEqual(NONE);
    expect(await excerpt('Glucose 101 mg/dL 70-99', { value: 70 })).toEqual(NONE);
  });

  it('HC-STW-003 value null with value_text matches the text token', async () => {
    expect(await excerpt('Panel\nGlucose Positive mg/dL', { value: null, value_text: 'Positive' })).toEqual({
      excerptLines: ['Panel', 'Glucose Positive mg/dL'],
      matchIndex: 1,
    });
  });

  it('HC-STW-003 value_text with a regex metacharacter is matched literally', async () => {
    const overrides = { value: null, value_text: '<5.0' };
    expect(await excerpt('Glucose <5.0 mg/dL', overrides)).toEqual({
      excerptLines: ['Glucose <5.0 mg/dL'],
      matchIndex: 0,
    });
    // "." is not a wildcard: "<5x0" must not match "<5.0".
    expect(await excerpt('Glucose <5x0 mg/dL', overrides)).toEqual(NONE);
  });

  it('HC-STW-003 an empty analyte_raw gives none, not every line', async () => {
    expect(await excerpt('Glucose 96 mg/dL\nSodium 96', { analyte_raw: '' })).toEqual(NONE);
  });

  it('HC-STW-003 an empty value_text with a null value gives none, not every line', async () => {
    expect(await excerpt('Glucose 96 mg/dL', { value: null, value_text: '' })).toEqual(NONE);
    expect(await excerpt('Glucose 96 mg/dL', { value: null, value_text: null })).toEqual(NONE);
  });

  it('HC-STW-003 source_page null gives none', async () => {
    expect(await excerpt(MATCH_LINE, { source_page: null })).toEqual(NONE);
  });

  it('HC-STW-003 a source_page with no such page gives none', async () => {
    expect(await excerpt(MATCH_LINE, { source_page: 2 })).toEqual(NONE);
  });

  it('HC-STW-003 no pages at all gives none', async () => {
    const { excerptFromPage } = await load<{ excerptFromPage: ExcerptFn }>('@/components/results/SourceTrace');
    expect(excerptFromPage(undefined, observation)).toEqual(NONE);
    expect(excerptFromPage([], observation)).toEqual(NONE);
  });

  it('HC-STW-003 reads the page named by source_page, not another page that also matches', async () => {
    const { excerptFromPage } = await load<{ excerptFromPage: ExcerptFn }>('@/components/results/SourceTrace');
    const pages: DocumentPage[] = [
      { page_number: 1, text: 'Glucose 96 mg/dL', has_tables: false },
      { page_number: 3, text: 'Panel\nGlucose 96 mg/dL', has_tables: false },
    ];
    expect(excerptFromPage(pages, observation)).toEqual({
      excerptLines: ['Panel', 'Glucose 96 mg/dL'],
      matchIndex: 1,
    });
  });
});

describe('HC-STW-004 Escape closes the sheet and focus returns to "Show source"', () => {
  it('HC-STW-004 returns focus to the button that opened the sheet', async () => {
    const user = userEvent.setup();
    renderCard({ observation });
    const button = screen.getByRole('button', SHOW_SOURCE);

    await user.click(button);
    await screen.findByRole('dialog', { name: 'Source for Glucose' });

    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Source for Glucose' })).toBeNull();
    });
    expect(document.activeElement).toBe(screen.getByRole('button', SHOW_SOURCE));
    expect(document.activeElement).toBe(button);
  });

  it('HC-STW-004 opens with Enter from the keyboard and closes with Escape', async () => {
    const user = userEvent.setup();
    renderCard({ observation });
    const button = screen.getByRole('button', SHOW_SOURCE);

    button.focus();
    await user.keyboard('{Enter}');
    await screen.findByRole('dialog', { name: 'Source for Glucose' });
    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Source for Glucose' })).toBeNull();
    });
    expect(document.activeElement).toBe(button);
  });
});

// ---------------------------------------------------------------------------
// HC-STW-006 to 008: "It matches, mark as checked" needs the source on screen.
// ---------------------------------------------------------------------------
const MARK_BUTTON = { name: 'It matches, mark as checked' };
const LOADING_REASON = 'Loading the source to compare.';
const UNAVAILABLE_REASON = 'The source is not available to compare, so this cannot be marked here.';
const VERIFY_PATH = `/observations/${OBSERVATION_ID}/verify`;
const MARKED_TEXT = 'You have marked this value as checked.';

type GetPlan = 'ok' | 'hold' | 'fail' | 'no-match' | 'null-source';
const gates: Array<() => void> = [];

/**
 * Like stubFetch, with a plan per GET: 'hold' leaves it pending until afterEach, 'fail' answers
 * 500 (document) or 404 (pages), 'no-match' serves a page with no matching line, 'null-source'
 * serves a document whose source is null. POST /observations/<id>/verify is answered here, so
 * a click that should not have sent one is caught by the recorded calls, not by a 500.
 */
function stubSheetFetch(plan: { document?: GetPlan; pages?: GetPlan } = {}) {
  const hold = () =>
    new Promise<void>((resolve) => {
      gates.push(resolve);
    });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = pathOf(input);
    const method = init?.method ?? 'GET';
    if (method === 'POST' && path === VERIFY_PATH) return jsonResponse({ ...observation, user_verified: true });
    if (method === 'GET' && path === `/documents/${DOC_ID}`) {
      if (plan.document === 'hold') await hold();
      if (plan.document === 'fail') return jsonResponse({ detail: 'failed' }, 500);
      if (plan.document === 'null-source') return jsonResponse({ ...documentBody, source: null });
      return jsonResponse(documentBody);
    }
    if (method === 'GET' && path === `/documents/${DOC_ID}/pages`) {
      if (plan.pages === 'hold') await hold();
      if (plan.pages === 'fail') return jsonResponse({ detail: 'failed' }, 404);
      if (plan.pages === 'no-match') return jsonResponse(pagesBody('Panel\nSodium 140 mmol/L 136-145'));
      return jsonResponse(pagesBody(PAGE_THREE_TEXT));
    }
    return jsonResponse({ detail: `not stubbed: ${method} ${path}` }, 500);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function nonGetCalls(fetchMock: FetchMock) {
  return fetchMock.mock.calls.filter(([, init]) => (init?.method ?? 'GET') !== 'GET');
}

async function openSheet(sheetObservation: Observation = observation) {
  const user = userEvent.setup();
  renderCard({ observation: sheetObservation });
  await user.click(screen.getByRole('button', SHOW_SOURCE));
  const dialog = await screen.findByRole('dialog', { name: 'Source for Glucose' });
  return { user, dialog };
}

async function bothGetsRequested(fetchMock: FetchMock) {
  await waitFor(() => {
    expect(requestsTo(fetchMock, `/documents/${DOC_ID}`)).toHaveLength(1);
    expect(requestsTo(fetchMock, `/documents/${DOC_ID}/pages`)).toHaveLength(1);
  });
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 50));

afterEach(() => {
  gates.splice(0).forEach((release) => release());
});

describe('HC-STW-006 "It matches, mark as checked" is disabled, with a visible reason, until the source is on screen', () => {
  // Held GETs: the document pending with the pages resolved has the excerpt ON SCREEN, so a rule that
  // looks only at the excerpt would leave the button enabled here.
  it.each<[string, { document?: GetPlan; pages?: GetPlan }, (dialog: HTMLElement, fetchMock: FetchMock) => Promise<unknown>]>([
    [
      'the document GET is pending and the excerpt is already on screen',
      { document: 'hold' },
      (dialog) => within(dialog).findByText(MATCH_LINE),
    ],
    [
      'the pages GET is pending and the file name is already on screen',
      { pages: 'hold' },
      (dialog) => within(dialog).findByText('provenance-report.pdf'),
    ],
    ['both GETs are pending', { document: 'hold', pages: 'hold' }, (_dialog, fetchMock) => bothGetsRequested(fetchMock)],
  ])('HC-STW-006 is disabled with the loading reason while %s', async (_label, plan, untilShown) => {
    const fetchMock = stubSheetFetch(plan);
    const { user, dialog } = await openSheet();
    await untilShown(dialog, fetchMock);
    await bothGetsRequested(fetchMock);

    const button = within(dialog).getByRole('button', MARK_BUTTON) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    const reason = within(dialog).getByText(LOADING_REASON);
    expect(button.getAttribute('aria-describedby')).toBe(reason.id);
    expect(reason.id).not.toBe('');
    expect(within(dialog).queryByText(UNAVAILABLE_REASON)).toBeNull();

    await user.click(button);
    await settle();
    expect(nonGetCalls(fetchMock)).toEqual([]);
  });

  it.each<[string, { document?: GetPlan; pages?: GetPlan }]>([
    ['the document GET fails with 500 (the excerpt is on screen)', { document: 'fail' }],
    ['the pages GET fails with 404', { pages: 'fail' }],
    ['both GETs fail', { document: 'fail', pages: 'fail' }],
    ['both GETs succeed but no line matches', { pages: 'no-match' }],
    ['the document GET succeeds with source null (the excerpt is on screen)', { document: 'null-source' }],
  ])('HC-STW-006 is disabled with the unavailable reason, and a click sends no POST, when %s', async (_label, plan) => {
    const fetchMock = stubSheetFetch(plan);
    const { user, dialog } = await openSheet();
    await bothGetsRequested(fetchMock);

    // The reason names the settled state, so both GETs have resolved when it appears.
    const reason = await within(dialog).findByText(UNAVAILABLE_REASON);
    const button = within(dialog).getByRole('button', MARK_BUTTON) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.getAttribute('aria-describedby')).toBe(reason.id);
    expect(reason.id).not.toBe('');
    expect(within(dialog).queryByText(LOADING_REASON)).toBeNull();
    // The way out stays available in every state.
    expect(within(dialog).getByRole('link', { name: 'Correct it in Review values' })).not.toBeNull();

    await user.click(button);
    await settle();
    expect(nonGetCalls(fetchMock)).toEqual([]);
  });
});

describe('HC-STW-007 with the source on screen the button is enabled and one click sends one verify POST', () => {
  it('HC-STW-007 shows no reason, is enabled, and one click sends exactly one POST with body {} and leaves the card text alone', async () => {
    const fetchMock = stubSheetFetch();
    const { user, dialog } = await openSheet();
    await bothGetsRequested(fetchMock);
    expect((await within(dialog).findByText(MATCH_LINE)).closest('li')?.textContent).toContain('Matching line:');
    expect(await within(dialog).findByText('provenance-report.pdf')).not.toBeNull();

    const button = within(dialog).getByRole('button', MARK_BUTTON) as HTMLButtonElement;
    expect(button.disabled).toBe(false);
    expect(within(dialog).queryByText(LOADING_REASON)).toBeNull();
    expect(within(dialog).queryByText(UNAVAILABLE_REASON)).toBeNull();
    expect(button.getAttribute('aria-describedby')).toBeNull();

    // The card sits behind the dialog (aria-hidden), so it is read by text, not by role.
    const textBefore = screen.getByText(interpretation.interpretation_text).textContent;
    expect(textBefore).toBe(interpretation.interpretation_text);

    await user.click(button);
    expect(await within(dialog).findByText(MARKED_TEXT)).not.toBeNull();
    await settle();

    const posts = nonGetCalls(fetchMock);
    expect(posts.map(([input, init]) => `${init?.method} ${pathOf(input)}`)).toEqual([`POST ${VERIFY_PATH}`]);
    expect(posts[0][1]?.body).toBe('{}');
    expect(screen.getByText(interpretation.interpretation_text).textContent).toBe(textBefore);
    expect(within(dialog).queryByRole('button', MARK_BUTTON)).toBeNull();
  });

  it('HC-STW-007 opening the sheet sends no POST, with the source on screen', async () => {
    const fetchMock = stubSheetFetch();
    const { dialog } = await openSheet();
    await bothGetsRequested(fetchMock);
    await within(dialog).findByText(MATCH_LINE);
    await settle();

    expect((within(dialog).getByRole('button', MARK_BUTTON) as HTMLButtonElement).disabled).toBe(false);
    expect(nonGetCalls(fetchMock)).toEqual([]);
  });

  it('HC-STW-007 opening the sheet sends no POST, with the source unavailable', async () => {
    const fetchMock = stubSheetFetch({ document: 'fail', pages: 'fail' });
    const { dialog } = await openSheet();
    await bothGetsRequested(fetchMock);
    // Both texts are the settled wording: they appear only once the failed GETs have been answered.
    await within(dialog).findByText('Source file not available');
    await within(dialog).findByText('Excerpt not available.');
    await settle();

    expect(nonGetCalls(fetchMock)).toEqual([]);
  });

  // Regression pin: true at head 7cb75d1b already (an already-checked value never showed the button).
  it('HC-STW-007 an already verified value shows no button and no reason', async () => {
    const fetchMock = stubSheetFetch({ pages: 'no-match' });
    const { dialog } = await openSheet({ ...observation, user_verified: true });
    await bothGetsRequested(fetchMock);
    await within(dialog).findByText('Excerpt not available.');
    await settle();

    expect(within(dialog).getByText(MARKED_TEXT)).not.toBeNull();
    expect(within(dialog).queryByRole('button', MARK_BUTTON)).toBeNull();
    expect(within(dialog).queryByText(LOADING_REASON)).toBeNull();
    expect(within(dialog).queryByText(UNAVAILABLE_REASON)).toBeNull();
  });
});

describe('HC-STW-008 "This is what your report states." is shown only with an excerpt', () => {
  const REPORT_STATES = 'This is what your report states.';

  it('HC-STW-008 is present with an excerpt', async () => {
    const fetchMock = stubSheetFetch();
    const { dialog } = await openSheet();
    await bothGetsRequested(fetchMock);
    await within(dialog).findByText(MATCH_LINE);
    expect(within(dialog).getByText(REPORT_STATES)).not.toBeNull();
  });

  it('HC-STW-008 is absent under "Excerpt not available."', async () => {
    const fetchMock = stubSheetFetch({ pages: 'no-match' });
    const { dialog } = await openSheet();
    await bothGetsRequested(fetchMock);
    expect(await within(dialog).findByText('provenance-report.pdf')).not.toBeNull();
    await settle();
    expect(within(dialog).getByText('Excerpt not available.')).not.toBeNull();
    expect(within(dialog).queryByText(REPORT_STATES)).toBeNull();
  });

  it('HC-STW-008 is absent while loading, which says "Loading the excerpt…" and not "Excerpt not available."', async () => {
    const fetchMock = stubSheetFetch({ document: 'hold', pages: 'hold' });
    const { dialog } = await openSheet();
    await bothGetsRequested(fetchMock);
    await settle();
    expect(within(dialog).getByText('Loading the excerpt…')).not.toBeNull();
    expect(within(dialog).queryByText('Excerpt not available.')).toBeNull();
    expect(within(dialog).queryByText(REPORT_STATES)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// HC-STW-014 / 015: review round 3 escalation (ruling 6591279713).
// ---------------------------------------------------------------------------
describe('HC-STW-014 each of the two "not available" sentences follows its own GET, and loading says so', () => {
  const FILE_LOADING = 'Loading the file name…';
  const EXCERPT_LOADING = 'Loading the excerpt…';
  const FILE_UNAVAILABLE = 'Source file not available';
  const EXCERPT_UNAVAILABLE = 'Excerpt not available.';
  const FILE_NAME = 'provenance-report.pdf';

  // One status for both GETs cannot do this: a failed document GET with the pages GET still pending
  // must read "Loading the excerpt…", not the false "Excerpt not available.".
  it.each<[GetPlan, GetPlan, string, string]>([
    ['hold', 'hold', FILE_LOADING, EXCERPT_LOADING],
    ['ok', 'hold', FILE_NAME, EXCERPT_LOADING],
    ['null-source', 'hold', FILE_UNAVAILABLE, EXCERPT_LOADING],
    ['fail', 'hold', FILE_UNAVAILABLE, EXCERPT_LOADING],
    ['hold', 'ok', FILE_LOADING, MATCH_LINE],
    ['hold', 'no-match', FILE_LOADING, EXCERPT_UNAVAILABLE],
    ['hold', 'fail', FILE_LOADING, EXCERPT_UNAVAILABLE],
  ])(
    'HC-STW-014 document %s, pages %s: File shows "%s", the excerpt area shows "%s"',
    async (documentPlan, pagesPlan, fileShows, excerptShows) => {
      const fetchMock = stubSheetFetch({ document: documentPlan, pages: pagesPlan });
      const { dialog } = await openSheet();
      await bothGetsRequested(fetchMock);

      // The settled value is awaited first; the absences are read after it, and after settle() for a held GET.
      expect(await within(dialog).findByText(fileShows)).not.toBeNull();
      expect(await within(dialog).findByText(excerptShows)).not.toBeNull();
      await settle();

      const everyFileText = [FILE_LOADING, FILE_UNAVAILABLE, FILE_NAME];
      for (const text of everyFileText) {
        if (text !== fileShows) expect(within(dialog).queryByText(text)).toBeNull();
      }
      const everyExcerptText = [EXCERPT_LOADING, EXCERPT_UNAVAILABLE];
      for (const text of everyExcerptText) {
        if (text !== excerptShows) expect(within(dialog).queryByText(text)).toBeNull();
      }
      // The false sentences are never shown beside a pending GET of their own.
      if (documentPlan === 'hold') expect(within(dialog).queryByText(FILE_UNAVAILABLE)).toBeNull();
      if (pagesPlan === 'hold') expect(within(dialog).queryByText(EXCERPT_UNAVAILABLE)).toBeNull();
    }
  );
});

describe('HC-STW-015 the opened sheet keeps its full height and its scrollbar gutter', () => {
  // This pins the classes only: Playwright launches Chromium with --hide-scrollbars, so no gate can see a classic scrollbar.
  it('HC-STW-015 has min-h-[85dvh] and [scrollbar-gutter:stable], and no lg:min-h-0', async () => {
    stubSheetFetch();
    const { dialog } = await openSheet();
    const classes = dialog.className.split(/\s+/);
    expect(classes).toContain('min-h-[85dvh]');
    expect(classes).toContain('[scrollbar-gutter:stable]');
    expect(classes).not.toContain('lg:min-h-0');
  });
});

// ---------------------------------------------------------------------------
// HC-STW-006 (stale data), HC-STW-010 (font), HC-STW-011 (file name): review round 2.
// ---------------------------------------------------------------------------
describe('HC-STW-006 a failed refetch does not leave the button enabled on the old data', () => {
  // One GET failing at a time as well as both: each query's isError must count on its own, not only
  // when the other query has no data.
  it.each<[string, { document?: GetPlan; pages?: GetPlan }]>([
    ['only the document GET fails', { document: 'fail' }],
    ['only the pages GET fails', { pages: 'fail' }],
    ['both GETs fail', { document: 'fail', pages: 'fail' }],
  ])('HC-STW-006 reopened with the cached source, %s: disabled with the unavailable reason', async (_label, plan) => {
    const first = stubSheetFetch();
    const { user, dialog } = await openSheet();
    await bothGetsRequested(first);
    await within(dialog).findByText(MATCH_LINE);
    expect((within(dialog).getByRole('button', MARK_BUTTON) as HTMLButtonElement).disabled).toBe(false);

    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Source for Glucose' })).toBeNull();
    });

    // The cache still holds both responses; react-query keeps them when the refetch on reopening fails.
    const second = stubSheetFetch(plan);
    await user.click(screen.getByRole('button', SHOW_SOURCE));
    const reopened = await screen.findByRole('dialog', { name: 'Source for Glucose' });
    await bothGetsRequested(second);

    const reason = await within(reopened).findByText(UNAVAILABLE_REASON);
    const button = within(reopened).getByRole('button', MARK_BUTTON) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.getAttribute('aria-describedby')).toBe(reason.id);

    await user.click(button);
    await settle();
    expect(nonGetCalls(second)).toEqual([]);
  });
});

describe('HC-STW-010 the monospace font is loaded before the sheet opens, so the excerpt does not move when it arrives', () => {
  const FONT_LOAD = vi.fn<(font: string, text?: string) => Promise<unknown[]>>();

  beforeEach(() => {
    FONT_LOAD.mockReset();
    FONT_LOAD.mockResolvedValue([]);
    Object.defineProperty(document, 'fonts', { value: { load: FONT_LOAD }, configurable: true });
  });

  afterEach(() => {
    Reflect.deleteProperty(document, 'fonts');
  });

  it('HC-STW-010 asks for JetBrains Mono when the card is shown, before any click, and makes no API request', async () => {
    const fetchMock = stubSheetFetch();
    renderCard({ observation });
    await waitFor(() => expect(FONT_LOAD).toHaveBeenCalled());

    expect(FONT_LOAD.mock.calls[0][0]).toContain('JetBrains Mono');
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('HC-STW-010 a font that fails to load does not break the sheet', async () => {
    FONT_LOAD.mockRejectedValue(new Error('font blocked'));
    const fetchMock = stubSheetFetch();
    const { dialog } = await openSheet();
    await bothGetsRequested(fetchMock);
    expect(await within(dialog).findByText(MATCH_LINE)).not.toBeNull();
    expect(FONT_LOAD).toHaveBeenCalled();
  });
});

describe('HC-STW-011 a long file name wraps to at most two lines and always reserves both, so the rows below it never move', () => {
  const LONG_NAME = 'a-very-long-lab-report-file-name-with-no-break-point-anywhere-2026-04-10-final.pdf';

  it('HC-STW-011 the File value is clamped to two lines, reserves two lines, can shrink, breaks inside a word and carries the full name as its title', async () => {
    const { SourceTrace } = await load<typeof import('@/components/results/SourceTrace')>('@/components/results/SourceTrace');
    const client = new QueryClient();
    render(
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <SourceTrace open observation={observation} sourceFile={LONG_NAME} excerptLines={[MATCH_LINE]} matchIndex={0} />
        </QueryClientProvider>
      </MemoryRouter>
    );

    const file = screen.getByText(LONG_NAME);
    const classes = file.className.split(/\s+/);
    // Two lines at most (the end is cut with an ellipsis, the title has the rest) ...
    expect(classes).toContain('line-clamp-2');
    // ... and the height of two lines is kept for a short name or "Source file not available", so the
    // row does not grow when the real name arrives. text-sm is 20 px a line, min-h-10 is 40 px.
    expect(classes).toContain('min-h-10');
    // The value column can shrink and an unbroken name breaks inside the word; a single-line
    // truncate would hide the extension where there is no hover to read the title.
    expect(classes).toContain('min-w-0');
    expect(classes).toContain('break-words');
    expect(classes).not.toContain('truncate');
    expect(file.getAttribute('title')).toBe(LONG_NAME);
    // The full name is still the element's text, so a screen reader reads all of it.
    expect(file.textContent).toBe(LONG_NAME);
  });
});
