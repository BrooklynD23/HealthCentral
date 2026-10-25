import { Suspense, lazy, type ComponentProps, type HTMLAttributes } from 'react';
import { cn } from '@/utils/cn';

/**
 * The orb library loads only when an orb mounts (plan §2.6, S3, HC-UISK-004).
 * A static import would put it in the main chunk for every page.
 */
const ThinkingOrbCanvas = lazy(() =>
  import('thinking-orbs').then((mod) => ({ default: mod.ThinkingOrb }))
);

type OrbProps = ComponentProps<typeof ThinkingOrbCanvas>;

export interface ThinkingOrbProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  /** The words a screen reader hears, such as "Reading page 2 of 3". Required. */
  status: string;
  state?: OrbProps['state'];
  size?: OrbProps['size'];
}

/**
 * S3 (plan §2.6): the thinking orb beside a status line. The canvas is
 * decoration and sits in an aria-hidden wrapper; the status text is what is
 * announced. Under reduced motion the library draws its own static frame.
 */
export function ThinkingOrb({ status, state = 'working', size = 20, className, ...props }: ThinkingOrbProps) {
  return (
    <span {...props} className={cn('inline-flex items-center gap-2', className)}>
      <span aria-hidden="true" className="inline-flex shrink-0" style={{ width: size, height: size }}>
        <Suspense fallback={null}>
          <ThinkingOrbCanvas state={state} size={size} theme="auto" />
        </Suspense>
      </span>
      <span role="status" className="text-sm text-ink-secondary">
        {status}
      </span>
    </span>
  );
}
