/**
 * LabInterpreter break-glass warning tests (HC-EXT-006)
 * and grounded explanation rendering (HC-LAB-001)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LabInterpreter } from '@/pages/LabInterpreter';
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

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  const filter = (props: React.PropsWithChildren<Record<string, unknown>>) => {
    const dom: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(props)) {
      if (
        !['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover', 'whileTap', 'whileInView', 'layout', 'layoutId'].includes(k)
      ) {
        dom[k] = v;
      }
    }
    return dom;
  };
  const make = (Tag: 'div' | 'button' | 'tr' | 'p' | 'span' | 'li' | 'ul' | 'section') =>
    function MotionStub(props: React.PropsWithChildren<Record<string, unknown>>) {
      return <Tag {...filter(props)}>{props.children}</Tag>;
    };
  const motionStubs = {
    div: make('div'),
    button: make('button'),
    tr: make('tr'),
    p: make('p'),
    span: make('span'),
    li: make('li'),
    ul: make('ul'),
    section: make('section'),
  };
  return {
    ...actual,
    motion: motionStubs,
    m: motionStubs,
    AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
  };
});

const observation = {
  id: 'obs-1',
  profile_id: 'p1',
  doc_id: 'doc-1',
  analyte_canonical: 'glucose',
  analyte_raw: 'Glucose',
  value: 90,
  value_text: null,
  unit: 'mg/dL',
  ref_low: 70,
  ref_high: 99,
  ref_range_text: null,
  flag: null,
  is_abnormal: false,
  collected_at: '2026-01-01T00:00:00Z',
  user_verified: true,
  extraction_confidence: 0.9,
  source_page: 1,
  source_bbox_json: null,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LabInterpreter />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function mockExternalApi(external: Record<string, unknown>) {
  vi.mocked(api.apiGet).mockImplementation(async (url) => {
    if (url === '/settings/model/external-api') {
      return { use_external_api: true, provider: 'openai', model: 'gpt-x', api_key_configured: true, ...external };
    }
    if (url === '/observations/') return [observation];
    throw new Error(`unmocked ${url}`);
  });
}

async function settled() {
  await screen.findByText(/Interpret CBC Panel/i);
  await waitFor(() => {
    expect(vi.mocked(api.apiGet)).toHaveBeenCalledWith('/settings/model/external-api');
  });
  await act(async () => {
    await new Promise((r) => setTimeout(r, 0));
  });
}

describe('HC-EXT-006: break-glass warning on the lab interpreter page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  it('HC-EXT-006 shows the alert while the external API is on and break-glass is active', async () => {
    mockExternalApi({ redaction_break_glass: true });
    renderPage();

    const warning = await screen.findByText(/privacy protection override is on/i);
    expect(warning.closest('[role="alert"]')).not.toBeNull();
  });

  it('HC-EXT-006b shows no alert when break-glass is off', async () => {
    mockExternalApi({ redaction_break_glass: false });
    renderPage();

    await settled();
    expect(screen.queryByText(/privacy protection override is on/i)).toBeNull();
  });

  it('HC-EXT-006c shows no alert when the external API is off, even if the flag is true', async () => {
    mockExternalApi({ use_external_api: false, redaction_break_glass: true });
    renderPage();

    await settled();
    expect(screen.queryByText(/privacy protection override is on/i)).toBeNull();
  });
});

describe('HC-LAB-001: grounded explanation panel renders bold runs, not raw markdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  async function generateGrounded(fullResponse: string) {
    vi.mocked(api.apiGet).mockImplementation(async (url) => {
      if (url === '/settings/model/external-api') {
        return { use_external_api: false, api_key_configured: false };
      }
      if (url === '/observations/') return [observation];
      // No stored interpretation yet -> the "Generate Interpretation" button shows.
      if (String(url).includes('/interpretation')) {
        throw new api.ApiError(404, 'Not Found', 'not found');
      }
      throw new Error(`unmocked ${url}`);
    });
    vi.mocked(api.apiPost).mockImplementation(async (url) => {
      if (String(url).includes('/interpret-grounded')) {
        return {
          interpretation: {
            id: 'interp-1',
            observation_id: 'obs-1',
            interpretation_text: 'Plain card text.',
            severity_level: 'mild',
            advice_text: null,
            citations: [],
            context: null,
            model_id: 'template-v1',
            model_tier: 'template',
            confidence_score: 0.9,
            requires_physician_review: false,
            physician_review_reason: null,
            viewed_at: null,
            created_at: '2026-01-01T00:00:00Z',
          },
          grounded_segments: [],
          full_response: fullResponse,
          insufficient_context: false,
          insufficient_reasons: [],
          verification: {
            enabled: true,
            total_claims: 1,
            verified_claims: 1,
            failed_claims: 0,
            faithfulness_score: 1,
            authority_score: 1,
            summary: '',
            issues: [],
          },
          is_valid: true,
          validation_errors: [],
        };
      }
      throw new Error(`unmocked POST ${url}`);
    });
    const { container } = renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText('Grounded explanation');
    return container;
  }

  it('HC-LAB-001 shows **UNCERTAINTY** as a bold run with no literal asterisks', async () => {
    const container = await generateGrounded('**UNCERTAINTY**\nMore context is needed.');

    const bold = await screen.findByText('UNCERTAINTY');
    expect(bold.tagName).toBe('STRONG');
    expect(screen.getByText(/More context is needed\./)).toBeInTheDocument();
    expect(container.textContent ?? '').not.toContain('**');
  });

  it('HC-LAB-001b renders HTML in the response as literal text, never as elements', async () => {
    const container = await generateGrounded(
      '**NOTE**\n<img src=x onerror=alert(1)> and <script>alert(2)</script>'
    );

    await screen.findByText('NOTE');
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent ?? '').toContain('<img src=x onerror=alert(1)>');
    expect(container.textContent ?? '').toContain('<script>alert(2)</script>');
  });
});

describe('HC-IWM-FE: a withheld explanation shows the escalation message', () => {
  const ESCALATE_TEXT =
    "This is a question for your doctor or pharmacist. Asclexis can explain what your verified results say, but it can't advise on diagnosis, treatment, or medication decisions. Please bring this question to your clinician.";
  const LEAD = 'Asclexis could not produce a safe explanation for this result.';
  const ldl = { ...observation, id: 'obs-2', analyte_canonical: 'ldl', analyte_raw: 'LDL Cholesterol' };
  const storedCard = {
    id: 'interp-stored',
    observation_id: 'obs-1',
    interpretation_text: 'Stored card text.',
    severity_level: 'mild',
    advice_text: null,
    citations: [],
    context: null,
    model_id: 'template-v1',
    model_tier: 'template',
    confidence_score: 0.9,
    requires_physician_review: false,
    physician_review_reason: null,
    viewed_at: null,
    created_at: '2026-01-01T00:00:00Z',
  };
  const emptyVerification = {
    enabled: false,
    total_claims: 0,
    verified_claims: 0,
    failed_claims: 0,
    faithfulness_score: 0,
    authority_score: 0,
    summary: '',
    issues: [],
  };

  function withheldBody() {
    return {
      interpretation: null,
      withheld: true,
      grounded_segments: [{ segment_type: 'uncertainty', content: ESCALATE_TEXT, citations: [] }],
      full_response: ESCALATE_TEXT,
      insufficient_context: false,
      insufficient_reasons: [],
      verification: emptyVerification,
      is_valid: false,
      validation_errors: [],
    };
  }

  function mockPage(opts: { stored?: boolean; observations?: unknown[]; post: () => unknown }) {
    vi.mocked(api.apiGet).mockImplementation(async (url) => {
      if (url === '/settings/model/external-api') {
        return { use_external_api: false, api_key_configured: false };
      }
      if (url === '/observations/') return opts.observations ?? [observation];
      if (String(url).includes('/interpretation')) {
        if (opts.stored) return storedCard;
        throw new api.ApiError(404, 'Not Found', 'not found');
      }
      throw new Error(`unmocked ${url}`);
    });
    vi.mocked(api.apiPost).mockImplementation(async (url) => {
      if (String(url).includes('/interpret-grounded')) return opts.post();
      throw new Error(`unmocked POST ${url}`);
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  it('HC-IWM-FE-001 shows the lead line and the message as plain text in a status region, no badge, no grounded card', async () => {
    const MARKUP = 'Plain **x** and <b>y</b> here.';
    mockPage({ post: () => ({ ...withheldBody(), full_response: MARKUP }) });
    renderPage();
    const generate = await screen.findByRole('button', { name: /Generate Interpretation/i });
    // The polite live region is mounted (empty) before the answer, so the notice is announced.
    const mounted = screen.getByTestId('withheld-live-region');
    expect(mounted.textContent).toBe('');
    expect(screen.queryByRole('status')).toBeNull();
    fireEvent.click(generate);

    const lead = await screen.findByText(LEAD);
    const region = lead.closest('[role="status"]');
    expect(mounted.contains(region)).toBe(true);
    expect(region?.textContent).toContain(MARKUP);
    expect(region?.querySelector('strong, b')).toBeNull();
    expect(screen.queryByText(/Grounded faithfulness/i)).toBeNull();
    expect(screen.queryByText('Grounded explanation')).toBeNull();
  });

  it('HC-IWM-FE-002 hides the notice when another observation is selected', async () => {
    mockPage({ observations: [observation, ldl], post: withheldBody });
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText(LEAD);

    fireEvent.click(await screen.findByRole('button', { name: /LDL Cholesterol/i }));

    await waitFor(() => expect(screen.queryByText(LEAD)).toBeNull());
    expect(screen.queryByText(ESCALATE_TEXT)).toBeNull();
  });

  it('HC-IWM-FE-003 a normal answer still shows the grounded card, a withheld one keeps the stored card, and a retry clears the notice', async () => {
    // Normal answer: grounded card and faithfulness badge, no notice.
    mockPage({
      post: () => ({
        interpretation: storedCard,
        grounded_segments: [],
        full_response: '**FACTS**\nNormal grounded text.',
        insufficient_context: false,
        insufficient_reasons: [],
        verification: { ...emptyVerification, enabled: true, faithfulness_score: 1 },
        is_valid: true,
        validation_errors: [],
      }),
    });
    const first = renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText('Grounded explanation');
    expect(screen.getByText(/Grounded faithfulness/i)).toBeInTheDocument();
    expect(screen.queryByText(LEAD)).toBeNull();
    first.unmount();

    // Withheld answer over a stored card: the hook must not write null to the cache.
    vi.clearAllMocks();
    mockPage({ stored: true, post: withheldBody });
    renderPage();
    expect(await screen.findByText('Stored card text.')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: /Regenerate/i }));

    await screen.findByText(LEAD);
    expect(screen.getByText('Stored card text.')).toBeInTheDocument();
    expect(screen.queryByText('No interpretation yet')).toBeNull();
    cleanup();

    // Withheld first (no card saved), then a normal answer on the same page:
    // the notice must be cleared, never shown beside the grounded explanation.
    vi.clearAllMocks();
    let posts = 0;
    mockPage({
      post: () => {
        posts += 1;
        if (posts === 1) return withheldBody();
        return {
          interpretation: storedCard,
          grounded_segments: [],
          full_response: '**FACTS**\nSecond try grounded text.',
          insufficient_context: false,
          insufficient_reasons: [],
          verification: { ...emptyVerification, enabled: true, faithfulness_score: 1 },
          is_valid: true,
          validation_errors: [],
        };
      },
    });
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText(LEAD);
    expect(screen.queryByText('Grounded explanation')).toBeNull();

    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText('Grounded explanation');
    expect(posts).toBe(2);
    expect(screen.queryByText(LEAD)).toBeNull();
    expect(screen.queryByText(ESCALATE_TEXT)).toBeNull();
  });
});
