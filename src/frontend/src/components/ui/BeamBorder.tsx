import type { HTMLAttributes, ReactNode } from 'react';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { cn } from '@/utils/cn';
import './showcase.css';

export interface BeamBorderProps extends HTMLAttributes<HTMLDivElement> {
  /** True only while a real process runs (plan §2.6, S2). */
  active: boolean;
  children?: ReactNode;
}

/**
 * S2 (plan §2.6): a beam of accent light runs round the border of a card while
 * `active`, and fades out over 240 ms when it stops. Only the border layer
 * animates; the content never does. Under reduced motion the beam is replaced
 * by a static 1 px accent border.
 */
export function BeamBorder({ active, className, children, ...props }: BeamBorderProps) {
  const reduced = useReducedMotion();

  return (
    <div
      {...props}
      className={cn('beam-border relative rounded-lg', className)}
      data-active={active ? 'true' : 'false'}
      data-motion={reduced ? 'reduced' : 'full'}
    >
      {reduced ? (
        <span aria-hidden="true" className="beam-border__frame" />
      ) : (
        <span aria-hidden="true" className="beam-border__beam" />
      )}
      <div className="beam-border__content">{children}</div>
    </div>
  );
}
