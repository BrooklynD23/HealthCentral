/**
 * Timeline API Service (HC-M14)
 *
 * React Query hooks for the chronological health record view.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';

export type TimelineEventType =
  | 'lab_results'
  | 'imaging'
  | 'pathology'
  | 'visit_notes'
  | 'medication_start'
  | 'medication_stop';

export type TimelineDateSource =
  | 'document_date'
  | 'entity_date'
  | 'upload_date'
  | 'recorded_date';

export type TimelineVerificationStatus = 'verified' | 'unverified' | 'mixed' | 'n/a';

export interface TimelineEvent {
  event_id: string;
  event_type: TimelineEventType;
  event_date: string | null;
  event_date_source: TimelineDateSource | null;
  title: string;
  doc_id: string | null;
  related_ids: string[];
  verification_status: TimelineVerificationStatus;
}

export interface TimelineResponse {
  events: TimelineEvent[];
  undated: TimelineEvent[];
}

export interface TimelineFilters {
  event_type?: TimelineEventType | '';
  date_from?: string;
  date_to?: string;
}

async function fetchTimeline(filters: TimelineFilters): Promise<TimelineResponse> {
  // profile_id is extracted from auth token by backend, not query params
  const params: Record<string, string> = {};
  if (filters.event_type) params.event_type = filters.event_type;
  if (filters.date_from) params.date_from = filters.date_from;
  if (filters.date_to) params.date_to = filters.date_to;

  return apiGet<TimelineResponse>('/timeline/', params);
}

export function useTimeline(filters: TimelineFilters = {}) {
  return useQuery({
    queryKey: ['timeline', filters],
    queryFn: () => fetchTimeline(filters),
  });
}
