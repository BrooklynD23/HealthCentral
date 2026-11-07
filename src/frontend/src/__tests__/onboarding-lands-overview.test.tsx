/**
 * ONBOARDING-LANDS-OVERVIEW (owner answer LANDING-OVERVIEW): unlocking an
 * existing profile and creating a new one (after the recovery code is
 * acknowledged) land on /overview, never /inbox.
 *
 * Each test also asserts '/inbox' was never navigated to, so a page that
 * navigates to both cannot pass. The recovery case is HC-OLO-003 in
 * RecoverProfile.test.tsx.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfileSetup } from '@/pages/ProfileSetup';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiPost: vi.fn(),
  apiGet: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public statusText: string,
      message: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const PASSWORD = 'SecurePass123';
const PROFILE = {
  id: 'profile-uuid-123',
  display_name: 'Maria Lopez',
  is_locked: false,
  created_at: '2026-01-01T00:00:00Z',
  last_accessed_at: null,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ProfileSetup />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('ONBOARDING-LANDS-OVERVIEW: sign-in landings open /overview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.getState().clearAuth();
  });

  it('HC-OLO-001: unlocking an existing profile navigates to /overview', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    vi.mocked(api.apiPost).mockResolvedValueOnce({
      access_token: 'unlocked-token-456',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: PROFILE.id,
      profile_name: PROFILE.display_name,
    });
    renderPage();

    await user.type(await screen.findByLabelText('Unlock password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: /^unlock$/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/overview'));
    expect(mockNavigate).not.toHaveBeenCalledWith('/inbox');
  });

  it('HC-OLO-002: creating a profile, then acknowledging the recovery code, navigates to /overview', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiGet).mockResolvedValue([]);
    vi.mocked(api.apiPost).mockResolvedValueOnce({
      access_token: 'new-token-123',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: 'profile-uuid-new',
      profile_name: 'My Health Profile',
      recovery_code: 'H4K2-9QMR-7TXB-3VWZ-5CDF-8GHJ-2NPS-6KTV',
    });
    renderPage();

    await user.type(await screen.findByLabelText('Profile Name'), 'My Health Profile');
    await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: /create your profile/i }));

    await screen.findByTestId('recovery-code');
    // Not navigated before the recovery code is acknowledged.
    expect(mockNavigate).not.toHaveBeenCalled();
    await user.click(screen.getByLabelText(/saved this recovery code/i));
    await user.click(screen.getByRole('button', { name: /continue to my records/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/overview'));
    expect(mockNavigate).not.toHaveBeenCalledWith('/inbox');
  });
});
