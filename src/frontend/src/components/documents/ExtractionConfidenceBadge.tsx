import { Badge } from '@/components/ui';

interface ExtractionConfidenceBadgeProps {
  confidence: number | null | undefined;
  lowest?: boolean;
}

export function ExtractionConfidenceBadge({
  confidence,
  lowest = false,
}: ExtractionConfidenceBadgeProps) {
  if (confidence === null || confidence === undefined) {
    return <Badge variant="default">Extraction confidence unavailable</Badge>;
  }

  const percentage = Math.round(confidence * 100);
  const label = (band: string) => lowest
    ? `${percentage}% · ${band} · Lowest extraction confidence`
    : `${percentage}% · ${band} extraction confidence`;
  if (confidence >= 0.8) {
    return <Badge variant="verified">{label('High')}</Badge>;
  }
  if (confidence >= 0.5) {
    return <Badge variant="caution">{label('Medium')}</Badge>;
  }
  return <Badge variant="attention">{label('Low')}</Badge>;
}
