/**
 * Notifications API Service
 *
 * React Query hooks for notification settings/history, scheduler status,
 * and test notification actions.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch, apiPost } from './api';
import type {
  NotificationSettings,
  NotificationSettingsUpdate,
  NotificationHistoryResponse,
  NotificationSchedulerStatus,
  TestNotificationRequest,
  TestNotificationResponse,
  ReminderInteractionType,
} from './types';

const QUERY_KEY = 'notifications';

export interface NotificationHistoryFilters {
  medicationId?: string;
  fromDate?: string;
  toDate?: string;
  limit?: number;
  offset?: number;
}

function toStartOfDayFilter(date: string): string {
  return `${date}T00:00:00`;
}

function toEndOfDayFilter(date: string): string {
  return `${date}T23:59:59`;
}

async function fetchNotificationSettings(
  medicationId: string
): Promise<NotificationSettings> {
  return apiGet<NotificationSettings>(`/notifications/settings/${medicationId}`);
}

async function patchNotificationSettings(
  medicationId: string,
  data: NotificationSettingsUpdate
): Promise<NotificationSettings> {
  return apiPatch<NotificationSettings, NotificationSettingsUpdate>(
    `/notifications/settings/${medicationId}`,
    data
  );
}

async function fetchNotificationHistory(
  filters: NotificationHistoryFilters
): Promise<NotificationHistoryResponse> {
  const params: Record<string, string> = {
    limit: String(filters.limit ?? 20),
    offset: String(filters.offset ?? 0),
  };

  if (filters.medicationId) params.medication_id = filters.medicationId;
  if (filters.fromDate) params.from_date = toStartOfDayFilter(filters.fromDate);
  if (filters.toDate) params.to_date = toEndOfDayFilter(filters.toDate);

  return apiGet<NotificationHistoryResponse>('/notifications/history', params);
}

async function fetchSchedulerStatus(): Promise<NotificationSchedulerStatus> {
  return apiGet<NotificationSchedulerStatus>('/notifications/scheduler/status');
}

async function sendTestNotification(
  data?: TestNotificationRequest
): Promise<TestNotificationResponse> {
  return apiPost<TestNotificationResponse, TestNotificationRequest | undefined>(
    '/notifications/test',
    data
  );
}

async function sendMedicationTestNotification(
  medicationId: string
): Promise<TestNotificationResponse> {
  return apiPost<TestNotificationResponse>(`/notifications/test/${medicationId}`);
}

async function recordReminderInteraction(
  reminderId: string,
  interactionType: ReminderInteractionType,
  snoozeMinutes?: number
): Promise<void> {
  const params = new URLSearchParams({ interaction_type: interactionType });
  if (interactionType === 'snoozed' && snoozeMinutes) {
    params.set('snooze_minutes', String(snoozeMinutes));
  }
  return apiPost<void>(`/notifications/${reminderId}/interaction?${params.toString()}`);
}

// React Query hooks

export function useNotificationSettings(medicationId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, 'settings', medicationId],
    queryFn: () => fetchNotificationSettings(medicationId!),
    enabled: !!medicationId,
    staleTime: 30_000,
  });
}

export function useUpdateNotificationSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      medicationId,
      data,
    }: {
      medicationId: string;
      data: NotificationSettingsUpdate;
    }) => patchNotificationSettings(medicationId, data),
    onSuccess: (_, { medicationId }) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'settings', medicationId] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'history'] });
    },
  });
}

export function useNotificationHistory(
  filters: NotificationHistoryFilters,
  enabled = true
) {
  return useQuery({
    queryKey: [QUERY_KEY, 'history', filters],
    queryFn: () => fetchNotificationHistory(filters),
    enabled,
    staleTime: 15_000,
  });
}

export function useNotificationSchedulerStatus(enabled = true) {
  return useQuery({
    queryKey: [QUERY_KEY, 'scheduler-status'],
    queryFn: fetchSchedulerStatus,
    enabled,
    refetchInterval: enabled ? 60_000 : false,
    staleTime: 30_000,
  });
}

export function useSendTestNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data?: TestNotificationRequest) => sendTestNotification(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'history'] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'scheduler-status'] });
    },
  });
}

export function useSendMedicationTestNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (medicationId: string) => sendMedicationTestNotification(medicationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'history'] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'scheduler-status'] });
    },
  });
}

export function useRecordReminderInteraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      reminderId,
      interactionType,
      snoozeMinutes,
    }: {
      reminderId: string;
      interactionType: ReminderInteractionType;
      snoozeMinutes?: number;
    }) => recordReminderInteraction(reminderId, interactionType, snoozeMinutes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'history'] });
    },
  });
}
