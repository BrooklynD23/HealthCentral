/**
 * PanelChartView — Panel-specific multi-analyte chart
 *
 * Displays all analytes in a lab panel on a normalized scale
 * (percent-of-reference-range) so different units can be compared.
 *
 * Formula: normalizedValue = ((value - ref_low) / (ref_high - ref_low)) * 100
 * - 0% = at ref_low, 100% = at ref_high
 * - Values >100% or <0% are out-of-range
 */

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  ReferenceArea,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import type { Panel } from '@/services/types';

interface PanelChartViewProps {
  panel: Panel;
  className?: string;
}

interface NormalizedObservation {
  analyte: string;
  value: number;
  normalizedValue: number;
  unit: string;
  refLow: number;
  refHigh: number;
  isAbnormal: boolean;
}

function normalizeObservations(panel: Panel): NormalizedObservation[] {
  return panel.observations
    .filter(
      (obs) =>
        obs.value !== null &&
        obs.ref_low !== null &&
        obs.ref_high !== null &&
        obs.ref_high !== obs.ref_low,
    )
    .map((obs) => {
      const value = obs.value!;
      const refLow = obs.ref_low!;
      const refHigh = obs.ref_high!;
      const normalizedValue = ((value - refLow) / (refHigh - refLow)) * 100;
      return {
        analyte: obs.analyte_raw,
        value,
        normalizedValue: Math.round(normalizedValue * 10) / 10,
        unit: obs.unit || '',
        refLow,
        refHigh,
        isAbnormal: normalizedValue < 0 || normalizedValue > 100,
      };
    });
}

function PanelTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: NormalizedObservation }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const data = payload[0].payload;
  return (
    <div className="rounded-xl border border-black/[0.08] bg-white px-3 py-2 shadow-soft">
      <p className="text-sm font-semibold text-ink">{data.analyte}</p>
      <p className="text-xs text-ink-secondary">
        {data.value} {data.unit}
      </p>
      <p className="text-xs text-ink-secondary">
        Range: {data.refLow}-{data.refHigh} {data.unit}
      </p>
      <p className="text-xs text-ink-secondary">
        {data.normalizedValue}% of reference
      </p>
    </div>
  );
}

export function PanelChartView({ panel, className }: PanelChartViewProps) {
  const chartData = useMemo(() => normalizeObservations(panel), [panel]);

  if (chartData.length === 0) {
    return (
      <Card className={className} data-testid="panel-chart-empty">
        <CardContent className="py-8 text-center text-ink-secondary">
          No numeric observations with reference ranges available for{' '}
          {panel.panel_name}.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className} data-testid="panel-chart">
      <CardHeader>
        <CardTitle>{panel.panel_name} — Analyte Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 5, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="analyte" tick={{ fontSize: 12 }} />
              <YAxis
                domain={[-20, 140]}
                tick={{ fontSize: 12 }}
                label={{ value: '% of Reference', angle: -90, position: 'insideLeft', fontSize: 11 }}
              />
              <Tooltip content={<PanelTooltip />} />
              <ReferenceArea y1={0} y2={100} fill="#2D7D6F" fillOpacity={0.08} />
              <ReferenceLine y={0} stroke="#2D7D6F" strokeDasharray="3 3" label="Low" />
              <ReferenceLine y={100} stroke="#2D7D6F" strokeDasharray="3 3" label="High" />
              <Bar
                dataKey="normalizedValue"
                name="% of Reference"
                fill="#2D7D6F"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* sr-only data table for accessibility */}
        <table className="sr-only" data-testid="panel-chart-table">
          <caption>{panel.panel_name} analyte values</caption>
          <thead>
            <tr>
              <th>Analyte</th>
              <th>Value</th>
              <th>Unit</th>
              <th>Reference Range</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((obs) => (
              <tr key={obs.analyte} data-abnormal={obs.isAbnormal || undefined}>
                <td>{obs.analyte}</td>
                <td>{obs.value}</td>
                <td>{obs.unit}</td>
                <td>
                  {obs.refLow}-{obs.refHigh}
                </td>
                <td>{obs.isAbnormal ? 'Abnormal' : 'Normal'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
