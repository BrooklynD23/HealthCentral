/**
 * Assistant & privacy section (UI-PG-SETTINGS): the step-by-step assistant, its memory, the external API with
 * the break-glass warning, and data donation.
 *
 * D12 (owner, 2026-09-27): the external API consent and the break-glass warning keep their text, their roles and
 * their behaviour. The consent is an AlertDialog and `still` (M0): nothing on it fades, scales or slides. The warning
 * is rendered outside every motion element and every AnimatePresence.
 */

import { useEffect, useRef, useState } from 'react';
import { Shield } from 'lucide-react';
import { m, AnimatePresence } from 'framer-motion';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { AlertDialog } from '@/components/ui/AlertDialog';
import { MemoryManager } from '@/components/MemoryManager';
import { DataDonationCard } from '@/components/settings/DataDonationCard';
import { AgentSettingsCard } from '@/components/settings/AgentSettingsCard';
import { ExternalApiBreakGlassWarning } from '@/components/settings/ExternalApiBreakGlassWarning';
import { useExternalApiSettings, useSaveExternalApiSettings } from '@/services';
import { SwitchRow } from './PreferencesSection';

const CONSENT_ITEMS = [
  'Lab results and observations referenced in your questions',
  'Your conversation messages and context',
  'Analyte names and values for interpretation',
];

export function AssistantPrivacySection() {
  const [showConsentDialog, setShowConsentDialog] = useState(false);
  const [externalProvider, setExternalProvider] = useState('');
  const [externalKey, setExternalKey] = useState('');
  const [externalModel, setExternalModel] = useState('');
  const { data: externalApiData, isError: externalApiError } = useExternalApiSettings();
  const saveExternalApi = useSaveExternalApiSettings();

  const externalEnabled = externalApiData?.use_external_api ?? false;

  // The consent dialog has no Trigger, so Radix has nothing to return focus to: the switch gets it back once the dialog
  // has closed (Escape, Cancel or Enable). Not in the close handler: the dialog's focus trap is still on there.
  const switchRef = useRef<HTMLButtonElement>(null);
  const consentWasOpen = useRef(false);
  useEffect(() => {
    if (consentWasOpen.current && !showConsentDialog) switchRef.current?.focus();
    consentWasOpen.current = showConsentDialog;
  }, [showConsentDialog]);

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

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:items-start">
      <div className="space-y-6">
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

            <ExternalApiBreakGlassWarning
              active={externalApiData?.redaction_break_glass}
              unknown={
                externalApiError ||
                (externalApiData?.use_external_api === true &&
                  externalApiData.redaction_break_glass === undefined)
              }
            />

            <SwitchRow label="Use External API" checked={externalEnabled} onCheckedChange={handleExternalApiToggle} switchRef={switchRef} />

            <AnimatePresence>
              {externalEnabled && (
                <m.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-3 pt-2 overflow-hidden"
                >
                  <div>
                    <label htmlFor="external-provider-select" className="text-xs font-bold uppercase tracking-wider text-ink-tertiary block mb-1.5 ml-1">Provider</label>
                    <select
                      id="external-provider-select"
                      value={externalProvider}
                      onChange={(e) => setExternalProvider(e.target.value)}
                      className="w-full px-3 py-2.5 h-11 rounded-xl bg-surface-elevated text-sm text-ink border border-black/8 focus:outline-hidden focus:ring-2 focus:ring-accent transition-all"
                    >
                      <option value="">Select provider</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-ink-tertiary block mb-1.5 ml-1">API Key</label>
                    <input
                      type="password"
                      value={externalKey}
                      onChange={(e) => setExternalKey(e.target.value)}
                      placeholder="sk-..."
                      className="w-full px-3 py-2.5 h-11 rounded-xl bg-surface-elevated text-sm text-ink border border-black/8 focus:outline-hidden focus:ring-2 focus:ring-accent transition-all"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-ink-tertiary block mb-1.5 ml-1">Model</label>
                    <input
                      type="text"
                      value={externalModel}
                      onChange={(e) => setExternalModel(e.target.value)}
                      placeholder="e.g. gpt-4o, claude-sonnet"
                      className="w-full px-3 py-2.5 h-11 rounded-xl bg-surface-elevated text-sm text-ink border border-black/8 focus:outline-hidden focus:ring-2 focus:ring-accent transition-all"
                    />
                  </div>
                </m.div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>

        <div className="text-xs text-ink-tertiary text-center px-4 leading-relaxed font-medium">
          All model inference runs locally by default. No data leaves your device unless
          you explicitly enable an external API.
        </div>

        {/* Step-by-step assistant switch (AGENT-ENABLED-TOGGLE) */}
        <AgentSettingsCard />
      </div>

      <div className="space-y-6">
        {/* Opt-in data donation consent (RSI1-DONATE) */}
        <DataDonationCard />

        {/* Assistant Memory */}
        <MemoryManager />
      </div>

      {/* Consent dialog: still (M0), Escape closes it, focus returns to the switch. */}
      <AlertDialog
        open={showConsentDialog}
        onOpenChange={setShowConsentDialog}
        still
        title="Privacy Notice"
        description="External API Processing"
      >
        <div data-t0="" className="space-y-4">
          <p className="text-sm text-ink-secondary leading-relaxed">
            Enabling an external API means your health data will be sent to a
            third-party server for processing. This includes:
          </p>
          <ul className="text-sm text-ink-secondary space-y-2 list-none">
            {CONSENT_ITEMS.map((item) => (
              <li key={item} className="flex items-start gap-2">
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
            data-alert-cancel=""
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
      </AlertDialog>
    </div>
  );
}
