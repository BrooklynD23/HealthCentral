import { useState, type ReactNode } from 'react';
import {
  Brain,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Eye,
  Loader2,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Button,
} from '@/components/ui';
import { cn } from '@/utils/cn';
import { CitationTooltip } from './CitationTooltip';
import { AdviceSection } from './AdviceSection';
import { ReferenceRangeComparison } from './ReferenceRangeComparison';
import { DisclaimerBanner } from './DisclaimerBanner';
import { formatInterpretationText } from './formatInterpretationText';
import { ObservationSourceTrace } from '@/components/results/SourceTrace';
import type { InterpretationResponse, Observation } from '@/services/types';

interface InterpretedResultCardProps {
  interpretation: InterpretationResponse;
  analyteName?: string;
  value?: number | null;
  unit?: string;
  refLow?: number | null;
  refHigh?: number | null;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
  className?: string;
  /** The value this card interprets. With a doc_id, the card offers "Show source" (SOURCE-TRACE-WIRE). */
  observation?: Observation;
  /**
   * Show each citation expanded (as a named source line, never a quotation) instead of as a chip. The caller sets it
   * from the stricter safety mode (SAFETY-MODE-CITATIONS); the card never reads the mode itself. Absent or false is
   * today's chips.
   */
  alwaysShowSources?: boolean;
}

/**
 * One source, expanded. The line "Source: name, page N" is always there. A quotation is drawn only when the
 * caller has real words from the source: a locator or an id is a place, never a quote (the honesty rule).
 */
export function SourceBlock({
  name,
  page,
  quote,
  marker,
  children,
}: {
  name: string;
  page: number | null;
  quote: string | null;
  /** The citation's number as the answer text and chip show it, e.g. "[1]". Omitted: the line is unchanged. */
  marker?: string;
  children?: ReactNode;
}) {
  return (
    <div className="w-full space-y-1">
      {quote !== null ? (
        <blockquote
          data-t0=""
          className="border-l-2 border-accent pl-3 text-sm italic leading-relaxed text-ink [overflow-wrap:anywhere]"
        >
          {quote}
        </blockquote>
      ) : null}
      <p data-t0="" className="text-xs text-ink-secondary [overflow-wrap:anywhere]">
        {marker ? `${marker} ` : ''}Source: {name}
        {page !== null ? `, page ${page}` : ''}
      </p>
      {children}
    </div>
  );
}

const severityVariant: Record<string, 'verified' | 'caution' | 'attention' | 'info' | 'default'> = {
  normal: 'verified',
  borderline_low: 'caution',
  borderline_high: 'caution',
  abnormal_low: 'attention',
  abnormal_high: 'attention',
  critical_low: 'attention',
  critical_high: 'attention',
  informational: 'info',
};

export function InterpretedResultCard({
  interpretation,
  analyteName,
  value,
  unit,
  refLow,
  refHigh,
  onRegenerate,
  isRegenerating,
  className,
  observation,
  alwaysShowSources = false,
}: InterpretedResultCardProps) {
  const [expanded, setExpanded] = useState(true);

  const variant = severityVariant[interpretation.severity_level] ?? 'default';

  return (
    <div>
      <Card className={cn('overflow-hidden', className)}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2.5">
              <Brain className="w-5 h-5 text-accent" />
              <span>{analyteName ?? 'Lab Interpretation'}</span>
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={variant}>
                {interpretation.severity_level}
              </Badge>
              {interpretation.requires_physician_review && (
                <Badge variant="attention">
                  <AlertTriangle className="w-3 h-3" />
                  Physician Review
                </Badge>
              )}
              <Badge variant="default">
                {Math.round(interpretation.confidence_score * 100)}% confidence
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Reference Range Bar */}
          {value != null && (refLow != null || refHigh != null) && (
            <ReferenceRangeComparison
              value={value}
              refLow={refLow ?? null}
              refHigh={refHigh ?? null}
              unit={unit ?? ''}
            />
          )}

          {/* Interpretation Text. T0: the card appears at once and holds still (no fade, no slide). */}
          <div data-t0 className="p-4 rounded-xl bg-surface-muted">
            <div className="space-y-2">
              {formatInterpretationText(interpretation.interpretation_text).paragraphs.map(
                (runs, i) => (
                  <p key={i} className="text-sm text-ink leading-relaxed">
                    {runs.map((run, j) =>
                      run.bold ? <strong key={j}>{run.text}</strong> : <span key={j}>{run.text}</span>
                    )}
                  </p>
                )
              )}
            </div>
            {(interpretation.citations.length > 0 || observation?.doc_id) && (
              <div className="flex flex-wrap items-center gap-1.5 mt-3">
                {interpretation.citations.map((citation, i) =>
                  alwaysShowSources ? (
                    <SourceBlock
                      key={`${citation.type}:${citation.id}:${i}`}
                      // A card citation's text is a name or a title (modules/interpret.py _generate_citations): a
                      // knowledge-base label, an organisation, a recommendation. It is shown as the source's name,
                      // never as a quotation, and the backend sends no page for it.
                      name={citation.text.trim() || citation.type.replace('_', ' ')}
                      page={null}
                      quote={null}
                    />
                  ) : (
                    <CitationTooltip
                      key={`${citation.type}:${citation.id}:${i}`}
                      citation={citation}
                      index={i}
                    />
                  )
                )}
                {observation?.doc_id ? (
                  <ObservationSourceTrace
                    observation={observation}
                    trigger={
                      <button
                        type="button"
                        className={cn(
                          'inline-flex h-11 items-center rounded-sm px-1 text-sm font-medium text-accent',
                          'underline underline-offset-4 hover:text-accent-hover transition-colors',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2'
                        )}
                      >
                        Show source
                      </button>
                    }
                  />
                ) : null}
              </div>
            )}
          </div>

          {/* Physician Review Reason */}
          {interpretation.requires_physician_review &&
            interpretation.physician_review_reason && (
              <div data-t0 className="flex items-start gap-2 p-3 rounded-xl bg-status-attention-subtle border border-status-attention/20">
                <AlertTriangle className="w-4 h-4 text-status-attention shrink-0 mt-0.5" />
                <p className="text-sm text-ink">
                  {interpretation.physician_review_reason}
                </p>
              </div>
            )}

          {/* Expandable Advice Section */}
          {interpretation.advice_text && (
            <>
              <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                className={cn(
                  'flex items-center gap-1.5 text-sm font-medium text-accent',
                  'hover:text-accent-hover transition-colors',
                  'focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 rounded-sm'
                )}
              >
                {expanded ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
                {expanded ? 'Hide' : 'Show'} questions to ask
              </button>
              {expanded && (
                <AdviceSection adviceText={interpretation.advice_text} />
              )}
            </>
          )}

          {/* Disclaimer */}
          <DisclaimerBanner />

          {/* Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-[var(--line)]">
            <div className="flex items-center gap-3 text-xs text-ink-tertiary">
              <span>
                {interpretation.model_tier === 'template'
                  ? 'Source: knowledge-base template'
                  : `Source: local model (${interpretation.model_tier})`}
              </span>
              <span>
                {new Date(interpretation.created_at).toLocaleDateString()}
              </span>
              {interpretation.viewed_at && (
                <span className="flex items-center gap-1">
                  <Eye className="w-3 h-3" />
                  Viewed
                </span>
              )}
            </div>
            {onRegenerate && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRegenerate}
                disabled={isRegenerating}
                className="text-xs"
              >
                {isRegenerating ? (
                  <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                ) : (
                  'Regenerate'
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
