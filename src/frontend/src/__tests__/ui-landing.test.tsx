/**
 * UI-OVERVIEW (HC-UILAND-001 .. 003, vitest half): the Overview landing at /overview.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md, "UI-OVERVIEW", §3.1 and §4.2. The page is built from the
 * existing queries only, so the HTTP layer (`@/services/api`) is the one thing replaced: every count and value on
 * screen comes through the real hooks. The Playwright half (the stillness probe through the S1 entrance, the counts
 * against the API, Gate G) is e2e/ui-landing.spec.ts.
 *
 * What these tests would not notice:
 * - an animation that runs in a real browser: jsdom loads no CSS and plays no animation, so "no animation on the
 *   next step" is read from class names and inline style here, and from `getAnimations()` in the e2e half;
 * - a count or value that moves while the S1 entrance runs (the e2e stillness probe measures that);
 * - the real API sending a different shape than the fixtures below (typed from services/types.ts, not the backend).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ComponentType } from 'react';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '@/App';
import { MotionProvider } from '@/motion/MotionProvider';
import { useAuthStore } from '@/stores/authStore';
import type { Document, Medication, MedicationSchedule, Observation } from '@/services/types';

// What each endpoint answers. A test sets it; anything not listed answers [] (the shell's own queries).
const server = vi.hoisted(() => ({
  documents: [] as unknown[],
  observations: [] as unknown[],
  medications: [] as unknown[],
  calls: [] as Array<{ path: string; params?: Record<string, string> }>,
}));

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(async (path: string, params?: Record<string, string>) => {
    server.calls.push({ path, params });
    if (path === '/documents/') return server.documents;
    if (path === '/observations/') {
      const rows = server.observations as Array<{ user_verified: boolean }>;
      return params?.needs_verification === 'true' ? rows.filter((row) => !row.user_verified) : rows;
    }
    if (path === '/medications/') return server.medications;
    return [];
  }),
  apiPost: vi.fn().mockResolvedValue({}),
  apiPut: vi.fn().mockResolvedValue({}),
  apiPatch: vi.fn().mockResolvedValue({}),
  apiDelete: vi.fn().mockResolvedValue(undefined),
  apiGetRaw: vi.fn().mockResolvedValue(new Response('')),
  apiUpload: vi.fn().mockResolvedValue({}),
  getApiBaseUrl: () => 'http://localhost:8000/api/v1',
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

const PROFILE = 'profile-123';

function makeDoc(over: Partial<Document> = {}): Document {
  return {
    id: 'doc-a',
    profile_id: PROFILE,
    doc_type: 'lab_pdf',
    source: 'a.pdf',
    status: 'needs_review',
    page_count: 1,
    collection_date: '2026-08-02T00:00:00',
    imported_at: '2026-08-03T07:41:00',
    parsed_at: '2026-08-03T07:41:03',
    verified_at: null,
    extraction_confidence: 0.9,
    ...over,
  };
}

function makeObservation(over: Partial<Observation> = {}): Observation {
  return {
    id: 'obs-1',
    profile_id: PROFILE,
    doc_id: 'doc-a',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 101,
    value_text: null,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 99,
    ref_range_text: '70-99',
    flag: null,
    is_abnormal: null,
    collected_at: '2026-08-02T00:00:00',
    user_verified: false,
    extraction_confidence: 0.9,
    source_page: 1,
    source_bbox_json: null,
    ...over,
  };
}

function makeSchedule(over: Partial<MedicationSchedule>): MedicationSchedule {
  return {
    id: 'sched-1',
    medication_id: 'med-1',
    schedule_label: 'Morning',
    target_time: '08:00',
    adaptive_window_start: null,
    adaptive_window_end: null,
    reminder_offset_minutes: 0,
    days_of_week: null,
    is_active: true,
    created_at: '2026-01-05T09:00:00',
    ...over,
  };
}

function makeMedication(schedules: MedicationSchedule[], over: Partial<Medication> = {}): Medication {
  return {
    id: 'med-1',
    profile_id: PROFILE,
    name: 'Metformin',
    generic_name: null,
    dosage_amount: 500,
    dosage_unit: 'mg',
    dosage_form: 'tablet',
    frequency: 'twice_daily',
    instructions: null,
    is_active: true,
    reminder_enabled: false,
    started_at: '2026-01-05',
    ended_at: null,
    created_at: '2026-01-05T09:00:00',
    updated_at: '2026-01-05T09:00:00',
    schedules,
    ...over,
  };
}

function signIn() {
  useAuthStore.getState().setAuth({
    token: 'test-token',
    profileId: PROFILE,
    profileName: 'Test Profile',
    expiresIn: 3600,
  });
}

beforeEach(() => {
  server.documents = [];
  server.observations = [];
  server.medications = [];
  server.calls = [];
  window.sessionStorage.clear();
  signIn();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  window.history.replaceState({}, '', '/');
});

/** App's own router reads window.location, so the route is the real one. */
async function renderAppAt(path: string) {
  window.history.pushState({}, '', path);
  render(
    <MotionProvider>
      <App />
    </MotionProvider>
  );
}

// A glob, not a static import: while the page does not exist the glob is empty and the data-state tests fail one by
// one with a clear message, instead of the whole file failing to load.
const pageModules = import.meta.glob<{ OverviewPage: ComponentType }>('../pages/OverviewPage.tsx');

/** The page on its own, with a fresh query cache, for the data states. */
async function renderOverview() {
  const load = pageModules['../pages/OverviewPage.tsx'];
  if (!load) throw new Error('src/pages/OverviewPage.tsx does not exist');
  const { OverviewPage } = await load();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/overview']}>
        <OverviewPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return Object.assign(view, { client });
}

describe('HC-UILAND-001: with no documents the checklist has three working links', () => {
  it('HC-UILAND-001: /overview shows one h1 and the Import, Review values, See results links, each to its page', async () => {
    await renderAppAt('/overview');

    const heading = await screen.findByRole('heading', { level: 1, name: 'Overview' });
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(window.location.pathname).toBe('/overview');

    const main = heading.closest('main');
    if (!main) throw new Error('the page renders inside <main>');
    const steps = await within(main).findByRole('list', { name: /first steps/i });
    const links = within(steps).getAllByRole('link');
    expect(links.map((link) => link.getAttribute('href'))).toEqual(['/inbox', '/verify', '/results']);
    expect(within(steps).getByRole('link', { name: /import/i })).toHaveAttribute('href', '/inbox');
    expect(within(steps).getByRole('link', { name: /review values/i })).toHaveAttribute('href', '/verify');
    expect(within(steps).getByRole('link', { name: /see results/i })).toHaveAttribute('href', '/results');
  });

  it('HC-UILAND-001: only the first step reads "Next step", in words, with a static accent border and no animation', async () => {
    await renderAppAt('/overview');
    const steps = await screen.findByRole('list', { name: /first steps/i });

    const marks = within(steps).getAllByText('Next step');
    expect(marks).toHaveLength(1);
    const card = marks[0].closest<HTMLElement>('[role="listitem"]');
    if (!card) throw new Error('the next-step mark sits in a checklist item');
    expect(within(card).getByRole('link', { name: /import/i })).toBeInTheDocument();
    expect(card.className).toMatch(/\bborder-accent\b/);

    // jsdom loads no CSS, so "no animation running" is read from what could start one: an animate-* or beam class,
    // an orb, a pulse, or an inline animation, on the card or anything inside it (plan §4.2: S2 marks a process).
    const animated = [card, ...Array.from(card.querySelectorAll<HTMLElement>('*'))].filter(
      (el) =>
        /(^|\s)(animate-|beam-border|orb|pulse|spin|ping|bounce)/.test(el.getAttribute('class') ?? '') ||
        el.style.animation !== '' ||
        el.style.animationName !== ''
    );
    expect(animated).toEqual([]);
    expect(card.querySelector('canvas')).toBeNull();
  });

  it('HC-UILAND-001: the other two steps are not marked, and no count or value is shown before the first import', async () => {
    await renderAppAt('/overview');
    const steps = await screen.findByRole('list', { name: /first steps/i });

    expect(within(steps).getAllByRole('listitem')).toHaveLength(3);
    expect(screen.queryByText(/waiting for review/i)).toBeNull();
    expect(steps.querySelector('[data-t0]')).toBeNull();
  });
});

describe('HC-UILAND-002 (vitest half): after the first import the page shows the API\'s counts and values', () => {
  it('HC-UILAND-002: "N values waiting for review" uses the needs_verification list, with N in a data-t0 node, linking to /verify', async () => {
    server.documents = [makeDoc()];
    server.observations = [
      makeObservation({ id: 'o1' }),
      makeObservation({ id: 'o2', analyte_canonical: 'ldl', analyte_raw: 'LDL', value: 142, unit: 'mg/dL' }),
      makeObservation({ id: 'o3', analyte_canonical: 'hba1c', analyte_raw: 'HbA1c', value: 6.1, unit: '%' }),
      makeObservation({ id: 'o4', user_verified: true }),
      makeObservation({ id: 'o5', user_verified: true }),
    ];
    await renderOverview();

    const count = await screen.findByTestId('overview-waiting-count');
    expect(count).toHaveTextContent(/^3$/);
    expect(count).toHaveAttribute('data-t0');
    expect(count.parentElement).toHaveTextContent('3 values waiting for review');
    // Plan :287 names the whole phrase as T0 text, so the noun carries data-t0 too.
    expect(screen.getByText('values waiting for review')).toHaveAttribute('data-t0');
    const link = screen.getByRole('link', { name: /review values/i });
    expect(link).toHaveAttribute('href', '/verify');
    // The count comes from the same filtered list the Review values page asks for.
    expect(server.calls.some((c) => c.path === '/observations/' && c.params?.needs_verification === 'true')).toBe(true);
    // No checklist after the first import.
    expect(screen.queryByRole('list', { name: /first steps/i })).toBeNull();
    expect(screen.queryByText('Next step')).toBeNull();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });

  it('HC-UILAND-002: one value reads "1 value waiting for review"', async () => {
    server.documents = [makeDoc()];
    server.observations = [makeObservation({ id: 'o1' })];
    await renderOverview();

    const count = await screen.findByTestId('overview-waiting-count');
    expect(count).toHaveTextContent(/^1$/);
    expect(count.parentElement).toHaveTextContent('1 value waiting for review');
  });

  it('HC-UILAND-002: the latest value of each analyte is static text with its range words, in data-t0 nodes, linking to /results', async () => {
    server.documents = [makeDoc()];
    server.observations = [
      makeObservation({ id: 'g1', value: 92, collected_at: '2026-01-10T00:00:00', user_verified: true }),
      makeObservation({ id: 'g2', value: 118, collected_at: '2026-06-02T00:00:00', user_verified: true }),
      makeObservation({
        id: 'l1',
        analyte_canonical: 'ldl',
        analyte_raw: 'LDL',
        value: 88,
        ref_low: 40,
        ref_high: 100,
        collected_at: '2026-06-02T00:00:00',
        user_verified: true,
      }),
    ];
    await renderOverview();

    const glucose = await screen.findByTestId('overview-latest-glucose');
    // The 118, not the older 92.
    expect(within(glucose).getByText('118 mg/dL')).toHaveAttribute('data-t0');
    expect(within(glucose).queryByText(/92/)).toBeNull();
    expect(within(glucose).getByText("Above the report's range")).toBeInTheDocument();
    const ldl = screen.getByTestId('overview-latest-ldl');
    expect(within(ldl).getByText('88 mg/dL')).toHaveAttribute('data-t0');
    expect(within(ldl).getByText('In range')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /see results/i })).toHaveAttribute('href', '/results');
  });

  it('HC-UILAND-002: the next dose is the next scheduled time today, then the first one tomorrow, linking to /medications', async () => {
    server.documents = [makeDoc()];
    server.medications = [
      makeMedication([
        makeSchedule({ id: 's-am', target_time: '08:00', schedule_label: 'Morning' }),
        makeSchedule({ id: 's-pm', target_time: '20:00', schedule_label: 'Evening' }),
        makeSchedule({ id: 's-off', target_time: '13:00', schedule_label: 'Off', is_active: false }),
      ]),
    ];

    vi.useFakeTimers({ toFake: ['Date'], now: new Date(2026, 10, 5, 12, 0, 0) });
    const first = await renderOverview();
    const noon = await screen.findByTestId('overview-next-dose');
    expect(noon).toHaveTextContent('Metformin');
    expect(within(noon).getByText('20:00')).toHaveAttribute('data-t0');
    expect(noon).toHaveTextContent(/today/i);
    expect(screen.getByRole('link', { name: /medications/i })).toHaveAttribute('href', '/medications');
    first.unmount();

    vi.setSystemTime(new Date(2026, 10, 5, 21, 0, 0));
    await renderOverview();
    const night = await screen.findByTestId('overview-next-dose');
    expect(within(night).getByText('08:00')).toHaveAttribute('data-t0');
    expect(night).toHaveTextContent(/tomorrow/i);
  });

  it('HC-UILAND-002: a schedule limited to other weekdays is skipped (days_of_week is 0 = Monday, so Thursday is 3)', async () => {
    server.documents = [makeDoc()];
    // 2026-11-05 is a Thursday: 3 with Monday = 0 (the API), 4 with Sunday = 0. At 07:00 the 09:00 dose is on today's
    // list only under the API's numbering; the 20:00 dose is every day. [4] is Friday and must be skipped today.
    server.medications = [
      makeMedication([
        makeSchedule({ id: 's-thu', target_time: '09:00', days_of_week: [3] }),
        makeSchedule({ id: 's-fri', target_time: '08:00', days_of_week: [4] }),
        makeSchedule({ id: 's-any', target_time: '20:00', days_of_week: null }),
      ]),
    ];
    vi.useFakeTimers({ toFake: ['Date'], now: new Date(2026, 10, 5, 7, 0, 0) });
    await renderOverview();

    const dose = await screen.findByTestId('overview-next-dose');
    expect(within(dose).getByText('09:00')).toBeInTheDocument();
    expect(dose).toHaveTextContent(/today/i);
    expect(within(dose).queryByText('08:00')).toBeNull();
    expect(within(dose).queryByText('20:00')).toBeNull();
  });
});

describe('HC-UILAND-002 (range words): a chip is shown only where the report\'s flag and the numbers agree', () => {
  // The backend rule is observation_range_status (api/observations.py, VALUE-RANGE-COMPARE): an unknown flag is not
  // decided, and a flag that disagrees with the numbers gets no wording.
  async function chipsFor(over: Partial<Observation>) {
    server.documents = [makeDoc()];
    server.observations = [makeObservation({ user_verified: true, ...over })];
    await renderOverview();
    const row = await screen.findByTestId('overview-latest-glucose');
    return row;
  }

  it('HC-UILAND-002: a flag the page does not know (A) on a value inside the range shows no range chip', async () => {
    const row = await chipsFor({ value: 90, flag: 'A' });
    expect(within(row).queryByText('In range')).toBeNull();
    expect(within(row).queryByText(/the report's range/)).toBeNull();
    expect(within(row).getByText('Checked by you')).toBeInTheDocument();
  });

  it('HC-UILAND-002: ABNORMAL, CRIT and * on a value inside the range show no "In range" chip', async () => {
    for (const flag of ['ABNORMAL', 'CRIT', '*']) {
      cleanup();
      const row = await chipsFor({ value: 90, flag });
      expect(within(row).queryByText('In range')).toBeNull();
    }
  });

  it('HC-UILAND-002: no flag, or a normal word (N, NORMAL), on a value inside the range reads "In range"', async () => {
    for (const flag of [null, 'N', 'NORMAL']) {
      cleanup();
      const row = await chipsFor({ value: 90, flag });
      expect(within(row).getByText('In range')).toBeInTheDocument();
    }
  });

  it('HC-UILAND-002: a normal word on a value outside the range, or H on a value inside it, shows no range chip', async () => {
    for (const over of [
      { value: 150, flag: 'N' },
      { value: 90, flag: 'H' },
      { value: 90, flag: 'L' },
      { value: 50, flag: 'H' },
    ]) {
      cleanup();
      const row = await chipsFor(over);
      expect(within(row).queryByText('In range')).toBeNull();
      expect(within(row).queryByText(/the report's range/)).toBeNull();
    }
  });

  it('HC-UILAND-002: H or L agreeing with the numbers, or with no range to compare, reads above / below the range', async () => {
    cleanup();
    expect(within(await chipsFor({ value: 150, flag: 'H' })).getByText("Above the report's range")).toBeInTheDocument();
    cleanup();
    expect(within(await chipsFor({ value: 50, flag: 'L' })).getByText("Below the report's range")).toBeInTheDocument();
    cleanup();
    expect(
      within(await chipsFor({ value: 150, flag: 'H', ref_low: null, ref_high: null })).getByText(
        "Above the report's range"
      )
    ).toBeInTheDocument();
  });
});

describe('HC-UILAND-002 (first run -> import): the first-run Overview leaves no empty observation lists in the cache', () => {
  it('HC-UILAND-002: with no documents no observation list is requested or cached; after the import the count is the API\'s and nothing else is ever shown', async () => {
    const { client } = await renderOverview();
    await screen.findByRole('list', { name: /first steps/i });

    // The Review values and Results pages ask for these same keys. An [] cached here would stay fresh for 5 minutes.
    expect(server.calls.filter((c) => c.path === '/observations/')).toEqual([]);
    // (A disabled query may sit in the cache with no data; what must not be there is an answer.)
    expect(
      client
        .getQueryCache()
        .findAll({ queryKey: ['observations'] })
        .filter((query) => query.state.data !== undefined)
    ).toEqual([]);

    // The count node is watched from now on: every text it ever holds is recorded.
    const seen: string[] = [];
    const record = () => {
      const node = document.querySelector('[data-testid="overview-waiting-count"]');
      if (node && node.textContent !== null && seen[seen.length - 1] !== node.textContent) seen.push(node.textContent);
    };
    const watcher = new MutationObserver(record);
    watcher.observe(document.body, { childList: true, subtree: true, characterData: true });

    // The import: the API now has a document and four rows, three waiting. useImportDocument invalidates 'documents'.
    server.documents = [makeDoc()];
    server.observations = [
      makeObservation({ id: 'o1' }),
      makeObservation({ id: 'o2', analyte_canonical: 'ldl', analyte_raw: 'LDL', value: 142 }),
      makeObservation({ id: 'o3', analyte_canonical: 'hba1c', analyte_raw: 'HbA1c', value: 6.1 }),
      makeObservation({ id: 'o4', analyte_canonical: 'tsh', analyte_raw: 'TSH', value: 2, user_verified: true }),
    ];
    await client.invalidateQueries({ queryKey: ['documents'] });

    const count = await screen.findByTestId('overview-waiting-count');
    record();
    watcher.disconnect();
    expect(count).toHaveTextContent(/^3$/);
    expect(seen).toEqual(['3']);
    expect(screen.queryByText('No values have been read yet.')).toBeNull();
    expect(screen.getByTestId('overview-latest-glucose')).toBeInTheDocument();
  });
});

describe('HC-UILAND-003: the index and an unknown path both land on /overview', () => {
  it('HC-UILAND-003: an unknown path redirects to /overview', async () => {
    await renderAppAt('/no-such-page');

    await waitFor(() => expect(window.location.pathname).toBe('/overview'));
    expect(await screen.findByRole('heading', { level: 1, name: 'Overview' })).toBeInTheDocument();
  });

  it('HC-UILAND-003: the index (/) redirects to /overview', async () => {
    await renderAppAt('/');

    await waitFor(() => expect(window.location.pathname).toBe('/overview'));
    expect(await screen.findByRole('heading', { level: 1, name: 'Overview' })).toBeInTheDocument();
  });
});
