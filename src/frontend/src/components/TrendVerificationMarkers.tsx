/**
 * Unverified-point markers for trend charts.
 * Owner decision D4 (2026-09-27): "Trends may show unverified points but
 * visibly marked 'unverified'". The state is never conveyed by colour alone:
 * the point marker is a hollow dashed circle rendered inside
 * `results/RangeRibbon.tsx` (`data-verified="false"`), and the chart shows a
 * text note with the count.
 */
import type { ReactElement } from 'react';

export const UNVERIFIED_LABEL = 'Unverified';

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
