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
      if (/\/recover/i.test(new URL(req.url()).pathname)) {
        recoveryCalls.push(req.url());
      }
    });

    // Simulate an expired session: the profile exists, the token does not.
    await page.goto('/setup');
    await page.evaluate(() => localStorage.removeItem('healthcentral-auth'));
    await page.reload();

    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
    await page.getByLabel('Unlock password').fill(E2E_PROFILE_PASSWORD);
    await page.getByRole('button', { name: 'Unlock', exact: true }).click();

    await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
    expect(new URL(page.url()).pathname).not.toMatch(/recover/i);
    expect(recoveryCalls).toEqual([]);
  });
});
