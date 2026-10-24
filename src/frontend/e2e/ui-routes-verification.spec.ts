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

    // Let the most-recent-session restore (ExplainAssistant, ASSIST-HIST-001)
    // finish first, so `before` is not taken ahead of restored turns.
    await page.waitForLoadState('networkidle');

    const question = 'What do my latest lab values show?';
    const assistantMessages = page.locator(
      '[data-testid="chat-message"][data-role="assistant"]'
    );
    const before = await assistantMessages.count();

    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill(question);

    const chatResponse = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/assistant\/chat\/?(?:\?.*)?$/.test(r.url()),
      { timeout: 120_000 }
    );
    const sendButton = page.getByRole('button').filter({ has: page.locator('svg') }).last();
    await sendButton.click();

    // CI has no model: the backend answers 200 with an abstain/fallback reply
    // (see E2E-RAG-002). An error reply (500/401/network) is not a valid reply.
    expect((await chatResponse).status()).toBe(200);

    // Exactly one new assistant message, with non-empty text that is not the
    // question echoed back.
    await expect(assistantMessages).toHaveCount(before + 1, { timeout: 120_000 });
    const reply = assistantMessages.last();
    await expect(reply).toBeVisible({ timeout: 120_000 });
    await expect
      .poll(async () => ((await reply.innerText()) ?? '').trim(), { timeout: 120_000 })
      .not.toBe('');
    const text = (await reply.innerText()).trim();
    expect(text).not.toBe(question);
    expect(text).not.toContain(question);
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
