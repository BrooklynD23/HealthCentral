/**
 * Medication Reconciliation API Service (HC-M19)
 *
 * Read-only comparison of a document's medication lines against the
 * profile's medication list. Suggestions only report differences
 * ("the note says X / your list has Y"); applying a change happens
 * exclusively through the existing medications endpoints, initiated by
 * the user in the normal add/edit form.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';

export type MedReconcileSuggestionType =
  | 'new_medication'
  | 'stopped_medication'
  | 'dose_or_frequency_change'
  | 'possible_duplicate'
  | 'unclear';

export interface MedReconcileSuggestion {
  suggestion_type: MedReconcileSuggestionType;
  source_entity_id: string | null;
  source_quote: string | null;
  entity_value: string;
  drug_name: string | null;
  matched_medication_id: string | null;
  current_list_summary: string;
  confidence: number;
  reason: string | null;
}

const QUERY_KEY = 'med-reconciliation';

export function useMedReconciliation(docId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, docId],
    queryFn: () =>
      apiGet<MedReconcileSuggestion[]>('/med-reconciliation/', {
        doc_id: docId!,
      }),
    enabled: !!docId,
  });
}
