/**
 * A11Y-CRIT-LABELS: accessible names for the /explain date-range inputs,
 * the /settings time-zone select and the /settings external provider select.
 *
 * Each test asserts the element's tagName, so a label bound to the wrong
 * node (or to nothing) fails here rather than only in the axe e2e scan.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExplainAssistant } from '@/pages/ExplainAssistant';
import { SettingsPage } from '@/pages/SettingsPage';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>();
  return {
    ...actual,
    apiGet: vi.fn(async () => []),
    apiPost: vi.fn(),
  };
});

vi.mock('framer-motion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('framer-motion')>();
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<object>) => (
        <div {...props}>{children}</div>
      ),
      button: ({ children, ...props }: React.PropsWithChildren<object>) => (
        <button {...props}>{children}</button>
      ),
    },
    AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
  };
});

// SettingsPage reads these hooks. Only the external-API query needs a value;
// the rest are inert so the page renders without a backend.
let mockExternalApiData: { use_external_api: boolean } | undefined;
vi.mock('@/services', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services')>();
  const query = () => ({ data: undefined, isLoading: false, isError: false });
  const mutation = () => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false });
  return {
    ...actual,
    useModelSettings: query,
    useTiers: query,
    useDetectHardware: mutation,
    useSetTier: mutation,
    useStartDownload: mutation,
    useDownloadProgress: query,
    useExternalApiSettings: () => ({ data: mockExternalApiData, isError: false }),
    useSaveExternalApiSettings: mutation,
    useTimezone: query,
    useSaveTimezone: mutation,
    useVoiceSettings: query,
    useSaveVoiceSettings: mutation,
    useSaveOcrPreference: mutation,
    useEnvironmentDiagnostics: query,
    useRecheckDiagnostics: mutation,
  };
});

vi.mock('@/services/modelSettings', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/modelSettings')>();
  return {
    ...actual,
    useGamificationSettings: () => ({ data: undefined }),
    useSaveGamificationSettings: () => ({ mutate: vi.fn(), isPending: false }),
  };
});

vi.mock('@/services/feedback', () => ({
  useFeedbackStats: () => ({ data: undefined }),
  useExportDataset: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSubmitFeedback: () => ({ mutate: vi.fn(), isPending: false }),
  FEEDBACK_TAGS: [],
}));
vi.mock('@/components/MemoryManager', () => ({ MemoryManager: () => null }));
// HC-A11YCL-005 renders the real MemoryManager via importActual; its hooks are
// stubbed here so it renders the loaded state with no backend.
vi.mock('@/services/memory', () => ({
  useMemoryItems: () => ({ data: [], isLoading: false, isError: false }),
  useCreateMemoryItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateMemoryItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteMemoryItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock('@/components/settings/BackupCard', () => ({ BackupCard: () => null }));
vi.mock('@/components/settings/RecoveryCodeCard', () => ({ RecoveryCodeCard: () => null }));
vi.mock('@/components/settings/DangerZone', () => ({ DangerZone: () => null }));
vi.mock('@/components/settings/AgentSettingsCard', () => ({ AgentSettingsCard: () => null }));

function renderExplain() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ExplainAssistant />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

/** /settings opens on one section at a time: the time zone is in `preferences`, the provider in `assistant-privacy`. */
function renderSettings(section: 'preferences' | 'assistant-privacy') {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[`/settings?section=${section}`]}>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('A11Y-CRIT-LABELS accessible names', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
    mockExternalApiData = undefined;
  });

  afterEach(() => {
    mockExternalApiData = undefined;
  });

  it('HC-A11YCL-001: explain date-range inputs are named From date and To date', () => {
    const { container } = renderExplain();
    const dateInputs = container.querySelectorAll<HTMLInputElement>('input[type="date"]');

    const from = screen.getByLabelText('From date');
    const to = screen.getByLabelText('To date');

    expect(from.tagName).toBe('INPUT');
    expect(to.tagName).toBe('INPUT');
    expect(from).toBe(dateInputs[0]);
    expect(to).toBe(dateInputs[1]);
  });

  it('HC-A11YCL-002: settings time-zone control is named Time zone and is a SELECT', () => {
    renderSettings('preferences');

    const timezone = screen.getByLabelText('Time zone');

    expect(timezone.tagName).toBe('SELECT');
  });

  it('HC-A11YCL-003: settings external provider control is named by its Provider label and is a SELECT', () => {
    mockExternalApiData = { use_external_api: true };
    renderSettings('assistant-privacy');

    const provider = screen.getByLabelText('Provider', { selector: 'select' });

    expect(provider.tagName).toBe('SELECT');
  });

  it('HC-A11YCL-004: external API Key and Model inputs are named by their labels', () => {
    mockExternalApiData = { use_external_api: true };
    renderSettings('assistant-privacy');

    const apiKey = screen.getByLabelText('API Key', { selector: 'input' });
    const model = screen.getByLabelText('Model', { selector: 'input' });

    expect(apiKey).toHaveAttribute('type', 'password');
    expect(model).toHaveAttribute('type', 'text');
  });

  it('HC-A11YCL-005: memory add-form fields are named Key, Value and Category', async () => {
    const { MemoryManager } = await vi.importActual<
      typeof import('@/components/MemoryManager')
    >('@/components/MemoryManager');
    render(<MemoryManager />);

    fireEvent.click(screen.getByRole('button', { name: 'Add' }));

    expect(screen.getByLabelText('Key', { selector: 'input' }).tagName).toBe('INPUT');
    expect(screen.getByLabelText('Value', { selector: 'textarea' }).tagName).toBe('TEXTAREA');
    expect(screen.getByLabelText('Category', { selector: 'select' }).tagName).toBe('SELECT');
  });
});
