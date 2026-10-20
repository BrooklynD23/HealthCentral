/**
 * Data donation consent (RSI1-DONATE PR-1).
 *
 * One switch per purpose, all off by default. Turning a purpose off deletes the
 * donated copies, so it always goes through an explicit confirmation.
 *
 * DRAFT COPY: the wording below needs owner approval (DON-COPY) before merge.
 * Bump CONSENT_TEXT_VERSION whenever the wording changes.
 */

import { useState } from 'react';
import { cn } from '@/utils/cn';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import {
  DONATION_PURPOSES,
  useDonationConsents,
  useSetDonationConsent,
  type DonationPurpose,
} from '@/services/donation';

export const CONSENT_TEXT_VERSION = '2026-10-20-v1';

// The audit write can fail after the change is saved, so never claim it failed.
const NEUTRAL_ERROR = 'Could not confirm your choice. Reload to see what was saved.';

export const CONSENT_INTRO = [
  'Donating is optional and off by default. You choose each purpose separately, and you can change your mind at any time.',
  'Your data never leaves this device. Before anything is stored as a donated copy, it goes through strict automatic redaction, which removes labelled names and some dates such as 03/15/2024. It can miss other date formats such as 2024-03-15, and names or dates written out in free text, so please keep that in mind.',
  'If you stop, the donated copies for that purpose are deleted. Your own records are not touched. A model already tuned with the copies, or a file already exported from them, is not changed.',
  'Nothing here is medical advice. Donated copies only help improve this app.',
].join('\n\n');

export const PURPOSE_COPY: Record<DonationPurpose, { label: string; description: string }> = {
  fine_tune: {
    label: 'Improve the assistant model',
    description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave, to tune the model on this device. This also allows a redacted training file saved on this device.',
  },
  synthetic_seed: {
    label: 'Create practice data',
    description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave as a starting point for made-up practice data, which is kept apart from real data and never replaces it.',
  },
  agent_traces: {
    label: 'Find assistant mistakes',
    description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave to find and fix the assistant’s mistakes.',
  },
};

export function DataDonationCard() {
  const { data, isLoading, isError } = useDonationConsents();
  const setConsent = useSetDonationConsent();
  const [confirming, setConfirming] = useState<DonationPurpose | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      setConfirming(null);
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
        <div className="space-y-2">
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
                  <button
                    type="button"
                    role="switch"
                    aria-checked={on}
                    aria-label={copy.label}
                    aria-describedby={`donation-desc-${purpose}`}
                    disabled={setConsent.isPending}
                    onClick={() => (on ? setConfirming(purpose) : grant(purpose))}
                    className={cn(
                      'w-full flex items-center justify-between gap-4 px-4 py-3 rounded-xl text-left',
                      'transition-all duration-300 ease-in-out',
                      on
                        ? 'bg-accent-subtle border border-accent/20'
                        : 'bg-surface-muted border border-transparent hover:bg-surface-sunken',
                    )}
                  >
                    <span>
                      <span className="block text-sm font-medium">{copy.label}</span>
                      <span id={`donation-desc-${purpose}`} className="block text-xs text-ink-secondary">{copy.description}</span>
                    </span>
                    <span
                      aria-hidden
                      className={cn(
                        'w-10 h-6 shrink-0 rounded-full relative transition-colors duration-300',
                        on ? 'bg-accent' : 'bg-black/12',
                      )}
                    >
                      <span
                        className={cn(
                          'absolute w-4 h-4 rounded-full bg-white top-1 transition-transform duration-300',
                          on ? 'translate-x-5' : 'translate-x-1',
                        )}
                      />
                    </span>
                  </button>

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
                      onClick={() => setConfirming(purpose)}
                    >
                      Stop and delete
                    </Button>
                  )}

                  {confirming === purpose && (
                    <div role="alertdialog" aria-label="Confirm stop and delete" className="space-y-2">
                      <p className="text-sm">
                        Stop donating for &ldquo;{copy.label}&rdquo; and delete its donated copies? This cannot be undone.
                      </p>
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => stop(purpose)} disabled={setConsent.isPending}>
                          Yes, stop and delete
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setConfirming(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}

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
