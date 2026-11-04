import { Badge } from '@/components/ui';

/** Below this, the inbox shows confidence in words (plan §2.5). */
const THRESHOLD = 0.8;

interface ExtractionConfidenceBadgeProps {
  confidence: number | null | undefined;
  lowest?: boolean;
  /**
   * Words first, and only below the threshold (plan §2.5, UI-PG-DOCUMENTS). At 0.8 or above it renders nothing.
   * Below it, a status-word badge ("Low read confidence · check this value") is followed by the percentage label
   * in a muted span. Unknown confidence stays visible: unknown is not the same as fine. The output carries data-t0.
   * Off by default, so every other caller (/verify) renders the same markup as before.
   */
  belowThresholdOnly?: boolean;
}

export function ExtractionConfidenceBadge({
  confidence,
  lowest = false,
  belowThresholdOnly = false,
}: ExtractionConfidenceBadgeProps) {
  if (confidence === null || confidence === undefined) {
    return belowThresholdOnly ? (
      <Badge variant="default" data-t0 data-confidence-words>
        Extraction confidence unavailable
      </Badge>
    ) : (
      <Badge variant="default">Extraction confidence unavailable</Badge>
    );
  }

  const percentage = Math.round(confidence * 100);
  const label = (band: string) => lowest
    ? `${percentage}% · ${band} · Lowest extraction confidence`
    : `${percentage}% · ${band} extraction confidence`;

  if (belowThresholdOnly) {
    if (confidence >= THRESHOLD) return null;
    const medium = confidence >= 0.5;
    const band = medium ? 'Medium' : 'Low';
    return (
      <span data-t0 data-confidence-words className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
        <Badge variant={medium ? 'caution' : 'attention'}>{band} read confidence · check this value</Badge>
        <span className="text-xs text-ink-secondary">{label(band)}</span>
      </span>
    );
  }

  if (confidence >= 0.8) {
    return <Badge variant="verified">{label('High')}</Badge>;
  }
  if (confidence >= 0.5) {
    return <Badge variant="caution">{label('Medium')}</Badge>;
  }
  return <Badge variant="attention">{label('Low')}</Badge>;
}
