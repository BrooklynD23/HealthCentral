import { Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { useReducedMotion } from '@/hooks/useReducedMotion';

export function AppLayout() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      
      <div className="flex-1 flex flex-col pl-64">
        <TopBar />
        
        <main className="flex-1 p-8">
          <motion.div
            initial={prefersReducedMotion ? {} : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="max-w-7xl mx-auto"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  );
}
