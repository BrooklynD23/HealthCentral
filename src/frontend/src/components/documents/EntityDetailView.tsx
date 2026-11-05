/**
 * EntityDetailView — table of extracted entities per document.
 * Low-confidence entities shown with dashed border + warning icon.
 * Each entity shows its verbatim source quote (HC-M12), its derived
 * highlight tags (HC-M16), and, when a verification handler is
 * provided, verify/reject controls.
 */

import { m } from 'framer-motion';
import { AlertTriangle, CheckCircle, X } from 'lucide-react';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { StatusChip } from '@/components/ui/StatusChip';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { duration, ease } from '@/motion/tokens';
import { cn } from '@/utils/cn';
import type { DocumentEntityResponse } from '@/services/documentCategories';
import { useDocumentHighlights, type HighlightType } from '@/services/highlights';
import { HighlightChips } from './HighlightChips';
import { ExtractionConfidenceBadge } from './ExtractionConfidenceBadge';

interface EntityDetailViewProps {
  entities: DocumentEntityResponse[];
  className?: string;
  /** When provided, verify/reject controls are shown per entity. */
  onSetVerification?: (entity: DocumentEntityResponse, verified: boolean | null) => void;
  verificationPending?: boolean;
  /** CITE-SRC-001: the entity an assistant citation deep-linked to. */
  highlightEntityId?: string | null;
}

const ENTITY_LABELS: Record<string, string> = {
  modality: 'Modality',
  body_region: 'Body Region',
  finding: 'Finding',
  impression: 'Impression',
  laterality: 'Laterality',
  contrast_used: 'Contrast',
  ordering_provider: 'Ordering Provider',
  report_date: 'Report Date',
  specimen_type: 'Specimen Type',
  specimen_site: 'Specimen Site',
  diagnosis: 'Diagnosis',
  grade: 'Grade',
  stage: 'Stage',
  margins: 'Margins',
  special_stains: 'Special Stains',
  pathologist: 'Pathologist',
  visit_type: 'Visit Type',
  chief_complaint: 'Chief Complaint',
  assessment: 'Assessment',
  plan: 'Plan',
  diagnoses: 'Diagnoses',
  provider: 'Provider',
  visit_date: 'Visit Date',
  vitals: 'Vitals',
  medication_change: 'Medication Change',
  test_ordered: 'Test Ordered',
  referral: 'Referral',
  follow_up_instruction: 'Follow-up Instruction',
  warning_sign: 'Warning Sign',
  facility: 'Facility',
};

// Mutable copy of the readonly token: framer's Easing type does not accept readonly tuples.
const EASE_OUT: [number, number, number, number] = [...ease.out];
const INK_SHUT = 'circle(0% at 50% 50%)';
const INK_OPEN = 'circle(75% at 50% 50%)';

/**
 * The Ink moment (plan section 4.1): the row marker goes from a dashed graphite ring (pencil) to a filled
 * mark (ink) when the user verifies a value. The ink layer is revealed with a clip-path circle, 360 ms
 * ease-out; nothing else moves. It is decoration (T3): aria-hidden and no data-t0, because the chip beside it
 * says the same thing in words. Reduced motion swaps instantly.
 */
export function InkMarker({ verified }: { verified: boolean }) {
  const reduced = useReducedMotion();
  return (
    <span
      data-ink-marker=""
      data-state={verified ? 'ink' : 'pencil'}
      data-motion={reduced ? 'instant' : 'ink'}
      aria-hidden="true"
      className="relative inline-block h-4 w-4 shrink-0"
    >
      <svg viewBox="0 0 16 16" className="absolute inset-0 h-4 w-4" fill="none">
        <circle
          cx="8"
          cy="8"
          r="6.5"
          strokeWidth="1.5"
          strokeDasharray="3 2.5"
          style={{ stroke: 'var(--pencil)' }}
        />
      </svg>
      <m.span
        data-ink-layer=""
        className="absolute inset-0"
        initial={false}
        animate={{ clipPath: verified ? INK_OPEN : INK_SHUT }}
        transition={reduced ? { duration: 0 } : { duration: duration.ink, ease: EASE_OUT }}
      >
        <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none">
          <circle cx="8" cy="8" r="7" style={{ fill: 'var(--ink-1)' }} />
          <path
            d="M4.75 8.25l2.25 2.25 4.25-4.5"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ stroke: 'var(--surface-1)' }}
          />
        </svg>
      </m.span>
    </span>
  );
}

export function EntityDetailView({
  entities,
  className,
  onSetVerification,
  verificationPending,
  highlightEntityId,
}: EntityDetailViewProps) {
  // Derived highlight tags (HC-M16), grouped per source entity.
  const { data: highlights = [] } = useDocumentHighlights(entities[0]?.doc_id);
  const highlightsByEntity = new Map<string, Partial<Record<HighlightType, number>>>();
  for (const highlight of highlights) {
    if (highlight.source_kind !== 'entity') continue;
    const counts = highlightsByEntity.get(highlight.source_id) ?? {};
    counts[highlight.highlight_type] = (counts[highlight.highlight_type] ?? 0) + 1;
    highlightsByEntity.set(highlight.source_id, counts);
  }

  if (entities.length === 0) return null;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">Extracted Information</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Stacked at every width (L0 ruling on review round 3, finding 5). This list sits in the one-third column, where
            sm:table cells sized by their content overflowed the page once a "Checked by you" chip joined the Review cell,
            and re-wrapped the value beside it. A block row has one width, so a chip changes no value. */}
        <table role="table" className="block w-full text-sm">
          <thead role="rowgroup" className="hidden">
            <tr role="row" className="border-b border-black/6">
              <th role="columnheader" className="text-left py-2 text-ink-tertiary font-medium">Field</th>
              <th role="columnheader" className="text-left py-2 text-ink-tertiary font-medium">Value</th>
              {onSetVerification && (
                <th role="columnheader" className="text-right py-2 text-ink-tertiary font-medium">Review</th>
              )}
            </tr>
          </thead>
          <tbody role="rowgroup" className="block">
            {entities.map((entity) => {
              const isLowConfidence = entity.confidence < 0.8;
              const label = ENTITY_LABELS[entity.entity_type] ?? entity.entity_type;
              return (
                <tr
                  key={entity.id}
                  id={`entity-row-${entity.id}`}
                  role="row"
                  className={cn(
                    'block border-b border-black/4 py-2',
                    isLowConfidence && 'border-dashed border-status-caution/30',
                    highlightEntityId === entity.id && 'bg-accent/10'
                  )}
                >
                  <td role="cell" className="block py-1 text-ink-secondary">
                    <span className="flex items-center gap-1.5">
                      {onSetVerification ? <InkMarker verified={entity.verified_by_user === true} /> : null}
                      {label}
                      {isLowConfidence && (
                        <AlertTriangle
                          className="w-3 h-3 text-status-caution"
                          aria-label={`Low confidence: ${Math.round(entity.confidence * 100)}%`}
                        />
                      )}
                    </span>
                  </td>
                  <td role="cell" className="block py-1 text-ink wrap-break-word">
                    <span data-t0="">{entity.entity_value}</span>
                    <div className="mt-1">
                      <ExtractionConfidenceBadge confidence={entity.confidence} />
                    </div>
                    {entity.quote && (
                      <p className="mt-1 text-xs text-ink-secondary font-mono italic wrap-break-word">
                        &ldquo;{entity.quote}&rdquo;
                      </p>
                    )}
                    {highlightsByEntity.has(entity.id) && (
                      <HighlightChips
                        counts={highlightsByEntity.get(entity.id)!}
                        className="mt-1.5"
                      />
                    )}
                  </td>
                  {onSetVerification && (
                    <td role="cell" className="block py-1">
                      <span className="inline-flex flex-wrap items-center gap-1">
                        {entity.verified_by_user === true && <StatusChip state="checked-by-you" />}
                        {entity.verified_by_user === false && (
                          <Badge variant="attention" className="text-xs">Rejected</Badge>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Verify ${label}`}
                          disabled={verificationPending}
                          onClick={() =>
                            onSetVerification(
                              entity,
                              entity.verified_by_user === true ? null : true
                            )
                          }
                        >
                          <CheckCircle
                            className={cn(
                              'w-4 h-4',
                              entity.verified_by_user === true
                                ? 'text-status-verified'
                                : 'text-ink-tertiary'
                            )}
                          />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Reject ${label}`}
                          disabled={verificationPending}
                          onClick={() =>
                            onSetVerification(
                              entity,
                              entity.verified_by_user === false ? null : false
                            )
                          }
                        >
                          <X
                            className={cn(
                              'w-4 h-4',
                              entity.verified_by_user === false
                                ? 'text-status-attention'
                                : 'text-ink-tertiary'
                            )}
                          />
                        </Button>
                      </span>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
