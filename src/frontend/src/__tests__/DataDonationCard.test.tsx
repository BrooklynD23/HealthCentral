/**
 * RSI1-DONATE PR-1: consent card (HC-DON-FE-001..003).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
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

function consents(grantedPurposes: string[] = [], stalePurposes: string[] = []) {
  return {
    consents: PURPOSES.map((purpose) => ({
      purpose,
      granted: grantedPurposes.includes(purpose),
      consent_text_version: grantedPurposes.includes(purpose) ? CONSENT_TEXT_VERSION : null,
      current: grantedPurposes.includes(purpose) && !stalePurposes.includes(purpose),
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
      // DON-COPY-R1: covers answers rated before and after agreeing.
      expect(description).toMatch(/chat answers I have rated or will rate/);
    }
    expect(PURPOSE_COPY.fine_tune.description).toContain(
      'This also allows a redacted training file saved on this device.',
    );
  });

  it('HC-DON-FE-006: the redaction caveat does not over-claim numeric dates', () => {
    expect(CONSENT_INTRO).not.toMatch(/dates written as numbers/i);
    expect(CONSENT_INTRO).toMatch(/can miss/i);
    expect(CONSENT_INTRO).toMatch(/2024-03-15/);
  });

  it('HC-DON-FE-007: the intro says stopping does not change a model already tuned', () => {
    expect(CONSENT_INTRO).toMatch(/already tuned/i);
    expect(CONSENT_INTRO).toMatch(/not changed/i);
    expect(CONSENT_INTRO).toMatch(/exported/i);
  });

  it('HC-DON-FE-008: a failed save shows a neutral error while the refetch shows the saved state', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiGet)
      .mockResolvedValueOnce(consents())
      .mockResolvedValue(consents(['fine_tune']));
    vi.mocked(api.apiPut).mockRejectedValue(new Error('audit write failed'));
    renderCard();
    const switches = await screen.findAllByRole('switch');
    await user.click(switches[0]);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/could not confirm your choice/i);
    expect(alert).toHaveTextContent(/reload to see what was saved/i);
    expect(alert).not.toHaveTextContent(/could not save/i);
    expect(alert).not.toHaveTextContent(/audit write failed/i);
    await waitFor(() =>
      expect(screen.getAllByRole('switch')[0]).toHaveAttribute('aria-checked', 'true'),
    );
  });

  it('HC-DON-FE-009: a stale consent offers Review and re-confirm, which grants and never stops', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiGet).mockResolvedValue(consents(['fine_tune', 'agent_traces'], ['fine_tune']));
    vi.mocked(api.apiPut).mockResolvedValue({
      purpose: 'fine_tune', granted: true, consent_text_version: CONSENT_TEXT_VERSION, deleted_count: 0,
    });
    renderCard();
    await screen.findAllByRole('switch');
    expect(screen.getByRole('switch', { name: PURPOSE_COPY.fine_tune.label })).toHaveAttribute('aria-checked', 'true');
    expect(
      screen.getAllByText(
        'The wording above changed after you agreed. Nothing new is donated for this purpose until you review it and re-confirm.',
      ),
    ).toHaveLength(1);
    // A current granted purpose shows no re-confirm button.
    expect(screen.getAllByRole('button', { name: /review and re-confirm/i })).toHaveLength(1);
    expect(screen.getAllByRole('button', { name: /stop and delete/i })).toHaveLength(2);

    await user.click(
      screen.getByRole('button', { name: `Review and re-confirm: ${PURPOSE_COPY.fine_tune.label}` }),
    );
    await waitFor(() => expect(api.apiPut).toHaveBeenCalledTimes(1));
    expect(api.apiPut).toHaveBeenCalledWith('/donation/consents/fine_tune', {
      granted: true,
      consent_text_version: CONSENT_TEXT_VERSION,
    });
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});

// HC-DON-FE-010: the owner approved this exact copy as version 2026-10-20-v2
// (DON-COPY, 2026-10-20). Changing any word must also change the version and
// get a new owner approval, so this pin fails until both happen.
describe('approved consent copy (DON-COPY)', () => {
  it('HC-DON-FE-010: copy matches the approved text for its version', () => {
    expect(CONSENT_TEXT_VERSION).toBe('2026-10-20-v2');
    expect(CONSENT_INTRO).toBe([
      'Donating is optional and off by default. You choose each purpose separately, and you can change your mind at any time.',
      'Your data never leaves this device. Before anything is stored as a donated copy, it goes through strict automatic redaction, which removes labelled names and some dates such as 03/15/2024. It can miss other date formats such as 2024-03-15, and names or dates written out in free text, so please keep that in mind.',
      'If you stop, the donated copies for that purpose are deleted. Your own records are not touched. A model already tuned with the copies, or a file already exported from them, is not changed.',
      'Nothing here is medical advice. Donated copies only help improve this app.',
    ].join('\n\n'));
    expect(PURPOSE_COPY).toEqual({
      fine_tune: {
        label: 'Improve the assistant model',
        description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave, to tune the model on this device. This also allows a redacted training file saved on this device.',
      },
      synthetic_seed: {
        label: 'Create practice data',
        description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave as a starting point for practice data that a model on this device rewrites from them. Some details may carry over. It is kept apart from real data and never replaces it.',
      },
      agent_traces: {
        label: 'Find assistant mistakes',
        description: 'For chat answers I have rated or will rate, use redacted copies of my question, the answer and any correction I gave to find and fix the assistant’s mistakes.',
      },
    });
  });
});
