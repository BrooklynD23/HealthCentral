/**
 * MED-CORR-002: MedicationDetail must source "Related Lab Results" from the
 * backend correlations endpoint, not from the frontend heuristic.
 *
 * MED-CORR-001 shipped `GET /medications/{id}/correlations` so the temporal
 * overlap rule would have ONE definition. The page kept using
 * `utils/correlation.ts`, so two definitions coexisted — and they disagree:
 * the endpoint defaults to `verified_only=true` ("an unverified extraction is
 * not a fact to correlate against"), the heuristic filters on nothing. Until
 * the page switches, it shows the looser answer.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MedicationDetail } from '@/pages/MedicationDetail';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(public status: number, public statusText: string, message: string) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom'
  );
  return { ...actual, useParams: () => ({ medicationId: 'med-1' }) };
});

const MEDICATION = {
  id: 'med-1',
  profile_id: 'profile-1',
  name: 'Metoprolol',
  dosage_amount: 25,
  dosage_unit: 'mg',
  frequency: 'once_daily',
  started_at: '2026-01-01T00:00:00',
  ended_at: null,
  is_active: true,
  schedules: [],
};

/** What the endpoint returns: verified only, undated counted not dropped. */
const CORRELATIONS = {
  medication_id: 'med-1',
  started_at: '2026-01-01T00:00:00',
  ended_at: null,
  observation_count: 1,
  excluded_undated_count: 2,
  analytes: ['potassium'],
  observations: [
    {
      id: 'obs-verified',
      analyte_canonical: 'potassium',
      value: 4.1,
      value_text: null,
      unit: 'mmol/L',
      ref_low: 3.5,
      ref_high: 5.1,
      flag: null,
      is_abnormal: false,
      collected_at: '2026-03-01T00:00:00',
      user_verified: true,
    },
  ],
};

/**
 * The raw observation list the old heuristic read. It contains an UNVERIFIED
 * result inside the medication window: the heuristic shows it, the endpoint
 * excludes it. This is the discriminator between the two implementations.
 */
const RAW_OBSERVATIONS = [
  {
    id: 'obs-verified',
    profile_id: 'profile-1',
    doc_id: 'doc-1',
    analyte_canonical: 'potassium',
    analyte_raw: 'Potassium',
    value: 4.1,
    unit: 'mmol/L',
    collected_at: '2026-03-01T00:00:00',
    user_verified: true,
  },
  {
    id: 'obs-unverified',
    profile_id: 'profile-1',
    doc_id: 'doc-2',
    analyte_canonical: 'ldl_cholesterol',
    analyte_raw: 'LDL Cholesterol',
    value: 190,
    unit: 'mg/dL',
    collected_at: '2026-04-01T00:00:00',
    user_verified: false,
  },
];

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <MedicationDetail />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('MED-CORR-002: correlations come from the backend', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ profileId: 'profile-1' });

    vi.mocked(api.apiGet).mockImplementation((url: string) => {
      if (url.includes('/correlations')) return Promise.resolve(CORRELATIONS);
      if (url === '/medications/med-1') return Promise.resolve(MEDICATION);
      if (url.startsWith('/medications/med-1/adherence'))
        return Promise.resolve({ adherence_rate: 1, doses_taken: 1, doses_expected: 1 });
      if (url.startsWith('/medications/med-1/doses')) return Promise.resolve([]);
      if (url.startsWith('/observations')) return Promise.resolve(RAW_OBSERVATIONS);
      return Promise.resolve([]);
    });
  });

  it('FE-MCORR-001: calls the correlations endpoint for this medication', async () => {
    renderPage();
    await waitFor(() => {
      expect(vi.mocked(api.apiGet).mock.calls.some(([url]) =>
        String(url).includes('/medications/med-1/correlations')
      )).toBe(true);
    });
  });

  it('FE-MCORR-002: renders the endpoint\'s observations', async () => {
    renderPage();
    expect(await screen.findByTestId('related-labs-list')).toBeInTheDocument();
    expect(screen.getByText(/potassium/i)).toBeInTheDocument();
  });

  it('FE-MCORR-003: does not show an unverified result the heuristic would include', async () => {
    renderPage();
    await screen.findByTestId('related-labs-list');
    // The heuristic reads the raw observation list and has no verified filter,
    // so it would render this. The endpoint excluded it.
    expect(screen.queryByText(/LDL Cholesterol/i)).not.toBeInTheDocument();
  });

  it('FE-MCORR-004: surfaces the undated count instead of silently dropping it', async () => {
    renderPage();
    await screen.findByTestId('related-labs-list');
    // The backend counts undated observations deliberately rather than
    // dropping them; hiding that count throws away the honesty it was built for.
    expect(await screen.findByTestId('related-labs-undated')).toHaveTextContent('2');
  });
});
