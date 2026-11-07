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
 * SAFETY-MODE-CITATIONS, HC-SMC-005 (real backend), appended below: with the mode on, one question is asked and
 * the answer's sources are on screen without a click.
 *
 * What these tests would not notice:
 * - the vitest-only behaviours (rollback on a failed PATCH, the unknown state, the invalidated query
 *   keys): HC-SMT-002, 003 and 006 hold those with a mocked API;
 * - a second profile reading this profile's flag (the route's own tests hold per-profile scoping);
 * - clipping at widths other than 1024 and 1440, or in a font that is not installed on this machine;
 * - a note that is clipped sideways: only scrollHeight against clientHeight is compared.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { E2E_API_URL, ensureE2EProfile, openAuthenticatedPage, resetE2EProfile } from './support/auth';

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

// ---------------------------------------------------------------------------
// SAFETY-MODE-CITATIONS, HC-SMC-005: sources are visible without a click.
// ---------------------------------------------------------------------------

const SYNTHETIC_LAB_PDF = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures', 'synthetic-lab.pdf');

test.describe('SAFETY-MODE-CITATIONS sources without a click', () => {
  test.beforeEach(async ({ request }) => {
    await resetFlagToOff(request);
  });

  // The test imports a document into the shared E2E profile, so it puts the profile back as global-setup found it
  // (the reset also drops the flag, which is then written off again through the API).
  test.afterEach(async ({ request }) => {
    const { access_token: token } = await ensureE2EProfile(request);
    await resetE2EProfile(request, token);
    await resetFlagToOff(request);
  });

  test('HC-SMC-005: mode on, one question, the sources are visible without a click', async ({ page, request }) => {
    test.setTimeout(240_000);
    await page.setViewportSize({ width: 1440, height: 900 });

    // Real data: import the synthetic report and mark its values as checked, so an answer has records to cite.
    const { access_token: token } = await ensureE2EProfile(request);
    const headers = { Authorization: `Bearer ${token}` };
    await resetE2EProfile(request, token);
    const imported = await request.post(`${E2E_API_URL}/documents/import`, {
      headers,
      multipart: { file: { name: 'synthetic-lab.pdf', mimeType: 'application/pdf', buffer: fs.readFileSync(SYNTHETIC_LAB_PDF) } },
    });
    expect(imported.ok(), await imported.text()).toBeTruthy();
    const observationsResponse = await request.get(`${E2E_API_URL}/observations/`, { headers });
    expect(observationsResponse.ok(), await observationsResponse.text()).toBeTruthy();
    const observations = (await observationsResponse.json()) as { id: string }[];
    expect(observations.length).toBeGreaterThanOrEqual(1);
    for (const observation of observations) {
      const verified = await request.post(`${E2E_API_URL}/observations/${observation.id}/verify`, { headers, data: {} });
      expect(verified.ok(), await verified.text()).toBeTruthy();
    }

    await openAuthenticatedPage(page, request, '/explain');
    const toggle = page.getByRole('switch', { name: 'Stricter safety mode' });
    await expect(toggle).toBeEnabled({ timeout: 30_000 });
    const turnedOn = waitForPatch(page);
    await toggle.click();
    await turnedOn;
    await expect(toggle).toHaveAttribute('aria-checked', 'true');

    await page.getByPlaceholder(/ask about your results/i).fill('What is my hemoglobin level?');
    await page.getByRole('button', { name: 'Send question' }).click();

    // The selectors ROUTES-002 depends on still resolve: one patient message, one answer.
    const answer = page.locator('[data-testid="chat-message"][data-role="assistant"]');
    await expect(answer).toHaveCount(1, { timeout: 180_000 });
    await expect(page.locator('[data-testid="chat-message"][data-role="user"]')).toHaveCount(1);

    // No click: the sources block and its "[N] Source: name" line are on screen, and no popover is open.
    await expect(answer.getByText('Sources:')).toBeVisible();
    await expect(answer.getByText(/^\[\d+\] Source: /).first()).toBeVisible();
    await expect(page.getByRole('dialog')).toHaveCount(0);

    // The honesty rule on the real agent path: text_snippet is a locator or a row id there, so any quotation that is
    // drawn must hold real words (whitespace), never "docId:page" or a bare id.
    for (const quote of await answer.locator('blockquote').allInnerTexts()) {
      expect(quote.trim(), 'a blockquote must hold words, not a locator').toMatch(/\s/);
    }
  });
});
