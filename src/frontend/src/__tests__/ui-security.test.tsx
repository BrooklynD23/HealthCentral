/**
 * UI-PG-SECURITY (HC-UISEC-003): the restore and delete confirmations are AlertDialogs.
 *
 * Each dialog must close on Escape, hold focus inside while open, hand focus back to the
 * button that opened it, and open with Cancel focused (AlertDialog moves focus to the
 * element marked `data-alert-cancel`). Before this row both confirmations were inline forms:
 * there was no dialog to find, so every check below fails on main at `findByRole('alertdialog')`.
 *
 * Would not notice: jsdom has no layout, so Tab order is the DOM order user-event computes
 * (see ui-overlays.test.tsx HC-UIOV-002). The `outside.focus()` assertion is what catches a
 * non-modal dialog, because `loop` alone keeps 25 Tabs inside either way.
 *
 * HC-UISEC-001 and HC-UISEC-002 are e2e pins against the real backend: e2e/ui-security.spec.ts.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen, waitFor, within, type RenderResult } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { LazyMotion, MotionConfig, domAnimation } from 'framer-motion';
import { SecuritySection } from '@/pages/settings/SecuritySection';
import { BACKUP_RESTORE_CONFIRMATION } from '@/services/backup';
import { PROFILE_DELETE_CONFIRMATION } from '@/services/profiles';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

const backups = [
  { backup_id: 'backup_a', created_at: '2026-07-01T10:00:00Z', file_count: 3, size_bytes: 2048 },
  { backup_id: 'backup_b', created_at: '2026-07-20T10:00:00Z', file_count: 4, size_bytes: 4096 },
];

/** The providers the app mounts, with the DOM features loaded: without them the exit path never runs. */
function Providers({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LazyMotion features={domAnimation} strict>
          <MotionConfig reducedMotion="user">{children}</MotionConfig>
        </LazyMotion>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function renderSection(): RenderResult {
  return render(<SecuritySection />, { wrapper: Providers });
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({
    token: 'tok',
    profileId: 'profile-123',
    profileName: 'Jane',
    isAuthenticated: true,
  });
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url.includes('schedule')) {
      return Promise.resolve({
        enabled: false,
        frequency: 'off',
        retention_days: 30,
        last_run_at: null,
        last_result: 'never_run',
        last_file_count: 0,
      });
    }
    if (url.includes('profiles')) {
      return Promise.resolve([{ id: 'profile-123', display_name: 'Jane', has_recovery_code: false }]);
    }
    return Promise.resolve({
      backups,
      backup_directory: '/data/backups/profile-123',
      last_backup_at: null,
    });
  });
});

interface DialogCase {
  name: string;
  /** The button that opens the dialog. Looked up fresh each time: it is hidden while the dialog is open. */
  trigger: () => Promise<HTMLElement>;
}

const DIALOGS: DialogCase[] = [
  {
    name: 'restore',
    trigger: async () => (await screen.findAllByRole('button', { name: /restore…/i }))[0],
  },
  {
    name: 'delete',
    trigger: async () => screen.findByRole('button', { name: /delete profile/i }),
  },
];

describe.each(DIALOGS)('HC-UISEC-003 the $name confirmation is an AlertDialog', ({ trigger }) => {
  it('opens as an alertdialog with Cancel focused', async () => {
    const user = userEvent.setup();
    renderSection();
    await user.click(await trigger());

    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus();
  });

  it('closes on Escape and focus returns to the button that opened it', async () => {
    const user = userEvent.setup();
    renderSection();
    const opener = await trigger();
    await user.click(opener);
    await screen.findByRole('alertdialog');

    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument(), {
      timeout: 2000,
    });
    // Radix returns focus in a setTimeout(0) after unmount, so the check waits for it.
    await waitFor(() => expect(opener).toHaveFocus(), { timeout: 1000 });
  });

  it('keeps focus inside over 25 Tabs, and pulls it back from outside', async () => {
    const user = userEvent.setup();
    renderSection();
    const opener = await trigger();
    await user.click(opener);
    const dialog = await screen.findByRole('alertdialog');

    for (let press = 1; press <= 25; press += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement), `focus after Tab ${press}`).toBe(true);
    }

    // Focus moved outside without Tab: the focus trap must return it to the dialog.
    act(() => opener.focus());
    expect(dialog.contains(document.activeElement), 'focus after opener.focus()').toBe(true);
    expect(opener).not.toHaveFocus();
  });
});

describe('HC-UISEC-003 the delete steps keep their order and the typed phrase', () => {
  it('lists the copy checkbox, then the password, then the phrase, and needs all three', async () => {
    const user = userEvent.setup();
    renderSection();
    await user.click(await screen.findByRole('button', { name: /delete profile/i }));
    const dialog = await screen.findByRole('alertdialog');

    const checkbox = within(dialog).getByLabelText(/i confirm i have a copy/i);
    const password = within(dialog).getByLabelText(/confirm your password/i);
    const phrase = within(dialog).getByPlaceholderText(PROFILE_DELETE_CONFIRMATION);
    const follows = (a: HTMLElement, b: HTMLElement) =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    expect(follows(checkbox, password), 'checkbox before password').toBe(true);
    expect(follows(password, phrase), 'password before phrase').toBe(true);

    const remove = within(dialog).getByRole('button', { name: /permanently delete this profile/i });
    expect(remove).toBeDisabled();
    await user.click(checkbox);
    await user.type(password, 'Whatever123');
    expect(remove, 'no phrase yet').toBeDisabled();
    await user.type(phrase, PROFILE_DELETE_CONFIRMATION);
    expect(remove).toBeEnabled();
    // The phrase is the whole gate: one character off and it locks again.
    await user.type(phrase, 'x');
    expect(remove, 'wrong phrase').toBeDisabled();
  });

  it('needs the password and the exact phrase to restore', async () => {
    const user = userEvent.setup();
    renderSection();
    await user.click((await screen.findAllByRole('button', { name: /restore…/i }))[0]);
    const dialog = await screen.findByRole('alertdialog');

    const restore = within(dialog).getByRole('button', { name: /restore this backup/i });
    expect(restore).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/confirm your password/i), 'Whatever123');
    expect(restore, 'no phrase yet').toBeDisabled();
    await user.type(within(dialog).getByPlaceholderText(BACKUP_RESTORE_CONFIRMATION), BACKUP_RESTORE_CONFIRMATION);
    expect(restore).toBeEnabled();
  });
});

describe('HC-UISEC-003 T0 marking (plan 2.7): warnings and errors carry data-t0', () => {
  it('marks the restore warning and its error', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Incorrect password'));
    renderSection();
    await user.click((await screen.findAllByRole('button', { name: /restore…/i }))[0]);
    const dialog = await screen.findByRole('alertdialog');

    expect(within(dialog).getByText(/this replaces your current data/i).closest('[data-t0]')).not.toBeNull();
    expect(within(dialog).getByText(/restoring rolls this profile back/i).closest('[data-t0]')).not.toBeNull();

    await user.type(within(dialog).getByLabelText(/confirm your password/i), 'WrongHorse1');
    await user.type(within(dialog).getByPlaceholderText(BACKUP_RESTORE_CONFIRMATION), BACKUP_RESTORE_CONFIRMATION);
    await user.click(within(dialog).getByRole('button', { name: /restore this backup/i }));
    const alert = await within(dialog).findByRole('alert');
    expect(alert).toHaveTextContent(/incorrect password/i);
    expect(alert).toHaveAttribute('data-t0');
  });

  it('marks the delete warning and its error', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiDelete).mockRejectedValueOnce(new Error('Incorrect password'));
    renderSection();
    // The section's own warning, before any dialog opens.
    const intro = (await screen.findByText(/this removes your encrypted health record/i)).closest('[data-t0]');
    expect(intro).not.toBeNull();

    await user.click(await screen.findByRole('button', { name: /delete profile/i }));
    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByText(/deleting also removes the backups/i).closest('[data-t0]')).not.toBeNull();

    await user.click(within(dialog).getByLabelText(/i confirm i have a copy/i));
    await user.type(within(dialog).getByLabelText(/confirm your password/i), 'WrongPass1');
    await user.type(within(dialog).getByPlaceholderText(PROFILE_DELETE_CONFIRMATION), PROFILE_DELETE_CONFIRMATION);
    await user.click(within(dialog).getByRole('button', { name: /permanently delete this profile/i }));
    const alert = await within(dialog).findByRole('alert');
    expect(alert).toHaveTextContent(/incorrect password/i);
    expect(alert).toHaveAttribute('data-t0');
  });

  it('marks the recovery code, its once warning and its replace warning', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiGet).mockImplementation((url: string) => {
      if (url.includes('profiles')) {
        return Promise.resolve([{ id: 'profile-123', display_name: 'Jane', has_recovery_code: true }]);
      }
      return Promise.resolve({ backups: [], backup_directory: '', last_backup_at: null });
    });
    vi.mocked(api.apiPost).mockResolvedValueOnce({ recovery_code: '1111-2222-3333' });
    renderSection();

    expect(await screen.findByTestId('recovery-code-replace-warning')).toHaveAttribute('data-t0');
    await user.type(screen.getByLabelText(/confirm your password/i), 'Whatever123');
    await user.click(screen.getByRole('button', { name: /replace recovery code/i }));
    expect(await screen.findByTestId('recovery-code-value')).toHaveAttribute('data-t0');
    expect(screen.getByTestId('recovery-code-once-warning')).toHaveAttribute('data-t0');
  });

  it('marks the intro warnings of the recovery code and backup cards', async () => {
    renderSection();
    expect(
      (await screen.findByText(/a forgotten password means the health record in this profile cannot be recovered/i)).closest(
        '[data-t0]'
      )
    ).not.toBeNull();
    expect(
      (await screen.findByText(/it is the only thing that survives losing this machine/i)).closest('[data-t0]')
    ).not.toBeNull();
  });

  it('marks the "backup is damaged" warning (it is a backup warning, plan 2.7)', async () => {
    // Would not notice: the intact-backup message. This is the one that tells the patient a backup cannot be trusted.
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockResolvedValueOnce({ valid: false, files_checked: 3, errors: ['a.db', 'b.db'] });
    renderSection();
    await user.click((await screen.findAllByRole('button', { name: 'Check' }))[0]);
    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent('This backup is damaged: 2 problem(s) found.');
    expect(status).toHaveAttribute('data-t0');
  });
});

describe('HC-UISEC-003 the recovery code keeps its groups whole', () => {
  it('renders each group in its own non-breaking span and keeps the code as textContent', async () => {
    // Would not notice: a long code at 320 px. jsdom has no layout, so this checks the markup that keeps a group
    // on one line (as components/profile/RecoveryCodeCard.tsx does), and the textContent that recovery-code.spec.ts reads.
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockResolvedValueOnce({ recovery_code: 'ABCD-EFGH-JKLM-NPQR' });
    renderSection();
    await user.type(await screen.findByLabelText(/confirm your password/i), 'Whatever123');
    await user.click(screen.getByRole('button', { name: /create recovery code/i }));
    const value = await screen.findByTestId('recovery-code-value');
    expect(value.textContent).toBe('ABCD-EFGH-JKLM-NPQR');
    const groups = value.querySelectorAll('[data-code-group]');
    expect(Array.from(groups).map((node) => node.textContent)).toEqual(['ABCD', 'EFGH', 'JKLM', 'NPQR']);
    groups.forEach((node) => expect(node).toHaveClass('whitespace-nowrap'));
    expect(value).not.toHaveClass('break-all');
  });
});

describe('HC-UISEC-003 closing the restore dialog drops its error', () => {
  it('does not leave "Incorrect password" in the card after Escape', async () => {
    // Would not notice: an error that mounts again in the card, out of context, once the dialog that raised it is gone.
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Incorrect password'));
    renderSection();
    await user.click((await screen.findAllByRole('button', { name: /restore…/i }))[0]);
    const dialog = await screen.findByRole('alertdialog');
    await user.type(within(dialog).getByLabelText(/confirm your password/i), 'WrongHorse1');
    await user.type(within(dialog).getByPlaceholderText(BACKUP_RESTORE_CONFIRMATION), BACKUP_RESTORE_CONFIRMATION);
    await user.click(within(dialog).getByRole('button', { name: /restore this backup/i }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/incorrect password/i);

    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument(), { timeout: 2000 });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText(/incorrect password/i)).not.toBeInTheDocument();
  });
});
