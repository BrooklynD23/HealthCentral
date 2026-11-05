import { ShieldAlert } from 'lucide-react';
import { cn } from '@/utils/cn';

interface DisclaimerBannerProps {
  className?: string;
}

/**
 * The contextual disclaimer. It is a note, not an alert: it is always on the page and nothing happens to announce,
 * so a screen reader reads it in order instead of interrupting (HC-EXT-006b asserts no alert on the page). It is
 * never animated, and it is T0 text (data-t0): the stillness probe holds it still from first paint.
 */
export function DisclaimerBanner({ className }: DisclaimerBannerProps) {
  return (
    <div
      role="note"
      data-t0
      className={cn(
        'flex items-start gap-2.5 p-3 rounded-xl sm:gap-3 sm:p-4',
        'bg-status-caution-subtle border border-status-caution/20',
        className
      )}
    >
      <ShieldAlert className="w-5 h-5 text-status-caution shrink-0 mt-0.5" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium text-ink">
          For informational purposes only
        </p>
        <p className="text-xs text-ink-secondary mt-1 leading-snug sm:leading-relaxed">
          AI-generated interpretations are not medical advice. Always consult
          your healthcare provider before making decisions based on lab results.
          Critical or unexpected values should be reviewed by a physician.
        </p>
      </div>
    </div>
  );
}
