/**
 * SESSION-REENTRY Task 3, "Lock now" (HC-SRE-012, plan §8.2).
 *
 * Real backend. After "Lock now" in the profile menu, the profile is locked: the
 * unlock card is the next screen, the old token is refused by a profile-data route,
 * a protected route sends the user back to /setup, and the password unlocks it.
 *
 * What these tests would not notice:
 * - a 401 versus a 403 on the stale token (only !ok is asserted; SESSION-AUTH-DIFF owns the code);
 * - a second lock POST from a double click on the real endpoint (HC-SRE-011 (a) and (d) cover
 *   it with a mocked API);
 * - a stale profile list or cache shown on /setup after the lock (only the card text is read);
 * - whether the vault keys were dropped on lock: the stale-token check shows only that the old
 *   token was refused (the token was revoked, or the vault was closed), and no read of vault
 *   data happens while the profile is locked.
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
    // Wait for the inbox list, so no request with this token is still in flight when Lock
    // now runs. A late 401 would clear the session in api.ts, not in ProfileMenu.
    const inboxLoaded = page.waitForResponse(
      (r) =>
        r.request().method() === 'GET' &&
        /\/documents\/?$/.test(new URL(r.url()).pathname) &&
        r.status() === 200
    );
    const auth = await openAuthenticatedPage(page, request, '/inbox');
    await inboxLoaded;
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

    // Lock now clears the persisted session, not only the screen: the stored token is gone.
    const persistedToken = await page.evaluate(() => {
      const raw = window.localStorage.getItem('healthcentral-auth');
      const persisted = raw ? (JSON.parse(raw) as { state: { token: string | null } }) : null;
      return persisted?.state.token ?? null;
    });
    expect(persistedToken).toBeNull();

    // While locked, the old token must not read profile data. Only "not ok" is
    // asserted: whether the refusal is a 401 or a 403 is SESSION-AUTH-DIFF's business.
    const staleRead = await request.get(`${E2E_API_URL}/documents/`, {
      headers: { Authorization: `Bearer ${auth.access_token}` },
    });
    expect(staleRead.ok()).toBe(false);

    // A protected route with no session goes back to the unlock card without loading its
    // data. The move stays in the page: a full load would re-run the seeded init script and
    // put the old token back. If the session were still there, the inbox would mount and
    // request its documents, so any such request means Lock now left the session in place.
    const inboxRequests: string[] = [];
    const onRequest = (req: { url(): string }) => {
      if (/\/documents\/?$/.test(new URL(req.url()).pathname)) inboxRequests.push(req.url());
    };
    page.on('request', onRequest);
    await page.evaluate(() => {
      window.history.pushState({}, '', '/inbox');
      window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
    });
    await expect(page).toHaveURL(/\/setup$/, { timeout: 15000 });
    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
    page.off('request', onRequest);
    expect(inboxRequests).toEqual([]);

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
