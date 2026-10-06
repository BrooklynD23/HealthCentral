import { test, expect } from '@playwright/test';
import { E2E_API_URL } from './support/auth';

test('E2E-HEALTH-001: /health returns 200 with a status field', async ({ request }) => {
  const response = await request.get(E2E_API_URL.replace(/\/api\/v1$/, '/health'));
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.status).toBe('healthy');
});
