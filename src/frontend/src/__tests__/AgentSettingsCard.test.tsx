/**
 * AGENT-ENABLED-TOGGLE: Settings switch for agent_enabled (HC-AET-FE-001..004).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AgentSettingsCard } from '@/components/settings/AgentSettingsCard';
import * as api from '@/services/api';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AgentSettingsCard />
    </QueryClientProvider>,
  );
}

describe('AgentSettingsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([true, false])('HC-AET-FE-001: the switch reflects agent_enabled=%s', async (value) => {
    vi.mocked(api.apiGet).mockResolvedValue({ agent_enabled: value });
    renderCard();
    const toggle = await screen.findByRole('switch');
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', String(value)));
    expect(
      screen.getByText(
        'Use the step-by-step assistant. When off, answers come from the simpler search path.',
      ),
    ).toBeInTheDocument();
  });

  it('HC-AET-FE-002: clicking the switch PATCHes the new value', async () => {
    vi.mocked(api.apiGet).mockResolvedValue({ agent_enabled: true });
    vi.mocked(api.apiPatch).mockResolvedValue({ agent_enabled: false });
    renderCard();
    const toggle = await screen.findByRole('switch');
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    await userEvent.click(toggle);
    await waitFor(() =>
      expect(api.apiPatch).toHaveBeenCalledWith('/settings/model/agent', { agent_enabled: false }),
    );
  });

  it('HC-AET-FE-003: a failed save shows an alert and keeps the stored value', async () => {
    vi.mocked(api.apiGet).mockResolvedValue({ agent_enabled: true });
    vi.mocked(api.apiPatch).mockRejectedValue(new Error('boom'));
    renderCard();
    const toggle = await screen.findByRole('switch');
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    await userEvent.click(toggle);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not save this setting. Try again.',
    );
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
  });

  it('HC-AET-FE-004a: no switch shows as on while settings load', () => {
    vi.mocked(api.apiGet).mockReturnValue(new Promise(() => {}));
    renderCard();
    expect(screen.queryByRole('switch', { checked: true })).not.toBeInTheDocument();
    expect(screen.getByText('Loading your assistant setting...')).toBeInTheDocument();
  });

  it('HC-AET-FE-004b: a failed load shows an alert and no switch', async () => {
    vi.mocked(api.apiGet).mockRejectedValue(new Error('boom'));
    renderCard();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load this setting. Reload to try again.',
    );
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });
});
