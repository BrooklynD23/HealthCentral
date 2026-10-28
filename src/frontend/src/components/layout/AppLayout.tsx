import { useState } from 'react';
import { useOutlet } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { PageTransition } from '@/components/ui';
import { useLocation } from 'react-router-dom';

// Keeps the page that was rendered when this wrapper mounted. AnimatePresence
// keeps the exiting page mounted during its exit animation, and a plain <Outlet />
// there would resolve to the new route, so the destination page would mount twice.
function FrozenOutlet() {
  const outlet = useOutlet();
  const [frozen] = useState(() => outlet);
  return frozen;
}

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
              <FrozenOutlet />
            </PageTransition>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
