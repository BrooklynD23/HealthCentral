/**
 * TOAST-SHELL (HC-TOAST-001 .. HC-TOAST-004): the shared toaster under Gate G5
 * (reduced motion) and against the phone chrome (TOAST-PHONE-CHROME).
 *
 * sonner centres its list with `transform: translateX(-50%)` above 600 px, which
 * fails G5 for the whole life of any toast, and it places the list over the tab
 * bar and the Safety Rail. globals.css fixes both with unlayered `:root` rules.
 *
 * Dev server (HC_E2E_BASE_URL unset, what CI runs): a real toast, raised with
 * notify() from /src/components/ui/toast.tsx, as HC-UISH-007 does. sonner is
 * never imported here, because a second copy of its store is not the one the
 * app's Toaster renders. Toasts are dismissed with OVERLAY_OPEN_EVENT only, never
 * with a pointer, which would expand the stack.
 *
 * vite preview (HC_E2E_BASE_URL set): /src/... does not exist, so an `ol` and its
 * `li` children are injected with sonner's runtime attributes and variables, and
 * the page's real cascade (sonner's <style> plus the built globals.css) is read.
 */

import { expect, test, type Page } from '@playwright/test';
import { reducedMotionSnapshot } from './support/gates';
import { installMockApi, seedMockSession } from './support/mockApi';

// The identity as getComputedStyle reports it: `none`, or the 2D identity matrix (a front toast's translateY(0)).
const IDENTITY_TRANSFORM = /^(none|matrix\(1, 0, 0, 1, 0, 0\))$/;
const PREVIEW = Boolean(process.env.HC_E2E_BASE_URL);
const TOASTER = '[data-sonner-toaster]';
const TOAST = '[data-sonner-toast]';

async function openInbox(page: Page, viewport: { width: number; height: number }) {
  await page.setViewportSize(viewport);
  await installMockApi(page);
  await seedMockSession(page);
  await page.goto('/inbox');
  await expect(page.locator('[data-safety-rail]')).toBeVisible({ timeout: 15_000 });
}

/** Dev only: raises real toasts through the app's own notify(). */
async function raise(page: Page, toasts: Array<{ message: string; still?: boolean }>) {
  await page.evaluate(async (items) => {
    const toast = await import('/src/components/ui/toast.tsx');
    for (const item of items) toast.notify(item);
  }, toasts);
}

/** Dev only: dismisses every toast the way an opening overlay does. */
async function dismissAll(page: Page) {
  await page.evaluate(async () => {
    const toast = await import('/src/components/ui/toast.tsx');
    document.dispatchEvent(new Event(toast.OVERLAY_OPEN_EVENT));
  });
}

async function waitForSettledToasts(page: Page, count: number) {
  await expect(page.locator(TOAST)).toHaveCount(count);
  await expect(page.locator(`${TOAST}[data-mounted="true"]`)).toHaveCount(count);
  // sonner measures heights after mount; let the layout stop moving.
  await expect
    .poll(
      async () => {
        const read = () =>
          page.locator(TOAST).evaluateAll((els) => els.map((el) => JSON.stringify(el.getBoundingClientRect())).join('|'));
        const a = await read();
        await page.waitForTimeout(150);
        return a === (await read());
      },
      { timeout: 5000 }
    )
    .toBe(true);
}

type FixtureToast = { front: boolean; removed: boolean };

/**
 * Preview only: asserts sonner's runtime <style> is present, then injects an `ol` that carries the
 * attributes and variables sonner's own render sets (sonner index.mjs:715-737, GAP = 14).
 */
async function injectFixture(page: Page, toasts: FixtureToast[]) {
  const hasSonnerStyle = await page.evaluate(() =>
    Array.from(document.querySelectorAll('style')).some((s) => (s.textContent ?? '').includes('[data-sonner-toaster]'))
  );
  expect(hasSonnerStyle, "sonner's runtime <style> is in <head>").toBe(true);
  await page.evaluate((items) => {
    const ol = document.createElement('ol');
    ol.setAttribute('data-sonner-toaster', 'true');
    ol.setAttribute('data-x-position', 'center');
    ol.setAttribute('data-y-position', 'bottom');
    ol.setAttribute(
      'style',
      '--width: 356px; --gap: 14px; --front-toast-height: 56px; --offset-bottom: 24px; ' +
        '--mobile-offset-bottom: 16px; --mobile-offset-left: 16px; --mobile-offset-right: 16px; z-index: var(--z-toast)'
    );
    items.forEach((item, index) => {
      const li = document.createElement('li');
      li.setAttribute('data-sonner-toast', '');
      li.setAttribute('data-y-position', 'bottom');
      li.setAttribute('data-x-position', 'center');
      li.setAttribute('data-mounted', 'true');
      li.setAttribute('data-styled', 'true');
      li.setAttribute('data-front', String(item.front));
      li.setAttribute('data-expanded', 'false');
      li.setAttribute('data-removed', String(item.removed));
      li.setAttribute('data-swiping', 'false');
      li.setAttribute('data-swipe-out', 'false');
      li.setAttribute(
        'style',
        `--index: ${index}; --toasts-before: ${index}; --z-index: ${items.length - index}; --offset: 0px; --initial-height: 56px`
      );
      li.textContent = `fixture toast ${index}`;
      ol.appendChild(li);
    });
    document.body.appendChild(ol);
  }, toasts);
}

interface ListState {
  transform: string;
  left: number;
  width: number;
  bottom: string;
  leftCss: string;
  rightCss: string;
  centreOffset: number;
}

async function listState(page: Page): Promise<ListState> {
  return page.evaluate((selector) => {
    const ol = document.querySelector(selector) as HTMLElement;
    const style = getComputedStyle(ol);
    const rect = ol.getBoundingClientRect();
    return {
      transform: style.transform,
      left: rect.left,
      width: rect.width,
      bottom: style.bottom,
      leftCss: style.left,
      rightCss: style.right,
      centreOffset: rect.left + rect.width / 2 - document.documentElement.clientWidth / 2,
    };
  }, TOASTER);
}

// ---------------------------------------------------------------------------
// HC-TOAST-001: a lone toast leaves no transform anywhere, and the list stays centred.
// ---------------------------------------------------------------------------
test.describe('HC-TOAST-001 a lone toast has no transform', () => {
  for (const viewport of [
    { width: 1280, height: 800 },
    { width: 1440, height: 900 },
  ]) {
    for (const still of [false, true]) {
      test(`HC-TOAST-001: ${still ? 'still' : 'plain'} toast at ${viewport.width}x${viewport.height}`, async ({ page }) => {
        await openInbox(page, viewport);
        if (PREVIEW) {
          // `still` only changes the toast's content class in the app; the injected fixture is identical for both
          // cases, so on preview the still and plain cases are the same check by design.
          await page.emulateMedia({ reducedMotion: 'reduce' });
          await injectFixture(page, [{ front: true, removed: false }]);
        } else {
          const offenders = await reducedMotionSnapshot(page, () => raise(page, [{ message: 'Saved', still }]));
          expect(offenders, 'elements with a non-identity transform 50 ms after the toast').toEqual([]);
        }
        const state = await listState(page);
        expect(state.transform, 'the list transform').toBe('none');
        expect(
          Math.abs(state.centreOffset),
          `list centre vs clientWidth/2 (left ${state.left}, width ${state.width})`
        ).toBeLessThanOrEqual(1);
      });
    }
  }
});

// ---------------------------------------------------------------------------
// HC-TOAST-002: the toast clears the phone chrome (tab bar, Safety Rail) and stays on screen.
// ---------------------------------------------------------------------------
test.describe('HC-TOAST-002 the toast sits above the shell chrome', () => {
  for (const viewport of [
    { width: 390, height: 844 },
    { width: 820, height: 1180 },
    { width: 1440, height: 900 },
  ]) {
    test(`HC-TOAST-002: ${viewport.width}x${viewport.height}`, async ({ page }) => {
      await openInbox(page, viewport);
      if (PREVIEW) {
        await injectFixture(page, [{ front: true, removed: false }]);
        const state = await listState(page);
        const shell = await page.evaluate(() =>
          parseFloat(document.documentElement.style.getPropertyValue('--shell-bottom-h') || '0')
        );
        expect(shell, '--shell-bottom-h on <html> (a missing or 0 value would make the check vacuous)').toBeGreaterThan(0);
        const expected = shell + (viewport.width <= 600 ? 16 : 24);
        expect(
          Math.abs(parseFloat(state.bottom) - expected),
          `bottom ${state.bottom} vs ${expected} (shell ${shell})`
        ).toBeLessThanOrEqual(0.5);
        return;
      }
      await raise(page, [{ message: 'Document saved' }]);
      await waitForSettledToasts(page, 1);
      const report = await page.evaluate((toastSel) => {
        const toast = document.querySelector(toastSel)!.getBoundingClientRect();
        const clientWidth = document.documentElement.clientWidth;
        const chrome: Array<{ name: string; rect: DOMRect }> = [];
        const tab = document.querySelector('nav[aria-label="Tab bar"]') as HTMLElement | null;
        if (tab && getComputedStyle(tab).display !== 'none') chrome.push({ name: 'tab bar', rect: tab.getBoundingClientRect() });
        const rail = document.querySelector('[data-safety-rail]') as HTMLElement | null;
        if (rail) chrome.push({ name: 'safety rail', rect: rail.getBoundingClientRect() });
        const overlaps = chrome
          .filter(
            ({ rect }) =>
              rect.width > 0 &&
              toast.left < rect.right &&
              toast.right > rect.left &&
              toast.top < rect.bottom &&
              toast.bottom > rect.top
          )
          .map(({ name, rect }) => `${name} ${JSON.stringify(rect)}`);
        return { toast: JSON.stringify(toast), overlaps, inside: toast.left >= 0 && toast.right <= clientWidth, clientWidth };
      }, TOAST);
      expect(report.overlaps, `toast ${report.toast} overlaps`).toEqual([]);
      expect(report.inside, `toast ${report.toast} inside [0, ${report.clientWidth}]`).toBe(true);
    });
  }
});

// ---------------------------------------------------------------------------
// HC-TOAST-003: stacked and dismissed toasts under reduced motion.
// ---------------------------------------------------------------------------
test.describe('HC-TOAST-003 stacked and dismissed toasts under reduced motion', () => {
  const VIEWPORT = { width: 1280, height: 800 };

  test('HC-TOAST-003a: a second toast over a first leaves no transform', async ({ page }) => {
    await openInbox(page, VIEWPORT);
    if (PREVIEW) {
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await injectFixture(page, [
        { front: true, removed: false },
        { front: false, removed: false },
      ]);
      const transforms = await page.locator(TOAST).evaluateAll((els) => els.map((el) => getComputedStyle(el).transform));
      expect(transforms.filter((t) => !IDENTITY_TRANSFORM.test(t)), `fixture li transforms (front, back): ${transforms}`).toEqual([]);
      return;
    }
    await raise(page, [{ message: 'First' }]);
    await waitForSettledToasts(page, 1);
    const offenders = await reducedMotionSnapshot(page, () => raise(page, [{ message: 'Second' }]));
    // Read right after the 50 ms snapshot; a replaced toast stays mounted well past it.
    const backToasts = await page.locator(`${TOAST}[data-front="false"]`).count();
    expect(backToasts, 'a back toast exists when the snapshot is taken (an empty list must not pass vacuously)').toBeGreaterThanOrEqual(1);
    expect(offenders, 'elements with a non-identity transform 50 ms after the second toast').toEqual([]);
  });

  test('HC-TOAST-003b: dismissing the toasts leaves no transform', async ({ page }) => {
    await openInbox(page, VIEWPORT);
    if (PREVIEW) {
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await injectFixture(page, [
        { front: true, removed: true }, // removed front toast
        { front: false, removed: true }, // removed back toast
      ]);
      const transforms = await page.locator(TOAST).evaluateAll((els) => els.map((el) => getComputedStyle(el).transform));
      expect(
        transforms.filter((t) => !IDENTITY_TRANSFORM.test(t)),
        `fixture li transforms (removed front, removed back): ${transforms}`
      ).toEqual([]);
      return;
    }
    await raise(page, [{ message: 'First' }, { message: 'Second' }]);
    await waitForSettledToasts(page, 2);
    const offenders = await reducedMotionSnapshot(page, () => dismissAll(page));
    // sonner keeps a removed li mounted for 200 ms (TIME_BEFORE_UNMOUNT), so it is still counted just after the 50 ms snapshot.
    const removedToasts = await page.locator(`${TOAST}[data-removed="true"]`).count();
    expect(removedToasts, 'a removed toast exists when the snapshot is taken (an empty list must not pass vacuously)').toBeGreaterThanOrEqual(1);
    expect(offenders, 'elements with a non-identity transform 50 ms after the dismissal').toEqual([]);
  });

  test('HC-TOAST-003c: a still toast behind a plain toast shows nothing', async ({ page }) => {
    await openInbox(page, VIEWPORT);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    if (PREVIEW) {
      await injectFixture(page, [
        { front: true, removed: false },
        { front: false, removed: false },
      ]);
      const back = await page.locator(`${TOAST}[data-front="false"]`).evaluate((el) => {
        const style = getComputedStyle(el);
        return { transform: style.transform, bottom: style.bottom };
      });
      expect(back, 'fixture back li').toEqual({ transform: 'none', bottom: '0px' });
      return;
    }
    await raise(page, [{ message: 'Appointment on 12 March', still: true }]);
    await waitForSettledToasts(page, 1);
    await raise(page, [{ message: 'Plain follow-up' }]);
    await waitForSettledToasts(page, 2);
    const report = await page.evaluate(() => {
      const back = document.querySelector('[data-sonner-toast][data-front="false"]') as HTMLElement;
      const front = document.querySelector('[data-sonner-toast][data-front="true"]') as HTMLElement;
      const text = back.querySelector('[data-t0]') as HTMLElement;
      const textRect = text.getBoundingClientRect();
      const frontRect = front.getBoundingClientRect();
      const points: Array<[number, number]> = [
        [textRect.left + textRect.width / 2, textRect.top + textRect.height / 2],
        [textRect.left + 2, textRect.top + 2],
        [textRect.right - 2, textRect.top + 2],
        [textRect.left + 2, textRect.bottom - 2],
        [textRect.right - 2, textRect.bottom - 2],
      ];
      const exposed = points
        .map(([x, y]) => ({ x, y, hit: document.elementFromPoint(x, y) }))
        .filter(({ hit }) => !hit || !front.contains(hit))
        .map(({ x, y, hit }) => `(${x.toFixed(1)}, ${y.toFixed(1)}) -> ${hit ? hit.tagName.toLowerCase() : 'null'}`);
      const inside =
        textRect.left >= frontRect.left &&
        textRect.right <= frontRect.right &&
        textRect.top >= frontRect.top &&
        textRect.bottom <= frontRect.bottom;
      return { exposed, inside, textRect: JSON.stringify(textRect), frontRect: JSON.stringify(frontRect) };
    });
    expect(report.exposed, 'points of the still back toast text not covered by the front toast').toEqual([]);
    expect(report.inside, `text ${report.textRect} inside front ${report.frontRect}`).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// HC-TOAST-004: both sides of sonner's 600 px phone breakpoint.
// ---------------------------------------------------------------------------
test.describe('HC-TOAST-004 the phone breakpoint', () => {
  async function toasterAt(page: Page, width: number): Promise<ListState> {
    await openInbox(page, { width, height: width < 600 ? 844 : 800 });
    if (PREVIEW) {
      await injectFixture(page, [{ front: true, removed: false }]);
    } else {
      await raise(page, [{ message: 'Saved' }]);
      await waitForSettledToasts(page, 1);
    }
    return listState(page);
  }

  for (const width of [390, 600]) {
    test(`HC-TOAST-004: ${width} px keeps sonner's phone layout`, async ({ page }) => {
      const state = await toasterAt(page, width);
      expect(state.transform).toBe('none');
      expect(state.leftCss).toBe('16px');
      expect(state.rightCss).toBe('16px');
    });
  }

  test('HC-TOAST-004: 601 px centres the list without a transform', async ({ page }) => {
    const state = await toasterAt(page, 601);
    expect(state.transform, 'the list transform').toBe('none');
    expect(
      Math.abs(state.centreOffset),
      `list centre vs clientWidth/2 (left ${state.left}, width ${state.width})`
    ).toBeLessThanOrEqual(1);
  });
});
