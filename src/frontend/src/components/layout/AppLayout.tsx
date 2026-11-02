import { useLayoutEffect, useRef, useState, type RefObject } from 'react';
import { useLocation, useOutlet } from 'react-router-dom';
import { m } from 'framer-motion';
import { AppToaster } from '@/components/ui/toast';
import { duration, ease } from '@/motion/tokens';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { MobileTabBar } from './MobileTabBar';
import { SafetyRail } from './SafetyRail';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

const EASE_OUT: [number, number, number, number] = [...ease.out];

// Keeps the page that was rendered when this wrapper mounted. The route container
// is keyed by pathname, so it remounts on each navigation and this captures the
// new page then. A plain <Outlet /> would also work; this keeps the page the
// container was mounted with (UI-ROUTES, HC-UIRT-003).
function FrozenOutlet() {
  const outlet = useOutlet();
  const [frozen] = useState(() => outlet);
  return frozen;
}

/**
 * Measures the chrome that covers the viewport (the header, and the tab bar with the Safety Rail above it) and
 * writes the heights to the root as --shell-top-h and --shell-bottom-h. globals.css reads them as scroll-padding,
 * so Tab scrolls a focused control clear of that chrome (WCAG 2.4.11). Without ResizeObserver the padding is 0.
 */
function useShellChromeHeights(shellRef: RefObject<HTMLDivElement>) {
  useLayoutEffect(() => {
    const shell = shellRef.current;
    if (!shell || typeof ResizeObserver === 'undefined') return;
    const root = document.documentElement;
    const header = shell.querySelector<HTMLElement>('header');
    const tabBar = shell.querySelector<HTMLElement>('nav[aria-label="Tab bar"]');
    const rail = shell.querySelector<HTMLElement>('[data-safety-rail]');
    // Rounded up: the rail is 43.4 px, and offsetHeight would leave a focused control 0.4 px under it.
    const heightOf = (el: HTMLElement | null) => el?.getBoundingClientRect().height ?? 0;
    const measure = () => {
      root.style.setProperty('--shell-top-h', `${Math.ceil(heightOf(header))}px`);
      root.style.setProperty('--shell-bottom-h', `${Math.ceil(heightOf(tabBar) + heightOf(rail))}px`);
    };
    const observer = new ResizeObserver(measure);
    for (const el of [header, tabBar, rail]) {
      if (el) observer.observe(el);
    }
    measure();
    return () => {
      observer.disconnect();
      root.style.removeProperty('--shell-top-h');
      root.style.removeProperty('--shell-bottom-h');
    };
  }, [shellRef]);
}

/**
 * The authenticated shell (plan §3.2, §3.6). Desktop: a 264 px sidebar beside the
 * content column. Phones: no sidebar, a top bar and a bottom tab bar. The route
 * container is the only part that moves: M7 fades its opacity over 200 ms with no
 * transform, and under reduced motion it appears at once. The top bar, the tab bar
 * and the Safety Rail sit outside it and never fade.
 */
export function AppLayout() {
  const { pathname } = useLocation();
  const prefersReducedMotion = useReducedMotion();
  const shellRef = useRef<HTMLDivElement>(null);
  useShellChromeHeights(shellRef);

  return (
    <div ref={shellRef} className="min-h-dvh bg-surface lg:grid lg:grid-cols-[264px_minmax(0,1fr)]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-surface-elevated focus:px-4 focus:py-3 focus:text-sm focus:font-medium focus:text-ink focus:shadow-elevated focus-visible:ring-2 focus-visible:ring-accent"
      >
        Skip to content
      </a>

      <Sidebar />

      <div className="flex min-h-dvh min-w-0 flex-col">
        <TopBar />

        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 px-4 pb-[calc(9.5rem+env(safe-area-inset-bottom))] pt-6 focus:outline-hidden lg:px-8 lg:pb-8 lg:pt-8"
        >
          <m.div
            key={pathname}
            data-route-container={pathname}
            className="mx-auto w-full max-w-7xl"
            initial={prefersReducedMotion ? false : { opacity: 0.35 }}
            animate={{ opacity: 1 }}
            transition={{ duration: duration.route, ease: EASE_OUT }}
          >
            <FrozenOutlet />
          </m.div>
        </main>

        <SafetyRail />
      </div>

      <MobileTabBar />
      <AppToaster />
    </div>
  );
}
