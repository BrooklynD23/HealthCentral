/**
 * Backup & restore service (BKUP-UX-001).
 *
 * Backups are the full-fidelity, restorable copy of a profile — distinct from
 * the export routes, which produce filtered sharing formats. This is what a
 * patient should take before deleting a profile, or before losing a device.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiGetRaw, apiPost, apiPut } from './api';

const QUERY_KEY = 'backups';

export const BACKUP_RESTORE_CONFIRMATION = 'RESTORE MY DATA';

export type BackupFrequency = 'off' | 'daily' | 'weekly';

export interface BackupSummary {
  backup_id: string;
  created_at: string;
  file_count: number;
  size_bytes: number;
  verified?: boolean | null;
}

export interface BackupListResponse {
  backups: BackupSummary[];
  backup_directory: string;
  last_backup_at: string | null;
}

export interface CreateBackupResponse {
  backup_id: string;
  file_count: number;
  method: string;
  created_at: string;
}

export interface VerifyBackupResponse {
  backup_id: string;
  valid: boolean;
  files_checked: number;
  errors: string[];
}

export interface RestoreRequest {
  password: string;
  confirmation_phrase: string;
}

export interface RestoreResponse {
  files_restored: number;
  safety_copy_count: number;
}

export interface BackupSchedule {
  enabled: boolean;
  frequency: BackupFrequency;
  retention_days: number;
  last_run_at: string | null;
  last_result: 'never_run' | 'success' | 'failed' | 'skipped_locked';
  last_file_count: number;
}

// API functions

async function fetchBackups(): Promise<BackupListResponse> {
  return apiGet<BackupListResponse>('/backup/');
}

async function createBackup(): Promise<CreateBackupResponse> {
  return apiPost<CreateBackupResponse>('/backup/');
}

async function verifyBackup(backupId: string): Promise<VerifyBackupResponse> {
  return apiPost<VerifyBackupResponse>(`/backup/${backupId}/verify`);
}

async function restoreBackup(
  backupId: string,
  data: RestoreRequest
): Promise<RestoreResponse> {
  return apiPost<RestoreResponse, RestoreRequest>(
    `/backup/${backupId}/restore`,
    data
  );
}

async function fetchSchedule(): Promise<BackupSchedule> {
  return apiGet<BackupSchedule>('/backup/schedule');
}

async function saveSchedule(data: {
  enabled: boolean;
  frequency: BackupFrequency;
  retention_days: number;
}): Promise<BackupSchedule> {
  return apiPut<BackupSchedule, typeof data>('/backup/schedule', data);
}

/**
 * Download a backup archive.
 *
 * Uses `apiGetRaw` rather than a plain anchor href: the API is behind a bearer
 * token, and an `<a download>` does not send the Authorization header — it just
 * 401s. Same reason `downloadCsv` in export.ts works the way it does.
 */
export async function downloadBackupArchive(backupId: string): Promise<void> {
  const response = await apiGetRaw(`/backup/${backupId}/download`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = `${backupId}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } finally {
    URL.revokeObjectURL(url);
  }
}

// React Query hooks

export function useBackups() {
  return useQuery({
    queryKey: [QUERY_KEY],
    queryFn: fetchBackups,
    staleTime: 1000 * 30,
  });
}

export function useCreateBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBackup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'schedule'] });
    },
  });
}

export function useVerifyBackup() {
  return useMutation({ mutationFn: verifyBackup });
}

export function useRestoreBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ backupId, data }: { backupId: string; data: RestoreRequest }) =>
      restoreBackup(backupId, data),
    onSuccess: () => {
      // The vault underneath every cached query has just been replaced.
      queryClient.clear();
    },
  });
}

export function useBackupSchedule() {
  return useQuery({
    queryKey: [QUERY_KEY, 'schedule'],
    queryFn: fetchSchedule,
    staleTime: 1000 * 30,
  });
}

export function useSaveBackupSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'schedule'] });
    },
  });
}
