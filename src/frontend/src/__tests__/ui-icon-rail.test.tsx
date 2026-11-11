// ICON-RAIL-TABLET (HC-IRL-001..005): the 768–1023 px tablet band gets an icon
// rail on the left instead of the phone tab bar. jsdom cannot evaluate @media,
// so the breakpoint classes are the contract; the quiet-box viewport check
// covers the real pixels.

import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MobileTabBar } from '@/components/layout/MobileTabBar';
import { SafetyRail } from '@/components/layout/SafetyRail';
import { navTabs } from '@/components/layout/navConfig';
import appLayoutSource from '@/components/layout/AppLayout.tsx?raw';

// Loaded at run time so a missing module fails that id alone, not the file
// (the ui-motion precedent). `@vite-ignore` keeps the path unresolvable at
// transform time, so the import reaches the runner and fails there.
const ICON_RAIL_MODULE = '@/components/layout/IconRail';

describe('ICON-RAIL-TABLET', () => {
  it('HC-IRL-001: the rail is a nav labelled "Icon rail", hidden below md and at lg', async () => {
    const { IconRail } = (await import(/* @vite-ignore */ ICON_RAIL_MODULE)) as typeof import('@/components/layout/IconRail');
    const { container } = render(
      <MemoryRouter>
        <IconRail />
      </MemoryRouter>
    );

    const nav = container.querySelector<HTMLElement>('nav[aria-label="Icon rail"]');
    expect(nav).not.toBeNull();
    const tokens = nav?.className.split(/\s+/) ?? [];
    expect(tokens).toContain('hidden');
    expect(tokens).toContain('md:flex');
    expect(tokens).toContain('lg:hidden');
  });

  it('HC-IRL-002: the phone tab bar hides at md and up, where the rail takes over', () => {
    const { container } = render(
      <MemoryRouter>
        <MobileTabBar />
      </MemoryRouter>
    );

    const nav = container.querySelector<HTMLElement>('nav[aria-label="Tab bar"]');
    expect(nav).not.toBeNull();
    const tokens = nav?.className.split(/\s+/) ?? [];
    expect(tokens).toContain('md:hidden');
    expect(tokens).not.toContain('lg:hidden');
  });

  it('HC-IRL-003: the rail lists the four routed tabs plus More and marks the current route', async () => {
    const { IconRail } = (await import(/* @vite-ignore */ ICON_RAIL_MODULE)) as typeof import('@/components/layout/IconRail');
    render(
      <MemoryRouter initialEntries={['/results']}>
        <IconRail />
      </MemoryRouter>
    );

    const nav = screen.getByRole('navigation', { name: 'Icon rail' });
    for (const tab of navTabs.filter((item) => item.to)) {
      const link = within(nav).getByRole('link', { name: tab.label });
      expect(link).toHaveAttribute('href', tab.to);
    }
    expect(within(nav).getByRole('button', { name: 'More' })).toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: 'Results' })).toHaveAttribute('aria-current', 'page');
    expect(within(nav).getByRole('link', { name: 'Overview' })).not.toHaveAttribute('aria-current');
  });

  it('HC-IRL-004: AppLayout mounts the rail and grids a 64 px tablet column', () => {
    expect(appLayoutSource).toContain('<IconRail');
    expect(appLayoutSource).toContain('md:grid-cols-[64px_minmax(0,1fr)]');
  });

  it('HC-IRL-005: the Safety Rail is fixed above the tab bar on phones and sticky from md up', () => {
    const { container } = render(<SafetyRail />);

    const rail = container.querySelector<HTMLElement>('[data-safety-rail]');
    expect(rail).not.toBeNull();
    const tokens = rail?.className.split(/\s+/) ?? [];
    expect(tokens).toContain('max-md:fixed');
    expect(tokens).toContain('md:sticky');
    expect(tokens).not.toContain('max-lg:fixed');
  });
});
