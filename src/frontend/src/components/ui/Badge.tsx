import { type HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils/cn';

const badgeVariants = cva(
  [
    'inline-flex items-center gap-1.5 rounded-full',
    'text-xs font-medium px-2.5 py-1',
    'transition-colors duration-200',
  ],
  {
    variants: {
      variant: {
        default: 'bg-surface-muted text-ink-secondary',
        accent: 'bg-accent-subtle text-accent',
        caution: 'bg-status-caution-subtle text-status-caution',
        attention: 'bg-status-attention-subtle text-status-attention',
        verified: 'bg-status-verified-subtle text-status-verified',
        info: 'bg-status-info-subtle text-status-info',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
