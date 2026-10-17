export const meta = {
  name: 'build-program',
  description: 'Drive queue.md to done: waves of build-item sub-orchestrators, an Opus unblocker for plan gaps, an Opus planner for unplanned rows, optional owner-authorised merges',
  whenToUse: 'L0 after merges or owner answers, to keep the queue moving without hand-starting each item. args {max_waves?: 4, max?: 12, plan_new?: true, auto_merge?: false}. auto_merge=true only with a current owner row that authorises agent merges.',
  phases: [
    { title: 'Select', detail: 'build-wave picks the eligible, file-disjoint set' },
    { title: 'Build', detail: 'one build-item per id: haiku explore, opus Task 0, sonnet implement, haiku tests, opus review + verify' },
    { title: 'Unblock', detail: 'opus sub-orchestrator turns a Task 0 plan gap (gates answered) into a plan delta, then the item re-runs once', model: 'opus' },
    { title: 'Plan', detail: 'haiku search per unplanned row, then one opus planner writes plan sections + queue rows in one docs PR' },
    { title: 'Merge', detail: 'only with auto_merge: opus merges green, approved, non-ask-first PRs and runs the post-merge batch', model: 'opus' },
  ],
}

// Runbook: docs/plans/2026-10-15-build-program/RUNBOOK.md §10.1. Owner gates are never inferred:
// an item blocked by an unanswered gate stays blocked and comes back as an owner question.
const STYLE = 'Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)'
const RUNBOOK = 'docs/plans/2026-10-15-build-program/RUNBOOK.md'
const QUEUE = 'docs/plans/2026-10-15-build-program/queue.md'
const DECISIONS = 'docs/capstone-report/owner-decisions-2026-09-27.md'
const ASK_FIRST = 'modules/interpret_safety.py, modules/redaction.py, modules/faithfulness.py, modules/verifier_agent.py, auth or encryption code'
const MAX_WAVES = Math.max(1, Math.min(8, (args && args.max_waves) || 4))
const MAX = Math.max(1, Math.min(15, (args && args.max) || 12))
const PLAN_NEW = !(args && args.plan_new === false)
const AUTO_MERGE = !!(args && args.auto_merge)

const TRIAGE_SCHEMA = {
  type: 'object',
  properties: {
    kind: { type: 'string', enum: ['done', 'plan_gap', 'owner_gate', 'env', 'review', 'other'] },
    pr_number: { type: 'integer' },
    summary: { type: 'string' },
    owner_question: { type: 'string', description: 'exact question for the owner when kind is owner_gate, else empty' },
  },
  required: ['kind', 'summary'],
}
const UNBLOCK_SCHEMA = {
  type: 'object',
  properties: { planned: { type: 'boolean' }, commits: { type: 'array', items: { type: 'string' } }, stop_reason: { type: 'string' } },
  required: ['planned', 'commits'],
}
const ROWS_SCHEMA = {
  type: 'object',
  properties: { rows: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, summary: { type: 'string' }, ask_first: { type: 'boolean' },
  }, required: ['id', 'summary', 'ask_first'] } } },
  required: ['rows'],
}
const FACTS_SCHEMA = {
  type: 'object',
  properties: { id: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, facts: { type: 'string' } },
  required: ['id', 'files', 'facts'],
}
const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    pr_number: { type: 'integer' }, planned: { type: 'array', items: { type: 'string' } },
    owner_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['planned', 'owner_questions'],
}
const MERGE_SCHEMA = {
  type: 'object',
  properties: { merged: { type: 'array', items: { type: 'string' } }, skipped: { type: 'array', items: { type: 'string' } }, batch_pr: { type: 'string' } },
  required: ['merged', 'skipped'],
}

const triage = (id, result) => agent(
  `Classify this build-item result for queue item ${id}. Read the PR and its latest comment with gh if a PR number appears.
Result:\n${typeof result === 'string' ? result : JSON.stringify(result)}
kind: done (PR opened, ready or draft-ready), plan_gap (Task 0 check 1 failed: the plan or a contract does not cover scope the owner already signed), owner_gate (an unanswered owner gate or an owner-only step blocks it), env (machine or tooling problem), review (escalated after review rounds), other.
For owner_gate, write the exact question the owner must answer, with the options from the lane doc or plan. Never mark a gate answered unless ${DECISIONS} on origin/main has the row.
${STYLE}`,
  { label: `triage ${id}`, phase: 'Unblock', model: 'haiku', effort: 'low', schema: TRIAGE_SCHEMA },
)

const unblock = (id, t) => agent(
  `You are an Opus sub-orchestrator unblocking queue item ${id} (PR #${t.pr_number || '?'}). Task 0 stopped on a plan gap: ${t.summary}
Do what L0 did for ASSIST-AGENT-DATES (#119): in the PR's worktree and branch (git worktree list; create one if missing), commit a plan delta to the item's lane-doc section covering exactly the scope the owner signed, with new test ids and the expected collected delta; amend the contract in contracts.md only as far as that scope needs; set the queue row status to ready; regenerate docs (python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph); push. Use Haiku subagents for code search when you need facts from many files.
Stop (planned=false, stop_reason = the exact owner question) if the signed scope leaves a patient-visible choice open, if a gate is unanswered in ${DECISIONS}, or if the plan would touch ${ASK_FIRST}. Never write product code here; build-item does that next.
${STYLE}`,
  { label: `unblock ${id}`, phase: 'Unblock', model: 'opus', effort: 'high', schema: UNBLOCK_SCHEMA },
)

const ownerQuestions = []
const report = []
let plannedOnce = false

for (let wave = 1; wave <= MAX_WAVES; wave++) {
  phase('Select')
  log(`wave ${wave}/${MAX_WAVES}`)
  const sel = await workflow('build-wave', { max: MAX })
  const picked = (sel && sel.picked) || []
  const notEligible = (sel && sel.not_eligible) || []

  phase('Build')
  const built = await pipeline(
    picked,
    (id) => workflow('build-item', { id }).catch((e) => `ERROR ${id}: ${e && e.message}`),
    (result, id) => triage(id, result).then((t) => ({ id, result, t })),
    async (r) => {
      if (!r.t || r.t.kind !== 'plan_gap') return r
      const u = await unblock(r.id, r.t)
      if (!u || !u.planned) {
        ownerQuestions.push(`${r.id}: ${u ? u.stop_reason : 'unblocker returned nothing'}`)
        return { ...r, unblocked: false }
      }
      const rerun = await workflow('build-item', { id: r.id }).catch((e) => `ERROR ${r.id}: ${e && e.message}`)
      return { ...r, unblocked: true, rerun }
    },
  )
  built.filter(Boolean).forEach((r) => {
    if (r.t && r.t.kind === 'owner_gate' && r.t.owner_question) ownerQuestions.push(`${r.id}: ${r.t.owner_question}`)
    report.push({ wave, id: r.id, kind: r.t ? r.t.kind : 'unknown', summary: r.t ? r.t.summary : String(r.result), rerun: r.rerun || null })
  })

  // Planning runs once per program run: it writes shared files (queue.md, lane docs) in one docs PR.
  let planned = []
  if (PLAN_NEW && !plannedOnce) {
    plannedOnce = true
    phase('Plan')
    const rows = await agent(
      `Read ${QUEUE} on origin/main (git fetch origin; git show origin/main:${QUEUE}). List every bullet under "New rows (not yet planned)" whose id has no queue table row and no open PR. ask_first = it names ${ASK_FIRST}. Copy only; judge nothing.
${STYLE}`,
      { label: 'list unplanned rows', phase: 'Plan', model: 'haiku', effort: 'low', schema: ROWS_SCHEMA },
    )
    const unplanned = (rows && rows.rows) || []
    if (unplanned.length) {
      const facts = (await parallel(unplanned.map((r) => () => agent(
        `Read-only code search for unplanned queue row ${r.id}: "${r.summary}". Find the exact files and line ranges involved, existing tests that cover the behaviour, and the test file a fix would extend. Quote file:line for every claim. Edit nothing.
${STYLE}`,
        { label: `search ${r.id}`, phase: 'Plan', model: 'haiku', effort: 'low', schema: FACTS_SCHEMA },
      )))).filter(Boolean)
      const plan = await agent(
        `You are an Opus planning sub-orchestrator. Turn these unplanned queue rows into planned ones in ONE docs-only PR (branch docs/plan-new-rows-<short main sha>, worktree outside the main checkout).
Rows:\n${JSON.stringify(unplanned, null, 1)}\nCode facts from Haiku search (a lead, not a finding; spot-check the decisive ones):\n${JSON.stringify(facts, null, 1)}
For each row: a plan section in the right lane doc (lane-A..F under docs/plans/2026-10-15-build-program/) with tasks, RED-first test ids and assertions that fail on today's main, acceptance commands, file list and expected collected delta; then a queue table row in the right wave with depends_on, owner gates, ask-first, files, est h, runtime claude, status.
Rows with ask_first=true: plan them, set status "blocked: owner yes on the <file> diff", and list them in owner_questions. A row whose fix is a product choice (wording, what patients see): add a gate id, status blocked, and put the question with options and your recommendation in owner_questions. Never write product code.
Regenerate docs (python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph), open the PR with a RUNBOOK §6 body, wait for CI green. Do not merge.
${STYLE}`,
        { label: 'plan new rows', phase: 'Plan', model: 'opus', effort: 'high', schema: PLAN_SCHEMA },
      )
      if (plan) {
        planned = plan.planned
        ownerQuestions.push(...plan.owner_questions)
        report.push({ wave, id: 'PLAN', kind: 'plan', summary: `planned ${plan.planned.join(', ')} in PR #${plan.pr_number || '?'}` })
      }
    }
  }

  let merged = []
  if (AUTO_MERGE) {
    phase('Merge')
    const m = await agent(
      `You are the Opus merge sub-orchestrator. The owner authorised agent merges (check ${DECISIONS} on origin/main for the current authorising row and quote it; if none, merge nothing and say so).
Merge each open PR that meets ALL: not draft; every CI check green on its head; final review VERDICT APPROVE or PASS in its body; no edit to ${ASK_FIRST}; no unanswered merge-only gate in its queue row; not a PR the queue says merges later (e.g. #68 merges last). Use gh pr merge <n> --merge (never squash, never --admin, never force).
Then run the post-merge batch (contracts.md §d step 3): re-measure the collected count on the new main with ~/venvs/asclexis-311/bin/python through scripts/pyslot.sh, update the CLAUDE.md/AGENT.md slots and queue statuses in one docs PR, wait for green, merge it.
${STYLE}`,
      { label: `merge wave ${wave}`, phase: 'Merge', model: 'opus', effort: 'high', schema: MERGE_SCHEMA },
    )
    if (m) {
      merged = m.merged
      report.push({ wave, id: 'MERGE', kind: 'merge', summary: `merged ${m.merged.join(', ') || 'none'}; skipped ${m.skipped.length}; batch ${m.batch_pr || 'none'}` })
    }
  }

  notEligible.forEach((n) => { if (/owner|gate/i.test(n.reason)) ownerQuestions.push(`${n.id}: ${n.reason}`) })
  // Dry: nothing started, planned or merged. Without auto_merge, nothing new can become eligible until a human merges.
  if (!picked.length && !planned.length && !merged.length) { log(`dry after wave ${wave}`); break }
  if (!AUTO_MERGE) { log('auto_merge off: stopping after this wave; the owner merges, then re-run'); break }
}

return {
  report,
  owner_questions: [...new Set(ownerQuestions)],
  next: AUTO_MERGE
    ? 'Answer owner_questions, then re-run build-program.'
    : 'Owner merges the ready PRs, L0 runs the post-merge batch, then re-run build-program.',
}
