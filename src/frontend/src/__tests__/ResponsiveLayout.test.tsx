/**
 * UXQA-002: Mobile Responsiveness Tests
 *
 * Validates responsive layouts across breakpoints.
 * Tests that Tailwind responsive classes are applied correctly
 * so layouts adapt from mobile-first stacked to desktop grid.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

// ---------- Mocks ----------

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
  apiUpload: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public statusText: string,
      message: string,
    ) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        // Filter out framer-motion props that are not valid HTML attributes
        const validProps: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(props)) {
          if (
            !['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover', 'whileTap', 'layout'].includes(key)
          ) {
            validProps[key] = value;
          }
        }
        return <div {...validProps}>{children}</div>;
      },
      tr: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        const validProps: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(props)) {
          if (
            !['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover', 'whileTap', 'layout'].includes(key)
          ) {
            validProps[key] = value;
          }
        }
        return <tr {...validProps}>{children}</tr>;
      },
      button: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        const validProps: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(props)) {
          if (
            !['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover', 'whileTap', 'layout'].includes(key)
          ) {
            validProps[key] = value;
          }
        }
        return <button {...validProps}>{children}</button>;
      },
    },
  };
});

// ---------- Helpers ----------

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
    </QueryClientProvider>,
  );
}

// Default API mock that returns sensible data for all pages
function setupDefaultApiMocks() {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url === '/observations/') {
      return Promise.resolve([
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
          collected_at: '2024-12-15T00:00:00',
          extraction_confidence: 0.95,
          ref_range_text: '12.0-17.5',
          value_text: null,
        },
      ]);
    }
    if (url.startsWith('/observations/trends/')) {
      return Promise.resolve({
        analyte_canonical: 'hemoglobin',
        analyte_display_name: 'HEMOGLOBIN',
        unit: 'g/dL',
        ref_low: 12.0,
        ref_high: 17.5,
        data_points: [
          { date: '2024-12-15T00:00:00', value: 14.2, unit: 'g/dL', is_abnormal: false, flag: null, doc_id: 'doc-1' },
        ],
        summary: 'Hemoglobin trend looks stable.',
      });
    }
    if (url.startsWith('/observations/panels/')) {
      return Promise.resolve({
        panel_id: 'cbc',
        panel_name: 'Complete Blood Count',
        observations: [],
        collection_date: '2024-12-15T00:00:00',
      });
    }
    if (url === '/medications/') {
      return Promise.resolve([]);
    }
    if (url === '/documents/') {
      return Promise.resolve([
        {
          id: 'doc-1',
          profile_id: 'profile-123',
          source: 'Lab Report',
          doc_type: 'lab_pdf',
          status: 'parsed',
          imported_at: '2024-12-15T00:00:00',
          collection_date: '2024-12-15',
        },
      ]);
    }
    if (url === '/search') {
      return Promise.resolve({
        results: [],
        total_count: 0,
        query: '',
        mode: 'hybrid',
      });
    }
    if (url === '/observations/analytes') {
      return Promise.resolve(['hemoglobin', 'glucose']);
    }
    return Promise.resolve(null);
  });

  vi.mocked(api.apiPost).mockImplementation(() => Promise.resolve(null));
  if (api.apiGetRaw) {
    vi.mocked(api.apiGetRaw).mockImplementation(() =>
      Promise.resolve(new Response()),
    );
  }
}

// ---------- Lazy imports (to avoid hoisting issues with vi.mock) ----------

async function importTrendsDashboard() {
  const mod = await import('@/pages/TrendsDashboard');
  return mod.TrendsDashboard;
}

async function importSearchPage() {
  const mod = await import('@/pages/SearchPage');
  return mod.SearchPage;
}

async function importExportPage() {
  const mod = await import('@/pages/ExportPage');
  return mod.ExportPage;
}

async function importDocumentInbox() {
  const mod = await import('@/pages/DocumentInbox');
  return mod.DocumentInbox;
}

async function importVerificationWorkbench() {
  const mod = await import('@/pages/VerificationWorkbench');
  return mod.VerificationWorkbench;
}

async function importExplainAssistant() {
  const mod = await import('@/pages/ExplainAssistant');
  return mod.ExplainAssistant;
}

// ---------- Tests ----------

describe('UXQA-002: Mobile Responsiveness', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();

    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });

    setupDefaultApiMocks();
  });

  afterEach(() => {
    // Restore default matchMedia (setup.ts sets this)
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  // ------------------------------------------------------------------
  // a) TrendsDashboard responsive layout
  // ------------------------------------------------------------------
  describe('TrendsDashboard responsive layout', () => {
    it('uses responsive grid classes (grid-cols-1 md:grid-cols-3)', async () => {
      const TrendsDashboard = await importTrendsDashboard();
      const { container } = renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Trends Dashboard')).toBeInTheDocument();
      }, { timeout: 120000 });

      // The main layout grid should use responsive breakpoints
      const grid = container.querySelector('.grid');
      expect(grid).not.toBeNull();
      expect(grid?.className).toContain('grid-cols-1');
      expect(grid?.className).toContain('md:grid-cols-3');
    }, 120000);

    it('uses responsive col-span (md:col-span-2)', async () => {
      const TrendsDashboard = await importTrendsDashboard();
      const { container } = renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Trends Dashboard')).toBeInTheDocument();
      });

      const mainCol = container.querySelector('.md\\:col-span-2');
      expect(mainCol).not.toBeNull();
    });

    it('panel tabs use flex-wrap for small screens', async () => {
      const TrendsDashboard = await importTrendsDashboard();
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByText('CBC')).toBeInTheDocument();
      });

      const tabContainer = screen.getByRole('tablist');
      expect(tabContainer.className).toContain('flex-wrap');
    });

    it('header buttons wrap on mobile with flex-wrap gap-2', async () => {
      const TrendsDashboard = await importTrendsDashboard();
      const { container } = renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Trends Dashboard')).toBeInTheDocument();
      });

      // The header action buttons container should have flex-wrap
      const headerButtons = container.querySelector('.flex.items-center.flex-wrap');
      expect(headerButtons).not.toBeNull();
    });

    it('chart container maintains minimum height on mobile', async () => {
      const TrendsDashboard = await importTrendsDashboard();
      const { container } = renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });

      // Chart wrapper should have min-h class for mobile
      // The chart container is wrapped in h-72 which provides fixed mobile height.
      const chartArea = container.querySelector('[class*="h-72"]');
      expect(chartArea).not.toBeNull();
    });
  });

  // ------------------------------------------------------------------
  // b) SearchPage responsive layout
  // ------------------------------------------------------------------
  describe('SearchPage responsive layout', () => {
    it('uses responsive grid classes (grid-cols-1 md:grid-cols-3)', async () => {
      const SearchPage = await importSearchPage();
      const { container } = renderWithProviders(<SearchPage />);

      const grid = container.querySelector('.grid');
      expect(grid).not.toBeNull();
      expect(grid?.className).toContain('grid-cols-1');
      expect(grid?.className).toContain('md:grid-cols-3');
    });

    it('main content area uses md:col-span-2', async () => {
      const SearchPage = await importSearchPage();
      const { container } = renderWithProviders(<SearchPage />);

      const mainCol = container.querySelector('.md\\:col-span-2');
      expect(mainCol).not.toBeNull();
    });

    it('search input takes full width', async () => {
      const SearchPage = await importSearchPage();
      renderWithProviders(<SearchPage />);

      const input = screen.getByPlaceholderText(/search analytes/i);
      expect(input.className).toContain('w-full');
    });

    it('filters sidebar is hidden on mobile by default', async () => {
      const SearchPage = await importSearchPage();
      const { container } = renderWithProviders(<SearchPage />);

      // Sidebar should have hidden md:block classes for mobile hiding
      const sidebar = container.querySelector('.hidden.md\\:block');
      expect(sidebar).not.toBeNull();
    });
  });

  // ------------------------------------------------------------------
  // c) ExportPage responsive layout
  // ------------------------------------------------------------------
  describe('ExportPage responsive layout', () => {
    it('uses responsive grid classes (grid-cols-1 md:grid-cols-3)', async () => {
      const ExportPage = await importExportPage();
      const { container } = renderWithProviders(<ExportPage />);

      const grid = container.querySelector('.grid');
      expect(grid).not.toBeNull();
      expect(grid?.className).toContain('grid-cols-1');
      expect(grid?.className).toContain('md:grid-cols-3');
    });

    it('main content uses md:col-span-2', async () => {
      const ExportPage = await importExportPage();
      const { container } = renderWithProviders(<ExportPage />);

      const mainCol = container.querySelector('.md\\:col-span-2');
      expect(mainCol).not.toBeNull();
    });

    it('export buttons wrap on mobile with flex-wrap', async () => {
      const ExportPage = await importExportPage();
      const { container } = renderWithProviders(<ExportPage />);

      // The header buttons container should have flex-wrap
      const buttonsContainer = container.querySelector('.flex.items-center.flex-wrap');
      expect(buttonsContainer).not.toBeNull();
    });
  });

  // ------------------------------------------------------------------
  // d) DocumentInbox responsive layout
  // ------------------------------------------------------------------
  describe('DocumentInbox responsive layout', () => {
    it('document list items use responsive stacking', async () => {
      const DocumentInbox = await importDocumentInbox();
      const { container } = renderWithProviders(<DocumentInbox />);

      await waitFor(() => {
        expect(screen.getAllByText('Lab Report').length).toBeGreaterThan(0);
      });

      // Document items should have flex-col md:flex-row for stacking on mobile
      const docItem = container.querySelector('.flex-col.md\\:flex-row, .flex.md\\:flex-row');
      // Alternatively, look for items in the document list
      expect(docItem).not.toBeNull();
    });

    it('action buttons are always visible on mobile (not hover-only)', async () => {
      const DocumentInbox = await importDocumentInbox();
      const { container } = renderWithProviders(<DocumentInbox />);

      await waitFor(() => {
        expect(screen.getAllByText('Lab Report').length).toBeGreaterThan(0);
      });

      // Action buttons should use md:opacity-0 md:group-hover:opacity-100
      // (visible by default, hidden only on desktop until hover)
      const actionContainer = container.querySelector(
        '[class*="md:opacity-0"][class*="md:group-hover:opacity-100"]',
      );
      expect(actionContainer).not.toBeNull();
    });
  });

  // ------------------------------------------------------------------
  // e) VerificationWorkbench responsive layout
  // ------------------------------------------------------------------
  describe('VerificationWorkbench responsive layout', () => {
    it('uses responsive grid classes (grid-cols-1 md:grid-cols-3)', async () => {
      const VerificationWorkbench = await importVerificationWorkbench();
      const { container } = renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(screen.getByText('Verification Workbench')).toBeInTheDocument();
      });

      const grid = container.querySelector('.grid');
      expect(grid).not.toBeNull();
      expect(grid?.className).toContain('grid-cols-1');
      expect(grid?.className).toContain('md:grid-cols-3');
    });

    it('main content uses md:col-span-2', async () => {
      const VerificationWorkbench = await importVerificationWorkbench();
      const { container } = renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(screen.getByText('Verification Workbench')).toBeInTheDocument();
      });

      const mainCol = container.querySelector('.md\\:col-span-2');
      expect(mainCol).not.toBeNull();
    });

    it('table has responsive horizontal scroll (overflow-x-auto)', async () => {
      const VerificationWorkbench = await importVerificationWorkbench();
      const { container } = renderWithProviders(<VerificationWorkbench />);

      await waitFor(() => {
        expect(screen.getByText('Verification Workbench')).toBeInTheDocument();
      });

      // The table container should have overflow-x-auto
      const scrollContainer = container.querySelector('.overflow-x-auto');
      expect(scrollContainer).not.toBeNull();
    });
  });

  // ------------------------------------------------------------------
  // f) ExplainAssistant responsive layout
  // ------------------------------------------------------------------
  describe('ExplainAssistant responsive layout', () => {
    it('uses flex-col md:flex-row for mobile stacking', async () => {
      const ExplainAssistant = await importExplainAssistant();
      const { container } = renderWithProviders(<ExplainAssistant />);

      // Top-level container should have flex-col md:flex-row
      const flexContainer = container.querySelector('.flex.flex-col.md\\:flex-row');
      expect(flexContainer).not.toBeNull();
    });

    it('sidebar uses full width on mobile (w-full md:w-80)', async () => {
      const ExplainAssistant = await importExplainAssistant();
      const { container } = renderWithProviders(<ExplainAssistant />);

      const sidebar = container.querySelector('.w-full.md\\:w-80');
      expect(sidebar).not.toBeNull();
    });
  });

  // ------------------------------------------------------------------
  // g) Touch target sizes
  // ------------------------------------------------------------------
  describe('Touch target sizes', () => {
    it('TrendsDashboard panel tab buttons have min-h-[44px] for touch targets', async () => {
      const TrendsDashboard = await importTrendsDashboard();
      renderWithProviders(<TrendsDashboard />);

      await waitFor(() => {
        expect(screen.getByText('CBC')).toBeInTheDocument();
      });

      const cbcTab = screen.getByRole('tab', { name: /cbc/i });
      expect(cbcTab.className).toContain('min-h-[44px]');
    });

    it('SearchPage search mode buttons have min-h-[44px]', async () => {
      const SearchPage = await importSearchPage();
      renderWithProviders(<SearchPage />);

      // Search mode buttons should have adequate touch targets
      const hybridButton = screen.getByText(/hybrid/i).closest('button');
      expect(hybridButton?.className).toContain('min-h-[44px]');
    });

    it('ExportPage section toggle buttons have adequate padding for touch (min-h-[44px])', async () => {
      const ExportPage = await importExportPage();
      renderWithProviders(<ExportPage />);

      const sectionButton = screen.getByText('Results Summary').closest('button');
      expect(sectionButton?.className).toContain('min-h-[44px]');
    });
  });
});
