/**
 * Loads the DOM animation features on demand, so LazyMotion keeps the main
 * chunk small. `m.*` components render without them until this resolves.
 */
export const loadFeatures = () => import('framer-motion').then((mod) => mod.domAnimation);
