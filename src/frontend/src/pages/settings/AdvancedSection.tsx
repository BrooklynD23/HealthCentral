/**
 * Advanced section (UI-PG-SETTINGS): OCR, environment and tools, hardware, model tiers, current status and the
 * training-data export. Collapsed behind "Show advanced settings" and off by default.
 *
 * The model tiers come first and the diagnostics list last (G10, stillness): the Ready, Download and Incompatible text is
 * T0, and the diagnostics list changes height when its data arrives, so it must not sit above that text.
 *
 * The panels (and so their requests) mount only after the button is pressed. Their loading and error states
 * are this section's: the other sections never wait on model settings.
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
import { SwitchRow } from './PreferencesSection';

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

// The query key of useDownloadProgress (services/modelSettings.ts).
const DOWNLOAD_PROGRESS_KEY = ['model-settings', 'download-progress'];

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

export function AdvancedSection() {
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
      {shown && (
        <div id={panelId}>
          <AdvancedPanels />
        </div>
      )}
    </div>
  );
}

function AdvancedPanels() {
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportResult, setExportResult] = useState<{ dpo: number; sft: number; grpo: number; path: string } | null>(null);
  const [diagToolId, setDiagToolId] = useState<string | null>(null);

  const { data: settings, isLoading, isError } = useModelSettings();
  const { data: tiersData } = useTiers();
  const detectHardware = useDetectHardware();
  const setTier = useSetTier();
  const startDownload = useStartDownload();
  const { data: externalApiData, isError: externalApiError } = useExternalApiSettings();
  const saveOcr = useSaveOcrPreference();
  const { data: diagnostics, isLoading: diagnosticsLoading } = useEnvironmentDiagnostics();
  const { data: feedbackStats } = useFeedbackStats();
  const exportDataset = useExportDataset();
  const recheckDiagnostics = useRecheckDiagnostics();

  // The export confirm has no Trigger, so Radix has nothing to return focus to: the button that opened it gets it back
  // once the dialog has closed. Not in the close handler: the dialog's focus trap is still on there.
  const exportButtonRef = useRef<HTMLButtonElement>(null);
  const exportWasOpen = useRef(false);
  useEffect(() => {
    if (exportWasOpen.current && !showExportDialog) exportButtonRef.current?.focus();
    exportWasOpen.current = showExportDialog;
  }, [showExportDialog]);

  const focusedDiag = diagnostics?.components.find((c) => c.id === diagToolId) ?? null;
  const queryClient = useQueryClient();
  const prefersReducedMotion = useReducedMotion();
  // The panels unmount on Hide and on every change of section, and a download goes on in the backend meanwhile. The
  // progress query is cached, so a download that was running when the user left is still in the cache when they return:
  // follow it from the start, or the bar freezes, polling stops and Download is enabled while the tier is downloading.
  const [downloadInitiated, setDownloadInitiated] = useState(() =>
    hasActiveDownloadEntry(queryClient.getQueryData<Record<string, DownloadProgress>>(DOWNLOAD_PROGRESS_KEY))
  );
  const { data: downloadProgress } = useDownloadProgress(downloadInitiated);

  // Derive active download status from progress data
  const hasActiveDownload = downloadInitiated && hasActiveDownloadEntry(downloadProgress);
  const isDownloading = hasActiveDownload || startDownload.isPending;

  // When a download transitions to completed, refresh tier list and settings
  const prevProgressRef = useRef<typeof downloadProgress>(undefined);
  useEffect(() => {
    const prev = prevProgressRef.current;
    prevProgressRef.current = downloadProgress;
    if (!prev || !downloadProgress) return;
    const justCompleted = Object.values(downloadProgress).some(
      (p) => p.status === 'completed'
    ) && Object.values(prev).some(
      (p) => p.status === 'pending' || p.status === 'downloading'
    );
    if (justCompleted) {
      queryClient.invalidateQueries({ queryKey: ['model-settings'] });
      queryClient.invalidateQueries({ queryKey: ['model-settings', 'tiers'] });
    }
  }, [downloadProgress, queryClient]);

  const handleDetectHardware = () => {
    detectHardware.mutate();
  };

  const handleSetTier = (tier: string) => {
    setTier.mutate(tier);
  };

  const handleStartDownload = (tier: string) => {
    setDownloadInitiated(true);
    startDownload.mutate(tier);
  };

  const externalEnabled = externalApiData?.use_external_api ?? false;

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:items-start">
        <div className="lg:col-span-2 space-y-6">
          {/* Model Tier Selection */}
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
                      'flex flex-col gap-3 px-4 py-4 rounded-xl border sm:flex-row sm:items-center sm:justify-between',
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
                          // T0: while a download runs the button is disabled, and disabled would fade it to half opacity.
                          // It turns grey instead, so the text a patient reads does not change opacity.
                          className="gap-1.5 h-8 border-black/6 text-xs font-bold disabled:opacity-100 disabled:text-ink-tertiary"
                          onClick={() => handleStartDownload(tier.tier)}
                          disabled={isDownloading}
                          data-t0=""
                        >
                          {isDownloading ? (
                            <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                          ) : (
                            <Download className="w-3 h-3" />
                          )}
                          Download
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

          {/* Hardware Info */}
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
                  className="gap-1.5 border-black/6"
                  onClick={handleDetectHardware}
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

          {/* Document import / OCR */}
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

          {/* Environment & tools */}
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
                  className="gap-1.5 border-black/6"
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
                      <p className="text-sm font-medium text-ink truncate">{c.label}</p>
                      <p className="text-xs text-ink-tertiary truncate">{c.detail}</p>
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
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Current Status */}
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

          {/* RL Training Data */}
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
        </div>
      </div>

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
                  setExportResult({
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
