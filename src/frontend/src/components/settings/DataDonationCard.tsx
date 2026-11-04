/**
 * Data donation consent (RSI1-DONATE PR-1).
 *
 * One switch per purpose, all off by default. Turning a purpose off deletes the
 * donated copies, so it always goes through an explicit confirmation.
 *
 * DRAFT COPY: the wording below needs owner approval (DON-COPY) before merge.
 * Bump CONSENT_TEXT_VERSION whenever the wording changes.
 */

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/utils/cn';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { AlertDialog } from '@/components/ui/AlertDialog';
import { Switch } from '@/components/ui/Switch';
import {
  DONATION_PURPOSES,
  useDonationConsents,
  useSetDonationConsent,
  type DonationPurpose,
} from '@/services/donation';

export const CONSENT_TEXT_VERSION = '2026-10-27-v3';

// The audit write can fail after the change is saved, so never claim it failed.
const NEUTRAL_ERROR = 'Could not confirm your choice. Reload to see what was saved.';

export const CONSENT_INTRO = [
  'Donating is optional and off by default. You choose each purpose separately, and you can change your mind at any time.',
  'Your data never leaves this device. Before anything is stored as a donated copy, it goes through strict automatic redaction, which removes labelled names and some dates such as 03/15/2024. It can miss other date formats such as 2024-03-15, and names or dates written out in free text, so please keep that in mind.',
  'If you stop, the donated copies for that purpose are deleted. Your own records are not touched. A model already tuned with the copies, or a file already exported from them, is not changed.',
  'Nothing here is medical advice. Donated copies only help improve this app.',
  'This includes answers from the step-by-step assistant.',
].join('\n\n');

export const PURPOSE_COPY: Record<DonationPurpose, { label: string; description: string }> = {
  fine_tune: {
    label: 'Improve the assistant model',
    description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave, to tune the model on this device. This also allows a redacted training file saved on this device.',
  },
  synthetic_seed: {
    label: 'Create practice data',
    description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave as a starting point for practice data that a model on this device rewrites from them. Some details may carry over. It is kept apart from real data and never replaces it.',
  },
  agent_traces: {
    label: 'Find assistant mistakes',
    description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave to find and fix the assistant’s mistakes.',
  },
};

export function DataDonationCard() {
  const { data, isLoading, isError } = useDonationConsents();
  const setConsent = useSetDonationConsent();
  // The purpose stays after the dialog closes, so the sentence does not change while the scrim fades out.
  const [confirm, setConfirm] = useState<{ purpose: DonationPurpose; open: boolean } | null>(null);
  const confirming = confirm?.open ? confirm.purpose : null;
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The dialog has no Trigger, so Radix has nothing to return focus to: whatever opened it (the switch or the
  // Stop and delete button) gets focus back once the dialog has closed. Not in the close handler: the focus trap is
  // still on there.
  const opener = useRef<HTMLElement | null>(null);
  const wasOpen = useRef(false);
  useEffect(() => {
    const open = confirm?.open === true;
    if (wasOpen.current && !open) {
      // The Stop and delete button is gone once the purpose is off, so its switch takes the focus then.
      const target = opener.current?.isConnected
        ? opener.current
        : document.getElementById(`donation-switch-${confirm?.purpose}`);
      target?.focus();
    }
    wasOpen.current = open;
  }, [confirm?.open, confirm?.purpose]);
  const askToStop = (purpose: DonationPurpose) => {
    setError(null);
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setConfirm({ purpose, open: true });
  };
  const closeConfirm = () => setConfirm((current) => (current ? { ...current, open: false } : null));

  const granted = new Set(
    (data?.consents ?? []).filter((c) => c.granted).map((c) => c.purpose),
  );
  const stale = new Set(
    (data?.consents ?? []).filter((c) => c.granted && !c.current).map((c) => c.purpose),
  );

  const grant = async (purpose: DonationPurpose) => {
    setError(null);
    setMessage(null);
    try {
      await setConsent.mutateAsync({ purpose, granted: true, consent_text_version: CONSENT_TEXT_VERSION });
    } catch {
      setError(NEUTRAL_ERROR);
    }
  };

  const stop = async (purpose: DonationPurpose) => {
    setError(null);
    setMessage(null);
    try {
      const result = await setConsent.mutateAsync({
        purpose,
        granted: false,
        consent_text_version: CONSENT_TEXT_VERSION,
      });
      closeConfirm();
      setMessage(
        `Stopped. ${result.deleted_count} donated ${result.deleted_count === 1 ? 'copy was' : 'copies were'} deleted.`,
      );
    } catch {
      setError(NEUTRAL_ERROR);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Data donation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2" data-t0="">
          {CONSENT_INTRO.split('\n\n').map((para) => (
            <p key={para} className="text-sm text-ink-secondary">
              {para}
            </p>
          ))}
        </div>

        {isLoading ? (
          <p className="text-sm text-ink-secondary">Loading your choices...</p>
        ) : isError || !data ? (
          <p role="alert" className="text-sm text-status-critical">
            Could not load your donation choices. Reload to try again.
          </p>
        ) : (
          <ul className="space-y-3">
            {DONATION_PURPOSES.map((purpose) => {
              const on = granted.has(purpose);
              const copy = PURPOSE_COPY[purpose];
              return (
                <li key={purpose} className="space-y-2">
                  <div
                    className={cn(
                      'w-full flex items-center justify-between gap-4 px-4 py-3 rounded-xl text-left',
                      on ? 'bg-accent-subtle border border-accent/20' : 'bg-surface-muted border border-transparent',
                    )}
                  >
                    <label htmlFor={`donation-switch-${purpose}`}>
                      <span className="block text-sm font-medium">{copy.label}</span>
                      <span id={`donation-desc-${purpose}`} data-t0="" className="block text-xs text-ink-secondary">{copy.description}</span>
                    </label>
                    <Switch
                      id={`donation-switch-${purpose}`}
                      checked={on}
                      aria-label={copy.label}
                      aria-describedby={`donation-desc-${purpose}`}
                      disabled={setConsent.isPending}
                      onCheckedChange={() => (on ? askToStop(purpose) : grant(purpose))}
                    />
                  </div>

                  {stale.has(purpose) && (
                    <div className="space-y-2">
                      <p className="text-sm text-ink-secondary">
                        The wording above changed after you agreed. Nothing new is donated for this purpose until you review it and re-confirm.
                      </p>
                      <Button
                        size="sm"
                        aria-label={`Review and re-confirm: ${copy.label}`}
                        onClick={() => grant(purpose)}
                        disabled={setConsent.isPending}
                      >
                        Review and re-confirm
                      </Button>
                    </div>
                  )}

                  {on && confirming !== purpose && (
                    <Button
                      size="sm"
                      variant="secondary"
                      aria-label={`Stop and delete: ${copy.label}`}
                      onClick={() => askToStop(purpose)}
                    >
                      Stop and delete
                    </Button>
                  )}

                </li>
              );
            })}
          </ul>
        )}

        <AlertDialog
          open={confirm?.open === true}
          onOpenChange={(open) => (open ? undefined : closeConfirm())}
          still
          title="Confirm stop and delete"
        >
          <p className="text-sm">
            Stop donating for &ldquo;{confirm ? PURPOSE_COPY[confirm.purpose].label : ''}&rdquo; and delete its donated copies? This cannot be undone.
          </p>
          {error && (
            <p role="alert" className="mt-2 text-sm text-status-critical">
              {error}
            </p>
          )}
          <div className="mt-4 flex gap-2 justify-end">
            <Button size="sm" variant="secondary" data-alert-cancel="" onClick={closeConfirm}>
              Cancel
            </Button>
            <Button size="sm" onClick={() => confirm && stop(confirm.purpose)} disabled={setConsent.isPending}>
              Yes, stop and delete
            </Button>
          </div>
        </AlertDialog>

        {message && (
          <p role="status" className="text-sm text-ink-secondary">
            {message}
          </p>
        )}
        {error && (
          <p role="alert" className="text-sm text-status-critical">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
