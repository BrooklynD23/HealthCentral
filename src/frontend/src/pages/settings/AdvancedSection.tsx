/**
 * Advanced section (UI-PG-SETTINGS): OCR, environment and tools, hardware, model tiers, current status and the
 * training-data export. Collapsed behind "Show advanced settings" and off by default.
 *
 * The model tiers come first and the diagnostics list last (G10, stillness): the Ready, Download and Incompatible text is
 * T0, and the diagnostics list changes height when its data arrives, so it must not sit above that text.
 *
 * The panels mount only after the button is pressed, and so do their requests, except the settings and the tiers: those
 * start when the section mounts (AdvancedReads). Their loading and error states are this section's: the other sections
 * never wait on model settings.
 */

import { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  HardDrive,
  Download,
  Check,
  AlertCircle,
  Loader2,
  Zap,
  Server,
  FileText,
  Wrench,
  Copy,
  Database,
  ChevronDown,
  ChevronUp,
  Download as DownloadIcon,
  Settings as SettingsIcon,
} from 'lucide-react';
import { m, AnimatePresence } from 'framer-motion';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, Skeleton, modalVariants, backdropVariants } from '@/components/ui';
import { AlertDialog } from '@/components/ui/AlertDialog';
import { TierCapabilities } from '@/components/settings/TierCapabilities';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  useModelSettings,
  useDetectHardware,
  useSetTier,
  useTiers,
  useDownloadProgress,
  useStartDownload,
  useExternalApiSettings,
  useSaveOcrPreference,
  useEnvironmentDiagnostics,
  useRecheckDiagnostics,
} from '@/services';
import { useFeedbackStats, useExportDataset } from '@/services/feedback';
import type { DownloadProgress, TierStatus } from '@/services/modelSettings';
import { SwitchRow, AfterPaint } from './PreferencesSection';

const OCR_BLOCKER_LABELS: Record<string, string> = {
  disabled_by_admin: 'OCR is disabled in server configuration (OCR_ENABLED). Restart the backend after changing .env.',
  tesseract_missing: 'Install Tesseract OCR and add it to PATH.',
  user_disabled: 'Turn on document OCR below for this profile.',
};

const tierDescriptions: Record<string, { label: string; desc: string; icon: typeof Zap }> = {
  low: { label: 'Low (Qwen2.5 0.5B)', desc: 'Fast, lightweight — works on most hardware', icon: Zap },
  mid: { label: 'Mid (Phi-4-mini)', desc: 'Balanced speed and quality', icon: Server },
  high: { label: 'High (BioMistral 7B)', desc: 'Best quality', icon: Cpu },
};

function hasActiveDownloadEntry(progress: Record<string, DownloadProgress> | undefined): boolean {
  return Object.values(progress ?? {}).some((p) => p.status === 'pending' || p.status === 'downloading');
}

/** RAM in GB that the tier asks for, from the tier's own requirements; null when it asks for none or none were sent. */
function requiredRamGb(tier: TierStatus): number | null {
  const ram = tier.requirements?.ram_gb;
  return typeof ram === 'number' && ram > 0 ? ram : null;
}

/**
 * The line under a tier's name. The RAM figure is the backend's requirement for that tier, not a constant here.
 * A tier with a model never shows the backend's template text: the backend has no display text for the tier ids
 * it does not list, and sends the template tier's "Template-based interpretations (no AI model)" for them.
 */
function tierDescription(tier: TierStatus): string {
  const ram = requiredRamGb(tier);
  const needs = ram === null ? '' : ` — needs ${ram}GB+ RAM`;
  const known = tierDescriptions[tier.tier];
  if (known) return tier.tier === 'high' || tier.tier === 'low' ? `${known.desc}${needs}` : known.desc;
  const hasModel = (tier.capabilities?.context_size ?? 0) > 0;
  if (tier.tier !== 'template' && hasModel) return `Runs a local model${needs}`;
  return tier.description;
}

/** What the last training-data export wrote: the only statement of the counts and where the file is. */
export interface TrainingExportResult {
  dpo: number;
  sft: number;
  grpo: number;
  path: string;
}

interface AdvancedSectionProps {
  /** Held by the page, which outlives the section: the result must still be there when the user comes back. */
  exportResult: TrainingExportResult | null;
  onExportResult: (result: TrainingExportResult) => void;
}

export function AdvancedSection({ exportResult, onExportResult }: AdvancedSectionProps) {
  const [shown, setShown] = useState(false);
  const panelId = useId();

  return (
    <div className="space-y-6">
      <Button
        variant="secondary"
        aria-expanded={shown}
        aria-controls={panelId}
        onClick={() => setShown((value) => !value)}
        className="gap-2"
      >
        {shown ? <ChevronUp className="h-4 w-4" aria-hidden="true" /> : <ChevronDown className="h-4 w-4" aria-hidden="true" />}
        {shown ? 'Hide advanced settings' : 'Show advanced settings'}
      </Button>
      <AdvancedReads />
      {shown && (
        <div id={panelId}>
          <AdvancedPanels exportResult={exportResult} onExportResult={onExportResult} />
        </div>
      )}
    </div>
  );
}

/**
 * Starts the two reads the panels wait on when the section mounts, so that a press after they settle renders the panels
 * once, with no skeleton before them: a skeleton and then the panels is two layouts straight after the press, and the
 * tasks between them were what G10's sampler waited behind (HC-UISET-021). Download progress and the cards' own reads
 * stay in the panels. A component of its own, rendering nothing: a hook whose result is not read re-renders its component
 * on every change to the query, which here is this and not the open panels.
 */
function AdvancedReads() {
  useModelSettings();
  useTiers();
  return null;
}

function AdvancedPanels({ exportResult, onExportResult }: AdvancedSectionProps) {
  // The panels wait on the model settings and on the tiers, and say so when the settings cannot load. Both requests start
  // together (HC-UISET-020), at the section's mount: the tier card used to ask for the tiers after the settings reply, a second
  // round trip, and a card of skeleton blocks that becomes seven rows moves everything under it. One skeleton, then all of it.
  // A press after a read that failed asks again (react-query retries an errored query when an observer mounts) and shows the
  // skeleton while it does, as a press did when it made the first request (HC-UISET-021). A tiers request that fails is waited
  // on with its retry (the app's query client retries once, about a second later), and then the tier card says there are no
  // tiers to show. Each card below asks for the rest itself, so a reply re-renders its own card and not the whole panel:
  // opening Advanced is a burst of replies, and one
  // render of the whole panel per reply would add a task to that burst for each of them (G10, stillness; the readings
  // found a burst of tasks under 50 ms at dev x1, not one long task).
  const { isLoading: settingsLoading, isError } = useModelSettings();
  const { isLoading: tiersLoading } = useTiers();
  // Waited on once. A tiers request that failed is asked again when the tier card mounts (react-query retries an errored
  // query on mount) and reads as loading again: waiting on that would unmount the card, which asks again, in a loop.
  const tiersSettled = useRef(false);
  if (!tiersLoading) tiersSettled.current = true;
  const isLoading = settingsLoading || (tiersLoading && !tiersSettled.current);

  if (isLoading) {
    return (
      <div data-testid="advanced-loading" className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Skeleton className="h-40 rounded-2xl" />
          <Skeleton className="h-40 rounded-2xl" />
          <Skeleton className="h-80 rounded-2xl" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-48 rounded-2xl" />
          <Skeleton className="h-64 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-24 text-status-attention">
        <AlertCircle className="w-6 h-6 mr-2" />
        <span>Failed to load settings. Please try again.</span>
      </div>
    );
  }

  return (
    <>
      {/* Three columns from xl (1280 px), two from lg, one below. The tiers sit alone in the first column and nothing
          above or beside them changes height when data arrives (G10); the diagnostics list, whose height does change,
          sits in the last column. Expanded, the page is 1764 px by default and 1843 px with a download running (the progress
          bar adds the difference), against the 1800 px bound of HC-UISET-005: the second figure is over the bound and is
          not ruled yet. */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)_minmax(0,1fr)] lg:items-start">
        <div className="space-y-6">
          <TierCard />
        </div>

        <div className="space-y-6">
          <AfterPaint frames={1}>
            <HardwareCard />
            <OcrCard />
            <StatusCard />
          </AfterPaint>
        </div>

        <div className="space-y-6 lg:col-span-2 xl:col-span-1">
          <AfterPaint frames={2}>
            <EnvironmentCard />
            <TrainingCard exportResult={exportResult} onExportResult={onExportResult} />
          </AfterPaint>
        </div>
      </div>
    </>
  );
}

function TierCard() {
  const { data: settings } = useModelSettings();
  const { data: tiersData } = useTiers();
  const setTier = useSetTier();
  const startDownload = useStartDownload();
  const queryClient = useQueryClient();
  // The panels unmount on Hide and on every change of section, and a download goes on in the backend meanwhile. The
  // progress is asked for as soon as the panels open, not only after a press here: the page may have been left for longer
  // than the query cache keeps an entry (5 minutes), and a download can also have been started by a reload or another
  // window. Asking is what keeps the bar moving and Download disabled while the tier is downloading.
  const { data: downloadProgress } = useDownloadProgress(true);

  // Derive active download status from progress data
  const hasActiveDownload = hasActiveDownloadEntry(downloadProgress);
  const isDownloading = hasActiveDownload || startDownload.isPending;

  // When a download transitions to completed, refresh tier list and settings
  const prevProgressRef = useRef<typeof downloadProgress>(undefined);
  useEffect(() => {
    const prev = prevProgressRef.current;
    prevProgressRef.current = downloadProgress;
    if (!prev || !downloadProgress) return;
    // A tier that is completed now and was not on the previous poll. Not "the previous poll was pending or downloading":
    // a second task can share the key of a first one (a second window's POST). The server reports the tier as `failed`
    // (api/model_settings.py) by two real routes: the first task really fails while the second runs (its real error, then
    // completed), or the second task's first write lands after the first dropped the key (the fixed failed answer, then
    // completed). The common order is downloading, downloading, completed. A rule that needs the previous poll to be active
    // would miss the refresh after downloading, failed, completed.
    const justCompleted = Object.entries(downloadProgress).some(
      ([tier, p]) => p.status === 'completed' && prev[tier]?.status !== 'completed'
    );
    if (justCompleted) {
      queryClient.invalidateQueries({ queryKey: ['model-settings'] });
      queryClient.invalidateQueries({ queryKey: ['model-settings', 'tiers'] });
    }
  }, [downloadProgress, queryClient]);

  const handleSetTier = (tier: string) => {
    setTier.mutate(tier);
  };

  const handleStartDownload = (tier: string) => {
    startDownload.mutate(tier);
  };

  return (
    <Card>
      <CardHeader className="border-b border-black/4">
        <CardTitle className="flex items-center gap-3">
          <HardDrive className="w-5 h-5 text-ink-secondary" />
          Model Tier
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6 space-y-3">
        {tiersData?.tiers.map((tier) => {
          const desc = tierDescriptions[tier.tier];
          const isSelected = settings?.preferred_tier === tier.tier;
          const isRecommended = tiersData.recommended_tier === tier.tier;
          const TierIcon = desc?.icon || Server;

          return (
            <div
              key={tier.tier}
              data-testid={`tier-row-${tier.tier}`}
              className={cn(
                // A tier column is about 340 px wide from xl (three columns): the buttons go under the text there, and beside it
                // again from 2xl, where the columns are wide enough.
                'flex flex-col gap-3 px-4 py-4 rounded-xl border sm:flex-row sm:items-center sm:justify-between xl:flex-col xl:items-stretch 2xl:flex-row 2xl:items-center',
                isSelected
                  ? 'border-accent bg-accent-subtle shadow-xs'
                  : 'border-black/6'
              )}
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className={cn('p-2 rounded-lg', isSelected ? 'bg-accent/10' : 'bg-surface-muted')}>
                  <TierIcon className={cn('w-5 h-5', isSelected ? 'text-accent' : 'text-ink-secondary')} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className={cn('text-sm font-bold', isSelected ? 'text-accent' : 'text-ink')}>
                      {desc?.label || tier.tier}
                    </p>
                    {isRecommended && (
                      <Badge variant="accent" className="text-xs uppercase tracking-wider font-bold">Recommended</Badge>
                    )}
                  </div>
                  <p className="text-xs text-ink-secondary mt-0.5">{tierDescription(tier)}</p>
                  <TierCapabilities capabilities={tier.capabilities} />
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {tier.downloaded ? (
                  <Badge variant="verified" className="gap-1 font-bold" data-t0="">
                    <Check className="w-3 h-3" />
                    Ready
                  </Badge>
                ) : tier.can_run ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    // The word "Download" is T0 (the span below), and the Button around it must not move it: a disabled
                    // Button is half opacity by default (disabled:opacity-100), a colour change would break G10 as the
                    // opacity did (no disabled:text-*), and the press scale moves the word's rect (active:scale-100).
                    // The spinner in place of the arrow is what says the tier is downloading.
                    className="gap-1.5 h-8 border-black/6 text-xs font-bold disabled:opacity-100 active:scale-100"
                    onClick={() => handleStartDownload(tier.tier)}
                    disabled={isDownloading}
                  >
                    {isDownloading ? (
                      <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                    ) : (
                      <Download className="w-3 h-3" />
                    )}
                    <span data-t0="">Download</span>
                  </Button>
                ) : (
                  <Badge variant="default" data-t0="">Incompatible</Badge>
                )}
                {!isSelected && (tier.downloaded || tier.can_run) && (
                  <Button
                    variant={isSelected ? 'primary' : 'ghost'}
                    size="sm"
                    className="h-8 text-xs font-bold"
                    onClick={() => handleSetTier(tier.tier)}
                    disabled={setTier.isPending}
                  >
                    Select
                  </Button>
                )}
              </div>
            </div>
          );
        }) ?? (
          <div className="text-center py-12 border-2 border-dashed border-black/4 rounded-2xl">
            <p className="text-sm text-ink-secondary">
              Run hardware detection first to see available tiers.
            </p>
          </div>
        )}

        {/* Download Progress */}
        <AnimatePresence>
          {downloadProgress && Object.entries(downloadProgress).map(([progressTier, progress]) => {
            if (progress.status !== 'downloading' && progress.status !== 'pending') return null;
            const pct = progress.progress <= 1 && progress.progress > 0
              ? Math.round(progress.progress * 100)
              : Math.round(progress.progress);
            const isIndeterminate = pct === 0;
            const label = progress.status === 'pending' ? 'Preparing…' : `${pct}%`;
            return (
              <m.div
                key={progressTier}
                initial={{ opacity: 0, height: 0, marginTop: 0 }}
                animate={{ opacity: 1, height: 'auto', marginTop: 12 }}
                exit={{ opacity: 0, height: 0, marginTop: 0 }}
                className="rounded-xl bg-surface-muted p-4 border border-black/4 overflow-hidden"
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-bold text-ink capitalize flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin text-accent" />
                    Downloading {progressTier}…
                  </p>
                  <p className="text-xs font-bold text-accent">{label}</p>
                </div>
                <div className="w-full bg-black/6 rounded-full h-2 overflow-hidden">
                  {isIndeterminate ? (
                    <div className="h-2 w-1/3 bg-accent rounded-full motion-safe:animate-shimmer" />
                  ) : (
                    <m.div
                      className="bg-accent rounded-full h-2"
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  )}
                </div>
                {progress.total_bytes > 0 && (
                  <p className="text-xs text-ink-tertiary mt-2 font-medium">
                    {(progress.downloaded_bytes / 1_073_741_824).toFixed(2)} GB / {(progress.total_bytes / 1_073_741_824).toFixed(2)} GB
                  </p>
                )}
              </m.div>
            );
          })}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}

function HardwareCard() {
  const { data: settings } = useModelSettings();
  const detectHardware = useDetectHardware();

  return (
    <Card>
      <CardHeader className="border-b border-black/4">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Cpu className="w-5 h-5 text-ink-secondary" />
            Hardware Detection
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="gap-1.5 whitespace-nowrap border-black/6"
            onClick={() => detectHardware.mutate()}
            disabled={detectHardware.isPending}
          >
            {detectHardware.isPending ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            ) : (
              <Cpu className="w-4 h-4" />
            )}
            {settings?.hardware_info ? 'Re-detect' : 'Detect Hardware'}
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        {settings?.hardware_info ? (
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl bg-surface-muted p-4 border border-black/2">
              <p className="text-xs text-ink-tertiary mb-1 font-medium uppercase tracking-wider">RAM</p>
              <p className="text-sm font-bold text-ink">{settings.hardware_info.ram_total_gb.toFixed(1)} GB</p>
            </div>
            <div className="rounded-xl bg-surface-muted p-4 border border-black/2">
              <p className="text-xs text-ink-tertiary mb-1 font-medium uppercase tracking-wider">CPU</p>
              <p className="text-sm font-bold text-ink">{settings.hardware_info.cpu_cores} cores</p>
              <p className="text-xs text-ink-tertiary truncate font-medium">{settings.hardware_info.cpu_name || 'Unknown'}</p>
            </div>
            <div className="rounded-xl bg-surface-muted p-4 border border-black/2">
              <p className="text-xs text-ink-tertiary mb-1 font-medium uppercase tracking-wider">Disk Free</p>
              <p className="text-sm font-bold text-ink">{settings.hardware_info.disk_free_gb.toFixed(1)} GB</p>
            </div>
            <div className="rounded-xl bg-surface-muted p-4 border border-black/2">
              <p className="text-xs text-ink-tertiary mb-1 font-medium uppercase tracking-wider">GPU</p>
              <p className="text-sm font-bold text-ink">
                {settings.hardware_info.gpu_name || 'Not detected'}
              </p>
              {settings.hardware_info.gpu_vram_gb && (
                <p className="text-xs text-ink-tertiary font-medium">{settings.hardware_info.gpu_vram_gb} GB VRAM</p>
              )}
            </div>
            <div className="col-span-2 rounded-xl bg-accent-subtle p-4 border border-accent/10">
              <p className="text-xs text-accent mb-1 font-bold uppercase tracking-wider">Recommended Tier</p>
              <p className="text-lg font-display font-bold text-accent capitalize">
                {settings.hardware_info.recommended_tier}
              </p>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 border-2 border-dashed border-black/4 rounded-2xl">
            <Cpu className="w-10 h-10 text-ink-tertiary mx-auto mb-3 opacity-50" />
            <p className="text-sm text-ink-secondary max-w-[240px] mx-auto">
              Run hardware detection to see recommended model settings.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function OcrCard() {
  const { data: settings } = useModelSettings();
  const saveOcr = useSaveOcrPreference();

  return (
    <Card>
      <CardHeader className="border-b border-black/4">
        <CardTitle className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-ink-secondary" />
          Document import (OCR)
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6 space-y-3">
        <p className="text-sm text-ink-secondary">
          Extract text from scanned PDFs and lab images using Tesseract. Your preference applies to this profile;
          the server must also allow OCR (<code className="text-xs bg-surface-muted px-1 rounded-sm">OCR_ENABLED</code>).
        </p>
        <SwitchRow
          label="Enable OCR for scans & images"
          checked={settings?.ocr_preference_enabled === true}
          onCheckedChange={() => {
            saveOcr.mutate(!settings?.ocr_preference_enabled);
          }}
          disabled={saveOcr.isPending}
        />
        <div
          className={cn(
            'rounded-xl px-3 py-2.5 text-sm border',
            settings?.ocr_effective
              ? 'bg-status-verified-subtle border-status-verified/20 text-status-verified'
              : 'bg-status-attention-subtle border-status-attention/20 text-status-attention'
          )}
        >
          {settings?.ocr_effective ? (
            <span>OCR is active for this profile (Tesseract + server allow).</span>
          ) : (
            <div className="space-y-1">
              <p className="font-medium">OCR is blocked</p>
              <ul className="list-disc pl-4 text-xs space-y-0.5 opacity-90">
                {(settings?.ocr_blockers ?? []).map((b) => (
                  <li key={b}>{OCR_BLOCKER_LABELS[b] ?? b}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function StatusCard() {
  const { data: settings } = useModelSettings();
  const { data: externalApiData, isError: externalApiError } = useExternalApiSettings();
  const externalEnabled = externalApiData?.use_external_api ?? false;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Current Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted border border-black/2">
          <span className="text-sm text-ink-secondary">Active Tier</span>
          <Badge variant="verified" className="capitalize font-bold">
            {settings?.current_tier || 'none'}
          </Badge>
        </div>
        <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted border border-black/2">
          <span className="text-sm text-ink-secondary">Preferred</span>
          <span className="text-sm font-bold text-ink capitalize">
            {settings?.preferred_tier || 'auto'}
          </span>
        </div>
        <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted border border-black/2">
          <span className="text-sm text-ink-secondary">External API</span>
          {/* A failed read is not "Off": the setting is unknown, and the patient has to be told so. */}
          <Badge variant={externalApiError ? 'caution' : externalEnabled ? 'verified' : 'default'} className="font-bold">
            {externalApiError ? 'Unknown' : externalEnabled ? 'Enabled' : 'Off'}
          </Badge>
        </div>
        <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted border border-black/2">
          <span className="text-sm text-ink-secondary">OCR (profile)</span>
          <Badge variant={settings?.ocr_effective ? 'verified' : 'attention'} className="font-bold">
            {settings?.ocr_effective ? 'Ready' : 'Blocked'}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function EnvironmentCard() {
  const [diagToolId, setDiagToolId] = useState<string | null>(null);
  const { data: diagnostics, isLoading: diagnosticsLoading } = useEnvironmentDiagnostics();
  const recheckDiagnostics = useRecheckDiagnostics();
  const prefersReducedMotion = useReducedMotion();
  const focusedDiag = diagnostics?.components.find((c) => c.id === diagToolId) ?? null;

  return (
    <>
      <Card>
        <CardHeader className="border-b border-black/4">
          <CardTitle className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-3">
              <Wrench className="w-5 h-5 text-ink-secondary" />
              Environment &amp; tools
            </div>
            <Button
              variant="secondary"
              size="sm"
              className="gap-1.5 whitespace-nowrap border-black/6"
              onClick={() => recheckDiagnostics.mutate()}
              disabled={recheckDiagnostics.isPending || diagnosticsLoading}
            >
              {recheckDiagnostics.isPending ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <Wrench className="w-4 h-4" />
              )}
              Re-check
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-2">
          <p className="text-sm text-ink-secondary mb-2">
            Local dependencies for OCR, encryption, models, and GPU. Use the fix menu for copy-paste install hints.
          </p>
          {diagnosticsLoading && !diagnostics ? (
            <Skeleton className="h-24 rounded-xl" />
          ) : (
            (diagnostics?.components ?? []).map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl bg-surface-muted border border-black/4"
              >
                <div className="min-w-0">
                  {/* The label wraps, the detail stops at two lines: the column is narrow from xl. The whole detail is the
                      title and is printed whole by the fix dialog (Fix <label>). */}
                  <p className="text-sm font-medium text-ink break-words">{c.label}</p>
                  <p className="text-xs text-ink-tertiary line-clamp-2 break-words" title={c.detail}>{c.detail}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge
                    variant={
                      c.status === 'ok'
                        ? 'verified'
                        : c.status === 'error'
                          ? 'attention'
                          : 'caution'
                    }
                    className="capitalize"
                  >
                    {c.status}
                  </Badge>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    aria-label={`Fix ${c.label}`}
                    onClick={() => setDiagToolId(c.id)}
                  >
                    <SettingsIcon className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Diagnostics fix actions (moved unchanged from SettingsPage) */}
      <AnimatePresence>
        {focusedDiag && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <m.div
              initial="initial"
              animate="animate"
              exit="exit"
              variants={backdropVariants}
              className="absolute inset-0 bg-black/40 backdrop-blur-xs"
              onClick={() => setDiagToolId(null)}
              aria-hidden
            />
            <m.div
              initial="initial"
              animate="animate"
              exit="exit"
              variants={modalVariants}
              transition={{ type: prefersReducedMotion ? 'tween' : 'spring', duration: prefersReducedMotion ? 0.15 : undefined }}
              className="relative w-full max-w-md rounded-2xl bg-surface-elevated border border-black/8 shadow-xl p-6 max-h-[85vh] overflow-y-auto"
              role="dialog"
              aria-labelledby="diag-tool-title"
            >
              <h2 id="diag-tool-title" className="font-display font-semibold text-lg text-ink">
                {focusedDiag.label}
              </h2>
              <p className="text-sm text-ink-secondary mt-2">{focusedDiag.detail}</p>
              <div className="mt-4 space-y-2">
                {focusedDiag.fix_actions.length === 0 ? (
                  <p className="text-xs text-ink-tertiary">No automated fix steps. Check docs or reinstall the component.</p>
                ) : (
                  focusedDiag.fix_actions.map((a, i) => (
                    <div
                      key={`${a.label}-${i}`}
                      className="rounded-xl border border-black/6 p-3 bg-surface-muted"
                    >
                      <p className="text-xs font-bold text-ink-tertiary uppercase tracking-wide">{a.label}</p>
                      {a.type === 'copy_command' && a.command && (
                        <div className="mt-2 flex items-start gap-2">
                          <code className="text-xs flex-1 break-all bg-surface-elevated rounded-lg px-2 py-1.5 border border-black/6">
                            {a.command}
                          </code>
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            className="shrink-0 h-8 px-2"
                            onClick={() => navigator.clipboard.writeText(a.command!)}
                            aria-label="Copy command"
                          >
                            <Copy className="w-4 h-4" />
                          </Button>
                        </div>
                      )}
                      {a.type === 'open_url' && a.url && (
                        <div className="mt-2">
                          {a.url.startsWith('/') ? (
                            <Link
                              // The backend sends url="/settings" (environment_diagnostics.py), which is now Profile & security.
                              // This dialog opens in Advanced, so the link goes back there.
                              to={a.url === '/settings' ? '/settings?section=advanced' : a.url}
                              className="text-sm font-medium text-accent hover:underline"
                              onClick={() => setDiagToolId(null)}
                            >
                              Open {a.url}
                            </Link>
                          ) : (
                            <a href={a.url} className="text-sm font-medium text-accent hover:underline" target="_blank" rel="noreferrer">
                              Open link
                            </a>
                          )}
                        </div>
                      )}
                      {a.type === 'rerun_detection' && (
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          className="mt-2"
                          onClick={() => {
                            recheckDiagnostics.mutate();
                            setDiagToolId(null);
                          }}
                        >
                          Re-run diagnostics
                        </Button>
                      )}
                    </div>
                  ))
                )}
              </div>
              <Button type="button" variant="ghost" className="mt-6 w-full" onClick={() => setDiagToolId(null)}>
                Close
              </Button>
            </m.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}

function TrainingCard({ exportResult, onExportResult }: AdvancedSectionProps) {
  const [showExportDialog, setShowExportDialog] = useState(false);
  const { data: feedbackStats } = useFeedbackStats();
  const exportDataset = useExportDataset();

  // The export confirm has no Trigger, so Radix has nothing to return focus to: the button that opened it gets it back
  // once the dialog has closed. Not in the close handler: the dialog's focus trap is still on there.
  const exportButtonRef = useRef<HTMLButtonElement>(null);
  const exportWasOpen = useRef(false);
  useEffect(() => {
    if (exportWasOpen.current && !showExportDialog) exportButtonRef.current?.focus();
    exportWasOpen.current = showExportDialog;
  }, [showExportDialog]);

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5 text-ink-secondary" />
            Training Data
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-ink-secondary">
            Thumbs-up/down feedback you give on assistant responses is stored locally and can
            be exported as a DPO/GRPO-ready preference dataset for offline fine-tuning.
          </p>

          {feedbackStats && (
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl bg-surface-muted p-3 text-center">
                <p className="text-2xl font-semibold text-ink">{feedbackStats.total_feedback}</p>
                <p className="text-xs text-ink-secondary mt-1">Total ratings</p>
              </div>
              <div className="rounded-xl bg-status-success/10 p-3 text-center">
                <p className="text-2xl font-semibold text-status-success">{feedbackStats.positive_count}</p>
                <p className="text-xs text-ink-secondary mt-1">Helpful</p>
              </div>
              <div className="rounded-xl bg-status-danger/10 p-3 text-center">
                <p className="text-2xl font-semibold text-status-danger">{feedbackStats.negative_count}</p>
                <p className="text-xs text-ink-secondary mt-1">Not helpful</p>
              </div>
            </div>
          )}

          {feedbackStats && feedbackStats.correction_count > 0 && (
            <p className="text-xs text-ink-secondary">
              {feedbackStats.correction_count} correction{feedbackStats.correction_count !== 1 ? 's' : ''} provided
              — these become &ldquo;chosen&rdquo; examples in DPO pairs.
            </p>
          )}

          {exportResult && (
            <div className="rounded-xl bg-status-success/10 p-3 text-sm text-status-success space-y-1">
              <p className="font-medium">Export complete</p>
              <p className="text-xs text-ink-secondary">
                {exportResult.dpo} DPO pairs · {exportResult.sft} SFT positives · {exportResult.grpo} reward records
              </p>
              <p className="text-xs text-ink-tertiary break-all">{exportResult.path}</p>
            </div>
          )}

          <Button
            ref={exportButtonRef}
            variant="secondary"
            onClick={() => setShowExportDialog(true)}
            disabled={!feedbackStats || feedbackStats.total_feedback === 0}
            className="gap-2"
          >
            <DownloadIcon className="w-4 h-4" />
            Export training data
          </Button>

          {(!feedbackStats || feedbackStats.total_feedback === 0) && (
            <p className="text-xs text-ink-tertiary">
              Rate some assistant responses first to enable export.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Export confirmation dialog: holds the redaction statement, so it is still (M0). */}
      <AlertDialog
        open={showExportDialog}
        onOpenChange={setShowExportDialog}
        still
        title="Export training data?"
      >
        <div className="space-y-4">
          <p className="text-sm text-ink-secondary">
            This will write JSONL files (DPO pairs, SFT positives, GRPO rewards) to your local
            filesystem. Redaction is applied to all prompt and response text before writing.
          </p>
          <p className="text-xs text-ink-tertiary">
            Files are stored locally only and never uploaded. No network calls are made.
          </p>
          <div className="flex gap-3 justify-end">
            <Button variant="ghost" data-alert-cancel="" onClick={() => setShowExportDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={async () => {
                setShowExportDialog(false);
                try {
                  const res = await exportDataset.mutateAsync({ confirmed: true });
                  onExportResult({
                    dpo: res.dpo_pairs_count,
                    sft: res.sft_positives_count,
                    grpo: res.grpo_rewards_count,
                    path: res.metadata_path,
                  });
                } catch {
                  // error surfaced by React Query
                }
              }}
              disabled={exportDataset.isPending}
            >
              {exportDataset.isPending ? 'Exporting…' : 'Confirm Export'}
            </Button>
          </div>
        </div>
      </AlertDialog>
    </>
  );
}
