/**
 * FE-BKUP-001/002 — restore form hygiene and what happens after a restore.
 *
 * Restore is the most destructive control in Settings, and two things about it
 * were wrong: the password typed for one backup carried over to another, and a
 * successful restore left the user signed in against a vault whose sealed keys
 * had just been replaced underneath them.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BackupCard } from '@/components/settings/BackupCard';
import { RESTORE_NOTICE_KEY, BACKUP_RESTORE_CONFIRMATION } from '@/services/backup';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

const backups = [
  { backup_id: 'backup_a', created_at: '2026-07-01T10:00:00Z', file_count: 3, size_bytes: 2048 },
  { backup_id: 'backup_b', created_at: '2026-07-20T10:00:00Z', file_count: 4, size_bytes: 4096 },
];

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BackupCard />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('FE-BKUP: restore flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
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
      return Promise.resolve({
        backups,
        backup_directory: '/data/backups/profile-123',
        last_backup_at: null,
      });
    });
  });

  it('FE-BKUP-001: opening a second backup starts with an empty form', async () => {
    const user = userEvent.setup();
    renderCard();

    const openRestore = async (index: number) => {
      const buttons = await screen.findAllByRole('button', { name: /restore…/i });
      await user.click(buttons[index]);
    };

    await openRestore(0);
    const firstPassword = screen.getByLabelText(/confirm your password/i);
    await user.type(firstPassword, 'PasswordForA1');
    expect(firstPassword).toHaveValue('PasswordForA1');

    await openRestore(1);

    // A destructive form pre-filled with a password meant for a different
    // snapshot is exactly the wrong kind of convenience.
    expect(screen.getByLabelText(/confirm your password/i)).toHaveValue('');
    expect(screen.getByPlaceholderText(BACKUP_RESTORE_CONFIRMATION)).toHaveValue('');
  });

  it('FE-BKUP-002: a successful restore ends the session and says why', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockResolvedValue({
      files_restored: 5,
      safety_copy_count: 5,
    });

    renderCard();

    const buttons = await screen.findAllByRole('button', { name: /restore…/i });
    await user.click(buttons[0]);

    await user.type(screen.getByLabelText(/confirm your password/i), 'CorrectHorse1');
    await user.type(
      screen.getByPlaceholderText(BACKUP_RESTORE_CONFIRMATION),
      BACKUP_RESTORE_CONFIRMATION
    );
    await user.click(screen.getByRole('button', { name: /restore this backup/i }));

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    // The reason has to outlive the page, or the sign-out reads as data loss.
    expect(window.sessionStorage.getItem(RESTORE_NOTICE_KEY)).toMatch(/restored from a backup/i);
  });
});
