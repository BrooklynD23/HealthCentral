/**
 * SESSION-REENTRY Task 3, "Lock now" (HC-SRE-012, plan §8.2).
 *
 * Real backend. After "Lock now" in the profile menu, the profile is locked: the
 * unlock card is the next screen, the old token is refused by a profile-data route,
 * a protected route sends the user back to /setup, and the password unlocks it.
 *
 * What these tests would not notice:
 * - a 401 versus a 403 on the stale token (only !ok is asserted; SESSION-AUTH-DIFF owns the code);
 * - a second lock POST from a double click (the vitest file HC-SRE-011 (a) covers it);
 * - a stale profile list or cache shown on /setup after the lock (only the card text is read);
 * - whether the vault keys were dropped on lock: the stale-token check proves only that the
 *   JWT was refused, and no read of vault data happens while the profile is locked.
 */

import { test, expect } from '@playwright/test';
import {
  E2E_API_URL,
  E2E_PROFILE_NAME,
  E2E_PROFILE_PASSWORD,
  openAuthenticatedPage,
} from './support/auth';

test.describe('SESSION-REENTRY Lock now', () => {
  test('HC-SRE-012: Lock now shows the unlock card, the old token is refused, and the password unlocks', async ({
    page,
    request,
  }) => {
    const auth = await openAuthenticatedPage(page, request, '/inbox');
    await expect(page.getByRole('button', { name: 'Profile and settings' })).toBeVisible({
      timeout: 15000,
    });

    await page.getByRole('button', { name: 'Profile and settings' }).click();
    const lockResponse = page.waitForResponse(
      (r) =>
        r.request().method() === 'POST' &&
        new URL(r.url()).pathname.endsWith(`/profiles/${auth.profile_id}/lock`) &&
        r.status() === 200
    );
    await page.getByRole('button', { name: 'Lock now', exact: true }).click();
    await lockResponse;

    await expect(page).toHaveURL(/\/setup$/, { timeout: 15000 });
    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });

    // While locked, the old token must not read profile data. Only "not ok" is
    // asserted: whether the refusal is a 401 or a 403 is SESSION-AUTH-DIFF's business.
    const staleRead = await request.get(`${E2E_API_URL}/documents/`, {
      headers: { Authorization: `Bearer ${auth.access_token}` },
    });
    expect(staleRead.ok()).toBe(false);

    // A protected route with no session goes back to the unlock card.
    await page.goto('/inbox');
    await expect(page).toHaveURL(/\/setup$/, { timeout: 15000 });
    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });

    // The password unlocks the profile, the vault really opens, and the user lands
    // on a protected route. This also leaves the profile unlocked for later specs.
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
    await page.getByLabel('Unlock password').fill(E2E_PROFILE_PASSWORD);
    const loginResponse = page.waitForResponse(
      (r) => new URL(r.url()).pathname.endsWith('/profiles/login') && r.status() === 200
    );
    const documentsResponse = page.waitForResponse(
      (r) =>
        r.request().method() === 'GET' &&
        /\/documents\/?$/.test(new URL(r.url()).pathname) &&
        r.status() === 200
    );
    await page.getByRole('button', { name: 'Unlock', exact: true }).click();
    await loginResponse;
    await documentsResponse;

    await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
    await expect(page.getByText('Your session has ended')).toHaveCount(0);
  });
});
