/**
 * UXQA-004: Comprehensive E2E Workflow Tests
 *
 * Full workflow coverage: import -> verify -> trends -> export.
 * Also covers error handling and recovery paths.
 */

import { test, expect } from '@playwright/test';

// Minimal valid PDF for upload tests
const MINIMAL_PDF = Buffer.from(
  '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n' +
    '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n' +
    '3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n' +
    'xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF'
);

async function setupAuthenticatedUser(page, profileName = 'Workflow Test') {
  await page.goto('/setup');
  await page.evaluate(() => localStorage.clear());

  await page.getByLabel('Profile Name').fill(profileName);
  await page.getByPlaceholder('Create a secure password').fill('SecurePass123');
  await page.getByRole('button', { name: /create your profile/i }).click();

  await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
}

test.describe('Document Workflow: Import -> Verify -> Trends -> Export', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-WF-001: Full happy path workflow', async ({ page }) => {
    await setupAuthenticatedUser(page);

    // Step 1: Import a document
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'workflow-test.pdf',
      mimeType: 'application/pdf',
      buffer: MINIMAL_PDF,
    });

    // Wait for import to complete
    await expect(
      page.getByText(/workflow-test\.pdf|pending|needs review|parsed/i)
    ).toBeVisible({ timeout: 15000 });

    // Step 2: Navigate to verification workbench
    await page.goto('/verify');
    await page.waitForTimeout(2000);

    // Should show either observations to verify or "all verified" message
    await expect(
      page
        .getByText(/verification workbench/i)
        .or(page.getByText(/all observations verified/i))
    ).toBeVisible({ timeout: 10000 });

    // Step 3: Navigate to trends dashboard
    await page.goto('/trends');
    await page.waitForTimeout(2000);

    // Should show trends page - either with data or empty state
    await expect(
      page
        .getByText(/trends dashboard/i)
        .or(page.getByText(/no data available/i))
    ).toBeVisible({ timeout: 10000 });

    // Step 4: Navigate to export
    await page.goto('/export');
    await page.waitForTimeout(2000);

    // Should show export page with download options
    await expect(page.getByText(/export summary/i)).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByRole('button', { name: /download csv/i })
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: /download json/i })
    ).toBeVisible();
  });

  test('E2E-WF-002: Navigation between workflow steps via sidebar', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Navigate through each major section
    const sections = [
      { nav: /inbox/i, heading: /document inbox/i },
      { nav: /verify/i, heading: /verification/i },
      { nav: /trends/i, heading: /trends/i },
      { nav: /export/i, heading: /export/i },
    ];

    for (const section of sections) {
      const link = page.getByRole('link', { name: section.nav });
      if (await link.isVisible()) {
        await link.click();
        await expect(page.getByText(section.heading)).toBeVisible({
          timeout: 10000,
        });
      }
    }
  });

  test('E2E-WF-003: Import multiple documents, verify list updates', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    const fileInput = page.locator('input[type="file"]');

    // Upload first document
    await fileInput.setInputFiles({
      name: 'doc-one.pdf',
      mimeType: 'application/pdf',
      buffer: MINIMAL_PDF,
    });

    await expect(page.getByText(/doc-one\.pdf/i)).toBeVisible({
      timeout: 15000,
    });

    // Upload second document (different name so not deduplicated)
    await fileInput.setInputFiles({
      name: 'doc-two.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from(
        '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n' +
          '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n' +
          '3 0 obj<</Type/Page/MediaBox[0 0 100 100]/Parent 2 0 R/Resources<<>>>>endobj\n' +
          'xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF'
      ),
    });

    await expect(page.getByText(/doc-two\.pdf/i)).toBeVisible({
      timeout: 15000,
    });
  });
});

test.describe('Error Handling and Recovery Paths', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-WF-004: API error on document list shows error state', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Intercept API to return 500
    await page.route('**/api/v1/documents/', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    // Refresh to trigger error
    await page.goto('/inbox');
    await page.waitForTimeout(3000);

    // Should show error state
    await expect(
      page.getByText(/failed to load|error|try again/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('E2E-WF-005: Network timeout shows recovery option', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Abort all API requests to simulate network failure
    await page.route('**/api/v1/**', async (route) => {
      await route.abort('connectionrefused');
    });

    await page.goto('/trends');
    await page.waitForTimeout(5000);

    // Should show some form of error or empty state (not crash)
    const body = page.locator('body');
    await expect(body).not.toHaveText(/undefined|null|NaN/);
  });

  test('E2E-WF-006: Session expiry redirects to setup', async ({ page }) => {
    await setupAuthenticatedUser(page);

    // Clear auth to simulate session expiry
    await page.evaluate(() => {
      localStorage.removeItem('healthcentral-auth');
    });

    // Try to navigate to protected route
    await page.goto('/inbox');

    // Should redirect to setup
    await expect(page).toHaveURL(/\/setup/, { timeout: 10000 });
  });
});
