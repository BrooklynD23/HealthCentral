/**
 * Profile API Service
 * 
 * React Query hooks for profile management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from './api';
import type { Profile, ProfileCreate } from './types';

const QUERY_KEY = 'profiles';

// API functions
async function fetchProfiles(): Promise<Profile[]> {
  return apiGet<Profile[]>('/profiles/');
}

async function fetchProfile(profileId: string): Promise<Profile> {
  return apiGet<Profile>(`/profiles/${profileId}`);
}

async function createProfile(data: ProfileCreate): Promise<Profile> {
  return apiPost<Profile, ProfileCreate>('/profiles/', data);
}

async function unlockProfile(profileId: string): Promise<Profile> {
  return apiPost<Profile>(`/profiles/${profileId}/unlock`, {});
}

async function lockProfile(profileId: string): Promise<Profile> {
  return apiPost<Profile>(`/profiles/${profileId}/lock`);
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
  
  return useMutation({
    mutationFn: createProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useUnlockProfile() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: unlockProfile,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
      queryClient.setQueryData([QUERY_KEY, data.id], data);
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
