import { cn } from '@/utils/cn';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular';
}

export function Skeleton({
  className,
  variant = 'rectangular',
  ...props
}: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse bg-black/5 dark:bg-white/5',
        variant === 'text' && 'h-4 w-full rounded-sm',
        variant === 'circular' && 'h-10 w-10 rounded-full',
        variant === 'rectangular' && 'rounded-xl',
        className
      )}
      {...props}
    />
  );
}

/** A list while its rows load. Its shapes take the surface of the final rows. */
export function ListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-20 w-full rounded-xl border border-black/6 bg-surface-muted animate-pulse"
        />
      ))}
    </div>
  );
}
