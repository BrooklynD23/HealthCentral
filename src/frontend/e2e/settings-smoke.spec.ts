/**
 * Settings Page E2E Smoke Tests
 *
 * STAB-006: E2E smoke suite for the Settings page.
 *
 * Verifies that the settings UI renders correctly with:
 * - Hardware detection button
 * - Tier selection cards
 * - External API toggle and consent dialog
 * - Download button for downloadable tiers
 */

import { test, expect } from '@playwright/test';

// Helper to set up authenticated state
async function setupAuthenticatedUser(page, profileName = 'Test Profile') {
  await page.goto('/setup');
  await page.evaluate(() => localStorage.clear());

  await page.getByLabel('Profile Name').fill(profileName);
  await page.getByPlaceholder('Create a secure password').fill('SecurePass123');
  await page.getByRole('button', { name: /create your profile/i }).click();

  await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
}

test.describe('Settings Page Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-SET-001: Navigate to settings, verify hardware detection button visible', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Navigate to settings
    await page.goto('/settings');

    // Hardware detection button should be visible
    await expect(
      page.getByRole('button', { name: /detect hardware|auto-detect|scan hardware/i })
    ).toBeVisible({ timeout: 10000 });
  });

  test('E2E-SET-002: Verify tier selection cards render', async ({ page }) => {
    await setupAuthenticatedUser(page);
    await page.goto('/settings');

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

  test('E2E-SET-003: Verify external API toggle and consent dialog', async ({ page }) => {
    await setupAuthenticatedUser(page);
    await page.goto('/settings');

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

  test('E2E-SET-004: Verify download button appears for downloadable tiers', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);
    await page.goto('/settings');

    // Wait for page to load
    await page.waitForTimeout(2000);

    // Should show at least one download-related button
    await expect(
      page.getByRole('button', { name: /download|install|get model/i }).first()
    ).toBeVisible({ timeout: 10000 });
  });
});
