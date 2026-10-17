export const meta = {
  name: 'rsi-loop',
  description: 'RSI step 2: mine failure logs, reflect, propose up to 3 small rule/replay/doc edits, deterministic gate + plugin test, PR survivors (never merged), measure',
  whenToUse: 'Standalone, or as the last stage of build-program (after every run). args {since?: ISO date, run_id?: string, dry_run?: bool}. dry_run=true skips PR creation. Owner merges RSI promotions.',
  phases: [
    { title: 'Mine', detail: 'haiku clusters tool failures by tool + error_class (metadata only)', model: 'haiku' },
    { title: 'Reflect', detail: 'opus GEPA-style reflection per top cluster', model: 'opus' },
    { title: 'Propose', detail: 'sonnet, one fresh worktree per candidate, max 3', model: 'sonnet' },
    { title: 'Gate', detail: 'JS allow/deny on the diff, then haiku runs claude plugin validate + test', model: 'haiku' },
    { title: 'Publish', detail: 'sonnet opens PRs for survivors, writes summary JSON, archives rejects', model: 'sonnet' },
  ],
}

// Agent budget per run: 1 mine + 1 reflect + 3 propose + 3 gate + 1 publish = 9 (< 10).
// Contract: rsi-contract (log schema, rule table, replay set). Mod lives in .claude/mods/asclexis-rsi/.
const STYLE = 'Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)'
const MAX_CANDIDATES = 3
const MOD = '.claude/mods/asclexis-rsi'
const SINCE = args && typeof args.since === 'string' ? args.since.trim() : ''
const RUN_ID = args && typeof args.run_id === 'string' && args.run_id.trim() ? args.run_id.trim() : 'manual'
const DRY_RUN = !!(args && args.dry_run)
// Both values reach shell commands and branch names: accept narrow shapes only.
if (SINCE && !/^\d{4}-\d{2}-\d{2}([T ][0-9:.]+Z?)?$/.test(SINCE)) throw new Error(`args.since must be an ISO date; got ${JSON.stringify(SINCE)}`)
if (!/^[A-Za-z0-9._-]{1,40}$/.test(RUN_ID)) throw new Error(`args.run_id must match [A-Za-z0-9._-]{1,40}; got ${JSON.stringify(RUN_ID)}`)

// ---------------------------------------------------------------------------
// Gate: pure, deterministic. A candidate may touch ONLY the allow-list; anything
// matching a deny pattern is called out separately so the archive says why.
const ALLOW = [
  `${MOD}/hooks/rules.ts`,
  `${MOD}/replay/cases.json`,
  'docs/agentic/recurring-failures.md',
]
const DENY = [
  [/(^|\/)src\/backend\/tests\//, 'tests'],
  [/(^|\/)__tests__\//, 'tests'],
  [/(^|\/)e2e\//, 'tests'],
  [/\.test\.[A-Za-z0-9]+$/, 'tests'],
  [/(^|\/)test_[^/]*\.py$/, 'tests'],
  [/^scripts\//, 'gate scripts'],
  [/^\.github\//, 'gate scripts'],
  [/threshold/i, 'thresholds'],
  [/(^|\/)modules\/interpret_safety\.py$/, 'ask-first'],
  [/(^|\/)modules\/redaction\.py$/, 'ask-first'],
  [/(^|\/)modules\/faithfulness\.py$/, 'ask-first'],
  [/(^|\/)modules\/verifier_agent\.py$/, 'ask-first'],
  [/(^|\/)core\/auth\.py$/, 'ask-first'],
  [/(^|\/)security\/encryption/, 'ask-first'],
]
function gateDiff(paths) {
  const violations = []
  if (!Array.isArray(paths) || paths.length === 0) return { ok: false, violations: ['empty diff'] }
  for (const raw of paths) {
    const p = String(raw).trim().replace(/\\/g, '/').replace(/^\.\//, '')
    if (!p) continue
    if (p.startsWith('/') || p.split('/').includes('..')) { violations.push(`${p}: path escapes repo`); continue }
    const hit = DENY.find(([re]) => re.test(p))
    if (hit) { violations.push(`${p}: denied (${hit[1]})`); continue }
    if (!ALLOW.includes(p)) violations.push(`${p}: outside allow-list`)
  }
  return { ok: violations.length === 0, violations }
}
// Additions only: deleting lines from the rule table or replay set would weaken a guard.
// numstat rows are "<added>\t<deleted>\t<path>"; binary files show "-".
function gateNumstat(text) {
  const violations = []
  const rows = String(text || '').split('\n').map((l) => l.trim()).filter(Boolean)
  if (!rows.length) return { ok: false, violations: ['empty numstat'] }
  for (const row of rows) {
    const [add, del, ...rest] = row.split(/\s+/)
    const p = rest.join(' ')
    if (![`${MOD}/hooks/rules.ts`, `${MOD}/replay/cases.json`].includes(p)) continue
    if (del === '-' || add === '-' || !/^\d+$/.test(del) || Number(del) > 0) violations.push(`${p}: ${del} deleted line(s); additions only`)
  }
  return { ok: violations.length === 0, violations }
}
const namesOf = (text) => String(text || '').split('\n').map((s) => s.trim()).filter(Boolean)

// ---------------------------------------------------------------------------
const MINE_SCHEMA = {
  type: 'object',
  properties: {
    main_checkout: { type: 'string' },
    window: { type: 'string' },
    clusters: { type: 'array', items: { type: 'object', properties: {
      tool: { type: 'string' }, error_class: { type: 'string' }, count: { type: 'integer' },
      denied: { type: 'integer' }, retries: { type: 'integer' },
      sources: { type: 'array', items: { type: 'string' }, description: 'rsi-log | session-log | pr-review, with PR numbers if any' },
      evidence: { type: 'string', description: 'metadata only: counts, dates, PR numbers, rule ids. No command text or file contents.' },
    }, required: ['tool', 'error_class', 'count'] } },
    metrics: { type: 'object', properties: {
      tool_calls: { type: 'integer' },
      failure_rate_by_tool: { type: 'object', additionalProperties: { type: 'number' } },
      retries: { type: 'integer' }, items: { type: 'integer' }, retries_per_item: { type: 'number' },
      tokens_per_item: { type: ['number', 'null'] },
      previous_summary: { type: 'string', description: 'path of the latest earlier .claude/logs/rsi/summary-*.json, or empty' },
      previous_failure_rate_by_tool: { type: 'object', additionalProperties: { type: 'number' } },
    }, required: ['tool_calls', 'failure_rate_by_tool', 'retries'] },
    existing_rule_ids: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['main_checkout', 'clusters', 'metrics', 'existing_rule_ids'],
}
const REFLECT_SCHEMA = {
  type: 'object',
  properties: { reflections: { type: 'array', items: { type: 'object', properties: {
    cluster: { type: 'string', description: 'tool/error_class' },
    went_wrong: { type: 'string' },
    smallest_change: { type: 'string', description: 'the one rule, replay case pair, or recurring-failures.md row that would have prevented it' },
    target_file: { type: 'string', enum: [`${MOD}/hooks/rules.ts`, `${MOD}/replay/cases.json`, 'docs/agentic/recurring-failures.md'] },
    worth_proposing: { type: 'boolean' },
    already_covered_by: { type: 'string', description: 'existing rule id if one already covers it, else empty' },
  }, required: ['cluster', 'went_wrong', 'smallest_change', 'target_file', 'worth_proposing'] } } },
  required: ['reflections'],
}
const PROPOSE_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['done', 'stopped'] },
    stop_reason: { type: 'string' },
    worktree: { type: 'string' },
    branch: { type: 'string' },
    commit: { type: 'string' },
    diff_names: { type: 'string', description: 'verbatim stdout of: git diff --name-only origin/main...HEAD' },
    diff_stat: { type: 'string', description: 'verbatim stdout of: git diff --stat origin/main...HEAD' },
    summary: { type: 'string' },
    new_rule_ids: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'diff_names', 'diff_stat', 'summary'],
}
const VALIDATE_SCHEMA = {
  type: 'object',
  properties: {
    diff_names: { type: 'string', description: 'verbatim stdout of: git diff --name-only origin/main...HEAD, run in the worktree' },
    numstat: { type: 'string', description: 'verbatim stdout of: git diff --numstat origin/main...HEAD, run in the worktree' },
    validate_exit: { type: 'integer' }, validate_tail: { type: 'string' },
    test_exit: { type: 'integer' }, test_tail: { type: 'string' },
  },
  required: ['diff_names', 'numstat', 'validate_exit', 'validate_tail', 'test_exit', 'test_tail'],
}
const PUBLISH_SCHEMA = {
  type: 'object',
  properties: {
    prs: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, url: { type: 'string' } }, required: ['id', 'url'] } },
    summary_path: { type: 'string' }, archive_path: { type: 'string' }, archived: { type: 'integer' },
    notes: { type: 'string' },
  },
  required: ['prs', 'summary_path', 'archived'],
}

// ---------------------------------------------------------------------------
phase('Mine')
const mined = await agent(
  `Read-only except nothing is written. Metadata only: never copy command text, file contents, tool output or prompts into your answer.
1. Main checkout: \`dirname "$(git rev-parse --path-format=absolute --git-common-dir)"\` (logs are git-ignored and absent from worktrees). Return it as main_checkout.
2. Read <main>/.claude/logs/rsi/*.jsonl (rows per the rsi-contract: kind tool|session; fields tool, ok, denied, guard, error_class, retry, edit_test_fail)${SINCE ? `, keeping rows with ts >= ${SINCE}` : ' (all rows)'}. window = the first and last ts you used. If the directory is empty, say so in notes and continue with the other sources.
3. Also read <main>/.claude/logs/session-log.jsonl (same since filter, if the file exists) and recent merged PR review rounds: \`gh pr list --state merged --limit 30 --json number,title\` then review and review-round comments for the PRs that show failures (retries, reverted gate, "flaky", environment errors). From these only note recurring failure categories and PR numbers.
4. Cluster failures (ok=false or denied=true) by tool + error_class; count, denied, retries, sources. Return the clusters sorted by count descending, all of them.
5. metrics: tool_calls total; failure_rate_by_tool (failures/calls); retries (retry=true rows); items = distinct build-item runs if the logs identify them (else 0); retries_per_item; tokens_per_item only if a log has token counts, else null. previous_summary = newest <main>/.claude/logs/rsi/summary-*.json if any (read its metrics.failure_rate_by_tool into previous_failure_rate_by_tool).
6. existing_rule_ids = ids in ${MOD}/hooks/rules.ts at origin/main (\`git show origin/main:${MOD}/hooks/rules.ts\`), empty if absent.
${STYLE}`,
  { label: 'mine failures', phase: 'Mine', model: 'haiku', effort: 'low', schema: MINE_SCHEMA },
)
if (!mined) return { clusters: [], candidates: 0, accepted_prs: [], rejected: [], metrics: null, stopped: 'mine agent failed' }

const clusters = (mined.clusters || []).slice().sort((a, b) => b.count - a.count)
log(`mined ${clusters.length} clusters; top: ${clusters.slice(0, 3).map((c) => `${c.tool}/${c.error_class} x${c.count}`).join(', ') || 'none'}`)
if (!clusters.length) {
  return { clusters: [], candidates: 0, accepted_prs: [], rejected: [], metrics: mined.metrics, note: 'no failures in window' }
}
const topClusters = clusters.slice(0, MAX_CANDIDATES)
if (clusters.length > topClusters.length) log(`not reflected on: ${clusters.slice(MAX_CANDIDATES).map((c) => `${c.tool}/${c.error_class}`).join(', ')} (candidate cap ${MAX_CANDIDATES})`)

// ---------------------------------------------------------------------------
phase('Reflect')
const reflected = await agent(
  `GEPA-style reflection. For each cluster below, write in natural language: what went wrong (grounded only in the metadata given), and the SMALLEST change that would have prevented it: one rule in ${MOD}/hooks/rules.ts (data-only entry: id, tool, when, match, action deny|hint, message, source), or a row in docs/agentic/recurring-failures.md (read it first; do not duplicate an existing failure mode). Every new rule needs one positive and one negative replay case in ${MOD}/replay/cases.json.
Set worth_proposing=false if an existing rule already covers it (already_covered_by = its id: ${JSON.stringify(mined.existing_rule_ids)}), if it is a one-off, or if the only fix would touch tests, gate scripts, thresholds, or ask-first safety/privacy/auth code (those are never proposed). Be conservative: this is a health app.
Clusters:\n${JSON.stringify(topClusters, null, 1)}
${STYLE}`,
  { label: 'reflect', phase: 'Reflect', model: 'opus', schema: REFLECT_SCHEMA },
)
const toPropose = ((reflected && reflected.reflections) || []).filter((r) => r.worth_proposing).slice(0, MAX_CANDIDATES)
log(`reflections: ${(reflected && reflected.reflections || []).length}, proposing ${toPropose.length}`)
if (!toPropose.length) {
  return { clusters, candidates: 0, accepted_prs: [], rejected: [], metrics: mined.metrics, reflections: reflected ? reflected.reflections : [], note: 'nothing worth proposing' }
}

// ---------------------------------------------------------------------------
// One chain per candidate: propose -> JS gate -> haiku validate -> JS gate again.
const results = await pipeline(
  toPropose,
  (refl, _item, i) => {
    const id = `rsi-${RUN_ID}-${i + 1}`
    return agent(
      `Implement ONE small, single-purpose RSI candidate in your own fresh worktree.
Setup: \`git fetch origin && git checkout -B rsi/${id} origin/main\` (if you are not already in a clean worktree off origin/main, create one with \`git worktree add\` under a sibling dir and work only there).
Reflection to implement:\n${JSON.stringify(refl, null, 1)}
Rules:
- You may edit ONLY: ${ALLOW.join(', ')}. Nothing else, ever. If the mod files do not exist at origin/main yet, stop (status=stopped, stop_reason).
- Each new rule in rules.ts must follow the rule-table shape and ship with at least one positive and one negative ("pass") case in cases.json (ids unique). A recurring-failures.md row needs the evidence and a specific recheck, like the existing rows.
- Never weaken an existing rule or case. Never touch tests, scripts/, .github/, thresholds or ask-first files.
- Commit (\`feat(harness): rsi candidate ${id}: <what>\`, ending with a Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com> line). Do not push. \`.claude/*\` is git-ignored: use \`git add -f <explicit paths>\`, never \`git add -A\`.
- Return diff_names / diff_stat as the verbatim stdout of \`git diff --name-only origin/main...HEAD\` and \`git diff --stat origin/main...HEAD\`, and worktree as \`pwd\`.
${STYLE}`,
      { label: `propose ${id}`, phase: 'Propose', model: 'sonnet', isolation: 'worktree', schema: PROPOSE_SCHEMA },
    )
  },
  async (prop, refl, i) => {
    const id = `rsi-${RUN_ID}-${i + 1}`
    const base = { id, cluster: refl.cluster, reflection: refl }
    if (!prop || prop.status !== 'done') return { ...base, accepted: false, reason: `propose: ${prop ? prop.stop_reason || 'stopped' : 'agent failed'}`, diff_stat: prop ? prop.diff_stat || '' : '' }
    const pre = gateDiff(namesOf(prop.diff_names))
    if (!pre.ok) return { ...base, accepted: false, reason: `gate(diff): ${pre.violations.join('; ')}`, diff_stat: prop.diff_stat }
    const v = await agent(
      `In the worktree ${prop.worktree} (cd there; do not edit anything, do not commit):
1. \`git diff --name-only origin/main...HEAD\` -> diff_names, verbatim. Also \`git diff --numstat origin/main...HEAD\` -> numstat, verbatim.
2. \`claude plugin validate ${MOD}\` -> validate_exit and last 20 lines.
3. \`claude plugin test ${MOD}\` (runs replay/cases.json) -> test_exit and last 30 lines.
Report real exit codes. Do not retry or fix a failure.
${STYLE}`,
      { label: `gate ${id}`, phase: 'Gate', model: 'haiku', effort: 'low', schema: VALIDATE_SCHEMA },
    )
    if (!v) return { ...base, accepted: false, reason: 'gate: validator agent failed', diff_stat: prop.diff_stat }
    const post = gateDiff(namesOf(v.diff_names))
    if (!post.ok) return { ...base, accepted: false, reason: `gate(diff, recheck): ${post.violations.join('; ')}`, diff_stat: prop.diff_stat }
    const ns = gateNumstat(v.numstat)
    if (!ns.ok) return { ...base, accepted: false, reason: `gate(numstat): ${ns.violations.join('; ')}`, diff_stat: prop.diff_stat }
    if (v.validate_exit !== 0) return { ...base, accepted: false, reason: `claude plugin validate exit ${v.validate_exit}`, diff_stat: prop.diff_stat, gate_output: v.validate_tail }
    if (v.test_exit !== 0) return { ...base, accepted: false, reason: `claude plugin test (replay) exit ${v.test_exit}`, diff_stat: prop.diff_stat, gate_output: v.test_tail }
    return { ...base, accepted: true, worktree: prop.worktree, branch: prop.branch || `rsi/${id}`, summary: prop.summary, diff_stat: prop.diff_stat, diff_names: v.diff_names, validate_tail: v.validate_tail, test_tail: v.test_tail }
  },
)

const done = results.filter(Boolean)
const accepted = done.filter((r) => r.accepted)
const rejected = done.filter((r) => !r.accepted).map((r) => ({ id: r.id, reason: r.reason, diff_stat: r.diff_stat || '' }))
log(`accepted ${accepted.length}, rejected ${rejected.length}`)

// ---------------------------------------------------------------------------
phase('Publish')
const summary = {
  run_id: RUN_ID, since: SINCE || null, dry_run: DRY_RUN, window: mined.window || null,
  clusters: clusters.map((c) => ({ tool: c.tool, error_class: c.error_class, count: c.count })),
  candidates: done.length, accepted: accepted.map((r) => r.id), rejected,
  metrics: mined.metrics,
}
const published = await agent(
  `Housekeeping for rsi-loop run ${RUN_ID}. Main checkout = ${mined.main_checkout}. Metadata only.
1. Write this JSON (pretty-printed) to ${mined.main_checkout}/.claude/logs/rsi/summary-${RUN_ID}.json, adding after_failure_rate_by_tool = metrics.failure_rate_by_tool and before = metrics.previous_failure_rate_by_tool (the "after" is only a baseline until the next run measures the effect of any merged promotion):\n${JSON.stringify(summary)}
2. Append ONE line per rejected candidate to ${mined.main_checkout}/.claude/logs/rsi/archive.jsonl ({id, reason, diff_stat, run_id:"${RUN_ID}"}); these files are local and git-ignored. Rejected: ${JSON.stringify(rejected)}
3. ${DRY_RUN || !accepted.length ? 'Create NO pull requests (' + (DRY_RUN ? 'dry_run=true' : 'no survivors') + '). prs=[].' : `For each survivor below: in its worktree \`git push -u origin <branch>\` (never force) and open a READY PR with \`gh pr create\` titled \`rsi: <summary> (RSI-4)\`. Body: the reflection (went wrong + smallest change), the gate output (diff names, validate tail, replay-test tail), the diff stat, then "CI on this PR is the second half of the gate (replay set + CI): the owner merges only on green. Owner merges (RSI promotion; never agent-merged)." and the line "🤖 Generated with [Claude Code](https://claude.com/claude-code)". Do NOT merge, do not enable auto-merge. Survivors:\n${JSON.stringify(accepted)}`}
Return PR urls, the summary path, archive path and number archived.
${STYLE}`,
  { label: 'publish + archive', phase: 'Publish', model: 'sonnet', schema: PUBLISH_SCHEMA },
)

return {
  clusters: summary.clusters,
  candidates: done.length,
  accepted_prs: published ? published.prs : [],
  rejected,
  metrics: mined.metrics,
  summary_path: published ? published.summary_path : null,
}
