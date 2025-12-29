/**
 * Observation API Service
 * 
 * React Query hooks for lab values and trends.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from './api';
import type { Observation, ObservationVerify, TrendData, Panel, ObservationFilters } from './types';

const QUERY_KEY = 'observations';

// API functions
async function fetchObservations(filters: ObservationFilters): Promise<Observation[]> {
  const params: Record<string, string> = {
    profile_id: filters.profile_id,
  };
  if (filters.analyte) params.analyte = filters.analyte;
  if (filters.from_date) params.from_date = filters.from_date;
  if (filters.to_date) params.to_date = filters.to_date;
  if (filters.abnormal_only) params.abnormal_only = 'true';
  if (filters.needs_verification) params.needs_verification = 'true';
  
  return apiGet<Observation[]>('/observations/', params);
}

async function fetchObservation(observationId: string): Promise<Observation> {
  return apiGet<Observation>(`/observations/${observationId}`);
}

async function verifyObservation(
  observationId: string,
  data: ObservationVerify
): Promise<Observation> {
  return apiPost<Observation, ObservationVerify>(
    `/observations/${observationId}/verify`,
    data
  );
}

async function fetchTrend(
  analyte: string,
  profileId: string,
  fromDate?: string,
  toDate?: string
): Promise<TrendData> {
  const params: Record<string, string> = {
    profile_id: profileId,
  };
  if (fromDate) params.from_date = fromDate;
  if (toDate) params.to_date = toDate;
  
  return apiGet<TrendData>(`/observations/trends/${analyte}`, params);
}

async function fetchPanel(
  panelId: string,
  profileId: string,
  collectionDate?: string
): Promise<Panel> {
  const params: Record<string, string> = {
    profile_id: profileId,
  };
  if (collectionDate) params.collection_date = collectionDate;
  
  return apiGet<Panel>(`/observations/panels/${panelId}`, params);
}

// React Query hooks
export function useObservations(filters: ObservationFilters) {
  return useQuery({
    queryKey: [QUERY_KEY, filters],
    queryFn: () => fetchObservations(filters),
    enabled: !!filters.profile_id,
  });
}

export function useObservation(observationId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, observationId],
    queryFn: () => fetchObservation(observationId!),
    enabled: !!observationId,
  });
}

export function useVerifyObservation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({
      observationId,
      data,
    }: {
      observationId: string;
      data: ObservationVerify;
    }) => verifyObservation(observationId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useTrend(
  analyte: string | undefined,
  profileId: string | undefined,
  fromDate?: string,
  toDate?: string
) {
  return useQuery({
    queryKey: [QUERY_KEY, 'trends', analyte, profileId, fromDate, toDate],
    queryFn: () => fetchTrend(analyte!, profileId!, fromDate, toDate),
    enabled: !!analyte && !!profileId,
  });
}

export function usePanel(
  panelId: string | undefined,
  profileId: string | undefined,
  collectionDate?: string
) {
  return useQuery({
    queryKey: [QUERY_KEY, 'panels', panelId, profileId, collectionDate],
    queryFn: () => fetchPanel(panelId!, profileId!, collectionDate),
    enabled: !!panelId && !!profileId,
  });
}

// Hook to get unique analytes for a profile
export function useAnalyteList(profileId: string | undefined) {
  const { data: observations } = useObservations({
    profile_id: profileId || '',
  });
  
  const analytes = observations
    ? [...new Set(observations.map((o) => o.analyte_canonical))].sort()
    : [];
  
  return analytes;
}
