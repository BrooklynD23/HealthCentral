/**
 * VerificationWorkbench edit dialog: strict numeric parse + handled save failure.
 * FE-VERIFY-NUMERIC (HC-FVN-001..005)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VerificationWorkbench } from '@/pages/VerificationWorkbench';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
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

function defaultApiGetMock(observations: unknown[]) {
  return (url: string) => {
    if (url.startsWith('/documents') && url.includes('/pages')) {
      return Promise.resolve([
        { page_number: 1, text: 'Glucose: 95 mg/dL (70-100)', has_tables: true },
      ]);
    }
    if (url.startsWith('/documents')) return Promise.resolve([]);
    if (url.startsWith('/observations')) return Promise.resolve(observations);
    return Promise.resolve([]);
  };
}

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
}

const mockObservations = [
  {
    id: 'obs-1',
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 95,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 100,
    flag: null,
    is_abnormal: false,
    user_verified: false,
    extraction_confidence: 0.9,
  },
];

const VERIFY_URL = '/observations/obs-1/verify';

function verifyCalls() {
  return vi.mocked(api.apiPost).mock.calls.filter((c) => c[0] === VERIFY_URL);
}

async function openEditDialog() {
  const user = userEvent.setup();
  renderWithProviders(<VerificationWorkbench />);
  await waitFor(() => expect(screen.getByText('Glucose')).toBeInTheDocument());
  await user.click(screen.getAllByLabelText('Edit value')[0]);
  const dialog = await screen.findByRole('dialog');
  const input = within(dialog).getByRole('textbox');
  return { user, dialog, input };
}

async function typeValue(
  user: ReturnType<typeof userEvent.setup>,
  input: HTMLElement,
  text: string
) {
  await user.clear(input);
  await user.type(input, text);
}

describe('VerificationWorkbench edit dialog (FE-VERIFY-NUMERIC)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
    vi.mocked(api.apiGet).mockImplementation(defaultApiGetMock(mockObservations));
    vi.mocked(api.apiPost).mockResolvedValue({ ...mockObservations[0], user_verified: true });
  });

  it('HC-FVN-001: 7,5 shows a dot-for-decimals error and sends no verify request', async () => {
    const { user, dialog, input } = await openEditDialog();
    await typeValue(user, input, '7,5');

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'Use a dot for decimals'
    );
    await user.click(within(dialog).getByRole('button', { name: /save & verify/i }));
    expect(verifyCalls()).toHaveLength(0);

    // Control: fixing the input does send a request.
    await typeValue(user, input, '7.5');
    await user.click(within(dialog).getByRole('button', { name: /save & verify/i }));
    await waitFor(() => expect(verifyCalls()).toHaveLength(1));
    expect(verifyCalls()[0][1]).toEqual({ value: 7.5, value_text: undefined });
  });

  it('HC-FVN-002: 7.5abc shows an error and sends no verify request', async () => {
    const { user, dialog, input } = await openEditDialog();
    await typeValue(user, input, '7.5abc');

    expect(await within(dialog).findByRole('alert')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /save & verify/i }));
    expect(verifyCalls()).toHaveLength(0);

    // Control: fixing the input does send a request.
    await typeValue(user, input, '7.5');
    await user.click(within(dialog).getByRole('button', { name: /save & verify/i }));
    await waitFor(() => expect(verifyCalls()).toHaveLength(1));
  });

  it('HC-FVN-003: 7.5 sends value 7.5 (pin; green on main)', async () => {
    const { user, dialog, input } = await openEditDialog();
    await typeValue(user, input, '7.5');
    await user.click(within(dialog).getByRole('button', { name: /save & verify/i }));

    await waitFor(() => expect(verifyCalls()).toHaveLength(1));
    const payload = verifyCalls()[0][1] as { value?: number; value_text?: string };
    expect(payload.value).toBe(7.5);
    expect(payload.value_text).toBeUndefined();
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('HC-FVN-004: <0.5 sends value_text "<0.5" (pin; green on main)', async () => {
    const { user, dialog, input } = await openEditDialog();
    await typeValue(user, input, '<0.5');
    await user.click(within(dialog).getByRole('button', { name: /save & verify/i }));

    await waitFor(() => expect(verifyCalls()).toHaveLength(1));
    const payload = verifyCalls()[0][1] as { value?: number; value_text?: string };
    expect(payload.value_text).toBe('<0.5');
    expect(payload.value).toBeUndefined();
  });

  it('HC-FVN-005: a rejected save shows the server detail and keeps the dialog open', async () => {
    const unhandled: unknown[] = [];
    const onUnhandled = (reason: unknown) => unhandled.push(reason);
    process.on('unhandledRejection', onUnhandled);
    try {
      vi.mocked(api.apiPost).mockRejectedValue(
        new api.ApiError(500, 'Internal Server Error', 'Verify failed: db locked')
      );
      const { user, dialog, input } = await openEditDialog();
      await typeValue(user, input, '7.5');
      await user.click(within(dialog).getByRole('button', { name: /save & verify/i }));

      expect(await within(dialog).findByText(/Verify failed: db locked/)).toBeInTheDocument();
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      await new Promise((r) => setTimeout(r, 50));
      expect(unhandled).toEqual([]);
    } finally {
      process.off('unhandledRejection', onUnhandled);
    }
  });
});
