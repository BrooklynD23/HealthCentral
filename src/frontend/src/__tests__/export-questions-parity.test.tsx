/**
 * EXPORT-QUESTIONS-PARITY (HC-EQP-FE-001 to 005): the download carries what the preview shows.
 *
 * The backend half (the stored questions equal POST /export/questions) is tests/test_export_questions_parity.py.
 * Here: a failed questions load unticks and locks the Questions box so the download leaves the stored questions out,
 * and the preview, the Full Preview sheet and Copy Text drop trend questions when Trends is unticked, as the
 * download's omit_trends does. Blind spot: the api module is mocked, so this pins what the page hands to
 * apiGetRaw/apiPost, not what the backend returns.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExportPage } from '@/pages/ExportPage';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
  apiPost: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

URL.createObjectURL = vi.fn(() => 'blob:mock-url');
URL.revokeObjectURL = vi.fn();
HTMLAnchorElement.prototype.click = vi.fn();

const summaryResponse = {
  summary_id: 'summary-123',
  profile_id: 'profile-123',
  generated_at: '2024-01-15T12:00:00Z',
  format: 'text',
  key_findings: ['Hemoglobin A1c: 6.5% (H)'],
  abnormal_count: 1,
  date_range: 'All time',
};

const ABNORMAL_Q = 'My hemoglobin A1c was outside the reference range. What might that indicate?';
const TREND_Q = 'My glucose has been up. Should I be concerned?';
const TASK_Q = 'The note says: "Call the clinic". Can you clarify when and with whom this should happen?';
const questionItems = [
  { category: 'abnormal', question: ABNORMAL_Q, context: 'c1', related_analytes: ['hemoglobin_a1c'], source_kind: 'observation', source_id: 'o1' },
  { category: 'trend', question: TREND_Q, context: 'c2', related_analytes: ['glucose'], source_kind: 'trend', source_id: 'glucose' },
  { category: 'clarification', question: TASK_Q, context: 'c3', related_analytes: [], source_kind: 'care_task', source_id: 't1' },
];

const LOAD_FAILED_LINE = /Questions could not be loaded, so they are left out of the download\./;
const DOWNLOAD_URL = '/export/doctor-summary/summary-123/download';

type PostImpl = (url: string, ...rest: unknown[]) => Promise<unknown>;

function setupApi({ questionsFail = false }: { questionsFail?: boolean } = {}) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url.startsWith('/documents')) return Promise.resolve([]);
    if (url.startsWith('/observations')) return Promise.resolve([]);
    return Promise.resolve(null);
  });
  vi.mocked(api.apiGetRaw).mockImplementation(() =>
    Promise.resolve({
      headers: new Headers({ 'Content-Type': 'text/plain' }),
      text: () => Promise.resolve('x'),
      blob: () => Promise.resolve(new Blob(['x'], { type: 'text/plain' })),
    } as Response)
  );
  vi.mocked(api.apiPost).mockImplementation(((url: string) => {
    if (url === '/export/doctor-summary') return Promise.resolve(summaryResponse);
    if (url === '/export/questions') {
      return questionsFail ? Promise.reject(new Error('questions down')) : Promise.resolve(questionItems);
    }
    return Promise.resolve(null);
  }) as PostImpl);
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ExportPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

const questionsBox = () => screen.getByRole('checkbox', { name: 'Questions for Clinician' });
const trendsBox = () => screen.getByRole('checkbox', { name: 'Trend Analysis' });

async function generate(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: /generate summary/i }));
  await screen.findByRole('button', { name: /download summary/i });
}

async function download(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: /download summary/i }));
  await waitFor(() => expect(api.apiGetRaw).toHaveBeenCalledTimes(1));
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
});

describe('a failed questions load leaves the questions out of the download', () => {
  it('HC-EQP-FE-001: the questions call rejects: box unticked and disabled, the line shows, Download omits the questions', async () => {
    const user = userEvent.setup();
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    setupApi({ questionsFail: true });
    renderPage();

    await user.click(questionsBox());
    expect(questionsBox()).toBeChecked();
    await generate(user);

    expect(screen.getByText('Health Summary Report')).toBeInTheDocument();
    expect(questionsBox()).not.toBeChecked();
    expect(questionsBox()).toBeDisabled();
    expect(screen.getByText(LOAD_FAILED_LINE)).toBeInTheDocument();

    await download(user);
    expect(api.apiGetRaw).toHaveBeenCalledWith(DOWNLOAD_URL, { format: 'text', omit_questions: 'true' });
    consoleError.mockRestore();
  });

  it('HC-EQP-FE-002: the questions call succeeds: the box stays enabled and untick / re-tick behave as HC-EDQ-003/005', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await user.click(questionsBox());
    await generate(user);
    expect(await screen.findByText(ABNORMAL_Q)).toBeInTheDocument();
    expect(questionsBox()).toBeEnabled();
    expect(questionsBox()).toBeChecked();
    expect(screen.queryByText(LOAD_FAILED_LINE)).not.toBeInTheDocument();

    await user.click(questionsBox());
    await download(user);
    expect(api.apiGetRaw).toHaveBeenLastCalledWith(DOWNLOAD_URL, { format: 'text', omit_questions: 'true' });

    vi.mocked(api.apiGetRaw).mockClear();
    await user.click(questionsBox());
    expect(questionsBox()).toBeChecked();
    await download(user);
    expect(api.apiGetRaw).toHaveBeenLastCalledWith(DOWNLOAD_URL, { format: 'text' });
  });

  it('HC-EQP-FE-003: generated without Questions: the box is disabled after generating, and Download sends the plain format', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    expect(questionsBox()).toBeEnabled(); // before the first generate it behaves as it did
    await generate(user);

    expect(questionsBox()).toBeDisabled();
    expect(questionsBox()).not.toBeChecked();
    expect(screen.queryByText(LOAD_FAILED_LINE)).not.toBeInTheDocument();
    await user.click(questionsBox()); // a click on a disabled box changes nothing
    expect(questionsBox()).not.toBeChecked();
    expect(screen.queryByText(ABNORMAL_Q)).not.toBeInTheDocument();

    await download(user);
    expect(api.apiGetRaw).toHaveBeenCalledWith(DOWNLOAD_URL, { format: 'text' });
  });

  it('HC-EQP-FE-005: fail, then the next visit (remount) succeeds: no state leaks between mounts', async () => {
    const user = userEvent.setup();
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    setupApi({ questionsFail: true });
    const first = renderPage();
    await user.click(questionsBox());
    await generate(user);
    expect(questionsBox()).toBeDisabled();
    expect(screen.getByText(LOAD_FAILED_LINE)).toBeInTheDocument();
    first.unmount();

    setupApi();
    renderPage();
    expect(questionsBox()).toBeEnabled();
    expect(questionsBox()).not.toBeChecked();
    expect(screen.queryByText(LOAD_FAILED_LINE)).not.toBeInTheDocument();

    await user.click(questionsBox());
    await generate(user);
    expect(await screen.findByText(ABNORMAL_Q)).toBeInTheDocument();
    expect(questionsBox()).toBeEnabled();
    expect(questionsBox()).toBeChecked();
    expect(screen.queryByText(LOAD_FAILED_LINE)).not.toBeInTheDocument();
    await download(user);
    expect(api.apiGetRaw).toHaveBeenCalledWith(DOWNLOAD_URL, { format: 'text' });
    consoleError.mockRestore();
  });
});

describe('HC-EQP-FE-004: Trends unticked after generating hides trend questions everywhere the page shows questions', () => {
  it('the preview, the Full Preview sheet and Copy Text lose the trend question; the other questions stay', async () => {
    const user = userEvent.setup();
    setupApi();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    renderPage();

    await user.click(questionsBox());
    await generate(user);
    // Trends on (the default): every question shows, and Copy Text carries the trend line.
    expect(await screen.findByText(TREND_Q)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /copy text/i }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    expect(writeText.mock.calls[0][0]).toContain(`- ${TREND_Q}`);

    await user.click(trendsBox());

    expect(screen.queryByText(TREND_Q)).not.toBeInTheDocument();
    expect(screen.getByText(ABNORMAL_Q)).toBeInTheDocument();
    expect(screen.getByText(TASK_Q)).toBeInTheDocument();

    // The button reads "Copied!" for two seconds after a copy.
    await user.click(screen.getByRole('button', { name: /copy text|copied/i }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(2));
    const copied = writeText.mock.calls[1][0] as string;
    expect(copied).not.toContain(TREND_Q);
    expect(copied).toContain(`- ${ABNORMAL_Q}`);
    expect(copied).toContain(`- ${TASK_Q}`);

    await user.click(screen.getByRole('button', { name: /full preview/i }));
    const dialog = await screen.findByRole('dialog', { name: 'Full summary preview' });
    expect(within(dialog).queryByText(TREND_Q)).not.toBeInTheDocument();
    expect(within(dialog).getByText(ABNORMAL_Q)).toBeInTheDocument();
    expect(within(dialog).getByText(TASK_Q)).toBeInTheDocument();
  });
});
