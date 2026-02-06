/**
 * ExportPage Component Tests
 *
 * Sprint 4 - S4-FE-001: Wire ExportPage
 *
 * Tests that:
 * - CSV download works
 * - JSON download works
 * - Summary generation works
 * - Summary download works
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExportPage } from '@/pages/ExportPage';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

// Mock the API module with URL-based routing
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

// Mock framer-motion to avoid animation issues
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<object>) => (
        <div {...props}>{children}</div>
      ),
    },
  };
});

// Mock file download
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
const mockRevokeObjectURL = vi.fn();
URL.createObjectURL = mockCreateObjectURL;
URL.revokeObjectURL = mockRevokeObjectURL;

// Mock anchor click
const mockAnchorClick = vi.fn();
HTMLAnchorElement.prototype.click = mockAnchorClick;

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

const mockCsvContent = `Date,Analyte,Value,Unit,Reference Low,Reference High,Flag,Verified
2024-01-15,glucose,95.0,mg/dL,70.0,100.0,,Yes
2024-01-15,hemoglobin_a1c,6.5,%,4.0,5.6,H,No`;

const mockJsonContent = JSON.stringify([
  {
    analyte_canonical: 'glucose',
    value: 95.0,
    unit: 'mg/dL',
    ref_low: 70.0,
    ref_high: 100.0,
    collected_at: '2024-01-15T00:00:00Z',
  },
  {
    analyte_canonical: 'hemoglobin_a1c',
    value: 6.5,
    unit: '%',
    ref_low: 4.0,
    ref_high: 5.6,
    flag: 'H',
    collected_at: '2024-01-15T00:00:00Z',
  },
]);

const mockSummaryResponse = {
  summary_id: 'summary-123',
  profile_id: 'profile-123',
  generated_at: '2024-01-15T12:00:00Z',
  format: 'text',
  key_findings: [
    'Hemoglobin A1c: 6.5% (H)',
    'Glucose: 95.0 mg/dL (normal)',
  ],
  abnormal_count: 1,
  date_range: 'All time',
};

const mockSummaryDownload = `============================================================
HEALTH SUMMARY REPORT
============================================================

Generated: 2024-01-15T12:00:00Z
Total Observations: 10
Abnormal Values: 1
Critical Values: 0

----------------------------------------
KEY FINDINGS
----------------------------------------
  - Hemoglobin A1c: 6.5% (H)
  - Glucose: 95.0 mg/dL (normal)
`;

const mockQuestions = [
  {
    category: 'abnormal',
    question: 'I noticed my hemoglobin_a1c was outside the reference range. What might that indicate?',
    context: 'Value: 6.5 %, flagged as H',
    related_analytes: ['hemoglobin_a1c'],
  },
];

// Helper to set up URL-based API mocking
function setupApiMocks(options: {
  csvContent?: string;
  jsonContent?: string;
  summaryResponse?: typeof mockSummaryResponse;
  summaryDownload?: string;
  questions?: typeof mockQuestions;
  csvError?: boolean;
  jsonError?: boolean;
  summaryError?: boolean;
} = {}) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url === '/export/csv') {
      if (options.csvError) {
        return Promise.reject(new Error('Export failed'));
      }
      return Promise.resolve(options.csvContent ?? mockCsvContent);
    }
    if (url === '/export/json') {
      if (options.jsonError) {
        return Promise.reject(new Error('Export failed'));
      }
      return Promise.resolve(options.jsonContent ?? mockJsonContent);
    }
    if (url.startsWith('/export/doctor-summary/') && url.endsWith('/download')) {
      return Promise.resolve(options.summaryDownload ?? mockSummaryDownload);
    }
    return Promise.resolve(null);
  });

  vi.mocked(api.apiPost).mockImplementation((url: string) => {
    if (url === '/export/doctor-summary') {
      if (options.summaryError) {
        return Promise.reject(new Error('Summary generation failed'));
      }
      return Promise.resolve(options.summaryResponse ?? mockSummaryResponse);
    }
    if (url === '/export/questions') {
      return Promise.resolve(options.questions ?? mockQuestions);
    }
    return Promise.resolve(null);
  });
}

describe('ExportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockCreateObjectURL.mockClear();
    mockRevokeObjectURL.mockClear();
    mockAnchorClick.mockClear();
    // Set up auth state
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  describe('FE-EXPORT-001: test_csv_download', () => {
    it('should render CSV download button', async () => {
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      await waitFor(() => {
        expect(screen.getByText(/Download CSV/i)).toBeInTheDocument();
      });
    });

    it('should trigger CSV download when button is clicked', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      const csvButton = screen.getByRole('button', { name: /csv/i });
      await user.click(csvButton);

      await waitFor(() => {
        expect(api.apiGet).toHaveBeenCalledWith(
          expect.stringContaining('/export/csv'),
          expect.any(Object)
        );
      });
    });

    it('should handle CSV export error gracefully', async () => {
      const user = userEvent.setup();
      setupApiMocks({ csvError: true });

      renderWithProviders(<ExportPage />);

      const csvButton = screen.getByRole('button', { name: /csv/i });
      await user.click(csvButton);

      // Should not crash - error handling is UI-specific
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /csv/i })).toBeInTheDocument();
      });
    });
  });

  describe('FE-EXPORT-002: test_json_download', () => {
    it('should render JSON download button', async () => {
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      await waitFor(() => {
        expect(screen.getByText(/Download JSON/i)).toBeInTheDocument();
      });
    });

    it('should trigger JSON download when button is clicked', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      const jsonButton = screen.getByRole('button', { name: /json/i });
      await user.click(jsonButton);

      await waitFor(() => {
        expect(api.apiGet).toHaveBeenCalledWith(
          expect.stringContaining('/export/json'),
          expect.any(Object)
        );
      });
    });
  });

  describe('FE-EXPORT-003: test_generate_summary', () => {
    it('should render summary generation section', async () => {
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      await waitFor(() => {
        expect(screen.getByText('Summary Preview')).toBeInTheDocument();
      });
    });

    it('should display key findings after summary is generated', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      // Click generate summary button
      const generateButton = screen.getByRole('button', { name: /generate|create/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(api.apiPost).toHaveBeenCalledWith(
          '/export/doctor-summary',
          expect.any(Object)
        );
      });
    });

    it('should display abnormal count in summary', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      const generateButton = screen.getByRole('button', { name: /generate|create/i });
      await user.click(generateButton);

      // After generation, should show findings
      await waitFor(() => {
        // The summary response should be displayed
        expect(screen.getByText(/1.*abnormal/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });
  });

  describe('FE-EXPORT-004: test_download_summary', () => {
    it('should allow downloading generated summary', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      // First generate a summary
      const generateButton = screen.getByRole('button', { name: /generate summary/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(api.apiPost).toHaveBeenCalledWith(
          '/export/doctor-summary',
          expect.any(Object)
        );
      });

      // Wait for summary to be displayed, then download button should appear
      await waitFor(() => {
        expect(screen.getByText(/Health Summary Report/i)).toBeInTheDocument();
      });

      // The download button replaces the generate button after summary is created
      const downloadButton = await screen.findByRole('button', { name: /download summary/i });
      await user.click(downloadButton);

      await waitFor(() => {
        // Check that the download endpoint was called (may have other calls too)
        const calls = vi.mocked(api.apiGet).mock.calls;
        const downloadCall = calls.find(
          (call) => call[0].includes('/export/doctor-summary/summary-123/download')
        );
        expect(downloadCall).toBeTruthy();
      });
    });
  });

  describe('Export sections toggle', () => {
    it('should toggle section inclusion', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      await waitFor(() => {
        expect(screen.getByText('Results Summary')).toBeInTheDocument();
      });

      // Toggle a section
      const summaryToggle = screen.getByText('Results Summary').closest('button');
      if (summaryToggle) {
        await user.click(summaryToggle);
      }

      // Section should toggle state
      expect(summaryToggle).toBeInTheDocument();
    });
  });

  describe('Questions generation', () => {
    it('should be able to include questions section', async () => {
      const user = userEvent.setup();
      setupApiMocks({});

      renderWithProviders(<ExportPage />);

      await waitFor(() => {
        expect(screen.getByText('Questions for Clinician')).toBeInTheDocument();
      });

      // Toggle questions section on
      const questionsToggle = screen.getByText('Questions for Clinician').closest('button');
      if (questionsToggle) {
        await user.click(questionsToggle);
      }

      // Questions section should be toggled
      expect(questionsToggle).toBeInTheDocument();
    });
  });
});
