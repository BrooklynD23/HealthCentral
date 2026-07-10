/**
 * EntityDetailView — table of extracted entities per document.
 * Low-confidence entities shown with dashed border + warning icon.
 * Each entity shows its verbatim source quote (HC-M12) and, when a
 * verification handler is provided, verify/reject controls.
 */

import { AlertTriangle, CheckCircle, X } from 'lucide-react';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/utils/cn';
import type { DocumentEntityResponse } from '@/services/documentCategories';

interface EntityDetailViewProps {
  entities: DocumentEntityResponse[];
  className?: string;
  /** When provided, verify/reject controls are shown per entity. */
  onSetVerification?: (entity: DocumentEntityResponse, verified: boolean | null) => void;
  verificationPending?: boolean;
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
};

export function EntityDetailView({
  entities,
  className,
  onSetVerification,
  verificationPending,
}: EntityDetailViewProps) {
  if (entities.length === 0) return null;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">Extracted Information</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-black/[0.06]">
              <th className="text-left py-2 text-ink-tertiary font-medium">Field</th>
              <th className="text-left py-2 text-ink-tertiary font-medium">Value</th>
              {onSetVerification && (
                <th className="text-right py-2 text-ink-tertiary font-medium">Review</th>
              )}
            </tr>
          </thead>
          <tbody>
            {entities.map((entity) => {
              const isLowConfidence = entity.confidence < 0.8;
              const label = ENTITY_LABELS[entity.entity_type] ?? entity.entity_type;
              return (
                <tr
                  key={entity.id}
                  className={cn(
                    'border-b border-black/[0.04]',
                    isLowConfidence && 'border-dashed border-status-caution/30'
                  )}
                >
                  <td className="py-2 text-ink-secondary whitespace-nowrap pr-4 align-top">
                    <span className="flex items-center gap-1">
                      {label}
                      {isLowConfidence && (
                        <AlertTriangle
                          className="w-3 h-3 text-status-caution"
                          aria-label={`Low confidence: ${Math.round(entity.confidence * 100)}%`}
                        />
                      )}
                    </span>
                  </td>
                  <td className="py-2 text-ink break-words max-w-xs align-top">
                    {entity.entity_value}
                    {entity.quote && (
                      <p className="mt-1 text-xs text-ink-secondary font-mono italic break-words">
                        &ldquo;{entity.quote}&rdquo;
                      </p>
                    )}
                  </td>
                  {onSetVerification && (
                    <td className="py-2 text-right whitespace-nowrap align-top">
                      <span className="inline-flex items-center gap-1">
                        {entity.verified_by_user === true && (
                          <Badge variant="verified" className="text-xs">Verified</Badge>
                        )}
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
