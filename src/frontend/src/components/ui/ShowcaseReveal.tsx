import { Children, useEffect, useState, type ReactNode } from 'react';
import { m, type Variants } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { duration, ease, stagger } from '@/motion/tokens';

const EASE_OUT: [number, number, number, number] = [...ease.out];

/** Seconds before group `index` starts: 60 ms per group, capped at 8 steps. */
export function revealDelay(index: number): number {
  return Math.min(index, stagger.show.cap) * stagger.show.step;
}

function alreadyPlayed(key: string): boolean {
  try {
    return window.sessionStorage.getItem(key) === '1';
  } catch {
    // Storage blocked: play the entrance. The content renders either way.
    return false;
  }
}

function rememberPlayed(key: string): void {
  try {
    window.sessionStorage.setItem(key, '1');
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
 * first visit per session, per surface (L0 ruling 2026-10-25). `id` names the
 * surface and keys its sessionStorage entry. Wrap only non-T0 content; a T0
 * value never moves. On a later mount of the same surface in the same session
 * the groups appear with no transform.
 */
export function ShowcaseReveal({ id, children }: { id: string; children: ReactNode }) {
  const reduced = useReducedMotion();
  const key = `showcase-reveal:${id}`;
  const [skip] = useState(() => alreadyPlayed(key));

  useEffect(() => {
    if (!skip) rememberPlayed(key);
  }, [skip, key]);

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
