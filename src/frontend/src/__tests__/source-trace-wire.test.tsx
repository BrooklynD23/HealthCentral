/**
 * SOURCE-TRACE-WIRE vitest halves: HC-STW-001 ("Show source" on the interpreted
 * result card), HC-STW-002 (no request before the click; the sheet shows the file,
 * the page and the matching line after it), HC-STW-003 (excerptFromPage table),
 * HC-STW-004 (Escape closes the sheet and focus returns to "Show source").
 * HC-STW-005 (the same path in a browser) is Playwright, in e2e/ui-provenance.spec.ts.
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
