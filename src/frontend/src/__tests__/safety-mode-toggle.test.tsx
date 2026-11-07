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
 * - a reset or invalidation of a key that no screen reads any more: the three keys are the ones the
 *   services use today, copied here by hand, so a renamed key in a service passes this file;
 * - the real 409 body or the real refusal screen: the reader in HC-SMT-002 is a stand-in that shows
 *   its data or its error, so a screen that ignores the error (the bug this test pins) is only
 *   caught for a screen that reads the cache the way the stand-in does;
 * - header geometry (no clipping, the fixed four lines): jsdom has no layout, and HC-SMT-005 and
 *   HC-UISH-006 measure it in a browser;
 * - the 599 mock answer for a PATCH sent on page load: only the e2e GATE G tests see it.
 */

import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
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
  "On: AI explanations of a single result need more verified support, and values you haven't checked get no explanation. Chat answers always show their sources. The standard safety checks always run.";
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
  const server = {
    value: initial,
    patchGate: null as Deferred<void> | null,
    /** The PATCH commits the flag and then answers 500, as update_safety_mode does when the audit commit fails. */
    failAfterCommit: false,
  };
  vi.mocked(api.apiGet).mockImplementation(async () => ({ strict_safety_mode: server.value }));
  vi.mocked(api.apiPatch).mockImplementation(async (_path: string, body: unknown) => {
    if (server.patchGate) await server.patchGate.promise;
    server.value = (body as { strict_safety_mode: boolean }).strict_safety_mode;
    if (server.failAfterCommit) throw new Error('500');
    return { strict_safety_mode: server.value };
  });
  return server;
}

function renderToggle(extra?: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <SafetyModeToggle />
      <AppToaster />
      {extra}
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

describe('HC-SMT-002 a click sends one PATCH and drops what depends on the mode', () => {
  it('sends the inverted value once, ignores a second click while pending, and refreshes three groups', async () => {
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
    const hasData = (key: readonly unknown[]) => queryClient.getQueryData(key) !== undefined;
    // The seeds start clean, so a later change can only come from the switch.
    for (const key of Object.values(seeded)) {
      expect(isInvalidated(key)).toBe(false);
      expect(hasData(key)).toBe(true);
    }

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
    for (const key of Object.values(seeded)) {
      expect(isInvalidated(key)).toBe(false);
      expect(hasData(key)).toBe(true);
    }

    await act(async () => {
      server.patchGate!.resolve();
    });
    // Explanations are reset (their data is dropped, not kept for a failed refetch); trends are invalidated.
    await waitFor(() => expect(hasData(seeded.interpretation)).toBe(false));
    expect(hasData(seeded.recent)).toBe(false);
    expect(isInvalidated(seeded.trend)).toBe(true);
    expect(hasData(seeded.trend)).toBe(true);
    expect(isInvalidated(seeded.unrelated)).toBe(false);
    expect(hasData(seeded.unrelated)).toBe(true);
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

describe('HC-SMT-002b an explanation written under the old mode does not outlive the switch', () => {
  /** A stand-in for a screen that shows the explanation it has, and a refusal when it has none. */
  function ExplanationReader({ answer }: { answer: () => Promise<{ text: string }> }) {
    const query = useQuery({ queryKey: ['interpretations', 'obs-1'], queryFn: answer });
    if (query.data) return <p data-testid="explanation">{query.data.text}</p>;
    if (query.isError) return <p data-testid="explanation">refused</p>;
    return <p data-testid="explanation">loading</p>;
  }

  it('turning the mode on removes the explanation when the refetch is refused with 409', async () => {
    const user = userEvent.setup();
    const server = fakeServer(false);
    let strict = false;
    const answer = vi.fn(async () => {
      if (strict) throw new Error('409 unverified value in strict mode');
      return { text: 'EXPLANATION WRITTEN UNDER OFF' };
    });
    renderToggle(<ExplanationReader answer={answer} />);

    expect(await screen.findByText('EXPLANATION WRITTEN UNDER OFF')).toBeInTheDocument();
    const toggle = await knownSwitch();
    // The backend refuses once the flag is on: the fake server flips both together.
    strict = true;
    server.patchGate = null;
    await user.click(toggle);

    await waitFor(() => expect(screen.getByTestId('explanation')).toHaveTextContent('refused'));
    expect(screen.queryByText('EXPLANATION WRITTEN UNDER OFF')).toBeNull();
    expect(answer).toHaveBeenCalledTimes(2);
  });
});

describe('HC-SMT-002c a PATCH that settles after the cache was cleared writes nothing', () => {
  it.each([
    ['succeeds', false],
    ['fails', true],
  ])('a PATCH that %s after queryClient.clear() leaves the cache empty', async (_label, reject) => {
    const user = userEvent.setup();
    const server = fakeServer(false);
    const queryClient = renderToggle();
    const toggle = await knownSwitch();
    server.patchGate = deferred<void>();
    await user.click(toggle);
    await waitFor(() => expect(api.apiPatch).toHaveBeenCalledTimes(1));

    // The lock flow clears the cache; whatever is read afterwards must come from the new profile's GET.
    vi.mocked(api.apiGet).mockImplementation(() => new Promise(() => {}));
    act(() => {
      queryClient.clear();
    });
    await act(async () => {
      if (reject) server.patchGate!.reject(new Error('503'));
      else server.patchGate!.resolve();
    });
    // A failure still tells the person; only the cache write is skipped.
    if (reject) expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
    await act(async () => {});
    if (!reject) expect(screen.queryByText(CHANGE_TOAST)).toBeNull();
    expect(api.apiPatch).toHaveBeenCalledTimes(1);
    expect(queryClient.getQueryData(KEY)).toBeUndefined();
  });

  it('a read-back that lands after queryClient.clear() leaves the cache empty', async () => {
    const user = userEvent.setup();
    const server = fakeServer(false);
    const queryClient = renderToggle();
    const toggle = await knownSwitch();

    // Unlike the case above, the cache is cleared after the PATCH has failed, with the read-back already out.
    const readBack = deferred<unknown>();
    vi.mocked(api.apiGet).mockImplementation(() => new Promise(() => {}));
    vi.mocked(api.apiGet).mockImplementationOnce(() => readBack.promise);
    server.patchGate = deferred<void>();
    await user.click(toggle);
    await waitFor(() => expect(api.apiPatch).toHaveBeenCalledTimes(1));
    await act(async () => {
      server.patchGate!.reject(new Error('503'));
    });
    expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
    await waitFor(() => expect(api.apiGet).toHaveBeenCalledTimes(2));

    act(() => {
      queryClient.clear();
    });
    await act(async () => {
      readBack.resolve({ strict_safety_mode: true });
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // The old profile's value must not be handed to the next one.
    expect(queryClient.getQueryData(KEY)).toBeUndefined();
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

    // The read-back after a failure is held open, so only the rollback itself can restore the old value.
    vi.mocked(api.apiGet).mockImplementation(() => new Promise(() => {}));
    await act(async () => {
      server.patchGate!.reject(new Error('503'));
    });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'));
    expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
    expect(screen.queryAllByText(CHANGE_TOAST)).toHaveLength(1);
    expect(queryClient.getQueryData(KEY)).toEqual({ strict_safety_mode: false });
    expect(queryClient.getQueryState(['interpretations', 'obs-1'])?.isInvalidated).toBe(false);
    expect(queryClient.getQueryData(['interpretations', 'obs-1'])).toEqual({ seeded: true });
    expect(server.value).toBe(false);

    // The switch is not stuck after a failure: the next click is a new request with the new value.
    vi.mocked(api.apiGet).mockImplementation(async () => ({ strict_safety_mode: server.value }));
    server.patchGate = null;
    await user.click(toggle);
    await waitFor(() => expect(api.apiPatch).toHaveBeenCalledTimes(2));
    expect(api.apiPatch).toHaveBeenLastCalledWith(PATH, { strict_safety_mode: true });
    await waitFor(() => expect(server.value).toBe(true));
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
  });

  it('follows the server when the PATCH committed and then failed (audit commit error)', async () => {
    const user = userEvent.setup();
    const server = fakeServer(false);
    server.failAfterCommit = true;
    const queryClient = renderToggle();
    queryClient.setQueryData(['interpretations', 'obs-1'], { seeded: true });
    queryClient.setQueryData(['observations', 'trends', 'glucose', undefined, undefined], { seeded: true });

    const toggle = await knownSwitch();
    expect(api.apiGet).toHaveBeenCalledTimes(1);
    await user.click(toggle);

    expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
    // The server kept the new value, so the switch reads it back instead of showing the old snapshot.
    expect(server.value).toBe(true);
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    expect(api.apiGet).toHaveBeenCalledTimes(2);
    expect(toggle).toBeEnabled();
    // The mode did change, so what was written under the old mode goes, exactly as after a clean PATCH.
    await waitFor(() => expect(queryClient.getQueryData(['interpretations', 'obs-1'])).toBeUndefined());
    expect(
      queryClient.getQueryState(['observations', 'trends', 'glucose', undefined, undefined])?.isInvalidated
    ).toBe(true);
  });

  it('keeps the explanations when the read-back confirms the old value', async () => {
    const user = userEvent.setup();
    const server = fakeServer(false);
    vi.mocked(api.apiPatch).mockRejectedValue(new Error('503'));
    const queryClient = renderToggle();
    queryClient.setQueryData(['interpretations', 'obs-1'], { seeded: true });
    queryClient.setQueryData(['observations', 'trends', 'glucose', undefined, undefined], { seeded: true });

    const toggle = await knownSwitch();
    await user.click(toggle);
    expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
    await waitFor(() => expect(api.apiGet).toHaveBeenCalledTimes(2));
    await act(async () => {});
    // Nothing changed on the server, so nothing shown under the old mode is stale.
    expect(server.value).toBe(false);
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(queryClient.getQueryData(['interpretations', 'obs-1'])).toEqual({ seeded: true });
    expect(
      queryClient.getQueryState(['observations', 'trends', 'glucose', undefined, undefined])?.isInvalidated
    ).toBe(false);
  });

  it('with the backend down: one change toast, no load toast, a usable switch, explanations reset', async () => {
    const user = userEvent.setup();
    fakeServer(false);
    const queryClient = renderToggle();
    queryClient.setQueryData(['interpretations', 'obs-1'], { seeded: true });

    const toggle = await knownSwitch();
    // The PATCH and the read-back both fail, so the value cannot be confirmed: drop what depends on it.
    vi.mocked(api.apiPatch).mockRejectedValue(new Error('down'));
    vi.mocked(api.apiGet).mockRejectedValue(new Error('down'));
    await user.click(toggle);

    expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
    await waitFor(() => expect(api.apiGet).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(queryClient.getQueryData(['interpretations', 'obs-1'])).toBeUndefined());
    await act(async () => {});
    expect(screen.queryAllByText(CHANGE_TOAST)).toHaveLength(1);
    expect(screen.queryByText(LOAD_TOAST)).toBeNull();
    expect(toggle).toBeEnabled();
    expect(toggle).toHaveAttribute('aria-checked', 'false');
  });

  it('a read-back that lands during the next click does not overwrite the new choice', async () => {
    const user = userEvent.setup();
    const server = fakeServer(false);
    renderToggle();

    const toggle = await knownSwitch();
    const readBack = deferred<unknown>();
    vi.mocked(api.apiGet).mockImplementation(() => readBack.promise);
    const first = deferred<void>();
    server.patchGate = first;
    await user.click(toggle);
    await act(async () => {
      first.reject(new Error('503'));
    });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'));

    const second = deferred<void>();
    server.patchGate = second;
    await user.click(toggle);
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    expect(api.apiPatch).toHaveBeenCalledTimes(2);

    await act(async () => {
      readBack.resolve({ strict_safety_mode: false });
      // The read-back's handlers run a few microtasks later; let a whole task pass before looking.
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    await act(async () => {
      second.resolve();
    });
    await waitFor(() => expect(server.value).toBe(true));
    expect(toggle).toHaveAttribute('aria-checked', 'true');
  });

  it('a read-back with no boolean changes nothing on the switch and still drops the explanations', async () => {
    const user = userEvent.setup();
    fakeServer(false);
    const queryClient = renderToggle();
    queryClient.setQueryData(['interpretations', 'obs-1'], { seeded: true });

    const toggle = await knownSwitch();
    vi.mocked(api.apiPatch).mockRejectedValue(new Error('503'));
    vi.mocked(api.apiGet).mockImplementation(async () => ({}));
    await user.click(toggle);

    expect(await screen.findByText(CHANGE_TOAST)).toBeInTheDocument();
    await waitFor(() => expect(api.apiGet).toHaveBeenCalledTimes(2));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // The value cannot be told, so what was written under the old mode goes.
    expect(queryClient.getQueryData(['interpretations', 'obs-1'])).toBeUndefined();
    // The switch keeps its rollback value and stays usable: {} never became the cached value.
    expect(queryClient.getQueryData(KEY)).toEqual({ strict_safety_mode: false });
    expect(toggle).toBeEnabled();
    expect(toggle).toHaveAttribute('aria-checked', 'false');
  });

  it.each([false, true])(
    'a read-back that lands after the next click settled does not overwrite it (start %s)',
    async (start) => {
      const user = userEvent.setup();
      const server = fakeServer(start);
      const queryClient = renderToggle();
      const shown = (value: boolean) => String(value);

      const toggle = await knownSwitch();
      const readBack = deferred<unknown>();
      vi.mocked(api.apiGet).mockImplementation(() => readBack.promise);
      // First click: the PATCH fails uncommitted, the rollback runs, the read-back is held.
      const first = deferred<void>();
      server.patchGate = first;
      await user.click(toggle);
      await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', shown(!start)));
      await act(async () => {
        first.reject(new Error('503'));
      });
      await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', shown(start)));
      await waitFor(() => expect(api.apiGet).toHaveBeenCalledTimes(2));

      // Second click, while the first read-back is still out: this PATCH settles in full (onSettled has run).
      const second = deferred<void>();
      server.patchGate = second;
      await user.click(toggle);
      await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', shown(!start)));
      expect(api.apiPatch).toHaveBeenCalledTimes(2);
      await act(async () => {
        second.resolve();
      });
      await waitFor(() => expect(server.value).toBe(!start));
      await waitFor(() => expect(queryClient.getQueryData(KEY)).toEqual({ strict_safety_mode: !start }));
      expect(toggle).toHaveAttribute('aria-checked', shown(!start));

      // Only now does the older read-back land, with the value from before the second click.
      await act(async () => {
        readBack.resolve({ strict_safety_mode: start });
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
      expect(toggle).toHaveAttribute('aria-checked', shown(!start));
      expect(queryClient.getQueryData(KEY)).toEqual({ strict_safety_mode: !start });
      expect(server.value).toBe(!start);
    }
  );

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

    // A repeat failed refetch must not stack a second toast. The refetch is held open so the
    // pending state is committed (aria-busy returns) before it fails again, as a real window-focus
    // refetch does: with no data the query goes back to pending, then to error.
    const retry = deferred<never>();
    vi.mocked(api.apiGet).mockImplementation(() => retry.promise);
    act(() => {
      void queryClient.refetchQueries({ queryKey: KEY });
    });
    await waitFor(() => expect(getSwitch()).toHaveAttribute('aria-busy', 'true'));
    await act(async () => {
      retry.reject(new Error('503'));
    });
    await waitFor(() => expect(getSwitch()).not.toHaveAttribute('aria-busy', 'true'));
    expect(await queryStatus(queryClient)).toBe('error');
    expect(screen.queryAllByText(LOAD_TOAST)).toHaveLength(1);
    expect(getSwitch()).toBeDisabled();
    vi.mocked(api.apiGet).mockImplementation(async () => {
      if (fail) throw new Error('503');
      return { strict_safety_mode: true };
    });

    fail = false;
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: KEY });
    });
    await waitFor(() => expect(getSwitch()).toBeEnabled());
    expect(getSwitch()).toHaveAttribute('aria-checked', 'true');
  });

  it('a failed background refetch after a good load keeps the last value usable and toasts once', async () => {
    const user = userEvent.setup();
    let fail = false;
    vi.mocked(api.apiGet).mockImplementation(async () => {
      if (fail) throw new Error('503');
      return { strict_safety_mode: true };
    });
    vi.mocked(api.apiPatch).mockResolvedValue({ strict_safety_mode: false });
    const queryClient = renderToggle();

    const toggle = await knownSwitch();
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByText(LOAD_TOAST)).toBeNull();

    fail = true;
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: KEY });
    });
    expect(await screen.findByText(LOAD_TOAST)).toBeInTheDocument();
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: KEY });
    });
    expect(screen.queryAllByText(LOAD_TOAST)).toHaveLength(1);
    // The last good value stays on screen and the switch still works: a stale value is not "unknown".
    expect(toggle).toBeEnabled();
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    await user.click(toggle);
    await waitFor(() => expect(api.apiPatch).toHaveBeenCalledTimes(1));
    expect(api.apiPatch).toHaveBeenLastCalledWith(PATH, { strict_safety_mode: false });
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
