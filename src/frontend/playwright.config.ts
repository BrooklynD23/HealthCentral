/**
 * Playwright E2E Test Configuration
 *
 * Sprint 1 - S1-E2E-001: E2E Harness Setup
 * STAB-006: Updated to start both frontend and backend servers
 */

import { defineConfig, devices } from '@playwright/test';

const cliArgs = process.argv.slice(2).join(' ');
const isAssistantCategoryProofRun =
  process.env.PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF === '1' ||
  (/assistant\.spec\.[cm]?[jt]sx?/i.test(cliArgs) && /\bcategory\b/i.test(cliArgs));

const frontendServer = {
  command: 'npm run dev -- --host 127.0.0.1 --port 3000',
  cwd: '.',
  url: 'http://127.0.0.1:3000',
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
};

const backendServer = {
  command: 'python -m uvicorn main:app --host 127.0.0.1 --port 8000',
  cwd: '../../src/backend',
  url: 'http://127.0.0.1:8000/health',
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
};

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: isAssistantCategoryProofRun ? [frontendServer] : [backendServer, frontendServer],
});
