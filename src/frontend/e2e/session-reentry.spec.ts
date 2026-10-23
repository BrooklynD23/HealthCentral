/**
 * SESSION-REENTRY: a patient whose session is gone gets back in with the
 * password, not the recovery code.
 *
 * The unit tests mock the API; this proves the unlock card works against the
 * real login endpoint.
 */

import { test, expect } from '@playwright/test';
import {
  E2E_PROFILE_NAME,
  E2E_PROFILE_PASSWORD,
  ensureE2EProfile,
} from './support/auth';

test.describe('SESSION-REENTRY unlock', () => {
  test('HC-SRE-004: with the token cleared, /setup unlocks with the password and never touches recovery', async ({
    page,
    request,
  }) => {
    await ensureE2EProfile(request);

    const recoveryCalls: string[] = [];
    page.on('request', (req) => {
      // API paths only: Vite also serves RecoveryCodeCard.tsx as a module.
      if (/\/api\/v1\/profiles\/[^/]+\/recover(y-code)?$/.test(new URL(req.url()).pathname)) {
        recoveryCalls.push(req.url());
      }
    });

    // Simulate an expired session the way E2E-AUTH-005 does: a persisted auth
    // state whose token has run out, then a protected route.
    await page.goto('/setup');
    await page.evaluate(() => {
      localStorage.setItem(
        'healthcentral-auth',
        JSON.stringify({
          state: {
            token: 'expired-token',
            profileId: 'test-id',
            profileName: 'Test',
            expiresAt: Date.now() - 1000,
            isAuthenticated: true,
          },
          version: 0,
        })
      );
    });
    await page.goto('/inbox');
    await expect(page).toHaveURL(/\/setup/, { timeout: 15000 });

    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
    await page.getByLabel('Unlock password').fill(E2E_PROFILE_PASSWORD);
    const loginResponse = page.waitForResponse(
      (r) => new URL(r.url()).pathname.endsWith('/profiles/login') && r.status() === 200
    );
    await page.getByRole('button', { name: 'Unlock', exact: true }).click();
    await loginResponse;

    await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
    await expect(page.getByText(/documents|inbox/i).first()).toBeVisible();
    await expect(page.getByText('Your session has ended')).toHaveCount(0);
    await expect(page.getByText('Access denied')).toHaveCount(0);
    expect(new URL(page.url()).pathname).not.toMatch(/recover/i);
    expect(recoveryCalls).toEqual([]);
  });
});
