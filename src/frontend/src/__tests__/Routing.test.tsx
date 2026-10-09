/**
 * Routing tests: unknown-path fallback through the real <App /> router.
 * The Future-Flag render must stay the FIRST render in this file
 * (v6 warns once per module instance).
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { BrowserRouter, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import App from '@/App';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn().mockResolvedValue([]),
  apiPost: vi.fn().mockResolvedValue({}),
  apiPut: vi.fn().mockResolvedValue({}),
  apiPatch: vi.fn().mockResolvedValue({}),
  apiDelete: vi.fn().mockResolvedValue(undefined),
  apiGetRaw: vi.fn().mockResolvedValue(new Response('')),
  apiUpload: vi.fn().mockResolvedValue({}),
  getApiBaseUrl: () => 'http://localhost:8000/api/v1',
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

describe('Routing', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, '', '/');
  });

  it('HC-ROUTE-001: unknown path redirects to /inbox without Future Flag warnings', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
      expiresIn: 3600,
    });
    window.history.pushState({}, '', '/no-such-page');

    render(<App />);

    await waitFor(() => expect(window.location.pathname).toBe('/inbox'));
    const flagWarnings = warn.mock.calls.filter((c) => /Future Flag/.test(String(c[0])));
    expect(flagWarnings).toEqual([]);
  });

  it('HC-ROUTE-002: navigate() with a backslash target never pushes another origin (GHSA-wrjc-x8rr-h8h6)', async () => {
    const pushSpy = vi.spyOn(window.history, 'pushState');
    let caught: unknown;

    function Go() {
      const navigate = useNavigate();
      useEffect(() => {
        try {
          navigate('/\\evil.example');
        } catch (e) {
          caught = e;
        }
      }, [navigate]);
      return null;
    }

    render(
      <BrowserRouter>
        <Go />
      </BrowserRouter>
    );

    // Either the router refuses (throws) or it pushes; one of the two must happen.
    await waitFor(() => expect(caught !== undefined || pushSpy.mock.calls.length > 0).toBe(true));
    for (const c of pushSpy.mock.calls) {
      console.log('PUSHED=' + JSON.stringify(c[2]));
      expect(new URL(String(c[2]), 'http://localhost/').origin).toBe('http://localhost');
    }
    if (caught !== undefined) {
      expect(String(caught)).toMatch(/External navigation is not allowed/);
    }
  });
});
