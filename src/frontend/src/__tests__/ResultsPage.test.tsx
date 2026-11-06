/**
 * ResultsPage tests: the Trends cases (FE-TRENDS-001..004, UX-001, HC-VER-FE-001) and the Lab Interpreter cases
 * (HC-EXT-006, HC-LAB-001, HC-IWM-FE-001..004) ported from TrendsDashboard.test.tsx and LabInterpreter.test.tsx
 * when UI-PG-RESULTS folded the two pages into one. Every assertion is kept. What changed is the way in:
 * the chart container is the ribbon's slider, "Interpret CBC Panel" is no longer the first thing on screen (the
 * tab list is the wait), and the flows that began at the Interpret page press "Explain this result" first.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ResultsPage } from '@/pages/ResultsPage';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

// Mock the API module with URL-based routing
vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
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

// ---------------------------------------------------------------------------
// Trends cases
// ---------------------------------------------------------------------------

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
}

const mockTrendData = {
  analyte_canonical: 'hemoglobin',
  analyte_display_name: 'HEMOGLOBIN',
  unit: 'g/dL',
  ref_low: 12.0,
  ref_high: 17.5,
  data_points: [
    {
      date: '2024-06-15T00:00:00',
      value: 13.8,
      unit: 'g/dL',
      is_abnormal: false,
      flag: null,
      user_verified: true,
      doc_id: 'doc-1',
    },
    {
      date: '2024-08-15T00:00:00',
      value: 14.1,
      unit: 'g/dL',
      is_abnormal: false,
      flag: null,
      user_verified: true,
      doc_id: 'doc-2',
    },
    {
      date: '2024-10-15T00:00:00',
      value: 13.5,
      unit: 'g/dL',
      is_abnormal: false,
      flag: null,
      user_verified: true,
      doc_id: 'doc-3',
    },
    {
      date: '2024-12-15T00:00:00',
      value: 14.2,
      unit: 'g/dL',
      is_abnormal: false,
      flag: null,
      user_verified: true,
      doc_id: 'doc-4',
    },
  ],
  summary: 'HEMOGLOBIN has increased by 2.9% over 4 measurements.',
};

const mockPanelData = {
  panel_id: 'cbc',
  panel_name: 'Complete Blood Count',
  observations: [
    {
      id: 'obs-1',
      profile_id: 'profile-123',
      doc_id: 'doc-1',
      analyte_canonical: 'hemoglobin',
      analyte_raw: 'Hemoglobin',
      value: 14.2,
      unit: 'g/dL',
      ref_low: 12.0,
      ref_high: 17.5,
      flag: null,
      is_abnormal: false,
      user_verified: true,
    },
    {
      id: 'obs-2',
      profile_id: 'profile-123',
      doc_id: 'doc-1',
      analyte_canonical: 'wbc',
      analyte_raw: 'WBC Count',
      value: 7.5,
      unit: 'K/uL',
      ref_low: 4.5,
      ref_high: 11.0,
      flag: null,
      is_abnormal: false,
      user_verified: true,
    },
  ],
  collection_date: '2024-12-15T00:00:00',
};

const mockAllObservations = [
  {
    id: 'obs-1',
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: 'hemoglobin',
    analyte_raw: 'Hemoglobin',
    value: 14.2,
    unit: 'g/dL',
    user_verified: true,
    collected_at: '2024-12-15T00:00:00',
  },
  {
    id: 'obs-2',
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: 'wbc',
    analyte_raw: 'WBC Count',
    value: 7.5,
    unit: 'K/uL',
    user_verified: true,
    collected_at: '2024-12-15T00:00:00',
  },
  {
    id: 'obs-3',
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 95,
    unit: 'mg/dL',
    user_verified: true,
    collected_at: '2024-12-15T00:00:00',
  },
];

const mockMedications = [
  {
    id: 'med-1',
    profile_id: 'profile-123',
    name: 'Metformin',
    generic_name: null,
    dosage_amount: 500,
    dosage_unit: 'mg',
    dosage_form: 'tablet',
    frequency: 'twice_daily',
    instructions: null,
    is_active: true,
    reminder_enabled: false,
    started_at: '2024-01-01T00:00:00',
    ended_at: null,
    created_at: '2024-01-01T00:00:00',
    updated_at: '2024-01-01T00:00:00',
    schedules: [],
  },
];

// Helper to set up URL-based API mocking
function setupApiMocks(options: {
  observations?: typeof mockAllObservations | [];
  trendData?: typeof mockTrendData | null;
  trendError?: boolean;
  panelData?: typeof mockPanelData | null;
  medications?: typeof mockMedications | [];
}) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url === '/observations/') {
      return Promise.resolve(options.observations ?? mockAllObservations);
    }
    if (url.startsWith('/observations/trends/')) {
      if (options.trendError) {
        return Promise.reject(new Error('No data found'));
      }
      return Promise.resolve(options.trendData ?? mockTrendData);
    }
    if (url.startsWith('/observations/panels/')) {
      return Promise.resolve(options.panelData ?? mockPanelData);
    }
    if (url === '/medications/') {
      return Promise.resolve(options.medications ?? mockMedications);
    }
    return Promise.resolve(null);
  });
}

describe('ResultsPage: Trends cases (ported from TrendsDashboard.test.tsx)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Set up auth state
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  describe('FE-TRENDS-001: test_chart_renders_real_data', () => {
    it('should load and display trend data from API', async () => {
      setupApiMocks({});

      renderWithProviders(<ResultsPage />);

      // Should show the chart. It is the Range Ribbon now, so the chart container is its slider (L0 ruling
      // 6600985053 Q5: the Recharts container is gone, and so is the Recharts mock).
      await waitFor(() => {
        expect(screen.getByRole('slider', { name: /results over time/i })).toBeInTheDocument();
      });

      // Should show the summary
      await waitFor(() => {
        expect(
          screen.getByText(/increased by 2.9%/i)
        ).toBeInTheDocument();
      });
    });

    it('should display latest value and reference range', async () => {
      setupApiMocks({});

      renderWithProviders(<ResultsPage />);

      await waitFor(() => {
        // Should show latest value (14.2 g/dL)
        expect(screen.getByText(/Latest value.*14\.2/i)).toBeInTheDocument();
      });

      await waitFor(() => {
        // Should show reference range info (12-17.5)
        expect(screen.getByText(/Reference range.*12.*17\.5/i)).toBeInTheDocument();
      });
    });
  });

  describe('FE-TRENDS-002: test_panel_tabs_filter', () => {
    it('should load panel data when tab is clicked', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ResultsPage />);

      await waitFor(() => {
        expect(screen.getByText('CBC')).toBeInTheDocument();
      });

      // Click on CBC tab
      await user.click(screen.getByText('CBC'));

      // Panel data should be fetched
      await waitFor(() => {
        expect(api.apiGet).toHaveBeenCalledWith(
          expect.stringContaining('/observations/panels/cbc'),
          expect.any(Object)
        );
      });
    });

    it('should switch between panels', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ResultsPage />);

      await waitFor(() => {
        expect(screen.getByText('CMP')).toBeInTheDocument();
      });

      // Click on CMP tab
      await user.click(screen.getByText('CMP'));

      // CMP should be active
      await waitFor(() => {
        const cmpButton = screen.getByText('CMP').closest('button');
        expect(cmpButton).toHaveClass('bg-accent');
      });
    });
  });

  describe('FE-TRENDS-003: test_empty_state', () => {
    it('should show empty state when no observations exist', async () => {
      setupApiMocks({ observations: [] });

      renderWithProviders(<ResultsPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/no data available/i)
        ).toBeInTheDocument();
      });
    });

    it('should show message when no trend data for selected analyte', async () => {
      setupApiMocks({ trendError: true });

      renderWithProviders(<ResultsPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/no trend data/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('FE-TRENDS-004: test_analyte_selection', () => {
    it('should update chart when different analyte is selected', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ResultsPage />);

      await waitFor(() => {
        expect(screen.getByText('Hemoglobin')).toBeInTheDocument();
      });

      // Click on Glucose in the analyte list
      const glucoseButton = screen.getByRole('button', { name: /glucose/i });
      await user.click(glucoseButton);

      // Should fetch glucose trend data
      await waitFor(() => {
        expect(api.apiGet).toHaveBeenCalledWith(
          expect.stringContaining('/observations/trends/glucose'),
          expect.any(Object)
        );
      });
    });
  });

  describe('UX-001: Medication overlay', () => {
    it('should show medication overlay when medications are active', async () => {
      setupApiMocks({ medications: mockMedications });

      renderWithProviders(<ResultsPage />);

      await waitFor(() => {
        expect(screen.getByTestId('medication-overlay')).toBeInTheDocument();
      });

      expect(screen.getByText('Metformin')).toBeInTheDocument();
    });

    it('should show empty overlay message when no medications are active', async () => {
      setupApiMocks({ medications: [] });

      renderWithProviders(<ResultsPage />);

      await waitFor(() => {
        expect(screen.getByTestId('medication-overlay-empty')).toBeInTheDocument();
      });
    });
  });

  describe('HC-VER-FE-001: unverified trend points are visibly marked (D4)', () => {
    const mixedTrend = {
      ...mockTrendData,
      data_points: [
        { ...mockTrendData.data_points[0], user_verified: true },
        { ...mockTrendData.data_points[1], user_verified: false },
      ],
    };

    it('shows a text note with the unverified count', async () => {
      setupApiMocks({ trendData: mixedTrend });
      renderWithProviders(<ResultsPage />);
      const note = await screen.findByTestId('trend-unverified-note');
      expect(note).toHaveTextContent('1 of 2 points on this chart are unverified');
    });

    it('marks the latest value as unverified when the newest point is unverified', async () => {
      setupApiMocks({ trendData: mixedTrend });
      renderWithProviders(<ResultsPage />);
      expect(
        await screen.findByText(/Latest value: 14\.1 g\/dL \(unverified\)/)
      ).toBeInTheDocument();
    });

    it('shows no unverified note when every charted point is verified', async () => {
      setupApiMocks({});
      renderWithProviders(<ResultsPage />);
      // Wait for a positive anchor first. A bare "not present" check passes on the
      // first empty render tick (recurring-failures #1).
      await screen.findByText(/increased by 2.9%/i);
      expect(screen.queryByTestId('trend-unverified-note')).not.toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Lab Interpreter cases
// ---------------------------------------------------------------------------

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
        <ResultsPage />
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
  // The tab list exists only once the observations have loaded (the old wait was the Interpret CBC Panel button).
  await screen.findByRole('tablist', { name: 'Lab panels' });
  await waitFor(() => {
    expect(vi.mocked(api.apiGet)).toHaveBeenCalledWith('/settings/model/external-api');
  });
  await act(async () => {
    await new Promise((r) => setTimeout(r, 0));
  });
}

describe('HC-EXT-006: break-glass warning on the Results page', () => {
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

// The interpretation is requested only after "Explain this result" (UI-PG-RESULTS, L0 ruling 6600985053), so the
// flows below that began at the Interpret page open it first. Nothing else in them changes.
async function openExplain() {
  fireEvent.click(await screen.findByRole('button', { name: /explain this result/i }));
}

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
            severity_level: 'borderline_high',
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
    await openExplain();
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
    severity_level: 'borderline_high',
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
    await openExplain();
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
    await openExplain();
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
    await openExplain();
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText('Grounded explanation');
    expect(screen.getByText(/Grounded faithfulness/i)).toBeInTheDocument();
    expect(screen.queryByText(LEAD)).toBeNull();
    first.unmount();

    // Withheld answer over a stored card: the hook must not write null to the cache.
    vi.clearAllMocks();
    mockPage({ stored: true, post: withheldBody });
    renderPage();
    await openExplain();
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
    await openExplain();
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText(LEAD);
    expect(screen.queryByText('Grounded explanation')).toBeNull();

    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText('Grounded explanation');
    expect(posts).toBe(2);
    expect(screen.queryByText(LEAD)).toBeNull();
    expect(screen.queryByText(ESCALATE_TEXT)).toBeNull();
  });

  it('HC-IWM-FE-005 a withheld notice survives an answer for another result, and that answer survives it', async () => {
    // Glucose is withheld, LDL gets a good answer, and back on Glucose its escalation message is still there: the
    // other result's answer must not clear it (the clinician line can ride on this notice).
    let posts = 0;
    mockPage({
      observations: [observation, ldl],
      post: () => {
        posts += 1;
        if (posts === 3) return { ...withheldBody(), full_response: 'Second withheld message.', withheld_physician_review: true };
        if (posts !== 2) return { ...withheldBody(), withheld_physician_review: true };
        return {
          interpretation: storedCard,
          grounded_segments: [],
          full_response: '**FACTS**\nLDL grounded text.',
          insufficient_context: false,
          insufficient_reasons: [],
          verification: { ...emptyVerification, enabled: true, faithfulness_score: 1 },
          is_valid: true,
          validation_errors: [],
        };
      },
    });
    renderPage();
    await openExplain();
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText(LEAD);

    fireEvent.click(await screen.findByRole('button', { name: /LDL Cholesterol/i }));
    await waitFor(() => expect(screen.queryByText(LEAD)).toBeNull());
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText('Grounded explanation');

    fireEvent.click(await screen.findByRole('button', { name: /Glucose/i }));
    expect(await screen.findByText(LEAD)).toBeInTheDocument();
    expect(screen.getByText(/contact your clinician promptly/i)).toBeInTheDocument();
    expect(screen.queryByText('Grounded explanation')).toBeNull();

    // And a second withheld answer for Glucose does not take LDL's grounded answer with it.
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    await screen.findByText(/Second withheld message\./);
    fireEvent.click(await screen.findByRole('button', { name: /LDL Cholesterol/i }));
    expect(await screen.findByText('Grounded explanation')).toBeInTheDocument();
    expect(screen.queryByText(LEAD)).toBeNull();

    // And a withheld answer for LDL itself takes LDL's own grounded card away: a grounded explanation and a withheld
    // notice never stand for the same result (the review's mutant deletes the setGrounded line in the withheld branch).
    fireEvent.click(await screen.findByRole('button', { name: /Regenerate/i }));
    expect(await screen.findByText(LEAD)).toBeInTheDocument();
    expect(posts).toBe(4);
    expect(screen.queryByText('Grounded explanation')).toBeNull();
  });

  it('HC-IWM-FE-004 a withheld critical card shows the clinician line; a false or missing flag does not', async () => {
    const CLINICIAN =
      'This result may need prompt attention. Please contact your clinician promptly.';
    // Flag true: one fixed line inside the status notice, as plain text.
    mockPage({ post: () => ({ ...withheldBody(), withheld_physician_review: true }) });
    const first = renderPage();
    await openExplain();
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    const lead = await screen.findByText(LEAD);
    const region = lead.closest('[role="status"]');
    const line = await screen.findByText(CLINICIAN);
    expect(region?.contains(line)).toBe(true);
    expect(screen.getAllByText(CLINICIAN)).toHaveLength(1);
    expect(region?.textContent).toContain(ESCALATE_TEXT);
    first.unmount();

    // Flag false, then missing (an older backend): the notice shows, the line does not.
    for (const extra of [{ withheld_physician_review: false }, {}]) {
      vi.clearAllMocks();
      mockPage({ post: () => ({ ...withheldBody(), ...extra }) });
      const view = renderPage();
      await openExplain();
      fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
      await screen.findByText(LEAD);
      expect(screen.queryByText(CLINICIAN)).toBeNull();
      view.unmount();
    }
  });
});
