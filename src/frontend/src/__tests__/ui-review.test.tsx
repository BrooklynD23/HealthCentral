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
import { SourceTrace } from '@/components/results/SourceTrace';
import type { Observation } from '@/services/types';
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

// Rows for the L0 ruling on review round 3 (finding 1): what a plain Verify does to a printed flag.
// CRITICAL with the number inside the range: the lab flagged it, and Verify must not erase that.
const criticalInRange = {
  ...baseObservation,
  id: 'obs-c',
  analyte_canonical: 'potassium',
  analyte_raw: 'Potassium',
  value: 4.2,
  unit: 'mmol/L',
  ref_low: 3.5,
  ref_high: 5.1,
  flag: 'CRITICAL',
  is_abnormal: true,
};
// H with no numeric range at all: the flag is the only evidence of direction.
const highNoRange = {
  ...baseObservation,
  id: 'obs-h',
  analyte_canonical: 'troponin',
  analyte_raw: 'Troponin',
  value: 0.08,
  unit: 'ng/mL',
  ref_low: null,
  ref_high: null,
  flag: 'H',
  is_abnormal: true,
};
// The extractor can keep the brackets: "(H)".
const bracketHigh = { ...highNoRange, id: 'obs-p', analyte_raw: 'Sodium', analyte_canonical: 'sodium', flag: '(H)' };
// A normal word with the number inside the range: nothing to claim before or after.
const normalWordInRange = { ...criticalInRange, id: 'obs-n', analyte_raw: 'Chloride', flag: 'N', is_abnormal: false };
// A normal word with the number over ref_high: the numbers win, and Verify recalculates it to H.
const normalWordHigh = { ...ldlUnflagged, id: 'obs-nh', analyte_raw: 'Triglycerides', flag: 'N' };

const state = {
  observations: [] as unknown[],
  documents: [] as unknown[],
  /** GET /documents/doc-1/pages: the source text the page preview and the Source Trace sheet read. */
  pages: [] as unknown[],
  /** When set, GET /documents (the list) waits for it, like a slow server. */
  holdDocuments: null as Promise<void> | null,
  /** When set, GET /observations/ waits for it and then reads the stored rows, like a refetch that is slow to answer. */
  holdObservations: null as Promise<void> | null,
};

/**
 * What POST /observations/:id/verify does, copied from src/backend/api/observations.py (`_NORMAL_FLAGS` and the
 * recalculation after `observation.version += 1`): the numbers are recalculated only when value, ref_low or
 * ref_high really changed, or when the row has no flag or a normal word. A plain Verify keeps any other flag.
 * This is a mock, not the backend; HC-VKF on main pins the real behaviour.
 */
const NORMAL_FLAGS = new Set(['NORMAL', 'N', 'WNL', 'NO', 'FALSE', '0']);
type Row = {
  id: string;
  value: number | null;
  ref_low: number | null;
  ref_high: number | null;
  flag: string | null;
  is_abnormal: boolean;
  user_verified: boolean;
};
function verifyLikeApi(current: Row, edit: Partial<Row> = {}): Row {
  const next: Row = { ...current };
  for (const field of ['value', 'ref_low', 'ref_high'] as const) {
    if (edit[field] !== undefined && edit[field] !== null) next[field] = edit[field] as number;
  }
  next.user_verified = true;
  const numbersChanged = (['value', 'ref_low', 'ref_high'] as const).some((field) => next[field] !== current[field]);
  const keepsFlag = current.flag !== null && !NORMAL_FLAGS.has(current.flag.trim().toUpperCase());
  if ((numbersChanged || !keepsFlag) && next.value !== null) {
    if (next.ref_low !== null && next.value < next.ref_low) Object.assign(next, { is_abnormal: true, flag: 'L' });
    else if (next.ref_high !== null && next.value > next.ref_high) Object.assign(next, { is_abnormal: true, flag: 'H' });
    else Object.assign(next, { is_abnormal: false, flag: null });
  }
  return next;
}

/** POST /observations/:id/verify answers like the API and keeps the stored row, so the next GET agrees. */
function mockVerifyEndpoint() {
  vi.mocked(api.apiPost).mockImplementation(async (url: string, body?: unknown) => {
    const id = /\/observations\/([^/]+)\/verify$/.exec(url)?.[1];
    const rows = state.observations as Row[];
    const current = rows.find((row) => row.id === id);
    if (!current) throw new Error(`not stubbed: ${url}`);
    const saved = verifyLikeApi(current, (body ?? {}) as Partial<Row>);
    state.observations = rows.map((row) => (row.id === id ? saved : row));
    return saved;
  });
}

/** Like the API: the default /verify list asks for needs_verification=true and gets only unverified rows back. */
function mockApi() {
  vi.mocked(api.apiGet).mockImplementation(async (url: string, params?: Record<string, string>) => {
    if (url.startsWith('/documents') && url.includes('/pages')) return state.pages;
    if (url === '/documents/doc-1') return reportDoc;
    if (url === '/documents' || url === '/documents/') {
      if (state.holdDocuments) await state.holdDocuments;
      return state.documents;
    }
    if (url.startsWith('/documents')) return [];
    if (url.startsWith('/observations')) {
      if (state.holdObservations) await state.holdObservations;
      const rows = state.observations as { user_verified: boolean }[];
      return params?.needs_verification === 'true' ? rows.filter((row) => !row.user_verified) : rows;
    }
    return [];
  });
}

function renderWorkbench() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <VerificationWorkbench />
      </BrowserRouter>
    </QueryClientProvider>
  );
  return { ...utils, queryClient };
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
  state.documents = [];
  state.pages = [];
  state.holdDocuments = null;
  state.holdObservations = null;
  mockApi();
  mockVerifyEndpoint();
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
  ])('%s shows the %s chip with its words and an icon', async (id, chipState, words) => {
    renderWorkbench();
    await screen.findByText('Glucose');
    const chip = rowOf(id).querySelector(`[data-state="${chipState}"]`);
    expect(chip).not.toBeNull();
    expect(chip).toHaveTextContent(words);
    expect(chip!.querySelector('svg')).not.toBeNull();
  });

  // L0 ruling on review round 3 (finding 1): this row asks only for words on out-of-range values, so the
  // in-range chip is gone. Round 1 of this row had asserted that chip ("In range" on obs-1) as new behaviour.
  // Blind spot: it checks the chip, not a different phrase for the same reassurance in another element.
  it('a value inside its range shows no range chip and no "In range" words', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(rowOf('obs-1').querySelector('[data-state="in-range"]')).toBeNull();
    expect(rowOf('obs-1').textContent).not.toMatch(/in range/i);
    expect(rowOf('obs-1').querySelector('[data-state$="-range"]')).toBeNull();
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
  // takes the same branch. A CRITICAL value inside its range must say nothing about the range (HC-UIREV-001 review).
  it.each([
    ['obs-5', 'flag A'],
    ['obs-6', 'flag CRITICAL'],
    ['obs-7', 'flag ABNORMAL'],
    ['obs-8', 'is_abnormal with no flag'],
  ])('%s (%s) with numbers inside the range shows no range chip', async (id) => {
    state.observations = [glucose, flaggedA, flaggedCritical, flaggedAbnormalWord, abnormalNoFlag];
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(rowOf(id)).not.toBeNull();
    expect(rowOf(id).querySelector('[data-state$="-range"]')).toBeNull();
    expect(rowOf(id).textContent).not.toMatch(/in range/i);
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

  // Finding 13. Blind spot: the text of one cell; the e2e spec reads the same cell on screen.
  it.each([
    ['obs-4', '≤ 100 mg/dL', 'only ref_high'],
    ['obs-1', '70-100 mg/dL', 'both limits'],
  ])('%s prints its range as %s (%s)', async (id, text) => {
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(Array.from(rowOf(id).querySelectorAll('[data-t0]')).map((node) => node.textContent)).toContain(text);
  });

  it('a range with only ref_low prints ≥, and ref_range_text still wins', async () => {
    state.observations = [
      { ...glucose, ref_high: null },
      { ...hba1c, ref_range_text: '4.0 to 5.6' },
    ];
    renderWorkbench();
    await screen.findByText('Glucose');
    const cells = (id: string) => Array.from(rowOf(id).querySelectorAll('[data-t0]')).map((node) => node.textContent);
    expect(cells('obs-1')).toContain('≥ 70 mg/dL');
    expect(cells('obs-2')).toContain('4.0 to 5.6 %');
    expect(cells('obs-2').join('|')).not.toContain('≥');
  });
});

describe('HC-UIREV-001 and HC-UIREV-002 across Verify (L0 ruling on review round 3, finding 1)', () => {
  const valueNodeOf = (row: HTMLElement) =>
    Array.from(row.querySelectorAll('span[data-t0]')).find((node) => node.className.includes('font-mono')) as HTMLElement;
  const chipWordsOf = (row: HTMLElement) => row.querySelector('[data-state$="-range"]')?.textContent ?? null;
  const tintOf = (row: HTMLElement) =>
    ['text-status-attention', 'text-status-caution', 'text-ink'].find((cls) => valueNodeOf(row).classList.contains(cls));

  /** Renders the rows, snapshots the row, clicks Verify, waits for the ink, and snapshots again. */
  async function acrossVerify(rows: unknown[], id: string) {
    state.observations = [glucose, ...rows];
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    const row = rowOf(id);
    const node = valueNodeOf(row);
    const before = { words: chipWordsOf(row), tint: tintOf(row), text: node.textContent };
    await user.click(within(row).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(row.querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'ink'));
    await waitFor(() => expect(vi.mocked(api.apiGet).mock.calls.filter(([url]) => url === '/observations/').length).toBeGreaterThan(1));
    await new Promise((resolve) => setTimeout(resolve, 50));
    const after = { words: chipWordsOf(rowOf(id)), tint: tintOf(rowOf(id)), text: valueNodeOf(rowOf(id)).textContent };
    return { before, after, sameNode: valueNodeOf(rowOf(id)) === node };
  }

  // Each case's blind spot: jsdom has no layout, so the value's rect and its computed colour are e2e's (the
  // "Verify keeps the printed flag" tests there). Here the chip words and the tint class are read.

  // (a) A pin on the old code once the mock is right: CRITICAL has no side, so there was never a chip.
  it('(a) CRITICAL 4.2 inside 3.5-5.1: no chip and ink, before and after', async () => {
    const { before, after, sameNode } = await acrossVerify([criticalInRange], 'obs-c');
    expect(before).toEqual({ words: null, tint: 'text-ink', text: '4.2' });
    expect(after).toEqual(before);
    expect(sameNode).toBe(true);
  });

  // (b) A pin on the old code too: the flag is the only evidence, and Verify keeps it.
  it('(b) H with no numeric range: "Above the report\'s range" and attention, before and after', async () => {
    const { before, after } = await acrossVerify([highNoRange], 'obs-h');
    expect(before).toEqual({ words: "Above the report's range", tint: 'text-status-attention', text: '0.08' });
    expect(after).toEqual(before);
  });

  // (c) RED on the old code: getStatusColor compared the raw flag, so "(H)" was ink while the chip said above.
  it('(c) "(H)" reads as attention, as the chip says', async () => {
    const { before, after } = await acrossVerify([bracketHigh], 'obs-p');
    expect(before).toEqual({ words: "Above the report's range", tint: 'text-status-attention', text: '0.08' });
    expect(after).toEqual(before);
  });

  // (d) RED on the old code: ink before Verify, attention after (the server then stored H).
  it('(d) no flag, 130 over ref_high 100: the same chip and attention, before and after', async () => {
    const { before, after } = await acrossVerify([ldlUnflagged], 'obs-4');
    expect(before).toEqual({ words: "Above the report's range", tint: 'text-status-attention', text: '130' });
    expect(after).toEqual(before);
  });

  // (e) RED on the old code: "In range" appeared after Verify, when the stored N was recalculated away.
  it('(e) flag N, 4.2 inside the range: no chip before and none after', async () => {
    const { before, after } = await acrossVerify([normalWordInRange], 'obs-n');
    expect(before).toEqual({ words: null, tint: 'text-ink', text: '4.2' });
    expect(after).toEqual(before);
  });

  // (f) RED on the old code: ink before (flag N), attention after (stored H).
  it('(f) flag N, 130 over 100: above the range both times, and the stored flag becomes H', async () => {
    const { before, after } = await acrossVerify([normalWordHigh], 'obs-nh');
    expect(before).toEqual({ words: "Above the report's range", tint: 'text-status-attention', text: '130' });
    expect(after).toEqual(before);
    expect((state.observations as Row[]).find((row) => row.id === 'obs-nh')?.flag).toBe('H');
  });

  // Blind spot: it pins the mock to the backend rules above; the backend itself is HC-VKF's. Without it, a mock
  // that erased every flag would make (a) and (b) fail for the wrong reason.
  it('the verify mock keeps CRITICAL and H, and recalculates N and no flag', () => {
    const base = { ref_low: 3.5, ref_high: 5.1, user_verified: false };
    expect(verifyLikeApi({ ...base, id: 'x', value: 4.2, flag: 'CRITICAL', is_abnormal: true }).flag).toBe('CRITICAL');
    expect(verifyLikeApi({ ...base, id: 'x', value: 4.2, ref_low: null, ref_high: null, flag: 'H', is_abnormal: true }).flag).toBe('H');
    expect(verifyLikeApi({ ...base, id: 'x', value: 4.2, flag: 'N', is_abnormal: false }).flag).toBeNull();
    expect(verifyLikeApi({ ...base, id: 'x', value: 9, flag: null, is_abnormal: false }).flag).toBe('H');
  });
});

describe('HC-UIREV-002: verifying flips the marker from pencil to ink and the chip to checked by you', () => {
  async function verifyGlucose(user: ReturnType<typeof userEvent.setup>) {
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

const reportDoc = { id: 'doc-1', doc_type: 'lab_report', source: 'report.pdf', status: 'parsed' };

describe('held rows follow reprocess (L0 ruling on review round 3, finding 2)', () => {
  const REVIEW_ALL = '/verify?doc=doc-1&mode=all';
  const inkOf = (id: string) => rowOf(id)?.querySelector('[data-ink-marker]') as HTMLElement | null;
  const rowIds = () =>
    Array.from(document.querySelectorAll('tr[id^="observation-row-"]')).map((tr) => tr.id.replace('observation-row-', ''));

  /** POST /documents/doc-1/reprocess replaces the rows, the way api/documents.py:639-641 does. */
  function mockReprocess(replacement: () => unknown[]) {
    const verifyEndpoint = vi.mocked(api.apiPost).getMockImplementation()!;
    vi.mocked(api.apiPost).mockImplementation(async (url: string, body?: unknown) => {
      if (url === '/documents/doc-1/reprocess') {
        state.observations = replacement();
        return {};
      }
      return verifyEndpoint(url, body);
    });
  }

  // RED on the old code: the held copy of obs-1 came back as a row the record no longer has. Blind spot: the
  // mock deletes and re-creates rows with new ids; a server that kept the ids is the next test.
  it('Retry extraction replaces the rows, and a verified row that is gone does not come back as a ghost', async () => {
    window.history.pushState({}, '', REVIEW_ALL);
    state.documents = [reportDoc];
    mockReprocess(() => [
      { ...glucose, id: 'obs-new-1' },
      { ...hba1c, id: 'obs-new-2' },
    ]);
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(inkOf('obs-1')).toHaveAttribute('data-state', 'ink'));

    const retry = await screen.findByRole('button', { name: 'Retry extraction' });
    await waitFor(() => expect(retry).toBeEnabled());
    await user.click(retry);
    await waitFor(() => expect(rowOf('obs-new-1')).not.toBeNull());
    expect(document.getElementById('observation-row-obs-1')).toBeNull();
    expect(rowIds()).toEqual(['obs-new-1', 'obs-new-2']);
  });

  // RED on the old code: the held copy won over the server's row, so the page kept "Checked by you" and 95
  // beside a record that says 91 and unchecked. Blind spot: the same ids, so only the held map decides.
  it('Retry extraction clears the held rows, so the server\'s row is what shows', async () => {
    window.history.pushState({}, '', REVIEW_ALL);
    state.documents = [reportDoc];
    mockReprocess(() => [{ ...glucose, value: 91, user_verified: false }, hba1c]);
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(inkOf('obs-1')).toHaveAttribute('data-state', 'ink'));

    const retry = await screen.findByRole('button', { name: 'Retry extraction' });
    await waitFor(() => expect(retry).toBeEnabled());
    await user.click(retry);
    await waitFor(() => expect(rowOf('obs-1')).toHaveTextContent('91'));
    expect(inkOf('obs-1')).toHaveAttribute('data-state', 'pencil');
    expect(rowOf('obs-1').querySelector('[data-state="not-checked"]')).not.toBeNull();
  });

  // RED on the old code: the held row won even after the server returned the row verified, with other numbers.
  // Blind spot: the mock's POST answer and its next GET disagree on purpose (a second device edited it).
  it('once the fetched row is verified it wins over the held copy', async () => {
    window.history.pushState({}, '', REVIEW_ALL);
    vi.mocked(api.apiPost).mockImplementation(async () => {
      state.observations = [{ ...glucose, value: 99, user_verified: true }, hba1c, ferritin, ldlUnflagged];
      return { ...glucose, user_verified: true };
    });
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(rowOf('obs-1')).toHaveTextContent('99'));
    expect(rowOf('obs-1')).not.toHaveTextContent('95');
    expect(inkOf('obs-1')).toHaveAttribute('data-state', 'ink');
  });

  // Blind spot: one row on the default list; the order test above covers several.
  it('on the default list a verified row the server dropped is still held (it is not a ghost there)', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(vi.mocked(api.apiGet).mock.calls.filter(([url]) => url === '/observations/').length).toBeGreaterThan(1));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(inkOf('obs-1')).toHaveAttribute('data-state', 'ink');
  });
});

describe('the end of the queue shows while the last row is held as ink (L0 ruling on review round 3, finding 3)', () => {
  const attentionDoc = { id: 'doc-2', doc_type: 'lab_report', source: 'scan.pdf', status: 'extraction_failed' };
  const markAll = () => screen.getByRole('button', { name: 'Mark All Verified' });

  async function verifyOnlyRow() {
    state.observations = [glucose];
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(rowOf('obs-1').querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'ink'));
    await waitFor(() => expect(vi.mocked(api.apiGet).mock.calls.filter(([url]) => url === '/observations/').length).toBeGreaterThan(1));
    await new Promise((resolve) => setTimeout(resolve, 50));
  }

  // RED on the old code: neither state existed while a held row kept the list non-empty. Blind spot: the held
  // row stays on screen (HC-UIREV-002 needs it), so the list moves down when this block mounts; e2e measures that.
  it('verifying the last row shows "All observations verified" above the list, and the row stays', async () => {
    await verifyOnlyRow();
    const done = screen.getByText('All observations verified');
    expect(done.compareDocumentPosition(rowOf('obs-1')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(rowOf('obs-1').querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'ink');
    expect(screen.queryByText(/^\d+ items need review$/)).toBeNull();
  });

  it('with an import that needs attention it shows "Documents needing attention" above the list', async () => {
    state.documents = [attentionDoc];
    await verifyOnlyRow();
    const heading = await screen.findByText('Documents needing attention');
    expect(heading.compareDocumentPosition(rowOf('obs-1')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText('scan.pdf')).toBeInTheDocument();
    expect(screen.queryByText('All observations verified')).toBeNull();
  });

  // RED on the old code: the button stayed enabled and sent nothing.
  it('Mark All Verified is disabled once no unverified row is left', async () => {
    await verifyOnlyRow();
    expect(markAll()).toBeDisabled();
  });

  // Blind spot: Mark All's own loop (it still skips markChecked) is unchanged and not tested here.
  it('while an unverified row remains, no end-of-queue state shows and Mark All is enabled', async () => {
    state.observations = [glucose, hba1c];
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(rowOf('obs-1').querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'ink'));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByText('All observations verified')).toBeNull();
    expect(screen.getByText('1 items need review')).toBeInTheDocument();
    expect(markAll()).toBeEnabled();
  });
});

describe('the Reviewing line is reserved before /documents answers (L0 ruling on review round 3, finding 4)', () => {
  // RED on the old code: the badge mounted when /documents resolved and wrapped the actions row. Blind spot:
  // jsdom has no layout, so this pins the reserved line; e2e measures the grid top while /documents is held.
  it('the line exists while the document list is pending and holds the file name once it arrives', async () => {
    window.history.pushState({}, '', '/verify?doc=doc-1&mode=all');
    let release: () => void = () => undefined;
    state.holdDocuments = new Promise<void>((resolve) => {
      release = resolve;
    });
    state.documents = [reportDoc];
    renderWorkbench();
    await screen.findByText('Glucose');
    const line = document.querySelector('[data-reviewing-line]');
    expect(line).not.toBeNull();
    expect(line!.textContent).toBe('');
    // The other thing that mounted with the file name: Retry extraction is there from the start, and waits.
    const retry = screen.getByRole('button', { name: 'Retry extraction' });
    expect(retry).toBeDisabled();
    release();
    await waitFor(() => expect(line).toHaveTextContent('Reviewing: report.pdf'));
    await waitFor(() => expect(retry).toBeEnabled());
    expect(document.querySelector('[data-reviewing-line]')).toBe(line);
  });

  // Blind spot: the default list. It must not grow a reserved line it has no use for.
  it('the default list has no Reviewing line', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(document.querySelector('[data-reviewing-line]')).toBeNull();
  });
});

describe('HC-UIREV-006: "Show source" on a row opens the Source Trace sheet for that row', () => {
  const showSourceOf = (id: string) => within(rowOf(id)).getByRole('button', { name: 'Show source' });
  const documentGets = () =>
    vi.mocked(api.apiGet).mock.calls.filter(([url]) => url === '/documents/doc-1').length;

  // RED on the old code: the page had no Show source. Blind spot: the class names stand for the 44 px target
  // (h-11); the box itself is measured in e2e.
  it('every row with a document has a Show source button with an h-11 target; one without a document has none', async () => {
    state.observations = [glucose, { ...hba1c, doc_id: null }];
    renderWorkbench();
    await screen.findByText('Glucose');
    expect(showSourceOf('obs-1').className).toMatch(/\bh-11\b/);
    expect(within(rowOf('obs-2')).queryByRole('button', { name: 'Show source' })).toBeNull();
  });

  // Blind spot: it watches the document GET by URL. The pages and entities the page itself loads are other URLs.
  it('makes no GET /documents/<id> before the sheet is opened', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(documentGets()).toBe(0);
    const user = userEvent.setup();
    await user.click(showSourceOf('obs-1'));
    await screen.findByRole('dialog', { name: 'Source for Glucose' });
    await waitFor(() => expect(documentGets()).toBe(1));
  });

  // Blind spot: the sheet's own content is SourceTrace's test (HC-STW-002). This checks the title and that it is
  // this row's.
  it('opens "Source for <that row>", and a second row opens its own', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(showSourceOf('obs-1'));
    await screen.findByRole('dialog', { name: 'Source for Glucose' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await user.click(showSourceOf('obs-2'));
    await screen.findByRole('dialog', { name: 'Source for Hemoglobin A1c' });
    expect(screen.queryByRole('dialog', { name: 'Source for Glucose' })).toBeNull();
  });

  // Radix portals bubble through the React tree, so a click on the trigger or inside the sheet would reach the row's
  // onClick. Blind spot: selection is read from the row's highlight class and the preview text; the page image
  // request is e2e's.
  it('opening the sheet and clicking inside it never selects the row', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(showSourceOf('obs-1'));
    const dialog = await screen.findByRole('dialog', { name: 'Source for Glucose' });
    expect(rowOf('obs-1').className).not.toMatch(/bg-accent-subtle/);
    await user.click(within(dialog).getByRole('heading', { name: 'Source for Glucose' }));
    await user.click(within(dialog).getByText('Excerpt'));
    expect(rowOf('obs-1').className).not.toMatch(/bg-accent-subtle/);
    expect(screen.getByText('Select a row to preview the source document location')).toBeInTheDocument();
  });

  // Blind spot: Radix returns focus to the trigger it knows; a trigger that unmounted would not be caught here.
  it('Escape closes the sheet and focus returns to Show source', async () => {
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    const trigger = showSourceOf('obs-1');
    await user.click(trigger);
    await screen.findByRole('dialog', { name: 'Source for Glucose' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  // Blind spot: the button is a click target only; the row's other buttons keep their own tests.
  it('Show source does not break the row: Edit, Verify and Expand are still there', async () => {
    renderWorkbench();
    await screen.findByText('Glucose');
    for (const name of ['Edit value', 'Verify observation', 'Expand details', 'Show source']) {
      expect(within(rowOf('obs-1')).getByRole('button', { name })).toBeInTheDocument();
    }
  });
});

/**
 * "It matches, mark as checked" inside the Source Trace sheet on the default /verify (L0 ruling 6602430522).
 * The sheet verifies through SourceTrace's own mutation, so the page's Verify handler never runs. Without a hold
 * the refetch drops the row (needs_verification), the open sheet unmounts, and there is no ink.
 */
describe('HC-UIREV-006 and HC-UIREV-002: verifying from the Source Trace sheet on the default /verify', () => {
  const sheetGlucose = { ...glucose, source_page: 1 };
  const sheetPotassium = { ...criticalInRange, source_page: 1 };
  // One matching line per analyte, so each sheet has an excerpt and the button is enabled.
  const reportPage = [
    { page_number: 1, text: 'Glucose 95 mg/dL 70-100\nPotassium 4.2 mmol/L 3.5-5.1', has_tables: false },
  ];
  const MARK = 'It matches, mark as checked';
  const CHECKED_TEXT = 'You have marked this value as checked.';

  function deferred() {
    let release: () => void = () => undefined;
    const promise = new Promise<void>((resolve) => {
      release = resolve;
    });
    return { promise, release };
  }

  // Reads through document, not within(): while the sheet is open Radix hides the page behind it from the a11y tree.
  const inkState = (id: string) =>
    document.getElementById(`observation-row-${id}`)?.querySelector('[data-ink-marker]')?.getAttribute('data-state') ??
    'row is gone';
  const chipStateOf = (id: string) =>
    document
      .getElementById(`observation-row-${id}`)
      ?.querySelector('[data-state="not-checked"], [data-state="checked-by-you"]')
      ?.getAttribute('data-state') ?? 'row is gone';
  const rangeWordsOf = (id: string) =>
    document.getElementById(`observation-row-${id}`)?.querySelector('[data-state$="-range"]')?.textContent ?? null;
  const valueNodeOf = (id: string) =>
    document.getElementById(`observation-row-${id}`)?.querySelector('span[data-t0].font-mono') ?? null;
  const tintOf = (id: string) =>
    ['text-status-attention', 'text-status-caution', 'text-ink'].find((cls) => valueNodeOf(id)?.classList.contains(cls));
  const observationGets = () => vi.mocked(api.apiGet).mock.calls.filter(([url]) => url === '/observations/').length;
  const verifyPosts = () => vi.mocked(api.apiPost).mock.calls.filter(([url]) => /\/verify$/.test(String(url))).length;
  const toastMessages = () => vi.mocked(notify).mock.calls.map(([toast]) => (toast as { message: string }).message);
  const pause = (ms = 50) => new Promise((resolve) => setTimeout(resolve, ms));

  beforeEach(() => {
    state.observations = [sheetGlucose, hba1c, ferritin, ldlUnflagged];
    state.pages = reportPage;
  });

  /** Opens the sheet from the row's Show source, and waits until the excerpt is on screen and the button is enabled. */
  async function openSheet(user: ReturnType<typeof userEvent.setup>, id = 'obs-1', name = 'Glucose') {
    const trigger = within(rowOf(id)).getByRole('button', { name: 'Show source' });
    await user.click(trigger);
    const dialog = await screen.findByRole('dialog', { name: `Source for ${name}` });
    await within(dialog).findByText('This is what your report states.');
    const button = within(dialog).getByRole('button', { name: MARK });
    await waitFor(() => expect(button).toBeEnabled());
    return { trigger, dialog, button };
  }

  async function settled(queryClient: { isFetching: () => number }) {
    await waitFor(() => expect(queryClient.isFetching()).toBe(0));
    await pause();
  }

  // RED on the old code: the refetch dropped the row and unmounted the sheet, and nothing was held. Blind spot: the
  // mocks answer in the order this test sets; a real browser's network order is the "order" tests below, by gate.
  it('the row stays, held, with its ink; the sheet stays open and says it is checked; the value shows throughout', async () => {
    const user = userEvent.setup();
    const { queryClient } = renderWorkbench();
    await screen.findByText('Glucose');
    const { trigger, dialog, button } = await openSheet(user);
    expect(inkState('obs-1')).toBe('pencil');
    const before = observationGets();
    await user.click(button);
    await waitFor(() => expect(inkState('obs-1')).toBe('ink'));
    await waitFor(() => expect(observationGets()).toBeGreaterThan(before));
    await settled(queryClient);
    // The refetch (needs_verification) no longer has obs-1: the held copy is what is on screen.
    expect(inkState('obs-1')).toBe('ink');
    expect(chipStateOf('obs-1')).toBe('checked-by-you');
    expect(valueNodeOf('obs-1')).toHaveTextContent('95');
    // The same sheet node, still open, and it shows the checked state in place of the button.
    expect(dialog.isConnected).toBe(true);
    expect(screen.getByRole('dialog', { name: 'Source for Glucose' })).toBe(dialog);
    expect(within(dialog).getByText(CHECKED_TEXT)).toBeInTheDocument();
    expect(within(dialog).queryByRole('button', { name: MARK })).toBeNull();
    // Closing it does not take the row away: the normal hold rule.
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(inkState('obs-1')).toBe('ink');
    expect(valueNodeOf('obs-1')).toHaveTextContent('95');
    expect(rowOf('obs-1').contains(trigger)).toBe(true);
  });

  // Order (a). Blind spot: the hold is a deferred promise standing in for a slow GET. Real timing is not tested.
  it('(a) order: the invalidation refetch answers only after the POST has resolved, and the row survives it', async () => {
    const user = userEvent.setup();
    const { queryClient } = renderWorkbench();
    await screen.findByText('Glucose');
    const { dialog, button } = await openSheet(user);
    const refetch = deferred();
    state.holdObservations = refetch.promise;
    const before = observationGets();
    await user.click(button);
    // The POST has answered and its refetch is in flight but held: only onVerified can have put the ink here.
    await waitFor(() => expect(observationGets()).toBeGreaterThan(before));
    expect(verifyPosts()).toBe(1);
    await waitFor(() => expect(inkState('obs-1')).toBe('ink'));
    expect(within(dialog).getByText(CHECKED_TEXT)).toBeInTheDocument();
    // Now the refetch answers, without the row.
    refetch.release();
    await settled(queryClient);
    expect(inkState('obs-1')).toBe('ink');
    expect(dialog.isConnected).toBe(true);
    expect(within(dialog).getByText(CHECKED_TEXT)).toBeInTheDocument();
    expect(toastMessages()).toHaveLength(1);
  });

  // RED on the old code (the prop did not exist, so the sheet's failure had no page effect to compare). A failure
  // must never show checked. Blind spot: one 500 from the mocked api module; a network error takes the same path.
  it('a failed verify from the sheet: no hold, no ink, nothing says checked, no toast, and the sheet shows its own error', async () => {
    vi.mocked(api.apiPost).mockRejectedValue(new api.ApiError(500, 'Internal Server Error', 'could not save'));
    const user = userEvent.setup();
    const { queryClient } = renderWorkbench();
    await screen.findByText('Glucose');
    const { dialog, button } = await openSheet(user);
    await user.click(button);
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('It could not be marked as checked. Try again.');
    // A refetch afterwards: the server never stored anything, so the row is the same unverified row.
    await queryClient.invalidateQueries({ queryKey: ['observations'] });
    await settled(queryClient);
    expect(inkState('obs-1')).toBe('pencil');
    expect(chipStateOf('obs-1')).toBe('not-checked');
    expect(rowOf('obs-1').textContent).not.toMatch(/checked by you/i);
    expect(within(dialog).queryByText(CHECKED_TEXT)).toBeNull();
    expect(within(dialog).getByRole('button', { name: MARK })).toBeEnabled();
    expect(within(dialog).getByRole('alert')).toBeInTheDocument();
    expect(notify).not.toHaveBeenCalled();
  });

  // RED on a page that announces too: markChecked sets justChecked, whose effect is a second notify beside the sheet's.
  // Blind spot: notify is mocked and counted; the toast's own rendering and a toast arriving after this window are not.
  it('exactly one toast across the whole flow, including after the refetch settles and the sheet closes', async () => {
    const user = userEvent.setup();
    const { queryClient } = renderWorkbench();
    await screen.findByText('Glucose');
    const { button } = await openSheet(user);
    await user.click(button);
    await waitFor(() => expect(notify).toHaveBeenCalled());
    await settled(queryClient);
    expect(notify).toHaveBeenCalledTimes(1);
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await pause(100);
    expect(notify).toHaveBeenCalledTimes(1);
    expect(toastMessages()[0]).toMatch(/Glucose.* is now marked as checked$/);
    expect(vi.mocked(notify).mock.calls[0][0]).toMatchObject({ still: true });
  });

  // Blind spot: Radix hands focus back to the trigger it was opened from. The page's own focus code
  // (focusEditAfterVerifyRef) must not run on this path, because focus belongs to the sheet.
  it('focus returns to "Show source" when the sheet closes, not to Edit or the body', async () => {
    const user = userEvent.setup();
    const { queryClient } = renderWorkbench();
    await screen.findByText('Glucose');
    const { trigger, button } = await openSheet(user);
    await user.click(button);
    await waitFor(() => expect(inkState('obs-1')).toBe('ink'));
    await settled(queryClient);
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(within(rowOf('obs-1')).getByRole('button', { name: 'Edit value' })).not.toHaveFocus();
  });

  // VERIFY-FLAG-WORDS. The POST answer must differ from the copy the row had, or a page that recomputes (or reuses the
  // old copy) could not be told from one that reads the answer. Blind spot: the real API echoes the stored flag; a
  // response that differs from the row is a contrivance that only tells the two sources apart.
  it.each([
    ['L before, H in the response', 'L', 'H', "Below the report's range", "Above the report's range", 'text-status-attention'],
    ['H before, CRITICAL in the response', 'H', 'CRITICAL', "Above the report's range", null, 'text-ink'],
  ])(
    'the held row reads the flag the server answered with (%s)',
    async (_label, copyFlag, responseFlag, wordsBefore, wordsAfter, tintAfter) => {
      const copy = { ...sheetPotassium, flag: copyFlag };
      state.observations = [sheetGlucose, copy];
      vi.mocked(api.apiPost).mockImplementation(async () => {
        const saved = { ...copy, flag: responseFlag, is_abnormal: true, user_verified: true };
        state.observations = [sheetGlucose, saved];
        return saved;
      });
      const user = userEvent.setup();
      const { queryClient } = renderWorkbench();
      await screen.findByText('Potassium');
      expect(rangeWordsOf('obs-c')).toBe(wordsBefore);
      const { button } = await openSheet(user, 'obs-c', 'Potassium');
      await user.click(button);
      await waitFor(() => expect(inkState('obs-c')).toBe('ink'));
      await settled(queryClient);
      expect(rangeWordsOf('obs-c')).toBe(wordsAfter);
      expect(tintOf('obs-c')).toBe(tintAfter);
      expect(valueNodeOf('obs-c')).toHaveTextContent('4.2');
    }
  );

  // Not RED on the old code, by design: it pins today's behaviour for the callers that do not pass the prop
  // (CitationTooltip, InterpretedResultCard). Blind spot: it renders SourceTrace alone; those two callers' own
  // tests are source-trace-wire and ui-provenance.
  it('a SourceTrace with no onVerified still verifies, shows the checked state, and toasts once', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({ ...sheetGlucose, user_verified: true });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <SourceTrace
            observation={sheetGlucose as unknown as Observation}
            excerptLines={['Glucose 95 mg/dL 70-100']}
            matchIndex={0}
            open
            onOpenChange={() => undefined}
          />
        </BrowserRouter>
      </QueryClientProvider>
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: MARK }));
    expect(await screen.findByText(CHECKED_TEXT)).toBeInTheDocument();
    await pause();
    expect(verifyPosts()).toBe(1);
    expect(toastMessages()).toHaveLength(1);
    expect(toastMessages()[0]).toMatch(/Glucose.* is now marked as checked$/);
  });
});

describe('Verify commit: focus, and a failed Verify (review round 3, findings 7 and 9)', () => {
  const editOf = (id: string) => within(rowOf(id)).getByRole('button', { name: 'Edit value' });

  // Finding 7. RED on the old code: the Verify button unmounted with the commit and focus fell to <body>.
  // Blind spot: jsdom's focus; whether a screen reader announces the move is not tested.
  it('after a keyboard Verify, focus moves to that row\'s Edit button, without scrolling', async () => {
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }).focus();
    focus.mockClear();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(editOf('obs-1')).toHaveFocus());
    const moved = focus.mock.contexts.findIndex((node) => node === editOf('obs-1'));
    expect(moved, 'Edit was focused by the page').toBeGreaterThanOrEqual(0);
    expect(focus.mock.calls[moved][0]).toEqual({ preventScroll: true });
    focus.mockRestore();
  });

  // Blind spot: the user moved on during the save. Focus that already went elsewhere is left alone.
  it('does not take focus that the user already moved to another field', async () => {
    let finish: (saved: unknown) => void = () => undefined;
    vi.mocked(api.apiPost).mockImplementation(
      () => new Promise((resolve) => { finish = resolve; })
    );
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    const other = within(rowOf('obs-2')).getByRole('button', { name: 'Expand details' });
    other.focus();
    state.observations = [{ ...glucose, user_verified: true }, hba1c, ferritin, ldlUnflagged];
    finish({ ...glucose, user_verified: true });
    await waitFor(() => expect(rowOf('obs-1').querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'ink'));
    expect(other).toHaveFocus();
  });

  // Finding 9. RED on the old code: the rejection was unhandled (vitest fails the run on it) and nothing told the user.
  // Blind spot: a 500 from the mocked api module; the ApiError wording belongs to services/api.
  it('a failed Verify shows one still error toast, never "marked as checked", and the row stays unchecked', async () => {
    vi.mocked(api.apiPost).mockRejectedValue(new api.ApiError(500, 'Internal Server Error', 'could not save'));
    const user = userEvent.setup();
    renderWorkbench();
    await screen.findByText('Glucose');
    await user.click(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' }));
    await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
    expect(vi.mocked(notify).mock.calls[0][0]).toEqual({
      message: 'Could not mark Glucose as checked. Try again.',
      still: true,
    });
    expect(rowOf('obs-1').querySelector('[data-ink-marker]')).toHaveAttribute('data-state', 'pencil');
    expect(rowOf('obs-1').querySelector('[data-state="not-checked"]')).not.toBeNull();
    // Verify is usable again, and the row did not enter the held list.
    expect(within(rowOf('obs-1')).getByRole('button', { name: 'Verify observation' })).toBeEnabled();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(notify).toHaveBeenCalledTimes(1);
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

  // L0 ruling on review round 3 (finding 5). RED on the old code: sm:table-cell and sm:whitespace-nowrap sized the
  // Review column by its content, so a chip appearing pushed the page wider and re-wrapped the value.
  // Blind spot: class names. The 1024, 1280 and 1440 no-scroll check and the rects are e2e's.
  it('stacks at every width: no table-cell layout and no nowrap at sm and up', () => {
    const { container } = renderEntities();
    const html = container.innerHTML;
    expect(html).not.toMatch(/whitespace-nowrap/);
    expect(html).not.toMatch(/\bsm:table(-cell|-row|-header-group|-row-group)?\b/);
    expect(html).not.toMatch(/\bsm:max-w-xs\b/);
    const none = entityRow('e-none');
    expect(none.className).toMatch(/\bblock\b/);
    for (const td of Array.from(none.querySelectorAll(':scope > td'))) expect(td.className).toMatch(/\bblock\b/);
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
