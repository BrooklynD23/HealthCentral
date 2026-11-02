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
  orb.mounts = 0;
  orb.sizes = [];
  setReducedMotion(false);
  apiGet.mockImplementation((async (path: string) => {
    if (path.startsWith('/documents/highlights/summary')) return highlights;
    if (path.startsWith('/pinboards')) return [];
    if (path.startsWith('/documents')) return documents;
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
    expect(container.querySelector('.beam-border')).toBeNull();

    await upload(user, 'big-scan.pdf');
    const reading = await screen.findByText('Reading big-scan.pdf');
    expect(reading).toHaveAttribute('role', 'status');
    const beams = container.querySelectorAll('.beam-border');
    expect(beams).toHaveLength(1);
    expect(beams[0]).toHaveAttribute('data-active', 'true');
    expect(beams[0]).toContainElement(reading);
    expect(within(beams[0] as HTMLElement).getByText('big-scan.pdf')).toBeInTheDocument();
    expect(await screen.findByTestId('orb')).toBeInTheDocument();
    expect(orb.sizes).toContain(20);

    await act(async () => finishUpload(importResponse({ doc: { source: 'big-scan.pdf' } })));
    await waitFor(() => expect(container.querySelector('.beam-border')).toBeNull());
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
    expect(container.querySelector('.beam-border')).toBeNull();
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
    expect(container.querySelectorAll('.beam-border')).toHaveLength(1);

    await act(async () => finishReprocess(importResponse()));
    await waitFor(() => expect(container.querySelector('.beam-border')).toBeNull());
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
    expect(document.body.querySelectorAll('.beam-border')).toHaveLength(1);
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
