/**
 * Timeline Service Contract Tests (HC-M14)
 *
 * Verifies the useTimeline hook calls the expected backend route
 * with the expected query params.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import { useTimeline } from '@/services/timeline';
import type { TimelineFilters } from '@/services/timeline';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
}));

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
}

function TimelineProbe({ filters }: { filters?: TimelineFilters }) {
  useTimeline(filters);
  return <div>timeline-probe</div>;
}

describe('useTimeline', () => {
  beforeEach(() => {
    vi.mocked(api.apiGet).mockReset();
    vi.mocked(api.apiGet).mockResolvedValue({ events: [], undated: [] });
  });

  it('fetches /timeline/ with no params by default', async () => {
    renderWithProviders(<TimelineProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalledWith('/timeline/', {});
    });
  });

  it('passes event_type and date range filters as query params', async () => {
    renderWithProviders(
      <TimelineProbe
        filters={{
          event_type: 'lab_results',
          date_from: '2024-01-01',
          date_to: '2024-06-30',
        }}
      />
    );

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalledWith('/timeline/', {
        event_type: 'lab_results',
        date_from: '2024-01-01',
        date_to: '2024-06-30',
      });
    });
  });

  it('omits empty filter values', async () => {
    renderWithProviders(
      <TimelineProbe filters={{ event_type: '', date_from: '', date_to: '' }} />
    );

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalledWith('/timeline/', {});
    });
  });
});
