/**
 * Medication API Service
 *
 * React Query hooks for medication management, dose logging,
 * and adherence tracking.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from './api';
import type {
  Medication,
  MedicationCreate,
  MedicationUpdate,
  MedicationSchedule,
  ScheduleCreate,
  ScheduleUpdate,
  DoseLog,
  DoseResponse,
  DoseLogResponse,
  AdherenceStats,
  LearnPatternsResponse,
} from './types';

const QUERY_KEY = 'medications';

// API functions

async function fetchMedications(activeOnly = true): Promise<Medication[]> {
  const params: Record<string, string> = {};
  if (!activeOnly) params.active_only = 'false';
  return apiGet<Medication[]>('/medications/', params);
}

async function fetchMedication(medicationId: string): Promise<Medication> {
  return apiGet<Medication>(`/medications/${medicationId}`);
}

async function createMedication(data: MedicationCreate): Promise<Medication> {
  return apiPost<Medication, MedicationCreate>('/medications/', data);
}

async function updateMedication(
  medicationId: string,
  data: MedicationUpdate
): Promise<Medication> {
  // Backend exposes PATCH /medications/{id} (partial update).
  return apiPatch<Medication, MedicationUpdate>(`/medications/${medicationId}`, data);
}

async function deleteMedication(
  medicationId: string,
  hardDelete = false
): Promise<void> {
  const params = hardDelete ? '?hard_delete=true' : '';
  return apiDelete(`/medications/${medicationId}${params}`);
}

async function fetchSchedules(medicationId: string): Promise<MedicationSchedule[]> {
  return apiGet<MedicationSchedule[]>(`/medications/${medicationId}/schedules`);
}

async function createSchedule(
  medicationId: string,
  data: ScheduleCreate
): Promise<MedicationSchedule> {
  return apiPost<MedicationSchedule, ScheduleCreate>(
    `/medications/${medicationId}/schedules`,
    data
  );
}

async function updateSchedule(
  medicationId: string,
  scheduleId: string,
  data: ScheduleUpdate
): Promise<MedicationSchedule> {
  return apiPut<MedicationSchedule, ScheduleUpdate>(
    `/medications/${medicationId}/schedules/${scheduleId}`,
    data
  );
}

async function deleteSchedule(
  medicationId: string,
  scheduleId: string
): Promise<void> {
  return apiDelete(`/medications/${medicationId}/schedules/${scheduleId}`);
}

async function logDose(
  medicationId: string,
  data: DoseLog,
  scheduleId?: string
): Promise<DoseLogResponse> {
  const params = scheduleId ? `?schedule_id=${scheduleId}` : '';
  return apiPost<DoseLogResponse, DoseLog>(
    `/medications/${medicationId}/doses${params}`,
    data
  );
}

async function fetchDoses(
  medicationId: string,
  fromDate?: string,
  toDate?: string,
  limit = 30
): Promise<DoseResponse[]> {
  const params: Record<string, string> = { limit: String(limit) };
  if (fromDate) params.from_date = fromDate;
  if (toDate) params.to_date = toDate;
  return apiGet<DoseResponse[]>(`/medications/${medicationId}/doses`, params);
}

async function fetchAdherenceStats(medicationId: string): Promise<AdherenceStats> {
  return apiGet<AdherenceStats>(`/medications/${medicationId}/stats`);
}

async function learnPatterns(
  medicationId: string,
  scheduleId?: string
): Promise<LearnPatternsResponse> {
  const params = scheduleId ? `?schedule_id=${scheduleId}` : '';
  return apiPost<LearnPatternsResponse>(
    `/medications/${medicationId}/learn-patterns${params}`
  );
}

// React Query hooks

export function useMedications(activeOnly = true) {
  return useQuery({
    queryKey: [QUERY_KEY, { activeOnly }],
    queryFn: () => fetchMedications(activeOnly),
  });
}

export function useMedication(medicationId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, medicationId],
    queryFn: () => fetchMedication(medicationId!),
    enabled: !!medicationId,
  });
}

export function useCreateMedication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: MedicationCreate) => createMedication(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useUpdateMedication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      data,
    }: {
      medicationId: string;
      data: MedicationUpdate;
    }) => updateMedication(medicationId, data),
    onSuccess: (_, { medicationId }) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, medicationId] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useDeleteMedication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      hardDelete,
    }: {
      medicationId: string;
      hardDelete?: boolean;
    }) => deleteMedication(medicationId, hardDelete),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useSchedules(medicationId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, medicationId, 'schedules'],
    queryFn: () => fetchSchedules(medicationId!),
    enabled: !!medicationId,
  });
}

export function useCreateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      data,
    }: {
      medicationId: string;
      data: ScheduleCreate;
    }) => createSchedule(medicationId, data),
    onSuccess: (_, { medicationId }) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY, medicationId, 'schedules'],
      });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, medicationId] });
    },
  });
}

export function useUpdateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      scheduleId,
      data,
    }: {
      medicationId: string;
      scheduleId: string;
      data: ScheduleUpdate;
    }) => updateSchedule(medicationId, scheduleId, data),
    onSuccess: (_, { medicationId }) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY, medicationId, 'schedules'],
      });
    },
  });
}

export function useDeleteSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      scheduleId,
    }: {
      medicationId: string;
      scheduleId: string;
    }) => deleteSchedule(medicationId, scheduleId),
    onSuccess: (_, { medicationId }) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY, medicationId, 'schedules'],
      });
    },
  });
}

export function useLogDose() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      data,
      scheduleId,
    }: {
      medicationId: string;
      data: DoseLog;
      scheduleId?: string;
    }) => logDose(medicationId, data, scheduleId),
    onSuccess: (_, { medicationId }) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY, medicationId, 'doses'],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY, medicationId, 'stats'],
      });
      queryClient.invalidateQueries({
        queryKey: ['gamification', 'badges'],
      });
    },
  });
}

export function useDoses(
  medicationId: string | undefined,
  fromDate?: string,
  toDate?: string,
  limit = 30
) {
  return useQuery({
    queryKey: [QUERY_KEY, medicationId, 'doses', fromDate, toDate, limit],
    queryFn: () => fetchDoses(medicationId!, fromDate, toDate, limit),
    enabled: !!medicationId,
  });
}

export function useAdherenceStats(medicationId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, medicationId, 'stats'],
    queryFn: () => fetchAdherenceStats(medicationId!),
    enabled: !!medicationId,
  });
}

export function useLearnPatterns() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      scheduleId,
    }: {
      medicationId: string;
      scheduleId?: string;
    }) => learnPatterns(medicationId, scheduleId),
    onSuccess: (_, { medicationId }) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY, medicationId],
      });
    },
  });
}
