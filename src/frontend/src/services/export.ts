/**
 * Export API Service
 *
 * React Query hooks for export functionality:
 * - CSV/JSON data export
 * - Doctor summary generation
 * - Discussion questions generation
 *
 * Sprint 4: Full implementation.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from './api';

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
  category: 'trend' | 'abnormal' | 'clarification';
  question: string;
  context: string;
  related_analytes: string[];
}

export interface ExportFilters {
  analytes?: string[];
  from_date?: string;
  to_date?: string;
}

const QUERY_KEY = 'export';

// API functions
async function exportCSV(filters?: ExportFilters): Promise<string> {
  const params: Record<string, string> = {};
  if (filters?.analytes?.length) {
    params.analytes = filters.analytes.join(',');
  }
  if (filters?.from_date) params.from_date = filters.from_date;
  if (filters?.to_date) params.to_date = filters.to_date;

  return apiGet<string>('/export/csv', params);
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

async function downloadSummary(summaryId: string): Promise<string> {
  return apiGet<string>(`/export/doctor-summary/${summaryId}/download`);
}

async function generateQuestions(filters?: ExportFilters): Promise<QuestionItem[]> {
  const params: Record<string, string> = {};
  if (filters?.from_date) params.from_date = filters.from_date;
  if (filters?.to_date) params.to_date = filters.to_date;

  return apiPost<QuestionItem[]>('/export/questions');
}

// React Query hooks

/**
 * Mutation hook for exporting CSV data.
 * Call mutate() to trigger export.
 */
export function useExportCSV() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => exportCSV(filters),
    onSuccess: (csvContent) => {
      // Trigger file download
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `health_data_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}

/**
 * Mutation hook for exporting JSON data.
 * Call mutate() to trigger export.
 */
export function useExportJSON() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => exportJSON(filters),
    onSuccess: (jsonContent) => {
      // Trigger file download
      const blob = new Blob([jsonContent], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `health_data_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
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
 */
export function useDownloadSummary() {
  return useMutation({
    mutationFn: (summaryId: string) => downloadSummary(summaryId),
    onSuccess: (textContent, summaryId) => {
      // Trigger file download
      const blob = new Blob([textContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `health_summary_${summaryId.substring(0, 8)}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}

/**
 * Mutation hook for generating discussion questions.
 */
export function useGenerateQuestions() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => generateQuestions(filters),
  });
}
