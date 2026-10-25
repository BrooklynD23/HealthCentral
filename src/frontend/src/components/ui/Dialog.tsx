import { useCallback, useEffect, useState, type ReactNode } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { AnimatePresence, m, type TargetAndTransition, type Transition } from 'framer-motion';
import { X } from 'lucide-react';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { duration, ease } from '@/motion/tokens';
import { cn } from '@/utils/cn';

/** Document event that UI-PRIM-FEEDBACK's toaster listens for (DF-3, HC-UIFB-004). */
export const OVERLAY_OPEN_EVENT = 'asclexis:overlay-open';

export interface DialogProps {
  /** Controlled open state. Omit it and use `defaultOpen` for uncontrolled use. */
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Rendered as the Radix trigger (asChild). */
  trigger?: ReactNode;
  /**
   * Required: the overlay's accessible name. Without it the title guard logs
   * an error, and the tests fail (HC-UIOV-003).
   */
  title: ReactNode;
  description?: ReactNode;
  /** M0 for content that holds T0 data: no opacity, scale or translate on the content. */
  still?: boolean;
  className?: string;
  children?: ReactNode;
}

export interface MotionSpec {
  initial?: TargetAndTransition;
  animate?: TargetAndTransition;
  exit?: TargetAndTransition;
  transition?: Transition;
}

export type ModalVariant = 'dialog' | 'sheet-bottom' | 'sheet-side';

// Radix-independent copies of the tokens in src/motion/tokens.ts, typed as framer's Easing.
const EASE_OUT: [number, number, number, number] = [...ease.out];
const EASE_DRAWER: [number, number, number, number] = [...ease.drawer];

/** M0: no motion props at all. */
const STILL: MotionSpec = {};

/** Reduced motion, every overlay: opacity only, 150 ms (plan §2.6). */
export const REDUCED_MOTION: MotionSpec = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.15, ease: EASE_OUT },
};

/** The scrim may still fade under `still`: it is not an ancestor of the content. */
const SCRIM: MotionSpec = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.2, ease: EASE_OUT },
};

/** M4: opacity and scale .97 → 1, 320 ms; exit 200 ms. */
const DIALOG_MOTION: MotionSpec = {
  initial: { opacity: 0, transform: 'scale(0.97)' },
  animate: { opacity: 1, transform: 'scale(1)' },
  exit: { opacity: 0, transform: 'scale(0.97)', transition: { duration: 0.2, ease: EASE_OUT } },
  transition: { duration: duration.lg, ease: EASE_OUT },
};

/** M5: slide in on the drawer curve; exit at 0.66 of the enter duration (token rule). */
function sheetMotion(axis: 'translateX' | 'translateY'): MotionSpec {
  return {
    initial: { transform: `${axis}(100%)` },
    animate: { transform: `${axis}(0%)` },
    exit: {
      transform: `${axis}(100%)`,
      transition: { duration: duration.lg * 0.66, ease: EASE_DRAWER },
    },
    transition: { duration: duration.lg, ease: EASE_DRAWER },
  };
}

const MOTION: Record<ModalVariant, MotionSpec> = {
  dialog: DIALOG_MOTION,
  'sheet-bottom': sheetMotion('translateY'),
  'sheet-side': sheetMotion('translateX'),
};

const VARIANT_CLASS: Record<ModalVariant, string> = {
  dialog: 'inset-x-4 top-1/2 mx-auto max-w-md -translate-y-1/2 rounded-xl',
  'sheet-bottom': 'inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto rounded-t-2xl',
  'sheet-side': 'inset-y-0 right-0 w-full max-w-md overflow-y-auto',
};

/** Open/close state that works both controlled (`open`) and uncontrolled (`defaultOpen`). */
export function useOverlayState({
  open,
  defaultOpen = false,
  onOpenChange,
}: Pick<DialogProps, 'open' | 'defaultOpen' | 'onOpenChange'>) {
  const [uncontrolled, setUncontrolled] = useState(defaultOpen);
  const isOpen = open ?? uncontrolled;
  const setOpen = useCallback(
    (next: boolean) => {
      if (open === undefined) setUncontrolled(next);
      onOpenChange?.(next);
    },
    [open, onOpenChange]
  );
  return { isOpen, setOpen };
}

/** Dispatches OVERLAY_OPEN_EVENT on document each time the overlay opens. */
export function useOverlayOpenEvent(isOpen: boolean) {
  useEffect(() => {
    if (isOpen) document.dispatchEvent(new CustomEvent(OVERLAY_OPEN_EVENT));
  }, [isOpen]);
}

export interface ModalProps extends DialogProps {
  /** Named in the title guard message. */
  name: string;
  variant: ModalVariant;
  role?: 'dialog' | 'alertdialog';
  /** AlertDialog: an outside click does not dismiss. Escape still does. */
  dismissOnOutsideClick?: boolean;
  showClose?: boolean;
}

/** Shared by Dialog, AlertDialog and Sheet. The variant picks the layout and the motion. */
export function Modal({
  name,
  variant,
  role = 'dialog',
  dismissOnOutsideClick = true,
  showClose = true,
  still = false,
  className,
  trigger,
  title,
  description,
  children,
  ...state
}: ModalProps) {
  const { isOpen, setOpen } = useOverlayState(state);
  const reduced = useReducedMotion();
  const hasTitle = Boolean(title);
  const hasHeader = hasTitle || Boolean(description);
  useOverlayOpenEvent(isOpen);

  useEffect(() => {
    if (isOpen && !hasTitle) {
      console.error(
        `\`${name}\` requires a \`title\` prop: an overlay with no title has no accessible name.`
      );
    }
  }, [isOpen, hasTitle, name]);

  const motion = still ? STILL : reduced ? REDUCED_MOTION : MOTION[variant];
  const blockOutside = dismissOnOutsideClick ? undefined : (event: Event) => event.preventDefault();

  return (
    <DialogPrimitive.Root open={isOpen} onOpenChange={setOpen}>
      {trigger ? <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger> : null}
      <AnimatePresence>
        {isOpen ? (
          <DialogPrimitive.Portal key="modal" forceMount>
            <DialogPrimitive.Overlay asChild forceMount>
              <m.div
                className="fixed inset-0 z-[var(--z-modal)] bg-black/40"
                initial={SCRIM.initial}
                animate={SCRIM.animate}
                exit={SCRIM.exit}
                transition={SCRIM.transition}
              />
            </DialogPrimitive.Overlay>
            <DialogPrimitive.Content
              asChild
              forceMount
              role={role}
              aria-modal="true"
              onPointerDownOutside={blockOutside}
              onInteractOutside={blockOutside}
            >
              <m.div
                className={cn(
                  'fixed z-[var(--z-modal)] bg-surface-elevated p-6 text-ink shadow-elevated focus:outline-none',
                  VARIANT_CLASS[variant],
                  className
                )}
                {...motion}
              >
                {title ? (
                  <DialogPrimitive.Title className="pr-8 text-lg font-semibold text-ink">
                    {title}
                  </DialogPrimitive.Title>
                ) : null}
                {description ? (
                  <DialogPrimitive.Description className="mt-1 text-sm text-ink-secondary">
                    {description}
                  </DialogPrimitive.Description>
                ) : null}
                <div className={hasHeader ? 'mt-4' : undefined}>{children}</div>
                {showClose ? (
                  <DialogPrimitive.Close
                    aria-label="Close"
                    className="absolute right-4 top-4 rounded-md p-1 text-ink-secondary hover:text-ink focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </DialogPrimitive.Close>
                ) : null}
              </m.div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        ) : null}
      </AnimatePresence>
    </DialogPrimitive.Root>
  );
}

/** A modal dialog centred on screen. Focus is trapped, Escape closes, focus returns to the trigger. */
export function Dialog(props: DialogProps) {
  return <Modal {...props} name="Dialog" variant="dialog" />;
}
