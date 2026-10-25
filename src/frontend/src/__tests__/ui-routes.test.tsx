// UI-ROUTES (HC-UIRT-001): a route element that throws renders the route
// boundary inside the layout, not a white screen, and its link recovers.
//
// HC-UIRT-002 (HC-ROUTE-001 unknown-path redirect, HC-ROUTE-002 navigate()
// guard) is pinned by Routing.test.tsx, which is not edited by this row.
//
// The test goes through the real <App /> so a route that is not wrapped in the
// boundary fails here (a unit test of ErrorBoundary alone cannot see that).

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '@/App';
import { useAuthStore } from '@/stores/authStore';

// The one lazy page that throws. The lazy import in App.tsx resolves to the
// same module, so this mock is what the router renders.
vi.mock('@/pages/SettingsPage', () => ({
  SettingsPage: function ThrowingSettingsPage() {
    throw new Error('boom-internal-detail');
  },
}));

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

describe('UI-ROUTES route error boundary', () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // React logs every caught render error to console.error. That is expected here.
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    vi.restoreAllMocks();
    window.history.replaceState({}, '', '/');
  });

  it('HC-UIRT-001: a route that throws shows the boundary inside the layout, and its link recovers', async () => {
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
      expiresIn: 3600,
    });
    window.history.pushState({}, '', '/settings');

    render(<App />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('This page hit a problem');

    const link = screen.getByRole('link', { name: 'Go to Documents' });
    expect(link).toHaveAttribute('href', '/inbox');

    // The boundary is per route, inside AppLayout: the navigation still renders.
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();

    // The thrown message may carry patient data, so it must never reach the page.
    expect(document.body.textContent).not.toContain('boom-internal-detail');

    // The link recovers: navigating away clears the boundary.
    fireEvent.click(link);
    await waitFor(() => expect(window.location.pathname).toBe('/inbox'));
    await waitFor(() => expect(screen.queryByText('This page hit a problem')).not.toBeInTheDocument());
  });
});
