import { cn } from '@/utils/cn';

export interface ProgressProps {
  value: number;
  max?: number;
  /** What the bar measures. Announced to assistive technology. */
  label: string;
  className?: string;
}

/**
 * Determinate progress (M12, clip-path over 240 ms). The fill is revealed by
 * clip-path, so the bar never changes layout and paints no transform — G5's
 * reduced-motion snapshot would read a resting scaleX as motion. Reduced
 * motion makes the step instant.
 */
export function Progress({ value, max = 100, label, className }: ProgressProps) {
  const now = Math.min(Math.max(value, 0), max);
  const fraction = max > 0 ? now / max : 0;

  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={now}
      className={cn('relative h-2 overflow-hidden rounded-full bg-surface-sunken', className)}
    >
      <div
        className="absolute inset-0 bg-accent transition-[clip-path] duration-[240ms] ease-[var(--ease-out)] motion-reduce:transition-none"
        style={{ clipPath: `inset(0 ${(1 - fraction) * 100}% 0 0)` }}
      />
    </div>
  );
}
