/**
 * Recovery code entry point (SEC-RECOV-002).
 *
 * The unit tests mock the API; this proves the surface works against the real
 * backend — that the endpoint accepts what the form sends, and that the code is
 * genuinely shown once rather than re-readable after a reload.
 */

import { test, expect } from '@playwright/test';
import { openAuthenticatedPage } from './support/auth';
import { E2E_PROFILE_PASSWORD } from './support/auth';

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
});
