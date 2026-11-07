/**
 * FE-STALE-LINKS: HC-FSL-001 to HC-FSL-003.
 *
 * /trends and /interpret are redirect stubs in App.tsx (RedirectToResults, HC-UIRES-001). A link that still points at
 * one costs a redirect hop and keeps a dead route name alive in the code. These tests pin the link TARGETS only. The
 * labels ("View trends") are UI-MICRO's copy and are not asserted here.
 *
 * Written red first. Each test says in its comment what it would not notice.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import * as api from '@/services/api';
import { MedicationDetail } from '@/pages/MedicationDetail';
import { SearchPage } from '@/pages/SearchPage';
import { TimelinePage } from '@/pages/TimelinePage';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/api')>()),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

// jsdom has no scrollIntoView, and Radix menu items call it.
if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = () => {};

const apiGet = vi.mocked(api.apiGet);

const MEDICATION = {
  id: 'med-1',
  profile_id: 'profile-1',
  name: 'Metoprolol',
  dosage_amount: 25,
  dosage_unit: 'mg',
  frequency: 'once_daily',
  started_at: '2026-01-01T00:00:00',
  ended_at: null,
  is_active: true,
  schedules: [],
};

const CORRELATION_OBSERVATION = {
  id: 'obs-1',
  analyte_canonical: 'potassium',
  value: 4.1,
  value_text: null,
  unit: 'mmol/L',
  ref_low: 3.5,
  ref_high: 5.1,
  flag: null,
  is_abnormal: false,
  collected_at: '2026-03-01T00:00:00',
  user_verified: true,
};

function correlations(observations: unknown[]) {
  return {
    medication_id: 'med-1',
    started_at: '2026-01-01T00:00:00',
    ended_at: null,
    observation_count: observations.length,
    excluded_undated_count: 0,
    analytes: observations.length ? ['potassium'] : [],
    observations,
  };
}

/** A fake server answering by path; `correlationRows` decides between the empty state and the list. */
function serve(correlationRows: unknown[]) {
  apiGet.mockImplementation((async (path: string) => {
    if (path.includes('/correlations')) return correlations(correlationRows);
    if (path === '/medications/med-1') return MEDICATION;
    if (path === '/search/') {
      return {
        count: 1,
        results: [
          {
            type: 'observation',
            id: 'obs-1',
            doc_id: 'doc-1',
            title: 'Potassium 4.1 mmol/L',
            snippet: 'Potassium was 4.1.',
            date: '2026-03-01',
            verified_status: 'verified',
            category: 'lab_results',
            highlight_types: [],
          },
        ],
      };
    }
    if (path === '/timeline/') {
      return {
        events: [
          {
            event_id: 'ev-1',
            event_type: 'lab_results',
            event_date: '2026-03-01',
            event_date_source: 'document_date',
            title: 'Lab results (1 analyte)',
            doc_id: 'doc-1',
            related_ids: [],
            verification_status: 'verified',
          },
        ],
        undated: [],
      };
    }
    return [];
  }) as unknown as typeof api.apiGet);
}

function LocationProbe() {
  const location = useLocation();
  return <p data-testid="location">{`${location.pathname}${location.search}`}</p>;
}

function renderAt(path: string, route: string, element: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={route} element={element} />
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ profileId: 'profile-1' });
});

describe('HC-FSL-001: MedicationDetail related-labs links point at /results', () => {
  // Would not notice: a button that still navigates to /trends and lands on /results only because App.tsx redirects it.
  // The probe route here has no redirect, so the pathname is the button's own target.
  it('the empty-state button navigates to /results', async () => {
    serve([]);
    const user = userEvent.setup();
    renderAt('/medications/med-1', '/medications/:medicationId', <MedicationDetail />);

    const empty = await screen.findByTestId('related-labs-empty');
    await user.click(empty.querySelector('button') as HTMLButtonElement);

    expect(screen.getByTestId('location')).toHaveTextContent(/^\/results$/);
  });

  // Would not notice: the analyte query dropped or renamed. The whole href is compared, not a substring.
  it('a related-lab link has href /results?analyte=<analyte>', async () => {
    serve([CORRELATION_OBSERVATION]);
    renderAt('/medications/med-1', '/medications/:medicationId', <MedicationDetail />);

    const list = await screen.findByTestId('related-labs-list');
    const link = list.querySelector('a') as HTMLAnchorElement;
    expect(link).toHaveAttribute('href', '/results?analyte=potassium');
  });
});

describe('HC-FSL-002: Search and Timeline lab links point at /results', () => {
  // Would not notice: a link whose label is right and whose target is a redirect stub; or another result type's link
  // (document, entity) that was changed by mistake: only the observation result is looked at, by its own href.
  it('the Search observation result link points to /results', async () => {
    serve([]);
    renderAt('/search?q=potassium', '/search', <SearchPage />);

    await screen.findByText('Potassium 4.1 mmol/L');
    const link = screen.getByRole('link', { name: /View trends/ });
    expect(link).toHaveAttribute('href', '/results');
  });

  // Would not notice: a Timeline link for another event type. Only the lab_results card is looked at.
  it('the Timeline lab_results event link points to /results', async () => {
    serve([]);
    renderAt('/timeline', '/timeline', <TimelinePage />);

    await screen.findByText('Lab results (1 analyte)');
    const link = screen.getByRole('link', { name: /View trends/ });
    expect(link).toHaveAttribute('href', '/results');
  });
});

describe('HC-FSL-003: no route literal for /trends or /interpret outside App.tsx', () => {
  // A route literal: a quote or backtick, then /trends or /interpret, then a quote, backtick, ? or /.
  // The API paths '/interpretations/<id>/interpret?' and '/observations/trends/<a>' do not match: the first needs the
  // quote directly before /interpret, the second has /trends after /observations.
  const ROUTE_LITERAL = /['"`]\/(?:trends|interpret)['"`?/]/;
  // vitest runs from src/frontend (import.meta.url is not a file: URL under jsdom).
  const SRC = join(process.cwd(), 'src');

  function sourceFiles(dir: string): string[] {
    return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) return entry.name === '__tests__' ? [] : sourceFiles(full);
      return /\.(ts|tsx)$/.test(entry.name) ? [full] : [];
    });
  }

  const scanned = sourceFiles(SRC).filter((file) => relative(SRC, file) !== 'App.tsx');

  // Would not notice: a scan that reads no files (a wrong root, a bad filter) and so finds nothing. The first two
  // checks make the scan prove it reads files and that its pattern can match.
  it('the scan reads files, and its pattern matches planted route literals and skips API paths', () => {
    expect(scanned.length).toBeGreaterThan(0);
    expect(scanned.some((file) => relative(SRC, file) === ['pages', 'MedicationDetail.tsx'].join(sep))).toBe(true);
    expect(scanned.some((file) => relative(SRC, file) === 'App.tsx')).toBe(false);

    expect(ROUTE_LITERAL.test("navigate('/trends')")).toBe(true);
    expect(ROUTE_LITERAL.test('to={`/trends?analyte=${a}`}')).toBe(true);
    expect(ROUTE_LITERAL.test("link: '/interpret'")).toBe(true);
    expect(ROUTE_LITERAL.test('`/interpret/${id}`')).toBe(true);
    expect(ROUTE_LITERAL.test('`/interpretations/${id}/interpret?x=1`')).toBe(false);
    expect(ROUTE_LITERAL.test('`/observations/trends/${analyte}`')).toBe(false);
  });

  it('no source file outside App.tsx and __tests__ has one', () => {
    const hits = scanned.flatMap((file) =>
      readFileSync(file, 'utf8')
        .split('\n')
        .flatMap((text, index) => (ROUTE_LITERAL.test(text) ? [`${relative(SRC, file)}:${index + 1}: ${text.trim()}`] : []))
    );
    expect(hits).toEqual([]);
  });
});
