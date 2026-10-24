/**
 * UI-MOTION (HC-UIMO-004): with the OS asking for reduced motion, /setup has
 * no element still moving 60 ms after load. ProfileSetup's item variants start
 * 20 px lower (`y: 20`); under reduced motion that offset must jump to rest
 * through MotionConfig, not glide in.
 */

import { test, expect } from '@playwright/test';

test.describe('UI-MOTION reduced motion', () => {
  test.use({ reducedMotion: 'reduce' });

  test('HC-UIMO-004: /setup has no non-identity transform 60 ms after load under reduced motion', async ({
    page,
  }) => {
    await page.goto('/setup');

    const moving = await page.evaluate(async () => {
      await new Promise((resolve) => setTimeout(resolve, 60));

      const isIdentity = (transform: string) => {
        if (transform === 'none') return true;
        const match = transform.match(/^matrix(3d)?\((.+)\)$/);
        if (!match) return false;
        const values = match[2].split(',').map((value) => parseFloat(value));
        const identity = match[1]
          ? [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
          : [1, 0, 0, 1, 0, 0];
        return (
          values.length === identity.length &&
          values.every((value, index) => Math.abs(value - identity[index]) < 1e-6)
        );
      };

      return Array.from(document.querySelectorAll('body *'))
        .filter((element) => !isIdentity(getComputedStyle(element).transform))
        .map((element) => {
          const label = element.getAttribute('data-testid') ?? element.className;
          return `${element.tagName.toLowerCase()} ${String(label)} ${getComputedStyle(element).transform}`;
        });
    });

    expect(moving).toEqual([]);
  });
});
