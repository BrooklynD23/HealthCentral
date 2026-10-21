/**
 * AGENT-ENABLED-TOGGLE: Settings switch for agent_enabled (HC-AET-FE-001..002).
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
});
