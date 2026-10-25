import { Children, useEffect, useState, type ReactNode } from 'react';
import { m, type Variants } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { duration, ease, stagger } from '@/motion/tokens';

/** The entrance plays on the first visit per session only (plan §2.6, S1). */
const PLAYED_KEY = 'showcase-reveal-played';

const EASE_OUT: [number, number, number, number] = [...ease.out];

/** Seconds before group `index` starts: 60 ms per group, capped at 8 steps. */
export function revealDelay(index: number): number {
  return Math.min(index, stagger.show.cap) * stagger.show.step;
}

function alreadyPlayed(): boolean {
  try {
    return window.sessionStorage.getItem(PLAYED_KEY) === '1';
  } catch {
    // Storage blocked: play the entrance. The content renders either way.
    return false;
  }
}

function rememberPlayed(): void {
  try {
    window.sessionStorage.setItem(PLAYED_KEY, '1');
  } catch {
    // Storage blocked: the entrance plays again on the next mount.
  }
}

// A CSS transform string, not the x/y shorthands: WAAPI offloads `transform`
// (framer-motion 10.18 acceleratedValues), so the rise does not run on the main thread.
const groupVariants: Variants = {
  hidden: { opacity: 0, transform: 'translateY(12px)' },
  show: (index: number) => ({
    opacity: 1,
    transform: 'translateY(0px)',
    transition: { duration: duration.show, ease: EASE_OUT, delay: revealDelay(index) },
  }),
};

// Reduced motion: opacity only, 150 ms, no stagger.
const reducedVariants: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: duration.hover, ease: EASE_OUT } },
};

/**
 * S1 (plan §2.6): each child group rises 12 px and fades in, staggered, on the
 * first visit per session. Wrap only non-T0 content; a T0 value never moves.
 * On later mounts in the same session the groups appear with no transform.
 */
export function ShowcaseReveal({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();
  const [skip] = useState(alreadyPlayed);

  useEffect(() => {
    if (!skip) rememberPlayed();
  }, [skip]);

  // A later mount in the same session has no transform at all, so it takes the opacity-only set.
  const variants = reduced || skip ? reducedVariants : groupVariants;

  return (
    <m.div initial={skip ? false : 'hidden'} animate="show">
      {Children.toArray(children).map((child, index) => (
        <m.div key={index} custom={index} variants={variants}>
          {child}
        </m.div>
      ))}
    </m.div>
  );
}
