// STILLNESS-NAV-LATE measurement config. Servers are started by run_wrap.sh; no webServer, no globalSetup.
// workers 1, retries 0; trace, video and screenshot are explicitly off (the repo config has
// trace: 'on-first-retry' and screenshot: 'only-on-failure'). nav-sets.spec.ts prints a CONFIG line to prove it.
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: ['nav-sets.spec.ts'],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'line',
  timeout: 120_000,
  use: {
    trace: 'off',
    video: 'off',
    screenshot: 'off',
    extraHTTPHeaders: { Origin: 'http://127.0.0.1:3000' },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
