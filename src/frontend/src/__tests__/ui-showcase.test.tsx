/**
 * UI-SHOWCASE-KIT (HC-UISK-001 .. 006): the showcase components.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md §2.6 (recipes S1 to S4),
 * §7.7 (UI-SHOWCASE-KIT). jsdom runs no CSS animation and lays out no boxes, so
 * keyframes, durations and the reduced-motion block are read from
 * showcase.css, and the DOM that selects them is read from the rendered tree.
 * The browser checks (G1-3, G5-7, G10) belong to the page rows (L0 ruling 2).
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { BeamBorder } from '@/components/ui/BeamBorder';

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
