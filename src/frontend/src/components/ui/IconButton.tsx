import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button, type ButtonProps } from './Button';

export interface IconButtonProps extends Omit<ButtonProps, 'aria-label' | 'size'> {
  /** Required: an icon-only control has no visible name, so the type demands one. */
  'aria-label': string;
}

/**
 * Icon-only Button. At least 44 px square (the min-h-target and min-w-target utilities).
 * While loading, the spinner replaces the icon, so the box does not grow a second glyph.
 */
const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, loading = false, disabled, children, ...props }, ref) => (
    <Button
      ref={ref}
      size="icon"
      className={cn('min-h-target min-w-target', className)}
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      loading={false}
      {...props}
    >
      {loading ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : children}
    </Button>
  )
);
IconButton.displayName = 'IconButton';

export { IconButton };
