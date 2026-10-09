/** Search page and compact header search tests (HC-M21). */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TopBar } from '@/components/layout/TopBar';
import { SearchPage } from '@/pages/SearchPage';
import { useSearch } from '@/services/search';

vi.mock('@/services/search', () => ({
  useSearch: vi.fn(),
}));

function LocationProbe() {
  return <div data-testid="location">{useLocation().pathname}{useLocation().search}</div>;
}

describe('SearchPage', () => {
  beforeEach(() => {
    vi.mocked(useSearch).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            type: 'entity',
            id: 'entity-1',
            doc_id: 'doc-1',
            title: 'Diagnoses — migraine aura',
            snippet: 'The note says migraine aura was recorded.',
            date: '2026-01-15',
            verified_status: 'unverified',
            category: 'visit_notes',
            highlight_types: ['needs_verification'],
          },
        ],
      },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useSearch>);
  });

  it('FE-SRCH-UI-001 exports the search page', async () => {
    const page = await import('@/pages/SearchPage');
    expect(typeof page.SearchPage).toBe('function');
  });

  it('FE-SRCH-UI-002 searches the URL query and labels unverified results', () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={['/search?q=migraine']}>
        <SearchPage />
      </MemoryRouter>
    );

    expect(useSearch).toHaveBeenCalledWith(expect.objectContaining({ q: 'migraine' }));
    expect(screen.getByText('Diagnoses — migraine aura')).toBeInTheDocument();
    expect(
      within(screen.getByRole('region', { name: 'Search results' })).getByText(
        'Needs verification'
      )
    ).toBeInTheDocument();
  });

  it('FE-SRCH-UI-003 submits the compact header search to the search route', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={['/inbox']}>
        <Routes>
          <Route
            path="*"
            element={
              <>
                <TopBar />
                <LocationProbe />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    const input = screen.getByRole('searchbox');
    await user.type(input, 'migraine aura{enter}');

    expect(screen.getByTestId('location')).toHaveTextContent(
      '/search?q=migraine+aura'
    );
  });
});
