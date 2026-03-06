/**
 * SettingsPage - Model configuration and external API settings
 *
 * Phase 4B: Hardware detection, tier selection, model download, external API opt-in.
 */

import { useState } from 'react';
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
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { MemoryManager } from '@/components/MemoryManager';
import { cn } from '@/utils/cn';
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
} from '@/services';

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

  const [downloadInitiated, setDownloadInitiated] = useState(false);
  const { data: downloadProgress } = useDownloadProgress(downloadInitiated);

  // Derive active download status from progress data
  const hasActiveDownload = downloadInitiated && Object.values(downloadProgress || {}).some(
    (p) => p.status === 'pending' || p.status === 'downloading'
  );
  const isDownloading = hasActiveDownload || startDownload.isPending;

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
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
        <span className="ml-3 text-ink-secondary">Loading settings...</span>
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
          Configure AI model and hardware preferences
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
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
                className="w-full px-3 py-2 rounded-xl bg-surface-muted text-sm text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent"
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
                  'w-full flex items-center justify-between px-3 py-3 rounded-xl',
                  'transition-colors duration-200',
                  voiceData?.voice_logging_enabled
                    ? 'bg-accent-subtle'
                    : 'bg-surface-muted hover:bg-surface-sunken'
                )}
              >
                <span className={cn(
                  'text-sm font-medium',
                  voiceData?.voice_logging_enabled ? 'text-accent' : 'text-ink-secondary'
                )}>
                  Enable Voice Logging
                </span>
                <div className={cn(
                  'w-10 h-6 rounded-full relative transition-colors',
                  voiceData?.voice_logging_enabled ? 'bg-accent' : 'bg-black/[0.12]'
                )}>
                  <div className={cn(
                    'absolute w-4 h-4 rounded-full bg-white top-1 transition-transform',
                    voiceData?.voice_logging_enabled ? 'translate-x-5' : 'translate-x-1'
                  )} />
                </div>
              </button>
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
                  className="gap-1.5"
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
                  <div className="rounded-xl bg-surface-muted p-4">
                    <p className="text-xs text-ink-tertiary mb-1">RAM</p>
                    <p className="text-sm font-medium text-ink">{settings.hardware_info.ram_total_gb.toFixed(1)} GB</p>
                  </div>
                  <div className="rounded-xl bg-surface-muted p-4">
                    <p className="text-xs text-ink-tertiary mb-1">CPU</p>
                    <p className="text-sm font-medium text-ink">{settings.hardware_info.cpu_cores} cores</p>
                    <p className="text-xs text-ink-tertiary truncate">{settings.hardware_info.cpu_name || 'Unknown'}</p>
                  </div>
                  <div className="rounded-xl bg-surface-muted p-4">
                    <p className="text-xs text-ink-tertiary mb-1">Disk Free</p>
                    <p className="text-sm font-medium text-ink">{settings.hardware_info.disk_free_gb.toFixed(1)} GB</p>
                  </div>
                  <div className="rounded-xl bg-surface-muted p-4">
                    <p className="text-xs text-ink-tertiary mb-1">GPU</p>
                    <p className="text-sm font-medium text-ink">
                      {settings.hardware_info.gpu_name || 'Not detected'}
                    </p>
                    {settings.hardware_info.gpu_vram_gb && (
                      <p className="text-xs text-ink-tertiary">{settings.hardware_info.gpu_vram_gb} GB VRAM</p>
                    )}
                  </div>
                  <div className="col-span-2 rounded-xl bg-accent-subtle p-4">
                    <p className="text-xs text-accent mb-1">Recommended Tier</p>
                    <p className="text-sm font-semibold text-accent capitalize">
                      {settings.hardware_info.recommended_tier}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Cpu className="w-10 h-10 text-ink-tertiary mx-auto mb-3" />
                  <p className="text-sm text-ink-secondary">
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
                    className={cn(
                      'flex items-center justify-between px-4 py-4 rounded-xl border transition-colors',
                      isSelected
                        ? 'border-accent bg-accent-subtle'
                        : 'border-black/[0.06] hover:border-black/[0.12]'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <TierIcon className={cn('w-5 h-5', isSelected ? 'text-accent' : 'text-ink-secondary')} />
                      <div>
                        <div className="flex items-center gap-2">
                          <p className={cn('text-sm font-medium', isSelected ? 'text-accent' : 'text-ink')}>
                            {desc?.label || tier.tier}
                          </p>
                          {isRecommended && (
                            <Badge variant="default" className="text-[10px]">Recommended</Badge>
                          )}
                        </div>
                        <p className="text-xs text-ink-tertiary">{desc?.desc || tier.description}</p>
                        <p className="text-xs text-ink-tertiary mt-0.5">{tier.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {tier.downloaded ? (
                        <Badge variant="verified" className="gap-1">
                          <Check className="w-3 h-3" />
                          Ready
                        </Badge>
                      ) : tier.can_run ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          className="gap-1.5"
                          onClick={() => handleStartDownload(tier.tier)}
                          disabled={isDownloading}
                        >
                          {isDownloading ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Download className="w-3.5 h-3.5" />
                          )}
                          Download
                        </Button>
                      ) : (
                        <Badge variant="default">Incompatible</Badge>
                      )}
                      {!isSelected && (tier.downloaded || tier.can_run) && (
                        <Button
                          variant={isSelected ? 'primary' : 'ghost'}
                          size="sm"
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
                <div className="text-center py-8">
                  <p className="text-sm text-ink-secondary">
                    Run hardware detection first to see available tiers.
                  </p>
                </div>
              )}

              {/* Download Progress */}
              {downloadProgress && Object.entries(downloadProgress).map(([tier, progress]) => {
                if (progress.status !== 'downloading') return null;
                return (
                  <div key={tier} className="rounded-xl bg-surface-muted p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-ink capitalize">Downloading {tier}...</p>
                      <p className="text-xs text-ink-secondary">{Math.round(progress.progress)}%</p>
                    </div>
                    <div className="w-full bg-black/[0.06] rounded-full h-2">
                      <div
                        className="bg-accent rounded-full h-2 transition-all duration-300"
                        style={{ width: `${Math.round(progress.progress)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Current Status */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Current Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                <span className="text-sm text-ink-secondary">Active Tier</span>
                <Badge variant="verified" className="capitalize">
                  {settings?.current_tier || 'none'}
                </Badge>
              </div>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                <span className="text-sm text-ink-secondary">Preferred</span>
                <span className="text-sm font-medium text-ink capitalize">
                  {settings?.preferred_tier || 'auto'}
                </span>
              </div>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                <span className="text-sm text-ink-secondary">External API</span>
                <Badge variant={externalEnabled ? 'verified' : 'default'}>
                  {externalEnabled ? 'Enabled' : 'Off'}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* External API Section */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Shield className="w-4 h-4" />
                External API
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-ink-tertiary">
                Optionally use an external AI provider for higher quality responses.
                Your data will be sent to the provider's servers.
              </p>

              <button
                onClick={handleExternalApiToggle}
                className={cn(
                  'w-full flex items-center justify-between px-3 py-3 rounded-xl',
                  'transition-colors duration-200',
                  externalEnabled
                    ? 'bg-accent-subtle'
                    : 'bg-surface-muted hover:bg-surface-sunken'
                )}
              >
                <span className={cn(
                  'text-sm font-medium',
                  externalEnabled ? 'text-accent' : 'text-ink-secondary'
                )}>
                  Use External API
                </span>
                <div className={cn(
                  'w-10 h-6 rounded-full relative transition-colors',
                  externalEnabled ? 'bg-accent' : 'bg-black/[0.12]'
                )}>
                  <div className={cn(
                    'absolute w-4 h-4 rounded-full bg-white top-1 transition-transform',
                    externalEnabled ? 'translate-x-5' : 'translate-x-1'
                  )} />
                </div>
              </button>

              {externalEnabled && (
                <div className="space-y-2 pt-2">
                  <div>
                    <label className="text-xs text-ink-secondary block mb-1">Provider</label>
                    <select
                      value={externalProvider}
                      onChange={(e) => setExternalProvider(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-surface-muted text-sm text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent"
                    >
                      <option value="">Select provider</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-ink-secondary block mb-1">API Key</label>
                    <input
                      type="password"
                      value={externalKey}
                      onChange={(e) => setExternalKey(e.target.value)}
                      placeholder="sk-..."
                      className="w-full px-3 py-2 rounded-xl bg-surface-muted text-sm text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-ink-secondary block mb-1">Model</label>
                    <input
                      type="text"
                      value={externalModel}
                      onChange={(e) => setExternalModel(e.target.value)}
                      placeholder="e.g. gpt-4o, claude-sonnet-4-5-20250929"
                      className="w-full px-3 py-2 rounded-xl bg-surface-muted text-sm text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent"
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="text-xs text-ink-tertiary text-center px-4">
            All model inference runs locally by default. No data leaves your device unless
            you explicitly enable an external API.
          </div>
        </div>
      </div>

      {/* Assistant Memory */}
      <MemoryManager />

      {/* Consent Dialog */}
      {showConsentDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-status-attention/10 flex items-center justify-center">
                <Shield className="w-5 h-5 text-status-attention" />
              </div>
              <h2 className="text-lg font-display font-semibold text-ink">
                Privacy Notice
              </h2>
            </div>
            <p className="text-sm text-ink-secondary mb-2">
              Enabling an external API means your health data will be sent to a
              third-party server for processing. This includes:
            </p>
            <ul className="text-sm text-ink-secondary space-y-1 mb-4 list-disc pl-5">
              <li>Lab results and observations referenced in your questions</li>
              <li>Your conversation messages and context</li>
              <li>Analyte names and values for interpretation</li>
            </ul>
            <p className="text-sm text-ink-secondary mb-6">
              Your data will be processed according to the provider's privacy policy.
              You can disable this at any time to return to local-only processing.
            </p>
            <div className="flex items-center gap-3 justify-end">
              <Button
                variant="secondary"
                onClick={() => setShowConsentDialog(false)}
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
              >
                I Understand, Enable
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
