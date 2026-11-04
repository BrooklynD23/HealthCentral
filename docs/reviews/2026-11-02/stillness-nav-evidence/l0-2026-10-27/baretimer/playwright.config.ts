// L0 measurement config (scratch, not committed). Servers are started by hand; no webServer, no globalSetup.
import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: '.',
  testMatch: ['baretimer.spec.ts'],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'line',
  timeout: 120_000,
  use: { extraHTTPHeaders: { Origin: 'http://127.0.0.1:3000' } },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
