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

/** First `before`/deny rule that matches this call, if any. */
export function checkBefore(tool: string, input: unknown, rules: readonly Rule[] = RULES): Rule | undefined {
  const cmd = cmdOf(tool, input)
  return rules.find(r => r.when === 'before' && r.action === 'deny' && r.tool === tool && new RegExp(r.match).test(cmd))
}

/** First `after` rule that matches the finished call, if any. */
export function checkAfter(
  tool: string,
  input: unknown,
  text: string,
  failed: boolean,
  rules: readonly Rule[] = RULES,
): Rule | undefined {
  const cmd = cmdOf(tool, input)
  return rules.find(
    r =>
      r.when === 'after' &&
      r.tool === tool &&
      (failed || r.onSuccess === true) &&
      (r.command === undefined || new RegExp(r.command).test(cmd)) &&
      new RegExp(r.match).test(text) &&
      (r.absent === undefined || !new RegExp(r.absent).test(text)),
  )
}

/**
 * Fixed error category for a failure no rule claimed. Never raw text.
 * Order matters: the first four checks win, then common Bash failure shapes,
 * then a bounded `exit-<n>` (1-255) from the `Exit code` line, else 'other'.
 * Returns only fixed literals or `exit-` plus captured digits, never input text.
 */
export function classifyError(text: string): string {
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
