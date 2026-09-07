/**
 * Playwright E2E Test Configuration
 *
 * Sprint 1 - S1-E2E-001: E2E Harness Setup
 * STAB-006: Updated to start both frontend and backend servers
 */

import { defineConfig, devices } from '@playwright/test';

const cliArgs = process.argv.slice(2).join(' ');
const e2eApiUrl = 'http://127.0.0.1:8000/api/v1';

/**
 * Optional Chromium override for sandboxes that ship a pre-installed browser
 * whose build number does not match the pinned @playwright/test version (the
 * package resolves a specific revision directory and fails if it is absent).
 *
 * Unset in CI, which installs the matching browser via `playwright install`,
 * so this changes nothing there. Locally:
 *   HC_E2E_CHROMIUM_PATH=/opt/pw-browsers/chromium npx playwright test
 */
const chromiumExecutablePath = process.env.HC_E2E_CHROMIUM_PATH;
const chromiumLaunch = chromiumExecutablePath
  ? { launchOptions: { executablePath: chromiumExecutablePath } }
  : {};
const isAssistantCategoryProofRun =
  process.env.PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF === '1' ||
  (/assistant\.spec\.[cm]?[jt]sx?/i.test(cliArgs) && /\bcategory\b/i.test(cliArgs));

const frontendServer = {
  command: 'npm run dev -- --host 127.0.0.1 --port 3000',
  cwd: '.',
  url: 'http://127.0.0.1:3000',
  env: {
    ...process.env,
    VITE_API_URL: e2eApiUrl,
  },
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
};

const backendServer = {
  command: 'node e2e/support/start-backend.mjs',
  cwd: '.',
  url: 'http://127.0.0.1:8000/health',
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
};

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  globalSetup: './e2e/support/global-setup.ts',
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',

  use: {
    baseURL: 'http://127.0.0.1:3000',
    extraHTTPHeaders: {
      Origin: 'http://127.0.0.1:3000',
    },
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], ...chromiumLaunch },
      testIgnore: ['**/ui-full-verification.spec.ts'],
    },
    {
      name: 'real-pdf-local',
      use: { ...devices['Desktop Chrome'], ...chromiumLaunch },
      testMatch: ['**/ui-full-verification.spec.ts'],
    },
  ],

  webServer: isAssistantCategoryProofRun ? [frontendServer] : [backendServer, frontendServer],
});
