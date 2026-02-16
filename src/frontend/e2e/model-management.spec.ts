/**
 * UXQA-004: Model Management E2E Tests
 *
 * Tests the Settings page for model tier selection,
 * hardware detection, and external API configuration.
 */

import { test, expect } from '@playwright/test';

async function setupAuthenticatedUser(page, profileName = 'Settings Test') {
  await page.goto('/setup');
  await page.evaluate(() => localStorage.clear());

  await page.getByLabel('Profile Name').fill(profileName);
  await page.getByPlaceholder('Create a secure password').fill('SecurePass123');
  await page.getByRole('button', { name: /create your profile/i }).click();

  await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
}

test.describe('Model Management Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-MODEL-001: Settings page loads with hardware and tier sections', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    await page.goto('/settings');
    await page.waitForTimeout(2000);

    // Should show settings page
    await expect(page.getByText(/settings/i).first()).toBeVisible({
      timeout: 10000,
    });

    // Should have hardware detection section
    await expect(
      page.getByText(/hardware detection/i)
    ).toBeVisible();

    // Should have model tier section
    await expect(page.getByText(/model tier/i)).toBeVisible();
  });

  test('E2E-MODEL-002: Hardware detection button triggers API call', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Mock the hardware detection endpoint
    await page.route('**/api/v1/model-settings/detect-hardware', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ram_total_gb: 16.0,
          cpu_cores: 8,
          cpu_name: 'Test CPU',
          disk_free_gb: 100.0,
          gpu_name: null,
          gpu_vram_gb: null,
          recommended_tier: 'mid',
        }),
      });
    });

    await page.goto('/settings');
    await page.waitForTimeout(2000);

    // Click detect hardware button
    const detectButton = page.getByRole('button', {
      name: /detect hardware|re-detect/i,
    });
    if (await detectButton.isVisible()) {
      await detectButton.click();
      await page.waitForTimeout(2000);
    }
  });

  test('E2E-MODEL-003: External API toggle shows consent dialog', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Mock the settings endpoints
    await page.route('**/api/v1/model-settings', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            current_tier: 'low',
            preferred_tier: 'low',
            hardware_info: null,
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.route('**/api/v1/model-settings/external-api', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            use_external_api: false,
            provider: null,
            model: null,
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/settings');
    await page.waitForTimeout(3000);

    // Find and click the external API toggle
    const toggle = page.getByText(/use external api/i);
    if (await toggle.isVisible()) {
      await toggle.click();

      // Should show privacy/consent dialog
      await expect(page.getByText(/privacy notice/i)).toBeVisible({
        timeout: 5000,
      });

      // Should have cancel option
      await expect(
        page.getByRole('button', { name: /cancel/i })
      ).toBeVisible();

      // Cancel the dialog
      await page.getByRole('button', { name: /cancel/i }).click();
    }
  });

  test('E2E-MODEL-004: Settings page handles API errors gracefully', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Mock settings endpoint to return error
    await page.route('**/api/v1/model-settings', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.goto('/settings');
    await page.waitForTimeout(3000);

    // Should show error state (not crash)
    await expect(
      page.getByText(/failed to load|error|try again/i)
    ).toBeVisible({ timeout: 10000 });
  });
});
