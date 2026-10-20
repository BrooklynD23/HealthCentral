/**
 * RSI1-DONATE PR-1: consent card (HC-DON-FE-001..003).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DataDonationCard, CONSENT_TEXT_VERSION, PURPOSE_COPY, CONSENT_INTRO } from '@/components/settings/DataDonationCard';
import * as api from '@/services/api';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

const PURPOSES = ['fine_tune', 'synthetic_seed', 'agent_traces'] as const;

function consents(grantedPurposes: string[] = []) {
  return {
    consents: PURPOSES.map((purpose) => ({
      purpose,
      granted: grantedPurposes.includes(purpose),
      consent_text_version: grantedPurposes.includes(purpose) ? CONSENT_TEXT_VERSION : null,
      granted_at: null,
      revoked_at: null,
    })),
  };
}

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DataDonationCard />
    </QueryClientProvider>,
  );
}

describe('DataDonationCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('HC-DON-FE-001: every switch starts off', async () => {
    vi.mocked(api.apiGet).mockResolvedValue(consents());
    renderCard();
    const switches = await screen.findAllByRole('switch');
    expect(switches).toHaveLength(3);
    for (const s of switches) expect(s).toHaveAttribute('aria-checked', 'false');
    expect(screen.queryByRole('button', { name: /stop and delete/i })).not.toBeInTheDocument();
  });

  it('HC-DON-FE-002: a toggle sends PUT with the right purpose', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiGet).mockResolvedValue(consents());
    vi.mocked(api.apiPut).mockResolvedValue({
      purpose: 'synthetic_seed',
      granted: true,
      consent_text_version: CONSENT_TEXT_VERSION,
      deleted_count: 0,
    });
    renderCard();
    const switches = await screen.findAllByRole('switch');
    await user.click(switches[1]);
    expect(api.apiPut).toHaveBeenCalledTimes(1);
    expect(api.apiPut).toHaveBeenCalledWith('/donation/consents/synthetic_seed', {
      granted: true,
      consent_text_version: CONSENT_TEXT_VERSION,
    });
  });

  it('HC-DON-FE-003: Stop and delete confirms, revokes and shows the count', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiGet).mockResolvedValue(consents(['fine_tune']));
    vi.mocked(api.apiPut).mockResolvedValue({
      purpose: 'fine_tune',
      granted: false,
      consent_text_version: CONSENT_TEXT_VERSION,
      deleted_count: 7,
    });
    renderCard();
    await user.click(await screen.findByRole('button', { name: /stop and delete/i }));
    // Nothing is sent until the user confirms.
    expect(api.apiPut).not.toHaveBeenCalled();
    const dialog = screen.getByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: /yes, stop and delete/i }));
    expect(api.apiPut).toHaveBeenCalledWith('/donation/consents/fine_tune', {
      granted: false,
      consent_text_version: CONSENT_TEXT_VERSION,
    });
    expect(await screen.findByRole('status')).toHaveTextContent(/7 donated copies were deleted/i);
  });

  it('HC-DON-FE-004: a failed load shows an error, not false off switches', async () => {
    vi.mocked(api.apiGet).mockRejectedValue(new Error('boom'));
    renderCard();
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not load/i);
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });

  it('HC-DON-FE-005: every purpose names question, answer, correction and redaction', async () => {
    vi.mocked(api.apiGet).mockResolvedValue(consents());
    renderCard();
    await screen.findAllByRole('switch');
    for (const purpose of PURPOSES) {
      const { label, description } = PURPOSE_COPY[purpose];
      for (const re of [/question/i, /answer/i, /correction/i, /redacted/i]) {
        expect(description).toMatch(re);
      }
      // The same words must be what the patient actually sees.
      // Screen readers get it too: the switch is described by the same text.
      expect(screen.getByRole('switch', { name: label })).toHaveAccessibleDescription(description);
    }
  });

  it('HC-DON-FE-006: the redaction caveat does not over-claim numeric dates', () => {
    expect(CONSENT_INTRO).not.toMatch(/dates written as numbers/i);
    expect(CONSENT_INTRO).toMatch(/can miss/i);
    expect(CONSENT_INTRO).toMatch(/2024-03-15/);
  });
});
