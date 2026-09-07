/**
 * SettingsPage - Model configuration and external API settings
 *
 * Phase 4B: Hardware detection, tier selection, model download, external API opt-in.
 */

import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  HardDrive,
  Download,
  Check,
  AlertCircle,
  Loader2,
  Shield,
  Zap,
  Server,
  Mic,
  Clock,
  FileText,
  Wrench,
  Copy,
  Settings as SettingsIcon,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, Skeleton, StaggerGroup, StaggerItem, modalVariants, backdropVariants } from '@/components/ui';
import { motion, AnimatePresence } from 'framer-motion';
import { MemoryManager } from '@/components/MemoryManager';
import { BackupCard } from '@/components/settings/BackupCard';
import { DangerZone } from '@/components/settings/DangerZone';
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
  useSaveExternalApiSettings,
  useTimezone,
  useSaveTimezone,
  useVoiceSettings,
  useSaveVoiceSettings,
  useSaveOcrPreference,
  useEnvironmentDiagnostics,
  useRecheckDiagnostics,
} from '@/services';
import { useFeedbackStats, useExportDataset } from '@/services/feedback';
import { Database, Download as DownloadIcon } from 'lucide-react';

const OCR_BLOCKER_LABELS: Record<string, string> = {
  disabled_by_admin: 'OCR is disabled in server configuration (OCR_ENABLED). Restart the backend after changing .env.',
  tesseract_missing: 'Install Tesseract OCR and add it to PATH.',
  user_disabled: 'Turn on document OCR below for this profile.',
};

const COMMON_TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Anchorage',
  'Pacific/Honolulu',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Kolkata',
  'Australia/Sydney',
];

const tierDescriptions: Record<string, { label: string; desc: string; icon: typeof Zap }> = {
  low: { label: 'Low (Qwen2.5 0.5B)', desc: 'Fast, lightweight — works on most hardware', icon: Zap },
  mid: { label: 'Mid (Phi-3 Mini)', desc: 'Balanced speed and quality', icon: Server },
  high: { label: 'High (BioMistral 7B)', desc: 'Best quality — needs 8GB+ RAM', icon: Cpu },
};

export function SettingsPage() {
  const [showConsentDialog, setShowConsentDialog] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportResult, setExportResult] = useState<{ dpo: number; sft: number; grpo: number; path: string } | null>(null);
  const [diagToolId, setDiagToolId] = useState<string | null>(null);
  const [externalProvider, setExternalProvider] = useState('');
  const [externalKey, setExternalKey] = useState('');
  const [externalModel, setExternalModel] = useState('');

  // API hooks
  const { data: settings, isLoading, isError } = useModelSettings();
  const { data: tiersData } = useTiers();
  const detectHardware = useDetectHardware();
  const setTier = useSetTier();
  const startDownload = useStartDownload();
  const { data: externalApiData } = useExternalApiSettings();
  const saveExternalApi = useSaveExternalApiSettings();

  const { data: timezoneData } = useTimezone();
  const saveTimezone = useSaveTimezone();
  const { data: voiceData } = useVoiceSettings();
  const saveVoice = useSaveVoiceSettings();
  const saveOcr = useSaveOcrPreference();
  const { data: diagnostics, isLoading: diagnosticsLoading } = useEnvironmentDiagnostics();
  const { data: feedbackStats } = useFeedbackStats();
  const exportDataset = useExportDataset();
  const recheckDiagnostics = useRecheckDiagnostics();

  const focusedDiag = diagnostics?.components.find((c) => c.id === diagToolId) ?? null;
  const queryClient = useQueryClient();
  const prefersReducedMotion = useReducedMotion();
  const [downloadInitiated, setDownloadInitiated] = useState(false);
  const { data: downloadProgress } = useDownloadProgress(downloadInitiated);

  // Derive active download status from progress data
  const hasActiveDownload = downloadInitiated && Object.values(downloadProgress || {}).some(
    (p) => p.status === 'pending' || p.status === 'downloading'
  );
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

  const handleExternalApiToggle = () => {
    if (!externalEnabled) {
      setShowConsentDialog(true);
    } else {
      saveExternalApi.mutate({
        use_external_api: false,
        provider: externalProvider,
        api_key: '',
        consent_acknowledged: true,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
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
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
          Settings
        </h1>
        <p className="text-ink-secondary mt-1">
          Configure AI models, document import (OCR), and hardware.
        </p>
      </div>

      <StaggerGroup className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <StaggerItem className="lg:col-span-2 space-y-6">
          {/* Timezone */}
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-ink-secondary" />
                Timezone
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <p className="text-sm text-ink-secondary mb-3">
                Used for streak and badge calculations.
              </p>
              <select
                value={timezoneData?.timezone ?? 'UTC'}
                onChange={(e) => saveTimezone.mutate(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-surface-muted text-sm text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent transition-all"
              >
                {COMMON_TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </CardContent>
          </Card>

          {/* Voice Logging */}
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-3">
                <Mic className="w-5 h-5 text-ink-secondary" />
                Voice Logging
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <p className="text-sm text-ink-secondary mb-3">
                Use your microphone to log doses by voice. Speech is processed locally by your browser.
              </p>
              <button
                onClick={() => {
                  saveVoice.mutate({
                    voice_logging_enabled: !voiceData?.voice_logging_enabled,
                  });
                }}
                className={cn(
                  'w-full flex items-center justify-between px-4 py-3 rounded-xl',
                  'transition-all duration-300 ease-in-out',
                  voiceData?.voice_logging_enabled
                    ? 'bg-accent-subtle border border-accent/20'
                    : 'bg-surface-muted border border-transparent hover:bg-surface-sunken'
                )}
              >
                <span className={cn(
                  'text-sm font-medium',
                  voiceData?.voice_logging_enabled ? 'text-accent' : 'text-ink-secondary'
                )}>
                  Enable Voice Logging
                </span>
                <div className={cn(
                  'w-10 h-6 rounded-full relative transition-colors duration-300',
                  voiceData?.voice_logging_enabled ? 'bg-accent' : 'bg-black/[0.12]'
                )}>
                  <div className={cn(
                    'absolute w-4 h-4 rounded-full bg-white top-1 transition-transform duration-300',
                    voiceData?.voice_logging_enabled ? 'translate-x-5' : 'translate-x-1'
                  )} />
                </div>
              </button>
            </CardContent>
          </Card>

          {/* Document import / OCR */}
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-ink-secondary" />
                Document import (OCR)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-3">
              <p className="text-sm text-ink-secondary">
                Extract text from scanned PDFs and lab images using Tesseract. Your preference applies to this profile;
                the server must also allow OCR (<code className="text-xs bg-surface-muted px-1 rounded">OCR_ENABLED</code>).
              </p>
              <button
                type="button"
                onClick={() => {
                  saveOcr.mutate(!settings?.ocr_preference_enabled);
                }}
                disabled={saveOcr.isPending}
                className={cn(
                  'w-full flex items-center justify-between px-4 py-3 rounded-xl',
                  'transition-all duration-300 ease-in-out',
                  settings?.ocr_preference_enabled
                    ? 'bg-accent-subtle border border-accent/20'
                    : 'bg-surface-muted border border-transparent hover:bg-surface-sunken'
                )}
              >
                <span
                  className={cn(
                    'text-sm font-medium',
                    settings?.ocr_preference_enabled ? 'text-accent' : 'text-ink-secondary'
                  )}
                >
                  Enable OCR for scans &amp; images
                </span>
                <div
                  className={cn(
                    'w-10 h-6 rounded-full relative transition-colors duration-300',
                    settings?.ocr_preference_enabled ? 'bg-accent' : 'bg-black/[0.12]'
                  )}
                >
                  <div
                    className={cn(
                      'absolute w-4 h-4 rounded-full bg-white top-1 transition-transform duration-300',
                      settings?.ocr_preference_enabled ? 'translate-x-5' : 'translate-x-1'
                    )}
                  />
                </div>
              </button>
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
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <Wrench className="w-5 h-5 text-ink-secondary" />
                  Environment &amp; tools
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  className="gap-1.5 border-black/[0.06]"
                  onClick={() => recheckDiagnostics.mutate()}
                  disabled={recheckDiagnostics.isPending || diagnosticsLoading}
                >
                  {recheckDiagnostics.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
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
                    className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl bg-surface-muted border border-black/[0.04]"
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

          {/* Hardware Info */}
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Cpu className="w-5 h-5 text-ink-secondary" />
                  Hardware Detection
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  className="gap-1.5 border-black/[0.06]"
                  onClick={handleDetectHardware}
                  disabled={detectHardware.isPending}
                >
                  {detectHardware.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
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
                  <div className="rounded-xl bg-surface-muted p-4 border border-black/[0.02]">
                    <p className="text-xs text-ink-tertiary mb-1 font-medium uppercase tracking-wider">RAM</p>
                    <p className="text-sm font-bold text-ink">{settings.hardware_info.ram_total_gb.toFixed(1)} GB</p>
                  </div>
                  <div className="rounded-xl bg-surface-muted p-4 border border-black/[0.02]">
                    <p className="text-xs text-ink-tertiary mb-1 font-medium uppercase tracking-wider">CPU</p>
                    <p className="text-sm font-bold text-ink">{settings.hardware_info.cpu_cores} cores</p>
                    <p className="text-[10px] text-ink-tertiary truncate font-medium">{settings.hardware_info.cpu_name || 'Unknown'}</p>
                  </div>
                  <div className="rounded-xl bg-surface-muted p-4 border border-black/[0.02]">
                    <p className="text-xs text-ink-tertiary mb-1 font-medium uppercase tracking-wider">Disk Free</p>
                    <p className="text-sm font-bold text-ink">{settings.hardware_info.disk_free_gb.toFixed(1)} GB</p>
                  </div>
                  <div className="rounded-xl bg-surface-muted p-4 border border-black/[0.02]">
                    <p className="text-xs text-ink-tertiary mb-1 font-medium uppercase tracking-wider">GPU</p>
                    <p className="text-sm font-bold text-ink">
                      {settings.hardware_info.gpu_name || 'Not detected'}
                    </p>
                    {settings.hardware_info.gpu_vram_gb && (
                      <p className="text-[10px] text-ink-tertiary font-medium">{settings.hardware_info.gpu_vram_gb} GB VRAM</p>
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
                <div className="text-center py-12 border-2 border-dashed border-black/[0.04] rounded-2xl">
                  <Cpu className="w-10 h-10 text-ink-tertiary mx-auto mb-3 opacity-50" />
                  <p className="text-sm text-ink-secondary max-w-[240px] mx-auto">
                    Run hardware detection to see recommended model settings.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Model Tier Selection */}
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
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
                      'flex items-center justify-between px-4 py-4 rounded-xl border transition-all duration-300',
                      isSelected
                        ? 'border-accent bg-accent-subtle shadow-sm'
                        : 'border-black/[0.06] hover:border-black/[0.12] hover:bg-black/[0.01]'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn('p-2 rounded-lg', isSelected ? 'bg-accent/10' : 'bg-surface-muted')}>
                        <TierIcon className={cn('w-5 h-5', isSelected ? 'text-accent' : 'text-ink-secondary')} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className={cn('text-sm font-bold', isSelected ? 'text-accent' : 'text-ink')}>
                            {desc?.label || tier.tier}
                          </p>
                          {isRecommended && (
                            <Badge variant="accent" className="text-[9px] uppercase tracking-wider font-bold">Recommended</Badge>
                          )}
                        </div>
                        <p className="text-xs text-ink-secondary mt-0.5">{desc?.desc || tier.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {tier.downloaded ? (
                        <Badge variant="verified" className="gap-1 font-bold">
                          <Check className="w-3 h-3" />
                          Ready
                        </Badge>
                      ) : tier.can_run ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          className="gap-1.5 h-8 border-black/[0.06] text-xs font-bold"
                          onClick={() => handleStartDownload(tier.tier)}
                          disabled={isDownloading}
                        >
                          {isDownloading ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Download className="w-3 h-3" />
                          )}
                          Download
                        </Button>
                      ) : (
                        <Badge variant="default" className="opacity-50">Incompatible</Badge>
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
                <div className="text-center py-12 border-2 border-dashed border-black/[0.04] rounded-2xl">
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
                    <motion.div
                      key={progressTier}
                      initial={{ opacity: 0, height: 0, marginTop: 0 }}
                      animate={{ opacity: 1, height: 'auto', marginTop: 12 }}
                      exit={{ opacity: 0, height: 0, marginTop: 0 }}
                      className="rounded-xl bg-surface-muted p-4 border border-black/[0.04] overflow-hidden"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-bold text-ink capitalize flex items-center gap-2">
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" />
                          Downloading {progressTier}…
                        </p>
                        <p className="text-xs font-bold text-accent">{label}</p>
                      </div>
                      <div className="w-full bg-black/[0.06] rounded-full h-2 overflow-hidden">
                        {isIndeterminate ? (
                          <div className="h-2 w-1/3 bg-accent rounded-full animate-shimmer" />
                        ) : (
                          <motion.div
                            className="bg-accent rounded-full h-2"
                            initial={{ width: 0 }}
                            animate={{ width: `${pct}%` }}
                            transition={{ duration: 0.5 }}
                          />
                        )}
                      </div>
                      {progress.total_bytes > 0 && (
                        <p className="text-[10px] text-ink-tertiary mt-2 font-medium">
                          {(progress.downloaded_bytes / 1_073_741_824).toFixed(2)} GB / {(progress.total_bytes / 1_073_741_824).toFixed(2)} GB
                        </p>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </CardContent>
          </Card>
        </StaggerItem>

        {/* Sidebar */}
        <StaggerItem className="space-y-4">
          {/* Current Status */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Current Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted border border-black/[0.02]">
                <span className="text-sm text-ink-secondary">Active Tier</span>
                <Badge variant="verified" className="capitalize font-bold">
                  {settings?.current_tier || 'none'}
                </Badge>
              </div>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted border border-black/[0.02]">
                <span className="text-sm text-ink-secondary">Preferred</span>
                <span className="text-sm font-bold text-ink capitalize">
                  {settings?.preferred_tier || 'auto'}
                </span>
              </div>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted border border-black/[0.02]">
                <span className="text-sm text-ink-secondary">External API</span>
                <Badge variant={externalEnabled ? 'verified' : 'default'} className="font-bold">
                  {externalEnabled ? 'Enabled' : 'Off'}
                </Badge>
              </div>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted border border-black/[0.02]">
                <span className="text-sm text-ink-secondary">OCR (profile)</span>
                <Badge variant={settings?.ocr_effective ? 'verified' : 'attention'} className="font-bold">
                  {settings?.ocr_effective ? 'Ready' : 'Blocked'}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* External API Section */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Shield className="w-4 h-4 text-ink-secondary" />
                External API
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-ink-tertiary leading-relaxed">
                Optionally use an external AI provider for higher quality responses.
                Your data will be sent to the provider's servers.
              </p>

              <button
                onClick={handleExternalApiToggle}
                className={cn(
                  'w-full flex items-center justify-between px-4 py-3 rounded-xl',
                  'transition-all duration-300 ease-in-out',
                  externalEnabled
                    ? 'bg-accent-subtle border border-accent/20'
                    : 'bg-surface-muted border border-transparent hover:bg-surface-sunken'
                )}
              >
                <span className={cn(
                  'text-sm font-medium',
                  externalEnabled ? 'text-accent' : 'text-ink-secondary'
                )}>
                  Use External API
                </span>
                <div className={cn(
                  'w-10 h-6 rounded-full relative transition-colors duration-300',
                  externalEnabled ? 'bg-accent' : 'bg-black/[0.12]'
                )}>
                  <div className={cn(
                    'absolute w-4 h-4 rounded-full bg-white top-1 transition-transform duration-300',
                    externalEnabled ? 'translate-x-5' : 'translate-x-1'
                  )} />
                </div>
              </button>

              <AnimatePresence>
                {externalEnabled && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-3 pt-2 overflow-hidden"
                  >
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-ink-tertiary block mb-1.5 ml-1">Provider</label>
                      <select
                        value={externalProvider}
                        onChange={(e) => setExternalProvider(e.target.value)}
                        className="w-full px-3 py-2.5 h-11 rounded-xl bg-surface-elevated text-sm text-ink border border-black/[0.08] focus:outline-none focus:ring-2 focus:ring-accent transition-all"
                      >
                        <option value="">Select provider</option>
                        <option value="openai">OpenAI</option>
                        <option value="anthropic">Anthropic</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-ink-tertiary block mb-1.5 ml-1">API Key</label>
                      <input
                        type="password"
                        value={externalKey}
                        onChange={(e) => setExternalKey(e.target.value)}
                        placeholder="sk-..."
                        className="w-full px-3 py-2.5 h-11 rounded-xl bg-surface-elevated text-sm text-ink border border-black/[0.08] focus:outline-none focus:ring-2 focus:ring-accent transition-all"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-ink-tertiary block mb-1.5 ml-1">Model</label>
                      <input
                        type="text"
                        value={externalModel}
                        onChange={(e) => setExternalModel(e.target.value)}
                        placeholder="e.g. gpt-4o, claude-sonnet"
                        className="w-full px-3 py-2.5 h-11 rounded-xl bg-surface-elevated text-sm text-ink border border-black/[0.08] focus:outline-none focus:ring-2 focus:ring-accent transition-all"
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </CardContent>
          </Card>

          <div className="text-[10px] text-ink-tertiary text-center px-4 leading-relaxed font-medium">
            All model inference runs locally by default. No data leaves your device unless
            you explicitly enable an external API.
          </div>
        </StaggerItem>
      </StaggerGroup>

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

      {/* Export confirmation dialog */}
      <AnimatePresence>
        {showExportDialog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial="initial" animate="animate" exit="exit"
              variants={backdropVariants}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
              onClick={() => setShowExportDialog(false)}
            />
            <motion.div
              initial="initial" animate="animate" exit="exit"
              variants={modalVariants}
              className="relative bg-surface rounded-2xl shadow-2xl p-6 max-w-md w-full z-10 space-y-4"
            >
              <h3 className="text-lg font-semibold text-ink">Export training data?</h3>
              <p className="text-sm text-ink-secondary">
                This will write JSONL files (DPO pairs, SFT positives, GRPO rewards) to your local
                filesystem. Redaction is applied to all prompt and response text before writing.
              </p>
              <p className="text-xs text-ink-tertiary">
                Files are stored locally only and never uploaded. No network calls are made.
              </p>
              <div className="flex gap-3 justify-end">
                <Button variant="ghost" onClick={() => setShowExportDialog(false)}>
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
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Assistant Memory */}
      <MemoryManager />

      {/* Backup & restore (BKUP-UX-001) — sits directly above the danger
          zone, since taking a backup is the step before deleting anything. */}
      <BackupCard />

      {/* Irreversible profile deletion (PROF-DEL-001) */}
      <DangerZone />

      {/* Diagnostics fix actions */}
      <AnimatePresence>
        {focusedDiag && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial="initial"
              animate="animate"
              exit="exit"
              variants={backdropVariants}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
              onClick={() => setDiagToolId(null)}
              aria-hidden
            />
            <motion.div
              initial="initial"
              animate="animate"
              exit="exit"
              variants={modalVariants}
              transition={{ type: prefersReducedMotion ? 'tween' : 'spring', duration: prefersReducedMotion ? 0.15 : undefined }}
              className="relative w-full max-w-md rounded-2xl bg-surface-elevated border border-black/[0.08] shadow-xl p-6 max-h-[85vh] overflow-y-auto"
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
                      className="rounded-xl border border-black/[0.06] p-3 bg-surface-muted"
                    >
                      <p className="text-xs font-bold text-ink-tertiary uppercase tracking-wide">{a.label}</p>
                      {a.type === 'copy_command' && a.command && (
                        <div className="mt-2 flex items-start gap-2">
                          <code className="text-[11px] flex-1 break-all bg-surface-elevated rounded-lg px-2 py-1.5 border border-black/[0.06]">
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
                              to={a.url}
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
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Consent Dialog */}
      <AnimatePresence>
        {showConsentDialog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial="initial"
              animate="animate"
              exit="exit"
              variants={backdropVariants}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
              onClick={() => setShowConsentDialog(false)}
              aria-hidden
            />
            <motion.div
              initial="initial"
              animate="animate"
              exit="exit"
              variants={prefersReducedMotion ? backdropVariants : modalVariants}
              className="relative z-10 w-full max-w-md"
            >
              <Card className="shadow-elevated border-black/[0.08] overflow-hidden">
                <div className="p-6">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-12 h-12 rounded-2xl bg-status-critical-subtle flex items-center justify-center border border-status-critical/10">
                      <Shield className="w-6 h-6 text-status-critical" />
                    </div>
                    <div>
                      <h2 className="text-xl font-display font-bold text-ink">
                        Privacy Notice
                      </h2>
                      <p className="text-xs text-ink-tertiary font-medium">External API Processing</p>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <p className="text-sm text-ink-secondary leading-relaxed">
                      Enabling an external API means your health data will be sent to a
                      third-party server for processing. This includes:
                    </p>
                    <ul className="text-sm text-ink-secondary space-y-2 list-none">
                      {[
                        'Lab results and observations referenced in your questions',
                        'Your conversation messages and context',
                        'Analyte names and values for interpretation'
                      ].map((item, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                    <p className="text-sm text-ink-secondary leading-relaxed pt-2">
                      Your data will be processed according to the provider's privacy policy.
                      You can disable this at any time to return to local-only processing.
                    </p>
                  </div>
                  <div className="flex items-center gap-3 justify-end mt-8">
                    <Button
                      variant="ghost"
                      onClick={() => setShowConsentDialog(false)}
                      className="font-bold"
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={() => {
                        setShowConsentDialog(false);
                        saveExternalApi.mutate({
                          use_external_api: true,
                          provider: externalProvider,
                          api_key: externalKey,
                          model: externalModel,
                          consent_acknowledged: true,
                        });
                      }}
                      className="font-bold"
                    >
                      I Understand, Enable
                    </Button>
                  </div>
                </div>
              </Card>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
