/**
 * UI-PRIM-FEEDBACK (HC-UIFB-001..006, vitest half): toasts, status chip,
 * pending text, progress, skeletons and the neutral Tag.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md, "UI-PRIM-FEEDBACK".
 * The Playwright half of HC-UIFB-006 (stillnessProbe on a toast) belongs to
 * UI-SHELL, which mounts the toaster in AppLayout (L0 ruling). No route here.
 *
 * New modules are imported inside each test, not at the top of the file, so a
 * missing module fails only the ids that need it and the RED run names each id.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { toast as sonnerToast } from 'sonner';
import { Badge } from '@/components/ui/Badge';
import type * as BadgeModule from '@/components/ui/Badge';
import * as SkeletonModule from '@/components/ui/Skeleton';
import { ListSkeleton } from '@/components/ui/Skeleton';
import type * as ToastModule from '@/components/ui/toast';
import type * as StatusChipModule from '@/components/ui/StatusChip';
import type * as PendingModule from '@/components/ui/Pending';
import type * as ProgressModule from '@/components/ui/Progress';

/**
 * Loads a module at run time. The specifier is a variable, so Vite does not
 * resolve it at transform time, and a module that does not exist yet fails
 * only the test that loads it (the same pattern as ui-motion.test.tsx).
 */
async function load<T>(specifier: string): Promise<T> {
  return (await import(/* @vite-ignore */ specifier)) as T;
}

// jsdom has no pointer-capture API, and sonner calls it on pointerdown when a
// toast's action is pressed. This shim only lets the event run in jsdom.
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
  Element.prototype.hasPointerCapture = () => false;
}

const GLOBALS_CSS = readFileSync(resolve(__dirname, '../styles/globals.css'), 'utf8');
const REDUCED_QUERY = '(prefers-reduced-motion: reduce)';
// The DOM event UI-PRIM-OVERLAYS dispatches (HC-UIOV-006). Spelled out here so
// a rename on either side fails a test instead of silently un-wiring DF-3.
const OVERLAY_OPEN = 'asclexis:overlay-open';

const STATUS_STATES = [
  'in-range',
  'above-range',
  'below-range',
  'not-checked',
  'checked-by-you',
  'caution',
  'info',
] as const;

let originalMatchMedia: typeof window.matchMedia;

beforeEach(() => {
  originalMatchMedia = window.matchMedia;
});

afterEach(() => {
  window.matchMedia = originalMatchMedia;
  sonnerToast.dismiss();
  cleanup();
});

function setReducedMotion(reduce: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: reduce && query === REDUCED_QUERY,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

/** The text between the braces of the first block that opens at or after `from`. */
function blockBody(source: string, from: number): string {
  const open = source.indexOf('{', from);
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === '{') depth += 1;
    else if (source[i] === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(open + 1, i);
    }
  }
  return '';
}

/** Numeric value of a `--name: N;` declaration in globals.css (the layer tokens). */
function layerToken(name: string): number {
  const match = new RegExp(`${name}:\\s*(\\d+)`).exec(GLOBALS_CSS);
  if (!match) throw new Error(`${name} not declared in globals.css`);
  return Number(match[1]);
}

/**
 * Selectors allowed to set animation-duration or iteration-count inside the
 * reduced-motion block. .animate-shimmer and .animate-bounce are loaders that
 * keep breathing at 1.6 s; .animate-ping is one decorative one-shot that stops
 * at its final frame. Any other selector with these properties is a kill switch.
 */
const LOADER_AND_ONE_SHOT = ['.animate-ping', '.animate-shimmer', '.animate-bounce'];
const TIMING_PROPERTY = /animation-(duration|iteration-count)\s*:/;

/** Rules inside the reduced-motion block, comments removed, as selector and body. */
function reducedMotionRules(css: string): Array<{ selector: string; body: string }> {
  const mediaAt = css.indexOf('@media (prefers-reduced-motion: reduce)');
  if (mediaAt < 0) throw new Error('no reduced-motion block in the CSS');
  const bare = blockBody(css, mediaAt).replace(/\/\*[\s\S]*?\*\//g, '');
  return Array.from(bare.matchAll(/([^{}]+)\{([^{}]*)\}/g), (m) => ({
    selector: m[1].trim(),
    body: m[2],
  }));
}

/** Selectors in the reduced-motion block that set timing outside the allowlist. */
function reducedMotionOffenders(css: string): string[] {
  return reducedMotionRules(css)
    .filter((rule) => TIMING_PROPERTY.test(rule.body) && !LOADER_AND_ONE_SHOT.includes(rule.selector))
    .map((rule) => rule.selector);
}

describe('HC-UIFB-001: notify() renders role="status" and its action calls the handler', () => {
  it('renders the message inside an element with role="status"', async () => {
    // Would not notice: a toast that shows the text with no status role.
    // sonner 2.0.8 sets no role on its own toast item, so notify() must add it.
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    render(<AppToaster />);

    act(() => {
      notify({ message: 'Saved 4 values' });
    });

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent('Saved 4 values');
  });

  it('calls the action handler once when the action button is pressed', async () => {
    // Would not notice: an action button that renders but is not wired to onClick.
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    const onUndo = vi.fn();
    render(<AppToaster />);

    act(() => {
      notify({ message: 'Entry removed', action: { label: 'Undo', onClick: onUndo } });
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Undo' }));
    expect(onUndo).toHaveBeenCalledTimes(1);
  });
});

describe('HC-UIFB-002: StatusChip shows an icon and words for every state', () => {
  it.each(STATUS_STATES)('%s renders an icon and a non-empty status word', async (state) => {
    // Would not notice: a colour-only chip (no svg) or a chip with an empty label.
    const { StatusChip } = await load<typeof StatusChipModule>('@/components/ui/StatusChip');
    const { container } = render(<StatusChip state={state} />);

    expect(container.querySelector('svg')).not.toBeNull();
    expect(container.textContent?.trim() ?? '').not.toBe('');
  });

  it('never uses "normal" or "abnormal" as a status word', async () => {
    // Would not notice: a label such as "Normal" that a per-state render test
    // only checks for presence, not for the forbidden words.
    const { StatusChip } = await load<typeof StatusChipModule>('@/components/ui/StatusChip');
    const words = STATUS_STATES.map((state) => {
      const { container, unmount } = render(<StatusChip state={state} />);
      const text = container.textContent ?? '';
      unmount();
      return text;
    });

    for (const text of words) {
      expect(text).not.toMatch(/\b(ab)?normal\b/i);
    }
  });

  it('gives each state its own words, so no two states read the same', async () => {
    // Would not notice: two states that collapse to one label, leaving the
    // user unable to tell "above range" from "below range".
    const { StatusChip } = await load<typeof StatusChipModule>('@/components/ui/StatusChip');
    const words = STATUS_STATES.map((state) => {
      const { container, unmount } = render(<StatusChip state={state} />);
      const text = (container.textContent ?? '').trim();
      unmount();
      return text;
    });

    expect(new Set(words).size).toBe(STATUS_STATES.length);
  });

  it.each([
    ['above-range', 'Above the report'],
    ['below-range', 'Below the report'],
  ] as const)('%s names the report as the source of the range (plan §2.2)', async (state, words) => {
    // Would not notice: a chip that says "Above range" and drops the source,
    // so the reader cannot tell whose reference range the value is outside.
    const { StatusChip } = await load<typeof StatusChipModule>('@/components/ui/StatusChip');
    const { container } = render(<StatusChip state={state} />);

    expect(container.textContent).toContain(words);
  });

  it('in range reads as neutral; only checked by you takes the verified green', async () => {
    // Would not notice: a green "In range" chip that reads as a pass verdict
    // on a value. Checked by you is the one state the verified token means.
    const { StatusChip } = await load<typeof StatusChipModule>('@/components/ui/StatusChip');
    const inRange = render(<StatusChip state="in-range" />);
    const inRangeClass = inRange.container.firstElementChild?.className ?? '';
    inRange.unmount();
    const checked = render(<StatusChip state="checked-by-you" />);
    const checkedClass = checked.container.firstElementChild?.className ?? '';

    expect(inRangeClass).not.toMatch(/status-verified/);
    expect(checkedClass).toMatch(/status-verified/);
  });

  it('in range uses a neutral glyph, not a check mark', async () => {
    // Would not notice: a check-circle glyph on "In range" that reads as a pass
    // verdict and sits close to "Checked by you". Lucide puts the icon name in
    // the svg class (lucide-check-circle-2), so the class shows the glyph.
    const { StatusChip } = await load<typeof StatusChipModule>('@/components/ui/StatusChip');
    const { container } = render(<StatusChip state="in-range" />);
    const icon = container.querySelector('svg');

    expect(icon).not.toBeNull();
    expect(icon?.getAttribute('class')).not.toMatch(/check/);
  });
});

describe('HC-UIFB-003: Pending keeps breathing under reduced motion', () => {
  it('keeps an opacity-only animation at 1.6 s when reduced motion is on', async () => {
    // Would not notice: a kill switch that drops the animation class under
    // reduce (the old global `* { animation-duration: .01ms }` froze loaders).
    setReducedMotion(true);
    // The mock sets the environment; Pending itself reads no media query, so the
    // reduce block in globals.css (checked below) is what decides the outcome.
    expect(window.matchMedia(REDUCED_QUERY).matches).toBe(true);
    const { Pending } = await load<typeof PendingModule>('@/components/ui/Pending');
    render(<Pending>Reading your verified results</Pending>);

    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('Reading your verified results');
    // An exact class token, not a substring: `motion-safe:` or `motion-reduce:`
    // in front of it would still contain the substring, and would switch it off.
    expect(status.className.split(/\s+/)).toContain('animate-[pulseSoft_1.6s_ease-in-out_infinite]');
  });

  it('names keyframes that change opacity only, never transform', () => {
    // Would not notice: a breathing loader that slides or scales. The class
    // check above names the keyframes; this one reads what they do.
    const keyframesAt = GLOBALS_CSS.indexOf('@keyframes pulseSoft');
    expect(keyframesAt).toBeGreaterThan(-1);
    const body = blockBody(GLOBALS_CSS, keyframesAt);

    expect(body).toMatch(/opacity/);
    expect(body).not.toMatch(/transform/);
  });

  it('is not stopped by the reduced-motion block in globals.css', () => {
    // Would not notice: a reduced-motion rule added later that sets
    // animation: none or pauses every animation.
    const mediaAt = GLOBALS_CSS.indexOf('@media (prefers-reduced-motion: reduce)');
    expect(mediaAt).toBeGreaterThan(-1);
    const body = blockBody(GLOBALS_CSS, mediaAt);

    expect(body).not.toMatch(/animation(-name)?\s*:\s*none/);
    expect(body).not.toMatch(/animation-play-state\s*:\s*paused/);
  });

  it('sets no animation-duration or iteration-count outside the loader and one-shot allowlist', () => {
    // Would not notice: the old global kill switch `* { animation-duration: .01ms;
    // animation-iteration-count: 1 }`, which froze every loader and passed the
    // test above. The parse must see the allowlisted rules, or the check is empty.
    const selectors = reducedMotionRules(GLOBALS_CSS).map((rule) => rule.selector);
    expect(selectors).toEqual(expect.arrayContaining(LOADER_AND_ONE_SHOT));
    expect(reducedMotionOffenders(GLOBALS_CSS)).toEqual([]);
  });

  it('the same check flags the old global kill switch', () => {
    // Would not notice: a check that flags nothing. The fixture is the kill
    // switch that froze loaders; the helper must name its `*` selector.
    const fixture = [
      '@media (prefers-reduced-motion: reduce) {',
      '  * {',
      '    animation-duration: 0.01ms;',
      '    animation-iteration-count: 1;',
      '  }',
      '  .animate-shimmer {',
      '    animation-duration: 1.6s;',
      '  }',
      '}',
    ].join('\n');

    expect(reducedMotionOffenders(fixture)).toEqual(['*']);
  });
});

describe('HC-UIFB-004: DF-3 toast layer sits below the modal and yields to overlays', () => {
  it('the --z-toast token is below --z-modal', () => {
    // Would not notice: an edit that moves the toast layer above the modal.
    expect(layerToken('--z-toast')).toBeLessThan(layerToken('--z-modal'));
  });

  it('AppToaster places its layer at var(--z-toast)', async () => {
    // Would not notice: a toaster left on sonner's default 999999999, which
    // sits above every modal and breaks DF-3.
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    render(<AppToaster />);
    // sonner renders its layer only while a toast exists, and shows the toast
    // asynchronously, so show one first and wait for it.
    act(() => {
      notify({ message: 'Layer probe' });
    });
    await screen.findByText('Layer probe');

    const toaster = document.querySelector('[data-sonner-toaster]');
    expect(toaster).not.toBeNull();
    expect(toaster?.getAttribute('style') ?? '').toMatch(/z-index:\s*var\(--z-toast\)/);
  });

  it('AppToaster sets the body font token, not sonner default', async () => {
    // Would not notice: a toaster left in sonner's own font, so its text does
    // not match the app's body text.
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    render(<AppToaster />);
    act(() => {
      notify({ message: 'Font probe' });
    });
    await screen.findByText('Font probe');

    const toaster = document.querySelector('[data-sonner-toaster]');
    expect(toaster?.getAttribute('style') ?? '').toMatch(/font-family:\s*var\(--font-body\)/);
  });

  it('dismisses visible toasts when the asclexis:overlay-open document event fires', async () => {
    // Would not notice: a listener on window instead of document. The event
    // is dispatched without bubbles, so only a document listener receives it.
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    render(<AppToaster />);

    act(() => {
      notify({ message: 'Toast before the sheet opens' });
    });
    await screen.findByText('Toast before the sheet opens');
    // Still on screen before the event, so the removal below is the event's
    // doing and not sonner's 4 s auto-dismiss. The window is 1 s, well under 4 s.
    expect(screen.getByText('Toast before the sheet opens')).toBeInTheDocument();

    act(() => {
      document.dispatchEvent(new Event(OVERLAY_OPEN));
    });

    await waitFor(
      () => expect(screen.queryByText('Toast before the sheet opens')).not.toBeInTheDocument(),
      { timeout: 1000 }
    );
  });
});

describe('HC-UIFB-005: Progress animates scaleX, never width', () => {
  it('exposes role="progressbar" with min, max and now', async () => {
    // Would not notice: a progress bar drawn with divs and no ARIA values.
    const { Progress } = await load<typeof ProgressModule>('@/components/ui/Progress');
    render(<Progress value={40} max={100} label="Importing documents" />);

    const bar = screen.getByRole('progressbar', { name: 'Importing documents' });
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
    expect(bar).toHaveAttribute('aria-valuenow', '40');
  });

  it('moves the fill with transform: scaleX and sets no width', async () => {
    // Would not notice: a fill that animates width (layout on every frame).
    // The class check catches a Tailwind w-* width that the inline style would miss.
    const { Progress } = await load<typeof ProgressModule>('@/components/ui/Progress');
    render(<Progress value={40} max={100} label="Importing documents" />);

    const fill = screen.getByRole('progressbar').firstElementChild as HTMLElement;
    expect(fill.style.transform).toBe('scaleX(0.4)');
    expect(fill.style.width).toBe('');
    expect(fill.className).not.toMatch(/(^|\s)w-/);
    expect(fill.className).toMatch(/transition-transform/);
    expect(fill.className).not.toMatch(/transition-all/);
  });
});

describe('HC-UIFB-006: still toasts and StatusChip carry data-t0 and never animate', () => {
  it('notify({ still: true }) puts data-t0 on its text and no enter transition on the toast', async () => {
    // Would not notice: a still toast that keeps sonner's 400 ms opacity and
    // transform transition, so a value fades and slides in.
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    render(<AppToaster />);

    act(() => {
      notify({ message: 'Verified 14.2 mg/dL on 2026-10-20', still: true });
    });

    const text = await screen.findByText('Verified 14.2 mg/dL on 2026-10-20');
    expect(text).toHaveAttribute('data-t0');
    const item = text.closest('[data-sonner-toast]') as HTMLElement;
    expect(item).not.toBeNull();
    expect(item.style.transition).toBe('none');
    // No inline opacity: an inline value beats sonner's removed and data-visible=false
    // rules, so a dismissed still toast would stay at full opacity for 200 ms.
    expect(item.style.opacity).toBe('');
    // Sonner moves the toast from its stylesheet, not from inline styles, so jsdom
    // cannot see the enter transform. CSS-driven motion is checked by UI-SHELL's
    // stillnessProbe (the Playwright half of HC-UIFB-006, L0 ruling).
  });

  it('a still toast keeps its text at full opacity when a newer toast stacks over it', async () => {
    // Would not notice: sonner's stacking rule `[data-front=false]>*{opacity:0}`
    // fades the content wrapper of an older toast when a second one arrives, so
    // the data-t0 value fades in a two-toast stack. Still toasts override it on
    // their content wrapper with !important utilities (Tailwind 4 suffix).
    // jsdom can only see the class, not the cascade; the cascade is UI-SHELL's probe.
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    render(<AppToaster />);

    act(() => {
      notify({ message: 'Verified 9.1 on 2026-10-21', still: true });
    });
    const text = await screen.findByText('Verified 9.1 on 2026-10-21');
    const content = text.closest('[data-content]') as HTMLElement;

    expect(content).not.toBeNull();
    expect(content.className).toMatch(/(^|\s)opacity-100!/);
    expect(content.className).toMatch(/(^|\s)transition-none!/);
  });

  it("a toast without still keeps sonner's transition and carries no data-t0", async () => {
    // Would not notice: still applied to every toast, which would make all of
    // them skip the M11 motion the plan keeps for toasts with no value.
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    render(<AppToaster />);

    act(() => {
      notify({ message: 'Changes saved' });
    });

    const text = await screen.findByText('Changes saved');
    expect(text).not.toHaveAttribute('data-t0');
    const item = text.closest('[data-sonner-toast]') as HTMLElement;
    expect(item.style.transition).not.toBe('none');
    // The still-only utilities must stay off a toast with no value in it.
    const content = text.closest('[data-content]') as HTMLElement;
    expect(content.className).not.toMatch(/transition-none!/);
  });

  it('StatusChip carries data-t0 on its root', async () => {
    // Would not notice: a chip that holds range words but is not probed, so
    // it could be animated later with no test failing.
    const { StatusChip } = await load<typeof StatusChipModule>('@/components/ui/StatusChip');
    const { container } = render(<StatusChip state="above-range" />);

    expect(container.querySelector('[data-t0]')).not.toBeNull();
  });

  it('under reduced motion no T0 element or its ancestors animate', async () => {
    // Would not notice: an animation class or inline animation added to a T0
    // node or to a wrapper above it. This sees class and style attributes only.
    // CSS-driven motion (sonner's own reduce rules, transitions in its stylesheet)
    // is checked by UI-SHELL's stillnessProbe, not here.
    setReducedMotion(true);
    const { AppToaster, notify } = await load<typeof ToastModule>('@/components/ui/toast');
    const { StatusChip } = await load<typeof StatusChipModule>('@/components/ui/StatusChip');
    render(
      <>
        <AppToaster />
        <StatusChip state="in-range" />
      </>
    );

    act(() => {
      notify({ message: 'Result 14.2 on 2026-10-20', still: true });
    });
    await screen.findByText('Result 14.2 on 2026-10-20');

    const t0Nodes = Array.from(document.querySelectorAll<HTMLElement>('[data-t0]'));
    expect(t0Nodes.length).toBeGreaterThanOrEqual(2);
    for (const node of t0Nodes) {
      let el: HTMLElement | null = node;
      while (el && el !== document.body) {
        expect(el.getAttribute('class') ?? '').not.toMatch(/animate-/);
        expect(el.getAttribute('style') ?? '').not.toMatch(/animation/);
        el = el.parentElement;
      }
    }
  });
});

describe('Skeleton and Badge (files in this row; no HC id)', () => {
  it('ListSkeleton container is aria-busy and renders one shape per count', () => {
    // Would not notice: a loading list that gives assistive tech no signal that
    // the region is still updating. aria-busy does not announce by itself.
    const { container } = render(<ListSkeleton count={3} />);
    const root = container.firstElementChild as HTMLElement;

    expect(root).toHaveAttribute('aria-busy', 'true');
    expect(root.children).toHaveLength(3);
  });

  it('ListSkeleton shapes use the surface of the final list rows', () => {
    // Would not notice: drift between the placeholder and the rows the pages
    // render (CareTasksPage and MedicationCoach use rounded-xl, border-black/6, bg-surface-muted).
    // It pins the class list, not the rendered height.
    const { container } = render(<ListSkeleton count={1} />);
    const shape = container.querySelector('.rounded-xl') as HTMLElement;

    expect(shape).not.toBeNull();
    expect(shape.className).toMatch(/border-black\/6/);
    expect(shape.className).toMatch(/bg-surface-muted/);
  });

  it('CardSkeleton is deleted (it had no callers)', () => {
    // Would not notice: a reintroduced unused export.
    expect(SkeletonModule).not.toHaveProperty('CardSkeleton');
  });

  it.each([
    ['default', 'bg-surface-muted'],
    ['accent', 'bg-accent-subtle'],
    ['caution', 'bg-status-caution-subtle'],
    ['attention', 'bg-status-attention-subtle'],
    ['verified', 'bg-status-verified-subtle'],
    ['info', 'bg-status-info-subtle'],
  ] as const)('Badge keeps variant %s for its existing callers', (variant, fill) => {
    // Would not notice: a Badge change that drops a value the ~40 callers pass.
    const { container } = render(<Badge variant={variant}>Label</Badge>);

    expect(container.firstElementChild?.className).toMatch(new RegExp(fill));
  });

  it('Tag renders neutral text with no status colour', async () => {
    // Would not notice: a Tag that borrows a status fill and reads as a verdict.
    const { Tag } = await load<typeof BadgeModule>('@/components/ui/Badge');
    const { container } = render(<Tag>Fasting</Tag>);
    const tag = container.firstElementChild as HTMLElement;

    expect(tag).toHaveTextContent('Fasting');
    expect(tag.className).not.toMatch(/status-|accent/);
  });
});
