// L0 measurement config (scratch). Runs the scratch copy of the branch e2e/ (instrumented gates.ts) and the main probe spec.
// Servers are started by hand; no webServer, no globalSetup.
import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: '.',
  testMatch: ['e2e/ui-shell.spec.ts', 'main-probe.spec.ts'],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'line',
  timeout: 120_000,
  use: {
    baseURL: process.env.HC_E2E_BASE_URL || 'http://127.0.0.1:3000',
    extraHTTPHeaders: { Origin: 'http://127.0.0.1:3000' },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
