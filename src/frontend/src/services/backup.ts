/**
 * Backup & restore service (BKUP-UX-001).
 *
 * Backups are the full-fidelity, restorable copy of a profile — distinct from
 * the export routes, which produce filtered sharing formats. This is what a
 * patient should take before deleting a profile, or before losing a device.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiGetRaw, apiPost, apiPut } from './api';
import { useAuthStore } from '@/stores/authStore';

const QUERY_KEY = 'backups';

export const BACKUP_RESTORE_CONFIRMATION = 'RESTORE MY DATA';

/**
 * Set on a successful restore, read once by the setup/sign-in screen.
 *
 * Clearing auth bounces the user out of the app immediately, so the reason has
 * to outlive this page — otherwise someone who just restored on purpose lands
 * on "Welcome to Asclexis" and reasonably concludes they lost everything.
 * sessionStorage, not the auth store, precisely because the store is what gets
 * cleared.
 */
export const RESTORE_NOTICE_KEY = 'hc.restoreNotice';

/** Reads and consumes the notice. Returns null when there is nothing to say. */
export function takeRestoreNotice(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const notice = window.sessionStorage.getItem(RESTORE_NOTICE_KEY);
    if (notice) window.sessionStorage.removeItem(RESTORE_NOTICE_KEY);
    return notice;
  } catch {
    return null;
  }
}

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
  const clearAuth = useAuthStore((state) => state.clearAuth);
  return useMutation({
    mutationFn: ({ backupId, data }: { backupId: string; data: RestoreRequest }) =>
      restoreBackup(backupId, data),
    // Variables hold the profile password. Drop the mutation from the cache
    // as soon as nothing observes it (RCC-3).
    gcTime: 0,
    onSuccess: () => {
      // The vault underneath every cached query has just been replaced.
      queryClient.clear();

      // And so have its sealed keys. The server dropped the in-memory key
      // before overwriting, so this session can no longer open the vault it
      // is authenticated against — every subsequent call 403s with nothing
      // the user can act on. Ending the session is the honest outcome, and
      // it is the same path api.ts already takes on session invalidation.
      try {
        window.sessionStorage.setItem(
          RESTORE_NOTICE_KEY,
          'Your profile was restored from a backup. Sign in again to open it — ' +
            'use the password that was in use when that backup was made, since ' +
            'the password and recovery code were restored along with the data.'
        );
      } catch {
        // Private-mode storage failures must not block the sign-out itself.
      }
      clearAuth();
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
