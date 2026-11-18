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
 *
 * UI-PG-SETTINGS: /settings is four sections. The hardware and tier checks open
 * /settings?section=advanced and press "Show advanced settings" first; the external
 * API check opens /settings?section=assistant-privacy.
 */

import { test, expect, type Page } from '@playwright/test';
import { openAuthenticatedPage } from './support/auth';

/** Advanced is collapsed by default (HC-UISET-002): hardware and tier controls exist only after this. */
async function openAdvanced(page: Page) {
  await page.getByRole('button', { name: 'Show advanced settings' }).click();
}

test.describe('Settings Page Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-SET-001: Navigate to settings, verify hardware detection button visible', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/settings?section=advanced');
    await openAdvanced(page);

    // Hardware detection button should be visible
    await expect(
      page.getByRole('button', { name: /detect hardware|re-detect|auto-detect|scan hardware/i })
    ).toBeVisible({ timeout: 10000 });
  });

  test('E2E-SET-002: Verify tier selection cards render', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/settings?section=advanced');
    await openAdvanced(page);

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
    await openAuthenticatedPage(page, request, '/settings?section=assistant-privacy');

    // Find external API toggle (by role: a text match could click the description and open nothing)
    const apiToggle = page.getByRole('switch', { name: /external api|cloud api/i });
    await expect(apiToggle).toBeVisible({ timeout: 10000 });

    // Click the toggle to enable
    await apiToggle.click();

    // E2E-SET-003-WEAK: the consent dialog itself, not text somewhere on the page, and its D12 copy.
    const dialog = page.getByRole('alertdialog', { name: 'Privacy Notice' });
    await expect(dialog).toBeVisible({ timeout: 5000 });
    await expect(dialog.getByText('External API Processing')).toBeVisible();
    await expect(dialog.getByText(/your health data will be sent to a third-party server for processing/)).toBeVisible();
    await expect(dialog.getByText('Lab results and observations referenced in your questions')).toBeVisible();
    await expect(dialog.getByText('Your conversation messages and context')).toBeVisible();
    await expect(dialog.getByText('Analyte names and values for interpretation')).toBeVisible();
    await expect(dialog.getByText(/You can disable this at any time to return to local-only processing/)).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'I Understand, Enable' })).toBeVisible();
  });

  test('E2E-SET-004: every model tier reports exactly one availability state', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/settings?section=advanced');
    await openAdvanced(page);

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
