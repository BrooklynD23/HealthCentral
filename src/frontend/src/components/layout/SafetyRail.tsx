import { cn } from '@/utils/cn';

/**
 * The Safety Rail (plan §3.6): a one-line strip on every authenticated page.
 * It sits outside the route container, so the route fade never touches it, and
 * it is never animated. Opaque with no backdrop blur (DF-1).
 *
 * Tablets and desktop: sticky at the bottom of the content column (no tab bar to clear at md and up).
 * Phones: above the tab bar, which is a 1 px border
 * plus a 56 px tab row (MobileTabBar), so the rail's bottom is 57 px plus the safe area.
 */
export function SafetyRail({ className }: { className?: string }) {
  return (
    <section
      data-safety-rail
      data-t0
      aria-label="Safety notice"
      className={cn(
        'border-t border-border bg-surface-elevated px-4 py-2 text-xs text-ink-secondary',
        'max-md:fixed max-md:inset-x-0 max-md:bottom-[calc(57px+env(safe-area-inset-bottom))] max-md:z-30',
        'md:sticky md:bottom-0 md:z-30 lg:px-8 lg:py-3',
        className
      )}
    >
      <p className="hidden lg:block">Educational only, not medical advice. Your records stay on this device.</p>
      <p className="lg:hidden">Educational only, not medical advice.</p>
    </section>
  );
}
