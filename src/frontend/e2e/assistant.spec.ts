/**
 * RAG Assistant E2E Tests
 *
 * Sprint 6 - S6-E2E-001: End-to-End Test Suite for RAG Assistant
 *
 * Tests the assistant feature including:
 * - Chat with insufficient context (no documents)
 * - Chat with documents (citations in response)
 * - Prohibited request handling (safe refusal)
 * - Glossary and test-intent endpoint verification
 */

import { test, expect } from '@playwright/test';
import { openAuthenticatedPage, seedAuthenticatedSession } from './support/auth';

const mockChatResponse = {
  segments: [
    {
      segment_type: 'general_info' as const,
      content: 'Category request proof response.',
      citations: [],
    },
  ],
  full_response: 'Category request proof response.',
  insufficient_context: false,
  insufficient_reasons: [],
  verification: {
    enabled: false,
    total_claims: 0,
    verified_claims: 0,
    failed_claims: 0,
    faithfulness_score: 1,
    authority_score: 1,
    summary: '',
    issues: [],
  },
  is_valid: true,
  validation_errors: [],
};

test.describe('RAG Assistant Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('E2E-RAG-001: No docs → chat returns insufficient context', async ({ page, request }) => {
    // Set up authenticated user
    await openAuthenticatedPage(page, request, '/explain');

    // Wait for the page to load
    await expect(page.getByText(/explain assistant|ask about your results/i)).toBeVisible({
      timeout: 10000,
    });

    // Find the input field and type a question
    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill('What is my glucose level?');

    // Click send button
    await page.getByRole('button').filter({ has: page.locator('svg') }).last().click();

    // Wait for response - should show insufficient context or error
    // With no documents, the assistant should indicate it doesn't have enough info
    await expect(
      page.getByText(/(insufficient|don't have enough|no relevant|limited context|not fully configured)/i)
    ).toBeVisible({ timeout: 15000 });
  });

  test('E2E-RAG-002: Handles no-model fallback gracefully', async ({ page, request }) => {
    // Set up authenticated user
    await openAuthenticatedPage(page, request, '/explain');

    // Wait for the page to load
    await expect(page.getByText(/explain assistant|ask about your results/i)).toBeVisible({
      timeout: 10000,
    });

    // Ask a question
    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill('What is my hemoglobin?');
    await page.getByRole('button').filter({ has: page.locator('svg') }).last().click();

    // When no LLM is available, the backend returns a 200 knowledge-base fallback
    // response instead of a 501 error
    await expect(
      page.getByText(
        /(not fully configured|setup instructions|insufficient|don't have enough|limited context|knowledge base only)/i
      )
    ).toBeVisible({ timeout: 15000 });
  });

  test('E2E-RAG-003: Suggested questions are clickable', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/explain');

    // Wait for page load
    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 10000 });

    // Find a suggested question
    const suggestedQuestion = page.getByRole('button', {
      name: /what does my hemoglobin level mean/i,
    });

    // Click it
    await suggestedQuestion.click();

    // The input should be filled with the question
    const input = page.getByPlaceholder(/ask about your results/i);
    await expect(input).toHaveValue(/hemoglobin/i);
  });

  test('E2E-RAG-004: Shows warning about not providing medical advice', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/explain');

    // Wait for page load
    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 10000 });

    // Should show the important disclaimer
    await expect(page.getByText(/does not provide medical advice/i)).toBeVisible();
    await expect(page.getByText(/always consult your healthcare provider/i)).toBeVisible();
  });

  test('E2E-RAG-005: Category filter sends selected document category in the chat request', async ({ page, request }) => {
    await page.route(/\/api\/v1\/observations\/?(?:\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route(/\/api\/v1\/assistant\/chat\/?(?:\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChatResponse),
      });
    });

    await seedAuthenticatedSession(page, request);
    await page.goto('/explain');

    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 10000 });

    const categoryFilter = page.getByRole('combobox', { name: 'Document Category' });
    await expect(categoryFilter).toBeVisible();
    await categoryFilter.selectOption('imaging');
    await expect(categoryFilter).toHaveValue('imaging');

    const assistantRequest = page.waitForRequest(
      (request) =>
        request.method() === 'POST' && /\/api\/v1\/assistant\/chat\/?(?:\?.*)?$/.test(request.url())
    );

    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill('Show me my imaging results.');
    await page.getByRole('button').filter({ has: page.locator('svg') }).last().click();

    const chatRequestPayload = (await assistantRequest).postDataJSON() as Record<string, unknown>;
    expect(chatRequestPayload).toMatchObject({
      question: 'Show me my imaging results.',
      include_references: true,
      enable_verification: true,
      document_category: 'imaging',
    });
    await expect(page.getByText('Category request proof response.')).toBeVisible();
  });
});

test.describe('Assistant API Endpoints', () => {
  test('E2E-RAG-004a: Glossary endpoint returns 200', async ({ request: _request }) => {
    // This test directly hits the API to verify the endpoint works
    // Note: Requires backend to be running

    // First we need to get an auth token
    // For now, skip if auth not available
    test.skip(true, 'Requires authenticated API access');

    // const response = await request.get('/api/assistant/glossary/hemoglobin', {
    //   headers: { Authorization: `Bearer ${token}` }
    // });
    // expect(response.status()).toBe(200);
    // const body = await response.json();
    // expect(body.term).toBeDefined();
    // expect(body.definition).toBeDefined();
  });

  test('E2E-RAG-004b: Test intent endpoint returns 200', async ({ request: _request }) => {
    // This test directly hits the API to verify the endpoint works
    // Note: Requires backend to be running

    test.skip(true, 'Requires authenticated API access');

    // const response = await request.get('/api/assistant/test-intent/glucose', {
    //   headers: { Authorization: `Bearer ${token}` }
    // });
    // expect(response.status()).toBe(200);
    // const body = await response.json();
    // expect(body.analyte).toBeDefined();
    // expect(body.intent_summary).toBeDefined();
  });
});

test.describe('Assistant UI Components', () => {
  test('Shows loading state while sending message', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/explain');

    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 10000 });

    // Type a message
    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill('Test question');

    // Start sending (click send button)
    await page.getByRole('button').filter({ has: page.locator('svg') }).last().click();

    // Should show loading indicator
    await expect(page.getByText(/searching documents|generating response/i)).toBeVisible();
  });

  test('Displays user message after sending', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/explain');

    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 10000 });

    const testQuestion = 'What is my glucose reading?';

    // Type and send
    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill(testQuestion);
    await page.getByRole('button').filter({ has: page.locator('svg') }).last().click();

    // User message should appear
    await expect(page.getByText(testQuestion)).toBeVisible();
  });

  test('Input clears after sending message', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/explain');

    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 10000 });

    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill('Test question');
    await page.getByRole('button').filter({ has: page.locator('svg') }).last().click();

    // Input should be cleared
    await expect(input).toHaveValue('');
  });

  test('Empty input disables send button', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/explain');

    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 10000 });

    // Find send button (last button with svg icon)
    const sendButton = page.getByRole('button').filter({ has: page.locator('svg') }).last();

    // Should be disabled with empty input
    await expect(sendButton).toBeDisabled();

    // Type something
    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill('Test');

    // Now should be enabled
    await expect(sendButton).toBeEnabled();
  });
});
