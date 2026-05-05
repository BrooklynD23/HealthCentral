import { motion, type HTMLMotionProps, type Variants } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { cn } from '@/utils/cn';

/**
 * Shared motion variants for consistent entrance animations.
 */
export const fadeVariants: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

export const slideUpVariants: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 12 },
};

export const staggerContainerVariants: Variants = {
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
};

/**
 * PageTransition wrapper for consistent route entrance.
 */
export function PageTransition({ children, className, ...props }: HTMLMotionProps<'div'>) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={prefersReducedMotion ? fadeVariants : slideUpVariants}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn('w-full', className)}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * StaggerGroup for list orchestrations.
 */
export function StaggerGroup({ children, className, ...props }: HTMLMotionProps<'div'>) {
  return (
    <motion.div
      initial="initial"
      animate="animate"
      variants={staggerContainerVariants}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * StaggerItem for children within a StaggerGroup.
 */
export function StaggerItem({ children, className, ...props }: HTMLMotionProps<'div'>) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      variants={prefersReducedMotion ? fadeVariants : slideUpVariants}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * Modal variants for consistent overlay motion.
 */
export const modalVariants: Variants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.95 },
};

export const backdropVariants: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};
