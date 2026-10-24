/**
 * Document Import E2E Smoke Tests
 *
 * STAB-006: E2E smoke suite for document inbox and import flow.
 *
 * Tests list-level document behavior only.
 * No "view document detail" tests — the Eye button is not wired to a route.
 */

import path from 'path';
import { fileURLToPath } from 'url';
import { test, expect } from '@playwright/test';
import { E2E_API_URL, openAuthenticatedPage } from './support/auth';

test.describe('Document Import Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-DOC-001: Navigate to inbox, verify empty state renders', async ({ page, request }) => {
    await openAuthenticatedPage(page, request);

    // Should be on inbox
    await expect(page).toHaveURL(/\/inbox/);

    // Empty state should show
    await expect(
      page.getByText(/no documents yet|import your first/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('E2E-DOC-002: Upload synthetic lab PDF, backend parses it', async ({ page, request }) => {
    const auth = await openAuthenticatedPage(page, request);

    // Committed text-lab fixture (see ui-full-verification.spec.ts header).
    // Track the id from this upload's own import response, so a 'parsed' row
    // left by an earlier attempt (retries, shared profile) cannot satisfy it.
    const importResponse = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/documents\/import\/?(?:\?.*)?$/.test(r.url())
    );
    await page
      .locator('input[type="file"]')
      .setInputFiles(path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures', 'synthetic-lab.pdf'));
    const imported = await importResponse;
    expect(imported.ok()).toBe(true);
    const documentId = ((await imported.json()) as { document: { id: string } }).document.id;

    // Assert the backend status, not toast/filename text: a rejected import
    // never produces a 'parsed' row. There is no backend "needs review" status
    // (the inbox labels every non-pending status that), so only 'parsed' passes.
    await expect
      .poll(
        async () => {
          const res = await request.get(`${E2E_API_URL}/documents/${documentId}`, {
            headers: { Authorization: `Bearer ${auth.access_token}` },
          });
          if (!res.ok()) return `http ${res.status()}`;
          return ((await res.json()) as { status: string }).status;
        },
        { timeout: 60_000, intervals: [1000] }
      )
      .toBe('parsed');

    await expect(page.getByRole('heading', { name: /synthetic-lab\.pdf/ }).first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test('E2E-DOC-003: Upload non-PDF, verify rejection message', async ({ page, request }) => {
    await openAuthenticatedPage(page, request);

    const fileInput = page.locator('input[type="file"]');

    // Try to upload a .txt file — should be rejected by accept attribute
    // or by server validation
    const txtContent = Buffer.from('This is not a PDF');

    await fileInput.setInputFiles({
      name: 'invalid-file.txt',
      mimeType: 'text/plain',
      buffer: txtContent,
    });

    // setInputFiles bypasses the accept attribute, so the server rejects the
    // file and the page must show the import-failure alert naming it (FE-IMPORT-ERROR).
    const alert = page.getByRole('alert');
    await expect(alert).toContainText('invalid-file.txt', { timeout: 15000 });
    await expect(alert).toContainText('Import failed');

    // Only after the upload has settled: no .txt document in the document list.
    // Rows render the name as an <h4>; the alert renders it in a <p>, so a
    // heading query cannot match the alert.
    await expect(page.getByRole('heading', { name: 'invalid-file.txt' })).not.toBeVisible();
  });

  test('E2E-DOC-004: Upload PDF, verify correct status badge text', async ({ page, request }) => {
    await openAuthenticatedPage(page, request);

    const fileInput = page.locator('input[type="file"]');

    // NOTE: include a unique comment marker so this file's content hash differs
    // from the one uploaded in E2E-DOC-002. The backend dedupes imports by
    // content hash and returns the *existing* document (with its original
    // filename) on a match — which would make the status-test.pdf assertion
    // below fail because the toast/list would show the earlier file's name.
    const pdfContent = Buffer.from(
      '%PDF-1.4\n%status-test-unique-marker\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n' +
      '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n' +
      '3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n' +
      'xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF'
    );

    await fileInput.setInputFiles({
      name: 'status-test.pdf',
      mimeType: 'application/pdf',
      buffer: pdfContent,
    });

    // Wait for the document to appear (.first(): matches both the import toast
    // and the list heading)
    await expect(
      page.getByText(/status-test\.pdf/i).first()
    ).toBeVisible({ timeout: 15000 });

    // Should show one of the valid status badges
    await expect(
      page.getByText(/pending|needs review|verified|ocr required/i).first()
    ).toBeVisible();
  });

  test('E2E-DOC-005: Verify OCR Required badge renders for pending_ocr status', async ({ page, request }) => {
    await openAuthenticatedPage(page, request);

    // Inject a mock document with pending_ocr status into the page
    // by intercepting the API response
    await page.route('**/api/v1/documents/**', async (route) => {
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
      page.getByText(/ocr required/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});
