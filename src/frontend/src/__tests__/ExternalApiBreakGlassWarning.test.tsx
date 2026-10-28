/**
 * HC-EXT-003 — D12 (owner, 2026-09-27): break-glass is allowed only with a UI
 * warning. The backend reports `redaction_break_glass` on
 * GET /settings/model/external-api (HC-EXT-004).
 *
 * Positive assertions come first; absence is asserted synchronously on a
 * completed render, never via waitFor(... not ...) (recurring-failures #1).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { ExternalApiBreakGlassWarning } from '../components/settings/ExternalApiBreakGlassWarning';
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

const UNKNOWN_COPY =
  "Could not confirm this installation's privacy settings. If the privacy protection override is on, external AI requests may leave this device with reduced redaction.";

describe('ExternalApiBreakGlassWarning', () => {
  it('HC-EXT-003 shows an alert that says data may leave unredacted and is audited', () => {
    render(<ExternalApiBreakGlassWarning active />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent(/privacy protection override is on/i);
    expect(alert).toHaveTextContent(/reduced or no redaction/i);
    expect(alert).toHaveTextContent(/audit log/i);
  });

  it('HC-EXT-003b renders nothing when break-glass is off', () => {
    const { container } = render(<ExternalApiBreakGlassWarning active={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('HC-EXT-003c renders nothing when an older backend sends no flag', () => {
    const { container } = render(<ExternalApiBreakGlassWarning active={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('ExternalApiBreakGlassWarning unknown state (B-1, BGS-1)', () => {
  it('HC-EXT-003d shows a status notice, not an alert, when the flag is unknown', () => {
    render(<ExternalApiBreakGlassWarning unknown />);
    expect(screen.getByRole('status')).toHaveTextContent(UNKNOWN_COPY);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('HC-EXT-003f active wins over unknown: only the alert shows', () => {
    render(<ExternalApiBreakGlassWarning active unknown />);
    expect(screen.getByRole('alert')).toHaveTextContent(/privacy protection override is on/i);
    expect(screen.queryByRole('status')).toBeNull();
  });
});

describe('HC-EXT-003e: lab interpreter shows the status notice when the settings fetch fails', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  it('HC-EXT-003e status notice present, no alert, when external-api GET rejects', async () => {
    vi.mocked(api.apiGet).mockImplementation(async (url) => {
      if (url === '/settings/model/external-api') throw new Error('network down');
      if (url === '/observations/') return [observation];
      throw new Error(`unmocked ${url}`);
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LabInterpreter />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await screen.findByText(/Interpret CBC Panel/i);
    expect(await screen.findByRole('status')).toHaveTextContent(UNKNOWN_COPY);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
