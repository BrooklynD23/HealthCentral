/**
 * BadgeToast — Framer Motion slide-in notification on badge earn.
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/utils/cn';
import type { BadgeInfo } from '@/services/types';

const ICON_MAP: Record<string, string> = {
  spark: '⚡',
  flame: '🔥',
  trophy: '🏆',
  star: '⭐',
  shield: '🛡️',
  heart: '❤️',
};

interface BadgeToastProps {
  badge: BadgeInfo | null;
  onDismiss: () => void;
}

export function BadgeToast({ badge, onDismiss }: BadgeToastProps) {
  useEffect(() => {
    if (badge) {
      const timer = setTimeout(onDismiss, 5000);
      return () => clearTimeout(timer);
    }
  }, [badge, onDismiss]);

  return (
    <AnimatePresence>
      {badge && (
        <motion.div
          initial={{ opacity: 0, y: -50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -50, scale: 0.9 }}
          className={cn(
            'fixed top-4 right-4 z-[60] flex items-center gap-3',
            'rounded-xl bg-surface-elevated p-4 shadow-elevated',
            'border border-accent/20'
          )}
          role="status"
          aria-live="polite"
        >
          <span className="text-2xl" aria-hidden>
            {ICON_MAP[badge.icon] ?? '🏅'}
          </span>
          <div>
            <p className="text-sm font-semibold text-ink">Badge Earned!</p>
            <p className="text-sm text-ink-secondary">{badge.name}</p>
          </div>
          <button
            onClick={onDismiss}
            className="ml-2 text-ink-tertiary hover:text-ink"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
