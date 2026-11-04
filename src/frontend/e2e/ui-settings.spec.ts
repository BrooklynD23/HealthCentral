/**
 * UI-PG-SETTINGS e2e (plan "UI-PG-SETTINGS"): HC-UISET-005 on the real layout, and Gate G on /settings.
 *
 *  - HC-UISET-005  no section is taller than 2 viewports at 1440 (RED on main: the one page was 5,565 px)
 *  - Gate G        the four sections (?section=security | preferences | assistant-privacy | advanced), plus the
 *                  consent dialog, the export confirm, the diagnostics dialog and the phone section sheet
 *
 * Every /api/v1 call is answered here: installMockApi serves the shared shell fixtures, and the routes registered
 * after it (they run first) give the settings calls realistic bodies (seven tiers, seven diagnostics worded as modules/environment_diagnostics.py words them, memories, one granted donation purpose), so the
 * heights below are not the height of an empty page. Run without the backend (recipe 2 in e2e/README.md):
 *   TMPDIR=/dev/shm npx playwright test e2e/ui-settings.spec.ts --project=chromium
 *
 * The stillness probes and the G2, G3 and G5 measurements are timing measurements. Run them on a quiet box only:
 *   GATE G2, G3, G5 and GATE G10 are selected with `-g`. The bare-timer test at the end is report-only and is
 *   skipped unless HC_REPORT_BARE_TIMER=1.
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
import type { DiagnosticsListResponse, ExternalApiSettings, TiersListResponse } from '../src/services/modelSettings';
import type { FeedbackStatsResponse } from '../src/services/feedback';
import type { MemoryItem } from '../src/services/types';

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const SMALL_PHONE = { width: 320, height: 640 };

type SectionId = 'security' | 'preferences' | 'assistant-privacy' | 'advanced';
const SECTIONS: Array<{ id: SectionId; tab: string }> = [
  { id: 'security', tab: 'Profile & security' },
  { id: 'preferences', tab: 'Preferences' },
  { id: 'assistant-privacy', tab: 'Assistant & privacy' },
  { id: 'advanced', tab: 'Advanced' },
];

const capabilities = (context_size: number) => ({
  context_size,
  multimodal: false,
  function_calling: false,
  agentic_capable: false,
});

const tiersFixture: TiersListResponse = {
  recommended_tier: 'mid',
  tiers: [
    // The seven rows GET /settings/model/tiers sends, in the backend's order (TIER_ORDER, then the template tier).
    { tier: 'high', name: 'Tier 3: High', model: 'BioMistral-7B', description: 'Medical-specialized model for best accuracy', available: false, downloaded: false, requirements: { ram_gb: 32, disk_gb: 5 }, can_run: false, capabilities: capabilities(8192) },
    { tier: 'gemma4-12b', name: 'Template Mode', model: null, description: 'Template-based interpretations (no AI model)', available: false, downloaded: false, requirements: { ram_gb: 16, disk_gb: 8 }, can_run: false, capabilities: { context_size: 32768, multimodal: true, function_calling: true, agentic_capable: false } },
    { tier: 'mid', name: 'Tier 2: Mid', model: 'Phi-4-mini-instruct', description: 'Balanced quality and performance', available: false, downloaded: false, requirements: { ram_gb: 16, disk_gb: 3 }, can_run: true, capabilities: capabilities(16384) },
    { tier: 'gemma4-e4b', name: 'Template Mode', model: null, description: 'Template-based interpretations (no AI model)', available: false, downloaded: false, requirements: { ram_gb: 12, disk_gb: 4 }, can_run: true, capabilities: capabilities(16384) },
    { tier: 'gemma4-e2b', name: 'Template Mode', model: null, description: 'Template-based interpretations (no AI model)', available: false, downloaded: false, requirements: { ram_gb: 8, disk_gb: 2 }, can_run: true, capabilities: capabilities(8192) },
    { tier: 'low', name: 'Tier 1: Low', model: 'Qwen2.5-0.5B-Instruct', description: 'Fast, lightweight model for basic interpretations', available: true, downloaded: true, requirements: { ram_gb: 8, disk_gb: 1 }, can_run: true, capabilities: capabilities(2048) },
    { tier: 'template', name: 'Template Mode', model: null, description: 'Template-based interpretations (no AI model)', available: true, downloaded: true, requirements: { ram_gb: 0, disk_gb: 0 }, can_run: true, capabilities: capabilities(0) },
  ],
};

// The seven components modules/environment_diagnostics.py returns, with its labels and its wording (its longest detail is the
// SQLCipher one on Windows). A shorter label or detail would hide how much room the list needs.
const diagnosticsFixture: DiagnosticsListResponse = {
  checked_at: '2026-11-01T08:00:00Z',
  components: [
    {
      id: 'tesseract', label: 'Tesseract OCR', status: 'error', detail: 'Not on PATH — required for OCR of scans and images.',
      fix_actions: [{ type: 'copy_command', label: 'Debian/Ubuntu', command: 'sudo apt install tesseract-ocr' }],
    },
    { id: 'ocr_python', label: 'OCR Python libraries', status: 'ok', detail: 'PIL: OK; pytesseract: OK; pdf2image: OK', fix_actions: [] },
    { id: 'poppler', label: 'Poppler (pdftoppm)', status: 'warn', detail: 'Not on PATH — scanned PDF → image conversion may fail on some systems.', fix_actions: [] },
    {
      id: 'sqlcipher', label: 'SQLCipher (profile DB)', status: 'warn',
      detail: 'sqlcipher3 not available. PyPI publishes Linux wheels only for sqlcipher3-binary, so pip usually cannot install it on Windows; the backend falls back to plain SQLite. Encryption is required in this configuration.',
      fix_actions: [],
    },
    {
      id: 'chat_model', label: 'Local chat model (GGUF)', status: 'ok', detail: 'At least one tier downloaded: low: qwen2.5-0.5b-instruct-q4_k_m.gguf',
      fix_actions: [{ type: 'open_url', label: 'Open Settings', url: '/settings' }],
    },
    { id: 'embeddings', label: 'Embeddings (sentence-transformers)', status: 'ok', detail: 'sentence-transformers importable.', fix_actions: [] },
    { id: 'gpu', label: 'GPU', status: 'ok', detail: 'NVIDIA GeForce RTX 3080 (10.0 GB VRAM)', fix_actions: [] },
  ],
};

const feedbackFixture: FeedbackStatsResponse = {
  total_feedback: 12,
  positive_count: 9,
  negative_count: 3,
  correction_count: 2,
  tag_distribution: {},
  model_distribution: {},
  provider_distribution: {},
};

const memoryFixture: MemoryItem[] = ['Allergy', 'Preferred pharmacy', 'Language'].map((key, i) => ({
  id: `mem-${i}`,
  profile_id: 'profile-fixture',
  key,
  value: `${key} note for the fixture`,
  category: ['medical', 'preferences', 'context'][i],
  created_at: '2026-10-01T10:00:00',
  updated_at: '2026-10-01T10:00:00',
}));

interface SettingsMockOptions {
  /** redaction_break_glass in GET /settings/model/external-api: true shows the warning. Default true. */
  breakGlass?: boolean;
  /** use_external_api in the same body: true shows the Provider, API Key and Model fields. Default false. */
  externalEnabled?: boolean;
}

/** GET /settings/model/external-api. A route registered later wins, so a test can call this again to change the body. */
async function mockExternalApi(page: Page, options: SettingsMockOptions = {}) {
  const { breakGlass = true, externalEnabled = false } = options;
  const body: ExternalApiSettings = {
    use_external_api: externalEnabled,
    provider: '',
    model: '',
    api_key_configured: false,
    redaction_break_glass: breakGlass,
  };
  await page.route(/\/api\/v1\/settings\/model\/external-api\/?$/, (route: Route, request) => {
    if (request.method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

/** Realistic bodies for the settings calls. Registered after installMockApi, so these routes win. */
async function mockSettingsApi(page: Page, options: SettingsMockOptions = {}) {
  const answer = (pattern: RegExp, body: unknown) =>
    page.route(pattern, (route: Route, request) => {
      if (request.method() !== 'GET') return route.fallback();
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    });
  await answer(/\/api\/v1\/settings\/model\/tiers\/?$/, tiersFixture);
  await answer(/\/api\/v1\/settings\/model\/diagnostics\/?$/, diagnosticsFixture);
  await mockExternalApi(page, options);
  await answer(/\/api\/v1\/feedback\/stats\/?$/, feedbackFixture);
  await answer(/\/api\/v1\/memory\/?(\?.*)?$/, memoryFixture);
  await answer(/\/api\/v1\/settings\/model\/download-progress\/?$/, {});
  // One purpose is granted, so the Stop and delete button (and its dialog) are on the page.
  await answer(/\/api\/v1\/donation\/consents\/?$/, {
    consents: (['fine_tune', 'synthetic_seed', 'agent_traces'] as const).map((purpose) => ({
      purpose,
      granted: purpose === 'fine_tune',
      consent_text_version: purpose === 'fine_tune' ? '2026-10-27-v3' : null,
      current: purpose === 'fine_tune',
      granted_at: null,
      revoked_at: null,
    })),
  });
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

/** Installs the mocks, then opens /settings (with ?section= when given). Returns the guard for G7. */
async function openSettings(page: Page, section?: SectionId, viewport = DESKTOP, options: SettingsMockOptions = {}) {
  await page.setViewportSize(viewport);
  const mock = await installMockApi(page);
  await mockSettingsApi(page, options);
  await seedMockSession(page);
  const guard = consoleAndNetworkGuard(page, { mock });
  await page.goto(section ? `/settings?section=${section}` : '/settings');
  await expect(page.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible({ timeout: 15_000 });
  await settle(page);
  return { mock, guard };
}

const showAdvanced = (page: Page) => page.getByRole('button', { name: 'Show advanced settings' });

async function expandAdvanced(page: Page) {
  await showAdvanced(page).click();
  await expect(page.getByTestId('tier-row-mid')).toBeVisible({ timeout: 10_000 });
  // The diagnostics list and the other panels arrive after the tiers: a height read before they do is not the page's height.
  await expect(page.getByRole('button', { name: 'Fix Tesseract OCR' })).toBeVisible({ timeout: 10_000 });
  await page.waitForLoadState('networkidle');
}

/** Opens a section on the page that is already loaded: the tab on a desktop, the section sheet on a phone. */
async function chooseSection(page: Page, tab: string, phone: boolean) {
  if (phone) {
    await page.getByRole('button', { name: /Settings sections/ }).click();
    await page.getByRole('dialog', { name: 'Settings sections' }).getByRole('button', { name: tab }).click();
  } else {
    await page.getByRole('tab', { name: tab }).click();
  }
}

const pageHeight = (page: Page) => page.evaluate(() => document.documentElement.scrollHeight);

// ---------------------------------------------------------------------------
// HC-UISET-005: no section is taller than 2 viewports at 1440 (1440 x 900, so 1800 px).
// ---------------------------------------------------------------------------
test.describe('HC-UISET-005: section height at 1440', () => {
  const BOUND = 2 * DESKTOP.height;

  for (const { id } of SECTIONS.filter((section) => section.id !== 'advanced')) {
    test(`HC-UISET-005: ${id} is at most 2 viewports tall`, async ({ page }) => {
      await openSettings(page, id);
      await page.waitForLoadState('networkidle');
      const height = await pageHeight(page);
      console.log(`HC-UISET-005 ${id}: ${height} px (bound ${BOUND})`);
      test.info().annotations.push({ type: 'height', description: `${id}: ${height} px (bound ${BOUND})` });
      expect(height, `${id} height ${height} px`).toBeLessThanOrEqual(BOUND);
    });
  }

  // Advanced is collapsed by default, and collapsed it is only the button: the page is the viewport (900 px), so a bound
  // asserted there could not fail. The bound is asserted on the state that has the content, expanded, with every panel
  // loaded and the fixture the size of the backend's (seven tiers, seven diagnostics, with the backend's wording).
  test('HC-UISET-005: advanced is at most 2 viewports tall expanded', async ({ page }) => {
    await openSettings(page, 'advanced');
    const collapsed = await pageHeight(page);
    await expandAdvanced(page);
    const expanded = await pageHeight(page);
    console.log(`HC-UISET-005 advanced: collapsed ${collapsed} px, expanded ${expanded} px (bound ${BOUND})`);
    test.info().annotations.push({ type: 'height', description: `advanced collapsed ${collapsed} px, expanded ${expanded} px (bound ${BOUND})` });
    expect(expanded, 'expanding Advanced added content').toBeGreaterThan(collapsed);
    expect(expanded, `advanced expanded height ${expanded} px`).toBeLessThanOrEqual(BOUND);
  });
});

// The three columns are narrow (about 340 px each at 1280): a label that is cut, or a button whose caption wraps on its hyphen,
// costs the patient the word. Detail text may be shortened to two lines only when the whole text can be read: from the title,
// and from the fix dialog, which prints it whole.
for (const width of [1280, 1440]) {
  test(`HC-UISET-005: Advanced shows its diagnostics labels and buttons whole at ${width}`, async ({ page }) => {
    await openSettings(page, 'advanced', { width, height: 900 });
    await expandAdvanced(page);
    for (const component of diagnosticsFixture.components) {
      const row = page.getByRole('button', { name: `Fix ${component.label}` }).locator('xpath=ancestor::div[contains(@class,"bg-surface-muted")][1]');
      const label = row.getByText(component.label, { exact: true });
      const box = await label.evaluate((el) => ({ w: el.scrollWidth - el.clientWidth, h: el.scrollHeight - el.clientHeight }));
      expect(box, `${width}: label "${component.label}" is cut`).toEqual({ w: 0, h: 0 });
      const detail = row.getByText(component.detail, { exact: true });
      const cut = await detail.evaluate((el) => el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight + 1);
      if (cut) await expect(detail, `${width}: cut detail of "${component.label}" has its text as title`).toHaveAttribute('title', component.detail);
    }
    for (const name of ['Re-detect', 'Detect Hardware', 'Re-check']) {
      const button = page.getByRole('button', { name });
      if ((await button.count()) === 0) continue;
      // A caption on one line is the button's minimum height (min-h-target); wrapped on the hyphen it is a line taller.
      const { height } = (await button.boundingBox())!;
      expect(height, `${width}: "${name}" is one line tall`).toBeLessThanOrEqual(48);
    }
  });
}

// ---------------------------------------------------------------------------
// HC-UISET-002 / 004 on the real layout: the collapsed region and the dialogs.
// ---------------------------------------------------------------------------
test('HC-UISET-002: Advanced shows no Tesseract, GPU or tier text until "Show advanced settings"', async ({ page }) => {
  await openSettings(page, 'advanced');
  await expect(showAdvanced(page)).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText(/Tesseract/)).toHaveCount(0);
  await expect(page.getByText(/GPU/)).toHaveCount(0);
  await expect(page.getByTestId('tier-row-mid')).toHaveCount(0);
  await expandAdvanced(page);
  await expect(page.getByText(/Tesseract/).first()).toBeVisible();
  await expect(page.getByText(/GPU/).first()).toBeVisible();
});

test('HC-UISET-004: the consent AlertDialog closes on Escape and returns focus to the switch', async ({ page }) => {
  await openSettings(page, 'assistant-privacy');
  const toggle = page.getByRole('switch', { name: 'Use External API' });
  await toggle.click();
  const dialog = page.getByRole('alertdialog', { name: 'Privacy Notice' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(toggle).toBeFocused();
});

// ---------------------------------------------------------------------------
// Gate G on /settings. G1, G6, G7 and G9 are not timing measurements; G2, G3, G5 and G10 are (quiet box only).
// ---------------------------------------------------------------------------
const THEMES: Theme[] = ['light', 'dark'];

/**
 * setTheme, then wait for the colour transitions it starts (Badge, filter chips and others fade their colours over 150 to
 * 200 ms). axe reads computed colours, so a read taken mid-fade measures a colour that is neither theme's.
 */
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

for (const theme of THEMES) {
  test(`UI-PG-SETTINGS GATE G1, G7, G9 on /settings (${theme})`, async ({ page }) => {
    const { mock, guard } = await openSettings(page);

    for (const { id, tab } of SECTIONS) {
      await page.goto(`/settings?section=${id}`);
      await expect(page.getByRole('tab', { name: tab })).toHaveAttribute('aria-selected', 'true');
      await settle(page);
      await expectRailVisible(page, `${id} first paint`);
      await applyTheme(page, theme);
      await expectNoBlockingViolations(page, theme, id);

      if (id === 'assistant-privacy') {
        // The consent dialog and the section with the break-glass warning shown.
        await expect(page.getByRole('alert').filter({ hasText: 'Privacy protection override is on.' })).toBeVisible();
        await page.getByRole('switch', { name: 'Use External API' }).click();
        await expect(page.getByRole('alertdialog', { name: 'Privacy Notice' })).toBeVisible();
        await expectNoBlockingViolations(page, theme, 'consent dialog');
        await page.keyboard.press('Escape');
        await expect(page.getByRole('alertdialog')).toHaveCount(0);

        await page.getByRole('button', { name: /^Stop and delete:/ }).click();
        await expect(page.getByRole('alertdialog', { name: 'Confirm stop and delete' })).toBeVisible();
        await expectNoBlockingViolations(page, theme, 'stop and delete dialog');
        await page.keyboard.press('Escape');
        await expect(page.getByRole('alertdialog')).toHaveCount(0);

        // The Provider, API Key and Model fields only render once the external API is on.
        await mockExternalApi(page, { externalEnabled: true });
        await page.reload();
        await expect(page.getByPlaceholder('sk-...')).toBeVisible();
        // The fields fade in: axe must not read them mid-fade.
        await waitUntilOpaque(page, '#external-provider-select');
        await applyTheme(page, theme);
        await expectNoBlockingViolations(page, theme, 'external API fields');
        await mockExternalApi(page);
      }

      if (id === 'advanced') {
        await expandAdvanced(page);
        await expectNoBlockingViolations(page, theme, 'advanced expanded');
        await page.getByRole('button', { name: 'Export training data' }).click();
        await expect(page.getByRole('alertdialog', { name: 'Export training data?' })).toBeVisible();
        await expectNoBlockingViolations(page, theme, 'export confirm');
        await page.keyboard.press('Escape');
        await expect(page.getByRole('alertdialog')).toHaveCount(0);
        await page.getByRole('button', { name: 'Fix Tesseract OCR' }).click();
        await expect(page.getByRole('dialog', { name: 'Tesseract OCR' })).toBeVisible();
        await waitUntilOpaque(page, '#diag-tool-title');
        await expectNoBlockingViolations(page, theme, 'diagnostics dialog');
        await page.getByRole('dialog', { name: 'Tesseract OCR' }).getByRole('button', { name: 'Close' }).click();
        await expect(page.getByRole('dialog')).toHaveCount(0);
      }
      await expectRailVisible(page, `${id} after`);
    }

    // The phone section sheet.
    await page.setViewportSize(PHONE);
    await page.goto('/settings?section=preferences');
    await settle(page);
    await applyTheme(page, theme);
    await page.getByRole('button', { name: /Settings sections/ }).click();
    await expect(page.getByRole('dialog', { name: 'Settings sections' })).toBeVisible();
    await expectNoBlockingViolations(page, theme, 'phone section sheet');

    // G7: no console error, no non-localhost request, no unmocked API call.
    guard.assertClean();
    expect(mock.unmocked, 'G7 unmocked').toEqual([]);
  });
}

test('UI-PG-SETTINGS GATE G6 on /settings: no horizontal scroll at 390 and 320', async ({ page }) => {
  await openSettings(page, 'security', PHONE);
  for (const [name, size] of [['390', PHONE], ['320', SMALL_PHONE]] as const) {
    await page.setViewportSize(size);
    for (const { id, tab } of SECTIONS) {
      await chooseSection(page, tab, true);
      await expect(page.getByRole('button', { name: /Settings sections/ })).toContainText(tab);
      await page.waitForLoadState('networkidle');
      expect((await noHorizontalScroll(page)).ok, `G6 ${name} ${id}`).toBe(true);
      if (id === 'advanced') {
        await expandAdvanced(page);
        expect((await noHorizontalScroll(page)).ok, `G6 ${name} advanced expanded`).toBe(true);
      }
      if (id === 'assistant-privacy') {
        await page.getByRole('switch', { name: 'Use External API' }).click();
        await expect(page.getByRole('alertdialog', { name: 'Privacy Notice' })).toBeVisible();
        expect((await noHorizontalScroll(page)).ok, `G6 ${name} consent dialog`).toBe(true);
        await page.keyboard.press('Escape');
        await expect(page.getByRole('alertdialog')).toHaveCount(0);
      }
    }
    await page.getByRole('button', { name: /Settings sections/ }).click();
    await expect(page.getByRole('dialog', { name: 'Settings sections' })).toBeVisible();
    expect((await noHorizontalScroll(page)).ok, `G6 ${name} section sheet`).toBe(true);
    await page.keyboard.press('Escape');
  }
});

test('UI-PG-SETTINGS GATE G2, G3, G5 on /settings (quiet box only)', async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await installMockApi(page);
  await mockSettingsApi(page);
  await seedMockSession(page);

  const interactions = async () => {
    await page.getByRole('tab', { name: 'Preferences' }).click();
    await expect(page.getByLabel('Time zone')).toBeVisible();
    await page.getByRole('tab', { name: 'Assistant & privacy' }).click();
    await page.getByRole('switch', { name: 'Use External API' }).click();
    await expect(page.getByRole('alertdialog', { name: 'Privacy Notice' })).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await page.getByRole('tab', { name: 'Advanced' }).click();
    await showAdvanced(page).click();
    await expect(page.getByTestId('tier-row-mid')).toBeVisible();
  };

  // G2: layout shift over the load and the interactions.
  const cls = await measureCls(page, async () => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible();
    await settle(page);
    await interactions();
  });
  expect(cls, 'G2 /settings').toBeLessThan(0.1);

  // G3: the worst Event Timing duration of the same interactions, CPU throttled x4.
  await page.goto('/settings');
  await settle(page);
  const inp = await maxEventDuration(page, interactions, { cpuRate: 4 });
  expect(inp, 'G3 /settings').toBeLessThan(200);

  // G5: reduced motion, one snapshot 50 ms after each interaction (plan G5), so a transform that one step leaves behind
  // is not cleared by the next. The overlays are separate steps: opening and closing each of them.
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/settings');
  await settle(page);
  const consentDialog = page.getByRole('alertdialog', { name: 'Privacy Notice' });
  const stopDialog = page.getByRole('alertdialog', { name: 'Confirm stop and delete' });
  const exportDialog = page.getByRole('alertdialog', { name: 'Export training data?' });
  const diagnosticsDialog = page.getByRole('dialog', { name: 'Tesseract OCR' });
  const steps: Array<[string, () => Promise<void>]> = [
    ['Preferences tab', async () => { await page.getByRole('tab', { name: 'Preferences' }).click(); await expect(page.getByLabel('Time zone')).toBeVisible(); }],
    ['Assistant & privacy tab', async () => { await page.getByRole('tab', { name: 'Assistant & privacy' }).click(); await expect(page.getByRole('switch', { name: 'Use External API' })).toBeVisible(); }],
    ['consent dialog opens', async () => { await page.getByRole('switch', { name: 'Use External API' }).click(); await expect(consentDialog).toBeVisible(); }],
    ['consent dialog closes', async () => { await page.keyboard.press('Escape'); await expect(consentDialog).toHaveCount(0); }],
    ['Stop and delete dialog opens', async () => { await page.getByRole('button', { name: /^Stop and delete:/ }).click(); await expect(stopDialog).toBeVisible(); }],
    ['Stop and delete dialog closes', async () => { await page.keyboard.press('Escape'); await expect(stopDialog).toHaveCount(0); }],
    ['Advanced tab', async () => { await page.getByRole('tab', { name: 'Advanced' }).click(); await expect(showAdvanced(page)).toBeVisible(); }],
    ['Show advanced settings', async () => { await showAdvanced(page).click(); await expect(page.getByTestId('tier-row-mid')).toBeVisible(); }],
    ['export confirm opens', async () => { await page.getByRole('button', { name: 'Export training data' }).click(); await expect(exportDialog).toBeVisible(); }],
    ['export confirm closes', async () => { await page.keyboard.press('Escape'); await expect(exportDialog).toHaveCount(0); }],
    ['diagnostics dialog opens', async () => { await page.getByRole('button', { name: 'Fix Tesseract OCR' }).click(); await expect(diagnosticsDialog).toBeVisible(); }],
    ['diagnostics dialog closes', async () => { await diagnosticsDialog.getByRole('button', { name: 'Close' }).click(); await expect(diagnosticsDialog).toHaveCount(0); }],
  ];
  const offenders: string[] = [];
  for (const [name, step] of steps) {
    offenders.push(...(await reducedMotionSnapshot(page, step)).map((offender) => `${name}: ${offender}`));
  }
  expect(offenders, 'G5 /settings').toEqual([]);

  // The phone section sheet.
  await page.setViewportSize(PHONE);
  await page.goto('/settings?section=preferences');
  await settle(page);
  const sheet = page.getByRole('dialog', { name: 'Settings sections' });
  const sheetOffenders = [
    ...(await reducedMotionSnapshot(page, async () => { await page.getByRole('button', { name: /Settings sections/ }).click(); await expect(sheet).toBeVisible(); })).map((o) => `section sheet opens: ${o}`),
    ...(await reducedMotionSnapshot(page, async () => { await page.keyboard.press('Escape'); await expect(sheet).toHaveCount(0); })).map((o) => `section sheet closes: ${o}`),
  ];
  expect(sheetOffenders, 'G5 /settings section sheet').toEqual([]);
});

test.describe('UI-PG-SETTINGS GATE G10 (quiet box only)', () => {
  test('UI-PG-SETTINGS GATE G10 on the navigation to /settings?section=assistant-privacy', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await installMockApi(page);
    await mockSettingsApi(page);
    await seedMockSession(page);
    await page.goto('/inbox');
    await settle(page);
    await page.evaluate(() => document.fonts.ready);
    const report = await stillnessProbe(page, {
      // No nav item leads to this section; the history entry is how the other specs reach a link-less route.
      trigger: async () => {
        await page.evaluate(() => {
          window.history.pushState({}, '', '/settings?section=assistant-privacy');
          window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
        });
      },
      expected: ['[role="alert"][data-t0]'],
      kind: 'navigation',
      lazyRoute: true,
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('UI-PG-SETTINGS GATE G10 on the tab switch to Assistant & privacy', async ({ page }) => {
    await openSettings(page);
    await page.evaluate(() => document.fonts.ready);
    const report = await stillnessProbe(page, {
      trigger: () => page.getByRole('tab', { name: 'Assistant & privacy' }).click(),
      expected: ['[role="alert"][data-t0]'],
      lazyRoute: true,
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('UI-PG-SETTINGS GATE G10 on "Show advanced settings"', async ({ page }) => {
    await openSettings(page, 'advanced');
    await page.evaluate(() => document.fonts.ready);
    const report = await stillnessProbe(page, {
      trigger: () => showAdvanced(page).click(),
      expected: ['[data-testid^="tier-row-"] [data-t0]'],
      lazyRoute: true,
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  test('UI-PG-SETTINGS GATE G10 on the consent dialog opening', async ({ page }) => {
    await openSettings(page, 'assistant-privacy');
    await page.evaluate(() => document.fonts.ready);
    const report = await stillnessProbe(page, {
      trigger: () => page.getByRole('switch', { name: 'Use External API' }).click(),
      expected: ['[role="alertdialog"] [data-t0]'],
      kind: 'overlay',
    });
    expect(report.nodes).toBeGreaterThan(0);
  });

  // Rows of the donation card sat 52 px higher while this dialog was open when the button that opens it was removed.
  test('UI-PG-SETTINGS GATE G10 on the Stop and delete dialog opening', async ({ page }) => {
    await openSettings(page, 'assistant-privacy');
    await page.evaluate(() => document.fonts.ready);
    const report = await stillnessProbe(page, {
      trigger: () => page.getByRole('button', { name: /^Stop and delete:/ }).click(),
      expected: ['[id^="donation-desc-"][data-t0]'],
      kind: 'overlay',
    });
    expect(report.nodes).toBeGreaterThan(0);
    await expect(page.getByRole('alertdialog', { name: 'Confirm stop and delete' })).toBeVisible();
  });

  // Every Download button is disabled while a download runs; they turn grey and must not fade.
  test('UI-PG-SETTINGS GATE G10 on pressing Download', async ({ page }) => {
    await openSettings(page, 'advanced');
    let started = false;
    await page.route(/\/api\/v1\/settings\/model\/download\/?$/, (route) => {
      started = true;
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tier: 'mid', status: 'pending', progress: 0, downloaded_bytes: 0, total_bytes: 0, path: null, error: null }) });
    });
    await page.route(/\/api\/v1\/settings\/model\/download-progress\/?$/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(started ? { mid: { tier: 'mid', status: 'downloading', progress: 0.3, downloaded_bytes: 1_000_000_000, total_bytes: 3_000_000_000, path: null, error: null } } : {}),
      })
    );
    await expandAdvanced(page);
    await page.evaluate(() => document.fonts.ready);
    // The Mid row is at the bottom edge of a 900 px viewport: if the click scrolled the page, every T0 rect would move
    // inside the probe's window. Scroll first, so the probe sees the press and nothing else.
    const download = page.getByTestId('tier-row-mid').getByRole('button', { name: 'Download' });
    await download.scrollIntoViewIfNeeded();
    const report = await stillnessProbe(page, {
      trigger: () => download.click(),
      expected: ['[data-testid^="tier-row-"] [data-t0]'],
    });
    expect(report.nodes).toBeGreaterThan(0);
    expect(started, 'the Download press reached POST /settings/model/download').toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Report-only: a bare 20 ms timer through /inbox -> /settings (recurring-failures #14). The page reads no DOM and
// the test asserts nothing about the figure. L0 judges it against the 40 ms bound (L0 ruling 6627952531 on #488, item 4).
//   HC_REPORT_BARE_TIMER=1 HC_E2E_BASE_URL=<vite preview> npx playwright test e2e/ui-settings.spec.ts -g "report-only"
// ---------------------------------------------------------------------------
test('UI-PG-SETTINGS report-only: bare 20 ms timer gap through /inbox -> /settings', async ({ page }) => {
  test.skip(process.env.HC_REPORT_BARE_TIMER !== '1', 'report-only; set HC_REPORT_BARE_TIMER=1 to run it');
  test.setTimeout(180_000);
  await page.setViewportSize(DESKTOP);
  await installMockApi(page);
  await mockSettingsApi(page);
  await seedMockSession(page);

  const maxGaps: number[] = [];
  for (let run = 0; run < 5; run += 1) {
    await page.goto('/inbox');
    await settle(page);
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => {
      const w = window as unknown as { __bareGaps: number[]; __bareTimer: number };
      w.__bareGaps = [];
      let last = performance.now();
      w.__bareTimer = window.setInterval(() => {
        const now = performance.now();
        w.__bareGaps.push(now - last);
        last = now;
      }, 20);
    });
    await page.getByRole('button', { name: 'Profile and settings' }).click();
    await page.getByRole('link', { name: 'Settings', exact: true }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible();
    await page.waitForTimeout(800);
    const gaps = await page.evaluate(() => {
      const w = window as unknown as { __bareGaps: number[]; __bareTimer: number };
      window.clearInterval(w.__bareTimer);
      return w.__bareGaps;
    });
    maxGaps.push(Math.max(...gaps));
  }
  const sorted = [...maxGaps].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];
  const line = `BARE-TIMER /inbox -> /settings: max gaps ${maxGaps.map((g) => g.toFixed(1)).join(', ')} ms; median ${median.toFixed(1)} ms (report only)`;
  console.log(line);
  test.info().annotations.push({ type: 'bare-timer', description: line });
});
