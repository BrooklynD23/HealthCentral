/**
 * Tests for chart image export (EXPORT-CHART-001).
 *
 * Verifies PNG/SVG export buttons render and trigger the right logic.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

// Mock framer-motion (project pattern)
vi.mock('framer-motion', () => {
  const createMotionComponent = (tag: string) => {
    const Component = ({ children, ...props }: Record<string, unknown> & { children?: React.ReactNode }) => {
      const domProps = Object.fromEntries(
        Object.entries(props).filter(
          ([key]) =>
            !['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover', 'whileTap', 'layout'].includes(key)
        )
      );
      const Tag = tag as keyof JSX.IntrinsicElements;
      return <Tag {...domProps}>{children}</Tag>;
    };
    Component.displayName = `motion.${tag}`;
    return Component;
  };
  return {
    motion: new Proxy({}, { get: (_, prop: string) => createMotionComponent(prop) }),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// Mock auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: Record<string, unknown>) => unknown) =>
    selector({ token: 'test-token', profileId: 'test-profile' })
  ),
}));

// Mock reduced motion
vi.mock('@/hooks/useReducedMotion', () => ({
  useReducedMotion: () => true,
}));

// Mock services
const mockObservations = [
  {
    id: 'obs-1',
    profile_id: 'test-profile',
    doc_id: 'doc-1',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 95,
    value_text: null,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 100,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2025-01-01T00:00:00',
    user_verified: true,
    extraction_confidence: 0.95,
    source_page: null,
    source_bbox_json: null,
  },
];

const mockTrendData = {
  analyte_canonical: 'glucose',
  analyte_display_name: 'GLUCOSE',
  unit: 'mg/dL',
  ref_low: 70,
  ref_high: 100,
  data_points: [
    {
      date: '2025-01-01T00:00:00',
      value: 95,
      unit: 'mg/dL',
      is_abnormal: false,
      flag: null,
      doc_id: 'doc-1',
      extraction_confidence: 0.95,
    },
  ],
  summary: 'Single measurement of GLUCOSE recorded.',
};

vi.mock('@/services/observations', () => ({
  useObservations: () => ({
    data: mockObservations,
    isLoading: false,
    isError: false,
  }),
  useTrend: () => ({
    data: mockTrendData,
    isLoading: false,
    isError: false,
  }),
  usePanel: () => ({ data: null }),
}));

vi.mock('@/services/medications', () => ({
  useMedications: () => ({ data: [] }),
}));

vi.mock('@/utils/correlation', () => ({
  findActiveMedications: () => [],
}));

vi.mock('@/components/MedicationOverlay', () => ({
  MedicationOverlay: () => <div data-testid="medication-overlay" />,
}));

// Mock html2canvas
vi.mock('html2canvas', () => ({
  default: vi.fn().mockResolvedValue({
    toDataURL: () => 'data:image/png;base64,mock',
  }),
}));

import { TrendsDashboard } from '../pages/TrendsDashboard';

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TrendsDashboard />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ChartExport (EXPORT-CHART-001)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders PNG export button', () => {
    renderWithProviders();
    expect(screen.getByLabelText('Download chart as PNG')).toBeDefined();
  });

  it('renders SVG export button', () => {
    renderWithProviders();
    expect(screen.getByLabelText('Download chart as SVG')).toBeDefined();
  });

  it('PNG button click triggers html2canvas', async () => {
    const user = userEvent.setup();
    renderWithProviders();

    const pngButton = screen.getByLabelText('Download chart as PNG');
    await user.click(pngButton);

    const html2canvas = (await import('html2canvas')).default;
    expect(html2canvas).toHaveBeenCalled();
  });

  it('SVG button click does not throw', async () => {
    const user = userEvent.setup();
    renderWithProviders();

    const svgButton = screen.getByLabelText('Download chart as SVG');
    // Should not throw even if no SVG element present in test DOM
    await user.click(svgButton);
  });
});
