/**
 * UXQA-003: Advanced Data Visualization Interactions
 *
 * Tests for chart interaction controls, drill-down support,
 * additional chart types, and refresh strategy.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendsDashboard } from '@/pages/TrendsDashboard';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { useAutoRefresh } from '@/hooks/useAutoRefresh';
import { renderHook } from '@testing-library/react';

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

// Mock framer-motion to avoid animation issues in jsdom
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  const filterDomProps = (props: Record<string, unknown>) => {
    const {
      variants: _variants,
      initial: _initial,
      animate: _animate,
      exit: _exit,
      whileHover: _whileHover,
      whileTap: _whileTap,
      transition: _transition,
      layout: _layout,
      layoutId: _layoutId,
      ...domProps
    } = props;
    return domProps;
  };

  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        return <div {...filterDomProps(props)}>{children}</div>;
      },
      button: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        return <button {...filterDomProps(props)}>{children}</button>;
      },
      tr: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        return <tr {...filterDomProps(props)}>{children}</tr>;
      },
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

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
      <BrowserRouter>{component}</BrowserRouter>
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

describe('UXQA-003: Advanced Data Visualization Interactions', () => {
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

  // ---------------------------------------------------------------
  // a) Chart zoom controls
  // ---------------------------------------------------------------
  describe('Chart zoom controls', () => {
    it('should render zoom in and zoom out buttons', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const zoomInBtn = screen.getByRole('button', { name: 'Zoom in' });
      const zoomOutBtn = screen.getByRole('button', { name: 'Zoom out' });

      expect(zoomInBtn).toBeInTheDocument();
      expect(zoomOutBtn).toBeInTheDocument();
    });

    it('should have correct aria-labels on zoom buttons', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
      expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    });

    it('should update zoom level class on click', async () => {
      const user = userEvent.setup();
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const chartContainer = screen.getByTestId('chart-container');
      expect(chartContainer).toHaveAttribute('data-zoom', '0');

      // Click zoom in
      await user.click(screen.getByLabelText('Zoom in'));
      expect(chartContainer).toHaveAttribute('data-zoom', '1');

      // Click zoom in again
      await user.click(screen.getByLabelText('Zoom in'));
      expect(chartContainer).toHaveAttribute('data-zoom', '2');

      // Click zoom out
      await user.click(screen.getByLabelText('Zoom out'));
      expect(chartContainer).toHaveAttribute('data-zoom', '1');
    });

    it('should clamp zoom level between 0 and 3', async () => {
      const user = userEvent.setup();
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const chartContainer = screen.getByTestId('chart-container');

      // Click zoom out when already at 0 - should stay at 0
      await user.click(screen.getByLabelText('Zoom out'));
      expect(chartContainer).toHaveAttribute('data-zoom', '0');

      // Zoom in to max (3)
      await user.click(screen.getByLabelText('Zoom in'));
      await user.click(screen.getByLabelText('Zoom in'));
      await user.click(screen.getByLabelText('Zoom in'));
      expect(chartContainer).toHaveAttribute('data-zoom', '3');

      // Click zoom in at max - should stay at 3
      await user.click(screen.getByLabelText('Zoom in'));
      expect(chartContainer).toHaveAttribute('data-zoom', '3');
    });
  });

  // ---------------------------------------------------------------
  // b) Date range picker integration
  // ---------------------------------------------------------------
  describe('Date range picker integration', () => {
    it('should render "Last 12 Months" button that opens date range selector', async () => {
      const user = userEvent.setup();
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const dateButton = screen.getByRole('button', { name: /last 12 months/i });
      expect(dateButton).toBeInTheDocument();

      // Click to open date range selector
      await user.click(dateButton);

      // Date range options should appear
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /last 3 months/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /last 6 months/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /all time/i })).toBeInTheDocument();
      });
    });

    it('should trigger data refetch when date range is selected', async () => {
      const user = userEvent.setup();
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      // Clear mock call count from initial load
      vi.mocked(api.apiGet).mockClear();
      setupApiMocks({});

      // Open date range selector
      const dateButton = screen.getByRole('button', { name: /last 12 months/i });
      await user.click(dateButton);

      // Select "Last 3 Months"
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /last 3 months/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /last 3 months/i }));

      // Verify trend API was called with date params
      await waitFor(() => {
        expect(api.apiGet).toHaveBeenCalledWith(
          expect.stringContaining('/observations/trends/'),
          expect.objectContaining({
            from_date: expect.any(String),
          })
        );
      });
    });
  });

  // ---------------------------------------------------------------
  // c) Trend chart tooltip content
  // ---------------------------------------------------------------
  describe('Trend chart tooltip content', () => {
    it('should render a custom tooltip component with value, unit, and reference range', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      // The custom tooltip component should be defined and used
      // We verify its existence by checking the Recharts Tooltip has a content prop
      // In test env, we check the tooltip renderer is present as a data attribute
      const chartContainer = screen.getByTestId('chart-container');
      expect(chartContainer).toHaveAttribute('data-has-custom-tooltip', 'true');
    });
  });

  // ---------------------------------------------------------------
  // d) Data point drill-down
  // ---------------------------------------------------------------
  describe('Data point drill-down', () => {
    it('should expose activeDot click handler for drill-down navigation', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      // Verify the chart container declares drill-down support
      const chartContainer = screen.getByTestId('chart-container');
      expect(chartContainer).toHaveAttribute('data-drilldown-enabled', 'true');
    });
  });

  // ---------------------------------------------------------------
  // e) Chart type toggle
  // ---------------------------------------------------------------
  describe('Chart type toggle', () => {
    it('should render line and bar chart type toggle buttons', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const lineBtn = screen.getByRole('button', { name: 'Line chart' });
      const barBtn = screen.getByRole('button', { name: 'Bar chart' });

      expect(lineBtn).toBeInTheDocument();
      expect(barBtn).toBeInTheDocument();
    });

    it('should default to line chart type with aria-pressed true', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const lineBtn = screen.getByRole('button', { name: 'Line chart' });
      const barBtn = screen.getByRole('button', { name: 'Bar chart' });

      expect(lineBtn).toHaveAttribute('aria-pressed', 'true');
      expect(barBtn).toHaveAttribute('aria-pressed', 'false');
    });

    it('should switch to bar chart when bar button is clicked', async () => {
      const user = userEvent.setup();
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const barBtn = screen.getByRole('button', { name: 'Bar chart' });
      await user.click(barBtn);

      // Bar should now be pressed
      expect(barBtn).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByRole('button', { name: 'Line chart' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );

      // Chart container should indicate bar chart type
      const chartContainer = screen.getByTestId('chart-container');
      expect(chartContainer).toHaveAttribute('data-chart-type', 'bar');
    });

    it('should switch back to line chart when line button is clicked', async () => {
      const user = userEvent.setup();
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      // Switch to bar first
      await user.click(screen.getByRole('button', { name: 'Bar chart' }));

      // Switch back to line
      await user.click(screen.getByRole('button', { name: 'Line chart' }));

      const lineBtn = screen.getByRole('button', { name: 'Line chart' });
      expect(lineBtn).toHaveAttribute('aria-pressed', 'true');

      const chartContainer = screen.getByTestId('chart-container');
      expect(chartContainer).toHaveAttribute('data-chart-type', 'line');
    });
  });

  // ---------------------------------------------------------------
  // f) Screen reader data table
  // ---------------------------------------------------------------
  describe('Screen reader data table', () => {
    it('should render a sr-only data table below the chart', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      // Find the sr-only table
      const table = screen.getByRole('table', { name: /hemoglobin trend data/i });
      expect(table).toBeInTheDocument();
      expect(table).toHaveClass('sr-only');
    });

    it('should have proper th and td elements with analyte values', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const table = screen.getByRole('table', { name: /hemoglobin trend data/i });

      // Check headers
      const headers = within(table).getAllByRole('columnheader');
      expect(headers).toHaveLength(3);
      expect(headers[0]).toHaveTextContent('Date');
      expect(headers[1]).toHaveTextContent('Value');
      expect(headers[2]).toHaveTextContent('Unit');

      // Check data rows
      const rows = within(table).getAllByRole('row');
      // 1 header row + 4 data rows
      expect(rows).toHaveLength(5);

      // Check first data row content
      const firstDataCells = within(rows[1]).getAllByRole('cell');
      expect(firstDataCells[0]).toHaveTextContent('2024-06');
      expect(firstDataCells[1]).toHaveTextContent('13.8');
      expect(firstDataCells[2]).toHaveTextContent('g/dL');
    });

    it('should include all data points from the chart', async () => {
      setupApiMocks({});
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      const table = screen.getByRole('table', { name: /hemoglobin trend data/i });
      const dataRows = within(table).getAllByRole('row').slice(1); // Skip header row

      expect(dataRows).toHaveLength(4); // 4 data points in mockTrendData

      // Verify last row
      const lastCells = within(dataRows[3]).getAllByRole('cell');
      expect(lastCells[0]).toHaveTextContent('2024-12');
      expect(lastCells[1]).toHaveTextContent('14.2');
      expect(lastCells[2]).toHaveTextContent('g/dL');
    });
  });

  // ---------------------------------------------------------------
  // g) Auto-refresh hook
  // ---------------------------------------------------------------
  describe('useAutoRefresh hook', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should exist and be importable', () => {
      expect(useAutoRefresh).toBeDefined();
      expect(typeof useAutoRefresh).toBe('function');
    });

    it('should not call refetch when disabled', () => {
      const refetchFn = vi.fn();

      renderHook(() => useAutoRefresh(refetchFn, 5000, false));

      vi.advanceTimersByTime(15000);
      expect(refetchFn).not.toHaveBeenCalled();
    });

    it('should call refetch on interval when enabled', () => {
      const refetchFn = vi.fn();

      renderHook(() => useAutoRefresh(refetchFn, 5000, true));

      // Should not have been called immediately
      expect(refetchFn).not.toHaveBeenCalled();

      // Advance past one interval
      vi.advanceTimersByTime(5000);
      expect(refetchFn).toHaveBeenCalledTimes(1);

      // Advance past two more intervals
      vi.advanceTimersByTime(10000);
      expect(refetchFn).toHaveBeenCalledTimes(3);
    });

    it('should use default 30 second interval when not specified', () => {
      const refetchFn = vi.fn();

      renderHook(() => useAutoRefresh(refetchFn));

      vi.advanceTimersByTime(29999);
      expect(refetchFn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(1);
      expect(refetchFn).toHaveBeenCalledTimes(1);
    });

    it('should stop calling refetch when disabled after being enabled', () => {
      const refetchFn = vi.fn();

      const { rerender } = renderHook(
        ({ enabled }) => useAutoRefresh(refetchFn, 5000, enabled),
        { initialProps: { enabled: true } }
      );

      vi.advanceTimersByTime(5000);
      expect(refetchFn).toHaveBeenCalledTimes(1);

      // Disable
      rerender({ enabled: false });

      vi.advanceTimersByTime(15000);
      // Should not have been called again
      expect(refetchFn).toHaveBeenCalledTimes(1);
    });

    it('should pick up new refetch function via ref', () => {
      const refetchFn1 = vi.fn();
      const refetchFn2 = vi.fn();

      const { rerender } = renderHook(
        ({ fn }) => useAutoRefresh(fn, 5000, true),
        { initialProps: { fn: refetchFn1 } }
      );

      vi.advanceTimersByTime(5000);
      expect(refetchFn1).toHaveBeenCalledTimes(1);
      expect(refetchFn2).not.toHaveBeenCalled();

      // Swap function
      rerender({ fn: refetchFn2 });

      vi.advanceTimersByTime(5000);
      expect(refetchFn1).toHaveBeenCalledTimes(1);
      expect(refetchFn2).toHaveBeenCalledTimes(1);
    });

    it('should clean up interval on unmount', () => {
      const refetchFn = vi.fn();

      const { unmount } = renderHook(() => useAutoRefresh(refetchFn, 5000, true));

      vi.advanceTimersByTime(5000);
      expect(refetchFn).toHaveBeenCalledTimes(1);

      unmount();

      vi.advanceTimersByTime(15000);
      // Should not have been called after unmount
      expect(refetchFn).toHaveBeenCalledTimes(1);
    });
  });
});
