/**
 * UI-PRIM-OVERLAYS (HC-UIOV-001..008): Dialog, AlertDialog, Sheet, Popover.
 *
 * HC-UIOV-007 is the vitest half only. Its e2e stillnessProbe moved to UI-SHELL
 * (L0 ruling on PR #363). Each describe block names what its checks would miss.
 */

import { describe, it, expect, vi, beforeEach, afterEach, type MockInstance } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ElementType, ReactElement, ReactNode } from 'react';
import { LazyMotion, MotionConfig, domAnimation } from 'framer-motion';
import { Dialog } from '@/components/ui/Dialog';
import { AlertDialog } from '@/components/ui/AlertDialog';
import { Sheet } from '@/components/ui/Sheet';
import { Popover } from '@/components/ui/Popover';

// Records the props every `m.<tag>` element receives, so the framer props
// (initial, animate, exit, transition) can be asserted. Rendering is unchanged:
// the real framer-motion component still renders underneath.
const motionRecords = vi.hoisted(() => [] as Array<{ tag: string; props: Record<string, unknown> }>);

vi.mock('framer-motion', async (importOriginal) => {
  const React = await import('react');
  const actual = await importOriginal<typeof import('framer-motion')>();
  const wrapped = new Map<string, unknown>();
  const recordingM = new Proxy(
    {},
    {
      get(_target, tag) {
        if (typeof tag !== 'string') return undefined;
        if (!wrapped.has(tag)) {
          const Real = (actual.m as unknown as Record<string, ElementType>)[tag];
          wrapped.set(
            tag,
            React.forwardRef<unknown, Record<string, unknown>>((props, ref) => {
              motionRecords.push({ tag, props });
              return React.createElement(Real, { ...props, ref });
            })
          );
        }
        return wrapped.get(tag);
      },
    }
  );
  return { ...actual, m: recordingM };
});

type Kind = 'dialog' | 'alertdialog' | 'sheet' | 'popover';
type OverlayKind = Exclude<Kind, 'popover'>;

const KINDS: Kind[] = ['dialog', 'alertdialog', 'sheet', 'popover'];
const ROLE: Record<Kind, 'dialog' | 'alertdialog'> = {
  dialog: 'dialog',
  alertdialog: 'alertdialog',
  sheet: 'dialog',
  popover: 'dialog',
};
const OVERLAY_OPEN_EVENT = 'asclexis:overlay-open';
const TITLE_WARNING = /requires a `title` prop/;

const REDUCE_QUERY = '(prefers-reduced-motion: reduce)';
// Plan §3.2: the phone/desktop boundary is 1024 px (the sidebar appears at >= 1024).
const DESKTOP_QUERY = '(min-width: 1024px)';
const realMatchMedia = window.matchMedia;

/**
 * Answers only the two queries the primitives read. The match is exact-string, so a
 * primitive that queries another width (say 768 px) gets no match and fails the
 * desktop tests. It cannot see a different width such as 1025 px.
 */
function setMedia({ reducedMotion = false, desktop = false }: { reducedMotion?: boolean; desktop?: boolean }) {
  window.matchMedia = ((query: string) => ({
    matches: (reducedMotion && query === REDUCE_QUERY) || (desktop && query === DESKTOP_QUERY),
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

function setReducedMotion(reduce: boolean) {
  setMedia({ reducedMotion: reduce });
}

const realConsoleError = console.error.bind(console);
const titleWarnings: string[] = [];
let errorSpy: MockInstance | undefined;

beforeEach(() => {
  setReducedMotion(false);
  motionRecords.length = 0;
  titleWarnings.length = 0;
  // Calls through to the real console.error, so nothing else is hidden.
  errorSpy = vi.spyOn(console, 'error').mockImplementation((...args: unknown[]) => {
    if (typeof args[0] === 'string' && TITLE_WARNING.test(args[0])) titleWarnings.push(args[0]);
    realConsoleError(...args);
  });
});

afterEach(() => {
  // HC-UIOV-003: an overlay rendered without a title fails the test that rendered it.
  const leaked = [...titleWarnings];
  errorSpy?.mockRestore();
  window.matchMedia = realMatchMedia;
  expect(leaked, 'overlay rendered without a title').toEqual([]);
});

/**
 * The providers the app mounts (MotionProvider), with the DOM features loaded at once.
 * Without them `m.*` renders but no animation runs and AnimatePresence removes the
 * content at once, so the exit path (and focus return after it) never executes.
 */
function Providers({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      <MotionConfig reducedMotion="user">{children}</MotionConfig>
    </LazyMotion>
  );
}

function renderInProviders(ui: ReactElement) {
  return render(ui, { wrapper: Providers });
}

const TITLE: Record<OverlayKind, string> = {
  dialog: 'Lab details',
  alertdialog: 'Delete this profile?',
  sheet: 'More',
};
const POPOVER_LABEL = 'Potassium details';

function renderOverlay(kind: Kind, still = false, beside: ReactNode = null) {
  const trigger = <button type="button">{`Open ${kind}`}</button>;
  const body = (
    <>
      <p data-t0>Potassium 5.2 mmol/L</p>
      <button type="button">First action</button>
      <button type="button">Second action</button>
    </>
  );
  switch (kind) {
    case 'dialog':
      return renderInProviders(
        <>
          <Dialog trigger={trigger} title={TITLE.dialog} description="Read-only summary" still={still}>
            {body}
          </Dialog>
          {beside}
        </>
      );
    case 'alertdialog':
      return renderInProviders(
        <>
          <AlertDialog
            trigger={trigger}
            title={TITLE.alertdialog}
            description="This cannot be undone."
            still={still}
          >
            {body}
            <button type="button" data-alert-cancel>
              Cancel
            </button>
          </AlertDialog>
          {beside}
        </>
      );
    case 'sheet':
      return renderInProviders(
        <>
          <Sheet trigger={trigger} title={TITLE.sheet} description="Other pages" still={still}>
            {body}
          </Sheet>
          {beside}
        </>
      );
    case 'popover':
      return renderInProviders(
        <>
          <Popover trigger={trigger} label={POPOVER_LABEL} still={still}>
            {body}
          </Popover>
          {beside}
        </>
      );
  }
}

function renderWithoutTitle(kind: OverlayKind) {
  const trigger = <button type="button">{`Open ${kind}`}</button>;
  switch (kind) {
    case 'dialog':
      // @ts-expect-error title is required by the type; this render checks the runtime guard
      return renderInProviders(<Dialog trigger={trigger}>{<p>Body</p>}</Dialog>);
    case 'alertdialog':
      // @ts-expect-error title is required by the type; this render checks the runtime guard
      return renderInProviders(<AlertDialog trigger={trigger}>{<p>Body</p>}</AlertDialog>);
    case 'sheet':
      // @ts-expect-error title is required by the type; this render checks the runtime guard
      return renderInProviders(<Sheet trigger={trigger}>{<p>Body</p>}</Sheet>);
  }
}

function triggerOf(kind: Kind) {
  return screen.getByRole('button', { name: `Open ${kind}` });
}

/** The framer props of the last content element (role dialog or alertdialog) rendered. */
function contentMotion(role: 'dialog' | 'alertdialog'): Record<string, unknown> {
  const records = motionRecords.filter((r) => r.tag === 'div' && r.props.role === role);
  const last = records[records.length - 1];
  if (!last) throw new Error(`no motion element with role "${role}" was rendered`);
  return last.props;
}

/**
 * Walks from `from` up to and including document.body. Reports any opacity,
 * scale or translate. Radix Popper positions its wrapper with translate(), which is
 * layout, not motion, so that wrapper is allowed a translate but never a scale or opacity.
 */
function motionProblems(from: HTMLElement): string[] {
  const problems: string[] = [];
  for (let el: HTMLElement | null = from; el; el = el.parentElement) {
    const label = el.getAttribute('role') ?? el.tagName.toLowerCase();
    const computed = getComputedStyle(el);
    if (el.style.opacity !== '' || (computed.opacity !== '' && computed.opacity !== '1')) {
      problems.push(`${label}: opacity ${el.style.opacity || computed.opacity}`);
    }
    const transform = el.style.transform || computed.transform;
    if (transform && transform !== 'none') {
      const positioning = el.hasAttribute('data-radix-popper-content-wrapper');
      if (!positioning || /scale/.test(transform)) {
        problems.push(`${label}: transform ${transform}`);
      }
    }
    if (el === document.body) break;
  }
  return problems;
}

describe('HC-UIOV-001 Escape closes each overlay and focus returns to the trigger', () => {
  // Would not notice: an exit that unmounts but never restores focus to the
  // trigger is caught by the focus check; an exit that never unmounts is caught by waitFor.
  it.each(KINDS)('%s closes on Escape and focus returns to its trigger', async (kind) => {
    const user = userEvent.setup();
    renderOverlay(kind);
    const trigger = triggerOf(kind);

    await user.click(trigger);
    expect(screen.getByRole(ROLE[kind])).toBeInTheDocument();

    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole(ROLE[kind])).not.toBeInTheDocument(), {
      timeout: 2000,
    });
    // Radix returns focus in a setTimeout(0) after unmount, so the check waits for it.
    await waitFor(() => expect(trigger).toHaveFocus(), { timeout: 1000 });
  });
});

describe('HC-UIOV-002 focus stays inside an open Dialog or Sheet over 25 Tab presses', () => {
  // Would not notice: jsdom has no layout, so Tab order is the DOM order that user-event
  // computes. Focus leaving through browser chrome cannot happen in this environment.
  // The outside button is rendered beside the overlay, not in its portal. Without a
  // focusable element outside, Tab has nowhere to escape to, so the case passed with
  // modal={false}.
  it.each(['dialog', 'sheet'] as const)('%s keeps focus inside across 25 Tab presses', async (kind) => {
    const user = userEvent.setup();
    renderOverlay(kind, false, <button type="button">Outside action</button>);
    await user.click(triggerOf(kind));
    const content = screen.getByRole('dialog');
    // Radix hides the rest of the page from the accessibility tree while the overlay is open,
    // so the lookup needs hidden: true. The button is still focusable, which is what is tested.
    const outside = screen.getByRole('button', { name: 'Outside action', hidden: true });

    for (let press = 1; press <= 25; press += 1) {
      await user.tab();
      expect(content.contains(document.activeElement), `focus after Tab ${press}`).toBe(true);
      expect(outside, `outside button after Tab ${press}`).not.toHaveFocus();
    }
  });
});

describe('HC-UIOV-002 the actions of a tall overlay can be reached: the content scrolls', () => {
  // Would not notice: the rendered height. jsdom has no layout, so these pin the classes
  // that make the content scroll inside a 320 x 640 phone viewport. Clipping at that size
  // is only visible in a browser, and no browser run covers it in this row.
  it('a Dialog is capped at the viewport and scrolls', async () => {
    const user = userEvent.setup();
    renderOverlay('dialog');
    await user.click(triggerOf('dialog'));

    expect(screen.getByRole('dialog')).toHaveClass('max-h-[calc(100dvh-2rem)]', 'overflow-y-auto');
  });

  it('an AlertDialog is capped at the viewport and scrolls', async () => {
    const user = userEvent.setup();
    renderOverlay('alertdialog');
    await user.click(triggerOf('alertdialog'));

    expect(screen.getByRole('alertdialog')).toHaveClass('max-h-[calc(100dvh-2rem)]', 'overflow-y-auto');
  });

  it('a bottom Sheet is capped at 85dvh, scrolls, and clears the home indicator', async () => {
    const user = userEvent.setup();
    renderOverlay('sheet');
    await user.click(triggerOf('sheet'));

    expect(screen.getByRole('dialog')).toHaveClass(
      'max-h-[85dvh]',
      'overflow-y-auto',
      'pb-[max(1.5rem,env(safe-area-inset-bottom))]'
    );
  });

  it('a side Sheet on desktop scrolls', async () => {
    setMedia({ desktop: true });
    const user = userEvent.setup();
    renderOverlay('sheet');
    await user.click(triggerOf('sheet'));

    expect(screen.getByRole('dialog')).toHaveClass('inset-y-0', 'overflow-y-auto');
  });

  // Would not notice: a close target smaller than 44 px, which the touch-target rule
  // (plan HC-UIPC-002) forbids. The class is the only thing jsdom can see of its size.
  it('the close button is a 44 px target', async () => {
    const user = userEvent.setup();
    renderOverlay('dialog');
    await user.click(triggerOf('dialog'));

    expect(screen.getByRole('button', { name: 'Close' })).toHaveClass('h-11', 'w-11');
  });
});

describe('HC-UIOV-003 aria-modal, and a missing title fails the test', () => {
  // Would not notice: Radix 1.3.1 emits no missing-DialogTitle warning, so the
  // title guard is this primitive's own console.error. A title that is only whitespace passes it.
  it.each(['dialog', 'alertdialog', 'sheet'] as const)('%s sets aria-modal="true"', async (kind) => {
    const user = userEvent.setup();
    renderOverlay(kind);
    await user.click(triggerOf(kind));

    // Named by its title: a Title that is not wired to aria-labelledby leaves the name empty.
    expect(screen.getByRole(ROLE[kind], { name: TITLE[kind] })).toHaveAttribute('aria-modal', 'true');
    expect(titleWarnings).toEqual([]);
  });

  // Would not notice: a Popover whose label is dropped still has role "dialog", so the
  // role check alone passes. The name check is what fails when the label is missing.
  it('popover content is named by its label prop', async () => {
    const user = userEvent.setup();
    renderOverlay('popover');
    await user.click(triggerOf('popover'));

    expect(screen.getByRole('dialog', { name: POPOVER_LABEL })).toBeInTheDocument();
  });

  it.each(['dialog', 'alertdialog', 'sheet'] as const)(
    '%s rendered without a title triggers the title warning',
    async (kind) => {
      const user = userEvent.setup();
      renderWithoutTitle(kind);
      await user.click(triggerOf(kind));

      expect(titleWarnings).toHaveLength(1);
      expect(titleWarnings[0]).toMatch(TITLE_WARNING);
      // Clear it here, so the afterEach check is about the other tests only.
      titleWarnings.length = 0;
    }
  );
});

describe('HC-UIOV-004 reduced motion: the content animates opacity only', () => {
  // Would not notice: a transform applied later by a CSS class (jsdom loads no
  // stylesheet). The framer props checked here are the ones set on the content element.
  it.each(['dialog', 'alertdialog', 'sheet', 'popover'] as const)(
    '%s under reduced motion: initial, animate and exit use opacity only',
    async (kind) => {
      setReducedMotion(true);
      const user = userEvent.setup();
      renderOverlay(kind);
      await user.click(triggerOf(kind));

      const props = contentMotion(ROLE[kind]);
      for (const key of ['initial', 'animate', 'exit'] as const) {
        expect(Object.keys((props[key] ?? {}) as object), key).toEqual(['opacity']);
      }
      expect(screen.getByRole(ROLE[kind]).style.transform).toBe('');
    }
  );

  // Control: proves the check above can fail. Normal motion does use a transform.
  it.each(['dialog', 'alertdialog', 'sheet', 'popover'] as const)(
    '%s control: normal motion starts from a transform',
    async (kind) => {
      setReducedMotion(false);
      const user = userEvent.setup();
      renderOverlay(kind);
      await user.click(triggerOf(kind));

      expect(Object.keys((contentMotion(ROLE[kind]).initial ?? {}) as object)).toContain('transform');
    }
  );
});

describe('HC-UIOV-004 Sheet direction (M5): bottom below 1024 px, side at 1024 px and up', () => {
  // Would not notice: a breakpoint other than 1024 px, because the mock matches the exact
  // query string. It also would not notice a sheet that slides from the wrong edge
  // without the initial transform being checked here.
  it('below 1024 px the sheet slides from the bottom', async () => {
    setMedia({ desktop: false });
    const user = userEvent.setup();
    renderOverlay('sheet');
    await user.click(triggerOf('sheet'));

    expect(contentMotion('dialog').initial).toEqual({ transform: 'translateY(100%)' });
    expect(contentMotion('dialog').exit).toMatchObject({ transform: 'translateY(100%)' });
  });

  it('at 1024 px the sheet slides from the side', async () => {
    setMedia({ desktop: true });
    const user = userEvent.setup();
    renderOverlay('sheet');
    await user.click(triggerOf('sheet'));

    expect(contentMotion('dialog').initial).toEqual({ transform: 'translateX(100%)' });
    expect(contentMotion('dialog').exit).toMatchObject({ transform: 'translateX(100%)' });
  });
});

describe('HC-UIOV-005 Popover opens on click, Enter and Space, not on hover', () => {
  // Would not notice: a non-button trigger, which would need its own key
  // handler. This test covers only the <button> trigger that the primitive renders.
  it('opens on click', async () => {
    const user = userEvent.setup();
    renderOverlay('popover');
    await user.click(triggerOf('popover'));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it.each([
    ['Enter', '{Enter}'],
    ['Space', ' '],
  ])('opens on %s when the trigger has focus', async (_name, key) => {
    const user = userEvent.setup();
    renderOverlay('popover');
    const trigger = triggerOf('popover');
    act(() => trigger.focus());

    await user.keyboard(key);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not open on hover alone', async () => {
    const user = userEvent.setup();
    renderOverlay('popover');
    const trigger = triggerOf('popover');

    await user.hover(trigger);
    fireEvent.pointerEnter(trigger);
    fireEvent.mouseEnter(trigger);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

describe('HC-UIOV-006 opening Dialog, AlertDialog or Sheet dispatches asclexis:overlay-open', () => {
  // Would not notice: that the toaster (UI-PRIM-FEEDBACK) listens for this event.
  // That is covered in that row's test file.
  it.each(['dialog', 'alertdialog', 'sheet'] as const)(
    '%s dispatches the event on document once when it opens',
    async (kind) => {
      const user = userEvent.setup();
      const listener = vi.fn();
      document.addEventListener(OVERLAY_OPEN_EVENT, listener);
      try {
        renderOverlay(kind);
        await user.click(triggerOf(kind));

        expect(listener).toHaveBeenCalledTimes(1);
      } finally {
        document.removeEventListener(OVERLAY_OPEN_EVENT, listener);
      }
    }
  );

  it('Popover does not dispatch the event', async () => {
    const user = userEvent.setup();
    const listener = vi.fn();
    document.addEventListener(OVERLAY_OPEN_EVENT, listener);
    try {
      renderOverlay('popover');
      await user.click(triggerOf('popover'));

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(listener).not.toHaveBeenCalled();
    } finally {
      document.removeEventListener(OVERLAY_OPEN_EVENT, listener);
    }
  });
});

describe('HC-UIOV-007 still: no opacity, scale or translate on T0 content (vitest half)', () => {
  // Would not notice: rendered frames. jsdom runs no CSS and no real animation
  // frames, so this checks the inline and computed style and the framer props of the
  // content chain. The e2e stillnessProbe is in UI-SHELL.
  const cases: Array<[Kind, boolean]> = KINDS.flatMap((kind): Array<[Kind, boolean]> => [
    [kind, false],
    [kind, true],
  ]);

  it.each(cases)('%s still (reduced motion: %s) renders M0 for a [data-t0] child', async (kind, reduce) => {
    setReducedMotion(reduce);
    const user = userEvent.setup();
    renderOverlay(kind, true);
    await user.click(triggerOf(kind));

    const content = screen.getByRole(ROLE[kind]);
    const t0 = content.querySelector<HTMLElement>('[data-t0]');
    expect(t0).not.toBeNull();
    const props = contentMotion(ROLE[kind]);
    expect(props.initial, 'initial').toBeUndefined();
    expect(props.animate, 'animate').toBeUndefined();
    expect(props.exit, 'exit').toBeUndefined();
    expect(motionProblems(t0 as HTMLElement)).toEqual([]);

    // A motion that starts after the opening click would show by now.
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(motionProblems(t0 as HTMLElement)).toEqual([]);
  });

  // Control: proves motionProblems can fail. A non-still dialog starts at opacity 0.
  it('control: a non-still Dialog is reported by the same check', async () => {
    setReducedMotion(false);
    const user = userEvent.setup();
    renderOverlay('dialog', false);
    await user.click(triggerOf('dialog'));

    const t0 = screen.getByRole('dialog').querySelector<HTMLElement>('[data-t0]');
    expect(t0).not.toBeNull();
    expect(motionProblems(t0 as HTMLElement).length).toBeGreaterThan(0);
  });
});

describe('HC-UIOV-008 a destructive AlertDialog opens with Cancel focused, whatever the DOM order', () => {
  // Would not notice: a Cancel that is focused only because it comes first in the DOM. The
  // fixture puts "Delete" first, so a rule that focuses the first focusable fails (a) and (b).
  // (c) counts the calls on errorSpy: a missing cancel action must log once per open, and
  // a second log on the same open fails it.
  function renderDestructive(onConfirm: () => void, onCancel: () => void) {
    return renderInProviders(
      <AlertDialog trigger={<button type="button">Open alertdialog</button>} title={TITLE.alertdialog}>
        <button type="button" onClick={onConfirm}>
          Delete
        </button>
        <button type="button" data-alert-cancel onClick={onCancel}>
          Cancel
        </button>
      </AlertDialog>
    );
  }

  it('on open, Cancel has focus, not the Delete button that comes before it', async () => {
    const user = userEvent.setup();
    renderDestructive(vi.fn(), vi.fn());
    await user.click(triggerOf('alertdialog'));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus());
  });

  it('Enter calls the cancel handler and not the confirm handler', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    renderDestructive(onConfirm, onCancel);
    await user.click(triggerOf('alertdialog'));
    await user.keyboard('{Enter}');

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('an AlertDialog with no cancel element logs one console.error that names AlertDialog', async () => {
    const user = userEvent.setup();
    renderInProviders(
      <AlertDialog trigger={<button type="button">Open alertdialog</button>} title={TITLE.alertdialog}>
        <button type="button">Delete</button>
      </AlertDialog>
    );
    await user.click(triggerOf('alertdialog'));

    const named = (errorSpy?.mock.calls ?? []).filter(
      ([message]) => typeof message === 'string' && message.includes('AlertDialog')
    );
    expect(named).toHaveLength(1);
  });
});
