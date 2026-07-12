/**
 * Smart Highlights API Service (HC-M16)
 *
 * React Query hooks for derived highlight tags. Highlights are computed
 * server-side on read from existing verified data structures (observations
 * and document entities) and always resolve to a source row. They are
 * organizational tags, not clinical alerts.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';

export type HighlightType =
  | 'abnormal_value'
  | 'medication_started'
  | 'medication_stopped'
  | 'medication_changed'
  | 'follow_up_needed'
  | 'test_ordered'
  | 'referral_created'
  | 'new_diagnosis_mentioned'
  | 'low_confidence_extraction'
  | 'needs_verification';

export interface Highlight {
  highlight_type: HighlightType;
  doc_id: string;
  source_kind: 'entity' | 'observation';
  source_id: string;
  quote: string | null;
  confidence: number | null;
  verification_state: string;
}

export interface DocumentHighlightSummary {
  doc_id: string;
  counts: Partial<Record<HighlightType, number>>;
}

/** Neutral, non-alarming labels — organizational tags, not clinical alerts. */
export const HIGHLIGHT_LABELS: Record<HighlightType, string> = {
  abnormal_value: 'Abnormal lab',
  medication_started: 'Medication started',
  medication_stopped: 'Medication stopped',
  medication_changed: 'Medication changed',
  follow_up_needed: 'Follow-up needed',
  test_ordered: 'Test ordered',
  referral_created: 'Referral',
  new_diagnosis_mentioned: 'Diagnosis mentioned',
  low_confidence_extraction: 'Low confidence',
  needs_verification: 'Needs verification',
};

const QUERY_KEY = 'highlights';

export function useDocumentHighlights(docId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, 'document', docId],
    queryFn: () => apiGet<Highlight[]>(`/documents/${docId}/highlights`),
    enabled: !!docId,
  });
}

export function useHighlightsSummary(limit?: number) {
  return useQuery({
    queryKey: [QUERY_KEY, 'summary', { limit: limit ?? null }],
    queryFn: () =>
      apiGet<DocumentHighlightSummary[]>(
        '/documents/highlights/summary',
        limit !== undefined ? { limit: String(limit) } : undefined
      ),
  });
}
