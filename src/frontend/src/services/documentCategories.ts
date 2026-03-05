/**
 * Document Categories API Service
 *
 * React Query hooks for document classification and entity data.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';

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
