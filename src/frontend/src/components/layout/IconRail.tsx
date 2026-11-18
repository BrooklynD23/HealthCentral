import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/utils/cn';
import { MoreSheet } from './MoreSheet';
import { isNavActive, navTabs } from './navConfig';

const ITEM_BASE =
  'flex min-h-target w-full items-center justify-center rounded-xl focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden';

/**
 * The tablet icon rail (plan §3.2, ICON-RAIL-TABLET): on the 768–1023 px band the
 * phone tab bar gives way to this strip in the shell's 64 px first grid column.
 * Like the sidebar it is a sticky, full-height item pinned to the left edge — an
 * in-flow grid child, so the content column lands in the second track. Icons
 * only, with sr-only labels and title tooltips; More opens the same sheet the
 * tab bar uses.
 */
export function IconRail() {
  const { pathname } = useLocation();

  return (
    <nav
      aria-label="Icon rail"
      className="hidden md:sticky md:top-0 md:flex md:h-dvh md:w-16 md:flex-col md:items-center md:border-r md:border-border md:bg-surface-elevated md:px-2 md:py-4 lg:hidden"
    >
      <ul className="flex w-full flex-col items-center gap-1">
        {navTabs.map((tab) => {
          const Icon = tab.icon;
          const body: ReactNode = (
            <>
              <Icon className="h-5 w-5" aria-hidden="true" />
              <span className="sr-only">{tab.label}</span>
            </>
          );
          if (!tab.to) {
            return (
              <li key={tab.label} className="w-full">
                <MoreSheet
                  trigger={
                    <button type="button" title={tab.label} className={cn(ITEM_BASE, 'text-ink-secondary')}>
                      {body}
                    </button>
                  }
                />
              </li>
            );
          }
          const active = isNavActive(pathname, tab.to);
          return (
            <li key={tab.label} className="w-full">
              <Link
                to={tab.to}
                title={tab.label}
                aria-current={active ? 'page' : undefined}
                className={cn(ITEM_BASE, active ? 'text-accent' : 'text-ink-secondary')}
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
