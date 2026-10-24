/**
 * The DOM animation features, loaded on demand by MotionProvider so LazyMotion
 * keeps the main chunk small. `m.*` components render without them until this
 * resolves. Re-exporting `domAnimation` (instead of reading it off the whole
 * framer-motion namespace inside a loader) keeps only these features in the
 * async chunk.
 */
export { domAnimation as default } from 'framer-motion';
