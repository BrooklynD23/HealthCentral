/**
 * PanelChartView Tests
 *
 * Tests for the panel-specific multi-analyte chart component
 * using percent-of-reference normalization.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PanelChartView } from '@/components/PanelChartView';
import type { Panel } from '@/services/types';

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

function makePanel(overrides: Partial<Panel> = {}): Panel {
  return {
    panel_id: 'cbc',
    panel_name: 'CBC',
    collection_date: '2024-01-15',
    observations: [
      {
        id: 'obs-1',
        profile_id: 'p-1',
        doc_id: 'doc-1',
        analyte_canonical: 'wbc',
        analyte_raw: 'WBC',
        value: 7.5,
        value_text: null,
        unit: 'K/uL',
        ref_low: 4.0,
        ref_high: 11.0,
        ref_range_text: '4.0-11.0',
        flag: null,
        is_abnormal: false,
        collected_at: '2024-01-15',
        user_verified: true,
        extraction_confidence: null,
      },
      {
        id: 'obs-2',
        profile_id: 'p-1',
        doc_id: 'doc-1',
        analyte_canonical: 'hgb',
        analyte_raw: 'Hemoglobin',
        value: 15.2,
        value_text: null,
        unit: 'g/dL',
        ref_low: 12.0,
        ref_high: 17.0,
        ref_range_text: '12.0-17.0',
        flag: null,
        is_abnormal: false,
        collected_at: '2024-01-15',
        user_verified: true,
        extraction_confidence: null,
      },
      {
        id: 'obs-3',
        profile_id: 'p-1',
        doc_id: 'doc-1',
        analyte_canonical: 'plt',
        analyte_raw: 'Platelets',
        value: 350,
        value_text: null,
        unit: 'K/uL',
        ref_low: 150,
        ref_high: 400,
        ref_range_text: '150-400',
        flag: 'H',
        is_abnormal: false,
        collected_at: '2024-01-15',
        user_verified: true,
        extraction_confidence: null,
      },
    ],
    ...overrides,
  };
}

describe('PanelChartView', () => {
  it('renders chart when panel has numeric observations', () => {
    render(<PanelChartView panel={makePanel()} />);
    expect(screen.getByTestId('panel-chart')).toBeInTheDocument();
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('shows empty state when panel has zero observations', () => {
    render(<PanelChartView panel={makePanel({ observations: [] })} />);
    expect(screen.getByTestId('panel-chart-empty')).toBeInTheDocument();
    expect(screen.getByText(/No numeric observations/)).toBeInTheDocument();
  });

  it('shows empty state when observations lack reference ranges', () => {
    const obs = [
      {
        id: 'obs-q',
        profile_id: 'p-1',
        doc_id: 'doc-1',
        analyte_canonical: 'color',
        analyte_raw: 'Color',
        value: null,
        value_text: 'Yellow',
        unit: null,
        ref_low: null,
        ref_high: null,
        ref_range_text: null,
        flag: null,
        is_abnormal: false,
        collected_at: '2024-01-15',
        user_verified: true,
        extraction_confidence: null,
      },
    ];
    render(<PanelChartView panel={makePanel({ observations: obs })} />);
    expect(screen.getByTestId('panel-chart-empty')).toBeInTheDocument();
  });

  it('renders sr-only data table with correct columns', () => {
    render(<PanelChartView panel={makePanel()} />);
    const table = screen.getByTestId('panel-chart-table');
    expect(table).toBeInTheDocument();

    // Check headers
    const headers = table.querySelectorAll('th');
    expect(headers).toHaveLength(5);
    expect(headers[0].textContent).toBe('Analyte');
    expect(headers[1].textContent).toBe('Value');
    expect(headers[2].textContent).toBe('Unit');
    expect(headers[3].textContent).toBe('Reference Range');
    expect(headers[4].textContent).toBe('Status');
  });

  it('renders all observations as table rows', () => {
    render(<PanelChartView panel={makePanel()} />);
    const table = screen.getByTestId('panel-chart-table');
    const rows = table.querySelectorAll('tbody tr');
    expect(rows).toHaveLength(3);
  });

  it('marks out-of-range observations as abnormal', () => {
    const obs = [
      {
        id: 'obs-high',
        profile_id: 'p-1',
        doc_id: 'doc-1',
        analyte_canonical: 'wbc',
        analyte_raw: 'WBC',
        value: 15.0, // above ref_high of 11.0
        value_text: null,
        unit: 'K/uL',
        ref_low: 4.0,
        ref_high: 11.0,
        ref_range_text: '4.0-11.0',
        flag: 'H',
        is_abnormal: true,
        collected_at: '2024-01-15',
        user_verified: true,
        extraction_confidence: null,
      },
    ];
    render(<PanelChartView panel={makePanel({ observations: obs })} />);
    const table = screen.getByTestId('panel-chart-table');
    const row = table.querySelector('tbody tr');
    expect(row?.getAttribute('data-abnormal')).toBe('true');
    expect(row?.textContent).toContain('Abnormal');
  });

  it('displays panel name in the chart heading', () => {
    render(<PanelChartView panel={makePanel({ panel_name: 'Lipid Panel' })} />);
    expect(screen.getByText(/Lipid Panel — Analyte Comparison/)).toBeInTheDocument();
  });
});
