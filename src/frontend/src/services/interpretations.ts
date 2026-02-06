/**
 * Interpretation API Service
 *
 * React Query hooks for lab result interpretations and biomarker knowledge.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from './api';
import type {
  InterpretationResponse,
  PanelInterpretationResponse,
  BiomarkerKnowledge,
  BatchInterpretResponse,
} from './types';

const QUERY_KEY = 'interpretations';

// API functions

async function generateInterpretation(
  observationId: string,
  forceRegenerate = false
): Promise<InterpretationResponse> {
  const params: Record<string, string> = {};
  if (forceRegenerate) params.force_regenerate = 'true';
  return apiPost<InterpretationResponse>(
    `/interpretations/observations/${observationId}/interpret?${new URLSearchParams(params)}`
  );
}

async function fetchInterpretation(
  observationId: string
): Promise<InterpretationResponse> {
  return apiGet<InterpretationResponse>(
    `/interpretations/observations/${observationId}/interpretation`
  );
}

async function generatePanelInterpretation(
  panelName: string,
  collectedAt: string,
  forceRegenerate = false
): Promise<PanelInterpretationResponse> {
  const params: Record<string, string> = {
    collected_at: collectedAt,
  };
  if (forceRegenerate) params.force_regenerate = 'true';
  return apiPost<PanelInterpretationResponse>(
    `/interpretations/panels/${panelName}/interpret?${new URLSearchParams(params)}`
  );
}

async function fetchRecentInterpretations(
  limit = 10
): Promise<InterpretationResponse[]> {
  return apiGet<InterpretationResponse[]>('/interpretations/recent', {
    limit: String(limit),
  });
}

async function fetchBiomarkerKnowledge(
  analyteCanonical: string
): Promise<BiomarkerKnowledge> {
  return apiGet<BiomarkerKnowledge>(
    `/interpretations/knowledge/biomarker/${analyteCanonical}`
  );
}

async function batchGenerateInterpretations(
  observationIds: string[],
  forceRegenerate = false
): Promise<BatchInterpretResponse> {
  return apiPost<BatchInterpretResponse, { observation_ids: string[]; force_regenerate: boolean }>(
    '/interpretations/batch',
    { observation_ids: observationIds, force_regenerate: forceRegenerate }
  );
}

// React Query hooks

export function useInterpretation(observationId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, observationId],
    queryFn: () => fetchInterpretation(observationId!),
    enabled: !!observationId,
    retry: false,
  });
}

export function useGenerateInterpretation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      observationId,
      forceRegenerate,
    }: {
      observationId: string;
      forceRegenerate?: boolean;
    }) => generateInterpretation(observationId, forceRegenerate),
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEY, data.observation_id], data);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'recent'] });
    },
  });
}

export function useGeneratePanelInterpretation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      panelName,
      collectedAt,
      forceRegenerate,
    }: {
      panelName: string;
      collectedAt: string;
      forceRegenerate?: boolean;
    }) => generatePanelInterpretation(panelName, collectedAt, forceRegenerate),
    onSuccess: (data) => {
      queryClient.setQueryData(
        [QUERY_KEY, 'panel', data.panel_name, data.collected_at],
        data
      );
    },
  });
}

export function useRecentInterpretations(limit = 10) {
  return useQuery({
    queryKey: [QUERY_KEY, 'recent', limit],
    queryFn: () => fetchRecentInterpretations(limit),
  });
}

export function useBiomarkerKnowledge(analyteCanonical: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, 'knowledge', analyteCanonical],
    queryFn: () => fetchBiomarkerKnowledge(analyteCanonical!),
    enabled: !!analyteCanonical,
  });
}

export function useBatchGenerateInterpretations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      observationIds,
      forceRegenerate,
    }: {
      observationIds: string[];
      forceRegenerate?: boolean;
    }) => batchGenerateInterpretations(observationIds, forceRegenerate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}
