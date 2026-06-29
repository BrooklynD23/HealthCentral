import { useState, useMemo, useRef, useCallback } from 'react';
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
  Download,
  Image as ImageIcon,
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
import { useMedications } from '@/services/medications';
import { useAuthStore } from '@/stores/authStore';
import { findActiveMedications } from '@/utils/correlation';
import { MedicationOverlay } from '@/components/MedicationOverlay';
import type { Observation } from '@/services/types';

const panels = [
  { id: 'cbc', label: 'CBC' },
  { id: 'cmp', label: 'CMP' },
  { id: 'lipid', label: 'Lipids' },
  { id: 'thyroid', label: 'Thyroid' },
];

function downloadFile(href: string, filename: string) {
  const link = document.createElement('a');
  link.download = filename;
  link.href = href;
  link.click();
}

async function renderSvgToCanvas(svgElement: SVGSVGElement) {
  const serializer = new XMLSerializer();
  const svgClone = svgElement.cloneNode(true) as SVGSVGElement;
  const viewBox = svgClone.viewBox.baseVal;
  const bounds = svgElement.getBoundingClientRect();
  const width = Math.max(
    Math.ceil(bounds.width || viewBox.width || Number(svgClone.getAttribute('width')) || 0),
    1
  );
  const height = Math.max(
    Math.ceil(bounds.height || viewBox.height || Number(svgClone.getAttribute('height')) || 0),
    1
  );

  svgClone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  svgClone.setAttribute('width', String(width));
  svgClone.setAttribute('height', String(height));

  const blob = new Blob([serializer.serializeToString(svgClone)], {
    type: 'image/svg+xml;charset=utf-8',
  });
  const objectUrl = URL.createObjectURL(blob);

  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const nextImage = new Image();
      nextImage.onload = () => resolve(nextImage);
      nextImage.onerror = () => reject(new Error('Failed to load chart SVG'));
      nextImage.src = objectUrl;
    });

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('Canvas 2D context is unavailable');
    }

    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, width, height);
    context.drawImage(image, 0, 0, width, height);

    return canvas;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

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
      confidence: point.extraction_confidence,
    }));
  }, [trendData]);

  // Chart container ref for export (EXPORT-CHART-001)
  const chartRef = useRef<HTMLDivElement>(null);

  const handleExportPNG = useCallback(async () => {
    if (!chartRef.current) return;
    const svgElement = chartRef.current.querySelector('svg');
    if (!svgElement) return;

    const canvas = await renderSvgToCanvas(svgElement);
    downloadFile(
      canvas.toDataURL('image/png'),
      `${effectiveSelectedAnalyte || 'chart'}-trend.png`
    );
  }, [effectiveSelectedAnalyte]);

  const handleExportSVG = useCallback(() => {
    if (!chartRef.current) return;
    const svgElement = chartRef.current.querySelector('svg');
    if (!svgElement) return;
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgElement);
    const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const objectUrl = URL.createObjectURL(blob);
    downloadFile(objectUrl, `${effectiveSelectedAnalyte || 'chart'}-trend.svg`);
    URL.revokeObjectURL(objectUrl);
  }, [effectiveSelectedAnalyte]);

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
  const unverifiedCount = useMemo(
    () => observations?.filter((obs) => !obs.user_verified).length ?? 0,
    [observations]
  );
  const lowConfidenceCount = useMemo(
    () => observations?.filter((obs) => (obs.extraction_confidence ?? 1) < 0.8).length ?? 0,
    [observations]
  );
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
          {unverifiedCount > 0 && (
            <Badge variant="caution">
              {unverifiedCount} unverified values
            </Badge>
          )}
          {lowConfidenceCount > 0 && (
            <Badge variant="attention">
              {lowConfidenceCount} low-confidence extractions
            </Badge>
          )}
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

      <div className="flex gap-2" role="tablist" aria-label="Lab panels">
        {panels.map((panel) => (
          <button
            key={panel.id}
            role="tab"
            aria-selected={activePanel === panel.id}
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
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-1.5 text-xs"
                    onClick={handleExportPNG}
                    aria-label="Download chart as PNG"
                  >
                    <ImageIcon className="w-3.5 h-3.5" />
                    PNG
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-1.5 text-xs"
                    onClick={handleExportSVG}
                    aria-label="Download chart as SVG"
                  >
                    <Download className="w-3.5 h-3.5" />
                    SVG
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
                <div className="h-72 flex items-center justify-center flex-col gap-3">
                  <p className="text-ink-secondary">
                    {trendData.summary || 'No dated measurements to chart.'}
                  </p>
                  <p className="text-xs text-ink-tertiary">
                    Collection dates could not be read from the source document.
                    Re-import or reprocess the document, or verify the observation to set a date.
                  </p>
                </div>
              ) : (
                <>
                  <div className="h-72" ref={chartRef}>
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
                          content={({ active, payload }) => {
                            if (!active || !payload?.[0]) return null;
                            const data = payload[0].payload as {
                              date: string;
                              value: number;
                              confidence: number | null;
                            };
                            return (
                              <div className="bg-white border border-black/[0.08] rounded-xl shadow-soft px-4 py-3">
                                <p className="text-sm font-medium text-ink">
                                  {data.value} {trendData?.unit}
                                </p>
                                <p className="text-xs text-ink-secondary">{data.date}</p>
                                {data.confidence != null && (
                                  <p className="text-xs text-ink-tertiary mt-1">
                                    Confidence: {(data.confidence * 100).toFixed(0)}%
                                  </p>
                                )}
                              </div>
                            );
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
                      {obs.collected_at === null && (
                        <p className="text-xs text-ink-tertiary mt-0.5 italic">undated</p>
                      )}
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
