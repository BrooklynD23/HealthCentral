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

/** jsdom's location.replace is not spy-able; swap window.location for a stub. */
function stubLocationReplace() {
  const original = window.location;
  const replace = vi.fn();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { pathname: '/settings', origin: 'http://localhost:3000', replace },
  });
  return {
    replace,
    restore: () =>
      Object.defineProperty(window, 'location', { configurable: true, value: original }),
  };
}

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
        <MemoryRouter>
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

describe('MVP-REAUTH-401: DangerZone wrong password', () => {
  it('HC-RA4-003: a wrong password shows the error and keeps the session', async () => {
    const user = userEvent.setup();
    const loc = stubLocationReplace();
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      text: async () => '{"detail": "Incorrect password"}',
    });
    vi.stubGlobal('fetch', mockFetch);
    try {
      // Run the real apiDelete so handleAuthError would really fire.
      const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api');
      vi.mocked(api.apiDelete).mockImplementation(actual.apiDelete);
      useAuthStore.setState({
        token: 'live-token',
        profileId: 'profile-1',
        isAuthenticated: true,
      });
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <DangerZone />
          </MemoryRouter>
        </QueryClientProvider>
      );

      await user.click(screen.getByRole('button', { name: /delete profile/i }));
      await user.click(screen.getByLabelText(/i confirm i have a copy/i));
      await user.type(screen.getByLabelText(/confirm your password/i), 'WrongPass1');
      await user.type(screen.getByPlaceholderText(PROFILE_DELETE_CONFIRMATION), PROFILE_DELETE_CONFIRMATION);
      await user.click(screen.getByRole('button', { name: /permanently delete this profile/i }));

      expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect password/i);
      expect(mockFetch).toHaveBeenCalled();
      expect(useAuthStore.getState().token).toBe('live-token');
      expect(loc.replace).not.toHaveBeenCalled();
      expect(vi.mocked(api.apiDelete).mock.calls[0][2]).toEqual({ reauth: true });
    } finally {
      loc.restore();
      vi.unstubAllGlobals();
    }
  });
});
