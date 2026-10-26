import { forwardRef } from 'react';
import { cn } from '@/utils/cn';
import { Button, type ButtonProps } from './Button';

export interface IconButtonProps extends Omit<ButtonProps, 'aria-label' | 'size'> {
  /** Required: an icon-only control has no visible name, so the type demands one. */
  'aria-label': string;
}

/** Icon-only Button. At least 44 px square (the min-h-target and min-w-target utilities). */
const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, ...props }, ref) => (
    <Button
      ref={ref}
      size="icon"
      className={cn('min-h-target min-w-target', className)}
      {...props}
    />
  )
);
IconButton.displayName = 'IconButton';

export { IconButton };
