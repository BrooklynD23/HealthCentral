import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils/cn';

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 font-medium',
    'rounded-xl transition-all duration-200',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-50',
    'min-h-[44px] min-w-[44px]',
  ],
  {
    variants: {
      variant: {
        primary: [
          'bg-accent text-white shadow-soft',
          'hover:bg-accent-hover hover:shadow-card hover:-translate-y-0.5',
          'active:translate-y-0 active:shadow-soft',
        ],
        secondary: [
          'bg-surface-elevated border border-black/[0.08] text-ink shadow-soft',
          'hover:bg-surface-muted hover:shadow-card hover:-translate-y-0.5',
          'active:translate-y-0 active:shadow-soft',
        ],
        ghost: [
          'text-ink-secondary',
          'hover:bg-black/[0.04] hover:text-ink',
        ],
        danger: [
          'bg-status-attention text-white shadow-soft',
          'hover:bg-status-attention/90 hover:shadow-card hover:-translate-y-0.5',
          'active:translate-y-0',
        ],
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
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
