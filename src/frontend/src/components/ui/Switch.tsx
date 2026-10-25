/**
 * Switch (UI-PRIM-CONTROLS): the Radix switch. It renders a button with
 * role="switch" and aria-checked. Give it a name with aria-label or a label.
 */

import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from 'react';
import * as SwitchPrimitive from '@radix-ui/react-switch';
import { cn } from '@/utils/cn';

// The thumb moves with `translate` (the Tailwind v4 translate-x utility sets the
// individual property, so it is named in the transition). Under reduced motion
// the thumb changes position at once and the track colour still fades.
const Switch = forwardRef<
  ElementRef<typeof SwitchPrimitive.Root>,
  ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitive.Root
    ref={ref}
    className={cn(
      'peer inline-flex h-6 w-11 shrink-0 items-center rounded-full border p-px',
      'border-[var(--line-strong)] bg-surface-muted',
      'transition-colors duration-[var(--dur-hover)] ease-[var(--ease-out)]',
      'data-[state=checked]:border-accent data-[state=checked]:bg-accent',
      'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
      'disabled:cursor-not-allowed disabled:opacity-50',
      className
    )}
    {...props}
  >
    <SwitchPrimitive.Thumb
      className={cn(
        'pointer-events-none block h-5 w-5 rounded-full bg-white shadow-soft',
        'translate-x-0 transition-[translate] duration-[var(--dur-hover)] ease-[var(--ease-out)]',
        'data-[state=checked]:translate-x-5',
        'motion-reduce:transition-none'
      )}
    />
  </SwitchPrimitive.Root>
));
Switch.displayName = 'Switch';

export { Switch };
