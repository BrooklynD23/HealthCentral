/**
 * Search API Service
 *
 * React Query hooks for hybrid search functionality.
 * Sprint 04: DATA-004/005
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';

export interface SearchFilters {
  mode?: 'hybrid' | 'text' | 'semantic';
  limit?: number;
  offset?: number;
  from_date?: string;
  to_date?: string;
  analyte?: string;
  abnormal_only?: boolean;
}

export interface SearchResultItem {
  id: string;
  type: 'observation' | 'chunk';
  title: string;
  score: number;
  snippet: string;
  highlight: string;
  collected_at: string | null;
  analyte: string | null;
  value: number | null;
  unit: string | null;
  explanation: string;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total_count: number;
  query: string;
  mode: string;
}

async function fetchSearchResults(
  query: string,
  filters: SearchFilters = {},
): Promise<SearchResponse> {
  const params: Record<string, string> = { q: query };
  if (filters.mode) params.mode = filters.mode;
  if (filters.limit) params.limit = String(filters.limit);
  if (filters.offset) params.offset = String(filters.offset);
  if (filters.from_date) params.from_date = filters.from_date;
  if (filters.to_date) params.to_date = filters.to_date;
  if (filters.analyte) params.analyte = filters.analyte;
  if (filters.abnormal_only) params.abnormal_only = 'true';

  return apiGet<SearchResponse>('/search', params);
}

async function fetchSuggestions(prefix: string, limit = 10): Promise<string[]> {
  return apiGet<string[]>('/search/suggestions', {
    prefix,
    limit: String(limit),
  });
}

/**
 * Search hook with debounced query.
 * Only fires when query is non-empty.
 */
export function useSearch(query: string, filters: SearchFilters = {}) {
  return useQuery({
    queryKey: ['search', query, filters],
    queryFn: () => fetchSearchResults(query, filters),
    enabled: query.length > 0,
    staleTime: 1000 * 60,
  });
}

/**
 * Autocomplete suggestions hook.
 */
export function useSearchSuggestions(prefix: string) {
  return useQuery({
    queryKey: ['search', 'suggestions', prefix],
    queryFn: () => fetchSuggestions(prefix),
    enabled: prefix.length >= 1,
    staleTime: 1000 * 60 * 5,
  });
}
