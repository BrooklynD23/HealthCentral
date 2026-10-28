/**
 * SourceTrace: the Source Trace sheet (UI-PROVENANCE, plan section 4.1).
 *
 * Shows where a value came from: the source file, the page, the excerpt with the
 * matching line highlighted, the collected date, the reference range and the read
 * confidence in words. For an unchecked value it offers "It matches, mark as
 * checked" (useVerifyObservation) and a link to Review values.
 *
 * The content holds T0 values, so the sheet is `still` (M0). The only moving
 * element is the TraceMark, a separate background with no data-t0. The text never
 * moves.
 */
import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { m } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { Sheet } from '@/components/ui/Sheet';
import { notify } from '@/components/ui/toast';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { ease } from '@/motion/tokens';
import { useVerifyObservation } from '@/services/observations';
import type { Observation } from '@/services/types';
import { cn } from '@/utils/cn';

const DRAW_MS = 420;
const DRAW_DELAY_MS = 160;
const FADE_MS = 150;
const DRAW_EASE: [number, number, number, number] = [...ease.out];

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
    <Sheet still open={open} onOpenChange={onOpenChange} trigger={trigger} title={`Source for ${name}`}>
      <div className="space-y-5">
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
          <dt className="text-ink-secondary">File</dt>
          <dd className="min-w-0 break-words text-ink">{sourceFile ?? 'Source file not available'}</dd>

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
            <p className="text-sm text-ink-secondary">Excerpt not available.</p>
          )}
          <p className="text-sm font-medium text-ink">This is what your report states.</p>
        </section>

        {isChecked ? (
          <p className="text-sm text-ink-secondary">You have marked this value as checked.</p>
        ) : (
          <div className="space-y-3">
            <Button type="button" onClick={markChecked} disabled={verify.isPending}>
              It matches, mark as checked
            </Button>
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
