/**
 * UXQA-001: Color Contrast Audit (Playwright + axe-core)
 *
 * Browser-based WCAG 2.1 AA color contrast checks.
 * Runs in CI via the e2e-tests job (requires backend).
 *
 * These tests complement the JSDOM structural checks in
 * StructuralA11y.test.tsx by verifying actual rendered contrast.
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const contrastPages = [
  { name: 'DocumentInbox', path: '/inbox' },
  { name: 'TrendsDashboard', path: '/trends' },
  { name: 'SettingsPage', path: '/settings' },
  { name: 'SearchPage', path: '/search' },
];

test.describe('WCAG 2.1 AA Color Contrast', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to setup to create a profile first (or use stored auth)
    // In CI the backend provides a test profile
    await page.goto('/');
    // Wait for the app to load
    await page.waitForLoadState('networkidle');
  });

  for (const { name, path } of contrastPages) {
    test(`${name} (${path}) passes color contrast checks`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState('networkidle');

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
