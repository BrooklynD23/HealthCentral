/**
 * LabInterpreter break-glass warning tests (HC-EXT-006)
 * and grounded explanation rendering (HC-LAB-001)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
