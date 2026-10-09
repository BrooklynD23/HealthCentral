/**
 * TrendsDashboard Component Tests
 *
 * Sprint 3 - S3-FE-003: Wire TrendsDashboard
 *
 * Tests that:
 * - Chart renders with real data
 * - Panel tabs filter correctly
 * - Empty state is handled
 * - Analyte selection works
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendsDashboard } from '@/pages/TrendsDashboard';
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

// Mock recharts to avoid canvas issues in tests
vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

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
      doc_id: 'doc-1',
    },
    {
      date: '2024-08-15T00:00:00',
      value: 14.1,
      unit: 'g/dL',
      is_abnormal: false,
      flag: null,
      doc_id: 'doc-2',
    },
    {
      date: '2024-10-15T00:00:00',
      value: 13.5,
      unit: 'g/dL',
      is_abnormal: false,
      flag: null,
      doc_id: 'doc-3',
    },
    {
      date: '2024-12-15T00:00:00',
      value: 14.2,
      unit: 'g/dL',
      is_abnormal: false,
      flag: null,
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

describe('TrendsDashboard', () => {
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

      renderWithProviders(<TrendsDashboard />);

      // Should show the chart container
      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
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

      renderWithProviders(<TrendsDashboard />);

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

      renderWithProviders(<TrendsDashboard />);

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

      renderWithProviders(<TrendsDashboard />);

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

      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(
          screen.getByText(/no data available/i)
        ).toBeInTheDocument();
      });
    });

    it('should show message when no trend data for selected analyte', async () => {
      setupApiMocks({ trendError: true });

      renderWithProviders(<TrendsDashboard />);

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

      renderWithProviders(<TrendsDashboard />);

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

      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('medication-overlay')).toBeInTheDocument();
      });

      expect(screen.getByText('Metformin')).toBeInTheDocument();
    });

    it('should show empty overlay message when no medications are active', async () => {
      setupApiMocks({ medications: [] });

      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('medication-overlay-empty')).toBeInTheDocument();
      });
    });
  });
});
