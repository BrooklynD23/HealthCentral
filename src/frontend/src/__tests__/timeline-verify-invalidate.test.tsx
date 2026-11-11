/**
 * TIMELINE-VERIFY-INVALIDATE (HC-TVI-001…005)
 *
 * The timeline view caches every query for 5 minutes (App.tsx staleTime).
 * Verifying an observation flips the card's "Needs verification" badge and
 * medication mutations add/remove medication_start/medication_stop events —
 * so those mutations must invalidate the ['timeline'] key or TimelinePage
 * shows stale clinical status for up to 5 minutes.
 *
 * Each test mounts a real useTimeline() observer (TimelineProbe) on the same
 * QueryClient as the mutation under test and asserts /timeline/ is fetched a
 * second time after the mutation succeeds. staleTime mirrors App.tsx: without
 * the invalidation the mounted query stays fresh and never refetches.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import { useVerifyObservation } from '@/services/observations';
import {
  useCreateMedication,
  useUpdateMedication,
  useDeleteMedication,
} from '@/services/medications';
import { useTimeline } from '@/services/timeline';
import type { TimelineFilters } from '@/services/timeline';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

function TimelineProbe({ filters }: { filters?: TimelineFilters }) {
  useTimeline(filters);
  return <div>timeline-probe</div>;
}

function setup() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 300_000 } },
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <TimelineProbe />
      {children}
    </QueryClientProvider>
  );
  return { queryClient, wrapper };
}

const timelineFetches = () =>
  vi.mocked(api.apiGet).mock.calls.filter((c) => c[0] === '/timeline/');

describe('timeline invalidation on mutation success', () => {
  beforeEach(() => {
    vi.mocked(api.apiGet).mockReset();
    vi.mocked(api.apiPost).mockReset();
    vi.mocked(api.apiPatch).mockReset();
    vi.mocked(api.apiDelete).mockReset();
    vi.mocked(api.apiGet).mockResolvedValue({ events: [], undated: [] });
  });

  it('HC-TVI-001: verifying an observation refetches the timeline', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({});
    const { wrapper } = setup();
    const { result } = renderHook(() => useVerifyObservation(), { wrapper });
    await waitFor(() => expect(timelineFetches()).toHaveLength(1));

    await act(async () => {
      await result.current.mutateAsync({ observationId: 'o-1', data: {} });
    });

    await waitFor(() => expect(timelineFetches()).toHaveLength(2));
  });

  it('HC-TVI-002: creating a medication refetches the timeline', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({});
    const { wrapper } = setup();
    const { result } = renderHook(() => useCreateMedication(), { wrapper });
    await waitFor(() => expect(timelineFetches()).toHaveLength(1));

    await act(async () => {
      await result.current.mutateAsync({ name: 'Amoxicillin' });
    });

    await waitFor(() => expect(timelineFetches()).toHaveLength(2));
  });

  it('HC-TVI-003: updating a medication refetches the timeline', async () => {
    vi.mocked(api.apiPatch).mockResolvedValue({});
    const { wrapper } = setup();
    const { result } = renderHook(() => useUpdateMedication(), { wrapper });
    await waitFor(() => expect(timelineFetches()).toHaveLength(1));

    await act(async () => {
      await result.current.mutateAsync({
        medicationId: 'm-1',
        data: { ended_at: '2024-06-01' },
      });
    });

    await waitFor(() => expect(timelineFetches()).toHaveLength(2));
  });

  it('HC-TVI-004: deleting a medication refetches the timeline', async () => {
    vi.mocked(api.apiDelete).mockResolvedValue(undefined);
    const { wrapper } = setup();
    const { result } = renderHook(() => useDeleteMedication(), { wrapper });
    await waitFor(() => expect(timelineFetches()).toHaveLength(1));

    await act(async () => {
      await result.current.mutateAsync({ medicationId: 'm-1' });
    });

    await waitFor(() => expect(timelineFetches()).toHaveLength(2));
  });

  it('HC-TVI-005: existing invalidations still fire; [timeline] prefix-matches filtered keys', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({});
    vi.mocked(api.apiPatch).mockResolvedValue({});
    vi.mocked(api.apiDelete).mockResolvedValue(undefined);
    const { queryClient, wrapper } = setup();
    const spy = vi.spyOn(queryClient, 'invalidateQueries');

    // Pins: verify still invalidates its pre-existing keys.
    const { result: verify } = renderHook(() => useVerifyObservation(), { wrapper });
    await act(async () => {
      await verify.current.mutateAsync({ observationId: 'o-1', data: {} });
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: ['observations'] });
    expect(spy).toHaveBeenCalledWith({ queryKey: ['documents'] });

    // Pins: the medication mutations still invalidate their existing keys.
    spy.mockClear();
    const { result: create } = renderHook(() => useCreateMedication(), { wrapper });
    await act(async () => {
      await create.current.mutateAsync({ name: 'Amoxicillin' });
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: ['medications'] });

    spy.mockClear();
    const { result: update } = renderHook(() => useUpdateMedication(), { wrapper });
    await act(async () => {
      await update.current.mutateAsync({
        medicationId: 'm-1',
        data: { name: 'Ibuprofen' },
      });
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: ['medications', 'm-1'] });
    expect(spy).toHaveBeenCalledWith({ queryKey: ['medications'] });

    // The ['timeline'] invalidation prefix-matches filtered timeline keys.
    const filteredKey = ['timeline', { event_type: 'medication_start' }];
    queryClient.setQueryData(filteredKey, { events: [], undated: [] });
    expect(queryClient.getQueryState(filteredKey)?.isInvalidated).toBe(false);

    const { result: del } = renderHook(() => useDeleteMedication(), { wrapper });
    await act(async () => {
      await del.current.mutateAsync({ medicationId: 'm-1' });
    });
    expect(queryClient.getQueryState(filteredKey)?.isInvalidated).toBe(true);
  });
});
