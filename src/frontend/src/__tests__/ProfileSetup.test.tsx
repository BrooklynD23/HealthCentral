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

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
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
        expect(api.apiPost).toHaveBeenCalledWith('/profiles/', {
          display_name: 'My Health Profile',
          password: 'SecurePass123',
        });
      });

      // Verify token stored in auth store
      await waitFor(() => {
        const authState = useAuthStore.getState();
        expect(authState.token).toBe('test-jwt-token-123');
        expect(authState.profileId).toBe('profile-uuid-123');
      });

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
});
