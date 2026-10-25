import { cn } from '@/utils/cn';

/**
 * The Safety Rail (plan §3.6): a one-line strip on every authenticated page.
 * It sits outside the route container, so the route fade never touches it, and
 * it is never animated. Opaque with no backdrop blur (DF-1).
 *
 * Desktop: sticky at the bottom of the content column. Phones: above the tab bar.
 */
export function SafetyRail({ className }: { className?: string }) {
  return (
    <section
      data-safety-rail
      data-t0
      aria-label="Safety notice"
      className={cn(
        'border-t border-border bg-surface-elevated px-4 py-2 text-xs text-ink-secondary',
        'max-lg:fixed max-lg:inset-x-0 max-lg:bottom-[calc(4rem+env(safe-area-inset-bottom))] max-lg:z-30',
        'lg:sticky lg:bottom-0 lg:z-30 lg:px-8 lg:py-3',
        className
      )}
    >
      <p className="hidden lg:block">Educational only, not medical advice. Your records stay on this device.</p>
      <p className="lg:hidden">Educational only, not medical advice.</p>
    </section>
  );
}
