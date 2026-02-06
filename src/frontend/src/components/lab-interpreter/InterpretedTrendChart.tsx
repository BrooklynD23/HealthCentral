import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import { Loader2, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import type { TrendData, InterpretationResponse } from '@/services/types';

interface InterpretedTrendChartProps {
  trendData: TrendData | undefined;
  interpretation: InterpretationResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  className?: string;
}

export function InterpretedTrendChart({
  trendData,
  interpretation,
  isLoading,
  isError,
  className,
}: InterpretedTrendChartProps) {
  const prefersReducedMotion = useReducedMotion();

  const chartData = useMemo(() => {
    if (!trendData?.data_points) return [];
    return trendData.data_points.map((point) => ({
      date: point.date.slice(0, 10),
      value: point.value,
      isAbnormal: point.is_abnormal,
    }));
  }, [trendData]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !trendData) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center gap-3">
            <AlertTriangle className="w-8 h-8 text-status-attention" />
            <p className="text-sm text-ink-secondary">No trend data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const latestPoint = trendData.data_points[trendData.data_points.length - 1];

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2.5">
            {trendData.analyte_display_name}
            {latestPoint && (
              <Badge variant={latestPoint.is_abnormal ? 'attention' : 'verified'}>
                {latestPoint.value} {trendData.unit}
              </Badge>
            )}
          </CardTitle>
          {interpretation && (
            <Badge variant="accent">Interpreted</Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {chartData.length === 0 ? (
          <div className="h-56 flex items-center justify-center">
            <p className="text-sm text-ink-secondary">No data points</p>
          </div>
        ) : (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(0,0,0,0.06)"
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#6B6B6B' }}
                  tickLine={false}
                  axisLine={{ stroke: 'rgba(0,0,0,0.08)' }}
                />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11, fill: '#6B6B6B' }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid rgba(0,0,0,0.08)',
                    borderRadius: '12px',
                    boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
                    fontSize: '12px',
                  }}
                />

                {/* Normal range shading */}
                {trendData.ref_low !== null && trendData.ref_high !== null && (
                  <ReferenceArea
                    y1={trendData.ref_low}
                    y2={trendData.ref_high}
                    fill="#7BA387"
                    fillOpacity={0.08}
                  />
                )}

                {trendData.ref_low !== null && (
                  <ReferenceLine
                    y={trendData.ref_low}
                    stroke="#7BA387"
                    strokeDasharray="4 4"
                    strokeOpacity={0.5}
                    label={{ value: 'Low', fontSize: 10, fill: '#7BA387' }}
                  />
                )}
                {trendData.ref_high !== null && (
                  <ReferenceLine
                    y={trendData.ref_high}
                    stroke="#7BA387"
                    strokeDasharray="4 4"
                    strokeOpacity={0.5}
                    label={{ value: 'High', fontSize: 10, fill: '#7BA387' }}
                  />
                )}

                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#2D7D6F"
                  strokeWidth={2.5}
                  dot={{ fill: '#2D7D6F', strokeWidth: 0, r: 4 }}
                  activeDot={{ r: 6, fill: '#2D7D6F' }}
                  animationDuration={prefersReducedMotion ? 0 : 800}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Interpretation summary inline */}
        {interpretation && (
          <div className="p-3 rounded-xl bg-accent-subtle border border-accent/10">
            <p className="text-sm text-ink leading-relaxed">
              {interpretation.interpretation_text.length > 200
                ? interpretation.interpretation_text.slice(0, 200) + '...'
                : interpretation.interpretation_text}
            </p>
          </div>
        )}

        {/* Trend summary */}
        {trendData.summary && (
          <p className="text-xs text-ink-secondary">{trendData.summary}</p>
        )}
      </CardContent>
    </Card>
  );
}
