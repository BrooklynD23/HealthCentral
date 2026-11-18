/**
 * RangeTick: the 64 px band-plus-marker glyph (UI-RIBBON). It replaces the gauge
 * in ReferenceRangeComparison. The glyph is decorative: the text beside it
 * carries the value and the range, so it is hidden from assistive technology.
 *
 * Zero width (low = high = value, or all zero) is guarded so no NaN reaches the
 * markup (HC-UIRR-008, mirroring HC-GZW-001/002). Colours are CSS tokens only.
 */
import type { ReactElement } from 'react';
import { cn } from '@/utils/cn';

const WIDTH = 64;
const HEIGHT = 16;
const PAD = 4;
const MID_Y = HEIGHT / 2;

interface RangeTickProps {
  value: number;
  refLow: number | null;
  refHigh: number | null;
  className?: string;
}

function finiteOrNull(n: number | null): number | null {
  return typeof n === 'number' && Number.isFinite(n) ? n : null;
}

export function RangeTick({ value, refLow, refHigh, className }: RangeTickProps): ReactElement | null {
  if (!Number.isFinite(value)) return null;

  const low = finiteOrNull(refLow);
  const high = finiteOrNull(refHigh);
  // A missing bound is drawn at the value, so it never widens the scale.
  const min = Math.min(low ?? value, high ?? value, value);
  const max = Math.max(low ?? value, high ?? value, value);
  const span = max - min;
  // With no span (every number equal) everything sits at the centre: no division by zero.
  const xOf = (v: number): number =>
    span > 0 ? PAD + ((v - min) / span) * (WIDTH - 2 * PAD) : WIDTH / 2;

  return (
    <svg
      aria-hidden="true"
      width={WIDTH}
      height={HEIGHT}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className={cn('shrink-0', className)}
      data-range-tick
    >
      {low !== null && high !== null && (
        <rect
          data-band
          x={Math.min(xOf(low), xOf(high))}
          y={MID_Y - 4}
          width={Math.abs(xOf(high) - xOf(low))}
          height={8}
          rx={2}
          fill="var(--band)"
        />
      )}
      {low !== null && (
        <line
          data-band-edge="low"
          x1={xOf(low)}
          x2={xOf(low)}
          y1={MID_Y - 5}
          y2={MID_Y + 5}
          stroke="var(--line-strong)"
          strokeWidth={1}
        />
      )}
      {high !== null && (
        <line
          data-band-edge="high"
          x1={xOf(high)}
          x2={xOf(high)}
          y1={MID_Y - 5}
          y2={MID_Y + 5}
          stroke="var(--line-strong)"
          strokeWidth={1}
        />
      )}
      <circle
        data-marker
        cx={xOf(value)}
        cy={MID_Y}
        r={3.5}
        fill="var(--ink-1)"
        stroke="var(--surface-1)"
        strokeWidth={1.5}
      />
    </svg>
  );
}
