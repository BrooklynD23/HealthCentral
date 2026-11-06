/**
 * SAFETY-MODE-TOGGLE, HC-SMT-005 (real backend).
 *
 * The stricter safety mode switch persists on the server, per profile: on, reload, still on (the
 * server's own value is read through the API, so a surviving cache cannot pass it); off, reload, still
 * off. At 1024 and 1440 px the note is not clipped once the fonts have loaded.
 *
 * The E2E profile is shared by the real-backend specs, so the flag is put back to off before and after
 * every test, through the API, also when the test fails.
 *
 * What these tests would not notice:
 * - the vitest-only behaviours (rollback on a failed PATCH, the unknown state, the invalidated query
 *   keys): HC-SMT-002, 003 and 006 hold those with a mocked API;
 * - a second profile reading this profile's flag (the route's own tests hold per-profile scoping);
 * - clipping at widths other than 1024 and 1440, or in a font that is not installed on this machine;
 * - a note that is clipped sideways: only scrollHeight against clientHeight is compared.
 */

import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { E2E_API_URL, ensureE2EProfile, openAuthenticatedPage } from './support/auth';

const SAFETY_MODE_URL = `${E2E_API_URL}/assistant/safety-mode`;

async function readServerValue(request: APIRequestContext, token: string): Promise<unknown> {
  const response = await request.get(SAFETY_MODE_URL, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.ok(), await response.text()).toBeTruthy();
  return ((await response.json()) as { strict_safety_mode?: unknown }).strict_safety_mode;
}

/** Puts the flag back to off through the API, with a fresh login so it does not depend on the test's page. */
async function resetFlagToOff(request: APIRequestContext): Promise<void> {
  const { access_token: token } = await ensureE2EProfile(request);
  const response = await request.patch(SAFETY_MODE_URL, {
    headers: { Authorization: `Bearer ${token}` },
    data: { strict_safety_mode: false },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  expect(await readServerValue(request, token)).toBe(false);
}

function waitForPatch(page: Page) {
  return page.waitForResponse(
    (r) => r.request().method() === 'PATCH' && new URL(r.url()).pathname.endsWith('/assistant/safety-mode') && r.status() === 200
  );
}

test.describe('SAFETY-MODE-TOGGLE persistence', () => {
  test.beforeEach(async ({ request }) => {
    await resetFlagToOff(request);
  });

  test.afterEach(async ({ request }) => {
    await resetFlagToOff(request);
  });

  test('HC-SMT-005: on survives a reload, off survives a reload, and the note is not clipped', async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);
    await page.setViewportSize({ width: 1440, height: 900 });
    const auth = await openAuthenticatedPage(page, request, '/inbox');
    const toggle = page.getByRole('switch', { name: 'Stricter safety mode' });

    // Off at the start: the server's value, shown on an enabled switch.
    await expect(toggle).toBeEnabled({ timeout: 30_000 });
    await expect(toggle).toHaveAttribute('aria-checked', 'false');

    // Switch on, reload, still on. The API is asked too, so the check is the server's value and not a cache.
    const turnedOn = waitForPatch(page);
    await toggle.click();
    await turnedOn;
    await expect(toggle).toHaveAttribute('aria-checked', 'true');
    expect(await readServerValue(request, auth.access_token)).toBe(true);
    await page.reload();
    await expect(toggle).toBeEnabled({ timeout: 30_000 });
    await expect(toggle).toHaveAttribute('aria-checked', 'true');

    // Switch off, reload, still off.
    const turnedOff = waitForPatch(page);
    await toggle.click();
    await turnedOff;
    await expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(await readServerValue(request, auth.access_token)).toBe(false);
    await page.reload();
    await expect(toggle).toBeEnabled({ timeout: 30_000 });
    await expect(toggle).toHaveAttribute('aria-checked', 'false');

    // The note is not clipped once the fonts have loaded (a hidden note would read 0 = 0, so it must have a height).
    for (const width of [1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.evaluate(() => document.fonts.ready);
      const note = await page.locator('[data-safety-toggle-note]').evaluate((el) => ({
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
      }));
      expect(note.clientHeight, `note clientHeight at ${width} px`).toBeGreaterThan(0);
      expect(note.scrollHeight, `note scrollHeight at ${width} px`).toBe(note.clientHeight);
    }
  });
});
