import { type ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Card, CardContent } from './Card';
import { ShowcaseReveal } from './ShowcaseReveal';

interface EmptyStateProps {
  icon?: LucideIcon;
  /** Static line art, drawn with strokes. Decorative: it is hidden from assistive technology. */
  illustration?: ReactNode;
  title: string;
  description: string;
  /** Optional. When given, it should be a real button or link. */
  action?: ReactNode;
  className?: string;
}

/**
 * Empty state (plan §2.6 and §7.7). The illustration, the sentence and the
 * action enter together as S1 groups, once per session. The action stays
 * optional (L0 ruling 1): the nine existing call sites compile unchanged.
 */
export function EmptyState({
  icon: Icon,
  illustration,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardContent className="py-16 text-center">
        <ShowcaseReveal>
          {illustration && (
            <div aria-hidden="true" className="mb-4 flex justify-center">
              {illustration}
            </div>
          )}
          {Icon && (
            <div className="mb-4 flex justify-center">
              <div className="rounded-full bg-surface-muted p-4">
                <Icon className="h-8 w-8 text-ink-tertiary" />
              </div>
            </div>
          )}
          <div>
            <h3 className="font-display text-lg font-medium text-ink mb-1">
              {title}
            </h3>
            <p className="mx-auto max-w-xs text-sm text-ink-secondary mb-6">
              {description}
            </p>
          </div>
          {action && <div className="flex justify-center">{action}</div>}
        </ShowcaseReveal>
      </CardContent>
    </Card>
  );
}
