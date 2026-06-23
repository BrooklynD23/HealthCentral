/**
 * Feedback API service — RL-FEED-001/002
 *
 * React Query hooks for submitting turn-level feedback and exporting
 * DPO/GRPO preference datasets.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiPost, apiGet } from './api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export const FEEDBACK_TAGS = [
  'inaccurate',
  'too_technical',
  'missing_context',
  'unsafe',
  'too_long',
  'too_short',
  'off_topic',
  'helpful',
] as const;

export type FeedbackTag = (typeof FEEDBACK_TAGS)[number];

export interface FeedbackRequest {
  session_id: string;
  rating: 1 | -1;
  correction_text?: string;
  feedback_tags?: FeedbackTag[];
  prompt_snapshot?: string;
  response_text?: string;
  model_name?: string;
  provider?: string;
}

export interface FeedbackResponse {
  turn_id: string;
  rating: number;
  correction_text: string | null;
  feedback_tags: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackStatsResponse {
  total_feedback: number;
  positive_count: number;
  negative_count: number;
  correction_count: number;
  tag_distribution: Record<string, number>;
  model_distribution: Record<string, number>;
  provider_distribution: Record<string, number>;
}

export interface ExportRequest {
  confirmed: boolean;
  output_dir?: string;
}

export interface ExportResponse {
  dpo_pairs_count: number;
  sft_positives_count: number;
  grpo_rewards_count: number;
  dpo_path: string;
  sft_path: string;
  grpo_path: string;
  metadata_path: string;
  redacted_fields: number;
}

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const FEEDBACK_STATS_KEY = ['feedback', 'stats'] as const;

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Submit or update feedback for a specific assistant turn.
 * Upsert: calling again with the same turn_id overwrites the previous rating.
 */
export function useSubmitFeedback() {
  const queryClient = useQueryClient();

  return useMutation<FeedbackResponse, Error, { turnId: string; data: FeedbackRequest }>({
    mutationFn: ({ turnId, data }) =>
      apiPost<FeedbackResponse>(`/feedback/turns/${turnId}`, data),
    onSuccess: () => {
      // Invalidate stats so the Settings page reflects the new count
      queryClient.invalidateQueries({ queryKey: FEEDBACK_STATS_KEY });
    },
  });
}

/**
 * Aggregate feedback stats for the authenticated profile.
 */
export function useFeedbackStats() {
  return useQuery<FeedbackStatsResponse>({
    queryKey: FEEDBACK_STATS_KEY,
    queryFn: () => apiGet<FeedbackStatsResponse>('/feedback/stats'),
    staleTime: 30_000,
  });
}

/**
 * Export DPO/GRPO/SFT dataset files to local storage.
 * Requires confirmed=true — call this only after the user confirms the dialog.
 */
export function useExportDataset() {
  return useMutation<ExportResponse, Error, ExportRequest>({
    mutationFn: (data) => apiPost<ExportResponse>('/feedback/export', data),
  });
}
