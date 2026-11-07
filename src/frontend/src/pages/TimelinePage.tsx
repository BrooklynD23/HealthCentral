/**
 * TimelinePage (HC-M14)
 *
 * One chronological view of the health record: lab observations,
 * classified documents, and medication starts/stops. Each card shows
 * date, type, title, and verification status, and links to the
 * relevant existing page. Undated items are listed separately.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Calendar,
  CalendarOff,
  FlaskConical,
  FileText,
  Loader2,
  Pill,
  ScanLine,
  Microscope,
  History,
  AlertTriangle,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Badge, Button, Card, CardContent, EmptyState, Input } from '@/components/ui';
import { useObservations } from '@/services/observations';
import type { Observation } from '@/services/types';
import { useTimeline } from '@/services/timeline';
import type {
  TimelineEvent,
  TimelineEventType,
  TimelineVerificationStatus,
} from '@/services/timeline';
import { AddToPinboardButton } from '@/components/pinboards/AddToPinboardButton';
import { useAuthStore } from '@/stores/authStore';

const EVENT_TYPE_OPTIONS: { value: TimelineEventType | ''; label: string }[] = [
  { value: '', label: 'All events' },
  { value: 'lab_results', label: 'Lab results' },
  { value: 'imaging', label: 'Imaging' },
  { value: 'pathology', label: 'Pathology' },
  { value: 'visit_notes', label: 'Visit notes' },
  { value: 'medication_start', label: 'Medication starts' },
  { value: 'medication_stop', label: 'Medication stops' },
];

const EVENT_META: Record<
  TimelineEventType,
  { label: string; icon: LucideIcon; link: string; linkLabel: string }
> = {
  lab_results: { label: 'Lab results', icon: FlaskConical, link: '/results', linkLabel: 'View trends' },
  imaging: { label: 'Imaging', icon: ScanLine, link: '/inbox', linkLabel: 'Open in inbox' },
  pathology: { label: 'Pathology', icon: Microscope, link: '/inbox', linkLabel: 'Open in inbox' },
  visit_notes: { label: 'Visit note', icon: FileText, link: '/inbox', linkLabel: 'Open in inbox' },
  medication_start: { label: 'Medication started', icon: Pill, link: '/medications', linkLabel: 'View medications' },
  medication_stop: { label: 'Medication stopped', icon: Pill, link: '/medications', linkLabel: 'View medications' },
};

const VERIFICATION_META: Record<
  TimelineVerificationStatus,
  { label: string; variant: 'verified' | 'caution' | 'attention' | 'default' } | null
> = {
  verified: { label: 'Verified', variant: 'verified' },
  unverified: { label: 'Needs verification', variant: 'caution' },
  mixed: { label: 'Partially verified', variant: 'attention' },
  'n/a': null,
};

const DATE_SOURCE_LABELS: Record<string, string> = {
  document_date: 'document date',
  entity_date: 'date found in document',
  upload_date: 'upload date',
  recorded_date: 'recorded date',
};

/** The name a patient sees for an observation: the same rule as SourceTrace (raw, then canonical). */
function analyteName(observation: Observation): string {
  return observation.analyte_raw || observation.analyte_canonical;
}

interface NamedObservation {
  name: string;
  /** The key the backend title counts analytes by (modules/timeline.py). */
  canonical: string;
}

const byName = (a: NamedObservation, b: NamedObservation) => a.name.localeCompare(b.name, 'en');

/**
 * The analyte names of a lab card: its related ids are observation ids. Each canonical analyte once, so the line agrees
 * with the "(N analytes)" the backend counts; sorted by name, because the backend lists the ids in a random order and
 * two cards must read the same way. An id that matches no observation adds nothing, and is never guessed. Only lab cards
 * name analytes.
 */
function analyteNamesFor(event: TimelineEvent, byId: Map<string, NamedObservation>): string[] {
  if (event.event_type !== 'lab_results') return [];
  const found: NamedObservation[] = [];
  for (const id of event.related_ids) {
    const row = byId.get(id);
    if (row) found.push(row);
  }
  found.sort(byName);
  const seen = new Set<string>();
  const names: string[] = [];
  for (const row of found) {
    if (seen.has(row.canonical)) continue;
    seen.add(row.canonical);
    names.push(row.name);
  }
  return names;
}

function EventCard({ event, analytes }: { event: TimelineEvent; analytes: string[] }) {
  const meta = EVENT_META[event.event_type];
  const verification = VERIFICATION_META[event.verification_status];
  const Icon = meta.icon;
  const needsVerification =
    event.verification_status === 'unverified' || event.verification_status === 'mixed';
  const pinnableItems = event.event_type === 'lab_results'
    ? event.related_ids.map((id) => ({ item_type: 'observation' as const, item_id: id }))
    : event.doc_id
      ? [{ item_type: 'document' as const, item_id: event.doc_id }]
      : [];

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-start gap-4">
          <div className="mt-0.5 rounded-xl bg-surface-muted p-2.5">
            <Icon className="h-5 w-5 text-ink-secondary" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="accent">{meta.label}</Badge>
              {verification && (
                <Badge variant={verification.variant} data-t0 data-timeline-verification>
                  {verification.label}
                </Badge>
              )}
              {pinnableItems.length > 0 && (
                <AddToPinboardButton items={pinnableItems} label={`Add ${event.title} to pinboard`} />
              )}
            </div>
            <p className="mt-1.5 text-sm font-medium text-ink truncate">{event.title}</p>
            {analytes.length > 0 && (
              <p
                data-t0
                data-timeline-analytes
                className="mt-0.5 min-w-0 text-sm text-ink-secondary [overflow-wrap:anywhere]"
              >
                {analytes.join(', ')}
              </p>
            )}
            <p data-t0 data-timeline-date className="mt-0.5 text-xs text-ink-tertiary">
              {event.event_date ? (
                <>
                  {event.event_date}
                  {event.event_date_source && (
                    <> · {DATE_SOURCE_LABELS[event.event_date_source] ?? event.event_date_source}</>
                  )}
                </>
              ) : (
                'No date available'
              )}
            </p>
            <div className="mt-2 flex flex-wrap gap-3 text-xs font-medium">
              <Link to={meta.link} className="text-accent hover:underline">
                {meta.linkLabel}
              </Link>
              {needsVerification && (
                <Link to="/verify" className="text-status-caution hover:underline">
                  Verify
                </Link>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function TimelinePage() {
  const [eventType, setEventType] = useState<TimelineEventType | ''>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const eventTypeSelect = useRef<HTMLSelectElement>(null);

  const {
    data,
    isLoading: timelineLoading,
    isError,
    refetch,
    dataUpdatedAt: timelineUpdatedAt,
  } = useTimeline({
    event_type: eventType,
    date_from: dateFrom,
    date_to: dateTo,
  });

  // Related ids are observation ids, and the timeline carries no names. The observations are asked for unfiltered:
  // the page's date filters would drop the rows an event in another window points at.
  const { profileId } = useAuthStore();
  const {
    data: observations,
    isLoading: observationsLoading,
    dataUpdatedAt: observationsUpdatedAt,
    refetch: refetchObservations,
  } = useObservations({
    profile_id: profileId || '',
  });
  const byId = useMemo(() => {
    const rows = new Map<string, NamedObservation>();
    for (const observation of observations ?? []) {
      rows.set(observation.id, { name: analyteName(observation), canonical: observation.analyte_canonical });
    }
    return rows;
  }, [observations]);

  const events = data?.events ?? [];
  const undated = data?.undated ?? [];

  // The observations are shared with other pages and kept for 5 minutes, and an import does not invalidate them, so a
  // lab card can point at an id the cached answer does not have. Once per visit, when that happens and a cached answer
  // exists (a failed query has none, and a refetch of it must not hold the cards) that is older than the timeline, they are asked for again, and the cards wait for that one answer.
  const [refreshed, setRefreshed] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const hasUnmatched = [...events, ...undated].some(
    (e) => e.event_type === 'lab_results' && e.related_ids.some((id) => !byId.has(id))
  );
  const needsRefresh =
    !!profileId && !refreshed && observationsUpdatedAt > 0 && hasUnmatched && observationsUpdatedAt < timelineUpdatedAt;
  useEffect(() => {
    if (!needsRefresh) return;
    setRefreshed(true);
    setRefreshing(true);
    void refetchObservations({ cancelRefetch: false }).finally(() => setRefreshing(false));
  }, [needsRefresh, refetchObservations]);

  // The names add a line to a card, so the cards wait for the answers: they would move every later card otherwise.
  // Only the first answer of the observations on this visit holds them: the flag is per mount, not the query's own
  // isFetched, which a failed answer from an earlier visit has already set (the cards would paint unnamed and move when
  // the names arrive). A refetch of a failed query after that reads as loading again and must not take the cards away.
  // Plus the one refresh above and a Try again. A failed observations query settles too: the cards render with their
  // backend titles and no names, and the timeline is never hidden for it.
  const [observationsSettled, setObservationsSettled] = useState(false);
  if (!observationsLoading && !observationsSettled) setObservationsSettled(true);
  const holding =
    timelineLoading || (observationsLoading && !observationsSettled) || needsRefresh || refreshing || retrying;
  // A failed timeline shows its alert alone: a spinner beside it would leave when the observations answer and move the
  // alert (error text is T0).
  const showSpinner = holding && !isError;

  // Asks for both again. The button leaves with the error, so focus goes to the first filter rather than to <body>.
  const tryAgain = () => {
    setRetrying(true);
    eventTypeSelect.current?.focus();
    void Promise.allSettled([refetch(), refetchObservations()]).finally(() => setRetrying(false));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
          Timeline
        </h1>
        <p className="mt-1 text-sm text-ink-secondary">
          Everything in your health record, in one chronological view.
        </p>
      </div>

      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink-secondary">Event type</span>
              <select
                ref={eventTypeSelect}
                value={eventType}
                onChange={(e) => setEventType(e.target.value as TimelineEventType | '')}
                className="w-full rounded-xl border border-border bg-surface-elevated px-3 py-2 text-sm text-ink focus:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
              >
                {EVENT_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink-secondary">From</span>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink-secondary">To</span>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </label>
          </div>
        </CardContent>
      </Card>

      {showSpinner && (
        <div className="flex justify-center py-16" role="status" aria-live="polite">
          <Loader2 className="h-6 w-6 motion-safe:animate-spin text-ink-tertiary" />
          <span className="sr-only">Loading timeline...</span>
        </div>
      )}

      {isError && (
        // Error text is T0 (plan section 2.1): a static alert, not an EmptyState, whose entrance would move it.
        <Card data-timeline-error className="border-status-critical/30 bg-status-critical/5">
          <CardContent className="py-10 text-center">
            <div role="alert" data-t0>
              <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-status-critical" aria-hidden="true" />
              <h2 className="font-display text-lg font-medium text-ink">Could not load timeline</h2>
              <p className="mx-auto mt-1 max-w-xs text-sm text-ink-secondary">
                Something went wrong loading your timeline. Please try again.
              </p>
            </div>
            <Button variant="secondary" className="mt-6" onClick={tryAgain}>
              Try again
            </Button>
          </CardContent>
        </Card>
      )}

      {!holding && !isError && events.length === 0 && undated.length === 0 && (
        <EmptyState
          icon={History}
          title="No events yet"
          description="Import documents or add medications to see your health history here."
          action={
            <Button asChild variant="secondary">
              <Link to="/inbox">Import a document</Link>
            </Button>
          }
        />
      )}

      {!holding && events.length > 0 && (
        <section aria-label="Dated events" className="space-y-3">
          <h2 className="flex items-center gap-2 text-sm font-medium text-ink-secondary">
            <Calendar className="h-4 w-4" aria-hidden="true" />
            {events.length} event{events.length === 1 ? '' : 's'}
          </h2>
          <ol className="space-y-3">
            {events.map((event) => (
              <li key={event.event_id}>
                <EventCard event={event} analytes={analyteNamesFor(event, byId)} />
              </li>
            ))}
          </ol>
        </section>
      )}

      {!holding && undated.length > 0 && (
        <section aria-label="Undated items" className="space-y-3">
          <h2 className="flex items-center gap-2 text-sm font-medium text-ink-secondary">
            <CalendarOff className="h-4 w-4" aria-hidden="true" />
            Undated items
          </h2>
          <p className="text-xs text-ink-tertiary">
            These records have no collection date, so they are not shown on the
            timeline above. Verify them to add a date.
          </p>
          <ol className="space-y-3">
            {undated.map((event) => (
              <li key={event.event_id}>
                <EventCard event={event} analytes={analyteNamesFor(event, byId)} />
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
