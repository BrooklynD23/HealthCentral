/**
 * RCC-2: recovery (SEC-RECOV-001) must not leave the old recovery code, the
 * new password, or the rotated code in the mutation cache, nor the typed code
 * and password in page state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RecoverProfile } from '@/pages/RecoverProfile';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import {
  cachedMutationsContaining,
  watchCacheFor,
  reactStateContains,
} from './support/secretRetention';

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

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const OLD_CODE = 'AAAA-BBBB-CCCC-DDDD-EEEE-FFFF-GGGG-HHHH';
const NEW_PASSWORD = 'NewPass123';
const ROTATED = 'R0TA-TEDC-0DEX-YZ12-3456-7890-ABCD-EFGH';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RecoverProfile />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { ...utils, queryClient };
}

async function fill(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(await screen.findByLabelText('Profile'), 'profile-1');
  await user.type(screen.getByLabelText('Recovery code'), OLD_CODE);
  await user.type(screen.getByLabelText('New password'), NEW_PASSWORD);
}

describe('RCC-2: RecoverProfile secret retention', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().clearAuth();
    vi.mocked(api.apiGet).mockResolvedValue([
      {
        id: 'profile-1',
        display_name: 'Test',
        has_password: true,
        has_recovery_code: true,
        created_at: '2026-01-01T00:00:00',
      },
    ]);
  });

  it('FE-RCC2-003: after recovery nothing keeps the old code, the new password or the rotated code', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockResolvedValueOnce({
      access_token: 'tok',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: 'profile-1',
      profile_name: 'Test',
      recovery_code: ROTATED,
    });
    const { queryClient, container } = renderPage();
    const oldCode = watchCacheFor(queryClient, OLD_CODE);
    const pw = watchCacheFor(queryClient, NEW_PASSWORD);
    const rotated = watchCacheFor(queryClient, ROTATED);

    await fill(user);
    expect(reactStateContains(container, OLD_CODE)).toBe(true); // positive control
    expect(reactStateContains(container, NEW_PASSWORD)).toBe(true); // positive control
    await user.click(screen.getByRole('button', { name: /unlock my records/i }));

    expect(await screen.findByTestId('recovery-code')).toHaveTextContent(ROTATED);
    expect(oldCode.seen.value).toBe(true);
    expect(pw.seen.value).toBe(true);
    expect(rotated.seen.value).toBe(true);
    [oldCode, pw, rotated].forEach((w) => w.unsubscribe());

    await waitFor(() => {
      expect(cachedMutationsContaining(queryClient, OLD_CODE)).toBe(0);
      expect(cachedMutationsContaining(queryClient, NEW_PASSWORD)).toBe(0);
      expect(cachedMutationsContaining(queryClient, ROTATED)).toBe(0);
    });
    expect(reactStateContains(container, OLD_CODE)).toBe(false);
    expect(reactStateContains(container, NEW_PASSWORD)).toBe(false);
    expect(screen.getByTestId('recovery-code')).toHaveTextContent(ROTATED);
  });

  it('FE-RCC2-004: a rejected code leaves nothing in the cache, and a retry is clean too', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('That recovery code is not valid.'));
    const { queryClient } = renderPage();
    const oldCode = watchCacheFor(queryClient, OLD_CODE);

    await fill(user);
    await user.click(screen.getByRole('button', { name: /unlock my records/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/not valid/i);
    expect(oldCode.seen.value).toBe(true);
    oldCode.unsubscribe();
    await waitFor(() => {
      expect(cachedMutationsContaining(queryClient, OLD_CODE)).toBe(0);
      expect(cachedMutationsContaining(queryClient, NEW_PASSWORD)).toBe(0);
    });

    vi.mocked(api.apiPost).mockResolvedValueOnce({
      access_token: 'tok',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: 'profile-1',
      profile_name: 'Test',
      recovery_code: ROTATED,
    });
    await user.click(screen.getByRole('button', { name: /unlock my records/i }));
    expect(await screen.findByTestId('recovery-code')).toHaveTextContent(ROTATED);
    await waitFor(() => {
      expect(cachedMutationsContaining(queryClient, OLD_CODE)).toBe(0);
      expect(cachedMutationsContaining(queryClient, ROTATED)).toBe(0);
    });
  });
});
