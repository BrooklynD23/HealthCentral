/**
 * UI-PG-RECORDS (HC-UIPIN-001..003 and the checks around them, vitest half): Timeline, Search and Pinboards.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md, "UI-PG-RECORDS". The Playwright half (Gate G on the three
 * routes, the stillness probe, the real-backend id match between /timeline and /observations) is
 * e2e/ui-records.spec.ts.
 *
 * The pages run on their real hooks. Only the HTTP layer (`@/services/api`) is replaced, by a small fake server that
 * answers by path and query, so a PATCH changes what the next GET returns. jsdom loads no Tailwind, so the class
 * contracts below pin what a stylesheet would do; the measured layout is e2e.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { focusManager, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom';
import * as api from '@/services/api';
import type { Observation } from '@/services/types';
import type { TimelineEvent, TimelineResponse } from '@/services/timeline';
import type { Pinboard, PinboardItem } from '@/services/pinboards';
import type { SearchResponse, SearchResult } from '@/services/search';
import { TimelinePage } from '@/pages/TimelinePage';
import { SearchPage } from '@/pages/SearchPage';
import { PinboardsPage } from '@/pages/PinboardsPage';
import { AddToPinboardButton } from '@/components/pinboards/AddToPinboardButton';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/api')>()),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

// jsdom has no pointer-capture API, and Radix menus call it on pointerdown.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
}
// jsdom has no scrollIntoView, and Radix menu items call it.
if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = () => {};

const PROFILE = 'profile-123';
const apiGet = vi.mocked(api.apiGet);
const apiPatch = vi.mocked(api.apiPatch);
const apiDelete = vi.mocked(api.apiDelete);

// ---------------------------------------------------------------------------
// The fake server
// ---------------------------------------------------------------------------
function obs(id: string, raw: string, canonical: string): Observation {
  return {
    id,
    profile_id: PROFILE,
    doc_id: 'doc-1',
    analyte_canonical: canonical,
    analyte_raw: raw,
    value: 5,
    value_text: null,
    unit: 'mg/dL',
    ref_low: null,
    ref_high: null,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2026-03-02T00:00:00',
    user_verified: true,
    extraction_confidence: 0.9,
    source_page: 1,
    source_bbox_json: null,
  };
}

function event(over: Partial<TimelineEvent> & Pick<TimelineEvent, 'event_id' | 'title'>): TimelineEvent {
  return {
    event_type: 'lab_results',
    event_date: '2026-03-02',
    event_date_source: 'document_date',
    doc_id: 'doc-1',
    related_ids: [],
    verification_status: 'verified',
    ...over,
  };
}

const OBSERVATIONS: Observation[] = [
  obs('o1', 'Glucose', 'glucose'),
  // No raw name: the canonical name is the fallback (the rule SourceTrace uses).
  obs('o2', '', 'ldl_cholesterol'),
  // A second Glucose row under another id: the name appears once.
  obs('o3', 'Glucose', 'glucose'),
  obs('o4', 'HbA1c', 'hba1c'),
  obs('o5', 'Sodium', 'sodium'),
  // The same canonical analyte under another spelling: the title counts it once (modules/timeline.py), so the names
  // must too.
  obs('o6', 'GLUCOSE', 'glucose'),
  obs('o7', 'Albumin', 'albumin'),
];

// o-missing is in no observation row: it adds no name, and never a guess.
const EV_MANY = event({ event_id: 'ev-1', title: 'Lab results (4 analytes)', related_ids: ['o1', 'o2', 'o3', 'o-missing'] });
const EV_ONE = event({ event_id: 'ev-2', title: 'Lab results (1 analyte)', related_ids: ['o4'], event_date: '2026-02-01' });
const EV_IMAGING = event({
  event_id: 'ev-3',
  event_type: 'imaging',
  title: 'Chest X-ray',
  related_ids: ['o1'],
  verification_status: 'unverified',
});
const EV_ORPHAN = event({ event_id: 'ev-4', title: 'Lab results (1 analyte) orphan', related_ids: ['o-missing'] });
// Only the lab_results filter answers with this one: the second answer has its own ids and names (recurring #17).
const EV_FILTERED = event({ event_id: 'ev-5', title: 'Lab results (2 analytes)', related_ids: ['o5', 'o1'], event_date: '2026-01-10' });

let timelineAll: TimelineResponse;
let timelineLabs: TimelineResponse;
let timelineFails = false;
let timelineAnswers = 0;
let observationsGate: Promise<void> | null = null;
let observationsFail = false;
let timelineGate: Promise<void> | null = null;
// Rows the observations route answers with beyond OBSERVATIONS (a document imported since the page last looked).
let extraObservations: Observation[] = [];

let pinboards: Pinboard[] = [];
let pinboardsGate: Promise<void> | null = null;
let boardItems: Record<string, PinboardItem[]> = {};
// Requests for the items of a board that no longer exists: the real route answers 404 (api/pinboards.py).
let itemsNotFound = 0;
let patchGate: Promise<void> | null = null;
let deleteGate: Promise<void> | null = null;

let searchFails = false;
let searchGate: Promise<void> | null = null;

function result(over: Partial<SearchResult> & Pick<SearchResult, 'id' | 'title'>): SearchResult {
  return {
    type: 'entity',
    doc_id: 'doc-1',
    snippet: `Snippet for ${over.title}`,
    date: '2026-01-15',
    verified_status: 'unverified',
    category: 'visit_notes',
    highlight_types: [],
    ...over,
  };
}

/** What GET /search/ answers for a query: each query has its own ids, so a second search is a different answer. */
function searchFor(q: string): SearchResponse {
  if (q === 'nothing') return { results: [], count: 0 };
  const results =
    q === 'migraine aura'
      ? [result({ id: 'e-2', title: 'Aura notes', type: 'document' })]
      : [
          result({ id: 'e-1', title: 'Diagnoses migraine' }),
          result({ id: 'd-1', title: 'Neurology letter', type: 'document', verified_status: 'verified' }),
        ];
  return { results, count: results.length };
}

function makeBoard(id: string, name: string): Pinboard {
  return { id, name, created_at: '', updated_at: '' };
}

function gate(): { wait: Promise<void>; open: () => void } {
  let open!: () => void;
  const wait = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { wait, open };
}

function setReducedMotion(reduce: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: reduce && query === '(prefers-reduced-motion: reduce)',
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
const originalMatchMedia = window.matchMedia;

beforeEach(() => {
  timelineAll = { events: [EV_MANY, EV_ONE, EV_IMAGING, EV_ORPHAN], undated: [] };
  timelineLabs = { events: [EV_ONE, EV_FILTERED], undated: [] };
  timelineFails = false;
  timelineAnswers = 0;
  timelineGate = null;
  observationsGate = null;
  observationsFail = false;
  pinboards = [makeBoard('board-a', 'Board A'), makeBoard('board-b', 'Board B')];
  pinboardsGate = null;
  boardItems = {};
  itemsNotFound = 0;
  patchGate = null;
  deleteGate = null;
  extraObservations = [];
  searchFails = false;
  searchGate = null;
  setReducedMotion(false);

  apiGet.mockImplementation((async (path: string, params?: Record<string, string>) => {
    if (path === '/timeline/') {
      if (timelineGate) await timelineGate;
      if (timelineFails) throw new api.ApiError(500, 'Server Error', 'timeline failed');
      timelineAnswers += 1;
      return params?.event_type === 'lab_results' ? timelineLabs : timelineAll;
    }
    if (path === '/observations/') {
      if (observationsGate) await observationsGate;
      if (observationsFail) throw new api.ApiError(500, 'Server Error', 'observations failed');
      return [...OBSERVATIONS, ...extraObservations];
    }
    if (path === '/pinboards/') {
      if (pinboardsGate) await pinboardsGate;
      return pinboards.map((b) => ({ ...b }));
    }
    const items = /^\/pinboards\/([^/]+)\/items$/.exec(path);
    if (items) {
      if (!pinboards.some((b) => b.id === items[1])) {
        itemsNotFound += 1;
        throw new api.ApiError(404, 'Not Found', 'no such pinboard');
      }
      return boardItems[items[1]] ?? [];
    }
    if (path === '/search/') {
      if (searchGate) await searchGate;
      if (searchFails) throw new api.ApiError(500, 'Server Error', 'search failed');
      return searchFor(params?.q ?? '');
    }
    throw new Error(`unmocked GET ${path}`);
  }) as never);

  apiPatch.mockImplementation((async (path: string, body: { name: string }) => {
    if (patchGate) await patchGate;
    const board = pinboards.find((b) => `/pinboards/${b.id}` === path);
    if (!board) throw new api.ApiError(404, 'Not Found', 'no such pinboard');
    board.name = body.name;
    return { ...board };
  }) as never);
  apiDelete.mockImplementation((async (path: string) => {
    if (deleteGate) await deleteGate;
    pinboards = pinboards.filter((b) => `/pinboards/${b.id}` !== path);
  }) as never);

  useAuthStore.getState().setAuth({ token: 'test-token', profileId: PROFILE, profileName: 'Test Profile' });
});

afterEach(() => {
  cleanup();
  window.matchMedia = originalMatchMedia;
  vi.restoreAllMocks();
});

function Probe() {
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <>
      <div data-testid="location">{`${location.pathname}${location.search}`}</div>
      <button type="button" onClick={() => navigate('/search?q=other')}>
        go other
      </button>
    </>
  );
}

function renderAt(
  ui: React.ReactNode,
  route = '/',
  client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Probe />
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

/** The page's own root element: the first child of the render container after the probe. */
function pageRoot(container: HTMLElement): HTMLElement {
  return container.querySelector('h1')!.parentElement!.parentElement as HTMLElement;
}

const cardOf = (title: string) => screen.getByText(title).closest('li') as HTMLElement;
const analytesOf = (title: string) => cardOf(title).querySelector('[data-timeline-analytes]');

/** Lets React Query hand a resolved answer to the component. */
const settle = () => new Promise((resolve) => setTimeout(resolve, 60));

// ---------------------------------------------------------------------------
// HC-UIPIN-001: a timeline card names its analytes.
// ---------------------------------------------------------------------------
describe('HC-UIPIN-001 timeline cards name their analytes', () => {
  it('HC-UIPIN-001: a lab card names its analytes under the backend title, sorted by name, once each per canonical analyte, with no guess for an unknown id', async () => {
    // Would not notice: a name taken from the wrong field (canonical over raw), a duplicate Glucose row that prints
    // twice, an unknown id that prints its raw id, or a non-lab card that borrows the lab ids. The title text is
    // unchanged, because TW4-TIMELINE reads it.
    // RED today: no card names an analyte; the card says only "Lab results (4 analytes)".
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByText('Lab results (4 analytes)');

    expect(analytesOf('Lab results (4 analytes)')).toHaveTextContent(/^Glucose, ldl_cholesterol$/);
    expect(analytesOf('Lab results (1 analyte)')).toHaveTextContent(/^HbA1c$/);
    // The imaging card has related ids too, but only lab cards carry analyte names.
    expect(analytesOf('Chest X-ray')).toBeNull();
    // Every id unknown: no element at all, so the card does not move for an empty line.
    expect(analytesOf('Lab results (1 analyte) orphan')).toBeNull();
    expect(document.body.textContent).not.toContain('o-missing');
  });

  it('HC-UIPIN-001: the names are marked T0 with their own attribute, wrap without a cut, and sit under the title', async () => {
    // Would not notice: names that are truncated (a long analyte name cut off), or missing from the G10 probe.
    // RED today: there is no analyte element.
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByText('Lab results (4 analytes)');
    const names = analytesOf('Lab results (4 analytes)')!;
    expect(names).toHaveAttribute('data-t0');
    const tokens = names.className.split(/\s+/);
    expect(tokens).toContain('[overflow-wrap:anywhere]');
    expect(tokens).not.toContain('truncate');
    const title = screen.getByText('Lab results (4 analytes)');
    expect(title.compareDocumentPosition(names) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('HC-UIPIN-001: the card date and the verification badge carry data-t0 and a named attribute', async () => {
    // Would not notice: a date or a verification word the stillness probe cannot see (plan section 2.7 lists both).
    // RED today: neither carries data-t0.
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByText('Lab results (4 analytes)');
    const card = cardOf('Lab results (4 analytes)');
    const date = card.querySelector('[data-timeline-date]');
    expect(date).toHaveAttribute('data-t0');
    expect(date).toHaveTextContent('2026-03-02 · document date');
    const badge = card.querySelector('[data-timeline-verification]');
    expect(badge).toHaveAttribute('data-t0');
    expect(badge).toHaveTextContent('Verified');
    expect(cardOf('Chest X-ray').querySelector('[data-timeline-verification]')).toHaveTextContent('Needs verification');
  });

  it('HC-UIPIN-001: no card shows while the observations are held, and the names arrive with the cards', async () => {
    // Would not notice: cards that render at once and get a new line when the names arrive (every later card moves,
    // G2 and G10). The timeline has answered; only the observations are held. After the release, the title and its
    // names are on screen in the same step.
    // RED today: the card is on screen as soon as the timeline answers, with no names.
    const held = gate();
    observationsGate = held.wait;
    renderAt(<TimelinePage />, '/timeline');
    await waitFor(() => expect(timelineAnswers).toBe(1));
    await settle();
    expect(apiGet).toHaveBeenCalledWith('/observations/', expect.anything());
    expect(screen.queryByText('Lab results (4 analytes)')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Loading timeline');
    // The empty state must not flash either.
    expect(screen.queryByText('No events yet')).not.toBeInTheDocument();

    held.open();
    await screen.findByText('Lab results (4 analytes)');
    expect(analytesOf('Lab results (4 analytes)')).toHaveTextContent('Glucose, ldl_cholesterol');
  });

  it('HC-UIPIN-001: when the observations fail, the cards still render with the backend title and no names, and no alert', async () => {
    // Would not notice: a timeline hidden because a second query failed, or an error shown for a missing nicety.
    // RED today: passes the "cards render" half only; the call to /observations/ is never made, which this asserts.
    observationsFail = true;
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByText('Lab results (4 analytes)');
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith('/observations/', expect.anything()));
    await settle();
    expect(document.querySelector('[data-timeline-analytes]')).toBeNull();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('Lab results (1 analyte)')).toBeInTheDocument();
  });

  it('HC-UIPIN-001: a failed timeline shows its alert alone, with no spinner while the observations are still held', async () => {
    // Would not notice: a spinner and the alert on screen together (the spinner waits on the observations too), then
    // the spinner leaves when they answer and the alert moves up by its height (measured 176 px; an error alert is T0).
    // RED today: the loading status is on screen beside the alert.
    const held = gate();
    observationsGate = held.wait;
    timelineFails = true;
    renderAt(<TimelinePage />, '/timeline');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not load timeline');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    held.open();
    await settle();
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('HC-UIPIN-001: a refetch of a failed observations query (window focus) does not take the cards away', async () => {
    // Would not notice: cards that unmount while the failed query refetches (isLoading is true again for a query with
    // no data), so a focus change blanks the page and every card re-enters. The refetch is held to make it visible.
    // RED today: the cards are gone while the refetch is in flight.
    observationsFail = true;
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByText('Lab results (4 analytes)');
    await settle();
    expect(document.querySelector('[data-timeline-analytes]')).toBeNull();

    const held = gate();
    observationsGate = held.wait;
    act(() => {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
    });
    await settle();
    expect(apiGet.mock.calls.filter(([path]) => path === '/observations/').length).toBeGreaterThan(1);
    expect(screen.getByText('Lab results (4 analytes)')).toBeInTheDocument();
    expect(screen.getByText('Lab results (1 analyte)')).toBeInTheDocument();
    held.open();
    await settle();
    expect(screen.getByText('Lab results (4 analytes)')).toBeInTheDocument();
  });

  it('HC-UIPIN-001: Try again asks for the timeline and the observations again, keeps focus on the page, and the names arrive with the cards', async () => {
    // Would not notice: a Try again that refetches only the timeline, so the observations stay failed and the cards
    // come back unnamed after the backend recovered; or a button that unmounts with focus on it, which drops focus on
    // <body>. Both queries fail first; both recover before the click.
    // RED today: the observations are not asked for again, and focus ends on <body>.
    const user = userEvent.setup();
    timelineFails = true;
    observationsFail = true;
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByRole('alert');
    await waitFor(() => expect(apiGet.mock.calls.filter(([path]) => path === '/observations/').length).toBe(1));
    await settle();

    timelineFails = false;
    observationsFail = false;
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(screen.getByLabelText('Event type')).toHaveFocus();
    await screen.findByText('Lab results (4 analytes)');
    expect(analytesOf('Lab results (4 analytes)')).toHaveTextContent('Glucose, ldl_cholesterol');
    expect(screen.getByLabelText('Event type')).toHaveFocus();
  });

  it('HC-UIPIN-001: observations cached before an import do not leave the new lab card unnamed on the first visit', async () => {
    // Would not notice: the names come from ['observations'], which the app keeps for 5 minutes and which a write made
    // elsewhere (another tab, a restore) leaves stale. The test loads the observations first, then adds a row on the server, then opens the page
    // again with the same cache (the timeline is gone from it, as on a first visit). Every other test starts with an
    // empty cache and cannot see this.
    // RED today: the card says "Lab results (1 analyte) fresh" with no name, and the page never asks again.
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 300_000 }, mutations: { retry: false } },
    });
    const first = renderAt(<TimelinePage />, '/timeline', client);
    await screen.findByText('Lab results (4 analytes)');
    first.unmount();
    await settle();

    extraObservations = [obs('o-new', 'Ferritin', 'ferritin')];
    timelineAll = {
      events: [event({ event_id: 'ev-new', title: 'Lab results (1 analyte) fresh', related_ids: ['o-new'], event_date: '2026-04-01' })],
      undated: [],
    };
    client.removeQueries({ queryKey: ['timeline'] });
    renderAt(<TimelinePage />, '/timeline', client);
    await screen.findByText('Lab results (1 analyte) fresh');
    // In the same step as the card: the cards were held while the observations were asked for once more.
    expect(analytesOf('Lab results (1 analyte) fresh')).toHaveTextContent(/^Ferritin$/);
    expect(apiGet.mock.calls.filter(([path]) => path === '/observations/')).toHaveLength(2);
  });

  /** A cache that keeps the observations for 5 minutes, as the app does. */
  const appClient = () =>
    new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 300_000 }, mutations: { retry: false } } });

  /** Loads the page once, then returns the cache with a new lab card whose observation the cached answer lacks. */
  async function cacheThenImport(client: QueryClient) {
    const first = renderAt(<TimelinePage />, '/timeline', client);
    await screen.findByText('Lab results (4 analytes)');
    first.unmount();
    await settle();
    extraObservations = [obs('o-new', 'Ferritin', 'ferritin')];
    timelineAll = {
      events: [event({ event_id: 'ev-new', title: 'Lab results (1 analyte) fresh', related_ids: ['o-new'], event_date: '2026-04-01' })],
      undated: [],
    };
    client.removeQueries({ queryKey: ['timeline'] });
  }
  const observationCalls = () => apiGet.mock.calls.filter(([path]) => path === '/observations/').length;

  it('HC-UIPIN-001: while the one refresh of cached observations is held, no card shows; the names arrive with the card', async () => {
    // Would not notice: a refresh whose answer is not waited for. The test above answers the refresh at once, so a page
    // that paints the card unnamed and names it a moment later reads the same; here the refresh is held, and the card
    // must not exist until it is released (a name line added later moves every card below it).
    // RED if the hold on `needsRefresh || refreshing` is removed: the unnamed card shows while the refresh is held.
    const client = appClient();
    await cacheThenImport(client);
    const held = gate();
    observationsGate = held.wait;
    renderAt(<TimelinePage />, '/timeline', client);
    await waitFor(() => expect(observationCalls()).toBe(2));
    await waitFor(() => expect(timelineAnswers).toBe(2));
    await settle();
    expect(screen.queryByText('Lab results (1 analyte) fresh')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Loading timeline');

    held.open();
    await screen.findByText('Lab results (1 analyte) fresh');
    expect(analytesOf('Lab results (1 analyte) fresh')).toHaveTextContent(/^Ferritin$/);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('HC-UIPIN-001: a refused refresh of cached observations still shows the card, with no names and no status left behind', async () => {
    // Would not notice: a refresh that never counts as done when it fails, so the cards stay held for good (a spinner
    // with the timeline answered and nothing on screen), or a refresh that retries on every render.
    // RED if `setRefreshed(true)` is removed: needsRefresh stays true after the failed refresh and the cards never show.
    const client = appClient();
    await cacheThenImport(client);
    observationsFail = true;
    renderAt(<TimelinePage />, '/timeline', client);
    await screen.findByText('Lab results (1 analyte) fresh');
    await settle();
    expect(analytesOf('Lab results (1 analyte) fresh')).toBeNull();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(observationCalls()).toBe(2);
  });

  it('HC-UIPIN-001: Try again holds the cards until the observations answer too, so the names arrive with them', async () => {
    // Would not notice: a Try again whose timeline answer paints the cards while the observations (failed before, so
    // fetched already) are still on their way; the names then arrive as a new line and move every later card. The
    // observations are held before the click, which the test above (answered at once) cannot see.
    // RED if `|| retrying` is removed: the unnamed cards show while the observations are held.
    const user = userEvent.setup();
    timelineFails = true;
    observationsFail = true;
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByRole('alert');
    await waitFor(() => expect(observationCalls()).toBe(1));
    await settle();

    timelineFails = false;
    observationsFail = false;
    const held = gate();
    observationsGate = held.wait;
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(timelineAnswers).toBe(1));
    await waitFor(() => expect(observationCalls()).toBe(2));
    await settle();
    expect(screen.queryByText('Lab results (4 analytes)')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Loading timeline');

    held.open();
    await screen.findByText('Lab results (4 analytes)');
    expect(analytesOf('Lab results (4 analytes)')).toHaveTextContent('Glucose, ldl_cholesterol');
  });

  it('HC-UIPIN-001: a later visit after a failed observations query holds the cards for the new answer too', async () => {
    // Would not notice: the hold read from the query's own isFetched, which the failed answer of the first visit has
    // already set. The second visit then paints the cached timeline at once, unnamed, and the names arrive later and
    // move every card (measured 66 px). The hold is per visit. The first visit's observations fail; the second's are held.
    // RED with `observationsFetched` in place of the per-visit flag: the unnamed cards show while the answer is held.
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    observationsFail = true;
    const first = renderAt(<TimelinePage />, '/timeline', client);
    await screen.findByText('Lab results (4 analytes)');
    await waitFor(() => expect(observationCalls()).toBe(1));
    await settle();
    first.unmount();
    await settle();

    observationsFail = false;
    const held = gate();
    observationsGate = held.wait;
    renderAt(<TimelinePage />, '/timeline', client);
    await waitFor(() => expect(observationCalls()).toBe(2));
    await settle();
    expect(screen.queryByText('Lab results (4 analytes)')).not.toBeInTheDocument();

    held.open();
    await screen.findByText('Lab results (4 analytes)');
    expect(analytesOf('Lab results (4 analytes)')).toHaveTextContent('Glucose, ldl_cholesterol');
  });

  it('HC-UIPIN-001: an id that stays unmatched after that one refresh asks once, and a later refetch does not hold the cards', async () => {
    // Would not notice: a refresh loop for an id that no observation has (a deleted row), or cards that blink on every
    // window focus. The held refetch after the first settle must leave the cards in place.
    // RED today: no refresh at all, so the first count below is 1, not 2.
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 300_000 }, mutations: { retry: false } },
    });
    const first = renderAt(<TimelinePage />, '/timeline', client);
    await screen.findByText('Lab results (4 analytes)');
    first.unmount();
    await settle();
    client.removeQueries({ queryKey: ['timeline'] });
    renderAt(<TimelinePage />, '/timeline', client);
    await screen.findByText('Lab results (4 analytes)');
    await settle();
    // o-missing is in no row: one refresh, no more.
    expect(apiGet.mock.calls.filter(([path]) => path === '/observations/')).toHaveLength(2);

    const held = gate();
    observationsGate = held.wait;
    client.invalidateQueries({ queryKey: ['observations'] });
    await settle();
    expect(screen.getByText('Lab results (4 analytes)')).toBeInTheDocument();
    held.open();
    await settle();
    expect(screen.getByText('Lab results (4 analytes)')).toBeInTheDocument();
    expect(apiGet.mock.calls.filter(([path]) => path === '/observations/')).toHaveLength(3);
  });

  it('HC-UIPIN-001: two spellings of one canonical analyte are named once, and the names are sorted so every card reads the same way', async () => {
    // Would not notice: names deduped on the exact spelling while the title counts canonical analytes, so
    // "Lab results (2 analytes)" sat over "Albumin, Glucose, GLUCOSE"; or an order that follows the random id sort of
    // the backend, so two cards list the same analytes in different orders.
    // RED today: the names are "Albumin, Glucose, GLUCOSE" (related ids in the order o7, o6, o1).
    timelineAll = {
      events: [event({ event_id: 'ev-6', title: 'Lab results (2 analytes) canonical', related_ids: ['o7', 'o6', 'o1'] })],
      undated: [],
    };
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByText('Lab results (2 analytes) canonical');
    expect(analytesOf('Lab results (2 analytes) canonical')).toHaveTextContent(/^Albumin, Glucose$/);
  });

  it('HC-UIPIN-001: the observations are asked for without the page filters, and a second answer has its own names', async () => {
    // Would not notice: an observations query that takes the date filters, so ids in the other window go unnamed.
    // The lab_results filter returns another event with its own ids; its names must be its own (recurring #17).
    // RED today: /observations/ is never asked for.
    const user = userEvent.setup();
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByText('Lab results (4 analytes)');

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-01' } });
    await waitFor(() =>
      expect(apiGet).toHaveBeenCalledWith('/timeline/', expect.objectContaining({ date_from: '2026-01-01' }))
    );
    await user.selectOptions(screen.getByLabelText('Event type'), 'lab_results');
    await screen.findByText('Lab results (2 analytes)');
    expect(analytesOf('Lab results (2 analytes)')).toHaveTextContent(/^Glucose, Sodium$/);

    const asked = apiGet.mock.calls.filter(([path]) => path === '/observations/');
    expect(asked.length).toBeGreaterThan(0);
    for (const [, params] of asked) expect(Object.keys((params as object | undefined) ?? {})).toEqual([]);
  });

  it('HC-UIPIN-001: the page root has no padding of its own (the layout main pads), and the spinner honours reduced motion', async () => {
    // Would not notice: a doubled p-8 (the content sits 64 px in on a phone), or a spinner that spins for users who
    // asked for reduced motion (G5, the #456 class).
    // RED today: the root has p-8 and the spinner has a bare animate-spin.
    const held = gate();
    timelineGate = held.wait;
    const { container } = renderAt(<TimelinePage />, '/timeline');
    expect(pageRoot(container).className.split(/\s+/)).not.toContain('p-8');
    const status = screen.getByRole('status');
    const spinner = status.querySelector('svg')!;
    const tokens = spinner.getAttribute('class')!.split(/\s+/);
    expect(tokens).toContain('motion-safe:animate-spin');
    expect(tokens).not.toContain('animate-spin');
    held.open();
    await screen.findByText('Lab results (4 analytes)');
  });

  it('HC-UIPIN-001: the native event-type select uses theme tokens, not bg-white and border-black/8', async () => {
    // Would not notice: a select that stays white in dark mode (axe color-contrast in dark; e2e GATE G1).
    // RED today: bg-white border-black/8.
    renderAt(<TimelinePage />, '/timeline');
    await screen.findByText('Lab results (4 analytes)');
    const tokens = screen.getByLabelText('Event type').className.split(/\s+/);
    expect(tokens).toContain('bg-surface-elevated');
    expect(tokens).toContain('border-border');
    expect(tokens).not.toContain('bg-white');
    expect(tokens).not.toContain('border-black/8');
  });

  it('HC-UIPIN-001: a failed timeline is a static alert with Try again, outside the S1 entrance, and it refetches', async () => {
    // Would not notice: error text inside EmptyState, whose ShowcaseReveal fades and rises it (error text is T0).
    // The control line shows the detector can fail: a real EmptyState on the same page has an inline-styled ancestor.
    // RED today: the error is an EmptyState with no role="alert" and no Try again.
    const user = userEvent.setup();
    timelineFails = true;
    renderAt(<TimelinePage />, '/timeline');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not load timeline');
    expect(alert.closest('[style*="opacity"], [style*="transform"]')).toBeNull();
    expect(alert.closest('[data-timeline-error]')).not.toBeNull();
    const before = apiGet.mock.calls.filter(([path]) => path === '/timeline/').length;
    timelineFails = false;
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('Lab results (4 analytes)');
    expect(apiGet.mock.calls.filter(([path]) => path === '/timeline/').length).toBeGreaterThan(before);
  });

  it('HC-UIPIN-001: the empty timeline offers a way forward to the inbox', async () => {
    // Would not notice: a dead-end empty state. The action is a real link, and no data-t0 sits inside the EmptyState.
    // RED today: no action.
    timelineAll = { events: [], undated: [] };
    renderAt(<TimelinePage />, '/timeline');
    const heading = await screen.findByRole('heading', { name: 'No events yet' });
    const link = screen.getByRole('link', { name: 'Import a document' });
    expect(link).toHaveAttribute('href', '/inbox');
    const emptyCard = heading.closest('.rounded-2xl')!;
    expect(emptyCard.querySelector('[data-t0]')).toBeNull();
    // Control for the detector above: an EmptyState is inside an inline-styled S1 group.
    expect(heading.closest('[style*="opacity"], [style*="transform"]')).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// HC-UIPIN-003: the search page shows the query it searched.
// ---------------------------------------------------------------------------
describe('HC-UIPIN-003 search echoes its query', () => {
  const echo = () => document.querySelector('[data-search-query]');

  it('HC-UIPIN-003: the echo shows the searched query, not the draft, and updates only on submit', async () => {
    // Would not notice: an echo read from the input state, which changes on every key. The draft is typed without
    // Enter, and the echo must stay; then Enter, and the second answer (its own ids) must replace it.
    // RED today: the page has no echo.
    const user = userEvent.setup();
    renderAt(<SearchPage />, '/search?q=migraine');
    await screen.findByText('Diagnoses migraine');
    expect(echo()).toHaveTextContent('migraine');

    const input = screen.getByRole('searchbox', { name: 'Search health records' });
    await user.type(input, ' aura');
    expect(input).toHaveValue('migraine aura');
    expect(echo()).toHaveTextContent('migraine');
    expect(echo()).not.toHaveTextContent('aura');

    await user.type(input, '{Enter}');
    await screen.findByText('Aura notes');
    expect(echo()).toHaveTextContent('migraine aura');
    expect(screen.queryByText('Diagnoses migraine')).not.toBeInTheDocument();
  });

  it('HC-UIPIN-003: the echo is shown for zero results and for an error, and a long unbroken query wraps', async () => {
    // Would not notice: an echo only in the results branch, or one that pushes the page wider than 320 px (G6).
    // RED today: no echo in any branch.
    const { unmount } = renderAt(<SearchPage />, '/search?q=nothing');
    await screen.findByText('No matching records');
    expect(echo()).toHaveTextContent('nothing');
    unmount();

    searchFails = true;
    const long = 'x'.repeat(240);
    const second = renderAt(<SearchPage />, `/search?q=${long}`);
    await screen.findByRole('alert');
    expect(echo()).toHaveTextContent(long);
    expect(echo()!.className.split(/\s+/)).toContain('[overflow-wrap:anywhere]');
    second.unmount();
  });

  it('HC-UIPIN-003: the query is printed as text: markup in it is not interpreted', async () => {
    // Would not notice: an echo built with dangerouslySetInnerHTML. The query holds a tag; it must be text.
    // RED today: no echo.
    renderAt(<SearchPage />, `/search?q=${encodeURIComponent('<img src=x onerror=alert(1)>')}`);
    await waitFor(() => expect(echo()).not.toBeNull());
    expect(echo()!.textContent).toContain('<img src=x onerror=alert(1)>');
    expect(echo()!.querySelector('img')).toBeNull();
  });

  it('HC-UIPIN-003: the input follows the URL when it changes on the same page', async () => {
    // Would not notice: the palette sends /search?q=other while this page is open (same pathname, so the layout
    // does not remount it); the box must show the new query, or the next Enter searches the old one.
    // RED today: the input keeps its first value.
    const user = userEvent.setup();
    renderAt(<SearchPage />, '/search?q=migraine');
    const input = screen.getByRole('searchbox', { name: 'Search health records' });
    expect(input).toHaveValue('migraine');
    await user.click(screen.getByRole('button', { name: 'go other' }));
    await waitFor(() => expect(input).toHaveValue('other'));
    expect(echo()).toHaveTextContent('other');
  });

  it('HC-UIPIN-003: each result is one whole-card link: stretched link, background hover, a focus ring, nothing that moves', async () => {
    // Would not notice: Card variant="interactive", whose hover lifts the card and so moves the T0 values inside it
    // (T0 allows no moving ancestor). The stretch itself is measured in e2e (a click on the snippet navigates).
    // RED today: the card is plain and only the link text is clickable.
    renderAt(<SearchPage />, '/search?q=migraine');
    await screen.findByText('Diagnoses migraine');
    const link = screen.getByRole('link', { name: 'Review extraction' });
    expect(link).toHaveAttribute('href', '/verify');
    expect(screen.getByRole('link', { name: 'Open inbox' })).toHaveAttribute('href', '/inbox');
    const linkTokens = link.className.split(/\s+/);
    expect(linkTokens).toContain('after:absolute');
    expect(linkTokens).toContain('after:inset-0');
    const card = link.closest<HTMLElement>('[data-search-result]')!;
    const tokens = card.className.split(/\s+/);
    expect(tokens).toContain('relative');
    expect(tokens.some((t) => /^hover:bg-/.test(t))).toBe(true);
    expect(tokens.some((t) => /focus.*ring-2/.test(t))).toBe(true);
    expect(tokens.filter((t) => /translate|scale/.test(t))).toEqual([]);
    for (let node: HTMLElement | null = card; node && node !== document.body; node = node.parentElement) {
      expect(node.className).not.toMatch(/translate|scale/);
    }
  });

  it('HC-UIPIN-003: title, snippet, date and the verification badge are marked T0 with named attributes', async () => {
    // Would not notice: result text the stillness probe cannot see (plan section 2.7: search result values).
    // The query echo is not T0 on purpose: it changes on submit, by design.
    // RED today: none of the four carries data-t0.
    renderAt(<SearchPage />, '/search?q=migraine');
    await screen.findByText('Diagnoses migraine');
    const card = document.querySelector('[data-search-result]')!;
    for (const [attr, text] of [
      ['data-search-title', 'Diagnoses migraine'],
      ['data-search-snippet', 'Snippet for Diagnoses migraine'],
      ['data-search-date', '2026-01-15'],
      ['data-search-verification', 'Needs verification'],
    ] as const) {
      const el = card.querySelector(`[${attr}]`);
      expect(el, attr).toHaveAttribute('data-t0');
      expect(el, attr).toHaveTextContent(text);
    }
    expect(echo()).not.toHaveAttribute('data-t0');
  });

  it('HC-UIPIN-003: the page root has no padding of its own, the spinner honours reduced motion, the selects use theme tokens', async () => {
    // Would not notice: the doubled p-8, a spinner that spins under reduced motion (G5), a white select in dark (G1).
    // RED today: p-8, bare animate-spin, bg-white border-black/8 on both selects.
    const held = gate();
    searchGate = held.wait;
    const { container } = renderAt(<SearchPage />, '/search?q=migraine');
    expect(pageRoot(container).className.split(/\s+/)).not.toContain('p-8');
    const spinner = screen.getByRole('status').querySelector('svg')!;
    const spin = spinner.getAttribute('class')!.split(/\s+/);
    expect(spin).toContain('motion-safe:animate-spin');
    expect(spin).not.toContain('animate-spin');
    for (const label of ['Category', 'Highlight']) {
      const tokens = screen.getByLabelText(label).className.split(/\s+/);
      expect(tokens, label).toContain('bg-surface-elevated');
      expect(tokens, label).toContain('border-border');
      expect(tokens, label).not.toContain('bg-white');
    }
    held.open();
    await screen.findByText('Diagnoses migraine');
  });

  it('HC-UIPIN-003: a failed search is a static alert with Try again, outside the S1 entrance, and it refetches', async () => {
    // Would not notice: error text inside EmptyState's ShowcaseReveal (error text is T0), or a Try again that does
    // nothing. After the retry the failure is gone and the results show.
    // RED today: the error is an EmptyState with no role="alert" and no Try again.
    const user = userEvent.setup();
    searchFails = true;
    renderAt(<SearchPage />, '/search?q=migraine');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not search records');
    expect(alert.closest('[style*="opacity"], [style*="transform"]')).toBeNull();
    expect(alert.closest('[data-search-error]')).not.toBeNull();
    searchFails = false;
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('Diagnoses migraine');
  });

  it('HC-UIPIN-003: Try again leaves focus in the page: the search box, not <body>', async () => {
    // Would not notice: a Try again button that unmounts with focus on it while the query refetches, so a keyboard user
    // is dropped on <body> and starts again from the top.
    // RED today: focus ends on <body>.
    const user = userEvent.setup();
    searchFails = true;
    renderAt(<SearchPage />, '/search?q=migraine');
    await screen.findByRole('alert');
    searchFails = false;
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('Diagnoses migraine');
    expect(screen.getByRole('searchbox', { name: 'Search health records' })).toHaveFocus();
  });

  it('HC-UIPIN-003: the empty search focuses the box, and "no matching records" clears the query and every filter', async () => {
    // Would not notice: an action that clears only the query and leaves a filter that makes the next search empty
    // again, or one that moves focus nowhere.
    // RED today: neither empty state has an action.
    const user = userEvent.setup();
    renderAt(<SearchPage />, '/search');
    const input = screen.getByRole('searchbox', { name: 'Search health records' });
    await user.click(screen.getByRole('button', { name: 'Start a search' }));
    expect(input).toHaveFocus();

    await user.type(input, 'nothing{Enter}');
    await screen.findByText('No matching records');
    await user.type(screen.getByLabelText('Provider'), 'Dr Who');
    await user.selectOptions(screen.getByLabelText('Category'), 'lab');
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith('/search/', expect.objectContaining({ provider: 'Dr Who' })));
    await user.click(await screen.findByRole('button', { name: 'Clear search and filters' }));

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/search$/));
    expect(input).toHaveValue('');
    expect(screen.getByLabelText('Provider')).toHaveValue('');
    expect(screen.getByLabelText('Category')).toHaveValue('');
    await screen.findByText('Search your records');
  });
});

// ---------------------------------------------------------------------------
// HC-UIPIN-002: window.prompt and window.confirm are never called.
// ---------------------------------------------------------------------------
describe('HC-UIPIN-002 pinboard rename and delete use dialogs', () => {
  beforeEach(() => {
    vi.spyOn(window, 'prompt').mockImplementation(() => {
      throw new Error('window.prompt must not be called');
    });
    vi.spyOn(window, 'confirm').mockImplementation(() => {
      throw new Error('window.confirm must not be called');
    });
  });

  async function renderLoaded() {
    const view = renderAt(<PinboardsPage />, '/pinboards');
    await screen.findByRole('button', { name: 'Rename' });
    return view;
  }

  it('HC-UIPIN-002: Rename opens a labelled, prefilled dialog; Save PATCHes the trimmed name; the second board has its own', async () => {
    // Would not notice: a dialog that PATCHes the old name, an untrimmed name, or a prefill left over from the first
    // board. The flow is driven to the PATCH twice, on two boards, with the prompt stub throwing.
    // RED today: window.prompt is called and the stub throws.
    const user = userEvent.setup();
    await renderLoaded();

    await user.click(screen.getByRole('button', { name: 'Rename' }));
    const dialog = await screen.findByRole('dialog', { name: 'Rename pinboard' });
    const input = within(dialog).getByLabelText('Pinboard name');
    expect(input).toHaveValue('Board A');
    const save = within(dialog).getByRole('button', { name: 'Save' });
    await user.clear(input);
    expect(save).toBeDisabled();
    await user.type(input, '  Renamed A  ');
    expect(save).toBeEnabled();
    expect(apiPatch).not.toHaveBeenCalled();
    await user.click(save);

    await waitFor(() => expect(apiPatch).toHaveBeenCalledTimes(1));
    expect(apiPatch).toHaveBeenCalledWith('/pinboards/board-a', { name: 'Renamed A' });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await screen.findByRole('heading', { name: 'Renamed A' });

    await user.click(screen.getByRole('button', { name: 'Board B' }));
    await user.click(screen.getByRole('button', { name: 'Rename' }));
    const again = await screen.findByRole('dialog', { name: 'Rename pinboard' });
    const second = within(again).getByLabelText('Pinboard name');
    expect(second).toHaveValue('Board B');
    await user.clear(second);
    await user.type(second, 'Renamed B');
    await user.click(within(again).getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(apiPatch).toHaveBeenCalledTimes(2));
    expect(apiPatch).toHaveBeenLastCalledWith('/pinboards/board-b', { name: 'Renamed B' });
    expect(window.prompt).not.toHaveBeenCalled();
  });

  it('HC-UIPIN-002: Cancel and Escape send nothing, and focus returns to the Rename button', async () => {
    // Would not notice: a Cancel that still PATCHes, or an Escape that drops focus on <body>.
    // RED today: window.prompt is called and the stub throws.
    const user = userEvent.setup();
    await renderLoaded();
    const rename = screen.getByRole('button', { name: 'Rename' });

    await user.click(rename);
    const dialog = await screen.findByRole('dialog', { name: 'Rename pinboard' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await waitFor(() => expect(rename).toHaveFocus());

    await user.click(rename);
    await screen.findByRole('dialog', { name: 'Rename pinboard' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await waitFor(() => expect(rename).toHaveFocus());
    expect(apiPatch).not.toHaveBeenCalled();
  });

  it('HC-UIPIN-002: a failed rename keeps the dialog open with an alert, and the retry completes', async () => {
    // Would not notice: a dialog that closes on a failed PATCH, so the new name is lost without a word.
    // RED today: window.prompt is called and the stub throws.
    const user = userEvent.setup();
    await renderLoaded();
    await user.click(screen.getByRole('button', { name: 'Rename' }));
    const dialog = await screen.findByRole('dialog', { name: 'Rename pinboard' });
    const input = within(dialog).getByLabelText('Pinboard name');
    await user.clear(input);
    await user.type(input, 'New name');

    apiPatch.mockRejectedValueOnce(new api.ApiError(500, 'Server Error', 'boom'));
    await user.click(within(dialog).getByRole('button', { name: 'Save' }));
    const alert = await within(dialog).findByRole('alert');
    expect(alert).toHaveTextContent(/could not rename/i);
    expect(screen.getByRole('dialog', { name: 'Rename pinboard' })).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Pinboard name')).toHaveValue('New name');

    await user.click(within(dialog).getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(apiPatch).toHaveBeenCalledTimes(2);
    expect(apiPatch).toHaveBeenLastCalledWith('/pinboards/board-a', { name: 'New name' });
    // A reopened dialog starts clean: the old error does not come back.
    await user.click(screen.getByRole('button', { name: 'Rename' }));
    const reopened = await screen.findByRole('dialog', { name: 'Rename pinboard' });
    expect(within(reopened).queryByRole('alert')).not.toBeInTheDocument();
  });

  it('HC-UIPIN-002: Delete asks through an alertdialog that names the board; Cancel sends nothing; Delete sends one DELETE', async () => {
    // Would not notice: a dialog that deletes on open (apiDelete is checked while it is open), a Cancel that still
    // deletes, or a dialog that names another board. Cancel is pressed first, then the flow runs again to Delete.
    // RED today: window.confirm is called and the stub throws.
    const user = userEvent.setup();
    await renderLoaded();
    const trigger = screen.getByRole('button', { name: 'Delete pinboard' });

    await user.click(trigger);
    const dialog = await screen.findByRole('alertdialog');
    expect(dialog).toHaveTextContent('Board A');
    expect(apiDelete).not.toHaveBeenCalled();
    const cancel = within(dialog).getByRole('button', { name: 'Cancel' });
    expect(cancel).toHaveAttribute('data-alert-cancel');
    await waitFor(() => expect(cancel).toHaveFocus());
    expect(dialog.className.split(/\s+/)).toContain('[overflow-wrap:anywhere]');
    await user.click(cancel);
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(apiDelete).not.toHaveBeenCalled();
    await waitFor(() => expect(trigger).toHaveFocus());

    await user.click(trigger);
    const again = await screen.findByRole('alertdialog');
    await user.click(within(again).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledTimes(1));
    expect(apiDelete).toHaveBeenCalledWith('/pinboards/board-a');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Board A' })).not.toBeInTheDocument());
    expect(screen.getByRole('heading', { name: 'Board B' })).toBeInTheDocument();
    expect(window.confirm).not.toHaveBeenCalled();
  });

  it('HC-UIPIN-002: the delete dialog names the board that was selected when it opened, on the second board too', async () => {
    // Would not notice: a target read from the selection at confirm time, or kept from the first open.
    // RED today: window.confirm is called and the stub throws.
    const user = userEvent.setup();
    await renderLoaded();
    await user.click(screen.getByRole('button', { name: 'Board B' }));
    await user.click(screen.getByRole('button', { name: 'Delete pinboard' }));
    const dialog = await screen.findByRole('alertdialog');
    expect(dialog).toHaveTextContent('Board B');
    expect(dialog).not.toHaveTextContent('Board A');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledWith('/pinboards/board-b'));
    expect(apiDelete).toHaveBeenCalledTimes(1);
  });

  it('HC-UIPIN-002: a failed delete keeps the alertdialog open with an alert, and Escape closes it without a DELETE', async () => {
    // Would not notice: a dialog that closes on a failed DELETE and shows the board still there with no reason.
    // RED today: window.confirm is called and the stub throws.
    const user = userEvent.setup();
    await renderLoaded();
    const trigger = screen.getByRole('button', { name: 'Delete pinboard' });
    await user.click(trigger);
    const dialog = await screen.findByRole('alertdialog');
    apiDelete.mockRejectedValueOnce(new api.ApiError(500, 'Server Error', 'boom'));
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/could not delete/i);
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(apiDelete).toHaveBeenCalledTimes(1);

    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(apiDelete).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Board A' })).toBeInTheDocument();
  });

  it('HC-UIPIN-002: a confirmed delete does not ask for the deleted board\'s items (the real route answers 404)', async () => {
    // Would not notice: the mutation invalidates every pinboard query by prefix, so the deleted board's items are asked
    // for again while it is still selected; the real route answers 404 (a console error, and with the app's one retry
    // the dialog stays open for about 2 s). The fake server counts those requests. A mock that answered 200 for a
    // deleted board (as the e2e one did) could not see it.
    // RED today: the fake counts one 404.
    const user = userEvent.setup();
    boardItems = {
      'board-a': [{ id: 'it-1', pinboard_id: 'board-a', item_type: 'document', item_id: 'doc-9', created_at: '' }],
    };
    await renderLoaded();
    await waitFor(() => expect(document.querySelector('[data-pinboard-item-id]')).not.toBeNull());
    await user.click(screen.getByRole('button', { name: 'Delete pinboard' }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await screen.findByRole('heading', { name: 'Board B' });
    await settle();
    expect(itemsNotFound).toBe(0);
  });

  it('HC-UIPIN-002: while a DELETE is in flight Escape and Cancel do nothing, the panel keeps its items, and one DELETE is sent', async () => {
    // Would not notice: a dialog that closes on Escape or Cancel while the request runs, after which the board is
    // deleted anyway with no undo, and a later failure shows nowhere. Overlaps are the point (recurring #17): the
    // request is held, Escape and a click on Cancel are tried, then the request is released.
    // RED today: Escape closes the dialog while the DELETE is still pending.
    const user = userEvent.setup();
    boardItems = {
      'board-a': [{ id: 'it-1', pinboard_id: 'board-a', item_type: 'document', item_id: 'doc-9', created_at: '' }],
    };
    await renderLoaded();
    await waitFor(() => expect(document.querySelector('[data-pinboard-item-id]')).not.toBeNull());
    const held = gate();
    deleteGate = held.wait;
    await user.click(screen.getByRole('button', { name: 'Delete pinboard' }));
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledTimes(1));

    await user.keyboard('{Escape}');
    await settle();
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled();
    // Behind the dialog the panel did not change while the request ran.
    expect(document.querySelector('[data-pinboard-item-id]')).not.toBeNull();

    held.open();
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(apiDelete).toHaveBeenCalledTimes(1);
    expect(apiDelete).toHaveBeenCalledWith('/pinboards/board-a');
  });

  it('HC-UIPIN-002: while a PATCH is in flight Escape and Cancel do nothing, and the dialog closes when it completes', async () => {
    // Would not notice: the same overlap as the delete, for Rename: the dialog gone while the rename is still on its
    // way, and a failure after that has no dialog to show it in.
    // RED today: Escape closes the dialog while the PATCH is pending.
    const user = userEvent.setup();
    await renderLoaded();
    const held = gate();
    patchGate = held.wait;
    await user.click(screen.getByRole('button', { name: 'Rename' }));
    const dialog = await screen.findByRole('dialog', { name: 'Rename pinboard' });
    const input = within(dialog).getByLabelText('Pinboard name');
    await user.clear(input);
    await user.type(input, 'Slow name');
    await user.click(within(dialog).getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(apiPatch).toHaveBeenCalledTimes(1));

    await user.keyboard('{Escape}');
    await settle();
    expect(screen.getByRole('dialog', { name: 'Rename pinboard' })).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled();

    held.open();
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await screen.findByRole('heading', { name: 'Slow name' });
    expect(apiPatch).toHaveBeenCalledTimes(1);
  });

  it('HC-UIPIN-002: deleting the board that was selected focuses the next board\'s Delete button, and deleting the last one focuses the new-pinboard box', async () => {
    // Would not notice: focus dropped on <body> after the board panel it sat in is gone (the #464 Remove class).
    // The second case deletes the only board left, so the panel and its buttons leave with it.
    // RED today: window.confirm is called and the stub throws.
    const user = userEvent.setup();
    await renderLoaded();
    await user.click(screen.getByRole('button', { name: 'Delete pinboard' }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await screen.findByRole('heading', { name: 'Board B' });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Delete pinboard' })).toHaveFocus());

    await user.click(screen.getByRole('button', { name: 'Delete pinboard' }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete' }));
    await screen.findByText('No pinboards yet');
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'New pinboard name' })).toHaveFocus());
    expect(apiDelete.mock.calls.map(([path]) => path)).toEqual(['/pinboards/board-a', '/pinboards/board-b']);
  });

  it('HC-UIPIN-002: pinned items carry data-t0 on label and id, and a long board name and a UUID item wrap', async () => {
    // Would not notice: a long board name or an unbroken id that pushes the page wider than 320 px (G6; the class
    // contract here, the measured width in e2e), or pinned text the stillness probe cannot see.
    // RED today: no data-t0, no wrap class.
    const uuid = '6f1c2a7e-0b3d-4c5e-9a8f-1d2e3f4a5b6c-6f1c2a7e0b3d4c5e9a8f1d2e3f4a5b6c';
    pinboards = [makeBoard('board-a', 'L'.repeat(90))];
    boardItems = {
      'board-a': [{ id: 'it-1', pinboard_id: 'board-a', item_type: 'observation', item_id: uuid, created_at: '' }],
    };
    await renderLoaded();
    const label = await waitFor(() => {
      const el = document.querySelector('[data-pinboard-item-label]');
      expect(el).not.toBeNull();
      return el!;
    });
    const id = document.querySelector('[data-pinboard-item-id]')!;
    expect(label).toHaveAttribute('data-t0');
    expect(label).toHaveTextContent('Observation');
    expect(id).toHaveAttribute('data-t0');
    expect(id).toHaveTextContent(uuid);
    for (const el of [label.parentElement!, id.parentElement!]) {
      expect(el.className.split(/\s+/)).toContain('min-w-0');
      expect(el.className.split(/\s+/)).toContain('[overflow-wrap:anywhere]');
    }
    const title = screen.getByRole('heading', { name: 'L'.repeat(90) });
    expect(title.className.split(/\s+/)).toContain('[overflow-wrap:anywhere]');
    expect(title.className.split(/\s+/)).toContain('min-w-0');
    expect(screen.getByRole('button', { name: 'L'.repeat(90) }).className.split(/\s+/)).toContain('[overflow-wrap:anywhere]');
  });

  it('HC-UIPIN-002: the list divides with the theme border, and the loading spinner is a status that honours reduced motion', async () => {
    // Would not notice: divide-black/5 (invisible in dark), or a bare animate-spin with no text (G5, the #456
    // class, and a spinner a screen reader never hears).
    // RED today: divide-black/5; the spinner has no role and a bare animate-spin.
    const held = gate();
    pinboardsGate = held.wait;
    boardItems = {
      'board-a': [{ id: 'it-1', pinboard_id: 'board-a', item_type: 'document', item_id: 'doc-9', created_at: '' }],
    };
    renderAt(<PinboardsPage />, '/pinboards');
    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent('Loading pinboards');
    const spin = status.querySelector('svg')!.getAttribute('class')!.split(/\s+/);
    expect(spin).toContain('motion-safe:animate-spin');
    expect(spin).not.toContain('animate-spin');
    held.open();
    await screen.findByRole('button', { name: 'Rename' });
    await waitFor(() => expect(document.querySelector('ul.divide-y')).not.toBeNull());
    const tokens = document.querySelector('ul.divide-y')!.className.split(/\s+/);
    expect(tokens).toContain('divide-border');
    expect(tokens).not.toContain('divide-black/5');
  });

  it('HC-UIPIN-002: the empty page offers a button that focuses the new-pinboard box', async () => {
    // Would not notice: an empty state with no way forward.
    // RED today: no action.
    const user = userEvent.setup();
    pinboards = [];
    renderAt(<PinboardsPage />, '/pinboards');
    await user.click(await screen.findByRole('button', { name: 'Name a pinboard' }));
    expect(screen.getByRole('textbox', { name: 'New pinboard name' })).toHaveFocus();
  });
});

// ---------------------------------------------------------------------------
// M3: the add-to-pinboard menu enters with opacity and scale from the Radix origin.
// ---------------------------------------------------------------------------
describe('M3 the add-to-pinboard menu enter', () => {
  it('M3: the open menu fades and scales from the Radix transform origin in 180 ms, with no transition-all', async () => {
    // Would not notice: a class that Tailwind does not generate (jsdom loads no CSS, so e2e measures the computed
    // style and the first frame); a transition-all, which the plan bans; a menu that scales under reduced motion.
    // RED today: the menu has no transition at all.
    const user = userEvent.setup();
    renderAt(<AddToPinboardButton items={[{ item_type: 'document', item_id: 'doc-1' }]} />);
    await user.click(screen.getByRole('button', { name: 'Add to pinboard' }));
    const menu = await screen.findByRole('menu');
    const tokens = menu.className.split(/\s+/);
    expect(tokens).toContain('transition-[opacity,scale]');
    expect(tokens).toContain('duration-[var(--dur-sm)]');
    expect(tokens).toContain('origin-[var(--radix-dropdown-menu-content-transform-origin)]');
    expect(tokens).toContain('starting:opacity-0');
    expect(tokens).toContain('starting:scale-96');
    expect(tokens).toContain('motion-reduce:starting:scale-100');
    expect(tokens.filter((t) => /(^|:)transition-all$/.test(t))).toEqual([]);
    // The existing surface stays: theme tokens, and the board names are listed.
    expect(tokens).toContain('bg-surface-elevated');
    expect(tokens).toContain('border-border');
    expect(within(menu).getByRole('menuitem', { name: 'Board A' })).toBeInTheDocument();
  });
});
