/**
 * UI-SHOWCASE-KIT (HC-UISK-001 .. 006): the showcase components.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md §2.6 (recipes S1 to S4),
 * §7.7 (UI-SHOWCASE-KIT). jsdom runs no CSS animation and lays out no boxes, so
 * keyframes, durations and the reduced-motion block are read from
 * showcase.css, and the DOM that selects them is read from the rendered tree.
 * The browser checks (G1-3, G5-7, G10) belong to the page rows (L0 ruling 2).
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LazyMotion, domAnimation } from 'framer-motion';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { BeamBorder } from '@/components/ui/BeamBorder';
import { ThinkingOrb } from '@/components/ui/ThinkingOrb';
import { ShowcaseReveal, revealDelay } from '@/components/ui/ShowcaseReveal';
import { EmptyState } from '@/components/ui/EmptyState';
import { Button } from '@/components/ui/Button';
import { duration, stagger } from '@/motion/tokens';

// The library is replaced by a stub that counts how often it is loaded and
// records the props it receives. The real package draws on a canvas, which
// jsdom does not provide.
const orbCalls = vi.hoisted(() => ({ loads: 0, props: [] as Record<string, unknown>[] }));

vi.mock('thinking-orbs', async () => {
  orbCalls.loads += 1;
  const React = await import('react');
  return {
    ThinkingOrb: (props: Record<string, unknown>) => {
      orbCalls.props.push(props);
      return React.createElement('canvas', { 'data-testid': 'orb' });
    },
  };
});

// Captured after the imports above run and before any test renders an orb.
// It is 0 only if ThinkingOrb.tsx does not import the library statically.
const LOADS_AT_IMPORT = orbCalls.loads;

const UI_DIR = resolve(__dirname, '../components/ui');
const FRONTEND_DIR = resolve(__dirname, '../..');
const CSS_RAW = readFileSync(join(UI_DIR, 'showcase.css'), 'utf8');
const CSS = CSS_RAW.replace(/\/\*[\s\S]*?\*\//g, '');
const BEAM_SRC = readFileSync(join(UI_DIR, 'BeamBorder.tsx'), 'utf8');
const GLOBALS_CSS = readFileSync(join(__dirname, '../styles/globals.css'), 'utf8');

interface Rule {
  /** Selector or at-rule text before the brace, trimmed. */
  prelude: string;
  /** Declarations (and nested rules, for @media) between the braces. */
  body: string;
}

/** Flat list of every rule in a stylesheet, nested ones included, in file order. */
function parseRules(source: string): Rule[] {
  const rules: Rule[] = [];
  const open: { prelude: string; start: number }[] = [];
  let last = 0;
  for (let i = 0; i < source.length; i += 1) {
    if (source[i] === '{') {
      open.push({ prelude: source.slice(last, i).trim(), start: i + 1 });
      last = i + 1;
    } else if (source[i] === '}') {
      const rule = open.pop();
      if (rule) rules.push({ prelude: rule.prelude, body: source.slice(rule.start, i) });
      last = i + 1;
    }
  }
  return rules;
}

const RULES = parseRules(CSS);

/** Bodies of the rules whose prelude is exactly `prelude`. */
function bodiesOf(prelude: string): string {
  return RULES.filter((rule) => rule.prelude === prelude)
    .map((rule) => rule.body)
    .join('\n');
}

/** Every `var(--name)` referenced in the stylesheet, without the `--`. */
function varsUsed(source: string): string[] {
  return [...source.matchAll(/var\(\s*--([\w-]+)/g)].map((match) => match[1] ?? '');
}

let originalMatchMedia: typeof window.matchMedia;

beforeEach(() => {
  originalMatchMedia = window.matchMedia;
});

afterEach(() => {
  window.matchMedia = originalMatchMedia;
});

/** Makes `prefers-reduced-motion: reduce` match (or not) for the next render. */
function setReducedMotion(reduce: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: reduce && query === '(prefers-reduced-motion: reduce)',
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

describe('UI-SHOWCASE-KIT BeamBorder (S2)', () => {
  it('HC-UISK-001: the beam pauses and fades out when active turns false', () => {
    setReducedMotion(false);
    const { container, rerender } = render(<BeamBorder active>card</BeamBorder>);
    const root = container.firstElementChild as HTMLElement;
    expect(root).toHaveAttribute('data-active', 'true');

    rerender(<BeamBorder active={false}>card</BeamBorder>);
    expect(root).toHaveAttribute('data-active', 'false');
    // The DOM above is what the stylesheet keys on: the paused state and the
    // fade are scoped to a card whose data-active is false.
    const idle = bodiesOf(".beam-border[data-active='false'] .beam-border__beam");
    expect(idle).toMatch(/animation-play-state\s*:\s*paused/);
    expect(idle).toMatch(/opacity\s*:\s*0\b/);
  });

  it('HC-UISK-001: the beam loops in 2.4 s, linear, on the border element only', () => {
    expect(bodiesOf('.beam-border__beam')).toMatch(
      /animation\s*:\s*beam-spin\s+2\.4s\s+linear\s+infinite/
    );
    expect(bodiesOf('@keyframes beam-spin')).toMatch(/--beam-angle\s*:\s*360deg/);
    expect(bodiesOf('@property --beam-angle')).toMatch(/syntax\s*:\s*'<angle>'/);

    // Any animation declaration outside the beam (and its keyframes) would
    // animate something other than the border element.
    const stray = RULES.filter(
      (rule) =>
        !rule.prelude.startsWith('@media') &&
        !rule.prelude.startsWith('@keyframes') &&
        rule.prelude !== '.beam-border__beam' &&
        /animation\s*:/.test(rule.body)
    ).map((rule) => rule.prelude);
    expect(stray).toEqual([]);
  });

  it('HC-UISK-001: the beam fades out over 240 ms', () => {
    expect(bodiesOf('.beam-border__beam')).toMatch(/transition\s*:\s*opacity\s+240ms\b/);
  });

  it('HC-UISK-001: under reduced motion there is no beam, only a static 1 px accent frame', () => {
    setReducedMotion(true);
    const { container } = render(<BeamBorder active>card</BeamBorder>);
    const root = container.firstElementChild as HTMLElement;

    expect(root).toHaveAttribute('data-motion', 'reduced');
    expect(container.querySelector('.beam-border__beam')).toBeNull();
    expect(container.querySelector('.beam-border__frame')).not.toBeNull();

    expect(bodiesOf('.beam-border__frame')).toMatch(/border\s*:\s*1px\s+solid\s+var\(--accent\)/);
    expect(bodiesOf('.beam-border__frame')).not.toMatch(/animation/);
    const reducedBlock = RULES.find(
      (rule) => rule.prelude === '@media (prefers-reduced-motion: reduce)'
    );
    expect(reducedBlock?.body ?? '').toMatch(/animation\s*:\s*none/);
  });

  it('HC-UISK-001: under full motion the beam renders and no static frame does', () => {
    setReducedMotion(false);
    const { container } = render(<BeamBorder active>card</BeamBorder>);

    expect(container.firstElementChild).toHaveAttribute('data-motion', 'full');
    expect(container.querySelector('.beam-border__beam')).not.toBeNull();
    expect(container.querySelector('.beam-border__frame')).toBeNull();
  });
});

describe('UI-SHOWCASE-KIT BeamBorder colours (S2)', () => {
  it('HC-UISK-002: colours resolve only to --accent, --accent-ink and --band', () => {
    const allowed = new Set(['accent', 'accent-ink', 'band', 'beam-angle']);
    const used = varsUsed(CSS);
    expect(used.filter((name) => !allowed.has(name))).toEqual([]);
    for (const name of ['accent', 'accent-ink', 'band']) {
      expect(used, `--${name} is not used`).toContain(name);
    }
  });

  it('HC-UISK-002: the beam is painted in an opaque token, so a translucent text colour cannot dim or hide it', () => {
    // The mask takes its alpha from currentColor. A consumer's text colour must not reach it.
    expect(bodiesOf('.beam-border__beam')).toMatch(/(?:^|[;\s])color\s*:\s*var\(--accent\)/);
  });

  it('HC-UISK-002: the three colour tokens are defined in globals.css', () => {
    for (const name of ['accent', 'accent-ink', 'band']) {
      expect(GLOBALS_CSS, `--${name} is not defined`).toMatch(new RegExp(`--${name}\\s*:`));
    }
  });

  it('HC-UISK-002: no hex, functional or named colour literal in showcase.css or BeamBorder.tsx', () => {
    const hex = /#[0-9a-f]{3,8}\b/i;
    const functional = /\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\(/i;
    const named =
      /\b(?:white|black|red|green|blue|gray|grey|silver|yellow|orange|purple|pink|brown|teal|navy|aqua|lime|maroon|olive|fuchsia|indigo|violet|gold)\b/i;
    for (const [label, source] of [
      ['showcase.css', CSS],
      ['BeamBorder.tsx', BEAM_SRC],
    ] as const) {
      expect(source, `${label} has a hex colour`).not.toMatch(hex);
      expect(source, `${label} has a functional colour`).not.toMatch(functional);
      expect(source, `${label} has a named colour`).not.toMatch(named);
    }
  });

  it('HC-UISK-002: no border-beam package, and showcase.css is imported by BeamBorder', () => {
    const pkg = readFileSync(join(FRONTEND_DIR, 'package.json'), 'utf8');
    expect(pkg).not.toMatch(/"border-beam"/);
    expect(BEAM_SRC).not.toMatch(/from\s+['"]border-beam/);
    expect(BEAM_SRC).toMatch(/import\s+['"]\.\/showcase\.css['"]/);
  });
});

describe('UI-SHOWCASE-KIT ThinkingOrb (S3)', () => {
  it('HC-UISK-003: status is required, so a call without it is a type error', () => {
    // tsc enforces this line (npx tsc --noEmit); vitest only runs it.
    // @ts-expect-error status is required
    const withoutStatus = <ThinkingOrb />;
    expect(withoutStatus.type).toBe(ThinkingOrb);
  });

  it('HC-UISK-003: renders the status text as a role=status element', async () => {
    render(<ThinkingOrb status="Reading page 2 of 3" />);
    expect(screen.getByRole('status')).toHaveTextContent('Reading page 2 of 3');
    await screen.findByTestId('orb');
  });

  it('HC-UISK-003: the canvas box is reserved at its size before the library loads, so the status text does not shift', () => {
    render(<ThinkingOrb status="Reading page 2 of 3" size={64} />);
    // The wrapper is the status element's previous sibling; it exists before the library does.
    const box = screen.getByRole('status').previousElementSibling as HTMLElement;
    expect(box).toHaveAttribute('aria-hidden', 'true');
    expect(box.style.width).toBe('64px');
    expect(box.style.height).toBe('64px');
  });

  it('HC-UISK-003: the canvas sits in an aria-hidden wrapper that does not hold the status', async () => {
    render(<ThinkingOrb status="Reading page 2 of 3" />);
    const orb = await screen.findByTestId('orb');
    const hidden = orb.closest('[aria-hidden="true"]');
    expect(hidden).not.toBeNull();
    expect(hidden?.contains(screen.getByRole('status'))).toBe(false);
  });

  it('HC-UISK-003: the library is given theme="auto"', async () => {
    render(<ThinkingOrb status="Reading" />);
    await screen.findByTestId('orb');
    const last = orbCalls.props[orbCalls.props.length - 1] ?? {};
    expect(last).toMatchObject({ theme: 'auto' });
  });

  it('HC-UISK-003: no paused or speed override is passed, so the library applies its own reduced-motion frame', async () => {
    // The wrapper never reads matchMedia; the library does, so this checks only that the wrapper adds no override.
    render(<ThinkingOrb status="Reading" />);
    await screen.findByTestId('orb');
    const last = orbCalls.props[orbCalls.props.length - 1] ?? {};
    expect(last).not.toHaveProperty('paused');
    expect(last).not.toHaveProperty('speed');
  });
});

describe('UI-SHOWCASE-KIT ThinkingOrb library load (HC-UISK-004)', () => {
  it('HC-UISK-004: importing the wrapper does not load thinking-orbs', () => {
    expect(LOADS_AT_IMPORT).toBe(0);
  });

  it('HC-UISK-004: thinking-orbs loads when an orb mounts, through React.lazy', async () => {
    render(<ThinkingOrb status="Reading" />);
    await screen.findByTestId('orb');
    expect(orbCalls.loads).toBe(1);
  });

  it('HC-UISK-004: no source file imports thinking-orbs statically; the wrapper imports it with a lazy dynamic import', () => {
    const staticImport =
      /^\s*(?:import\s+(?!type\s)[^;]*?\bfrom\s*|import\s*|export\s[^;]*?\bfrom\s*)['"]thinking-orbs['"]/m;
    const srcRoot = resolve(__dirname, '..');
    const files = (dir: string): string[] =>
      readdirSync(dir).flatMap((name) => {
        const full = join(dir, name);
        if (statSync(full).isDirectory()) return name === '__tests__' ? [] : files(full);
        return /\.(ts|tsx)$/.test(name) ? [full] : [];
      });
    const offenders = files(srcRoot)
      .filter((file) => staticImport.test(readFileSync(file, 'utf8')))
      .map((file) => file.slice(srcRoot.length));
    expect(offenders).toEqual([]);

    const wrapper = readFileSync(join(UI_DIR, 'ThinkingOrb.tsx'), 'utf8');
    expect(wrapper).toMatch(/lazy\(\s*\(\)\s*=>\s*import\(\s*['"]thinking-orbs['"]\s*\)/);
  });
});

describe('UI-SHOWCASE-KIT ShowcaseReveal (S1)', () => {
  // The motion features are loaded here directly; the app loads them through MotionProvider.
  function renderReveal() {
    return render(
      <LazyMotion features={domAnimation}>
        <ShowcaseReveal>
          <p>One</p>
          <p>Two</p>
        </ShowcaseReveal>
      </LazyMotion>
    );
  }

  beforeEach(() => {
    setReducedMotion(false);
    window.sessionStorage.clear();
  });

  it('HC-UISK-005: the first visit starts each group 12 px down and transparent', () => {
    renderReveal();
    const group = screen.getByText('One').parentElement as HTMLElement;
    expect(group.style.opacity).toBe('0');
    expect(group.style.transform).toMatch(/translateY\(12px\)/);
  });

  it('HC-UISK-005: once per session: the second mount has no transform and is visible', () => {
    const first = renderReveal();
    first.unmount();
    renderReveal();
    const group = screen.getByText('One').parentElement as HTMLElement;
    expect(group.style.opacity).not.toBe('0');
    expect(group.style.transform).not.toMatch(/translate/);
  });

  it('HC-UISK-005: with storage blocked, the content still renders', () => {
    // A blocked browser throws when the sessionStorage getter is read, so the
    // getter itself is replaced. (Spying on Storage.prototype does not reach it.)
    const original = Object.getOwnPropertyDescriptor(window, 'sessionStorage');
    Object.defineProperty(window, 'sessionStorage', {
      configurable: true,
      get() {
        throw new DOMException('storage blocked', 'SecurityError');
      },
    });
    try {
      renderReveal();
      expect(screen.getByText('One')).toBeInTheDocument();
      expect(screen.getByText('Two')).toBeInTheDocument();
    } finally {
      Reflect.deleteProperty(window, 'sessionStorage');
      if (original) Object.defineProperty(window, 'sessionStorage', original);
    }
  });

  it('HC-UISK-005: under reduced motion the first render is opacity only, with no transform', () => {
    setReducedMotion(true);
    renderReveal();
    const group = screen.getByText('One').parentElement as HTMLElement;
    expect(group.style.opacity).toBe('0');
    expect(group.style.transform).not.toMatch(/translate/);
  });

  it('HC-UISK-005: the stagger is 60 ms per group, capped at 8 steps', () => {
    expect(revealDelay(0)).toBe(0);
    expect(revealDelay(3)).toBeCloseTo(0.18, 5);
    expect(revealDelay(8)).toBeCloseTo(0.48, 5);
    expect(revealDelay(20)).toBeCloseTo(0.48, 5);
  });

  it('HC-UISK-005: the timing is the plan S1 timing, taken from the motion tokens', () => {
    expect(duration.show).toBe(0.48);
    expect(stagger.show).toEqual({ step: 0.06, cap: 8 });
    const source = readFileSync(join(UI_DIR, 'ShowcaseReveal.tsx'), 'utf8');
    expect(source).toMatch(/from\s+['"]@\/motion\/tokens['"]/);
    expect(source).toMatch(/import\s*\{[^}]*\bm\b[^}]*\}\s*from\s+['"]framer-motion['"]/);
    expect(source).not.toMatch(/\bmotion\./);
  });

  it('HC-UISK-005: S1 moves with a CSS transform string, not the x/y/scale shorthands (plan §2.6: those run on the main thread)', () => {
    // jsdom renders translateY(12px) for either spelling, so the source is what is checked.
    const source = readFileSync(join(UI_DIR, 'ShowcaseReveal.tsx'), 'utf8');
    expect(source).not.toMatch(/(?<![\w.])(?:x|y|scale)\s*:/);
    expect(source).toMatch(/transform\s*:\s*'translateY\(12px\)'/);
  });
});

describe('UI-SHOWCASE-KIT EmptyState (HC-UISK-006)', () => {
  beforeEach(() => {
    setReducedMotion(false);
    window.sessionStorage.clear();
  });

  it('HC-UISK-006: an action given as a button renders as a real button', () => {
    render(
      <EmptyState
        title="No values yet"
        description="Import a report to start."
        action={<Button>Import a report</Button>}
      />
    );
    expect(screen.getByRole('button', { name: 'Import a report' })).toBeInTheDocument();
  });

  it('HC-UISK-006: an action given as a link renders as a real link', () => {
    render(
      <EmptyState
        title="No values yet"
        description="Import a report to start."
        action={<a href="/inbox">Go to documents</a>}
      />
    );
    expect(screen.getByRole('link', { name: 'Go to documents' })).toHaveAttribute('href', '/inbox');
  });

  it('HC-UISK-006: action stays optional: this call compiles without one and renders none', () => {
    // tsc is the check here: the call below must compile with no action (L0 ruling 1).
    render(<EmptyState title="Nothing here yet" description="Results appear after an import." />);
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('HC-UISK-006: the layout is illustration, then the sentence, then the action', () => {
    render(
      <EmptyState
        title="Nothing here yet"
        description="Results appear after an import."
        illustration={
          <svg data-testid="line-art" viewBox="0 0 10 10">
            <line x1="0" y1="5" x2="10" y2="5" />
          </svg>
        }
        action={<Button>Import a report</Button>}
      />
    );
    const art = screen.getByTestId('line-art');
    const title = screen.getByRole('heading', { name: 'Nothing here yet' });
    const description = screen.getByText('Results appear after an import.');
    const button = screen.getByRole('button', { name: 'Import a report' });
    const following = Node.DOCUMENT_POSITION_FOLLOWING;
    expect(art.compareDocumentPosition(title) & following).toBeTruthy();
    expect(title.compareDocumentPosition(description) & following).toBeTruthy();
    expect(description.compareDocumentPosition(button) & following).toBeTruthy();
  });

  it('HC-UISK-006: the illustration is decorative and hidden from assistive technology', () => {
    render(
      <EmptyState
        title="Nothing here yet"
        description="Results appear after an import."
        illustration={<svg data-testid="line-art" viewBox="0 0 10 10" />}
      />
    );
    expect(screen.getByTestId('line-art').closest('[aria-hidden="true"]')).not.toBeNull();
    expect(screen.getByRole('heading', { name: 'Nothing here yet' })).toBeInTheDocument();
  });

  it('HC-UISK-006: the sentence takes the S1 entrance: 12 px down and transparent on the first visit', () => {
    render(
      <LazyMotion features={domAnimation}>
        <EmptyState title="Nothing here yet" description="Results appear after an import." />
      </LazyMotion>
    );
    // heading -> sentence group (title and description) -> reveal wrapper for that group.
    const sentence = screen.getByRole('heading', { name: 'Nothing here yet' }).parentElement;
    const group = sentence?.parentElement as HTMLElement;
    expect(group.style.opacity).toBe('0');
    expect(group.style.transform).toMatch(/translateY\(12px\)/);
  });
});
