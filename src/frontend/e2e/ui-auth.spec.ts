/**
 * UI-PG-AUTH e2e (plan section 7.8), real backend: Gate G on /setup and /recover, the Lift on unlock
 * (HC-UIAUTH-003), the recovery code in 4-character groups (HC-UIAUTH-004) and stillness of every error and of
 * the recovery-code step (HC-UIAUTH-005).
 *
 * Presentation only (L0 AUTH GUARD): nothing here changes what is sent or kept. The backend and the E2E profile
 * come from the normal harness (playwright.config.ts starts both).
 *
 * Timing gates (G2, G3, G5, G10, and the Lift timing of HC-UIAUTH-003) are measurements: run them on a quiet box
 * only. Their titles end in "(timing)". `--grep '\(timing\)'` selects them; `--grep-invert '\(timing\)'` is the
 * functional run (no describe title carries the word, so nothing leaves the functional run by accident).
 *
 * G3 is measured on a production build (plan section 6), against the real backend. Preview must therefore sit on
 * port 3000: the backend's local CORS list is http://127.0.0.1:3000 and http://localhost:3000 only
 * (src/backend/main.py), and extraHTTPHeaders sends that Origin, so a preview on 4173 (e2e/README recipe 3, which
 * runs without a backend) would have its API calls refused. The config reuses a server already answering on 3000
 * instead of starting the dev server, and starts the backend itself. From the repo root, build first (heavy; the
 * quiet box does not need to be quiet for it), then measure:
 *
 *   cd src/frontend
 *   VITE_API_URL=http://127.0.0.1:8000/api/v1 ../../scripts/pyslot.sh npm run build
 *   /tmp/claude-1000/quiet_run.sh bash -c '
 *     cd src/frontend
 *     npx vite preview --host 127.0.0.1 --port 3000 --strictPort & PV=$!
 *     trap "kill $PV" EXIT
 *     sleep 3
 *     HC_E2E_BACKEND_PYTHON=/home/danny/venvs/asclexis-311/bin/python HC_E2E_BASE_URL=http://127.0.0.1:3000 \
 *       npx playwright test e2e/ui-auth.spec.ts --project=chromium --grep "G3 "'
 *
 * Not run when written (L0 owns the quiet box): the CORS reasoning is from reading, so the first run is also the
 * check; a CORS refusal shows as every API call failing with "net::ERR_FAILED" in the trace.
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import {
  axeGate,
  consoleAndNetworkGuard,
  maxEventDuration,
  measureCls,
  noHorizontalScroll,
  reducedMotionSnapshot,
  safetyVisible,
  stillnessProbe,
  type Theme,
} from './support/gates';
import {
  E2E_API_URL,
  E2E_PROFILE_NAME,
  E2E_PROFILE_PASSWORD,
  ensureE2EProfile,
} from './support/auth';

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };
const THEMES: Theme[] = ['light', 'dark'];

const NEW_PASSWORD = 'SecurePass123';
const ROTATED_PASSWORD = 'RotatedPass456';

/** /recover lists only profiles that hold a recovery code (the same seed as tailwind4-styles.spec.ts). */
async function ensureRecoverable(request: APIRequestContext): Promise<void> {
  const auth = await ensureE2EProfile(request);
  const response = await request.post(`${E2E_API_URL}/profiles/${auth.profile_id}/recovery-code`, {
    headers: { Authorization: `Bearer ${auth.access_token}` },
    data: { password: E2E_PROFILE_PASSWORD },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}

/** Opens /setup and leaves the create form showing (a profile already on file hides it behind a button). */
async function openCreateForm(page: Page): Promise<void> {
  await page.goto('/setup');
  const createNew = page.getByRole('button', { name: 'Create a new profile' });
  const nameField = page.getByLabel('Profile Name');
  await createNew.or(nameField).waitFor({ timeout: 15000 });
  if (await createNew.isVisible()) await createNew.click();
  await expect(nameField).toBeVisible();
}

/** Creates a profile through the form and waits for the one-time recovery code. */
async function createProfileUi(page: Page): Promise<string> {
  await openCreateForm(page);
  await page.getByLabel('Profile Name').fill(`Playwright UIAuth ${Date.now()}`);
  await page.getByPlaceholder('Create a secure password').fill(NEW_PASSWORD);
  await page.getByRole('button', { name: /create your profile/i }).click();
  const code = page.getByTestId('recovery-code');
  await expect(code).toBeVisible({ timeout: 30000 });
  return (await code.textContent()) ?? '';
}

/** Fills the create form with a throwaway name and a valid password (does not submit). */
async function fillCreateForm(page: Page): Promise<void> {
  await page.getByLabel('Profile Name').fill(`Playwright UIAuth ${Date.now()}`);
  await page.getByPlaceholder('Create a secure password').fill(NEW_PASSWORD);
}

/** Submits the filled create form and waits for the one-time recovery code (30 s, as createProfileUi does). */
async function submitCreateUntilRecoveryCode(page: Page): Promise<void> {
  await page.getByRole('button', { name: /create your profile/i }).click();
  await expect(page.getByTestId('recovery-code')).toBeVisible({ timeout: 30000 });
}

/**
 * Answers POST /profiles/ with a 500 after 700 ms; other requests pass through. A real failure arrives after the
 * key derivation, well outside the 500 ms hadRecentInput window of the layout-shift observer, so the shift of the
 * card that follows it is counted (an instant mock would hide it from measureCls). The stillness probe passes 0: its
 * 800 ms window starts at the click.
 */
async function failProfileCreate(page: Page, delayMs = 700): Promise<void> {
  await page.route('**/profiles/', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    if (delayMs > 0) await new Promise((resolve) => setTimeout(resolve, delayMs));
    return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Server unavailable' }) });
  });
}

/** Opens /setup and fills the unlock card for the E2E profile (does not submit). */
async function fillUnlockForm(page: Page): Promise<void> {
  await page.goto('/setup');
  await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
  await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
  await page.getByLabel('Unlock password').fill(E2E_PROFILE_PASSWORD);
}

/** Submits the unlock card and waits for the real login to land on /inbox. */
async function submitUnlock(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Unlock', exact: true }).click();
  await expect(page).toHaveURL(/\/inbox/, { timeout: 30000 });
  await expect(page.getByRole('heading', { name: 'Document Inbox' })).toBeVisible({ timeout: 30000 });
}

/** Lowest opacity on the name field and its ancestors: below 1 while S1 is still running. -1 if there is no field. */
async function minGroupOpacity(page: Page): Promise<number> {
  return page.evaluate(() => {
    const input = document.querySelector('input[autocomplete="name"]');
    if (!input) return -1;
    let min = 1;
    for (let el: Element | null = input; el && el !== document.body; el = el.parentElement) {
      min = Math.min(min, parseFloat(getComputedStyle(el).opacity));
    }
    return min;
  });
}

/** A profile made through the API with its one-time recovery code, so /recover can rotate it without touching the E2E profile. */
async function createRecoverableProfile(
  request: APIRequestContext
): Promise<{ name: string; code: string }> {
  const name = `UIAuth Recover ${Date.now()}`;
  const response = await request.post(`${E2E_API_URL}/profiles/`, {
    data: { display_name: name, password: NEW_PASSWORD },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const body = (await response.json()) as { recovery_code: string };
  return { name, code: body.recovery_code };
}

/** Fills /recover with a malformed code (answers 400, the page shows its error) and submits. */
async function submitMalformedRecovery(page: Page): Promise<void> {
  await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
  await page.locator('#recover-code').fill('AAAA-BBBB');
  await page.getByLabel('New password').fill(NEW_PASSWORD);
  await page.getByRole('button', { name: /unlock my records/i }).click();
}

/** Waits for the S1 entrance on the create form to finish (opacity 1 and no translate on every group). */
async function settleReveal(page: Page): Promise<void> {
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const input = document.querySelector('input[autocomplete="name"]');
          if (!input) return -1;
          let min = 1;
          for (let el: Element | null = input; el && el !== document.body; el = el.parentElement) {
            min = Math.min(min, parseFloat(getComputedStyle(el).opacity));
            const t = getComputedStyle(el).transform;
            if (t !== 'none' && t !== 'matrix(1, 0, 0, 1, 0, 0)') return -2;
          }
          return min;
        }),
      { timeout: 10_000 }
    )
    .toBeGreaterThanOrEqual(0.99);
}

test.describe('UI-PG-AUTH gate G on /setup and /recover', () => {
  test.beforeEach(async ({ request }) => {
    await ensureRecoverable(request);
  });

  const SCREENS = [
    {
      name: '/setup (unlock card)',
      open: async (page: Page) => {
        await page.goto('/setup');
        await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
      },
    },
    {
      name: '/setup (create form)',
      open: openCreateForm,
    },
    {
      name: '/recover',
      open: async (page: Page) => {
        await page.goto('/recover');
        await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
      },
    },
  ];

  for (const theme of THEMES) {
    for (const screen of SCREENS) {
      test(`G1 axe and G7 console/network guard on ${screen.name} (${theme})`, async ({ page }) => {
        await page.setViewportSize(DESKTOP);
        const guard = consoleAndNetworkGuard(page);
        await screen.open(page);
        await page.waitForLoadState('networkidle');
        if (screen.name.includes('create')) await settleReveal(page);
        const axe = await axeGate(page, { theme });
        expect(
          axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
          `G1 ${screen.name} ${theme}`
        ).toEqual([]);
        guard.assertClean();
      });
    }
  }

  for (const screen of SCREENS) {
    test(`G6 no horizontal scroll on ${screen.name} at 390 and 320`, async ({ page }) => {
      await page.setViewportSize(PHONE);
      await screen.open(page);
      await page.waitForLoadState('networkidle');
      expect((await noHorizontalScroll(page)).ok, `G6 390 ${screen.name}`).toBe(true);
      await page.setViewportSize(SMALL_PHONE);
      expect((await noHorizontalScroll(page)).ok, `G6 320 ${screen.name}`).toBe(true);
    });
  }

  for (const theme of THEMES) {
    test(`G1 axe with the create-form errors showing (${theme})`, async ({ page }) => {
      await page.setViewportSize(DESKTOP);
      await openCreateForm(page);
      await settleReveal(page);
      await page.getByRole('button', { name: /create your profile/i }).click();
      await expect(page.getByText('Name is required')).toBeVisible();
      const axe = await axeGate(page, { theme });
      expect(
        axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
        `G1 create errors ${theme}`
      ).toEqual([]);
    });

    test(`G1 axe with the unlock error showing (${theme})`, async ({ page }) => {
      await page.setViewportSize(DESKTOP);
      await page.goto('/setup');
      await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
      await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
      await page.getByLabel('Unlock password').fill('WrongPass999');
      await page.getByRole('button', { name: 'Unlock', exact: true }).click();
      await expect(page.getByRole('alert')).toHaveText('Incorrect password');
      const axe = await axeGate(page, { theme });
      expect(
        axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
        `G1 unlock error ${theme}`
      ).toEqual([]);
    });

    test(`G1 axe on /recover with its error showing (${theme})`, async ({ page }) => {
      await page.setViewportSize(DESKTOP);
      await page.goto('/recover');
      await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
      await submitMalformedRecovery(page);
      await expect(page.getByRole('alert')).toBeVisible();
      const axe = await axeGate(page, { theme });
      expect(
        axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
        `G1 recover error ${theme}`
      ).toEqual([]);
    });
  }

  test('G2 CLS on a cold /setup load and opening the create form (timing)', async ({ page }) => {
    const cls = await measureCls(page, async () => {
      await page.goto('/setup');
      await page.getByLabel('Profile Name').or(page.getByRole('button', { name: 'Create a new profile' })).waitFor();
      const createNew = page.getByRole('button', { name: 'Create a new profile' });
      if (await createNew.isVisible()) await createNew.click();
    });
    expect(cls, 'G2 /setup').toBeLessThan(0.1);
  });

  test('G3 INP proxy on opening the create form, CPU x4 (timing)', async ({ page, request }) => {
    // A profile on file puts the create form behind a button; seed one so the click is always measured.
    await ensureE2EProfile(request);
    await page.goto('/setup');
    const createNew = page.getByRole('button', { name: 'Create a new profile' });
    await expect(createNew).toBeVisible({ timeout: 15000 });
    const inp = await maxEventDuration(page, () => createNew.click(), { cpuRate: 4 });
    expect(inp, 'G3 /setup').toBeLessThan(200);
  });

  test('G2 CLS on a cold /recover load, filling the form and showing its error (timing)', async ({ page }) => {
    const cls = await measureCls(page, async () => {
      await page.goto('/recover');
      await page.locator('#recover-code').waitFor({ timeout: 15000 });
      await submitMalformedRecovery(page);
      await page.getByRole('alert').waitFor();
    });
    expect(cls, 'G2 /recover').toBeLessThan(0.1);
  });

  test('G2 CLS on submitting the empty create form and on a failed create (timing)', async ({ page }) => {
    await failProfileCreate(page);
    const cls = await measureCls(page, async () => {
      await openCreateForm(page);
      await page.getByRole('button', { name: /create your profile/i }).click();
      await page.getByText('Name is required').waitFor();
      await page.getByLabel('Profile Name').fill(`Playwright UIAuth ${Date.now()}`);
      await page.getByPlaceholder('Create a secure password').fill(NEW_PASSWORD);
      await page.getByRole('button', { name: /create your profile/i }).click();
      await page.getByText('Failed to create profile').waitFor();
    });
    expect(cls, 'G2 /setup errors').toBeLessThan(0.1);
  });

  test('G3 INP proxy on /recover (select, type, submit), CPU x4 (timing)', async ({ page }) => {
    await page.goto('/recover');
    await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
    const inp = await maxEventDuration(
      page,
      async () => {
        await submitMalformedRecovery(page);
        await page.getByRole('alert').waitFor();
      },
      { cpuRate: 4 }
    );
    expect(inp, 'G3 /recover').toBeLessThan(200);
  });

  test('G3 INP proxy on submitting the empty create form, CPU x4 (timing)', async ({ page }) => {
    await openCreateForm(page);
    await settleReveal(page);
    const inp = await maxEventDuration(
      page,
      async () => {
        await page.getByRole('button', { name: /create your profile/i }).click();
        await page.getByText('Name is required').waitFor();
      },
      { cpuRate: 4 }
    );
    expect(inp, 'G3 /setup submit').toBeLessThan(200);
  });

  test('G5 reduced motion: no transform 50 ms after showing the /recover error (timing)', async ({ page }) => {
    await page.goto('/recover');
    await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
    await page.locator('#recover-code').fill('AAAA-BBBB');
    await page.getByLabel('New password').fill(NEW_PASSWORD);
    const offenders = await reducedMotionSnapshot(page, async () => {
      await page.getByRole('button', { name: /unlock my records/i }).click();
      await page.getByRole('alert').waitFor();
    });
    expect(offenders, 'G5 /recover').toEqual([]);
  });

  test('G5 reduced motion: no transform 50 ms after submitting the empty create form (timing)', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openCreateForm(page);
    const offenders = await reducedMotionSnapshot(page, async () => {
      await page.getByRole('button', { name: /create your profile/i }).click();
    });
    expect(offenders, 'G5 /setup submit').toEqual([]);
  });

  test('G5 reduced motion: no transform 50 ms after opening the create form (timing)', async ({ page }) => {
    await page.goto('/setup');
    const createNew = page.getByRole('button', { name: 'Create a new profile' });
    await expect(createNew.or(page.getByLabel('Profile Name'))).toBeVisible({ timeout: 15000 });
    const offenders = await reducedMotionSnapshot(page, async () => {
      if (await createNew.isVisible()) await createNew.click();
    });
    expect(offenders, 'G5 /setup').toEqual([]);
  });

  // ---- Unlock submit (the Lift): real backend, real login ----

  test('G2 CLS on opening /setup and submitting the unlock form through the Lift (timing)', async ({ page, request }) => {
    await ensureE2EProfile(request);
    const cls = await measureCls(page, async () => {
      await fillUnlockForm(page);
      await submitUnlock(page);
    });
    expect(cls, 'G2 unlock submit').toBeLessThan(0.1);
  });

  test('G3 INP proxy on submitting the unlock form, CPU x4 (timing)', async ({ page, request }) => {
    await ensureE2EProfile(request);
    await fillUnlockForm(page);
    const inp = await maxEventDuration(page, () => submitUnlock(page), { cpuRate: 4 });
    expect(inp, 'G3 unlock submit').toBeLessThan(200);
  });

  test('G5 reduced motion: no transform 50 ms after the unlock submit lands on /inbox (timing)', async ({
    page,
    request,
  }) => {
    await ensureE2EProfile(request);
    // Reduced motion before the page loads, so the Lift reads it at mount. Its contract is an opacity fade only
    // (HC-UIAUTH-003), so no element may carry a transform while it runs.
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await fillUnlockForm(page);
    const offenders = await reducedMotionSnapshot(page, () => submitUnlock(page));
    expect(offenders, 'G5 unlock submit').toEqual([]);
  });

  // ---- Create success, up to the one-time recovery code ----

  test('G2 CLS on creating a profile up to the recovery-code step (timing)', async ({ page }) => {
    const cls = await measureCls(page, async () => {
      await openCreateForm(page);
      await fillCreateForm(page);
      await submitCreateUntilRecoveryCode(page);
    });
    expect(cls, 'G2 create success').toBeLessThan(0.1);
  });

  test('G3 INP proxy on submitting the create form to the recovery-code step, CPU x4 (timing)', async ({ page }) => {
    await openCreateForm(page);
    await settleReveal(page);
    await fillCreateForm(page);
    const inp = await maxEventDuration(page, () => submitCreateUntilRecoveryCode(page), { cpuRate: 4 });
    expect(inp, 'G3 create success').toBeLessThan(200);
  });

  test('G5 reduced motion: no transform 50 ms after the recovery-code step shows (timing)', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openCreateForm(page);
    await fillCreateForm(page);
    const offenders = await reducedMotionSnapshot(page, () => submitCreateUntilRecoveryCode(page));
    expect(offenders, 'G5 create success').toEqual([]);
  });

  // ---- Failed create (mocked POST /profiles/ 500; G2 for it is above) ----

  test('G3 INP proxy on a failed create, CPU x4 (timing)', async ({ page }) => {
    await failProfileCreate(page);
    await openCreateForm(page);
    await settleReveal(page);
    await fillCreateForm(page);
    const inp = await maxEventDuration(
      page,
      async () => {
        await page.getByRole('button', { name: /create your profile/i }).click();
        await page.getByText('Failed to create profile').waitFor();
      },
      { cpuRate: 4 }
    );
    expect(inp, 'G3 failed create').toBeLessThan(200);
  });

  test('G5 reduced motion: no transform 50 ms after a failed create shows its error (timing)', async ({ page }) => {
    await failProfileCreate(page);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openCreateForm(page);
    await fillCreateForm(page);
    const offenders = await reducedMotionSnapshot(page, async () => {
      await page.getByRole('button', { name: /create your profile/i }).click();
      await page.getByText('Failed to create profile').waitFor();
    });
    expect(offenders, 'G5 failed create').toEqual([]);
  });

  // ---- G5 screenshots: one per touched screen, under reduced motion ----

  test('G5 reduced motion screenshots: /setup unlock, /setup create, recovery-code step, /recover (timing)', async ({
    page,
  }) => {
    await page.setViewportSize(DESKTOP);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    const shoot = async (name: string) => {
      const path = test.info().outputPath(`g5-${name}.png`);
      await page.screenshot({ path });
      await test.info().attach(`g5-${name}`, { path, contentType: 'image/png' });
    };

    await page.goto('/setup');
    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
    await shoot('setup-unlock');

    await openCreateForm(page);
    await settleReveal(page);
    await shoot('setup-create');

    await fillCreateForm(page);
    await submitCreateUntilRecoveryCode(page);
    await shoot('recovery-code');

    await page.goto('/recover');
    await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
    await shoot('recover');
  });
});

test.describe('HC-UIAUTH-003: the Lift on unlock', () => {
  /** Watches the Lift ghost and the shell from before the click; the log lands on window.__lift. */
  async function watchLift(page: Page): Promise<void> {
    await page.evaluate((password) => {
      type Log = {
        ghostAt?: number;
        shellAt?: number;
        duration?: number;
        keyframes?: Record<string, unknown>[];
        panelGap?: boolean;
        ghostContainsRailCentre?: boolean;
        railCoveredBy?: string | null;
        ghostHasControl?: boolean;
        ghostHtmlHasPassword?: boolean;
        ariaHidden?: string | null;
        pointerEvents?: string;
      };
      const log: Log = {};
      (window as unknown as { __lift: Log }).__lift = log;
      const shellSelector = '[data-safety-rail], nav[aria-label="Main navigation"]';
      const observer = new MutationObserver(() => {
        const now = performance.now();
        const ghost = document.querySelector('[data-lift-ghost]') as HTMLElement | null;
        // The card must not blank out between the cache clear and the route commit: while the page is still
        // there and no ghost has taken over, the unlock heading is on screen.
        if (!ghost && log.ghostAt === undefined && document.querySelector('[data-setup-page]')) {
          const heading = Array.from(document.querySelectorAll('[data-setup-page] h2')).some(
            (h) => h.textContent === 'Unlock your profile'
          );
          // The create card (here: the button, a profile is on file) and the footer stay too, or the page would
          // shrink under the ghost and a scroll clamp could move the panel away from the rect the ghost copied.
          const createButton = Array.from(document.querySelectorAll('[data-setup-page] button')).some(
            (b) => b.textContent === 'Create a new profile'
          );
          const footer = (document.querySelector('[data-setup-page]')?.textContent ?? '').includes(
            'Your data is stored locally and never uploaded.'
          );
          if (!heading || !createButton || !footer) log.panelGap = true;
        }
        if (ghost && log.ghostAt === undefined) {
          log.ghostAt = now;
          const animation = ghost.getAnimations()[0];
          const timing = animation?.effect?.getTiming();
          log.duration = typeof timing?.duration === 'number' ? timing.duration : undefined;
          log.keyframes = (animation?.effect as KeyframeEffect | undefined)?.getKeyframes() as Record<string, unknown>[];
          log.ghostHasControl = !!ghost.querySelector('input, select, textarea, button');
          log.ghostHtmlHasPassword = ghost.outerHTML.includes(password);
          log.ariaHidden = ghost.getAttribute('aria-hidden');
          log.pointerEvents = ghost.style.pointerEvents;
        }
        if (log.shellAt === undefined && document.querySelector(shellSelector)) log.shellAt = now;
        // G9 at first paint of the shell: what is on top at the centre of the Safety Rail. elementFromPoint skips
        // pointer-events:none, so the ghost is made hittable for this one synchronous call, then put back.
        const rail = document.querySelector('[data-safety-rail]');
        if (ghost && rail && log.railCoveredBy === undefined) {
          const box = rail.getBoundingClientRect();
          // The probe means something only where the ghost is: record whether it sits over the rail's centre.
          const ghostBox = ghost.getBoundingClientRect();
          const cx = box.left + box.width / 2;
          const cy = box.top + box.height / 2;
          log.ghostContainsRailCentre =
            cx >= ghostBox.left && cx <= ghostBox.right && cy >= ghostBox.top && cy <= ghostBox.bottom;
          const previous = ghost.style.pointerEvents;
          ghost.style.pointerEvents = 'auto';
          const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
          ghost.style.pointerEvents = previous;
          log.railCoveredBy = top && rail.contains(top) ? null : (top?.tagName.toLowerCase() ?? 'nothing');
        }
      });
      observer.observe(document, { childList: true, subtree: true });
    }, E2E_PROFILE_PASSWORD);
  }

  async function unlock(page: Page, viewport?: { width: number; height: number }): Promise<void> {
    if (viewport) await page.setViewportSize(viewport);
    await page.goto('/setup');
    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
    await page.getByLabel('Unlock password').fill(E2E_PROFILE_PASSWORD);
    await watchLift(page);
    await page.getByRole('button', { name: 'Unlock', exact: true }).click();
    await expect(page).toHaveURL(/\/inbox/, { timeout: 15000 });
    await expect(page.getByRole('heading', { name: 'Document Inbox' })).toBeVisible();
  }

  async function documentHoldsPassword(page: Page): Promise<string[]> {
    return page.evaluate((needle) => {
      const holders: string[] = [];
      for (const el of Array.from(document.querySelectorAll('*'))) {
        for (const attr of Array.from(el.attributes)) {
          if (attr.value.includes(needle)) holders.push(`${el.tagName.toLowerCase()}[${attr.name}]`);
        }
        const value = (el as HTMLInputElement).value;
        if (typeof value === 'string' && value.includes(needle)) holders.push(`${el.tagName.toLowerCase()}.value`);
      }
      return holders;
    }, E2E_PROFILE_PASSWORD);
  }

  test('unlock lands on /inbox, the Lift ghost holds no form control or password, and it removes itself', async ({
    page,
    request,
  }) => {
    await ensureE2EProfile(request);
    // G7 over the whole unlock, the ghost and the landing included, not only the page open.
    const guard = consoleAndNetworkGuard(page);
    await unlock(page);

    const lift = await page.evaluate(() => (window as unknown as { __lift: Record<string, unknown> }).__lift);
    expect(lift.ghostAt, 'a Lift ghost appeared').toBeDefined();
    expect(lift.ghostHasControl).toBe(false);
    expect(lift.ghostHtmlHasPassword).toBe(false);
    expect(lift.ariaHidden).toBe('true');
    expect(lift.pointerEvents).toBe('none');
    expect(lift.panelGap, 'the unlock card stayed on screen until the route committed').not.toBe(true);

    // It cleans up after itself, and no attribute or value in the document holds the password.
    await expect(page.locator('[data-lift-ghost]')).toHaveCount(0, { timeout: 5000 });
    expect(await documentHoldsPassword(page)).toEqual([]);
    guard.assertClean();
  });

  test('at 390x844 the Lift ghost does not cover the Safety Rail, and the rail is visible once it ends (G9)', async ({
    page,
    request,
  }) => {
    await ensureE2EProfile(request);
    await unlock(page, PHONE);
    const lift = await page.evaluate(
      () =>
        (window as unknown as { __lift: { railCoveredBy?: string | null; ghostContainsRailCentre?: boolean } }).__lift
    );
    expect(lift.railCoveredBy, 'the rail was probed while the ghost was up').not.toBeUndefined();
    // Without this a ghost placed elsewhere would pass too: the probe only counts where the ghost really is.
    expect(lift.ghostContainsRailCentre, 'the ghost overlaps the rail centre, so the probe tests z-order').toBe(true);
    expect(lift.railCoveredBy, 'what covered the rail').toBeNull();
    await expect(page.locator('[data-lift-ghost]')).toHaveCount(0, { timeout: 5000 });
    const rail = await safetyVisible(page);
    expect(rail.found).toBe(true);
    expect(rail.inViewport).toBe(true);
    expect(rail.effectiveOpacity).toBe(1);
  });

  test('the shell is committed in the same frame as the Lift (DOM commit stamps), which fades and lifts 8 px in 240 ms (timing)', async ({
    page,
    request,
  }) => {
    await ensureE2EProfile(request);
    await unlock(page);

    const lift = await page.evaluate(
      () =>
        (window as unknown as { __lift: { ghostAt?: number; shellAt?: number; duration?: number; keyframes?: Record<string, unknown>[] } })
          .__lift
    );
    expect(lift.duration).toBe(240);
    const last = lift.keyframes![lift.keyframes!.length - 1];
    expect(last.opacity).toBe('0');
    expect(String(last.transform)).toContain('translateY(-8px)');
    expect(lift.shellAt, 'the shell mounted').toBeDefined();
    // One frame at 60 Hz. These are MutationObserver stamps: they read commits, not paint.
    expect(Math.abs(lift.shellAt! - lift.ghostAt!), 'shell within one frame of the Lift').toBeLessThanOrEqual(17);
  });

  test.describe('reduced motion', () => {
    test.use({ contextOptions: { reducedMotion: 'reduce' } });

    test('the Lift is an opacity fade of 150 ms, with no transform (timing)', async ({ page, request }) => {
      await ensureE2EProfile(request);
      await unlock(page);

      const lift = await page.evaluate(
        () =>
          (window as unknown as { __lift: { duration?: number; keyframes?: Record<string, unknown>[] } }).__lift
      );
      expect(lift.duration).toBe(150);
      for (const frame of lift.keyframes!) {
        expect(frame.transform === undefined || frame.transform === 'none').toBe(true);
      }
      expect(lift.keyframes![lift.keyframes!.length - 1].opacity).toBe('0');
    });
  });

  test('a wrong password shows "Incorrect password" with no Lift and stays on /setup', async ({ page, request }) => {
    await ensureE2EProfile(request);
    await page.goto('/setup');
    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
    await page.getByLabel('Unlock password').fill('WrongPass999');
    await page.getByRole('button', { name: 'Unlock', exact: true }).click();
    await expect(page.getByRole('alert')).toHaveText('Incorrect password');
    await expect(page.locator('[data-lift-ghost]')).toHaveCount(0);
    await expect(page).toHaveURL(/\/setup/);
  });
});

test.describe('HC-UIAUTH-004: the recovery code in 4-character groups', () => {
  test('at 320x640 no group splits across lines and nothing overflows', async ({ page }) => {
    await page.setViewportSize(SMALL_PHONE);
    // G7 over the whole create, up to and including the recovery-code step.
    const guard = consoleAndNetworkGuard(page);
    const code = await createProfileUi(page);
    expect(code).toMatch(/^([A-Z0-9]{4}-){7}[A-Z0-9]{4}$/);

    const report = await codeGeometry(page);
    expect(report.text).toBe(code);
    expect(report.groupTexts).toEqual(code.split('-'));
    expect(report.lineCounts.every((n) => n === 1), `group line counts ${report.lineCounts}`).toBe(true);
    expect(report.overflowing, 'groups outside the code block').toBe(0);
    expect((await noHorizontalScroll(page)).ok, 'G6 320 recovery step').toBe(true);
    // The code does wrap at this width, and only between groups.
    expect(report.lineTops).toBeGreaterThan(1);
    guard.assertClean();
  });

  test('copy writes the code unchanged, and the step passes axe in both themes', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.setViewportSize(DESKTOP);
    const code = await createProfileUi(page);

    await page.getByRole('button', { name: 'Copy' }).click();
    await expect(page.getByRole('button', { name: 'Copied' })).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(code);

    for (const theme of THEMES) {
      const axe = await axeGate(page, { theme });
      expect(
        axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
        `G1 recovery step ${theme}`
      ).toEqual([]);
    }
  });

  test('/recover rotated-code step: groups intact and no horizontal scroll at 390 and 320 (G6)', async ({
    page,
    request,
  }) => {
    const profile = await createRecoverableProfile(request);
    await page.setViewportSize(PHONE);
    const code = await rotateOnRecoverPage(page, profile);
    expect(code).toMatch(/^([A-Z0-9]{4}-){7}[A-Z0-9]{4}$/);
    expect((await noHorizontalScroll(page)).ok, 'G6 390 /recover rotated').toBe(true);
    await page.setViewportSize(SMALL_PHONE);
    expect((await noHorizontalScroll(page)).ok, 'G6 320 /recover rotated').toBe(true);
    const report = await codeGeometry(page);
    expect(report.text).toBe(code);
    expect(report.lineCounts.every((n) => n === 1), `group line counts ${report.lineCounts}`).toBe(true);
    expect(report.overflowing, 'groups outside the code block').toBe(0);
  });

  test('/recover rotated-code step passes axe in both themes (G1)', async ({ page, request }) => {
    const profile = await createRecoverableProfile(request);
    await page.setViewportSize(DESKTOP);
    await rotateOnRecoverPage(page, profile);
    for (const theme of THEMES) {
      const axe = await axeGate(page, { theme });
      expect(
        axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
        `G1 /recover rotated step ${theme}`
      ).toEqual([]);
    }
  });
});

/** Geometry of the recovery-code block: its text, each group's text and line count, overflow, distinct line tops. */
async function codeGeometry(page: Page) {
  return page.getByTestId('recovery-code').evaluate((block) => {
    const blockRect = block.getBoundingClientRect();
    const groups = Array.from(block.querySelectorAll('[data-code-group]'));
    return {
      text: block.textContent,
      groupTexts: groups.map((g) => g.textContent),
      lineCounts: groups.map((g) => {
        const range = document.createRange();
        range.selectNodeContents(g);
        // Distinct line tops among the text's client rects: more than one means the group wrapped.
        return new Set(Array.from(range.getClientRects()).map((r) => Math.round(r.top))).size;
      }),
      overflowing: groups
        .map((g) => g.getBoundingClientRect())
        .filter((r) => r.left < blockRect.left - 0.5 || r.right > blockRect.right + 0.5).length,
      lineTops: Array.from(new Set(groups.map((g) => Math.round(g.getBoundingClientRect().top)))).length,
    };
  });
}

/** Rotates a profile's recovery code on /recover and returns the new code once it shows. */
async function rotateOnRecoverPage(page: Page, profile: { name: string; code: string }): Promise<string> {
  await page.goto('/recover');
  await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
  await page.getByLabel('Profile', { exact: true }).selectOption({ label: profile.name });
  await page.locator('#recover-code').fill(profile.code);
  await page.getByLabel('New password').fill(ROTATED_PASSWORD);
  await page.getByRole('button', { name: /unlock my records/i }).click();
  const code = page.getByTestId('recovery-code');
  await expect(code).toBeVisible({ timeout: 30000 });
  return (await code.textContent()) ?? '';
}

test.describe('HC-UIAUTH-001: a fixed field error clears (functional)', () => {
  test('fixing a field clears its error, and only that one (real browser)', async ({ page }) => {
    await openCreateForm(page);
    await page.getByRole('button', { name: /create your profile/i }).click();
    await expect(page.getByText('Name is required')).toBeVisible();
    await page.getByLabel('Profile Name').fill('A');
    await expect(page.getByText('Name is required')).toHaveCount(0);
    await expect(page.getByText('Password is required')).toBeVisible();
  });
});

test.describe('SEC-RECOV-001: leaving while the profile is being created (functional)', () => {
  test('while POST /profiles/ is pending the recovery link is hidden, the fields are locked and a revealed password is masked; the code shows after release', async ({
    page,
  }) => {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route('**/profiles/', async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      await held;
      return route.fallback();
    });
    try {
      await openCreateForm(page);
      await fillCreateForm(page);
      await page.getByRole('button', { name: 'Show password' }).click();
      await expect(page.getByPlaceholder('Create a secure password')).toHaveAttribute('type', 'text');
      const link = page.locator('a[href="/recover"]');
      await expect(link).toBeVisible();

      await page.getByRole('button', { name: /create your profile/i }).click();
      await expect(page.getByRole('button', { name: /creating your profile/i })).toBeVisible();

      // visibility:hidden: out of the tab order and out of the pointer's reach, and the card keeps its height.
      await expect(link).toBeHidden();
      await expect(page.getByLabel('Profile Name')).toBeDisabled();
      await expect(page.getByPlaceholder('Create a secure password')).toBeDisabled();
      await expect(page.getByPlaceholder('Create a secure password')).toHaveAttribute('type', 'password');
    } finally {
      release();
    }
    await expect(page.getByTestId('recovery-code')).toBeVisible({ timeout: 30000 });
  });
});

test.describe('HC-UIAUTH-005: stillness (timing)', () => {
  test('submitting during the S1 entrance: every field error passes from its first render (timing)', async ({
    page,
  }) => {
    await page.setViewportSize(DESKTOP);
    await page.goto('/setup');
    const createNew = page.getByRole('button', { name: 'Create a new profile' });
    await createNew.or(page.getByLabel('Profile Name')).waitFor({ timeout: 15000 });
    // Open the form and submit at once: the S1 groups are still rising.
    if (await createNew.isVisible()) await createNew.click();
    await stillnessProbe(page, {
      trigger: async () => {
        // The point of this test: S1 is running at the click. On a box too slow to get here in time this fails,
        // instead of quietly becoming the "after" test.
        expect(await minGroupOpacity(page), 'S1 is still running when the form is submitted').toBeLessThan(1);
        await page.getByRole('button', { name: /create your profile/i }).click();
      },
      expected: ['p[role="alert"][data-t0]'],
    });
    await expect(page.getByText('Name is required')).toBeVisible();
    await expect(page.getByText('Password is required')).toBeVisible();
  });

  test('submitting after the S1 entrance: every field error passes from its first render (timing)', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openCreateForm(page);
    await settleReveal(page);
    await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: /create your profile/i }).click(),
      expected: ['p[role="alert"][data-t0]'],
    });
  });

  test('the recovery-code step passes with the code and its warning expected (timing)', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await openCreateForm(page);
    await settleReveal(page);
    await page.getByLabel('Profile Name').fill(`Playwright UIAuth ${Date.now()}`);
    await page.getByPlaceholder('Create a secure password').fill(NEW_PASSWORD);
    await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: /create your profile/i }).click(),
      expected: ['[data-testid="recovery-code"][data-t0]', 'p[data-t0]'],
      lazyRoute: true,
    });
    await expect(page.getByTestId('recovery-code')).toBeVisible();
  });

  test('the create-failure error passes from its first render (timing)', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await failProfileCreate(page, 0);
    await openCreateForm(page);
    await settleReveal(page);
    await page.getByLabel('Profile Name').fill(`Playwright UIAuth ${Date.now()}`);
    await page.getByPlaceholder('Create a secure password').fill(NEW_PASSWORD);
    await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: /create your profile/i }).click(),
      expected: ['[role="alert"][data-t0]'],
    });
    await expect(page.getByRole('alert')).toContainText('Failed to create profile');
  });

  test('the /recover rotated-code step passes with the code and its warning expected (timing)', async ({
    page,
    request,
  }) => {
    const profile = await createRecoverableProfile(request);
    await page.setViewportSize(DESKTOP);
    await page.goto('/recover');
    await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: profile.name });
    await page.locator('#recover-code').fill(profile.code);
    await page.getByLabel('New password').fill(ROTATED_PASSWORD);
    await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: /unlock my records/i }).click(),
      expected: ['[data-testid="recovery-code"][data-t0]', 'p[data-t0]'],
      lazyRoute: true,
    });
    await expect(page.getByTestId('recovery-code')).toBeVisible();
  });

  test('the unlock error passes from its first render (timing)', async ({ page, request }) => {
    await ensureE2EProfile(request);
    await page.setViewportSize(DESKTOP);
    await page.goto('/setup');
    await expect(page.getByText('Unlock your profile')).toBeVisible({ timeout: 15000 });
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
    await page.getByLabel('Unlock password').fill('WrongPass999');
    await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: 'Unlock', exact: true }).click(),
      expected: ['p[role="alert"][data-t0]'],
      lazyRoute: true,
    });
    await expect(page.getByRole('alert')).toHaveText('Incorrect password');
  });

  test('the /recover error passes from its first render (timing)', async ({ page, request }) => {
    await ensureRecoverable(request);
    await page.setViewportSize(DESKTOP);
    await page.goto('/recover');
    await expect(page.locator('#recover-code')).toBeVisible({ timeout: 15000 });
    await page.getByLabel('Profile', { exact: true }).selectOption({ label: E2E_PROFILE_NAME });
    // A malformed code answers 400 "not valid". A well-formed wrong code answers 401, which services/api.ts treats
    // as an expired session and answers with a redirect to /setup (reported to L0; not this row's file).
    await page.locator('#recover-code').fill('AAAA-BBBB');
    await page.getByLabel('New password').fill(NEW_PASSWORD);
    await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: /unlock my records/i }).click(),
      expected: ['p[role="alert"][data-t0]'],
      lazyRoute: true,
    });
    await expect(page.getByRole('alert')).toBeVisible();
  });
});
