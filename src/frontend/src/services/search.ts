/** Local cross-record search service (HC-M21). */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';
import type { HighlightType } from './highlights';

export type SearchRecordType = 'document' | 'entity' | 'observation';
export type SearchVerifiedStatus = 'verified' | 'unverified';

export interface SearchResult {
  type: SearchRecordType;
  id: string;
  doc_id: string;
  title: string;
  snippet: string;
  date: string | null;
  verified_status: SearchVerifiedStatus;
  category: string | null;
  highlight_types: HighlightType[];
}

export interface SearchResponse {
  results: SearchResult[];
  count: number;
}

export interface SearchFilters {
  q: string;
  provider?: string;
  date_from?: string;
  date_to?: string;
  category?: string;
  highlight_type?: HighlightType | '';
  limit?: number;
}

function searchParams(filters: SearchFilters): Record<string, string> {
  const params: Record<string, string> = { q: filters.q.trim() };
  if (filters.provider) params.provider = filters.provider;
  if (filters.date_from) params.date_from = filters.date_from;
  if (filters.date_to) params.date_to = filters.date_to;
  if (filters.category) params.category = filters.category;
  if (filters.highlight_type) params.highlight_type = filters.highlight_type;
  if (filters.limit !== undefined) params.limit = String(filters.limit);
  return params;
}

export function useSearch(filters: SearchFilters) {
  const hasQuery = filters.q.trim().length > 0;
  return useQuery({
    queryKey: ['search', filters],
    queryFn: () => apiGet<SearchResponse>('/search/', searchParams(filters)),
    enabled: hasQuery,
  });
}
