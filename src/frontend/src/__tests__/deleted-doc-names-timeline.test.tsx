/**
 * DELETED-DOC-NAMES-TIMELINE (HC-DDNT-001..005)
 *
 * Document mutations must expire every filtered timeline cache while preserving
 * the existing document and observation invalidations.
 */

import type { PropsWithChildren } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import * as api from '@/services/api';
import {
  useDeleteDocument,
  useImportDocument,
  useReprocessDocument,
  useVerifyDocument,
} from '@/services/documents';
import { useTimeline } from '@/services/timeline';
import type { TimelineResponse } from '@/services/timeline';
import type { Observation } from '@/services/types';
import { TimelinePage } from '@/pages/TimelinePage';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/api')>()),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
  apiUpload: vi.fn(),
}));

const PROFILE_ID = 'profile-1';
const timelineKey = ['timeline', { event_type: 'lab_results' }] as const;
const apiGet = vi.mocked(api.apiGet);
const apiPost = vi.mocked(api.apiPost);
const apiDelete = vi.mocked(api.apiDelete);
const apiUpload = vi.mocked(api.apiUpload);

const observations: Observation[] = [
  {
    id: 'o-1',
    profile_id: PROFILE_ID,
    doc_id: 'doc-1',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 95,
    value_text: null,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 100,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2026-11-07T00:00:00',
    user_verified: true,
    extraction_confidence: 0.99,
    source_page: 1,
    source_bbox_json: null,
  },
  {
    id: 'o-2',
    profile_id: PROFILE_ID,
    doc_id: 'doc-1',
    analyte_canonical: 'ldl',
    analyte_raw: 'LDL',
    value: 90,
    value_text: null,
    unit: 'mg/dL',
    ref_low: null,
    ref_high: 100,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2026-11-07T00:00:00',
    user_verified: true,
    extraction_confidence: 0.99,
    source_page: 1,
    source_bbox_json: null,
  },
];

const populatedTimeline: TimelineResponse = {
  events: [
    {
      event_id: 'event-1',
      event_type: 'lab_results',
      event_date: '2026-11-07',
      event_date_source: 'document_date',
      title: 'Lab results (2 analytes)',
      doc_id: 'doc-1',
      related_ids: ['o-1', 'o-2'],
      verification_status: 'verified',
    },
  ],
  undated: [],
};

const emptyTimeline: TimelineResponse = { events: [], undated: [] };
let timelineAnswer = populatedTimeline;
let observationAnswer = observations;

function appClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 300_000 },
      mutations: { retry: false },
    },
  });
}

function wrapperFor(client: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function renderTimeline(client: QueryClient) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/timeline']}>
        <TimelinePage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function timelineCalls() {
  return apiGet.mock.calls.filter(([path]) => path === '/timeline/').length;
}

function seedExistingCaches(client: QueryClient) {
  client.setQueryData(['documents'], { seeded: true });
  client.setQueryData(['observations'], { seeded: true });
  client.setQueryData(timelineKey, { seeded: true });
}

function expectExistingCachesInvalidated(client: QueryClient) {
  expect(client.getQueryState(['documents'])?.isInvalidated).toBe(true);
  expect(client.getQueryState(['observations'])?.isInvalidated).toBe(true);
}

function expectNoCacheInvalidated(client: QueryClient) {
  expect(client.getQueryState(['documents'])?.isInvalidated).toBe(false);
  expect(client.getQueryState(['observations'])?.isInvalidated).toBe(false);
  expect(client.getQueryState(timelineKey)?.isInvalidated).toBe(false);
}

beforeEach(() => {
  timelineAnswer = populatedTimeline;
  observationAnswer = observations;
  apiGet.mockImplementation((async (path: string) => {
    if (path === '/timeline/') return timelineAnswer;
    if (path === '/observations/') return observationAnswer;
    if (path === '/pinboards/') return [];
    throw new Error(`unmocked GET ${path}`);
  }) as never);
  apiPost.mockResolvedValue({} as never);
  apiDelete.mockResolvedValue(undefined as never);
  apiUpload.mockResolvedValue({} as never);
  useAuthStore.getState().setAuth({
    token: 'test-token',
    profileId: PROFILE_ID,
    profileName: 'Test Profile',
  });
});

describe('DELETED-DOC-NAMES-TIMELINE', () => {
  it('HC-DDNT-001: deleting a document removes its cached timeline card and analyte names', async () => {
    const client = appClient();
    const firstVisit = renderTimeline(client);

    await screen.findByText('Lab results (2 analytes)');
    expect(screen.getByText('Glucose, LDL')).toBeInTheDocument();
    firstVisit.unmount();

    client.setQueryData(timelineKey, { seeded: true });
    timelineAnswer = emptyTimeline;
    observationAnswer = [];

    const { result } = renderHook(() => useDeleteDocument(), {
      wrapper: wrapperFor(client),
    });
    await act(async () => {
      await result.current.mutateAsync('doc-1');
    });

    renderTimeline(client);
    await screen.findByText('No events yet');

    expect(screen.queryByText('Lab results (2 analytes)')).not.toBeInTheDocument();
    expect(screen.queryByText('Glucose, LDL')).not.toBeInTheDocument();
    expect(timelineCalls()).toBe(2);
    expect(client.getQueryState(timelineKey)?.isInvalidated).toBe(true);
  });

  it('HC-DDNT-002: importing a document refetches a mounted timeline observer', async () => {
    const client = appClient();
    const { result } = renderHook(
      () => ({ timeline: useTimeline(), mutation: useImportDocument() }),
      { wrapper: wrapperFor(client) }
    );
    await waitFor(() => expect(timelineCalls()).toBe(1));

    await act(async () => {
      await result.current.mutation.mutateAsync({
        file: new File(['report'], 'report.pdf', { type: 'application/pdf' }),
      });
    });

    await waitFor(() => expect(timelineCalls()).toBe(2));
  });

  it('HC-DDNT-003: reprocessing a document refetches a mounted timeline observer', async () => {
    const client = appClient();
    const { result } = renderHook(
      () => ({ timeline: useTimeline(), mutation: useReprocessDocument() }),
      { wrapper: wrapperFor(client) }
    );
    await waitFor(() => expect(timelineCalls()).toBe(1));

    await act(async () => {
      await result.current.mutation.mutateAsync('doc-1');
    });

    await waitFor(() => expect(timelineCalls()).toBe(2));
    expect(apiPost).toHaveBeenCalledWith('/documents/doc-1/reprocess');
  });

  it('HC-DDNT-004: verifying a document refetches a mounted timeline observer', async () => {
    const client = appClient();
    const { result } = renderHook(
      () => ({ timeline: useTimeline(), mutation: useVerifyDocument() }),
      { wrapper: wrapperFor(client) }
    );
    await waitFor(() => expect(timelineCalls()).toBe(1));

    await act(async () => {
      await result.current.mutation.mutateAsync('doc-1');
    });

    await waitFor(() => expect(timelineCalls()).toBe(2));
    expect(apiPost).toHaveBeenCalledWith('/documents/doc-1/verify');
  });

  it('HC-DDNT-005: existing success invalidations remain and failed mutations invalidate nothing', async () => {
    {
      const client = appClient();
      seedExistingCaches(client);
      const { result, unmount } = renderHook(() => useImportDocument(), { wrapper: wrapperFor(client) });
      await act(async () => {
        await result.current.mutateAsync({ file: new File(['report'], 'report.pdf') });
      });
      expectExistingCachesInvalidated(client);
      unmount();
    }
    {
      const client = appClient();
      seedExistingCaches(client);
      const { result, unmount } = renderHook(() => useDeleteDocument(), { wrapper: wrapperFor(client) });
      await act(async () => {
        await result.current.mutateAsync('doc-1');
      });
      expectExistingCachesInvalidated(client);
      unmount();
    }
    {
      const client = appClient();
      seedExistingCaches(client);
      const { result, unmount } = renderHook(() => useReprocessDocument(), { wrapper: wrapperFor(client) });
      await act(async () => {
        await result.current.mutateAsync('doc-1');
      });
      expectExistingCachesInvalidated(client);
      unmount();
    }
    {
      const client = appClient();
      seedExistingCaches(client);
      const { result, unmount } = renderHook(() => useVerifyDocument(), { wrapper: wrapperFor(client) });
      await act(async () => {
        await result.current.mutateAsync('doc-1');
      });
      expectExistingCachesInvalidated(client);
      unmount();
    }

    apiUpload.mockRejectedValueOnce(new Error('import failed'));
    {
      const client = appClient();
      seedExistingCaches(client);
      const { result, unmount } = renderHook(() => useImportDocument(), { wrapper: wrapperFor(client) });
      await act(async () => {
        await expect(result.current.mutateAsync({ file: new File(['report'], 'report.pdf') })).rejects.toThrow(
          'import failed'
        );
      });
      expectNoCacheInvalidated(client);
      unmount();
    }

    apiDelete.mockRejectedValueOnce(new Error('delete failed'));
    {
      const client = appClient();
      seedExistingCaches(client);
      const { result, unmount } = renderHook(() => useDeleteDocument(), { wrapper: wrapperFor(client) });
      await act(async () => {
        await expect(result.current.mutateAsync('doc-1')).rejects.toThrow('delete failed');
      });
      expectNoCacheInvalidated(client);
      unmount();
    }

    apiPost.mockRejectedValueOnce(new Error('reprocess failed'));
    {
      const client = appClient();
      seedExistingCaches(client);
      const { result, unmount } = renderHook(() => useReprocessDocument(), { wrapper: wrapperFor(client) });
      await act(async () => {
        await expect(result.current.mutateAsync('doc-1')).rejects.toThrow('reprocess failed');
      });
      expectNoCacheInvalidated(client);
      unmount();
    }

    apiPost.mockRejectedValueOnce(new Error('verify failed'));
    {
      const client = appClient();
      seedExistingCaches(client);
      const { result } = renderHook(() => useVerifyDocument(), { wrapper: wrapperFor(client) });
      await act(async () => {
        await expect(result.current.mutateAsync('doc-1')).rejects.toThrow('verify failed');
      });
      expectNoCacheInvalidated(client);
    }
  });
});
