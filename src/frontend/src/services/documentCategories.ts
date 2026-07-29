/**
 * Document Categories API Service
 *
 * React Query hooks for document classification and entity data.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch } from './api';

export interface DocumentCategoryResponse {
  id: string;
  doc_id: string;
  category: string;
  confidence: number;
  classified_by: string;
}

export interface DocumentEntityResponse {
  id: string;
  doc_id: string;
  category: string;
  entity_type: string;
  entity_value: string;
  confidence: number;
  source_page: number | null;
  // CITE-SRC-001: the entity's region on that page, as a JSON [x0,y0,x1,y1].
  source_bbox_json: string | null;
  char_start: number | null;
  char_end: number | null;
  quote: string | null;
  verified_by_user: boolean | null;
  extraction_version: string | null;
}

export interface EntityVerificationRequest {
  verified: boolean | null;
}

export function setEntityVerification(
  docId: string,
  entityId: string,
  verified: boolean | null
): Promise<DocumentEntityResponse> {
  return apiPatch<DocumentEntityResponse, EntityVerificationRequest>(
    `/documents/${docId}/entities/${entityId}/verification`,
    { verified }
  );
}

export function useDocumentCategory(docId: string) {
  return useQuery({
    queryKey: ['documents', docId, 'category'],
    queryFn: () => apiGet<DocumentCategoryResponse>(`/documents/${docId}/category`),
    enabled: !!docId,
  });
}

export function useDocumentEntities(docId: string) {
  return useQuery({
    queryKey: ['documents', docId, 'entities'],
    queryFn: () => apiGet<DocumentEntityResponse[]>(`/documents/${docId}/entities`),
    enabled: !!docId,
  });
}

export function useSetEntityVerification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      docId,
      entityId,
      verified,
    }: {
      docId: string;
      entityId: string;
      verified: boolean | null;
    }) => setEntityVerification(docId, entityId, verified),
    onSuccess: (_data, { docId }) => {
      queryClient.invalidateQueries({ queryKey: ['documents', docId, 'entities'] });
    },
  });
}
