/**
 * EntityDetailView — table of extracted entities per document.
 * Low-confidence entities shown with dashed border + warning icon.
 */

import { AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/utils/cn';
import type { DocumentEntityResponse } from '@/services/documentCategories';

interface EntityDetailViewProps {
  entities: DocumentEntityResponse[];
  className?: string;
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

export function EntityDetailView({ entities, className }: EntityDetailViewProps) {
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
            </tr>
          </thead>
          <tbody>
            {entities.map((entity) => {
              const isLowConfidence = entity.confidence < 0.8;
              return (
                <tr
                  key={entity.id}
                  className={cn(
                    'border-b border-black/[0.04]',
                    isLowConfidence && 'border-dashed border-status-caution/30'
                  )}
                >
                  <td className="py-2 text-ink-secondary whitespace-nowrap pr-4">
                    <span className="flex items-center gap-1">
                      {ENTITY_LABELS[entity.entity_type] ?? entity.entity_type}
                      {isLowConfidence && (
                        <AlertTriangle
                          className="w-3 h-3 text-status-caution"
                          aria-label={`Low confidence: ${Math.round(entity.confidence * 100)}%`}
                        />
                      )}
                    </span>
                  </td>
                  <td className="py-2 text-ink break-words max-w-xs">
                    {entity.entity_value}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
