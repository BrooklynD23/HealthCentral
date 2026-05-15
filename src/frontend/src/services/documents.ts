/**
 * Document API Service
 * 
 * React Query hooks for document management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiDelete, apiUpload, apiGetRaw, apiPost, getApiBaseUrl } from './api';
import type {
  Document,
  DocumentImportResponse,
  DocumentPage,
  DocumentFilters,
  DocumentVerifyResponse,
} from './types';

const QUERY_KEY = 'documents';

/**
 * Build the URL for a page image endpoint (OCR-BOX-001).
 * Uses the same base URL as the API client.
 */
export function getPageImageUrl(documentId: string, pageNumber: number): string {
  const base = getApiBaseUrl().replace(/\/$/, '');
  return `${base}/documents/${documentId}/pages/${pageNumber}/image`;
}

/**
 * Fetch a page image as a Blob using Authorization headers (OCR-BOX-001).
 *
 * Do not rely on credentialed <img> requests (no Authorization header) and
 * do not put tokens into URLs (F-008).
 */
export async function fetchPageImageBlob(
  documentId: string,
  pageNumber: number
): Promise<Blob> {
  const response = await apiGetRaw(
    `/documents/${documentId}/pages/${pageNumber}/image`
  );
  return response.blob();
}

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

async function reprocessDocument(documentId: string): Promise<DocumentImportResponse> {
  return apiPost<DocumentImportResponse>(`/documents/${documentId}/reprocess`);
}

async function verifyDocument(documentId: string): Promise<DocumentVerifyResponse> {
  return apiPost<DocumentVerifyResponse>(`/documents/${documentId}/verify`);
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

export function useReprocessDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reprocessDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: ['observations'] });
    },
  });
}

export function useVerifyDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: verifyDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: ['observations'] });
    },
  });
}
