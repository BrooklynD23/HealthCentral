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

      const card = list.parentElement as HTMLElement;
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
      const chips = screen.getAllByRole('button', { name: /^\[\d\]/ });
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
      for (const chip of screen.getAllByRole('button', { name: /^\[\d\]/ })) {
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
    it('a citation chip opens a popover with the quote, and a deep link when the citation has one', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/hemoglobin level is 14.2/);

      await user.click(screen.getByRole('button', { name: /^\[1\] Quest Lab Report/ }));
      const dialog = await screen.findByRole('dialog', { name: /Source 1/ });
      expect(within(dialog).getByText(/Hemoglobin: 14\.2 g\/dL \(13\.5-17\.5\)/)).toBeInTheDocument();

      await user.click(within(dialog).getByRole('button', { name: 'Show in source document' }));
      expect(await screen.findByTestId('location')).toHaveTextContent('/verify?observation=obs-1&doc=doc-1&page=2');
    });

    it('a citation with no source region opens the quote but offers no link (CITE-SRC-001)', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(answerWithCitations);
      renderAsk();
      await sendQuestion(user, 'Test question');
      await screen.findByText(/hemoglobin level is 14.2/);

      await user.click(screen.getByRole('button', { name: /^\[2\] Medical Reference/ }));
      const dialog = await screen.findByRole('dialog', { name: /Source 2/ });
      expect(within(dialog).getByText(/oxygen-carrying protein/)).toBeInTheDocument();
      expect(within(dialog).queryByRole('button', { name: 'Show in source document' })).toBeNull();
    });
  });
});
