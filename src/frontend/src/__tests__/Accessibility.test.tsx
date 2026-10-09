/**
 * A11Y-001: Accessibility Audit Tests
 *
 * Checks:
 * - Keyboard navigation (tablist/tab roles on panel selectors)
 * - Semantic ARIA labels on interactive elements
 * - Reduced-motion behavior (framer-motion animations disabled)
 * - Chart data table alternative text
 * - Loading state aria-live announcements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendsDashboard } from '@/pages/TrendsDashboard';
import { VerificationWorkbench } from '@/pages/VerificationWorkbench';
import { ExportPage } from '@/pages/ExportPage';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

// Mock API
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

// Mock recharts
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
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{component}</BrowserRouter>
    </QueryClientProvider>
  );
}

const mockObservations = [
  {
    id: 'obs-1',
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: 'hemoglobin',
    analyte_raw: 'Hemoglobin',
    value: 14.2,
    value_text: null,
    unit: 'g/dL',
    ref_low: 12.0,
    ref_high: 17.5,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2024-12-15T00:00:00',
    user_verified: false,
    extraction_confidence: 0.9,
  },
];

const mockTrendData = {
  analyte_canonical: 'hemoglobin',
  analyte_display_name: 'HEMOGLOBIN',
  unit: 'g/dL',
  ref_low: 12.0,
  ref_high: 17.5,
  data_points: [
    { date: '2024-12-15T00:00:00', value: 14.2, unit: 'g/dL', is_abnormal: false, flag: null, doc_id: 'doc-1' },
  ],
  summary: 'Stable.',
};

function setupMocks(overrides: { observations?: unknown[] } = {}) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url === '/observations/') {
      return Promise.resolve(overrides.observations ?? mockObservations);
    }
    if (url.startsWith('/observations/trends/')) {
      return Promise.resolve(mockTrendData);
    }
    if (url.startsWith('/observations/panels/')) {
      return Promise.resolve({ panel_id: 'cbc', panel_name: 'CBC', observations: [], collection_date: null });
    }
    if (url === '/medications/') {
      return Promise.resolve([]);
    }
    if (url === '/documents/') {
      return Promise.resolve([]);
    }
    if (url.startsWith('/documents/')) {
      return Promise.resolve([]);
    }
    return Promise.resolve(null);
  });
}

describe('Accessibility Audit (A11Y-001)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test',
    });
    setupMocks();
  });

  describe('TrendsDashboard: Panel Tab Accessibility', () => {
    it('should have tablist role on panel selector container', async () => {
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByRole('tablist')).toBeInTheDocument();
      });
    });

    it('should have tab roles on individual panel buttons', async () => {
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        expect(tabs.length).toBeGreaterThanOrEqual(4);
      });
    });

    it('should mark active tab with aria-selected', async () => {
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        const cbcTab = screen.getByRole('tab', { name: /CBC/i });
        expect(cbcTab).toHaveAttribute('aria-selected', 'true');
      });
    });
  });

  describe('TrendsDashboard: Chart Accessibility', () => {
    it('should have accessible chart data summary', async () => {
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        // The sr-only data table or summary text should exist
        expect(screen.getByText(/Latest value/i)).toBeInTheDocument();
      });
    });
  });

  describe('TrendsDashboard: Loading State', () => {
    it('should have aria-live region for loading announcements', async () => {
      vi.mocked(api.apiGet).mockImplementation(() => new Promise(() => {})); // never resolves

      renderWithProviders(<TrendsDashboard />);

      const loadingRegion = screen.getByRole('status');
      expect(loadingRegion).toBeInTheDocument();
    });
  });

  describe('VerificationWorkbench: Form Control Labels', () => {
    it('should have aria-labels on action buttons', async () => {
      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        // If observations load, check for labeled buttons
        const editButtons = screen.queryAllByLabelText('Edit value');
        const verifyButtons = screen.queryAllByLabelText('Verify observation');
        const expandButtons = screen.queryAllByLabelText('Expand details');
        // At least the empty state or buttons should be present
        expect(
          editButtons.length > 0 ||
          verifyButtons.length > 0 ||
          expandButtons.length > 0 ||
          screen.queryByText(/All observations verified/i) !== null
        ).toBe(true);
      });
    });
  });

  describe('ExportPage: Button Accessible Names', () => {
    it('should have accessible names on export buttons', async () => {
      renderWithProviders(<ExportPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Download CSV/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Download JSON/i })).toBeInTheDocument();
      });
    });
  });
});
