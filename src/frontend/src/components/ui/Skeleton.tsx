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
        'animate-pulse bg-black/[0.05] dark:bg-white/[0.05]',
        variant === 'text' && 'h-4 w-full rounded',
        variant === 'circular' && 'h-10 w-10 rounded-full',
        variant === 'rectangular' && 'rounded-xl',
        className
      )}
      {...props}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-black/[0.04] bg-white/50 p-6 space-y-4">
      <div className="flex items-center gap-4">
        <Skeleton variant="circular" />
        <div className="space-y-2 flex-1">
          <Skeleton variant="text" className="w-1/3" />
          <Skeleton variant="text" className="w-1/4" />
        </div>
      </div>
      <Skeleton variant="rectangular" className="h-20 w-full" />
    </div>
  );
}

export function ListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-20 w-full rounded-xl border border-black/[0.04] bg-white/50 animate-pulse"
        />
      ))}
    </div>
  );
}
