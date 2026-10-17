/**
 * Gamification API Service
 *
 * React Query hooks for badges and the profile-level streak. Keys carry the
 * profile id so a profile switch without logout never serves cached data from
 * the previous profile; ['gamification', kind] still prefix-matches for
 * invalidation.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';
import { useAuthStore } from '@/stores/authStore';
import type { BadgeListResponse, StreakResponse } from './types';

const QUERY_KEY = 'gamification';

export function useBadges() {
  const profileId = useAuthStore((s) => s.profileId);
  return useQuery({
    queryKey: [QUERY_KEY, 'badges', profileId],
    queryFn: () => apiGet<BadgeListResponse>('/gamification/badges'),
  });
}

export function useStreaks() {
  const profileId = useAuthStore((s) => s.profileId);
  return useQuery({
    queryKey: [QUERY_KEY, 'streaks', profileId],
    queryFn: () => apiGet<StreakResponse>('/gamification/streaks'),
  });
}
