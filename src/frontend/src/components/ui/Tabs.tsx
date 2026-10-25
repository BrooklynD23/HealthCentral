/**
 * Tabs (UI-PRIM-CONTROLS): the Radix tabs. Arrow keys move focus between tabs
 * (roving focus), and each tabpanel is aria-labelledby its tab.
 *
 * The active indicator is a bar on each trigger that scales in over 240 ms
 * (M9, transform only). Under reduced motion it fades over 120 ms instead.
 */

import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import { cn } from '@/utils/cn';

const Tabs = TabsPrimitive.Root;

const TabsList = forwardRef<
  ElementRef<typeof TabsPrimitive.List>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn('flex items-center gap-1 border-b border-[var(--line)]', className)}
    {...props}
  />
));
TabsList.displayName = 'TabsList';

const TabsTrigger = forwardRef<
  ElementRef<typeof TabsPrimitive.Trigger>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'relative inline-flex min-h-target items-center rounded-md px-3 py-2 text-sm font-medium',
      'text-ink-secondary hover:text-ink data-[state=active]:text-ink',
      'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent/20',
      "after:absolute after:inset-x-2 after:-bottom-px after:h-0.5 after:rounded-full after:bg-accent after:content-['']",
      'after:origin-center after:scale-x-0 after:transition-transform after:duration-[var(--dur-md)] after:ease-[var(--ease-out)]',
      'data-[state=active]:after:scale-x-100',
      'motion-reduce:after:scale-x-100 motion-reduce:after:opacity-0 motion-reduce:after:transition-opacity motion-reduce:after:duration-[120ms]',
      'motion-reduce:data-[state=active]:after:opacity-100',
      className
    )}
    {...props}
  />
));
TabsTrigger.displayName = 'TabsTrigger';

const TabsContent = forwardRef<
  ElementRef<typeof TabsPrimitive.Content>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn('mt-4 rounded-xl focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent/20', className)}
    {...props}
  />
));
TabsContent.displayName = 'TabsContent';

export { Tabs, TabsList, TabsTrigger, TabsContent };
