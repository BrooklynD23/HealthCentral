/**
 * SEC-RECOV-002: a signed-in surface that issues a recovery code.
 *
 * SEC-RECOV-001 shipped the backend (`POST /profiles/{id}/recovery-code`) and
 * the `useIssueRecoveryCode` hook, but nothing called it. Codes were issued
 * only at profile creation, so a profile made before the feature existed could
 * never obtain one. RecoverProfile.tsx tells the user a recovery code "can only
 * be created while you can still sign in" — an instruction that could not be
 * followed, because no signed-in surface created one.
 *
 * The code is shown exactly once and never persisted: it seals a second copy of
 * the profile's DEK, so storing it anywhere the app can read would defeat the
 * point of sealing it.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RecoveryCodeCard } from '@/components/settings/RecoveryCodeCard';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

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

const CODE = 'ABCD-EFGH-JKLM-NPQR';

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <RecoveryCodeCard />
    </QueryClientProvider>
  );
  return { ...utils, queryClient };
}

/**
 * How many mutations in this client's cache still carry `needle` in their
 * variables or their result. The recovery code seals a second copy of the
 * DEK; the password unlocks the first. Neither may outlive the request.
 */
function cachedMutationsContaining(queryClient: QueryClient, needle: string): number {
  return queryClient
    .getMutationCache()
    .getAll()
    .filter((m) =>
      JSON.stringify({ v: m.state.variables, d: m.state.data }).includes(needle)
    ).length;
}

/**
 * Positive control: records whether the cache ever held `needle`. Without it,
 * a "nothing cached" assertion would also pass if the mutation never reached
 * this client at all.
 */
function watchCacheFor(queryClient: QueryClient, needle: string) {
  const seen = { value: false };
  const unsubscribe = queryClient.getMutationCache().subscribe((event) => {
    const m = event.mutation;
    if (m && JSON.stringify({ v: m.state.variables, d: m.state.data }).includes(needle)) {
      seen.value = true;
    }
  });
  return { seen, unsubscribe };
}

/**
 * Mocks the real API shape: `has_recovery_code` is returned by the profile
 * LIST endpoint (ProfileListResponse), not by `GET /profiles/{id}`
 * (ProfileResponse). An earlier version of this file mocked the flag onto the
 * single-profile response — a shape the backend never returns — so the test
 * passed against a component that could never show the "replace" state. The
 * e2e run caught it; this mock now matches `api/profiles.py`.
 */
function mockProfile(hasCode: boolean) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (String(url) === '/profiles/')
      return Promise.resolve([
        {
          id: 'profile-1',
          display_name: 'Test',
          has_password: true,
          has_recovery_code: hasCode,
          created_at: '2026-01-01T00:00:00',
        },
      ]);
    return Promise.resolve([]);
  });
}

describe('SEC-RECOV-002: recovery code entry point', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ profileId: 'profile-1' });
    vi.mocked(api.apiPost).mockResolvedValue({
      recovery_code: CODE,
      replaced_existing: false,
    });
  });

  it('FE-RECOV-001: offers to create a code for a profile that has none', async () => {
    mockProfile(false);
    renderCard();
    expect(await screen.findByRole('button', { name: /create recovery code/i })).toBeInTheDocument();
  });

  it('FE-RECOV-002: requires the password before issuing', async () => {
    mockProfile(false);
    renderCard();
    const button = await screen.findByRole('button', { name: /create recovery code/i });
    expect(button).toBeDisabled();

    await userEvent.type(await screen.findByLabelText(/password/i), 'hunter2hunter2');
    expect(button).toBeEnabled();
  });

  it('FE-RECOV-003: shows the issued code once, with a not-shown-again warning', async () => {
    mockProfile(false);
    renderCard();
    await userEvent.type(await screen.findByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /create recovery code/i }));

    expect(await screen.findByTestId('recovery-code-value')).toHaveTextContent(CODE);
    expect(screen.getByTestId('recovery-code-once-warning')).toBeInTheDocument();
  });

  it('FE-RECOV-004: sends the password to the recovery-code endpoint', async () => {
    mockProfile(false);
    renderCard();
    await userEvent.type(await screen.findByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /create recovery code/i }));

    await waitFor(() => {
      expect(api.apiPost).toHaveBeenCalledWith(
        '/profiles/profile-1/recovery-code',
        { password: 'hunter2hunter2' },
        expect.anything()
      );
    });
  });

  it('FE-RECOV-005: does not retain the password after the code is issued', async () => {
    mockProfile(false);
    renderCard();
    await userEvent.type(await screen.findByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /create recovery code/i }));
    await screen.findByTestId('recovery-code-value');

    // While the code is displayed the field is unmounted, so asserting on the
    // detached node proves nothing. Dismiss the code and check the field that
    // comes back: the component never unmounts, so a password still in state
    // would reappear here.
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /i have saved it/i }));

    const field = (await screen.findByLabelText(/password/i)) as HTMLInputElement;
    expect(field.value).toBe('');
  });

  it('FE-RECOV-006: warns that replacing invalidates the previous code', async () => {
    mockProfile(true);
    renderCard();
    // A profile that already has a code gets Replace wording, not Create.
    expect(await screen.findByRole('button', { name: /replace recovery code/i })).toBeInTheDocument();
    expect(screen.getByTestId('recovery-code-replace-warning')).toBeInTheDocument();
  });

  it('FE-RECOV-007: the mutation cache keeps neither the password nor the code after success', async () => {
    mockProfile(false);
    const { queryClient } = renderCard();
    const password = watchCacheFor(queryClient, 'hunter2hunter2');
    const code = watchCacheFor(queryClient, CODE);

    await userEvent.type(await screen.findByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /create recovery code/i }));
    expect(await screen.findByTestId('recovery-code-value')).toHaveTextContent(CODE);

    // The cache did hold both, so the assertions below can fail.
    expect(password.seen.value).toBe(true);
    expect(code.seen.value).toBe(true);
    password.unsubscribe();
    code.unsubscribe();

    await waitFor(() => {
      expect(cachedMutationsContaining(queryClient, 'hunter2hunter2')).toBe(0);
      expect(cachedMutationsContaining(queryClient, CODE)).toBe(0);
    });
    // The code is still on screen: it lives in component state, not the cache.
    expect(screen.getByTestId('recovery-code-value')).toHaveTextContent(CODE);
  });

  it('FE-RECOV-008: the mutation cache drops the password after a failed attempt', async () => {
    mockProfile(false);
    vi.mocked(api.apiPost).mockRejectedValue(new Error('Incorrect password'));
    const { queryClient } = renderCard();
    const password = watchCacheFor(queryClient, 'wrongpassword1');

    await userEvent.type(await screen.findByLabelText(/password/i), 'wrongpassword1');
    await userEvent.click(screen.getByRole('button', { name: /create recovery code/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect password/i);

    expect(password.seen.value).toBe(true);
    password.unsubscribe();

    await waitFor(() => {
      expect(cachedMutationsContaining(queryClient, 'wrongpassword1')).toBe(0);
    });
    // The user can try again: the mutation is idle, not stuck pending.
    expect(screen.getByRole('button', { name: /create recovery code/i })).toBeEnabled();
  });
});
