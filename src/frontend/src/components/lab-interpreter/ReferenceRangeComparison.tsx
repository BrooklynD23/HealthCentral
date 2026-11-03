import { cn } from '@/utils/cn';
import { RangeTick } from '@/components/results/RangeTick';

interface ReferenceRangeComparisonProps {
  value: number;
  refLow: number | null;
  refHigh: number | null;
  unit: string;
  className?: string;
}

/**
 * The range text, a RangeTick (band plus marker on its own scale) and the value with its Low/High/Normal word.
 * The tick has no axis labels, so nothing prints a scale the tick does not draw. The value text is T0 (data-t0).
 * RangeTick guards a zero-width range and a non-finite value itself (GAUGE-ZERO-WIDTH, HC-UIRR-008).
 */
export function ReferenceRangeComparison({
  value,
  refLow,
  refHigh,
  unit,
  className,
}: ReferenceRangeComparisonProps) {
  if (refLow === null || refHigh === null) return null;

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

      <div className="flex items-center gap-3">
        <RangeTick value={value} refLow={refLow} refHigh={refHigh} />
        <span
          data-t0
          className={cn(
            'text-xs font-medium',
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
      </div>
    </div>
  );
}
