import { type ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Card, CardContent } from './Card';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardContent className="py-16 text-center">
        {Icon && (
          <div className="mb-4 flex justify-center">
            <div className="rounded-full bg-surface-muted p-4">
              <Icon className="h-8 w-8 text-ink-tertiary" />
            </div>
          </div>
        )}
        <h3 className="font-display text-lg font-medium text-ink mb-1">
          {title}
        </h3>
        <p className="mx-auto max-w-xs text-sm text-ink-secondary mb-6">
          {description}
        </p>
        {action && <div className="flex justify-center">{action}</div>}
      </CardContent>
    </Card>
  );
}
