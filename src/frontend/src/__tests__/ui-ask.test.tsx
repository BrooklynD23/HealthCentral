/**
 * UI-PG-ASK vitest half (plan "UI-PG-ASK"): HC-UIASK-001 to 005 as far as jsdom can see them.
 *
 * jsdom has no layout, no scroll and no CSS, so what it cannot see is measured in e2e/ui-ask.spec.ts:
 * window.scrollY after a send (001), the disclaimer inside the viewport at 390 and 1440 (002), axe on the
 * scrollable region and the labels (003), and the stillness probe on the answer (005). Each test here says what it
 * would fail to notice.
 *
 * Written red first: the markup the rows ask for does not exist yet, so each id fails on its own query.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { ExplainAssistant } from '@/pages/ExplainAssistant';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
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

function LocationProbe() {
  const location = useLocation();
  return <p data-testid="location">{`${location.pathname}${location.search}`}</p>;
}

function renderAsk() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/explain']}>
        <Routes>
          <Route path="/explain" element={<ExplainAssistant />} />
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

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

/** One answer with two citations: an observation-backed one (has a deep link) and a reference (has none). */
const answerWithCitations = {
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
          text_snippet: 'Hemoglobin: 14.2 g/dL (13.5-17.5)',
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
          page: null,
          text_snippet: 'Hemoglobin is the oxygen-carrying protein of red blood cells.',
        },
      ],
    },
  ],
  full_response: 'Your hemoglobin level is 14.2 g/dL [cite:1]. Hemoglobin carries oxygen [cite:2].',
  insufficient_context: false,
  insufficient_reasons: [],
  verification,
  is_valid: true,
  validation_errors: [],
  session_id: 'session-1',
  turn_id: 'turn-1',
};

/** The record behind obs-1 as GET /observations returns it. */
const hemoglobinObservation = {
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

async function sendQuestion(user: ReturnType<typeof userEvent.setup>, text: string) {
  await user.type(screen.getByPlaceholderText('Ask about your results...'), text);
  await user.click(screen.getByRole('button', { name: 'Send question' }));
}

/** Every inline opacity or transform on `el` and on its ancestors up to `stopAt` (exclusive). */
function inlineMotionOnPath(el: HTMLElement, stopAt: HTMLElement): string[] {
  const found: string[] = [];
  for (let node: HTMLElement | null = el; node && node !== stopAt; node = node.parentElement) {
    const { opacity, transform } = node.style;
    if (opacity !== '' || (transform !== '' && transform !== 'none')) {
      found.push(`${node.tagName.toLowerCase()} opacity=${opacity} transform=${transform}`);
    }
  }
  return found;
}

describe('UI-PG-ASK', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
    vi.mocked(api.apiGet).mockImplementation(async () => []);
  });

  afterEach(() => {
    cleanup();
  });

  describe('HC-UIASK-001: sending scrolls only the message list', () => {
    // Blind spot: jsdom does not scroll, so this proves the code path (no scrollIntoView, the list's own scrollTop is
    // set) and not what the window does. The window.scrollY half is in e2e/ui-ask.spec.ts.
    it('the message list is a named, focusable region', () => {
      renderAsk();
      const list = screen.getByRole('log', { name: 'Conversation' });
      expect(list).toHaveAttribute('tabindex', '0');
    });

    // Review round 2: the list used to scroll to its end on mount, which put the empty state's top and the banners
    // above the list's edge. Nothing to follow means nothing to scroll to.
    it('an empty list that is not waiting for an answer is not scrolled', () => {
      const scrollHeight = vi.spyOn(Element.prototype, 'scrollHeight', 'get').mockReturnValue(480);
      try {
        renderAsk();
        expect(screen.getByRole('log', { name: 'Conversation' }).scrollTop).toBe(0);
      } finally {
        scrollHeight.mockRestore();
      }
    });

    it('a restored conversation is scrolled to its newest message', async () => {
      vi.mocked(api.apiGet).mockImplementation(async (url: string) => {
        if (url === '/assistant/sessions') {
          return { sessions: [{ session_id: 's1', title: null, turn_count: 2, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }] };
        }
        if (url === '/assistant/sessions/s1') {
          return {
            session_id: 's1',
            title: null,
            turns: [
              { role: 'user', content: 'What was my A1C?', turn_id: 't1' },
              { role: 'assistant', content: 'Your A1C restored answer', turn_id: 't2' },
            ],
          };
        }
        return [];
      });
      const scrollHeight = vi.spyOn(Element.prototype, 'scrollHeight', 'get').mockReturnValue(480);
      try {
        renderAsk();
        await screen.findByText('Your A1C restored answer');
        expect(screen.getByRole('log', { name: 'Conversation' }).scrollTop).toBe(480);
      } finally {
        scrollHeight.mockRestore();
      }
    });

    it('a send and its answer never call scrollIntoView, and the list scrolls itself to the end', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      const scrollIntoView = vi.mocked(Element.prototype.scrollIntoView);
      scrollIntoView.mockClear();
      // jsdom reports a scrollHeight of 0; give the list one so scrollTop has something to move to.
      const scrollHeight = vi.spyOn(Element.prototype, 'scrollHeight', 'get').mockReturnValue(480);

      try {
        renderAsk();
        await sendQuestion(user, 'What does my hemoglobin level mean?');
        await screen.findByText(/hemoglobin level is 14.2/);

        expect(scrollIntoView).not.toHaveBeenCalled();
        expect(screen.getByRole('log', { name: 'Conversation' }).scrollTop).toBe(480);
      } finally {
        scrollHeight.mockRestore();
      }
    });
  });

  describe('HC-UIASK-002: the disclaimer sits under the composer', () => {
    // Blind spot: DOM order is not screen position. That the disclaimer is in the viewport at 390 and 1440 without a
    // scroll is measured in e2e/ui-ask.spec.ts.
    it('the disclaimer is in the chat card, after the composer, not in a side column', () => {
      renderAsk();
      const list = screen.getByRole('log', { name: 'Conversation' });
      const composer = screen.getByRole('textbox', { name: 'Your question' });
      const disclaimer = screen.getByText(/does not provide medical advice/i);

      const card = list.closest('[data-testid="ask-card"]') as HTMLElement;
      expect(card).not.toBeNull();
      expect(card.contains(composer)).toBe(true);
      expect(card.contains(disclaimer)).toBe(true);
      expect(composer.compareDocumentPosition(disclaimer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(screen.getByText(/always consult your healthcare provider/i)).toBe(disclaimer);
    });
  });

  describe('HC-UIASK-003: labels, names and 44 px controls', () => {
    // Blind spot: this reads names from the DOM, not from axe, and cannot see a region that scrolls. The axe run on the
    // real page is in e2e/ui-ask.spec.ts.
    it('the date filters have visible labels', () => {
      renderAsk();
      const from = screen.getByLabelText('From date');
      const to = screen.getByLabelText('To date');
      for (const input of [from, to]) {
        const labels = (input as HTMLInputElement).labels;
        expect(labels?.length, 'a <label> element, not only an aria-label').toBeGreaterThan(0);
      }
    });

    it('the feedback thumbs are 44 px buttons with aria-pressed, and the thumbs-down controls are named', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockImplementation(async (url: string) =>
        url === '/assistant/chat' ? answerWithCitations : { ok: true }
      );
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/hemoglobin level is 14.2/);

      const helpful = screen.getByRole('button', { name: 'Helpful' });
      const notHelpful = screen.getByRole('button', { name: 'Not helpful' });
      expect(helpful).toHaveAttribute('aria-pressed', 'false');
      expect(notHelpful).toHaveAttribute('aria-pressed', 'false');
      expect(helpful.className).toContain('min-h-target');
      expect(helpful.className).toContain('min-w-target');

      await user.click(notHelpful);
      await waitFor(() => expect(notHelpful).toHaveAttribute('aria-pressed', 'true'));
      expect(helpful).toHaveAttribute('aria-pressed', 'false');

      // The tag toggle is an icon only button; the correction textarea has only a placeholder today.
      expect(screen.getByRole('button', { name: /feedback options/i })).toBeInTheDocument();
      expect(screen.getByRole('textbox', { name: /better answer/i })).toBeInTheDocument();
    });
  });

  describe('HC-UIASK-004: no orb and no canvas (pin for the tier rule)', () => {
    // Blind spot: a canvas drawn after a later interaction would not exist yet. The e2e spec checks the page after an
    // answer; this one checks the first render, the pending state and the source.
    it('renders no canvas and no ThinkingOrb while idle, pending and answered', async () => {
      const user = userEvent.setup();
      let resolveChat: (value: unknown) => void = () => {};
      vi.mocked(api.apiPost).mockImplementationOnce(() => new Promise((resolve) => (resolveChat = resolve)));
      const { container } = renderAsk();
      expect(container.querySelector('canvas')).toBeNull();

      await sendQuestion(user, 'Test question');
      // The user's message is on screen and the answer is still pending.
      await screen.findByText('Test question');
      expect(container.querySelector('canvas')).toBeNull();

      resolveChat(answerWithCitations);
      await screen.findByText(/hemoglobin level is 14.2/);
      expect(container.querySelector('canvas')).toBeNull();
    });

    it('the page source does not import ThinkingOrb or a canvas', () => {
      const source = readFileSync(resolve(__dirname, '../pages/ExplainAssistant.tsx'), 'utf8');
      expect(source).not.toMatch(/ThinkingOrb/);
      expect(source).not.toMatch(/<canvas/);
    });
  });

  describe('HC-UIASK-005: answers and citations are T0 and carry no motion', () => {
    // Blind spot: the computed stillness of a real render (a transition from CSS, a layout shift) is the stillnessProbe
    // run in e2e/ui-ask.spec.ts. This checks the markup rules it relies on: data-t0 where the plan puts it and no
    // animated wrapper around it.
    it('the answer bubble, the citation chips and the disclaimer carry data-t0', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'Test question');
      const answer = await screen.findByText(/hemoglobin level is 14.2/);

      expect(answer.closest('[data-t0]'), 'the answer text').not.toBeNull();
      // Citation 1's observation is not in the (empty) list, so it is the workbench link chip; citation 2 is a quote chip.
      const chips = within(screen.getByText('Sources:').parentElement as HTMLElement).getAllByRole('button');
      expect(chips).toHaveLength(2);
      for (const chip of chips) expect(chip.querySelector('[data-t0]') ?? chip.closest('[data-t0]'), chip.textContent ?? '').not.toBeNull();
      expect(screen.getByText(/does not provide medical advice/i).closest('[data-t0]'), 'the disclaimer').not.toBeNull();
    });

    it('chat error text carries data-t0', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('boom'));
      renderAsk();
      await sendQuestion(user, 'Test question');
      const error = await screen.findByText(/encountered an error/);
      expect(error.closest('[data-t0]')).not.toBeNull();
    });

    it('nothing around an assistant answer or its citations sets an inline opacity or transform', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'Test question');
      const answer = await screen.findByText(/hemoglobin level is 14.2/);
      const list = screen.getByRole('log', { name: 'Conversation' });

      expect(inlineMotionOnPath(answer, list)).toEqual([]);
      for (const chip of within(screen.getByText('Sources:').parentElement as HTMLElement).getAllByRole('button')) {
        expect(inlineMotionOnPath(chip, list)).toEqual([]);
      }
    });

    it('the patient’s own message enters with M6: opacity .35 and a 6 px rise', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'My own question');
      const own = (await screen.findByText('My own question')).closest('[data-role="user"]') as HTMLElement;

      expect(own).not.toBeNull();
      // The first frame, before framer-motion animates it.
      expect(own.style.opacity).toBe('0.35');
      expect(own.style.transform).toMatch(/translateY\(6px\)/);
      // The user's words are not T0: only values and citations are.
      expect(own.querySelector('[data-t0]')).toBeNull();
    });
  });

  describe('UI-PG-ASK: pending state and citation popover', () => {
    // Blind spot: the 1.6 s breathing is CSS; this reads the text and role, not the animation.
    it('the pending state is Pending text, with no bouncing dots', async () => {
      const user = userEvent.setup();
      let resolveChat: (value: unknown) => void = () => {};
      vi.mocked(api.apiPost).mockImplementationOnce(() => new Promise((resolve) => (resolveChat = resolve)));
      const { container } = renderAsk();
      await sendQuestion(user, 'Test question');

      const pending = await screen.findByRole('status');
      expect(pending).toHaveTextContent('Reading your verified results…');
      expect(container.querySelector('.animate-bounce')).toBeNull();
      expect(screen.queryByText(/searching documents/i)).toBeNull();

      resolveChat(answerWithCitations);
      await waitFor(() => expect(screen.queryByRole('status')).toBeNull());
    });

    // Blind spot: a Radix popover in jsdom has no collision handling; position is not asserted.
    it('a citation chip is the UI-PROVENANCE CitationTooltip: it opens the quote, and "Open source" opens the trace sheet', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiGet).mockImplementation(async (url: string) => (url === '/observations/' ? [hemoglobinObservation] : []));
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/hemoglobin level is 14.2/);

      await user.click(await screen.findByRole('button', { name: /^Citation 1:/ }));
      const dialog = await screen.findByRole('dialog', { name: 'Citation 1' });
      expect(within(dialog).getByText(/Hemoglobin: 14\.2 g\/dL \(13\.5-17\.5\)/)).toBeInTheDocument();
      expect(within(dialog).getByText('Page 2')).toBeInTheDocument();

      await user.click(within(dialog).getByRole('button', { name: 'Open source' }));
      expect(await screen.findByRole('dialog', { name: 'Source for Hemoglobin' })).toBeInTheDocument();
    });

    it('a citation with no observation behind it opens the quote but offers no "Open source"', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/hemoglobin level is 14.2/);

      await user.click(screen.getByRole('button', { name: /^Citation 2:/ }));
      const dialog = await screen.findByRole('dialog', { name: 'Citation 2' });
      expect(within(dialog).getByText(/oxygen-carrying protein/)).toBeInTheDocument();
      expect(within(dialog).queryByRole('button', { name: 'Open source' })).toBeNull();
    });

    it('the source name stays visible next to the chip', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/hemoglobin level is 14.2/);
      expect(screen.getByText(/Quest Lab Report/)).toBeInTheDocument();
      expect(screen.getByText(/Medical Reference/)).toBeInTheDocument();
    });

    it('a citation whose observation is not in the loaded list keeps its CITE-SRC-001 deep link', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/hemoglobin level is 14.2/);

      // obs-1 is not in the (empty) observation list, so there is nothing to trace: the chip goes to the workbench.
      await user.click(screen.getByRole('button', { name: /^\[1\] Quest Lab Report/ }));
      expect(await screen.findByTestId('location')).toHaveTextContent('/verify?observation=obs-1&doc=doc-1&page=2');
    });
  });

  // Recurring failure #1: every test above mocks a real sentence as text_snippet. The default agent path
  // (AGENT_ENABLED_DEFAULT) does not: be/api/assistant.py `_to_api_citation` sets text_snippet = locator or source_id,
  // and the locator is a row id (modules/agent/nodes/draft.py, graph.py). These are the shapes it really emits.
  describe('UI-PG-ASK: citations in the shape the default agent path sends', () => {
    const OBS_ID = '7b0e6a52-3c1d-4f0a-9d2e-5a1f0c9b8e11';
    const TASK_ID = 'c41d9a08-77b2-4e5f-8a63-0d2b9e7f4a10';
    const DOC_ID = '0f9e8d7c-6b5a-4c3d-9e2f-1a0b9c8d7e6f';
    const ENTITY_ID = '5d4c3b2a-1f0e-4d9c-8b7a-6f5e4d3c2b1a';
    const agentObservation = {
      source_type: 'user_document', doc_id: null, doc_title: null, page: null,
      observation_id: OBS_ID, entity_id: null, text_snippet: OBS_ID, relevance_score: 1.0,
    };
    const agentTask = {
      source_type: 'user_document', doc_id: null, doc_title: null, page: null,
      observation_id: null, entity_id: null, text_snippet: TASK_ID, relevance_score: 1.0,
    };
    const agentEntity = {
      source_type: 'user_document', doc_id: DOC_ID, doc_title: null, page: null,
      observation_id: null, entity_id: ENTITY_ID, text_snippet: DOC_ID, relevance_score: 1.0,
    };
    const agentAnswer = (citations: unknown[]) => ({
      ...answerWithCitations,
      segments: [{ segment_type: 'report_facts', content: 'Your hemoglobin is 14.2 g/dL.', citations }],
      full_response: 'Your hemoglobin is 14.2 g/dL.',
    });
    const traced = { ...hemoglobinObservation, id: OBS_ID };

    it('an observation citation shows the record, never its row id, and offers Open source', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiGet).mockImplementation(async (url: string) => (url === '/observations/' ? [traced] : []));
      vi.mocked(api.apiPost).mockResolvedValueOnce(agentAnswer([agentObservation]));
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/Your hemoglobin is 14.2/);

      await user.click(await screen.findByRole('button', { name: /^Citation 1:/ }));
      const dialog = await screen.findByRole('dialog', { name: 'Citation 1' });
      expect(dialog).not.toHaveTextContent(OBS_ID);
      expect(within(dialog).getByText(/Hemoglobin: 14\.2 g\/dL/)).toBeInTheDocument();
      expect(within(dialog).getByRole('button', { name: 'Open source' })).toBeInTheDocument();
      expect(document.body).not.toHaveTextContent(OBS_ID);
    });

    // Same text as SourceTrace's result line: an empty value_text falls through to the number (review round 2, #9).
    it('an empty value_text falls through to the number, as the Source Trace sheet does', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiGet).mockImplementation(async (url: string) =>
        url === '/observations/' ? [{ ...traced, value_text: '' }] : []
      );
      vi.mocked(api.apiPost).mockResolvedValueOnce(agentAnswer([agentObservation]));
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/Your hemoglobin is 14.2/);

      await user.click(await screen.findByRole('button', { name: /^Citation 1:/ }));
      const dialog = await screen.findByRole('dialog', { name: 'Citation 1' });
      expect(within(dialog).getByText(/Hemoglobin: 14\.2 g\/dL/)).toBeInTheDocument();
    });

    it('a care-task citation has no quote and no target, so it is a plain label, not a chip', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(agentAnswer([agentTask]));
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/Your hemoglobin is 14.2/);

      const sources = screen.getByText('Sources:').parentElement as HTMLElement;
      expect(within(sources).queryByRole('button')).toBeNull();
      expect(sources).not.toHaveTextContent(TASK_ID);
      expect(document.body).not.toHaveTextContent(TASK_ID);
    });

    it('an entity citation keeps its deep link and never shows the document id as a quote', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(agentAnswer([agentEntity]));
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/Your hemoglobin is 14.2/);

      const sources = screen.getByText('Sources:').parentElement as HTMLElement;
      expect(sources).not.toHaveTextContent(DOC_ID);
      await user.click(within(sources).getByRole('button'));
      expect(await screen.findByTestId('location')).toHaveTextContent(`/verify?entity=${ENTITY_ID}&doc=${DOC_ID}`);
    });

    it('a chunk locator ("doc:page") is not shown as a quote either', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(
        agentAnswer([{ source_type: 'reference', doc_id: null, doc_title: null, page: null, observation_id: null, entity_id: null, text_snippet: `${DOC_ID}:3`, relevance_score: 1.0 }])
      );
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/Your hemoglobin is 14.2/);
      expect(document.body).not.toHaveTextContent(DOC_ID);
      expect(within(screen.getByText('Sources:').parentElement as HTMLElement).queryByRole('button')).toBeNull();
    });
  });

  // L0 ruling 6586537788, option (a): "Open source" on a citation shows the real source, fetched only once the sheet is
  // open (ObservationSourceTrace), never the chat citation's doc_title as a file name, and #460's rule: "It matches,
  // mark as checked" is enabled only with the excerpt on screen. Blind spot: jsdom has no layout, so a long excerpt
  // line wrapping (HC-UIPV-004) and the sheet staying still are measured in e2e/ui-ask.spec.ts.
  describe('UI-PG-ASK: Open source shows the real source', () => {
    const SOURCE_FILE = 'quest-lipid-panel-2026-03.pdf';
    const MARK = 'It matches, mark as checked';
    const STATES = 'This is what your report states.';
    const unverified = { ...hemoglobinObservation, user_verified: false };
    const pages = [{ page_number: 2, text: 'Lab Report\nHemoglobin 14.2 g/dL\nHematocrit 42 %', has_tables: false }];
    const documentRow = { id: 'doc-1', source: SOURCE_FILE };

    interface Serve {
      observation?: typeof unverified;
      pages?: unknown;
      document?: () => Promise<unknown>;
      pagesCall?: () => Promise<unknown>;
    }
    function serve({ observation = unverified, pages: pageRows = pages, document, pagesCall }: Serve = {}) {
      vi.mocked(api.apiGet).mockImplementation(async (url: string) => {
        if (url === '/observations/') return [observation];
        if (url === '/documents/doc-1') return document ? document() : documentRow;
        if (url === '/documents/doc-1/pages') return pagesCall ? pagesCall() : pageRows;
        return [];
      });
    }
    const documentCalls = () =>
      vi.mocked(api.apiGet).mock.calls.map(([url]) => url).filter((url) => String(url).startsWith('/documents/doc-1'));

    async function openPopover(user: ReturnType<typeof userEvent.setup>, answer: unknown = answerWithCitations) {
      vi.mocked(api.apiPost).mockResolvedValueOnce(answer);
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/hemoglobin level is 14.2/);
      await user.click(await screen.findByRole('button', { name: /^Citation 1:/ }));
      return screen.findByRole('dialog', { name: 'Citation 1' });
    }
    async function openSheet(user: ReturnType<typeof userEvent.setup>) {
      const popover = await openPopover(user);
      await user.click(within(popover).getByRole('button', { name: 'Open source' }));
      return screen.findByRole('dialog', { name: 'Source for Hemoglobin' });
    }

    it('shows the document\u2019s file name and the excerpt, never the chat title or "not available"', async () => {
      const user = userEvent.setup();
      serve();
      const sheet = await openSheet(user);
      expect(await within(sheet).findByText(SOURCE_FILE)).toBeInTheDocument();
      expect(await within(sheet).findByText('Hemoglobin 14.2 g/dL')).toBeInTheDocument();
      expect(within(sheet).getByText(STATES)).toBeInTheDocument();
      expect(sheet).not.toHaveTextContent('Source file not available');
      expect(sheet).not.toHaveTextContent('Excerpt not available.');
      // The chat citation's doc_title ("Quest Lab Report") is a title, not a file name.
      expect(sheet).not.toHaveTextContent('Quest Lab Report');
    });

    it('makes no document request until "Open source" is clicked', async () => {
      const user = userEvent.setup();
      serve();
      const popover = await openPopover(user);
      expect(documentCalls(), 'after the answer renders and the popover opens').toEqual([]);

      await user.click(within(popover).getByRole('button', { name: 'Open source' }));
      await screen.findByRole('dialog', { name: 'Source for Hemoglobin' });
      await waitFor(() => expect([...documentCalls()].sort()).toEqual(['/documents/doc-1', '/documents/doc-1/pages']));
    });

    it('keeps "It matches, mark as checked" disabled while the source loads, and enables it only over the excerpt', async () => {
      const user = userEvent.setup();
      let release: () => void = () => {};
      const gate = new Promise<void>((resolve) => (release = resolve));
      serve({ document: async () => (await gate, documentRow), pagesCall: async () => (await gate, pages) });
      const sheet = await openSheet(user);

      expect(await within(sheet).findByRole('button', { name: MARK })).toBeDisabled();
      expect(within(sheet).getByText('Loading the source to compare.')).toBeInTheDocument();
      expect(within(sheet).queryByText(STATES)).toBeNull();

      release();
      expect(await within(sheet).findByText('Hemoglobin 14.2 g/dL')).toBeInTheDocument();
      expect(within(sheet).getByText(STATES)).toBeInTheDocument();
      await waitFor(() => expect(within(sheet).getByRole('button', { name: MARK })).toBeEnabled());
    });

    it('keeps it disabled, and claims nothing, when no single line matches', async () => {
      const user = userEvent.setup();
      serve({ pages: [{ page_number: 2, text: 'Hemoglobin 14.2 g/dL\nHemoglobin 14.2 g/dL (repeat)', has_tables: false }] });
      const sheet = await openSheet(user);
      expect(await within(sheet).findByText(SOURCE_FILE)).toBeInTheDocument();
      expect(await within(sheet).findByText('Excerpt not available.')).toBeInTheDocument();
      expect(within(sheet).queryByText(STATES)).toBeNull();
      expect(within(sheet).getByRole('button', { name: MARK })).toBeDisabled();
    });

    it('keeps it disabled when the document GET fails', async () => {
      const user = userEvent.setup();
      serve({ document: async () => Promise.reject(new Error('boom')) });
      const sheet = await openSheet(user);
      // The GET really went out and failed: an empty sheet would also say "not available".
      await waitFor(() => expect(documentCalls()).toContain('/documents/doc-1'));
      expect(await within(sheet).findByText('Source file not available')).toBeInTheDocument();
      expect(within(sheet).getByRole('button', { name: MARK })).toBeDisabled();
      expect(within(sheet).getByText(/The source is not available to compare/)).toBeInTheDocument();
    });

    it('a record with no document behind it keeps its text and offers no "Open source"', async () => {
      const user = userEvent.setup();
      serve({ observation: { ...unverified, doc_id: null as unknown as string } });
      const popover = await openPopover(user);
      expect(within(popover).getByText(/Hemoglobin: 14\.2 g\/dL \(13\.5-17\.5\)/)).toBeInTheDocument();
      expect(within(popover).queryByRole('button', { name: 'Open source' })).toBeNull();
    });

    it('shows a source title unchanged: Quest_Lab_Report.pdf keeps both underscores', async () => {
      const user = userEvent.setup();
      serve();
      const answer = {
        ...answerWithCitations,
        segments: [
          {
            ...answerWithCitations.segments[0],
            citations: [{ ...answerWithCitations.segments[0].citations[0], doc_title: 'Quest_Lab_Report.pdf' }],
          },
        ],
      };
      const popover = await openPopover(user, answer);
      expect(within(popover).getByText('Quest_Lab_Report.pdf')).toBeInTheDocument();
      expect(popover).not.toHaveTextContent('Quest Lab_Report.pdf');
    });

    it('the popover title and quote wrap by their own class, and the page injects no global rule for them', async () => {
      const user = userEvent.setup();
      serve();
      const popover = await openPopover(user);
      expect(within(popover).getByText('Quest Lab Report')).toHaveClass('[overflow-wrap:anywhere]');
      expect(within(popover).getByText(/Hemoglobin: 14\.2 g\/dL/)).toHaveClass('[overflow-wrap:anywhere]');
      expect(Array.from(document.querySelectorAll('style')).some((el) => /Citation/.test(el.textContent ?? ''))).toBe(false);
    });

    // The popover stays open under the modal sheet. Escape closes the sheet and focus returns to "Open source"; the
    // next Escape closes the popover and focus returns to the chip.
    it('Escape closes the sheet, then the popover, and focus walks back to the chip', async () => {
      const user = userEvent.setup();
      serve();
      const popover = await openPopover(user);
      const chip = screen.getByRole('button', { name: /^Citation 1:/ });
      const openSource = within(popover).getByRole('button', { name: 'Open source' });
      await user.click(openSource);
      await screen.findByRole('dialog', { name: 'Source for Hemoglobin' });

      await user.keyboard('{Escape}');
      await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Source for Hemoglobin' })).toBeNull());
      expect(screen.getByRole('dialog', { name: 'Citation 1' })).toBeInTheDocument();
      await waitFor(() => expect(document.activeElement).toBe(openSource));

      await user.keyboard('{Escape}');
      await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Citation 1' })).toBeNull());
      await waitFor(() => expect(document.activeElement).toBe(chip));
    });
  });

  describe('UI-PG-ASK: restored messages', () => {
    // Blind spot: vitest sees only the first frame (no LazyMotion), so this proves a restored message does not start
    // at M6's first frame. That a sent one finishes M6 is measured in e2e/ui-ask.spec.ts.
    it('a restored patient message does not replay M6, a freshly sent one does', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiGet).mockImplementation(async (url: string) => {
        if (url === '/assistant/sessions') {
          return { sessions: [{ session_id: 's1', title: null, turn_count: 2, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }] };
        }
        if (url === '/assistant/sessions/s1') {
          return {
            session_id: 's1',
            title: null,
            turns: [
              { role: 'user', content: 'What was my A1C?', turn_id: 't1' },
              { role: 'assistant', content: 'Your A1C restored answer', turn_id: 't2' },
            ],
          };
        }
        return [];
      });
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      const restored = (await screen.findByText('What was my A1C?')).closest('[data-role="user"]') as HTMLElement;
      expect(restored.style.opacity).not.toBe('0.35');
      expect(restored.style.transform).not.toMatch(/translateY\(6px\)/);

      await sendQuestion(user, 'A fresh question');
      const fresh = (await screen.findByText('A fresh question')).closest('[data-role="user"]') as HTMLElement;
      expect(fresh.style.opacity).toBe('0.35');
    });
  });
});
