import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InterpretedTrendChart } from '@/components/lab-interpreter/InterpretedTrendChart';
import type { TrendData } from '@/services/types';

vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

const point = (date: string, value: number, user_verified: boolean) => ({
  date, value, unit: 'mg/dL', is_abnormal: false, flag: null, doc_id: 'd',
  extraction_confidence: 0.9, user_verified,
});

const trend = (verified: boolean[]): TrendData => ({
  analyte_canonical: 'glucose', analyte_display_name: 'GLUCOSE', unit: 'mg/dL',
  ref_low: 70, ref_high: 99, summary: 'GLUCOSE summary',
  data_points: [point('2025-01-10T00:00:00', 90, verified[0]), point('2025-06-10T00:00:00', 95, verified[1])],
});

describe('HC-VER-FE-003: LabInterpreter trend chart marks unverified points (D4)', () => {
  it('shows the note and labels an unverified latest value', () => {
    render(<InterpretedTrendChart trendData={trend([true, false])} interpretation={undefined} isLoading={false} isError={false} />);
    expect(screen.getByTestId('trend-unverified-note')).toHaveTextContent('1 of 2 points on this chart are unverified');
    expect(screen.getByText(/95 mg\/dL \(unverified\)/)).toBeInTheDocument();
  });

  it('shows neither when every point is verified', () => {
    render(<InterpretedTrendChart trendData={trend([true, true])} interpretation={undefined} isLoading={false} isError={false} />);
    expect(screen.getByText('GLUCOSE summary')).toBeInTheDocument(); // positive anchor
    expect(screen.queryByTestId('trend-unverified-note')).not.toBeInTheDocument();
    expect(screen.queryByText(/\(unverified\)/)).not.toBeInTheDocument();
  });
});
