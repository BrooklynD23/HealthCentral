// UI-BUDGET (HC-UIBG-001, HC-UIBG-002): the bundle budget check can fail.
//
// scripts/check-bundle.mjs is a plain .mjs file and tsconfig has no allowJs, so
// it is loaded by path at run time; a static import would fail tsc (TS7016).
// The committed fixture is a tiny dist-shaped folder that covers every budget.
// The over-budget case is generated here, not committed.

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
  BUDGETS: unknown[];
  readDist: (dir: string) => BundleFile[];
}

const SCRIPT = resolve(__dirname, '../../scripts/check-bundle.mjs');
const FIXTURE = resolve(__dirname, '../../scripts/__fixtures__/bundle');

async function loadCheck(): Promise<BundleCheckModule> {
  return (await import(/* @vite-ignore */ SCRIPT)) as BundleCheckModule;
}

// The entry is the module script that index.html names. The fixture has two
// index-*.js files (the entry and a re-export shim), so a name glob is not enough.
function entryOf(files: BundleFile[]): string {
  const html = new TextDecoder().decode(files.find((f) => f.path === 'index.html')?.bytes);
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

describe('HC-UIBG-001: an over-budget main chunk fails and names the budget', () => {
  it('a 166 kB gz main chunk makes checkBudgets fail with the main JS budget', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const files = readDist(FIXTURE);
    const entry = entryOf(files);
    const over = files.map((f) =>
      f.path === entry ? { path: f.path, bytes: incompressible(166_000, 7) } : f,
    );

    const result = checkBudgets(over, BUDGETS);

    expect(result.ok).toBe(false);
    const failed = result.rows.filter((r) => r.status === 'FAIL');
    expect(failed.map((r) => r.name)).toEqual(['main JS']);
    expect(failed[0].measuredKb).toBeGreaterThan(165);
    expect(failed[0].measuredKb).toBeLessThan(167);
  });

  it('a required route chunk that is missing fails closed', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();
    const files = readDist(FIXTURE).filter((f) => !f.path.startsWith('assets/DocumentInbox-'));

    const result = checkBudgets(files, BUDGETS);

    expect(result.ok).toBe(false);
    expect(result.rows.find((r) => r.name.includes('DocumentInbox'))?.status).toBe('FAIL');
  });
});

describe('HC-UIBG-002: a fixture under every budget passes', () => {
  it('every budget has a row and every row PASSes on the committed fixture', async () => {
    const { checkBudgets, BUDGETS, readDist } = await loadCheck();

    const result = checkBudgets(readDist(FIXTURE), BUDGETS);

    expect(result.rows.map((r) => r.name)).toEqual(
      (BUDGETS as { name: string }[]).map((b) => b.name),
    );
    expect(result.rows.filter((r) => r.status !== 'PASS')).toEqual([]);
    expect(result.ok).toBe(true);
  });
});
