import { useEffect, useRef, useState } from 'react';
import { BookOpen } from 'lucide-react';
import { ObservationSourceTrace, SourceTrace, type TraceSource } from '@/components/results/SourceTrace';
import { Popover } from '@/components/ui/Popover';
import { cn } from '@/utils/cn';
import type { Citation, Observation } from '@/services/types';

export interface CitationTooltipProps {
  citation: Citation;
  index: number;
  /**
   * The observation and its source text, for a caller that already has both: "Open source" then opens the sheet
   * from them. With neither `source` nor `traceObservation` the popover shows the quote only, with no "Open source":
   * a knowledge-base reference has no page, and the popover never invents one.
   */
  source?: TraceSource;
  /**
   * The observation behind this citation, for a caller that has the record but not its source text. "Open source"
   * then opens the Source Trace sheet through ObservationSourceTrace, which fetches the document and its pages only
   * once the sheet is open. Callers pass it only for an observation with a `doc_id`: without one the sheet would wait
   * for a file name that never comes. `source` wins if both are given.
   */
  traceObservation?: Observation;
  /**
   * The title line, shown exactly as given: no case change, so a file name such as "Quest_Lab_Report.pdf" reads as
   * it is. Omit it and the line is the citation's machine type with its first underscore read as a space
   * ("knowledge_base" reads "KNOWLEDGE BASE"), as every other caller shows it.
   */
  title?: string;
}

// min-h-target: on a phone this is the only way to the source, so it is a 44 px target like "Show source".
const OPEN_SOURCE_CLASS =
  'inline-flex min-h-target items-center text-sm font-medium text-accent underline underline-offset-4';

/**
 * A citation chip. Click, tap or Enter opens its quote; hover alone does not
 * (UI-PROVENANCE, HC-UIPV-001). The popover holds a quote, so it is `still` (M0).
 */
export function CitationTooltip({ citation, index, source, traceObservation, title }: CitationTooltipProps) {
  const [open, setOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const chipRef = useRef<HTMLButtonElement>(null);
  const sourceWasOpen = useRef(false);
  const page = (source?.observation ?? traceObservation)?.source_page ?? null;

  // SourceTrace is controlled and has no trigger, so Radix has nothing to return focus to.
  // Return it to the chip once the sheet has closed. Not in the close handler: the sheet's
  // focus trap is still on there and pulls focus back into the sheet.
  useEffect(() => {
    if (sourceWasOpen.current && !sourceOpen) chipRef.current?.focus();
    sourceWasOpen.current = sourceOpen;
  }, [sourceOpen]);

  return (
    <>
      <Popover
        still
        open={open}
        onOpenChange={setOpen}
        label={`Citation ${index + 1}`}
        className="w-64 text-sm"
        trigger={
          <button
            ref={chipRef}
            type="button"
            aria-label={`Citation ${index + 1}: ${citation.text}`}
            className={cn(
              // 44 px hit area around the 20 px chip (UI-PROVENANCE, HC-UIPV-002).
              'inline-flex h-11 w-11 items-center justify-center rounded-full',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1'
            )}
          >
            <span
              data-t0=""
              className={cn(
                'inline-flex h-5 w-5 items-center justify-center rounded-full',
                'bg-accent-subtle text-[10px] font-semibold text-accent'
              )}
            >
              {index + 1}
            </span>
          </button>
        }
      >
        <div className="flex items-start gap-2">
          <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-ink-tertiary" aria-hidden="true" />
          <div className="min-w-0 space-y-1">
            <p
              data-t0=""
              className={cn(
                'text-xs font-medium text-ink-secondary [overflow-wrap:anywhere]',
                // A given title is a name (often a file name): shown as it is. Only the machine type is set in caps.
                title === undefined && 'uppercase tracking-wider'
              )}
            >
              {title ?? citation.type.replace('_', ' ')}
            </p>
            <p data-t0="" className="leading-relaxed text-ink [overflow-wrap:anywhere]">
              {citation.text}
            </p>
            {page !== null ? (
              <p data-t0="" className="text-xs text-ink-secondary">
                Page {page}
              </p>
            ) : null}
            {source ? (
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setSourceOpen(true);
                }}
                className={OPEN_SOURCE_CLASS}
              >
                Open source
              </button>
            ) : traceObservation ? (
              // Rendered inside the popover so the sheet has a trigger to return focus to. The popover stays open
              // under the modal sheet: Escape closes the sheet (focus back on this button), the next Escape the popover.
              <ObservationSourceTrace
                observation={traceObservation}
                trigger={
                  <button type="button" className={OPEN_SOURCE_CLASS}>
                    Open source
                  </button>
                }
              />
            ) : null}
          </div>
        </div>
      </Popover>
      {source ? (
        <SourceTrace
          open={sourceOpen}
          onOpenChange={setSourceOpen}
          observation={source.observation}
          sourceFile={source.sourceFile}
          excerptLines={source.excerptLines}
          matchIndex={source.matchIndex}
        />
      ) : null}
    </>
  );
}
