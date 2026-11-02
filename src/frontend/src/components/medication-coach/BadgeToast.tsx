/**
 * BadgeToast: announces a newly earned badge through the app's toaster (notify, UI-PG-MEDS).
 *
 * One badge at a time: the queue owner (MedicationCoach) passes the head of its queue. The toast closes
 * itself after 5 s or when Dismiss is pressed, and onDismiss advances the queue. The toast has no pulsing
 * ring (HC-UIMED-003); the badge is a plain message.
 */

import { useEffect, useRef } from 'react';
import { notify } from '@/components/ui/toast';
import type { BadgeInfo } from '@/services/types';

const ICON_MAP: Record<string, string> = {
  spark: '⚡',
  flame: '🔥',
  trophy: '🏆',
  star: '⭐',
  shield: '🛡️',
  heart: '❤️',
};

const TOAST_MS = 5000;

interface BadgeToastProps {
  badge: BadgeInfo | null;
  onDismiss: () => void;
}

export function BadgeToast({ badge, onDismiss }: BadgeToastProps) {
  // StrictMode runs effects twice in development. This guard announces each badge once.
  const announced = useRef<BadgeInfo | null>(null);

  useEffect(() => {
    if (!badge || announced.current === badge) return;
    announced.current = badge;
    notify({
      message: `${ICON_MAP[badge.icon] ?? '🏅'} New Achievement! ${badge.name}`,
      action: { label: 'Dismiss', onClick: onDismiss },
    });
  }, [badge, onDismiss]);

  // Own effect, so the StrictMode re-run above cannot cancel the timer.
  useEffect(() => {
    if (!badge) return undefined;
    const timer = setTimeout(onDismiss, TOAST_MS);
    return () => clearTimeout(timer);
  }, [badge, onDismiss]);

  return null;
}
