/**
 * Model Settings Service Contract Tests
 *
 * TDD scaffolding for HC-REM-001:
 * Frontend service paths must match backend router mount at /settings/model.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import {
  useModelSettings,
  useTiers,
  useStartDownload,
  useSaveExternalApiSettings,
} from '@/services/modelSettings';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}));

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
}

function ModelSettingsProbe() {
  useModelSettings();
  return <div>model-settings-probe</div>;
}

function TiersProbe() {
  useTiers();
  return <div>tiers-probe</div>;
}

function StartDownloadProbe() {
  const mutation = useStartDownload();
  return (
    <button onClick={() => mutation.mutate('low')}>
      start-download
    </button>
  );
}

function SaveExternalApiProbe() {
  const mutation = useSaveExternalApiSettings();
  return (
    <button
      onClick={() =>
        mutation.mutate({
          use_external_api: true,
          provider: 'openai',
          api_key: 'sk-test',
          consent_acknowledged: true,
        })
      }
    >
      save-external-api
    </button>
  );
}

describe('ModelSettings service route contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.apiPut).mockResolvedValue({
      use_external_api: true,
      provider: 'openai',
      model: '',
      api_key_configured: true,
    });

    vi.mocked(api.apiGet).mockImplementation((endpoint: string) => {
      if (endpoint.endsWith('/tiers')) {
        return Promise.resolve({
          tiers: [],
          recommended_tier: 'low',
        });
      }

      return Promise.resolve({
        current_tier: 'low',
        preferred_tier: 'low',
        recommended_tier: 'low',
        auto_detect_enabled: true,
        hardware_info: {
          ram_total_gb: 16,
          ram_available_gb: 8,
          cpu_cores: 8,
          cpu_name: 'Test CPU',
          disk_free_gb: 100,
          gpu_available: false,
          gpu_vram_gb: null,
          gpu_name: null,
          recommended_tier: 'low',
          max_supported_tier: 'mid',
          detection_timestamp: new Date().toISOString(),
        },
        tier_availability: {},
      });
    });

    vi.mocked(api.apiPost).mockResolvedValue({
      success: true,
      tier: 'low',
      status: 'pending',
    });
  });

  it('FE-SETTINGS-API-001: useModelSettings should call /settings/model', async () => {
    renderWithProviders(<ModelSettingsProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/settings/model');
  });

  it('FE-SETTINGS-API-002: useTiers should call /settings/model/tiers', async () => {
    renderWithProviders(<TiersProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/settings/model/tiers');
  });

  it('FE-SETTINGS-API-003: useStartDownload should post to /settings/model/download', async () => {
    const user = userEvent.setup();
    renderWithProviders(<StartDownloadProbe />);

    await user.click(screen.getByRole('button', { name: /start-download/i }));

    await waitFor(() => {
      expect(api.apiPost).toHaveBeenCalled();
    });

    expect(api.apiPost).toHaveBeenCalledWith('/settings/model/download', { tier: 'low' });
  });

  it('FE-SETTINGS-API-004: useSaveExternalApiSettings should PUT to /settings/model/external-api', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SaveExternalApiProbe />);

    await user.click(screen.getByRole('button', { name: /save-external-api/i }));

    await waitFor(() => {
      expect(api.apiPut).toHaveBeenCalled();
    });

    expect(api.apiPut).toHaveBeenCalledWith('/settings/model/external-api', {
      use_external_api: true,
      provider: 'openai',
      api_key: 'sk-test',
      consent_acknowledged: true,
    });
  });
});
