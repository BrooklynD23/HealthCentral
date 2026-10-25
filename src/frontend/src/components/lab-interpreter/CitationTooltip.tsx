import { useState } from 'react';
import { BookOpen } from 'lucide-react';
import { SourceTrace, type TraceSource } from '@/components/results/SourceTrace';
import { Popover } from '@/components/ui/Popover';
import { cn } from '@/utils/cn';
import type { Citation } from '@/services/types';

export interface CitationTooltipProps {
  citation: Citation;
  index: number;
  /**
   * The observation behind this citation, when the caller has one. Without it the
   * popover shows the quote only: a knowledge-base reference has no page, and the
   * popover never invents one.
   */
  source?: TraceSource;
}

/**
 * A citation chip. Click, tap or Enter opens its quote; hover alone does not
 * (UI-PROVENANCE, HC-UIPV-001). The popover holds a quote, so it is `still` (M0).
 */
export function CitationTooltip({ citation, index, source }: CitationTooltipProps) {
  const [open, setOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const page = source?.observation.source_page ?? null;

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
            <p data-t0="" className="leading-relaxed text-ink">
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
                className="pt-1 text-sm font-medium text-accent underline underline-offset-4"
              >
                Open source
              </button>
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
