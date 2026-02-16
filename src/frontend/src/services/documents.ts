/**
 * Document API Service
 * 
 * React Query hooks for document management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiDelete, apiUpload } from './api';
import type { Document, DocumentImportResponse, DocumentPage, DocumentFilters } from './types';

export interface ExternalImportResponse {
  document_id: string;
  source_type: string;
  observation_count: number;
  error_count: number;
  warnings: string[];
}

const QUERY_KEY = 'documents';

// API functions
async function fetchDocuments(filters: DocumentFilters): Promise<Document[]> {
  // profile_id is extracted from auth token by backend, not query params
  const params: Record<string, string> = {};
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

async function importDocument(file: File): Promise<DocumentImportResponse> {
  // profile_id is extracted from auth token by backend
  return apiUpload<DocumentImportResponse>('/documents/import', file);
}

async function deleteDocument(documentId: string): Promise<void> {
  return apiDelete(`/documents/${documentId}`);
}

async function importExternal(
  file: File,
  sourceType: string,
): Promise<ExternalImportResponse> {
  return apiUpload<ExternalImportResponse>(
    '/documents/import/external',
    file,
    { source_type: sourceType },
  );
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
    mutationFn: ({ file }: { file: File; profileId?: string }) =>
      importDocument(file),
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

export function useImportExternal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, sourceType }: { file: File; sourceType: string }) =>
      importExternal(file, sourceType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}
