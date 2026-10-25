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
