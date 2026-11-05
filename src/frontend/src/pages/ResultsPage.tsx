/**
 * Results (UI-PG-RESULTS): Trends and Interpret folded into one page around the Range Ribbon.
 *
 * - The shell comes first and is always there: the heading, the break-glass warning (D12, BG-WARN-INTERP: it must
 *   not be narrower than the old Interpret page) and the page-level disclaimer. The loading, error and empty
 *   branches sit under it, so none of them can drop the disclaimer.
 * - Tabs: All is the first tab and the default, and asks for no panel. A panel tab filters the list and fetches
 *   that panel; while it loads, or if it fails or is empty, the list says so. It is never the unfiltered list under a
 *   panel label. A named ?analyte= resets to All, so the row it names is listed.
 * - ?analyte= (the command palette, the medication page). AppLayout keys the route container on the pathname, so
 *   /results -> /results?analyte=x does not remount this page: a click made earlier would still win. A navigation is
 *   the later choice, so each new location (its key, not the URL: picking the same analyte twice is the same URL)
 *   that names an analyte drops the click and goes back to All.
 * - Explain: the interpretation is requested only once "Explain this result" has been pressed (or the page was
 *   opened with router state { explain: true }, which is what /interpret redirects with). It then stays on and
 *   follows the selected analyte.
 * - The ribbon replaces Recharts. Below lg it is drawn taller (PHONE_VIEW_HEIGHT), so the drawn plot is at least
 *   200 px on a 390 px phone (DF-4). The height is read from matchMedia in the first render, not in an effect, so
 *   the chart never draws once at one height and then again at another.
 * - Nothing here moves: no motion elements, no stagger, no transform. A spinner turns only where motion is allowed.
 *
 * The lab-interpreter components are imported by path, never through their barrel: the barrel re-exports the Recharts
 * trend chart, and the Results bundle budget (205 kB gz, UI-BUDGET) has no room for Recharts.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  Brain,
  Download,
  FileText,
  Image as ImageIcon,
  Info,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, EmptyState } from '@/components/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { cn } from '@/utils/cn';
import { useObservations, usePanel, useTrend } from '@/services/observations';
import { useMedications } from '@/services/medications';
import {
  useGenerateGroundedInterpretation,
  useGeneratePanelInterpretation,
  useInterpretation,
} from '@/services/interpretations';
import { useExternalApiSettings } from '@/services/modelSettings';
import { useAuthStore } from '@/stores/authStore';
import { findActiveMedications } from '@/utils/correlation';
import { MedicationOverlay } from '@/components/MedicationOverlay';
import { UnverifiedTrendNote } from '@/components/TrendVerificationMarkers';
import { ExternalApiBreakGlassWarning } from '@/components/settings/ExternalApiBreakGlassWarning';
import { RangeRibbon, bandOfValue, serializeRangeRibbonSvg } from '@/components/results/RangeRibbon';
import { DisclaimerBanner } from '@/components/lab-interpreter/DisclaimerBanner';
import { InterpretedResultCard } from '@/components/lab-interpreter/InterpretedResultCard';
import { PanelInterpretationDashboard } from '@/components/lab-interpreter/PanelInterpretationDashboard';
import { formatInterpretationText } from '@/components/lab-interpreter/formatInterpretationText';
import type { Observation, PanelInterpretationResponse } from '@/services/types';

const ALL = 'all';
const tabs = [
  { id: ALL, label: 'All' },
  { id: 'cbc', label: 'CBC' },
  { id: 'cmp', label: 'CMP' },
  { id: 'lipid', label: 'Lipids' },
  { id: 'thyroid', label: 'Thyroid' },
];

// Tailwind's lg. At and above it the ribbon keeps its default 320 x 160; below it the width is the limit, so the
// drawing is taller (see the viewHeight note in RangeRibbon.tsx).
const DESKTOP_QUERY = '(min-width: 1024px)';
const DESKTOP_VIEW_HEIGHT = 160;
// The band and the marks fill about 77% of the plot (the domain pads 15% each side) and the plot is the drawing's
// height less 48, so 320 units drawn at about 1:1 on a 390 px phone give the 200 px DF-4 asks for.
const PHONE_VIEW_HEIGHT = 320;

function readIsDesktop(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia(DESKTOP_QUERY).matches
    : false;
}

function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(readIsDesktop);
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return undefined;
    const query = window.matchMedia(DESKTOP_QUERY);
    setIsDesktop(query.matches);
    const onChange = (event: { matches: boolean }) => setIsDesktop(event.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);
  return isDesktop;
}

/**
 * The first toLocaleDateString of a page loads the browser's ICU date data: 9-15 ms on the main thread (CDP trace of the
 * Explain click, PR #476). The Explain card prints a date in its footer, so that cost landed inside the one task that
 * commits the card. This pays it while the page is idle instead; the card still prints its date in its first commit.
 */
function warmDateFormat(): () => void {
  const warm = () => void new Date(0).toLocaleDateString();
  if (typeof window.requestIdleCallback === 'function') {
    const handle = window.requestIdleCallback(warm, { timeout: 2000 });
    return () => window.cancelIdleCallback(handle);
  }
  const handle = window.setTimeout(warm, 300);
  return () => window.clearTimeout(handle);
}

function downloadFile(href: string, filename: string) {
  const link = document.createElement('a');
  link.download = filename;
  link.href = href;
  link.click();
}

// The size comes from the exported markup, whose width and height serializeRangeRibbonSvg set from the svg's viewBox, so
// the canvas and the file can never disagree and the viewBox is parsed in one place (RangeRibbon.tsx).
function markupSize(markup: string): { width: number; height: number } {
  const root = new DOMParser().parseFromString(markup, 'image/svg+xml').documentElement;
  return { width: Number(root.getAttribute('width')), height: Number(root.getAttribute('height')) };
}

// The PNG is the ribbon's own markup with the tokens resolved (a standalone svg has no page CSS, so raw
// XMLSerializer output would leave var(--token) and draw blank), on the page's surface colour.
async function renderSvgToCanvas(svgElement: SVGSVGElement) {
  const markup = serializeRangeRibbonSvg(svgElement);
  const { width: viewWidth, height: viewHeight } = markupSize(markup);
  const scale = 2;
  const width = Math.ceil(viewWidth * scale);
  const height = Math.ceil(viewHeight * scale);

  const blob = new Blob([markup], { type: 'image/svg+xml;charset=utf-8' });
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
    const surface = window.getComputedStyle(document.documentElement).getPropertyValue('--surface-1').trim();
    context.fillStyle = surface || '#ffffff';
    context.fillRect(0, 0, width, height);
    context.drawImage(image, 0, 0, width, height);
    return canvas;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

const chipBase = [
  'flex w-full min-h-11 shrink-0 items-center justify-between gap-2 text-left transition-colors',
  'rounded-full border border-[var(--line)] bg-surface-elevated px-3.5 py-1',
  'lg:min-h-0 lg:rounded-none lg:border-0 lg:bg-transparent lg:px-4 lg:py-3',
  'hover:bg-surface-muted/50 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent',
];

export function ResultsPage() {
  const { profileId } = useAuthStore();
  const navigate = useNavigate();
  const isDesktop = useIsDesktop();
  const [activeTab, setActiveTab] = useState(ALL);
  const [selectedAnalyte, setSelectedAnalyte] = useState<string | null>(null);

  const location = useLocation();
  const openedWithExplain = (location.state as { explain?: boolean } | null)?.explain === true;
  const [explainOpen, setExplainOpen] = useState(openedWithExplain);
  // A panel interpretation belongs to the tab it was made on, a grounded explanation to the result it was made for:
  // each is kept with its key and shown only while that key is the one on screen.
  const [panelInterpretation, setPanelInterpretation] = useState<{
    panel: string;
    data: PanelInterpretationResponse;
  } | null>(null);
  const [grounded, setGrounded] = useState<{
    observationId: string;
    summary: string;
    isValid: boolean;
    score: number;
  } | null>(null);
  const [withheldNotice, setWithheldNotice] = useState<{
    observationId: string;
    message: string;
    physicianReview: boolean;
  } | null>(null);

  const [searchParams] = useSearchParams();
  const { key: locationKey } = location;
  const requestedAnalyte = searchParams.get('analyte');
  const [seenLocationKey, setSeenLocationKey] = useState(locationKey);
  if (locationKey !== seenLocationKey) {
    setSeenLocationKey(locationKey);
    if (requestedAnalyte) {
      setSelectedAnalyte(null);
      setActiveTab(ALL);
      setPanelInterpretation(null);
    }
    if (openedWithExplain) setExplainOpen(true);
  }

  const {
    data: observations,
    isLoading: observationsLoading,
    isError: observationsError,
  } = useObservations({ profile_id: profileId || '' });

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

  // All asks for no panel. A panel tab asks for its panel and lists only the analytes it holds.
  const panelId = activeTab === ALL ? undefined : activeTab;
  const { data: panelData, isLoading: panelLoading, isError: panelError } = usePanel(panelId, profileId || '');
  const visibleList = useMemo(() => {
    if (activeTab === ALL) return analyteList;
    if (!panelData) return [];
    const members = new Set(panelData.observations.map((obs) => obs.analyte_canonical));
    return analyteList.filter((obs) => members.has(obs.analyte_canonical));
  }, [activeTab, analyteList, panelData]);

  // A click wins, then ?analyte= if it names a listed analyte (the raw URL value never reaches useTrend), else the first.
  const listed = (canonical: string | null) =>
    canonical !== null && visibleList.some((obs) => obs.analyte_canonical === canonical) ? canonical : undefined;
  const effectiveAnalyte = listed(selectedAnalyte) ?? listed(requestedAnalyte) ?? visibleList[0]?.analyte_canonical;
  const effectiveObservation = visibleList.find((obs) => obs.analyte_canonical === effectiveAnalyte) ?? null;

  const { data: trendData, isLoading: trendLoading, isError: trendError } = useTrend(effectiveAnalyte, profileId || '');
  const { data: medications } = useMedications();
  const { data: externalApi, isError: externalApiError } = useExternalApiSettings();
  const { data: interpretation, isLoading: interpLoading } = useInterpretation(
    explainOpen ? effectiveObservation?.id : undefined
  );
  const generateInterpretation = useGenerateGroundedInterpretation();
  const generatePanelInterp = useGeneratePanelInterpretation();
  useEffect(warmDateFormat, []);

  const latestValue = trendData?.data_points?.[trendData.data_points.length - 1];
  // The trend route sends is_abnormal false for a point that has no range, so "Normal Range" is claimed only when the
  // chart has a range and the latest value sits inside it. Otherwise no badge: absence is not normality. "Outside
  // Range" is shown whenever the value is outside the band, flagged or not (import sets is_abnormal only from a printed
  // flag, so a report with ranges and no flags lands here), and it stands alone. "Flagged on the report" is the
  // report's own flag where the band does not bear it out, so it is never hidden. The badge reads the band alone, so a flag
  // pointing the other way still gets "Outside Range" while the ribbon says the flag and the range disagree.
  // The band is read by the ribbon's own helper, on the same cleaned number the ribbon draws.
  const latestBand = latestValue
    ? bandOfValue(latestValue.value, trendData?.ref_low, trendData?.ref_high)
    : null;
  const latestPlace = !latestBand || latestBand.side === 'none' ? 'unknown' : latestBand.side === 'within' ? 'inside' : 'outside';
  const latestInsideRange = latestPlace === 'inside' && !latestValue?.is_abnormal;
  const unverifiedPointCount = useMemo(
    () => trendData?.data_points.filter((point) => point.user_verified !== true).length ?? 0,
    [trendData]
  );
  const activeMedsForSelected = useMemo(() => {
    if (!effectiveObservation || !medications) return [];
    return findActiveMedications(effectiveObservation, medications);
  }, [effectiveObservation, medications]);
  const unverifiedCount = useMemo(
    () => observations?.filter((obs) => !obs.user_verified).length ?? 0,
    [observations]
  );
  const lowConfidenceCount = useMemo(
    () => observations?.filter((obs) => (obs.extraction_confidence ?? 1) < 0.8).length ?? 0,
    [observations]
  );

  const chartRef = useRef<HTMLDivElement>(null);

  const handleExportPNG = useCallback(async () => {
    const svgElement = chartRef.current?.querySelector('svg');
    if (!svgElement) return;
    const canvas = await renderSvgToCanvas(svgElement);
    downloadFile(canvas.toDataURL('image/png'), `${effectiveAnalyte || 'chart'}-trend.png`);
  }, [effectiveAnalyte]);

  const handleExportSVG = useCallback(() => {
    const svgElement = chartRef.current?.querySelector('svg');
    if (!svgElement) return;
    const blob = new Blob([serializeRangeRibbonSvg(svgElement)], { type: 'image/svg+xml;charset=utf-8' });
    const objectUrl = URL.createObjectURL(blob);
    downloadFile(objectUrl, `${effectiveAnalyte || 'chart'}-trend.svg`);
    URL.revokeObjectURL(objectUrl);
  }, [effectiveAnalyte]);

  const handleGenerateInterpretation = () => {
    if (!effectiveObservation) return;
    const observationId = effectiveObservation.id;
    generateInterpretation.mutate(
      { observationId },
      {
        onSuccess: (data) => {
          if (data.withheld) {
            // INTERP-WITHHOLD-MSG: show the escalation message, never a grounded card.
            setWithheldNotice({
              observationId,
              message: data.full_response,
              physicianReview: data.withheld_physician_review === true,
            });
            setGrounded((current) => (current?.observationId === observationId ? null : current));
            return;
          }
          // Only this result's own notice goes, so another result's withheld message stays while it is on screen again.
          // There is one notice slot: a second withheld result replaces the first one's.
          setWithheldNotice((current) => (current?.observationId === observationId ? null : current));
          setGrounded({
            observationId,
            summary: data.full_response,
            isValid: data.is_valid,
            score: data.verification.faithfulness_score,
          });
        },
      }
    );
  };

  // The panel is interpreted for the day the panel itself is from (the route matches observations of that day), never
  // another analyte's date. No date, no request.
  const panelDate = activeTab !== ALL ? (panelData?.collection_date ?? null) : null;

  const handleGeneratePanelInterpretation = () => {
    if (!panelDate) return;
    const panel = activeTab;
    generatePanelInterp.mutate(
      { panelName: panel, collectedAt: panelDate },
      // The answer is kept with the tab it was asked on and shown only while that tab is on screen.
      { onSuccess: (data) => setPanelInterpretation({ panel, data }) }
    );
  };

  const selectTab = (id: string) => {
    setActiveTab(id);
    setSelectedAnalyte(null);
    setPanelInterpretation(null);
  };

  const viewHeight = isDesktop ? DESKTOP_VIEW_HEIGHT : PHONE_VIEW_HEIGHT;

  // The mutation is one object for every tab: its state counts here only for the tab it was started on.
  const askedPanel = generatePanelInterp.variables?.panelName;
  const panelShown = panelInterpretation?.panel === activeTab ? panelInterpretation : null;
  const panelPending = generatePanelInterp.isPending && askedPanel === activeTab;
  const panelFailed = generatePanelInterp.isError && askedPanel === activeTab;
  // The ribbon is on the page: nothing to download before it is, and nothing is selected on an empty or loading panel.
  const chartReady =
    effectiveAnalyte !== undefined && !trendLoading && !trendError && (trendData?.data_points.length ?? 0) > 0;
  const groundedShown = grounded && grounded.observationId === effectiveObservation?.id ? grounded : null;

  const shell = (
    <>
      <div>
        <h1 className="font-display text-xl font-semibold text-ink tracking-tight lg:text-2xl">Results</h1>
        <p className="mt-1 hidden text-ink-secondary lg:block">Track changes in your test results over time</p>
      </div>

      <ExternalApiBreakGlassWarning
        active={externalApi?.use_external_api === true && externalApi.redaction_break_glass === true}
        unknown={
          externalApiError ||
          (externalApi?.use_external_api === true && externalApi.redaction_break_glass === undefined)
        }
      />

      <DisclaimerBanner />
    </>
  );

  if (observationsLoading) {
    return (
      <div className="space-y-3 lg:space-y-6">
        {shell}
        <div className="flex h-64 items-center justify-center" role="status" aria-live="polite">
          <Loader2 className="h-8 w-8 text-accent motion-safe:animate-spin" />
          <span className="sr-only">Loading observations...</span>
        </div>
      </div>
    );
  }

  if (observationsError) {
    return (
      <div className="space-y-3 lg:space-y-6">
        {shell}
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="mx-auto mb-3 h-12 w-12 text-status-attention" />
            <p className="text-ink-secondary">Failed to load observations</p>
          </div>
        </div>
      </div>
    );
  }

  if (!observations || observations.length === 0) {
    return (
      <div className="space-y-3 lg:space-y-6">
        {shell}
        <EmptyState
          icon={FileText}
          title="No data available"
          description="Import lab documents to see your trends and get plain-language explanations."
          action={
            <Button asChild variant="secondary">
              <Link to="/inbox">Import a lab report</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const panelMessage = (() => {
    if (activeTab === ALL) return null;
    if (panelError) return 'Could not load this panel. Choose All to see every result.';
    if (panelLoading || !panelData) return 'Loading this panel...';
    if (visibleList.length === 0) return 'No results from this panel yet.';
    return null;
  })();

  const trendBody = (() => {
    if (!effectiveAnalyte) {
      return (
        <div className="flex min-h-48 items-center justify-center">
          <p className="text-ink-secondary">Nothing to chart on this tab.</p>
        </div>
      );
    }
    if (trendLoading) {
      // Holds the ribbon's place, so the swap to the chart does not move the page (G2).
      return (
        <div className="mx-auto max-w-lg lg:max-w-none" aria-busy="true">
          <div className="aspect-square w-full lg:aspect-[2/1]" />
          <div className="min-h-48" />
        </div>
      );
    }
    if (trendError || !trendData) {
      return (
        <div className="flex min-h-48 items-center justify-center">
          <p className="text-ink-secondary">No trend data available for this analyte</p>
        </div>
      );
    }
    if (trendData.data_points.length === 0) {
      return (
        <div className="flex min-h-48 flex-col items-center justify-center gap-3">
          <p className="text-ink-secondary">{trendData.summary || 'No dated measurements to chart.'}</p>
          <p className="text-xs text-ink-tertiary">
            Collection dates could not be read from the source document.
            Re-import or reprocess the document, or verify the observation to set a date.
          </p>
        </div>
      );
    }
    return (
      <>
        <div ref={chartRef} className="mx-auto max-w-lg lg:max-w-none">
          <RangeRibbon trend={trendData} viewHeight={viewHeight} />
        </div>

        <div className="mt-4 rounded-xl bg-surface-muted p-3 sm:p-4">
          <div className="flex items-start gap-3">
            <Info className="mt-0.5 h-5 w-5 shrink-0 text-ink-secondary" />
            <div>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <p data-t0 className="text-sm text-ink">
                  <strong>
                    Latest value: {latestBand?.value ?? latestValue?.value} {trendData.unit}
                    {latestValue && latestValue.user_verified !== true && ' (unverified)'}
                  </strong>
                </p>
                {latestInsideRange && <Badge variant="verified">Normal Range</Badge>}
                {latestPlace === 'outside' && <Badge variant="attention">Outside Range</Badge>}
                {latestPlace !== 'outside' && latestValue?.is_abnormal && <Badge variant="attention">Flagged on the report</Badge>}
              </div>
              {trendData.summary && (
                <p data-t0 className="mt-1 text-sm text-ink-secondary">
                  {trendData.summary}
                </p>
              )}
              <UnverifiedTrendNote unverified={unverifiedPointCount} total={trendData.data_points.length} />
              {(trendData.excluded_count ?? 0) > 0 && (
                <p className="mt-1 text-sm text-ink-secondary">
                  {trendData.excluded_count} point(s) hidden — unrecognized unit
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="mt-4">
          <p className="mb-2 text-xs font-medium text-ink-secondary">
            Medications active at time of latest result
          </p>
          <MedicationOverlay medications={activeMedsForSelected} />
        </div>
      </>
    );
  })();

  return (
    <div className="space-y-3 lg:space-y-6">
      {shell}

      <Tabs value={activeTab} onValueChange={selectTab} activationMode="manual" className="space-y-3 lg:space-y-6">
        <TabsList aria-label="Lab panels" className="gap-1.5 overflow-x-auto border-b-0 sm:gap-2">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className={cn(
                'shrink-0 rounded-xl px-3 sm:px-4 after:hidden',
                activeTab === tab.id
                  ? 'bg-accent text-[var(--on-accent)] hover:text-[var(--on-accent)] data-[state=active]:text-[var(--on-accent)] shadow-soft'
                  : 'bg-surface-elevated border border-[var(--line)] text-ink-secondary hover:bg-surface-muted'
              )}
            >
              {tab.label}
              {panelData?.observations && activeTab === tab.id && tab.id !== ALL && (
                <span className="ml-1.5 text-xs tabular-nums">{panelData.observations.length}</span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value={activeTab} tabIndex={-1} className="mt-0 space-y-3 lg:space-y-6">
          {activeTab !== ALL && (
            <div>
              <Button
                onClick={handleGeneratePanelInterpretation}
                disabled={generatePanelInterp.isPending || !panelDate}
                className="gap-2"
              >
                {panelPending ? (
                  <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Interpret {activeTab.toUpperCase()} Panel
              </Button>
            </div>
          )}

          {(panelShown || panelPending || panelFailed) && (
            <PanelInterpretationDashboard
              interpretation={panelShown?.data}
              isLoading={panelPending}
              isError={panelFailed}
            />
          )}

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3 lg:gap-6">
            <div className="min-w-0 lg:col-start-3 lg:row-start-1">
              <h2 id="lab-results-heading" className="sr-only text-base font-semibold text-ink lg:not-sr-only lg:mb-2">
                Lab results
              </h2>
              <div
                role="region"
                aria-labelledby="lab-results-heading"
                tabIndex={0}
                className={cn(
                  'overflow-x-auto rounded-xl focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent',
                  'lg:overflow-visible lg:rounded-2xl lg:border lg:border-[var(--line)] lg:bg-surface-elevated'
                )}
              >
                {panelMessage ? (
                  <p className="p-3 text-sm text-ink-secondary lg:p-4">{panelMessage}</p>
                ) : (
                  <ul className="flex gap-2 p-0.5 lg:flex-col lg:gap-0 lg:divide-y lg:divide-[var(--line)] lg:p-0">
                    {visibleList.map((obs) => {
                      const selected = effectiveAnalyte === obs.analyte_canonical;
                      return (
                        <li key={obs.analyte_canonical} className="shrink-0 lg:shrink">
                          <button
                            type="button"
                            aria-current={selected ? 'true' : undefined}
                            onClick={() => setSelectedAnalyte(obs.analyte_canonical)}
                            className={cn(chipBase, selected && 'border-accent bg-accent-subtle lg:bg-accent-subtle')}
                          >
                            <span className="min-w-0 text-left">
                              <span className="block truncate text-sm font-medium text-ink">{obs.analyte_raw}</span>
                              <span data-t0 className="block text-xs text-ink-secondary">
                                {obs.value ?? obs.value_text} {obs.unit}
                                {obs.collected_at === null && (
                                  <>
                                    {' · '}
                                    <span className="italic text-ink-tertiary">undated</span>
                                  </>
                                )}
                              </span>
                            </span>
                            {obs.is_abnormal && obs.flag && (
                              <Badge variant="attention" className="px-1.5 py-0.5" aria-label="Flagged on the report">
                                !
                              </Badge>
                            )}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>

            <div className="min-w-0 space-y-3 lg:col-span-2 lg:col-start-1 lg:row-span-2 lg:row-start-1 lg:space-y-4">
              <Card>
                <CardHeader className="p-4 pb-2 sm:p-6 sm:pb-4">
                  <div className="flex items-start justify-between gap-2">
                    {/* One line on a phone (DF-4): a long display name is cut with an ellipsis, and the ribbon's own label
                        and the list row still carry it whole. The Normal/Outside badge sits with the latest value below. */}
                    <CardTitle className="flex min-w-0 items-center text-base sm:text-xl">
                      <span className="min-w-0 truncate" title={trendData?.analyte_display_name || effectiveAnalyte}>
                        {trendData?.analyte_display_name || effectiveAnalyte}
                      </span>
                    </CardTitle>
                    <div className="flex shrink-0 items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="gap-1.5 text-xs"
                        onClick={handleExportPNG}
                        disabled={!chartReady}
                        aria-label="Download chart as PNG"
                      >
                        <ImageIcon className="h-3.5 w-3.5" />
                        <span className="hidden sm:inline">PNG</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="gap-1.5 text-xs"
                        onClick={handleExportSVG}
                        disabled={!chartReady}
                        aria-label="Download chart as SVG"
                      >
                        <Download className="h-3.5 w-3.5" />
                        <span className="hidden sm:inline">SVG</span>
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-0 sm:p-6 sm:pt-0">{trendBody}</CardContent>
              </Card>

              {(unverifiedCount > 0 || lowConfidenceCount > 0) && (
                <div className="flex flex-wrap gap-2">
                  {unverifiedCount > 0 && <Badge variant="caution">{unverifiedCount} unverified values</Badge>}
                  {lowConfidenceCount > 0 && (
                    <Badge variant="attention">{lowConfidenceCount} low-confidence extractions</Badge>
                  )}
                </div>
              )}

              {!explainOpen ? (
                effectiveObservation && (
                  <Card>
                    <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                      <p className="text-sm text-ink-secondary">Want this result explained in plain language?</p>
                      <Button onClick={() => setExplainOpen(true)} className="gap-2">
                        <Sparkles className="h-4 w-4" />
                        Explain this result
                      </Button>
                    </CardContent>
                  </Card>
                )
              ) : interpretation ? (
                <InterpretedResultCard
                  interpretation={interpretation}
                  analyteName={effectiveObservation?.analyte_raw}
                  value={effectiveObservation?.value}
                  unit={effectiveObservation?.unit ?? undefined}
                  refLow={effectiveObservation?.ref_low}
                  refHigh={effectiveObservation?.ref_high}
                  onRegenerate={handleGenerateInterpretation}
                  isRegenerating={generateInterpretation.isPending}
                  observation={effectiveObservation ?? undefined}
                />
              ) : !interpLoading && effectiveObservation ? (
                <Card>
                  <CardContent className="py-8">
                    <div className="space-y-3 text-center">
                      <Brain className="mx-auto h-10 w-10 text-ink-tertiary" />
                      <div>
                        <p className="text-sm font-medium text-ink">No interpretation yet</p>
                        <p className="mt-1 text-xs text-ink-secondary">
                          Generate an AI interpretation for {effectiveObservation.analyte_raw}
                        </p>
                      </div>
                      <Button
                        onClick={handleGenerateInterpretation}
                        disabled={generateInterpretation.isPending}
                        className="gap-2"
                      >
                        {generateInterpretation.isPending ? (
                          <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
                        ) : (
                          <Sparkles className="h-4 w-4" />
                        )}
                        Generate Interpretation
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : interpLoading ? (
                <Card>
                  <CardContent className="py-8">
                    <div className="flex items-center justify-center gap-2 text-sm text-ink-secondary">
                      <Loader2 className="h-5 w-5 text-accent motion-safe:animate-spin" />
                      Loading interpretation...
                    </div>
                  </CardContent>
                </Card>
              ) : null}

              {/* The polite live region stays mounted so screen readers announce the notice when it appears inside it. */}
              {effectiveObservation && (
                <div aria-live="polite" data-testid="withheld-live-region">
                  {withheldNotice && withheldNotice.observationId === effectiveObservation.id && (
                    <Card role="status">
                      <CardContent className="space-y-2 py-4">
                        <p className="text-sm font-medium text-ink">
                          Asclexis could not produce a safe explanation for this result.
                        </p>
                        <p className="text-sm text-ink-secondary">{withheldNotice.message}</p>
                        {withheldNotice.physicianReview && (
                          <p className="text-sm text-ink-secondary">
                            This result may need prompt attention. Please contact your clinician promptly.
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {groundedShown && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex flex-wrap items-center gap-3 text-base">
                      Grounded explanation
                      <Badge variant={groundedShown.isValid ? 'verified' : 'caution'}>
                        Grounded faithfulness: {(groundedShown.score * 100).toFixed(0)}%
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div data-t0 className="space-y-2">
                      {formatInterpretationText(groundedShown.summary).paragraphs.map((runs, i) => (
                        <p key={i} className="whitespace-pre-wrap text-sm text-ink-secondary">
                          {runs.map((run, j) =>
                            run.bold ? <strong key={j}>{run.text}</strong> : <span key={j}>{run.text}</span>
                          )}
                        </p>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            <Card className="min-w-0 border-accent/20 bg-accent-subtle lg:col-start-3 lg:row-start-2 lg:self-start">
              <CardContent className="p-4">
                <p className="mb-1 text-sm font-medium text-ink">Need help understanding?</p>
                <p className="mb-3 text-xs text-ink-secondary">
                  Ask our assistant to explain any test result in plain language.
                </p>
                <Button size="sm" className="w-full" onClick={() => navigate('/explain')}>
                  Open Explain
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
