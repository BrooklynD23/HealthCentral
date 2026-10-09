/**
 * RCC-2: a failed profile deletion (PROF-DEL-001) must not leave the
 * password in the mutation cache. Success already calls queryClient.clear().
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DangerZone } from '@/components/settings/DangerZone';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { PROFILE_DELETE_CONFIRMATION } from '@/services/profiles';
import { cachedMutationsContaining, watchCacheFor } from './support/secretRetention';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(public status: number, public statusText: string, message: string) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

const PASSWORD = 'DeleteMe123';

describe('RCC-2: DangerZone secret retention', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ profileId: 'profile-1' });
  });

  it('FE-RCC2-005: a failed delete leaves no password in the mutation cache', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiDelete).mockRejectedValueOnce(new Error('Incorrect password'));
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <DangerZone />
        </MemoryRouter>
      </QueryClientProvider>
    );
    const pw = watchCacheFor(queryClient, PASSWORD);

    await user.click(screen.getByRole('button', { name: /delete profile/i }));
    await user.click(screen.getByLabelText(/i confirm i have a copy/i));
    await user.type(screen.getByLabelText(/confirm your password/i), PASSWORD);
    await user.type(screen.getByPlaceholderText(PROFILE_DELETE_CONFIRMATION), PROFILE_DELETE_CONFIRMATION);
    await user.click(screen.getByRole('button', { name: /permanently delete this profile/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect password/i);
    expect(pw.seen.value).toBe(true);
    pw.unsubscribe();
    await waitFor(() => expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0));
  });
});
