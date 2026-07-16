/** Search service contract tests (HC-M21). */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '@/services/api';
import { useSearch } from '@/services/search';
import type { SearchFilters } from '@/services/search';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
}));

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
}

function SearchProbe({ filters }: { filters: SearchFilters }) {
  useSearch(filters);
  return <div>search-probe</div>;
}

describe('search service', () => {
  beforeEach(() => {
    vi.mocked(api.apiGet).mockReset();
    vi.mocked(api.apiGet).mockResolvedValue({ results: [], count: 0 });
  });

  it('FE-SRCH-API-001 exports the search hook', async () => {
    const search = await import('@/services/search');
    expect(typeof search.useSearch).toBe('function');
  });

  it('FE-SRCH-API-002 does not request an empty query', () => {
    renderWithProviders(<SearchProbe filters={{ q: '   ' }} />);
    expect(api.apiGet).not.toHaveBeenCalled();
  });

  it('FE-SRCH-API-003 forwards query, filters, dates, and limit', async () => {
    renderWithProviders(
      <SearchProbe
        filters={{
          q: 'migraine',
          provider: 'Dr Rivera',
          date_from: '2026-01-01',
          date_to: '2026-01-31',
          category: 'visit_notes',
          highlight_type: 'needs_verification',
          limit: 25,
        }}
      />
    );

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalledWith('/search/', {
        q: 'migraine',
        provider: 'Dr Rivera',
        date_from: '2026-01-01',
        date_to: '2026-01-31',
        category: 'visit_notes',
        highlight_type: 'needs_verification',
        limit: '25',
      });
    });
  });
});
