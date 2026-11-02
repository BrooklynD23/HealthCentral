import type { Register } from 'claude-code'
import { checkAfter, checkBefore, classifyError, scoreboard, tracker, type Row } from './logic'

const LOG_DIR = '.claude/logs/rsi'
const DAY = 86_400_000

// Metadata only. Rows never hold command text, file contents, tool output, prompts or paths
// (see README). Every logging step is caught: telemetry must never block or fail a tool call.
let sid = ''
let calls = 0
let fails = 0
let guards = 0
const track = tracker()
// Serialised read-append-write (`$.fs` has no append). Fire-and-forget for tool calls.
let queue: Promise<unknown> = Promise.resolve()

function append($: any, ts: string, row: object) {
  const path = `${LOG_DIR}/${ts.slice(0, 10)}.jsonl`
  queue = queue
    .then(async () => {
      const cur = (await $.fs.exists(path)) ? ((await $.fs.read(path)) as string) : ''
      await $.fs.write(path, `${cur}${JSON.stringify(row)}\n`)
    })
    .catch(() => {})
  return queue
}
async function sessionId($: any): Promise<string> {
  try { return (sid ||= await $.session.id()) } catch { return 'unknown' }
}
async function iso($: any): Promise<string> {
  return new Date(await $.clock.now()).toISOString()
}
function refresh($: any) {
  $.ui.status(`rsi: ${calls} calls · ${fails} fail · ${guards} guard`)
}

export const register: Register = on => {
  on('session.start', async ($, e) => {
    try {
      await $.command.register({ name: 'rsi', description: 'RSI scoreboard: tool failures, retries, guards (this session + 7 days)' })
      await append($, await iso($), { v: 1, ts: await iso($), session: await sessionId($), kind: 'session', event: 'start' })
      refresh($)
    } catch {}
    return e as any
  })

  on('session.end', async ($, e) => {
    try {
      const ts = await iso($)
      await append($, ts, { v: 1, ts, session: await sessionId($), kind: 'session', event: 'end' })
    } catch {}
    return e as any
  })

  // One tool.call hook (the engine allows one unmatched hook per event). Two failure modes:
  // - Guard (deny rules, the code before `next`): FAILS CLOSED. If it throws, the .catch denies
  //   the call, as the skill's guard pattern does.
  // - Observer + hints (everything after `next`): FAILS OPEN. Wrapped in its own try/catch, so
  //   a logging or hint error can never fail or alter the call.
  on('tool.call', async ($, e, next) => {
    const { tool, tool_use_id, agentId, requestMeta, ...input } = e as any
    const guardRule = checkBefore(tool, input)
    let t0 = 0
    try { t0 = await $.clock.now() } catch {}
    const ran: any = guardRule
      ? { deny: `asclexis-rsi/${guardRule.id}: ${guardRule.message}` }
      : await next(e)
    try {
      const denied = ran.deny !== undefined
      const failed = denied || ran.isError === true
      const text: string = denied ? '' : (ran.text ?? '')
      const hintRule = denied ? undefined : checkAfter(tool, input, text, failed)
      const rule = guardRule ?? hintRule
      const { retry, edit_test_fail } = track.note(tool, input, !failed)
      const ts = await iso($)
      const row: Row = {
        v: 1, ts, session: await sessionId($), kind: 'tool', tool,
        ok: !failed,
        duration_ms: t0 ? Math.max(0, (await $.clock.now()) - t0) : null,
        denied,
        guard: guardRule?.id ?? null,
        hint: hintRule?.id ?? null,
        error_class: rule?.errorClass ?? (failed ? classifyError(text, tool) : null),
        retry, edit_test_fail,
      }
      calls++
      if (failed) fails++
      if (rule) guards++
      append($, ts, row)
      refresh($)
      if (hintRule) return { ...ran, context: [...(ran.context ?? []), `[asclexis-rsi:${hintRule.id}] ${hintRule.message}`] }
    } catch {}
    return ran
  }).catch(($, e, next) =>
    next.called ? next(e) : { deny: 'asclexis-rsi: its guard failed, so the call is held. Retry, or disable asclexis-rsi.' },
  )

  on('command.run', { command: 'rsi' }, async $ => {
    try {
      await queue
      const now = await $.clock.now()
      const cutoff = new Date(now - 6 * DAY).toISOString().slice(0, 10)
      const names = (await $.fs.list(LOG_DIR)).map((f: any) => f.name as string).filter((n: string) => /^\d{4}-\d{2}-\d{2}\.jsonl$/.test(n) && n.slice(0, 10) >= cutoff)
      const rows: Row[] = []
      for (const n of names)
        for (const line of ((await $.fs.read(`${LOG_DIR}/${n}`)) as string).split('\n'))
          try { if (line) rows.push(JSON.parse(line)) } catch {}
      return { text: scoreboard(await sessionId($), rows) }
    } catch {
      return { text: 'RSI scoreboard: no log yet (.claude/logs/rsi is empty or unreadable).' }
    }
  })
}
