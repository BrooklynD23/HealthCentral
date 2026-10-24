/**
 * UI routes verification — runs in every Playwright run (project "chromium", CI).
 *
 * Split out of ui-full-verification.spec.ts, which needs a PDF and only runs in
 * the local "real-pdf-local" project. These checks have no PDF dependency and
 * no skip.
 */

import { test, expect } from '@playwright/test';
import { openAuthenticatedPage } from './support/auth';

const SIDEBAR_PATHS = [
  '/inbox',
  '/verify',
  '/trends',
  '/interpret',
  '/medications',
  '/notifications',
  '/explain',
  '/export',
  '/settings',
] as const;

test.describe('UI routes verification', () => {
  // (was E2E-UI-FULL-002)
  test('E2E-UI-ROUTES-001: sidebar routes render main content', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/inbox');

    for (const routePath of SIDEBAR_PATHS) {
      await page.goto(routePath);
      await expect(page.locator('main').first()).toBeVisible({ timeout: 30_000 });
    }
  });

  // (was E2E-UI-FULL-003)
  test('E2E-UI-ROUTES-002: Explain Assistant sends and shows fallback or answer', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/explain');

    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 15_000 });

    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill('What do my latest lab values show?');

    const sendButton = page.getByRole('button').filter({ has: page.locator('svg') }).last();
    await sendButton.click();

    await expect(
      page.getByText(
        /(insufficient|don't have enough|no relevant|limited context|not fully configured|knowledge base only|setup instructions|reference range|lab value|result|mg\/dl|mmol|hemoglobin|glucose)/i
      )
    ).toBeVisible({ timeout: 120_000 });
  });

  // (was E2E-UI-FULL-004)
  test('E2E-UI-ROUTES-003: Settings hardware detection completes', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/settings');

    await expect(
      page.getByText(/Configure AI models, document import/i)
    ).toBeVisible({ timeout: 15_000 });

    const detectButton = page.getByRole('button', { name: /^(Detect Hardware|Re-detect)$/ });
    await detectButton.click();

    // Both labels render once detection completes (stricter than the old .or()).
    await expect(page.getByText(/^RAM$/)).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Recommended Tier/i)).toBeVisible({ timeout: 60_000 });
  });
});
