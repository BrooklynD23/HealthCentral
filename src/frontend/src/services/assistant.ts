/**
 * Assistant API Service
 *
 * React Query hooks for RAG-based assistant functionality:
 * - Chat with grounded responses and citations
 * - Glossary term lookups
 * - Test intent explanations
 *
 * Sprint 5: Full implementation.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from './api';

// Types

export interface Citation {
  source_type: 'user_document' | 'reference';
  doc_id: string | null;
  doc_title: string | null;
  page: number | null;
  text_snippet: string;
  relevance_score?: number;
  authority_tier?: number;
  authority_score?: number;
}

export interface ResponseSegment {
  segment_type: 'report_facts' | 'general_info' | 'uncertainty';
  content: string;
  citations: Citation[];
}

export interface VerificationInfo {
  enabled: boolean;
  total_claims: number;
  verified_claims: number;
  failed_claims: number;
  faithfulness_score: number;
  authority_score: number;
  summary: string;
  issues: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const DOCUMENT_CATEGORIES = ['lab', 'imaging', 'pathology', 'visit_notes'] as const;

export type DocumentCategory = (typeof DOCUMENT_CATEGORIES)[number];

export interface ChatRequest {
  question: string;
  selected_analytes?: string[];
  selected_panel?: string;
  from_date?: string;
  to_date?: string;
  document_category?: DocumentCategory;
  include_references?: boolean;
  enable_verification?: boolean;
  min_faithfulness_score?: number;
  use_memory?: boolean;
  history?: ChatMessage[];
}

export interface ChatResponse {
  segments: ResponseSegment[];
  full_response: string;
  insufficient_context: boolean;
  insufficient_reasons: string[];
  verification: VerificationInfo;
  is_valid: boolean;
  validation_errors: string[];
}

export interface GlossaryResponse {
  term: string;
  definition: string;
  related_terms: string[];
  source: string;
}

export interface TestIntentResponse {
  analyte: string;
  analyte_display_name: string;
  intent_summary: string;
  general_info: string;
  citations: Citation[];
  verification: VerificationInfo;
}

const QUERY_KEY = 'assistant';

// API functions

async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return apiPost<ChatResponse, ChatRequest>('/assistant/chat', request);
}

async function lookupGlossaryTerm(term: string): Promise<GlossaryResponse> {
  return apiGet<GlossaryResponse>(`/assistant/glossary/${encodeURIComponent(term)}`);
}

async function lookupTestIntent(analyte: string): Promise<TestIntentResponse> {
  return apiGet<TestIntentResponse>(`/assistant/test-intent/${encodeURIComponent(analyte)}`);
}

async function getVerificationStatus(): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>('/assistant/verification-status');
}

// React Query hooks

/**
 * Mutation hook for sending chat messages.
 * Returns structured response with citations and verification info.
 */
export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ChatRequest) => sendChatMessage(request),
    onSuccess: () => {
      // Optionally invalidate any chat history queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'history'] });
    },
  });
}

/**
 * Query hook for looking up a glossary term.
 * Caches results to avoid redundant API calls.
 *
 * @param term The medical term to look up
 * @param options.enabled Whether to fetch (default: true when term is provided)
 */
export function useGlossaryLookup(term: string | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [QUERY_KEY, 'glossary', term],
    queryFn: () => (term ? lookupGlossaryTerm(term) : Promise.reject('No term provided')),
    enabled: options?.enabled ?? !!term,
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes (glossary rarely changes)
    retry: false, // Don't retry on 404
  });
}

/**
 * Query hook for looking up test intent/purpose.
 * Caches results to avoid redundant API calls.
 *
 * @param analyte The analyte to look up
 * @param options.enabled Whether to fetch (default: true when analyte is provided)
 */
export function useTestIntentLookup(analyte: string | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [QUERY_KEY, 'test-intent', analyte],
    queryFn: () => (analyte ? lookupTestIntent(analyte) : Promise.reject('No analyte provided')),
    enabled: options?.enabled ?? !!analyte,
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes
    retry: false, // Don't retry on 404
  });
}

/**
 * Query hook for getting verification system status.
 */
export function useVerificationStatus() {
  return useQuery({
    queryKey: [QUERY_KEY, 'verification-status'],
    queryFn: getVerificationStatus,
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
}

/**
 * Mutation hook for glossary lookup (for on-demand lookups).
 * Use this when you want to trigger lookup on user action rather than auto-fetch.
 */
export function useGlossaryMutation() {
  return useMutation({
    mutationFn: (term: string) => lookupGlossaryTerm(term),
  });
}

/**
 * Mutation hook for test intent lookup (for on-demand lookups).
 * Use this when you want to trigger lookup on user action rather than auto-fetch.
 */
export function useTestIntentMutation() {
  return useMutation({
    mutationFn: (analyte: string) => lookupTestIntent(analyte),
  });
}

// Helper functions

/**
 * Format citations for display.
 * Converts Citation objects to a user-friendly format.
 */
export function formatCitation(citation: Citation, index: number): string {
  const parts = [`[${index}]`];

  if (citation.doc_title) {
    parts.push(citation.doc_title);
  } else {
    parts.push(citation.source_type === 'user_document' ? 'Your Document' : 'Reference');
  }

  if (citation.page) {
    parts.push(`(p.${citation.page})`);
  }

  return parts.join(' ');
}

/**
 * Extract citation references from response text.
 * Finds all [cite:N] markers and maps them to citation objects.
 */
export function extractCitationRefs(text: string): number[] {
  const matches = text.match(/\[cite:(\d+)\]/g);
  if (!matches) return [];

  return matches
    .map((match) => {
      const num = match.match(/\d+/);
      return num ? parseInt(num[0], 10) : 0;
    })
    .filter((n) => n > 0);
}

/**
 * Replace citation markers with formatted references.
 * Converts [cite:1] to [1] for cleaner display.
 */
export function formatResponseText(text: string): string {
  return text.replace(/\[cite:(\d+)\]/g, '[$1]');
}
