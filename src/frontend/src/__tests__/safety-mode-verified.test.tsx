/**
 * SAFETY-MODE-VERIFIED-FE: with the stricter safety mode on, the Results chart leaves out unchecked values and lists
 * them under it; an interpretation refused with the 409 `observation_unverified` shows a verify-first state
 * (HC-SMV-001..004). HC-SMV-005 is the real-backend spec, e2e/safety-mode.spec.ts.
 *
 * The network seam (@/services/api) is mocked, and its ApiError is a stand-in with the same fields. The real one's
 * `message` is "[object Object]" for a dict detail (services/api.ts), so the page tests status 409 only, and these
 * tests send a 409 with that same message.
 *
 * What these tests would not notice:
 * - whether the real server sends 409 for an unverified value under the mode (HC-SMV-005 asks the real backend);
 * - the drawing itself: jsdom has no layout, so a point drawn off the plot or a list that overlaps the chart passes;
 * - that the PNG file matches the SVG (the PNG is drawn from the same serialised markup; only the SVG export is read);
 * - the mode being flipped while the page is open (the toggle invalidates the trend query: HC-SMT-002);
 * - the bundle budget (UI-BUDGET) and the stillness gates (HC-UISH-003/009), which are the quiet box's.
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ResultsPage } from '@/pages/ResultsPage';
import { RangeRibbon, serializeRangeRibbonSvg } from '@/components/results/RangeRibbon';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import type { Observation, TrendData, TrendPoint } from '@/services/types';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public statusText: string,
      message: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

const MODE_PATH = '/assistant/safety-mode';
const MODE_KEY = ['assistant', 'safety-mode'];
const VERIFY_FIRST = 'Verify this result first';

const HEMOGLOBIN: Observation = {
  id: 'obs-1',
  profile_id: 'profile-123',
  doc_id: 'doc-1',
  analyte_canonical: 'hemoglobin',
  analyte_raw: 'Hemoglobin',
  value: 14.2,
  value_text: null,
  unit: 'g/dL',
  ref_low: 13.5,
  ref_high: 17.5,
  ref_range_text: null,
  flag: null,
  is_abnormal: false,
  collected_at: '2026-04-10',
  user_verified: false,
  extraction_confidence: 0.92,
  source_page: 2,
  source_bbox_json: null,
};

function trendPoint(date: string, value: number, verified: boolean | undefined): TrendPoint {
  return {
    date,
    value,
    unit: 'g/dL',
    is_abnormal: false,
    flag: null,
    doc_id: 'doc-1',
    extraction_confidence: 0.9,
    ...(verified === undefined ? {} : { user_verified: verified }),
  };
}

function trendOf(points: TrendPoint[]): TrendData {
  return {
    analyte_canonical: 'hemoglobin',
    analyte_display_name: 'Hemoglobin',
    unit: 'g/dL',
    ref_low: 13.5,
    ref_high: 17.5,
    data_points: points,
    summary: 'Two measurements.',
  };
}

// One checked value and one unchecked value (the latest one).
const MIXED = trendOf([trendPoint('2026-01-10T00:00:00', 13.8, true), trendPoint('2026-04-10T00:00:00', 14.2, false)]);
const TWO_UNCHECKED = trendOf([
  trendPoint('2026-01-10T00:00:00', 13.8, false),
  trendPoint('2026-02-10T00:00:00', 14.0, undefined),
  trendPoint('2026-04-10T00:00:00', 14.2, true),
]);
const ALL_UNCHECKED = trendOf([trendPoint('2026-01-10T00:00:00', 13.8, false), trendPoint('2026-04-10T00:00:00', 14.2, false)]);

type Mode = boolean | 'unknown';

function apiError(status: number): Error {
  return new api.ApiError(status, 'Error', status === 409 ? '[object Object]' : 'boom');
}

function setApi(mode: Mode, trend: TrendData, fail?: { get?: () => Error; post?: () => Error }) {
  vi.mocked(api.apiGet).mockImplementation(async (url: string) => {
    if (url === MODE_PATH) return mode === 'unknown' ? [] : { strict_safety_mode: mode };
    if (url === '/observations/') return [HEMOGLOBIN];
    if (url.startsWith('/observations/trends/')) return trend;
    if (url === '/observations/panels/cbc') {
      return { panel_id: 'cbc', panel_name: 'Complete Blood Count', observations: [HEMOGLOBIN], collection_date: '2026-04-10T00:00:00' };
    }
    if (url === '/settings/model/external-api') {
      return { use_external_api: false, provider: '', model: '', api_key_configured: false };
    }
    if (url.includes('/interpretation')) throw fail?.get ? fail.get() : apiError(404);
    return [];
  });
  vi.mocked(api.apiPost).mockImplementation(async () => {
    throw fail?.post ? fail.post() : new Error('unmocked POST');
  });
}

function renderResults(ui: ReactNode = <ResultsPage />, explain = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[{ pathname: '/results', state: explain ? { explain: true } : null }]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
  return client;
}

/** The mode's GET has been answered, so a page that reads "off" has really been told "off". */
async function modeLoaded(client: QueryClient, value: boolean | undefined) {
  if (value === undefined) {
    await waitFor(() => expect(vi.mocked(api.apiGet)).toHaveBeenCalledWith(MODE_PATH));
    return;
  }
  await waitFor(() => expect(client.getQueryData(MODE_KEY)).toEqual({ strict_safety_mode: value }));
}

function plot(): HTMLElement {
  return screen.getByRole('slider', { name: 'Hemoglobin: results over time' }) as unknown as HTMLElement;
}

function marks(): { verified: string | null }[] {
  return Array.from(plot().querySelectorAll('[data-point-index]')).map((el) => ({ verified: el.getAttribute('data-verified') }));
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
});

afterEach(() => {
  cleanup();
});

describe('SAFETY-MODE-VERIFIED-FE: the chart', () => {
  it('HC-SMV-001: mode on, an unchecked point is absent from the plot and present in the list', async () => {
    setApi(true, MIXED);
    renderResults();

    const list = await screen.findByTestId('unchecked-values');
    // Absent from the plot: one mark, and it is the checked one.
    await screen.findByRole('slider', { name: 'Hemoglobin: results over time' });
    expect(marks()).toEqual([{ verified: 'true' }]);
    expect(plot().querySelectorAll('[data-marker]')).toHaveLength(1);
    // The drawing's own table follows the drawing: one row, the checked date.
    expect(screen.getAllByRole('row').filter((row) => row.closest('tbody'))).toHaveLength(1);
    expect(screen.getByRole('row', { name: /Jan 10, 2026/ })).toBeInTheDocument();
    expect(screen.queryByRole('row', { name: /Apr 10, 2026/ })).toBeNull();

    // Present in the list: date, value, unit.
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(1);
    expect(items[0]).toHaveTextContent('Apr 10, 2026');
    expect(items[0]).toHaveTextContent('14.2 g/dL');
    // The one-line note, singular, with the link to Review values.
    const note = screen.getByTestId('unchecked-values-note');
    expect(note).toHaveTextContent('1 unchecked value is not plotted. Check it in Review values.');
    expect(within(note).getByRole('link', { name: 'Review values' })).toHaveAttribute('href', '/verify');
    // The hollow-marker note no longer describes anything on screen.
    expect(screen.queryByTestId('trend-unverified-note')).toBeNull();
  });

  it('HC-SMV-001: two unchecked values are listed in the plural, a missing flag counts as unchecked', async () => {
    setApi(true, TWO_UNCHECKED);
    renderResults();

    const list = await screen.findByTestId('unchecked-values');
    expect(marks()).toEqual([{ verified: 'true' }]);
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByTestId('unchecked-values-note')).toHaveTextContent(
      '2 unchecked values are not plotted. Check them in Review values.'
    );
  });

  it('HC-SMV-001: mode on, every value unchecked shows plain words and no plot, and the exports are off', async () => {
    setApi(true, ALL_UNCHECKED);
    renderResults();

    const list = await screen.findByTestId('unchecked-values');
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
    expect(screen.queryByRole('slider')).toBeNull();
    expect(screen.getByText(/none of these values has been checked/i)).toBeInTheDocument();
    // "No values to chart yet." would say there is no data.
    expect(screen.queryByText('No values to chart yet.')).toBeNull();
    expect(screen.getByRole('button', { name: 'Download chart as PNG' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Download chart as SVG' })).toBeDisabled();
  });

  it('HC-SMV-001: mode on, every value checked shows no list and no note', async () => {
    const checked = trendOf([trendPoint('2026-01-10T00:00:00', 13.8, true), trendPoint('2026-04-10T00:00:00', 14.2, true)]);
    setApi(true, checked);
    const client = renderResults();

    await screen.findByRole('slider', { name: 'Hemoglobin: results over time' });
    await modeLoaded(client, true);
    await waitFor(() => expect(marks()).toHaveLength(2));
    expect(screen.queryByTestId('unchecked-values')).toBeNull();
    expect(screen.queryByTestId('unchecked-values-note')).toBeNull();
  });

  it.each([
    ['off', false],
    ['unknown', 'unknown' as const],
  ])('HC-SMV-002: mode %s, both points are plotted, the unchecked one with today\'s hollow marker', async (_label, mode) => {
    setApi(mode, MIXED);
    const client = renderResults();

    await screen.findByRole('slider', { name: 'Hemoglobin: results over time' });
    await modeLoaded(client, mode === 'unknown' ? undefined : false);
    expect(marks()).toEqual([{ verified: 'true' }, { verified: 'false' }]);
    // Today's marker: hollow, dashed.
    const hollow = plot().querySelector('[data-verified="false"] [data-marker]');
    expect(hollow).toHaveAttribute('fill', 'none');
    expect(hollow).toHaveAttribute('stroke-dasharray', '3 2');
    // Today's note, and no list.
    expect(await screen.findByTestId('trend-unverified-note')).toHaveTextContent('1 of 2 points on this chart are unverified');
    expect(screen.queryByTestId('unchecked-values')).toBeNull();
    expect(screen.queryByTestId('unchecked-values-note')).toBeNull();
    expect(screen.getAllByRole('row').filter((row) => row.closest('tbody'))).toHaveLength(2);
    expect(screen.getByRole('button', { name: 'Download chart as SVG' })).toBeEnabled();
  });
});

describe('SAFETY-MODE-VERIFIED-FE: RangeRibbon hideUnverified', () => {
  it('HC-SMV-001: hideUnverified leaves unchecked points out of the plot, the table and the exported svg', () => {
    const { container } = render(<RangeRibbon trend={MIXED} hideUnverified />);

    expect(container.querySelectorAll('[data-point-index]')).toHaveLength(1);
    expect(container.querySelectorAll('tbody tr')).toHaveLength(1);
    // The export follows the drawn svg: one circle, filled (the checked one).
    const svg = container.querySelector('svg') as SVGSVGElement;
    const exported = serializeRangeRibbonSvg(svg);
    expect(exported.match(/<circle/g)).toHaveLength(1);
    expect(exported).not.toContain('stroke-dasharray="3 2"');
  });

  it('HC-SMV-001: hideUnverified does not count an unchecked value toward the scale', () => {
    const outlier = trendOf([trendPoint('2026-01-10T00:00:00', 14.0, true), trendPoint('2026-04-10T00:00:00', 90, false)]);
    const hidden = render(<RangeRibbon trend={outlier} hideUnverified />);
    const hiddenY = hidden.container.querySelector('[data-marker]')?.getAttribute('cy');
    hidden.unmount();
    const checkedOnly = render(<RangeRibbon trend={trendOf([outlier.data_points[0]])} />);
    const checkedOnlyY = checkedOnly.container.querySelector('[data-marker]')?.getAttribute('cy');
    expect(hiddenY).toBeTruthy();
    expect(hiddenY).toBe(checkedOnlyY);
  });

  it('HC-SMV-002: hideUnverified with every point checked renders exactly what no prop renders', () => {
    const checked = trendOf([trendPoint('2026-01-10T00:00:00', 13.8, true), trendPoint('2026-04-10T00:00:00', 14.2, true)]);
    const without = render(<RangeRibbon trend={checked} />);
    const withoutHtml = without.container.innerHTML;
    without.unmount();
    const withProp = render(<RangeRibbon trend={checked} hideUnverified />);
    expect(withProp.container.innerHTML).toBe(withoutHtml);
    withProp.unmount();
    const explicitFalse = render(<RangeRibbon trend={checked} hideUnverified={false} />);
    expect(explicitFalse.container.innerHTML).toBe(withoutHtml);
  });

  it('HC-SMV-002: without the prop an unchecked point is still drawn', () => {
    const { container } = render(<RangeRibbon trend={MIXED} />);
    expect(container.querySelectorAll('[data-point-index]')).toHaveLength(2);
    expect(container.querySelector('[data-verified="false"] [data-marker]')).toHaveAttribute('stroke-dasharray', '3 2');
  });

  it('HC-SMV-001: hideUnverified with every point unchecked says so in plain words', () => {
    const { container } = render(<RangeRibbon trend={ALL_UNCHECKED} hideUnverified />);
    expect(container.querySelector('svg')).toBeNull();
    expect(container).toHaveTextContent(/none of these values has been checked/i);
    expect(container).not.toHaveTextContent('No values to chart yet.');
  });

  it('HC-SMV-002: with no points at all the old words stay, with or without the prop', () => {
    const empty = trendOf([]);
    const a = render(<RangeRibbon trend={empty} hideUnverified />);
    expect(a.container).toHaveTextContent('No values to chart yet.');
    a.unmount();
    const b = render(<RangeRibbon trend={empty} />);
    expect(b.container).toHaveTextContent('No values to chart yet.');
  });
});
