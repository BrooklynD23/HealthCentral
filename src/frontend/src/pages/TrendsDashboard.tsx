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
  BarChart,
  Bar,
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
import { useAutoRefresh } from '@/hooks/useAutoRefresh';
import { useObservations, useTrend, usePanel } from '@/services/observations';
import { useMedications } from '@/services/medications';
import { useAuthStore } from '@/stores/authStore';
import { findActiveMedications } from '@/utils/correlation';
import { MedicationOverlay } from '@/components/MedicationOverlay';
import { PanelChartView } from '@/components/PanelChartView';
import type { Observation } from '@/services/types';

const panels = [
  { id: 'cbc', label: 'CBC' },
  { id: 'cmp', label: 'CMP' },
  { id: 'lipid', label: 'Lipids' },
  { id: 'thyroid', label: 'Thyroid' },
];

type DateRangePreset = '3m' | '6m' | '12m' | 'all';

const dateRangeOptions: Array<{ value: DateRangePreset; label: string }> = [
  { value: '3m', label: 'Last 3 Months' },
  { value: '6m', label: 'Last 6 Months' },
  { value: '12m', label: 'Last 12 Months' },
  { value: 'all', label: 'All Time' },
];

function isoDate(daysAgo: number): string {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().slice(0, 10);
}

function fromDateForPreset(preset: DateRangePreset): string | undefined {
  if (preset === 'all') return undefined;
  if (preset === '3m') return isoDate(90);
  if (preset === '6m') return isoDate(180);
  return isoDate(365);
}

function TrendTooltip({
  active,
  payload,
  label,
  unit,
  refLow,
  refHigh,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
  unit: string | null;
  refLow: number | null;
  refHigh: number | null;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-xl border border-black/[0.08] bg-white px-3 py-2 shadow-soft">
      <p className="text-xs text-ink-secondary">{label}</p>
      <p className="text-sm font-semibold text-ink">
        {payload[0].value} {unit}
      </p>
      {refLow !== null && refHigh !== null && (
        <p className="text-xs text-ink-secondary">
          Range: {refLow}-{refHigh} {unit}
        </p>
      )}
    </div>
  );
}

export function TrendsDashboard() {
  const prefersReducedMotion = useReducedMotion();
  const { profileId } = useAuthStore();
  const [activePanel, setActivePanel] = useState('cbc');
  const [selectedAnalyte, setSelectedAnalyte] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState(0);
  const [chartType, setChartType] = useState<'line' | 'bar'>('line');
  const [dateRangePreset, setDateRangePreset] = useState<DateRangePreset>('12m');
  const [isDateMenuOpen, setIsDateMenuOpen] = useState(false);

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
  const fromDate = useMemo(
    () => fromDateForPreset(dateRangePreset),
    [dateRangePreset]
  );

  const {
    data: trendData,
    isLoading: trendLoading,
    isError: trendError,
    refetch: refetchTrend,
  } = useTrend(effectiveSelectedAnalyte, profileId || '', fromDate);

  useAutoRefresh(
    () => {
      void refetchTrend();
    },
    30_000,
    !!effectiveSelectedAnalyte
  );

  // Fetch panel data when panel tab changes
  const { data: panelData } = usePanel(activePanel, profileId || '');

  // Fetch medications for correlation overlay
  const { data: medications } = useMedications();

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

  const visibleChartData = useMemo(() => {
    if (zoomLevel <= 0) return chartData;
    const visibleCount = Math.max(2, chartData.length - zoomLevel);
    return chartData.slice(-visibleCount);
  }, [chartData, zoomLevel]);

  // Get latest value info
  const latestValue = trendData?.data_points?.[trendData.data_points.length - 1];

  // Compute medications active at time of latest observation for the selected analyte
  const selectedObservation = useMemo(() => {
    if (!effectiveSelectedAnalyte || !observations) return null;
    return observations.find(
      (obs) => obs.analyte_canonical === effectiveSelectedAnalyte
    ) ?? null;
  }, [observations, effectiveSelectedAnalyte]);

  const activeMedsForSelected = useMemo(() => {
    if (!selectedObservation || !medications) return [];
    return findActiveMedications(selectedObservation, medications);
  }, [selectedObservation, medications]);
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

  const dateRangeLabel =
    dateRangeOptions.find((option) => option.value === dateRangePreset)?.label ||
    'Last 12 Months';

  // Loading state
  if (observationsLoading) {
    return (
      <div className="flex items-center justify-center h-64" role="status" aria-live="polite">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
        <span className="sr-only">Loading observations...</span>
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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Trends Dashboard
          </h1>
          <p className="text-ink-secondary mt-1">
            Track changes in your test results over time
          </p>
        </div>
        <div className="flex items-center flex-wrap gap-2">
          <div className="relative">
            <Button
              variant="secondary"
              className="gap-2 min-h-[44px]"
              onClick={() => setIsDateMenuOpen((prev) => !prev)}
            >
              <Calendar className="w-4 h-4" />
              {dateRangeLabel}
            </Button>
            {isDateMenuOpen && (
              <div className="absolute right-0 z-20 mt-2 w-44 rounded-xl border border-black/[0.08] bg-white p-2 shadow-soft">
                {dateRangeOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={cn(
                      'w-full rounded-lg px-3 py-2 text-left text-sm',
                      'hover:bg-surface-muted',
                      dateRangePreset === option.value && 'bg-accent-subtle text-accent'
                    )}
                    onClick={() => {
                      setDateRangePreset(option.value);
                      setIsDateMenuOpen(false);
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          <Button variant="secondary" className="gap-2 min-h-[44px]">
            <Calendar className="w-4 h-4" />
            Timeline
          </Button>
          <Button variant="secondary" className="gap-2 min-h-[44px]">
            <Filter className="w-4 h-4" />
            Filters
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Lab panels">
        {panels.map((panel) => (
          <button
            key={panel.id}
            role="tab"
            aria-selected={activePanel === panel.id}
            onClick={() => handlePanelClick(panel.id)}
            className={cn(
              'px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 min-h-[44px]',
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

      {panelData && panelData.observations.length > 0 && (
        <PanelChartView panel={panelData} className="mb-6" />
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="md:col-span-2">
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
                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label="Zoom out"
                    onClick={() => setZoomLevel((prev) => Math.max(0, prev - 1))}
                  >
                    -
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label="Zoom in"
                    onClick={() => setZoomLevel((prev) => Math.min(3, prev + 1))}
                  >
                    +
                  </Button>
                  <Button
                    type="button"
                    variant={chartType === 'line' ? 'primary' : 'ghost'}
                    size="sm"
                    aria-label="Line chart"
                    aria-pressed={chartType === 'line'}
                    onClick={() => setChartType('line')}
                  >
                    Line
                  </Button>
                  <Button
                    type="button"
                    variant={chartType === 'bar' ? 'primary' : 'ghost'}
                    size="sm"
                    aria-label="Bar chart"
                    aria-pressed={chartType === 'bar'}
                    onClick={() => setChartType('bar')}
                  >
                    Bar
                  </Button>
                  <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
                    <ExternalLink className="w-3.5 h-3.5" />
                    View Sources
                  </Button>
                </div>
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
                  <div
                    className="h-72 min-h-[200px]"
                    data-testid="chart-container"
                    data-zoom={zoomLevel}
                    data-chart-type={chartType}
                    data-drilldown-enabled="true"
                    data-has-custom-tooltip="true"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      {chartType === 'line' ? (
                        <LineChart
                          data={visibleChartData}
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
                            content={
                              <TrendTooltip
                                unit={trendData.unit}
                                refLow={trendData.ref_low}
                                refHigh={trendData.ref_high}
                              />
                            }
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
                      ) : (
                        <BarChart
                          data={visibleChartData}
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
                            content={
                              <TrendTooltip
                                unit={trendData.unit}
                                refLow={trendData.ref_low}
                                refHigh={trendData.ref_high}
                              />
                            }
                          />
                          <Bar dataKey="value" fill="#2D7D6F" radius={[6, 6, 0, 0]} />
                        </BarChart>
                      )}
                    </ResponsiveContainer>
                  </div>

                  <table
                    className="sr-only"
                    aria-label={`${trendData.analyte_display_name} trend data`}
                  >
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Value</th>
                        <th>Unit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {chartData.map((point) => (
                        <tr key={`${point.date}-${point.value}`}>
                          <td>{point.date}</td>
                          <td>{point.value}</td>
                          <td>{trendData.unit}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

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

                  {/* Medication Correlation Overlay */}
                  <div className="mt-4">
                    <p className="text-xs font-medium text-ink-secondary mb-2">
                      Medications active at time of latest result
                    </p>
                    <MedicationOverlay medications={activeMedsForSelected} />
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
