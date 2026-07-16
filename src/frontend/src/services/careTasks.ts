/**
 * Care Tasks API Service (HC-M15)
 *
 * React Query hooks for the follow-up task checklist. Task candidates are
 * derived server-side from visit-note entities and become persisted tasks
 * only through explicit user acceptance.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch, apiPost } from './api';

export type CareTaskStatus = 'open' | 'done' | 'ignored' | 'needs_review';

export interface CarePlanTask {
  id: string;
  title: string;
  due_date: string | null;
  due_date_confidence: number | null;
  status: CareTaskStatus;
  source_document_id: string | null;
  source_entity_id: string | null;
  source_quote: string | null;
  user_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface CareTaskCandidate {
  title: string;
  source_entity_id: string | null;
  source_document_id: string | null;
  source_quote: string | null;
  due_date: string | null;
  due_date_confidence: number | null;
  suggested_status: CareTaskStatus;
}

export interface AcceptCareTaskRequest {
  source_entity_id: string;
  source_document_id: string;
  source_quote: string | null;
  user_note?: string | null;
}

export interface CareTaskUpdateRequest {
  status?: CareTaskStatus;
  user_note?: string;
}

const QUERY_KEY = 'care-tasks';

export function useCareTasks(status?: CareTaskStatus) {
  return useQuery({
    queryKey: [QUERY_KEY, { status: status ?? null }],
    queryFn: () =>
      apiGet<CarePlanTask[]>('/care-tasks/', status ? { status } : undefined),
  });
}

export function useCareTaskCandidates(docId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, 'candidates', docId],
    queryFn: () =>
      apiGet<CareTaskCandidate[]>('/care-tasks/candidates', { doc_id: docId! }),
    enabled: !!docId,
  });
}

export function useAcceptCareTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: AcceptCareTaskRequest) =>
      apiPost<CarePlanTask, AcceptCareTaskRequest>('/care-tasks/accept', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useUpdateCareTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: CareTaskUpdateRequest }) =>
      apiPatch<CarePlanTask, CareTaskUpdateRequest>(`/care-tasks/${taskId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}
