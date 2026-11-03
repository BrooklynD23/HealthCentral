/**
 * SourceTrace: the Source Trace sheet (UI-PROVENANCE, plan section 4.1).
 *
 * Shows where a value came from: the source file, the page, the excerpt with the
 * matching line highlighted, the collected date, the reference range and the read
 * confidence in words. For an unchecked value it offers "It matches, mark as
 * checked" (useVerifyObservation) and a link to Review values. The button is enabled
 * only while an excerpt is on screen and the source has loaded (sourceStatus), so a
 * value is never marked as checked with nothing to compare it with; otherwise it is
 * disabled and a short reason is shown beside it.
 *
 * The content holds T0 values, so the sheet is `still` (M0). The only moving
 * element is the TraceMark, a separate background with no data-t0. The text never
 * moves. The File value is clamped to two lines and always reserves both (full name in
 * its title), ObservationSourceTrace loads the monospace face before the sheet opens, and
 * below 1024 px, where the sheet is anchored to the bottom, the sheet is kept at its full
 * height (min-h-[85dvh], its max-h), so neither the name, the font swap nor the excerpt that arrives later
 * shifts a T0 row. The scrollbar gutter is reserved (scrollbar-gutter: stable), so a classic scrollbar
 * that appears once the excerpt makes the sheet scroll does not narrow the text and re-wrap it.
 * While its own GET is pending, the sheet says "Loading the file name…" or "Loading the excerpt…"
 * as plain text, with no spinner (the sheet is still, and the TraceMark is its only motion). Once that
 * GET settles, or if a caller has nothing to load, a value with nothing to show reads "Source file not
 * available" or "Excerpt not available." That includes a page that has no single matching line.
 */
import { useEffect, useId, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { m } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { Sheet } from '@/components/ui/Sheet';
import { notify } from '@/components/ui/toast';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { ease } from '@/motion/tokens';
import { useDocument, useDocumentPages } from '@/services/documents';
import { useVerifyObservation } from '@/services/observations';
import type { DocumentPage, Observation } from '@/services/types';
import { cn } from '@/utils/cn';

const DRAW_MS = 420;
const DRAW_DELAY_MS = 160;
const FADE_MS = 150;
const DRAW_EASE: [number, number, number, number] = [...ease.out];

/** The face of the excerpt (`font-mono`, weight 400). */
const MONO_FONT = '400 12px "JetBrains Mono"';
const REASON_LOADING = 'Loading the source to compare.';
const REASON_UNAVAILABLE = 'The source is not available to compare, so this cannot be marked here.';

/**
 * The trace mark: a background that draws across its positioned parent once
 * (clip-path, 420 ms after a 160 ms delay). Under reduced motion it fades in over
 * 150 ms. It carries no data-t0, so the stillness probe ignores it (HC-UIPV-006).
 */
export function TraceMark({ className }: { className?: string }) {
  const reduced = useReducedMotion();
  const motion = reduced
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        transition: { duration: FADE_MS / 1000 },
      }
    : {
        initial: { clipPath: 'inset(0 100% 0 0)' },
        animate: { clipPath: 'inset(0 0% 0 0)' },
        transition: { duration: DRAW_MS / 1000, delay: DRAW_DELAY_MS / 1000, ease: DRAW_EASE },
      };

  return (
    <m.span
      aria-hidden="true"
      data-trace-mark="true"
      className={cn('pointer-events-none absolute inset-0 rounded-xs bg-accent/15', className)}
      {...motion}
    />
  );
}

/** What the sheet is shown for. Each field is read as it is; nothing is filled in. */
export interface TraceSource {
  observation: Observation;
  /** The source file's name, when the caller has it. */
  sourceFile?: string | null;
  /** The excerpt lines around the value, in reading order. */
  excerptLines?: string[];
  /** Index into excerptLines of the line that holds the value. Null highlights nothing. */
  matchIndex?: number | null;
}

export interface SourceTraceProps extends TraceSource {
  /**
   * Whether the source behind `excerptLines` is still being fetched, could not be fetched, or is
   * ready. Default 'ready': a caller that passes the excerpt itself has nothing to load.
   */
  sourceStatus?: 'loading' | 'failed' | 'ready';
  /**
   * Whether the document GET (the file name) is still pending, and whether the pages GET (the excerpt)
   * is. Each decides only its own wording, so a failed document GET beside a pending pages GET does not
   * say "Excerpt not available.". Default false: a caller that passes the values itself has nothing to load.
   */
  sourceFileLoading?: boolean;
  excerptLoading?: boolean;
  /** Controlled open state. Omit it and use a `trigger` for uncontrolled use. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: ReactNode;
}

function analyteName(observation: Observation): string {
  return observation.analyte_raw || observation.analyte_canonical;
}

/** "Apr 10, 2026" from the stored calendar date. UTC, so the day never shifts. */
function formatCollected(collectedAt: string | null): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(collectedAt ?? '');
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

function formatRange(observation: Observation): string | null {
  const { ref_low, ref_high, unit, ref_range_text } = observation;
  if (ref_low !== null && ref_high !== null) {
    // "to", not a dash: a negative low ("-2 to 2") reads apart from a hyphen range.
    return `${ref_low} to ${ref_high}${unit ? ` ${unit}` : ''}`;
  }
  return ref_range_text || null;
}

function formatResult(observation: Observation): string | null {
  if (observation.value_text) return observation.value_text;
  if (observation.value === null) return null;
  return `${observation.value}${observation.unit ? ` ${observation.unit}` : ''}`;
}

/** The same bands as ExtractionConfidenceBadge, in words. */
function readConfidenceWords(confidence: number | null): string | null {
  if (confidence === null) return null;
  if (confidence >= 0.8) return 'High';
  if (confidence >= 0.5) return 'Medium';
  return 'Low';
}

export function SourceTrace({
  observation,
  sourceFile = null,
  excerptLines = [],
  matchIndex = null,
  sourceStatus = 'ready',
  sourceFileLoading = false,
  excerptLoading = false,
  open,
  onOpenChange,
  trigger,
}: SourceTraceProps) {
  const name = analyteName(observation);
  const date = formatCollected(observation.collected_at);
  const range = formatRange(observation);
  const result = formatResult(observation);
  const confidence = readConfidenceWords(observation.extraction_confidence);
  const page = observation.source_page;

  const verify = useVerifyObservation();
  const { reset: resetVerify } = verify;
  // The row verified here is kept by id, so a sheet reused for another row does not show it as checked.
  const [checkedId, setCheckedId] = useState<string | null>(null);
  const isChecked = observation.user_verified || checkedId === observation.id;
  // "Mark as checked" says the value matches the report, so there must be a report line to compare.
  const canCompare = sourceStatus === 'ready' && excerptLines.length > 0;
  const reasonId = useId();

  // A different row starts with no verify state: no stale error, no in-flight flag.
  useEffect(() => {
    resetVerify();
  }, [observation.id, resetVerify]);

  // No unverify endpoint exists (be/api/observations.py:384 is verify only), so the
  // confirmation has no Undo.
  const markChecked = () => {
    const observationId = observation.id;
    verify.mutate(
      { observationId, data: {} },
      {
        onSuccess: () => {
          setCheckedId(observationId);
          notify({
            message: `${[name, date].filter(Boolean).join(', ')} is now marked as checked`,
            still: true,
          });
        },
      }
    );
  };

  return (
    // Below 1024 px the sheet grows upward from the bottom edge, so an excerpt that mounts later would move every row above
    // it. min-h-[85dvh] is the bottom sheet's own max-h, so it is the same height before and after, whatever its padding and title.
    // [scrollbar-gutter:stable] is on the same overflow-y-auto element: when the excerpt makes it scroll, a classic scrollbar
    // takes its width from the gutter that was already reserved, not from the text, which would re-wrap.
    <Sheet
      still
      open={open}
      onOpenChange={onOpenChange}
      trigger={trigger}
      title={`Source for ${name}`}
      className="min-h-[85dvh] [scrollbar-gutter:stable]"
    >
      <div className="space-y-5">
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
          <dt className="text-ink-secondary">File</dt>
          {/* Two lines at most, and both always reserved (min-h-10 is two text-sm lines): the name arrives with the document, and a name that wrapped then would push every row below it down. The end of a longer name is cut; the title has all of it. */}
          <dd className="min-h-10 min-w-0 line-clamp-2 break-words text-ink" title={sourceFile ?? undefined}>
            {sourceFile ?? (sourceFileLoading ? 'Loading the file name…' : 'Source file not available')}
          </dd>

          <dt className="text-ink-secondary">Location</dt>
          <dd className="min-w-0 break-words text-ink" data-t0="">
            {page !== null ? `Page ${page}` : 'Page not available'}
          </dd>

          <dt className="text-ink-secondary">Result</dt>
          <dd className="min-w-0 break-words text-ink" data-t0="">
            {result ?? 'Result not available'}
          </dd>

          <dt className="text-ink-secondary">Collected</dt>
          <dd className="min-w-0 break-words text-ink" data-t0="">
            {date ?? 'Collection date not available'}
          </dd>

          <dt className="text-ink-secondary">Range</dt>
          <dd className="min-w-0 break-words text-ink" data-t0="">
            {range ?? 'Reference range not available'}
          </dd>

          <dt className="text-ink-secondary">Read confidence</dt>
          <dd className="min-w-0 break-words text-ink" data-t0="">
            {confidence ?? 'Not available'}
          </dd>
        </dl>

        <section className="space-y-2">
          <h3 className="text-xs font-medium uppercase tracking-wider text-ink-secondary">Excerpt</h3>
          {excerptLines.length > 0 ? (
            <ol className="rounded-lg bg-surface-muted p-3 font-mono text-xs leading-relaxed">
              {excerptLines.map((line, index) => {
                const matched = index === matchIndex;
                return (
                  // The match has a text prefix and a 2 px left border, so it does not rely on the tint alone.
                  <li
                    key={index}
                    className={cn('relative border-l-2 px-2 py-0.5', matched ? 'border-accent' : 'border-transparent')}
                  >
                    {matched ? (
                      <>
                        <span className="sr-only">Matching line: </span>
                        <TraceMark />
                      </>
                    ) : null}
                    <span data-t0="" className="relative whitespace-pre-wrap break-words">
                      {line}
                    </span>
                  </li>
                );
              })}
            </ol>
          ) : (
            <p className="text-sm text-ink-secondary">
              {excerptLoading ? 'Loading the excerpt…' : 'Excerpt not available.'}
            </p>
          )}
          {excerptLines.length > 0 ? (
            <p className="text-sm font-medium text-ink">This is what your report states.</p>
          ) : null}
        </section>

        {isChecked ? (
          <p className="text-sm text-ink-secondary">You have marked this value as checked.</p>
        ) : (
          <div className="space-y-3">
            <Button
              type="button"
              onClick={markChecked}
              disabled={verify.isPending || !canCompare}
              aria-describedby={canCompare ? undefined : reasonId}
            >
              It matches, mark as checked
            </Button>
            {canCompare ? null : (
              <p id={reasonId} className="text-sm text-ink-secondary">
                {sourceStatus === 'loading' ? REASON_LOADING : REASON_UNAVAILABLE}
              </p>
            )}
            {verify.isError ? (
              <p role="alert" className="text-sm text-status-attention">
                It could not be marked as checked. Try again.
              </p>
            ) : null}
            <div>
              <Link
                to={`/verify?observation=${observation.id}`}
                className="text-sm font-medium text-accent underline underline-offset-4"
              >
                Correct it in Review values
              </Link>
            </div>
          </div>
        )}
      </div>
    </Sheet>
  );
}

const EXCERPT_CONTEXT_LINES = 2;
const NO_EXCERPT = { excerptLines: [] as string[], matchIndex: null as number | null };

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * The lines of the report around a value, or nothing. The sheet says "This is what your
 * report states.", so a wrong highlighted line would be a false provenance claim: a line
 * matches only when it names the analyte (case-insensitive) AND holds the value as a
 * whole whitespace-delimited token ("96" is not in "196", "96.5", "-96" or "70-99").
 * Exactly one matching line on the observation's source page gives that line and up to
 * 2 lines either side; zero or several, no source page, or no such page give nothing.
 * An empty analyte or value never matches (`includes('')` would match every line).
 */
export function excerptFromPage(
  pages: readonly DocumentPage[] | undefined,
  observation: Observation
): { excerptLines: string[]; matchIndex: number | null } {
  const { source_page: sourcePage, analyte_raw: analyteRaw, value, value_text: valueText } = observation;
  if (sourcePage === null || !pages) return NO_EXCERPT;
  const page = pages.find((candidate) => candidate.page_number === sourcePage);
  if (!page) return NO_EXCERPT;

  const analyte = (analyteRaw ?? '').trim().toLowerCase();
  const valueToken = (value !== null ? String(value) : (valueText ?? '')).trim();
  if (analyte === '' || valueToken === '') return NO_EXCERPT;

  const valuePattern = new RegExp(`(^|\\s)${escapeRegExp(valueToken)}(\\s|$)`);
  const lines = page.text.split(/\r?\n/);
  const matches: number[] = [];
  lines.forEach((line, index) => {
    if (line.toLowerCase().includes(analyte) && valuePattern.test(line)) matches.push(index);
  });
  if (matches.length !== 1) return NO_EXCERPT;

  const start = Math.max(0, matches[0] - EXCERPT_CONTEXT_LINES);
  const end = Math.min(lines.length, matches[0] + EXCERPT_CONTEXT_LINES + 1);
  return { excerptLines: lines.slice(start, end), matchIndex: matches[0] - start };
}

/**
 * The Source Trace sheet for an observation, opened from `trigger` (SOURCE-TRACE-WIRE).
 * The document and its pages are fetched only once the sheet has been opened, so a page
 * that only offers the trigger makes no request. Opening the sheet writes nothing: the
 * file name and the excerpt come from the stored document. The sheet's own "It matches,
 * mark as checked" button still sends a verify POST when the patient clicks it, but only
 * while both requests have succeeded and an excerpt is on screen: it is disabled, with a
 * reason, while either is loading or failed, when the document has no file name, and when
 * no single line matches.
 */
export function ObservationSourceTrace({
  observation,
  trigger,
}: {
  observation: Observation;
  trigger: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  // The excerpt is set in JetBrains Mono (font-display: swap). Loading it now, not when the sheet opens,
  // keeps the excerpt lines from moving when the face arrives after they mount. Absent in some
  // environments (jsdom), and a failed load only means the fallback face stays.
  useEffect(() => {
    window.document.fonts?.load(MONO_FONT)?.catch(() => undefined);
  }, []);
  const documentId = open ? observation.doc_id : undefined;
  const documentQuery = useDocument(documentId);
  const pagesQuery = useDocumentPages(documentId);
  const document = documentQuery.data;
  const { excerptLines, matchIndex } = excerptFromPage(pagesQuery.data, observation);
  // isSuccess/isError, not data: react-query keeps the old data after a failed refetch.
  let sourceStatus: 'loading' | 'failed' | 'ready' = 'ready';
  if (documentQuery.isError || pagesQuery.isError) sourceStatus = 'failed';
  else if (!documentQuery.isSuccess || !pagesQuery.isSuccess) sourceStatus = 'loading';
  else if (!documentQuery.data.source) sourceStatus = 'failed';

  return (
    <SourceTrace
      open={open}
      onOpenChange={setOpen}
      trigger={trigger}
      observation={observation}
      sourceFile={document?.source ?? null}
      excerptLines={excerptLines}
      matchIndex={matchIndex}
      sourceStatus={sourceStatus}
      sourceFileLoading={documentQuery.isPending}
      excerptLoading={pagesQuery.isPending}
    />
  );
}
