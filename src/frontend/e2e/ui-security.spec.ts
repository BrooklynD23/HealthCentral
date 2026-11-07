/**
 * UI-PG-SECURITY e2e (plan 7.9 "UI-PG-SECURITY"): HC-UISEC-001 and HC-UISEC-002 against the real backend, and Gate G
 * on /settings (Profile & security).
 *
 *  - HC-UISEC-001  delete with a wrong password shows "Incorrect password" and keeps the session (pin, GREEN on main)
 *  - HC-UISEC-002  the /api/v1 request sequence of the backup, restore and delete flows (pin, GREEN on main). The
 *                  three lists below were recorded on main's code (63bf37b2) before the restyle and are compared as
 *                  they are. They stay identical after it: the dialogs change the markup, not the requests.
 *  - Gate G        G1, G2, G3, G5, G6, G7, G9 and G10 on the security section and its two dialogs.
 *
 * Everything here goes through HTTP to the real backend (e2e/support/start-backend.mjs); there is no page.route and no
 * mock of auth or of a status code. Run it as recipe 1 in e2e/README.md:
 *   HC_E2E_BACKEND_PYTHON=<python with the backend requirements> TMPDIR=/dev/shm npx playwright test e2e/ui-security.spec.ts --project=chromium
 *
 * SAFETY: no test deletes or restores over the shared E2E profile (E2E_PROFILE_NAME). A success-path delete or
 * restore uses a throwaway profile created inside the test (and removed again if it still exists). The shared
 * profile only ever receives a wrong password: the backend refuses it before it touches anything.
 *
 * The first two pins select the password and phrase fields by id (#danger-password, #restore-password-*) and the
 * other controls by role and name, so the same file runs on the inline forms of main and on the dialogs of this row.
 * G2, G3, G5 and G10 are timing measurements: run them on a quiet box (select them with -g "GATE G"). G3 is mocked
 * (it needs no backend, so CI's production-build G3 job can run it); everything else here needs the backend.
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import {
  axeGate,
  consoleAndNetworkGuard,
  maxEventDuration,
  measureCls,
  noHorizontalScroll,
  reducedMotionSnapshot,
  ROUTE_CONTAINER_SELECTOR,
  ROUTE_FALLBACK_SELECTOR,
  safetyVisible,
  setTheme,
  stillnessProbe,
  type Theme,
} from './support/gates';
import { FIXTURE_PERSON, installMockApi, seedMockSession } from './support/mockApi';
import {
  E2E_API_URL,
  E2E_PROFILE_PASSWORD,
  openAuthenticatedPage,
  seedAuthenticatedSession,
} from './support/auth';

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };

const RESTORE_PHRASE = 'RESTORE MY DATA';
const DELETE_PHRASE = 'DELETE MY HEALTH DATA';
const WRONG_PASSWORD = `${E2E_PROFILE_PASSWORD}-wrong`;

interface Session {
  access_token: string;
  profile_id: string;
  profile_name: string;
  expires_in: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** A profile that exists only for one test. Creation runs two PBKDF2 derivations, so it takes a few seconds. */
async function createThrowawayProfile(request: APIRequestContext, label: string): Promise<{ session: Session; name: string }> {
  const name = `UiSec ${label} ${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  const created = await request.post(`${E2E_API_URL}/profiles/`, {
    data: { display_name: name, password: E2E_PROFILE_PASSWORD },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
  return { session: (await created.json()) as Session, name };
}

/** Removes a throwaway profile that a test left behind (a restore leaves one). Best effort. */
async function removeThrowawayProfile(request: APIRequestContext, profileId: string): Promise<void> {
  try {
    const login = await request.post(`${E2E_API_URL}/profiles/login`, {
      data: { profile_id: profileId, password: E2E_PROFILE_PASSWORD },
    });
    if (!login.ok()) return;
    const { access_token } = (await login.json()) as Session;
    await request.delete(`${E2E_API_URL}/profiles/${profileId}`, {
      headers: { Authorization: `Bearer ${access_token}` },
      data: { password: E2E_PROFILE_PASSWORD, confirmation_phrase: DELETE_PHRASE, export_acknowledged: true },
    });
  } catch {
    // The profile is a throwaway: a failed cleanup must not fail the test that already passed.
  }
}

/**
 * Signs the page in as a throwaway profile. The session is written after a first load, not with an init script: an init
 * script re-runs on every navigation and would put the session back after the app cleared it, hiding clearAuth.
 */
async function signInAs(page: Page, session: Session, name: string): Promise<void> {
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
}

async function createBackupViaApi(request: APIRequestContext, token: string): Promise<string> {
  const response = await request.post(`${E2E_API_URL}/backup/`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.ok(), await response.text()).toBeTruthy();
  return ((await response.json()) as { backup_id: string }).backup_id;
}

/** The shared profile needs one backup for the restore dialog to open on. A backup is harmless. */
async function ensureBackup(request: APIRequestContext, token: string): Promise<void> {
  const listing = await request.get(`${E2E_API_URL}/backup/`, { headers: { Authorization: `Bearer ${token}` } });
  expect(listing.ok(), await listing.text()).toBeTruthy();
  const { backups } = (await listing.json()) as { backups: unknown[] };
  if (backups.length === 0) await createBackupViaApi(request, token);
}

/** `METHOD /path` for every /api/v1 request from now on, with the ids replaced so two runs compare equal. */
function recordApiRequests(page: Page): { readonly seen: string[] } {
  const seen: string[] = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (!url.pathname.startsWith('/api/v1')) return;
    const path = url.pathname
      .replace(/^\/api\/v1/, '')
      .replace(/\/backup\/[^/]+\/(restore|download|verify)$/, '/backup/:backup/$1')
      .replace(/\/profiles\/[0-9a-f-]{36}/, '/profiles/:profile');
    seen.push(`${request.method()} ${path}`);
  });
  return { seen };
}

async function settle(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
  await expect
    .poll(
      () =>
        page.evaluate(
          ({ container, fallback }) => {
            const el = document.querySelector(container) ?? document.querySelector(fallback);
            return el ? parseFloat(getComputedStyle(el).opacity) : NaN;
          },
          { container: ROUTE_CONTAINER_SELECTOR, fallback: ROUTE_FALLBACK_SELECTOR }
        ),
      { timeout: 10_000 }
    )
    .toBeGreaterThanOrEqual(0.99);
}

async function expectSettingsLoaded(page: Page): Promise<void> {
  await expect(page.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('button', { name: /^(back up now|backing up)/i })).toBeVisible({ timeout: 15_000 });
}

const restoreButton = (page: Page) => page.getByRole('button', { name: /restore…/i }).first();
const deleteButton = (page: Page) => page.getByRole('button', { name: /delete profile/i });
const restoreDialog = (page: Page) => page.getByRole('alertdialog').filter({ hasText: RESTORE_PHRASE });
const deleteDialog = (page: Page) => page.getByRole('alertdialog').filter({ hasText: DELETE_PHRASE });

/** Fills the restore password and phrase. The ids are the same on the inline form and in the dialog. */
async function fillRestore(page: Page, password: string): Promise<void> {
  await page.locator('[id^="restore-password-"]').fill(password);
  await page.locator('[id^="restore-phrase-"]').fill(RESTORE_PHRASE);
}

/** Walks the delete steps in their order: the copy checkbox, the password, the phrase. `Back up and download` ticks the box itself, so it is checked, not clicked. */
async function fillDelete(page: Page, password: string): Promise<void> {
  await page.getByLabel(/i confirm i have a copy/i).check();
  await page.locator('#danger-password').fill(password);
  await page.locator('#danger-phrase').fill(DELETE_PHRASE);
}

async function storedAuth(page: Page): Promise<{ token: string | null; isAuthenticated: boolean } | null> {
  return page.evaluate(() => {
    const raw = localStorage.getItem('healthcentral-auth');
    if (!raw) return null;
    const state = JSON.parse(raw).state;
    return { token: state.token ?? null, isAuthenticated: Boolean(state.isAuthenticated) };
  });
}

// ---------------------------------------------------------------------------
// HC-UISEC-001: a wrong delete password keeps the session (MVP-REAUTH-401, pin).
// ---------------------------------------------------------------------------
test.describe('HC-UISEC-001 delete with a wrong password', () => {
  test('HC-UISEC-001: shows "Incorrect password" and keeps the session on /settings', async ({ page, request }) => {
    const session = await openAuthenticatedPage(page, request, '/settings');
    await expectSettingsLoaded(page);
    const before = await storedAuth(page);
    expect(before?.token, 'session was seeded').toBe(session.access_token);

    await deleteButton(page).click();
    await fillDelete(page, WRONG_PASSWORD);
    const deleteResponse = page.waitForResponse(
      (r) => r.request().method() === 'DELETE' && new URL(r.url()).pathname.endsWith(`/profiles/${session.profile_id}`),
      { timeout: 60_000 } // PBKDF2 key derivation is slow
    );
    await page.getByRole('button', { name: /permanently delete this profile/i }).click();
    expect((await deleteResponse).status()).toBe(401);

    await expect(page.getByRole('alert').filter({ hasText: 'Incorrect password' })).toBeVisible();
    // A redirect is asynchronous and the alert can flash before it lands: give a bad fix time to show itself.
    await page.waitForTimeout(1000);
    await expect(page.getByRole('alert').filter({ hasText: 'Incorrect password' })).toBeVisible();
    expect(new URL(page.url()).pathname).toBe('/settings');
    expect(await storedAuth(page)).toEqual(before);
    // Still signed in: a reload still lands on /settings with the page's own data loaded, and the stored session is the
    // same one. A data query that answered 401 a moment after first paint would clear it, so wait for the network to
    // go idle before reading it, and ask the backend that the token still opens a protected route.
    await page.reload();
    await expectSettingsLoaded(page);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    expect(new URL(page.url()).pathname).toBe('/settings');
    expect(await storedAuth(page)).toEqual(before);
    const stillValid = await request.get(`${E2E_API_URL}/backup/`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    });
    expect(stillValid.status(), 'the token still opens a protected route').toBe(200);
  });
});

// ---------------------------------------------------------------------------
// HC-UISEC-002: the request sequence of the backup, restore and delete flows (pin).
// Recorded on main's code before the restyle (see the header). Each list starts at the first press of the flow, on a page
// that has loaded and gone idle, and ends when the flow's last visible effect has happened and the network is idle again.
// ---------------------------------------------------------------------------
const BACKUP_SEQUENCE: string[] = [
  'POST /backup/',
  'GET /backup/',
  'GET /backup/schedule',
  'GET /backup/schedule',
];
const RESTORE_SEQUENCE: string[] = [
  'POST /backup/:backup/restore',
  'GET /profiles/', // the sign-in screen the app lands on once the restore has ended the session
];
const DELETE_SEQUENCE: string[] = [
  'POST /backup/',
  'GET /backup/',
  'GET /backup/schedule',
  'GET /backup/schedule',
  'GET /backup/:backup/download',
  'DELETE /profiles/:profile',
  'GET /profiles/', // the sign-in screen the app lands on once the profile is gone
];

test.describe('HC-UISEC-002 request sequence of backup, restore and delete', () => {
  test.describe.configure({ timeout: 180_000 });

  test('HC-UISEC-002: backup', async ({ page, request }) => {
    const { session, name } = await createThrowawayProfile(request, 'backup');
    try {
      await signInAs(page, session, name);
      await page.goto('/settings');
      await expectSettingsLoaded(page);
      await page.waitForLoadState('networkidle');

      const { seen } = recordApiRequests(page);
      await page.getByRole('button', { name: 'Back up now' }).click();
      await expect(page.getByRole('status').filter({ hasText: /^Backed up \d+ file\(s\)\.$/ })).toBeVisible({ timeout: 60_000 });
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      console.log(`HC-UISEC-002 backup: ${JSON.stringify(seen)}`);
      expect(seen).toEqual(BACKUP_SEQUENCE);
    } finally {
      await removeThrowawayProfile(request, session.profile_id);
    }
  });

  test('HC-UISEC-002: restore', async ({ page, request }) => {
    const { session, name } = await createThrowawayProfile(request, 'restore');
    try {
      await createBackupViaApi(request, session.access_token);
      await signInAs(page, session, name);
      await page.goto('/settings');
      await expectSettingsLoaded(page);
      await expect(restoreButton(page)).toBeVisible({ timeout: 15_000 });
      await page.waitForLoadState('networkidle');

      const { seen } = recordApiRequests(page);
      await restoreButton(page).click();
      await fillRestore(page, E2E_PROFILE_PASSWORD);
      const restoreResponse = page.waitForResponse(
        (r) => r.request().method() === 'POST' && /\/backup\/[^/]+\/restore$/.test(new URL(r.url()).pathname),
        { timeout: 90_000 }
      );
      await page.getByRole('button', { name: 'Restore this backup' }).click();
      expect((await restoreResponse).status()).toBe(200);
      // The restore ends the session: the stored auth is cleared.
      await expect.poll(async () => (await storedAuth(page))?.isAuthenticated ?? false, { timeout: 30_000 }).toBe(false);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      console.log(`HC-UISEC-002 restore: ${JSON.stringify(seen)}`);
      expect(seen).toEqual(RESTORE_SEQUENCE);
    } finally {
      await removeThrowawayProfile(request, session.profile_id);
    }
  });

  test('HC-UISEC-002: delete', async ({ page, request }) => {
    const { session, name } = await createThrowawayProfile(request, 'delete');
    try {
      await signInAs(page, session, name);
      await page.goto('/settings');
      await expectSettingsLoaded(page);
      await page.waitForLoadState('networkidle');

      const { seen } = recordApiRequests(page);
      await deleteButton(page).click();
      await page.getByRole('button', { name: 'Back up and download' }).click();
      await expect(page.getByText(/downloaded the archive/)).toBeVisible({ timeout: 60_000 });
      await fillDelete(page, E2E_PROFILE_PASSWORD);
      const deleteResponse = page.waitForResponse(
        (r) => r.request().method() === 'DELETE' && new URL(r.url()).pathname.endsWith(`/profiles/${session.profile_id}`),
        { timeout: 90_000 }
      );
      await page.getByRole('button', { name: /permanently delete this profile/i }).click();
      expect((await deleteResponse).status()).toBeLessThan(300);
      await expect.poll(async () => (await storedAuth(page))?.isAuthenticated ?? false, { timeout: 30_000 }).toBe(false);
      await expect.poll(() => new URL(page.url()).pathname, { timeout: 30_000 }).not.toBe('/settings');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      console.log(`HC-UISEC-002 delete: ${JSON.stringify(seen)}`);
      expect(seen).toEqual(DELETE_SEQUENCE);
    } finally {
      await removeThrowawayProfile(request, session.profile_id);
    }
  });
});

// ---------------------------------------------------------------------------
// Gate G on /settings (Profile & security). G1, G6, G7 and G9 are not timing measurements; G2, G3, G5 and G10 are.
// The shared E2E profile is only read, given a recovery code (as recovery-code.spec.ts does) and sent wrong passwords.
// ---------------------------------------------------------------------------
const THEMES: Theme[] = ['light', 'dark'];

/** Opens /settings as the shared profile, with one backup in place so the restore dialog can open. */
async function openSecurity(page: Page, request: APIRequestContext, viewport = DESKTOP) {
  await page.setViewportSize(viewport);
  const guard = consoleAndNetworkGuard(page);
  const session = await seedAuthenticatedSession(page, request);
  await ensureBackup(request, session.access_token);
  await page.goto('/settings');
  await expectSettingsLoaded(page);
  await expect(restoreButton(page)).toBeVisible({ timeout: 15_000 });
  await settle(page);
  return { session, guard };
}

/** setTheme, then wait for the colour transitions it starts: axe reads computed colours, and a read mid-fade is neither theme's. */
async function applyTheme(page: Page, theme: Theme) {
  await setTheme(page, theme);
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((animation) => animation instanceof CSSTransition)
        .map((animation) => animation.finished.catch(() => undefined))
    )
  );
}

/** Waits until the element and every ancestor are at opacity 1: axe must not read a dialog mid-fade. */
async function waitUntilOpaque(page: Page, selector: string) {
  await page.waitForFunction((target) => {
    for (let node: Element | null = document.querySelector(target); node; node = node.parentElement) {
      if (parseFloat(getComputedStyle(node).opacity) < 1) return false;
    }
    return document.querySelector(target) !== null;
  }, selector);
}

async function expectNoBlockingViolations(page: Page, theme: Theme, where: string) {
  const result = await axeGate(page);
  expect(
    result.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
    `G1 ${where} ${theme}`
  ).toEqual([]);
}

async function expectRailVisible(page: Page, where: string) {
  const rail = await safetyVisible(page);
  expect(rail.found && rail.inViewport && rail.effectiveOpacity >= 0.99, `G9 ${where} ${JSON.stringify(rail)}`).toBe(true);
}

/** Issues (or replaces) a recovery code on the shared profile and waits for it to show. */
async function issueRecoveryCode(page: Page): Promise<void> {
  await page.locator('#recovery-code-password').fill(E2E_PROFILE_PASSWORD);
  await page.getByRole('button', { name: /(create|replace) recovery code/i }).click();
  await expect(page.getByTestId('recovery-code-value')).toBeVisible({ timeout: 30_000 });
}

for (const theme of THEMES) {
  test(`UI-PG-SECURITY GATE G1, G7, G9 on /settings (${theme})`, async ({ page, request }) => {
    test.setTimeout(180_000);
    const { guard } = await openSecurity(page, request);
    await expectRailVisible(page, 'first paint');
    await applyTheme(page, theme);
    await expectNoBlockingViolations(page, theme, 'security section');

    // The recovery code, with both of its warnings.
    await issueRecoveryCode(page);
    await expect(page.getByTestId('recovery-code-once-warning')).toBeVisible();
    await expectNoBlockingViolations(page, theme, 'recovery code shown');
    await page.getByRole('button', { name: 'I have saved it' }).click();

    // The restore dialog, then the same dialog with its error showing.
    await restoreButton(page).click();
    await expect(restoreDialog(page)).toBeVisible();
    await waitUntilOpaque(page, '[role="alertdialog"]');
    await expectNoBlockingViolations(page, theme, 'restore dialog');
    await expectRailVisible(page, 'restore dialog');
    await fillRestore(page, WRONG_PASSWORD);
    await page.getByRole('button', { name: 'Restore this backup' }).click();
    await expect(restoreDialog(page).getByRole('alert')).toContainText('Incorrect password', { timeout: 60_000 });
    await expectNoBlockingViolations(page, theme, 'restore dialog with an error');
    await page.keyboard.press('Escape');
    await expect(page.getByRole('alertdialog')).toHaveCount(0);

    // The delete dialog, then the same dialog with its error showing.
    await deleteButton(page).click();
    await expect(deleteDialog(page)).toBeVisible();
    await waitUntilOpaque(page, '[role="alertdialog"]');
    await expectNoBlockingViolations(page, theme, 'delete dialog');
    await expectRailVisible(page, 'delete dialog');
    await fillDelete(page, WRONG_PASSWORD);
    await page.getByRole('button', { name: /permanently delete this profile/i }).click();
    await expect(deleteDialog(page).getByRole('alert')).toContainText('Incorrect password', { timeout: 60_000 });
    await expectNoBlockingViolations(page, theme, 'delete dialog with an error');
    await page.keyboard.press('Escape');
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await expectRailVisible(page, 'after');

    // G7: the two wrong passwords above answer 401, which the browser logs as a failed resource load. That is the
    // behaviour under test, so only a console error that is not one of those fails the gate.
    const report = guard.report();
    expect(
      report.consoleErrors.filter((text) => !/status of 401/.test(text)),
      'G7 console errors'
    ).toEqual([]);
    expect(report.externalRequests, 'G7 non-localhost requests').toEqual([]);
  });
}

test('UI-PG-SECURITY GATE G6 on /settings: no horizontal scroll at 390 and 320', async ({ page, request }) => {
  test.setTimeout(180_000);
  await openSecurity(page, request, PHONE);
  for (const [name, size] of [['390', PHONE], ['320', SMALL_PHONE]] as const) {
    await page.setViewportSize(size);
    await page.waitForLoadState('networkidle');
    expect((await noHorizontalScroll(page)).ok, `G6 ${name} security section`).toBe(true);

    await issueRecoveryCode(page);
    expect((await noHorizontalScroll(page)).ok, `G6 ${name} recovery code shown`).toBe(true);
    await page.getByRole('button', { name: 'I have saved it' }).click();

    await restoreButton(page).click();
    await expect(restoreDialog(page)).toBeVisible();
    expect((await noHorizontalScroll(page)).ok, `G6 ${name} restore dialog`).toBe(true);
    // The dialog scrolls its own content, so its actions stay reachable at 640 px tall.
    const cancel = restoreDialog(page).getByRole('button', { name: 'Cancel' });
    await cancel.scrollIntoViewIfNeeded();
    await expect(cancel).toBeInViewport();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('alertdialog')).toHaveCount(0);

    await deleteButton(page).click();
    await expect(deleteDialog(page)).toBeVisible();
    expect((await noHorizontalScroll(page)).ok, `G6 ${name} delete dialog`).toBe(true);
    const sheetBox = await deleteDialog(page).boundingBox();
    expect(sheetBox && sheetBox.x >= 0 && sheetBox.x + sheetBox.width <= size.width, `G6 ${name} delete dialog inside the viewport`).toBe(true);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
  }
});

/** The two dialogs opened and closed the way a patient would, with something typed into the delete form. */
async function dialogInteractions(page: Page): Promise<void> {
  await restoreButton(page).click();
  await expect(restoreDialog(page)).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('alertdialog')).toHaveCount(0);
  await deleteButton(page).click();
  await expect(deleteDialog(page)).toBeVisible();
  await page.getByLabel(/i confirm i have a copy/i).click();
  await page.locator('#danger-password').fill('typed-but-not-sent');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('alertdialog')).toHaveCount(0);
}

// The G3 title is its own test on purpose. CI's "G3 on Production Build" job selects titles by --grep '\bG3\b' and runs
// no backend (ci.yml), so the G3 measurement here is MOCKED (installMockApi, the shared fixtures; the same convention as
// ui-settings.spec.ts) and no real-backend test below carries "G3" in its title. G3 reads timing, not auth or a status
// code, so the mock does not stand in for anything the backend decides. Run it on a production build, quiet box:
//   npm run build; npx vite preview --host 127.0.0.1 --port 4173 --strictPort &
//   HC_E2E_BASE_URL=http://127.0.0.1:4173 PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-security.spec.ts --project=chromium -g "G3"
test('UI-PG-SECURITY GATE G3 on /settings: the dialogs open and close under 200 ms with CPU throttled x4 (mocked, quiet box only)', async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize(DESKTOP);
  await installMockApi(page);
  // Registered after installMockApi, so it wins: one backup, so that the restore dialog has something to open on.
  await page.route(/\/api\/v1\/backup\/?$/, (route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        backups: [{ backup_id: 'backup_fixture_1', created_at: '2026-10-20T08:00:00Z', file_count: 3, size_bytes: 2048 }],
        backup_directory: '/fixture/backups',
        last_backup_at: '2026-10-20T08:00:00Z',
      }),
    });
  });
  await seedMockSession(page, FIXTURE_PERSON);
  await page.goto('/settings');
  await expectSettingsLoaded(page);
  await expect(restoreButton(page)).toBeVisible({ timeout: 15_000 });
  await settle(page);
  // Returns 0 when no event reaches 16 ms, so a dead observer also passes; the bound is the gate's, unchanged.
  const inp = await maxEventDuration(page, () => dialogInteractions(page), { cpuRate: 4 });
  console.log(`UI-PG-SECURITY G3 /settings (${process.env.HC_E2E_BASE_URL ? 'production build' : 'dev server'}): ${inp} ms`);
  expect(inp, 'G3 /settings').toBeLessThan(200);
});

test('UI-PG-SECURITY GATE G2 and G5 on /settings (real backend, quiet box only)', async ({ page, request }) => {
  test.setTimeout(180_000);
  await page.setViewportSize(DESKTOP);
  const session = await seedAuthenticatedSession(page, request);
  await ensureBackup(request, session.access_token);

  // G2: layout shift over the load and the interactions.
  const cls = await measureCls(page, async () => {
    await page.goto('/settings');
    await expectSettingsLoaded(page);
    await expect(restoreButton(page)).toBeVisible({ timeout: 15_000 });
    await settle(page);
    await dialogInteractions(page);
  });
  expect(cls, 'G2 /settings').toBeLessThan(0.1);

  // G5: reduced motion, one snapshot 50 ms after each interaction, so a transform one step leaves behind is not cleared by the next.
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/settings');
  await expect(restoreButton(page)).toBeVisible({ timeout: 15_000 });
  await settle(page);
  const steps: Array<[string, () => Promise<void>]> = [
    ['restore dialog opens', async () => { await restoreButton(page).click(); await expect(restoreDialog(page)).toBeVisible(); }],
    ['restore dialog closes', async () => { await page.keyboard.press('Escape'); await expect(page.getByRole('alertdialog')).toHaveCount(0); }],
    ['delete dialog opens', async () => { await deleteButton(page).click(); await expect(deleteDialog(page)).toBeVisible(); }],
    ['delete dialog closes', async () => { await page.keyboard.press('Escape'); await expect(page.getByRole('alertdialog')).toHaveCount(0); }],
  ];
  const offenders: string[] = [];
  for (const [name, step] of steps) {
    offenders.push(...(await reducedMotionSnapshot(page, step)).map((offender) => `${name}: ${offender}`));
  }
  expect(offenders, 'G5 /settings').toEqual([]);
});

test.describe('UI-PG-SECURITY GATE G10 (quiet box only)', () => {
  test.describe.configure({ timeout: 180_000 });

  // The opener may sit below the fold: if the click scrolled the page, every T0 rect on it would move inside the
  // probe's window. Scroll first, so the probe sees the press and nothing else.
  test('UI-PG-SECURITY GATE G10 on the restore dialog opening', async ({ page, request }) => {
    await openSecurity(page, request);
    await page.evaluate(() => document.fonts.ready);
    await restoreButton(page).scrollIntoViewIfNeeded();
    const report = await stillnessProbe(page, {
      trigger: () => restoreButton(page).click(),
      expected: ['[role="alertdialog"] [data-t0]'],
      kind: 'overlay',
    });
    expect(report.nodes).toBeGreaterThan(0);
    await expect(restoreDialog(page)).toBeVisible();
  });

  test('UI-PG-SECURITY GATE G10 on the delete dialog opening', async ({ page, request }) => {
    await openSecurity(page, request);
    await page.evaluate(() => document.fonts.ready);
    await deleteButton(page).scrollIntoViewIfNeeded();
    const report = await stillnessProbe(page, {
      trigger: () => deleteButton(page).click(),
      expected: ['[role="alertdialog"] [data-t0]'],
      kind: 'overlay',
    });
    expect(report.nodes).toBeGreaterThan(0);
    await expect(deleteDialog(page)).toBeVisible();
  });

  // Not probed here: the recovery code appearing. Its card is taller with the code showing than with the password form, so
  // every [data-t0] warning on the cards below it moves down in the same frame, and the probe (rightly) reads that as
  // movement. The recovery code, its warnings and its alert carry data-t0 (checked in ui-security.test.tsx) and the
  // reveal has no animation; its layout shift is inside G2's budget (the code is issued in the G1 and G6 tests).

  test('UI-PG-SECURITY GATE G10 on the restore error appearing', async ({ page, request }) => {
    await openSecurity(page, request);
    await page.evaluate(() => document.fonts.ready);
    await restoreButton(page).scrollIntoViewIfNeeded();
    await restoreButton(page).click();
    await expect(restoreDialog(page)).toBeVisible();
    await fillRestore(page, WRONG_PASSWORD);
    const report = await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: 'Restore this backup' }).click(),
      expected: ['[role="alert"][data-t0]'],
      lazyRoute: true,
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('UI-PG-SECURITY GATE G10 on the delete error appearing', async ({ page, request }) => {
    await openSecurity(page, request);
    await page.evaluate(() => document.fonts.ready);
    await deleteButton(page).scrollIntoViewIfNeeded();
    await deleteButton(page).click();
    await expect(deleteDialog(page)).toBeVisible();
    await fillDelete(page, WRONG_PASSWORD);
    const report = await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: /permanently delete this profile/i }).click(),
      expected: ['[role="alert"][data-t0]'],
      lazyRoute: true,
    });
    expect(report.nodes).toBeGreaterThan(0);
  });
});
