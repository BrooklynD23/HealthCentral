// UI-BUDGET (HC-UIBG-001, HC-UIBG-002): the bundle budget check can fail.
//
// scripts/check-bundle.mjs is a plain .mjs file and tsconfig has no allowJs, so
// it is loaded by path at run time; a static import would fail tsc (TS7016).
// The committed fixture is a tiny dist-shaped folder that covers every budget.
// Every over-budget case is generated here, not committed.

import { describe, it, expect } from 'vitest';
import { resolve } from 'node:path';

interface BundleFile {
  path: string;
  bytes: Uint8Array;
}

interface BudgetRow {
  name: string;
  status: 'PASS' | 'FAIL' | 'absent';
  measuredKb: number | null;
  limitKb: number;
  detail: string;
}

interface BundleCheckModule {
  checkBudgets: (files: BundleFile[], budgets: unknown[]) => { ok: boolean; rows: BudgetRow[] };
  BUDGETS: { name: string }[];
  readDist: (dir: string) => BundleFile[];
}

const SCRIPT = resolve(__dirname, '../../scripts/check-bundle.mjs');
const FIXTURE = resolve(__dirname, '../../scripts/__fixtures__/bundle');
const ENTRY = 'assets/index-fx01.js';
const PALETTE_IMPORT = 'import("./CommandPalette-fx07.js");';
const enc = new TextEncoder();
const dec = new TextDecoder();

async function loadCheck(): Promise<BundleCheckModule> {
  return (await import(/* @vite-ignore */ SCRIPT)) as BundleCheckModule;
}

// The entry is the module script that index.html names. The fixture has a
// decoy index-fx00.js that sorts before it, as Vite's re-export shim does.
function entryOf(files: BundleFile[]): string {
  const html = dec.decode(files.find((f) => f.path === 'index.html')?.bytes);
  const m = /<script[^>]*type="module"[^>]*src="\/([^"]+)"/.exec(html);
  if (!m) throw new Error('fixture index.html names no module entry');
  return m[1];
}

// Seeded, incompressible bytes (xorshift32). gzip cannot shrink them, so the
// measured size is the byte count plus gzip framing.
function incompressible(length: number, seed: number): Uint8Array {
  const out = new Uint8Array(length);
  let s = seed >>> 0 || 1;
  for (let i = 0; i < length; i++) {
    s = (s ^ (s << 13)) >>> 0;
    s = (s ^ (s >>> 17)) >>> 0;
    s = (s ^ (s << 5)) >>> 0;
    out[i] = s & 0xff;
  }
  return out;
}

function appendBytes(bytes: Uint8Array, extra: Uint8Array): Uint8Array {
  const out = new Uint8Array(bytes.length + extra.length);
  out.set(bytes, 0);
  out.set(extra, bytes.length);
  return out;
}

function replaceBytes(files: BundleFile[], path: string, bytes: Uint8Array): BundleFile[] {
  return files.map((f) => (f.path === path ? { path, bytes } : f));
}

// The fixture entry imports the palette with import(); remove both the file and that import.
function withoutPalette(files: BundleFile[]): BundleFile[] {
  const text = dec.decode(files.find((f) => f.path === ENTRY)?.bytes);
  if (!text.includes(PALETTE_IMPORT)) throw new Error('fixture entry no longer imports the palette');
  return files
    .filter((f) => f.path !== 'assets/CommandPalette-fx07.js')
    .map((f) => (f.path === ENTRY ? { path: f.path, bytes: enc.encode(text.replace(PALETTE_IMPORT, '')) } : f));
}

function failedNames(rows: BudgetRow[]): string[] {
  return rows.filter((r) => r.status === 'FAIL').map((r) => r.name);
}

describe('HC-UIBG-001: an over-budget chunk fails and names the budget', () => {
  it('a 166 kB gz main chunk makes checkBudgets fail with the main JS budget', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const files = readDist(FIXTURE);
    const over = files.map((f) =>
      f.path === ENTRY ? { path: f.path, bytes: appendBytes(f.bytes, incompressible(166_000, 7)) } : f,
    );

    const result = checkBudgets(over, BUDGETS);

    expect(result.ok).toBe(false);
    expect(failedNames(result.rows)).toEqual(['main JS']);
    const main = result.rows.find((r) => r.name === 'main JS');
    expect(main?.measuredKb).toBeGreaterThan(165);
    expect(main?.measuredKb).toBeLessThan(167);
    expect(main?.detail).toContain(ENTRY);
  });

  it('a required route chunk that is missing fails closed', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const files = readDist(FIXTURE).filter((f) => !f.path.startsWith('assets/DocumentInbox-'));

    const result = checkBudgets(files, BUDGETS);

    expect(result.ok).toBe(false);
    expect(result.rows.find((r) => r.name === 'route DocumentInbox')?.status).toBe('FAIL');
  });

  it('a lazy chunk the entry loads that no named row covers still fails at 40 kB gz', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const over = replaceBytes(readDist(FIXTURE), 'assets/ExplainAssistant-fx12.js', incompressible(40_000, 11));

    const result = checkBudgets(over, BUDGETS);

    expect(result.ok).toBe(false);
    expect(failedNames(result.rows)).toEqual(['route chunks (each)']);
    expect(result.rows.find((r) => r.name === 'route chunks (each)')?.detail).toContain(
      'assets/ExplainAssistant-fx12.js',
    );
  });

  it('a 26 kB gz CSS file fails the CSS budget (sum mode is enforced)', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const over = replaceBytes(readDist(FIXTURE), 'assets/index-fx03.css', incompressible(26_000, 13));

    const result = checkBudgets(over, BUDGETS);

    expect(result.ok).toBe(false);
    expect(failedNames(result.rows)).toEqual(['CSS']);
  });

  it('a 210 kB gz dependency two static imports below ResultsPage fails Results total', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const over = replaceBytes(readDist(FIXTURE), 'assets/results-deep-fx13.js', incompressible(210_000, 17));

    const result = checkBudgets(over, BUDGETS);

    expect(result.ok).toBe(false);
    expect(failedNames(result.rows)).toEqual(['Results total']);
  });

  it('a 210 kB chart that ResultsPage loads with import() fails Results total', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const over = replaceBytes(readDist(FIXTURE), 'assets/chart-fx14.js', incompressible(210_000, 19));

    const result = checkBudgets(over, BUDGETS);

    expect(result.ok).toBe(false);
    expect(failedNames(result.rows)).toEqual(['Results total']);
  });

  it('a 16 kB gz thinking-orbs chunk fails its budget, though Vite names it index.es-*', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const over = replaceBytes(readDist(FIXTURE), 'assets/index.es-fx15.js', incompressible(16_000, 23));

    const result = checkBudgets(over, BUDGETS);

    expect(result.ok).toBe(false);
    expect(failedNames(result.rows)).toEqual(['thinking-orbs']);
    expect(result.rows.find((r) => r.name === 'thinking-orbs')?.detail).toContain('assets/index.es-fx15.js');
  });

  it('a preloaded vendor chunk counts toward total first-load JS, and main JS still passes', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const files = replaceBytes(readDist(FIXTURE), 'assets/vendor-fx02.js', incompressible(100_000, 29));
    const over = files.map((f) =>
      f.path === ENTRY ? { path: f.path, bytes: appendBytes(f.bytes, incompressible(105_000, 31)) } : f,
    );

    const result = checkBudgets(over, BUDGETS);

    expect(result.ok).toBe(false);
    expect(failedNames(result.rows)).toEqual(['total first-load JS']);
    const total = result.rows.find((r) => r.name === 'total first-load JS');
    expect(total?.measuredKb).toBeGreaterThan(200);
    expect(total?.detail).toContain('assets/vendor-fx02.js');
  });

  it('an index.html with two module scripts fails closed: main JS and total first-load JS both FAIL', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const files = readDist(FIXTURE);
    const html = dec.decode(files.find((f) => f.path === 'index.html')?.bytes);
    const twoEntries = html.replace(
      '</head>',
      '    <script type="module" crossorigin src="/assets/index-fx00.js"></script>\n  </head>',
    );
    expect(twoEntries).not.toBe(html);

    const result = checkBudgets(replaceBytes(files, 'index.html', enc.encode(twoEntries)), BUDGETS);

    expect(result.ok).toBe(false);
    expect(result.rows.find((r) => r.name === 'main JS')?.status).toBe('FAIL');
    expect(result.rows.find((r) => r.name === 'total first-load JS')?.status).toBe('FAIL');
  });
});

describe('HC-UIBG-002: a fixture under every budget passes', () => {
  it('every budget has a row and every row PASSes on the committed fixture', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();

    const result = checkBudgets(readDist(FIXTURE), BUDGETS);

    expect(result.rows.map((r) => r.name)).toEqual(BUDGETS.map((b) => b.name));
    expect(result.rows.filter((r) => r.status !== 'PASS')).toEqual([]);
    expect(result.ok).toBe(true);
  });

  it('the main row measures the entry that index.html names, not a name match', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const files = readDist(FIXTURE);

    expect(entryOf(files)).toBe(ENTRY);
    const main = checkBudgets(files, BUDGETS).rows.find((r) => r.name === 'main JS');
    expect(main?.detail).toBe(ENTRY);
  });

  it('an absent optional chunk prints absent and does not fail the build', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();

    const result = checkBudgets(withoutPalette(readDist(FIXTURE)), BUDGETS);

    const palette = result.rows.find((r) => r.name === 'palette (CommandPalette)');
    expect(palette?.status).toBe('absent');
    expect(palette?.measuredKb).toBeNull();
    expect(result.ok).toBe(true);
  });
});
