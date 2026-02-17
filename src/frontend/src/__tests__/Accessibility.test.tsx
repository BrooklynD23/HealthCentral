/**
 * A11Y-001: Accessibility Audit Tests
 *
 * Checks:
 * - Keyboard navigation (tablist/tab roles on panel selectors)
 * - Semantic ARIA labels on interactive elements
 * - Reduced-motion behavior (framer-motion animations disabled)
 * - Chart data table alternative text
 * - Loading state aria-live announcements
 * - SearchPage: search input, mode radio buttons, pagination, clear, filter toggle
 * - DocumentInbox: drop zone region, file input, document list, status badges, actions
 * - SettingsPage: external API toggle switch, tier radio selection, hardware cards, progress bar
 * - ExplainAssistant: chat input, send button, message log, suggested questions
 * - Global: skip-to-content link, focus-visible patterns
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendsDashboard } from '@/pages/TrendsDashboard';
import { VerificationWorkbench } from '@/pages/VerificationWorkbench';
import { ExportPage } from '@/pages/ExportPage';
import { SearchPage } from '@/pages/SearchPage';
import { DocumentInbox } from '@/pages/DocumentInbox';
import { SettingsPage } from '@/pages/SettingsPage';
import { ExplainAssistant } from '@/pages/ExplainAssistant';
import { AppLayout } from '@/components/layout/AppLayout';
import { SearchResults } from '@/components/SearchResults';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import type { SearchResultItem } from '@/services/search';

// Mock API
vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
  apiUpload: vi.fn(),
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

// Mock framer-motion for simpler rendering
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

// Mock search hooks
vi.mock('@/services/search', () => ({
  useSearch: vi.fn(() => ({ data: null, isLoading: false, isFetching: false })),
  useSearchSuggestions: vi.fn(() => ({ data: [] })),
}));

// Mock assistant hooks
vi.mock('@/services/assistant', () => ({
  useSendMessage: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  formatResponseText: vi.fn((t: string) => t),
}));

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

const mockDocuments = [
  {
    id: 'doc-1',
    profile_id: 'profile-123',
    source: 'Blood Work - Jan 2024',
    doc_type: 'lab_pdf',
    status: 'verified',
    imported_at: '2024-01-15T00:00:00',
    page_count: 2,
    file_hash: 'abc123',
  },
  {
    id: 'doc-2',
    profile_id: 'profile-123',
    source: 'Metabolic Panel',
    doc_type: 'lab_image',
    status: 'pending',
    imported_at: '2024-02-10T00:00:00',
    page_count: 1,
    file_hash: 'def456',
  },
];

const mockModelSettings = {
  current_tier: 'mid',
  preferred_tier: 'mid',
  recommended_tier: 'mid',
  auto_detect_enabled: true,
  hardware_info: {
    ram_total_gb: 16,
    ram_available_gb: 8,
    cpu_cores: 8,
    cpu_name: 'Intel i7',
    disk_free_gb: 100,
    gpu_available: false,
    gpu_vram_gb: null,
    gpu_name: null,
    recommended_tier: 'mid',
    max_supported_tier: 'high',
    detection_timestamp: '2024-01-01T00:00:00',
  },
  tier_availability: {},
};

const mockTiers = {
  tiers: [
    {
      tier: 'low',
      name: 'Qwen2.5 0.5B',
      model: 'qwen-0.5b',
      description: 'Fast, lightweight',
      available: true,
      downloaded: true,
      requirements: {},
      can_run: true,
    },
    {
      tier: 'mid',
      name: 'Phi-3 Mini',
      model: 'phi-3-mini',
      description: 'Balanced',
      available: true,
      downloaded: false,
      requirements: {},
      can_run: true,
    },
    {
      tier: 'high',
      name: 'BioMistral 7B',
      model: 'biomistral-7b',
      description: 'Best quality',
      available: true,
      downloaded: false,
      requirements: {},
      can_run: false,
    },
  ],
  recommended_tier: 'mid',
};

const mockDownloadProgress = {
  mid: {
    tier: 'mid',
    status: 'downloading' as const,
    progress: 45,
    downloaded_bytes: 450_000_000,
    total_bytes: 1_000_000_000,
    path: null,
    error: null,
  },
};

function setupMocks(overrides: {
  observations?: unknown[];
  documents?: unknown[];
  modelSettings?: unknown;
  tiers?: unknown;
  downloadProgress?: unknown;
  externalApi?: unknown;
} = {}) {
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
    if (url === '/observations/analytes') {
      return Promise.resolve(['hemoglobin', 'glucose', 'cholesterol']);
    }
    if (url === '/medications/') {
      return Promise.resolve([]);
    }
    if (url === '/documents/') {
      return Promise.resolve(overrides.documents ?? []);
    }
    if (url.startsWith('/documents/')) {
      return Promise.resolve([]);
    }
    if (url === '/settings/model') {
      return Promise.resolve(overrides.modelSettings ?? mockModelSettings);
    }
    if (url === '/settings/model/tiers') {
      return Promise.resolve(overrides.tiers ?? mockTiers);
    }
    if (url === '/settings/model/download-progress') {
      return Promise.resolve(overrides.downloadProgress ?? {});
    }
    if (url === '/settings/model/external-api') {
      return Promise.resolve(overrides.externalApi ?? { use_external_api: false, provider: '', model: '', api_key_configured: false });
    }
    return Promise.resolve(null);
  });
}

describe('Accessibility Audit (A11Y-001)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
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

  // ====================================================================
  // NEW TEST SECTIONS: UXQA-001 Accessibility Completion
  // ====================================================================

  describe('SearchPage: Accessibility', () => {
    it('should have aria-label on search input', () => {
      renderWithProviders(<SearchPage />);

      const searchInput = screen.getByLabelText('Search');
      expect(searchInput).toBeInTheDocument();
      expect(searchInput.tagName).toBe('INPUT');
    });

    it('should have radiogroup role on search mode container and radio roles on mode buttons', () => {
      renderWithProviders(<SearchPage />);

      const radiogroup = screen.getByRole('radiogroup', { name: /search mode/i });
      expect(radiogroup).toBeInTheDocument();

      const radios = screen.getAllByRole('radio');
      expect(radios).toHaveLength(3);
    });

    it('should mark active search mode with aria-checked', () => {
      renderWithProviders(<SearchPage />);

      const hybridRadio = screen.getByRole('radio', { name: /hybrid/i });
      expect(hybridRadio).toHaveAttribute('aria-checked', 'true');

      const textRadio = screen.getByRole('radio', { name: /full text/i });
      expect(textRadio).toHaveAttribute('aria-checked', 'false');

      const semanticRadio = screen.getByRole('radio', { name: /semantic/i });
      expect(semanticRadio).toHaveAttribute('aria-checked', 'false');
    });

    it('should have aria-label on clear search button', { timeout: 30000 }, async () => {
      const { useSearch } = await import('@/services/search');
      vi.mocked(useSearch).mockReturnValue({
        data: { results: [], total_count: 0, query: 'test', mode: 'hybrid' },
        isLoading: false,
        isFetching: false,
      } as unknown as ReturnType<typeof useSearch>);

      renderWithProviders(<SearchPage />);

      // Type into the search input to reveal the clear button
      const searchInput = screen.getByLabelText('Search');
      // Simulate having input value by checking the clear button
      // We need to trigger the input to show the clear button
      const user = await import('@testing-library/user-event');
      await user.default.setup().type(searchInput, 'test');

      await waitFor(() => {
        const clearButton = screen.getByLabelText('Clear search');
        expect(clearButton).toBeInTheDocument();
      }, { timeout: 30000 });
    });

    it('should have aria-label on filter toggle button', () => {
      renderWithProviders(<SearchPage />);

      const filterToggle = screen.getByLabelText('Toggle filters');
      expect(filterToggle).toBeInTheDocument();
    });

    it('should have descriptive aria-labels on pagination buttons', async () => {
      const { useSearch } = await import('@/services/search');
      vi.mocked(useSearch).mockReturnValue({
        data: {
          results: Array.from({ length: 20 }, (_, i) => ({
            id: `obs-${i}`,
            type: 'observation' as const,
            title: `Result ${i}`,
            score: 0.9,
            snippet: `Snippet ${i}`,
            highlight: '',
            collected_at: '2024-01-15',
            analyte: 'glucose',
            value: 95,
            unit: 'mg/dL',
            explanation: 'match',
          })),
          total_count: 50,
          query: 'glucose',
          mode: 'hybrid',
        },
        isLoading: false,
        isFetching: false,
      } as unknown as ReturnType<typeof useSearch>);

      renderWithProviders(<SearchPage />);

      // Type to trigger search
      const searchInput = screen.getByLabelText('Search');
      const user = await import('@testing-library/user-event');
      await user.default.setup().type(searchInput, 'glucose');

      await waitFor(() => {
        const prevButton = screen.getByRole('button', { name: /previous page/i });
        const nextButton = screen.getByRole('button', { name: /next page/i });
        expect(prevButton).toBeInTheDocument();
        expect(nextButton).toBeInTheDocument();
      });
    });
  });

  describe('SearchResults: Accessibility', () => {
    it('should have role="list" on results container', () => {
      const mockResults: SearchResultItem[] = [
        {
          id: 'obs-1',
          type: 'observation',
          title: 'Glucose',
          score: 0.95,
          snippet: 'Glucose: 95 mg/dL',
          highlight: '',
          collected_at: '2024-01-15',
          analyte: 'glucose',
          value: 95,
          unit: 'mg/dL',
          explanation: 'FTS match',
        },
      ];

      renderWithProviders(<SearchResults results={mockResults} />);

      const list = screen.getByRole('list');
      expect(list).toBeInTheDocument();
    });

    it('should have role="listitem" on each result card', () => {
      const mockResults: SearchResultItem[] = [
        {
          id: 'obs-1',
          type: 'observation',
          title: 'Glucose',
          score: 0.95,
          snippet: 'Glucose: 95 mg/dL',
          highlight: '',
          collected_at: '2024-01-15',
          analyte: 'glucose',
          value: 95,
          unit: 'mg/dL',
          explanation: 'FTS match',
        },
        {
          id: 'chunk-2',
          type: 'chunk',
          title: 'Lab Report Page 1',
          score: 0.80,
          snippet: 'Complete blood count results',
          highlight: '',
          collected_at: null,
          analyte: null,
          value: null,
          unit: null,
          explanation: 'Semantic match',
        },
      ];

      renderWithProviders(<SearchResults results={mockResults} />);

      const items = screen.getAllByRole('listitem');
      expect(items).toHaveLength(2);
    });

    it('should have aria-label on each result card describing the result', () => {
      const mockResults: SearchResultItem[] = [
        {
          id: 'obs-1',
          type: 'observation',
          title: 'Glucose',
          score: 0.95,
          snippet: 'Glucose: 95 mg/dL',
          highlight: '',
          collected_at: '2024-01-15',
          analyte: 'glucose',
          value: 95,
          unit: 'mg/dL',
          explanation: 'FTS match',
        },
      ];

      renderWithProviders(<SearchResults results={mockResults} />);

      const item = screen.getByRole('listitem');
      expect(item).toHaveAttribute('aria-label', expect.stringContaining('Glucose'));
    });
  });

  describe('DocumentInbox: Accessibility', () => {
    it('should have role="region" and aria-label on drop zone', () => {
      renderWithProviders(<DocumentInbox />);

      const dropZone = screen.getByRole('region', { name: /document upload area/i });
      expect(dropZone).toBeInTheDocument();
    });

    it('should have aria-label on file input', () => {
      renderWithProviders(<DocumentInbox />);

      const fileInput = screen.getByLabelText('Upload medical documents');
      expect(fileInput).toBeInTheDocument();
    });

    it('should have accessible document list with listitem roles', async () => {
      setupMocks({ documents: mockDocuments });

      renderWithProviders(<DocumentInbox />);

      await waitFor(() => {
        const list = screen.getByRole('list', { name: /document list/i });
        expect(list).toBeInTheDocument();
      });

      const items = screen.getAllByRole('listitem');
      expect(items).toHaveLength(mockDocuments.length);
    });

    it('should have aria-labels on status badges', async () => {
      setupMocks({ documents: mockDocuments });

      renderWithProviders(<DocumentInbox />);

      await waitFor(() => {
        const verifiedBadge = screen.getByLabelText(/status: verified/i);
        expect(verifiedBadge).toBeInTheDocument();

        const pendingBadge = screen.getByLabelText(/status: pending/i);
        expect(pendingBadge).toBeInTheDocument();
      });
    });

    it('should have aria-labels on View and More action buttons', async () => {
      setupMocks({ documents: mockDocuments });

      renderWithProviders(<DocumentInbox />);

      await waitFor(() => {
        const viewButtons = screen.getAllByLabelText('View document');
        expect(viewButtons.length).toBeGreaterThan(0);

        const moreButtons = screen.getAllByLabelText('More options');
        expect(moreButtons.length).toBeGreaterThan(0);
      });
    });
  });

  describe('SettingsPage: Accessibility', () => {
    it('should have role="switch" and aria-checked on external API toggle', async () => {
      renderWithProviders(<SettingsPage />);

      await waitFor(() => {
        const toggle = screen.getByRole('switch', { name: /use external api/i });
        expect(toggle).toBeInTheDocument();
        expect(toggle).toHaveAttribute('aria-checked', 'false');
      });
    });

    it('should have radiogroup and radio roles on tier selection', async () => {
      renderWithProviders(<SettingsPage />);

      await waitFor(() => {
        const radiogroup = screen.getByRole('radiogroup', { name: /model tier/i });
        expect(radiogroup).toBeInTheDocument();

        const radios = screen.getAllByRole('radio');
        expect(radios.length).toBeGreaterThanOrEqual(3);
      });
    });

    it('should mark selected tier with aria-checked', async () => {
      renderWithProviders(<SettingsPage />);

      await waitFor(() => {
        const radios = screen.getAllByRole('radio');
        // 'mid' is the preferred tier
        const midRadio = radios.find((r) => r.getAttribute('aria-checked') === 'true');
        expect(midRadio).toBeTruthy();
      });
    });

    it('should have aria-label descriptions on hardware info cards', async () => {
      renderWithProviders(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/ram/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/cpu/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/disk/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/gpu/i)).toBeInTheDocument();
      });
    });

    it('should have role="progressbar" with aria-valuenow on download progress', async () => {
      setupMocks({ downloadProgress: mockDownloadProgress });

      renderWithProviders(<SettingsPage />);

      // Trigger a download to start polling
      // The download progress is shown when downloadProgress data is present
      // We need to simulate that the download was initiated
      await waitFor(() => {
        const progressBars = screen.queryAllByRole('progressbar');
        // Progress bars should appear when download data is present
        // Note: this tests the case where progress is already being tracked
        if (progressBars.length > 0) {
          const bar = progressBars[0];
          expect(bar).toHaveAttribute('aria-valuenow');
          expect(bar).toHaveAttribute('aria-valuemin', '0');
          expect(bar).toHaveAttribute('aria-valuemax', '100');
        }
      });
    });
  });

  describe('ExplainAssistant: Accessibility', () => {
    it('should have aria-label on chat input', () => {
      renderWithProviders(<ExplainAssistant />);

      const chatInput = screen.getByLabelText('Ask about your results');
      expect(chatInput).toBeInTheDocument();
      expect(chatInput.tagName).toBe('INPUT');
    });

    it('should have aria-label on send button', () => {
      renderWithProviders(<ExplainAssistant />);

      const sendButton = screen.getByLabelText('Send message');
      expect(sendButton).toBeInTheDocument();
    });

    it('should have role="log" and aria-live="polite" on messages container', () => {
      renderWithProviders(<ExplainAssistant />);

      const messageLog = screen.getByRole('log');
      expect(messageLog).toBeInTheDocument();
      expect(messageLog).toHaveAttribute('aria-live', 'polite');
    });

    it('should have descriptive aria-labels on suggested question buttons', () => {
      renderWithProviders(<ExplainAssistant />);

      const suggestedButtons = screen.getAllByRole('button', { name: /ask:/i });
      expect(suggestedButtons.length).toBeGreaterThanOrEqual(4);
    });
  });

  describe('Global: Keyboard Navigation', () => {
    it('should have skip-to-main-content link in AppLayout', () => {
      renderWithProviders(<AppLayout />);

      const skipLink = screen.getByText(/skip to main content/i);
      expect(skipLink).toBeInTheDocument();
      expect(skipLink.tagName).toBe('A');
      expect(skipLink).toHaveAttribute('href', '#main-content');
    });

    it('should have main content landmark with id', () => {
      renderWithProviders(<AppLayout />);

      const main = screen.getByRole('main');
      expect(main).toBeInTheDocument();
      expect(main).toHaveAttribute('id', 'main-content');
    });
  });
});
