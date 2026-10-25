import { useLayoutEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { cn } from '@/utils/cn';
import { BrandMark } from './BrandMark';
import { isNavActive, navGroups } from './navConfig';

const ITEM =
  'relative z-10 flex h-11 items-center gap-3 rounded-xl px-4 text-sm font-medium focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2';

/**
 * The desktop sidebar (plan §3.2, at 1024 px and up). Groups from navConfig.ts;
 * the active destination is the longest prefix match (plan §3.1). One indicator
 * element moves with a CSS transition (M9); it does not use a layout spring.
 */
export function Sidebar() {
  const { pathname } = useLocation();
  const navRef = useRef<HTMLElement>(null);
  const activeRef = useRef<HTMLAnchorElement | null>(null);
  const [indicatorTop, setIndicatorTop] = useState<number | null>(null);
  const prefersReducedMotion = useReducedMotion();

  const activeTo = navGroups.flatMap((group) => group.items).find((item) => isNavActive(pathname, item.to))?.to;

  // Measured before paint, so the indicator never shows at the wrong row.
  // Reduced motion places the indicator with `top` and no transform (G5 reads transforms).
  useLayoutEffect(() => {
    setIndicatorTop(activeRef.current ? activeRef.current.offsetTop : null);
  }, [activeTo]);

  return (
    <aside className="hidden lg:sticky lg:top-0 lg:flex lg:h-dvh lg:w-[264px] lg:flex-col border-r border-border bg-surface-elevated">
      <div className="border-b border-border p-6">
        <BrandMark showTagline />
      </div>

      <nav aria-label="Main navigation" ref={navRef} className="relative flex-1 overflow-y-auto px-3 py-4">
        <span
          aria-hidden="true"
          className={cn(
            'pointer-events-none absolute inset-x-3 top-0 h-11 rounded-xl bg-accent-subtle',
            'transition-transform duration-[var(--dur-md)] ease-[var(--ease-in-out)] motion-reduce:transition-none',
            indicatorTop === null && 'opacity-0'
          )}
          style={prefersReducedMotion ? { top: indicatorTop ?? 0 } : { transform: `translateY(${indicatorTop ?? 0}px)` }}
        />
        {navGroups.map((group) => (
          <div key={group.label} className="mb-2">
            <p className="px-4 pb-1 pt-3 text-xs font-medium uppercase tracking-wide text-ink-tertiary">
              {group.label}
            </p>
            <ul className="space-y-1">
              {group.items.map((item) => {
                const active = item.to === activeTo;
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <Link
                      ref={active ? activeRef : undefined}
                      to={item.to}
                      aria-current={active ? 'page' : undefined}
                      className={cn(
                        ITEM,
                        active ? 'text-accent' : 'text-ink-secondary hover:bg-black/3 hover:text-ink'
                      )}
                    >
                      <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-border p-4">
        <div className="rounded-xl bg-surface-muted px-4 py-3">
          <p className="text-sm font-medium text-ink">Stored on this device</p>
          <p className="text-xs text-ink-secondary">Offline-first • Private</p>
        </div>
      </div>
    </aside>
  );
}
