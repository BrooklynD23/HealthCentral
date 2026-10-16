export const meta = {
  name: 'build-wave',
  description: 'Run every build-program queue item that is eligible now, in parallel: haiku gathers state, opus selects a file-disjoint set, each item runs build-item',
  whenToUse: 'L0 after merges or owner answers. args {max?: 3, ids?: ["D-1","E-3a"]}. Re-run after the next merges to pick up deferred items.',
  phases: [
    { title: 'Scan', detail: 'haiku reads queue, open PRs, merged PRs, owner decisions', model: 'haiku' },
    { title: 'Select', detail: 'opus picks the eligible, file-disjoint set', model: 'opus' },
    { title: 'Build', detail: 'one build-item run per selected item, at most max at once' },
  ],
}

// Runbook: docs/plans/2026-10-15-build-program/RUNBOOK.md. Per-item loop: .claude/workflows/build-item.js.
const STYLE = 'Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)'
const QUEUE = 'docs/plans/2026-10-15-build-program/queue.md'
// ponytail: 3 items at once on the 12 GB box; every pytest run is serialised by flock, so raise only with more RAM.
const MAX = Math.max(1, Math.min(6, (args && args.max) || 3))
const ONLY = (args && Array.isArray(args.ids)) ? args.ids : null

const SCAN_SCHEMA = {
  type: 'object',
  properties: {
    main_sha: { type: 'string' },
    rows: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, kind: { type: 'string' }, runtime: { type: 'string' }, status: { type: 'string' },
      depends_on: { type: 'string' }, gates: { type: 'string' }, files: { type: 'array', items: { type: 'string' } },
    }, required: ['id', 'kind', 'runtime', 'status', 'depends_on', 'gates', 'files'] } },
    open_prs: { type: 'array', items: { type: 'object', properties: {
      number: { type: 'integer' }, title: { type: 'string' }, head: { type: 'string' }, draft: { type: 'boolean' },
      files: { type: 'array', items: { type: 'string' } },
    }, required: ['number', 'title', 'head', 'files'] } },
    merged_recent: { type: 'array', items: { type: 'string' }, description: '"#N title" for PRs merged in the last 30 days' },
    owner_rows: { type: 'array', items: { type: 'string' }, description: 'gate id + owner choice, one per owner-decisions row' },
  },
  required: ['main_sha', 'rows', 'open_prs', 'merged_recent', 'owner_rows'],
}

const SELECT_SCHEMA = {
  type: 'object',
  properties: {
    eligible: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, priority: { type: 'integer', description: '1 = start first' }, why: { type: 'string' },
    }, required: ['id', 'files', 'priority', 'why'] } },
    not_eligible: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, reason: { type: 'string' },
    }, required: ['id', 'reason'] } },
  },
  required: ['eligible', 'not_eligible'],
}

phase('Scan')
const scan = await agent(
  `Read-only state scan for the build program. Repo: run \`git rev-parse --show-toplevel\`, then \`git fetch origin\`.
1. main_sha = git rev-parse --short origin/main.
2. Read ${QUEUE} from origin/main (\`git show origin/main:${QUEUE}\`). One entry per queue row in every table (waves and owner sections): id, kind, runtime, status text, depends_on, owner gates, full file list (expand be/ = src/backend/, fe/ = src/frontend/src/).
3. open_prs: \`gh pr list --state open --limit 100 --json number,title,headRefName,isDraft\`, then for each \`gh pr diff <n> --name-only\`.
4. merged_recent: \`gh pr list --state merged --limit 60 --json number,title,mergedAt\`.
5. owner_rows: every row of docs/capstone-report/owner-decisions-2026-09-27.md on origin/main as "<gate id>: <owner choice>".
Copy facts only; judge nothing; edit nothing.
${STYLE}`,
  { label: 'scan state', phase: 'Scan', model: 'haiku', effort: 'low', schema: SCAN_SCHEMA },
)
if (!scan) return 'STOPPED: scan returned nothing'

phase('Select')
const sel = await agent(
  `You are L0 (Opus) choosing which build-program items start now. State (from a Haiku scan; spot-check anything decisive with git/gh yourself):
${JSON.stringify(scan, null, 1)}
${ONLY ? `Consider only these ids: ${ONLY.join(', ')}.` : 'Consider every row.'}

An item is eligible only if ALL hold (cite evidence in why):
1. kind is PRODUCT or DOCS (not OWNER, not model-machine); runtime is claude or any.
2. Every depends_on PR/item is merged on origin/main (git merge-base --is-ancestor, or merged_recent).
3. Every gate that blocks EXECUTION is answered in owner_rows with a choice that allows the work (merge-only gates do not block). Never infer an approval; quote the row.
4. No open PR already claims it (head branch matches ^[a-z]+/<id-lower>- or title has "[claim:" + id).
5. None of its files is in an open non-draft PR's file list (contracts.md §b rule 1; count slots, docs/INDEX.md, docs/_link_graph.json are never in an item's list under SLOT-RULE-2 — drop them from files).
Priority: unblocks the most downstream rows first, then smaller est hours.
A row marked "runs alone" (e.g. E-3a, repo-wide) is returned ALONE in eligible (and every other eligible row goes to not_eligible with reason "waits for <id>, runs alone"), or put in not_eligible if any open PR edits Python; never mix it with other items.
Put every other considered row in not_eligible with the one blocking reason.
${STYLE}`,
  { label: 'select', phase: 'Select', model: 'opus', effort: 'high', schema: SELECT_SCHEMA },
)
if (!sel) return 'STOPPED: select returned nothing'

// Greedy file-disjoint pick in priority order: two running items never share a file.
const taken = new Set()
const picked = []
const deferred = []
for (const it of [...sel.eligible].sort((a, b) => a.priority - b.priority)) {
  const clash = it.files.find((f) => taken.has(f))
  if (clash) { deferred.push(`${it.id}: shares ${clash} with a picked item`); continue }
  it.files.forEach((f) => taken.add(f))
  picked.push(it.id)
}
log(`picked ${picked.length}: ${picked.join(', ') || 'none'}; deferred ${deferred.length}; not eligible ${sel.not_eligible.length}`)
deferred.forEach((d) => log(`deferred ${d}`))

phase('Build')
// Semaphore: at most MAX build-item runs at once; the rest queue in priority order.
let running = 0
const waiters = []
const acquire = () => (running < MAX ? (running++, Promise.resolve()) : new Promise((r) => waiters.push(r)))
const release = () => { const next = waiters.shift(); if (next) next(); else running-- }

const results = await parallel(picked.map((id) => async () => {
  await acquire()
  try {
    return { id, result: await workflow('build-item', { id }) }
  } catch (e) {
    return { id, result: `ERROR ${e && e.message}` }
  } finally {
    release()
  }
}))

return {
  main_sha: scan.main_sha,
  built: results.filter(Boolean),
  deferred,
  not_eligible: sel.not_eligible,
  next: 'Owner merges the READY PRs; L0 runs the post-merge batch (contracts §d step 3), then re-runs build-wave.',
}
