import { describe, expect, mock, test } from 'claude-code/testing'
import cases from './replay/cases'
import { RULES } from './hooks/rules'
import { classifyError } from './hooks/logic'

// The test environment has no fs: an in-memory one answers fs.* beneath the plugin.
function memfs(on: any) {
  const files = new Map<string, string>()
  on('fs.exists', ($: any, e: any) => ({ value: files.has(e.path) }))
  on('fs.read', ($: any, e: any) => ({ value: files.get(e.path) ?? '' }))
  on('fs.write', ($: any, e: any) => (files.set(e.path, e.text), { value: undefined }))
  on('fs.list', ($: any, e: any) => ({
    value: [...files.keys()].filter(k => k.startsWith(e.path + '/')).map(k => ({ name: k.slice(e.path.length + 1), kind: 'file', size: 0, mtimeMs: 0, isLink: false })),
  }))
  on('ui.status', () => ({ value: undefined }))
  return files
}
const rowsOf = (files: Map<string, string>) =>
  [...files.values()].join('').split('\n').filter(Boolean).map(l => JSON.parse(l))
const T0 = Date.parse('2026-10-17T12:00:00Z')
const bottom = (on: any, text: string, isError: boolean) =>
  on('tool.call', () => ({ result: text, text, ...(isError ? { isError: true } : {}) }))

describe('replay set', () => {
  for (const c of cases as any[]) {
    test(c.id, async ($, on) => {
      const clock = mock.clock(on, { now: T0 })
    const files = memfs(on)
      const failed = c.failed ?? c.error_text !== undefined
      bottom(on, c.error_text ?? '', failed)
      const r: any = await $.tool.call({ tool: c.tool, ...c.input })
      await clock.settle()
      const ctx = (r.context ?? []).join('\n')
      if (c.expect === 'deny') expect(r.deny).toContain(c.rule)
      else expect(r.deny).toBeUndefined()
      if (c.expect === 'hint') expect(ctx).toContain(`[asclexis-rsi:${c.rule}]`)
      else expect(ctx).not.toContain(`[asclexis-rsi:${c.rule}]`)
      const [row] = rowsOf(files)
      if (c.expect === 'deny') expect(row.guard).toBe(c.rule)
      if (c.expect === 'hint') expect(row.hint).toBe(c.rule)
      if (c.error_class !== undefined) expect(row.error_class).toBe(c.error_class)
      if (c.expect === 'pass') (expect(row.guard).toBeNull(), expect(row.hint).toBeNull())
    })
  }
  test('every rule has a positive and a negative case', () => {
    for (const r of RULES) {
      const mine = (cases as any[]).filter(c => c.rule === r.id)
      expect(mine.some(c => c.expect !== 'pass')).toBe(true)
      expect(mine.some(c => c.expect === 'pass')).toBe(true)
    }
  })
})

describe('classifyError', () => {
  test('fixed classes for common Bash failures', () => {
    const cases: [string, string][] = [
      ["Exit code 1\nModuleNotFoundError: No module named 'foo'", 'module-not-found'],
      ['Exit code 2\nNo such file or directory', 'no-such-file'],
      ['Exit code 1\n3 failed, 10 passed', 'tests-failed'],
      ['Exit code 127\ncommand not found', 'command-not-found'],
      ['Exit code 128\nfatal: not a git repository', 'git-fatal'],
      ['Exit code 1\nSyntaxError', 'syntax-error'],
      ['Exit code 144', 'exit-144-self-kill'],
      ['timed out', 'timeout'],
    ]
    for (const [text, cls] of cases) expect(classifyError(text)).toBe(cls)
  })
  test('bounded exit-code fallback', () => {
    expect(classifyError('Exit code 1\nboom')).toBe('exit-1')
    expect(classifyError('Exit code 2')).toBe('exit-2')
    expect(classifyError('Exit code 99999')).toBe('other')
    expect(classifyError('no exit line')).toBe('other')
  })
  test('never echoes input', () => {
    const planted = ['SECRET-123', '/home/x/patient.pdf', 'Jane']
    const shapes = (p: string) => [
      `Exit code 1\n${p}`,
      `Exit code 2\nNo such file or directory: ${p}`,
      `Exit code 127\n${p}: command not found`,
      `Exit code 1\nModuleNotFoundError: No module named '${p}'`,
      `fatal: ${p}`,
      `SyntaxError: ${p}`,
      `${p} timed out`,
      p,
    ]
    const ok = /^(exit-144-self-kill|timeout|edit-no-match|permission-denied|module-not-found|command-not-found|no-such-file|tests-failed|git-fatal|syntax-error|exit-\d{1,3}|other)$/
    for (const p of planted)
      for (const t of shapes(p)) {
        const r = classifyError(t)
        expect(r).toMatch(ok)
        for (const q of planted) expect(r).not.toContain(q)
      }
  })
})

describe('classifyError, non-Bash', () => {
  // [tool, neutral first line, class]. Placeholders only: no real path, name or secret.
  const MEASURED: [string, string, string][] = [
    ['Monitor', '<tool_use_error>InputValidationError: Monitor failed due to the following issue:\nThe required parameter `x` is missing', 'input-validation'],
    ['Nope', '<tool_use_error>Error: No such tool available: Nope. Use one of the listed tools.', 'no-such-tool'],
    ['Edit', '<tool_use_error>File has not been read yet. Read it first before writing to it.', 'edit-not-read'],
    ['Write', '<tool_use_error>File has not been read yet. Read it first before writing to it.', 'edit-not-read'],
    ['MultiEdit', '<tool_use_error>File has not been read yet. Read it first before writing to it.', 'edit-not-read'],
    ['NotebookEdit', '<tool_use_error>File has not been read yet. Read it first before writing to it.', 'edit-not-read'],
    ['Read', 'File does not exist. Note: your current working directory is /x.', 'read-not-found'],
    ['Read', 'File content (30000 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters.', 'read-too-large'],
    ['StructuredOutput', 'Output does not match required schema: x', 'schema-mismatch'],
    ['AskUserQuestion', "The user doesn't want to proceed with this tool use. The tool use was rejected.", 'user-rejected'],
    ['Workflow', '<tool_use_error>Workflow "x" not found. Available: a, b', 'workflow-not-found'],
    ['Workflow', '<tool_use_error>scriptPath must be a script path this tool returned, or a file you can already read.', 'workflow-bad-script'],
    ['Skill', '<tool_use_error>Skill x cannot be used with Skill tool due to disable-model-invocation', 'skill-disabled'],
    ['TaskStop', '<tool_use_error>No task found with ID: x', 'task-not-found'],
    ['TaskStop', '<tool_use_error>Task x is not running (status: completed)', 'task-not-running'],
    ['Agent', 'Concurrent subagent limit reached. You can run 4 subagents at once.', 'subagent-limit'],
    ['Grep', 'Search failed — ripgrep rejected the pattern, glob, or file type without searching:', 'grep-pattern-rejected'],
    ['Bash', 'Permission for this action was denied by the Claude Code auto mode classifier. Reason: x', 'permission-denied-auto'],
  ]
  test('fixed classes for measured tool errors', () => {
    for (const [tool, text, cls] of MEASURED) expect(classifyError(text, tool)).toBe(cls)
  })
  test('tool-scoped classes need the tool', () => {
    expect(classifyError('File does not exist.', 'Bash')).toBe('other')
    expect(classifyError('Output does not match required schema: x', 'Read')).toBe('other')
    const scoped = ['edit-not-read', 'read-not-found', 'read-too-large', 'schema-mismatch', 'workflow-not-found', 'workflow-bad-script', 'skill-disabled', 'task-not-found', 'task-not-running', 'subagent-limit', 'grep-pattern-rejected']
    for (const [, text, cls] of MEASURED) if (scoped.includes(cls)) expect(classifyError(text, 'Bash')).not.toBe(cls)
  })
  test('tool envelope wins over Bash shapes', () => {
    const t = '<tool_use_error>InputValidationError: Monitor failed due to the following issue:\ntimeout_ms must be a number'
    expect(classifyError(t, 'Monitor')).toBe('input-validation')
    expect(classifyError(t)).toBe('input-validation')
    // An auto-mode denial that mentions a timeout or a missing file is still the denial.
    expect(classifyError('Permission for this action was denied by the Claude Code auto mode classifier. timeout: No such file or directory', 'Bash')).toBe('permission-denied-auto')
  })
  test('never echoes input, non-Bash', () => {
    const planted = ['SECRET-123', '/home/x/patient.pdf', 'Jane']
    const ok = /^(input-validation|no-such-tool|edit-not-read|read-not-found|read-too-large|schema-mismatch|user-rejected|workflow-not-found|workflow-bad-script|skill-disabled|task-not-found|task-not-running|subagent-limit|grep-pattern-rejected|permission-denied-auto|exit-144-self-kill|timeout|edit-no-match|permission-denied|module-not-found|command-not-found|no-such-file|tests-failed|git-fatal|syntax-error|exit-\d{1,3}|other)$/
    for (const p of planted)
      for (const [tool, text] of MEASURED) {
        // Planted text after the fixed prefix, before it, and as the whole text.
        for (const t of [`${text} ${p}`, `${p} ${text}`, p, text.replace(/\bx\b/g, p)]) {
          const r = classifyError(t, tool)
          expect(r).toMatch(ok)
          for (const q of planted) expect(r).not.toContain(q)
        }
      }
  })
})

describe('logger', () => {
  test('row is metadata only: no command text, no output', async ($, on) => {
    const clock = mock.clock(on, { now: T0 })
    const files = memfs(on)
    const secret = 'echo SECRET-TOKEN-123 patient=Jane'
    bottom(on, 'out SECRET-OUTPUT-456', true)
    await $.tool.call({ tool: 'Bash', command: secret })
    await clock.settle()
    const raw = [...files.values()].join('')
    expect(raw).not.toContain('SECRET')
    expect(raw).not.toContain('Jane')
    const [row] = rowsOf(files)
    expect(row).toEqual(expect.objectContaining({ v: 1, kind: 'tool', tool: 'Bash', ok: false, denied: false, error_class: 'other', retry: false }))
  })
  test('row classifies without the text', async ($, on) => {
    const clock = mock.clock(on, { now: T0 })
    const files = memfs(on)
    bottom(on, "Exit code 1\nModuleNotFoundError: No module named 'secretpkg'", true)
    await $.tool.call({ tool: 'Bash', command: 'make x' })
    await clock.settle()
    const raw = [...files.values()].join('')
    expect(raw).not.toContain('secretpkg')
    const [row] = rowsOf(files)
    expect(row.error_class).toBe('module-not-found')
  })
  test('Read row classifies without the text', async ($, on) => {
    const clock = mock.clock(on, { now: T0 })
    const files = memfs(on)
    bottom(on, 'File does not exist. Note: your current working directory is /home/x/Jane.', true)
    await $.tool.call({ tool: 'Read', file_path: '/home/x/patient.pdf' })
    await clock.settle()
    const raw = [...files.values()].join('')
    expect(raw).not.toContain('patient')
    expect(raw).not.toContain('Jane')
    const [row] = rowsOf(files)
    expect(row.error_class).toBe('read-not-found')
  })
  test('detects retry after a failure', async ($, on) => {
    const clock = mock.clock(on, { now: T0 })
    const files = memfs(on)
    bottom(on, 'boom', true)
    await $.tool.call({ tool: 'Bash', command: 'make x' })
    await $.tool.call({ tool: 'Bash', command: 'make x' })
    await clock.settle()
    const rows = rowsOf(files)
    expect(rows.map((r: any) => r.retry)).toEqual([false, true])
  })
  test('detects edit then test fail', async ($, on) => {
    const clock = mock.clock(on, { now: T0 })
    const files = memfs(on)
    on('tool.call', { tool: 'Bash' }, () => ({ result: 'x', text: '1 failed', isError: true }))
    on('tool.call', { tool: 'Edit' }, () => ({ result: 'ok', text: 'ok' }))
    await $.tool.call({ tool: 'Edit', file_path: '/a.py', old_string: 'a', new_string: 'b' })
    await $.tool.call({ tool: 'Bash', command: 'pytest -q' })
    await $.tool.call({ tool: 'Bash', command: 'pytest -q' })
    await clock.settle()
    const rows = rowsOf(files)
    expect(rows.map((r: any) => r.edit_test_fail)).toEqual([false, true, false])
  })
})

describe('/rsi', () => {
  test('scoreboard shape', async ($, on) => {
    mock.clock(on, { now: T0 })
    memfs(on)
    on('tool.call', { tool: 'Bash' }, ($: any, e: any) => e.command === 'bad' ? { result: 'x', text: 'nope', isError: true } : { result: 'x', text: 'fine' })
    await $.tool.call({ tool: 'Bash', command: 'ok' })
    await $.tool.call({ tool: 'Bash', command: 'bad' })
    await $.tool.call({ tool: 'Bash', command: 'bad' })
    await $.tool.call({ tool: 'Bash', command: 'pkill -f x' })
    const r = await $.command.run({ command: 'rsi', args: '', origin: { kind: 'composer' } as any, presentation: {} as any })
    expect(r.text).toContain('RSI scoreboard')
    expect(r.text).toContain('This session: 4 calls, 3 fail')
    expect(r.text).toContain('Last 7 days: 4 calls')
    expect(r.text).toContain('1 retries')
    expect(r.text).toContain('1 denials')
    expect(r.text).toMatch(/Bash\s+calls\s+4/)
  })
})
