/**
 * TOAST-TIMER-TEARDOWN (folds SONNER-TEARDOWN-FLAKE): pins the shared-harness
 * contract that no toast is left in sonner's module-level store when a test
 * ends.
 *
 * Two CI runs recorded vitest "Unhandled error: ReferenceError: window is not
 * defined" thrown from a sonner timer after jsdom teardown with every test
 * green (queue.md :748 in #507 at a4ebe8bf, and :669 in #465 run 41495977227).
 * The mechanism, read on node_modules/sonner/dist/index.mjs@2.0.8: a dismissal
 * arms a bare `setTimeout(() => removeToast(toast), TIME_BEFORE_UNMOUNT)` —
 * 200 ms — inside deleteToast (:634-636), and the store subscribers arm more
 * bare `setTimeout`s wrapping `ReactDOM.flushSync` (:943-947, :951-972, :1032)
 * plus a `requestAnimationFrame` delete flag (:1023). None is cancelled when
 * the Toaster unmounts, so whichever survives past RTL cleanup fires into a
 * deleted `window`. The fix lives in src/__tests__/setup.ts: an afterEach that
 * dismisses any queued toast plus an afterAll that outwaits the unmount timer.
 *
 * HC-TTD-001a/001b (and 002a/002b) are ORDERED PAIRS by design: the first
 * deliberately leaves a live toast so the second can observe the shared
 * teardown clearing it. Do not reorder, merge, or give the "a" tests their
 * own dismiss — the coupling is the thing under test.
 */
import { describe, expect, it } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { toast } from 'sonner';
import { AppToaster, notify } from '@/components/ui/toast';

describe('toast teardown (TOAST-TIMER-TEARDOWN)', () => {
  it("HC-TTD-001a: a toast left live in the DOM stays in sonner's queue across the boundary", async () => {
    render(<AppToaster />);

    act(() => {
      notify({ message: 'Teardown probe' });
    });

    // Wait out sonner's 0-tick subscriber flush so the toast is really mounted.
    const status = await screen.findByRole('status');
    expect(status.closest('[data-sonner-toast]')).not.toBeNull();
    expect(toast.getToasts().length).toBeGreaterThan(0);
    // Deliberately no dismiss — 001b asserts the shared teardown clears it.
  });

  it('HC-TTD-001b: the shared teardown dismisses it — getToasts() is empty', () => {
    expect(toast.getToasts()).toHaveLength(0);
  });

  it("HC-TTD-002a: a still toast left live stays in sonner's queue across the boundary", async () => {
    render(<AppToaster />);

    act(() => {
      notify({ still: true, message: 'Value 14.2' });
    });

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent('Value 14.2');
    expect(status.closest('[data-sonner-toast]')).not.toBeNull();
    expect(toast.getToasts().length).toBeGreaterThan(0);
    // Deliberately no dismiss — 002b asserts the shared teardown clears it.
  });

  it('HC-TTD-002b: the shared teardown dismisses the still toast — getToasts() is empty', () => {
    expect(toast.getToasts()).toHaveLength(0);
  });
});
