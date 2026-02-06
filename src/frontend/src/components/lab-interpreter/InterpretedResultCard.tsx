import { useState } from 'react';
import { motion } from 'framer-motion';
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
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { CitationTooltip } from './CitationTooltip';
import { AdviceSection } from './AdviceSection';
import { ReferenceRangeComparison } from './ReferenceRangeComparison';
import { DisclaimerBanner } from './DisclaimerBanner';
import type { InterpretationResponse } from '@/services/types';

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
}

const severityVariant: Record<string, 'verified' | 'caution' | 'attention' | 'info' | 'default'> = {
  normal: 'verified',
  mild: 'caution',
  moderate: 'attention',
  severe: 'attention',
  critical: 'attention',
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
}: InterpretedResultCardProps) {
  const [expanded, setExpanded] = useState(true);
  const prefersReducedMotion = useReducedMotion();

  const variant = severityVariant[interpretation.severity_level] ?? 'default';

  return (
    <motion.div
      initial={prefersReducedMotion ? {} : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
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

          {/* Interpretation Text */}
          <div className="p-4 rounded-xl bg-surface-muted">
            <p className="text-sm text-ink leading-relaxed">
              {interpretation.interpretation_text}
            </p>
            {interpretation.citations.length > 0 && (
              <div className="flex items-center gap-1.5 mt-3">
                {interpretation.citations.map((citation, i) => (
                  <CitationTooltip
                    key={citation.id}
                    citation={citation}
                    index={i}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Physician Review Reason */}
          {interpretation.requires_physician_review &&
            interpretation.physician_review_reason && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-status-attention-subtle border border-status-attention/20">
                <AlertTriangle className="w-4 h-4 text-status-attention flex-shrink-0 mt-0.5" />
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
                  'focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 rounded'
                )}
              >
                {expanded ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
                {expanded ? 'Hide' : 'Show'} Recommendations
              </button>
              {expanded && (
                <AdviceSection adviceText={interpretation.advice_text} />
              )}
            </>
          )}

          {/* Disclaimer */}
          <DisclaimerBanner />

          {/* Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-black/[0.04]">
            <div className="flex items-center gap-3 text-xs text-ink-tertiary">
              <span>Model: {interpretation.model_tier}</span>
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
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  'Regenerate'
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
