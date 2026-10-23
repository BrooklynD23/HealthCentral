/**
 * ProfileSetup Component Tests
 *
 * Sprint 1 - S1-FE-001: Fix ProfileCreate Contract
 *
 * Tests that:
 * - Profile creation includes password field
 * - Password validation is enforced
 * - Token is stored on success
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfileSetup } from '@/pages/ProfileSetup';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import {
  cachedMutationsContaining,
  watchCacheFor,
  reactStateContains,
} from './support/secretRetention';

// Mock the API module
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

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{component}</BrowserRouter>
      </QueryClientProvider>
    ),
    queryClient,
  };
}

describe('ProfileSetup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Reset auth store
    useAuthStore.getState().clearAuth();
  });

  describe('FE-AUTH-001: test_create_profile_with_password', () => {
    it('should create profile with password and store access token', async () => {
      const user = userEvent.setup();
      const mockTokenResponse = {
        access_token: 'test-jwt-token-123',
        token_type: 'bearer',
        expires_in: 3600,
        profile_id: 'profile-uuid-123',
        profile_name: 'My Health Profile',
        // SEC-RECOV-001: creation now also returns a one-time recovery code.
        recovery_code: 'H4K2-9QMR-7TXB-3VWZ-5CDF-8GHJ-2NPS-6KTV',
      };

      vi.mocked(api.apiPost).mockResolvedValueOnce(mockTokenResponse);

      renderWithProviders(<ProfileSetup />);

      // Fill in display name using label
      const displayNameInput = screen.getByLabelText('Profile Name');
      await user.type(displayNameInput, 'My Health Profile');

      // Fill in password using placeholder since label matches multiple
      const passwordInput = screen.getByPlaceholderText(
        'Create a secure password'
      );
      await user.type(passwordInput, 'SecurePass123');

      // Submit form
      const createButton = screen.getByRole('button', {
        name: /create your profile/i,
      });
      await user.click(createButton);

      // Verify API called with password
      await waitFor(() => {
        expect(api.apiPost).toHaveBeenCalledWith(
          '/profiles/',
          {
            display_name: 'My Health Profile',
            password: 'SecurePass123',
          },
          expect.objectContaining({
            signal: expect.any(AbortSignal),
          })
        );
      });

      // Verify token stored in auth store
      await waitFor(() => {
        const authState = useAuthStore.getState();
        expect(authState.token).toBe('test-jwt-token-123');
        expect(authState.profileId).toBe('profile-uuid-123');
      });

      // SEC-RECOV-001: the one-time recovery code is shown before the app is
      // entered, and the user cannot skip past it without acknowledging it.
      const codeBlock = await screen.findByTestId('recovery-code');
      expect(codeBlock).toHaveTextContent(
        'H4K2-9QMR-7TXB-3VWZ-5CDF-8GHJ-2NPS-6KTV'
      );
      expect(mockNavigate).not.toHaveBeenCalled();

      const continueButton = screen.getByRole('button', {
        name: /continue to my records/i,
      });
      expect(continueButton).toBeDisabled();

      await user.click(
        screen.getByLabelText(/saved this recovery code/i)
      );
      await user.click(continueButton);

      // Verify navigation to inbox
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/inbox');
      });
    });
  });

  describe('FE-AUTH-002: test_password_validation_required', () => {
    it('should require password field before submission', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ProfileSetup />);

      // Fill only display name
      const displayNameInput = screen.getByLabelText('Profile Name');
      await user.type(displayNameInput, 'My Health Profile');

      // Submit without password
      const createButton = screen.getByRole('button', {
        name: /create your profile/i,
      });
      await user.click(createButton);

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument();
      });

      // API should NOT have been called
      expect(api.apiPost).not.toHaveBeenCalled();
    });

    it('should show password strength requirements', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ProfileSetup />);

      const passwordInput = screen.getByPlaceholderText(
        'Create a secure password'
      );

      // Type weak password
      await user.type(passwordInput, 'weak');

      // Should show strength feedback
      await waitFor(() => {
        const feedback = screen.getByText(/at least 8 characters/i);
        expect(feedback).toBeInTheDocument();
      });
    });
  });

  describe('FE-AUTH-003: test_token_stored_on_success', () => {
    it('should store token and profile data in auth store on success', async () => {
      const user = userEvent.setup();
      const mockTokenResponse = {
        access_token: 'jwt-token-abc',
        token_type: 'bearer',
        expires_in: 7200,
        profile_id: 'profile-123',
        profile_name: 'Test Profile',
      };

      vi.mocked(api.apiPost).mockResolvedValueOnce(mockTokenResponse);

      renderWithProviders(<ProfileSetup />);

      // Fill form
      await user.type(screen.getByLabelText('Profile Name'), 'Test Profile');
      await user.type(
        screen.getByPlaceholderText('Create a secure password'),
        'SecurePass123'
      );

      // Submit
      await user.click(
        screen.getByRole('button', { name: /create your profile/i })
      );

      // Verify auth store state
      await waitFor(() => {
        const authState = useAuthStore.getState();
        expect(authState.token).toBe('jwt-token-abc');
        expect(authState.profileId).toBe('profile-123');
        expect(authState.profileName).toBe('Test Profile');
        expect(authState.isAuthenticated).toBe(true);
      });
    });

    it('should handle API error and show error message', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockRejectedValueOnce(
        new Error('Password too weak')
      );

      renderWithProviders(<ProfileSetup />);

      // Fill form
      await user.type(screen.getByLabelText('Profile Name'), 'Test Profile');
      await user.type(
        screen.getByPlaceholderText('Create a secure password'),
        'SecurePass123'
      );

      // Submit
      await user.click(
        screen.getByRole('button', { name: /create your profile/i })
      );

      // Should show error
      await waitFor(() => {
        expect(screen.getByText(/password too weak/i)).toBeInTheDocument();
      });

      // Auth store should remain empty
      const authState = useAuthStore.getState();
      expect(authState.token).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
    });
  });

  describe('RCC-2: no password or recovery code left behind', () => {
    const PASSWORD = 'SecurePass123';
    const CODE = 'H4K2-9QMR-7TXB-3VWZ-5CDF-8GHJ-2NPS-6KTV';
    const created = {
      access_token: 'test-jwt-token-123',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: 'profile-uuid-123',
      profile_name: 'My Health Profile',
      recovery_code: CODE,
    };

    async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
      await user.type(screen.getByLabelText('Profile Name'), 'My Health Profile');
      await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
      await user.click(screen.getByRole('button', { name: /create your profile/i }));
    }

    it('FE-RCC2-001: after creation neither the cache nor page state keeps the password or code', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(created);
      const { queryClient, container } = renderWithProviders(<ProfileSetup />);
      const pw = watchCacheFor(queryClient, PASSWORD);
      const code = watchCacheFor(queryClient, CODE);

      await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
      expect(reactStateContains(container, PASSWORD)).toBe(true); // positive control
      await user.clear(screen.getByPlaceholderText('Create a secure password'));
      await fillAndSubmit(user);

      expect(await screen.findByTestId('recovery-code', {}, { timeout: 5000 })).toHaveTextContent(CODE);
      expect(pw.seen.value).toBe(true);
      expect(code.seen.value).toBe(true);
      pw.unsubscribe();
      code.unsubscribe();

      await waitFor(() => {
        expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0);
        expect(cachedMutationsContaining(queryClient, CODE)).toBe(0);
      });
      expect(reactStateContains(container, PASSWORD)).toBe(false);
      // The code itself is still displayed: it lives in its one display state.
      expect(screen.getByTestId('recovery-code')).toHaveTextContent(CODE);
    }, 15000);

    it('FE-RCC2-002: a failed creation leaves no password in the cache, and a retry is clean too', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Server unavailable'));
      const { queryClient } = renderWithProviders(<ProfileSetup />);
      const pw = watchCacheFor(queryClient, PASSWORD);

      await fillAndSubmit(user);
      expect(await screen.findByText(/server unavailable/i, {}, { timeout: 5000 })).toBeInTheDocument();
      expect(pw.seen.value).toBe(true);
      pw.unsubscribe();
      await waitFor(() => expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0));

      vi.mocked(api.apiPost).mockResolvedValueOnce(created);
      await user.click(screen.getByRole('button', { name: /create your profile/i }));
      expect(await screen.findByTestId('recovery-code', {}, { timeout: 5000 })).toHaveTextContent(CODE);
      await waitFor(() => {
        expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0);
        expect(cachedMutationsContaining(queryClient, CODE)).toBe(0);
      });
    }, 15000);
  });

  describe('SESSION-REENTRY: unlock an existing profile with its password', () => {
    const PROFILE = {
      id: 'profile-uuid-123',
      display_name: 'Maria Lopez',
      is_locked: false,
      created_at: '2026-01-01T00:00:00Z',
      last_accessed_at: null,
    };
    const PASSWORD = 'SecurePass123';

    function mockOneProfile() {
      vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    }

    it('HC-SRE-001: with a profile on file, /setup offers "Unlock your profile"', async () => {
      mockOneProfile();
      renderWithProviders(<ProfileSetup />);

      expect(await screen.findByText('Unlock your profile')).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Maria Lopez' })).toBeInTheDocument();
      expect(screen.getByLabelText('Unlock password')).toHaveAttribute('type', 'password');
      expect(screen.getByRole('button', { name: /^unlock$/i })).toBeInTheDocument();
      // The recovery-code route stays reachable.
      expect(screen.getByRole('link', { name: /use your recovery code/i })).toBeInTheDocument();
    });

    it('HC-SRE-002: unlocking posts {profile_id, password}, stores the token and goes to /inbox', async () => {
      const user = userEvent.setup();
      mockOneProfile();
      vi.mocked(api.apiPost).mockResolvedValueOnce({
        access_token: 'unlocked-token-456',
        token_type: 'bearer',
        expires_in: 3600,
        profile_id: PROFILE.id,
        profile_name: PROFILE.display_name,
      });
      const { queryClient } = renderWithProviders(<ProfileSetup />);
      const pw = watchCacheFor(queryClient, PASSWORD);

      await user.type(await screen.findByLabelText('Unlock password'), PASSWORD);
      await user.click(screen.getByRole('button', { name: /^unlock$/i }));

      await waitFor(() => {
        expect(api.apiPost).toHaveBeenCalledWith('/profiles/login', {
          profile_id: PROFILE.id,
          password: PASSWORD,
        });
      });
      await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/inbox'));
      expect(useAuthStore.getState().token).toBe('unlocked-token-456');
      // RCC-2: positive control, then the password must leave the cache.
      expect(pw.seen.value).toBe(true);
      pw.unsubscribe();
      await waitFor(() => expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0));
    });

    it('HC-SRE-003: a 401 shows "Incorrect password" in an alert and stays on /setup', async () => {
      const user = userEvent.setup();
      mockOneProfile();
      vi.mocked(api.apiPost).mockRejectedValueOnce(
        new api.ApiError(401, 'Unauthorized', 'Invalid credentials')
      );
      const { queryClient } = renderWithProviders(<ProfileSetup />);
      const pw = watchCacheFor(queryClient, 'WrongPass999');

      await user.type(await screen.findByLabelText('Unlock password'), 'WrongPass999');
      await user.click(screen.getByRole('button', { name: /^unlock$/i }));

      expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect password');
      expect(mockNavigate).not.toHaveBeenCalled();
      expect(useAuthStore.getState().token).toBeNull();
      // The wrong password is not kept in the field.
      expect(screen.getByLabelText('Unlock password')).toHaveValue('');
      // RCC-2: positive control, then the password must leave the cache.
      expect(pw.seen.value).toBe(true);
      pw.unsubscribe();
      await waitFor(() => expect(cachedMutationsContaining(queryClient, 'WrongPass999')).toBe(0));
    });

    it('HC-SRE-006: with two profiles, the one selected in the picker is the one unlocked', async () => {
      const user = userEvent.setup();
      const second = { ...PROFILE, id: 'profile-uuid-456', display_name: 'Sam Lee' };
      vi.mocked(api.apiGet).mockResolvedValue([PROFILE, second]);
      vi.mocked(api.apiPost).mockResolvedValueOnce({
        access_token: 'second-token',
        token_type: 'bearer',
        expires_in: 3600,
        profile_id: second.id,
        profile_name: second.display_name,
      });
      renderWithProviders(<ProfileSetup />);

      await user.selectOptions(await screen.findByLabelText('Profile'), second.id);
      await user.type(screen.getByLabelText('Unlock password'), PASSWORD);
      await user.click(screen.getByRole('button', { name: /^unlock$/i }));

      await waitFor(() => {
        expect(api.apiPost).toHaveBeenCalledWith('/profiles/login', {
          profile_id: second.id,
          password: PASSWORD,
        });
      });
    });

    it('HC-SRE-007: a 429 tells the patient to wait and try again', async () => {
      const user = userEvent.setup();
      mockOneProfile();
      vi.mocked(api.apiPost).mockRejectedValueOnce(
        new api.ApiError(429, 'Too Many Requests', 'rate limited')
      );
      renderWithProviders(<ProfileSetup />);

      await user.type(await screen.findByLabelText('Unlock password'), PASSWORD);
      await user.click(screen.getByRole('button', { name: /^unlock$/i }));

      expect(await screen.findByRole('alert')).toHaveTextContent(/too many attempts.*try again/i);
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('HC-SRE-008: unlocking clears the query cache so no other profile\'s data survives', async () => {
      const user = userEvent.setup();
      mockOneProfile();
      vi.mocked(api.apiPost).mockResolvedValueOnce({
        access_token: 'unlocked-token-456',
        token_type: 'bearer',
        expires_in: 3600,
        profile_id: PROFILE.id,
        profile_name: PROFILE.display_name,
      });
      const { queryClient } = renderWithProviders(<ProfileSetup />);
      await screen.findByText('Unlock your profile');
      // Data fetched under a previous profile's session.
      queryClient.setQueryData(['medications', { activeOnly: true }], [{ name: 'Metformin' }]);
      expect(queryClient.getQueryData(['medications', { activeOnly: true }])).toBeDefined();

      await user.type(screen.getByLabelText('Unlock password'), PASSWORD);
      await user.click(screen.getByRole('button', { name: /^unlock$/i }));
      await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/inbox'));

      // The mounted profiles-list observer may re-create its own query after
      // the clear; everything else must be gone.
      const leftover = queryClient
        .getQueryCache()
        .getAll()
        .filter((q) => q.queryKey[0] !== 'profiles');
      expect(leftover).toEqual([]);
    });

    it('HC-SRE-009: while the profile list is loading, neither the create button nor the create form is shown', async () => {
      vi.mocked(api.apiGet).mockReturnValue(new Promise(() => {}));
      renderWithProviders(<ProfileSetup />);

      // Let the first render settle; the list never arrives.
      await new Promise((r) => setTimeout(r, 50));
      expect(screen.queryByRole('button', { name: /create a new profile/i })).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Profile Name')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /create your profile/i })).not.toBeInTheDocument();
    });
  });
});
