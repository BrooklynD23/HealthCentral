/**
 * BadgeToast — Framer Motion slide-in notification on badge earn.
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { BadgeInfo } from '@/services/types';
import { useReducedMotion } from '@/hooks/useReducedMotion';

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
  const prefersReducedMotion = useReducedMotion();

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
          initial={prefersReducedMotion ? { opacity: 0, y: 20 } : { opacity: 0, y: -50, scale: 0.9, rotate: -5 }}
          animate={{ opacity: 1, y: 0, scale: 1, rotate: 0 }}
          exit={prefersReducedMotion ? { opacity: 0, scale: 0.95 } : { opacity: 0, y: -20, scale: 0.9 }}
          transition={{ type: 'spring', damping: 20, stiffness: 300 }}
          className={cn(
            'fixed top-4 right-4 z-[60] flex items-center gap-4',
            'rounded-2xl bg-white p-4 shadow-elevated',
            'border border-accent/20 min-w-[300px]'
          )}
          role="status"
          aria-live="polite"
        >
          <div className="relative">
            <div className="absolute inset-0 bg-accent/10 rounded-full animate-ping scale-150 opacity-20" />
            <span className="text-3xl relative z-10 block" aria-hidden>
              {ICON_MAP[badge.icon] ?? '🏅'}
            </span>
          </div>
          <div className="flex-1">
            <p className="text-xs font-bold text-accent uppercase tracking-wider mb-0.5">New Achievement!</p>
            <p className="text-sm font-semibold text-ink leading-tight">{badge.name}</p>
          </div>
          <button
            onClick={onDismiss}
            className="h-8 w-8 flex items-center justify-center rounded-lg text-ink-tertiary hover:text-ink hover:bg-black/[0.04] transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
