import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/utils/cn';
import { MoreSheet } from './MoreSheet';
import { isNavActive, navTabs } from './navConfig';

const TAB_BASE =
  'flex min-h-[56px] w-full flex-col items-center justify-center gap-1 px-1 text-[11px] font-medium leading-tight rounded-xl focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden';

/**
 * The phone tab bar (plan §3.2): it replaces the sidebar below 1024 px, five
 * slots, each at least 56 px tall, above the home indicator.
 */
export function MobileTabBar() {
  const { pathname } = useLocation();

  return (
    <nav
      aria-label="Tab bar"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface-elevated pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <ul className="grid grid-cols-5">
        {navTabs.map((tab) => {
          const Icon = tab.icon;
          const body: ReactNode = (
            <>
              <Icon className="h-5 w-5" aria-hidden="true" />
              <span>{tab.label}</span>
            </>
          );
          if (!tab.to) {
            return (
              <li key={tab.label}>
                <MoreSheet
                  trigger={
                    <button type="button" className={cn(TAB_BASE, 'text-ink-secondary')}>
                      {body}
                    </button>
                  }
                />
              </li>
            );
          }
          const active = isNavActive(pathname, tab.to);
          return (
            <li key={tab.label}>
              <Link
                to={tab.to}
                aria-current={active ? 'page' : undefined}
                className={cn(TAB_BASE, active ? 'text-accent' : 'text-ink-secondary')}
              >
                {body}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
