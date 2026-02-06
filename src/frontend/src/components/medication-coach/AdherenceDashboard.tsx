import { Loader2, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/utils/cn';
import { StreakDisplay } from './StreakDisplay';
import type { AdherenceStats } from '@/services/types';

interface AdherenceDashboardProps {
  stats: AdherenceStats | undefined;
  isLoading: boolean;
  isError: boolean;
  className?: string;
}

function AdherenceRing({
  value,
  label,
  size = 80,
}: {
  value: number;
  label: string;
  size?: number;
}) {
  const pct = Math.round(value * 100);
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value * circumference);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(0,0,0,0.06)"
          strokeWidth={6}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={pct >= 80 ? '#7BA387' : pct >= 50 ? '#D4A574' : '#C9857A'}
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="text-center -mt-[calc(50%+16px)] mb-4">
        <p className="text-lg font-display font-semibold text-ink">{pct}%</p>
      </div>
      <p className="text-xs text-ink-secondary">{label}</p>
    </div>
  );
}

export function AdherenceDashboard({
  stats,
  isLoading,
  isError,
  className,
}: AdherenceDashboardProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="py-8">
          <div className="flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-accent" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !stats) {
    return (
      <Card className={className}>
        <CardContent className="py-8">
          <div className="flex flex-col items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-status-attention" />
            <p className="text-sm text-ink-secondary">Failed to load stats</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader>
        <CardTitle className="text-base">Adherence</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Streaks */}
        <StreakDisplay
          currentStreak={stats.current_streak_days}
          longestStreak={stats.longest_streak_days}
        />

        {/* Adherence Rings */}
        <div className="flex items-center justify-around">
          <AdherenceRing
            value={stats.last_7_days_adherence}
            label="Last 7 days"
          />
          <AdherenceRing
            value={stats.last_30_days_adherence}
            label="Last 30 days"
          />
        </div>

        {/* Totals */}
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 rounded-xl bg-surface-muted text-center">
            <p className="text-lg font-display font-semibold text-status-verified">
              {stats.total_doses_taken}
            </p>
            <p className="text-xs text-ink-secondary">Taken</p>
          </div>
          <div className="p-3 rounded-xl bg-surface-muted text-center">
            <p className="text-lg font-display font-semibold text-status-caution">
              {stats.total_doses_skipped}
            </p>
            <p className="text-xs text-ink-secondary">Skipped</p>
          </div>
          <div className="p-3 rounded-xl bg-surface-muted text-center">
            <p className="text-lg font-display font-semibold text-ink">
              {stats.total_doses_expected}
            </p>
            <p className="text-xs text-ink-secondary">Expected</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
