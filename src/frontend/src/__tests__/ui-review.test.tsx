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

const state = { observations: [] as unknown[] };

function mockApi() {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url.startsWith('/documents') && url.includes('/pages')) return Promise.resolve([]);
    if (url.startsWith('/documents')) return Promise.resolve([]);
    if (url.startsWith('/observations')) return Promise.resolve(state.observations);
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

  // Blind spot: it keeps UI-SHELL's classes by name. L0 ruling on #370: grid-cols-1 lg:grid-cols-3 and lg:col-span-2 stay.
  it('keeps the page grid from UI-SHELL', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(document.querySelector('.grid.grid-cols-1.lg\\:grid-cols-3')).not.toBeNull();
    expect(document.querySelector('.lg\\:col-span-2')).not.toBeNull();
  });
});
