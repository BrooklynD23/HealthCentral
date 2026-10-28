/**
 * UI-PG-MEDS e2e (plan section 7.7): Gate G1-G10 on the medication routes in light and dark, the dose sheet
 * (HC-UIMED-002) and the Reminders tab (HC-UIMED-004), end to end.
 *
 * The medication and notification calls are answered here (page.route, registered after installMockApi so it
 * runs first); every other /api/v1 call goes to the shared shell fixtures. Run without the backend (recipe 2 in
 * e2e/README.md):
 *   PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1 npx playwright test e2e/ui-meds.spec.ts --project=chromium
 *
 * The stillness probes (G10 and the dialog's still check) are timing measurements. Run them on a quiet box only.
 */

import { expect, test, type Page, type Route } from '@playwright/test';
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
import { installMockApi, seedMockSession } from './support/mockApi';

const MED_ID = 'med-fixture-1';
const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };

const medication = {
  id: MED_ID,
  profile_id: '8d2f4a10-6c1e-4b7a-9f00-0000000e2e03',
  name: 'Metformin',
  generic_name: 'metformin',
  dosage_amount: 500,
  dosage_unit: 'mg',
  dosage_form: 'tablet',
  frequency: 'twice_daily',
  instructions: 'Take with food.',
  is_active: true,
  reminder_enabled: true,
  started_at: '2026-01-01T00:00:00',
  ended_at: null,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-02-01T00:00:00',
  schedules: [
    {
      id: 'sched-1',
      medication_id: MED_ID,
      schedule_label: 'morning',
      target_time: '08:00',
      reminder_offset_minutes: 15,
      is_active: true,
      adaptive_window_start: null,
      adaptive_window_end: null,
      created_at: '2026-01-01T00:00:00',
      updated_at: '2026-01-01T00:00:00',
    },
  ],
};

const stats = {
  medication_id: MED_ID,
  current_streak_days: 4,
  longest_streak_days: 9,
  last_7_days_adherence: 0.86,
  last_30_days_adherence: 0.71,
  total_doses_taken: 18,
  total_doses_skipped: 2,
  total_doses_expected: 22,
};

const doses = [
  {
    id: 'dose-1',
    medication_id: MED_ID,
    schedule_id: 'sched-1',
    taken_at: '2026-04-10T08:02:00',
    was_skipped: false,
    skip_reason: null,
    log_method: 'manual',
    notes: null,
    variance_minutes: 2,
    created_at: '2026-04-10T08:02:00',
  },
];

const notificationSettings = {
  medication_id: MED_ID,
  enabled: true,
  quiet_hours_start: '22:00',
  quiet_hours_end: '07:00',
  max_reminders_per_dose: 3,
  initial_offset_minutes: 0,
  nudge_delay_minutes: 15,
  alert_delay_minutes: 30,
  weekend_enabled: true,
  celebration_enabled: true,
};

const notificationHistory = {
  total: 1,
  reminders: [
    {
      id: 'rem-1',
      medication_id: MED_ID,
      medication_name: 'Metformin',
      reminder_type: 'nudge',
      delivery_method: 'desktop',
      sent_at: '2026-04-10T08:15:00',
      was_interacted: true,
      interaction_type: 'taken',
    },
  ],
  stats: { sent_last_7_days: 3, sent_last_30_days: 12, interaction_rate_7d: 0.67, by_type: {} },
};

/** Medication and notification answers. Anything else falls through to installMockApi's shell fixtures. */
async function mockMedicationApi(page: Page): Promise<void> {
  await page.route(/\/api\/v1\/(medications|notifications)(\/|\?|$)/, async (route: Route, request) => {
    const path = new URL(request.url()).pathname.replace(/^.*\/api\/v1/, '').replace(/\/+$/, '') || '/';
    const json = (body: unknown) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    if (request.method() === 'GET') {
      if (path === '/medications') return json([medication]);
      if (path === `/medications/${MED_ID}`) return json(medication);
      if (path === `/medications/${MED_ID}/stats`) return json(stats);
      if (path === `/medications/${MED_ID}/doses`) return json(doses);
      if (path === `/medications/${MED_ID}/schedules`) return json(medication.schedules);
      if (path === `/medications/${MED_ID}/correlations`) {
        return json({ medication_id: MED_ID, observations: [], excluded_undated_count: 0 });
      }
      if (path === `/notifications/settings/${MED_ID}`) return json(notificationSettings);
      if (path === '/notifications/history') return json(notificationHistory);
    }
    return route.fallback();
  });
}

/** Waits until the route container has finished its entrance fade (the shell's settle, copied). */
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

const nav = (page: Page, name: string) =>
  page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name, exact: true });

/** Opens the dose sheet from the first Log button, then closes it with Escape. */
async function openAndCloseDoseSheet(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Log', exact: true }).first().click();
  await expect(page.getByRole('dialog', { name: 'Log Dose' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog', { name: 'Log Dose' })).toHaveCount(0);
}

interface GateRoute {
  name: string;
  path: string;
  /** The page is up when this is visible. */
  ready: (page: Page) => Promise<void>;
  /** The gate's interaction after load (G3, G5). */
  interact: (page: Page) => Promise<void>;
  /** G10: the page the probe starts from, and the trigger that enters this route. */
  from: string;
  trigger: (page: Page) => Promise<void>;
  kind: 'navigation' | 'interaction';
  lazyRoute: boolean;
  /** G10: each selector must match a [data-t0] node (plan §2.7). */
  expected: string[];
}

const REMINDERS_READY = (page: Page) =>
  expect(page.getByRole('tab', { name: 'Reminders' })).toHaveAttribute('aria-selected', 'true');

const GATE_ROUTES: GateRoute[] = [
  {
    name: 'medications',
    path: '/medications',
    ready: async (page) => expect(page.getByRole('heading', { name: 'Medication Coach' })).toBeVisible(),
    interact: openAndCloseDoseSheet,
    from: '/settings',
    trigger: (page) => nav(page, 'Medications').click(),
    kind: 'navigation',
    lazyRoute: true,
    expected: [`a[href="/medications/${MED_ID}"] [data-t0]`],
  },
  {
    name: 'medication-detail',
    path: `/medications/${MED_ID}`,
    ready: async (page) => expect(page.getByRole('heading', { name: 'Metformin', level: 1 })).toBeVisible(),
    interact: async (page) => {
      await page.getByRole('button', { name: 'Log Dose' }).click();
      await expect(page.getByRole('dialog', { name: 'Log Dose' })).toBeVisible();
      await page.keyboard.press('Escape');
    },
    from: '/medications',
    trigger: (page) => page.locator(`a[href="/medications/${MED_ID}"]`).first().click(),
    kind: 'navigation',
    lazyRoute: true,
    expected: ['svg[data-t0]', 'p[data-t0]', 'span[data-t0]'],
  },
  {
    name: 'medications-reminders',
    path: '/medications?tab=reminders',
    ready: REMINDERS_READY,
    interact: async (page) => {
      await page.getByRole('button', { name: 'Refresh History' }).click();
    },
    from: '/medications',
    trigger: (page) => page.getByRole('tab', { name: 'Reminders' }).click(),
    kind: 'interaction',
    lazyRoute: true,
    expected: ['div[data-t0]'],
  },
  {
    name: 'notifications',
    path: '/notifications',
    ready: REMINDERS_READY,
    interact: async (page) => {
      await page.getByRole('button', { name: 'Refresh History' }).click();
    },
    from: '/medications',
    // The old route: the nav link opens it and the redirect lands on the Reminders tab (HC-UIMED-004).
    trigger: (page) => nav(page, 'Reminders').click(),
    kind: 'navigation',
    lazyRoute: true,
    expected: ['div[data-t0]'],
  },
];

const THEMES: Theme[] = ['light', 'dark'];

for (const theme of THEMES) {
  for (const route of GATE_ROUTES) {
    test(`UI-PG-MEDS GATE G1-G10 on ${route.path} (${theme})`, async ({ page }, testInfo) => {
      await page.setViewportSize(DESKTOP);
      const mock = await installMockApi(page);
      await mockMedicationApi(page);
      await seedMockSession(page);
      const guard = consoleAndNetworkGuard(page, { mock });

      await page.goto(route.path);
      await route.ready(page);
      await settle(page);

      // G9: the Safety Rail is in view at full opacity at first paint.
      const rail = await safetyVisible(page);
      expect(rail.found && rail.inViewport && rail.effectiveOpacity >= 0.99, `G9 ${JSON.stringify(rail)}`).toBe(true);

      // G1: axe, WCAG 2.0-2.2 A and AA, no serious or critical violations, in this theme.
      await setTheme(page, theme);
      const axe = await axeGate(page, { theme });
      expect(
        axe.blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
        `G1 ${route.path} ${theme}`
      ).toEqual([]);

      // G2: layout shift over the load.
      const cls = await measureCls(page, () => page.goto(route.path));
      expect(cls, `G2 ${route.path} ${theme}`).toBeLessThan(0.1);
      await route.ready(page);
      await settle(page);

      // G3: the worst Event Timing duration of the interaction, with CPU throttled x4.
      const inp = await maxEventDuration(page, () => route.interact(page), { cpuRate: 4 });
      expect(inp, `G3 ${route.path} ${theme}`).toBeLessThan(200);
      await settle(page);

      // G5: reduced motion, no element with a transform 50 ms after the interaction; screenshot for the PR.
      const offenders = await reducedMotionSnapshot(page, () => route.interact(page));
      expect(offenders, `G5 ${route.path} ${theme}`).toEqual([]);
      await page.screenshot({ path: testInfo.outputPath(`${route.name}-${theme}-reduced.png`), fullPage: false });
      testInfo.annotations.push({ type: 'gate-g5-screenshot', description: testInfo.outputPath(`${route.name}-${theme}-reduced.png`) });

      // G10: stillness of every [data-t0] node from the trigger, over the probe's window.
      await page.goto(route.from);
      await settle(page);
      const report = await stillnessProbe(page, {
        trigger: () => route.trigger(page),
        expected: route.expected,
        kind: route.kind,
        lazyRoute: route.lazyRoute,
      });
      testInfo.annotations.push({ type: 'gate-g10', description: `${route.path} ${theme}: ${JSON.stringify(report)}` });
      await route.ready(page);

      // G7: no console error, no non-localhost request, no unmocked API call.
      guard.assertClean();
      expect(mock.unmocked, `G7 unmocked ${route.path}`).toEqual([]);
    });
  }
}

// G6 at a phone width and at 320 px, on each route (light theme: the width does not change the theme).
for (const route of GATE_ROUTES) {
  test(`UI-PG-MEDS GATE G6 on ${route.path}: no horizontal scroll at 390 and 320`, async ({ page }) => {
    await installMockApi(page);
    await mockMedicationApi(page);
    await seedMockSession(page);
    await page.setViewportSize(PHONE);
    await page.goto(route.path);
    await route.ready(page);
    await settle(page);
    expect((await noHorizontalScroll(page)).ok, `G6 390 ${route.path}`).toBe(true);
    await page.setViewportSize(SMALL_PHONE);
    expect((await noHorizontalScroll(page)).ok, `G6 320 ${route.path}`).toBe(true);
  });
}

// HC-UIMED-002, end to end: the dose sheet is a modal, Escape closes it, focus is trapped and returns, and its
// dose text passes the stillness probe from the Log click.
test.describe('HC-UIMED-002: the dose sheet', () => {
  test('Escape closes it, Tab stays inside it, and focus returns to the Log button', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await installMockApi(page);
    await mockMedicationApi(page);
    await seedMockSession(page);
    await page.goto('/medications');
    await settle(page);

    const logButton = page.getByRole('button', { name: 'Log', exact: true }).first();
    await logButton.click();
    const dialog = page.getByRole('dialog', { name: 'Log Dose' });
    await expect(dialog).toBeVisible();
    for (let i = 0; i < 12; i += 1) {
      await page.keyboard.press('Tab');
      expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
    }
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(logButton).toBeFocused();
  });

  test('the dose text passes the stillness probe from the Log click', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await installMockApi(page);
    await mockMedicationApi(page);
    await seedMockSession(page);
    await page.goto('/medications');
    await settle(page);

    const report = await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: 'Log', exact: true }).first().click(),
      expected: ['[role="dialog"] [data-t0]'],
      kind: 'interaction',
    });
    expect(report.nodes).toBeGreaterThan(0);
    await page.keyboard.press('Escape');
  });
});

// HC-UIMED-004, end to end: /notifications lands on the Reminders tab with the same settings.
test('HC-UIMED-004: /notifications redirects to the Reminders tab with the same settings', async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await installMockApi(page);
  await mockMedicationApi(page);
  await seedMockSession(page);
  await page.goto(`/notifications?medicationId=${MED_ID}`);
  await expect(page).toHaveURL(new RegExp(`/medications\\?tab=reminders&medicationId=${MED_ID}$`));
  await expect(page.getByRole('tab', { name: 'Reminders' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByLabel('Quiet hours start')).toHaveValue('22:00');
  await expect(page.getByLabel('Quiet hours end')).toHaveValue('07:00');
});
