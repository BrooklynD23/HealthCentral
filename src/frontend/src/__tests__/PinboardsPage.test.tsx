import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PinboardsPage } from '@/pages/PinboardsPage';

const resetExport = vi.fn();
const idleMutation = { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false };

vi.mock('@/services', () => ({
  usePinboards: () => ({
    data: [
      { id: 'board-a', name: 'Board A', created_at: '', updated_at: '' },
      { id: 'board-b', name: 'Board B', created_at: '', updated_at: '' },
    ],
    isLoading: false,
  }),
  usePinboardItems: () => ({ data: [] }),
  useCreatePinboard: () => idleMutation,
  useRenamePinboard: () => idleMutation,
  useDeletePinboard: () => idleMutation,
  useRemovePinboardItem: () => idleMutation,
  useExportPinboard: () => ({
    ...idleMutation,
    reset: resetExport,
    data: {
      packet_id: 'packet-from-board-a', profile_id: 'p1', generated_at: '',
      section_titles: [], markdown: '# Pinboard Packet', redaction_count: 0,
    },
  }),
  downloadVisitPrep: vi.fn(),
}));

describe('PinboardsPage', () => {
  it('FE-PIN-PAGE-001: switching boards clears confirmation and stale download', async () => {
    const user = userEvent.setup();
    render(<PinboardsPage />);

    const confirm = screen.getByRole('checkbox');
    await user.click(confirm);
    expect(confirm).toBeChecked();

    await user.click(screen.getByRole('button', { name: 'Board B' }));

    await waitFor(() => expect(confirm).not.toBeChecked());
    expect(screen.getByRole('button', { name: 'Create packet' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: /download/i })).not.toBeInTheDocument();
  });
});
