/**
 * Tailwind 3 -> 4 style guard (TW4-VISUAL).
 *
 * Computed-style asserts on elements that rely on Tailwind defaults (expected
 * values are the Tailwind 3 output), plus full-page screenshots of every route
 * with real seeded data. Screenshots never fail the job; CI uploads them.
 * No route mocking: all data comes from the backend's own write routes.
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import {
  E2E_API_URL,
  E2E_PROFILE_PASSWORD,
  ensureE2EProfile,
  openAuthenticatedPage,
} from './support/auth';

const SHOTS = 'test-results/tw4-shots';
const GLUCOSE_FILE = 'tw4-glucose.csv';
const A1C_FILE = 'tw4-a1c.csv';
const MED_NAME = 'TW4 Metformin';
const QUESTION = 'TW4 style check: what is my glucose level?';
const CSV_HEADER = 'Date,Analyte,Value,Unit,Reference Low,Reference High,Flag\n';
const GLUCOSE_CSV =
  CSV_HEADER +
  '2026-01-10,Glucose,92,mg/dL,70,99,\n' +
  '2026-04-10,Glucose,118,mg/dL,70,99,H\n' +
  '2026-07-10,Glucose,101,mg/dL,70,99,\n';
const A1C_CSV =
  CSV_HEADER +
  '2026-01-10,Hemoglobin A1c,5.4,%,4.0,5.6,\n' +
  '2026-04-10,Hemoglobin A1c,5.9,%,4.0,5.6,H\n' +
  '2026-07-10,Hemoglobin A1c,6.1,%,4.0,5.6,H\n';

test.use({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });

async function shot(page: Page, name: string) {
  await page.screenshot({
    fullPage: true,
    animations: 'disabled',
    path: `${SHOTS}/${name}.png`,
  });
}

async function expectOk(response: { ok(): boolean; status(): number; text(): Promise<string> }, what: string) {
  expect(response.ok(), `${what}: ${response.status()} ${await response.text()}`).toBeTruthy();
}

async function seed(request: APIRequestContext) {
  const auth = await ensureE2EProfile(request);
  const headers = { Authorization: `Bearer ${auth.access_token}` };

  // /recover lists only profiles that hold a recovery code.
  await expectOk(
    await request.post(`${E2E_API_URL}/profiles/${auth.profile_id}/recovery-code`, {
      headers,
      data: { password: E2E_PROFILE_PASSWORD },
    }),
    'issue recovery code'
  );

  // S1: two lab CSV imports (different content, so no hash dedupe between them).
  for (const [name, csv] of [
    [GLUCOSE_FILE, GLUCOSE_CSV],
    [A1C_FILE, A1C_CSV],
  ]) {
    await expectOk(
      await request.post(`${E2E_API_URL}/documents/import`, {
        headers,
        multipart: { file: { name, mimeType: 'text/csv', buffer: Buffer.from(csv) } },
      }),
      `import ${name}`
    );
  }

  // S2: verify the Glucose rows only; Hemoglobin A1c stays unverified for /verify.
  const listResponse = await request.get(`${E2E_API_URL}/observations/`, { headers });
  await expectOk(listResponse, 'list observations');
  const observations = (await listResponse.json()) as { id: string; analyte_canonical: string }[];
  const glucose = observations.filter((o) => /glucose/i.test(o.analyte_canonical));
  expect(glucose.length, 'glucose observations seeded').toBeGreaterThan(0);
  for (const obs of glucose) {
    await expectOk(
      await request.post(`${E2E_API_URL}/observations/${obs.id}/verify`, { headers, data: {} }),
      `verify ${obs.id}`
    );
  }

  // S3: one active medication with a once-daily schedule.
  const medResponse = await request.post(`${E2E_API_URL}/medications/`, {
    headers,
    data: { name: MED_NAME, dosage_amount: 500, dosage_unit: 'mg', frequency: 'once_daily' },
  });
  await expectOk(medResponse, 'create medication');
  const med = (await medResponse.json()) as { id: string };
  await expectOk(
    await request.post(`${E2E_API_URL}/medications/${med.id}/schedules`, {
      headers,
      data: { schedule_label: 'morning', target_time: '08:00' },
    }),
    'create schedule'
  );

  // S4: one assistant session with one real question (CI has no model).
  const sessionResponse = await request.post(`${E2E_API_URL}/assistant/sessions`, {
    headers,
    data: { title: QUESTION },
  });
  await expectOk(sessionResponse, 'create assistant session');
  const { session_id } = (await sessionResponse.json()) as { session_id: string };
  const chatResponse = await request.post(`${E2E_API_URL}/assistant/chat`, {
    headers,
    data: { question: QUESTION, session_id },
    timeout: 120_000,
  });
  await expectOk(chatResponse, 'assistant chat');
  const chat = (await chatResponse.json()) as { turn_id?: string; session_id?: string };
  expect(chat.turn_id, 'assistant chat persisted a turn').toBeTruthy();
  expect(chat.session_id).toBe(session_id);
}

test.describe('Tailwind 4 style guard', () => {
  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext({
      extraHTTPHeaders: { Origin: 'http://127.0.0.1:3000' },
    });
    try {
      await seed(request);
    } finally {
      await request.dispose();
    }
  });

  test('TW4-RECOVER: default border and placeholder (unauthenticated)', async ({ page }) => {
    await page.goto('/recover');
    // Target: RecoverProfile.tsx:136-143, bare border utility, no border colour or placeholder class.
    const input = page.locator('#recover-code');
    await expect(input).toBeVisible({ timeout: 15000 });
    expect(await input.evaluate((el) => getComputedStyle(el).borderTopColor)).toBe('rgb(229, 231, 235)');
    expect(await input.evaluate((el) => getComputedStyle(el, '::placeholder').color)).toBe(
      'rgb(156, 163, 175)'
    );
    await shot(page, 'recover');
  });

  test('TW4-SETUP: /setup screenshot (unauthenticated)', async ({ page }) => {
    await page.goto('/setup');
    await page.waitForLoadState('networkidle');
    await shot(page, 'setup');
  });

  test('TW4-INBOX: sidebar touch target, collision guards, focus ring', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/inbox');
    await expect(page.getByText(GLUCOSE_FILE).first()).toBeVisible({ timeout: 15000 });

    // Target: Sidebar NavLink (Sidebar.tsx:62-68).
    const nav = page.getByRole('navigation', { name: /main navigation/i }).getByRole('link').first();
    const box = await nav.boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    expect(await nav.evaluate((el) => getComputedStyle(el).minHeight)).toBe('44px');

    // Collision guards: body (globals.css:49), rounded-lg (DoseLoggingModal.tsx:100 close button,
    // checked in the modal test), text-ink (Sidebar.tsx:48 heading).
    expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe(
      'rgb(250, 250, 248)'
    );
    const heading = page.locator('aside h1').first();
    expect(await heading.evaluate((el) => getComputedStyle(el).color)).toBe('rgb(31, 31, 31)');

    // Cursor: TopBar.tsx:68-78 Button (`h-10 w-10 rounded-xl border-black/[0.06]` + Button.tsx cva) has
    // no cursor-* class and no ancestor in TopBar/layout carries one; enabled, so preflight gives pointer.
    const btn = page.getByRole('button', { name: 'Profile and settings' });
    await expect(btn).toBeEnabled();
    expect(await btn.evaluate((el) => getComputedStyle(el.parentElement!).cursor)).toBe('auto');
    expect(await btn.evaluate((el) => getComputedStyle(el).cursor)).toBe('pointer');

    // Focus ring relies on the global focus-visible rule (globals.css:65-67); the NavLink
    // (Sidebar.tsx:62-68) carries no outline class of its own.
    await nav.focus();
    const ring = await nav.evaluate((el) => {
      const s = getComputedStyle(el);
      return { boxShadow: s.boxShadow, outlineStyle: s.outlineStyle, outlineColor: s.outlineColor };
    });
    expect(ring.boxShadow).not.toBe('none');
    expect(ring.outlineStyle === 'none' || ring.outlineColor === 'rgba(0, 0, 0, 0)').toBeTruthy();

    await nav.blur();
    await shot(page, 'inbox');
  });

  test.describe('dark', () => {
    test.use({ colorScheme: 'dark' });
    test('TW4-INBOX-DARK: /inbox screenshot', async ({ page, request }) => {
      await openAuthenticatedPage(page, request, '/inbox');
      await expect(page.getByText(GLUCOSE_FILE).first()).toBeVisible({ timeout: 15000 });
      await shot(page, 'inbox-dark');
    });
  });

  test('TW4-VERIFY: /verify screenshot', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/verify');
    await expect(page.getByText(/hemoglobin a1c|hba1c/i).first()).toBeVisible({ timeout: 15000 });
    await shot(page, 'verify');
  });

  test('TW4-TRENDS: /trends screenshot', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/trends');
    await expect(page.getByText(/glucose/i).first()).toBeVisible({ timeout: 15000 });
    await shot(page, 'trends');
  });

  test('TW4-TIMELINE: /timeline screenshot', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/timeline');
    // Timeline never renders analyte names: labs are "Lab results (N analytes)"
    // (timeline.py:113), meds are "Started medication: <name>" (timeline.py:209).
    await expect(page.getByText(/Lab results \(/).first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(MED_NAME).first()).toBeVisible({ timeout: 15000 });
    await shot(page, 'timeline');
  });

  test('TW4-SEARCH: /search screenshot', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/search?q=Glucose');
    await expect(page.getByText(/glucose/i).first()).toBeVisible({ timeout: 15000 });
    await shot(page, 'search');
  });

  test('TW4-EXPLAIN: /explain screenshot', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/explain');
    await page.waitForLoadState('networkidle');
    await shot(page, 'explain-before-assert');
    await expect(page.getByText(/TW4 style check/i).first()).toBeVisible({ timeout: 15000 });
    await shot(page, 'explain');
  });

  test('TW4-SETTINGS: /settings screenshot', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/settings');
    await expect(page.getByRole('heading', { name: /settings/i }).first()).toBeVisible({
      timeout: 15000,
    });
    await shot(page, 'settings');
  });

  test('TW4-MEDS: /medications and open DoseLoggingModal', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/medications');
    await expect(page.getByText(MED_NAME).first()).toBeVisible({ timeout: 15000 });
    await shot(page, 'medications');

    await page.getByRole('button', { name: /^log$/i }).first().click();
    const dialogTitle = page.getByRole('heading', { name: 'Log Dose' });
    await expect(dialogTitle).toBeVisible();

    // Target: modal close button, explicit radius utility at DoseLoggingModal.tsx:100.
    const close = page.getByRole('button', { name: 'Close' });
    expect(await close.evaluate((el) => getComputedStyle(el).borderTopLeftRadius)).toBe('8px');
    await shot(page, 'dose-logging-modal');
  });
});
