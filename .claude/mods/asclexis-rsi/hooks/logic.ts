import { RULES, type Rule } from './rules'

export type Row = {
  v: 1
  ts: string
  session: string
  kind: 'tool'
  tool: string
  ok: boolean
  duration_ms: number | null
  denied: boolean
  guard: string | null
  hint: string | null
  error_class: string | null
  retry: boolean
  edit_test_fail: boolean
  cmd_sig?: CmdSig
}

const EDIT_TOOLS = ['Edit', 'Write', 'MultiEdit', 'NotebookEdit']
const TEST_CMD = /\b(?:pytest|vitest|playwright\s+test|npm\s+(?:run\s+)?test|npm\s+t)\b/

/** Non-reversible 32-bit FNV-1a of the input. Held in memory only, never logged. */
export function fingerprint(tool: string, input: unknown): string {
  const s = tool + JSON.stringify(input ?? null)
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193)
  return (h >>> 0).toString(16)
}

const cmdOf = (tool: string, input: unknown): string =>
  tool === 'Bash' && input && typeof (input as { command?: unknown }).command === 'string'
    ? (input as { command: string }).command
    : ''

const FIELD_MAX = 200

/**
 * The one fixed, non-free-text input field a rule may test, per tool; '' when none applies.
 * Bash: command. Workflow: name, else a safe scriptPath basename. Skill: skill. Agent: subagent_type.
 * mcp__<server>__<tool>: <server>, parsed from the tool name. Never prompt, args, description or content.
 * Non-Bash values longer than FIELD_MAX give ''; Bash command is returned whole, as cmdOf does.
 * Held in memory only; callers never log it.
 */
export function fieldOf(tool: string, input: unknown): string {
  const o = input && typeof input === 'object' && !Array.isArray(input) ? (input as Record<string, unknown>) : {}
  const str = (k: string): string => (typeof o[k] === 'string' ? (o[k] as string) : '')
  if (typeof tool !== 'string') return ''
  // Bash is uncapped, exactly as cmdOf: a cap would silently skip every deny/hint rule on long commands.
  if (tool === 'Bash') return str('command')
  let v = ''
  if (tool === 'Workflow') {
    v = str('name')
    if (!v) {
      const base = (str('scriptPath').split('/').pop() ?? '').replace(/\.js$/, '')
      v = /^[A-Za-z0-9._-]+$/.test(base) ? base : ''
    }
  } else if (tool === 'Skill') v = str('skill')
  else if (tool === 'Agent') v = str('subagent_type')
  else if (tool.startsWith('mcp__')) v = tool.split('__')[1] ?? ''
  return v.length <= FIELD_MAX ? v : ''
}

const toolMatches = (ruleTool: string, tool: string): boolean =>
  ruleTool === tool || (ruleTool === 'mcp__*' && typeof tool === 'string' && tool.startsWith('mcp__'))

/** First `before`/deny rule that matches this call, if any. */
export function checkBefore(tool: string, input: unknown, rules: readonly Rule[] = RULES): Rule | undefined {
  const field = fieldOf(tool, input)
  return rules.find(r => r.when === 'before' && r.action === 'deny' && toolMatches(r.tool, tool) && new RegExp(r.match).test(field))
}

/** First `after` rule that matches the finished call, if any. */
export function checkAfter(
  tool: string,
  input: unknown,
  text: string,
  failed: boolean,
  rules: readonly Rule[] = RULES,
): Rule | undefined {
  const field = fieldOf(tool, input)
  return rules.find(
    r =>
      r.when === 'after' &&
      toolMatches(r.tool, tool) &&
      (failed || r.onSuccess === true) &&
      (r.command === undefined || new RegExp(r.command).test(field)) &&
      new RegExp(r.match).test(text) &&
      (r.absent === undefined || !new RegExp(r.absent).test(text)),
  )
}

/**
 * Fixed error category for a failure no rule claimed. Never raw text.
 * Order matters: tool-error envelopes (anchored with ^, some gated on `tool`) win first,
 * so they can never fall through to a Bash shape; then the first four Bash checks,
 * then common Bash failure shapes, then a bounded `exit-<n>` (1-255) from the
 * `Exit code` line, else 'other'.
 * Returns only fixed literals or `exit-` plus captured digits, never input text.
 */
export function classifyError(text: string, tool = ''): string {
  if (/^Permission for this action was denied by the Claude Code auto mode classifier\./.test(text)) return 'permission-denied-auto'
  if (/^<tool_use_error>InputValidationError: /.test(text)) return 'input-validation'
  if (/^<tool_use_error>Error: No such tool available: /.test(text)) return 'no-such-tool'
  if (EDIT_TOOLS.includes(tool) && /^<tool_use_error>File has not been read yet\. /.test(text)) return 'edit-not-read'
  if (tool === 'Read' && /^File does not exist\./.test(text)) return 'read-not-found'
  if (tool === 'Read' && /^File content \(\d+ tokens\) exceeds maximum allowed tokens \(\d+\)/.test(text)) return 'read-too-large'
  if (tool === 'StructuredOutput' && /^Output does not match required schema: /.test(text)) return 'schema-mismatch'
  if (/^The user doesn't want to proceed with this tool use\./.test(text)) return 'user-rejected'
  if (tool === 'Workflow' && /^<tool_use_error>Workflow "[^"\n]*" not found\./.test(text)) return 'workflow-not-found'
  if (tool === 'Workflow' && /^<tool_use_error>scriptPath must be a script path/.test(text)) return 'workflow-bad-script'
  if (tool === 'Skill' && /^<tool_use_error>Skill \S+ cannot be used with Skill tool/.test(text)) return 'skill-disabled'
  if (tool === 'TaskStop' && /^<tool_use_error>No task found with ID: /.test(text)) return 'task-not-found'
  if (tool === 'TaskStop' && /^<tool_use_error>Task \S+ is not running \(status: /.test(text)) return 'task-not-running'
  if (tool === 'Agent' && /^Concurrent subagent limit reached\./.test(text)) return 'subagent-limit'
  if (tool === 'Grep' && /^Search failed \u2014 ripgrep rejected/.test(text)) return 'grep-pattern-rejected'
  if (/Exit code 144\b/.test(text)) return 'exit-144-self-kill'
  if (/timed out|timeout/i.test(text)) return 'timeout'
  if (/did not match|not found in file|String to replace not found/i.test(text)) return 'edit-no-match'
  if (/permission denied|EACCES/i.test(text)) return 'permission-denied'
  if (/ModuleNotFoundError|No module named/.test(text)) return 'module-not-found'
  if (/command not found|Exit code 127\b/.test(text)) return 'command-not-found'
  if (/No such file or directory|ENOENT/.test(text)) return 'no-such-file'
  if (/\b\d+ failed\b/.test(text)) return 'tests-failed'
  if (/^fatal: /m.test(text)) return 'git-fatal'
  if (/SyntaxError|syntax error/i.test(text)) return 'syntax-error'
  const m = /^Exit code (\d{1,3})\b/m.exec(text)
  if (m) {
    const n = Number(m[1])
    if (n >= 1 && n <= 255) return `exit-${n}`
  }
  return 'other'
}

// --- cmd_sig (RSI-LOG-CMD; owner decision "Redacted signature") -------------------------
// The signature keeps only argv[0] when it is a plain program word, flags, key names from
// key=value, and shell operators. Every other argument becomes a class — paths PATH,
// quoted strings STR, URLs/IPs HOST, key=value KEY=, anything else ARG — so no path,
// argument value, or free text can reach the log.

export type CmdSig = { shape: string; args_hash: string }

const SIG_SEPS = new Set(['&&', '||', '|', ';'])
const SIG_OPS = new Set([...SIG_SEPS, '&', '>', '>>', '<', '<<', '2>', '2>>', '&>', '>&', '<&', '2>&1', '>&2', '&>>'])
const SIG_FLAG = /^(?:--[A-Za-z0-9][A-Za-z0-9-]{0,38}|-[A-Za-z]{1,4})$/
const SIG_PROG = /^[A-Za-z0-9._-]{1,64}$/
const SIG_KEYVAL = /^(--?[A-Za-z0-9][A-Za-z0-9._-]{0,38}|[A-Za-z_][A-Za-z0-9._-]{0,38})=/
const SIG_URL = /^[a-z][a-z0-9+.-]*:\/\//i
const SIG_IP = /^\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?$/
const sigIsPath = (t: string): boolean => /[/\\]/.test(t) || t.startsWith('~') || /^[A-Za-z]:[\\/]/.test(t)

// Whitespace splits outside quotes; a token holding any quoted segment is quoted.
function sigTokens(command: string): { text: string; quoted: boolean }[] {
  const out: { text: string; quoted: boolean }[] = []
  let cur = '', quoted = false, seen = false, q = ''
  for (const c of command) {
    if (q) {
      if (c === q) q = ''
      else cur += c
      continue
    }
    if (c === '"' || c === "'") { q = c; quoted = true; seen = true; continue }
    if (/\s/.test(c)) {
      if (seen) { out.push({ text: cur, quoted }); cur = ''; quoted = false; seen = false }
      continue
    }
    cur += c; seen = true
  }
  if (seen) out.push({ text: cur, quoted })
  return out
}

// {shape, norm}: shape is what the row logs; norm is what feeds args_hash. Bare words keep
// their literal in norm only (git push != git pull), never in shape.
function sigClass(t: { text: string; quoted: boolean }, isProgram: boolean): { shape: string; norm: string } {
  if (t.quoted) return { shape: 'STR', norm: 'STR' }
  const kv = SIG_KEYVAL.exec(t.text)
  if (kv) return { shape: `${kv[1]}=`, norm: 'KEY=' }
  if (SIG_OPS.has(t.text)) return { shape: t.text, norm: t.text }
  if (SIG_FLAG.test(t.text)) return { shape: t.text, norm: t.text }
  if (SIG_URL.test(t.text) || SIG_IP.test(t.text)) return { shape: 'HOST', norm: 'HOST' }
  if (sigIsPath(t.text)) return { shape: 'PATH', norm: 'PATH' }
  if (isProgram && SIG_PROG.test(t.text)) return { shape: t.text, norm: t.text }
  return { shape: 'ARG', norm: t.text }
}

const SIG_SHA256_K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

// sha256 over UTF-8 in plain TS — the mod engine imports no node modules. 64-char lowercase hex.
function sha256Hex(msg: string): string {
  const data: number[] = []
  for (let i = 0; i < msg.length; i++) {
    let c = msg.charCodeAt(i)
    if (c < 0x80) data.push(c)
    else {
      if (c >= 0xd800 && c <= 0xdbff && i + 1 < msg.length) {
        const d = msg.charCodeAt(i + 1)
        if (d >= 0xdc00 && d <= 0xdfff) { c = 0x10000 + ((c - 0xd800) << 10) + (d - 0xdc00); i++ }
      }
      if (c < 0x800) data.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f))
      else if (c < 0x10000) data.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f))
      else data.push(0xf0 | (c >> 18), 0x80 | ((c >> 12) & 0x3f), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f))
    }
  }
  const bitLen = data.length * 8
  data.push(0x80)
  while (data.length % 64 !== 56) data.push(0)
  const hi = Math.floor(bitLen / 0x100000000)
  const lo = bitLen >>> 0
  data.push((hi >>> 24) & 0xff, (hi >>> 16) & 0xff, (hi >>> 8) & 0xff, hi & 0xff)
  data.push((lo >>> 24) & 0xff, (lo >>> 16) & 0xff, (lo >>> 8) & 0xff, lo & 0xff)
  const H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
  const w = new Array<number>(64)
  const rotr = (x: number, n: number) => (x >>> n) | (x << (32 - n))
  for (let off = 0; off < data.length; off += 64) {
    for (let i = 0; i < 16; i++)
      w[i] = (data[off + 4 * i] << 24) | (data[off + 4 * i + 1] << 16) | (data[off + 4 * i + 2] << 8) | data[off + 4 * i + 3]
    for (let i = 16; i < 64; i++) {
      const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3)
      const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10)
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0
    }
    let [a, b, c, d, e, f, g, h] = H
    for (let i = 0; i < 64; i++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
      const ch = (e & f) ^ (~e & g)
      const t1 = (h + S1 + ch + SIG_SHA256_K[i] + w[i]) | 0
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
      const maj = (a & b) ^ (a & c) ^ (b & c)
      const t2 = (S0 + maj) | 0
      h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0
    }
    H[0] = (H[0] + a) | 0; H[1] = (H[1] + b) | 0; H[2] = (H[2] + c) | 0; H[3] = (H[3] + d) | 0
    H[4] = (H[4] + e) | 0; H[5] = (H[5] + f) | 0; H[6] = (H[6] + g) | 0; H[7] = (H[7] + h) | 0
  }
  return H.map(x => (x >>> 0).toString(16).padStart(8, '0')).join('')
}

/**
 * Redacted signature for a Bash command string: {shape, args_hash}. shape is the argv
 * skeleton — argv[0] kept when a plain program word (and the word after a &&, ||, | or ;),
 * flags kept, key=value kept as `key=`, and PATH/STR/HOST/ARG classes for everything else.
 * args_hash is the first 12 hex of sha256 over the class-normalized argument list: same
 * normalized command, same hash (git push and git pull differ; different paths, quoted
 * values and key= values do not). null for a non-string or empty command — the row field
 * is absent, never guessed.
 */
export function commandSignature(command: string): CmdSig | null {
  if (typeof command !== 'string') return null
  const toks = sigTokens(command)
  if (toks.length === 0) return null
  // env-prefixes (FOO=bar) are not the program; argv[0] is the first non-key=value token.
  const progIdx = toks.findIndex(t => !t.quoted && !SIG_KEYVAL.test(t.text))
  const shape: string[] = []
  const norm: string[] = []
  toks.forEach((t, i) => {
    const isProgram = i === progIdx || (i > 0 && SIG_SEPS.has(toks[i - 1].text))
    const c = sigClass(t, isProgram)
    shape.push(c.shape)
    norm.push(c.norm)
  })
  return { shape: shape.join(' '), args_hash: sha256Hex(JSON.stringify(norm)).slice(0, 12) }
}

export const isTestCommand = (tool: string, input: unknown): boolean => TEST_CMD.test(cmdOf(tool, input))
export const isEditTool = (tool: string): boolean => EDIT_TOOLS.includes(tool)

/** In-memory per-session state for retry and edit-then-test-fail detection. */
export function tracker() {
  const recent: { key: string; ok: boolean }[] = []
  let editedSinceTest = false
  return {
    /** Call once per finished (or denied) call, in order. */
    note(tool: string, input: unknown, ok: boolean): { retry: boolean; edit_test_fail: boolean } {
      const key = fingerprint(tool, input)
      const retry = recent.some(r => r.key === key && !r.ok)
      recent.push({ key, ok })
      if (recent.length > 5) recent.shift()
      let edit_test_fail = false
      if (isTestCommand(tool, input)) {
        edit_test_fail = !ok && editedSinceTest
        editedSinceTest = false
      } else if (isEditTool(tool) && ok) editedSinceTest = true
      return { retry, edit_test_fail }
    },
  }
}

export type Summary = {
  calls: number
  fail: number
  retries: number
  denials: number
  hints: Record<string, number>
  editTestFail: number
  tools: Record<string, { calls: number; fail: number; retries: number }>
}

export function summarize(rows: readonly Row[]): Summary {
  const s: Summary = { calls: 0, fail: 0, retries: 0, denials: 0, hints: {}, editTestFail: 0, tools: {} }
  for (const r of rows) {
    if (r.kind !== 'tool') continue
    const t = (s.tools[r.tool] ??= { calls: 0, fail: 0, retries: 0 })
    s.calls++
    t.calls++
    if (!r.ok) (s.fail++, t.fail++)
    if (r.retry) (s.retries++, t.retries++)
    if (r.denied) s.denials++
    if (r.hint) s.hints[r.hint] = (s.hints[r.hint] ?? 0) + 1
    if (r.edit_test_fail) s.editTestFail++
  }
  return s
}

const pct = (a: number, b: number) => (b === 0 ? '0%' : `${Math.round((100 * a) / b)}%`)

function block(title: string, s: Summary): string[] {
  const hints = Object.entries(s.hints).map(([k, n]) => `${k}=${n}`).join(' ') || 'none'
  const lines = [
    `${title}: ${s.calls} calls, ${s.fail} fail (${pct(s.fail, s.calls)}), ${s.retries} retries, ${s.denials} denials, ${s.editTestFail} edit->test-fail`,
    `  hints: ${hints}`,
  ]
  for (const [tool, t] of Object.entries(s.tools).sort((a, b) => b[1].calls - a[1].calls))
    lines.push(`  ${tool.padEnd(14)} calls ${String(t.calls).padStart(4)}  fail ${String(t.fail).padStart(3)}  rate ${pct(t.fail, t.calls).padStart(4)}  retries ${t.retries}`)
  return lines
}

export function scoreboard(session: string, rows: readonly Row[]): string {
  const week = summarize(rows)
  const mine = summarize(rows.filter(r => r.session === session))
  return ['RSI scoreboard', ...block('This session', mine), ...block('Last 7 days', week)].join('\n')
}
