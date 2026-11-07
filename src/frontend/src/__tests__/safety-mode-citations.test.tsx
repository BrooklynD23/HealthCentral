/**
 * SAFETY-MODE-CITATIONS: with the stricter safety mode on, an answer's and an interpretation's sources show
 * expanded, with no click (HC-SMC-001..004). HC-SMC-005 is the real-backend spec, e2e/safety-mode.spec.ts.
 *
 * The network seam (@/services/api) is mocked. The chat page reads the mode through useSafetyMode (a GET of
 * /assistant/safety-mode). The result card never reads it: its caller passes `alwaysShowSources` (L0 ruling
 * 6703822280, route b), so HC-SMC-004 drives the prop.
 *
 * What these tests would not notice:
 * - whether the real agent path sends a locator rather than a quote in text_snippet (HC-SMC-002 builds the
 *   shapes by hand from be/api/assistant.py `_to_api_citation`; HC-SMC-005 asks the real backend and asserts
 *   that every blockquote it draws holds whitespace, i.e. words and not a locator);
 * - the card's alwaysShowSources branch in a real browser (only jsdom drives it: no e2e path renders it);
 * - layout: jsdom has no CSS, so a source block that overflows or hides behind another element passes here;
 * - the Results page's other cards (the panel interpretation card is out of scope: SAFETY-MODE-PANEL-CITATIONS);
 * - the stillness of the expanded view (the e2e stillness probe reads data-t0).
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ExplainAssistant } from '@/pages/ExplainAssistant';
import { ResultsPage } from '@/pages/ResultsPage';
import { InterpretedResultCard } from '@/components/lab-interpreter/InterpretedResultCard';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import type { InterpretationResponse, Observation, TrendData } from '@/services/types';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public statusText: string,
      message: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

const MODE_PATH = '/assistant/safety-mode';

const HEMOGLOBIN: Observation = {
  id: 'obs-1',
  profile_id: 'profile-123',
  doc_id: 'doc-1',
  analyte_canonical: 'hemoglobin',
  analyte_raw: 'Hemoglobin',
  value: 14.2,
  value_text: null,
  unit: 'g/dL',
  ref_low: 13.5,
  ref_high: 17.5,
  ref_range_text: null,
  flag: null,
  is_abnormal: false,
  collected_at: '2026-03-14',
  user_verified: true,
  extraction_confidence: 0.92,
  source_page: 2,
  source_bbox_json: null,
};

const QUOTE_ONE = 'Hemoglobin: 14.2 g/dL (13.5-17.5)';
const QUOTE_TWO = 'Hemoglobin is the oxygen-carrying protein of red blood cells.';

/** Two citations that carry a real quote (the legacy RAG path), one backed by an observation and one a reference. */
const answerWithTwoQuotes = {
  segments: [
    {
      segment_type: 'report_facts',
      content: 'Your hemoglobin level is 14.2 g/dL [cite:1].',
      citations: [
        {
          source_type: 'user_observation',
          doc_id: 'doc-1',
          doc_title: 'Quest Lab Report',
          page: 2,
          text_snippet: QUOTE_ONE,
          observation_id: 'obs-1',
        },
      ],
    },
    {
      segment_type: 'general_info',
      content: 'Hemoglobin carries oxygen [cite:2].',
      citations: [
        {
          source_type: 'reference',
          doc_id: null,
          doc_title: 'Medical Reference',
          page: 5,
          text_snippet: QUOTE_TWO,
        },
      ],
    },
  ],
  full_response: 'Your hemoglobin level is 14.2 g/dL [cite:1]. Hemoglobin carries oxygen [cite:2].',
  insufficient_context: false,
  insufficient_reasons: [],
  verification: {
    enabled: true,
    total_claims: 2,
    verified_claims: 2,
    failed_claims: 0,
    faithfulness_score: 0.95,
    authority_score: 0.85,
    summary: 'All claims verified',
    issues: [],
  },
  is_valid: true,
  validation_errors: [],
  session_id: 'session-1',
  turn_id: 'turn-1',
};

/** The default agent path: text_snippet is a locator ("docId:page") or a row id, never a quote (be/api/assistant.py). */
const DOC_LOCATOR = '0f9e8d7c-6b5a-4c3d-9e2f-1a0b9c8d7e6f:3';
const ROW_ID = 'c41d9a08-77b2-4e5f-8a63-0d2b9e7f4a10';
const answerWithLocators = {
  ...answerWithTwoQuotes,
  segments: [
    {
      segment_type: 'report_facts',
      content: 'Your hemoglobin is 14.2 g/dL.',
      citations: [
        {
          source_type: 'user_document',
          doc_id: '0f9e8d7c-6b5a-4c3d-9e2f-1a0b9c8d7e6f',
          doc_title: 'Quest Lab Report',
          page: 3,
          text_snippet: DOC_LOCATOR,
          observation_id: null,
          entity_id: null,
        },
        {
          source_type: 'user_document',
          doc_id: null,
          doc_title: 'Care plan',
          page: null,
          text_snippet: ROW_ID,
          observation_id: null,
          entity_id: null,
        },
      ],
    },
  ],
  full_response: 'Your hemoglobin is 14.2 g/dL.',
};

function setMode(value: boolean | undefined) {
  vi.mocked(api.apiGet).mockImplementation(async (url: string) => {
    if (url === MODE_PATH) return value === undefined ? [] : { strict_safety_mode: value };
    if (url === '/observations/') return [HEMOGLOBIN];
    return [];
  });
}

function providers(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/explain']}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

async function askAndWaitForAnswer(answer: unknown, text: RegExp) {
  const user = userEvent.setup();
  vi.mocked(api.apiPost).mockResolvedValueOnce(answer);
  render(providers(<ExplainAssistant />));
  await user.type(screen.getByPlaceholderText('Ask about your results...'), 'Test question');
  await user.click(screen.getByRole('button', { name: 'Send question' }));
  await screen.findByText(text);
  return user;
}

function sourcesOf(): HTMLElement {
  return screen.getByText('Sources:').parentElement as HTMLElement;
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
});

afterEach(() => {
  cleanup();
});

describe('SAFETY-MODE-CITATIONS', () => {
  it('HC-SMC-001: mode on, an answer with two citations shows both expanded, with name and page', async () => {
    setMode(true);
    await askAndWaitForAnswer(answerWithTwoQuotes, /Your hemoglobin level is 14\.2/);

    // No click: the sources are on screen as soon as the mode is known.
    const sources = sourcesOf();
    await waitFor(() => expect(within(sources).getByText(QUOTE_ONE)).toBeInTheDocument());
    expect(within(sources).getByText(QUOTE_TWO)).toBeInTheDocument();
    expect(sources).toHaveTextContent('Source: Quest Lab Report, page 2');
    expect(sources).toHaveTextContent('Source: Medical Reference, page 5');
    // Nothing is waiting behind a click: no popover is open and none is needed.
    expect(screen.queryByRole('dialog')).toBeNull();
    // The two real quotes are quotations.
    expect(sources.querySelectorAll('blockquote')).toHaveLength(2);
  });

  it('HC-SMC-002: a citation that only gives a location never gets quote styling', async () => {
    setMode(true);
    await askAndWaitForAnswer(answerWithLocators, /Your hemoglobin is 14\.2/);

    const sources = sourcesOf();
    await waitFor(() => expect(sources).toHaveTextContent('Source: Quest Lab Report, page 3'));
    expect(sources).toHaveTextContent('Source: Care plan');
    // A locator or row id is a place, not words from the report: no quotation, and the id itself is never shown.
    expect(sources.querySelectorAll('blockquote')).toHaveLength(0);
    expect(document.body).not.toHaveTextContent(DOC_LOCATOR);
    expect(document.body).not.toHaveTextContent(ROW_ID);
  });

  it('HC-SMC-003: mode off renders exactly today\'s chips and popovers', async () => {
    setMode(false);
    const user = await askAndWaitForAnswer(answerWithTwoQuotes, /Your hemoglobin level is 14\.2/);
    // The page must have read the mode: an off that was never read proves nothing.
    await waitFor(() => expect(vi.mocked(api.apiGet)).toHaveBeenCalledWith(MODE_PATH));
    await waitFor(() => expect(vi.mocked(api.apiGet).mock.calls.map(([url]) => url)).toContain('/observations/'));

    const sources = sourcesOf();
    // The role tree of the sources block: two named chips, two labels, no quotation, no open popover.
    const tree = Array.from(sources.querySelectorAll('button, blockquote, [role="dialog"]')).map(
      (el) => `${el.getAttribute('role') ?? el.tagName.toLowerCase()} "${el.getAttribute('aria-label') ?? ''}"`
    );
    expect(tree).toEqual([
      `button "Citation 1: ${QUOTE_ONE}"`,
      `button "Citation 2: ${QUOTE_TWO}"`,
    ]);
    expect(sources).toHaveTextContent('Quest Lab Report (p.2)');
    expect(sources).toHaveTextContent('Medical Reference (p.5)');
    expect(sources).not.toHaveTextContent('Source:');
    expect(screen.queryByRole('dialog')).toBeNull();

    // The popover is still a click away, with the quote inside it.
    await user.click(within(sources).getByRole('button', { name: /^Citation 2:/ }));
    const dialog = await screen.findByRole('dialog', { name: 'Citation 2' });
    expect(within(dialog).getByText(QUOTE_TWO)).toBeInTheDocument();
  });

  // The shapes modules/interpret.py `_generate_citations` builds (:1112-1137): a knowledge-base label, an organisation
  // name and a recommendation title. All three are names, never words quoted from a report, and none carries an
  // observation id, so the card has no page to show.
  const KB_TEXT = 'Biomarker knowledge: Hemoglobin';
  const SOURCE_TEXT = 'American Heart Association';
  const REC_TEXT = 'Eat iron-rich foods';

  describe('HC-SMC-004: the result card under the mode', () => {
    const interpretation: InterpretationResponse = {
      id: 'interp-1',
      observation_id: 'obs-1',
      interpretation_text: 'Your hemoglobin is in the usual range.',
      severity_level: 'normal',
      advice_text: null,
      citations: [
        { type: 'knowledge_base', id: 'kb-hgb', text: KB_TEXT },
        { type: 'source', id: 'src-aha', text: SOURCE_TEXT },
        { type: 'intervention', id: 'rec-iron', text: REC_TEXT },
      ],
      context: null,
      model_id: 'template-v1',
      model_tier: 'template',
      confidence_score: 0.9,
      requires_physician_review: false,
      physician_review_reason: null,
      viewed_at: null,
      created_at: '2026-01-01T00:00:00Z',
    };

    function renderCard(alwaysShowSources?: boolean) {
      return render(
        providers(
          <InterpretedResultCard
            interpretation={interpretation}
            analyteName="Hemoglobin"
            observation={HEMOGLOBIN}
            {...(alwaysShowSources === undefined ? {} : { alwaysShowSources })}
          />
        )
      );
    }

    it('alwaysShowSources shows each source expanded as a named source, never as a quotation', () => {
      const { container } = renderCard(true);

      expect(container).toHaveTextContent(`Source: ${KB_TEXT}`);
      expect(container).toHaveTextContent(`Source: ${SOURCE_TEXT}`);
      expect(container).toHaveTextContent(`Source: ${REC_TEXT}`);
      // A card citation is a name or a title, not words from the report: no quotation, and no page is invented.
      expect(container.querySelectorAll('blockquote')).toHaveLength(0);
      expect(container).not.toHaveTextContent(/page \d/);
      expect(screen.queryByLabelText(/^Citation 1: /)).toBeNull();
      expect(screen.queryByRole('dialog')).toBeNull();
      // The existing way to the report itself stays.
      expect(screen.getByRole('button', { name: 'Show source' })).toBeInTheDocument();
    });

    it.each([
      ['false', false],
      ['absent', undefined],
    ])('alwaysShowSources %s keeps today\'s chips, with the quote behind a click', async (_label, flag) => {
      const user = userEvent.setup();
      const { container } = renderCard(flag);

      expect(screen.getByLabelText(`Citation 1: ${KB_TEXT}`)).toBeInTheDocument();
      expect(screen.getByLabelText(`Citation 2: ${SOURCE_TEXT}`)).toBeInTheDocument();
      expect(screen.getByLabelText(`Citation 3: ${REC_TEXT}`)).toBeInTheDocument();
      expect(screen.queryByText(KB_TEXT)).toBeNull();
      expect(container).not.toHaveTextContent(`Source: ${KB_TEXT}`); // the card's own footer also reads "Source: ..."
      expect(container.querySelectorAll('blockquote')).toHaveLength(0);

      await user.click(screen.getByLabelText(`Citation 1: ${KB_TEXT}`));
      const dialog = await screen.findByRole('dialog', { name: 'Citation 1' });
      expect(within(dialog).getByText(KB_TEXT)).toBeInTheDocument();
    });
  });
  describe('HC-SMC-004: the Results page hands the mode to its card', () => {
    const stored = {
      id: 'interp-1',
      observation_id: 'obs-1',
      interpretation_text: 'Stored card text.',
      severity_level: 'normal',
      advice_text: null,
      citations: [{ type: 'knowledge_base', id: 'kb-hgb', text: KB_TEXT }],
      context: null,
      model_id: 'template-v1',
      model_tier: 'template',
      confidence_score: 0.9,
      requires_physician_review: false,
      physician_review_reason: null,
      viewed_at: null,
      created_at: '2026-01-01T00:00:00Z',
    };
    const trend: TrendData = {
      analyte_canonical: 'hemoglobin',
      analyte_display_name: 'Hemoglobin',
      unit: 'g/dL',
      ref_low: 13.5,
      ref_high: 17.5,
      data_points: [
        { date: '2026-03-14T00:00:00', value: 14.2, unit: 'g/dL', is_abnormal: false, flag: null, doc_id: 'doc-1', extraction_confidence: 0.9, user_verified: true },
      ],
      summary: 'One measurement.',
    };

    function renderResults(mode: boolean | undefined) {
      vi.mocked(api.apiGet).mockImplementation(async (url: string) => {
        if (url === MODE_PATH) return mode === undefined ? [] : { strict_safety_mode: mode };
        if (url === '/observations/') return [HEMOGLOBIN];
        if (url.startsWith('/observations/trends/')) return trend;
        if (url === '/settings/model/external-api') {
          return { use_external_api: false, provider: '', model: '', api_key_configured: false };
        }
        if (url.includes('/interpretation')) return stored;
        return [];
      });
      const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
      return render(
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[{ pathname: '/results', state: { explain: true } }]}>
            <ResultsPage />
          </MemoryRouter>
        </QueryClientProvider>
      );
    }

    it('mode on: the Results card shows its source expanded', async () => {
      renderResults(true);
      expect(await screen.findByText('Stored card text.')).toBeInTheDocument();
      expect(await screen.findByText(`Source: ${KB_TEXT}`)).toBeInTheDocument();
      expect(document.querySelectorAll('blockquote')).toHaveLength(0);
      expect(screen.queryByLabelText(/^Citation 1: /)).toBeNull();
    });

    it.each([
      ['off', false],
      ['unknown', undefined],
    ])('mode %s: the Results card keeps its chip', async (_label, mode) => {
      renderResults(mode);
      expect(await screen.findByText('Stored card text.')).toBeInTheDocument();
      await waitFor(() => expect(vi.mocked(api.apiGet)).toHaveBeenCalledWith(MODE_PATH));
      expect(screen.getByLabelText(`Citation 1: ${KB_TEXT}`)).toBeInTheDocument();
      expect(screen.queryByText(KB_TEXT)).toBeNull();
    });
  });
});
