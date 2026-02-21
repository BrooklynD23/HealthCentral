/**
 * UXQA-001: Color Contrast Audit (Playwright + axe-core)
 *
 * Browser-based WCAG 2.1 AA color contrast checks.
 * Runs in CI via the e2e-tests job (requires backend).
 *
 * These tests complement the JSDOM structural checks in
 * StructuralA11y.test.tsx by verifying actual rendered contrast.
 *
 * FND-001 fix: Establishes authenticated state before navigating
 * to protected routes and asserts the correct route before scanning.
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const contrastPages = [
  { name: 'DocumentInbox', path: '/inbox' },
  { name: 'TrendsDashboard', path: '/trends' },
  { name: 'SettingsPage', path: '/settings' },
  { name: 'SearchPage', path: '/search' },
];

async function setupAuthenticatedUser(page: import('@playwright/test').Page) {
  await page.goto('/setup');
  await page.evaluate(() => localStorage.clear());

  await page.getByLabel('Profile Name').fill('Contrast Audit User');
  await page.getByPlaceholder('Create a secure password').fill('SecurePass123');
  await page.getByRole('button', { name: /create your profile/i }).click();

  await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
}

test.describe('WCAG 2.1 AA Color Contrast', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedUser(page);
  });

  for (const { name, path } of contrastPages) {
    test(`${name} (${path}) passes color contrast checks`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState('networkidle');

      // Assert we landed on the intended route, not a redirect to /setup
      const currentURL = new URL(page.url());
      expect(
        currentURL.pathname,
        `Expected to be on ${path} but was redirected to ${currentURL.pathname}. Auth may not be established.`,
      ).toBe(path);

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2aa'])
        .analyze();

      const contrastViolations = results.violations.filter(
        (v) => v.id === 'color-contrast',
      );

      expect(
        contrastViolations,
        `${name} has ${contrastViolations.length} contrast violations`,
      ).toEqual([]);
    });
  }
});
