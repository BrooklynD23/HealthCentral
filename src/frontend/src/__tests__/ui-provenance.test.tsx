/**
 * UI-PROVENANCE vitest halves: HC-UIPV-001 (popover opens on click and Enter,
 * not on hover; Escape closes and returns focus), HC-UIPV-003 (Source Trace
 * content), HC-UIPV-005 (verify: one POST, confirmation toast, no Undo),
 * HC-UIPV-006 (markup half: every T0 node has data-t0; the highlight has none).
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md, "UI-PROVENANCE".
 * HC-UIPV-002 (tap in hasTouch) and the stillnessProbe part of HC-UIPV-006 are
 * Playwright, in e2e/ui-provenance.spec.ts. Layout (DF-2, HC-UIPV-004) is not
 * measured here: jsdom has no layout (recurring-failures #1, L0 ruling).
 *
 * SourceTrace is imported at run time, so a missing module fails only the ids
 * that need it and the RED run names each id (the ui-feedback.test.tsx pattern).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { CitationTooltip } from '@/components/lab-interpreter/CitationTooltip';
import { AppToaster } from '@/components/ui/toast';
import type { Citation, Observation } from '@/services/types';
import type * as SourceTraceModule from '@/components/results/SourceTrace';

/** Loads a module at run time (variable specifier, so a missing file fails one test). */
async function load<T>(specifier: string): Promise<T> {
  return (await import(/* @vite-ignore */ specifier)) as T;
}

const OBSERVATION_ID = '6f1c2c4e-8a1b-4c3d-9e0f-123456789abc';

const observation: Observation = {
  id: OBSERVATION_ID,
  profile_id: 'profile-1',
  doc_id: 'doc-1',
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
  source_bbox_json: '{"x0":10,"y0":20,"x1":200,"y1":40}',
};

const EXCERPT = ['Test Result Units Range', 'Glucose 96 mg/dL 70-99', 'Hemoglobin A1c 5.4 % 4.0-5.6'];
const MATCH_LINE = EXCERPT[1];

/** A knowledge-base reference, as the interpreter returns it today: no page, no observation. */
const kbCitation: Citation = {
  type: 'knowledge_base',
  id: 'kb-ferritin-1',
  text: 'Ferritin reflects stored iron; low values can reflect depleted stores.',
};

function renderWithProviders(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** The POSTs that reached the verify endpoint for the test observation. */
function verifyPostsOf(fetchMock: { mock: { calls: unknown[][] } }): unknown[][] {
  return fetchMock.mock.calls.filter(([url, init]) => {
    const method = (init as RequestInit | undefined)?.method;
    return String(url).endsWith(`/observations/${OBSERVATION_ID}/verify`) && method === 'POST';
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(observation)));
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('HC-UIPV-001 citation popover opens on click and Enter, not on hover', () => {
  it('hover alone does not open the popover; a click does', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CitationTooltip citation={kbCitation} index={0} />);

    const trigger = screen.getByRole('button', { name: /^Citation 1: / });
    await user.hover(trigger);
    expect(screen.queryByRole('dialog', { name: 'Citation 1' })).toBeNull();
    expect(screen.queryByRole('tooltip')).toBeNull();

    await user.click(trigger);
    expect(screen.getByRole('dialog', { name: 'Citation 1' })).not.toBeNull();
  });

  it('Enter opens it; Escape closes it and focus returns to the trigger', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CitationTooltip citation={kbCitation} index={0} />);

    const trigger = screen.getByRole('button', { name: /^Citation 1: / });
    trigger.focus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('dialog', { name: 'Citation 1' })).not.toBeNull();

    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Citation 1' })).toBeNull();
    });
    expect(document.activeElement).toBe(trigger);
  });

  it('shows the quote, and no page or Open source, for a knowledge-base reference', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CitationTooltip citation={kbCitation} index={0} />);

    await user.click(screen.getByRole('button', { name: /^Citation 1: / }));
    const dialog = screen.getByRole('dialog', { name: 'Citation 1' });
    expect(within(dialog).getByText(kbCitation.text)).not.toBeNull();
    expect(within(dialog).queryByRole('button', { name: /open source/i })).toBeNull();
    expect(within(dialog).queryByText(/^Page /)).toBeNull();
  });

  it('keeps the citation type line (knowledge base) above the quote, marked data-t0', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CitationTooltip citation={kbCitation} index={0} />);

    await user.click(screen.getByRole('button', { name: /^Citation 1: / }));
    const dialog = screen.getByRole('dialog', { name: 'Citation 1' });
    const typeLine = within(dialog).getByText('knowledge base');
    const quote = within(dialog).getByText(kbCitation.text);
    expect(typeLine.closest('[data-t0]')).not.toBeNull();
    expect(typeLine.compareDocumentPosition(quote) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
  });
});

describe('UI-PROVENANCE source-aware popover (page and Open source only when the citation carries a source)', () => {
  it('shows the page and an Open source button when a source is passed, and opens Source Trace from it', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <CitationTooltip
        citation={kbCitation}
        index={0}
        source={{ observation, excerptLines: EXCERPT, matchIndex: 1 }}
      />
    );

    await user.click(screen.getByRole('button', { name: /^Citation 1: / }));
    const dialog = screen.getByRole('dialog', { name: 'Citation 1' });
    expect(within(dialog).getByText('Page 3')).not.toBeNull();

    await user.click(within(dialog).getByRole('button', { name: /open source/i }));
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /source/i })).not.toBeNull();
    });
    expect(screen.getByText('This is what your report states.')).not.toBeNull();
  });

  it('returns focus to the citation chip when Source Trace closes with Escape', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <CitationTooltip
        citation={kbCitation}
        index={0}
        source={{ observation, excerptLines: EXCERPT, matchIndex: 1 }}
      />
    );
    const trigger = screen.getByRole('button', { name: /^Citation 1: / });

    await user.click(trigger);
    await user.click(
      within(screen.getByRole('dialog', { name: 'Citation 1' })).getByRole('button', { name: /open source/i })
    );
    await screen.findByRole('dialog', { name: /source for glucose/i });

    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /source for glucose/i })).toBeNull();
    });
    expect(document.activeElement).toBe(trigger);
  });
});

describe('HC-UIPV-003 Source Trace shows the highlighted row, page, date and the report line', () => {
  it('renders the matching row with the mark, the page, the date, the range, the read confidence and the report line', async () => {
    const { SourceTrace } = await load<typeof SourceTraceModule>('@/components/results/SourceTrace');
    renderWithProviders(
      <SourceTrace open observation={observation} excerptLines={EXCERPT} matchIndex={1} />
    );

    expect(screen.getByText('This is what your report states.')).not.toBeNull();
    expect(screen.getByText('Page 3')).not.toBeNull();
    expect(screen.getByText('Apr 10, 2026')).not.toBeNull();
    expect(screen.getByText('70 to 99 mg/dL')).not.toBeNull();
    expect(screen.getByText('High')).not.toBeNull();

    const matchRow = screen.getByText(MATCH_LINE).closest('li');
    expect(matchRow?.querySelector('[data-trace-mark]')).not.toBeNull();
    const otherRow = screen.getByText(EXCERPT[0]).closest('li');
    expect(otherRow?.querySelector('[data-trace-mark]')).toBeNull();
  });

  it('says "not available" where the source has no page, and does not invent one', async () => {
    const { SourceTrace } = await load<typeof SourceTraceModule>('@/components/results/SourceTrace');
    renderWithProviders(
      <SourceTrace
        open
        observation={{ ...observation, source_page: null, extraction_confidence: null }}
      />
    );

    expect(screen.getByText('Page not available')).not.toBeNull();
    expect(screen.getByText('Not available')).not.toBeNull();
    expect(screen.queryByText('Page 3')).toBeNull();
  });

  it('writes a range with a negative low as "-2 to 2 mmol/L", not "-2-2 mmol/L"', async () => {
    const { SourceTrace } = await load<typeof SourceTraceModule>('@/components/results/SourceTrace');
    renderWithProviders(
      <SourceTrace open observation={{ ...observation, ref_low: -2, ref_high: 2, unit: 'mmol/L' }} />
    );

    expect(screen.getByText('-2 to 2 mmol/L')).not.toBeNull();
    expect(screen.queryByText('-2-2 mmol/L')).toBeNull();
  });
});

describe('HC-UIPV-005 verify sends one POST, shows the confirmation toast, offers no Undo', () => {
  it('posts once to /observations/{id}/verify, shows the toast, and has no Undo control', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      jsonResponse({ ...observation, user_verified: true })
    );
    vi.stubGlobal('fetch', fetchMock);
    const { SourceTrace } = await load<typeof SourceTraceModule>('@/components/results/SourceTrace');

    renderWithProviders(
      <>
        <AppToaster />
        <SourceTrace open observation={observation} excerptLines={EXCERPT} matchIndex={1} />
      </>
    );

    await user.click(screen.getByRole('button', { name: 'It matches, mark as checked' }));

    await screen.findByText('Glucose, Apr 10, 2026 is now marked as checked');
    const verifyPosts = verifyPostsOf(fetchMock);
    expect(verifyPosts).toHaveLength(1);
    // The verify endpoint takes no value: the body is {}. A body that carried a value would overwrite the stored one.
    expect(JSON.parse(String((verifyPosts[0][1] as RequestInit).body))).toEqual({});

    expect(screen.queryByRole('button', { name: /undo/i })).toBeNull();
    expect(screen.queryByText(/undo/i)).toBeNull();
  });

  it('a double click while the POST is in flight still sends exactly one POST', async () => {
    const user = userEvent.setup();
    // Hold the response until both clicks have landed. A response that arrives at once
    // removes the button before the second click, and the test would pass with no guard.
    let releaseResponse: () => void = () => {};
    const responseGate = new Promise<void>((resolve) => {
      releaseResponse = resolve;
    });
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
      await responseGate;
      return jsonResponse({ ...observation, user_verified: true });
    });
    vi.stubGlobal('fetch', fetchMock);
    const { SourceTrace } = await load<typeof SourceTraceModule>('@/components/results/SourceTrace');

    renderWithProviders(
      <>
        <AppToaster />
        <SourceTrace open observation={observation} excerptLines={EXCERPT} matchIndex={1} />
      </>
    );

    await user.dblClick(screen.getByRole('button', { name: 'It matches, mark as checked' }));
    releaseResponse();

    await screen.findByText('Glucose, Apr 10, 2026 is now marked as checked');
    expect(verifyPostsOf(fetchMock)).toHaveLength(1);
  });
});

describe('HC-UIPV-006 markup half: data-t0 on every T0 node, none on the highlight', () => {
  it('Source Trace: every T0 node carries data-t0; the highlight carries none and sits outside them', async () => {
    const { SourceTrace } = await load<typeof SourceTraceModule>('@/components/results/SourceTrace');
    renderWithProviders(
      <SourceTrace open observation={observation} excerptLines={EXCERPT} matchIndex={1} />
    );

    for (const text of [MATCH_LINE, EXCERPT[0], 'Page 3', 'Apr 10, 2026', '70 to 99 mg/dL', 'High']) {
      const node = screen.getByText(text);
      expect(node.closest('[data-t0]'), `T0 node for "${text}"`).not.toBeNull();
    }

    const marks = document.querySelectorAll('[data-trace-mark]');
    expect(marks.length).toBeGreaterThan(0);
    marks.forEach((mark) => {
      expect(mark.hasAttribute('data-t0')).toBe(false);
      expect(mark.closest('[data-t0]')).toBeNull();
    });
  });

  it('citation popover: chip label, quote and page carry data-t0; the verify toast is still', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <CitationTooltip
        citation={kbCitation}
        index={0}
        source={{ observation, excerptLines: EXCERPT, matchIndex: 1 }}
      />
    );

    const trigger = screen.getByRole('button', { name: /^Citation 1: / });
    expect(trigger.querySelector('[data-t0]')).not.toBeNull();

    await user.click(trigger);
    const dialog = screen.getByRole('dialog', { name: 'Citation 1' });
    expect(within(dialog).getByText(kbCitation.text).closest('[data-t0]')).not.toBeNull();
    expect(within(dialog).getByText('Page 3').closest('[data-t0]')).not.toBeNull();
  });

  it('verify toast: the confirmation is a still toast (data-t0 on its status text)', async () => {
    const user = userEvent.setup();
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ ...observation, user_verified: true })));
    const { SourceTrace } = await load<typeof SourceTraceModule>('@/components/results/SourceTrace');

    renderWithProviders(
      <>
        <AppToaster />
        <SourceTrace open observation={observation} excerptLines={EXCERPT} matchIndex={1} />
      </>
    );
    await user.click(screen.getByRole('button', { name: 'It matches, mark as checked' }));

    const toastText = await screen.findByText('Glucose, Apr 10, 2026 is now marked as checked');
    expect(toastText.closest('[data-t0]')).not.toBeNull();
  });
});
