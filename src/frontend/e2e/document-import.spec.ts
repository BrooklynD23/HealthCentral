/**
 * Document Import E2E Smoke Tests
 *
 * STAB-006: E2E smoke suite for document inbox and import flow.
 *
 * Tests list-level document behavior only.
 * No "view document detail" tests — the Eye button is not wired to a route.
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

test.describe('Document Import Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-DOC-001: Navigate to inbox, verify empty state renders', async ({ page }) => {
    await setupAuthenticatedUser(page);

    // Should be on inbox
    await expect(page).toHaveURL(/\/inbox/);

    // Empty state should show
    await expect(
      page.getByText(/no documents yet|import your first/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('E2E-DOC-002: Upload test PDF, verify document list item appears', async ({ page }) => {
    await setupAuthenticatedUser(page);

    // Create a minimal test PDF in memory and upload
    const fileInput = page.locator('input[type="file"]');

    // Use a minimal PDF content
    const pdfContent = Buffer.from(
      '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n' +
      '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n' +
      '3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n' +
      'xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF'
    );

    await fileInput.setInputFiles({
      name: 'test-report.pdf',
      mimeType: 'application/pdf',
      buffer: pdfContent,
    });

    // Wait for import to process — either a list item appears or an error
    // The document should appear in the list with a status badge
    await expect(
      page.getByText(/test-report\.pdf|pending|needs review|parsed/i)
    ).toBeVisible({ timeout: 15000 });
  });

  test('E2E-DOC-003: Upload non-PDF, verify rejection message', async ({ page }) => {
    await setupAuthenticatedUser(page);

    const fileInput = page.locator('input[type="file"]');

    // Try to upload a .txt file — should be rejected by accept attribute
    // or by server validation
    const txtContent = Buffer.from('This is not a PDF');

    await fileInput.setInputFiles({
      name: 'invalid-file.txt',
      mimeType: 'text/plain',
      buffer: txtContent,
    });

    // Should show an error or the file should not appear in the list
    // The file input has accept=".pdf,.png,.jpg,.jpeg" so browser may reject,
    // but if it gets through, server should reject with 400
    await page.waitForTimeout(2000);

    // Verify no .txt document appears in list
    await expect(page.getByText('invalid-file.txt')).not.toBeVisible();
  });

  test('E2E-DOC-004: Upload PDF, verify correct status badge text', async ({ page }) => {
    await setupAuthenticatedUser(page);

    const fileInput = page.locator('input[type="file"]');

    const pdfContent = Buffer.from(
      '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n' +
      '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n' +
      '3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n' +
      'xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF'
    );

    await fileInput.setInputFiles({
      name: 'status-test.pdf',
      mimeType: 'application/pdf',
      buffer: pdfContent,
    });

    // Wait for the document to appear
    await expect(
      page.getByText(/status-test\.pdf/i)
    ).toBeVisible({ timeout: 15000 });

    // Should show one of the valid status badges
    await expect(
      page.getByText(/pending|needs review|verified|ocr required/i)
    ).toBeVisible();
  });

  test('E2E-DOC-005: Verify OCR Required badge renders for pending_ocr status', async ({ page }) => {
    await setupAuthenticatedUser(page);

    // Inject a mock document with pending_ocr status into the page
    // by intercepting the API response
    await page.route('**/api/v1/documents/*', async (route) => {
      const response = await route.fetch().catch(() => null);
      if (response && response.ok()) {
        const json = await response.json();
        // If it's a list response, add a mock pending_ocr document
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

    // Refresh to pick up the mock
    await page.goto('/inbox');
    await page.waitForTimeout(2000);

    // The "OCR Required" badge should be visible
    await expect(
      page.getByText(/ocr required/i)
    ).toBeVisible({ timeout: 10000 });
  });
});
