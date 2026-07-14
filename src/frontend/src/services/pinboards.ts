/** Profile-scoped pinboard API and React Query hooks (HC-M20). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiDelete, apiGet, apiPatch, apiPost } from './api';

export type PinboardItemType = 'document' | 'observation' | 'care_task' | 'question';

export interface Pinboard {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface PinboardItem {
  id: string;
  pinboard_id: string;
  item_type: PinboardItemType;
  item_id: string;
  created_at: string;
}

export interface AddPinboardItemRequest {
  item_type: PinboardItemType;
  item_id: string;
}

export interface PinboardExportRequest {
  reason_for_visit?: string | null;
  confirm: boolean;
}

export interface PinboardExportResponse {
  packet_id: string;
  profile_id: string;
  generated_at: string;
  section_titles: string[];
  markdown: string;
  redaction_count: number;
}

const QUERY_KEY = 'pinboards';

export function listPinboards() {
  return apiGet<Pinboard[]>('/pinboards/');
}

export function createPinboard(name: string) {
  return apiPost<Pinboard, { name: string }>('/pinboards/', { name });
}

export function renamePinboard(pinboardId: string, name: string) {
  return apiPatch<Pinboard, { name: string }>(`/pinboards/${pinboardId}`, { name });
}

export function deletePinboard(pinboardId: string) {
  return apiDelete(`/pinboards/${pinboardId}`);
}

export function listPinboardItems(pinboardId: string) {
  return apiGet<PinboardItem[]>(`/pinboards/${pinboardId}/items`);
}

export function addPinboardItem(pinboardId: string, request: AddPinboardItemRequest) {
  return apiPost<PinboardItem, AddPinboardItemRequest>(
    `/pinboards/${pinboardId}/items`, request
  );
}

export function removePinboardItem(pinboardId: string, itemId: string) {
  return apiDelete(`/pinboards/${pinboardId}/items/${itemId}`);
}

export function exportPinboard(pinboardId: string, request: PinboardExportRequest) {
  return apiPost<PinboardExportResponse, PinboardExportRequest>(
    `/pinboards/${pinboardId}/export`, request
  );
}

export function usePinboards() {
  return useQuery({ queryKey: [QUERY_KEY], queryFn: listPinboards });
}

export function usePinboardItems(pinboardId?: string) {
  return useQuery({
    queryKey: [QUERY_KEY, pinboardId, 'items'],
    queryFn: () => listPinboardItems(pinboardId!),
    enabled: !!pinboardId,
  });
}

function usePinboardMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [QUERY_KEY] }),
  });
}

export function useCreatePinboard() {
  return usePinboardMutation((name: string) => createPinboard(name));
}

export function useRenamePinboard() {
  return usePinboardMutation(
    ({ pinboardId, name }: { pinboardId: string; name: string }) =>
      renamePinboard(pinboardId, name)
  );
}

export function useDeletePinboard() {
  return usePinboardMutation((pinboardId: string) => deletePinboard(pinboardId));
}

export function useAddPinboardItem() {
  return usePinboardMutation(
    ({ pinboardId, item }: { pinboardId: string; item: AddPinboardItemRequest }) =>
      addPinboardItem(pinboardId, item)
  );
}

export function useRemovePinboardItem() {
  return usePinboardMutation(
    ({ pinboardId, itemId }: { pinboardId: string; itemId: string }) =>
      removePinboardItem(pinboardId, itemId)
  );
}

export function useExportPinboard() {
  return useMutation({
    mutationFn: ({ pinboardId, request }: {
      pinboardId: string; request: PinboardExportRequest;
    }) => exportPinboard(pinboardId, request),
  });
}
