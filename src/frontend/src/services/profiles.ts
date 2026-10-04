/**
 * Profile API Service
 *
 * React Query hooks for profile management.
 * Sprint 1: Updated to handle TokenResponse from auth endpoints.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiDelete, apiGet, apiPost } from './api';
import { useAuthStore } from '@/stores/authStore';
import type {
  Profile,
  ProfileCreate,
  TokenResponse,
  LoginRequest,
  UnlockRequest,
  ProfileDeleteRequest,
  ProfileCreateResponse,
  ProfileRecoverRequest,
  ProfileRecoverResponse,
  RecoveryCodeResponse,
} from './types';

/**
 * PROF-DEL-001: the backend requires this exact phrase. Keep it in one place
 * so the confirmation input and the request body cannot drift apart.
 */
export const PROFILE_DELETE_CONFIRMATION = 'DELETE MY HEALTH DATA';

const QUERY_KEY = 'profiles';

// API functions
async function fetchProfiles(): Promise<Profile[]> {
  return apiGet<Profile[]>('/profiles/');
}

async function fetchProfile(profileId: string): Promise<Profile> {
  return apiGet<Profile>(`/profiles/${profileId}`);
}

async function createProfile(data: ProfileCreate): Promise<ProfileCreateResponse> {
  // Creation now runs two PBKDF2 derivations (password seal + recovery seal),
  // which is why the timeout is generous.
  return apiPost<ProfileCreateResponse, ProfileCreate>('/profiles/', data, {
    signal: AbortSignal.timeout(180_000),
  });
}

async function recoverProfile(
  profileId: string,
  data: ProfileRecoverRequest
): Promise<ProfileRecoverResponse> {
  return apiPost<ProfileRecoverResponse, ProfileRecoverRequest>(
    `/profiles/${profileId}/recover`,
    data,
    { signal: AbortSignal.timeout(180_000) }
  );
}

async function issueRecoveryCode(
  profileId: string,
  password: string
): Promise<RecoveryCodeResponse> {
  return apiPost<RecoveryCodeResponse, { password: string }>(
    `/profiles/${profileId}/recovery-code`,
    { password },
    { signal: AbortSignal.timeout(180_000) }
  );
}

async function login(data: LoginRequest): Promise<TokenResponse> {
  return apiPost<TokenResponse, LoginRequest>('/profiles/login', data);
}

async function unlockProfile(
  profileId: string,
  data: UnlockRequest
): Promise<TokenResponse> {
  return apiPost<TokenResponse, UnlockRequest>(
    `/profiles/${profileId}/unlock`,
    data
  );
}

async function lockProfile(profileId: string): Promise<Profile> {
  return apiPost<Profile>(`/profiles/${profileId}/lock`);
}

async function logout(): Promise<void> {
  return apiPost<void>('/profiles/logout');
}

async function deleteProfile(
  profileId: string,
  data: ProfileDeleteRequest
): Promise<void> {
  return apiDelete<ProfileDeleteRequest>(`/profiles/${profileId}`, data);
}

// React Query hooks
export function useProfiles() {
  return useQuery({
    queryKey: [QUERY_KEY],
    queryFn: fetchProfiles,
  });
}

export function useProfile(profileId: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, profileId],
    queryFn: () => fetchProfile(profileId!),
    enabled: !!profileId,
  });
}

export function useCreateProfile() {
  const queryClient = useQueryClient();
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: createProfile,
    // Variables carry the password (and recovery code); drop the mutation
    // from the cache as soon as nothing observes it (RCC-2).
    gcTime: 0,
    onSuccess: (data: ProfileCreateResponse) => {
      // Store token in auth store
      setAuth({
        token: data.access_token,
        profileId: data.profile_id,
        profileName: data.profile_name,
        expiresIn: data.expires_in,
      });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: login,
    onSuccess: (data: TokenResponse) => {
      setAuth({
        token: data.access_token,
        profileId: data.profile_id,
        profileName: data.profile_name,
        expiresIn: data.expires_in,
      });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useUnlockProfile() {
  const queryClient = useQueryClient();
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: ({
      profileId,
      password,
    }: {
      profileId: string;
      password: string;
    }) => unlockProfile(profileId, { password }),
    onSuccess: (data: TokenResponse) => {
      setAuth({
        token: data.access_token,
        profileId: data.profile_id,
        profileName: data.profile_name,
        expiresIn: data.expires_in,
      });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useLockProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: lockProfile,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
      queryClient.setQueryData([QUERY_KEY, data.id], data);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const clearAuth = useAuthStore((state) => state.clearAuth);

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      clearAuth();
      queryClient.clear();
    },
    onError: () => {
      // Clear auth even on error (e.g., if server is unreachable)
      clearAuth();
      queryClient.clear();
    },
  });
}

/**
 * Irreversibly delete a profile and everything in its vault (PROF-DEL-001).
 *
 * The caller must have offered the user a data export first: the backend
 * rejects the request unless `export_acknowledged` is set.
 */
export function useDeleteProfile() {
  const queryClient = useQueryClient();
  const clearAuth = useAuthStore((state) => state.clearAuth);

  return useMutation({
    mutationFn: ({
      profileId,
      data,
    }: {
      profileId: string;
      data: ProfileDeleteRequest;
    }) => deleteProfile(profileId, data),
    // Variables carry the password (and recovery code); drop the mutation
    // from the cache as soon as nothing observes it (RCC-2).
    gcTime: 0,
    onSuccess: () => {
      // The session now points at a profile that no longer exists.
      clearAuth();
      queryClient.clear();
    },
  });
}

/**
 * Unlock a profile with its recovery code and set a new password
 * (SEC-RECOV-001). Returns a session token plus a *rotated* recovery code —
 * the old code stops working, so the new one must be shown to the user.
 */
export function useRecoverProfile() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: ({
      profileId,
      data,
    }: {
      profileId: string;
      data: ProfileRecoverRequest;
    }) => recoverProfile(profileId, data),
    // Variables carry the password (and recovery code); drop the mutation
    // from the cache as soon as nothing observes it (RCC-2).
    gcTime: 0,
    onSuccess: (response) => {
      setAuth({
        token: response.access_token,
        profileId: response.profile_id,
        profileName: response.profile_name,
        expiresIn: response.expires_in,
      });
    },
  });
}

/**
 * Generate or replace this profile's recovery code. Serves both backfill for
 * profiles created before recovery codes existed and user-initiated rotation.
 */
export function useIssueRecoveryCode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ profileId, password }: { profileId: string; password: string }) =>
      issueRecoveryCode(profileId, password),
    // The variables hold the password and the result holds the recovery code:
    // drop the mutation from the cache as soon as nothing observes it.
    gcTime: 0,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}
