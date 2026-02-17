/**
 * AdherenceChart — Daily medication adherence time-series
 *
 * Aggregates individual dose records into daily buckets,
 * showing taken vs skipped as a stacked bar chart.
 *
 * Data source: GET /medications/{id}/doses (list_doses endpoint)
 * No new backend endpoint needed — client-side aggregation.
 */

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';

interface DoseRecord {
  taken_at: string;
  was_skipped: boolean;
}

interface AdherenceChartProps {
  doses: DoseRecord[];
  className?: string;
}

interface DailyBucket {
  date: string;
  dateLabel: string;
  taken: number;
  skipped: number;
}

function aggregateDoses(doses: DoseRecord[]): DailyBucket[] {
  const buckets = new Map<string, { taken: number; skipped: number }>();

  for (const dose of doses) {
    const date = dose.taken_at.slice(0, 10); // YYYY-MM-DD
    const existing = buckets.get(date) ?? { taken: 0, skipped: 0 };
    if (dose.was_skipped) {
      existing.skipped += 1;
    } else {
      existing.taken += 1;
    }
    buckets.set(date, existing);
  }

  return Array.from(buckets.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, counts]) => ({
      date,
      dateLabel: new Date(date + 'T00:00:00').toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      taken: counts.taken,
      skipped: counts.skipped,
    }));
}

function AdherenceTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-xl border border-black/[0.08] bg-white px-3 py-2 shadow-soft">
      <p className="text-xs font-semibold text-ink">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="text-xs text-ink-secondary">
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  );
}

export function AdherenceChart({ doses, className }: AdherenceChartProps) {
  const chartData = useMemo(() => aggregateDoses(doses), [doses]);

  if (chartData.length === 0) {
    return (
      <Card className={className} data-testid="adherence-chart-empty">
        <CardContent className="py-8 text-center text-ink-secondary">
          No dose records available for adherence visualization.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className} data-testid="adherence-chart">
      <CardHeader>
        <CardTitle>Daily Adherence</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ width: '100%', height: 250 }}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData} margin={{ top: 10, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="dateLabel" tick={{ fontSize: 10 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip content={<AdherenceTooltip />} />
              <Legend />
              <Bar
                dataKey="taken"
                name="Taken"
                stackId="adherence"
                fill="#2D7D6F"
                radius={[0, 0, 0, 0]}
              />
              <Bar
                dataKey="skipped"
                name="Skipped"
                stackId="adherence"
                fill="#D97706"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* sr-only data table for accessibility */}
        <table className="sr-only" data-testid="adherence-chart-table">
          <caption>Daily medication adherence</caption>
          <thead>
            <tr>
              <th>Date</th>
              <th>Taken</th>
              <th>Skipped</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((day) => (
              <tr key={day.date}>
                <td>{day.dateLabel}</td>
                <td>{day.taken}</td>
                <td>{day.skipped}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
