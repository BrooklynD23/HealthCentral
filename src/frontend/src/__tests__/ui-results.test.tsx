/**
 * UI-PG-RESULTS (HC-UIRES-001 .. 017): the Results page that folds Trends and Interpret around the Range Ribbon.
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md (UI-PG-RESULTS); L0 rulings on PR #476
 * (comments 6600140569 and 6600985053).
 *
 * The modules under test are loaded with a dynamic import inside each test, so before they exist every id fails on
 * its own line instead of the whole file failing to load. Only the network is mocked: the page, the ribbon and the
 * lab-interpreter components are the real ones.
 *
 * Ids: 001 redirects; 002 the CBC tab lists CBC analytes only; 003 and 011 the disclaimer and break-glass warning
 * sit in the page shell; 005 the closed table of controls; 006 PNG and SVG export; 007 and 008 the ribbon's Reported
 * and Read-confidence words and its viewHeight; 009 the page's phone height; 010 tabs; 012 and 013 the Explain
 * click; 014 the lab-interpreter components; 015 the folded-in Trends and Interpret details; 016 and 017 source audits;
 * 018 a grounded explanation belongs to the result it was made for; 019 a panel interpretation belongs to its tab;
 * 020 the gauge prints no verdict on a scale that is not finite; 021 the logged-out route; 022 an empty panel;
 * 023 the card's toggle name; 024 no analyte name reaches browser storage, before or after a lock; 025 the tabs are the Tabs primitive;
 * 026 the Normal Range badge needs a range and a value inside it.
 *
 * Canonical names in the fixtures are the ones NormalizeModule stores (white_blood_cells, ...). The panel fixtures list
 * the analytes a panel should hold for those names (the backend's PANEL_DEFINITIONS must agree, see the PR).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import { ProfileMenu } from '@/components/layout/ProfileMenu';
import type { ComponentType } from 'react';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import type { TrendData, TrendPoint } from '@/services/types';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
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

// Variable specifiers keep Vite from resolving the modules at transform time.
const PAGE_MODULE = '@/pages/ResultsPage';
const PAGE_SOURCE = '@/pages/ResultsPage.tsx?raw';
const RIBBON_MODULE = '@/components/results/RangeRibbon';
const BANNER_MODULE = '@/components/lab-interpreter/DisclaimerBanner';
const ADVICE_MODULE = '@/components/lab-interpreter/AdviceSection';
const RANGE_MODULE = '@/components/lab-interpreter/ReferenceRangeComparison';
const CARD_MODULE = '@/components/lab-interpreter/InterpretedResultCard';
const DASHBOARD_MODULE = '@/components/lab-interpreter/PanelInterpretationDashboard';

interface RibbonProps {
  trend: TrendData;
  viewHeight?: number;
}
const loadPage = () => import(/* @vite-ignore */ PAGE_MODULE) as Promise<{ ResultsPage: ComponentType }>;
const loadPageSource = () => import(/* @vite-ignore */ PAGE_SOURCE) as Promise<{ default: string }>;
const loadRibbon = () =>
  import(/* @vite-ignore */ RIBBON_MODULE) as Promise<{
    RangeRibbon: ComponentType<RibbonProps>;
    serializeRangeRibbonSvg: (svg: SVGSVGElement) => string;
  }>;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function observation(
  id: string,
  canonical: string,
  raw: string,
  value: number,
  unit: string,
  extra: Record<string, unknown> = {}
) {
  return {
    id,
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: canonical,
    analyte_raw: raw,
    value,
    value_text: null,
    unit,
    ref_low: null,
    ref_high: null,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2026-04-10T00:00:00',
    user_verified: true,
    extraction_confidence: 0.9,
    source_page: 1,
    source_bbox_json: null,
    ...extra,
  };
}

// Vitamin D belongs to none of the four panels: it must stay reachable from All.
const OBSERVATIONS = [
  observation('o-hgb', 'hemoglobin', 'Hemoglobin', 14.2, 'g/dL', { ref_low: 12, ref_high: 17.5 }),
  observation('o-wbc', 'white_blood_cells', 'WBC Count', 7.5, 'K/uL'),
  observation('o-glu', 'glucose', 'Glucose', 95, 'mg/dL', { ref_low: 70, ref_high: 99 }),
  observation('o-vitd', 'vitamin_d', 'Vitamin D', 31, 'ng/mL'),
];

const PANELS: Record<string, unknown> = {
  cbc: { panel_id: 'cbc', panel_name: 'Complete Blood Count', observations: [OBSERVATIONS[0], OBSERVATIONS[1]], collection_date: '2026-04-10T00:00:00' },
  cmp: { panel_id: 'cmp', panel_name: 'Metabolic Panel', observations: [OBSERVATIONS[2]], collection_date: '2026-04-10T00:00:00' },
  lipid: { panel_id: 'lipid', panel_name: 'Lipid Panel', observations: [], collection_date: null },
};

// The panel is asked for its own date, so the button is off until the panel has loaded.
async function interpretButton(panel: string) {
  const button = await screen.findByRole('button', { name: `Interpret ${panel} Panel` });
  await waitFor(() => expect(button).toBeEnabled());
  return button;
}

function trendPoint(date: string, value: number, extra: Partial<TrendPoint> = {}): TrendPoint {
  return {
    date,
    value,
    unit: 'g/dL',
    is_abnormal: false,
    flag: null,
    doc_id: 'doc-1',
    extraction_confidence: null,
    user_verified: true,
    ...extra,
  };
}

function trendFor(canonical: string, display: string): TrendData {
  return {
    analyte_canonical: canonical,
    analyte_display_name: display,
    unit: 'g/dL',
    ref_low: 12,
    ref_high: 17.5,
    data_points: [
      trendPoint('2026-01-10T00:00:00', 13.5, { original_value: 135, original_unit: 'g/L', extraction_confidence: 0.9 }),
      trendPoint('2026-03-10T00:00:00', 14.0, { extraction_confidence: 0.6 }),
      trendPoint('2026-04-10T00:00:00', 14.2, { extraction_confidence: 0.3 }),
    ],
    summary: `${display} has increased by 2.9% over 3 measurements.`,
  };
}

const STORED_CARD = {
  id: 'interp-stored',
  observation_id: 'o-hgb',
  interpretation_text: 'Stored card text.',
  severity_level: 'mild',
  advice_text: null,
  citations: [{ type: 'knowledge_base', id: 'kb-hgb', text: 'Hemoglobin carries oxygen in the blood.' }],
  context: null,
  model_id: 'template-v1',
  model_tier: 'template',
  confidence_score: 0.9,
  requires_physician_review: false,
  physician_review_reason: null,
  viewed_at: null,
  created_at: '2026-01-01T00:00:00Z',
};

interface ApiOptions {
  observations?: unknown[];
  observationsFail?: boolean;
  observationsHold?: boolean;
  external?: Record<string, unknown>;
  externalFail?: boolean;
  interpretation?: 'none' | 'stored';
  trend?: (canonical: string) => TrendData;
}

function setupApi(options: ApiOptions = {}) {
  vi.mocked(api.apiGet).mockImplementation(async (url: string) => {
    if (url === '/observations/') {
      if (options.observationsHold) return new Promise(() => {});
      if (options.observationsFail) throw new Error('network down');
      return options.observations ?? OBSERVATIONS;
    }
    const trend = /^\/observations\/trends\/(.+)$/.exec(url);
    if (trend) {
      const raw = OBSERVATIONS.find((o) => o.analyte_canonical === trend[1])?.analyte_raw ?? trend[1];
      return (options.trend ?? ((c: string) => trendFor(c, raw.toUpperCase())))(trend[1]);
    }
    const panel = /^\/observations\/panels\/(.+)$/.exec(url);
    if (panel) {
      if (panel[1] === 'thyroid') throw new Error('panel unavailable');
      return PANELS[panel[1]];
    }
    if (url === '/medications/') return [];
    if (url === '/settings/model/external-api') {
      if (options.externalFail) throw new Error('network down');
      return { use_external_api: false, provider: '', model: '', api_key_configured: false, ...options.external };
    }
    if (url.includes('/interpretation')) {
      if (options.interpretation === 'stored') return STORED_CARD;
      throw new api.ApiError(404, 'Not Found', 'not found');
    }
    throw new Error(`unmocked ${url}`);
  });
  vi.mocked(api.apiPost).mockImplementation(async (url: string) => {
    if (url.includes('/interpret-grounded')) {
      return {
        interpretation: STORED_CARD,
        grounded_segments: [],
        full_response: '**FACTS**\nGrounded text.',
        insufficient_context: false,
        insufficient_reasons: [],
        verification: { enabled: true, total_claims: 1, verified_claims: 1, failed_claims: 0, faithfulness_score: 1, authority_score: 1, summary: '', issues: [] },
        is_valid: true,
        validation_errors: [],
      };
    }
    if (url.includes('/panels/')) {
      return {
        id: 'panel-1',
        panel_name: 'cbc',
        collected_at: '2026-04-10T00:00:00',
        observation_ids: ['o-hgb', 'o-wbc'],
        summary_text: 'Panel summary text.',
        overall_status: 'normal',
        relationship_insights: null,
        advice_text: null,
        citations: [],
        confidence_score: 0.9,
        requires_physician_review: false,
        created_at: '2026-04-10T00:00:00',
      };
    }
    throw new Error(`unmocked POST ${url}`);
  });
}

const apiGetCalls = () => vi.mocked(api.apiGet).mock.calls.map((call) => String(call[0]));

function Probe() {
  const location = useLocation();
  return (
    <div>
      <div data-testid="location">{`${location.pathname}${location.search}`}</div>
      <div data-testid="state">{JSON.stringify(location.state ?? null)}</div>
    </div>
  );
}

function GoTo({ to }: { to: string }) {
  const navigate = useNavigate();
  return (
    <button type="button" onClick={() => navigate(to)}>
      go {to}
    </button>
  );
}

interface RenderOptions {
  entry?: string | { pathname: string; search?: string; state?: unknown };
  go?: string;
  client?: QueryClient;
}

async function renderPage(options: RenderOptions = {}) {
  const { ResultsPage } = await loadPage();
  const client =
    options.client ?? new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[options.entry ?? '/results']}>
        <Probe />
        {options.go ? <GoTo to={options.go} /> : null}
        <Routes>
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/explain" element={<p>explain page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { ...view, client };
}

const listButtons = () => within(screen.getByRole('region', { name: /lab results/i })).queryAllByRole('button');
const listNames = () => listButtons().map((button) => button.textContent ?? '');
const chartTitle = () => document.querySelector('h3 span')?.textContent ?? null;
const sliderOf = () => screen.getByRole('slider');

async function pageLoaded() {
  await screen.findByRole('slider', {}, { timeout: 8000 });
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
  setupApi();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// HC-UIRES-001: /trends and /interpret redirect to /results
// ---------------------------------------------------------------------------

describe('HC-UIRES-001 redirects', () => {
  async function openApp(path: string) {
    // Routing.test.tsx's recipe: the real router, and an api that answers every call with an empty list.
    vi.mocked(api.apiGet).mockResolvedValue([] as never);
    vi.mocked(api.apiPost).mockResolvedValue({} as never);
    useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile', expiresIn: 3600 });
    window.history.pushState({}, '', path);
    const { default: App } = await import('@/App');
    render(<App />);
  }
  afterEach(() => window.history.replaceState({}, '', '/'));

  // The first test loads the whole app's modules, which takes longer than the default 10 s on a /mnt checkout.
  it('HC-UIRES-001: /trends?analyte=ldl_cholesterol redirects to /results?analyte=ldl_cholesterol', { timeout: 60_000 }, async () => {
    await openApp('/trends?analyte=ldl_cholesterol');
    await waitFor(() => expect(`${window.location.pathname}${window.location.search}`).toBe('/results?analyte=ldl_cholesterol'), {
      timeout: 8000,
    });
  });

  it('HC-UIRES-001: plain /trends redirects to /results', async () => {
    await openApp('/trends');
    await waitFor(() => expect(`${window.location.pathname}${window.location.search}`).toBe('/results'), { timeout: 8000 });
  });

  it('HC-UIRES-001: /interpret lands on exactly /results, with router state { explain: true }', async () => {
    await openApp('/interpret');
    await waitFor(() => expect(window.location.pathname).toBe('/results'), { timeout: 8000 });
    expect(window.location.search).toBe('');
    expect((window.history.state as { usr?: unknown } | null)?.usr).toEqual({ explain: true });
  });

  it('HC-UIRES-001: /interpret?analyte=ldl_cholesterol keeps the query and carries { explain: true }', async () => {
    await openApp('/interpret?analyte=ldl_cholesterol');
    await waitFor(() => expect(`${window.location.pathname}${window.location.search}`).toBe('/results?analyte=ldl_cholesterol'), {
      timeout: 8000,
    });
    expect((window.history.state as { usr?: unknown } | null)?.usr).toEqual({ explain: true });
  });

  for (const old of ['/trends?analyte=glucose', '/interpret']) {
    it(`HC-UIRES-001: ${old} replaces its entry: no entry is added, and Back lands on the page before it`, async () => {
      window.history.pushState({}, '', '/inbox');
      // Read after the old path is in place and before the app renders: only the redirect can change it from here.
      window.history.pushState({}, '', old);
      const lengthBefore = window.history.length;
      vi.mocked(api.apiGet).mockResolvedValue([] as never);
      vi.mocked(api.apiPost).mockResolvedValue({} as never);
      useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile', expiresIn: 3600 });
      const { default: App } = await import('@/App');
      render(<App />);
      await waitFor(() => expect(window.location.pathname).toBe('/results'), { timeout: 8000 });
      expect(window.history.length, 'push would add an entry').toBe(lengthBefore);
      // With push instead of replace, Back returns to the old path, which redirects straight back to /results.
      act(() => window.history.back());
      await waitFor(() => expect(window.location.pathname).toBe('/inbox'), { timeout: 8000 });
    });
  }
});

// ---------------------------------------------------------------------------
// HC-UIRES-021: /results is behind the login
// ---------------------------------------------------------------------------

describe('HC-UIRES-021 /results and the old paths are protected', () => {
  afterEach(() => window.history.replaceState({}, '', '/'));

  for (const path of ['/results', '/trends?analyte=glucose', '/interpret']) {
    it(`HC-UIRES-021: logged out, ${path} lands on /setup and asks the API for no observation`, async () => {
      vi.mocked(api.apiGet).mockResolvedValue([] as never);
      useAuthStore.getState().clearAuth();
      window.history.pushState({}, '', path);
      const { default: App } = await import('@/App');
      render(<App />);
      await waitFor(() => expect(window.location.pathname).toBe('/setup'), { timeout: 8000 });
      expect(apiGetCalls().filter((url) => url.startsWith('/observations'))).toEqual([]);
    });
  }
});

// ---------------------------------------------------------------------------
// HC-UIRES-002 and 010: the tabs
// ---------------------------------------------------------------------------

describe('HC-UIRES-002 / 010 panel tabs', () => {
  it('HC-UIRES-010: All is the first tab and the default, lists every analyte (Vitamin D is in no panel), and makes no panel request', async () => {
    await renderPage();
    await pageLoaded();
    const tabs = screen.getAllByRole('tab').map((tab) => tab.textContent);
    expect(tabs[0]).toBe('All');
    expect(screen.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true');
    expect(listNames().map((name) => name.split(/\d/)[0].trim())).toEqual(['Hemoglobin', 'WBC Count', 'Glucose', 'Vitamin D']);
    expect(apiGetCalls().filter((url) => url.startsWith('/observations/panels/'))).toEqual([]);
  });

  it('HC-UIRES-002: selecting the CBC tab lists only CBC analytes (Glucose and Vitamin D are gone) and fetches the CBC panel', async () => {
    await renderPage();
    // A row is up before the slider is, so this waits for the list, not the chart.
    await screen.findByRole('button', { name: /Hemoglobin/ });
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    await waitFor(() => expect(apiGetCalls()).toContain('/observations/panels/cbc'));
    // The reported defect: the CBC tab selected over a list that still shows Glucose.
    await waitFor(() => expect(screen.queryByRole('button', { name: /Glucose/ })).toBeNull());
    expect(screen.queryByRole('button', { name: /Vitamin D/ })).toBeNull();
    expect(screen.getByRole('tab', { name: /^CBC/ })).toHaveAttribute('aria-selected', 'true');
    expect(listNames().map((name) => name.split(/\d/)[0].trim())).toEqual(['Hemoglobin', 'WBC Count']);
  });

  it('HC-UIRES-010: the chart follows the panel: the selected analyte is one the tab lists', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.click(screen.getByRole('button', { name: /Glucose/ }));
    await waitFor(() => expect(chartTitle()).toBe('GLUCOSE'));
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    await waitFor(() => expect(chartTitle()).toBe('HEMOGLOBIN'));
  });

  it('HC-UIRES-010: a panel that fails to load shows a message, never an unfiltered list under the panel label', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^Thyroid/ }));
    expect(await screen.findByText(/could not load this panel/i)).toBeInTheDocument();
    expect(listButtons()).toHaveLength(0);
  });

  it('HC-UIRES-010: an empty panel shows a message, never an unfiltered list', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^Lipids/ }));
    expect(await screen.findByText(/no results from this panel/i)).toBeInTheDocument();
    expect(listButtons()).toHaveLength(0);
  });

  it('HC-UIRES-010: while a panel is loading the list is empty, not the unfiltered list', async () => {
    await renderPage();
    await pageLoaded();
    const original = vi.mocked(api.apiGet).getMockImplementation()!;
    vi.mocked(api.apiGet).mockImplementation(async (url: string, params?: Record<string, string>) =>
      url.startsWith('/observations/panels/') ? new Promise(() => {}) : original(url, params)
    );
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CMP/ }));
    await waitFor(() => expect(screen.getByRole('tab', { name: /^CMP/ })).toHaveAttribute('aria-selected', 'true'));
    expect(listButtons()).toHaveLength(0);
  });

  it('HC-UIRES-010: a named ?analyte= resets the tab to All, so the selected row is listed', async () => {
    await renderPage({ go: '/results?analyte=glucose' });
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    await waitFor(() => expect(listNames()).toHaveLength(2));
    fireEvent.click(screen.getByRole('button', { name: 'go /results?analyte=glucose' }));
    await waitFor(() => expect(screen.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true'));
    await waitFor(() => expect(chartTitle()).toBe('GLUCOSE'));
    expect(listNames()).toHaveLength(4);
  });

  it('HC-UIRES-010: an analyte outside the four panels is reachable from All, and its ?analyte= opens its chart', async () => {
    await renderPage({ entry: '/results?analyte=vitamin_d' });
    await waitFor(() => expect(chartTitle()).toBe('VITAMIN D'));
    expect(screen.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true');
    expect(apiGetCalls()).toContain('/observations/trends/vitamin_d');
  });

  it('HC-UIRES-010: Interpret <panel> shows only with a panel tab selected, and posts that panel', async () => {
    await renderPage();
    await pageLoaded();
    expect(screen.queryByRole('button', { name: /^Interpret .* Panel$/ })).toBeNull();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    fireEvent.click(await interpretButton('CBC'));
    await waitFor(() =>
      expect(vi.mocked(api.apiPost).mock.calls.some((call) => String(call[0]).startsWith('/interpretations/panels/cbc/interpret'))).toBe(true)
    );
    expect(await screen.findByText('Panel summary text.')).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'All' }));
    await waitFor(() => expect(screen.queryByRole('button', { name: /^Interpret .* Panel$/ })).toBeNull());
  });

  it('HC-UIRES-010: the active tab keeps bg-accent and takes its text colour from --on-accent, not text-white', async () => {
    await renderPage();
    await pageLoaded();
    const tab = screen.getByRole('tab', { name: 'All' });
    expect(tab).toHaveClass('bg-accent');
    expect(tab.className).toContain('text-[var(--on-accent)]');
    expect(tab.className).not.toContain('text-white');
  });

  it('HC-UIRES-025: the tabs are the ui/Tabs primitive: ArrowRight moves focus without choosing, Enter chooses, one tabpanel is labelled by the chosen tab', async () => {
    const user = userEvent.setup();
    await renderPage();
    await pageLoaded();
    const all = screen.getByRole('tab', { name: 'All' });
    expect(all).toHaveAttribute('aria-controls');
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', all.id);

    act(() => all.focus());
    await user.keyboard('{ArrowRight}');
    const cbc = screen.getByRole('tab', { name: /^CBC/ });
    expect(cbc).toHaveFocus();
    expect(all).toHaveAttribute('aria-selected', 'true');
    expect(cbc).toHaveAttribute('aria-selected', 'false');

    await user.keyboard('{Enter}');
    expect(cbc).toHaveAttribute('aria-selected', 'true');
    expect(all).toHaveAttribute('aria-selected', 'false');
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', cbc.id);
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-003 / 011: the shell
// ---------------------------------------------------------------------------

describe('HC-UIRES-003 / 011 page shell: heading, break-glass warning and disclaimer come before any branch', () => {
  const BREAK_GLASS = { use_external_api: true, provider: 'openai', model: 'gpt-x', api_key_configured: true, redaction_break_glass: true };
  const disclaimer = () => screen.getByRole('note');

  function expectShell() {
    expect(screen.getByRole('heading', { level: 1, name: 'Results' })).toBeInTheDocument();
    expect(disclaimer()).toHaveTextContent(/not medical advice/i);
    expect(disclaimer()).toHaveTextContent(/for informational purposes only/i);
  }

  it('HC-UIRES-003: the disclaimer is in the DOM at the first render (loading), and is not an alert', async () => {
    setupApi({ observationsHold: true });
    await renderPage();
    expectShell();
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('HC-UIRES-011: loading branch keeps the shell, and the break-glass alert shows while observations load', async () => {
    setupApi({ observationsHold: true, external: BREAK_GLASS });
    await renderPage();
    expectShell();
    expect((await screen.findByText(/privacy protection override is on/i)).closest('[role="alert"]')).not.toBeNull();
  });

  it('HC-UIRES-011: error branch keeps the shell and the alert', async () => {
    setupApi({ observationsFail: true, external: BREAK_GLASS });
    await renderPage();
    expect(await screen.findByText('Failed to load observations')).toBeInTheDocument();
    expectShell();
    expect((await screen.findByText(/privacy protection override is on/i)).closest('[role="alert"]')).not.toBeNull();
  });

  it('HC-UIRES-011: empty branch keeps the shell and the alert', async () => {
    setupApi({ observations: [], external: BREAK_GLASS });
    await renderPage();
    expect(await screen.findByText(/no data available/i)).toBeInTheDocument();
    expectShell();
    expect((await screen.findByText(/privacy protection override is on/i)).closest('[role="alert"]')).not.toBeNull();
  });

  it('HC-UIRES-011: the loaded page shows the shell before the Explain click, and the Explain click is what asks for an interpretation', async () => {
    setupApi({ external: BREAK_GLASS });
    await renderPage();
    await pageLoaded();
    expectShell();
    expect((await screen.findByText(/privacy protection override is on/i)).closest('[role="alert"]')).not.toBeNull();
    expect(apiGetCalls().filter((url) => url.includes('/interpretation'))).toEqual([]);
  });

  it('HC-UIRES-011: the unknown state (settings fetch fails) shows the status notice on every branch, and no alert', async () => {
    setupApi({ externalFail: true, observations: [] });
    await renderPage();
    await screen.findByText(/no data available/i);
    expect(await screen.findByText(/could not confirm this installation's privacy settings/i)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('HC-UIRES-011: break-glass off shows no alert and no status notice', async () => {
    await renderPage();
    await pageLoaded();
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.queryByText(/privacy protection override is on/i)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-012 / 013: the Explain click
// ---------------------------------------------------------------------------

describe('HC-UIRES-012 / 013 Explain this result', () => {
  it('HC-UIRES-012: no interpretation is requested before the click; the click requests it for the selected analyte', async () => {
    await renderPage();
    await pageLoaded();
    expect(screen.queryByText('No interpretation yet')).toBeNull();
    expect(apiGetCalls().filter((url) => url.includes('/interpretation'))).toEqual([]);
    fireEvent.click(screen.getByRole('button', { name: /explain this result/i }));
    expect(await screen.findByText('No interpretation yet')).toBeInTheDocument();
    expect(apiGetCalls()).toContain('/interpretations/observations/o-hgb/interpretation');
  });

  it('HC-UIRES-012: with a stored interpretation the click shows the card, its disclaimer, and Show source', async () => {
    setupApi({ interpretation: 'stored' });
    await renderPage();
    await pageLoaded();
    fireEvent.click(screen.getByRole('button', { name: /explain this result/i }));
    expect(await screen.findByText('Stored card text.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /show source/i })).toBeInTheDocument();
    // "and citations" (the row): the stored card's citation is a chip the reader can open.
    expect(screen.getByRole('button', { name: 'Citation 1: Hemoglobin carries oxygen in the blood.' })).toBeInTheDocument();
    expect(screen.getAllByRole('note').length).toBeGreaterThanOrEqual(2);
  });

  it('HC-UIRES-013: router state { explain: true } (the /interpret redirect) opens Explain without a click', async () => {
    await renderPage({ entry: { pathname: '/results', state: { explain: true } } });
    expect(await screen.findByText('No interpretation yet')).toBeInTheDocument();
    expect(apiGetCalls()).toContain('/interpretations/observations/o-hgb/interpretation');
  });

  it('HC-UIRES-013: once open, Explain stays open and follows the selected analyte', async () => {
    await renderPage({ entry: { pathname: '/results', state: { explain: true } } });
    await screen.findByText('No interpretation yet');
    fireEvent.click(screen.getByRole('button', { name: /Glucose/ }));
    await waitFor(() => expect(apiGetCalls()).toContain('/interpretations/observations/o-glu/interpretation'));
    expect(await screen.findByText('Generate an AI interpretation for Glucose')).toBeInTheDocument();
  });

  it('HC-UIRES-013: Open Explain goes to /explain', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.click(screen.getByRole('button', { name: 'Open Explain' }));
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/explain$/));
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-005: the closed table of controls
// ---------------------------------------------------------------------------

interface Control {
  name: string;
  match: RegExp;
}

// aria-label, then aria-labelledby, then the text.
function accessibleName(element: HTMLElement): string {
  const label = element.getAttribute('aria-label');
  if (label !== null) return label.trim();
  const by = element.getAttribute('aria-labelledby');
  if (by) return (document.getElementById(by)?.textContent ?? '').trim();
  return (element.textContent ?? '').trim();
}

function controlsOnPage(): Array<{ element: HTMLElement; name: string }> {
  const root = document.body;
  const found = root.querySelectorAll<HTMLElement>(
    'button, [role="tab"], [role="slider"], a[href], input, select, textarea, [tabindex="0"]'
  );
  return Array.from(found).map((element) => ({
    element,
    name: accessibleName(element),
  }));
}

/** Fails when the page has a control the table does not name, or the table names a control the page lacks. */
function expectControlSet(table: Control[]) {
  const controls = controlsOnPage();
  const unmatched = controls.filter(({ name }) => table.filter((row) => row.match.test(name)).length !== 1).map(({ name }) => name);
  const missing = table.filter((row) => !controls.some(({ name }) => row.match.test(name))).map((row) => row.name);
  expect({ unmatched, missing, count: controls.length }).toEqual({ unmatched: [], missing: [], count: table.length });
}

const ANALYTE_ROWS: Control[] = [
  { name: 'Hemoglobin', match: /^Hemoglobin\s*\d/ },
  { name: 'WBC Count', match: /^WBC Count\s*\d/ },
  { name: 'Glucose', match: /^Glucose\s*\d/ },
  { name: 'Vitamin D', match: /^Vitamin D\s*\d/ },
];
const TAB_ROWS: Control[] = [
  // The tablist itself is the one Tab stop of Radix's roving focus (tabindex 0); focus then lands on the chosen tab.
  { name: 'Lab panels tablist', match: /^Lab panels$/ },
  { name: 'All', match: /^All$/ },
  { name: 'CBC', match: /^CBC(\d+)?$/ },
  { name: 'CMP', match: /^CMP(\d+)?$/ },
  { name: 'Lipids', match: /^Lipids(\d+)?$/ },
  { name: 'Thyroid', match: /^Thyroid(\d+)?$/ },
];
const COMMON_ROWS: Control[] = [
  { name: 'Lab results scroller', match: /^Lab results$/ },
  { name: 'Download chart as PNG', match: /^Download chart as PNG$/ },
  { name: 'Download chart as SVG', match: /^Download chart as SVG$/ },
  { name: 'Open Explain', match: /^Open Explain$/ },
];

describe('HC-UIRES-005 the page has exactly the controls in this table, and each one does something', () => {
  let anchors: Array<{ download: string; href: string }>;
  beforeEach(() => {
    anchors = [];
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, writable: true, value: vi.fn(() => 'blob:mock') });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, writable: true, value: vi.fn() });
    Object.defineProperty(HTMLAnchorElement.prototype, 'click', {
      configurable: true,
      writable: true,
      value(this: HTMLAnchorElement) {
        anchors.push({ download: this.download, href: this.href });
      },
    });
  });

  it('HC-UIRES-005: All tab, trend loaded, Explain closed: every control is in the table', async () => {
    await renderPage();
    await pageLoaded();
    expectControlSet([
      ...TAB_ROWS,
      ...ANALYTE_ROWS,
      ...COMMON_ROWS,
      { name: 'Ribbon slider', match: /results over time$/ },
      { name: 'Explain this result', match: /^Explain this result$/ },
    ]);
  });

  it('HC-UIRES-005: a panel tab adds Interpret <panel> Panel and removes the other analytes', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    await screen.findByRole('button', { name: 'Interpret CBC Panel' });
    await waitFor(() => expect(listNames()).toHaveLength(2));
    expectControlSet([
      ...TAB_ROWS,
      ANALYTE_ROWS[0],
      ANALYTE_ROWS[1],
      ...COMMON_ROWS,
      { name: 'Ribbon slider', match: /results over time$/ },
      { name: 'Explain this result', match: /^Explain this result$/ },
      { name: 'Interpret CBC Panel', match: /^Interpret CBC Panel$/ },
    ]);
  });

  it('HC-UIRES-005: Explain open with no stored interpretation swaps Explain for Generate Interpretation', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.click(screen.getByRole('button', { name: /explain this result/i }));
    await screen.findByText('No interpretation yet');
    expectControlSet([
      ...TAB_ROWS,
      ...ANALYTE_ROWS,
      ...COMMON_ROWS,
      { name: 'Ribbon slider', match: /results over time$/ },
      { name: 'Generate Interpretation', match: /^Generate Interpretation$/ },
    ]);
  });

  it('HC-UIRES-005: each control has its observable effect', async () => {
    await renderPage();
    await pageLoaded();

    // Tabs: each selects itself and filters the list; All restores it.
    for (const [label, count] of [['CBC', 2], ['CMP', 1], ['Lipids', 0], ['Thyroid', 0]] as const) {
      fireEvent.mouseDown(screen.getByRole('tab', { name: new RegExp(`^${label}`) }));
      await waitFor(() => expect(screen.getByRole('tab', { name: new RegExp(`^${label}`) })).toHaveAttribute('aria-selected', 'true'));
      await waitFor(() => expect(listButtons()).toHaveLength(count));
    }
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'All' }));
    await waitFor(() => expect(listButtons()).toHaveLength(4));
    expect(screen.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true');

    // Analyte rows: each opens its own chart.
    for (const [name, title] of [['Glucose', 'GLUCOSE'], ['Vitamin D', 'VITAMIN D'], ['WBC Count', 'WBC COUNT'], ['Hemoglobin', 'HEMOGLOBIN']] as const) {
      fireEvent.click(screen.getByRole('button', { name: new RegExp(`^${name}`) }));
      await waitFor(() => expect(chartTitle()).toBe(title));
    }

    // The ribbon: a key moves the selected point.
    const slider = sliderOf();
    const before = Number(slider.getAttribute('aria-valuenow'));
    fireEvent.keyDown(slider, { key: 'ArrowLeft' });
    expect(Number(sliderOf().getAttribute('aria-valuenow'))).toBe(before - 1);

    // The scroller takes focus.
    const scroller = screen.getByRole('region', { name: /lab results/i });
    scroller.focus();
    expect(document.activeElement).toBe(scroller);

    // Exports: each downloads a file named for the analyte.
    fireEvent.click(screen.getByRole('button', { name: 'Download chart as SVG' }));
    await waitFor(() => expect(anchors.map((a) => a.download)).toContain('hemoglobin-trend.svg'));

    // Explain asks for the interpretation; Generate posts.
    fireEvent.click(screen.getByRole('button', { name: /explain this result/i }));
    fireEvent.click(await screen.findByRole('button', { name: 'Generate Interpretation' }));
    await waitFor(() =>
      expect(vi.mocked(api.apiPost).mock.calls.some((call) => String(call[0]).includes('/interpret-grounded'))).toBe(true)
    );

    // Open Explain leaves for /explain.
    fireEvent.click(screen.getByRole('button', { name: 'Open Explain' }));
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/explain$/));
  });

  it('HC-UIRES-005: the old dead controls are gone', async () => {
    await renderPage();
    await pageLoaded();
    for (const label of [/last 12 months/i, /^filters$/i, /view sources/i]) {
      expect(screen.queryByRole('button', { name: label })).toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-006: PNG and SVG export
// ---------------------------------------------------------------------------

describe('HC-UIRES-006 PNG and SVG export come from the ribbon', () => {
  let blobs: Blob[];
  let anchors: Array<{ download: string; href: string }>;
  let fills: string[];
  const revoke = vi.fn();

  function readBlob(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsText(blob);
    });
  }

  beforeEach(() => {
    blobs = [];
    anchors = [];
    fills = [];
    revoke.mockClear();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: vi.fn((blob: Blob) => {
        blobs.push(blob);
        return 'blob:mock';
      }),
    });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, writable: true, value: revoke });
    Object.defineProperty(HTMLAnchorElement.prototype, 'click', {
      configurable: true,
      writable: true,
      value(this: HTMLAnchorElement) {
        anchors.push({ download: this.download, href: this.href });
      },
    });
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      configurable: true,
      writable: true,
      value: vi.fn(() => ({
        fillRect: vi.fn(),
        drawImage: vi.fn(),
        set fillStyle(value: string) {
          fills.push(value);
        },
      })),
    });
    Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
      configurable: true,
      writable: true,
      value: vi.fn(() => 'data:image/png;base64,mock'),
    });
    class MockImage {
      onload: null | (() => void) = null;
      onerror: null | (() => void) = null;
      set src(_value: string) {
        this.onload?.();
      }
    }
    vi.stubGlobal('Image', MockImage);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.documentElement.style.removeProperty('--surface-1');
  });

  it('HC-UIRES-006: SVG export downloads <analyte>-trend.svg whose markup is the ribbon (slider) with no var(--) left, and revokes the URL', async () => {
    await renderPage();
    await pageLoaded();
    document.documentElement.style.setProperty('--ink-1', '#123456');
    fireEvent.click(screen.getByRole('button', { name: 'Download chart as SVG' }));
    await waitFor(() => expect(anchors).toHaveLength(1));
    expect(anchors[0].download).toBe('hemoglobin-trend.svg');
    const markup = await readBlob(blobs[0]);
    expect(blobs[0].type).toBe('image/svg+xml;charset=utf-8');
    expect(markup).toContain('role="slider"');
    expect(markup).not.toMatch(/var\(--/);
    expect(markup).toContain('#123456');
    expect(revoke).toHaveBeenCalled();
    document.documentElement.style.removeProperty('--ink-1');
  });

  it('HC-UIRES-006: PNG export downloads <analyte>-trend.png drawn from the ribbon markup, on the --surface-1 fill', async () => {
    document.documentElement.style.setProperty('--surface-1', '#abcdef');
    await renderPage();
    await pageLoaded();
    fireEvent.click(screen.getByRole('button', { name: 'Download chart as PNG' }));
    await waitFor(() => expect(anchors).toHaveLength(1));
    expect(anchors[0].download).toBe('hemoglobin-trend.png');
    expect(anchors[0].href).toContain('data:image/png');
    const markup = await readBlob(blobs[0]);
    expect(markup).toContain('role="slider"');
    expect(markup).not.toMatch(/var\(--/);
    expect(fills).toContain('#abcdef');
    expect(revoke).toHaveBeenCalled();
  });

  it('HC-UIRES-006: PNG fill falls back to #ffffff when --surface-1 is unset', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.click(screen.getByRole('button', { name: 'Download chart as PNG' }));
    await waitFor(() => expect(anchors).toHaveLength(1));
    expect(fills).toContain('#ffffff');
  });

  it('HC-UIRES-006: the export follows the svg: its width and height are the viewBox the page drew', async () => {
    await renderPage();
    await pageLoaded();
    const viewBox = sliderOf().getAttribute('viewBox') ?? '';
    const [, , w, h] = viewBox.split(' ');
    fireEvent.click(screen.getByRole('button', { name: 'Download chart as SVG' }));
    await waitFor(() => expect(blobs).toHaveLength(1));
    const markup = await readBlob(blobs[0]);
    expect(markup).toContain(`width="${w}"`);
    expect(markup).toContain(`height="${h}"`);
  });

  // HC-UIRES-028 (L0 ruling 6615916306, point 1): the drawing shows no text, so a patient cannot see the live svg's
  // aria-label (the analyte name) and aria-valuetext (the active value and its date) before sharing the file. The
  // clone drops both; the live svg keeps them. D3 exempts only CSV and JSON, so this makes no new exception.
  function expectNoHiddenValue(markup: string, live: Element) {
    const text = live.getAttribute('aria-valuetext') ?? '';
    const [datePart, rest = ''] = text.split(': ');
    const valuePart = rest.split(', ')[0];
    expect(datePart, 'the live svg names a date').not.toBe('');
    expect(valuePart, 'the live svg names a value').toMatch(/14\.2/);
    expect(markup).not.toContain('aria-label');
    expect(markup).not.toContain('aria-valuetext');
    expect(markup.toLowerCase()).not.toContain('hemoglobin');
    expect(markup).not.toContain(valuePart);
    expect(markup).not.toContain(datePart);
    expect(markup).not.toContain(text);
  }

  it('HC-UIRES-028: serializeRangeRibbonSvg drops aria-label and aria-valuetext from the clone only, and still parses as a slider', async () => {
    const { RangeRibbon, serializeRangeRibbonSvg } = await loadRibbon();
    const { container } = render(<RangeRibbon trend={trendFor('hemoglobin', 'HEMOGLOBIN')} />);
    const live = container.querySelector('svg') as SVGSVGElement;
    expect(live.getAttribute('aria-label')).toContain('HEMOGLOBIN');
    const before = live.getAttribute('aria-valuetext');
    const markup = serializeRangeRibbonSvg(live);
    expectNoHiddenValue(markup, live);
    expect(live.getAttribute('aria-label')).toContain('HEMOGLOBIN');
    expect(live.getAttribute('aria-valuetext')).toBe(before);
    const parsed = new DOMParser().parseFromString(markup, 'image/svg+xml');
    expect(parsed.getElementsByTagName('parsererror')).toHaveLength(0);
    expect(parsed.documentElement.getAttribute('role')).toBe('slider');
    expect(parsed.documentElement.hasAttribute('aria-label')).toBe(false);
    expect(parsed.documentElement.hasAttribute('aria-valuetext')).toBe(false);
  });

  it('HC-UIRES-028: the page\'s Download chart as SVG button exports no aria-label or aria-valuetext, keeps the analyte in the filename, and leaves the live svg whole', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.click(screen.getByRole('button', { name: 'Download chart as SVG' }));
    await waitFor(() => expect(anchors).toHaveLength(1));
    expect(anchors[0].download).toBe('hemoglobin-trend.svg');
    const markup = await readBlob(blobs[0]);
    expectNoHiddenValue(markup, sliderOf());
    expect(sliderOf().getAttribute('aria-label')).toContain('HEMOGLOBIN');
    expect(sliderOf().getAttribute('aria-valuetext')).toMatch(/14\.2/);
    expect(markup).toContain('role="slider"');
    const parsed = new DOMParser().parseFromString(markup, 'image/svg+xml');
    expect(parsed.getElementsByTagName('parsererror')).toHaveLength(0);
  });

  it('HC-UIRES-028: the PNG path draws from the same serializer, so its markup has neither attribute either', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.click(screen.getByRole('button', { name: 'Download chart as PNG' }));
    await waitFor(() => expect(anchors).toHaveLength(1));
    expect(anchors[0].download).toBe('hemoglobin-trend.png');
    expectNoHiddenValue(await readBlob(blobs[0]), sliderOf());
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-007 / 008: the ribbon (Reported, Read confidence, viewHeight)
// ---------------------------------------------------------------------------

function ribbonTrend(points: TrendPoint[], overrides: Partial<TrendData> = {}): TrendData {
  return {
    analyte_canonical: 'hemoglobin',
    analyte_display_name: 'Hemoglobin',
    unit: 'g/dL',
    ref_low: 12,
    ref_high: 17.5,
    data_points: points,
    summary: '',
    ...overrides,
  };
}

const rowsOf = () =>
  within(screen.getByRole('table'))
    .getAllByRole('row')
    .slice(1)
    .map((row) => Array.from(row.querySelectorAll('th, td'), (cell) => cell.textContent ?? ''));

describe('HC-UIRES-007 the ribbon shows Reported and Read confidence for every point', () => {
  const POINTS = [
    trendPoint('2026-01-10T00:00:00', 13.5, { original_value: 135, original_unit: 'g/L', extraction_confidence: 0.9 }),
    trendPoint('2026-03-10T00:00:00', 14.0, { extraction_confidence: 0.6 }),
    trendPoint('2026-04-10T00:00:00', 14.2, { extraction_confidence: 0.3 }),
  ];

  it('HC-UIRES-007: the readout shows both for a point that is not the latest (not only for the latest)', async () => {
    const { RangeRibbon } = await loadRibbon();
    render(<RangeRibbon trend={ribbonTrend(POINTS)} />);
    const readout = () => document.querySelector('[data-readout]')?.textContent ?? '';
    expect(readout()).toContain('Read confidence: Low');
    expect(readout()).not.toContain('Reported:');
    fireEvent.keyDown(sliderOf(), { key: 'Home' });
    expect(readout()).toContain('Jan 10, 2026');
    expect(readout()).toContain('Reported: 135 g/L');
    expect(readout()).toContain('Read confidence: High');
  });

  it('HC-UIRES-007: every table row carries them inside its Result cell, and the row keeps 4 cells', async () => {
    const { RangeRibbon } = await loadRibbon();
    render(<RangeRibbon trend={ribbonTrend(POINTS)} />);
    const rows = rowsOf();
    expect(rows.map((row) => row.length)).toEqual([4, 4, 4]);
    expect(rows[0][1]).toBe('13.5 g/dL · Reported: 135 g/L · Read confidence: High');
    expect(rows[1][1]).toBe('14 g/dL · Read confidence: Medium');
    expect(rows[2][1]).toBe('14.2 g/dL · Read confidence: Low');
  });

  it('HC-UIRES-007: a point with neither keeps its text exactly as before', async () => {
    const { RangeRibbon } = await loadRibbon();
    render(<RangeRibbon trend={ribbonTrend([trendPoint('2026-04-01T00:00:00', 14), trendPoint('2026-04-10T00:00:00', 15)])} />);
    expect(rowsOf().map((row) => row[1])).toEqual(['14 g/dL', '15 g/dL']);
    const readout = document.querySelector('[data-readout]')?.textContent ?? '';
    expect(readout).not.toContain('Reported');
    expect(readout).not.toContain('Read confidence');
    expect(readout).toContain('Apr 10, 2026: 15 g/dL');
  });

  it('HC-UIRES-007: confidence bands are the SourceTrace ones: 0.8 High, 0.79 Medium, 0.5 Medium, 0.49 Low, 0 Low', async () => {
    const { RangeRibbon } = await loadRibbon();
    const cases: Array<[number, string]> = [
      [1, 'High'],
      [0.8, 'High'],
      [0.79, 'Medium'],
      [0.5, 'Medium'],
      [0.49, 'Low'],
      [0, 'Low'],
    ];
    render(
      <RangeRibbon
        trend={ribbonTrend(cases.map(([confidence], i) => trendPoint(`2026-04-${String(i + 1).padStart(2, '0')}T00:00:00`, 14, { extraction_confidence: confidence })))}
      />
    );
    expect(rowsOf().map((row) => row[1])).toEqual(cases.map(([, words]) => `14 g/dL · Read confidence: ${words}`));
  });

  it('HC-UIRES-007: Reported needs both the value and the unit, and a value of 0 is a value', async () => {
    const { RangeRibbon } = await loadRibbon();
    render(
      <RangeRibbon
        trend={ribbonTrend([
          trendPoint('2026-04-01T00:00:00', 14, { original_value: 140, original_unit: null }),
          trendPoint('2026-04-02T00:00:00', 14, { original_value: null, original_unit: 'g/L' }),
          trendPoint('2026-04-03T00:00:00', 14, { original_value: 0, original_unit: 'g/L' }),
          trendPoint('2026-04-04T00:00:00', 14, { extraction_confidence: Number.NaN }),
        ])}
      />
    );
    expect(rowsOf().map((row) => row[1])).toEqual(['14 g/dL', '14 g/dL', '14 g/dL · Reported: 0 g/L', '14 g/dL']);
  });

  it('HC-UIRES-007: the new words carry data-t0 (inside the readout and the Result cells)', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(<RangeRibbon trend={ribbonTrend(POINTS)} />);
    expect(container.querySelector('[data-readout]')).toHaveAttribute('data-t0');
    const cells = Array.from(container.querySelectorAll('tbody tr')).map((row) => row.children[1]);
    expect(cells).toHaveLength(3);
    for (const cell of cells) expect(cell).toHaveAttribute('data-t0');
  });
});

describe('HC-UIRES-008 RangeRibbon viewHeight', () => {
  const POINTS = [
    trendPoint('2026-04-01T00:00:00', 85),
    trendPoint('2026-04-10T00:00:00', 118),
  ];
  const trend = ribbonTrend(POINTS, { ref_low: 70, ref_high: 99 });

  it('HC-UIRES-008: the default is 160: viewBox, plot bottom 136 and the cursor line as before', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(<RangeRibbon trend={trend} />);
    expect(container.querySelector('svg')).toHaveAttribute('viewBox', '0 0 320 160');
    const cursor = container.querySelector('[data-cursor]');
    expect(Number(cursor?.getAttribute('y1'))).toBe(18);
    expect(Number(cursor?.getAttribute('y2'))).toBe(142);
  });

  it('HC-UIRES-008: viewHeight 300 sets the viewBox, moves the plot bottom to 276 and the cursor with it', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(<RangeRibbon trend={trend} viewHeight={300} />);
    expect(container.querySelector('svg')).toHaveAttribute('viewBox', '0 0 320 300');
    const cursor = container.querySelector('[data-cursor]');
    expect(Number(cursor?.getAttribute('y1'))).toBe(18);
    expect(Number(cursor?.getAttribute('y2'))).toBe(282);
    // domain 70..118 padded by 15% of 48: 62.8..125.2; low edge 70 sits at 276 - (7.2 / 62.4) * 252.
    const lowEdge = container.querySelector('[data-band-edge="low"]');
    expect(Number(lowEdge?.getAttribute('y1'))).toBeCloseTo(276 - (7.2 / 62.4) * 252, 1);
    const markers = Array.from(container.querySelectorAll('[data-marker]')).map((m) => Number(m.getAttribute('cy')));
    expect(markers[0]).toBeCloseTo(276 - ((85 - 62.8) / 62.4) * 252, 1);
    expect(markers[1]).toBeCloseTo(276 - ((118 - 62.8) / 62.4) * 252, 1);
  });

  it('HC-UIRES-008: the export height follows the svg, and the default export stays 320 x 160', async () => {
    const { RangeRibbon, serializeRangeRibbonSvg } = await loadRibbon();
    const tall = render(<RangeRibbon trend={trend} viewHeight={300} />);
    const tallOut = serializeRangeRibbonSvg(tall.container.querySelector('svg') as SVGSVGElement);
    const parsedTall = new DOMParser().parseFromString(tallOut, 'image/svg+xml');
    expect(parsedTall.getElementsByTagName('parsererror')).toHaveLength(0);
    expect(parsedTall.documentElement.getAttribute('width')).toBe('320');
    expect(parsedTall.documentElement.getAttribute('height')).toBe('300');
    tall.unmount();

    const flat = render(<RangeRibbon trend={trend} />);
    const flatOut = new DOMParser().parseFromString(
      serializeRangeRibbonSvg(flat.container.querySelector('svg') as SVGSVGElement),
      'image/svg+xml'
    );
    expect(flatOut.documentElement.getAttribute('width')).toBe('320');
    expect(flatOut.documentElement.getAttribute('height')).toBe('160');
  });

  it('HC-UIRES-008: a non-finite or too-small viewHeight falls back to 160', async () => {
    const { RangeRibbon } = await loadRibbon();
    for (const bad of [Number.NaN, 0, -5, 40, Number.POSITIVE_INFINITY]) {
      const { container, unmount } = render(<RangeRibbon trend={trend} viewHeight={bad} />);
      expect(container.querySelector('svg')).toHaveAttribute('viewBox', '0 0 320 160');
      expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
      unmount();
    }
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-009: the page's own height
// ---------------------------------------------------------------------------

describe('HC-UIRES-009 the page draws the ribbon taller below lg', () => {
  // setup.ts installs matchMedia in a beforeAll, so it is read here in a beforeEach, not when the file is collected.
  let originalMatchMedia: typeof window.matchMedia;
  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
  });
  afterEach(() => {
    Object.defineProperty(window, 'matchMedia', { writable: true, configurable: true, value: originalMatchMedia });
  });
  const setDesktop = (matches: boolean) => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('min-width') ? matches : false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  };
  const heightOf = () => Number((sliderOf().getAttribute('viewBox') ?? '').split(' ')[3]);

  it('HC-UIRES-009: below lg the viewBox is taller than 160 (200 px of drawn plot at 390 wide needs about 300)', async () => {
    setDesktop(false);
    await renderPage();
    await pageLoaded();
    expect(heightOf()).toBeGreaterThanOrEqual(288);
  });

  it('HC-UIRES-009: at lg and above it stays 160', async () => {
    setDesktop(true);
    await renderPage();
    await pageLoaded();
    expect(heightOf()).toBe(160);
  });

  // The height comes from a useState initialiser, so the svg is created once at its final height. A height read in an
  // effect draws once at a default and then again, so each orientation is checked: below lg and at lg.
  for (const desktop of [false, true]) {
    it(`HC-UIRES-009: the height is chosen in the first render (${desktop ? 'lg' : 'below lg'}): the svg gets its viewBox once, never a default and then a correction`, async () => {
      setDesktop(desktop);
      const sets: string[] = [];
      const original = Element.prototype.setAttribute;
      vi.spyOn(Element.prototype, 'setAttribute').mockImplementation(function (this: Element, name: string, value: string) {
        if (name === 'viewBox' && this.getAttribute('role') === 'slider') sets.push(value);
        return original.call(this, name, value);
      });
      // The cache holds the observations and the trend already, so the very first commit holds the svg. With the
      // data still to arrive, an effect would have run before the svg existed and the test could not see it.
      const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
      client.setQueryData(['observations', { profile_id: 'profile-123' }], OBSERVATIONS);
      client.setQueryData(['observations', 'trends', 'hemoglobin', undefined, undefined], trendFor('hemoglobin', 'HEMOGLOBIN'));
      await renderPage({ client });
      await pageLoaded();
      expect(sets).toHaveLength(1);
      const height = Number(sets[0].split(' ')[3]);
      if (desktop) expect(height).toBe(160);
      else expect(height).toBeGreaterThanOrEqual(288);
    });
  }

  it('HC-UIRES-009: crossing lg re-draws the ribbon at the other height (the listener is wired)', async () => {
    let listener: ((event: { matches: boolean }) => void) | null = null;
    let matches = false;
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        get matches() {
          return query.includes('min-width') ? matches : false;
        },
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: (_type: string, fn: (event: { matches: boolean }) => void) => {
          if (query.includes('min-width')) listener = fn;
        },
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
    await renderPage();
    await pageLoaded();
    expect(heightOf()).toBeGreaterThanOrEqual(288);
    expect(listener).not.toBeNull();
    matches = true;
    act(() => listener!({ matches: true }));
    await waitFor(() => expect(heightOf()).toBe(160));
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-014: lab-interpreter components
// ---------------------------------------------------------------------------

describe('HC-UIRES-014 lab-interpreter components', () => {
  it('HC-UIRES-014: DisclaimerBanner is a note (not an alert), carries data-t0, is never animated, and its copy is unchanged', async () => {
    const { DisclaimerBanner } = (await import(/* @vite-ignore */ BANNER_MODULE)) as typeof import('@/components/lab-interpreter/DisclaimerBanner');
    const { container } = render(<DisclaimerBanner />);
    const note = screen.getByRole('note');
    expect(screen.queryByRole('alert')).toBeNull();
    expect(note).toHaveAttribute('data-t0');
    expect(note.className).not.toMatch(/animate|transition/);
    expect(container.textContent).toContain('For informational purposes only');
    expect(container.textContent).toContain(
      'AI-generated interpretations are not medical advice. Always consult your healthcare provider before making decisions based on lab results. Critical or unexpected values should be reviewed by a physician.'
    );
  });

  it('HC-UIRES-014: AdviceSection is headed "Questions you could ask your clinician" and carries data-t0', async () => {
    const { AdviceSection } = (await import(/* @vite-ignore */ ADVICE_MODULE)) as typeof import('@/components/lab-interpreter/AdviceSection');
    const { container } = render(<AdviceSection adviceText="Ask about fibre." />);
    expect(screen.getByText('Questions you could ask your clinician')).toBeInTheDocument();
    expect(screen.queryByText('Recommendations')).toBeNull();
    expect(container.querySelector('[data-t0]')).not.toBeNull();
    expect(container.querySelector('[data-t0]')?.textContent).toContain('Ask about fibre.');
  });

  it('HC-UIRES-014: ReferenceRangeComparison draws a RangeTick, drops the two axis labels, and marks the value text data-t0', async () => {
    const { ReferenceRangeComparison } = (await import(/* @vite-ignore */ RANGE_MODULE)) as typeof import('@/components/lab-interpreter/ReferenceRangeComparison');
    const { container } = render(<ReferenceRangeComparison value={80} refLow={70} refHigh={99} unit="mg/dL" />);
    expect(container.querySelector('[data-range-tick]')).not.toBeNull();
    expect(screen.queryByText('61.3')).toBeNull();
    expect(screen.queryByText('107.7')).toBeNull();
    expect(screen.getByText(/70 - 99 mg\/dL/)).toBeInTheDocument();
    expect(screen.getByText(/80 mg\/dL \(Normal\)/)).toHaveAttribute('data-t0');
  });

  it('HC-UIRES-014: InterpretedResultCard body and PanelInterpretationDashboard values carry data-t0, and neither fades or moves in', async () => {
    const { InterpretedResultCard } = (await import(/* @vite-ignore */ CARD_MODULE)) as typeof import('@/components/lab-interpreter/InterpretedResultCard');
    const { PanelInterpretationDashboard } = (await import(/* @vite-ignore */ DASHBOARD_MODULE)) as typeof import('@/components/lab-interpreter/PanelInterpretationDashboard');
    const card = render(<InterpretedResultCard interpretation={STORED_CARD} analyteName="Hemoglobin" />);
    expect(screen.getByText('Stored card text.').closest('[data-t0]')).not.toBeNull();
    const wrapper = card.container.firstElementChild as HTMLElement;
    expect(wrapper.getAttribute('style') ?? '').not.toMatch(/opacity|transform/);
    card.unmount();

    const panel = render(
      <PanelInterpretationDashboard
        interpretation={{
          id: 'p1',
          panel_name: 'cbc',
          collected_at: '2026-04-10T00:00:00',
          observation_ids: ['a'],
          summary_text: 'Panel summary text.',
          overall_status: 'normal',
          relationship_insights: [{ relationship: 'A and B', value: 1, status: 'normal', interpretation: 'Insight text.', source_id: null }],
          advice_text: null,
          citations: [],
          confidence_score: 0.9,
          requires_physician_review: false,
          created_at: '2026-04-10T00:00:00',
        }}
        isLoading={false}
        isError={false}
      />
    );
    expect(screen.getByText('Panel summary text.').closest('[data-t0]')).not.toBeNull();
    expect(screen.getByText('Insight text.').closest('[data-t0]')).not.toBeNull();
    for (const el of Array.from(panel.container.querySelectorAll<HTMLElement>('*'))) {
      expect(el.getAttribute('style') ?? '').not.toMatch(/opacity|transform/);
    }
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-015: what the two old pages showed is still shown
// ---------------------------------------------------------------------------

describe('HC-UIRES-015 nothing either old page showed has gone', () => {
  it('HC-UIRES-015: the unverified and low-confidence counts, Normal/Outside badge, and the undated mark', async () => {
    setupApi({
      observations: [
        observation('a', 'hemoglobin', 'Hemoglobin', 19.4, 'g/dL', { user_verified: false, extraction_confidence: 0.5, collected_at: null, is_abnormal: true }),
        observation('b', 'glucose', 'Glucose', 95, 'mg/dL', { user_verified: true, extraction_confidence: 0.95 }),
      ],
      trend: (c) => ({ ...trendFor(c, c.toUpperCase()), data_points: [trendPoint('2026-04-10T00:00:00', 19.4, { is_abnormal: true, user_verified: false })] }),
    });
    await renderPage();
    await pageLoaded();
    expect(screen.getByText('1 unverified values')).toBeInTheDocument();
    expect(screen.getByText('1 low-confidence extractions')).toBeInTheDocument();
    expect(screen.getByText('undated')).toBeInTheDocument();
    expect(screen.getByText('Outside Range')).toBeInTheDocument();
    expect(within(screen.getByRole('region', { name: /lab results/i })).getByText('!')).toBeInTheDocument();
  });

  it('HC-UIRES-015: a trend of undated points, an unrecognised-unit count and a missing trend keep their messages', async () => {
    setupApi({
      trend: (c) => ({ ...trendFor(c, 'HEMOGLOBIN'), data_points: [], summary: 'No dated measurements to chart.' }),
    });
    await renderPage();
    expect(await screen.findByText('No dated measurements to chart.')).toBeInTheDocument();
    expect(screen.getByText(/Collection dates could not be read/)).toBeInTheDocument();
    cleanup();

    setupApi({ trend: (c) => ({ ...trendFor(c, 'HEMOGLOBIN'), excluded_count: 2 }) });
    await renderPage();
    expect(await screen.findByText('2 point(s) hidden — unrecognized unit')).toBeInTheDocument();
    expect(screen.getByText('Medications active at time of latest result')).toBeInTheDocument();
  });

  it('HC-UIRES-015: the grounded summary, its faithfulness badge and the withheld region survive the fold', async () => {
    await renderPage({ entry: { pathname: '/results', state: { explain: true } } });
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    expect(await screen.findByText('Grounded explanation')).toBeInTheDocument();
    expect(screen.getByText(/Grounded faithfulness: 100%/)).toBeInTheDocument();
    expect(screen.getByTestId('withheld-live-region')).toHaveAttribute('aria-live', 'polite');
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-016 / 017: source audits
// ---------------------------------------------------------------------------

describe('HC-UIRES-016 / 017 source audits', () => {
  it('HC-UIRES-016: the page uses no framer-motion element, no stagger and no transform', async () => {
    const { default: source } = await loadPageSource();
    expect(source).not.toMatch(/framer-motion/);
    expect(source).not.toMatch(/\bm\.(button|div|li)\b|\bmotion\./);
    expect(source).not.toMatch(/\b-?(translate-[xy]|rotate-|scale-)/);
    // A spinner may turn only when motion is allowed (G5): motion-safe:animate-spin.
    expect(source).not.toMatch(/(?<!motion-safe:)\banimate-/);
    expect(source).not.toContain('text-white');
  });

  it('HC-UIRES-016: the spinners in the two components the page renders turn only where motion is allowed', async () => {
    const card = (await import(/* @vite-ignore */ '@/components/lab-interpreter/InterpretedResultCard.tsx?raw')) as { default: string };
    const dashboard = (await import(/* @vite-ignore */ '@/components/lab-interpreter/PanelInterpretationDashboard.tsx?raw')) as { default: string };
    for (const source of [card.default, dashboard.default]) {
      expect(source).toMatch(/motion-safe:animate-spin/);
      expect(source).not.toMatch(/(?<!motion-safe:)\banimate-/);
    }
  });

  it('HC-UIRES-017: the page imports the lab-interpreter components by path and never reaches recharts (the Results bundle budget)', async () => {
    const { default: source } = await loadPageSource();
    expect(source).not.toMatch(/from '@\/components\/lab-interpreter'/);
    expect(source).not.toMatch(/from '@\/services'/);
    expect(source).not.toMatch(/recharts|InterpretedTrendChart/);
    expect(source).toContain("from '@/components/results/RangeRibbon'");
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-018: a grounded explanation belongs to the result it was made for
// ---------------------------------------------------------------------------

describe('HC-UIRES-018 a grounded explanation and its faithfulness badge follow the selected result', () => {
  it('HC-UIRES-018: generated on Hemoglobin, gone on Glucose, back on Hemoglobin', async () => {
    await renderPage({ entry: { pathname: '/results', state: { explain: true } } });
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    expect(await screen.findByText('Grounded explanation')).toBeInTheDocument();
    expect(screen.getByText(/Grounded faithfulness: 100%/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /^Glucose/ }));
    await waitFor(() => expect(chartTitle()).toBe('GLUCOSE'));
    expect(screen.queryByText('Grounded explanation')).toBeNull();
    expect(screen.queryByText(/Grounded faithfulness/)).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /^Hemoglobin/ }));
    await waitFor(() => expect(chartTitle()).toBe('HEMOGLOBIN'));
    expect(screen.getByText('Grounded explanation')).toBeInTheDocument();
    expect(screen.getByText(/Grounded faithfulness: 100%/)).toBeInTheDocument();
  });

  it('HC-UIRES-018: a ?analyte= pick that moves the selection hides it too', async () => {
    await renderPage({ entry: { pathname: '/results', state: { explain: true } }, go: '/results?analyte=glucose' });
    fireEvent.click(await screen.findByRole('button', { name: /Generate Interpretation/i }));
    expect(await screen.findByText('Grounded explanation')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'go /results?analyte=glucose' }));
    await waitFor(() => expect(chartTitle()).toBe('GLUCOSE'));
    expect(screen.queryByText('Grounded explanation')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-019: a panel interpretation belongs to its tab
// ---------------------------------------------------------------------------

describe('HC-UIRES-019 a panel interpretation stays with the tab it was made for', () => {
  it('HC-UIRES-019: a named ?analyte= resets to All and takes the CBC dashboard with it', async () => {
    await renderPage({ go: '/results?analyte=glucose' });
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    fireEvent.click(await interpretButton('CBC'));
    expect(await screen.findByText('Panel summary text.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'go /results?analyte=glucose' }));
    await waitFor(() => expect(screen.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true'));
    expect(screen.queryByText('Panel summary text.')).toBeNull();
    // And it does not come back when the tab is chosen again.
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    await waitFor(() => expect(listNames()).toHaveLength(2));
    expect(screen.queryByText('Panel summary text.')).toBeNull();
  });

  it('HC-UIRES-019: a response that arrives after the tab changed is dropped, and its spinner is not shown under the new tab', async () => {
    await renderPage();
    await pageLoaded();
    let finish: (value: unknown) => void = () => undefined;
    const original = vi.mocked(api.apiPost).getMockImplementation()!;
    vi.mocked(api.apiPost).mockImplementation((url: string, ...rest: unknown[]) =>
      url.includes('/panels/') ? new Promise((resolve) => (finish = resolve)) : (original as (...args: unknown[]) => Promise<unknown>)(url, ...rest)
    );
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    fireEvent.click(await interpretButton('CBC'));
    expect(await screen.findByText('Generating panel interpretation...')).toBeInTheDocument();
    // The button's icon follows the tab the request belongs to (L0 ruling 6615916306): CBC holds the spinner.
    const spinnerIn = (button: HTMLElement) => button.querySelector('svg[class*="animate-spin"]');
    const cbcButton = screen.getByRole('button', { name: 'Interpret CBC Panel' });
    expect(cbcButton).toBeDisabled();
    expect(spinnerIn(cbcButton), 'under CBC the request is in flight').not.toBeNull();

    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CMP/ }));
    await waitFor(() => expect(screen.getByRole('tab', { name: /^CMP/ })).toHaveAttribute('aria-selected', 'true'));
    expect(screen.queryByText('Generating panel interpretation...'), 'the CBC request is not a CMP spinner').toBeNull();
    // CMP's own list has loaded, so the button is off for the request in flight, not for a missing date. A second
    // mutate would drop the first call's onSuccess, so it stays disabled; it just does not spin.
    await waitFor(() => expect(listNames().length).toBeGreaterThan(0));
    const cmpButton = await screen.findByRole('button', { name: 'Interpret CMP Panel' });
    expect(cmpButton).toBeDisabled();
    expect(spinnerIn(cmpButton), 'the CBC request is not a CMP button spinner').toBeNull();

    await act(async () => {
      finish({
        id: 'panel-1',
        panel_name: 'cbc',
        collected_at: '2026-04-10T00:00:00',
        observation_ids: ['o-hgb'],
        summary_text: 'Panel summary text.',
        overall_status: 'normal',
        relationship_insights: null,
        advice_text: null,
        citations: [],
        confidence_score: 0.9,
        requires_physician_review: false,
        created_at: '2026-04-10T00:00:00',
      });
    });
    expect(screen.queryByText('Panel summary text.'), 'not under CMP').toBeNull();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    await waitFor(() => expect(listNames()).toHaveLength(2));
    expect(screen.queryByText('Panel summary text.'), 'dropped, not parked until CBC is back').toBeNull();
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-027: Interpret <panel> is asked for the panel's own date
// ---------------------------------------------------------------------------

describe('HC-UIRES-027 Interpret <panel> sends the panel\'s own collection date', () => {
  it('HC-UIRES-027: the newest observation of another analyte does not set the date', async () => {
    // The route matches the panel\'s observations on that day: another analyte\'s newer date would find none (404).
    setupApi({ observations: [observation('o-ldl', 'ldl_cholesterol', 'LDL Cholesterol', 142, 'mg/dL', { collected_at: '2026-08-02T00:00:00' }), ...OBSERVATIONS] });
    await renderPage();
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^CBC/ }));
    fireEvent.click(await interpretButton('CBC'));
    await waitFor(() =>
      expect(vi.mocked(api.apiPost).mock.calls.some((call) => String(call[0]).startsWith('/interpretations/panels/cbc/interpret'))).toBe(true)
    );
    const asked = vi.mocked(api.apiPost).mock.calls.map((call) => String(call[0])).filter((url) => url.includes('/panels/cbc/'));
    expect(asked).toEqual(['/interpretations/panels/cbc/interpret?collected_at=2026-04-10T00%3A00%3A00']);
  });

  it('HC-UIRES-027: a panel with no date offers a disabled button and posts nothing', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^Lipids/ }));
    const button = await screen.findByRole('button', { name: 'Interpret LIPID Panel' });
    await screen.findByText(/no results from this panel/i);
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(vi.mocked(api.apiPost).mock.calls.some((call) => String(call[0]).includes('/panels/'))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-022: an empty panel
// ---------------------------------------------------------------------------

describe('HC-UIRES-022 an empty panel has nothing to download or explain', () => {
  const emptyPanelRows: Control[] = [
    ...TAB_ROWS,
    { name: 'Lab results scroller', match: /^Lab results$/ },
    { name: 'Download chart as PNG', match: /^Download chart as PNG$/ },
    { name: 'Download chart as SVG', match: /^Download chart as SVG$/ },
    { name: 'Open Explain', match: /^Open Explain$/ },
    { name: 'Interpret LIPID Panel', match: /^Interpret LIPID Panel$/ },
  ];

  it('HC-UIRES-022: the exports are off, Explain is not offered, and the body does not say to choose a result', async () => {
    await renderPage();
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^Lipids/ }));
    expect(await screen.findByText(/no results from this panel/i)).toBeInTheDocument();
    expectControlSet(emptyPanelRows);
    expect(screen.getByRole('button', { name: 'Download chart as PNG' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Download chart as SVG' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: /explain this result/i })).toBeNull();
    expect(screen.queryByText(/choose a result/i)).toBeNull();
  });

  it('HC-UIRES-022: with Explain already open, an empty panel offers no Generate and no empty interpretation card', async () => {
    await renderPage({ entry: { pathname: '/results', state: { explain: true } } });
    await pageLoaded();
    fireEvent.mouseDown(screen.getByRole('tab', { name: /^Lipids/ }));
    expect(await screen.findByText(/no results from this panel/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Generate Interpretation/i })).toBeNull();
    expect(screen.queryByText('No interpretation yet')).toBeNull();
    expectControlSet(emptyPanelRows);
  });

  it('HC-UIRES-022: the exports are off while the trend loads, and a click then downloads nothing', async () => {
    const anchors: string[] = [];
    Object.defineProperty(HTMLAnchorElement.prototype, 'click', { configurable: true, writable: true, value(this: HTMLAnchorElement) { anchors.push(this.download); } });
    const base = vi.mocked(api.apiGet).getMockImplementation()!;
    vi.mocked(api.apiGet).mockImplementation(async (url: string, params?: Record<string, string>) =>
      url.startsWith('/observations/trends/') ? new Promise(() => {}) : base(url, params)
    );
    await renderPage();
    await screen.findByRole('button', { name: /^Hemoglobin/ });
    expect(screen.getByRole('button', { name: 'Download chart as PNG' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Download chart as SVG' }));
    expect(anchors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-020: the gauge prints a verdict only on a finite scale
// ---------------------------------------------------------------------------

describe('HC-UIRES-020 ReferenceRangeComparison prints a verdict only when value and both bounds are finite', () => {
  async function gauge(value: number, refLow: number, refHigh: number) {
    const { ReferenceRangeComparison } = (await import(/* @vite-ignore */ RANGE_MODULE)) as typeof import('@/components/lab-interpreter/ReferenceRangeComparison');
    return render(<ReferenceRangeComparison value={value} refLow={refLow} refHigh={refHigh} unit="mg/dL" />);
  }

  it('HC-UIRES-020: a finite scale still reads Low, High and Normal', async () => {
    for (const [value, word] of [[60, 'Low'], [120, 'High'], [80, 'Normal']] as const) {
      const view = await gauge(value, 70, 99);
      expect(view.container.textContent).toContain(`(${word})`);
      view.unmount();
    }
  });

  it('HC-UIRES-020: a NaN or infinite value or bound prints the value and no verdict word', async () => {
    for (const [value, low, high] of [[Number.NaN, 70, 99], [80, Number.NaN, 99], [80, 70, Number.POSITIVE_INFINITY], [Number.POSITIVE_INFINITY, 70, 99]] as const) {
      const view = await gauge(value, low, high);
      expect(view.container.textContent, `${value} in ${low}..${high}`).not.toMatch(/\((Low|High|Normal)\)/);
      expect(view.container.textContent).toContain('mg/dL');
      view.unmount();
    }
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-023: the card's toggle names what it opens
// ---------------------------------------------------------------------------

describe('HC-UIRES-023 the card toggle matches the heading it opens', () => {
  it('HC-UIRES-023: the toggle reads "Hide questions to ask" over "Questions you could ask your clinician"; nothing on the card says Recommendations', async () => {
    const { InterpretedResultCard } = (await import(/* @vite-ignore */ CARD_MODULE)) as typeof import('@/components/lab-interpreter/InterpretedResultCard');
    render(<InterpretedResultCard interpretation={{ ...STORED_CARD, advice_text: 'Ask about a repeat test.' }} analyteName="Hemoglobin" />);
    // The advice starts open, so the toggle offers to hide it.
    expect(screen.getByText('Questions you could ask your clinician')).toBeInTheDocument();
    expect(screen.getByText('Ask about a repeat test.')).toBeInTheDocument();
    expect(screen.queryByText(/recommendations/i)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /hide questions to ask/i }));
    expect(screen.queryByText('Questions you could ask your clinician')).toBeNull();
    expect(screen.getByRole('button', { name: /show questions to ask/i })).toBeInTheDocument();
    expect(screen.queryByText(/recommendations/i)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-026: "Normal Range" is claimed only for a value inside a range the chart has
// ---------------------------------------------------------------------------

describe('HC-UIRES-026 the Normal Range badge', () => {
  // The trend route sends is_abnormal false for a point with no range (api/observations.py), so the flag alone proves nothing.
  function withLatest(value: number, over: Partial<TrendData>, abnormal = false) {
    return (canonical: string): TrendData => ({
      ...trendFor(canonical, 'HEMOGLOBIN'),
      data_points: [trendPoint('2026-01-10T00:00:00', value, { is_abnormal: abnormal })],
      ...over,
    });
  }
  async function open(trend: (canonical: string) => TrendData) {
    setupApi({ trend });
    await renderPage();
    await pageLoaded();
  }

  it('HC-UIRES-026: a value inside the range shows Normal Range', async () => {
    await open(withLatest(14.2, {}));
    expect(await screen.findByText('Normal Range')).toBeInTheDocument();
    expect(screen.queryByText('Outside Range')).toBeNull();
  });

  it('HC-UIRES-026: a result with no range and no flag shows neither badge', async () => {
    await open(withLatest(14.2, { ref_low: null, ref_high: null }));
    await screen.findByText(/Latest value: 14.2/);
    expect(screen.queryByText('Normal Range')).toBeNull();
    expect(screen.queryByText('Outside Range')).toBeNull();
  });

  it('HC-UIRES-026: a value outside the range that the route left unflagged shows Outside Range, never Normal Range or Flagged (L0 ruling 6615916306)', async () => {
    await open(withLatest(130, { ref_low: 70, ref_high: 99 }));
    await screen.findByText(/Latest value: 130/);
    expect(await screen.findByText('Outside Range')).toBeInTheDocument();
    expect(screen.queryByText('Normal Range')).toBeNull();
    expect(screen.queryByText('Flagged on the report')).toBeNull();
  });

  it('HC-UIRES-026: an unflagged value below the low bound shows Outside Range, never Normal Range or Flagged', async () => {
    await open(withLatest(50, { ref_low: 70, ref_high: 99 }));
    await screen.findByText(/Latest value: 50/);
    expect(await screen.findByText('Outside Range')).toBeInTheDocument();
    expect(screen.queryByText('Normal Range')).toBeNull();
    expect(screen.queryByText('Flagged on the report')).toBeNull();
  });

  it('HC-UIRES-026: a flagged value below the low bound shows Outside Range alone', async () => {
    await open(withLatest(50, { ref_low: 70, ref_high: 99 }, true));
    expect(await screen.findByText('Outside Range')).toBeInTheDocument();
    expect(screen.queryByText('Normal Range')).toBeNull();
    expect(screen.queryByText('Flagged on the report')).toBeNull();
  });

  it('HC-UIRES-026: float noise on the bound is not outside: the flag is the report\'s, an unflagged value is Normal Range', async () => {
    // normalize.py can hand back 99.10010000000001 for a value the report printed as 99.1001; the ribbon cleans it
    // to 12 significant digits, so the badge must read the same number.
    await open(withLatest(99.10010000000001, { ref_low: 70, ref_high: 99.1001 }, true));
    expect(await screen.findByText('Flagged on the report')).toBeInTheDocument();
    expect(screen.queryByText('Outside Range')).toBeNull();
    expect(screen.queryByText('Normal Range')).toBeNull();
    cleanup();
    await open(withLatest(99.10010000000001, { ref_low: 70, ref_high: 99.1001 }));
    expect(await screen.findByText('Normal Range')).toBeInTheDocument();
    expect(screen.queryByText('Outside Range')).toBeNull();
    expect(screen.queryByText('Flagged on the report')).toBeNull();
  });

  it('HC-UIRES-026: the printed Latest value is the cleaned number the ribbon shows', async () => {
    await open(withLatest(194.48000000000002, { ref_low: 70, ref_high: 99 }));
    expect(await screen.findByText('Latest value: 194.48 g/dL')).toBeInTheDocument();
  });

  it('HC-UIRES-026: a flagged value outside the range shows Outside Range and never Normal Range', async () => {
    await open(withLatest(130, { ref_low: 70, ref_high: 99 }, true));
    expect(await screen.findByText('Outside Range')).toBeInTheDocument();
    expect(screen.queryByText('Normal Range')).toBeNull();
    expect(screen.queryByText('Flagged on the report')).toBeNull();
  });

  it('HC-UIRES-026: a flagged value inside the band is the report\'s flag, not Outside Range, and is not hidden', async () => {
    await open(withLatest(14.2, {}, true));
    expect(await screen.findByText('Flagged on the report')).toBeInTheDocument();
    expect(screen.queryByText('Outside Range')).toBeNull();
    expect(screen.queryByText('Normal Range')).toBeNull();
  });

  it('HC-UIRES-026: a flagged value on a chart with no range is the report\'s flag, not Outside Range', async () => {
    await open(withLatest(14.2, { ref_low: null, ref_high: null }, true));
    expect(await screen.findByText('Flagged on the report')).toBeInTheDocument();
    expect(screen.queryByText('Outside Range')).toBeNull();
    expect(screen.queryByText('Normal Range')).toBeNull();
  });

  it('HC-UIRES-026: a value on either bound is inside the range', async () => {
    await open(withLatest(12, {}));
    expect(await screen.findByText('Normal Range')).toBeInTheDocument();
    cleanup();
    await open(withLatest(17.5, {}));
    expect(await screen.findByText('Normal Range')).toBeInTheDocument();
  });

  it('HC-UIRES-026: a one-sided limit is a range: inside it is Normal Range, past it is Outside Range', async () => {
    await open(withLatest(90, { ref_low: null, ref_high: 99 }));
    expect(await screen.findByText('Normal Range')).toBeInTheDocument();
    cleanup();
    await open(withLatest(130, { ref_low: null, ref_high: 99 }, true));
    expect(await screen.findByText('Outside Range')).toBeInTheDocument();
    expect(screen.queryByText('Normal Range')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// HC-UIRES-024: no analyte name reaches browser storage (L0 ruling, PR #476 comment 6606545865)
// ---------------------------------------------------------------------------

describe('HC-UIRES-024 the ribbon puts no analyte name in sessionStorage or localStorage', () => {
  // The suite's localStorage is a plain object with no key() or length (setup.ts), so it cannot be listed. Every
  // setItem on either storage is recorded instead, and sessionStorage (jsdom's real one) is also listed as it stands.
  // jsdom's sessionStorage is a Storage, and spying on the instance would store a literal 'setItem' key and record
  // nothing, so the spy goes on Storage.prototype. The plain-object localStorage is spied on directly.
  type Write = { area: string; key: string; value: string };
  const spies: Array<{ mockRestore: () => void }> = [];
  function recordWrites(): Write[] {
    const writes: Write[] = [];
    const wrap = (area: string, target: Storage) => {
      const original = target.setItem;
      const spy = vi.spyOn(target, 'setItem').mockImplementation(function (this: Storage, key: string, value: string) {
        writes.push({ area, key: String(key), value: String(value) });
        original.call(this, key, value);
      });
      spies.push(spy);
    };
    wrap('localStorage', window.localStorage);
    wrap('sessionStorage', Object.getPrototypeOf(window.sessionStorage) as Storage);
    return writes;
  }
  afterEach(() => {
    spies.splice(0).forEach((spy) => spy.mockRestore());
  });
  function storedText(writes: Write[]): string[] {
    const texts = writes.flatMap((w) => [w.key, w.value]);
    for (let i = 0; i < window.sessionStorage.length; i += 1) {
      const key = window.sessionStorage.key(i) as string;
      texts.push(key, window.sessionStorage.getItem(key) ?? '');
    }
    return texts;
  }
  const NAMES = ['fasting_glucose', 'Fasting Glucose', 'vitamin_b12', 'Vitamin B12'];
  function namesFound(writes: Write[]): string[] {
    const texts = storedText(writes).map((text) => text.toLowerCase());
    return NAMES.filter((name) => texts.some((text) => text.includes(name.toLowerCase())));
  }

  it('HC-UIRES-024: after a reveal, and after Lock now, neither storage holds the analyte canonical or display name', async () => {
    window.sessionStorage.clear();
    const writes = recordWrites();
    const animateCalls: Element[] = [];
    Object.defineProperty(Element.prototype, 'animate', {
      configurable: true,
      writable: true,
      value(this: Element) {
        animateCalls.push(this);
        return { cancel: () => undefined, finish: () => undefined, finished: Promise.resolve() };
      },
    });
    try {
      // A unique analyte, so no earlier test in this file has already used up its reveal.
      const { RangeRibbon } = await loadRibbon();
      const fasting = ribbonTrend(
        [trendPoint('2026-01-10T00:00:00', 92, { unit: 'mg/dL' }), trendPoint('2026-04-10T00:00:00', 101, { unit: 'mg/dL' })],
        { analyte_canonical: 'fasting_glucose', analyte_display_name: 'Fasting Glucose', unit: 'mg/dL', ref_low: 70, ref_high: 99 }
      );
      const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
      vi.mocked(api.apiPost).mockResolvedValue({ id: 'profile-123', is_locked: true });
      const view = render(
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={['/results']}>
            <ProfileMenu />
            <Probe />
            <RangeRibbon trend={fasting} />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // The reveal really ran (reduced motion is off in this suite). Without this, an empty storage proves nothing.
      expect(window.matchMedia('(prefers-reduced-motion: reduce)').matches).toBe(false);
      expect(animateCalls.length).toBeGreaterThan(0);
      expect(screen.getByRole('slider')).toHaveAttribute('aria-label', 'Fasting Glucose: results over time');
      expect(namesFound(writes)).toEqual([]);
      // Nothing the ribbon does touches storage at all (a write-then-remove or an encoded name would show here).
      expect(writes.filter((w) => w.key !== 'healthcentral-auth')).toEqual([]);

      // The real lock path: Lock now calls clearAuth() and queryClient.clear().
      const user = userEvent.setup();
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      await user.click(screen.getByRole('button', { name: 'Profile and settings' }));
      await user.click(screen.getByRole('button', { name: 'Lock now' }));
      await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false));
      expect(screen.getByTestId('location')).toHaveTextContent('/setup');
      expect(namesFound(writes)).toEqual([]);

      // A second analyte revealed after the lock leaves nothing behind either.
      animateCalls.length = 0;
      view.rerender(
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={['/results']}>
            <ProfileMenu />
            <Probe />
            <RangeRibbon
              trend={ribbonTrend(
                [trendPoint('2026-01-10T00:00:00', 410, { unit: 'pg/mL' }), trendPoint('2026-04-10T00:00:00', 450, { unit: 'pg/mL' })],
                { analyte_canonical: 'vitamin_b12', analyte_display_name: 'Vitamin B12', unit: 'pg/mL', ref_low: 200, ref_high: 900 }
              )}
            />
          </MemoryRouter>
        </QueryClientProvider>
      );
      expect(animateCalls.length).toBeGreaterThan(0);
      expect(namesFound(writes)).toEqual([]);
      expect(writes.filter((w) => w.key !== 'healthcentral-auth')).toEqual([]);
    } finally {
      delete (Element.prototype as unknown as { animate?: unknown }).animate;
    }
  });
});
