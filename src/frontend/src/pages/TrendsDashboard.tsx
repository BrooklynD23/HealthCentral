import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  Filter,
  ExternalLink,
  Info,
  Loader2,
  AlertTriangle,
  FileText,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useObservations, useTrend, usePanel } from '@/services/observations';
import { useAuthStore } from '@/stores/authStore';
import type { Observation } from '@/services/types';

const panels = [
  { id: 'cbc', label: 'CBC' },
  { id: 'cmp', label: 'CMP' },
  { id: 'lipid', label: 'Lipids' },
  { id: 'thyroid', label: 'Thyroid' },
];

export function TrendsDashboard() {
  const prefersReducedMotion = useReducedMotion();
  const { profileId } = useAuthStore();
  const [activePanel, setActivePanel] = useState('cbc');
  const [selectedAnalyte, setSelectedAnalyte] = useState<string | null>(null);

  // Fetch all observations to get list of analytes
  const {
    data: observations,
    isLoading: observationsLoading,
    isError: observationsError,
  } = useObservations({
    profile_id: profileId || '',
  });

  // Get unique analytes from observations
  const analyteList = useMemo(() => {
    if (!observations) return [];
    const uniqueAnalytes = new Map<string, Observation>();
    observations.forEach((obs) => {
      if (!uniqueAnalytes.has(obs.analyte_canonical)) {
        uniqueAnalytes.set(obs.analyte_canonical, obs);
      }
    });
    return Array.from(uniqueAnalytes.values());
  }, [observations]);

  // Auto-select first analyte if none selected
  const effectiveSelectedAnalyte = selectedAnalyte || analyteList[0]?.analyte_canonical;

  // Fetch trend data for selected analyte
  const {
    data: trendData,
    isLoading: trendLoading,
    isError: trendError,
  } = useTrend(effectiveSelectedAnalyte, profileId || '');

  // Fetch panel data when panel tab changes
  const { data: panelData } = usePanel(activePanel, profileId || '');

  // Transform trend data for chart
  const chartData = useMemo(() => {
    if (!trendData?.data_points) return [];
    return trendData.data_points.map((point) => ({
      date: point.date.slice(0, 7), // YYYY-MM format
      value: point.value,
      refLow: trendData.ref_low,
      refHigh: trendData.ref_high,
    }));
  }, [trendData]);

  // Get latest value info
  const latestValue = trendData?.data_points?.[trendData.data_points.length - 1];
  const getTrendIcon = (current: number | undefined, previous: number | undefined) => {
    if (!current || !previous) return <Minus className="w-4 h-4" />;
    const diff = current - previous;
    if (Math.abs(diff) < 0.1) return <Minus className="w-4 h-4" />;
    if (diff > 0) return <TrendingUp className="w-4 h-4" />;
    return <TrendingDown className="w-4 h-4" />;
  };

  const getTrendColor = (current: number | undefined, previous: number | undefined, isAbnormal: boolean) => {
    if (isAbnormal) return 'text-status-attention';
    if (!current || !previous) return 'text-ink-secondary';
    const diff = current - previous;
    if (diff > 0) return 'text-status-verified';
    if (diff < 0) return 'text-status-caution';
    return 'text-ink-secondary';
  };

  const handlePanelClick = (panelId: string) => {
    setActivePanel(panelId);
  };

  // Loading state
  if (observationsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  // Error state
  if (observationsError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-attention mx-auto mb-3" />
          <p className="text-ink-secondary">Failed to load observations</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!observations || observations.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Trends Dashboard
          </h1>
          <p className="text-ink-secondary mt-1">
            Track changes in your test results over time
          </p>
        </div>
        <Card>
          <CardContent className="py-16">
            <div className="text-center">
              <FileText className="w-12 h-12 text-ink-tertiary mx-auto mb-3" />
              <p className="text-lg font-medium text-ink mb-1">No data available</p>
              <p className="text-ink-secondary">
                Import lab documents to see your trends.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Trends Dashboard
          </h1>
          <p className="text-ink-secondary mt-1">
            Track changes in your test results over time
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" className="gap-2">
            <Calendar className="w-4 h-4" />
            Last 12 Months
          </Button>
          <Button variant="secondary" className="gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </Button>
        </div>
      </div>

      <div className="flex gap-2">
        {panels.map((panel) => (
          <button
            key={panel.id}
            onClick={() => handlePanelClick(panel.id)}
            className={cn(
              'px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
              activePanel === panel.id
                ? 'bg-accent text-white shadow-soft'
                : 'bg-surface-elevated border border-black/[0.06] text-ink-secondary hover:bg-surface-muted'
            )}
          >
            {panel.label}
            {panelData?.observations && activePanel === panel.id && (
              <span
                className={cn(
                  'ml-2 px-1.5 py-0.5 rounded text-xs',
                  'bg-white/20'
                )}
              >
                {panelData.observations.length}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span>{trendData?.analyte_display_name || effectiveSelectedAnalyte}</span>
                  {latestValue && !latestValue.is_abnormal && (
                    <Badge variant="verified">Normal Range</Badge>
                  )}
                  {latestValue?.is_abnormal && (
                    <Badge variant="attention">Outside Range</Badge>
                  )}
                </div>
                <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
                  <ExternalLink className="w-3.5 h-3.5" />
                  View Sources
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {trendLoading ? (
                <div className="h-72 flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-accent" />
                </div>
              ) : trendError || !trendData ? (
                <div className="h-72 flex items-center justify-center">
                  <p className="text-ink-secondary">No trend data available for this analyte</p>
                </div>
              ) : chartData.length === 0 ? (
                <div className="h-72 flex items-center justify-center">
                  <p className="text-ink-secondary">No trend data available</p>
                </div>
              ) : (
                <>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={chartData}
                        margin={{ top: 20, right: 20, left: 0, bottom: 0 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="rgba(0,0,0,0.06)"
                          vertical={false}
                        />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 12, fill: '#6B6B6B' }}
                          tickLine={false}
                          axisLine={{ stroke: 'rgba(0,0,0,0.08)' }}
                        />
                        <YAxis
                          domain={['auto', 'auto']}
                          tick={{ fontSize: 12, fill: '#6B6B6B' }}
                          tickLine={false}
                          axisLine={false}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'white',
                            border: '1px solid rgba(0,0,0,0.08)',
                            borderRadius: '12px',
                            boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
                          }}
                        />
                        {trendData.ref_low !== null && (
                          <ReferenceLine
                            y={trendData.ref_low}
                            stroke="#7BA387"
                            strokeDasharray="4 4"
                            strokeOpacity={0.6}
                          />
                        )}
                        {trendData.ref_high !== null && (
                          <ReferenceLine
                            y={trendData.ref_high}
                            stroke="#7BA387"
                            strokeDasharray="4 4"
                            strokeOpacity={0.6}
                          />
                        )}
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#2D7D6F"
                          strokeWidth={2.5}
                          dot={{ fill: '#2D7D6F', strokeWidth: 0, r: 5 }}
                          activeDot={{ r: 7, fill: '#2D7D6F' }}
                          animationDuration={prefersReducedMotion ? 0 : 800}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="mt-4 p-4 rounded-xl bg-surface-muted">
                    <div className="flex items-start gap-3">
                      <Info className="w-5 h-5 text-ink-secondary flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm text-ink">
                          <strong>
                            Latest value: {latestValue?.value} {trendData.unit}
                          </strong>{' '}
                          {trendData.ref_low !== null && trendData.ref_high !== null && (
                            <>
                              — Reference range: {trendData.ref_low}-{trendData.ref_high} {trendData.unit}
                            </>
                          )}
                        </p>
                        {trendData.summary && (
                          <p className="text-sm text-ink-secondary mt-1">
                            {trendData.summary}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Analyte Summary</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-black/[0.04]">
                {analyteList.map((obs, index) => (
                  <motion.button
                    key={obs.analyte_canonical}
                    initial={prefersReducedMotion ? {} : { opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => setSelectedAnalyte(obs.analyte_canonical)}
                    className={cn(
                      'w-full flex items-center justify-between p-4 text-left transition-colors',
                      'hover:bg-surface-muted/50 focus:outline-none focus:bg-accent-subtle',
                      effectiveSelectedAnalyte === obs.analyte_canonical && 'bg-accent-subtle'
                    )}
                  >
                    <div>
                      <p className="font-medium text-ink text-sm">{obs.analyte_raw}</p>
                      <p className="text-xs text-ink-secondary mt-0.5">
                        {obs.value ?? obs.value_text} {obs.unit}
                      </p>
                    </div>
                    <div
                      className={cn(
                        'flex items-center gap-1',
                        getTrendColor(
                          obs.value ?? undefined,
                          undefined,
                          obs.is_abnormal ?? false
                        )
                      )}
                    >
                      {getTrendIcon(obs.value ?? undefined, undefined)}
                    </div>
                  </motion.button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-accent-subtle border-accent/20">
            <CardContent className="p-4">
              <p className="text-sm text-ink font-medium mb-1">
                Need help understanding?
              </p>
              <p className="text-xs text-ink-secondary mb-3">
                Ask our assistant to explain any test result in plain language.
              </p>
              <Button size="sm" className="w-full">
                Open Explain
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
