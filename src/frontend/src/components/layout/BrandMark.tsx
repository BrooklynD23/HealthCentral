import { Heart } from 'lucide-react';
import { cn } from '@/utils/cn';

/**
 * The product mark. The wordmark is a span, never a heading, so each page has
 * exactly one h1 (plan §3.1). `data-brand` is the hook for the brand colour
 * check (TW4-INBOX) and the h1 rule. `wordmark={false}` keeps the name for
 * screen readers only, for the phone top bar where the sidebar is absent.
 */
export function BrandMark({
  className,
  showTagline = false,
  wordmark = true,
}: {
  className?: string;
  showTagline?: boolean;
  wordmark?: boolean;
}) {
  return (
    <span className={cn('inline-flex items-center gap-3', className)}>
      <span
        aria-hidden="true"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-accent to-accent/80 shadow-soft"
      >
        <Heart className="h-5 w-5 text-white" strokeWidth={2.5} />
      </span>
      {wordmark ? (
        <span className="min-w-0">
          <span data-brand className="block font-display text-lg font-semibold tracking-tight text-ink">
            Asclexis
          </span>
          {showTagline ? <span className="block text-xs text-ink-secondary">Your health companion</span> : null}
        </span>
      ) : (
        <span className="sr-only">Asclexis</span>
      )}
    </span>
  );
}
