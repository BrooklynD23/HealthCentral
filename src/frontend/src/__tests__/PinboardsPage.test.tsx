import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PinboardsPage } from '@/pages/PinboardsPage';

const resetExport = vi.fn();
const refetchList = vi.fn();
const refetchItems = vi.fn();
const pinState = vi.hoisted(() => ({
  list: 'ok' as 'ok' | 'empty' | 'error',
  items: 'ok' as 'ok' | 'error',
}));
const idleMutation = { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false };

vi.mock('@/services', () => ({
  usePinboards: () =>
    pinState.list === 'error'
      ? { data: undefined, isLoading: false, isError: true, refetch: refetchList }
      : {
          data: pinState.list === 'empty' ? [] : [
            { id: 'board-a', name: 'Board A', created_at: '', updated_at: '' },
            { id: 'board-b', name: 'Board B', created_at: '', updated_at: '' },
          ],
          isLoading: false,
        },
  usePinboardItems: () =>
    pinState.items === 'error'
      ? { data: undefined, isError: true, refetch: refetchItems }
      : { data: [] },
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

describe('PinboardsPage load failures', () => {
  beforeEach(() => {
    pinState.list = 'ok';
    pinState.items = 'ok';
    refetchList.mockClear();
    refetchItems.mockClear();
  });

  it('HC-PINLF-001: a refused list shows an error card, not "No pinboards yet"', () => {
    pinState.list = 'error';
    render(<PinboardsPage />);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveAttribute('data-t0');
    expect(within(alert).getByText('Could not load pinboards')).toBeInTheDocument();
    expect(within(alert).getByText('Something went wrong loading your pinboards. Please try again.')).toBeInTheDocument();
    expect(screen.queryByText('No pinboards yet')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Board A' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('New pinboard name')).toBeInTheDocument();
  });

  it('HC-PINLF-002: refused items show an inline error, not "No pinned items yet."', async () => {
    const user = userEvent.setup();
    pinState.items = 'error';
    render(<PinboardsPage />);
    await user.click(screen.getByRole('button', { name: 'Board A' }));

    const alert = screen.getByRole('alert');
    expect(within(alert).getByText('Could not load the pinned items. Please try again.')).toBeInTheDocument();
    expect(screen.queryByText('No pinned items yet.')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(refetchItems).toHaveBeenCalledTimes(1);
  });

  it('HC-PINLF-003: Try again refetches the list once and focus moves to the name box', async () => {
    const user = userEvent.setup();
    pinState.list = 'error';
    render(<PinboardsPage />);

    await user.click(screen.getByRole('button', { name: 'Try again' }));

    expect(refetchList).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('New pinboard name')).toHaveFocus();
  });

  it('HC-PINLF-004: a real empty list still shows "No pinboards yet"', () => {
    pinState.list = 'empty';
    render(<PinboardsPage />);

    expect(screen.getByText('No pinboards yet')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
