import { cn } from '@/utils/cn';

interface ReferenceRangeComparisonProps {
  value: number;
  refLow: number | null;
  refHigh: number | null;
  unit: string;
  className?: string;
}

export function ReferenceRangeComparison({
  value,
  refLow,
  refHigh,
  unit,
  className,
}: ReferenceRangeComparisonProps) {
  if (refLow === null || refHigh === null) return null;

  const range = refHigh - refLow;
  const padding = range * 0.3;
  const displayMin = refLow - padding;
  const displayMax = refHigh + padding;
  const displayRange = displayMax - displayMin;

  const refLowPct = ((refLow - displayMin) / displayRange) * 100;
  const refHighPct = ((refHigh - displayMin) / displayRange) * 100;
  const valuePct = Math.max(0, Math.min(100, ((value - displayMin) / displayRange) * 100));

  const isLow = value < refLow;
  const isHigh = value > refHigh;
  const isNormal = !isLow && !isHigh;

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between text-xs text-ink-secondary">
        <span>Reference Range</span>
        <span>
          {refLow} - {refHigh} {unit}
        </span>
      </div>

      <div className="relative h-8">
        {/* Track */}
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-2 rounded-full bg-surface-sunken" />

        {/* Normal range highlight */}
        <div
          className="absolute top-1/2 -translate-y-1/2 h-2 rounded-full bg-status-verified/20"
          style={{
            left: `${refLowPct}%`,
            width: `${refHighPct - refLowPct}%`,
          }}
        />

        {/* Low boundary marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-px h-4 bg-status-verified/40"
          style={{ left: `${refLowPct}%` }}
        />

        {/* High boundary marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-px h-4 bg-status-verified/40"
          style={{ left: `${refHighPct}%` }}
        />

        {/* Value indicator */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
          style={{ left: `${valuePct}%` }}
        >
          <div
            className={cn(
              'w-4 h-4 rounded-full border-2 border-white shadow-soft',
              isNormal && 'bg-status-verified',
              isLow && 'bg-status-info',
              isHigh && 'bg-status-attention'
            )}
          />
        </div>
      </div>

      <div className="flex items-center justify-between text-xs">
        <span className="text-ink-tertiary">{displayMin.toFixed(1)}</span>
        <span
          className={cn(
            'font-medium',
            isNormal && 'text-status-verified',
            isLow && 'text-status-info',
            isHigh && 'text-status-attention'
          )}
        >
          {value} {unit}
          {isLow && ' (Low)'}
          {isHigh && ' (High)'}
          {isNormal && ' (Normal)'}
        </span>
        <span className="text-ink-tertiary">{displayMax.toFixed(1)}</span>
      </div>
    </div>
  );
}
