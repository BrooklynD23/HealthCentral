/**
 * HighlightChips — small neutral badges for derived highlight tags (HC-M16).
 *
 * Highlights are organizational tags computed server-side from existing
 * data (abnormal labs, medication changes, follow-ups, verification state).
 * Presentation stays deliberately calm: these help spot what matters,
 * they are not clinical alerts.
 */

import { Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { HIGHLIGHT_LABELS, type HighlightType } from '@/services/highlights';

type BadgeVariant = 'default' | 'accent' | 'caution' | 'attention' | 'verified' | 'info';

/** Stable display order: content tags first, review-workflow tags last. */
const HIGHLIGHT_ORDER: HighlightType[] = [
  'abnormal_value',
  'medication_started',
  'medication_stopped',
  'medication_changed',
  'follow_up_needed',
  'test_ordered',
  'referral_created',
  'new_diagnosis_mentioned',
  'low_confidence_extraction',
  'needs_verification',
];

const CHIP_VARIANTS: Record<HighlightType, BadgeVariant> = {
  abnormal_value: 'info',
  medication_started: 'accent',
  medication_stopped: 'accent',
  medication_changed: 'accent',
  follow_up_needed: 'info',
  test_ordered: 'info',
  referral_created: 'info',
  new_diagnosis_mentioned: 'info',
  low_confidence_extraction: 'caution',
  needs_verification: 'caution',
};

interface HighlightChipsProps {
  /** Highlight-type counts (a lone tag may simply have count 1). */
  counts: Partial<Record<HighlightType, number>>;
  /** Cap on chips rendered; overflow collapses into a "+N" chip. */
  max?: number;
  className?: string;
}

export function HighlightChips({ counts, max, className }: HighlightChipsProps) {
  const present = HIGHLIGHT_ORDER.filter((type) => (counts[type] ?? 0) > 0);
  if (present.length === 0) return null;

  const shown = max !== undefined ? present.slice(0, max) : present;
  const overflow = present.length - shown.length;

  return (
    <span className={cn('flex flex-wrap items-center gap-1', className)}>
      {shown.map((type) => {
        const count = counts[type] ?? 0;
        return (
          <Badge key={type} variant={CHIP_VARIANTS[type]} className="whitespace-nowrap">
            {HIGHLIGHT_LABELS[type]}
            {count > 1 ? ` ×${count}` : ''}
          </Badge>
        );
      })}
      {overflow > 0 && <Badge variant="default">+{overflow}</Badge>}
    </span>
  );
}
