import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Inbox,
  CheckCircle,
  TrendingUp,
  MessageCircle,
  FileOutput,
  Heart,
} from 'lucide-react';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const navItems = [
  { to: '/inbox', icon: Inbox, label: 'Inbox' },
  { to: '/verify', icon: CheckCircle, label: 'Verify' },
  { to: '/trends', icon: TrendingUp, label: 'Trends' },
  { to: '/explain', icon: MessageCircle, label: 'Explain' },
  { to: '/export', icon: FileOutput, label: 'Export' },
];

export function Sidebar() {
  const location = useLocation();
  const prefersReducedMotion = useReducedMotion();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 bg-white/60 backdrop-blur-xl border-r border-black/[0.06] flex flex-col">
      <div className="p-6 border-b border-black/[0.04]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent/80 flex items-center justify-center shadow-soft">
            <Heart className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-display text-lg font-semibold text-ink tracking-tight">
              HealthCentral
            </h1>
            <p className="text-xs text-ink-secondary">Your health companion</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1" role="navigation" aria-label="Main navigation">
        {navItems.map((item) => {
          const isActive = location.pathname === item.to || 
            (item.to === '/inbox' && location.pathname === '/');
          
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive: linkActive }) =>
                cn(
                  'relative flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors duration-200',
                  'min-h-target focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
                  linkActive || isActive
                    ? 'text-accent'
                    : 'text-ink-secondary hover:text-ink hover:bg-black/[0.03]'
                )
              }
            >
              {isActive && (
                <motion.div
                  layoutId={prefersReducedMotion ? undefined : 'sidebar-active'}
                  className="absolute inset-0 bg-accent-subtle rounded-xl"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
                />
              )}
              <item.icon className="w-5 h-5 relative z-10" />
              <span className="relative z-10">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-black/[0.04]">
        <div className="px-4 py-3 rounded-xl bg-surface-muted">
          <p className="text-xs text-ink-tertiary">
            All data stored locally
          </p>
          <p className="text-xs font-medium text-ink-secondary mt-0.5">
            Offline-first • Private
          </p>
        </div>
      </div>
    </aside>
  );
}
