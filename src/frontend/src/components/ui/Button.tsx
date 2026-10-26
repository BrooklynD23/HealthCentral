import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';
import { cn } from '@/utils/cn';

// Transitions name their properties. Press (M1) is scale .97 on :active for
// 120 ms and colour only under reduced motion. Hover is colour only (M2), with
// no lift. The focus ring is a box-shadow and is not in the transition list, so
// it appears on the first frame. `scale` sits next to `transform` because the
// scale-[.97] utility sets the individual scale property.
const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 font-medium',
    'rounded-xl',
    'transition-[transform,scale,background-color,color] duration-[var(--dur-hover)] ease-[var(--ease-out)]',
    'active:scale-[.97] active:duration-[var(--dur-press)]',
    'motion-reduce:active:scale-100',
    'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-50',
    'min-h-target min-w-target',
  ],
  {
    variants: {
      variant: {
        primary: ['bg-accent text-white shadow-soft', 'hover:bg-accent-hover'],
        secondary: [
          'bg-surface-elevated border border-black/8 text-ink shadow-soft',
          'hover:bg-surface-muted',
        ],
        ghost: ['text-ink-secondary', 'hover:bg-black/4 hover:text-ink'],
        danger: [
          'bg-status-attention text-[var(--on-status)] shadow-soft',
          'hover:bg-status-attention/90',
        ],
        link: ['text-accent underline underline-offset-4', 'hover:text-accent-hover'],
      },
      size: {
        sm: 'px-3 py-2 text-sm',
        md: 'px-4 py-2.5 text-sm',
        lg: 'px-6 py-3 text-base',
        icon: 'p-2.5',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  /**
   * Sets aria-busy and disables the button, and shows a spinner before the
   * label. With asChild the spinner is not added (Slot takes one child);
   * aria-busy and disabled still apply.
   */
  loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant, size, asChild = false, loading = false, disabled, children, ...props },
    ref
  ) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        aria-busy={loading || undefined}
        disabled={disabled || loading}
        {...props}
      >
        {loading && !asChild ? (
          <>
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            {children}
          </>
        ) : (
          children
        )}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
