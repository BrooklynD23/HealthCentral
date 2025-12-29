/**
 * Document API Service
 * 
 * React Query hooks for document management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiDelete, apiUpload } from './api';
import type { Document, DocumentImportResponse, DocumentPage, DocumentFilters } from './types';

const QUERY_KEY = 'documents';

// API functions
async function fetchDocuments(filters: DocumentFilters): Promise<Document[]> {
  const params: Record<string, string> = {
    profile_id: filters.profile_id,
  };
  if (filters.status) params.status = filters.status;
  if (filters.doc_type) params.doc_type = filters.doc_type;
  
  return apiGet<Document[]>('/documents/', params);
}

async function fetchDocument(documentId: string): Promise<Document> {
  return apiGet<Document>(`/documents/${documentId}`);
}

async function fetchDocumentPages(documentId: string): Promise<DocumentPage[]> {
  return apiGet<DocumentPage[]>(`/documents/${documentId}/pages`);
}

async function importDocument(
  file: File,
  profileId: string
): Promise<DocumentImportResponse> {
  return apiUpload<DocumentImportResponse>('/documents/import', file, {
    profile_id: profileId,
  });
}

async function deleteDocument(documentId: string): Promise<void> {
  return apiDelete(`/documents/${documentId}`);
}

// React Query hooks
export function useDocuments(filters: DocumentFilters) {
  return useQuery({
    queryKey: [QUERY_KEY, filters],
    queryFn: () => fetchDocuments(filters),
    enabled: !!filters.profile_id,
  });
}

export function useDocument(documentId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, documentId],
    queryFn: () => fetchDocument(documentId!),
    enabled: !!documentId,
  });
}

export function useDocumentPages(documentId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, documentId, 'pages'],
    queryFn: () => fetchDocumentPages(documentId!),
    enabled: !!documentId,
  });
}

export function useImportDocument() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ file, profileId }: { file: File; profileId: string }) =>
      importDocument(file, profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}
