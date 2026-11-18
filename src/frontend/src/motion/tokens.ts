/**
 * Motion tokens (plan §2.6). The CSS custom properties in globals.css are the
 * source for styles; this file mirrors them for framer-motion, which takes
 * durations in seconds.
 */

/** One easing family for UI. `linear` is reserved for progress loops. */
export const ease = {
  out: [0.23, 1, 0.32, 1],
  inOut: [0.77, 0, 0.175, 1],
  drawer: [0.32, 0.72, 0, 1],
} as const;

/** Durations in seconds (CSS tokens are in ms). */
export const duration = {
  press: 0.12,
  hover: 0.15,
  sm: 0.18,
  route: 0.2,
  md: 0.24,
  lg: 0.32,
  ink: 0.36,
  draw: 0.64,
  show: 0.48,
} as const;

/** Sheet snap and drag release. No bounce anywhere else. */
export const snappySpring = { type: 'spring', duration: 0.22, bounce: 0 } as const;

/** List stagger: 40 ms per item, cap 6 (T1); 60 ms, cap 8 (S tier). Seconds. */
export const stagger = {
  list: { step: 0.04, cap: 6 },
  show: { step: 0.06, cap: 8 },
} as const;
