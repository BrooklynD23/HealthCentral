// UI-ROUTES (HC-UIRT-001): a page that throws while rendering shows the route
// boundary, not a white screen, and its link recovers. On the routes inside
// AppLayout the navigation still renders around the boundary. /setup has no
// layout, so only the boundary is checked there.
//
// HC-UIRT-002 (HC-ROUTE-001 unknown-path redirect, HC-ROUTE-002 navigate()
// guard) is pinned by Routing.test.tsx, which is not edited by this row.
//
// The test goes through the real <App /> so the boundary wiring is exercised
// (a unit test of ErrorBoundary alone cannot see it). The wiring is checked for
// the four routes below, not for every route inside the boundary.
// The pages are stubs, so the test decides when each one throws.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within, act } from '@testing-library/react';
import App from '@/App';
import { useAuthStore } from '@/stores/authStore';

// While `throwing` is set, every stubbed page throws. The test clears it right
// before clicking the recovery link, so the Documents page renders afterwards.
// `inboxMounts` and `verifyMounts` count how many times the Inbox and Verify stubs mount (HC-UIRT-003).
const stubs = vi.hoisted(() => ({ throwing: true, inboxMounts: 0, verifyMounts: 0 }));

vi.mock('@/pages/ProfileSetup', async () => {
  const { createElement } = await import('react');
  return {
    ProfileSetup: function SetupStub() {
      if (stubs.throwing) throw new Error('boom-internal-detail');
      return createElement('h1', null, 'Setup stub');
    },
  };
});

vi.mock('@/pages/DocumentInbox', async () => {
  const { createElement, useEffect } = await import('react');
  return {
    DocumentInbox: function InboxStub() {
      // The hook is called before the throw, so the hook order is the same on every render.
      useEffect(() => {
        stubs.inboxMounts += 1;
      }, []);
      if (stubs.throwing) throw new Error('boom-internal-detail');
      return createElement('h1', null, 'Inbox stub');
    },
  };
});

vi.mock('@/pages/VerificationWorkbench', async () => {
  const { createElement, useEffect } = await import('react');
  return {
    VerificationWorkbench: function VerifyStub() {
      // The hook is called before the throw, so the hook order is the same on every render.
      useEffect(() => {
        stubs.verifyMounts += 1;
      }, []);
      if (stubs.throwing) throw new Error('boom-internal-detail');
      return createElement('h1', null, 'Verify stub');
    },
  };
});

vi.mock('@/pages/SettingsPage', async () => {
  const { createElement } = await import('react');
  return {
    SettingsPage: function SettingsStub() {
      if (stubs.throwing) throw new Error('boom-internal-detail');
      return createElement('h1', null, 'Settings stub');
    },
  };
});

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
    stubs.throwing = true;
    // React logs every caught render error to console.error. That is expected here.
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
      expiresIn: 3600,
    });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    vi.restoreAllMocks();
    window.history.replaceState({}, '', '/');
  });

  it.each([
    { path: '/inbox', inLayout: true },
    { path: '/verify', inLayout: true },
    { path: '/settings', inLayout: true },
    { path: '/setup', inLayout: false },
  ])('HC-UIRT-001: $path that throws shows the boundary, and its link recovers', async ({ path, inLayout }) => {
    window.history.pushState({}, '', path);

    render(<App />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('This page hit a problem');

    const link = screen.getByRole('link', { name: 'Go to Documents' });
    expect(link).toHaveAttribute('href', '/inbox');
    // Reloading covers a page whose code chunk failed to load, which a click cannot retry.
    expect(screen.getByRole('button', { name: 'Reload page' })).toBeInTheDocument();

    if (inLayout) {
      // The boundary is per route, inside AppLayout: the navigation still renders.
      expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
    }

    // The thrown message may carry patient data, so it must never reach the page.
    expect(document.body.textContent).not.toContain('boom-internal-detail');

    // The link recovers: it clears the boundary and renders Documents, even when
    // the broken page is Documents itself (the same path, so no remount).
    stubs.throwing = false;
    fireEvent.click(link);
    await waitFor(() => expect(window.location.pathname).toBe('/inbox'), { timeout: 5000 });
    expect(await screen.findByRole('heading', { name: 'Inbox stub' }, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.queryByText('This page hit a problem')).not.toBeInTheDocument();
  });

  it('HC-UIRT-003: a cross-route navigation inside AppLayout mounts the destination page once', async () => {
    stubs.throwing = false;
    stubs.inboxMounts = 0;
    stubs.verifyMounts = 0;
    window.history.pushState({}, '', '/verify');

    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Verify stub' }, { timeout: 5000 })).toBeInTheDocument();
    // The outgoing page's wrapper element. It is removed when its exit animation ends.
    const verifyPage = screen.getByRole('main').firstElementChild;

    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    fireEvent.click(within(nav).getByRole('link', { name: 'Inbox' }));

    await waitFor(() => expect(verifyPage?.isConnected).toBe(false), { timeout: 5000 });
    // Let the entering page finish mounting before counting.
    await act(() => new Promise((resolve) => setTimeout(resolve, 50)));

    expect(screen.getByRole('heading', { name: 'Inbox stub' })).toBeInTheDocument();
    expect(stubs.inboxMounts).toBe(1);
    // The outgoing page must not remount while it fades out, so Verify still mounts once.
    expect(stubs.verifyMounts).toBe(1);
  });
});
