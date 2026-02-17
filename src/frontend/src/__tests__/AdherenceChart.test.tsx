/**
 * AdherenceChart Tests
 *
 * Tests for the daily medication adherence time-series chart.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AdherenceChart } from '@/components/medication-coach/AdherenceChart';

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

function makeDoses(count: number = 10): Array<{ taken_at: string; was_skipped: boolean }> {
  const doses = [];
  for (let i = 0; i < count; i++) {
    const date = new Date(2024, 0, 1 + i);
    doses.push({
      taken_at: date.toISOString(),
      was_skipped: i % 5 === 0, // every 5th dose skipped
    });
  }
  return doses;
}

describe('AdherenceChart', () => {
  it('renders chart when doses array is non-empty', () => {
    render(<AdherenceChart doses={makeDoses()} />);
    expect(screen.getByTestId('adherence-chart')).toBeInTheDocument();
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('shows empty state when doses is empty', () => {
    render(<AdherenceChart doses={[]} />);
    expect(screen.getByTestId('adherence-chart-empty')).toBeInTheDocument();
    expect(screen.getByText(/No dose records/)).toBeInTheDocument();
  });

  it('aggregates multiple doses on same date into single bar', () => {
    const doses = [
      { taken_at: '2024-01-15T08:00:00Z', was_skipped: false },
      { taken_at: '2024-01-15T20:00:00Z', was_skipped: false },
      { taken_at: '2024-01-16T08:00:00Z', was_skipped: true },
    ];
    render(<AdherenceChart doses={doses} />);
    const table = screen.getByTestId('adherence-chart-table');
    const rows = table.querySelectorAll('tbody tr');
    expect(rows).toHaveLength(2); // 2 unique dates
  });

  it('renders sr-only data table with Date, Taken, Skipped columns', () => {
    render(<AdherenceChart doses={makeDoses(3)} />);
    const table = screen.getByTestId('adherence-chart-table');
    const headers = table.querySelectorAll('th');
    expect(headers).toHaveLength(3);
    expect(headers[0].textContent).toBe('Date');
    expect(headers[1].textContent).toBe('Taken');
    expect(headers[2].textContent).toBe('Skipped');
  });

  it('correctly counts taken vs skipped', () => {
    const doses = [
      { taken_at: '2024-01-15T08:00:00Z', was_skipped: false },
      { taken_at: '2024-01-15T20:00:00Z', was_skipped: true },
      { taken_at: '2024-01-15T12:00:00Z', was_skipped: false },
    ];
    render(<AdherenceChart doses={doses} />);
    const table = screen.getByTestId('adherence-chart-table');
    const row = table.querySelector('tbody tr');
    const cells = row?.querySelectorAll('td');
    // Taken = 2, Skipped = 1
    expect(cells?.[1].textContent).toBe('2');
    expect(cells?.[2].textContent).toBe('1');
  });

  it('chart container has correct test ID', () => {
    render(<AdherenceChart doses={makeDoses()} />);
    expect(screen.getByTestId('adherence-chart')).toBeInTheDocument();
  });
});
