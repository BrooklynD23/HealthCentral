/**
 * UI-PG-AUTH e2e (plan section 7.8), real backend: Gate G on /setup and /recover, the Lift on unlock
 * (HC-UIAUTH-003), the recovery code in 4-character groups (HC-UIAUTH-004) and stillness of every error and of
 * the recovery-code step (HC-UIAUTH-005).
 *
 * Presentation only (L0 AUTH GUARD): nothing here changes what is sent or kept. The backend and the E2E profile
 * come from the normal harness (playwright.config.ts starts both).
 *
 * Timing gates (G2, G3, G5, G10, and the Lift timing of HC-UIAUTH-003) are measurements: run them on a quiet box
 * only. Their titles end in "(timing)".
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import {
  axeGate,
  consoleAndNetworkGuard,
  maxEventDuration,
  measureCls,
  noHorizontalScroll,
  reducedMotionSnapshot,
  setTheme,
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

  test('G2 CLS on a cold /setup load and opening the create form (timing)', async ({ page }) => {
    const cls = await measureCls(page, async () => {
      await page.goto('/setup');
      await page.getByLabel('Profile Name').or(page.getByRole('button', { name: 'Create a new profile' })).waitFor();
      const createNew = page.getByRole('button', { name: 'Create a new profile' });
      if (await createNew.isVisible()) await createNew.click();
    });
    expect(cls, 'G2 /setup').toBeLessThan(0.1);
  });

  test('G3 INP proxy on opening the create form, CPU x4 (timing)', async ({ page }) => {
    await page.goto('/setup');
    const createNew = page.getByRole('button', { name: 'Create a new profile' });
    await expect(createNew.or(page.getByLabel('Profile Name'))).toBeVisible({ timeout: 15000 });
    test.skip(!(await createNew.isVisible()), 'no profile on file: the form is already open');
    const inp = await maxEventDuration(page, () => createNew.click(), { cpuRate: 4 });
    expect(inp, 'G3 /setup').toBeLessThan(200);
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
      });
      observer.observe(document, { childList: true, subtree: true });
    }, E2E_PROFILE_PASSWORD);
  }

  async function unlock(page: Page): Promise<void> {
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
    await unlock(page);

    const lift = await page.evaluate(() => (window as unknown as { __lift: Record<string, unknown> }).__lift);
    expect(lift.ghostAt, 'a Lift ghost appeared').toBeDefined();
    expect(lift.ghostHasControl).toBe(false);
    expect(lift.ghostHtmlHasPassword).toBe(false);
    expect(lift.ariaHidden).toBe('true');
    expect(lift.pointerEvents).toBe('none');

    // It cleans up after itself, and no attribute or value in the document holds the password.
    await expect(page.locator('[data-lift-ghost]')).toHaveCount(0, { timeout: 5000 });
    expect(await documentHoldsPassword(page)).toEqual([]);
  });

  test('the shell is visible within one frame of the Lift, which fades and lifts 8 px in 240 ms (timing)', async ({
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
    expect(Math.abs(lift.shellAt! - lift.ghostAt!), 'shell within one frame of the Lift').toBeLessThanOrEqual(34);
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
    const code = await createProfileUi(page);
    expect(code).toMatch(/^([A-Z0-9]{4}-){7}[A-Z0-9]{4}$/);

    const report = await page.getByTestId('recovery-code').evaluate((block) => {
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
    expect(report.text).toBe(code);
    expect(report.groupTexts).toEqual(code.split('-'));
    expect(report.lineCounts.every((n) => n === 1), `group line counts ${report.lineCounts}`).toBe(true);
    expect(report.overflowing, 'groups outside the code block').toBe(0);
    expect((await noHorizontalScroll(page)).ok, 'G6 320 recovery step').toBe(true);
    // The code does wrap at this width, and only between groups.
    expect(report.lineTops).toBeGreaterThan(1);
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
      trigger: () => page.getByRole('button', { name: /create your profile/i }).click(),
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

  test('fixing a field clears its error, and only that one (real browser)', async ({ page }) => {
    await openCreateForm(page);
    await page.getByRole('button', { name: /create your profile/i }).click();
    await expect(page.getByText('Name is required')).toBeVisible();
    await page.getByLabel('Profile Name').fill('A');
    await expect(page.getByText('Name is required')).toHaveCount(0);
    await expect(page.getByText('Password is required')).toBeVisible();
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
