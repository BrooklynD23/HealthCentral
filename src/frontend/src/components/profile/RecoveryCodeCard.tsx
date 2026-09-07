/**
 * One-time recovery code display (SEC-RECOV-001).
 *
 * Shown after profile creation, after a successful recovery, and after
 * generating a replacement code. In every case the code is displayed exactly
 * once — the server keeps only the seal derived from it, never the code — so
 * the "I have stored this" gate is the last chance to write it down.
 *
 * The copy is deliberately blunt: losing both the password and this code means
 * the record is unrecoverable. That is the design, not a bug, and telling the
 * user otherwise would be a false promise.
 */

import { useState } from 'react';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';

interface RecoveryCodeCardProps {
  code: string;
  /** Called when the user confirms they have stored the code. */
  onAcknowledge: () => void;
  acknowledgeLabel?: string;
  title?: string;
}

export function RecoveryCodeCard({
  code,
  onAcknowledge,
  acknowledgeLabel = 'Continue',
  title = 'Save your recovery code',
}: RecoveryCodeCardProps) {
  const [stored, setStored] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked by permissions; the code is on screen anyway.
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-ink-secondary">
          This code is the only way back into your health record if you forget
          your password. We show it once and never store it — write it down or
          print it, and keep it somewhere safe and private.
        </p>

        <div
          className="rounded-md bg-surface-muted p-4 font-mono text-lg tracking-wider break-all select-all text-center"
          data-testid="recovery-code"
          aria-label="Your recovery code"
        >
          {code}
        </div>

        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={handleCopy}>
            {copied ? 'Copied' : 'Copy'}
          </Button>
          <Button variant="secondary" size="sm" onClick={() => window.print()}>
            Print
          </Button>
        </div>

        <p className="text-sm text-status-attention">
          If you lose both your password and this code, your health record
          cannot be recovered by anyone — including us. Everything stays
          encrypted on this device, so there is no copy to restore from.
        </p>

        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={stored}
            onChange={(e) => setStored(e.target.checked)}
            className="mt-1"
          />
          <span>I have saved this recovery code somewhere safe</span>
        </label>

        <Button onClick={onAcknowledge} disabled={!stored} className="w-full">
          {acknowledgeLabel}
        </Button>
      </CardContent>
    </Card>
  );
}
