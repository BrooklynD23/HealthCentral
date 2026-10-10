/**
 * AchievementsWidget — displays earned and unearned badges in a grid.
 */

import { Award, Lock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, StaggerGroup, StaggerItem } from '@/components/ui';
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

// Backend emits naive UTC ISO strings (no offset); JS would parse them as local time.
function parseUtc(iso: string): Date {
  const time = iso.split('T')[1];
  return new Date(time && !/(Z|[+-]\d{2}(:?\d{2})?)$/i.test(time) ? `${iso}Z` : iso);
}

function BadgeCard({ badge }: { badge: BadgeStatus }) {
  return (
    <div
      className={cn(
        'flex flex-col items-center gap-1.5 rounded-xl p-3 text-center transition-all duration-300',
        badge.earned
          ? 'bg-accent/5 border border-accent/20 shadow-sm hover:shadow-md hover:-translate-y-0.5'
          : 'bg-surface-muted border border-transparent opacity-40 grayscale'
      )}
    >
      <div className="relative">
        <span className="text-2xl" aria-hidden>
          {badge.earned ? (ICON_MAP[badge.icon] ?? '🏅') : ''}
        </span>
        {!badge.earned && (
          <div className="h-8 w-8 flex items-center justify-center bg-black/5 rounded-full">
            <Lock className="w-4 h-4 text-ink-tertiary" />
          </div>
        )}
      </div>
      <p className={cn('text-[10px] font-bold uppercase tracking-tight', badge.earned ? 'text-accent' : 'text-ink-tertiary')}>
        {badge.name}
      </p>
      {badge.earned && badge.earned_at && (
        <p className="text-[9px] text-ink-tertiary font-medium">
          {parseUtc(badge.earned_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
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
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-accent" />
            <span>Achievements</span>
          </div>
          <span className="text-xs font-bold text-ink-secondary bg-surface-muted px-2 py-0.5 rounded-full">
            {earned} / {data.badges.length}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <StaggerGroup className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
          {data.badges.map((badge) => (
            <StaggerItem key={`${badge.id}-${badge.medication_id ?? ''}`}>
              <BadgeCard badge={badge} />
            </StaggerItem>
          ))}
        </StaggerGroup>
      </CardContent>
    </Card>
  );
}
