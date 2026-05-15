/**
 * Profile API Service
 *
 * React Query hooks for profile management.
 * Sprint 1: Updated to handle TokenResponse from auth endpoints.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from './api';
import { useAuthStore } from '@/stores/authStore';
import type {
  Profile,
  ProfileCreate,
  TokenResponse,
  LoginRequest,
  UnlockRequest,
} from './types';

const QUERY_KEY = 'profiles';

// API functions
async function fetchProfiles(): Promise<Profile[]> {
  return apiGet<Profile[]>('/profiles/');
}

async function fetchProfile(profileId: string): Promise<Profile> {
  return apiGet<Profile>(`/profiles/${profileId}`);
}

async function createProfile(data: ProfileCreate): Promise<TokenResponse> {
  return apiPost<TokenResponse, ProfileCreate>('/profiles/', data, {
    signal: AbortSignal.timeout(180_000),
  });
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
    onSuccess: (data: TokenResponse) => {
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
