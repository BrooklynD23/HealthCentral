/**
 * Data donation consent service (RSI1-DONATE PR-1).
 *
 * React Query hooks for the per-purpose consent switches. Revoking a purpose
 * deletes its donated copies on the server and returns how many were deleted.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPut } from './api';

export const DONATION_PURPOSES = ['fine_tune', 'synthetic_seed', 'agent_traces'] as const;

export type DonationPurpose = (typeof DONATION_PURPOSES)[number];

export interface DonationConsentState {
  purpose: DonationPurpose;
  granted: boolean;
  consent_text_version: string | null;
  granted_at: string | null;
  revoked_at: string | null;
}

export interface DonationConsentList {
  consents: DonationConsentState[];
}

export interface DonationConsentUpdate {
  purpose: DonationPurpose;
  granted: boolean;
  consent_text_version: string;
}

export interface DonationConsentResult {
  purpose: DonationPurpose;
  granted: boolean;
  consent_text_version: string;
  deleted_count: number;
}

export const DONATION_CONSENTS_KEY = ['donation', 'consents'] as const;

export function useDonationConsents() {
  return useQuery<DonationConsentList>({
    queryKey: DONATION_CONSENTS_KEY,
    queryFn: () => apiGet<DonationConsentList>('/donation/consents'),
  });
}

export function useSetDonationConsent() {
  const queryClient = useQueryClient();

  return useMutation<DonationConsentResult, Error, DonationConsentUpdate>({
    mutationFn: ({ purpose, granted, consent_text_version }) =>
      apiPut<DonationConsentResult>(`/donation/consents/${purpose}`, {
        granted,
        consent_text_version,
      }),
    // onSettled: the vault commits before the audit write, so a failed audit
    // can leave the server changed while the request errors.
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: DONATION_CONSENTS_KEY });
    },
  });
}
