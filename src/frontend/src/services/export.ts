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

export type ExportFormat = 'text' | 'html' | 'pdf';

export interface SummaryTemplateOptions {
  brandName?: string;
  brandTagline?: string;
  accentColor?: string;
  includeOverview?: boolean;
  includeAbnormal?: boolean;
  includeTrends?: boolean;
  includeQuestions?: boolean;
  includeKeyFindings?: boolean;
}

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
  format: ExportFormat = 'text',
  includeCharts: boolean = false,
  templateOptions?: SummaryTemplateOptions,
): Promise<{ blob: Blob; contentType: string; extension: string }> {
  const params: Record<string, string> = { format };
  if (includeCharts) params.include_charts = 'true';
  if (templateOptions?.brandName) params.brand_name = templateOptions.brandName;
  if (templateOptions?.brandTagline) params.brand_tagline = templateOptions.brandTagline;
  if (templateOptions?.accentColor) params.accent_color = templateOptions.accentColor;
  if (templateOptions?.includeOverview !== undefined) {
    params.include_overview = String(templateOptions.includeOverview);
  }
  if (templateOptions?.includeAbnormal !== undefined) {
    params.include_abnormal = String(templateOptions.includeAbnormal);
  }
  if (templateOptions?.includeTrends !== undefined) {
    params.include_trends = String(templateOptions.includeTrends);
  }
  if (templateOptions?.includeQuestions !== undefined) {
    params.include_questions = String(templateOptions.includeQuestions);
  }
  if (templateOptions?.includeKeyFindings !== undefined) {
    params.include_key_findings = String(templateOptions.includeKeyFindings);
  }

  const response = await apiGetRaw(
    `/export/doctor-summary/${summaryId}/download`,
    params,
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
    mutationFn: ({ summaryId, format, includeCharts, templateOptions }: {
      summaryId: string;
      format: ExportFormat;
      includeCharts?: boolean;
      templateOptions?: SummaryTemplateOptions;
    }) => downloadSummary(summaryId, format, includeCharts, templateOptions),
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

// --- Sprint 04: New Export Functions ---

async function exportExcel(filters?: ExportFilters): Promise<Blob> {
  const params: Record<string, string> = {};
  if (filters?.analytes?.length) params.analytes = filters.analytes.join(',');
  if (filters?.from_date) params.from_date = filters.from_date;
  if (filters?.to_date) params.to_date = filters.to_date;

  const response = await apiGetRaw('/export/excel', params);
  return response.blob();
}

async function exportFHIR(filters?: ExportFilters): Promise<string> {
  const params: Record<string, string> = {};
  if (filters?.analytes?.length) params.analytes = filters.analytes.join(',');
  if (filters?.from_date) params.from_date = filters.from_date;
  if (filters?.to_date) params.to_date = filters.to_date;

  const response = await apiGetRaw('/export/fhir', params);
  return response.text();
}

/**
 * Mutation hook for exporting Excel workbook.
 */
export function useExportExcel() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => exportExcel(filters),
    onSuccess: (blob) => {
      triggerDownload(blob, `health_data_${new Date().toISOString().split('T')[0]}.xlsx`);
    },
  });
}

/**
 * Mutation hook for exporting FHIR R4 Bundle.
 */
export function useExportFHIR() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => exportFHIR(filters),
    onSuccess: (content) => {
      const blob = new Blob([content], { type: 'application/fhir+json' });
      triggerDownload(blob, `health_data_${new Date().toISOString().split('T')[0]}_fhir.json`);
    },
  });
}
