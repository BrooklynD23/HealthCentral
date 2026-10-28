/**
 * VITEST-TZ-PIN: the vitest process runs in the zone the config pins.
 * A worker thread ignores a process.env.TZ write, so the config sets the zone
 * on the main process before the pool starts. HC-VTZ-001.
 */
import { describe, it, expect } from 'vitest';

const PINNED_ZONE = process.env.VITEST_TZ ?? 'America/New_York';

describe('vitest time zone pin', () => {
  it('HC-VTZ-001: the vitest process runs in the pinned zone', () => {
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe(PINNED_ZONE);
    if (process.env.VITEST_TZ === undefined) {
      // 2026-03-05 is EST (UTC-5) before DST starts on 2026-03-08.
      expect(new Date('2026-03-05T12:00:00Z').getTimezoneOffset()).toBe(300);
    }
  });
});
