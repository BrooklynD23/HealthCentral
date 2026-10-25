/**
 * Select (UI-PRIM-CONTROLS): the Radix select, styled with the field tokens.
 * Give SelectTrigger a label (a <label htmlFor> that matches its id, or
 * aria-label) so the field has a name.
 */

import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from 'react';
import * as SelectPrimitive from '@radix-ui/react-select';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '@/utils/cn';

const Select = SelectPrimitive.Root;
const SelectValue = SelectPrimitive.Value;

const SelectTrigger = forwardRef<
  ElementRef<typeof SelectPrimitive.Trigger>,
  ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      'flex h-11 w-full items-center justify-between gap-2 rounded-xl border bg-white px-4 py-2',
      'border-[var(--line-strong)] text-left text-ink',
      'data-[placeholder]:text-ink-tertiary',
      'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent/20 focus-visible:border-accent',
      'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-surface-muted',
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown aria-hidden="true" className="h-4 w-4 shrink-0 text-ink-secondary" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
));
SelectTrigger.displayName = 'SelectTrigger';

// An overlay holds shadow only, never a border too (E1, E2).
const SelectContent = forwardRef<
  ElementRef<typeof SelectPrimitive.Content>,
  ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = 'popper', ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      position={position}
      sideOffset={4}
      className={cn(
        'relative z-50 min-w-[8rem] overflow-hidden rounded-[14px] bg-surface-elevated text-ink shadow-elevated',
        'max-h-[min(20rem,var(--radix-select-content-available-height))]',
        className
      )}
      {...props}
    >
      <SelectPrimitive.Viewport
        className={cn(
          'p-1.5',
          position === 'popper' &&
            'h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]'
        )}
      >
        {children}
      </SelectPrimitive.Viewport>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
));
SelectContent.displayName = 'SelectContent';

const SelectItem = forwardRef<
  ElementRef<typeof SelectPrimitive.Item>,
  ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      'relative flex min-h-target w-full cursor-default select-none items-center rounded-lg py-2 pl-8 pr-3 text-sm text-ink outline-hidden',
      'data-[highlighted]:bg-accent-subtle data-[disabled]:opacity-50',
      className
    )}
    {...props}
  >
    <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check aria-hidden="true" className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
));
SelectItem.displayName = 'SelectItem';

export { Select, SelectValue, SelectTrigger, SelectContent, SelectItem };
