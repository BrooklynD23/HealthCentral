import { describe, expect, mock, test } from 'claude-code/testing'
import cases from './replay/cases'
import { RULES } from './hooks/rules'

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
