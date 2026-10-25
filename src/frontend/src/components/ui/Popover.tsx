import type { ReactNode } from 'react';
import * as PopoverPrimitive from '@radix-ui/react-popover';
import { AnimatePresence, m } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { duration, ease } from '@/motion/tokens';
import { cn } from '@/utils/cn';
import { REDUCED_MOTION, useOverlayState, type MotionSpec } from './Dialog';

export interface PopoverProps {
  /** Controlled open state. Omit it and use `defaultOpen` for uncontrolled use. */
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  /**
   * Must be a focusable element, normally a <button>. It opens on click, Enter and
   * Space through the element's own activation. Hover never opens it.
   */
  trigger: ReactNode;
  /** The popover's accessible name (its content has role "dialog"). Required. */
  label: string;
  /** M0 for content that holds T0 data. */
  still?: boolean;
  side?: 'top' | 'right' | 'bottom' | 'left';
  align?: 'start' | 'center' | 'end';
  className?: string;
  children?: ReactNode;
}

const EASE_OUT: [number, number, number, number] = [...ease.out];

/** M3: opacity and scale .96 → 1 from the Radix transform origin, 180 ms; exit 120 ms. */
const POPOVER_MOTION: MotionSpec = {
  initial: { opacity: 0, transform: 'scale(0.96)' },
  animate: { opacity: 1, transform: 'scale(1)' },
  exit: { opacity: 0, transform: 'scale(0.96)', transition: { duration: 0.12, ease: EASE_OUT } },
  transition: { duration: duration.sm, ease: EASE_OUT },
};

/**
 * A non-modal popover anchored to its trigger. Escape closes it and focus returns to
 * the trigger. It does not dispatch the overlay-open event (Dialog, AlertDialog and Sheet do).
 */
export function Popover({
  open,
  defaultOpen,
  onOpenChange,
  trigger,
  label,
  still = false,
  side = 'bottom',
  align = 'center',
  className,
  children,
}: PopoverProps) {
  const { isOpen, setOpen } = useOverlayState({ open, defaultOpen, onOpenChange });
  const reduced = useReducedMotion();
  const motion = still ? {} : reduced ? REDUCED_MOTION : POPOVER_MOTION;

  return (
    <PopoverPrimitive.Root open={isOpen} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>{trigger}</PopoverPrimitive.Trigger>
      <AnimatePresence>
        {isOpen ? (
          <PopoverPrimitive.Portal key="popover" forceMount>
            <PopoverPrimitive.Content
              asChild
              forceMount
              aria-label={label}
              side={side}
              align={align}
              sideOffset={6}
              collisionPadding={8}
            >
              <m.div
                className={cn(
                  'z-[var(--z-modal)] rounded-xl bg-surface-elevated p-4 text-ink shadow-elevated focus:outline-none',
                  className
                )}
                style={{ transformOrigin: 'var(--radix-popover-content-transform-origin)' }}
                {...motion}
              >
                {children}
              </m.div>
            </PopoverPrimitive.Content>
          </PopoverPrimitive.Portal>
        ) : null}
      </AnimatePresence>
    </PopoverPrimitive.Root>
  );
}
