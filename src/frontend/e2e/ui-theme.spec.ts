import { test, expect } from '@playwright/test';

test.describe('UI-THEME', () => {
  test.use({ colorScheme: 'dark' });

  test('HC-UITH-004: OS dark preference still yields data-theme=light before paint', async ({ page }) => {
    await page.addInitScript(() => {
      document.addEventListener('DOMContentLoaded', () => {
        (window as unknown as { __themeAtDcl: string | null }).__themeAtDcl =
          document.documentElement.getAttribute('data-theme');
      });
    });
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    const recorded = await page.evaluate(
      () => (window as unknown as { __themeAtDcl: string | null }).__themeAtDcl,
    );
    expect(recorded).toBe('light');
  });

  test('HC-UITH-005: /favicon.svg is served as SVG, not the SPA fallback', async ({ request }) => {
    const res = await request.get('/favicon.svg');
    expect(res.status()).toBe(200);
    expect(res.headers()['content-type']).toContain('svg');
    expect(await res.text()).toContain('<svg');
  });
});
