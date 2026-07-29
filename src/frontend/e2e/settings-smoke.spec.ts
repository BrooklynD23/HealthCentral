/**
 * Settings Page E2E Smoke Tests
 *
 * STAB-006: E2E smoke suite for the Settings page.
 *
 * Verifies that the settings UI renders correctly with:
 * - Hardware detection button
 * - Tier selection cards
 * - External API toggle and consent dialog
 * - Every tier reporting exactly one availability state
 */

import { test, expect } from '@playwright/test';
import { openAuthenticatedPage } from './support/auth';

test.describe('Settings Page Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-SET-001: Navigate to settings, verify hardware detection button visible', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/settings');

    // Hardware detection button should be visible
    await expect(
      page.getByRole('button', { name: /detect hardware|re-detect|auto-detect|scan hardware/i })
    ).toBeVisible({ timeout: 10000 });
  });

  test('E2E-SET-002: Verify tier selection cards render', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/settings');

    // Wait for page to load
    await page.waitForTimeout(2000);

    // Should show tier selection options (low/mid/high)
    await expect(
      page.getByText(/low|lightweight|basic/i).first()
    ).toBeVisible({ timeout: 10000 });

    // At least one tier card should be present
    await expect(
      page.getByText(/mid|balanced|standard/i).first()
    ).toBeVisible();
  });

  test('E2E-SET-003: Verify external API toggle and consent dialog', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/settings');

    // Find external API toggle
    const apiToggle = page.getByRole('switch', { name: /external api|cloud api/i }).or(
      page.getByText(/external api|use cloud/i)
    );
    await expect(apiToggle.first()).toBeVisible({ timeout: 10000 });

    // Click the toggle to enable
    await apiToggle.first().click();

    // Should show consent dialog or warning
    await expect(
      page.getByText(/consent|acknowledge|data will be sent|privacy|understand/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('E2E-SET-004: every model tier reports exactly one availability state', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/settings');

    // This used to assert that *some* Download button existed. That is a
    // property of the machine running the test, not of the app: the button
    // renders only for a tier that is `can_run` and not yet downloaded, and
    // `can_run_tier()` requires >= 8 GB RAM even for the smallest tier. On a
    // 7 GB CI runner every tier is legitimately "Incompatible" and the old
    // assertion failed against correct behaviour.
    //
    // The invariant that actually holds on any hardware: each tier row shows
    // exactly one of Ready / Download / Incompatible — never none (a row that
    // tells the user nothing) and never two (contradictory state).
    const tierRows = page.locator('[data-testid^="tier-row-"]');
    await expect(tierRows.first()).toBeVisible({ timeout: 10000 });

    const rowCount = await tierRows.count();
    expect(rowCount).toBeGreaterThan(0);

    for (let i = 0; i < rowCount; i++) {
      const row = tierRows.nth(i);
      const testId = await row.getAttribute('data-testid');

      const states = await Promise.all([
        row.getByText(/^Ready$/).count(),
        row.getByRole('button', { name: /download|install|get model/i }).count(),
        row.getByText(/^Incompatible$/).count(),
      ]);

      const shown = states.reduce((sum, n) => sum + Math.min(n, 1), 0);
      expect(shown, `${testId} should show exactly one of Ready/Download/Incompatible, got ${JSON.stringify(states)}`).toBe(1);
    }
  });
});
