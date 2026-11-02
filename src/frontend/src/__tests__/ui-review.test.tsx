/**
 * UI-PG-REVIEW (plan section 7.7): HC-UIREV-001 to HC-UIREV-005 on /verify, plus the page rules the review
 * page shares (data-t0 on values, no row entrance stagger, no transition-all).
 *
 * Written red first. Each test says in its comment what it would not notice. HC-UIREV-004 and HC-UIREV-005
 * are layout and timing measurements: jsdom has no layout and no clock-driven paint, so e2e/ui-review.spec.ts
 * carries the real check (G6 at 390 and 320; stillnessProbe from the Edit click). The tests here pin the markup
 * those checks rely on.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { VerificationWorkbench } from '@/pages/VerificationWorkbench';
import { EntityDetailView } from '@/components/documents/EntityDetailView';
import * as api from '@/services/api';
import { notify } from '@/components/ui/toast';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/components/ui/toast', () => ({ notify: vi.fn(), AppToaster: () => null }));

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
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

vi.mock('@/services/highlights', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/highlights')>()),
  useDocumentHighlights: () => ({ data: [] }),
}));

const PAGES_DIR = resolve(__dirname, '..', 'pages');
const DOCUMENTS_DIR = resolve(__dirname, '..', 'components', 'documents');

const baseObservation = {
  profile_id: 'profile-123',
  doc_id: 'doc-1',
  value_text: null,
  ref_range_text: null,
  is_abnormal: false,
  collected_at: '2026-04-10T00:00:00',
  user_verified: false,
  extraction_confidence: 0.9,
  source_page: null,
  source_bbox_json: null,
};

const glucose = {
  ...baseObservation,
  id: 'obs-1',
  analyte_canonical: 'glucose',
  analyte_raw: 'Glucose',
  value: 95,
  unit: 'mg/dL',
  ref_low: 70,
  ref_high: 100,
  flag: null,
};
const hba1c = {
  ...baseObservation,
  id: 'obs-2',
  analyte_canonical: 'hba1c',
  analyte_raw: 'Hemoglobin A1c',
  value: 6.5,
  unit: '%',
  ref_low: 4.0,
  ref_high: 5.6,
  flag: 'H',
  is_abnormal: true,
};
const ferritin = {
  ...baseObservation,
  id: 'obs-3',
  analyte_canonical: 'ferritin',
  analyte_raw: 'Ferritin',
  value: 8,
  unit: 'ng/mL',
  ref_low: 12,
  ref_high: 150,
  flag: 'L',
  is_abnormal: true,
};
// No flag from the report: the direction comes from the numbers.
const ldlUnflagged = {
  ...baseObservation,
  id: 'obs-4',
  analyte_canonical: 'ldl',
  analyte_raw: 'LDL cholesterol',
  value: 130,
  unit: 'mg/dL',
  ref_low: null,
  ref_high: 100,
  flag: null,
};

// The extractor also emits A, ABNORMAL and CRITICAL (be/modules/extract.py), and sets is_abnormal. These three
// have numbers inside the range, so a chip that trusts the numbers alone would say "In range" beside a value
// the report itself flagged.
const flaggedA = {
  ...baseObservation,
  id: 'obs-5',
  analyte_canonical: 'sodium',
  analyte_raw: 'Sodium',
  value: 140,
  unit: 'mmol/L',
  ref_low: 135,
  ref_high: 145,
  flag: 'A',
  is_abnormal: true,
};
const flaggedCritical = { ...flaggedA, id: 'obs-6', analyte_raw: 'Potassium', flag: 'CRITICAL' };
const flaggedAbnormalWord = { ...flaggedA, id: 'obs-7', analyte_raw: 'Calcium', flag: 'ABNORMAL' };
const abnormalNoFlag = { ...flaggedA, id: 'obs-8', analyte_raw: 'Chloride', flag: null };
// A letter flag with numbers outside the range: the numbers still give the direction.
const flaggedAHigh = { ...flaggedA, id: 'obs-9', analyte_raw: 'Magnesium', value: 3, ref_low: 1, ref_high: 2 };

const state = { observations: [] as unknown[] };

/** Like the API: the default /verify list asks for needs_verification=true and gets only unverified rows back. */
function mockApi() {
  vi.mocked(api.apiGet).mockImplementation((url: string, params?: Record<string, string>) => {
    if (url.startsWith('/documents') && url.includes('/pages')) return Promise.resolve([]);
    if (url.startsWith('/documents')) return Promise.resolve([]);
    if (url.startsWith('/observations')) {
      const rows = state.observations as { user_verified: boolean }[];
      return Promise.resolve(params?.needs_verification === 'true' ? rows.filter((row) => !row.user_verified) : rows);
    }
    return Promise.resolve([]);
  });
}

function renderWorkbench() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <VerificationWorkbench />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

const rowOf = (id: string) => document.getElementById(`observation-row-${id}`) as HTMLElement;

function setReducedMotion(reduce: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: reduce && query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useAuthStore.getState().setAuth({
    token: 'test-token',
    profileId: 'profile-123',
    profileName: 'Test Profile',
  });
  state.observations = [glucose, hba1c, ferritin, ldlUnflagged];
  mockApi();
  setReducedMotion(false);
});

afterEach(() => {
  setReducedMotion(false);
  window.history.pushState({}, '', '/');
});

describe('HC-UIREV-001: a value outside its range carries an icon and words, not colour alone', () => {
  // Blind spot: it reads the chip's words and icon, not its contrast. UI-TOKENS' contrast test and axe (G1) own that.
  it.each([
    ['obs-2', 'above-range', "Above the report's range"],
    ['obs-3', 'below-range', "Below the report's range"],
    ['obs-1', 'in-range', 'In range'],
  ])('%s shows the %s chip with its words and an icon', async (id, chipState, words) => {
    renderWorkbench();
    await screen.findByText('Glucose');
    const chip = rowOf(id).querySelector(`[data-state="${chipState}"]`);
    expect(chip).not.toBeNull();
    expect(chip).toHaveTextContent(words);
    expect(chip!.querySelector('svg')).not.toBeNull();
  });

  // Blind spot: a flagged value is covered by the cases above. This one has no flag, so it fails if the
  // direction comes only from the report's flag and never from the numbers.
  it('a value over ref_high with no flag still reads as above the range', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(rowOf('obs-4').querySelector('[data-state="above-range"]')).toHaveTextContent(
      "Above the report's range"
    );
  });

  // Blind spot: it covers the three flag words the extractor emits and is_abnormal. Any other unknown flag text
  // takes the same branch. Without this a CRITICAL value inside its range reads "In range" (HC-UIREV-001 review).
  it.each([
    ['obs-5', 'flag A'],
    ['obs-6', 'flag CRITICAL'],
    ['obs-7', 'flag ABNORMAL'],
    ['obs-8', 'is_abnormal with no flag'],
  ])('%s (%s) with numbers inside the range never reads In range', async (id) => {
    state.observations = [glucose, flaggedA, flaggedCritical, flaggedAbnormalWord, abnormalNoFlag];
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(rowOf(id)).not.toBeNull();
    expect(rowOf(id).querySelector('[data-state="in-range"]')).toBeNull();
    expect(rowOf(id).textContent).not.toMatch(/in range/i);
    // The clean row beside them still says it.
    expect(rowOf('obs-1').querySelector('[data-state="in-range"]')).not.toBeNull();
  });

  // Blind spot: one value. It pins that a letter flag does not switch the numbers off.
  it('flag A with a value over ref_high still reads as above the range', async () => {
    state.observations = [glucose, flaggedAHigh];
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(rowOf('obs-9').querySelector('[data-state="above-range"]')).toHaveTextContent("Above the report's range");
  });

  // Blind spot: only the words are checked. A row that says "Above" in the chip and shows no number is not caught here.
  it('never says normal or abnormal', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    for (const id of ['obs-1', 'obs-2', 'obs-3', 'obs-4']) {
      expect(rowOf(id).textContent).not.toMatch(/\b(abnormal|normal)\b/i);
    }
  });
});

describe('HC-UIREV-002: verifying flips the marker from pencil to ink and the chip to checked by you', () => {
  async function verifyGlucose(user: ReturnType<typeof userEvent.setup>) {
    vi.mocked(api.apiPost).mockImplementation(async () => {
      state.observations = [{ ...glucose, user_verified: true }, hba1c, ferritin, ldlUnflagged];
      return { ...glucose, user_verified: true };
    });
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
  }

  const markerOf = (row: HTMLElement) => row.querySelector('[data-ink-marker]') as HTMLElement | null;
  const checkChipOf = (row: HTMLElement) =>
    row.querySelector('[data-state="not-checked"], [data-state="checked-by-you"]') as HTMLElement | null;

  // Blind spot: the states are data attributes. That the ink layer is revealed with a clip-path is not visible
  // in jsdom (no CSS engine); the e2e probe samples the real thing.
  it('starts as pencil and not yet checked', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'pencil');
    expect(checkChipOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'not-checked');
    expect(checkChipOf(rowOf('obs-1'))).toHaveTextContent('Not yet checked');
  });

  // Blind spot: it watches one row. The chart half of "row, chart and chip together" needs a chart; /verify has none.
  it('marker and chip flip in the same commit, never one before the other', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    const row = rowOf('obs-1');

    const seen: string[] = [];
    const record = () => {
      seen.push(`${markerOf(row)?.dataset.state}+${checkChipOf(row)?.dataset.state}`);
    };
    record();
    const observer = new MutationObserver(record);
    observer.observe(row, { subtree: true, childList: true, attributes: true, characterData: true });

    await verifyGlucose(user);
    await waitFor(() => expect(markerOf(row)).toHaveAttribute('data-state', 'ink'));
    observer.disconnect();

    expect(checkChipOf(row)).toHaveAttribute('data-state', 'checked-by-you');
    expect(checkChipOf(row)).toHaveTextContent('Checked by you');
    for (const combo of seen) {
      expect(['pencil+not-checked', 'ink+checked-by-you']).toContain(combo);
    }
    expect(seen).toContain('ink+checked-by-you');
  });

  // Blind spot: textContent and node identity only. A colour or position change is the e2e probe's job.
  it('the value, unit and range nodes keep their text and stay the same nodes', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    const row = rowOf('obs-1');
    const before = Array.from(row.querySelectorAll('[data-t0]')).filter(
      (node) => !node.hasAttribute('data-state')
    );
    const texts = before.map((node) => node.textContent);
    expect(texts).toEqual(expect.arrayContaining(['95', 'mg/dL']));

    await verifyGlucose(user);
    await waitFor(() => expect(markerOf(row)).toHaveAttribute('data-state', 'ink'));

    for (const [index, node] of before.entries()) {
      expect(node.isConnected).toBe(true);
      expect(node.textContent).toBe(texts[index]);
    }
  });

  // Blind spot: aria-hidden is read from the attribute, not from the accessibility tree.
  it('the marker is decoration: aria-hidden, no data-t0 on it or inside it', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    const marker = markerOf(rowOf('obs-1'))!;
    expect(marker).toHaveAttribute('aria-hidden', 'true');
    expect(marker.hasAttribute('data-t0')).toBe(false);
    expect(marker.querySelector('[data-t0]')).toBeNull();
  });

  // Blind spot: the mocked notify records the call. That sonner renders it with M0 is UI-PRIM-FEEDBACK's test.
  it('shows a still toast that names the value and its date, with no Undo', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await verifyGlucose(user);
    await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
    // toEqual: an `action` key (Undo) would fail it, and so would a missing `still`.
    expect(vi.mocked(notify).mock.calls[0][0]).toEqual({
      message: 'Glucose, Apr 10, 2026 is now marked as checked',
      still: true,
    });
  });

  // Blind spot: it covers a null date only. An unparseable string is dropped by the same branch.
  it('drops the date when collected_at is null and never invents one', async () => {
    const user = userEvent.setup();
    state.observations = [{ ...glucose, collected_at: null }, hba1c];
    renderWorkbench();
    await screen.findByText('Glucose');
    vi.mocked(api.apiPost).mockResolvedValue({ ...glucose, collected_at: null, user_verified: true });
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
    expect(vi.mocked(notify).mock.calls[0][0]).toEqual({
      message: 'Glucose is now marked as checked',
      still: true,
    });
  });

  // Blind spot: reduced motion is read from a mocked matchMedia, as in ui-motion.test.tsx.
  it('under reduced motion the swap is instant and the toast still shows', async () => {
    setReducedMotion(true);
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-motion', 'instant');
    await verifyGlucose(user);
    await waitFor(() => expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'ink'));
    expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-motion', 'instant');
    expect(notify).toHaveBeenCalledTimes(1);
  });

  // Blind spot: it checks the attribute that selects the 360 ms reveal, not the duration itself.
  it('with motion allowed the marker uses the ink reveal', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-motion', 'ink');
  });

  const rowIds = () =>
    Array.from(document.querySelectorAll('tr[id^="observation-row-"]')).map((tr) => tr.id.replace('observation-row-', ''));

  // Blind spot: the mock drops verified rows from a needs_verification list the way the API does, so this is the
  // route a user actually lands on. The first version of this suite served every row to every filter and never saw
  // the row leave (recurring-failures 1).
  it('on the default list (needs_verification) a verified row stays, as ink, in the same place', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(vi.mocked(api.apiGet)).toHaveBeenCalledWith(
      '/observations/',
      expect.objectContaining({ needs_verification: 'true' })
    );
    const before = rowIds();
    await verifyGlucose(user);
    await waitFor(() => expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'ink'));
    // Let the refetch (which no longer contains obs-1) land.
    await waitFor(() => expect(vi.mocked(api.apiGet).mock.calls.filter(([url]) => url === '/observations/').length).toBeGreaterThan(1));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(rowIds()).toEqual(before);
    expect(checkChipOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'checked-by-you');
    expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'ink');
    // The rows that were not verified are untouched.
    expect(markerOf(rowOf('obs-2'))).toHaveAttribute('data-state', 'pencil');
  });

  // Blind spot: document mode serves every row, so the row never left; it pins that the hold does not duplicate it.
  it('in document review mode a verified row is shown once, as ink', async () => {
    window.history.pushState({}, '', '/verify?doc=doc-1&mode=all');
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await verifyGlucose(user);
    await waitFor(() => expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'ink'));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(document.querySelectorAll('#observation-row-obs-1')).toHaveLength(1);
    expect(checkChipOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'checked-by-you');
  });

  // Blind spot: it reads the DOM from inside the mocked notify. The toast text itself is pinned above.
  it('the toast fires after the row reads Checked by you, not while it still reads Not yet checked', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    let chipAtToast: string | undefined;
    vi.mocked(notify).mockImplementation(() => {
      chipAtToast = checkChipOf(rowOf('obs-1'))?.dataset.state;
      return 'toast-id';
    });
    await verifyGlucose(user);
    await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
    expect(chipAtToast).toBe('checked-by-you');
  });

  // Blind spot: the held row comes from the mutation's answer. It does not check the Edit dialog's own closing.
  it('Save & Verify from the Edit dialog also leaves the row as ink with the saved value', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    vi.mocked(api.apiPost).mockImplementation(async () => {
      state.observations = [{ ...glucose, value: 99, user_verified: true }, hba1c, ferritin, ldlUnflagged];
      return { ...glucose, value: 99, user_verified: true };
    });
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Edit value' }));
    const dialog = await screen.findByRole('dialog');
    const input = within(dialog).getByRole('textbox');
    await user.clear(input);
    await user.type(input, '99');
    await user.click(within(dialog).getByRole('button', { name: /save & verify/i }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(markerOf(rowOf('obs-1'))).toHaveAttribute('data-state', 'ink'));
    expect(rowOf('obs-1')).toHaveTextContent('99');
  });
});

describe('page rules shared with every T0 page', () => {
  // Blind spot: only inline style is read. A CSS class animation would not show here; the next test scans classes.
  it('rows have no entrance motion (M6 never sits on a list of T0 items)', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    for (const id of ['obs-1', 'obs-2', 'obs-3', 'obs-4']) {
      expect(rowOf(id).getAttribute('style') ?? '').not.toMatch(/opacity|transform/);
    }
  });

  // Blind spot: a source scan. It sees the words in the file, not what a build produces.
  it('neither page file animates rows with m.tr or uses transition-all', () => {
    for (const source of [
      readFileSync(resolve(PAGES_DIR, 'VerificationWorkbench.tsx'), 'utf8'),
      readFileSync(resolve(DOCUMENTS_DIR, 'EntityDetailView.tsx'), 'utf8'),
    ]) {
      expect(source).not.toMatch(/<m\.tr\b/);
      expect(source).not.toMatch(/(^|[\s"'`:])transition-all\b/);
    }
  });

  // Blind spot: the cells are found by their text. A value cell with the right text and no data-t0 on its own
  // node (the td only) would fail, which is intended: the probe needs the node that holds the text.
  it('the observation value, unit and range cells are T0 nodes', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    const t0Texts = Array.from(rowOf('obs-1').querySelectorAll('[data-t0]')).map((node) => node.textContent);
    expect(t0Texts).toContain('95');
    expect(t0Texts).toContain('mg/dL');
    expect(t0Texts).toContain('70-100 mg/dL');
  });

  // Blind spot: it covers one date entity and one text entity. Other entity types share the same cell.
  it('EntityDetailView entity_value cells are T0 nodes, date entities included', () => {
    const entities = [
      {
        id: 'ent-1',
        doc_id: 'doc-1',
        category: 'radiology',
        entity_type: 'report_date',
        entity_value: '2026-04-10',
        confidence: 0.95,
        source_page: null,
        source_bbox_json: null,
        char_start: null,
        char_end: null,
        quote: null,
        verified_by_user: null,
        extraction_version: null,
      },
      {
        id: 'ent-2',
        doc_id: 'doc-1',
        category: 'radiology',
        entity_type: 'finding',
        entity_value: 'No acute findings',
        confidence: 0.9,
        source_page: null,
        source_bbox_json: null,
        char_start: null,
        char_end: null,
        quote: null,
        verified_by_user: null,
        extraction_version: null,
      },
    ];
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <EntityDetailView entities={entities} />
      </QueryClientProvider>
    );
    for (const value of ['2026-04-10', 'No acute findings']) {
      const node = screen.getByText(value);
      expect(node.closest('[data-t0]')?.textContent).toBe(value);
    }
  });
});

describe('HC-UIREV-003 and HC-UIREV-005: the Edit dialog', () => {
  async function openEdit() {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    const opener = within(rowOf('obs-1')).getByRole('button', { name: 'Edit value' });
    await user.click(opener);
    const dialog = await screen.findByRole('dialog');
    return { user, dialog, opener };
  }

  // Blind spot: the name is matched by regex, so "Edit Value" and "Edit value" both pass.
  it('is a dialog with a visible title as its accessible name', async () => {
    const { dialog } = await openEdit();
    expect(screen.getByRole('dialog', { name: /edit value/i })).toBe(dialog);
    expect(within(dialog).getByRole('heading', { name: /edit value/i })).toBeVisible();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  // Blind spot: the label is read from the accessibility name, not from how it looks.
  it('labels the input with the analyte', async () => {
    const { dialog } = await openEdit();
    expect(within(dialog).getByRole('textbox', { name: /glucose/i })).toHaveValue('95');
  });

  // Blind spot: jsdom tab order follows the DOM. A browser also tabs into the URL bar, which a trap cannot stop.
  it('traps focus: twelve forward and twelve backward Tabs stay inside', async () => {
    const { user, dialog } = await openEdit();
    expect(dialog.contains(document.activeElement)).toBe(true);
    for (let i = 0; i < 12; i += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
    for (let i = 0; i < 12; i += 1) {
      await user.tab({ shift: true });
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
  });

  // Blind spot: it closes from the input. Escape from the Close button goes through the same Radix handler.
  it('Escape closes it and focus returns to the Edit button', async () => {
    const { user, opener } = await openEdit();
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(opener).toHaveFocus());
  });

  // Blind spot: still means no motion props on the content. The scrim may fade (Dialog keeps it), so it is not checked.
  it('is still: the content carries no opacity or transform', async () => {
    const { dialog } = await openEdit();
    expect(dialog.getAttribute('style') ?? '').not.toMatch(/opacity|transform/);
  });

  // Blind spot: the node is found by [data-t0] inside the dialog. The probe in e2e checks it does not move.
  it('shows the current value as a T0 node that is not the input and does not follow typing', async () => {
    const { user, dialog } = await openEdit();
    const current = dialog.querySelector('[data-t0]') as HTMLElement;
    expect(current).not.toBeNull();
    expect(current.tagName).not.toBe('INPUT');
    expect(current).toHaveTextContent('95');
    expect(current).toHaveTextContent('mg/dL');
    await user.clear(within(dialog).getByRole('textbox'));
    await user.type(within(dialog).getByRole('textbox'), '7.5');
    expect(current).toHaveTextContent('95');
  });

  // Blind spot: strict parse and error path are pinned in full by HC-FVN-001..005. This only checks that the
  // alert still lives inside the new dialog.
  it('keeps the strict-parse alert inside the dialog', async () => {
    const { user, dialog } = await openEdit();
    const input = within(dialog).getByRole('textbox');
    await user.clear(input);
    await user.type(input, '7,5');
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Use a dot for decimals');
  });
});

describe('HC-UIREV-004: below sm the observation rows stack', () => {
  // Blind spot: jsdom applies no CSS, so this reads class names. The measurement is G6 at 390 and 320 in e2e.
  it('table parts switch to block layout below sm and back to table parts from sm', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    const table = rowOf('obs-1').closest('table')!;
    expect(table.className).toMatch(/\bblock\b/);
    expect(table.className).toMatch(/\bsm:table\b/);
    expect(table.querySelector('thead')!.className).toMatch(/\bhidden\b/);
    expect(table.querySelector('thead')!.className).toMatch(/\bsm:table-header-group\b/);
    for (const id of ['obs-1', 'obs-2', 'obs-3', 'obs-4']) {
      expect(rowOf(id).className).toMatch(/\bblock\b/);
      expect(rowOf(id).className).toMatch(/\bsm:table-row\b/);
    }
  });

  // Blind spot: roles are read from attributes. A screen reader's table mode is not run here. display:block on a
  // table part drops its table semantics in some readers, so each part names its role.
  it('table parts keep their roles when they are laid out as blocks', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    const table = rowOf('obs-1').closest('table')!;
    expect(table).toHaveAttribute('role', 'table');
    expect(table.querySelector('thead')).toHaveAttribute('role', 'rowgroup');
    expect(table.querySelector('tbody')).toHaveAttribute('role', 'rowgroup');
    expect(table.querySelector('thead tr')).toHaveAttribute('role', 'row');
    for (const th of Array.from(table.querySelectorAll('th'))) expect(th).toHaveAttribute('role', 'columnheader');
    for (const id of ['obs-1', 'obs-2']) {
      expect(rowOf(id)).toHaveAttribute('role', 'row');
      for (const td of Array.from(rowOf(id).querySelectorAll(':scope > td'))) expect(td).toHaveAttribute('role', 'cell');
    }
  });

  // Blind spot: the label is found by its sm:hidden class. That it is shown below sm and hidden from sm is the e2e check.
  it('the value cell has a phone-only "Value" label, since the header row is hidden there', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    const valueCell = rowOf('obs-1').querySelectorAll(':scope > td')[1] as HTMLElement;
    const label = within(valueCell).getByText('Value');
    expect(label.className).toMatch(/\bsm:hidden\b/);
    // The label is not the T0 node: the value node keeps its text.
    expect(label.hasAttribute('data-t0')).toBe(false);
  });

  // Blind spot: it keeps UI-SHELL's classes by name. L0 ruling on #370: grid-cols-1 lg:grid-cols-3 and lg:col-span-2 stay.
  it('keeps the page grid from UI-SHELL', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(document.querySelector('.grid.grid-cols-1.lg\\:grid-cols-3')).not.toBeNull();
    expect(document.querySelector('.lg\\:col-span-2')).not.toBeNull();
  });
});

describe('EntityDetailView rows say it in words and show the marker too', () => {
  const entity = (id: string, verified: boolean | null) => ({
    id,
    doc_id: 'doc-1',
    category: 'radiology',
    entity_type: 'finding',
    entity_value: `Finding ${id}`,
    confidence: 0.9,
    source_page: null,
    source_bbox_json: null,
    char_start: null,
    char_end: null,
    quote: null,
    verified_by_user: verified,
    extraction_version: null,
  });

  function renderEntities() {
    return render(
      <QueryClientProvider client={new QueryClient()}>
        <EntityDetailView
          entities={[entity('e-yes', true), entity('e-no', false), entity('e-none', null)]}
          onSetVerification={vi.fn()}
        />
      </QueryClientProvider>
    );
  }
  const entityRow = (id: string) => document.getElementById(`entity-row-${id}`) as HTMLElement;

  // Blind spot: static props. That the marker animates when the prop flips is the observation row's test above.
  it('a verified entity shows Checked by you and an ink marker; an unchecked one shows a pencil marker', () => {
    renderEntities();
    const yes = entityRow('e-yes');
    expect(yes.querySelector('[data-state="checked-by-you"]')).toHaveTextContent('Checked by you');
    expect(yes.querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
    expect(yes.textContent).not.toMatch(/\bVerified\b/);
    const none = entityRow('e-none');
    expect(none.querySelector('[data-state="checked-by-you"]')).toBeNull();
    expect(none.querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'pencil');
  });

  // Blind spot: a rejected entity keeps its Rejected badge; the plan gives no Ink for a rejection.
  it('a rejected entity keeps its Rejected badge and gets no ink', () => {
    renderEntities();
    const no = entityRow('e-no');
    expect(no).toHaveTextContent('Rejected');
    expect(no.querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'pencil');
  });

  // Blind spot: aria-hidden is read from the attribute.
  it('the entity marker is decoration: aria-hidden, no data-t0', () => {
    renderEntities();
    const marker = entityRow('e-yes').querySelector('[data-ink-marker]')!;
    expect(marker).toHaveAttribute('aria-hidden', 'true');
    expect(marker.hasAttribute('data-t0')).toBe(false);
  });

  // Blind spot: roles from attributes only.
  it('the entity table keeps table roles', () => {
    renderEntities();
    const table = entityRow('e-yes').closest('table')!;
    expect(table).toHaveAttribute('role', 'table');
    expect(entityRow('e-yes')).toHaveAttribute('role', 'row');
    expect(entityRow('e-yes').querySelector('td')).toHaveAttribute('role', 'cell');
  });
});
