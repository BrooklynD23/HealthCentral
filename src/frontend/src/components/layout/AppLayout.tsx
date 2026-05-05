import { Outlet } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { PageTransition } from '@/components/ui';
import { useLocation } from 'react-router-dom';

export function AppLayout() {
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      
      <div className="flex-1 flex flex-col pl-64">
        <TopBar />
        
        <main className="flex-1 p-8">
          <AnimatePresence mode="wait">
            <PageTransition
              key={location.pathname}
              className="max-w-7xl mx-auto"
            >
              <Outlet />
            </PageTransition>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
