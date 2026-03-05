/**
 * Gamification API Service
 *
 * React Query hooks for badge listing.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';
import type { BadgeListResponse } from './types';

const QUERY_KEY = 'gamification';

async function fetchBadges(): Promise<BadgeListResponse> {
  return apiGet<BadgeListResponse>('/gamification/badges');
}

export function useBadges() {
  return useQuery({
    queryKey: [QUERY_KEY, 'badges'],
    queryFn: fetchBadges,
  });
}
