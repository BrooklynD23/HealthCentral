import type { ReactNode } from 'react';
import { cn } from '@/utils/cn';

/**
 * Loading text. It breathes with opacity (M12, 1.6 s) and keeps going under
 * reduced motion, because a loader that freezes looks broken. The class is not
 * switched off by the reduced-motion block in globals.css.
 */
export function Pending({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      role="status"
      className={cn('animate-[pulseSoft_1.6s_ease-in-out_infinite] text-sm text-ink-secondary', className)}
    >
      {children}
    </span>
  );
}
