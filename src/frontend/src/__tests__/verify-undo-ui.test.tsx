/**
 * VERIFY-UNDO-UI: HC-VUU-001 to HC-VUU-006. The "is now marked as checked" toast on /verify carries an Undo, and
 * Undo calls POST /observations/:id/unverify (VERIFY-UNDO, flag-only).
 *
 * Written red first. The mocks follow ui-review.test.tsx: notify and the API are replaced, the rest renders for real.
 * Each test says what it would not notice.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VerificationWorkbench } from '@/pages/VerificationWorkbench';
import * as api from '@/services/api';
import { notify } from '@/components/ui/toast';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/components/ui/toast', () => ({ notify: vi.fn(), AppToaster: () => null }));

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

vi.mock('@/services/highlights', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/highlights')>()),
  useDocumentHighlights: () => ({ data: [] }),
}));

type Row = {
  id: string;
  analyte_raw: string;
  analyte_canonical: string;
  value: number;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  flag: string | null;
  is_abnormal: boolean;
  collected_at: string | null;
  user_verified: boolean;
  [key: string]: unknown;
};

const glucose: Row = {
  id: 'obs-1',
  profile_id: 'profile-123',
  doc_id: 'doc-1',
  analyte_canonical: 'glucose',
  analyte_raw: 'Glucose',
  value: 95,
  value_text: null,
  unit: 'mg/dL',
  ref_low: 70,
  ref_high: 100,
  ref_range_text: null,
  flag: null,
  is_abnormal: false,
  collected_at: '2026-04-10T00:00:00',
  user_verified: false,
  extraction_confidence: 0.9,
  source_page: null,
  source_bbox_json: null,
};
const hba1c: Row = {
  ...glucose,
  id: 'obs-2',
  analyte_canonical: 'hba1c',
  analyte_raw: 'Hemoglobin A1c',
  value: 6.5,
  unit: '%',
  ref_low: 4.0,
  ref_high: 5.6,
  flag: 'H',
  is_abnormal: true,
};

const state = { observations: [] as Row[] };

/** What the two routes do to the stored row, so the next GET /observations/ agrees (needs_verification drops checked rows). */
function mockApi({ unverifyRejects = false }: { unverifyRejects?: boolean } = {}) {
  vi.mocked(api.apiGet).mockImplementation(async (url: string, params?: Record<string, string>) => {
    if (url === '/documents' || url === '/documents/') return [];
    if (url.startsWith('/documents')) return [];
    if (url.startsWith('/observations')) {
      return params?.needs_verification === 'true'
        ? state.observations.filter((row) => !row.user_verified)
        : state.observations;
    }
    return [];
  });
  vi.mocked(api.apiPost).mockImplementation(async (url: string) => {
    const match = /\/observations\/([^/]+)\/(verify|unverify)$/.exec(url);
    if (!match) throw new Error(`not stubbed: ${url}`);
    const [, id, verb] = match;
    if (verb === 'unverify' && unverifyRejects) {
      throw new api.ApiError(409, 'Conflict', 'Observation is not verified');
    }
    const saved = { ...state.observations.find((row) => row.id === id)!, user_verified: verb === 'verify' };
    state.observations = state.observations.map((row) => (row.id === id ? saved : row));
    return saved;
  });
}

function renderWorkbench() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidate = vi.spyOn(queryClient, 'invalidateQueries');
  render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <VerificationWorkbench />
      </BrowserRouter>
    </QueryClientProvider>
  );
  return { queryClient, invalidate };
}

const rowOf = (id: string) => document.getElementById(`observation-row-${id}`) as HTMLElement;

async function verifyGlucose(user: ReturnType<typeof userEvent.setup>) {
  await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
  await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
}

/** The Undo handler the page handed to notify. Calling it is what clicking the toast's button does. */
function undoOf(call = 0): () => void | Promise<void> {
  const action = vi.mocked(notify).mock.calls[call][0].action;
  if (!action) throw new Error('the toast has no action');
  return action.onClick;
}

const unverifyPosts = () =>
  vi.mocked(api.apiPost).mock.calls.filter(([url]) => String(url).endsWith('/unverify'));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(notify).mockReset();
  localStorage.clear();
  useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
  state.observations = [glucose, hba1c];
  mockApi();
});

describe('HC-VUU-001: the checked toast offers Undo', () => {
  // Blind spot: the mocked notify records the call. That sonner draws the action as a button is UI-PRIM-FEEDBACK's test.
  it('notify gets a still message and an Undo action', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await verifyGlucose(user);
    expect(vi.mocked(notify).mock.calls[0][0]).toEqual({
      message: 'Glucose, Apr 10, 2026 is now marked as checked',
      still: true,
      action: { label: 'Undo', onClick: expect.any(Function) },
    });
  });
});

describe('HC-VUU-002: Undo sends one unverify and the row reads "Not yet checked" again', () => {
  // Blind spot: the mock answers like the API (flag-only). The real route's audit and document status are backend tests.
  it('POSTs /observations/obs-1/unverify once, then toasts, and the row is unchecked after the refetch', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await verifyGlucose(user);
    await waitFor(() => expect(within(rowOf('obs-1')).getByText('Checked by you')).toBeInTheDocument());

    await act(async () => {
      await undoOf()();
    });

    expect(unverifyPosts()).toEqual([['/observations/obs-1/unverify', {}]]);
    expect(notify).toHaveBeenCalledTimes(2);
    expect(vi.mocked(notify).mock.calls[1][0]).toEqual({
      message: 'Glucose, Apr 10, 2026 is no longer marked as checked',
      still: true,
    });
    // The hold must let go of the row: a held copy would keep it as ink over the refetched, unverified row.
    await waitFor(() => expect(within(rowOf('obs-1')).getByText('Not yet checked')).toBeInTheDocument());
    expect(within(rowOf('obs-1')).queryByText('Checked by you')).toBeNull();
  });
});

describe('HC-VUU-003: Undo invalidates what Verify does', () => {
  // Blind spot: it reads the invalidation calls, not that each query then refetches. React Query owns that.
  it('invalidates observations, documents and timeline', async () => {
    const user = userEvent.setup();
    const { invalidate } = renderWorkbench();
    await screen.findByText('Glucose');
    await verifyGlucose(user);
    invalidate.mockClear();

    await act(async () => {
      await undoOf()();
    });

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['observations'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['documents'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['timeline'] });
  });
});

describe('HC-VUU-004: a refused Undo says so and leaves the row checked', () => {
  // Blind spot: the 409 is a rejected promise from a mock. That the backend sends 409 for an empty undo is its own test.
  it('shows the failure toast and the row still reads "Checked by you"', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await verifyGlucose(user);
    mockApi({ unverifyRejects: true });

    await act(async () => {
      await undoOf()();
    });

    expect(notify).toHaveBeenCalledTimes(2);
    expect(vi.mocked(notify).mock.calls[1][0]).toEqual({
      message: 'Could not undo. Glucose is still marked as checked.',
    });
    expect(within(rowOf('obs-1')).getByText('Checked by you')).toBeInTheDocument();
    expect(within(rowOf('obs-1')).queryByText('Not yet checked')).toBeNull();
  });
});

describe('HC-VUU-005: two quick clicks on one Undo send one request', () => {
  // Blind spot: it guards one toast's button. Two toasts (verify, undo, verify again) are two buttons, and the
  // server's 409 covers a second undo of the same flag.
  it('a second click while the first is in flight sends nothing', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await verifyGlucose(user);

    const undo = undoOf();
    await act(async () => {
      await Promise.all([undo(), undo()]);
    });

    expect(unverifyPosts()).toHaveLength(1);
    expect(notify).toHaveBeenCalledTimes(2);
  });
});

describe('HC-VUU-006: a row with no date drops the date in both toasts', () => {
  // Blind spot: a null date only. An unparseable string takes the same branch (formatCollectedDate).
  it('says "Glucose is now ..." and "Glucose is no longer ..."', async () => {
    state.observations = [{ ...glucose, collected_at: null }, hba1c];
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await verifyGlucose(user);
    expect(vi.mocked(notify).mock.calls[0][0].message).toBe('Glucose is now marked as checked');

    await act(async () => {
      await undoOf()();
    });

    expect(vi.mocked(notify).mock.calls[1][0]).toEqual({
      message: 'Glucose is no longer marked as checked',
      still: true,
    });
  });
});
