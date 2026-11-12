import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import {
  Upload,
  FileText,
  Calendar,
  CheckCircle,
  AlertCircle,
  MoreVertical,
  Eye,
  Plus,
  Loader2,
  X,
  RefreshCcw,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, EmptyState } from '@/components/ui';
// Overlays and the showcase recipes are imported by path, as the ui barrel notes. ThinkingOrb loads
// thinking-orbs lazily: never import that library from this page (HC-UISK-004).
import { AlertDialog } from '@/components/ui/AlertDialog';
import { Sheet } from '@/components/ui/Sheet';
import { BeamBorder } from '@/components/ui/BeamBorder';
import { ThinkingOrb } from '@/components/ui/ThinkingOrb';
import { cn } from '@/utils/cn';
import {
  useDocuments,
  useImportDocument,
  useDeleteDocument,
  useReprocessDocument,
  useHighlightsSummary,
  ApiError,
  type Document,
  type DocumentImportResponse,
} from '@/services';
import { useAuthStore } from '@/stores/authStore';
import { PageImageOverlay } from '@/components/PageImageOverlay';
import { HighlightChips } from '@/components/documents/HighlightChips';
import { AddToPinboardButton } from '@/components/pinboards/AddToPinboardButton';
import { ExtractionConfidenceBadge } from '@/components/documents/ExtractionConfidenceBadge';
// CategoryBadge + EntityDetailView available in @/components/documents/
// Wire into document detail view when it's built (no detail page exists yet)

// IMPORT-SCANNED-PAGE: the values on these pages were not read; say which ones.
function pagesWithoutTextNotice(pages: number[]): string {
  if (pages.length === 1) {
    return `Page ${pages[0]} has no readable text, so its values were not read. Check the original report.`;
  }
  const head = pages.slice(0, -1).join(', ');
  return `Pages ${head} and ${pages[pages.length - 1]} have no readable text, so their values were not read. Check the original report.`;
}

/** The words for a stored document type. A raw identifier never reaches the page (HC-UIDOC-002). */
const DOC_TYPE_WORDS: Record<string, string> = {
  lab_pdf: 'Lab Report',
  lab_report: 'Lab Report',
  lab_pdf_scanned: 'Scanned Lab Report',
  lab_image: 'Lab Image',
  lab_csv: 'Lab Spreadsheet',
  fhir_bundle: 'Health Record (FHIR)',
};

function docTypeWords(doc: Document): string {
  return DOC_TYPE_WORDS[doc.doc_type] ?? 'Document';
}

/** How long an import result waits for the list refresh to settle before it shows without the new row (INBOX-ROW-JUMP). */
const IMPORT_RESULT_WAIT_MS = 3000;

/**
 * The first toLocaleDateString of a page loads the browser's ICU date data (7-13 ms at normal CPU speed). On an empty
 * list the first row's date is that first call, so it would land inside the one task that commits the imported row
 * (UIDOC-006A-FLAKE). This pays it while the page is idle instead; the row still prints its date in its first commit.
 * Same pattern as warmExplainClick in ResultsPage.tsx.
 */
function warmDateFormat(): () => void {
  const warm = () => {
    void new Date(0).toLocaleDateString();
  };
  if (typeof window.requestIdleCallback === 'function') {
    const handle = window.requestIdleCallback(warm, { timeout: 2000 });
    return () => window.cancelIdleCallback(handle);
  }
  const handle = window.setTimeout(warm, 300);
  return () => window.clearTimeout(handle);
}

export function DocumentInbox() {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [previewDocId, setPreviewDocId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);
  // Every import that resolved this visit, oldest first. The card shows one of them (see importCard below).
  const [imports, setImports] = useState<DocumentImportResponse[]>([]);
  const [duplicateWarnings, setDuplicateWarnings] = useState<DocumentImportResponse[]>([]);
  // `after` is how many imports had resolved when it failed. An import after that lets the alert go; it is not known to
  // be a retry of the same file (a later file of a multi-file pick does the same, so that failure goes unreported).
  const [importError, setImportError] = useState<{ message: string; fileName: string; after: number } | null>(null);
  const importsResolved = useRef(0);
  // Positions in `imports` whose IMPORT_RESULT_WAIT_MS timer has fired. The timers are cleared on unmount.
  const [waitedOut, setWaitedOut] = useState<number[]>([]);
  const waitTimers = useRef<ReturnType<typeof setTimeout>[]>([]);
  useEffect(() => () => waitTimers.current.forEach(clearTimeout), []);
  useEffect(warmDateFormat, []);
  // Documents the patient removed in this visit: their import card and duplicate warning leave with their row.
  const [removedIds, setRemovedIds] = useState<string[]>([]);
  // A Remove the server refused: the row stays, so the patient is told (HC-UIDOC-020). Cleared by Dismiss or a later Remove.
  const [removeError, setRemoveError] = useState<{ name: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const moreButtons = useRef(new Map<string, HTMLButtonElement>());
  const importButton = useRef<HTMLButtonElement>(null);
  const previewOpener = useRef<HTMLElement | null>(null);

  // Get active profile from auth store
  const profileId = useAuthStore((state) => state.profileId) || '';
  
  // Fetch documents from API
  const { data: documents = [], isLoading, isFetching, error } = useDocuments({ profile_id: profileId });
  const importDocument = useImportDocument();
  const deleteDocument = useDeleteDocument();
  const reprocessDocument = useReprocessDocument();

  // Highlight chips for recent documents (HC-M16) — organizational tags only
  // The rows wait for the summary on a cold load: chips that arrive after the rows grow the row and push every row
  // below it down (HC-UIDOC-006). A failed summary stops loading, so the rows show without chips.
  const { data: highlightSummary = [], isLoading: highlightsLoading } = useHighlightsSummary();
  const highlightsByDoc = new Map(highlightSummary.map((s) => [s.doc_id, s.counts]));

  // A process counts as running only while its request is in flight. A stored status of 'pending' does not prove
  // one (plan §2.6, S2), so the list is never read for this. There is no page index to report: POST
  // /documents/import is one synchronous request, so the card names the document, not "page N of M".
  const processingName: string | null = importDocument.isPending
    ? (importDocument.variables?.file.name ?? 'document')
    : reprocessDocument.isPending
      ? (documents.find((d) => d.id === reprocessDocument.variables)?.source || 'document')
      : null;

  // The import card and a duplicate warning appear in the same frame as the new row they describe, and leave in the same
  // frame as its row (HC-UIDOC-006: rows move once). The import resolves before the invalidated list answers, so shown
  // from the result alone they would land first and push every row down, and the row would push them down again. They
  // wait for the list, but not for ever: once it has settled (success or failure), or IMPORT_RESULT_WAIT_MS after the
  // import resolved, whichever comes first, they show. If the timer won, the row arrives later as a second step: an
  // event the patient was waiting on, and each step is still one instant jump (INBOX-ROW-JUMP).
  const importResultShown = (id: string, at: number): boolean => {
    const inList = documents.some((doc) => doc.id === id);
    return removedIds.includes(id) ? Boolean(isFetching) && inList : inList || !isFetching || waitedOut.includes(at);
  };

  // An import is ready when its row has arrived, the list has stopped fetching without it, or its timer has fired. One
  // the patient removed stays ready through every later refresh and timer: its row is not coming back, so waiting for it
  // would make an older card, or the alert of a failure it retried past, the newest ready result and show it again.
  const importReady = (result: DocumentImportResponse, at: number): boolean =>
    !isFetching ||
    waitedOut.includes(at) ||
    removedIds.includes(result.document.id) ||
    documents.some((doc) => doc.id === result.document.id);

  // The card is the newest import that is ready, so a second import keeps the first card until its own row is in the
  // list, and the two swap in one render (a card that left when the import resolved would move every row up, and the
  // new row would move them down again). A removed import stays the newest ready one, so no older card comes back.
  const readyAt = imports.map(importReady).lastIndexOf(true);
  const importCard = readyAt >= 0 && importResultShown(imports[readyAt].document.id, readyAt) ? imports[readyAt] : null;
  // The alert stays until a retry has landed the same way, then it leaves in the render that adds the row (or at the timer).
  const importErrorShown =
    importError !== null && !imports.some((result, at) => at >= importError.after && importReady(result, at)) ? importError : null;

  const openPreview = (id: string, opener: HTMLElement) => {
    previewOpener.current = opener;
    setPreviewDocId(id);
  };

  // The Sheet is opened from a button, not from a trigger, so Radix has no element to give focus back to and the
  // focus would fall to <body> (the next Tab lands on "Skip to content"). It goes back to the button that opened it.
  const closePreview = () => {
    const opener = previewOpener.current;
    previewOpener.current = null;
    setPreviewDocId(null);
    // After the render: while the Sheet is still open its focus trap would pull the focus straight back.
    requestAnimationFrame(() => {
      if (opener?.isConnected) opener.focus();
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    for (const file of files) {
      await handleFileUpload(file);
    }
  };
  
  const handleFileUpload = async (file: File) => {
    if (!profileId) return;
    
    try {
      const result = await importDocument.mutateAsync({ file, profileId });
      const at = importsResolved.current;
      importsResolved.current += 1;
      setImports((current) => [...current, result]);
      waitTimers.current.push(setTimeout(() => setWaitedOut((current) => [...current, at]), IMPORT_RESULT_WAIT_MS));
      if (result.duplicate_warning) {
        setDuplicateWarnings((current) => [...current, result]);
      }
    } catch (err) {
      console.error('Failed to import document:', err);
      const message =
        err instanceof ApiError
          ? err.status === 413
            ? 'This file is too large to import.'
            : err.message
          : 'Something went wrong while importing this file. Please try again.';
      setImportError({ message, fileName: file.name, after: importsResolved.current });
    }
  };

  const handleReprocessDocument = (doc: Document) => {
    reprocessDocument.mutate(doc.id);
  };
  
  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };
  
  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    for (const file of files) {
      await handleFileUpload(file);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // The dialog is opened from a menu item, not from a trigger, so Radix has no element to give focus back to.
  // Cancel and Escape return it to the More options button of the row the dialog was opened for.
  const closeDeleteDialog = () => {
    const id = deleteTarget?.id;
    setDeleteTarget(null);
    // After the render: while the dialog is still open its focus trap would pull the focus straight back.
    if (id) requestAnimationFrame(() => moreButtons.current.get(id)?.focus());
  };

  const confirmDelete = () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    // The row is about to disappear, and with it its More options button. Focus goes to the next row's button, else
    // the previous row's, else the Import Document button, so a keyboard user is never dropped on <body>.
    const at = documents.findIndex((d) => d.id === id);
    const neighbour = documents[at + 1] ?? documents[at - 1];
    // A card that offers "N values ready to review" must not link to a document that no longer exists. It goes when
    // the list drops the row (importResultShown), not before, so the two leave in one frame. The record is made here and
    // not in a per-call onSuccess: that fires only for the observer's latest call, so a second Remove sent while this
    // one is in flight would lose it. A failed DELETE records nothing (the document is still there).
    const name = deleteTarget.source || 'this document';
    setRemoveError(null);
    deleteDocument.mutateAsync(id).then(
      () => setRemovedIds((current) => [...current, id]),
      () => setRemoveError({ name })
    );
    setDeleteTarget(null);
    // With a neighbour: preventScroll. The page scrolls smoothly (globals.css), and a focus() that scrolls it slides every
    // row for 300 ms, then the removed row's height snaps the scroll back. The neighbour takes the removed row's place.
    // Without one the Import Document button is at the top of the page, possibly far above the viewport, and no row is
    // left to slide: the focus may scroll, or a keyboard user is left with focus they cannot see.
    requestAnimationFrame(() => {
      const next = neighbour ? moreButtons.current.get(neighbour.id) : undefined;
      if (next) next.focus({ preventScroll: true });
      else importButton.current?.focus();
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Document Inbox
          </h1>
          <p className="text-ink-secondary mt-1">
            Import and manage your medical documents
          </p>
        </div>
        <Button ref={importButton} className="gap-2" onClick={handleBrowseClick}>
          <Plus className="w-4 h-4" />
          Import Document
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.csv,.json"
          multiple
          className="hidden"
          onChange={handleFileInputChange}
          aria-label="Upload medical documents"
        />
      </div>

      {importErrorShown && (
        <Card className="border-status-critical/30 bg-status-critical/5" role="alert" data-t0 data-inbox-error>
          <CardContent className="py-4 flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <AlertCircle className="w-5 h-5 text-status-critical shrink-0 mt-0.5" />
              <div className="min-w-0 break-words">
                <p className="font-medium text-ink">Import failed: {importErrorShown.fileName}</p>
                <p className="text-sm text-ink-secondary mt-1">{importErrorShown.message}</p>
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="shrink-0"
              aria-label={`Dismiss import error for ${importErrorShown.fileName}`}
              onClick={() => setImportError(null)}
            >
              <X className="w-4 h-4" />
            </Button>
          </CardContent>
        </Card>
      )}

      {removeError && (
        <Card className="border-status-critical/30 bg-status-critical/5" role="alert" data-inbox-remove-error>
          <CardContent className="py-4 flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <AlertCircle className="w-5 h-5 text-status-critical shrink-0 mt-0.5" />
              <div className="min-w-0 break-words">
                <p className="font-medium text-ink">Couldn't remove {removeError.name}</p>
                <p className="text-sm text-ink-secondary mt-1">It is still in your library. Try again.</p>
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="shrink-0"
              aria-label="Dismiss"
              onClick={() => setRemoveError(null)}
            >
              <X className="w-4 h-4" />
            </Button>
          </CardContent>
        </Card>
      )}

      {/* The running state lives in the drop zone's own slot: the idle block stays in the grid cell (hidden) so the
          cell keeps its height, and the page below does not move when an import STARTS (HC-UIDOC-006, G6). When it
          ENDS, the handoff card and the new row are inserted above the rows in one frame: the one allowed jump. The ring
          is lifted above the opaque card (z-10), or the card would paint over it. */}
      <BeamBorder active={processingName !== null} className="rounded-2xl [&>span]:z-10">
        <Card
          className={cn(
            'border-2 border-dashed transition-colors duration-200',
            isDragging
              ? 'border-accent bg-accent-subtle/50'
              : 'border-border hover:border-accent/50'
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <CardContent className="py-12">
            <div className="text-center">
              <div className="grid">
                <div
                  className={cn('col-start-1 row-start-1', processingName !== null && 'invisible')}
                  aria-hidden={processingName !== null ? true : undefined}
                >
                  <div
                    className={cn(
                      'w-14 h-14 mx-auto rounded-2xl flex items-center justify-center mb-4 transition-colors',
                      isDragging ? 'bg-accent text-white' : 'bg-surface-muted text-ink-secondary'
                    )}
                  >
                    <Upload className="w-6 h-6" />
                  </div>
                  <h3 className="font-medium text-ink mb-1">
                    {isDragging ? 'Drop files here' : 'Drag and drop files'}
                  </h3>
                  <p className="text-sm text-ink-secondary">
                    or click to browse • PDF, images supported
                  </p>
                </div>
                {processingName !== null && (
                  <div className="col-start-1 row-start-1 flex min-w-0 flex-col items-center justify-center gap-2">
                    <h3 className="font-medium text-ink">
                      {importDocument.isPending ? 'Importing document...' : 'Reprocessing document...'}
                    </h3>
                    <p className="max-w-full truncate text-sm text-ink-secondary" title={processingName}>
                      {processingName}
                    </p>
                    <ThinkingOrb
                      size={20}
                      status={`Reading ${processingName}`}
                      className="max-w-full min-w-0 [overflow-wrap:anywhere] [&_[role=status]]:line-clamp-2 [&_[role=status]]:min-w-0"
                    />
                  </div>
                )}
              </div>
              <Button variant="secondary" size="sm" className="mt-4" onClick={handleBrowseClick}>
                Browse Files
              </Button>
            </div>
          </CardContent>
        </Card>
      </BeamBorder>

      {error && (
        <Card className="border-status-critical/20 bg-status-critical/5">
          <CardContent className="py-4 space-y-3">
            <div className="flex items-start gap-3 text-status-critical">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-medium text-ink">
                  {error instanceof ApiError && error.status === 401
                    ? 'Your session has ended or is invalid.'
                    : error instanceof ApiError && error.status === 403
                      ? 'Access denied — your profile may be locked.'
                      : 'Failed to load documents'}
                </p>
                <p className="text-sm text-ink-secondary">
                  {error instanceof ApiError && error.status === 401
                    ? 'For privacy, invalid sessions are cleared. Sign in again to continue.'
                    : error instanceof ApiError && error.status === 403
                      ? 'Unlock your profile or adjust access in Settings.'
                      : 'Check that the Asclexis server is running and try again.'}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 pl-8">
              {(error instanceof ApiError && (error.status === 401 || error.status === 403)) && (
                <>
                  <Button variant="secondary" size="sm" className="gap-1.5" asChild>
                    <Link to="/setup">Sign in again</Link>
                  </Button>
                  <Button variant="secondary" size="sm" className="gap-1.5" asChild>
                    <Link to="/settings">Open Settings</Link>
                  </Button>
                </>
              )}
              <Button variant="secondary" size="sm" onClick={() => navigate(0)}>
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {importCard && (
        <Card className="border-accent/20 bg-accent-subtle/40">
          <CardContent className="py-4 flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <p className="font-medium text-ink break-words">Document imported: {importCard.document.source || 'Untitled document'}</p>
              <p className="text-sm text-ink-secondary">
                {importCard.observations_extracted} values extracted · status {importCard.document.status.replace(/_/g, ' ')}
              </p>
              {importCard.import_summary && (
                <p className="text-sm text-ink-secondary">
                  Imported {importCard.import_summary.observations_imported} lab results and{' '}
                  {importCard.import_summary.entities_imported} record mentions — all pending your
                  verification
                </p>
              )}
              {(importCard.pages_without_text?.length ?? 0) > 0 && (
                <p role="status" data-t0 data-inbox-scanned className="text-sm font-medium text-ink">
                  {pagesWithoutTextNotice(importCard.pages_without_text ?? [])}
                </p>
              )}
              {importCard.observations_extracted > 0 && (
                <p className="text-sm font-medium">
                  <Link
                    to={`/verify?doc=${importCard.document.id}&mode=all`}
                    data-t0
                    data-inbox-handoff
                    className="text-ink underline underline-offset-4 hover:text-accent-hover"
                  >
                    {importCard.observations_extracted}{' '}
                    {importCard.observations_extracted === 1 ? 'value' : 'values'} ready to review
                  </Link>
                </p>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={(e) => openPreview(importCard.document.id, e.currentTarget)}>
                Preview
              </Button>
              <Button size="sm" onClick={() => navigate(`/verify?doc=${importCard.document.id}&mode=all`)}>
                Review values
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {duplicateWarnings.filter((importResult) => importResultShown(importResult.document.id, imports.indexOf(importResult))).map((importResult) => (
        <Card
          key={importResult.document.id}
          className="border-status-caution/30 bg-status-caution/5"
          role="status"
        >
          <CardContent className="py-4 flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <AlertCircle className="w-5 h-5 text-status-caution shrink-0 mt-0.5" />
              <div className="min-w-0 break-words">
                <p className="font-medium text-ink">Possible duplicate upload</p>
                <p className="text-sm text-ink-secondary mt-1">
                  {importResult.duplicate_warning?.match_type === 'content_hash'
                    ? 'This file has the same content as'
                    : 'This document has the same recorded date as'}{' '}
                  <span className="font-medium">
                    {importResult.duplicate_warning?.title || 'an existing document'}
                  </span>
                  . The new upload was still imported; review both records if needed.
                </p>
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="shrink-0"
              aria-label={`Dismiss duplicate warning for ${
                importResult.duplicate_warning?.title || importResult.document.source || 'document'
              }`}
              onClick={() => setDuplicateWarnings((current) =>
                current.filter((warning) => warning.document.id !== importResult.document.id)
              )}
            >
              <X className="w-4 h-4" />
            </Button>
          </CardContent>
        </Card>
      ))}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Recent Documents</span>
            {/* A list that has not answered or failed to load has no count: "0 total" would say the library is empty. */}
            {!isLoading && !(error && documents.length === 0) && <Badge variant="default">{documents.length} total</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {/* A list that failed to load is not an empty library: the error card above is the answer. */}
          {isLoading || highlightsLoading ? (
            <div className="p-8 text-center text-ink-secondary">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin mx-auto mb-2" />
              Loading documents...
            </div>
          ) : documents.length === 0 && !error ? (
            <EmptyState
              icon={FileText}
              title="Your library is empty"
              description="No documents yet. Import your first lab report above."
              action={
                <Button variant="secondary" onClick={handleBrowseClick}>
                  Choose a file
                </Button>
              }
              className="border-0 bg-transparent"
            />
          ) : (
            <div className="divide-y divide-border">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  data-inbox-row
                  className="flex flex-wrap items-start gap-x-3 gap-y-2 p-4 hover:bg-surface-muted/50 transition-colors"
                >
                  <div className="shrink-0 w-10 h-10 rounded-xl bg-surface-muted flex items-center justify-center">
                    <FileText className="w-5 h-5 text-ink-secondary" />
                  </div>

                  <div className="min-w-0 flex-1 basis-40">
                    <h4 className="font-medium text-ink truncate" title={doc.source || undefined}>
                      {doc.source || 'Untitled Document'}
                    </h4>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-sm text-ink-secondary">
                      <span>{docTypeWords(doc)}</span>
                      <span className="text-ink-tertiary">•</span>
                      <span data-t0 data-inbox-date className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {new Date(doc.imported_at).toLocaleDateString()}
                      </span>
                      {doc.status === 'verified' ? (
                        <Badge variant="verified" className="gap-1" data-t0 data-inbox-status>
                          <CheckCircle className="w-3 h-3" />
                          Verified
                        </Badge>
                      ) : doc.status === 'pending_ocr' ? (
                        <Badge variant="default" className="gap-1" data-t0 data-inbox-status title="This scan needs text recognition before its values can be read. In Settings, turn on document OCR under Document import (the reader is built in; your server must allow OCR with OCR_ENABLED).">
                          <AlertCircle className="w-3 h-3" />
                          OCR Required
                        </Badge>
                      ) : (
                        <Badge variant="caution" className="gap-1" data-t0 data-inbox-status>
                          <AlertCircle className="w-3 h-3" />
                          {doc.status === 'pending' ? 'Pending' : 'Needs Review'}
                        </Badge>
                      )}
                    </div>
                    {highlightsByDoc.has(doc.id) && (
                      <HighlightChips
                        counts={highlightsByDoc.get(doc.id)!}
                        max={2}
                        className="mt-1.5"
                      />
                    )}
                    <div className="mt-1.5 empty:hidden">
                      <ExtractionConfidenceBadge confidence={doc.extraction_confidence} lowest belowThresholdOnly />
                    </div>
                  </div>

                  {/* Always visible and reachable by Tab (HC-UIDOC-001). focus-within:opacity-100 no longer does
                      anything: it stays only because FE-TW4-HOVER-002 asserts the token. */}
                  <div className="ml-auto flex items-center gap-1 focus-within:opacity-100">
                    <AddToPinboardButton items={[{ item_type: 'document', item_id: doc.id }]} />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label="View document"
                      onClick={(e) => openPreview(doc.id, e.currentTarget)}
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                    <DropdownMenu.Root modal={false}>
                      <DropdownMenu.Trigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          aria-label="More options"
                          ref={(el) => {
                            if (el) moreButtons.current.set(doc.id, el);
                            else moreButtons.current.delete(doc.id);
                          }}
                        >
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenu.Trigger>
                      <DropdownMenu.Portal>
                        <DropdownMenu.Content
                          className="min-w-48 rounded-xl border border-border bg-surface-elevated p-1 text-ink shadow-lg z-100"
                          sideOffset={8}
                          align="end"
                        >
                          <DropdownMenu.Item
                            className="rounded-lg px-3 py-2 text-sm outline-hidden cursor-pointer hover:bg-surface-muted focus:bg-surface-muted"
                            onSelect={() => navigate(`/verify?doc=${doc.id}&mode=all`)}
                          >
                            Review extracted values
                          </DropdownMenu.Item>
                          {(doc.status === 'pending_ocr' || doc.status === 'extraction_failed' || doc.status === 'parsed') && (
                            <DropdownMenu.Item
                              className="rounded-lg px-3 py-2 text-sm outline-hidden cursor-pointer hover:bg-surface-muted focus:bg-surface-muted"
                              onSelect={() => handleReprocessDocument(doc)}
                            >
                              <span className="inline-flex items-center gap-2">
                                <RefreshCcw className="w-3.5 h-3.5" />
                                Continue OCR / Retry extraction
                              </span>
                            </DropdownMenu.Item>
                          )}
                          <DropdownMenu.Item
                            className="rounded-lg px-3 py-2 text-sm outline-hidden cursor-pointer text-status-critical hover:bg-status-critical/10 focus:bg-status-critical/10"
                            onSelect={() => setDeleteTarget(doc)}
                          >
                            Delete…
                          </DropdownMenu.Item>
                        </DropdownMenu.Content>
                      </DropdownMenu.Portal>
                    </DropdownMenu.Root>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* The preview holds document content, so the Sheet is still (M0). */}
      <Sheet
        open={previewDocId !== null}
        onOpenChange={(open) => {
          if (!open) closePreview();
        }}
        title="Document preview"
        still
        className="lg:max-w-3xl"
      >
        {previewDocId && <PageImageOverlay documentId={previewDocId} pageNumber={1} bbox={null} />}
      </Sheet>

      <AlertDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) closeDeleteDialog();
        }}
        title="Remove this document?"
        className="[overflow-wrap:anywhere]"
        description={`Remove "${deleteTarget?.source || 'this document'}" from your library? This cannot be undone.`}
      >
        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" data-alert-cancel onClick={closeDeleteDialog}>
            Cancel
          </Button>
          <Button type="button" variant="danger" onClick={confirmDelete}>
            Remove
          </Button>
        </div>
      </AlertDialog>
    </div>
  );
}
