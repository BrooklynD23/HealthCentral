/**
 * Unverified-point markers for trend charts.
 * Owner decision D4 (2026-09-27): "Trends may show unverified points but
 * visibly marked 'unverified'". The state is never conveyed by colour alone:
 * the dot is hollow and dashed, carries an SVG <title>, and the chart shows a
 * text note with the count.
 */
import type { ReactElement } from 'react';

export const UNVERIFIED_LABEL = 'Unverified';

interface TrendPointDotProps {
  cx?: number;
  cy?: number;
  verified: boolean;
  radius?: number;
  color?: string;
}

export function TrendPointDot({
  cx,
  cy,
  verified,
  radius = 5,
  color = '#2D7D6F',
}: TrendPointDotProps): ReactElement | null {
  if (cx === undefined || cy === undefined) return null;
  if (verified) {
    return <circle cx={cx} cy={cy} r={radius} fill={color} strokeWidth={0} data-verified="true" />;
  }
  return (
    <g data-verified="false" role="img" aria-label={UNVERIFIED_LABEL}>
      <title>{UNVERIFIED_LABEL}</title>
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill="#FFFFFF"
        stroke={color}
        strokeWidth={2}
        strokeDasharray="2 2"
      />
    </g>
  );
}

interface UnverifiedTrendNoteProps {
  unverified: number;
  total: number;
}

export function UnverifiedTrendNote({ unverified, total }: UnverifiedTrendNoteProps): ReactElement | null {
  if (unverified <= 0) return null;
  return (
    <p className="text-sm text-ink-secondary mt-1" data-testid="trend-unverified-note">
      <strong>{UNVERIFIED_LABEL}:</strong> {unverified} of {total} points on this chart are
      unverified (hollow markers). They have not been reviewed yet.
    </p>
  );
}
