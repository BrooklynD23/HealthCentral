/**
 * TimelinePage (HC-M14)
 *
 * One chronological view of the health record: lab observations,
 * classified documents, and medication starts/stops. Each card shows
 * date, type, title, and verification status, and links to the
 * relevant existing page. Undated items are listed separately.
 */

import { useState } from 'react';
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
import { Badge, Card, CardContent, EmptyState, Input } from '@/components/ui';
import { useTimeline } from '@/services/timeline';
import type {
  TimelineEvent,
  TimelineEventType,
  TimelineVerificationStatus,
} from '@/services/timeline';

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
  lab_results: { label: 'Lab results', icon: FlaskConical, link: '/trends', linkLabel: 'View trends' },
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

function EventCard({ event }: { event: TimelineEvent }) {
  const meta = EVENT_META[event.event_type];
  const verification = VERIFICATION_META[event.verification_status];
  const Icon = meta.icon;
  const needsVerification =
    event.verification_status === 'unverified' || event.verification_status === 'mixed';

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
                <Badge variant={verification.variant}>{verification.label}</Badge>
              )}
            </div>
            <p className="mt-1.5 text-sm font-medium text-ink truncate">{event.title}</p>
            <p className="mt-0.5 text-xs text-ink-tertiary">
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

  const { data, isLoading, isError } = useTimeline({
    event_type: eventType,
    date_from: dateFrom,
    date_to: dateTo,
  });

  const events = data?.events ?? [];
  const undated = data?.undated ?? [];

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-6">
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
                value={eventType}
                onChange={(e) => setEventType(e.target.value as TimelineEventType | '')}
                className="w-full rounded-xl border border-black/[0.08] bg-white px-3 py-2 text-sm text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
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

      {isLoading && (
        <div className="flex justify-center py-16" role="status" aria-live="polite">
          <Loader2 className="h-6 w-6 animate-spin text-ink-tertiary" />
          <span className="sr-only">Loading timeline...</span>
        </div>
      )}

      {isError && (
        <EmptyState
          icon={AlertTriangle}
          title="Could not load timeline"
          description="Something went wrong loading your timeline. Please try again."
        />
      )}

      {!isLoading && !isError && events.length === 0 && undated.length === 0 && (
        <EmptyState
          icon={History}
          title="No events yet"
          description="Import documents or add medications to see your health history here."
        />
      )}

      {events.length > 0 && (
        <section aria-label="Dated events" className="space-y-3">
          <h2 className="flex items-center gap-2 text-sm font-medium text-ink-secondary">
            <Calendar className="h-4 w-4" aria-hidden="true" />
            {events.length} event{events.length === 1 ? '' : 's'}
          </h2>
          <ol className="space-y-3">
            {events.map((event) => (
              <li key={event.event_id}>
                <EventCard event={event} />
              </li>
            ))}
          </ol>
        </section>
      )}

      {undated.length > 0 && (
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
                <EventCard event={event} />
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
