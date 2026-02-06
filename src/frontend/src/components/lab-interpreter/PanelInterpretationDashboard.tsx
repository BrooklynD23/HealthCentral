import { motion } from 'framer-motion';
import {
  Loader2,
  AlertTriangle,
  Link2,
  Brain,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
} from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { CitationTooltip } from './CitationTooltip';
import { AdviceSection } from './AdviceSection';
import { DisclaimerBanner } from './DisclaimerBanner';
import type { PanelInterpretationResponse } from '@/services/types';

interface PanelInterpretationDashboardProps {
  interpretation: PanelInterpretationResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  className?: string;
}

const statusVariant: Record<string, 'verified' | 'caution' | 'attention' | 'default'> = {
  normal: 'verified',
  borderline: 'caution',
  abnormal: 'attention',
  critical: 'attention',
};

export function PanelInterpretationDashboard({
  interpretation,
  isLoading,
  isError,
  className,
}: PanelInterpretationDashboardProps) {
  const prefersReducedMotion = useReducedMotion();

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
            <p className="text-sm text-ink-secondary">Generating panel interpretation...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !interpretation) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center gap-3">
            <AlertTriangle className="w-8 h-8 text-status-attention" />
            <p className="text-sm text-ink-secondary">
              {isError ? 'Failed to load interpretation' : 'No interpretation available'}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const variant = statusVariant[interpretation.overall_status] ?? 'default';

  return (
    <motion.div
      initial={prefersReducedMotion ? {} : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <Card className={cn('overflow-hidden', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2.5">
              <Brain className="w-5 h-5 text-accent" />
              {interpretation.panel_name.toUpperCase()} Panel Interpretation
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={variant}>{interpretation.overall_status}</Badge>
              <Badge variant="default">
                {Math.round(interpretation.confidence_score * 100)}% confidence
              </Badge>
              {interpretation.requires_physician_review && (
                <Badge variant="attention">
                  <AlertTriangle className="w-3 h-3" />
                  Review Needed
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Summary */}
          <div className="p-4 rounded-xl bg-surface-muted">
            <p className="text-sm text-ink leading-relaxed">
              {interpretation.summary_text}
            </p>
            {interpretation.citations.length > 0 && (
              <div className="flex items-center gap-1.5 mt-3">
                {interpretation.citations.map((citation, i) => (
                  <CitationTooltip key={citation.id} citation={citation} index={i} />
                ))}
              </div>
            )}
          </div>

          {/* Relationship Insights */}
          {interpretation.relationship_insights &&
            interpretation.relationship_insights.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Link2 className="w-4 h-4 text-accent" />
                  <h4 className="text-sm font-semibold text-ink">
                    Biomarker Relationships
                  </h4>
                </div>
                <div className="grid gap-2">
                  {interpretation.relationship_insights.map((insight, i) => (
                    <motion.div
                      key={i}
                      initial={prefersReducedMotion ? {} : { opacity: 0, x: -4 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-xl',
                        'bg-surface-elevated border border-black/[0.04]'
                      )}
                    >
                      <Badge
                        variant={statusVariant[insight.status] ?? 'default'}
                        className="flex-shrink-0 mt-0.5"
                      >
                        {insight.status}
                      </Badge>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-ink">
                          {insight.relationship}
                        </p>
                        <p className="text-xs text-ink-secondary mt-0.5">
                          {insight.interpretation}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

          {/* Advice */}
          {interpretation.advice_text && (
            <AdviceSection adviceText={interpretation.advice_text} />
          )}

          {/* Disclaimer */}
          <DisclaimerBanner />

          {/* Meta */}
          <div className="flex items-center gap-3 text-xs text-ink-tertiary pt-2 border-t border-black/[0.04]">
            <span>
              Collected: {new Date(interpretation.collected_at).toLocaleDateString()}
            </span>
            <span>
              {interpretation.observation_ids.length} biomarkers analyzed
            </span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
