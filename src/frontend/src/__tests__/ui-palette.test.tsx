/**
 * UI-PALETTE (HC-UIPAL-001, 002, 004, plus the vitest half of 005): the lazy command palette.
 *
 * HC-UIPAL-001/004 here are the behaviour checks. jsdom loads no stylesheet, so computed transition-duration and
 * animation-name are blank and this file cannot see them: it asserts that the dialog carries no motion props, no
 * transition or animation class and no inline style. The computed-style half is e2e/ui-palette.spec.ts.
 * HC-UIPAL-002 is the DF-5 check. It would miss a stale id that only appears in a real layout, so the e2e half
 * repeats it in Chromium.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CommandPalette from '@/components/layout/CommandPalette';
import { closePalette, PaletteMount } from '@/components/layout/paletteEvents';
import { TopBar } from '@/components/layout/TopBar';
import { apiGet } from '@/services/api';
import { useObservations } from '@/services/observations';
import { useSearch } from '@/services/search';
import type { Observation } from '@/services/types';
import { useAuthStore } from '@/stores/authStore';

// The two hooks are mocked by default; the tests that need the real hook (its query, its refetch on focus) call
// vi.importActual and put the real one back, with only the network (apiGet) mocked.
vi.mock('@/services/observations', () => ({ useObservations: vi.fn() }));
vi.mock('@/services/search', () => ({ useSearch: vi.fn() }));
vi.mock('@/services/api', async (importActual) => ({
  ...(await importActual<typeof import('@/services/api')>()),
  apiGet: vi.fn(),
}));

function observation(overrides: Partial<Observation>): Observation {
  return {
    id: 'obs',
    profile_id: 'p1',
    doc_id: 'doc-1',
    analyte_canonical: 'glucose',
    analyte_raw: 'Glucose',
    value: 100,
    value_text: null,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 99,
    ref_range_text: null,
    flag: null,
    is_abnormal: null,
    collected_at: '2026-01-10',
    user_verified: false,
    extraction_confidence: null,
    source_page: null,
    source_bbox_json: null,
    ...overrides,
  };
}

const OBSERVATIONS: Observation[] = [
  observation({ id: 'g1', value: 92, collected_at: '2026-01-10' }),
  observation({ id: 'g2', value: 118, collected_at: '2026-04-10', user_verified: true }),
  observation({ id: 'g3', value: 101, collected_at: '2026-02-10' }),
  observation({
    id: 'l1',
    analyte_canonical: 'ldl_cholesterol',
    analyte_raw: 'LDL Cholesterol',
    value: 142,
    collected_at: '2026-04-10',
  }),
  observation({
    id: 'h1',
    analyte_canonical: 'hdl_cholesterol',
    analyte_raw: 'HDL Cholesterol',
    value: 51,
    collected_at: '2026-04-10',
  }),
];

function LocationProbe() {
  const location = useLocation();
  return (
    <div data-testid="location">
      {location.pathname}
      {location.search}
    </div>
  );
}

function renderShell(initialPath = '/inbox', gated = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="*"
            element={
              <>
                <TopBar />
                <input aria-label="Some field" />
                {gated ? (
                  <PaletteMount>
                    <CommandPalette />
                  </PaletteMount>
                ) : (
                  <CommandPalette />
                )}
                <LocationProbe />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const trigger = () => screen.getByRole('button', { name: /search/i });
const dialog = () => screen.getByRole('dialog', { name: 'Command palette' });

beforeEach(() => {
  vi.mocked(apiGet).mockRejectedValue(new Error('unmocked API call'));
  vi.mocked(useObservations).mockReturnValue({ data: OBSERVATIONS } as unknown as ReturnType<typeof useObservations>);
  vi.mocked(useSearch).mockReturnValue({ data: { count: 0, results: [] }, isLoading: false, isError: false } as unknown as ReturnType<
    typeof useSearch
  >);
});

afterEach(() => {
  act(() => closePalette());
  cleanup();
  vi.clearAllMocks();
});

/** Every aria-activedescendant on the page names an element that exists, and that element is the selected option. */
function expectActiveDescendantsResolve(label: string) {
  const holders = Array.from(document.querySelectorAll('[aria-activedescendant]'));
  expect(holders.length, `${label}: something carries aria-activedescendant`).toBeGreaterThan(0);
  for (const holder of holders) {
    const id = holder.getAttribute('aria-activedescendant') ?? '';
    const target = id ? document.getElementById(id) : null;
    expect(target, `${label}: #${id} on <${holder.tagName.toLowerCase()} role=${holder.getAttribute('role')}>`).not.toBeNull();
    expect(target?.getAttribute('role'), `${label}: #${id} role`).toBe('option');
    expect(target?.getAttribute('aria-selected'), `${label}: #${id} is the selected option`).toBe('true');
  }
}

describe('HC-UIPAL-001: Ctrl/Cmd K and / open the palette, and it does not animate', () => {
  it('Ctrl+K opens it and Ctrl+K again closes it', async () => {
    renderShell();
    expect(screen.queryByRole('dialog')).toBeNull();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    expect(await screen.findByRole('dialog', { name: 'Command palette' })).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });

  it('Cmd+K opens it', async () => {
    renderShell();
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    expect(await screen.findByRole('dialog', { name: 'Command palette' })).toBeInTheDocument();
  });

  it('/ opens it from the page body', async () => {
    renderShell();
    fireEvent.keyDown(document.body, { key: '/' });
    expect(await screen.findByRole('dialog', { name: 'Command palette' })).toBeInTheDocument();
  });

  it('/ typed in an input, a textarea or a contenteditable does not open it', () => {
    renderShell();
    fireEvent.keyDown(screen.getByRole('textbox', { name: 'Some field' }), { key: '/' });
    const area = document.body.appendChild(document.createElement('textarea'));
    fireEvent.keyDown(area, { key: '/' });
    const editable = document.body.appendChild(document.createElement('div'));
    editable.setAttribute('contenteditable', 'true');
    // jsdom does not implement isContentEditable, so the handler must also read the attribute.
    fireEvent.keyDown(editable, { key: '/' });
    expect(screen.queryByRole('dialog')).toBeNull();
    area.remove();
    editable.remove();
  });

  it('the header trigger opens it', async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(trigger());
    expect(await screen.findByRole('dialog', { name: 'Command palette' })).toBeInTheDocument();
  });

  it('the dialog has no transition, animation or inline motion style', async () => {
    renderShell();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const root = await screen.findByRole('dialog', { name: 'Command palette' });
    for (const el of [root, ...Array.from(root.querySelectorAll<HTMLElement>('*'))]) {
      const where = `${el.tagName.toLowerCase()}.${el.getAttribute('class') ?? ''}`;
      expect(el.getAttribute('class') ?? '', where).not.toMatch(/(^|\s)(transition|animate-|duration-|ease-)/);
      expect(el.style.transition, where).toBe('');
      expect(el.style.animation, where).toBe('');
      expect(el.style.opacity, where).toBe('');
      expect(el.style.transform, where).toBe('');
    }
  });
});

describe('HC-UIPAL-002 (DF-5): aria-activedescendant always names a rendered option', () => {
  it('after typing chol, and after each edit that follows, every aria-activedescendant resolves', async () => {
    const user = userEvent.setup();
    renderShell();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const input = await screen.findByRole('combobox');
    await waitFor(() => expectActiveDescendantsResolve('open'));

    for (const [typed, step] of [
      ['c', 'c'],
      ['h', 'ch'],
      ['o', 'cho'],
      ['l', 'chol'],
    ] as const) {
      await user.type(input, typed);
      await waitFor(() => expectActiveDescendantsResolve(step));
    }
    expect(within(dialog()).getByText('LDL Cholesterol')).toBeInTheDocument();
    expect(within(dialog()).queryByText('Glucose')).toBeNull();

    // A filter that removes the selected option, then one that matches nothing static, then a clear.
    await user.type(input, 'x');
    await waitFor(() => expectActiveDescendantsResolve('cholx'));
    await user.clear(input);
    await waitFor(() => expectActiveDescendantsResolve('cleared'));
    await user.type(input, 'gluc');
    await waitFor(() => expectActiveDescendantsResolve('gluc'));
    await user.keyboard('{Backspace}{Backspace}{Backspace}{Backspace}');
    await waitFor(() => expectActiveDescendantsResolve('backspaced'));
  });

  it('the first visible option is selected after every filter change', async () => {
    const user = userEvent.setup();
    renderShell();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const input = await screen.findByRole('combobox');
    await user.type(input, 'chol');
    await waitFor(() => {
      const options = within(dialog()).getAllByRole('option');
      expect(options[0]).toHaveAttribute('aria-selected', 'true');
      expect(input.getAttribute('aria-activedescendant')).toBe(options[0].id);
    });
  });
});

describe('HC-UIPAL-004: Escape returns focus to the trigger, and Enter on free text goes to /search', () => {
  it('Escape closes the palette and focus returns to the header trigger', async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(trigger());
    await screen.findByRole('dialog', { name: 'Command palette' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(trigger()).toHaveFocus());
  });

  it('Enter on free text with no match opens /search?q= and closes the palette', async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(trigger());
    await user.type(await screen.findByRole('combobox'), 'migraine aura{Enter}');
    expect(screen.getByTestId('location')).toHaveTextContent('/search?q=migraine+aura');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });

  it('Enter on free text still reaches /search when the record search has hits (a hit is not the default)', async () => {
    vi.mocked(useSearch).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            type: 'entity',
            id: 'e1',
            doc_id: 'doc-1',
            title: 'Diagnoses: migraine aura',
            snippet: 'recorded',
            date: null,
            verified_status: 'unverified',
            category: null,
            highlight_types: [],
          },
        ],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearch>);
    const user = userEvent.setup();
    renderShell();
    await user.click(trigger());
    await user.type(await screen.findByRole('combobox'), 'migraine aura');
    // The hit renders only once the 150 ms debounce has passed; Enter before then proves nothing about the order.
    await within(dialog()).findByRole('option', { name: /Diagnoses: migraine aura/ });
    await user.keyboard('{Enter}');
    expect(screen.getByTestId('location')).toHaveTextContent('/search?q=migraine+aura');
  });

  it('Escape after the palette was opened from the page body returns focus to the header trigger', async () => {
    const user = userEvent.setup();
    renderShell();
    expect(document.activeElement).toBe(document.body);
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    await screen.findByRole('dialog', { name: 'Command palette' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(trigger()).toHaveFocus());
  });

  it('Enter on a matching destination goes there instead of to /search', async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(trigger());
    await user.type(await screen.findByRole('combobox'), 'timeline{Enter}');
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/timeline$/);
  });
});

describe('HC-UIPAL-005 (vitest half): the Results group shows the latest value as static T0 text', () => {
  it('shows the latest value of each analyte with data-t0, not an older one', async () => {
    renderShell();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const root = await screen.findByRole('dialog', { name: 'Command palette' });
    const latest = await within(root).findByText('118 mg/dL');
    expect(latest).toHaveAttribute('data-t0');
    expect(within(root).queryByText('92 mg/dL')).toBeNull();
    expect(within(root).queryByText('101 mg/dL')).toBeNull();
  });
});

const HIT = (overrides: Record<string, unknown>) => ({
  type: 'entity',
  id: 'e1',
  doc_id: 'doc-1',
  title: 'Diagnoses: migraine aura',
  snippet: 'recorded',
  date: null,
  verified_status: 'verified',
  category: null,
  highlight_types: [],
  ...overrides,
});

describe('HC-UIPAL-005 (D4): a value is never shown without its unit and mark', () => {
  it('shows a zero value, with and without a unit', async () => {
    vi.mocked(useObservations).mockReturnValue({
      data: [
        observation({ id: 'b1', analyte_canonical: 'basophils', analyte_raw: 'Basophils', value: 0, unit: '%', user_verified: true }),
        observation({ id: 'n1', analyte_canonical: 'titre', analyte_raw: 'Titre', value: 0, unit: null, user_verified: true }),
      ],
    } as unknown as ReturnType<typeof useObservations>);
    renderShell();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const root = await screen.findByRole('dialog', { name: 'Command palette' });
    expect(await within(root).findByText('0 %')).toHaveAttribute('data-t0');
    const titre = within(root).getByRole('option', { name: /Titre/ });
    expect(within(titre).getByText('0')).toHaveAttribute('data-t0');
  });

  it('marks an unverified latest value inside the same data-t0 text, and leaves a verified one bare', async () => {
    renderShell();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const root = await screen.findByRole('dialog', { name: 'Command palette' });
    expect(await within(root).findByText('142 mg/dL (unverified)')).toHaveAttribute('data-t0');
    expect(within(root).getByText('118 mg/dL')).toHaveAttribute('data-t0');
    expect(within(root).queryByText('118 mg/dL (unverified)')).toBeNull();
  });

  it('marks an unverified record hit, and leaves a verified one bare', async () => {
    vi.mocked(useSearch).mockReturnValue({
      data: {
        count: 2,
        results: [
          HIT({ id: 'e1', title: 'Diagnoses: migraine aura', verified_status: 'unverified' }),
          HIT({ id: 'e2', title: 'Diagnoses: migraine without aura', verified_status: 'verified' }),
        ],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearch>);
    const user = userEvent.setup();
    renderShell();
    await user.click(trigger());
    await user.type(await screen.findByRole('combobox'), 'migraine');
    expect(await within(dialog()).findByRole('option', { name: 'Diagnoses: migraine aura (unverified)' })).toBeInTheDocument();
    expect(within(dialog()).getByRole('option', { name: 'Diagnoses: migraine without aura' })).toBeInTheDocument();
  });
});

describe('HC-UIPAL-004: a Results row jumps to its analyte', () => {
  it('Enter on an analyte goes to /trends?analyte=<canonical>', async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(trigger());
    await user.type(await screen.findByRole('combobox'), 'ldl{Enter}');
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/trends\?analyte=ldl_cholesterol$/);
  });
});

describe('HC-UIPAL-004: the record search is debounced 150 ms and stops when the palette closes', () => {
  const queries = () => vi.mocked(useSearch).mock.calls.map(([filters]) => filters.q);
  const last = () => queries()[queries().length - 1];

  it('asks for a query only after 150 ms without typing, and not at all once closed', async () => {
    renderShell();
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const input = await screen.findByRole('combobox');
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    try {
      fireEvent.change(input, { target: { value: 'chol' } });
      act(() => void vi.advanceTimersByTime(149));
      expect(queries()).not.toContain('chol');
      act(() => void vi.advanceTimersByTime(1));
      expect(queries()).toContain('chol');
      expect(last()).toBe('chol');

      act(() => closePalette());
      expect(last(), 'a closed palette keeps no live query').toBe('');
    } finally {
      vi.useRealTimers();
    }
  });
});

const openWithKeys = () => fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
const optionNamed = (name: string | RegExp) => within(dialog()).getByRole('option', { name });
const searchHits = (types: string[]) =>
  vi.mocked(useSearch).mockReturnValue({
    data: {
      count: types.length,
      results: types.map((type) => HIT({ type, id: `${type}-1`, title: `Hit ${type}`, verified_status: 'verified' })),
    },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useSearch>);

describe('HC-UIPAL-004: the Actions group and each record hit go to their destination', () => {
  // Start away from /inbox, /medications, /verify and /trends so a wrong or missing navigation cannot look right.
  it.each([
    ['import a document', /^\/inbox$/],
    ['log a dose', /^\/medications$/],
  ])('Enter on the action "%s" goes to its page', async (text, path) => {
    const user = userEvent.setup();
    renderShell('/timeline');
    await user.click(trigger());
    await user.type(await screen.findByRole('combobox'), `${text}{Enter}`);
    expect(screen.getByTestId('location')).toHaveTextContent(path);
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });

  it.each([
    ['document', /^\/inbox$/],
    ['entity', /^\/verify$/],
    ['observation', /^\/trends$/],
  ])('a %s hit goes to its page', async (type, path) => {
    searchHits([type]);
    const user = userEvent.setup();
    renderShell('/timeline');
    await user.click(trigger());
    await user.type(await screen.findByRole('combobox'), 'zzq');
    await user.click(await within(dialog()).findByRole('option', { name: `Hit ${type}` }));
    expect(screen.getByTestId('location')).toHaveTextContent(path);
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });
});

describe('HC-UIPAL-004: the mouse activates and highlights an option', () => {
  it('a click on a page goes there and closes the palette', async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(trigger());
    await user.type(await screen.findByRole('combobox'), 'timeline');
    await user.click(optionNamed(/^Timeline$/));
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/timeline$/);
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });

  it('moving the pointer over an option selects it and the input follows', async () => {
    renderShell();
    openWithKeys();
    const input = await screen.findByRole('combobox');
    const options = within(dialog()).getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    fireEvent.mouseMove(options[3]);
    expect(options[3]).toHaveAttribute('aria-selected', 'true');
    expect(options[0]).toHaveAttribute('aria-selected', 'false');
    expect(input.getAttribute('aria-activedescendant')).toBe(options[3].id);
  });
});

describe('HC-UIPAL-001: another open modal keeps the keyboard', () => {
  it.each([
    ['a dialog', 'dialog'],
    ['an alert dialog', 'alertdialog'],
  ])('Ctrl+K and / do not open the palette over %s, and do once it is gone', async (_name, role) => {
    renderShell();
    const other = document.body.appendChild(document.createElement('div'));
    other.setAttribute('role', role);
    other.setAttribute('aria-modal', 'true');
    try {
      openWithKeys();
      fireEvent.keyDown(document.body, { key: '/' });
      expect(screen.queryByRole('dialog', { name: 'Command palette' })).toBeNull();
    } finally {
      other.remove(); // a failed assertion must not leave a modal behind for the next test
    }
    openWithKeys();
    expect(await screen.findByRole('dialog', { name: 'Command palette' })).toBeInTheDocument();
  });
});

describe('the palette starts closed and unfetched in each shell', () => {
  it('unmounting the shell with the palette open closes it, and the next shell neither shows nor fetches it', async () => {
    const first = renderShell('/inbox', true);
    openWithKeys();
    await screen.findByRole('dialog', { name: 'Command palette' });
    first.unmount();

    vi.mocked(useObservations).mockClear();
    renderShell('/inbox', true);
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(useObservations, 'the palette body is not mounted until the first open').not.toHaveBeenCalled();
  });
});

describe('the search box', () => {
  it('stops at 200 characters, which the /search route would refuse beyond', async () => {
    renderShell();
    openWithKeys();
    expect(await screen.findByRole('combobox')).toHaveAttribute('maxLength', '200');
  });

  it('Escape returns focus to the visible trigger: the phone search link when the header button is hidden', async () => {
    const user = userEvent.setup();
    renderShell();
    const link = screen.getByRole('link', { name: 'Search' });
    expect(link).toHaveAttribute('data-palette-trigger');
    // jsdom has no layout: a hidden element has no client rects, as below lg for the header button.
    vi.spyOn(trigger(), 'getClientRects').mockReturnValue([] as unknown as DOMRectList);
    vi.spyOn(link, 'getClientRects').mockReturnValue([{}] as unknown as DOMRectList);
    expect(document.activeElement).toBe(document.body);
    openWithKeys();
    await screen.findByRole('dialog', { name: 'Command palette' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(link).toHaveFocus());
  });
});

describe('a closed palette makes no API call (the real hooks, only the network mocked)', () => {
  const calls = (path: string) => vi.mocked(apiGet).mock.calls.filter(([called]) => called === path).length;
  // React Query refetches a stale query for an active observer when the window comes back into focus.
  const refocusWindow = () => act(() => void window.dispatchEvent(new Event('visibilitychange')));
  const settle = (ms: number) => act(() => new Promise<void>((resolve) => setTimeout(resolve, ms)));

  beforeEach(async () => {
    const observations = await vi.importActual<typeof import('@/services/observations')>('@/services/observations');
    const search = await vi.importActual<typeof import('@/services/search')>('@/services/search');
    vi.mocked(useObservations).mockImplementation(observations.useObservations);
    vi.mocked(useSearch).mockImplementation(search.useSearch);
    vi.mocked(apiGet).mockImplementation((async (path: string) => {
      if (path === '/observations/') return OBSERVATIONS;
      if (path === '/search/') return { count: 0, results: [] };
      throw new Error(`unmocked API call ${path}`);
    }) as never);
    useAuthStore.setState({ profileId: 'p1' });
  });

  afterEach(() => {
    useAuthStore.setState({ profileId: null });
  });

  it('refetches /observations on window focus while open, and not once closed', async () => {
    renderShell();
    openWithKeys();
    await waitFor(() => expect(calls('/observations/')).toBe(1));
    refocusWindow();
    await waitFor(() => expect(calls('/observations/'), 'open: a focus refetch is how this test sees a live query').toBe(2));

    act(() => closePalette());
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    refocusWindow();
    await settle(100);
    expect(calls('/observations/'), 'closed: no refetch').toBe(2);
  });

  it('reopening does not run the last search again, and the box is empty', async () => {
    const user = userEvent.setup();
    renderShell();
    openWithKeys();
    await user.type(await screen.findByRole('combobox'), 'chol');
    await waitFor(() => expect(calls('/search/')).toBe(1));

    act(() => closePalette());
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    openWithKeys();
    expect(await screen.findByRole('combobox')).toHaveValue('');
    await settle(400); // past the 150 ms debounce
    expect(calls('/search/'), 'q=chol is not asked again on reopen').toBe(1);
  });
});
