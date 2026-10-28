/**
 * SESSION-REENTRY Task 3, "Lock now" (HC-SRE-011, plan §8.2).
 *
 * The profile menu's "Lock now" calls the existing lock endpoint once, then clears
 * the session the way logout does and lands on /setup. The API is mocked here; the
 * real endpoint is checked by e2e/session-lock-now.spec.ts (HC-SRE-012).
 *
 * What these tests would not notice:
 * - whether the server really closed the vault or revoked the token (mocked here;
 *   HC-SRE-012 covers the real endpoint);
 * - a second click that arrives after the request has settled (the in-flight guard
 *   is only exercised while the request is pending, which is what (a) holds open);
 * - whether the navigation is a true history replace (only the location is read).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfileMenu } from '@/components/layout/ProfileMenu';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));

const PROFILE_ID = 'profile-lock-1';

function LocationProbe() {
  const location = useLocation();
  return <p data-testid="location">{location.pathname}</p>;
}

function renderMenu() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  // A profile-data query that must be gone once the session is cleared.
  queryClient.setQueryData(['health-data', PROFILE_ID], { observations: 3 });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/inbox']}>
        <ProfileMenu />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return queryClient;
}

async function openMenu(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Profile and settings' }));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.apiPost).mockReset();
  useAuthStore.getState().setAuth({
    token: 'live-token',
    profileId: PROFILE_ID,
    profileName: 'Test profile',
    expiresIn: 3600,
  });
});

describe('HC-SRE-011 Lock now in the profile menu', () => {
  it('HC-SRE-011: Settings stays the first item and keeps its name', async () => {
    const user = userEvent.setup();
    renderMenu();
    await openMenu(user);

    const settings = screen.getByRole('link', { name: 'Settings', exact: true });
    const lock = screen.getByRole('button', { name: 'Lock now' });
    expect(settings.compareDocumentPosition(lock) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('HC-SRE-011 (a): a double click calls the lock endpoint exactly once', async () => {
    const user = userEvent.setup();
    // Hold the request open so the second click lands while it is still pending.
    let finishLock: (value: unknown) => void = () => {};
    vi.mocked(api.apiPost).mockReturnValue(
      new Promise((resolve) => {
        finishLock = resolve;
      })
    );
    renderMenu();
    await openMenu(user);

    const lockButton = screen.getByRole('button', { name: 'Lock now' });
    await user.dblClick(lockButton);

    expect(api.apiPost).toHaveBeenCalledTimes(1);
    expect(api.apiPost).toHaveBeenCalledWith(`/profiles/${PROFILE_ID}/lock`);
    expect(lockButton).toBeDisabled();

    finishLock({ id: PROFILE_ID });
    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false));
  });

  it('HC-SRE-011 (b): after the lock resolves, the auth store is signed out, the cache is empty and the route is /setup', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockResolvedValue({
      id: PROFILE_ID,
      display_name: 'Test profile',
      is_locked: true,
    });
    const queryClient = renderMenu();
    await openMenu(user);

    await user.click(screen.getByRole('button', { name: 'Lock now' }));

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false));
    expect(useAuthStore.getState().token).toBeNull();
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    expect(screen.getByTestId('location').textContent).toBe('/setup');
  });

  it('HC-SRE-011 (c): when the lock call rejects, the session is still cleared and the route is /setup', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockRejectedValue(new Error('Network request failed'));
    const queryClient = renderMenu();
    await openMenu(user);

    await user.click(screen.getByRole('button', { name: 'Lock now' }));

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false));
    expect(useAuthStore.getState().token).toBeNull();
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    expect(screen.getByTestId('location').textContent).toBe('/setup');
    expect(api.apiPost).toHaveBeenCalledTimes(1);
  });
});
