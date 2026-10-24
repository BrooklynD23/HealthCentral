import type { ReactNode } from 'react';
import { LazyMotion, MotionConfig } from 'framer-motion';
import { loadFeatures } from './features';

/**
 * App-wide motion setup. `strict` makes a leftover `motion.*` element throw,
 * so only `m.*` may be used. `reducedMotion="user"` switches transform
 * animations off when the OS asks for reduced motion.
 */
export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={loadFeatures} strict>
      <MotionConfig reducedMotion="user">{children}</MotionConfig>
    </LazyMotion>
  );
}
