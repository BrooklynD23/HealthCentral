import { Flame, Trophy } from 'lucide-react';
import { cn } from '@/utils/cn';

interface StreakDisplayProps {
  currentStreak: number;
  longestStreak: number;
  className?: string;
}

export function StreakDisplay({
  currentStreak,
  longestStreak,
  className,
}: StreakDisplayProps) {
  return (
    <div className={cn('flex items-center gap-6', className)}>
      {/* Current Streak */}
      <div className="flex items-center gap-3">
        <div
          className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center',
            currentStreak > 0 ? 'bg-status-caution-subtle' : 'bg-surface-muted'
          )}
        >
          <Flame
            className={cn(
              'w-5 h-5',
              currentStreak > 0 ? 'text-status-caution' : 'text-ink-tertiary'
            )}
          />
        </div>
        <div>
          <p className="text-2xl font-display font-semibold text-ink">
            {currentStreak}
          </p>
          <p className="text-xs text-ink-secondary">Day streak</p>
        </div>
      </div>

      {/* Longest Streak */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-accent-subtle flex items-center justify-center">
          <Trophy className="w-5 h-5 text-accent" />
        </div>
        <div>
          <p className="text-2xl font-display font-semibold text-ink">
            {longestStreak}
          </p>
          <p className="text-xs text-ink-secondary">Best streak</p>
        </div>
      </div>
    </div>
  );
}
