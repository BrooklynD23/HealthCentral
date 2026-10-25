// UI-BUDGET: gzip budgets for the production build (plan §5, values copied as-is).
//
//   node scripts/check-bundle.mjs [distDir]     (default: dist, after `npm run build`)
//
// Exit 1 on any FAIL, naming the budget. A required chunk that is missing fails
// closed. An optional chunk ("when present") prints `absent`, never silently.
// The main chunk and the first-load set come from dist/index.html, not from a
// file-name glob: Vite also writes a tiny index-*.js re-export shim.
// Lazy sets follow the import graph of the emitted JS. "route chunks" are every
// module the entry loads with import(). "Results total" is main plus the Results
// page and everything it reaches by static or dynamic import (its chart included).
// Shared chunks that only static importers load are not route chunks.
// kB = 1000 bytes, the unit Vite prints in its gzip column.

import { gzipSync } from 'node:zlib';
import { readdirSync, readFileSync } from 'node:fs';
import { join, posix, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const KB = 1000;
const ASSETS = 'assets/';
// import x from "./a.js", import "./a.js", export {x} from "./a.js"
const STATIC_RE = /\b(?:from|import)\s*["'](\.{1,2}\/[^"']+)["']/g;
// import("./a.js"): how Vite loads each lazy route and the palette
const DYNAMIC_RE = /\bimport\(\s*["'](\.{1,2}\/[^"']+)["']\s*\)/g;

export const BUDGETS = [
  { name: 'main JS', limitKb: 165, required: true, mode: 'each', pick: (c) => [c.entry] },
  { name: 'route chunks (each)', limitKb: 30, required: true, mode: 'each', pick: (c) => c.routeChunks() },
  { name: 'route DocumentInbox', limitKb: 30, required: true, mode: 'each', pick: (c) => c.find(/^DocumentInbox-/) },
  { name: 'route VerificationWorkbench', limitKb: 30, required: true, mode: 'each', pick: (c) => c.find(/^VerificationWorkbench-/) },
  { name: 'route SettingsPage', limitKb: 30, required: true, mode: 'each', pick: (c) => c.find(/^SettingsPage-/) },
  { name: 'CSS', limitKb: 25, required: true, mode: 'sum', pick: (c) => c.cssFiles() },
  { name: 'total first-load JS', limitKb: 200, required: true, mode: 'sum', pick: (c) => [c.entry, ...c.preload] },
  { name: 'palette (CommandPalette)', limitKb: 8, required: false, mode: 'each', pick: (c) => c.find(/^CommandPalette-/) },
  { name: 'thinking-orbs', limitKb: 15, required: false, mode: 'each', pick: (c) => c.find(/^(?:ThinkingOrb|thinking-orbs)-/) },
  { name: 'Results total', limitKb: 205, required: false, mode: 'sum', pick: (c) => c.resultsGroup() },
];

// Reads every file under dist (except source maps) as { path, bytes }, with
// '/'-separated paths relative to the folder. A missing folder throws.
export function readDist(dir) {
  const out = [];
  const walk = (abs, rel) => {
    for (const entry of readdirSync(abs, { withFileTypes: true })) {
      const childAbs = join(abs, entry.name);
      const childRel = rel ? `${rel}/${entry.name}` : entry.name;
      if (entry.isDirectory()) walk(childAbs, childRel);
      else if (entry.isFile() && !entry.name.endsWith('.map')) {
        out.push({ path: childRel, bytes: readFileSync(childAbs) });
      }
    }
  };
  walk(resolve(dir), '');
  return out;
}

function parseIndexHtml(html) {
  const attr = (tag, name) => tag.match(new RegExp(`\\b${name}="([^"]+)"`))?.[1];
  const normalize = (src) => src.replace(/^\.?\//, '');
  const moduleScripts = (html.match(/<script\b[^>]*>/gi) ?? [])
    .filter((t) => /\btype="module"/i.test(t))
    .map((t) => attr(t, 'src'))
    .filter(Boolean);
  const preloads = (html.match(/<link\b[^>]*>/gi) ?? [])
    .filter((t) => /\brel="modulepreload"/i.test(t))
    .map((t) => attr(t, 'href'))
    .filter(Boolean)
    .map(normalize);
  // More than one module script is ambiguous: null makes the main budget fail closed.
  const entry = moduleScripts.length === 1 ? normalize(moduleScripts[0]) : null;
  return { entry, preload: preloads };
}

// Edges out of one emitted JS file, as paths relative to the dist folder.
function edgesOf(page, bytes) {
  const text = Buffer.from(bytes).toString('utf8');
  const target = (m) => posix.join(posix.dirname(page), m[1]);
  return {
    statics: [...text.matchAll(STATIC_RE)].map(target),
    dynamics: [...text.matchAll(DYNAMIC_RE)].map(target),
  };
}

// Every file reachable from `start` through static or dynamic imports, sorted.
// Missing files stay in the result so evaluate() reports them. The entry is not
// walked into: it is counted once, as main, and its import() list is the route set.
function reachable(start, byPath, entry) {
  const seen = new Set();
  const stack = [start];
  while (stack.length > 0) {
    const page = stack.pop();
    if (seen.has(page)) continue;
    seen.add(page);
    if (page === entry || !byPath.has(page) || !page.endsWith('.js')) continue;
    const { statics, dynamics } = edgesOf(page, byPath.get(page));
    stack.push(...statics, ...dynamics);
  }
  return [...seen].sort();
}

const row = (budget, status, measuredKb, detail) => ({
  name: budget.name,
  status,
  measuredKb,
  limitKb: budget.limitKb,
  detail,
});

function evaluate(budget, picker, byPath, gzOf) {
  const limit = budget.limitKb * KB;
  const paths = budget.pick(picker);
  if (paths.length === 0) {
    return budget.required
      ? row(budget, 'FAIL', null, 'required chunk not found in the build')
      : row(budget, 'absent', null, 'not in this build');
  }
  const missing = paths.filter((p) => p === null || !byPath.has(p));
  if (missing.length > 0) {
    return row(budget, 'FAIL', null, `missing file: ${missing.map(String).join(', ')}`);
  }
  if (budget.mode === 'sum') {
    const unique = [...new Set(paths)];
    const total = unique.reduce((n, p) => n + gzOf(p), 0);
    return row(budget, total > limit ? 'FAIL' : 'PASS', total / KB, unique.join(' + '));
  }
  let worst = null;
  const over = [];
  for (const p of paths) {
    const g = gzOf(p);
    if (g > limit) over.push(p);
    if (worst === null || g > worst.g) worst = { p, g };
  }
  if (over.length > 0) {
    return row(budget, 'FAIL', worst.g / KB, `over by ${((worst.g - limit) / KB).toFixed(2)} kB: ${over.join(', ')}`);
  }
  return row(budget, 'PASS', worst.g / KB, worst.p);
}

// Pure: no file reads, no printing. `files` is [{ path, bytes }] as readDist returns.
export function checkBudgets(files, budgets = BUDGETS) {
  const byPath = new Map(files.map((f) => [f.path, f.bytes]));
  const gzCache = new Map();
  const gzOf = (p) => {
    if (!gzCache.has(p)) gzCache.set(p, gzipSync(byPath.get(p)).length);
    return gzCache.get(p);
  };
  const html = byPath.has('index.html') ? Buffer.from(byPath.get('index.html')).toString('utf8') : '';
  const { entry, preload } = parseIndexHtml(html);
  const find = (re) =>
    [...byPath.keys()].filter((p) => p.startsWith(ASSETS) && re.test(p.slice(ASSETS.length))).sort();
  const entryDynamics =
    entry !== null && byPath.has(entry) ? edgesOf(entry, byPath.get(entry)).dynamics : [];
  const picker = {
    entry,
    preload,
    find,
    cssFiles: () => [...byPath.keys()].filter((p) => p.endsWith('.css')).sort(),
    routeChunks: () => [...new Set(entryDynamics)].sort(),
    resultsGroup: () => {
      const [page] = find(/^ResultsPage-/);
      if (!page) return [];
      return [...new Set([entry, ...reachable(page, byPath, entry)])];
    },
  };
  const rows = budgets.map((b) => evaluate(b, picker, byPath, gzOf));
  return { ok: rows.every((r) => r.status !== 'FAIL'), rows };
}

function formatTable(rows) {
  const head = `${'budget'.padEnd(30)}${'measured'.padStart(12)}${'limit'.padStart(12)}  ${'status'.padEnd(7)}detail`;
  const body = rows.map((r) => {
    const measured = r.measuredKb === null ? '-' : `${r.measuredKb.toFixed(2)} kB`;
    return `${r.name.padEnd(30)}${measured.padStart(12)}${`${r.limitKb} kB`.padStart(12)}  ${r.status.padEnd(7)}${r.detail}`;
  });
  return [head, ...body].join('\n');
}

const isCli = process.argv[1] !== undefined && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;
if (isCli) {
  try {
    const dir = resolve(process.argv[2] ?? 'dist');
    const { ok, rows } = checkBudgets(readDist(dir), BUDGETS);
    console.log(`bundle budgets (gzip, kB = 1000 bytes): ${dir}`);
    console.log(formatTable(rows));
    if (ok) {
      console.log('all bundle budgets PASS');
    } else {
      const failed = rows.filter((r) => r.status === 'FAIL').map((r) => r.name);
      console.error(`bundle budget FAIL: ${failed.join(', ')}`);
      process.exitCode = 1;
    }
  } catch (err) {
    console.error(`check-bundle: ${err.message}`);
    process.exitCode = 1;
  }
}
