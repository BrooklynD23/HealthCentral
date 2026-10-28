/**
 * UI-TOKENS: colour, type and utility checks (HC-UITK-001 .. 003).
 *
 * These tests read the real files: styles/globals.css for the plan §2.2 colour
 * tokens and the §2.3 type scale, and every component .tsx under src/ for the
 * colour utilities it uses. No token value is written here, except in the
 * detector self-check at the end, which proves the contrast function can fail.
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md §2.2, §2.3 and §7.3.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import ts from 'typescript';
import { createElement } from 'react';
import { render } from '@testing-library/react';
import { buttonVariants } from '@/components/ui/Button';
import { Input, type InputProps } from '@/components/ui/Input';

// This file lives in src/__tests__; the stylesheet and components are one level up.
const SRC_ROOT = resolve(__dirname, '..');
const STYLES_PATH = join(SRC_ROOT, 'styles', 'globals.css');
const css = readFileSync(STYLES_PATH, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');

/** Bodies of every rule whose selector matches `selector` (a regex), in file order. */
function ruleBodies(source: string, selector: RegExp): string[] {
  const opener = new RegExp(`${selector.source}\\s*\\{`, 'g');
  const bodies: string[] = [];
  for (const match of source.matchAll(opener)) {
    const start = (match.index ?? 0) + match[0].length;
    let depth = 1;
    let i = start;
    while (i < source.length && depth > 0) {
      if (source[i] === '{') depth += 1;
      else if (source[i] === '}') depth -= 1;
      i += 1;
    }
    bodies.push(source.slice(start, i - 1));
  }
  return bodies;
}

/** `--name: value;` declarations of one rule body. */
function declarations(body: string): Map<string, string> {
  const map = new Map<string, string>();
  for (const match of body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    map.set(match[1] ?? '', (match[2] ?? '').trim());
  }
  return map;
}

// Raw tokens: plain :root (light), then :root[data-theme='dark'] over it.
const LIGHT = new Map<string, string>();
for (const body of ruleBodies(css, /:root/)) {
  for (const [name, value] of declarations(body)) LIGHT.set(name, value);
}
const DARK = new Map(LIGHT);
for (const body of ruleBodies(css, /:root\[data-theme=['"]dark['"]\]/)) {
  for (const [name, value] of declarations(body)) DARK.set(name, value);
}
const TOKENS = { light: LIGHT, dark: DARK } as const;

/** Follows var(--x) references until a literal value, or returns undefined. */
function resolveToken(name: string, tokens: Map<string, string>, depth = 0): string | undefined {
  const raw = tokens.get(name);
  if (raw === undefined || depth > 5) return undefined;
  const reference = /^var\((--[\w-]+)\)$/.exec(raw);
  return reference ? resolveToken(reference[1] ?? '', tokens, depth + 1) : raw;
}

type Rgb = [number, number, number];

function parseHex(value: string | undefined): Rgb | undefined {
  const match = /^#([0-9a-f]{6})$/i.exec(value?.trim() ?? '');
  if (!match) return undefined;
  const n = parseInt(match[1] ?? '0', 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** WCAG 2.x contrast ratio between two sRGB colours. */
function contrastRatio(a: Rgb, b: Rgb): number {
  const luminance = ([r, g, bl]: Rgb) => {
    const lin = (channel: number) => {
      const s = channel / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(bl);
  };
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

const TEXT_MIN = 4.5;
const NON_TEXT_MIN = 3;

interface Pair {
  /** Token names, without the leading -- of the foreground and background. */
  fg: string;
  bg: string;
  min: number;
  /** The §2.2 table row this pair comes from. */
  row: string;
  /** The plan marks this light-theme pair "—" in dark. */
  skipDark?: boolean;
}

/** Every pair in the plan §2.2 ratio table. Tokens are names; values come from globals.css. */
const PAIRS: Pair[] = [
  { fg: 'ink-1', bg: 'paper', min: TEXT_MIN, row: 'ink-1 on paper' },
  { fg: 'ink-1', bg: 'surface-1', min: TEXT_MIN, row: 'ink-1 on surface-1' },
  { fg: 'ink-1', bg: 'surface-2', min: TEXT_MIN, row: 'ink-1 on surface-2' },
  { fg: 'ink-2', bg: 'paper', min: TEXT_MIN, row: 'ink-2 on paper' },
  { fg: 'ink-2', bg: 'surface-1', min: TEXT_MIN, row: 'ink-2 on surface-1' },
  { fg: 'ink-2', bg: 'surface-2', min: TEXT_MIN, row: 'ink-2 on surface-2' },
  { fg: 'ink-3', bg: 'paper', min: TEXT_MIN, row: 'ink-3 on paper' },
  { fg: 'ink-3', bg: 'surface-1', min: TEXT_MIN, row: 'ink-3 on surface-1' },
  { fg: 'ink-3', bg: 'surface-2', min: TEXT_MIN, row: 'ink-3 on surface-2' },
  { fg: 'ink-3', bg: 'surface-3', min: TEXT_MIN, row: 'ink-3 on surface-3' },
  { fg: 'ink-3', bg: 'band', min: TEXT_MIN, row: 'ink-3 on band (chart labels)' },
  { fg: 'accent', bg: 'paper', min: TEXT_MIN, row: 'accent on paper' },
  { fg: 'accent', bg: 'surface-1', min: TEXT_MIN, row: 'accent on surface-1' },
  { fg: 'accent', bg: 'surface-2', min: TEXT_MIN, row: 'accent on surface-2', skipDark: true },
  { fg: 'accent-ink', bg: 'accent-subtle', min: TEXT_MIN, row: 'accent-ink on accent-subtle (active nav)' },
  { fg: 'on-accent', bg: 'accent', min: TEXT_MIN, row: 'on-accent on accent (primary button)' },
  { fg: 'on-accent', bg: 'accent-hover', min: TEXT_MIN, row: 'on-accent on accent-hover (primary button)' },
  { fg: 'caution', bg: 'caution-subtle', min: TEXT_MIN, row: 'caution on its bg' },
  { fg: 'caution', bg: 'surface-1', min: TEXT_MIN, row: 'caution on surface-1' },
  { fg: 'outside', bg: 'outside-subtle', min: TEXT_MIN, row: 'outside on its bg' },
  { fg: 'outside', bg: 'surface-1', min: TEXT_MIN, row: 'outside on surface-1' },
  { fg: 'outside', bg: 'paper', min: TEXT_MIN, row: 'outside on paper' },
  { fg: 'verified', bg: 'verified-subtle', min: TEXT_MIN, row: 'verified on its bg' },
  { fg: 'verified', bg: 'surface-1', min: TEXT_MIN, row: 'verified on surface-1' },
  { fg: 'verified', bg: 'paper', min: TEXT_MIN, row: 'verified on paper', skipDark: true },
  { fg: 'info', bg: 'info-subtle', min: TEXT_MIN, row: 'info on its bg' },
  { fg: 'info', bg: 'surface-1', min: TEXT_MIN, row: 'info on surface-1' },
  { fg: 'on-status', bg: 'outside', min: TEXT_MIN, row: 'on-status on outside (danger button)' },
  { fg: 'pencil', bg: 'surface-1', min: NON_TEXT_MIN, row: 'pencil on surface-1 (non-text)' },
  { fg: 'pencil', bg: 'band', min: NON_TEXT_MIN, row: 'pencil on band (non-text)' },
  { fg: 'line-strong', bg: 'surface-1', min: NON_TEXT_MIN, row: 'line-strong on surface-1 (1.4.11)' },
  { fg: 'line-strong', bg: 'paper', min: NON_TEXT_MIN, row: 'line-strong on paper (1.4.11)' },
  { fg: 'accent', bg: 'paper', min: NON_TEXT_MIN, row: 'focus ring (accent) on paper' },
];

describe('UI-TOKENS contrast', () => {
  for (const theme of ['light', 'dark'] as const) {
    it(`HC-UITK-001 (${theme}): every plan §2.2 pair reaches its WCAG ratio`, () => {
      const tokens = TOKENS[theme];
      const failures: string[] = [];
      for (const pair of PAIRS) {
        if (theme === 'dark' && pair.skipDark) continue;
        const fg = parseHex(resolveToken(`--${pair.fg}`, tokens));
        const bg = parseHex(resolveToken(`--${pair.bg}`, tokens));
        if (!fg || !bg) {
          failures.push(`${pair.row}: --${pair.fg} or --${pair.bg} is not a hex token`);
          continue;
        }
        const ratio = contrastRatio(fg, bg);
        if (ratio < pair.min) {
          failures.push(`${pair.row}: ${ratio.toFixed(2)} < ${pair.min}`);
        }
      }
      expect(failures, `${theme} pairs below their ratio`).toEqual([]);
    });
  }

  it('HC-UITK-001 self-check: the contrast function flags the legacy ink-tertiary pair', () => {
    // Legacy --color-ink-tertiary on the old canvas: the defect this row removes (2.69).
    const legacy = contrastRatio([154, 154, 154], [250, 250, 248]);
    expect(legacy).toBeLessThan(3);
    expect(contrastRatio([0, 0, 0], [255, 255, 255])).toBeCloseTo(21, 5);
  });
});

// ---------------------------------------------------------------------------
// HC-UITK-002: every colour utility used in the components resolves to a token.
// ---------------------------------------------------------------------------

/** Colours from the theme's `--color-*` tokens (a utility needs one to be generated). */
const THEME_COLOURS = new Set(
  [...declarations(ruleBodies(css, /@theme/)[0] ?? '').keys()]
    .filter((name) => name.startsWith('--color-'))
    .map((name) => name.slice('--color-'.length))
);

/** Tailwind's default palette, which Tailwind v4 generates without a project token. */
const DEFAULT_PALETTE =
  /^(?:(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-(?:50|100|200|300|400|500|600|700|800|900|950)|white|black|transparent|current|inherit)$/;

/** Utility suffixes after a colour prefix that are sizes, positions or styles, not colours. */
const NOT_A_COLOUR =
  /^(?:\d+(?:\.\d+)?%?|xs|sm|base|lg|xl|[2-9]xl|left|right|center|justify|start|end|balance|pretty|wrap|nowrap|ellipsis|clip|b|t|l|r|x|y|s|e|solid|dashed|dotted|double|none|hidden|inset|cover|contain|fixed|local|scroll|repeat|repeat-x|repeat-y|no-repeat|linear|linear-to-[a-z]+|radial|conic|uppercase|lowercase|capitalize|italic|normal-case|full)$/;

const COLOUR_PREFIX = /^(?:bg|text|border(?:-[trblxy])?|ring(?:-offset)?|outline|fill|stroke|from|via|to|divide|placeholder|decoration|accent|caret)-([^/]+)(?:\/.*)?$/;

/** The utility's colour name, or undefined when the class is not a colour utility. */
function colourName(token: string): string | undefined {
  const base = token.slice(token.lastIndexOf(':') + 1).replace(/^!/, '');
  const match = COLOUR_PREFIX.exec(base);
  if (!match) return undefined;
  const name = match[1] ?? '';
  if (/[[\]${}]/.test(name) || NOT_A_COLOUR.test(name)) return undefined;
  return name;
}

/** Every .tsx under src/, except tests (they name classes inside fixtures and strings). */
function componentFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === '__tests__' ? [] : componentFiles(path);
    return entry.name.endsWith('.tsx') && !entry.name.endsWith('.test.tsx') ? [path] : [];
  });
}

/** Class-name characters only, so prose and code fragments inside a literal are not read as classes. */
const CLASS_SYNTAX = /^[\w:/\-[\]!.%&>()#,=]+$/;

/** Whitespace-separated class tokens of every string literal in a .tsx file (JSX text is not read). */
function classTokens(source: string, file: string): string[] {
  const syntax = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, false, ts.ScriptKind.TSX);
  const literals: string[] = [];
  const visit = (node: ts.Node): void => {
    if (
      ts.isStringLiteral(node) ||
      ts.isNoSubstitutionTemplateLiteral(node) ||
      ts.isTemplateHead(node) ||
      ts.isTemplateMiddle(node) ||
      ts.isTemplateTail(node)
    ) {
      literals.push(node.text);
    }
    ts.forEachChild(node, visit);
  };
  visit(syntax);
  return literals.flatMap((text) => text.split(/\s+/)).filter((token) => CLASS_SYNTAX.test(token));
}

describe('UI-TOKENS utilities', () => {
  it('HC-UITK-002: every colour utility in src/**/*.tsx resolves to a defined token', () => {
    const undefinedUses: string[] = [];
    for (const file of componentFiles(SRC_ROOT)) {
      for (const token of classTokens(readFileSync(file, 'utf8'), file)) {
        const name = colourName(token);
        if (name === undefined) continue;
        if (THEME_COLOURS.has(name) || DEFAULT_PALETTE.test(name)) continue;
        undefinedUses.push(`${file.slice(SRC_ROOT.length)}: ${token}`);
      }
    }
    expect(undefinedUses, `${undefinedUses.length} undefined colour utilities`).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// HC-UITK-003: type floor and body size.
// ---------------------------------------------------------------------------

/** Pixels for a `px` or `rem` length (the html root is 16px); undefined otherwise. */
function lengthPx(value: string | undefined): number | undefined {
  const match = /^(-?\d+(?:\.\d+)?)(px|rem)$/.exec(value?.trim() ?? '');
  if (!match) return undefined;
  return Number(match[1]) * (match[2] === 'rem' ? 16 : 1);
}

describe('UI-TOKENS type', () => {
  it('HC-UITK-003: --text-xs is at least 13px', () => {
    const xs = declarations(ruleBodies(css, /@theme/)[0] ?? '').get('--text-xs');
    expect(lengthPx(xs), `--text-xs is ${xs}`).toBeGreaterThanOrEqual(13);
  });

  it('HC-UITK-003: body is 17px with a 26.4px line height', () => {
    const bodies = ruleBodies(css, /(?<![\w-])body/);
    const fontSize = bodies.map((body) => /font-size\s*:\s*([^;]+);/.exec(body)?.[1]).find(Boolean);
    const lineHeight = bodies.map((body) => /line-height\s*:\s*([^;]+);/.exec(body)?.[1]).find(Boolean);
    expect(lengthPx(fontSize), `body font-size is ${fontSize}`).toBe(17);
    expect(lengthPx(lineHeight), `body line-height is ${lineHeight}`).toBeCloseTo(26.4, 5);
  });
});

// ---------------------------------------------------------------------------
// DARK-PRIMITIVE-CONTRAST (HC-DPC-001, HC-DPC-002): the colour classes a primitive
// paints are read back as tokens and checked against the pair they sit on.
// ---------------------------------------------------------------------------

const THEMES = ['light', 'dark'] as const;
type Theme = (typeof THEMES)[number];

/** `--color-*` aliases from the @theme block: the names Tailwind turns into utilities. */
const THEME_ALIASES = declarations(ruleBodies(css, /@theme/)[0] ?? '');

/** Per theme: the aliases plus that theme's raw tokens, so `--color-accent` resolves to a hex. */
const RESOLVE: Record<Theme, Map<string, string>> = {
  light: new Map([...THEME_ALIASES, ...LIGHT]),
  dark: new Map([...THEME_ALIASES, ...DARK]),
};

/** Size, alignment and style suffixes that share a colour prefix (text-sm, border-2, border-t). They are not colours. */
const NOT_A_COLOUR_SUFFIX =
  /^(?:xs|sm|base|lg|xl|[2-9]xl|left|center|right|justify|start|end|balance|pretty|wrap|nowrap|ellipsis|clip|solid|dashed|dotted|double|none|[xytrblse]|(?:[xytrblse]-)?\d+)$/;

/**
 * State prefixes whose classes are skipped, and why. focus-visible adds a ring and a border colour but leaves the
 * text and fill alone. disabled is exempt from WCAG 1.4.3, and axe skips disabled controls. active only scales.
 * ring-*, ring-offset-*, shadow-* and outline-* paint no text, fill or border, so they are never read at all.
 * Any other prefix on a colour class is not skipped: it fails closed in readPaint.
 */
const SKIPPED_STATES: ReadonlySet<string> = new Set(['focus-visible', 'disabled', 'active']);

/** The slot a colour utility fills, keyed by its role (text, bg, border) and its state prefix ('' is rest). */
type Slot = 'text' | 'hoverText' | 'placeholderText' | 'bg' | 'hoverBg' | 'border';
const SLOT_OF: Record<string, Slot> = {
  'text|': 'text',
  'text|hover': 'hoverText',
  'text|placeholder': 'placeholderText',
  'bg|': 'bg',
  'bg|hover': 'hoverBg',
  'border|': 'border',
};

type Paint = Partial<Record<Slot, string>>;

function unmapped(cls: string): Error {
  return new Error(`unmapped colour class ${cls}`);
}

/** The CSS colour a colour utility paints with: a hex literal or a var() reference. Fails closed. */
function paintValue(name: string, cls: string): string {
  const bracket = /^\[(.*)\]$/.exec(name);
  if (bracket) {
    const reference = /^var\((--[\w-]+)\)$/.exec(bracket[1] ?? '');
    if (!reference) throw unmapped(cls);
    return `var(${reference[1] ?? ''})`;
  }
  if (name.includes('/')) throw unmapped(cls); // an opacity suffix such as /80
  if (name === 'white') return '#ffffff';
  if (name === 'black') return '#000000';
  if (!THEME_ALIASES.has(`--color-${name}`)) throw unmapped(cls);
  return `var(--color-${name})`;
}

/** Reads the colour utilities of one class string into the slots they fill. */
function readPaint(className: string): Paint {
  const paint: Paint = {};
  for (const cls of className.split(/\s+/).filter(Boolean)) {
    const parts = cls.split(':');
    const base = parts.pop() ?? '';
    const match = /^(bg|text|border)-(.+)$/.exec(base);
    if (!match) continue;
    const role = match[1] ?? '';
    const name = match[2] ?? '';
    if (NOT_A_COLOUR_SUFFIX.test(name)) continue;
    if (parts.length === 1 && SKIPPED_STATES.has(parts[0] ?? '')) continue;
    const slot = SLOT_OF[`${role}|${parts.join(':')}`];
    if (slot === undefined) throw unmapped(cls);
    const value = paintValue(name, cls);
    if (paint[slot] !== undefined) throw new Error(`two colour classes for ${slot} in "${className}"`);
    paint[slot] = value;
  }
  return paint;
}

/** A colour value (hex or var() reference) as RGB in one theme, or undefined when it does not resolve. */
function colourOf(value: string, theme: Theme): Rgb | undefined {
  const reference = /^var\((--[\w-]+)\)$/.exec(value);
  return parseHex(reference ? resolveToken(reference[1] ?? '', RESOLVE[theme]) : value);
}

interface ContrastCheck {
  label: string;
  ratio: number;
  min: number;
}

/** The contrast pairs one class string paints, in one theme. Throws when a pair cannot be read. */
function contrastChecks(className: string, theme: Theme): ContrastCheck[] {
  const paint = readPaint(className);
  const text = paint.text;
  const bg = paint.bg;
  if (text === undefined || bg === undefined) {
    throw new Error(`no rest text and rest background in "${className}"`);
  }
  const pairs: [label: string, fg: string, bgValue: string, min: number][] = [
    ['rest text on rest background', text, bg, TEXT_MIN],
    ['hover text on hover background', paint.hoverText ?? text, paint.hoverBg ?? bg, TEXT_MIN],
  ];
  if (paint.placeholderText !== undefined) {
    pairs.push(['placeholder text on rest background', paint.placeholderText, bg, TEXT_MIN]);
  }
  if (paint.border !== undefined) {
    pairs.push(['rest border on rest background', paint.border, bg, NON_TEXT_MIN]);
  }
  return pairs.map(([label, fg, bgValue, min]) => {
    const fgRgb = colourOf(fg, theme);
    const bgRgb = colourOf(bgValue, theme);
    if (!fgRgb || !bgRgb) throw new Error(`${label} in ${theme}: ${fg} or ${bgValue} is not a colour`);
    return { label, min, ratio: contrastRatio(fgRgb, bgRgb) };
  });
}

/** Logs every measured pair in both themes (the ratios are the evidence) and returns the ones below their minimum. */
function contrastFailures(className: string, id: string): string[] {
  const failures: string[] = [];
  for (const theme of THEMES) {
    for (const check of contrastChecks(className, theme)) {
      const line = `${id} ${theme} ${check.label}: ${check.ratio.toFixed(2)} (min ${check.min})`;
      console.log(line);
      if (check.ratio < check.min) failures.push(line);
    }
  }
  return failures;
}

/** The class string an Input renders with the given props, after its cn() call. */
function renderedInputClass(props: InputProps): string {
  const { container, unmount } = render(createElement(Input, props));
  try {
    const field = container.querySelector('input');
    if (!field) throw new Error('Input rendered no <input>');
    return field.className;
  } finally {
    unmount();
  }
}

describe('DARK-PRIMITIVE-CONTRAST', () => {
  it('HC-DPC-001: primary Button text reaches 4.5:1 on its fill, light and dark, at rest and on hover', () => {
    // The default variant must be the primary one, so a caller that passes nothing gets the same pair.
    const primary = buttonVariants({ variant: 'primary' });
    expect(buttonVariants({})).toBe(primary);
    expect(contrastFailures(primary, 'HC-DPC-001'), 'primary Button pairs below their ratio').toEqual([]);
  });

  it('HC-DPC-002: Input value and placeholder reach 4.5:1 on the field, and its border 3:1, light and dark', () => {
    const states: [string, InputProps][] = [
      ['rest', { label: 'Field' }],
      ['error', { label: 'Field', error: 'Required' }],
    ];
    const failures: string[] = [];
    for (const [state, props] of states) {
      const className = renderedInputClass(props);
      // A pair the mapper does not see would pass without a check, so each required pair must be present.
      const labels = THEMES.flatMap((theme) => contrastChecks(className, theme).map((check) => check.label));
      for (const required of [
        'rest text on rest background',
        'placeholder text on rest background',
        'rest border on rest background',
      ]) {
        expect(labels, `${state} Input has no "${required}" pair`).toContain(required);
      }
      failures.push(...contrastFailures(className, `HC-DPC-002 ${state}`));
    }
    expect(failures, 'Input pairs below their ratio').toEqual([]);
  });

  it('HC-DPC-001 self-check: the mapper fails closed on what it cannot read', () => {
    for (const cls of [
      'bg-[#ffffff]',
      'bg-accent/80',
      'dark:bg-white',
      'md:text-white',
      'placeholder:bg-accent',
      'text-gray-500',
    ]) {
      expect(() => contrastChecks(`text-white bg-accent ${cls}`, 'light'), cls).toThrow(
        `unmapped colour class ${cls}`
      );
    }
    expect(() => contrastChecks('bg-accent', 'light')).toThrow('no rest text and rest background');
  });
});
