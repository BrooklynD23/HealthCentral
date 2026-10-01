/**
 * Break-glass redaction warning (D12, owner decision 2026-09-27).
 *
 * The external AI runner always applies strict redaction, except when the
 * installation sets EXTERNAL_API_REDACTION_BREAK_GLASS and weakens redaction.
 * That exception is audited server-side; this component is the required UI
 * warning. It renders nothing unless the backend says `true`.
 */
import { AlertCircle } from 'lucide-react';

interface ExternalApiBreakGlassWarningProps {
  active?: boolean;
}

export function ExternalApiBreakGlassWarning({ active }: ExternalApiBreakGlassWarningProps) {
  if (active !== true) return null;

  return (
    <div
      role="alert"
      className="flex items-start gap-2 px-3 py-2.5 rounded-xl bg-status-critical-subtle border border-status-critical/20"
    >
      <AlertCircle className="w-4 h-4 text-status-critical shrink-0 mt-0.5" aria-hidden />
      <p className="text-xs text-ink leading-relaxed">
        <strong>Privacy protection override is on.</strong> This installation is set to send
        external AI requests with reduced or no redaction, so names, birth dates and record
        numbers may leave this device. Each such request is recorded in the audit log.
      </p>
    </div>
  );
}
