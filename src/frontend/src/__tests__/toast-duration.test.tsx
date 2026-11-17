/**
 * VERIFY-UNDO-UI: `notify` passes an optional `duration` to sonner. A toast without one gets none, so sonner's
 * default (4 s) stays. Blind spot: sonner is mocked, so how long it really keeps a toast is sonner's.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const { toastSpy } = vi.hoisted(() => ({ toastSpy: vi.fn() }));
vi.mock('sonner', () => ({ Toaster: () => null, toast: toastSpy }));

import { notify } from '@/components/ui/toast';

describe('HC-TOASTDUR-001: notify passes an optional duration through', () => {
  beforeEach(() => toastSpy.mockClear());

  it('a toast with a duration hands it to sonner', () => {
    notify({ message: 'Glucose is now marked as checked', duration: 10_000 });
    expect(toastSpy).toHaveBeenCalledTimes(1);
    expect(toastSpy.mock.calls[0][1]).toMatchObject({ duration: 10_000 });
  });

  it('a toast without one passes none, so sonner keeps its default', () => {
    notify({ message: 'Saved' });
    expect(toastSpy).toHaveBeenCalledTimes(1);
    expect(toastSpy.mock.calls[0][1].duration).toBeUndefined();
  });
});
