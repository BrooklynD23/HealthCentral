/**
 * Export API Service
 *
 * React Query hooks for export functionality:
 * - CSV/JSON data export
 * - Doctor summary generation (text/html/pdf)
 * - Discussion questions generation
 *
 * Sprint 4 + Phase 3C: Format-aware download with binary support.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiGetRaw, apiPost } from './api';

// Types
export interface SummaryRequest {
  from_date?: string;
  to_date?: string;
  include_all_values?: boolean;
  include_trends?: boolean;
  include_questions?: boolean;
  format?: 'text' | 'pdf' | 'html';
}

export interface SummaryResponse {
  summary_id: string;
  profile_id: string;
  generated_at: string;
  format: string;
  key_findings: string[];
  abnormal_count: number;
  date_range: string;
}

export interface QuestionItem {
  category:
    | 'trend'
    | 'abnormal'
    | 'clarification'
    | 'follow_up'
    | 'medication_change'
    | 'test_ordered'
    | 'referral';
  question: string;
  context: string;
  related_analytes: string[];
  // Provenance (HC-M17)
  source_kind?: 'observation' | 'trend' | 'care_task' | 'entity' | null;
  source_id?: string | null;
  source_quote?: string | null;
}

// Visit-prep packet (HC-M18)
export interface VisitPrepRequest {
  reason_for_visit?: string;
  from_date?: string;
  to_date?: string;
  include_medications?: boolean;
  include_labs?: boolean;
  include_visits?: boolean;
  include_tasks?: boolean;
  include_questions?: boolean;
  selected_doc_ids?: string[];
  confirm: boolean;
}

export interface VisitPrepResponse {
  packet_id: string;
  profile_id: string;
  generated_at: string;
  section_titles: string[];
  markdown: string;
  redaction_count: number;
}

export type VisitPrepFormat = 'markdown' | 'html' | 'pdf';

export interface ExportFilters {
  analytes?: string[];
  from_date?: string;
  to_date?: string;
}

export type ExportFormat = 'text' | 'html' | 'pdf';

const QUERY_KEY = 'export';

// Helper: trigger file download from blob
function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// API functions
async function exportCSV(filters?: ExportFilters): Promise<string> {
  const params: Record<string, string> = {};
  if (filters?.analytes?.length) {
    params.analytes = filters.analytes.join(',');
  }
  if (filters?.from_date) params.from_date = filters.from_date;
  if (filters?.to_date) params.to_date = filters.to_date;

  const response = await apiGetRaw('/export/csv', params);
  return response.text();
}

async function exportJSON(filters?: ExportFilters): Promise<string> {
  const params: Record<string, string> = {};
  if (filters?.analytes?.length) {
    params.analytes = filters.analytes.join(',');
  }
  if (filters?.from_date) params.from_date = filters.from_date;
  if (filters?.to_date) params.to_date = filters.to_date;

  return apiGet<string>('/export/json', params);
}

async function generateSummary(request: SummaryRequest): Promise<SummaryResponse> {
  return apiPost<SummaryResponse, SummaryRequest>('/export/doctor-summary', request);
}

async function downloadSummary(
  summaryId: string,
  format: ExportFormat = 'text'
): Promise<{ blob: Blob; contentType: string; extension: string }> {
  const response = await apiGetRaw(
    `/export/doctor-summary/${summaryId}/download`,
    { format }
  );

  const contentType = response.headers.get('Content-Type') || 'text/plain';
  const blob = await response.blob();

  let extension = '.txt';
  if (contentType.includes('html')) {
    extension = '.html';
  } else if (contentType.includes('pdf')) {
    extension = '.pdf';
  }

  return { blob, contentType, extension };
}

/**
 * Generate a visit-prep packet (HC-M18). The backend requires an explicit
 * confirm: true and redacts all packet content before it can be downloaded.
 */
export async function generateVisitPrep(
  request: VisitPrepRequest
): Promise<VisitPrepResponse> {
  return apiPost<VisitPrepResponse, VisitPrepRequest>('/export/visit-prep', request);
}

/**
 * Download a previously generated visit-prep packet.
 */
export async function downloadVisitPrep(
  packetId: string,
  format: VisitPrepFormat = 'markdown'
): Promise<{ blob: Blob; contentType: string; extension: string }> {
  const response = await apiGetRaw(`/export/visit-prep/${packetId}/download`, {
    format,
  });

  const contentType = response.headers.get('Content-Type') || 'text/markdown';
  const blob = await response.blob();

  let extension = '.md';
  if (contentType.includes('html')) {
    extension = '.html';
  } else if (contentType.includes('pdf')) {
    extension = '.pdf';
  }

  return { blob, contentType, extension };
}

async function generateQuestions(filters?: ExportFilters): Promise<QuestionItem[]> {
  const queryParams = new URLSearchParams();
  if (filters?.from_date) queryParams.set('from_date', filters.from_date);
  if (filters?.to_date) queryParams.set('to_date', filters.to_date);

  const queryString = queryParams.toString();
  const url = queryString ? `/export/questions?${queryString}` : '/export/questions';
  return apiPost<QuestionItem[]>(url);
}

// React Query hooks

/**
 * Mutation hook for exporting CSV data.
 */
export function useExportCSV() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => exportCSV(filters),
    onSuccess: (csvContent) => {
      const blob = new Blob([csvContent], { type: 'text/csv' });
      triggerDownload(blob, `health_data_${new Date().toISOString().split('T')[0]}.csv`);
    },
  });
}

/**
 * Mutation hook for exporting JSON data.
 */
export function useExportJSON() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => exportJSON(filters),
    onSuccess: (jsonContent) => {
      const content = typeof jsonContent === 'string' ? jsonContent : JSON.stringify(jsonContent, null, 2);
      const blob = new Blob([content], { type: 'application/json' });
      triggerDownload(blob, `health_data_${new Date().toISOString().split('T')[0]}.json`);
    },
  });
}

/**
 * Mutation hook for generating doctor summary.
 */
export function useGenerateSummary() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: SummaryRequest) => generateSummary(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'summary'] });
    },
  });
}

/**
 * Mutation hook for downloading a generated summary.
 * Accepts { summaryId, format } to support text/html/pdf downloads.
 */
export function useDownloadSummary() {
  return useMutation({
    mutationFn: ({ summaryId, format }: { summaryId: string; format: ExportFormat }) =>
      downloadSummary(summaryId, format),
    onSuccess: ({ blob, extension }, { summaryId }) => {
      triggerDownload(blob, `health_summary_${summaryId.substring(0, 8)}${extension}`);
    },
  });
}

/**
 * Mutation hook for generating discussion questions.
 */
export function useGenerateQuestions() {
  return useMutation({
    mutationFn: (filters: ExportFilters | void) => generateQuestions(filters || undefined),
  });
}

/**
 * Mutation hook for generating a visit-prep packet (HC-M18).
 */
export function useGenerateVisitPrep() {
  return useMutation({
    mutationFn: (request: VisitPrepRequest) => generateVisitPrep(request),
  });
}

/**
 * Mutation hook for downloading a generated visit-prep packet.
 */
export function useDownloadVisitPrep() {
  return useMutation({
    mutationFn: ({ packetId, format }: { packetId: string; format: VisitPrepFormat }) =>
      downloadVisitPrep(packetId, format),
    onSuccess: ({ blob, extension }, { packetId }) => {
      triggerDownload(blob, `visit_prep_${packetId.substring(0, 8)}${extension}`);
    },
  });
}
