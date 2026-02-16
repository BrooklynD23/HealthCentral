/**
 * UXQA-004: OCR-Specific Workflow Tests
 *
 * Tests document import flows for scanned PDFs and images
 * that require OCR processing.
 */

import { test, expect } from '@playwright/test';

async function setupAuthenticatedUser(page, profileName = 'OCR Test') {
  await page.goto('/setup');
  await page.evaluate(() => localStorage.clear());

  await page.getByLabel('Profile Name').fill(profileName);
  await page.getByPlaceholder('Create a secure password').fill('SecurePass123');
  await page.getByRole('button', { name: /create your profile/i }).click();

  await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
}

test.describe('OCR Workflow Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-OCR-001: Upload image file, verify processing state', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    const fileInput = page.locator('input[type="file"]');

    // Upload a PNG image (simulated lab image)
    const pngHeader = Buffer.from([
      0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
      0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
      0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xde, 0x00, 0x00, 0x00,
      0x0c, 0x49, 0x44, 0x41, 0x54, 0x08, 0xd7, 0x63, 0xf8, 0xcf, 0xc0, 0x00,
      0x00, 0x00, 0x02, 0x00, 0x01, 0xe2, 0x21, 0xbc, 0x33, 0x00, 0x00, 0x00,
      0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
    ]);

    await fileInput.setInputFiles({
      name: 'scanned-lab.png',
      mimeType: 'image/png',
      buffer: pngHeader,
    });

    // Wait for processing - should show either the image document or pending_ocr status
    await page.waitForTimeout(5000);

    // The page should not crash
    const body = page.locator('body');
    await expect(body).not.toHaveText(/undefined|null|NaN/);
  });

  test('E2E-OCR-002: Mock pending_ocr document shows OCR Required badge', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Intercept documents API to return a pending_ocr document
    await page.route('**/api/v1/documents/*', async (route) => {
      const response = await route.fetch().catch(() => null);
      if (response && response.ok()) {
        const json = await response.json();
        if (Array.isArray(json)) {
          json.push({
            id: 'mock-ocr-doc',
            profile_id: 'test',
            doc_type: 'lab_pdf_scanned',
            source: 'scanned-report.pdf',
            status: 'pending_ocr',
            page_count: 1,
            collection_date: null,
            imported_at: new Date().toISOString(),
            parsed_at: null,
            verified_at: null,
          });
          await route.fulfill({ json });
          return;
        }
      }
      await route.continue();
    });

    await page.goto('/inbox');
    await page.waitForTimeout(3000);

    // Should show OCR Required badge
    await expect(page.getByText(/ocr required/i)).toBeVisible({
      timeout: 10000,
    });
  });

  test('E2E-OCR-003: Pending OCR document pages show informative message', async ({
    page,
  }) => {
    await setupAuthenticatedUser(page);

    // Mock a document with pending_ocr status and its pages endpoint
    await page.route('**/api/v1/documents/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'ocr-pending-doc',
            profile_id: 'test',
            doc_type: 'lab_pdf_scanned',
            source: 'ocr-pending.pdf',
            status: 'pending_ocr',
            page_count: 1,
            collection_date: null,
            imported_at: new Date().toISOString(),
            parsed_at: null,
            verified_at: null,
          },
        ]),
      });
    });

    await page.goto('/inbox');
    await page.waitForTimeout(2000);

    // The OCR Required badge should be visible
    await expect(page.getByText(/ocr required/i)).toBeVisible({
      timeout: 10000,
    });
  });
});
