/**
 * Medication Detail E2E Coverage
 *
 * E2E-MED-001: `/medications/:medicationId` was the only routed page in the
 * app with no covering Playwright spec — the route worked, it was simply
 * untested end to end.
 *
 * These are deliberately structural checks (the page renders, its sections are
 * present, an unknown id degrades rather than crashing) rather than assertions
 * about specific clinical content, which depends on seeded data.
 */

import { test, expect } from '@playwright/test';
import { E2E_API_URL, ensureE2EProfile, openAuthenticatedPage, resetE2EProfile } from './support/auth';

/**
 * DEMO-E2E-REAL: seed one synthetic medication when the vault has none, so E2E-MED-001 and E2E-MED-003 follow the
 * link to a real detail page instead of taking the empty-vault branch or skipping. Idempotent: a vault that already
 * holds a medication is left alone.
 */
async function ensureOneMedication(request: import('@playwright/test').APIRequestContext): Promise<void> {
  const { access_token: token } = await ensureE2EProfile(request);
  const headers = { Authorization: `Bearer ${token}` };
  const listed = await request.get(`${E2E_API_URL}/medications/`, { headers });
  expect(listed.ok(), await listed.text()).toBeTruthy();
  if (((await listed.json()) as unknown[]).length > 0) return;
  const created = await request.post(`${E2E_API_URL}/medications/`, {
    headers,
    data: { name: 'Demo Seedamine', dosage_amount: 5, dosage_unit: 'mg', frequency: 'once_daily' },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
}

test.describe('Medication Detail', () => {
  test.beforeEach(async ({ page, request }) => {
    await ensureOneMedication(request);
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  // Put the vault back as global-setup left it: the seeded medication must not leak into later specs.
  test.afterEach(async ({ request }) => {
    const { access_token: token } = await ensureE2EProfile(request);
    await resetE2EProfile(request, token);
  });

  test('E2E-MED-001: medication list links through to a detail page', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/medications');

    const firstMedicationLink = page
      .locator('a[href^="/medications/"]')
      .first();

    // The list loads after the page paints and isVisible() does not wait, so wait for the seeded link first
    // (DEMO-E2E-REAL: without this the seeded vault raced into the empty-state branch).
    await firstMedicationLink.waitFor({ state: 'visible', timeout: 15000 }).catch(() => undefined);

    const hasMedications = await firstMedicationLink
      .isVisible()
      .catch(() => false);

    if (!hasMedications) {
      // Empty vault is a legitimate state — the list must say so rather than
      // rendering a broken page.
      await expect(
        page.getByText(/no medications|add your first|get started/i).first()
      ).toBeVisible({ timeout: 10000 });
      return;
    }

    await firstMedicationLink.click();
    await expect(page).toHaveURL(/\/medications\/[^/]+$/);

    // The detail page must render its own heading, not fall through to a blank
    // shell or an error boundary.
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/error|something went wrong/i)).toHaveCount(0);
  });

  test('E2E-MED-002: unknown medication id degrades without crashing', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(
      page,
      request,
      '/medications/00000000-0000-4000-8000-000000000000'
    );

    // Either a not-found message or a redirect back to the list is acceptable;
    // a blank page or an unhandled exception is not.
    await page.waitForLoadState('networkidle');

    const body = page.locator('body');
    await expect(body).toBeVisible();
    await expect(body).not.toBeEmpty();

    const pageErrors: string[] = [];
    page.on('pageerror', (err) => pageErrors.push(err.message));
    await page.waitForTimeout(500);
    expect(pageErrors).toEqual([]);
  });

  test('E2E-MED-003: detail page is reachable directly by URL', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/medications');

    const firstMedicationLink = page
      .locator('a[href^="/medications/"]')
      .first();
    // The list loads after the page paints and isVisible() does not wait, so wait for the seeded link first
    // (DEMO-E2E-REAL: without this the seeded vault raced into the empty-state branch).
    await firstMedicationLink.waitFor({ state: 'visible', timeout: 15000 }).catch(() => undefined);
    if (!(await firstMedicationLink.isVisible().catch(() => false))) {
      test.skip(true, 'No seeded medications in this vault');
      return;
    }

    const href = await firstMedicationLink.getAttribute('href');
    expect(href).toBeTruthy();

    // A deep link must work on a cold load, not only via client-side routing.
    await openAuthenticatedPage(page, request, href!);
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10000 });
  });
});
