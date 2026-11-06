/**
 * OverviewPage: the landing page at /overview (UI-OVERVIEW; plan §3.1, §4.2 Overview row, motion §2.6 S1, data-t0 §2.7).
 *
 * Built from the queries the other pages already use (documents, observations, medications). It adds no endpoint.
 *
 * Before the first import: the Import, Review values, See results checklist. Each step is a working link. The first
 * is marked "Next step" in words, with a static accent border (S2 marks a running process, so it is not used). The
 * cards enter with S1 (ShowcaseReveal), once per session.
 *
 * After the first import: "N values waiting for review", the latest result of each analyte as static text with
 * StatusChips, and the next dose, each linking to its page. There is no S1 here: every count and value carries
 * `data-t0` and sits outside any moving wrapper. To keep a count from changing under the reader, no card is drawn
 * until all three lists have answered, so a count never appears as 0 and then turns into the real number.
 */
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { ShowcaseReveal } from '@/components/ui/ShowcaseReveal';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatusChip, type StatusChipState } from '@/components/ui/StatusChip';
import { useDocuments } from '@/services/documents';
import { useMedications } from '@/services/medications';
import { useObservations } from '@/services/observations';
import { useAuthStore } from '@/stores/authStore';
import { cn } from '@/utils/cn';
import type { Medication, Observation } from '@/services/types';

const STEPS: Array<{ title: string; text: string; link: string; to: string }> = [
  {
    title: 'Import',
    text: 'Add a lab report from a file on this device. Its text is read here.',
    link: 'Import a document',
    to: '/inbox',
  },
  {
    title: 'Review values',
    text: 'Check each value against the page it was read from, and correct anything that was misread.',
    link: 'Review values',
    to: '/verify',
  },
  {
    title: 'See results',
    text: 'See each value over time, next to the reference range from your report.',
    link: 'See results',
    to: '/results',
  },
];

/** How many analytes the latest-results card lists. */
const LATEST_LIMIT = 5;

const HIGH_FLAGS = new Set(['H', 'HH', 'HIGH']);
const LOW_FLAGS = new Set(['L', 'LL', 'LOW']);
// The same words the backend reads as "normal" (api/observations.py _NORMAL_FLAGS).
const NORMAL_FLAGS = new Set(['NORMAL', 'N', 'WNL', 'NO', 'FALSE', '0']);

/**
 * Which side of the report's range a value sits on, in words. This follows the backend's observation_range_status
 * (VALUE-RANGE-COMPARE): a chip is drawn only where the report's flag and the numbers agree. A flag this page does
 * not know (A, ABNORMAL, CRIT, *) is not decided, and neither is a flag that disagrees with the numbers (a normal
 * word on a value outside the range, H on a value inside it, L on a value above it): those get no range chip. With
 * no range to compare, only an H or L flag makes a claim, and no range is never read as "in range".
 */
function rangeStateOf(observation: Observation): StatusChipState | null {
  const flag = (observation.flag ?? '').replace(/[()\s]/g, '').toUpperCase();
  const { value, ref_low: low, ref_high: high } = observation;
  const hasRange = typeof value === 'number' && (low !== null || high !== null);
  let place: 'above' | 'below' | 'inside' | null = null;
  if (typeof value === 'number' && hasRange) {
    if (low !== null && value < low) place = 'below';
    else if (high !== null && value > high) place = 'above';
    else place = 'inside';
  }

  if (HIGH_FLAGS.has(flag)) return place === null || place === 'above' ? 'above-range' : null;
  if (LOW_FLAGS.has(flag)) return place === null || place === 'below' ? 'below-range' : null;
  if (flag !== '' && !NORMAL_FLAGS.has(flag)) return null;
  const printedNormal = flag !== '';
  if (place === 'inside') return 'in-range';
  // A normal word on a value outside the range disagrees with the numbers: no wording is chosen for it.
  if (printedNormal) return null;
  if (place === 'above') return 'above-range';
  if (place === 'below') return 'below-range';
  return null;
}

/** The newest row of each analyte, newest analytes first. A row with no date counts as the oldest. */
function latestPerAnalyte(observations: Observation[]): Observation[] {
  const newest = new Map<string, Observation>();
  for (const row of observations) {
    const kept = newest.get(row.analyte_canonical);
    if (!kept || (row.collected_at ?? '') > (kept.collected_at ?? '')) newest.set(row.analyte_canonical, row);
  }
  return [...newest.values()].sort((a, b) => (b.collected_at ?? '').localeCompare(a.collected_at ?? ''));
}

function valueText(observation: Observation): string {
  if (typeof observation.value === 'number') return `${observation.value} ${observation.unit ?? ''}`.trim();
  return observation.value_text ?? '';
}

function dateText(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

interface NextDose {
  medication: Medication;
  time: string;
  /** 0 is today, 1 tomorrow. */
  daysAhead: number;
  date: Date;
}

/**
 * The next scheduled dose across the active medications. A schedule with `days_of_week` only counts on those days
 * (the API numbers them 0 = Monday, 6 = Sunday). This reads the schedule, not the dose log: it says when a dose is
 * scheduled, not whether one was taken.
 */
function nextDoseOf(medications: Medication[], now: Date): NextDose | null {
  let best: NextDose | null = null;
  for (const medication of medications) {
    if (!medication.is_active) continue;
    for (const schedule of medication.schedules) {
      if (!schedule.is_active) continue;
      const [hours, minutes] = schedule.target_time.split(':').map(Number);
      if (!Number.isFinite(hours) || !Number.isFinite(minutes)) continue;
      for (let daysAhead = 0; daysAhead <= 7; daysAhead += 1) {
        const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() + daysAhead, hours, minutes);
        const weekday = (date.getDay() + 6) % 7;
        if (schedule.days_of_week && !schedule.days_of_week.includes(weekday)) continue;
        if (date.getTime() <= now.getTime()) continue;
        if (!best || date.getTime() < best.date.getTime()) {
          best = { medication, time: schedule.target_time.slice(0, 5), daysAhead, date };
        }
        break;
      }
    }
  }
  return best;
}

function dayWord(next: NextDose): string {
  if (next.daysAhead === 0) return 'Today';
  if (next.daysAhead === 1) return 'Tomorrow';
  return next.date.toLocaleDateString(undefined, { weekday: 'long' });
}

function PageHeader({ text }: { text: string }) {
  return (
    <header>
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">Overview</h1>
      <p className="mt-1 text-ink-secondary">{text}</p>
    </header>
  );
}

function OverviewSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-live="polite">
      <div className="space-y-2">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-72 max-w-full" />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Skeleton className="h-40 rounded-2xl" />
        <Skeleton className="h-40 rounded-2xl" />
        <Skeleton className="h-40 rounded-2xl" />
      </div>
      <span className="sr-only">Loading page...</span>
    </div>
  );
}

function FirstRun() {
  return (
    <div className="space-y-6">
      <PageHeader text="Three steps take you from a lab report to your first results. Everything stays on this device." />
      <div role="list" aria-label="First steps" className="mx-auto max-w-3xl lg:mx-0">
        <ShowcaseReveal id="overview">
          {STEPS.map((step, index) => {
            const current = index === 0;
            return (
              <Card
                key={step.title}
                role="listitem"
                className={cn('mb-4', current && 'border-2 border-accent')}
              >
                <CardContent className="space-y-3 p-5">
                  <div className="flex flex-wrap items-center gap-3">
                    <span
                      aria-hidden="true"
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-muted text-sm font-medium text-ink"
                    >
                      {index + 1}
                    </span>
                    <h2 className="font-display text-lg font-semibold text-ink">{step.title}</h2>
                    {current && <span className="text-sm font-medium text-accent">Next step</span>}
                  </div>
                  <p className="text-ink-secondary">{step.text}</p>
                  <Button asChild variant={current ? 'primary' : 'secondary'}>
                    <Link to={step.to}>{step.link}</Link>
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </ShowcaseReveal>
      </div>
    </div>
  );
}

function CardError({ what }: { what: string }) {
  return (
    <p role="alert" className="text-sm text-ink-secondary">
      {what} could not be loaded. Reloading the page tries again.
    </p>
  );
}

interface DataProps {
  waiting: Observation[] | undefined;
  observations: Observation[] | undefined;
  medications: Medication[] | undefined;
}

function WithData({ waiting, observations, medications }: DataProps) {
  const latest = observations ? latestPerAnalyte(observations).slice(0, LATEST_LIMIT) : undefined;
  const next = medications ? nextDoseOf(medications, new Date()) : undefined;

  return (
    <div className="space-y-6">
      <PageHeader text="Where your records stand." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardContent className="space-y-3 p-5">
            <h2 className="font-display text-lg font-semibold text-ink">Waiting for review</h2>
            {waiting ? (
              <p className="text-ink">
                <span data-t0="" data-testid="overview-waiting-count" className="font-display text-3xl tabular-nums">
                  {waiting.length}
                </span>{' '}
                <span data-t0="" data-testid="overview-waiting-noun">
                  {waiting.length === 1 ? 'value' : 'values'} waiting for review
                </span>
              </p>
            ) : (
              <CardError what="The count" />
            )}
            <Button asChild variant="secondary">
              <Link to="/verify">Review values</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3 p-5">
            <h2 className="font-display text-lg font-semibold text-ink">Latest results</h2>
            {!latest && <CardError what="Your results" />}
            {latest && latest.length === 0 && <p className="text-ink-secondary">No values have been read yet.</p>}
            {latest && latest.length > 0 && (
              <ul className="space-y-3">
                {latest.map((row) => {
                  const range = rangeStateOf(row);
                  const date = dateText(row.collected_at);
                  return (
                    <li
                      key={row.analyte_canonical}
                      data-testid={`overview-latest-${row.analyte_canonical}`}
                      className="space-y-1"
                    >
                      <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <span className="min-w-0 font-medium text-ink [overflow-wrap:anywhere]">{row.analyte_raw}</span>
                        <span data-t0="" className="tabular-nums text-ink [overflow-wrap:anywhere]">
                          {valueText(row)}
                        </span>
                        {date && (
                          <span data-t0="" className="text-xs text-ink-secondary">
                            {date}
                          </span>
                        )}
                      </p>
                      <p className="flex flex-wrap gap-1.5">
                        {range && <StatusChip state={range} />}
                        <StatusChip state={row.user_verified ? 'checked-by-you' : 'not-checked'} />
                      </p>
                    </li>
                  );
                })}
              </ul>
            )}
            <Button asChild variant="secondary">
              <Link to="/results">See results</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3 p-5">
            <h2 className="font-display text-lg font-semibold text-ink">Next dose</h2>
            {next === undefined && <CardError what="Your medications" />}
            {next === null && <p className="text-ink-secondary">No dose is scheduled.</p>}
            {next && (
              <p data-testid="overview-next-dose" className="text-ink">
                <span className="font-medium [overflow-wrap:anywhere]">{next.medication.name}</span>
                {next.medication.dosage_amount !== null && (
                  <>
                    {' '}
                    <span data-t0="" className="tabular-nums">
                      {`${next.medication.dosage_amount} ${next.medication.dosage_unit ?? ''}`.trim()}
                    </span>
                  </>
                )}
                <span className="text-ink-secondary">
                  {' '}
                  {dayWord(next)} at{' '}
                </span>
                <span data-t0="" className="tabular-nums">
                  {next.time}
                </span>
              </p>
            )}
            <Button asChild variant="secondary">
              <Link to="/medications">Medications</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export function OverviewPage() {
  const profileId = useAuthStore((state) => state.profileId) || '';
  const documents = useDocuments({ profile_id: profileId });
  // The same filtered list the Review values page asks for, so the count here is the count there.
  //
  // Before the first import there is nothing to count, and the observation lists are not requested: the answer would
  // be [] and be cached under the keys the Review values and Results pages use, where it stays fresh for 5 minutes
  // after the import. An empty profile id keeps the hook disabled, so nothing is fetched or cached.
  const hasDocuments = (documents.data ?? []).length > 0;
  const listProfileId = hasDocuments ? profileId : '';
  const waiting = useObservations({ profile_id: listProfileId, needs_verification: true });
  const observations = useObservations({ profile_id: listProfileId });
  const medications = useMedications();

  if (documents.isLoading) return <OverviewSkeleton />;
  if (documents.error) {
    return (
      <div className="space-y-6">
        <PageHeader text="Where your records stand." />
        <p role="alert" className="text-ink-secondary">
          Your documents could not be loaded. Reloading the page tries again.
        </p>
      </div>
    );
  }
  if (!hasDocuments) return <FirstRun />;

  // isPending, not isLoading: on the render where the lists are first enabled the fetch has not started yet.
  if (waiting.isPending || observations.isPending || medications.isLoading) return <OverviewSkeleton />;
  // An import or a delete marks the cached lists out of date. While they are fetched again the loading shape stays,
  // so the reader never sees the old count and then the new one.
  if ((waiting.isFetching && waiting.isStale) || (observations.isFetching && observations.isStale)) {
    return <OverviewSkeleton />;
  }
  return <WithData waiting={waiting.data} observations={observations.data} medications={medications.data} />;
}
