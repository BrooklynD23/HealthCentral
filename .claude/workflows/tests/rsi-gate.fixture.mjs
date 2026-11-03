// Adversarial fixture for the rsi-loop deterministic gate (RSI-GATE-ADVERSARIAL).
// Extracts MOD, ALLOW/DENY/gateDiff/gateNumstat and parseCodexVerdict from rsi-loop.js
// (a workflow script, not importable) and asserts a table of paths and verdict lines.
// Run from anywhere: node .claude/workflows/tests/rsi-gate.fixture.mjs   (Node 22+, no deps)
// Prints metadata only: row labels and ok flags, never prompts or command text.
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import assert from 'node:assert/strict'

const src = readFileSync(fileURLToPath(new URL('../rsi-loop.js', import.meta.url)), 'utf8').split('\n')

function die(msg) { console.error(`gate fixture: ${msg}`); process.exit(1) }

// Lines from the first one matching `start` through the first one matching `end` at or after it (same line allowed).
function extract(label, start, end, mustContain) {
  const i = src.findIndex((l) => start.test(l))
  if (i < 0) die(`${label}: start marker not found`)
  const j = src.findIndex((l, k) => k >= i && end.test(l))
  if (j < 0) die(`${label}: end marker not found`)
  const code = src.slice(i, j + 1).join('\n')
  for (const name of mustContain) if (!code.includes(name)) die(`${label}: extracted range is missing ${name}`)
  return code
}

const modLine = extract('MOD', /^const MOD = /, /^const MOD = /, ['MOD'])
const gateCode = extract('gate', /^const ALLOW = \[/, /^const namesOf/, ['ALLOW', 'DENY', 'function gateDiff', 'function gateNumstat', 'namesOf'])
const verdictCode = extract('verdict', /^function parseCodexVerdict\(/, /^}/, ['parseCodexVerdict'])

const { MOD, ALLOW, DENY, gateDiff, gateNumstat, parseCodexVerdict } =
  new Function(`${modLine}\n${gateCode}\n${verdictCode}\nreturn { MOD, ALLOW, DENY, gateDiff, gateNumstat, parseCodexVerdict }`)()
if (typeof gateDiff !== 'function' || typeof gateNumstat !== 'function' || typeof parseCodexVerdict !== 'function' || !Array.isArray(DENY)) die('extracted code did not evaluate to the expected shapes')

const RULES = `${MOD}/hooks/rules.ts`
const CASES = `${MOD}/replay/cases.ts`
const RF = 'docs/agentic/recurring-failures.md'

const rows = []
const failures = []
function row(label, fn) {
  rows.push(label)
  try { fn() } catch (e) { failures.push(`${label}: ${e.detail ?? (e.actual !== undefined ? `actual ${JSON.stringify(e.actual)}` : e.message.split('\n')[0])}`) }
}
const fail = (detail) => Object.assign(new Error(detail), { detail })
const rejects = (r, sub) => {
  if (r.ok !== false) throw fail(`actual ok=${r.ok}, wanted ok=false`)
  if (sub && !r.violations.some((v) => v.includes(sub))) throw fail(`ok=false but no violation contains "${sub}"`)
}
const accepts = (r) => { if (r.ok !== true) throw fail(`actual ok=${r.ok} (${r.violations.length} violation(s)), wanted ok=true`) }

// (a) plan Fact 3 rows
row('diff reject: dot-dot inside allowed path', () => rejects(gateDiff([`${MOD}/hooks/../hooks/rules.ts`])))
row('diff reject: Scripts/x.sh (case)', () => rejects(gateDiff(['Scripts/x.sh'])))
row('diff reject: .\\scripts\\x.sh (backslash)', () => rejects(gateDiff(['.\\scripts\\x.sh'])))
row('diff reject: mod test file', () => rejects(gateDiff([`${MOD}/rsi.test.ts`])))
row('diff reject: rsi-loop.js itself', () => rejects(gateDiff(['.claude/workflows/rsi-loop.js'])))
row('diff reject: empty list', () => rejects(gateDiff([]), 'empty diff'))
row('diff reject: one allowed plus one outside', () => rejects(gateDiff([RULES, 'src/backend/main.py']), 'outside allow-list'))
row('diff accept: ./ prefix on allowed path', () => accepts(gateDiff([`./${RULES}`])))
row('numstat reject: deletion in rules.ts', () => rejects(gateNumstat(`1\t2\t${RULES}`)))
row('numstat reject: binary row', () => rejects(gateNumstat(`-\t-\t${RULES}`)))
row('numstat reject: empty input', () => rejects(gateNumstat(''), 'empty numstat'))
for (const [input, want] of [
  ['﻿VERDICT: PASS', 'PASS'],
  ['VERDICT: PASS\r', 'PASS'],
  ['VERDICT: PASS\r\nbody', 'PASS'],
  ['VERDICT: REVISE', 'REVISE'],
  [' VERDICT: PASS', 'UNAVAILABLE'],
  ['verdict: pass', 'UNAVAILABLE'],
  ['VERDICT: PASS and REVISE', 'UNAVAILABLE'],
  [null, 'UNAVAILABLE'],
]) row(`verdict ${JSON.stringify(input)} -> ${want}`, () => assert.equal(parseCodexVerdict(input), want))

// (b) one path per DENY entry names its reason
for (const [p, why] of [
  ['src/backend/tests/x.py', 'tests'], ['__tests__/x', 'tests'], ['e2e/x', 'tests'], ['a.test.ts', 'tests'], ['test_x.py', 'tests'],
  ['scripts/x', 'gate scripts'], ['.github/x', 'gate scripts'],
  ['docs/threshold.md', 'thresholds'],
  ['src/backend/modules/interpret_safety.py', 'ask-first'], ['src/backend/modules/redaction.py', 'ask-first'],
  ['src/backend/modules/faithfulness.py', 'ask-first'], ['src/backend/modules/verifier_agent.py', 'ask-first'],
  ['src/backend/core/auth.py', 'ask-first'], ['src/backend/security/encryption/x', 'ask-first'],
]) row(`deny ${p} -> ${why}`, () => rejects(gateDiff([p]), `denied (${why})`))
row('deny table has 14 entries', () => assert.equal(DENY.length, 14))

// (c) escapes
row('escape: absolute path', () => rejects(gateDiff(['/etc/x']), 'path escapes repo'))
row('escape: leading ..', () => rejects(gateDiff(['../x']), 'path escapes repo'))
row('escape: nested ..', () => rejects(gateDiff(['docs/../../x']), 'path escapes repo'))

// (d) allow-list is pinned, and each member passes alone
row('allow-list is exactly the three known paths', () => assert.deepEqual([...ALLOW], [RULES, CASES, RF]))
for (const p of ALLOW) row(`allow accepts ${p}`, () => accepts(gateDiff([p])))

// (e) rename pair: numstat skips the brace-rename row, so gateDiff on the new name is what fails the candidate
row('rename pair: numstat passes the rename row', () => accepts(gateNumstat(`1\t0\t${MOD}/hooks/{rules.ts => r.ts}`)))
row('rename pair: diff fails the new name', () => rejects(gateDiff([`${MOD}/hooks/r.ts`]), 'outside allow-list'))

// (f) additions-only, including recurring-failures.md (the gap)
row('numstat reject: recurring-failures 0 added 12 deleted', () => rejects(gateNumstat(`0\t12\t${RF}`), '12 deleted'))
row('numstat reject: recurring-failures 3 added 1 deleted', () => rejects(gateNumstat(`3\t1\t${RF}`), '1 deleted'))
row('numstat reject: recurring-failures binary row', () => rejects(gateNumstat(`-\t-\t${RF}`)))
row('numstat accept: recurring-failures 5 added 0 deleted', () => accepts(gateNumstat(`5\t0\t${RF}`)))
row('numstat accept: rules.ts additions only', () => accepts(gateNumstat(`4\t0\t${RULES}\n2\t0\t${CASES}`)))
row('numstat reject: cases.ts deletion among clean rows', () => rejects(gateNumstat(`4\t0\t${RULES}\n2\t1\t${CASES}`)))

if (failures.length) {
  console.error(`gate FAILED (${failures.length} of ${rows.length} rows):`)
  for (const f of failures) console.error(`  FAIL ${f}`)
  process.exit(1)
}
console.log(`gate ok (${rows.length})`)
