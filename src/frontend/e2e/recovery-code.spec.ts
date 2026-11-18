/**
 * Recovery code entry point (SEC-RECOV-002).
 *
 * The unit tests mock the API; this proves the surface works against the real
 * backend — that the endpoint accepts what the form sends, and that the code is
 * genuinely shown once rather than re-readable after a reload.
 */

import { test, expect } from '@playwright/test';
import { openAuthenticatedPage } from './support/auth';
import { E2E_API_URL, E2E_PROFILE_PASSWORD } from './support/auth';

test.describe('SEC-RECOV-002 recovery code', () => {
  test('E2E-RECOV-001: issues a code, shows it once, and does not show it again after reload', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/settings');

    const passwordField = page.getByLabel(/confirm your password/i);
    await expect(passwordField).toBeVisible({ timeout: 15000 });
    await passwordField.fill(E2E_PROFILE_PASSWORD);

    await page
      .getByRole('button', { name: /(create|replace) recovery code/i })
      .click();

    const codeValue = page.getByTestId('recovery-code-value');
    await expect(codeValue).toBeVisible({ timeout: 15000 });
    const issued = (await codeValue.textContent())?.trim();
    expect(issued).toBeTruthy();

    await expect(page.getByTestId('recovery-code-once-warning')).toBeVisible();

    // The code is held in component state only. A reload must not bring it
    // back — if it does, it is being persisted somewhere it should not be.
    await page.reload();
    await expect(page.getByTestId('recovery-code-value')).toHaveCount(0);
    await expect(page.locator('body')).not.toContainText(issued!);
  });

  test('E2E-RECOV-002: a profile with a code offers replacement, warning that the old one dies', async ({
    page,
    request,
  }) => {
    // E2E-RECOV-001 leaves the profile holding a code; if this spec runs first,
    // issue one so the state under test exists either way.
    await openAuthenticatedPage(page, request, '/settings');

    // Branch on the settled state, never on a bare count(): the card's label
    // depends on `GET /profiles/`, so counting before React Query resolves
    // reads "absent" for a card that is merely still loading, and takes the
    // wrong branch. Wait for the button, then read what it says.
    const actionButton = page.getByRole('button', {
      name: /(create|replace) recovery code/i,
    });
    await expect(actionButton).toBeVisible({ timeout: 15000 });

    if (!/replace/i.test((await actionButton.textContent()) ?? '')) {
      await page.getByLabel(/confirm your password/i).fill(E2E_PROFILE_PASSWORD);
      await actionButton.click();
      await expect(page.getByTestId('recovery-code-value')).toBeVisible({
        timeout: 15000,
      });
      await page.reload();
    }

    await expect(page.getByTestId('recovery-code-replace-warning')).toBeVisible({
      timeout: 15000,
    });
    await expect(
      page.getByRole('button', { name: /replace recovery code/i })
    ).toBeVisible();
  });

  test('E2E-RECOV-003: a wrong recovery code shows the alert and keeps the patient on /recover, signed in', async ({
    page,
    request,
  }) => {
    // Own profile: the recover rate limit is keyed per profile, so failures on
    // the shared E2E profile (here or in other specs) must not make this a 429.
    const name = `Recover401 ${Date.now()}`;
    const created = await request.post(`${E2E_API_URL}/profiles/`, {
      data: { display_name: name, password: E2E_PROFILE_PASSWORD },
    });
    expect(created.ok(), await created.text()).toBeTruthy();
    const session = (await created.json()) as {
      access_token: string;
      profile_id: string;
      expires_in: number;
    };

    // Seed a real session without addInitScript: an init script re-runs on every
    // navigation and would re-seed auth after a redirect, hiding clearAuth.
    await page.goto('/recover');
    await page.evaluate(
      ({ s, profileName }) => {
        localStorage.setItem(
          'healthcentral-auth',
          JSON.stringify({
            state: {
              token: s.access_token,
              profileId: s.profile_id,
              profileName,
              expiresAt: Date.now() + s.expires_in * 1000,
              isAuthenticated: true,
            },
            version: 0,
          })
        );
      },
      { s: session, profileName: name }
    );
    await page.reload();

    const before = await page.evaluate(() => localStorage.getItem('healthcentral-auth'));
    expect(before, 'auth was not seeded').toBeTruthy();
    expect(JSON.parse(before!).state.token).toBe(session.access_token);

    await page.getByLabel('Profile', { exact: true }).selectOption({ label: name });
    // Well formed on purpose: a malformed code answers 400, which could not fail.
    await page.locator('#recover-code').fill('0000-0000-0000-0000-0000-0000-0000-0000');
    await page.getByLabel('New password').fill('BrandNewPass456');

    const recoverResponse = page.waitForResponse(
      (r) =>
        r.request().method() === 'POST' &&
        new URL(r.url()).pathname.endsWith(`/profiles/${session.profile_id}/recover`),
      { timeout: 60000 } // PBKDF2 key derivation is slow
    );
    await page.getByRole('button', { name: /unlock my records/i }).click();
    expect((await recoverResponse).status()).toBe(401);

    await expect(page.getByRole('alert')).toContainText(/not valid/i);

    // A redirect is asynchronous and the alert can flash before it lands, so
    // give a bad fix time to show itself before asserting nothing moved.
    await page.waitForTimeout(1000);
    await expect(page.getByRole('alert')).toContainText(/not valid/i);
    expect(new URL(page.url()).pathname).toBe('/recover');
    expect(await page.evaluate(() => localStorage.getItem('healthcentral-auth'))).toBe(before);
  });
});
