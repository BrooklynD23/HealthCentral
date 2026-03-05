/**
 * AchievementsWidget — displays earned and unearned badges in a grid.
 */

import { Award, Lock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useBadges } from '@/services';
import type { BadgeStatus } from '@/services/types';

const ICON_MAP: Record<string, string> = {
  spark: '⚡',
  flame: '🔥',
  trophy: '🏆',
  star: '⭐',
  shield: '🛡️',
  heart: '❤️',
};

function BadgeCard({ badge }: { badge: BadgeStatus }) {
  return (
    <div
      className={cn(
        'flex flex-col items-center gap-1.5 rounded-xl p-3 text-center transition-colors',
        badge.earned
          ? 'bg-accent/5 border border-accent/20'
          : 'bg-surface-muted border border-transparent opacity-50'
      )}
    >
      <span className="text-2xl" aria-hidden>
        {badge.earned ? (ICON_MAP[badge.icon] ?? '🏅') : ''}
      </span>
      {!badge.earned && <Lock className="w-5 h-5 text-ink-tertiary" />}
      <p className="text-xs font-medium text-ink">{badge.name}</p>
      {badge.earned && badge.earned_at && (
        <p className="text-[10px] text-ink-tertiary">
          {new Date(badge.earned_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}

export function AchievementsWidget() {
  const { data, isLoading } = useBadges();

  if (isLoading || !data) return null;

  const earned = data.badges.filter((b) => b.earned).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Award className="w-4 h-4 text-accent" />
          Achievements ({earned}/{data.badges.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-2">
          {data.badges.map((badge) => (
            <BadgeCard key={`${badge.id}-${badge.medication_id ?? ''}`} badge={badge} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
