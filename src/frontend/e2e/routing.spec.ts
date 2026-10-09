/**
 * Routing E2E (React Router 7 migration guard)
 *
 * - Unknown path falls back to /inbox through the real router.
 * - Lazy navigation never leaves <main> empty (Suspense fallback / startTransition).
 */

import { test, expect } from '@playwright/test';
import { openAuthenticatedPage } from './support/auth';

test.describe('Routing', () => {
  test('E2E-ROUTE-001: unknown path redirects to /inbox', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/no-such-page');

    await expect(page).toHaveURL(/\/inbox$/);
    await expect(page.getByRole('heading', { level: 1, name: 'Document Inbox' })).toBeVisible();
  });

  test('E2E-ROUTE-002: lazy navigation never shows an empty main', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/inbox');
    const main = page.locator('main');
    await expect(main).toBeVisible();
    await expect(main.getByRole('heading', { level: 1 })).toBeVisible();

    await page.evaluate(() => {
      const el = document.querySelector('main');
      if (!el) throw new Error('main not found');
      const w = window as unknown as { __emptyMain: boolean };
      w.__emptyMain = false;
      const check = () => {
        if ((el.textContent ?? '').trim() === '') {
          w.__emptyMain = true;
        }
      };
      check();
      new MutationObserver(check).observe(el, {
        subtree: true,
        childList: true,
        characterData: true,
      });
    });

    const nav = page.locator('nav[aria-label="Main navigation"]');

    // Each route has its own lazyRoute Suspense; RouteFallback (sr-only 'Loading page...') is expected on both legs.
    await nav.getByRole('link', { name: 'Trends' }).click();
    await expect(page).toHaveURL(/\/trends$/);
    await expect(main.getByRole('heading', { level: 1, name: 'Trends Dashboard' })).toBeVisible({ timeout: 15_000 });

    await nav.getByRole('link', { name: 'Timeline' }).click();
    await expect(page).toHaveURL(/\/timeline$/);
    await expect(main.getByRole('heading', { level: 1, name: 'Timeline' })).toBeVisible({ timeout: 15_000 });

    const empty = await page.evaluate(
      () => (window as unknown as { __emptyMain: boolean }).__emptyMain
    );
    expect(empty).toBe(false);
  });
});
