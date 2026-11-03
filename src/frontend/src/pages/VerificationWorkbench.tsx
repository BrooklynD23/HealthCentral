import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  CheckCircle,
  AlertTriangle,
  Edit3,
  Eye,
  ChevronDown,
  FileText,
  Info,
  Loader2,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, Input } from '@/components/ui';
import { Dialog } from '@/components/ui/Dialog';
import { StatusChip } from '@/components/ui/StatusChip';
import { notify } from '@/components/ui/toast';
import { cn } from '@/utils/cn';
import { useObservations, useVerifyObservation } from '@/services/observations';
import {
  useDocuments,
  useVerifyDocument,
  useReprocessDocument,
  useDocumentEntities,
  useSetEntityVerification,
} from '@/services';
import { useAuthStore } from '@/stores/authStore';
import { apiGet, ApiError } from '@/services/api';
import { PageImageOverlay } from '@/components/PageImageOverlay';
import { EntityDetailView, InkMarker } from '@/components/documents/EntityDetailView';
import { ExtractionConfidenceBadge } from '@/components/documents/ExtractionConfidenceBadge';
import type { Observation, DocumentPage, BoundingBox, Document } from '@/services/types';
import type { DocumentEntityResponse } from '@/services';

const DOCUMENT_ATTENTION_STATUSES = new Set([
  'pending',
  'pending_ocr',
  'parsed',
  'extraction_failed',
]);

/** `[x0,y0,x1,y1]` as stored on observations and entities alike. */
function parseBbox(json: string | null | undefined): BoundingBox | null {
  if (!json) return null;
  try {
    const arr = JSON.parse(json) as number[];
    if (arr.length === 4) return { x0: arr[0], y0: arr[1], x1: arr[2], y1: arr[3] };
  } catch { /* invalid JSON */ }
  return null;
}

const HIGH_FLAGS = new Set(['H', 'HH', 'HIGH']);
const LOW_FLAGS = new Set(['L', 'LL', 'LOW']);

/**
 * Which side of the report's range a value sits on, in words (HC-UIREV-001, WCAG 1.4.1).
 * The report's own flag wins. Without one, the direction comes from the numbers; with no range to compare
 * against, nothing is claimed. A value inside its range gets no word at all: this page claims no reassurance
 * it was not asked to (L0 ruling on review round 3).
 */
function rangeStateOf(observation: Observation): 'above-range' | 'below-range' | null {
  // The extractor can keep the brackets around a flag, as in "(H)".
  const flag = (observation.flag ?? '').replace(/[()\s]/g, '').toUpperCase();
  if (HIGH_FLAGS.has(flag)) return 'above-range';
  if (LOW_FLAGS.has(flag)) return 'below-range';
  const { value, ref_low: low, ref_high: high } = observation;
  if (typeof value === 'number') {
    if (high !== null && value > high) return 'above-range';
    if (low !== null && value < low) return 'below-range';
  }
  // A flag with no side (A, ABNORMAL, CRITICAL) or is_abnormal on numbers inside the range also gets no word here.
  // This page does not print the flag text itself, so such a row shows no range word at all.
  return null;
}

/** The value's tint, from the same state as the words, so a flag form such as "(H)" is read once. */
function valueTintOf(observation: Observation): string {
  const state = rangeStateOf(observation);
  if (state === 'above-range') return 'text-status-attention';
  if (state === 'below-range') return 'text-status-caution';
  return 'text-ink';
}

/**
 * A value verified in this visit. On the default list (needs_verification) the API drops a row once it is
 * verified, so the row is held in place, as ink, until the page is left. Reload and it is gone, as before.
 */
interface HeldRow {
  observation: Observation;
  index: number;
}
const NO_HELD_ROWS: HeldRow[] = [];

/**
 * `fetched` with the held rows laid over it. A fetched row that is verified wins: the server has it, and it may
 * differ from the copy held here. A row the fetch no longer has comes back only on the needs_verification list,
 * where the API drops a row once it is verified. On any other list a missing row is gone for a reason (a document
 * that was reprocessed deletes its rows and makes new ids), and putting it back would show a ghost.
 */
function withHeldRows(
  fetched: Observation[] | undefined,
  held: HeldRow[],
  reinsertMissing: boolean
): Observation[] | undefined {
  if (!fetched || held.length === 0) return fetched;
  const heldById = new Map(held.map((entry) => [entry.observation.id, entry.observation]));
  const rows = fetched.map((row) => (row.user_verified ? row : (heldById.get(row.id) ?? row)));
  if (!reinsertMissing) return rows;
  const present = new Set(fetched.map((row) => row.id));
  // Back at the place each one had on screen, lowest first, so the list reads as it did before the refetch.
  for (const entry of [...held].sort((a, b) => a.index - b.index)) {
    if (!present.has(entry.observation.id)) rows.splice(Math.min(entry.index, rows.length), 0, entry.observation);
  }
  return rows;
}

/** "Apr 10, 2026" from the stored date, read as a calendar date so no time zone moves it. Null if there is none. */
function formatCollectedDate(raw: string | null): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(raw ?? '');
  if (!match) return null;
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

/** The Ink confirmation. It names a value and a date (T0), so it is still. No Undo: the API cannot unverify. */
function announceChecked(observation: Observation) {
  const date = formatCollectedDate(observation.collected_at);
  notify({
    message: `${observation.analyte_raw}${date ? `, ${date}` : ''} is now marked as checked`,
    still: true,
  });
}

function documentAttentionHint(doc: Document): string {
  switch (doc.status) {
    case 'pending_ocr':
      return 'OCR is required or unavailable. In Settings, turn on document OCR under Document import and ensure Tesseract is installed. Your server must allow OCR (OCR_ENABLED). Or use a clearer scan.';
    case 'extraction_failed':
      return 'Extraction failed for this file. Try re-importing or a different PDF export.';
    case 'pending':
      return 'Import is still processing or pending extraction.';
    case 'parsed':
      return 'No lab values were extracted or the document is not marked fully verified yet. Check the source in Inbox or review OCR quality.';
    default:
      return 'This document may need review in Inbox.';
  }
}

export function VerificationWorkbench() {
  const { profileId } = useAuthStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedDocId = searchParams.get('doc');
  const mode = searchParams.get('mode');
  const documentReviewMode = !!selectedDocId && mode === 'all';
  // CITE-SRC-001: deep link from an assistant citation chip. A citation is
  // backed by either an observation (a lab value) or a document entity (a
  // finding, impression, diagnosis…) — both must land somewhere real.
  const citedObservationId = searchParams.get('observation');
  const citedEntityId = searchParams.get('entity');
  const [citedNotFound, setCitedNotFound] = useState(false);
  const [selectedRow, setSelectedRow] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [editingObservation, setEditingObservation] = useState<Observation | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saveError, setSaveError] = useState<string | null>(null);
  const [sourcePages, setSourcePages] = useState<DocumentPage[]>([]);
  const [loadingSource, setLoadingSource] = useState(false);
  // A citation applies once per navigation. Without this the effect below
  // re-runs on every `observations` refetch — and verifying a row invalidates
  // that query — so the user's selection snaps back to the cited row.
  const appliedCitationRef = useRef<string | null>(null);
  // The Edit button that opened the dialog. Dialog has no trigger here, so focus goes back to it by hand.
  const editOpenerRef = useRef<HTMLElement | null>(null);

  // Fetch observations that need verification
  // A cited observation is normally already *verified* — that is exactly why the
  // assistant was willing to ground an answer on it — so the default
  // needs_verification filter would never contain it. Widen to the whole
  // document when following a citation.
  const needsVerificationList = !(documentReviewMode || citedObservationId || citedEntityId);
  const observationFilters = needsVerificationList
    ? { profile_id: profileId || '', needs_verification: true }
    : { profile_id: profileId || '', doc_id: selectedDocId || undefined };
  const { data: fetchedObservations, isLoading, isError, error } = useObservations(observationFilters);
  // Rows verified in this visit stay on screen as ink. They belong to one filter: another document, another
  // profile or a citation starts clean.
  const filterKey = JSON.stringify(observationFilters);
  const [held, setHeld] = useState<{ key: string; rows: HeldRow[] }>({ key: '', rows: NO_HELD_ROWS });
  const heldRows = held.key === filterKey ? held.rows : NO_HELD_ROWS;
  const observations = useMemo(
    () => withHeldRows(fetchedObservations, heldRows, needsVerificationList),
    [fetchedObservations, heldRows, needsVerificationList]
  );
  // The confirmation waits for the commit that flips the row, so the toast never says "checked" over a row that
  // still reads "Not yet checked".
  const [justChecked, setJustChecked] = useState<Observation | null>(null);
  useEffect(() => {
    if (!justChecked) return;
    announceChecked(justChecked);
    setJustChecked(null);
  }, [justChecked]);

  const { data: allDocuments = [], isLoading: documentsLoading } = useDocuments({
    profile_id: profileId || '',
  });

  const verifyMutation = useVerifyObservation();
  const verifyDocumentMutation = useVerifyDocument();
  const reprocessMutation = useReprocessDocument();
  // Reprocessing deletes the document's rows and makes new ones, so nothing held here describes the record any more.
  const retryExtraction = (docId: string) =>
    reprocessMutation.mutate(docId, { onSuccess: () => setHeld({ key: '', rows: NO_HELD_ROWS }) });
  const selectedDocument = selectedDocId
    ? allDocuments.find((d) => d.id === selectedDocId) ?? null
    : null;

  // Extracted document entities (HC-M12): verbatim source quotes + verify/reject
  const entityDocId =
    selectedDocId ?? observations?.find((o) => o.id === selectedRow)?.doc_id ?? '';
  const { data: docEntities = [], isLoading: entitiesLoading } =
    useDocumentEntities(entityDocId);
  const entityVerificationMutation = useSetEntityVerification();
  const handleSetEntityVerification = (
    entity: DocumentEntityResponse,
    verified: boolean | null
  ) => {
    entityVerificationMutation.mutate({
      docId: entity.doc_id,
      entityId: entity.id,
      verified,
    });
  };

  /** The server said yes: show the row as checked now, ahead of (and surviving) the refetch, then say so. */
  const markChecked = (observation: Observation, saved: Observation | undefined) => {
    const checked: Observation = { ...observation, ...saved, user_verified: true };
    const index = Math.max(0, observations?.findIndex((row) => row.id === observation.id) ?? 0);
    setHeld((prev) => ({
      key: filterKey,
      rows: [
        ...(prev.key === filterKey ? prev.rows : NO_HELD_ROWS).filter(
          (entry) => entry.observation.id !== observation.id
        ),
        { observation: checked, index },
      ],
    }));
    setJustChecked(checked);
  };

  const handleVerify = async (observation: Observation) => {
    const saved = await verifyMutation.mutateAsync({
      observationId: observation.id,
      data: {},
    });
    markChecked(observation, saved);
  };

  const handleMarkAllVerifiedClick = async () => {
    if (selectedDocId) {
      await verifyDocumentMutation.mutateAsync(selectedDocId);
      return;
    }
    if (!observations?.length) return;
    for (const obs of observations) {
      if (!obs.user_verified) {
        await verifyMutation.mutateAsync({
          observationId: obs.id,
          data: {},
        });
      }
    }
  };

  const handleEdit = (observation: Observation, opener: HTMLElement) => {
    editOpenerRef.current = opener;
    setEditingObservation(observation);
    setEditValue(observation.value?.toString() || observation.value_text || '');
    setSaveError(null);
  };

  const closeEdit = () => {
    setEditingObservation(null);
    setSaveError(null);
    const opener = editOpenerRef.current;
    editOpenerRef.current = null;
    // After the focus trap lets go. A row that left the list with its verify has no opener to return to.
    if (opener) {
      window.setTimeout(() => {
        if (opener.isConnected) opener.focus();
      }, 0);
    }
  };

  // Strict parse: never convert "7,5" or "7.5abc" into a number silently.
  const parseEditValue = (
    raw: string
  ): { kind: 'empty' } | { kind: 'error'; message: string } | { kind: 'number'; value: number } | { kind: 'text'; text: string } => {
    const trimmed = raw.trim();
    if (!trimmed) return { kind: 'empty' };
    if (/^-?\d+(?:\.\d+)?$/.test(trimmed)) return { kind: 'number', value: Number(trimmed) };
    if (/^-?\d+,\d+$/.test(trimmed)) {
      return { kind: 'error', message: 'Use a dot for decimals, for example 7.5' };
    }
    if (/^[<>]/.test(trimmed)) return { kind: 'text', text: raw };
    if (/^[-+]?[\d.]/.test(trimmed)) {
      return { kind: 'error', message: 'Enter a number such as 7.5, or a result like <0.5' };
    }
    return { kind: 'text', text: raw };
  };

  const parsedEdit = parseEditValue(editValue);

  const handleSaveEdit = async () => {
    if (!editingObservation) return;
    if (parsedEdit.kind === 'empty' || parsedEdit.kind === 'error') return;

    try {
      const saved = await verifyMutation.mutateAsync({
        observationId: editingObservation.id,
        data:
          parsedEdit.kind === 'number'
            ? { value: parsedEdit.value }
            : { value_text: parsedEdit.text },
      });
      markChecked(editingObservation, saved);
      closeEdit();
    } catch (err) {
      setSaveError(
        err instanceof ApiError ? err.message : 'Could not save this value. Try again.'
      );
    }
  };

  const handleRowSelect = useCallback(async (observation: Observation) => {
    setSelectedRow(observation.id);

    if (observation.doc_id) {
      setLoadingSource(true);
      try {
        const pages = await apiGet<DocumentPage[]>(
          `/documents/${observation.doc_id}/pages`,
          {}
        );
        setSourcePages(pages);
      } catch {
        setSourcePages([]);
      } finally {
        setLoadingSource(false);
      }
    }
  }, []);

  // FE-04: the notice belongs to one citation, not to the page. Without this,
  // following a second citation that resolves fine still shows "no longer
  // available" from the first one, sitting above a perfectly good selection.
  useEffect(() => {
    setCitedNotFound(false);
    appliedCitationRef.current = null;
  }, [citedObservationId, citedEntityId]);

  // CITE-SRC-001: select the exact observation a citation pointed at.
  useEffect(() => {
    if (!citedObservationId || !observations) return;
    if (appliedCitationRef.current === citedObservationId) return;
    const match = observations.find((o) => o.id === citedObservationId);
    if (match) {
      appliedCitationRef.current = citedObservationId;
      setCitedNotFound(false);
      void handleRowSelect(match);
      document
        .getElementById(`observation-row-${match.id}`)
        ?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    } else {
      // The row was deleted, or the document was reprocessed. Say so rather
      // than silently showing an unrelated selection.
      setCitedNotFound(true);
    }
  }, [citedObservationId, observations, handleRowSelect]);

  // CITE-SRC-001: the entity-backed half of the same deep link. Entities have
  // no row in the observations table, so there is nothing to select — the
  // landing is the highlighted row in Extracted Information plus the page
  // region, which is what the citation was pointing at in the first place.
  useEffect(() => {
    if (!citedEntityId || entitiesLoading) return;
    // No doc means no entity list can be fetched, so "no longer available" is
    // the wrong message — nothing was ever looked up. Citations without an
    // inspectable source are filtered at emit time instead (citationTarget).
    if (!entityDocId) return;
    const match = docEntities.find((e) => e.id === citedEntityId);
    if (match) {
      document
        .getElementById(`entity-row-${match.id}`)
        ?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    } else {
      setCitedNotFound(true);
    }
  }, [citedEntityId, docEntities, entitiesLoading, entityDocId]);

  useEffect(() => {
    // An entity citation needs `doc` to stay in the URL — it is the only thing
    // telling the workbench which document's entities to load.
    if (!selectedDocId || citedObservationId || citedEntityId) return;
    const match = observations?.find((o) => o.doc_id === selectedDocId);
    if (match) {
      void handleRowSelect(match);
      if (!documentReviewMode) {
        const next = new URLSearchParams(searchParams);
        next.delete('doc');
        setSearchParams(next, { replace: true });
      }
    }
  }, [observations, searchParams, setSearchParams, handleRowSelect, selectedDocId, documentReviewMode, citedObservationId, citedEntityId]);

  const handleViewSourceClick = () => {
    if (observations && observations.length > 0) {
      void handleRowSelect(observations[0]);
    }
  };

  const formatRefRange = (observation: Observation) => {
    if (observation.ref_range_text) return observation.ref_range_text;
    if (observation.ref_low !== null && observation.ref_high !== null) {
      return `${observation.ref_low}-${observation.ref_high}`;
    }
    // One limit only: say which side, so "Above the report's range" never sits beside "- mg/dL".
    if (observation.ref_high !== null) return `≤ ${observation.ref_high}`;
    if (observation.ref_low !== null) return `≥ ${observation.ref_low}`;
    return '-';
  };

  // Parse bbox JSON for selected observation
  const selectedObservation = observations?.find((o) => o.id === selectedRow) ?? null;
  const selectedBbox: BoundingBox | null = parseBbox(selectedObservation?.source_bbox_json);

  // The entity a citation pointed at, if any — drives the same page overlay.
  const citedEntity = citedEntityId
    ? docEntities.find((e) => e.id === citedEntityId) ?? null
    : null;

  // Count unverified items
  const unverifiedCount = observations?.filter((o) => !o.user_verified).length ?? 0;
  // On the default list no unverified row is left: the queue has ended, even while the rows verified in this
  // visit are still held on screen as ink (L0 ruling on review round 3, finding 3).
  const queueDone = needsVerificationList && unverifiedCount === 0;

  // What follows the last unverified value: the documents that still need follow-up, or the all-clear.
  const attentionDocuments = documentsLoading
    ? []
    : allDocuments.filter((d) => DOCUMENT_ATTENTION_STATUSES.has(d.status));
  const queueEnd = (
    <>
      {documentsLoading ? (
        <Card>
          <CardContent className="py-16 flex justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-accent" aria-hidden />
            <span className="sr-only">Loading documents…</span>
          </CardContent>
        </Card>
      ) : attentionDocuments.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-status-attention" />
              Documents needing attention
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-ink-secondary">
              There are no lab values waiting in the verification queue. These imports still need
              follow-up (OCR, extraction, or document-level review).
            </p>
            <ul className="divide-y divide-black/6 rounded-xl border border-black/6 bg-surface-muted/30">
              {attentionDocuments.map((doc) => (
                <li key={doc.id} className="p-4 flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-ink truncate">{doc.source || 'Untitled document'}</p>
                    <p className="text-xs text-ink-secondary mt-0.5">
                      {doc.doc_type.replace(/_/g, ' ')} · {doc.status.replace(/_/g, ' ')}
                    </p>
                  </div>
                  <p className="text-xs text-ink-secondary sm:max-w-md shrink-0">
                    {documentAttentionHint(doc)}
                  </p>
                </li>
              ))}
            </ul>
            <p className="text-sm text-ink-secondary">
              Open{' '}
              <Link to="/inbox" className="text-accent font-medium hover:underline">
                Inbox
              </Link>{' '}
              to preview files or re-import. In Settings, check Document import (OCR) if scans are not readable.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-16">
            <div className="text-center">
              <CheckCircle className="w-12 h-12 text-status-verified mx-auto mb-3" />
              <p className="text-lg font-medium text-ink mb-1">All observations verified</p>
              <p className="text-ink-secondary">No items need review at this time.</p>
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64" role="status" aria-live="polite">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
        <span className="sr-only">Loading observations for verification...</span>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-attention mx-auto mb-3" />
          <p className="text-ink-secondary">
            Failed to load observations: {(error as Error)?.message || 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }

  // Empty state — observation queue clear, but documents may still need attention
  if (!observations || observations.length === 0) {
    // An entity citation commonly points at a narrative document — a radiology
    // report, a visit note — which has entities but no lab values at all. The
    // generic "queue is clear" view would drop the user somewhere unrelated to
    // what they clicked, so the citation gets its own landing.
    if (citedEntityId) {
      return (
        <div className="space-y-6">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
              Verification Workbench
            </h1>
            <p className="text-ink-secondary mt-1">
              {selectedDocument?.source
                ? `Cited from ${selectedDocument.source}`
                : 'Cited source'}
            </p>
          </div>

          {citedNotFound && (
            <div
              role="status"
              className="rounded-lg border border-status-caution/40 bg-status-caution/5 px-4 py-3 text-sm"
            >
              That source is no longer available — the finding it pointed to may
              have been deleted, or its document re-extracted.
            </div>
          )}

          {citedEntity?.source_page && (
            <PageImageOverlay
              documentId={citedEntity.doc_id}
              pageNumber={citedEntity.source_page}
              bbox={parseBbox(citedEntity.source_bbox_json)}
            />
          )}

          <EntityDetailView
            entities={docEntities}
            onSetVerification={handleSetEntityVerification}
            verificationPending={entityVerificationMutation.isPending}
            highlightEntityId={citedEntityId}
          />
        </div>
      );
    }

    if (documentReviewMode && selectedDocument) {
      const needsRetry =
        selectedDocument.status === 'pending_ocr' || selectedDocument.status === 'extraction_failed';
      return (
        <div className="space-y-6">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
              Verification Workbench
            </h1>
            <p className="text-ink-secondary mt-1">
              Review and correct extracted values from your documents
            </p>
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-status-attention" />
                {selectedDocument.source || 'Selected document'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-ink-secondary">
                No extracted values are available for this document yet. Status: {selectedDocument.status.replace(/_/g, ' ')}.
              </p>
              <p className="text-sm text-ink-secondary">{documentAttentionHint(selectedDocument)}</p>
              <div className="flex flex-wrap gap-2">
                {needsRetry && (
                  <Button
                    onClick={() => retryExtraction(selectedDocument.id)}
                    disabled={reprocessMutation.isPending}
                    className="gap-2"
                  >
                    {reprocessMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    Continue OCR / Retry extraction
                  </Button>
                )}
                <Button variant="secondary" asChild>
                  <Link to="/inbox">Open Inbox</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
          <EntityDetailView
            entities={docEntities}
            onSetVerification={handleSetEntityVerification}
            verificationPending={entityVerificationMutation.isPending}
            highlightEntityId={citedEntityId}
          />
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Verification Workbench
          </h1>
          <p className="text-ink-secondary mt-1">
            Review and correct extracted values from your documents
          </p>
        </div>

        {queueEnd}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Verification Workbench
          </h1>
          <p className="text-ink-secondary mt-1">
            Review and correct extracted values from your documents
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {documentReviewMode && selectedDocument && (
            <Badge variant="default">
              Reviewing: {selectedDocument.source || 'Document'}
            </Badge>
          )}
          {unverifiedCount > 0 && (
            <Badge variant="caution" className="gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              {unverifiedCount} items need review
            </Badge>
          )}
          <Button
            type="button"
            variant="secondary"
            className="gap-2"
            onClick={handleViewSourceClick}
            disabled={!observations?.length}
          >
            <Eye className="w-4 h-4" />
            View Source
          </Button>
          <Button
            type="button"
            className="gap-2"
            onClick={() => void handleMarkAllVerifiedClick()}
            disabled={
              !observations?.length ||
              queueDone ||
              verifyMutation.isPending ||
              verifyDocumentMutation.isPending
            }
          >
            <CheckCircle className="w-4 h-4" />
            {documentReviewMode ? 'Mark Document Verified' : 'Mark All Verified'}
          </Button>
          {documentReviewMode && selectedDocument && (
            <Button
              type="button"
              variant="secondary"
              className="gap-2"
              onClick={() => retryExtraction(selectedDocument.id)}
              disabled={reprocessMutation.isPending}
            >
              {reprocessMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Retry extraction
            </Button>
          )}
        </div>
      </div>

      {citedNotFound && (
        <div
          role="status"
          className="rounded-lg border border-status-caution/40 bg-status-caution/5 px-4 py-3 text-sm"
        >
          That source is no longer available — the result or finding it pointed
          to may have been deleted, or its document re-extracted.
        </div>
      )}

      {queueDone && !documentsLoading ? queueEnd : null}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="border-b border-black/4">
              <CardTitle className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-ink-secondary" />
                Lab Results
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table role="table" className="block w-full sm:table">
                  <thead role="rowgroup" className="hidden sm:table-header-group">
                    <tr role="row" className="border-b border-black/4 bg-surface-muted/50">
                      <th role="columnheader" className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Test Name
                      </th>
                      <th role="columnheader" className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Value
                      </th>
                      <th role="columnheader" className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Reference Range
                      </th>
                      <th role="columnheader" className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Status
                      </th>
                      <th role="columnheader" className="text-right text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody role="rowgroup" className="block sm:table-row-group">
                    {observations.map((observation) => {
                      const rangeState = rangeStateOf(observation);
                      return (
                      <tr
                        key={observation.id}
                        id={`observation-row-${observation.id}`}
                        role="row"
                        className={cn(
                          'block border-b border-black/4 py-2 transition-colors cursor-pointer sm:table-row sm:py-0',
                          selectedRow === observation.id
                            ? 'bg-accent-subtle'
                            : 'hover:bg-surface-muted/50'
                        )}
                        onClick={() => handleRowSelect(observation)}
                      >
                        <td role="cell" className="block px-4 py-1.5 sm:table-cell sm:py-4">
                          <div className="flex flex-wrap items-center gap-2">
                            <InkMarker verified={observation.user_verified} />
                            <span className="font-medium text-ink">
                              {observation.analyte_raw}
                            </span>
                          </div>
                        </td>
                        <td role="cell" className="block px-4 py-1.5 sm:table-cell sm:py-4">
                          {/* The header row is hidden below sm, so the cell names itself there. */}
                          <span className="mr-1.5 font-sans text-xs text-ink-secondary sm:hidden">Value</span>
                          {/* The tint is a hint, from the same state as the chip below, which carries the meaning in words (HC-UIREV-001). */}
                          <span
                            data-t0=""
                            className={cn(
                              'font-mono font-semibold',
                              valueTintOf(observation)
                            )}
                          >
                            {observation.value ?? observation.value_text ?? '-'}
                          </span>
                          {observation.unit ? (
                            <span data-t0="" className="text-ink-secondary ml-1 text-sm">
                              {observation.unit}
                            </span>
                          ) : null}
                          {rangeState ? (
                            <div className="mt-1">
                              <StatusChip state={rangeState} />
                            </div>
                          ) : null}
                        </td>
                        <td role="cell" className="block px-4 py-1.5 text-sm text-ink-secondary font-mono sm:table-cell sm:py-4">
                          <span className="font-sans text-xs sm:hidden">Range </span>
                          <span data-t0="">
                            {formatRefRange(observation)} {observation.unit}
                          </span>
                        </td>
                        <td role="cell" className="block px-4 py-1.5 sm:table-cell sm:py-4">
                          {/* sm:min-w-[7.5rem]: "Checked by you" is 0.7 px wider than "Not yet checked". Without a floor above both, the column grows on Verify and the auto layout shifts every other column by a fraction of a pixel. */}
                          <div className="flex flex-wrap items-center gap-1.5 sm:min-w-[7.5rem] sm:flex-col sm:items-start">
                            {/* Keyed by state: the old chip leaves and a new one arrives, so no T0 node changes its own text. */}
                            <StatusChip
                              key={observation.user_verified ? 'checked-by-you' : 'not-checked'}
                              state={observation.user_verified ? 'checked-by-you' : 'not-checked'}
                            />
                            <ExtractionConfidenceBadge confidence={observation.extraction_confidence} />
                          </div>
                        </td>
                        <td role="cell" className="block px-4 py-1.5 sm:table-cell sm:py-4 sm:text-right">
                          <div className="flex items-center gap-1 sm:justify-end">
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Edit value"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEdit(observation, e.currentTarget);
                              }}
                            >
                              <Edit3 className="w-4 h-4" />
                            </Button>
                            {/* Verify keeps its width (and leaves an equal gap once checked), so the columns never reflow under a value. */}
                            {observation.user_verified ? (
                              <span aria-hidden="true" className="inline-block w-18 shrink-0" />
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="w-18 shrink-0"
                                aria-label="Verify observation"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleVerify(observation);
                                }}
                                disabled={verifyMutation.isPending}
                              >
                                {verifyMutation.isPending ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  'Verify'
                                )}
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedRow(
                                  expandedRow === observation.id ? null : observation.id
                                );
                              }}
                              aria-label="Expand details"
                            >
                              <ChevronDown
                                className={cn(
                                  'w-4 h-4 transition-transform',
                                  expandedRow === observation.id && 'rotate-180'
                                )}
                              />
                            </Button>
                          </div>
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          {/* OCR Bounding-Box Citation Overlay (OCR-BOX-001). An observation
              selection wins over a cited entity: the user clicked the row. */}
          {selectedObservation?.source_page && selectedObservation?.doc_id ? (
            <PageImageOverlay
              documentId={selectedObservation.doc_id}
              pageNumber={selectedObservation.source_page}
              bbox={selectedBbox}
            />
          ) : citedEntity?.source_page ? (
            <PageImageOverlay
              documentId={citedEntity.doc_id}
              pageNumber={citedEntity.source_page}
              bbox={parseBbox(citedEntity.source_bbox_json)}
            />
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Source Preview</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingSource ? (
                <div className="aspect-3/4 rounded-xl bg-surface-muted flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-accent" />
                </div>
              ) : sourcePages.length > 0 ? (
                <div className="aspect-3/4 rounded-xl bg-surface-muted p-4 overflow-auto">
                  {sourcePages.map((page) => (
                    <div key={page.page_number} className="mb-4">
                      <p className="text-xs font-medium text-ink-secondary mb-2">
                        Page {page.page_number}
                      </p>
                      <p className="text-sm text-ink whitespace-pre-wrap font-mono">
                        {page.text}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="aspect-3/4 rounded-xl bg-surface-muted flex items-center justify-center">
                  <div className="text-center p-6">
                    <FileText className="w-12 h-12 text-ink-tertiary mx-auto mb-3" />
                    <p className="text-sm text-ink-secondary">
                      Select a row to preview the source document location
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <EntityDetailView
            entities={docEntities}
            onSetVerification={handleSetEntityVerification}
            verificationPending={entityVerificationMutation.isPending}
            highlightEntityId={citedEntityId}
          />

          <Card className="bg-status-info-subtle border-status-info/20">
            <CardContent className="p-4">
              <div className="flex gap-3">
                <Info className="w-5 h-5 text-status-info shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-ink text-sm mb-1">
                    Verification Tips
                  </h4>
                  <p className="text-xs text-ink-secondary leading-relaxed">
                    Click any value to edit. Low confidence items are flagged
                    for your review. All changes are tracked with "Edited"
                    badges.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit value: still (M0), because it shows the current value (T0). Focus trap, Escape and the title come from Dialog. */}
      <Dialog
        open={editingObservation !== null}
        onOpenChange={(open) => {
          if (!open) closeEdit();
        }}
        title="Edit Value"
        still
      >
        {editingObservation && (
          <div className="space-y-4">
            <p className="text-sm text-ink-secondary">
              Current value:{' '}
              <span data-t0="" className="font-mono font-semibold text-ink">
                {editingObservation.value ?? editingObservation.value_text ?? '-'}
                {editingObservation.unit ? ` ${editingObservation.unit}` : ''}
              </span>
            </p>
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <Input
                  type="text"
                  label={`New value for ${editingObservation.analyte_raw}`}
                  value={editValue}
                  onChange={(e) => {
                    setEditValue(e.target.value);
                    setSaveError(null);
                  }}
                  error={
                    parsedEdit.kind === 'error' ? parsedEdit.message : (saveError ?? undefined)
                  }
                />
              </div>
              {editingObservation.unit ? (
                <span className="mt-7 rounded-lg bg-surface-muted px-3 py-2.5 text-ink-secondary">
                  {editingObservation.unit}
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="secondary" onClick={closeEdit}>
                Cancel
              </Button>
              <Button
                onClick={handleSaveEdit}
                disabled={
                  verifyMutation.isPending ||
                  parsedEdit.kind === 'empty' ||
                  parsedEdit.kind === 'error'
                }
              >
                {verifyMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : null}
                Save & Verify
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
