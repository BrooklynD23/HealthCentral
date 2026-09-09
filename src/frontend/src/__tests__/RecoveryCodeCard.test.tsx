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
  return render(
    <QueryClientProvider client={queryClient}>
      <RecoveryCodeCard />
    </QueryClientProvider>
  );
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
});
