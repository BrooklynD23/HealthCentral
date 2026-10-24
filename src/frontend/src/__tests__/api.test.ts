/**
 * API Client Tests
 *
 * Sprint 1 - S1-FE-002: Add Authorization Header to API Client
 *
 * Tests that:
 * - Authorization header is attached to all requests
 * - Missing token redirects to login
 * - Expired token is handled
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiGet, apiPost, apiPut, apiDelete, apiUpload } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

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

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Reset auth store
    useAuthStore.getState().clearAuth();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('FE-AUTH-004: test_authorization_header_attached', () => {
    it('should attach Authorization header when token exists', async () => {
      // Set up auth store with token
      useAuthStore.getState().setAuth({
        token: 'test-bearer-token',
        profileId: 'profile-123',
        profileName: 'Test Profile',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ data: 'test' }),
      });

      await apiGet('/test-endpoint');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-bearer-token',
          }),
        })
      );
    });

    it('should attach Authorization header to POST requests', async () => {
      useAuthStore.getState().setAuth({
        token: 'post-token',
        profileId: 'profile-123',
        profileName: 'Test Profile',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ created: true }),
      });

      await apiPost('/test-endpoint', { data: 'value' });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Bearer post-token',
          }),
        })
      );
    });

    it('should attach Authorization header to PUT requests', async () => {
      useAuthStore.getState().setAuth({
        token: 'put-token',
        profileId: 'profile-123',
        profileName: 'Test Profile',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ updated: true }),
      });

      await apiPut('/test-endpoint', { data: 'value' });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({
            Authorization: 'Bearer put-token',
          }),
        })
      );
    });

    it('should attach Authorization header to DELETE requests', async () => {
      useAuthStore.getState().setAuth({
        token: 'delete-token',
        profileId: 'profile-123',
        profileName: 'Test Profile',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await apiDelete('/test-endpoint');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'DELETE',
          headers: expect.objectContaining({
            Authorization: 'Bearer delete-token',
          }),
        })
      );
    });

    it('should attach Authorization header to file upload requests', async () => {
      useAuthStore.getState().setAuth({
        token: 'upload-token',
        profileId: 'profile-123',
        profileName: 'Test Profile',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ uploaded: true }),
      });

      const file = new File(['test content'], 'test.pdf', {
        type: 'application/pdf',
      });
      await apiUpload('/documents/import', file);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Bearer upload-token',
          }),
        })
      );
    });
  });

  describe('FE-AUTH-005: test_missing_token_redirects_to_login', () => {
    it('should not attach Authorization header when no token', async () => {
      // Ensure no token
      expect(useAuthStore.getState().token).toBeNull();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ public: 'data' }),
      });

      await apiGet('/public-endpoint');

      // Should still call fetch but without Authorization
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      );
    });

    it('should throw AuthenticationError on 401 response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        text: async () => '{"detail": "Not authenticated"}',
      });

      await expect(apiGet('/protected-endpoint')).rejects.toThrow();

      // Should clear auth state on 401
      const authState = useAuthStore.getState();
      expect(authState.token).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
    });
  });

  describe('FE-AUTH-006: test_expired_token_handled', () => {
    it('should clear auth and throw on 401 with expired token message', async () => {
      // Start with a token
      useAuthStore.getState().setAuth({
        token: 'expired-token',
        profileId: 'profile-123',
        profileName: 'Test Profile',
      });

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        text: async () => '{"detail": "Session expired"}',
      });

      await expect(apiGet('/protected-endpoint')).rejects.toThrow();

      // Auth should be cleared
      const authState = useAuthStore.getState();
      expect(authState.token).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
    });

    it('should handle 403 for locked profile database', async () => {
      useAuthStore.getState().setAuth({
        token: 'valid-token',
        profileId: 'profile-123',
        profileName: 'Test Profile',
      });

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        text: async () =>
          '{"detail": "Profile database not available. Please log in again."}',
      });

      await expect(apiGet('/protected-endpoint')).rejects.toMatchObject({
        status: 403,
        message: expect.stringContaining('Profile database not available'),
      });
    });
  });
  describe('MVP-REAUTH-401: re-auth 401 must not log the user out', () => {
    let loc: ReturnType<typeof stubLocationReplace>;
    beforeEach(() => {
      loc = stubLocationReplace();
      useAuthStore.getState().setAuth({
        token: 'live-token',
        profileId: 'profile-123',
        profileName: 'Test Profile',
      });
    });
    afterEach(() => loc.restore());

    const wrongPassword = () =>
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        text: async () => '{"detail": "Incorrect password"}',
      });

    it('HC-RA4-001: apiDelete with reauth throws ApiError 401 and keeps the session', async () => {
      wrongPassword();
      await expect(
        apiDelete('/profiles/p1', { password: 'bad' }, { reauth: true })
      ).rejects.toMatchObject({ status: 401, message: expect.stringContaining('Incorrect password') });
      expect(useAuthStore.getState().token).toBe('live-token');
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(loc.replace).not.toHaveBeenCalled();
    });

    it('HC-RA4-001b: apiPost with reauth throws ApiError 401 and keeps the session', async () => {
      wrongPassword();
      await expect(
        apiPost('/backup/b1/restore', { password: 'bad' }, { reauth: true })
      ).rejects.toMatchObject({ status: 401, message: expect.stringContaining('Incorrect password') });
      expect(useAuthStore.getState().token).toBe('live-token');
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(loc.replace).not.toHaveBeenCalled();
    });

    it('HC-RA4-001c: reauth is not forwarded to fetch', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await apiPost('/x', { a: 1 }, { reauth: true });
      expect(mockFetch.mock.calls[0][1]).not.toHaveProperty('reauth');
    });

    it('HC-RA4-002: a plain apiGet 401 still clears auth and redirects', async () => {
      wrongPassword();
      await expect(apiGet('/protected-endpoint')).rejects.toThrow();
      expect(useAuthStore.getState().token).toBeNull();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(loc.replace).toHaveBeenCalledTimes(1);
    });
  });
});
