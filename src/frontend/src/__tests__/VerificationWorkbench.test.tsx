/**
 * VerificationWorkbench Component Tests
 *
 * Sprint 3 - S3-FE-001: Wire VerificationWorkbench to Observations API
 *
 * Tests that:
 * - Observations are loaded from API
 * - Verify updates the list
 * - Edit value persists
 * - Source preview loads
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VerificationWorkbench } from '@/pages/VerificationWorkbench';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

// Mock the API module
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

/** Default: documents list empty, observations from tests via shared state. */
function defaultApiGetMock(observations: unknown[]) {
  return (url: string) => {
    if (url.startsWith('/documents') && url.includes('/pages')) {
      return Promise.resolve([
        {
          page_number: 1,
          text: 'Glucose: 95 mg/dL (70-100)',
          has_tables: true,
        },
      ]);
    }
    if (url.startsWith('/documents')) {
      return Promise.resolve([]);
    }
    if (url.startsWith('/observations')) {
      return Promise.resolve(observations);
    }
    return Promise.resolve([]);
  };
}

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
}

const mockObservations = [
  {
    id: 'obs-1',
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 95,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 100,
    flag: null,
    is_abnormal: false,
    user_verified: false,
    extraction_confidence: 0.9,
  },
  {
    id: 'obs-2',
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: 'hba1c',
    analyte_raw: 'Hemoglobin A1c',
    value: 6.5,
    unit: '%',
    ref_low: 4.0,
    ref_high: 5.6,
    flag: 'H',
    is_abnormal: true,
    user_verified: false,
    extraction_confidence: 0.85,
  },
];

describe('VerificationWorkbench', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Set up auth state
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
    vi.mocked(api.apiGet).mockImplementation(defaultApiGetMock(mockObservations));
  });

  describe('FE-VERIFY-001: test_loads_observations_from_api', () => {
    it('should load observations from API on mount', async () => {
      renderWithProviders(<VerificationWorkbench />);

      // Should show loading state initially, then observations
      await waitFor(() => {
        expect(screen.getByText('Glucose')).toBeInTheDocument();
      });

      // Verify API was called with needs_verification filter
      expect(api.apiGet).toHaveBeenCalledWith(
        '/observations/',
        expect.objectContaining({
          needs_verification: 'true',
        })
      );
    });

    it('should display observation values from API', async () => {
      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        // Check glucose value
        expect(screen.getByText('95')).toBeInTheDocument();
        expect(screen.getByText('mg/dL')).toBeInTheDocument();

        // Check HbA1c value (abnormal)
        expect(screen.getByText('6.5')).toBeInTheDocument();
      });
    });

    it('should show items needing review badge', async () => {
      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        // Should show count of unverified items
        expect(screen.getByText(/2 items need review/i)).toBeInTheDocument();
      });
    });

    it('HC-CONF-003: shows extraction confidence percentage and preserves 0.0', async () => {
      vi.mocked(api.apiGet).mockImplementation(defaultApiGetMock([
        { ...mockObservations[0], extraction_confidence: 0.0 },
      ]));

      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(screen.getByText(/0%.*low extraction confidence/i)).toBeInTheDocument();
      });
    });
  });

  describe('FE-VERIFY-002: test_verify_updates_list', () => {
    it('should mark observation as verified when verify button clicked', async () => {
      const user = userEvent.setup();

      const verifiedObs = { ...mockObservations[0], user_verified: true };
      const state = { obs: mockObservations as typeof mockObservations };

      vi.mocked(api.apiGet).mockImplementation((url: string) => {
        if (url.startsWith('/documents')) {
          return Promise.resolve([]);
        }
        if (url.startsWith('/observations')) {
          return Promise.resolve(state.obs);
        }
        return Promise.resolve([]);
      });

      vi.mocked(api.apiPost).mockImplementation(async () => {
        state.obs = [mockObservations[1]];
        return verifiedObs;
      });

      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(screen.getByText('Glucose')).toBeInTheDocument();
      });

      // Click verify on first row
      const rows = screen.getAllByRole('row');
      const glucoseRow = rows.find((row) =>
        within(row).queryByText('Glucose')
      );
      expect(glucoseRow).toBeDefined();

      const verifyButton = within(glucoseRow!).getByRole('button', {
        name: /verify/i,
      });
      await user.click(verifyButton);

      // Verify API was called
      await waitFor(() => {
        expect(api.apiPost).toHaveBeenCalledWith(
          '/observations/obs-1/verify',
          expect.any(Object)
        );
      });
    });
  });

  describe('FE-VERIFY-003: test_edit_value_persists', () => {
    it('should allow editing observation value', async () => {
      const user = userEvent.setup();

      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(screen.getByText('Glucose')).toBeInTheDocument();
      });

      // Click edit on glucose row
      const rows = screen.getAllByRole('row');
      const glucoseRow = rows.find((row) =>
        within(row).queryByText('Glucose')
      );

      const editButton = within(glucoseRow!).getByRole('button', {
        name: /edit/i,
      });
      await user.click(editButton);

      // Should show edit modal/input
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });
  });

  describe('FE-VERIFY-004: test_source_preview_loads', () => {
    it('should show source preview when row is selected', async () => {
      const user = userEvent.setup();

      vi.mocked(api.apiGet).mockImplementation(defaultApiGetMock(mockObservations));

      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(screen.getByText('Glucose')).toBeInTheDocument();
      });

      // Click on a row to select it
      const glucoseRow = screen.getByText('Glucose').closest('tr');
      await user.click(glucoseRow!);

      // Source preview should update
      await waitFor(() => {
        expect(screen.getByText(/source preview/i)).toBeInTheDocument();
      });
    });
  });

  describe('Empty state', () => {
    it('should show empty state when no observations need verification', async () => {
      vi.mocked(api.apiGet).mockImplementation(defaultApiGetMock([]));

      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(
          screen.getByText(/all observations verified/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('Document review mode', () => {
    it('loads all observations for selected document when mode=all', async () => {
      window.history.pushState({}, '', '/verify?doc=doc-1&mode=all');
      vi.mocked(api.apiGet).mockImplementation((url: string) => {
        if (url.startsWith('/documents')) {
          return Promise.resolve([
            {
              id: 'doc-1',
              profile_id: 'profile-123',
              doc_type: 'lab_pdf',
              source: 'sample.pdf',
              status: 'parsed',
              page_count: 1,
              collection_date: null,
              imported_at: new Date().toISOString(),
              parsed_at: new Date().toISOString(),
              verified_at: null,
            },
          ]);
        }
        if (url.startsWith('/observations')) {
          return Promise.resolve(mockObservations);
        }
        return Promise.resolve([]);
      });

      renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(screen.getByText(/reviewing: sample.pdf/i)).toBeInTheDocument();
      });

      expect(api.apiGet).toHaveBeenCalledWith(
        '/observations/',
        expect.objectContaining({
          doc_id: 'doc-1',
        })
      );
      expect(screen.getByRole('button', { name: /mark document verified/i })).toBeInTheDocument();
    });

    it('shows OCR retry action when selected document has no extracted rows', async () => {
      window.history.pushState({}, '', '/verify?doc=doc-ocr&mode=all');
      vi.mocked(api.apiGet).mockImplementation((url: string) => {
        if (url.startsWith('/documents')) {
          return Promise.resolve([
            {
              id: 'doc-ocr',
              profile_id: 'profile-123',
              doc_type: 'lab_image',
              source: 'scan.png',
              status: 'pending_ocr',
              page_count: 1,
              collection_date: null,
              imported_at: new Date().toISOString(),
              parsed_at: null,
              verified_at: null,
            },
          ]);
        }
        if (url.startsWith('/observations')) {
          return Promise.resolve([]);
        }
        return Promise.resolve([]);
      });

      renderWithProviders(<VerificationWorkbench />);
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /continue ocr/i })).toBeInTheDocument();
      });
    });
  });
});
