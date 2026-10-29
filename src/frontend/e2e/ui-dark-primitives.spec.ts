/**
 * DARK-PRIMITIVE-CONTRAST end-to-end check (HC-DPC-003).
 *
 * The unlock form on /setup renders the shared Input and the primary Button. Both must pass axe
 * (WCAG tags, serious and critical) and a computed-style contrast of at least 4.5:1, in dark and in
 * light. The page is served by the mock API, so the form renders without a backend profile.
 * Plan: docs/plans/2026-10-28-followups-plan.md, section DARK-PRIMITIVE-CONTRAST.
 */
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { installMockApi } from './support/mockApi';
import { setTheme, WCAG_TAGS, type Theme } from './support/gates';

/** Waits until no finite animation runs. Infinite loaders (spinners, pulses) are ignored. */
async function settleFiniteAnimations(page: Page): Promise<void> {
  await page.waitForFunction(
    () =>
      document.getAnimations().every((animation) => {
        const iterations = animation.effect?.getComputedTiming().iterations;
        return iterations === Infinity || animation.playState !== 'running';
      }),
    undefined,
    { timeout: 5000 }
  );
}

/** Settles transitions after a theme change, then waits one frame, so the read is never a blend of two themes. */
async function settleTheme(page: Page, theme: Theme): Promise<void> {
  await setTheme(page, theme);
  await settleFiniteAnimations(page);
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => resolve())));
}

/** WCAG 2.x ratio of the element's computed text colour over its computed background, read in the page. */
async function computedContrast(target: Locator): Promise<number> {
  return target.evaluate((el) => {
    const channels = (value: string): number[] => {
      const match = /rgba?\(([^)]+)\)/.exec(value);
      if (!match) throw new Error(`not an rgb colour: ${value}`);
      return (match[1] ?? '').split(/[\s,/]+/).filter(Boolean).map(Number);
    };
    const luminance = (rgb: number[]): number => {
      const lin = (channel: number) => {
        const s = channel / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * lin(rgb[0] ?? 0) + 0.7152 * lin(rgb[1] ?? 0) + 0.0722 * lin(rgb[2] ?? 0);
    };
    const style = getComputedStyle(el);
    const text = channels(style.color);
    const fill = channels(style.backgroundColor);
    if ((fill[3] ?? 1) < 1) throw new Error(`background is not opaque: ${style.backgroundColor}`);
    const a = luminance(text);
    const b = luminance(fill);
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  });
}

test('HC-DPC-003: the unlock form\'s Input and default Button pass axe and computed contrast in dark', async ({
  page,
}) => {
  await installMockApi(page);
  await page.goto('/setup');

  const field = page.getByLabel('Unlock password');
  const button = page.getByRole('button', { name: 'Unlock', exact: true });
  await field.fill('x');
  await expect(field).toBeVisible();
  await expect(button).toBeVisible();

  // axe runs on one element at a time, so each target carries a data attribute that `include` can select.
  await field.evaluate((el) => el.setAttribute('data-dpc-target', 'field'));
  await button.evaluate((el) => el.setAttribute('data-dpc-target', 'button'));
  const targets: [name: string, locator: Locator, selector: string][] = [
    ['Input', field, '[data-dpc-target="field"]'],
    ['primary Button', button, '[data-dpc-target="button"]'],
  ];

  // Every measurement is logged and every failure collected before the single assertion, so one run shows
  // each target's result in both themes (the ratios are the evidence).
  const failures: string[] = [];
  for (const theme of ['dark', 'light'] as const) {
    await settleTheme(page, theme);
    for (const [name, locator, selector] of targets) {
      const axe = await new AxeBuilder({ page }).withTags(WCAG_TAGS).include(selector).analyze();
      const blocking = axe.violations
        .filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
        .map((violation) => `${violation.id} (${violation.impact})`);
      for (const id of blocking) failures.push(`${theme} ${name} axe: ${id}`);

      const ratio = await computedContrast(locator);
      console.log(`HC-DPC-003 ${theme} ${name} axe serious or critical: ${JSON.stringify(blocking)}`);
      console.log(`HC-DPC-003 ${theme} ${name} computed contrast: ${ratio.toFixed(2)} (min 4.5)`);
      if (ratio < 4.5) failures.push(`${theme} ${name} computed contrast ${ratio.toFixed(2)} < 4.5`);
    }
  }
  expect(failures, 'unlock form Input and primary Button in dark and light').toEqual([]);
});
