/**
 * SAFETY-MODE-TOGGLE: the stricter safety mode switch in the top bar (HC-SMT-001..004, 006).
 * HC-SMT-005 is the real-backend spec, e2e/safety-mode.spec.ts.
 *
 * The network seam (@/services/api apiGet/apiPatch) is mocked by a small fake server that
 * remembers the value, so the PATCH answers differently from one call to the next. The
 * QueryClient is real; the toast is the real AppToaster.
 *
 * What these tests would not notice:
 * - whether the real route returns this shape or stores the flag (HC-SMT-005 reads the real
 *   backend; the route's own tests live in src/backend/tests);
 * - a screen that keeps an AI explanation in component state across the switch (the
 *   invalidations are checked on the cache, not on every screen that reads it);
 * - an invalidation of a key that no screen reads any more: the three keys are the ones the
 *   services use today, copied here by hand, so a renamed key in a service passes this file;
 * - header geometry (no clipping, the fixed four lines): jsdom has no layout, and HC-SMT-005 and
 *   HC-UISH-006 measure it in a browser;
 * - the 599 mock answer for a PATCH sent on page load: only the e2e GATE G tests see it.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';
import { SafetyModeToggle } from '@/components/layout/SafetyModeToggle';
import { AppToaster } from '@/components/ui/toast';
import * as api from '@/services/api';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));

const PATH = '/assistant/safety-mode';
const KEY = ['assistant', 'safety-mode'];
const LOAD_TOAST = "Couldn't load the stricter safety mode setting.";
const CHANGE_TOAST = "Couldn't change the stricter safety mode setting.";
const NOTE =
  "On: AI explanations of a single result need more verified support, and values you haven't checked get no explanation. The standard safety checks always run.";
const LONG_TEXT =
  'Asclexis checks every answer for medical advice and against your own records. These checks are always on and cannot be turned off. This switch turns on a stricter mode for this profile. It never turns the standard checks off.';

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

/** A server that remembers the flag: a PATCH changes what the next GET returns. */
function fakeServer(initial: boolean) {
  const server = { value: initial, patchGate: null as Deferred<void> | null };
  vi.mocked(api.apiGet).mockImplementation(async () => ({ strict_safety_mode: server.value }));
  vi.mocked(api.apiPatch).mockImplementation(async (_path: string, body: unknown) => {
    if (server.patchGate) await server.patchGate.promise;
    server.value = (body as { strict_safety_mode: boolean }).strict_safety_mode;
    return { strict_safety_mode: server.value };
  });
  return server;
}

function renderToggle() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <SafetyModeToggle />
      <AppToaster />
    </QueryClientProvider>
  );
  return queryClient;
}

function getSwitch() {
  return screen.getByRole('switch', { name: 'Stricter safety mode' });
}

/** Waits until the GET has landed and the switch can be used. */
async function knownSwitch() {
  await waitFor(() => expect(getSwitch()).toBeEnabled());
  return getSwitch();
}

async function queryStatus(queryClient: QueryClient) {
  await waitFor(() => expect(queryClient.getQueryState(KEY)?.fetchStatus).toBe('idle'));
  return queryClient.getQueryState(KEY)?.status;
}

beforeEach(() => {
  vi.mocked(api.apiGet).mockReset();
  vi.mocked(api.apiPatch).mockReset();
});

afterEach(() => {
  cleanup();
  act(() => {
    toast.dismiss();
  });
});

describe('HC-SMT-001 the switch shows the server value', () => {
  it.each([
    [true, 'true'],
    [false, 'false'],
  ])('server %s renders aria-checked %s on an enabled switch', async (serverValue, expected) => {
    fakeServer(serverValue);
    renderToggle();
    const toggle = await knownSwitch();
    expect(toggle).toHaveAttribute('aria-checked', expected);
    expect(toggle).not.toHaveAttribute('aria-disabled');
    expect(api.apiGet).toHaveBeenCalledWith(PATH);
  });
});

describe('HC-SMT-002 a click sends one PATCH and invalidates what depends on the mode', () => {
  it('sends the inverted value once, ignores a second click while pending, and invalidates three groups', async () => {
    const user = userEvent.setup();
    const server = fakeServer(false);
    const queryClient = renderToggle();
    const seeded = {
      interpretation: ['interpretations', 'obs-1'],
      recent: ['interpretations', 'recent', 5],
      trend: ['observations', 'trends', 'glucose', undefined, undefined],
      unrelated: ['observations', 'list'],
    };
    for (const key of Object.values(seeded)) queryClient.setQueryData(key, { seeded: true });
    const isInvalidated = (key: readonly unknown[]) => queryClient.getQueryState(key)?.isInvalidated;
    // The seeds start clean, so a later "true" can only come from the switch.
    for (const key of Object.values(seeded)) expect(isInvalidated(key)).toBe(false);

    const toggle = await knownSwitch();
    server.patchGate = deferred<void>();
    await user.click(toggle);

    // Optimistic: the new value shows before the server has answered.
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    expect(api.apiPatch).toHaveBeenCalledTimes(1);
    expect(api.apiPatch).toHaveBeenLastCalledWith(PATH, { strict_safety_mode: true });

    // A second click while the first is pending sends nothing and does not flip it back.
    await user.click(toggle);
    expect(api.apiPatch).toHaveBeenCalledTimes(1);
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    for (const key of Object.values(seeded)) expect(isInvalidated(key)).toBe(false);

    await act(async () => {
      server.patchGate!.resolve();
    });
    await waitFor(() => expect(isInvalidated(seeded.interpretation)).toBe(true));
    expect(isInvalidated(seeded.recent)).toBe(true);
    expect(isInvalidated(seeded.trend)).toBe(true);
    expect(isInvalidated(seeded.unrelated)).toBe(false);
    expect(queryClient.getQueryData(KEY)).toEqual({ strict_safety_mode: true });
    expect(toggle).toHaveAttribute('aria-checked', 'true');

    // The next click is a new request with the other value: the mock does not answer both alike.
    server.patchGate = null;
    await user.click(toggle);
    await waitFor(() => expect(api.apiPatch).toHaveBeenCalledTimes(2));
    expect(api.apiPatch).toHaveBeenLastCalledWith(PATH, { strict_safety_mode: false });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'));
    expect(server.value).toBe(false);
  });
});

describe('HC-SMT-003 a failed PATCH restores the previous state', () => {
  it('rolls the switch back, shows the exact toast, and invalidates nothing', async () => {
    const user = userEvent.setup();
    const server = fakeServer(false);
    const queryClient = renderToggle();
    queryClient.setQueryData(['interpretations', 'obs-1'], { seeded: true });

    const toggle = await knownSwitch();
    server.patchGate = deferred<void>();
    await user.click(toggle);
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));

    await act(async () => {
      server.patchGate!.reject(new Error('503'));
    });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'));
    expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
    expect(screen.queryAllByText(CHANGE_TOAST)).toHaveLength(1);
    expect(queryClient.getQueryData(KEY)).toEqual({ strict_safety_mode: false });
    expect(queryClient.getQueryState(['interpretations', 'obs-1'])?.isInvalidated).toBe(false);
    expect(server.value).toBe(false);
  });

  it('restores an ON switch to ON when the PATCH to turn it off fails', async () => {
    const user = userEvent.setup();
    const server = fakeServer(true);
    renderToggle();

    const toggle = await knownSwitch();
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    server.patchGate = deferred<void>();
    await user.click(toggle);
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'));
    expect(api.apiPatch).toHaveBeenLastCalledWith(PATH, { strict_safety_mode: false });

    await act(async () => {
      server.patchGate!.reject(new Error('503'));
    });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
  });
});

describe('HC-SMT-004 name, value and note', () => {
  it('has the accessible name, the value, the stage-1 note and the long popover text', async () => {
    const user = userEvent.setup();
    fakeServer(true);
    const { container } = render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <SafetyModeToggle />
      </QueryClientProvider>
    );
    const toggle = await knownSwitch();
    expect(toggle).toHaveAccessibleName('Stricter safety mode');
    expect(toggle).toHaveAttribute('role', 'switch');
    expect(toggle).toHaveAttribute('aria-checked', 'true');

    // Later rows edit this assertion (one added sentence each); keep it verbatim, not a regex.
    const note = container.querySelector('[data-safety-toggle-note]');
    expect(note).not.toBeNull();
    expect(note?.textContent).toBe(NOTE);
    expect(toggle).toHaveAccessibleDescription(NOTE);

    // The words ON and OFF and "Safety Mode" never appear in the switch row or the note (case-sensitive).
    const bannerText = container.textContent ?? '';
    expect(bannerText).not.toMatch(/Safety Mode/);
    expect(bannerText).not.toMatch(/\b(ON|OFF)\b/);

    await user.click(screen.getByRole('button', { name: 'About the stricter safety mode' }));
    const popover = await screen.findByRole('dialog', { name: 'About the stricter safety mode' });
    expect(popover.querySelector('[data-safety-toggle-popover-note]')?.textContent).toBe(NOTE);
    expect(popover.querySelector('[data-safety-toggle-popover]')?.textContent).toBe(LONG_TEXT);
    expect(within(popover).queryByText(/Not available yet/)).toBeNull();
  });
});

describe('HC-SMT-006 the unknown state is disabled and sends nothing', () => {
  it('while the GET is pending: disabled, off, busy, no PATCH, note unchanged', async () => {
    const user = userEvent.setup();
    const gate = deferred<unknown>();
    vi.mocked(api.apiGet).mockImplementation(() => gate.promise);
    vi.mocked(api.apiPatch).mockResolvedValue({ strict_safety_mode: true });
    const { container } = render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <SafetyModeToggle />
      </QueryClientProvider>
    );
    const noteBefore = container.querySelector('[data-safety-toggle-note]')?.textContent;

    const toggle = getSwitch();
    expect(toggle).toBeDisabled();
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(toggle).toHaveAttribute('aria-busy', 'true');
    await user.click(toggle);
    expect(api.apiPatch).not.toHaveBeenCalled();
    expect(container.querySelector('[data-safety-toggle-note]')?.textContent).toBe(noteBefore);

    await act(async () => {
      gate.resolve({ strict_safety_mode: true });
    });
    await waitFor(() => expect(getSwitch()).toBeEnabled());
    expect(getSwitch()).toHaveAttribute('aria-checked', 'true');
    expect(getSwitch()).not.toHaveAttribute('aria-busy', 'true');
  });

  it('when the GET fails: disabled, off, not busy, one toast, then recovers on a good refetch', async () => {
    const user = userEvent.setup();
    let fail = true;
    vi.mocked(api.apiGet).mockImplementation(async () => {
      if (fail) throw new Error('503');
      return { strict_safety_mode: true };
    });
    vi.mocked(api.apiPatch).mockResolvedValue({ strict_safety_mode: true });
    const queryClient = renderToggle();

    expect(await screen.findByText(LOAD_TOAST)).toBeInTheDocument();
    expect(await queryStatus(queryClient)).toBe('error');
    const toggle = getSwitch();
    expect(toggle).toBeDisabled();
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(toggle).not.toHaveAttribute('aria-busy', 'true');
    await user.click(toggle);
    expect(api.apiPatch).not.toHaveBeenCalled();

    // A repeat failed refetch must not stack a second toast.
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: KEY });
    });
    expect(await queryStatus(queryClient)).toBe('error');
    expect(screen.queryAllByText(LOAD_TOAST)).toHaveLength(1);
    expect(getSwitch()).toBeDisabled();

    fail = false;
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: KEY });
    });
    await waitFor(() => expect(getSwitch()).toBeEnabled());
    expect(getSwitch()).toHaveAttribute('aria-checked', 'true');
  });

  it.each([
    ['an empty body', {}],
    ['a string instead of a boolean', { strict_safety_mode: 'true' }],
    ['null', { strict_safety_mode: null }],
    ['a number', { strict_safety_mode: 1 }],
  ])('when the body has no boolean (%s): disabled, off, no PATCH', async (_label, body) => {
    const user = userEvent.setup();
    vi.mocked(api.apiGet).mockResolvedValue(body);
    vi.mocked(api.apiPatch).mockResolvedValue({ strict_safety_mode: true });
    const queryClient = renderToggle();

    expect(await queryStatus(queryClient)).toBe('success');
    const toggle = getSwitch();
    expect(toggle).toBeDisabled();
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(toggle).not.toHaveAttribute('aria-busy', 'true');
    await user.click(toggle);
    expect(api.apiPatch).not.toHaveBeenCalled();
  });
});
