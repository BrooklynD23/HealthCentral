/**
 * UI-PG-DOCUMENTS (HC-UIDOC-001..006 and the confidence and empty-state checks, vitest half): the Documents page.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md, "UI-PG-DOCUMENTS". The Playwright half (Gate G, the
 * stillness probe across an import and the preview Sheet, the real Radix focus checks) is
 * e2e/ui-documents.spec.ts.
 *
 * The page runs on its real hooks. Only the HTTP layer (`@/services/api`) is replaced, so a delete is a real
 * apiDelete call, an import is a real pending mutation, and `isPending` / `variables` come from React Query.
 * PageImageOverlay and the orb library are stubs: the first needs a blob URL, the second a canvas.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import * as api from '@/services/api';
import type { Document, DocumentImportResponse } from '@/services/types';
import { HIGHLIGHT_LABELS, type DocumentHighlightSummary } from '@/services/highlights';
import { DocumentInbox } from '@/pages/DocumentInbox';
import { ExtractionConfidenceBadge } from '@/components/documents/ExtractionConfidenceBadge';
import { Badge } from '@/components/ui';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/api')>()),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
  apiUpload: vi.fn(),
}));

vi.mock('@/components/PageImageOverlay', () => ({
  PageImageOverlay: ({ documentId }: { documentId: string }) => (
    <div data-testid="page-image-overlay">page image of {documentId}</div>
  ),
}));

// The library draws on a canvas, which jsdom does not provide. The stub counts mounts.
const orb = vi.hoisted(() => ({ mounts: 0, sizes: [] as unknown[] }));
vi.mock('thinking-orbs', async () => {
  const React = await import('react');
  return {
    ThinkingOrb: (props: { size?: number }) => {
      orb.mounts += 1;
      orb.sizes.push(props.size);
      return React.createElement('canvas', { 'data-testid': 'orb' });
    },
  };
});

// jsdom has no pointer-capture API, and Radix menus call it on pointerdown.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
}

const PROFILE = 'profile-123';
const originalMatchMedia = window.matchMedia;

function makeDoc(over: Partial<Document> = {}): Document {
  return {
    id: 'doc-a',
    profile_id: PROFILE,
    doc_type: 'lab_pdf',
    source: 'a.pdf',
    status: 'parsed',
    page_count: 1,
    collection_date: '2026-07-01T00:00:00',
    imported_at: '2026-07-13T09:00:00',
    parsed_at: '2026-07-13T09:00:01',
    verified_at: null,
    extraction_confidence: 0.9,
    ...over,
  };
}

function importResponse(over: Partial<DocumentImportResponse> & { doc?: Partial<Document> } = {}): DocumentImportResponse {
  const { doc, ...rest } = over;
  return {
    document: makeDoc({ id: 'new-doc', source: 'new.pdf', ...doc }),
    observations_extracted: 3,
    needs_verification: true,
    duplicate_warning: null,
    import_summary: null,
    pages_without_text: [],
    ...rest,
  };
}

let documents: Document[] = [];
let highlights: DocumentHighlightSummary[] = [];
/** While set, GET /documents waits for it (the refetch an import or a delete starts). */
let listGate: Promise<void> | null = null;
let listFails = false;
/** While set, GET /documents/highlights/summary waits for it, or fails. */
let summaryGate: Promise<void> | null = null;
let summaryFails = false;
/** What GET /pinboards answers. */
let pinboards: Array<{ id: string; name: string; created_at: string; updated_at: string }> = [];
/** How many GET /documents have answered with the list. */
let listAnswers = 0;

/** A gate the test opens by calling the returned function. */
function gate(): { wait: Promise<void>; open: () => void } {
  let open!: () => void;
  const wait = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { wait, open };
}

/** Resolvers for the requests the test keeps in flight. */
let finishUpload: (value: DocumentImportResponse) => void = () => {};
let finishReprocess: (value: DocumentImportResponse) => void = () => {};

const apiGet = vi.mocked(api.apiGet);
const apiPost = vi.mocked(api.apiPost);
const apiDelete = vi.mocked(api.apiDelete);
const apiUpload = vi.mocked(api.apiUpload);

function holdUpload() {
  apiUpload.mockImplementation(
    () =>
      new Promise((resolve) => {
        finishUpload = resolve as (value: DocumentImportResponse) => void;
      }) as never
  );
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

function renderInbox() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/inbox']}>
        <DocumentInbox />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

/** The list is loaded when the first row heading is on screen. */
async function renderLoaded(firstName = 'a.pdf') {
  const view = renderInbox();
  await screen.findByRole('heading', { name: firstName });
  return view;
}

/** The row of the document called `name`: heading, then its text column, then the row. */
function rowOf(name: string): HTMLElement {
  const heading = screen.getByRole('heading', { name });
  return heading.parentElement!.parentElement as HTMLElement;
}

/** The container of a row's actions: the parent of its View document button. */
function actionsOf(row: HTMLElement): HTMLElement {
  return within(row).getByRole('button', { name: 'View document' }).parentElement as HTMLElement;
}

function upload(user: ReturnType<typeof userEvent.setup>, name = 'big-scan.pdf') {
  return user.upload(
    screen.getByLabelText(/upload medical documents/i),
    new File(['%PDF-1.4'], name, { type: 'application/pdf' })
  );
}

async function openRowMenu(user: ReturnType<typeof userEvent.setup>, row: HTMLElement) {
  await user.click(within(row).getByRole('button', { name: 'More options' }));
}

beforeEach(() => {
  documents = [makeDoc()];
  highlights = [];
  listGate = null;
  listFails = false;
  summaryGate = null;
  summaryFails = false;
  listAnswers = 0;
  pinboards = [];
  orb.mounts = 0;
  orb.sizes = [];
  setReducedMotion(false);
  apiGet.mockImplementation((async (path: string) => {
    if (path.startsWith('/documents/highlights/summary')) {
      if (summaryGate) await summaryGate;
      if (summaryFails) throw new api.ApiError(500, 'Server Error', 'summary failed');
      return highlights;
    }
    if (path.startsWith('/pinboards')) return pinboards;
    if (path.startsWith('/documents')) {
      if (listGate) await listGate;
      if (listFails) throw new api.ApiError(500, 'Server Error', 'list failed');
      listAnswers += 1;
      return documents;
    }
    throw new Error(`unmocked GET ${path}`);
  }) as never);
  apiPost.mockResolvedValue({} as never);
  apiDelete.mockResolvedValue(undefined as never);
  apiUpload.mockResolvedValue(importResponse() as never);
  useAuthStore.getState().setAuth({ token: 'test-token', profileId: PROFILE, profileName: 'Test Profile' });
});

afterEach(() => {
  cleanup();
  window.matchMedia = originalMatchMedia;
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// HC-UIDOC-001: rows are still, and their actions are always there.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-001 rows and actions', () => {
  it('HC-UIDOC-001: the row actions carry no opacity-0, invisible or hover-reveal class', async () => {
    // Would not notice: a hide set from a stylesheet, an inline style, or a parent. jsdom loads no Tailwind, so
    // this is a class contract; the computed opacity with the mouse away is e2e HC-UIDOC-001.
    // RED today: the container has sm:[@media(hover:hover)]:opacity-0 sm:group-hover:opacity-100.
    await renderLoaded();
    const tokens = actionsOf(rowOf('a.pdf')).className.split(/\s+/);
    expect(tokens.filter((t) => /(^|:)(opacity-0|invisible|hidden)$/.test(t))).toEqual([]);
    expect(tokens.filter((t) => t.includes('group-hover'))).toEqual([]);
  });

  it('HC-UIDOC-001: Tab reaches Add to pinboard, View document and More options of a row in order', async () => {
    // Would not notice: a button with tabindex -1, or one that is display:none. It does not see CSS opacity, which
    // the e2e test covers. The order check stops a reorder that hides View document behind the menu.
    const user = userEvent.setup();
    await renderLoaded();
    const row = rowOf('a.pdf');
    const reached: string[] = [];
    for (let i = 0; i < 30 && reached.length < 3; i++) {
      await user.tab();
      const active = document.activeElement as HTMLElement | null;
      if (active && row.contains(active)) reached.push(active.getAttribute('aria-label') ?? '');
    }
    expect(reached).toEqual(['Add to pinboard', 'View document', 'More options']);
  });

  it('HC-UIDOC-001: a row has no entrance style (no m.div variants, M0)', async () => {
    // Would not notice: an entrance applied by a class instead of a style. The e2e stillness probe covers that.
    // RED today: the m.div starts with opacity 0 and translateY(12px) as inline style.
    await renderLoaded();
    const style = rowOf('a.pdf').getAttribute('style') ?? '';
    expect(style).not.toMatch(/opacity|transform/);
    expect(rowOf('a.pdf').parentElement?.getAttribute('style') ?? '').not.toMatch(/opacity|transform/);
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-002: at most two tags, no raw identifier.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-002 chips and raw identifiers', () => {
  const FIVE = {
    abnormal_value: 2,
    medication_started: 1,
    follow_up_needed: 1,
    low_confidence_extraction: 1,
    needs_verification: 3,
  } as const;

  it('HC-UIDOC-002: a row with five highlight types shows at most 2 tag chips and one "+3"', async () => {
    // Would not notice: a status word or a confidence word that grows into a third chip. By the brief's reading
    // those are not counted; the tag chips are the highlight labels. A chip that is hidden by CSS is counted.
    // RED today: max={4} shows four tags and "+1".
    highlights = [{ doc_id: 'doc-a', counts: { ...FIVE } }];
    await renderLoaded();
    const row = rowOf('a.pdf');
    const labels = new Set(Object.values(HIGHLIGHT_LABELS));
    const tags = within(row).queryAllByText((_, el) => el?.tagName === 'SPAN' && labels.has(el.textContent?.trim().replace(/ ×\d+$/, '') ?? ''));
    expect(tags.length).toBeLessThanOrEqual(2);
    expect(tags.length).toBe(2);
    expect(within(row).getByText('+3')).toBeInTheDocument();
  });

  it.each([
    ['lab_pdf', 'Lab Report'],
    ['lab_report', 'Lab Report'],
    ['lab_pdf_scanned', 'Scanned Lab Report'],
    ['lab_image', 'Lab Image'],
    ['lab_csv', 'Lab Spreadsheet'],
    ['fhir_bundle', 'Health Record (FHIR)'],
    ['something_new_v2', 'Document'],
  ])('HC-UIDOC-002: doc_type %s reads "%s", once, and never as the raw identifier', async (docType, words) => {
    // Would not notice: an identifier that reaches the page through a title or aria-label rather than text
    // (the row's whole text and every aria-label and title in it are checked). RED today: raw ids print twice.
    documents = [makeDoc({ id: 'doc-t', source: 'typed.pdf', doc_type: docType })];
    await renderLoaded('typed.pdf');
    const row = rowOf('typed.pdf');
    expect(row.textContent).not.toContain(docType);
    const attrs = Array.from(row.querySelectorAll('[aria-label],[title]')).map(
      (el) => `${el.getAttribute('aria-label') ?? ''} ${el.getAttribute('title') ?? ''}`
    );
    expect(attrs.join(' ')).not.toContain(docType);
    expect(within(row).getAllByText(words)).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-003: a document being read shows the beam and a status text.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-003 processing card', () => {
  it('HC-UIDOC-003: while an import is in flight one beam card holds the file name and "Reading <name>"', async () => {
    // Would not notice: a beam that runs but sits on the wrong element (the whole page), or an orb with no text.
    // The in-flight check is real: the mutation stays pending until finishUpload runs.
    // RED today: no beam, no status text, no orb.
    holdUpload();
    const user = userEvent.setup();
    const { container } = await renderLoaded();
    expect(container.querySelector('.beam-border[data-active="true"]')).toBeNull();

    await upload(user, 'big-scan.pdf');
    const reading = await screen.findByText('Reading big-scan.pdf');
    expect(reading).toHaveAttribute('role', 'status');
    const beams = container.querySelectorAll('.beam-border[data-active="true"]');
    expect(beams).toHaveLength(1);
    expect(beams[0]).toHaveAttribute('data-active', 'true');
    expect(beams[0]).toContainElement(reading);
    expect(within(beams[0] as HTMLElement).getByText('big-scan.pdf')).toBeInTheDocument();
    expect(await screen.findByTestId('orb')).toBeInTheDocument();
    expect(orb.sizes).toContain(20);

    await act(async () => finishUpload(importResponse({ doc: { source: 'big-scan.pdf' } })));
    await waitFor(() => expect(container.querySelector('.beam-border[data-active="true"]')).toBeNull());
    expect(screen.queryByText('Reading big-scan.pdf')).not.toBeInTheDocument();
  });

  it('HC-UIDOC-003: a stored status of pending or pending_ocr is not a running process: no beam, no orb', async () => {
    // Would not notice: a beam driven by something other than status (it checks the idle page only). The S2 rule
    // is that the beam shows a real process, and a stored status does not prove one.
    // GREEN today and kept green: the pin that stops the card being driven from the list.
    documents = [
      makeDoc({ id: 'p1', source: 'queued.pdf', status: 'pending' }),
      makeDoc({ id: 'p2', source: 'scan.pdf', status: 'pending_ocr' }),
    ];
    const { container } = await renderLoaded('queued.pdf');
    expect(container.querySelector('.beam-border[data-active="true"]')).toBeNull();
    expect(screen.queryByTestId('orb')).not.toBeInTheDocument();
    expect(screen.queryByText(/^Reading /)).not.toBeInTheDocument();
    expect(orb.mounts).toBe(0);
  });

  it('HC-UIDOC-003: under reduced motion the border is a static frame and the text stays', async () => {
    // Would not notice: a frame whose colour is wrong; the stylesheet is checked by HC-UISK-001, not here.
    // RED today: there is no card.
    setReducedMotion(true);
    holdUpload();
    const user = userEvent.setup();
    const { container } = await renderLoaded();
    await upload(user, 'big-scan.pdf');
    const reading = await screen.findByText('Reading big-scan.pdf');
    const beam = container.querySelector('.beam-border') as HTMLElement;
    expect(beam).toHaveAttribute('data-motion', 'reduced');
    expect(beam.querySelector('.beam-border__frame')).not.toBeNull();
    expect(beam.querySelector('.beam-border__beam')).toBeNull();
    expect(reading).toBeVisible();
    await act(async () => finishUpload(importResponse()));
  });

  it('HC-UIDOC-003: a reprocess in flight shows the same card for that document, and only until it ends', async () => {
    // Would not notice: a card that names the wrong document when two rows exist (the second row is the one
    // reprocessed). RED today: no card.
    documents = [
      makeDoc({ id: 'd1', source: 'first.pdf', status: 'verified' }),
      makeDoc({ id: 'd2', source: 'second-scan.pdf', status: 'pending_ocr' }),
    ];
    apiPost.mockImplementation(
      () =>
        new Promise((resolve) => {
          finishReprocess = resolve as (value: DocumentImportResponse) => void;
        }) as never
    );
    const user = userEvent.setup();
    const { container } = await renderLoaded('first.pdf');
    await openRowMenu(user, rowOf('second-scan.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /continue ocr \/ retry extraction/i }));

    expect(await screen.findByText('Reading second-scan.pdf')).toBeInTheDocument();
    expect(screen.queryByText('Reading first.pdf')).not.toBeInTheDocument();
    expect(apiPost).toHaveBeenCalledWith('/documents/d2/reprocess');
    expect(container.querySelectorAll('.beam-border[data-active="true"]')).toHaveLength(1);

    await act(async () => finishReprocess(importResponse()));
    await waitFor(() => expect(container.querySelector('.beam-border[data-active="true"]')).toBeNull());
  });

  it('HC-UIDOC-003: the drop zone has no pulse and no spinner while importing; its heading stays', async () => {
    // Would not notice: a spinner added under another class name. It looks for animate-pulse and animate-spin.
    // RED today: the icon box pulses and a Loader2 spins.
    holdUpload();
    const user = userEvent.setup();
    const { container } = await renderLoaded();
    await upload(user);
    expect(await screen.findByRole('heading', { name: 'Importing document...' })).toBeInTheDocument();
    expect(container.querySelector('.animate-pulse, .animate-spin')).toBeNull();
    await act(async () => finishUpload(importResponse()));
  });

  it('HC-UIDOC-003: the running state is in the drop zone and the idle block keeps its place (hidden), so nothing below moves', async () => {
    // Would not notice: a height change that CSS causes. jsdom has no layout, so this reads the structure that
    // holds the height (the idle block stays in the same grid cell, hidden from sight and from the accessibility
    // tree); the e2e probe measures the rects of the rows. A processing card put back between the drop zone and
    // the list would fail the first two assertions.
    // RED before this round: the card was a separate block above the list.
    holdUpload();
    const user = userEvent.setup();
    const { container } = await renderLoaded();
    await upload(user, 'big-scan.pdf');
    const reading = await screen.findByText('Reading big-scan.pdf');
    const beam = container.querySelector('.beam-border[data-active="true"]') as HTMLElement;
    expect(within(beam).getByRole('button', { name: 'Browse Files' })).toBeInTheDocument();
    expect(screen.getByText('Recent Documents').closest('.beam-border')).toBeNull();
    expect(within(beam).getByRole('heading', { name: 'Importing document...' })).toBeInTheDocument();

    const idle = within(beam).getByText('Drag and drop files', { selector: 'h3' }).parentElement as HTMLElement;
    expect(idle).toHaveClass('invisible');
    expect(idle).toHaveAttribute('aria-hidden', 'true');
    expect(idle.parentElement).toBe((reading.closest('.col-start-1') as HTMLElement).parentElement);
    await act(async () => finishUpload(importResponse()));
    await waitFor(() => expect(idle).not.toHaveClass('invisible'));
    expect(idle).not.toHaveAttribute('aria-hidden');
  });

  it('HC-UIDOC-003: the status text wraps inside the card, even for a name with no space', async () => {
    // Would not notice: a width the test cannot measure (jsdom). It reads the wrapping classes the page passes to
    // the orb; the e2e G6 test measures scrollWidth during an import with a 127-character name at 390 and 320.
    // RED before this round: the status line could not wrap and pushed the page to 813 px wide.
    holdUpload();
    const user = userEvent.setup();
    await renderLoaded();
    await upload(user, 'a-very-long-name-without-any-space-in-it-at-all-for-the-wrap-check.pdf');
    const status = await screen.findByText(/^Reading a-very-long-name/);
    const orbRoot = status.parentElement as HTMLElement;
    expect(orbRoot.className).toContain('min-w-0');
    expect(orbRoot.className).toContain('[overflow-wrap:anywhere]');
    await act(async () => finishUpload(importResponse()));
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-004: alerts and warnings are static, never inside the beam.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-004 alerts and warnings are static', () => {
  /** An element or an ancestor that animates: an animate-* class, or an inline animation or transition. */
  function animates(el: Element): boolean {
    for (let node: Element | null = el; node; node = node.parentElement) {
      if (/(^|\s)animate-/.test(node.getAttribute('class') ?? '')) return true;
      if (/animation|transition/.test(node.getAttribute('style') ?? '')) return true;
    }
    return false;
  }

  it('HC-UIDOC-004: the import-failed alert is outside the beam, static and marked data-t0, while a second import runs', async () => {
    // Would not notice: an alert that animates through a stylesheet rule on its card class. The unit check reads
    // classes and inline style; the e2e probe samples the alert's real computed style.
    // RED today for the data-t0 mark only: the alert is already static and outside any beam.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockRejectedValueOnce(new api.ApiError(400, 'Bad Request', 'Unsupported file type'));
    await upload(user, 'bad.pdf');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Unsupported file type');

    holdUpload();
    await upload(user, 'good.pdf');
    await screen.findByText('Reading good.pdf');
    expect(document.body.querySelectorAll('.beam-border[data-active="true"]')).toHaveLength(1);
    expect(screen.getByRole('alert')).toBe(alert);
    expect(alert.closest('.beam-border')).toBeNull();
    expect(animates(alert)).toBe(false);
    expect(alert.matches('[data-t0]') || alert.querySelector('[data-t0]') !== null).toBe(true);
    await act(async () => finishUpload(importResponse()));
  });

  it('HC-UIDOC-004: the scanned-page warning and the duplicate warning are outside the beam, static, and the warning is data-t0', async () => {
    // Would not notice: the same as above for the two cards. A warning that is moved into the beam card would
    // sit inside .beam-border and fail here.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(
      importResponse({
        doc: { source: 'scan.pdf', page_count: 3 },
        pages_without_text: [2],
        duplicate_warning: { match_type: 'content_hash', document_id: 'old', title: 'prior.pdf' },
      }) as never
    );
    await upload(user, 'scan.pdf');
    const warning = await screen.findByText(/Page 2 has no readable text/);
    const duplicate = (await screen.findByText(/possible duplicate upload/i)).closest('[role="status"]') as HTMLElement;

    holdUpload();
    await upload(user, 'next.pdf');
    await screen.findByText('Reading next.pdf');
    expect(warning).toHaveAttribute('role', 'status');
    expect(warning).toHaveAttribute('data-t0');
    for (const el of [warning, duplicate]) {
      expect(el.closest('.beam-border')).toBeNull();
      expect(animates(el)).toBe(false);
    }
    await act(async () => finishUpload(importResponse()));
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-005: delete asks through an AlertDialog.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-005 delete through AlertDialog', () => {
  beforeEach(() => {
    vi.spyOn(window, 'confirm').mockImplementation(() => {
      throw new Error('window.confirm must not be called');
    });
  });

  it('HC-UIDOC-005: Delete opens an alertdialog with the sentence, and sends nothing until Remove is pressed', async () => {
    // Would not notice: a dialog that deletes on open (apiDelete is checked while it is open), or one whose Cancel
    // still deletes. Cancel is pressed first, then the whole flow runs again to Remove.
    // RED today: window.confirm is called, and the stub throws.
    const user = userEvent.setup();
    await renderLoaded();
    await openRowMenu(user, rowOf('a.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));

    const dialog = await screen.findByRole('alertdialog');
    expect(dialog).toHaveTextContent('Remove "a.pdf" from your library? This cannot be undone.');
    expect(apiDelete).not.toHaveBeenCalled();
    const cancel = within(dialog).getByRole('button', { name: 'Cancel' });
    expect(cancel).toHaveAttribute('data-alert-cancel');
    await waitFor(() => expect(cancel).toHaveFocus());

    await user.click(cancel);
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(apiDelete).not.toHaveBeenCalled();

    await openRowMenu(user, rowOf('a.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    const again = await screen.findByRole('alertdialog');
    expect(apiDelete).not.toHaveBeenCalled();
    await user.click(within(again).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledTimes(1));
    expect(apiDelete).toHaveBeenCalledWith('/documents/doc-a');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(window.confirm).not.toHaveBeenCalled();
  });

  it('HC-UIDOC-005: the dialog names the row it was opened from when two rows exist', async () => {
    // Would not notice: a target kept in a ref that is read after another row changed it; this opens the second row.
    documents = [makeDoc({ id: 'd1', source: 'one.pdf' }), makeDoc({ id: 'd2', source: 'two.pdf' })];
    const user = userEvent.setup();
    await renderLoaded('one.pdf');
    await openRowMenu(user, rowOf('two.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    const dialog = await screen.findByRole('alertdialog');
    expect(dialog).toHaveTextContent('Remove "two.pdf" from your library?');
    await user.click(within(dialog).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledWith('/documents/d2'));
    expect(apiDelete).toHaveBeenCalledTimes(1);
  });

  it('HC-UIDOC-005: after Remove, focus lands on a neighbouring row, not on <body>', async () => {
    // Would not notice: a focus that Radix puts back on a trigger it does not have (the dialog opens from a menu
    // item). Removing the LAST row sends focus to the previous row's More options; removing the first, to the next.
    // RED before this round: Remove left the focus on <body>.
    documents = [makeDoc({ id: 'd1', source: 'one.pdf' }), makeDoc({ id: 'd2', source: 'two.pdf' })];
    apiDelete.mockImplementation((async (path: string) => {
      documents = documents.filter((d) => `/documents/${d.id}` !== path);
    }) as never);
    const user = userEvent.setup();
    await renderLoaded('one.pdf');
    await openRowMenu(user, rowOf('two.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() =>
      expect(within(rowOf('one.pdf')).getByRole('button', { name: 'More options' })).toHaveFocus()
    );

    await openRowMenu(user, rowOf('one.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    // Nothing left to focus in the list: the Import Document button.
    await waitFor(() => expect(screen.getByRole('button', { name: /import document/i })).toHaveFocus());
  });

  it('HC-UIDOC-005: deleting the document that was just imported clears the "values ready to review" card', async () => {
    // Would not notice: a stale card that is only hidden. It looks for the link and the line by role and text, so a
    // card left in the DOM would be found. A failed DELETE must keep the card (the document still exists).
    // RED before this round: the card kept offering a link to a deleted document.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(importResponse({ observations_extracted: 3, doc: { id: 'new-1', source: 'fresh.pdf' } }) as never);
    documents = [makeDoc({ id: 'new-1', source: 'fresh.pdf' }), ...documents];
    await upload(user, 'fresh.pdf');
    await screen.findByRole('link', { name: '3 values ready to review' });

    apiDelete.mockRejectedValueOnce(new api.ApiError(500, 'Server Error', 'nope'));
    await openRowMenu(user, rowOf('fresh.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('link', { name: '3 values ready to review' })).toBeInTheDocument();

    documents = documents.filter((d) => d.id !== 'new-1');
    await openRowMenu(user, rowOf('fresh.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.queryByRole('link', { name: /ready to review/i })).not.toBeInTheDocument());
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-006 (vitest half): the import card and the duplicate warning commit with their row, and leave with it, so
// the rows below move once (owner INBOX-ROW-JUMP). The e2e half samples the rects at frame rate.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-006 the import card commits with its row', () => {
  const fresh = () => importResponse({ observations_extracted: 3, doc: { id: 'new-1', source: 'fresh.pdf' } });

  /** Uploads fresh.pdf with the list refetch held; returns once the import has resolved and the refetch is waiting. */
  async function importWithHeldList(user: ReturnType<typeof userEvent.setup>, response = fresh()) {
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(response as never);
    documents = [makeDoc({ id: 'new-1', source: 'fresh.pdf' }), ...documents];
    const held = gate();
    listGate = held.wait;
    await upload(user, 'fresh.pdf');
    await waitFor(() => expect(screen.queryByText('Importing document...')).not.toBeInTheDocument());
    return held;
  }

  it('HC-UIDOC-006: the card is not shown before the list has the new row, and both appear in one render', async () => {
    // Would not notice: a card that shows for a reason other than the list (the fallback test below owns that). The
    // import has resolved when "Importing document..." is gone, so the absence checked first is not a state the page
    // has not reached yet.
    // RED before this round: the card showed when the import resolved, a frame before the new row.
    const user = userEvent.setup();
    const held = await importWithHeldList(user);
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'fresh.pdf' })).not.toBeInTheDocument();
    held.open();
    await screen.findByText(/document imported: fresh\.pdf/i);
    // Found in the same render as the card: the row is already there.
    expect(screen.getByRole('heading', { name: 'fresh.pdf' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '3 values ready to review' })).toBeInTheDocument();
  });

  it('HC-UIDOC-006: a duplicate warning waits for the list the same way', async () => {
    // Would not notice: a warning that shows in the same render as the card but a render before the row; the first
    // test reads the card, this one the warning.
    const user = userEvent.setup();
    const held = await importWithHeldList(
      user,
      importResponse({
        doc: { id: 'new-1', source: 'fresh.pdf' },
        duplicate_warning: { match_type: 'content_hash', document_id: 'doc-a', title: 'a.pdf' },
      })
    );
    expect(screen.queryByText(/possible duplicate upload/i)).not.toBeInTheDocument();
    held.open();
    await screen.findByText(/possible duplicate upload/i);
    expect(screen.getByRole('heading', { name: 'fresh.pdf' })).toBeInTheDocument();
  });

  it('HC-UIDOC-011: when the list refresh fails the patient still sees the import result', async () => {
    // Would not notice: a card that appears after a delay the test does not time. Conservative first: the card is
    // there once the refetch has failed, and so is the list error.
    // RED if the card waits for the list for ever: it never shows.
    const user = userEvent.setup();
    const held = await importWithHeldList(user);
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
    listFails = true;
    held.open();
    expect(await screen.findByText(/document imported: fresh\.pdf/i)).toBeInTheDocument();
    expect(screen.getByText('Failed to load documents')).toBeInTheDocument();
  });

  it('HC-UIDOC-006: Remove keeps the card until the list drops the row, then both go in one render', async () => {
    // Would not notice: a card that waits for the list but stays after it (the old test above, "clears the values
    // ready to review card", owns that end state). The first check runs after the DELETE has resolved.
    // RED before this round: the card went when the DELETE resolved, a frame before the row.
    const user = userEvent.setup();
    (await importWithHeldList(user)).open();
    await screen.findByRole('link', { name: '3 values ready to review' });
    await openRowMenu(user, rowOf('fresh.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    const held = gate();
    listGate = held.wait;
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledTimes(1));
    await act(async () => {});
    expect(screen.getByRole('link', { name: '3 values ready to review' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'fresh.pdf' })).toBeInTheDocument();
    documents = documents.filter((d) => d.id !== 'new-1');
    held.open();
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'fresh.pdf' })).not.toBeInTheDocument());
    expect(screen.queryByRole('link', { name: /ready to review/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
  });

  it('HC-UIDOC-011: when the refresh after a Remove fails, the card for the removed document is gone', async () => {
    // Would not notice: a stale row. The list keeps its old data after a failed refetch, so the row stays; only the
    // card, which would link to a deleted document, goes.
    const user = userEvent.setup();
    (await importWithHeldList(user)).open();
    await screen.findByRole('link', { name: '3 values ready to review' });
    await openRowMenu(user, rowOf('fresh.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    listFails = true;
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.queryByRole('link', { name: /ready to review/i })).not.toBeInTheDocument());
    expect(screen.getByText('Failed to load documents')).toBeInTheDocument();
  });

  it('HC-UIDOC-006: a second import keeps the first card until the list has the second row, then swaps them in one render', async () => {
    // Would not notice: a card that is replaced by something other than the second import (the swap is read by the two
    // file names). The first import has no card to replace, so the tests above cannot see this. Read in review on a
    // production build: the old card left when the import resolved, and the rows moved up, then down again.
    // RED before this round: the old card was gone the moment the second import resolved.
    const user = userEvent.setup();
    (await importWithHeldList(user)).open();
    await screen.findByText(/document imported: fresh\.pdf/i);
    apiUpload.mockResolvedValueOnce(importResponse({ doc: { id: 'new-2', source: 'second.pdf' } }) as never);
    documents = [makeDoc({ id: 'new-2', source: 'second.pdf' }), ...documents];
    const held = gate();
    listGate = held.wait;
    await upload(user, 'second.pdf');
    await waitFor(() => expect(screen.queryByText('Importing document...')).not.toBeInTheDocument());
    await act(async () => {});
    expect(screen.getByText(/document imported: fresh\.pdf/i)).toBeInTheDocument();
    expect(screen.queryByText(/document imported: second\.pdf/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'second.pdf' })).not.toBeInTheDocument();
    held.open();
    await screen.findByText(/document imported: second\.pdf/i);
    // In the same render as the new card: the row is there and the old card is gone.
    expect(screen.getByRole('heading', { name: 'second.pdf' })).toBeInTheDocument();
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
  });

  it('HC-UIDOC-006: a retry after a failed import keeps the alert until the list has the new row, then drops it in one render', async () => {
    // Would not notice: an alert that is hidden by CSS (it looks for the role). The failed attempt resolves first, so
    // the alert is on screen before the retry starts.
    // RED before this round: the alert left when the retry resolved, a render before the row.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockRejectedValueOnce(new api.ApiError(400, 'Bad Request', 'Unsupported file type'));
    await upload(user, 'fresh.pdf');
    expect(await screen.findByRole('alert')).toHaveTextContent('Unsupported file type');
    apiUpload.mockResolvedValueOnce(fresh() as never);
    documents = [makeDoc({ id: 'new-1', source: 'fresh.pdf' }), ...documents];
    const held = gate();
    listGate = held.wait;
    await upload(user, 'fresh.pdf');
    await waitFor(() => expect(screen.queryByText('Importing document...')).not.toBeInTheDocument());
    await act(async () => {});
    expect(screen.getByRole('alert')).toHaveTextContent('Unsupported file type');
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
    held.open();
    await screen.findByText(/document imported: fresh\.pdf/i);
    expect(screen.getByRole('heading', { name: 'fresh.pdf' })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('HC-UIDOC-011: a retry that succeeds drops the alert even when the list refresh fails, and the result shows', async () => {
    // Would not notice: a card that never shows. Conservative first: the alert says the import failed, and the
    // retry worked, so once the refresh has ended (it failed) the alert goes and the result shows.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockRejectedValueOnce(new api.ApiError(400, 'Bad Request', 'Unsupported file type'));
    await upload(user, 'fresh.pdf');
    await screen.findByRole('alert');
    apiUpload.mockResolvedValueOnce(fresh() as never);
    listFails = true;
    await upload(user, 'fresh.pdf');
    expect(await screen.findByText(/document imported: fresh\.pdf/i)).toBeInTheDocument();
    expect(screen.queryByText(/import failed: fresh\.pdf/i)).not.toBeInTheDocument();
  });

  it('HC-UIDOC-006: a second failed import replaces the alert and a failure after a success keeps the card', async () => {
    // Would not notice: an alert that changes height with its text (the rects are read in the e2e half).
    const user = userEvent.setup();
    (await importWithHeldList(user)).open();
    await screen.findByText(/document imported: fresh\.pdf/i);
    apiUpload.mockRejectedValueOnce(new api.ApiError(400, 'Bad Request', 'Unsupported file type'));
    await upload(user, 'bad.pdf');
    expect(await screen.findByRole('alert')).toHaveTextContent('Unsupported file type');
    expect(screen.getByText(/document imported: fresh\.pdf/i)).toBeInTheDocument();
    apiUpload.mockRejectedValueOnce(new api.ApiError(413, 'Too Large', 'big'));
    await upload(user, 'bad2.pdf');
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('This file is too large to import.'));
    expect(screen.getAllByRole('alert')).toHaveLength(1);
  });

  it('HC-UIDOC-006: after Remove, focus moves to the neighbour without scrolling the page', async () => {
    // Would not notice: a scroll the browser starts for another reason. jsdom does not scroll, so this reads the
    // call: focus() must carry preventScroll, because the page scrolls smoothly (globals.css) and the scroll slides
    // every row. The e2e Remove tests measure the slide.
    // RED before this round: focus() was called with no options.
    documents = [makeDoc({ id: 'd1', source: 'one.pdf' }), makeDoc({ id: 'd2', source: 'two.pdf' })];
    apiDelete.mockImplementation((async (path: string) => {
      documents = documents.filter((d) => `/documents/${d.id}` !== path);
    }) as never);
    const user = userEvent.setup();
    await renderLoaded('one.pdf');
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    await openRowMenu(user, rowOf('two.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    focus.mockClear();
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() =>
      expect(within(rowOf('one.pdf')).getByRole('button', { name: 'More options' })).toHaveFocus()
    );
    const calls = focus.mock.calls.filter(([options]) => options !== undefined);
    expect(calls.length).toBeGreaterThan(0);
    expect(calls.every(([options]) => (options as FocusOptions).preventScroll === true)).toBe(true);
    const last = focus.mock.instances[focus.mock.calls.length - 1] as unknown as HTMLElement;
    expect(last.getAttribute('aria-label')).toBe('More options');
  });

  it('HC-UIDOC-006: removing the only row focuses Import Document and lets the page scroll to it', async () => {
    // Would not notice: the scroll itself (jsdom does not scroll); the e2e HC-UIDOC-013 reads the position at 320x640.
    // With no neighbour row nothing takes the removed row's place, so there is no slide to prevent, and a focus() that
    // may not scroll leaves the button above the viewport (top -321 at scrollY 542, measured in review).
    // RED before this round: the fallback focus carried preventScroll too.
    documents = [makeDoc({ id: 'd1', source: 'one.pdf' })];
    apiDelete.mockImplementation((async (path: string) => {
      documents = documents.filter((d) => `/documents/${d.id}` !== path);
    }) as never);
    const user = userEvent.setup();
    await renderLoaded('one.pdf');
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    await openRowMenu(user, rowOf('one.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    focus.mockClear();
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.getByRole('button', { name: /import document/i })).toHaveFocus());
    const onImport = focus.mock.calls.filter(
      (_call, index) => (focus.mock.instances[index] as unknown as HTMLElement).textContent?.includes('Import Document')
    );
    expect(onImport.length).toBeGreaterThan(0);
    expect(onImport.every(([options]) => (options as FocusOptions | undefined)?.preventScroll !== true)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-014..017: the import result waits for the list, but not for ever. A list refresh that has not settled after
// 3 s no longer hides the card, the scanned-page notice, the duplicate warning or the alert (L0 ruling on PR #464,
// comment 6606938809). The row may arrive later as a second step; each step is one instant jump (INBOX-ROW-JUMP).
// These tests run on real timers: the page's timer is 3 s.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-014 the import result does not wait for a list refresh for ever', () => {
  const fresh = (over: Partial<DocumentImportResponse> = {}) =>
    importResponse({ observations_extracted: 3, doc: { id: 'new-1', source: 'fresh.pdf' }, ...over });
  const TIMER_WAIT = { timeout: 4500 };

  /** Uploads fresh.pdf with the list refetch held; returns once the import has resolved and the refetch is waiting. */
  async function importWithHeldList(user: ReturnType<typeof userEvent.setup>, response = fresh()) {
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(response as never);
    documents = [makeDoc({ id: 'new-1', source: 'fresh.pdf' }), ...documents];
    const held = gate();
    listGate = held.wait;
    await upload(user, 'fresh.pdf');
    await waitFor(() => expect(screen.queryByText('Importing document...')).not.toBeInTheDocument());
    return held;
  }

  it('HC-UIDOC-014: a list refresh that never answers still shows the card, the scanned-page notice and the duplicate warning after 3 s, and not before', async () => {
    // Would not notice: the exact tick (the timer is 3000 ms; this reads "not at 1 s, there by 4.5 s"); or a result
    // that shows for another reason, since the list is held for the whole test and never answers.
    // RED at fb6e7ef2: the list was held and the card, the notice and the warning never showed (reviewer: all null at 2 s).
    const user = userEvent.setup();
    await importWithHeldList(
      user,
      fresh({
        pages_without_text: [2],
        duplicate_warning: { match_type: 'content_hash', document_id: 'doc-a', title: 'a.pdf' },
      })
    );
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    });
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
    expect(await screen.findByText(/document imported: fresh\.pdf/i, {}, TIMER_WAIT)).toBeInTheDocument();
    expect(screen.getByText(/page 2 has no readable text, so its values were not read/i)).toBeInTheDocument();
    expect(screen.getByText(/possible duplicate upload/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '3 values ready to review' })).toBeInTheDocument();
    // The list never answered, so the new row is not there: the row is the second step.
    expect(screen.queryByRole('heading', { name: 'fresh.pdf' })).not.toBeInTheDocument();
  }, 12000);

  it('HC-UIDOC-014: when the list answers after the timer the row arrives as a second step and the card stays', async () => {
    // Would not notice: that the two steps are each one jump (the e2e HC-UIDOC-006 (u) samples the rects); this reads the
    // order and that the card does not go and come back.
    const user = userEvent.setup();
    const held = await importWithHeldList(user);
    await screen.findByText(/document imported: fresh\.pdf/i, {}, TIMER_WAIT);
    expect(screen.queryByRole('heading', { name: 'fresh.pdf' })).not.toBeInTheDocument();
    held.open();
    await screen.findByRole('heading', { name: 'fresh.pdf' });
    expect(screen.getByText(/document imported: fresh\.pdf/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '3 values ready to review' })).toBeInTheDocument();
  }, 12000);

  it('HC-UIDOC-015: a refresh that is held past 3 s and then fails shows the result at the timer, and keeps it', async () => {
    // Would not notice: a plain failing refresh (HC-UIDOC-011 above pins that; it is GREEN at fb6e7ef2 because
    // !isFetching covers it). Only a failure held past the timer is RED at fb6e7ef2: the card waited for the failure.
    const user = userEvent.setup();
    const held = await importWithHeldList(user);
    listFails = true;
    await screen.findByText(/document imported: fresh\.pdf/i, {}, TIMER_WAIT);
    expect(screen.queryByText('Failed to load documents')).not.toBeInTheDocument();
    held.open();
    expect(await screen.findByText('Failed to load documents')).toBeInTheDocument();
    expect(screen.getByText(/document imported: fresh\.pdf/i)).toBeInTheDocument();
  }, 12000);

  it('HC-UIDOC-016: a failed import, then a retry whose refresh is held: the alert leaves with the card at the timer', async () => {
    // Would not notice: an alert that leaves and a card that shows in two different renders (the swap is read by
    // looking for the card the moment the alert is gone).
    // RED at fb6e7ef2: the alert stayed for ever, because it reads the same readiness as the card.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockRejectedValueOnce(new api.ApiError(400, 'Bad Request', 'Unsupported file type'));
    await upload(user, 'fresh.pdf');
    expect(await screen.findByRole('alert')).toHaveTextContent('Unsupported file type');
    apiUpload.mockResolvedValueOnce(fresh() as never);
    documents = [makeDoc({ id: 'new-1', source: 'fresh.pdf' }), ...documents];
    const held = gate();
    listGate = held.wait;
    await upload(user, 'fresh.pdf');
    await waitFor(() => expect(screen.queryByText('Importing document...')).not.toBeInTheDocument());
    await act(async () => {});
    expect(screen.getByRole('alert')).toHaveTextContent('Unsupported file type');
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument(), TIMER_WAIT);
    expect(screen.getByText(/document imported: fresh\.pdf/i)).toBeInTheDocument();
  }, 12000);

  it('HC-UIDOC-017: Remove of an import before its timer fires: the card does not come back when it fires, or on a later refresh', async () => {
    // Would not notice: a card that comes back for less than a render (this reads the settled page after the timer
    // and after a later Remove). Recurring failure 17's chain: the removed branch of importResultShown comes first.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(fresh() as never);
    documents = [makeDoc({ id: 'new-1', source: 'fresh.pdf' }), ...documents];
    apiDelete.mockImplementation((async (path: string) => {
      documents = documents.filter((d) => `/documents/${d.id}` !== path);
    }) as never);
    await upload(user, 'fresh.pdf');
    await screen.findByRole('link', { name: '3 values ready to review' });
    await openRowMenu(user, rowOf('fresh.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'fresh.pdf' })).not.toBeInTheDocument());
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
    // The import resolved about a second ago: let its 3 s timer fire.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 3500));
    });
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /ready to review/i })).not.toBeInTheDocument();
    // A later refresh: Remove the other row.
    await openRowMenu(user, rowOf('a.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'a.pdf' })).not.toBeInTheDocument());
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
  }, 15000);

  it('HC-UIDOC-017: a failed import, a retry, Remove of the retried row before the timer fires: the alert does not come back', async () => {
    // Would not notice: the same limits as the test above. The alert says a file failed that the retry did import.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockRejectedValueOnce(new api.ApiError(400, 'Bad Request', 'Unsupported file type'));
    await upload(user, 'fresh.pdf');
    await screen.findByRole('alert');
    apiUpload.mockResolvedValueOnce(fresh() as never);
    documents = [makeDoc({ id: 'new-1', source: 'fresh.pdf' }), ...documents];
    apiDelete.mockImplementation((async (path: string) => {
      documents = documents.filter((d) => `/documents/${d.id}` !== path);
    }) as never);
    await upload(user, 'fresh.pdf');
    await screen.findByRole('link', { name: '3 values ready to review' });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await openRowMenu(user, rowOf('fresh.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'fresh.pdf' })).not.toBeInTheDocument());
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 3500));
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText(/document imported: fresh\.pdf/i)).not.toBeInTheDocument();
  }, 15000);
});

// ---------------------------------------------------------------------------
// HC-UIDOC-018: a second Remove sent while the first is still in flight. useMutation runs a per-call onSuccess only
// for the observer's latest call (query-core mutationObserver.ts), so the first Remove's record of the removed
// document was lost and its card and "values ready to review" link stayed for a document that no longer exists.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-018 a second Remove while the first is in flight', () => {
  it('HC-UIDOC-018: with two DELETEs in flight, the card and the link for the document of the first Remove are gone once both settle', async () => {
    // Would not notice: the order the two DELETEs settle in (this releases the first, then the second); the e2e
    // HC-UIDOC-018 holds both on a production-shaped run. It reads the settled page, not a frame.
    // RED at fb6e7ef2 (round 3 measurement): {"card":"Document imported: private-fresh.pdf","link":"3 values ready to review","rows":[]}.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(
      importResponse({ observations_extracted: 3, doc: { id: 'new-1', source: 'private-fresh.pdf' } }) as never
    );
    documents = [makeDoc({ id: 'new-1', source: 'private-fresh.pdf' }), ...documents];
    await upload(user, 'private-fresh.pdf');
    await screen.findByRole('link', { name: '3 values ready to review' });

    const releases: Array<() => void> = [];
    apiDelete.mockImplementation((async (path: string) => {
      await new Promise<void>((resolve) => releases.push(resolve));
      documents = documents.filter((d) => `/documents/${d.id}` !== path);
    }) as never);
    await openRowMenu(user, rowOf('private-fresh.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await openRowMenu(user, rowOf('a.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledTimes(2));

    releases.forEach((release) => release());
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'private-fresh.pdf' })).not.toBeInTheDocument());
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'a.pdf' })).not.toBeInTheDocument());
    await act(async () => {});
    expect(screen.queryByText(/document imported: private-fresh\.pdf/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /ready to review/i })).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-019: a list that has not answered yet has no count. "0 total" beside "Loading documents..." says the library
// is empty before the patient knows.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-019 no count while the list loads', () => {
  it('HC-UIDOC-019: on a cold load with the list held there is no "0 total"; after the answer the real count shows', async () => {
    // Would not notice: the header height when the badge appears (e2e HC-UIDOC-019 reads the rects); a count hidden by
    // CSS only: this looks for the text, so a badge that stays in the DOM is found.
    // RED at fb6e7ef2: '0 total' beside "Loading documents...".
    const held = gate();
    listGate = held.wait;
    renderInbox();
    await screen.findByText('Loading documents...');
    expect(screen.queryByText(/\d+ total/)).not.toBeInTheDocument();
    held.open();
    expect(await screen.findByText('1 total')).toBeInTheDocument();
    expect(screen.queryByText('Loading documents...')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-006: the rows wait for the highlight summary on a cold load, so chips never arrive after the rows and push
// the rows below them down. The e2e half navigates /verify to /inbox under stillnessProbe with the summary held.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-006 rows wait for the highlights', () => {
  it('HC-UIDOC-006: with the highlight summary still loading the list says Loading, and the rows come with their chips', async () => {
    // Would not notice: a summary that is already cached and refetches in the background. isLoading is false then
    // (App.tsx staleTime is five minutes), so the rows are not held and a changed summary could still insert chips.
    // This test starts with no cache. The first check runs after the list has answered: the documents mock is not
    // gated, so "Loading documents..." with the list loaded can only be the summary.
    // RED before this round: the rows showed at once and the chips were inserted when the summary answered.
    highlights = [{ doc_id: 'doc-a', counts: { abnormal_value: 2 } }];
    const held = gate();
    summaryGate = held.wait;
    renderInbox();
    await waitFor(() => expect(listAnswers).toBeGreaterThan(0));
    await act(async () => {});
    expect(screen.getByText('Loading documents...')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'a.pdf' })).not.toBeInTheDocument();
    held.open();
    const heading = await screen.findByRole('heading', { name: 'a.pdf' });
    // The chips are in the same render as the row.
    const row = heading.parentElement!.parentElement as HTMLElement;
    expect(within(row).getByText(new RegExp(HIGHLIGHT_LABELS.abnormal_value))).toBeInTheDocument();
    expect(screen.queryByText('Loading documents...')).not.toBeInTheDocument();
  });

  it('HC-UIDOC-006: a failing highlight summary still shows the rows (no chips)', async () => {
    // Would not notice: the delay in the real app. App.tsx sets retry: 1, so a failing summary holds the list through
    // one retry; this test client has retry off. The e2e HC-UIDOC-012 measures the delay.
    // Conservative first: the patient sees the documents even when the summary is down.
    summaryFails = true;
    highlights = [{ doc_id: 'doc-a', counts: { abnormal_value: 2 } }];
    await renderLoaded('a.pdf');
    const row = rowOf('a.pdf');
    expect(within(row).queryByText(new RegExp(HIGHLIGHT_LABELS.abnormal_value))).not.toBeInTheDocument();
    expect(screen.queryByText('Loading documents...')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-010 (cont.): the Add to pinboard menu is the row menu's twin: same surface tokens, modal off, a spinner
// that stops under reduced motion.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-010 the Add to pinboard menu', () => {
  it('HC-UIDOC-010: the open pin menu uses the theme surface and the row menu tokens, not bg-white or black/8', async () => {
    // Would not notice: a value computed in a stylesheet (jsdom loads none), so this is a class contract; the axe scan
    // of the open pin menu in light and dark is e2e GATE G1. modal={false} is read in the e2e scan (aria-hidden-focus),
    // not here: a modal menu hides the page with aria-hidden, which is the test below.
    // RED today: bg-white with border-black/8.
    pinboards = [{ id: 'pb1', name: 'Cardiology', created_at: '2026-07-01T00:00:00', updated_at: '2026-07-01T00:00:00' }];
    const user = userEvent.setup();
    await renderLoaded();
    await user.click(within(rowOf('a.pdf')).getByRole('button', { name: 'Add to pinboard' }));
    const menu = await screen.findByRole('menu');
    const tokens = menu.className.split(/\s+/);
    for (const token of ['border-border', 'bg-surface-elevated', 'text-ink']) expect(tokens).toContain(token);
    expect(tokens).not.toContain('bg-white');
    expect(tokens.filter((t) => /^border-black\/\d+$/.test(t))).toEqual([]);
  });

  it('HC-UIDOC-010: with the pin menu open the rest of the page is not aria-hidden (modal off)', async () => {
    // Would not notice: a page hidden by another mechanism (inert, display). aria-hidden is what axe reads
    // (aria-hidden-focus), and it is what a modal Radix menu sets on every sibling of its portal.
    // RED today: the row's other buttons sit under an aria-hidden ancestor while the trigger keeps focus.
    pinboards = [{ id: 'pb1', name: 'Cardiology', created_at: '2026-07-01T00:00:00', updated_at: '2026-07-01T00:00:00' }];
    const user = userEvent.setup();
    await renderLoaded();
    await user.click(within(rowOf('a.pdf')).getByRole('button', { name: 'Add to pinboard' }));
    await screen.findByRole('menu');
    expect(document.querySelector('[aria-hidden="true"][data-aria-hidden]')).toBeNull();
    expect(screen.getByRole('heading', { name: 'a.pdf' }).closest('[aria-hidden="true"]')).toBeNull();
  });

  it('HC-UIDOC-010: the pin spinner spins only under motion-safe', async () => {
    // Would not notice: a spinner class set from somewhere else (the Button, a wrapper). The spinner is found by its
    // lucide class inside the trigger while the add is in flight, and every animate-spin token on it must carry the
    // motion-safe: prefix. Loaders keep running under reduced motion elsewhere (globals.css); this one is the row's.
    // RED today: a bare animate-spin.
    pinboards = [{ id: 'pb1', name: 'Cardiology', created_at: '2026-07-01T00:00:00', updated_at: '2026-07-01T00:00:00' }];
    apiPost.mockImplementation((() => new Promise(() => {})) as never);
    const user = userEvent.setup();
    await renderLoaded();
    const trigger = within(rowOf('a.pdf')).getByRole('button', { name: 'Add to pinboard' });
    await user.click(trigger);
    await user.click(await screen.findByRole('menuitem', { name: 'Cardiology' }));
    await waitFor(() => expect(trigger.querySelector('svg.lucide-loader2')).not.toBeNull());
    const spinner = trigger.querySelector('svg') as SVGElement;
    const spin = (spinner.getAttribute('class') ?? '').split(/\s+/).filter((t) => t.includes('animate-spin'));
    expect(spin).toEqual(['motion-safe:animate-spin']);
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-006 (vitest half): T0 marks, the handoff, the preview Sheet.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-006 T0 marks, handoff and preview', () => {
  it('HC-UIDOC-006: the row date and status word carry data-t0 and their hooks; low confidence words carry data-t0', async () => {
    // Would not notice: a mark on the row but not on the text node's element. The probe (e2e) reads the marked
    // element's own text, so the marks are on the elements that hold the words.
    // RED today: zero data-t0 nodes in a row.
    documents = [makeDoc({ id: 'd1', source: 'low.pdf', status: 'parsed', extraction_confidence: 0.31 })];
    await renderLoaded('low.pdf');
    const row = rowOf('low.pdf');
    const date = row.querySelector('[data-inbox-date]');
    const status = row.querySelector('[data-inbox-status]');
    const confidence = row.querySelector('[data-confidence-words]');
    for (const el of [date, status, confidence]) {
      expect(el).not.toBeNull();
      expect(el).toHaveAttribute('data-t0');
    }
    expect(status).toHaveTextContent('Needs Review');
    expect(date?.textContent).toBe(new Date('2026-07-13T09:00:00').toLocaleDateString());
    expect(confidence).toHaveTextContent('Low read confidence · check this value');
  });

  it('HC-UIDOC-006: a high-confidence row shows no confidence words at all', async () => {
    // Would not notice: a high band hidden by CSS. The check is on the DOM text, not on visibility.
    // RED today: "90% · High · Lowest extraction confidence" shows on every row.
    await renderLoaded();
    const row = rowOf('a.pdf');
    expect(row.textContent).not.toMatch(/confidence/i);
    expect(row.querySelector('[data-confidence-words]')).toBeNull();
  });

  it('HC-UIDOC-006: the new row arrives with no entrance style and the last-import card links "N values ready to review"', async () => {
    // Would not notice: a handoff that is a button with onClick (a link is what a screen reader lists and what
    // opens in a new tab). The href is checked, not only the text.
    // RED today: no such link; the card has a "Review values" button only.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(importResponse({ observations_extracted: 3, doc: { id: 'new-1', source: 'fresh.pdf' } }) as never);
    documents = [makeDoc({ id: 'new-1', source: 'fresh.pdf' }), ...documents];
    await upload(user, 'fresh.pdf');
    const link = await screen.findByRole('link', { name: '3 values ready to review' });
    expect(link).toHaveAttribute('href', '/verify?doc=new-1&mode=all');
    expect(link).toHaveAttribute('data-t0');
    expect(link).toHaveAttribute('data-inbox-handoff');
    await waitFor(() => expect(screen.getAllByRole('heading', { name: 'fresh.pdf' }).length).toBeGreaterThan(0));
    const style = rowOf('fresh.pdf').getAttribute('style') ?? '';
    expect(style).not.toMatch(/opacity|transform/);
    // The existing line and buttons stay.
    expect(screen.getByText(/document imported: fresh\.pdf/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Review values' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Preview' })).toBeInTheDocument();
  });

  it.each([
    [1, '1 value ready to review'],
    [12, '12 values ready to review'],
  ])('HC-UIDOC-006: %i extracted reads "%s"', async (count, words) => {
    // Would not notice: a plural that is wrong for one. Both ends are checked.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(importResponse({ observations_extracted: count }) as never);
    await upload(user, 'n.pdf');
    expect(await screen.findByRole('link', { name: words })).toBeInTheDocument();
  });

  it('HC-UIDOC-006: no handoff link when nothing was extracted (no link to an empty review)', async () => {
    // Would not notice: a link that appears with the card but is hidden. It looks for the role, so a hidden link
    // is not counted either way.
    const user = userEvent.setup();
    await renderLoaded();
    apiUpload.mockResolvedValueOnce(importResponse({ observations_extracted: 0 }) as never);
    await upload(user, 'empty.pdf');
    await screen.findByText(/document imported: new\.pdf/i);
    expect(screen.queryByRole('link', { name: /ready to review/i })).not.toBeInTheDocument();
    expect(document.querySelector('[data-inbox-handoff]')).toBeNull();
  });

  it('HC-UIDOC-006: View document opens a still Sheet named "Document preview", and closing removes it', async () => {
    // Would not notice: a Sheet that animates its content (the e2e stillness probe samples that). It does see the
    // old hand-made overlay, which had no role=dialog name from a Radix title.
    // RED today: the hand-made div is a dialog labelled by its own heading, with no Radix, and it stays after Escape
    // is pressed (it has no key handler).
    const user = userEvent.setup();
    await renderLoaded();
    await user.click(within(rowOf('a.pdf')).getByRole('button', { name: 'View document' }));
    const dialog = await screen.findByRole('dialog', { name: 'Document preview' });
    expect(within(dialog).getByTestId('page-image-overlay')).toHaveTextContent('doc-a');
    expect(dialog.getAttribute('style') ?? '').not.toMatch(/opacity|transform/);

    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.queryByTestId('page-image-overlay')).not.toBeInTheDocument();
  });

  it('HC-UIDOC-009: closing the preview Sheet with Escape returns focus to View document of that row', async () => {
    // Would not notice: a focus that Radix gives back to a trigger it does not have (the Sheet has none, so it falls
    // to <body> and the next Tab lands on "Skip to content"). Only the opener's own button counts: a different
    // focused element would also pass "not <body>", so the exact button is read.
    // RED before this round: the focus stayed on <body> after Escape.
    documents = [makeDoc({ id: 'd1', source: 'one.pdf' }), makeDoc({ id: 'd2', source: 'two.pdf' })];
    const user = userEvent.setup();
    await renderLoaded('one.pdf');
    const view = within(rowOf('two.pdf')).getByRole('button', { name: 'View document' });
    await user.click(view);
    await screen.findByRole('dialog', { name: 'Document preview' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await waitFor(() => expect(view).toHaveFocus());
  });

  it('HC-UIDOC-009: closing the preview Sheet that the last-import card opened returns focus to its Preview button', async () => {
    const user = userEvent.setup();
    await renderLoaded();
    await upload(user);
    await screen.findByText(/document imported: new\.pdf/i);
    const preview = screen.getByRole('button', { name: 'Preview' });
    await user.click(preview);
    await screen.findByRole('dialog', { name: 'Document preview' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await waitFor(() => expect(preview).toHaveFocus());
  });
});

// ---------------------------------------------------------------------------
// HC-UIDOC-010: no migration leftovers, and the delete dialog never cuts the name off.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-010 tokens and the delete dialog', () => {
  it('HC-UIDOC-010: the open row menu uses the theme surface, not bg-white, and no element uses transition-all or a black/N border', async () => {
    // Would not notice: a value computed in a stylesheet (jsdom loads none), so this is a class contract; the axe scan
    // of the open menu in light and dark is e2e GATE G1. bg-white is #fff in dark mode (contrast 1.18 on the text).
    // RED today: the menu is bg-white with border-black/8, the drop zone has transition-all, the list divides with
    // divide-black/4.
    const user = userEvent.setup();
    await renderLoaded();
    await openRowMenu(user, rowOf('a.pdf'));
    const menu = await screen.findByRole('menu');
    const menuTokens = menu.className.split(/\s+/);
    expect(menuTokens).toContain('bg-surface-elevated');
    expect(menuTokens).toContain('border-border');
    expect(menuTokens).not.toContain('bg-white');
    // Whole page for transition-all (banned, plan 2.6). The shared Card, Button and AddToPinboardButton carry their
    // own border-black/N outside this row's licence, so the border check reads this page's drop zone and list only.
    const all = Array.from(document.querySelectorAll('*')).flatMap((el) => (el.getAttribute('class') ?? '').split(/\s+/));
    expect(all.filter((t) => /(^|:)transition-all$/.test(t))).toEqual([]);
    const dropZone = document.querySelector('[class*="border-dashed"]');
    const list = document.querySelector('[class*="divide-y"]');
    expect(dropZone).not.toBeNull();
    expect(list).not.toBeNull();
    const own = [dropZone, list].flatMap((el) => (el?.getAttribute('class') ?? '').split(/\s+/));
    expect(own.filter((t) => /^(border|divide)-black\/\d+$/.test(t))).toEqual([]);
    expect(list?.className).toContain('divide-border');
  });

  it('HC-UIDOC-010: the delete dialog wraps a long document name inside itself', async () => {
    // Would not notice: a layout that only a browser computes (jsdom has none); the measured text range at 1440, 390
    // and 320 is e2e HC-UIDOC-010. This pins the class that lets an unbroken name wrap.
    // RED today: the dialog has no overflow-wrap class.
    documents = [makeDoc({ source: 'x'.repeat(120) + '.pdf' })];
    const user = userEvent.setup();
    await renderLoaded('x'.repeat(120) + '.pdf');
    await openRowMenu(user, rowOf('x'.repeat(120) + '.pdf'));
    await user.click(await screen.findByRole('menuitem', { name: /delete/i }));
    const dialog = await screen.findByRole('alertdialog');
    expect(dialog.className).toContain('[overflow-wrap:anywhere]');
  });
});

// ---------------------------------------------------------------------------
// Empty state: one real action.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-007 empty state', () => {
  it('HC-UIDOC-007: an empty library says "No documents yet. Import your first lab report above." once, with a button that opens the file picker', async () => {
    // Would not notice: an action that is not wired. The click is counted on the real file input. The text check
    // is for ONE element: e2e document-import E2E-DOC-001 uses getByText(/no documents yet|import your first/i),
    // which fails in strict mode on two matches (the title must match neither phrase).
    // RED today: the empty state has no action.
    documents = [];
    const user = userEvent.setup();
    renderInbox();
    const sentence = await screen.findByText(/no documents yet|import your first/i);
    expect(sentence).toHaveTextContent('No documents yet. Import your first lab report above.');

    const input = screen.getByLabelText(/upload medical documents/i) as HTMLInputElement;
    const clicks = vi.fn();
    input.addEventListener('click', clicks);
    const action = screen.getByRole('button', { name: 'Choose a file' });
    await user.click(action);
    expect(clicks).toHaveBeenCalledTimes(1);
  });

  for (const [status, text] of [
    [403, 'Access denied'],
    [500, 'Failed to load documents'],
  ] as const) {
    it(`HC-UIDOC-007: a list that failed with ${status} says so and does not call the library empty`, async () => {
      // Would not notice: a different wording of the count (it looks for "total" anywhere). The patient must not be
      // told the library is empty when the list never loaded: the title, the sentence, the button and the "0 total"
      // badge are the empty state's, and the error card above them is the answer.
      // RED before this round: the empty state showed beside the error.
      documents = [makeDoc()];
      apiGet.mockImplementation((async (path: string) => {
        if (path.startsWith('/documents/highlights/summary')) return [];
        if (path.startsWith('/pinboards')) return [];
        throw new api.ApiError(status, 'Failed', 'list failed');
      }) as never);
      renderInbox();
      expect(await screen.findByText(new RegExp(text))).toBeInTheDocument();
      await waitFor(() => expect(screen.queryByText('Loading documents...')).not.toBeInTheDocument());
      expect(screen.queryByText('Your library is empty')).not.toBeInTheDocument();
      expect(screen.queryByText(/no documents yet/i)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Choose a file' })).not.toBeInTheDocument();
      expect(screen.queryByText(/\btotal\b/)).not.toBeInTheDocument();
    });
  }
});

// ---------------------------------------------------------------------------
// HC-UIDOC-008: confidence in words, only below the threshold, only where asked.
// ---------------------------------------------------------------------------
describe('HC-UIDOC-008 ExtractionConfidenceBadge belowThresholdOnly', () => {
  const show = (confidence: number | null | undefined) =>
    render(<ExtractionConfidenceBadge confidence={confidence} lowest belowThresholdOnly />);

  it('HC-UIDOC-008: 0.8 and above render nothing', () => {
    // Would not notice: a threshold off by float rounding (0.8 is the boundary and is tested exactly).
    for (const value of [0.8, 0.94, 1]) {
      const { container, unmount } = show(value);
      expect(container).toBeEmptyDOMElement();
      unmount();
    }
  });

  it('HC-UIDOC-008: 0.79 reads Medium in words, with the old label kept in a muted span', () => {
    // Would not notice: the wording changing silently; the strings are the plan's.
    const { container } = show(0.79);
    const wrapper = container.querySelector('[data-t0][data-confidence-words]') as HTMLElement;
    expect(wrapper).not.toBeNull();
    expect(within(wrapper).getByText('Medium read confidence · check this value')).toBeInTheDocument();
    expect(within(wrapper).getByText('79% · Medium · Lowest extraction confidence')).toBeInTheDocument();
  });

  it('HC-UIDOC-008: 0.5 is Medium and 0.49 is Low', () => {
    const medium = show(0.5);
    expect(medium.container).toHaveTextContent('Medium read confidence');
    medium.unmount();
    const low = show(0.49);
    expect(low.container).toHaveTextContent('Low read confidence · check this value');
  });

  it('HC-UIDOC-008: 0.0 is Low, not missing', () => {
    // HC-CONF-004's rule: a zero is a value. A truthiness check would call it unavailable.
    const { container } = show(0);
    expect(container).toHaveTextContent('Low read confidence · check this value');
    expect(container).toHaveTextContent('0% · Low · Lowest extraction confidence');
    expect(container).not.toHaveTextContent(/unavailable/i);
  });

  it('HC-UIDOC-008: null and undefined stay visible as "unavailable" with data-t0 (unknown is not fine)', () => {
    for (const value of [null, undefined]) {
      const { container, unmount } = show(value);
      expect(container).toHaveTextContent('Extraction confidence unavailable');
      expect(container.querySelector('[data-t0]')).not.toBeNull();
      unmount();
    }
  });

  it('HC-UIDOC-008: without the prop the output is unchanged: same elements, same text, no data-t0', () => {
    // Would not notice: a change that keeps text but adds an attribute. The markup is compared with a Badge built
    // by hand, so /verify (which does not pass the prop) cannot drift.
    const cases: Array<[number | null, boolean, string, 'verified' | 'caution' | 'attention' | 'default']> = [
      [0.94, false, '94% · High extraction confidence', 'verified'],
      [0.94, true, '94% · High · Lowest extraction confidence', 'verified'],
      [0.6, false, '60% · Medium extraction confidence', 'caution'],
      [0, true, '0% · Low · Lowest extraction confidence', 'attention'],
      [null, false, 'Extraction confidence unavailable', 'default'],
    ];
    for (const [confidence, lowest, text, variant] of cases) {
      const actual = render(<ExtractionConfidenceBadge confidence={confidence} lowest={lowest} />);
      const expected = render(<Badge variant={variant}>{text}</Badge>);
      expect(actual.container.innerHTML).toBe(expected.container.innerHTML);
      expect(actual.container.querySelector('[data-t0]')).toBeNull();
      actual.unmount();
      expected.unmount();
    }
  });
});
