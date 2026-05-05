import { request, type APIRequestContext } from '@playwright/test';
import { E2E_API_URL, ensureE2EProfile, resetE2EProfile } from './auth';

export default async function globalSetup() {
  if (process.env.PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF === '1') {
    return;
  }

  const context = await request.newContext();
  try {
    await waitForBackend(context);
    const auth = await ensureE2EProfile(context);
    await resetE2EProfile(context, auth.access_token);
  } finally {
    await context.dispose();
  }
}

async function waitForBackend(context: APIRequestContext) {
  const healthUrl = E2E_API_URL.replace(/\/api\/v1$/, '/health');
  const deadline = Date.now() + 30_000;
  let lastError = '';

  while (Date.now() < deadline) {
    try {
      const response = await context.get(healthUrl);
      if (response.ok()) return;
      lastError = `${response.status()} ${await response.text()}`;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error(`Backend health preflight failed at ${healthUrl}: ${lastError}`);
}
